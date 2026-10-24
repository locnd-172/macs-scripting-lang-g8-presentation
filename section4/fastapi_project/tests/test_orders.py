from fastapi.testclient import TestClient


def stock(client: TestClient, sku: str) -> int:
    return client.get(f"/products/{sku}").json()["stock"]


def order(client: TestClient, *items: tuple[str, int]):
    payload = {"items": [{"sku": sku, "quantity": quantity} for sku, quantity in items]}
    return client.post("/orders", json=payload)


def test_order_reserves_stock_and_totals_the_lines(stocked: TestClient) -> None:
    response = order(stocked, ("KB-001", 2), ("MS-002", 1))
    assert response.status_code == 201
    assert response.json()["total_cents"] == 2 * 8990 + 2450
    assert stock(stocked, "KB-001") == 8
    assert stock(stocked, "MS-002") == 24


def test_failing_line_rolls_back_the_reservations_made_before_it(stocked: TestClient) -> None:
    # KB-001 is reserved first; HD-003 only has 3 in stock, so the whole order must fail.
    response = order(stocked, ("KB-001", 1), ("HD-003", 5))
    assert response.status_code == 409
    assert stock(stocked, "KB-001") == 10
    assert stock(stocked, "HD-003") == 3


def test_unknown_sku_rolls_back_too(stocked: TestClient) -> None:
    response = order(stocked, ("KB-001", 1), ("NOPE", 1))
    assert response.status_code == 404
    assert stock(stocked, "KB-001") == 10


def test_invalid_order_body_is_rejected(stocked: TestClient) -> None:
    assert stocked.post("/orders", json={"items": []}).status_code == 422
    assert order(stocked, ("KB-001", 0)).status_code == 422


def test_metrics_count_each_outcome(stocked: TestClient) -> None:
    order(stocked, ("KB-001", 1))
    order(stocked, ("HD-003", 99))
    assert stocked.get("/metrics").json() == {
        "products_imported": 1,
        "orders_placed": 1,
        "orders_rejected": 1,
    }
