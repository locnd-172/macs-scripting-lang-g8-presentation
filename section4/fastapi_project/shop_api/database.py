"""SQLite access: connections, a bounded connection pool, and the schema."""

import queue
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS products (
    sku         TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    stock       INTEGER NOT NULL CHECK (stock >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    total_cents INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id         INTEGER NOT NULL REFERENCES orders (id),
    sku              TEXT NOT NULL REFERENCES products (sku),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL
);
"""


class PoolExhausted(RuntimeError):
    """No connection became available before the timeout."""


def connect(db_path: Path) -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may run a request's dependency and its endpoint on
    # different worker threads. This is safe because the pool lends a connection to one
    # request at a time.
    # isolation_level=None: transactions are opened explicitly, by atomic().
    conn = sqlite3.connect(db_path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


class ConnectionPool:
    """A fixed set of connections that requests borrow one at a time."""

    def __init__(self, connections: Iterable[sqlite3.Connection]) -> None:
        self._idle: queue.Queue[sqlite3.Connection] = queue.Queue()
        for conn in connections:
            self._idle.put(conn)

    @property
    def idle(self) -> int:
        return self._idle.qsize()

    @contextmanager
    def connection(self, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
        """Lend a connection for the length of a `with` block and always take it back."""
        try:
            conn = self._idle.get(timeout=timeout)
        except queue.Empty:
            raise PoolExhausted(f"no connection available after {timeout}s") from None
        try:
            yield conn
        finally:
            if conn.in_transaction:
                conn.rollback()  # never hand a half-finished transaction to the next request
            self._idle.put(conn)
