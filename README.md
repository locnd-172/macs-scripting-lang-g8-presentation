# Python Context Managers: demos

---

## 1. Files & ETL

The caller owns the file. The transform only reads from a stream.

```
 caller                                transform
 with open(...) as f ───── f ────────► total_by_region(f)      never opens or closes
        │
        └─ block ends (success or error) ─► file closed
```

```python
# naive: close() is skipped when the processing raises
f = open(BAD_CSV, newline="", encoding="utf-8")
total_by_region(f)
f.close()

# with: closed on every path
with open(BAD_CSV, newline="", encoding="utf-8") as f:
    total_by_region(f)
```

```
Naive: open, process, close
  good file: {'west': 165.5, 'east': 281.0, 'north': 10.0}
  bad file : could not convert string to float: 'n/a'
  file closed? False
With a context manager
  good file: {'west': 165.5, 'east': 281.0, 'north': 10.0}
  bad file : could not convert string to float: 'n/a'
  file closed? True
  in memory: {'west': 3.75}
```

Code: [files_etl.py](section4/01_files_etl/files_etl.py), [sales_etl.py](section4/01_files_etl/sales_etl.py)

---

## 2. Database transactions, v2

One tool, `atomic()`: a transaction scope that nests.

| `atomic()` is entered... | It does |
|---|---|
| with no transaction open | `BEGIN IMMEDIATE` ... `COMMIT`, or `ROLLBACK` on an error |
| inside an open transaction | `SAVEPOINT` ... `RELEASE`, or `ROLLBACK TO` on an error |

### Flow: `checkout()` = reserve stock + record order + award points

```
 NAIVE: every function has its own `with conn:`

 checkout()
   ├─ reserve_stock()   UPDATE stock ──► COMMIT   saved for good
   ├─ record_order()    unknown customer ✘        only this step rolls back
   └─ award_points()    never runs
                                      result: stock reduced, no order  ► partly saved


 ATOMIC: one transaction, the inner calls become savepoints

 checkout()             BEGIN IMMEDIATE
   ├─ reserve_stock()   SAVEPOINT sp1 ── UPDATE ── RELEASE sp1
   ├─ record_order()    SAVEPOINT sp2 ── unknown customer ✘ ── ROLLBACK TO sp2
   │                    the error keeps going up
   └─ checkout()        ROLLBACK
                                      result: nothing changed  ► nothing saved
```

### Flow: a fresh database for every test

```
 test starts          BEGIN
   test body          checkout() ─► atomic() sees an open transaction ─► SAVEPOINT / RELEASE
                      (nothing is committed)
 test ends            ROLLBACK ─► database is back to the seed data

 With plain `with conn:` in the code under test, checkout() would COMMIT.
 The final ROLLBACK then has nothing left to undo, and the next test sees stale data.
```

### Code

```python
# shop_naive.py
def checkout(conn, customer, sku, quantity):
    with conn:  # looks like one transaction, but every call below has already committed
        reserve_stock(conn, sku, quantity)
        record_order(conn, customer, sku, quantity)
        award_points(conn, customer, quantity * 10)

# shop_atomic.py: the same code with atomic()
def checkout(conn, customer, sku, quantity):
    with atomic(conn):  # one transaction: the calls below become savepoints inside it
        reserve_stock(conn, sku, quantity)
        record_order(conn, customer, sku, quantity)
        award_points(conn, customer, quantity * 10)
```

```python
# atomic.py (abridged)
@contextmanager
def atomic(conn):
    if conn.in_transaction:                       # nested: use a savepoint
        name = f"sp{next(savepoint_numbers)}"
        conn.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            conn.execute(f"ROLLBACK TO {name}")
            conn.execute(f"RELEASE {name}")
            raise
        conn.execute(f"RELEASE {name}")
    else:                                         # outermost: a real transaction
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
```

```python
# shop_tests.py: the test fixture is a small context manager too
@contextmanager
def rolled_back(conn):
    conn.execute("BEGIN")
    try:
        yield
    finally:
        conn.rollback()
```

### Output

