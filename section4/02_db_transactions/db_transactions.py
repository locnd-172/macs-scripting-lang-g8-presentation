"""Application 2 - Database transactions.

A transfer is two updates: take money from one account, give it to another.
If the second update fails, the first one must not stay behind.

`with conn:` is how sqlite3 does it. It commits when the block ends and rolls back on an
exception, but it does not close the connection. Other libraries behave differently.
"""

import sqlite3
from contextlib import closing


def open_bank():
    conn = sqlite3.connect(":memory:")
    with conn:
        conn.execute("CREATE TABLE accounts (name TEXT PRIMARY KEY, balance INTEGER NOT NULL)")
        conn.executemany("INSERT INTO accounts VALUES (?, ?)", [("alice", 100), ("bob", 50)])
    return conn


def show(conn):
    rows = conn.execute("SELECT name, balance FROM accounts ORDER BY name").fetchall()
    balances = " ".join(f"{name}={balance}" for name, balance in rows)
    total = sum(balance for _, balance in rows)
    return f"{balances} total={total} | transaction open: {conn.in_transaction}"


def naive_transfer(conn, source, target, amount):
    conn.execute("UPDATE accounts SET balance = balance - ? WHERE name = ?", (amount, source))
    credit = conn.execute(
        "UPDATE accounts SET balance = balance + ? WHERE name = ?", (amount, target)
    )
    if credit.rowcount == 0:
        raise LookupError(f"no such account: {target}")
    conn.commit()  # skipped when the credit fails


def managed_transfer(conn, source, target, amount):
    with conn:  # commit at the end, roll back if anything raises
        conn.execute("UPDATE accounts SET balance = balance - ? WHERE name = ?", (amount, source))
        credit = conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE name = ?", (amount, target)
        )
        if credit.rowcount == 0:
            raise LookupError(f"no such account: {target}")


def run(title, transfer):
    print(title, "(the total must stay 150)")
    with closing(open_bank()) as conn:  # sqlite3's own `with conn:` never closes it
        transfer(conn, "alice", "bob", 30)
        print("  alice -> bob   :", show(conn))

        try:
            transfer(conn, "alice", "carol", 50)
        except LookupError as error:
            print("  alice -> carol : failed,", error)
        print("  after failure  :", show(conn))

        conn.commit()  # some later, unrelated commit in the application
        print("  after a commit :", show(conn))


def main():
    run("Naive: execute, then commit() at the end", naive_transfer)
    run("With a context manager: `with conn:`", managed_transfer)


if __name__ == "__main__":
    main()
