"""Application 4 - Temporary resources.

A report is built in a scratch folder. The folder has to be deleted however the
function ends: normally, with an exception, or with an early return.

NamedTemporaryFile works the same way for a single file. An open one cannot be
reopened by name on Windows, so check the docs before relying on it.
"""

import shutil
import tempfile
from contextlib import suppress
from pathlib import Path


def write_report(folder, rows):
    if any(row < 0 for row in rows):
        raise ValueError("negative row")
    report = folder / "report.txt"
    report.write_text("\n".join(str(row) for row in rows), encoding="utf-8")
    return report.stat().st_size


# `parent` is only here so the demo can look at what is left behind


def naive_report(parent, rows):
    folder = Path(tempfile.mkdtemp(dir=parent))
    if not rows:
        return 0  # early return: the cleanup below is skipped
    size = write_report(folder, rows)  # may raise: the cleanup below is skipped
    shutil.rmtree(folder)
    return size


def managed_report(parent, rows):
    with tempfile.TemporaryDirectory(dir=parent) as folder:
        if not rows:
            return 0
        return write_report(Path(folder), rows)


def folders_left_behind(report, rows):
    with tempfile.TemporaryDirectory() as parent:
        with suppress(ValueError):
            report(Path(parent), rows)
        return len(list(Path(parent).iterdir()))


def main():
    print("Scratch folders left behind")
    print(f"  {'how it ended':<14}{'naive':>7}{'context manager':>18}")
    for how, rows in [("normal exit", [1, 2, 3]), ("exception", [1, -2]), ("early return", [])]:
        naive = folders_left_behind(naive_report, rows)
        managed = folders_left_behind(managed_report, rows)
        print(f"  {how:<14}{naive:>7}{managed:>18}")


if __name__ == "__main__":
    main()
