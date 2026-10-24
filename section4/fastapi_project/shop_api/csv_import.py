"""Parsing product CSV files.

Nothing in this module opens or closes a file. The parser is handed a text stream, so the
same code serves an HTTP upload, a file on disk, or an in-memory string in a test.
"""

import csv
import io
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import BinaryIO, TextIO

REQUIRED_COLUMNS = frozenset({"sku", "name", "price", "stock"})


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int
    stock: int


class ProductImportError(ValueError):
    """The CSV could not be turned into products. `line` is the 1-based line at fault."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line


@contextmanager
def borrowed_text(binary: BinaryIO, encoding: str = "utf-8-sig") -> Iterator[TextIO]:
    """View a binary file as text without taking ownership of it.

    TextIOWrapper closes the file it wraps when it is discarded. Detaching in `finally`
    hands the file back to its owner (here, the web framework) still open.
    """
    text = io.TextIOWrapper(binary, encoding=encoding, newline="")
    try:
        yield text
    finally:
        text.detach()


def parse_products(stream: TextIO) -> list[Product]:
    """Read every row or raise ProductImportError; never returns a partial result."""
    reader = csv.DictReader(stream)
    missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
    if missing:
        raise ProductImportError(1, f"missing columns: {', '.join(sorted(missing))}")

    products: list[Product] = []
    try:
        for row in reader:
            try:
                products.append(_parse_row(row))
            except ValueError as exc:
                raise ProductImportError(reader.line_num, str(exc)) from None
    except (UnicodeDecodeError, csv.Error):
        raise ProductImportError(reader.line_num, "not a valid UTF-8 CSV file") from None
    return products


def _parse_row(row: Mapping[str, str | None]) -> Product:
    sku = (row["sku"] or "").strip()
    name = (row["name"] or "").strip()
    if not sku or not name:
        raise ValueError("sku and name are required")
    return Product(sku, name, _to_cents(row["price"] or ""), _to_stock(row["stock"] or ""))


def _to_cents(text: str) -> int:
    try:
        price = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"invalid price {text!r}") from None
    if not price.is_finite() or price < 0 or price != price.quantize(Decimal("0.01")):
        raise ValueError(f"price must be a non-negative amount with at most 2 decimals: {text!r}")
    return int(price * 100)


def _to_stock(text: str) -> int:
    try:
        stock = int(text)
    except ValueError:
        raise ValueError(f"invalid stock {text!r}") from None
    if stock < 0:
        raise ValueError(f"stock must not be negative: {text!r}")
    return stock
