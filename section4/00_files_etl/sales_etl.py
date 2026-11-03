import csv
from typing import TextIO


def total_by_region(stream: TextIO) -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in csv.DictReader(stream):
        region = row["region"]
        totals[region] = totals.get(region, 0.0) + float(row["amount"])
    return totals
