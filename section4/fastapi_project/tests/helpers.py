from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

SAMPLE_DATA = Path(__file__).parent.parent / "sample_data"


def upload(client: TestClient, path: Path) -> Any:
    with path.open("rb") as f:
        return client.post("/products/import", files={"file": (path.name, f, "text/csv")})
