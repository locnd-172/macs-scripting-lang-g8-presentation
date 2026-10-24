import io

import pytest
from fastapi.testclient import TestClient

from shop_api.csv_import import Product, ProductImportError, borrowed_text, parse_products
from tests.helpers import SAMPLE_DATA, upload

HEADER = "sku,name,price,stock\n"


# The parser takes a stream, so these tests need no files: an in-memory stream is enough.


def test_parse_products_reads_every_row() -> None:
    stream = io.StringIO(HEADER + "KB-1,Keyboard,89.90,10\nMS-2,Mouse,24.50,0\n")
    assert parse_products(stream) == [
        Product("KB-1", "Keyboard", 8990, 10),
        Product("MS-2", "Mouse", 2450, 0),
    ]


@pytest.mark.parametrize(
    ("row", "line"),
    [
        ("KB-1,Keyboard,free,10", 2),
        ("KB-1,Keyboard,89.999,10", 2),
        ("KB-1,Keyboard,89.90,-1", 2),
        ("KB-1,Keyboard,89.90,ten", 2),
        (",Keyboard,89.90,10", 2),
    ],
)
def test_parse_products_reports_the_bad_line(row: str, line: int) -> None:
    with pytest.raises(ProductImportError) as error:
        parse_products(io.StringIO(HEADER + row + "\n"))
    assert error.value.line == line


def test_parse_products_requires_all_columns() -> None:
    with pytest.raises(ProductImportError, match="missing columns: price, stock"):
        parse_products(io.StringIO("sku,name\nKB-1,Keyboard\n"))


def test_borrowed_text_hands_the_file_back_open() -> None:
    upload_file = io.BytesIO((HEADER + "KB-1,Keyboard,89.90,10\n").encode())
    with borrowed_text(upload_file) as text:
        assert len(parse_products(text)) == 1
    assert not upload_file.closed


def test_import_then_list(client: TestClient) -> None:
    response = upload(client, SAMPLE_DATA / "products.csv")
    assert response.status_code == 200
    assert response.json() == {"imported": 3}

    skus = [product["sku"] for product in client.get("/products").json()]
    assert skus == ["HD-003", "KB-001", "MS-002"]


def test_bad_upload_is_rejected_and_nothing_is_imported(client: TestClient) -> None:
    response = upload(client, SAMPLE_DATA / "products_bad.csv")
    assert response.status_code == 422
    assert "line 3" in response.json()["detail"]
    assert client.get("/products").json() == []


def test_unknown_product_is_404(client: TestClient) -> None:
    assert client.get("/products/NOPE").status_code == 404
