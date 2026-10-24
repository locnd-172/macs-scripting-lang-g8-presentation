"""The transform used by applications 1 and 6 (each folder keeps its own copy).

It knows how to read sales rows but not where they come from: there is no open() and
no close() in this module. Whoever supplies the stream also owns its lifecycle.
"""

import csv
from typing import TextIO


def total_by_region(stream: TextIO) -> dict[str, float]:
    """Sum the `amount` column per `region`."""
    totals: dict[str, float] = {}
    for row in csv.DictReader(stream):
        region = row["region"]
        totals[region] = totals.get(region, 0.0) + float(row["amount"])
    return totals
