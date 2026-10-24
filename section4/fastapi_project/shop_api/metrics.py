"""In-process counters shared by every worker thread."""

import threading
from collections import Counter


class Metrics:
    """Counters updated from FastAPI's worker threads.

    `count += 1` is a read-modify-write, not an atomic step, so every access to the
    counters happens inside the critical section guarded by the lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Counter[str] = Counter()

    def increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)
