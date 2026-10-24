"""Application 2 (v2) - Transactions across functions, and a fresh database for every test.

Two real-world problems with one tool: a transaction scope that can be nested (atomic.py).

  Act 1  checkout() calls three functions that each write. They must all succeed or all fail.
  Act 2  integration tests need a clean database for each test, without rebuilding it.

shop_naive.py wraps every function in `with conn:`. shop_atomic.py uses atomic().
`with conn:` commits as soon as its block ends, so an inner function commits early and the
outer `with` protects nothing. A test that is wrapped in BEGIN / ROLLBACK breaks the same way:
the code under test commits, and the rollback has nothing left to undo.
"""

import shop_atomic
import shop_naive
from shop_db import CheckoutError, snapshot
from shop_tests import run_tests

SHOPS = [("naive", shop_naive), ("atomic()", shop_atomic)]

CHECKOUTS = [
    ("alice", "a regular customer"),
    ("carol", "not a customer"),
    ("bob", "has no loyalty account"),
]


def show_composition():
    print("Act 1 - checkout() = reserve_stock() + record_order() + award_points()")
    for customer, description in CHECKOUTS:
        print(f"  {customer} ({description}) buys 1 KB-1")
        for name, shop in SHOPS:
            conn = shop.connect()
            before = snapshot(conn)
            try:
                shop.checkout(conn, customer, "KB-1", 1)
                result = "ok"
            except CheckoutError:
                saved = snapshot(conn) != before
                result = "failed, PARTLY SAVED" if saved else "failed, nothing saved"
            print(f"    {name:<8}: {snapshot(conn)}  {result}")


def show_test_isolation():
    print("Act 2 - a fresh database for every test (one database per test file)")
    for name, shop in SHOPS:
        print(f"  {name}")
        run_tests(shop, shop.connect())


def main():
    show_composition()
    print()
    show_test_isolation()


if __name__ == "__main__":
    main()
