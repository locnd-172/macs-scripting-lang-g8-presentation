from pathlib import Path

from sales_etl import total_by_region

BAD_CSV = Path(__file__).parent / "fixtures" / "sales_bad.csv"


def naive():
    file = open(BAD_CSV, newline="", encoding="utf-8")
    total_by_region(file)
    file.close()  # skipped if processing raises


def managed():
    with open(BAD_CSV, newline="", encoding="utf-8") as file:
        total_by_region(file)
