"""Two small integration tests, and the fixture that runs them (Act 2 of the v2 demo)."""

from contextlib import contextmanager

from shop_db import SEED_STOCK, get_stock


def test_checkout_reserves_stock(shop, conn):
    shop.checkout(conn, "alice", "KB-1", 1)
    assert get_stock(conn, "KB-1") == SEED_STOCK - 1


def test_each_test_starts_from_the_seed_data(shop, conn):
    stock = get_stock(conn, "KB-1")
    assert stock == SEED_STOCK, f"stock is {stock}, expected {SEED_STOCK}"


@contextmanager
def rolled_back(conn):
    """The fixture: the test runs inside a transaction that is undone afterwards."""
    conn.execute("BEGIN")
    try:
        yield
    finally:
        conn.rollback()


def run_tests(shop, conn):
    for test in [test_checkout_reserves_stock, test_each_test_starts_from_the_seed_data]:
        with rolled_back(conn):
            try:
                test(shop, conn)
            except AssertionError as error:
                print(f"    FAIL {test.__name__}: {error}")
            else:
                print(f"    PASS {test.__name__}")
