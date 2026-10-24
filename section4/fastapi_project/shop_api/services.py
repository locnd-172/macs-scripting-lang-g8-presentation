"""Business operations. Each write is exactly one transaction."""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from shop_api.csv_import import Product
from shop_api.transactions import atomic


class UnknownProduct(LookupError):
    """A SKU that is not in the catalogue."""


class InsufficientStock(Exception):
    """Fewer units in stock than the order asks for."""


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int


@dataclass(frozen=True)
class PlacedOrder:
    order_id: int
    total_cents: int


INSERT_ORDER_ITEM = """
INSERT INTO order_items (order_id, sku, quantity, unit_price_cents) VALUES (?, ?, ?, ?)
"""

UPSERT_PRODUCT = """
INSERT INTO products (sku, name, price_cents, stock) VALUES (?, ?, ?, ?)
ON CONFLICT (sku) DO UPDATE SET
    name = excluded.name,
    price_cents = excluded.price_cents,
    stock = excluded.stock
"""


def list_products(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM products ORDER BY sku").fetchall()


def get_product(conn: sqlite3.Connection, sku: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
    if row is None:
        raise UnknownProduct(f"unknown product: {sku}")
    return row


def import_products(conn: sqlite3.Connection, products: Sequence[Product]) -> int:
    with atomic(conn):  # the whole catalogue update commits together, or not at all
        conn.executemany(
            UPSERT_PRODUCT, [(p.sku, p.name, p.price_cents, p.stock) for p in products]
        )
    return len(products)


def place_order(conn: sqlite3.Connection, lines: Sequence[OrderLine]) -> PlacedOrder:
    """Reserve stock for every line and record the order, atomically.

    If any line cannot be fulfilled, the reservations made for earlier lines are rolled back.
    """
    with atomic(conn):  # commit on success, roll back if anything below raises
        priced = [(line, _reserve(conn, line)) for line in lines]
        total = sum(unit_price * line.quantity for line, unit_price in priced)
        order_id = conn.execute("INSERT INTO orders (total_cents) VALUES (?)", (total,)).lastrowid
        conn.executemany(
            INSERT_ORDER_ITEM,
            [(order_id, line.sku, line.quantity, unit_price) for line, unit_price in priced],
        )
    return PlacedOrder(order_id=order_id, total_cents=total)


def _reserve(conn: sqlite3.Connection, line: OrderLine) -> int:
    """Take `line.quantity` units out of stock and return the unit price in cents."""
    unit_price = get_product(conn, line.sku)["price_cents"]
    updated = conn.execute(
        "UPDATE products SET stock = stock - ? WHERE sku = ? AND stock >= ?",
        (line.quantity, line.sku, line.quantity),
    )
    if updated.rowcount == 0:
        raise InsufficientStock(f"not enough stock for {line.sku}")
    return unit_price
