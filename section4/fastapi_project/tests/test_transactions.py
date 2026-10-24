import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest

from shop_api.database import connect
from shop_api.transactions import atomic


@pytest.fixture
def db_path() -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.db"
        with closing(connect(path)) as conn:
            conn.execute("CREATE TABLE t (x INTEGER)")
        yield path


def rows(db_path: Path) -> list[int]:
    """What a second connection sees: only committed data."""
    with closing(connect(db_path)) as other:
        return [x for (x,) in other.execute("SELECT x FROM t ORDER BY x")]


def test_commits_on_success(db_path: Path) -> None:
    with closing(connect(db_path)) as conn, atomic(conn):
        conn.execute("INSERT INTO t VALUES (1)")
    assert rows(db_path) == [1]


def test_rolls_back_and_reraises_on_error(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        with pytest.raises(RuntimeError), atomic(conn):
            conn.execute("INSERT INTO t VALUES (1)")
            raise RuntimeError("boom")
        assert not conn.in_transaction
    assert rows(db_path) == []


def test_a_failed_inner_scope_undoes_only_its_own_work(db_path: Path) -> None:
    with closing(connect(db_path)) as conn, atomic(conn):
        conn.execute("INSERT INTO t VALUES (1)")
        with pytest.raises(RuntimeError), atomic(conn):
            conn.execute("INSERT INTO t VALUES (2)")
            raise RuntimeError("tolerated by the caller")
        conn.execute("INSERT INTO t VALUES (3)")
    assert rows(db_path) == [1, 3]


def test_a_failed_outer_scope_undoes_the_inner_work_too(db_path: Path) -> None:
    with closing(connect(db_path)) as conn, pytest.raises(RuntimeError), atomic(conn):
        with atomic(conn):
            conn.execute("INSERT INTO t VALUES (1)")
        raise RuntimeError("the outer step fails after the inner one succeeded")
    assert rows(db_path) == []


def test_inside_an_open_transaction_it_never_commits(db_path: Path) -> None:
    with closing(connect(db_path)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        with atomic(conn):
            conn.execute("INSERT INTO t VALUES (1)")
        assert rows(db_path) == []  # released a savepoint, did not commit
        conn.rollback()
    assert rows(db_path) == []


def test_requires_manual_transaction_control() -> None:
    with (
        closing(sqlite3.connect(":memory:")) as conn,
        pytest.raises(ValueError, match="isolation_level=None"),
        atomic(conn),
    ):
        pass
