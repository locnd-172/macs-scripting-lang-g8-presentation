from shop_db import CheckoutError, create_database


def connect():
    return create_database()


def checkout(conn, customer, sku, quantity):
    # update stock
    with conn:
        conn.execute(
            "UPDATE products SET stock = stock - ? WHERE sku = ?", (quantity, sku)
        )

    # check for known customer and insert order
    with conn:
        known = conn.execute(
            "SELECT 1 FROM customers WHERE name = ?", (customer,)
        ).fetchone()

        if known is None:
            raise CheckoutError(f"unknown customer: {customer}")

        conn.execute("INSERT INTO orders VALUES (?, ?, ?)", (customer, sku, quantity))
