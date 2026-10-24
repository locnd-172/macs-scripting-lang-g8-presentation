import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shop_api.database import connect
from shop_api.dependencies import get_connection, get_metrics
from shop_api.main import create_app
from shop_api.metrics import Metrics
from tests.helpers import SAMPLE_DATA, upload


@pytest.fixture(scope="module")
def app() -> Iterator[FastAPI]:
    """One app with its own throwaway database per test file."""
    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(db_path=Path(tmp) / "shop.db", pool_size=2)
        with TestClient(app):  # entering the client runs the lifespan, which creates the schema
            yield app
        # The lifespan has closed its connections, so the directory can now be removed.


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client whose requests all run inside one transaction, undone when the test ends.

    The routes receive this transaction's connection instead of one from the pool. Their
    atomic() scopes become savepoints inside it, so nothing is really committed.
    """
    conn = connect(app.state.db_path)
    conn.execute("BEGIN IMMEDIATE")
    metrics = Metrics()  # in-process state is not rolled back, so each test gets its own
    app.dependency_overrides[get_connection] = lambda: conn
    app.dependency_overrides[get_metrics] = lambda: metrics
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        conn.rollback()
        conn.close()


@pytest.fixture
def stocked(client: TestClient) -> TestClient:
    """The client after importing the sample catalogue."""
    upload(client, SAMPLE_DATA / "products.csv")
    return client
