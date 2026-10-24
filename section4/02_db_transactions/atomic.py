"""atomic(): a transaction scope that can be nested.

Outermost, it starts a real transaction: commit at the end, rollback on an error.
Inside a transaction that is already open, it uses a savepoint instead, so an error
undoes only the work done inside it.

The connection has to be created with isolation_level=None, otherwise Python opens
transactions on its own and gets in the way.
"""

from contextlib import contextmanager
from itertools import count

savepoint_numbers = count(1)


@contextmanager
def atomic(conn):
    if conn.isolation_level is not None:
        raise ValueError("atomic() needs a connection with isolation_level=None")

    if conn.in_transaction:
        name = f"sp{next(savepoint_numbers)}"
        conn.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            conn.execute(f"ROLLBACK TO {name}")
            conn.execute(f"RELEASE {name}")
            raise
        conn.execute(f"RELEASE {name}")
    else:
        # IMMEDIATE takes the write lock right away, so two writers cannot
        # collide halfway through a read-then-write
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
