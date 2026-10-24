import sqlite3
import tempfile
import threading
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shop_api.database import ConnectionPool, PoolExhausted, connect
from shop_api.main import create_app
from shop_api.metrics import Metrics


def memory_pool(size: int) -> ConnectionPool:
    return ConnectionPool([sqlite3.connect(":memory:") for _ in range(size)])


def test_pool_takes_the_connection_back_after_an_error() -> None:
    pool = memory_pool(2)
    with pytest.raises(RuntimeError), pool.connection():
        assert pool.idle == 1
        raise RuntimeError("request failed")
    assert pool.idle == 2


def test_pool_rolls_back_an_unfinished_transaction() -> None:
    pool = memory_pool(1)  # one connection, so the second checkout gets the same one back
    with pool.connection() as conn:
        conn.execute("CREATE TABLE t (x)")
        conn.commit()
        conn.execute("INSERT INTO t VALUES (1)")  # opens a transaction that is never committed
    with pool.connection() as conn:
        assert not conn.in_transaction
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0


def test_pool_gives_up_when_every_connection_is_lent_out() -> None:
    pool = memory_pool(2)
    with (
        pool.connection(),
        pool.connection(),
        pytest.raises(PoolExhausted),
        pool.connection(timeout=0.05),
    ):
        pass


def test_metrics_do_not_lose_updates_across_threads() -> None:
    metrics = Metrics()

    def worker() -> None:
        for _ in range(5_000):
            metrics.increment("hits")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert metrics.snapshot() == {"hits": 40_000}


def test_lifespan_opens_resources_at_startup_and_closes_them_at_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[sqlite3.Connection] = []

    def recording_connect(db_path: Path) -> sqlite3.Connection:
        opened.append(connect(db_path))
        return opened[-1]

    monkeypatch.setattr("shop_api.main.connect", recording_connect)
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(db_path=Path(tmp) / "shop.db", pool_size=3)
        assert not hasattr(app.state, "pool")

        with TestClient(app):
            assert app.state.pool.idle == 3
            assert [conn.execute("SELECT 1").fetchone()[0] for conn in opened] == [1, 1, 1]

    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):  # closed at shutdown
            conn.execute("SELECT 1")


def test_lifespan_closes_earlier_connections_when_a_later_one_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened: list[sqlite3.Connection] = []

    def flaky_connect(db_path: Path) -> sqlite3.Connection:
        if len(opened) == 2:
            raise sqlite3.OperationalError("cannot open the third connection")
        opened.append(connect(db_path))
        return opened[-1]

    monkeypatch.setattr("shop_api.main.connect", flaky_connect)
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(db_path=Path(tmp) / "shop.db", pool_size=3)
        with pytest.raises(sqlite3.OperationalError), TestClient(app):
            pass

    assert len(opened) == 2
    for conn in opened:
        with pytest.raises(sqlite3.ProgrammingError):  # already closed by the ExitStack
            conn.execute("SELECT 1")


def test_connect_enforces_foreign_keys() -> None:
    with tempfile.TemporaryDirectory() as tmp, closing(connect(Path(tmp) / "shop.db")) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
