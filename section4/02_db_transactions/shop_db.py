"""The shop database for the v2 demo: schema, seed data, and two helpers for printing."""

import sqlite3

SEED_STOCK = 10

SCHEMA = f"""
CREATE TABLE products (sku TEXT PRIMARY KEY, stock INTEGER NOT NULL);
CREATE TABLE customers (name TEXT PRIMARY KEY);
CREATE TABLE loyalty (customer TEXT PRIMARY KEY, points INTEGER NOT NULL);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    sku TEXT NOT NULL,
    quantity INTEGER NOT NULL
);

INSERT INTO products VALUES ('KB-1', {SEED_STOCK});
INSERT INTO customers VALUES ('alice'), ('bob');
INSERT INTO loyalty VALUES ('alice', 0);  -- bob has no loyalty account
"""


class CheckoutError(Exception):
    pass


def create_database(**options):
    conn = sqlite3.connect(":memory:", **options)
    conn.executescript(SCHEMA)
    return conn


def get_stock(conn, sku):
    return conn.execute("SELECT stock FROM products WHERE sku = ?", (sku,)).fetchone()[0]


def snapshot(conn):
    stock = get_stock(conn, "KB-1")
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    points = conn.execute("SELECT SUM(points) FROM loyalty").fetchone()[0]
    return f"stock={stock} orders={orders} points={points}"