```
Act 1 - checkout() = reserve_stock() + record_order() + award_points()
  alice (a regular customer) buys 1 KB-1
    naive   : stock=9 orders=1 points=10  ok
    atomic(): stock=9 orders=1 points=10  ok
  carol (not a customer) buys 1 KB-1
    naive   : stock=9 orders=0 points=0  failed, PARTLY SAVED
    atomic(): stock=10 orders=0 points=0  failed, nothing saved
  bob (has no loyalty account) buys 1 KB-1
    naive   : stock=9 orders=1 points=0  failed, PARTLY SAVED
    atomic(): stock=10 orders=0 points=0  failed, nothing saved

Act 2 - a fresh database for every test (one database per test file)
  naive
    PASS test_checkout_reserves_stock
    FAIL test_each_test_starts_from_the_seed_data: stock is 9, expected 10
  atomic()
    PASS test_checkout_reserves_stock
    PASS test_each_test_starts_from_the_seed_data
```

Limits: rollback isolation needs one connection, and in-process state is not undone.

Code: [db_transactions_v2.py](section4/02_db_transactions/db_transactions_v2.py), [atomic.py](section4/02_db_transactions/atomic.py), [shop_naive.py](section4/02_db_transactions/shop_naive.py), [shop_atomic.py](section4/02_db_transactions/shop_atomic.py), [shop_tests.py](section4/02_db_transactions/shop_tests.py)

---

## 3. Temporary resources, v2

A video analytics job. The video and audio are large and must be gone however the job ends.
The tools work on paths, so the scratch space is a folder. All tools are fake.

### Flow

```
 NAIVE: mkdtemp() ... rmtree()

 mkdtemp() ─► download ─► extract audio ─► transcribe ─► analyze (LLM) ─► save ─► rmtree()
                 ✘             ✘               ✘               ✘            ✘
                 └─────────────┴───────────────┴───────────────┴────────────┘
              any error, or an early return: rmtree() is skipped, the folder stays on disk


 WITH A CONTEXT MANAGER: the folder only lives around the steps that need files

 with TemporaryDirectory() as folder:
 ┌───────────────────────────────────────────┐
 │ download ─► extract audio ─► transcribe   │──► transcript ─► analyze (LLM) ─► save
 └───────────────────────────────────────────┘
   exit: the folder is deleted, whether the block succeeded, raised or returned early
```

### Code

```python
# pipeline_naive.py
folder = Path(tempfile.mkdtemp(prefix="transcribe-", dir=work_root))
video = download_video(post_id, folder)
audio = extract_audio(video)
if audio is None:
    return "skipped, no audio track"  # the cleanup at the bottom never runs
transcript = transcribe(audio)
save_insights(post_id, analyze(post_id, transcript))
shutil.rmtree(folder)  # only reached if every step above worked
```

```python
# pipeline_managed.py
def get_transcript(post_id, work_root):
    """The video and audio only exist inside this block."""
    with tempfile.TemporaryDirectory(prefix="transcribe-", dir=work_root) as folder:
        video = download_video(post_id, Path(folder))
        audio = extract_audio(video)
        if audio is None:
            return None
        return transcribe(audio)

def process_post(post_id, work_root):
    transcript = get_transcript(post_id, work_root)
    if transcript is None:
        return "skipped, no audio track"
    # the video and audio are already gone, so the slow LLM call does not hold them
    save_insights(post_id, analyze(post_id, transcript))
    return "analyzed"
```

### Output

```
Lifecycle of one run
  inside the block: ok.mp4 (1024 KiB), ok.wav (256 KiB)
  after the block : folder exists? False

Left behind after each kind of run (folders / size)
                          naive               context manager
  success                 0 / 0 KiB           0 / 0 KiB
  download fails          1 / 256 KiB         0 / 0 KiB
  audio extraction fails  1 / 1024 KiB        0 / 0 KiB
  no audio track          1 / 1024 KiB        0 / 0 KiB
  transcription fails     1 / 1280 KiB        0 / 0 KiB
  LLM call fails          1 / 1280 KiB        0 / 0 KiB
  database save fails     1 / 1280 KiB        0 / 0 KiB
```

Limit: a context manager does not cover a hard kill, so a real service also sweeps stale
`transcribe-*` folders at startup.

Code: [temp_resources_v2.py](section4/04_temp_resources/temp_resources_v2.py), [pipeline_naive.py](section4/04_temp_resources/pipeline_naive.py), [pipeline_managed.py](section4/04_temp_resources/pipeline_managed.py), [media_tools.py](section4/04_temp_resources/media_tools.py), [insights.py](section4/04_temp_resources/insights.py)
