# Python context manager examples

## Files and ETL

`section4/00_files_etl/main.py` compares manual file cleanup with `with open(...)`.

## Database transactions

`section4/01_db_transactions/main.py` compares a checkout that can partly commit with one
wrapped in a transaction context manager.

## Temporary resources

Run `python3 section4/02_temp_resources/main.py` to compare manual temporary-folder cleanup with
`TemporaryDirectory` in a video analytics job. The demo covers a successful run and an early
return when a video has no audio. It leaves inspectable output under
`section4/02_temp_resources/demo_output/`.
