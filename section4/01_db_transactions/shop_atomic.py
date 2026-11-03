from atomic import atomic
from shop_db import CheckoutError, create_database


def connect():
    # Let atomic() control when the transaction starts and ends.
    return create_database(isolation_level=None)


def checkout(conn, customer, sku, quantity):
    #  update stock, check for known customer, and insert order in a single atomic transaction
    with atomic(conn):
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE sku = ?", (quantity, sku)
        )

        known = conn.execute(
            "SELECT 1 FROM customers WHERE name = ?", (customer,)
        ).fetchone()

        if known is None:
            raise CheckoutError(f"unknown customer: {customer}")

        conn.execute("INSERT INTO orders VALUES (?, ?, ?)", (customer, sku, quantity))
