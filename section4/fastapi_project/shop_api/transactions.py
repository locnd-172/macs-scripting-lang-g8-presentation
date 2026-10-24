"""A transaction scope that nests: the unit of work behind every write in the service.

  - With no transaction open, atomic() starts a real one: commit on success, rollback on error.
  - With one already open, atomic() uses a SAVEPOINT: an error undoes only the inner work.

Because the scope nests, functions can each be atomic on their own and still compose into
one larger transaction. The connection must use isolation_level=None, so that Python does
not open transactions behind our back.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from itertools import count

_savepoint_ids = count(1)


@contextmanager
def atomic(conn: sqlite3.Connection) -> Iterator[None]:
    if conn.isolation_level is not None:
        raise ValueError("atomic() needs a connection created with isolation_level=None")

    if conn.in_transaction:
        savepoint = f"sp_{next(_savepoint_ids)}"
        conn.execute(f"SAVEPOINT {savepoint}")
        try:
            yield
        except BaseException:
            conn.execute(f"ROLLBACK TO {savepoint}")
            conn.execute(f"RELEASE {savepoint}")
            raise
        conn.execute(f"RELEASE {savepoint}")
    else:
        # IMMEDIATE takes the write lock up front, so a read-then-write sequence cannot
        # fail later when two writers collide.
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
