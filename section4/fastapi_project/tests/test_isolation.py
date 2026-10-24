"""Every test starts from the same database, although the app commits through atomic()."""

from fastapi.testclient import TestClient


def test_data_written_through_the_api_is_visible_within_the_test(stocked: TestClient) -> None:
    order = {"items": [{"sku": "KB-001", "quantity": 1}]}
    assert stocked.post("/orders", json=order).status_code == 201
    assert len(stocked.get("/products").json()) == 3


def test_the_next_test_starts_from_an_empty_database(client: TestClient) -> None:
    assert client.get("/products").json() == []
    assert client.get("/metrics").json() == {}
