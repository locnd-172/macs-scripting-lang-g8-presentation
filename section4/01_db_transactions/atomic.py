from contextlib import contextmanager


@contextmanager
def atomic(conn):
    conn.execute("BEGIN")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
