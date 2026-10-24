"""Turns the errors raised by the services into HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shop_api.csv_import import ProductImportError
from shop_api.database import PoolExhausted
from shop_api.services import InsufficientStock, UnknownProduct


def add_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnknownProduct)
    async def unknown_product(request: Request, error: UnknownProduct):
        return JSONResponse(status_code=404, content={"detail": str(error)})

    @app.exception_handler(InsufficientStock)
    async def insufficient_stock(request: Request, error: InsufficientStock):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ProductImportError)
    async def bad_import(request: Request, error: ProductImportError):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(PoolExhausted)
    async def pool_exhausted(request: Request, error: PoolExhausted):
        return JSONResponse(status_code=503, content={"detail": str(error)})
