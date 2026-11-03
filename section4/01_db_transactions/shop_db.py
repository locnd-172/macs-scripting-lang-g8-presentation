import sqlite3


SEED_STOCK = 10
SCHEMA = f"""
CREATE TABLE products (
    sku         TEXT PRIMARY KEY, 
    stock       INTEGER NOT NULL
);
CREATE TABLE customers (
    name        TEXT PRIMARY KEY
);
CREATE TABLE orders (
    customer    TEXT NOT NULL,
    sku         TEXT NOT NULL,
    quantity    INTEGER NOT NULL
);

INSERT INTO products VALUES ('item', {SEED_STOCK});
INSERT INTO customers VALUES ('liam');
"""


class CheckoutError(Exception):
    pass


def create_database(**options):
    conn = sqlite3.connect(":memory:", **options)
    conn.executescript(SCHEMA)
    return conn


def snapshot(conn):
    stock = conn.execute("SELECT stock FROM products WHERE sku = 'item'").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    return f"stock={stock} orders={orders}"
