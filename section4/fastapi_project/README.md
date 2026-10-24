# Shop API: context managers in a real FastAPI service

A small product-and-orders service. It is built so that each place a context manager
appears is one a production service would genuinely need: owning resources for the life
of the app, borrowing them per request, making multi-step writes atomic, guarding shared
state across threads, and keeping tests clean.

Requires Python 3.11+. Dependency versions are pinned to the ones the project was tested with.

## Run it

```bash
cd presentation/section4/fastapi_project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest                                                   # 31 tests
uvicorn shop_api.main:create_app --factory --reload      # http://127.0.0.1:8000/docs
```

The database file defaults to `shop.db` in the working directory; set `SHOP_DB` to change it.

```bash
curl -F "file=@sample_data/products.csv" localhost:8000/products/import
curl -F "file=@sample_data/products_bad.csv" localhost:8000/products/import   # 422, line 3
curl localhost:8000/products
curl -H 'content-type: application/json' localhost:8000/orders \
     -d '{"items": [{"sku": "KB-001", "quantity": 2}]}'
curl -H 'content-type: application/json' localhost:8000/orders \
     -d '{"items": [{"sku": "KB-001", "quantity": 1}, {"sku": "HD-003", "quantity": 9}]}'  # 409
curl localhost:8000/products/KB-001      # stock is 8: the failed order took nothing
curl localhost:8000/metrics
```

## Where the context managers are

| # | Context manager | Where | What it guarantees | Section 4 application |
|---|---|---|---|---|
| 1 | `lifespan` (`@asynccontextmanager`) | [main.py](shop_api/main.py) | App-wide resources are acquired before the first request and released after the last | The app's outermost scope |
| 2 | `ExitStack` inside the lifespan | [main.py](shop_api/main.py) | `pool_size` connections, a number known only at runtime. If opening one fails, the earlier ones are closed. Shutdown closes them in reverse order | ExitStack |
| 3 | `ConnectionPool.connection()` (`@contextmanager`) | [database.py](shop_api/database.py) | A borrowed connection always goes back to the pool, and is rolled back if the borrower left a transaction open | Generator-based managers |
| 4 | `get_connection` (dependency with `yield`) | [dependencies.py](shop_api/dependencies.py) | One connection per request, released on success and on error | Same idea, scoped to a request |
| 5 | `atomic(conn)` in `place_order` / `import_products` | [services.py](shop_api/services.py), [transactions.py](shop_api/transactions.py) | Reserving stock for every order line and recording the order commit together or not at all. It nests: a real transaction when outermost, a savepoint inside another | Database transactions |
| 6 | `with self._lock:` in `Metrics` | [metrics.py](shop_api/metrics.py) | Counters updated from FastAPI's worker threads never lose an update | Thread locks |
| 7 | `borrowed_text()` (`@contextmanager`) | [csv_import.py](shop_api/csv_import.py) | The upload is read as text, then handed back to the framework still open. The parser takes a stream and never opens or closes anything | Files & ETL |
| 8 | `TemporaryDirectory`, `TestClient`, `io.StringIO` | [tests/](tests/) | Each test file gets a throwaway database. Each test runs inside a transaction that is rolled back, so it starts from the same state without rebuilding anything. Entering `TestClient` runs the lifespan. Parser tests need no files | Temporary resources, StringIO & dependency injection |

### One request, end to end

```
POST /orders
  └─ get_connection (dependency)            enter: borrow a connection from the pool
       └─ create_order (route)
            └─ place_order: with atomic()   enter: begin transaction
                 reserve line 1, then line 2 raises InsufficientStock
                                            exit: roll back, line 1's reservation is undone
       get_connection exit                  return the connection to the pool
  the registered error handler answers 409
```

The same exits run when everything succeeds, with a commit instead of a rollback. The `with`
statements decide what happens on each path, so no route handler contains cleanup code.

## Design notes

- **Why a pool and a lifespan, with SQLite?** SQLite needs nothing installed, and the shape
  carries over unchanged to Postgres: swap `connect()` and keep the pool, lifespan and
  dependency as they are.
- **Why `def` handlers, not `async def`?** `sqlite3` blocks. FastAPI runs plain `def`
  handlers in a thread pool, which is also why the connections use `check_same_thread=False`
  and why `Metrics` needs a lock.
- **Test isolation.** `tests/conftest.py` opens a transaction, hands that connection to the routes through `dependency_overrides`, and rolls it back after the test. This works because the routes use `atomic()`, which becomes a savepoint inside the test's transaction. A plain `with conn:` would commit for real, and `tests/test_isolation.py` would fail. Only database state is undone: in-process state such as `Metrics` is replaced per test, and tests that need several connections or real concurrency need their own database.
- **Atomic imports.** `parse_products` reads the whole upload before anything is written, so
  a bad row at line 900 never leaves the first 899 rows behind.
- **Not included:** authentication, upload size limits, and shared metrics across multiple
  worker processes (each process keeps its own counters).
