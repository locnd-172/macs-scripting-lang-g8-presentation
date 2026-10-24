"""The same shop operations, with atomic() instead of `with conn:`."""

from atomic import atomic
from shop_db import CheckoutError, create_database


def connect():
    return create_database(isolation_level=None)


def reserve_stock(conn, sku, quantity):
    with atomic(conn):
        conn.execute("UPDATE products SET stock = stock - ? WHERE sku = ?", (quantity, sku))


def record_order(conn, customer, sku, quantity):
    with atomic(conn):
        known = conn.execute("SELECT 1 FROM customers WHERE name = ?", (customer,)).fetchone()
        if known is None:
            raise CheckoutError(f"unknown customer: {customer}")
        conn.execute(
            "INSERT INTO orders (customer, sku, quantity) VALUES (?, ?, ?)",
            (customer, sku, quantity),
        )


def award_points(conn, customer, points):
    with atomic(conn):
        updated = conn.execute(
            "UPDATE loyalty SET points = points + ? WHERE customer = ?", (points, customer)
        )
        if updated.rowcount == 0:
            raise CheckoutError(f"{customer} has no loyalty account")


def checkout(conn, customer, sku, quantity):
    with atomic(conn):  # one transaction: the calls below become savepoints inside it
        reserve_stock(conn, sku, quantity)
        record_order(conn, customer, sku, quantity)
        award_points(conn, customer, quantity * 10)
