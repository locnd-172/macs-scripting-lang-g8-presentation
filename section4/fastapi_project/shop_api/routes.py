"""HTTP routes. Handlers are plain `def`: sqlite3 blocks, so FastAPI runs them in a thread pool."""

from fastapi import APIRouter, UploadFile

from shop_api import services
from shop_api.csv_import import borrowed_text, parse_products
from shop_api.dependencies import Connection, MetricsDep
from shop_api.schemas import ImportResult, OrderRequest, OrderResponse, ProductOut
from shop_api.services import InsufficientStock, OrderLine, UnknownProduct

router = APIRouter()


@router.post("/products/import")
def import_products(file: UploadFile, conn: Connection, metrics: MetricsDep) -> ImportResult:
    # The framework owns the upload and closes it after the request; we only borrow it.
    with borrowed_text(file.file) as stream:
        products = parse_products(stream)
    imported = services.import_products(conn, products)
    metrics.increment("products_imported")
    return ImportResult(imported=imported)


@router.get("/products")
def list_products(conn: Connection) -> list[ProductOut]:
    return [ProductOut(**row) for row in services.list_products(conn)]


@router.get("/products/{sku}")
def get_product(sku: str, conn: Connection) -> ProductOut:
    return ProductOut(**services.get_product(conn, sku))


@router.post("/orders", status_code=201)
def create_order(order: OrderRequest, conn: Connection, metrics: MetricsDep) -> OrderResponse:
    lines = [OrderLine(item.sku, item.quantity) for item in order.items]
    try:
        placed = services.place_order(conn, lines)
    except (UnknownProduct, InsufficientStock):
        metrics.increment("orders_rejected")
        raise
    metrics.increment("orders_placed")
    return OrderResponse(order_id=placed.order_id, total_cents=placed.total_cents)


@router.get("/metrics")
def read_metrics(metrics: MetricsDep) -> dict[str, int]:
    return metrics.snapshot()
