from contextlib import closing

import shop_atomic
import shop_naive
from shop_db import CheckoutError, snapshot


SHOPS = [
    ("naive", shop_naive), 
    ("atomic", shop_atomic)
]
CHECKOUTS = [
    ("emma", "known customer"), 
    ("liam", "unknown customer")
]


def main():
    for customer, description in CHECKOUTS:
        print(f"\n{customer} ({description}) orders 1 item")
        for name, shop in SHOPS:
            with closing(shop.connect()) as conn:
                try:
                    shop.checkout(conn, customer, "item", 1)
                    result = "complete"
                except CheckoutError:
                    result = "failed"
                print(f"  {name:<10} {snapshot(conn):<20} {result}")


if __name__ == "__main__":
    main()
