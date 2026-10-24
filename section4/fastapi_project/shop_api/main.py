"""Application factory and lifespan.

Run with:  uvicorn shop_api.main:create_app --factory
"""

import os
from collections.abc import AsyncIterator
from contextlib import ExitStack, asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI

from shop_api.database import ConnectionPool, connect, initialise_schema
from shop_api.errors import add_error_handlers
from shop_api.metrics import Metrics
from shop_api.routes import router

DEFAULT_DB_PATH = Path(os.environ.get("SHOP_DB", "shop.db"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Everything the app owns for its whole life: acquired at startup, released at shutdown."""
    with ExitStack() as stack:
        # The pool size is a runtime setting, so the number of connections is not known
        # when the code is written. If opening one fails, those already open are closed.
        connections = [
            stack.enter_context(closing(connect(app.state.db_path)))
            for _ in range(app.state.pool_size)
        ]
        initialise_schema(connections[0])
        app.state.pool = ConnectionPool(connections)
        app.state.metrics = Metrics()
        yield
    # Leaving the `with` closed every connection, last opened first.


def create_app(db_path: Path = DEFAULT_DB_PATH, pool_size: int = 4) -> FastAPI:
    app = FastAPI(title="Shop API", lifespan=lifespan)
    app.state.db_path = db_path
    app.state.pool_size = pool_size
    app.include_router(router)
    add_error_handlers(app)
    return app
