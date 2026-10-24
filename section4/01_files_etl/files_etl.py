"""Application 1 - Files & ETL.

What happens to a file when processing goes wrong, and why the transform
receives a stream instead of opening the file itself.
"""

import io
from pathlib import Path

from sales_etl import total_by_region

FIXTURES = Path(__file__).parent / "fixtures"
GOOD_CSV = FIXTURES / "sales.csv"
BAD_CSV = FIXTURES / "sales_bad.csv"  # one amount is "n/a"


def naive():
    print("Naive: open, process, close")
    f = open(GOOD_CSV, newline="", encoding="utf-8")
    print("  good file:", total_by_region(f))
    f.close()

    f = open(BAD_CSV, newline="", encoding="utf-8")
    try:
        total_by_region(f)
        f.close()  # never reached when the processing fails
    except ValueError as error:
        print("  bad file :", error)
    print("  file closed?", f.closed)
    f.close()  # tidy up after the demo


def with_context_manager():
    print("With a context manager")
    with open(GOOD_CSV, newline="", encoding="utf-8") as f:
        print("  good file:", total_by_region(f))

    try:
        with open(BAD_CSV, newline="", encoding="utf-8") as f:
            total_by_region(f)
    except ValueError as error:
        print("  bad file :", error)
    print("  file closed?", f.closed)

    # The transform only needs a stream, so it works without any file
    text = "region,product,amount\nwest,widget,1.50\nwest,gadget,2.25\n"
    print("  in memory:", total_by_region(io.StringIO(text)))


def main():
    naive()
    with_context_manager()


if __name__ == "__main__":
    main()
