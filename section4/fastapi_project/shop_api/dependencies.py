"""Dependencies injected into the route handlers."""

import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from shop_api.metrics import Metrics


def get_connection(request: Request) -> Iterator[sqlite3.Connection]:
    """One pooled connection per request.

    A dependency with `yield` is a context manager: FastAPI runs the code before `yield`
    when the request arrives and the code after it once the request is finished, on
    success and on error alike.
    """
    with request.app.state.pool.connection() as conn:
        yield conn


def get_metrics(request: Request) -> Metrics:
    return request.app.state.metrics


Connection = Annotated[sqlite3.Connection, Depends(get_connection)]
MetricsDep = Annotated[Metrics, Depends(get_metrics)]
