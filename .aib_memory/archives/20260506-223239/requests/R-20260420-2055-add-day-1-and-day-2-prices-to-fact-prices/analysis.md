# Analysis: R-20260420-2055 — Add day-1 and day-2 prices to fact_prices

## Executive Summary

- **Request ID:** R-20260420-2055

- **Request title:** Add day-1 and day-2 prices to fact_prices

- **High-level purpose (amended):** Create a new derived fact table `data/schema/fact_prices_lookback.csv` computed from the 3 most recent daily fact CSVs, presenting one row per product-store-category triplet from the latest date D enriched with D-1 and D-2 lookback prices. The original approach of extending each of the 63 existing fact CSVs in-place was superseded by inline amendments in `request.md` — the historical fact partitions remain immutable.

- **Impacted scripts:** `src/transform.py` (new `LOOKBACK_HEADER` constant, `load_fact_dict` helper, `build_lookback_table` function) and `src/load_supabase.py` (new DDL for `fact_prices_lookback` Supabase table, new `insert_lookback` function).

- **Existing 63 fact CSVs are NOT modified.** The amended approach separates the derived lookback artifact from the immutable historical partition store, eliminating the need for force-reprocessing historical data and reducing operational risk.

- **Prior-day lookup key:** `(store_key, category_key, product_key)` — uniquely identifies a price record across days given that `store_key` already encodes `(store_name, settlement_key, company_key)`.

- **Memory impact is bounded and improved vs the original approach:** Only 2 prior-day fact CSVs (D-1 and D-2) are loaded as dicts once per run — not once per ZIP × 63 iterations. Peak RAM ~400–800 MB for two loaded dicts simultaneously.

- **Two open design questions (Q001, Q002)** are raised for user decision before implementation: output format/location of the new table, and whether Supabase sync is in scope.

- **`request.md` sections updated this run:** `## Goal`, `## Scope`, `## Out of scope`, `## Constraints`, `## Success criteria`, `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs` (sections 10–12 added for first time).

---

## Domain Knowledge Essentials

**Fact table (fact_prices):** Star-schema fact table storing one row per product price observation per day. Grain: one price record per `(date, store, file, category, product)` tuple. Currently 7 columns — unchanged by this request.

**fact_prices_lookback (new):** A new derived fact-like table produced by `transform.py` on every run. Contains one row per product-store-category triplet for the most recent fact date D, enriched with retail and promo prices from D-1 and D-2. It is a convenience derivation, not a source-of-truth partition. Fully replaced on each run.

**retail_price:** The regular (non-promotional) shelf price for a product at a given store on a given day. Already nullable in the source fact (~57 non-parseable rows per ZIP stored as empty string).

**promo_price:** The promotional price for a product at a given store on a given day when a promotion is active. Empty string when no promotion is active (~64.9 % of rows).

**Day-1 / Day-2 (lookback):** For a row in `fact_prices_lookback.csv` dated D, `_day1` columns carry the retail and promo prices for the same product-store-category triplet from D-1's fact partition; `_day2` from D-2's fact partition.

**Lookback column (denormalized lag feature):** A column that carries a value from a prior period, identified by matching the current row's composite business key against prior period fact data. Trades storage overhead for simpler single-file analytical queries.

**Derived / convenience artifact:** A file or table whose content is fully derivable from existing source data at any time. Should not be treated as a source of truth; source partitions take precedence for historical accuracy.

**EKATTE:** Bulgarian administrative code registry; used as the settlement dimension natural key. Not directly relevant to this request.

**UIC (ЕИК):** Bulgarian company identification code; forms the `dim_company` natural key. Not directly relevant to this request.

**Key impacted roles/personas:**
- Data engineers: integrate the new `build_lookback_table` step and optionally update Supabase sync.
- Analysts: benefit from single-file day-over-day price comparisons via the new lookback CSV.

**Business process touched:** ETL transformation pipeline (`src/transform.py`); Supabase cloud sync (`src/load_supabase.py`).

---

## Technical Knowledge & Terms

**`LOOKBACK_HEADER`:** New Python list constant in `src/transform.py` defining the 11-column layout of `fact_prices_lookback.csv`. Separate from and does not alter `FACT_HEADER` (7 columns, used by existing `build_schema`).

**`FACT_HEADER`:** Existing 7-column constant — unchanged by this request: `["date_key", "store_key", "file_key", "category_key", "product_key", "retail_price", "promo_price"]`.

**`build_lookback_table(facts_dir, output_path)`:** New function in `src/transform.py`. Reads the 3 most recent fact CSVs from `facts_dir`, builds lookup dicts for D-1 and D-2, iterates D row-by-row to produce 11-column output rows, and writes atomically to `output_path`.

**`load_fact_dict(fact_path)`:** New helper in `src/transform.py`. Reads a single fact CSV into a dict keyed by `(store_key, category_key, product_key)` → `(retail_price, promo_price)` using `csv.DictReader`. Returns empty dict if file absent.

**`csv.DictReader` header compatibility:** Reading prior-day fact CSVs with `csv.DictReader` gives column-name access (`row['store_key']`, etc.), which is safe regardless of the underlying column count. No format detection logic needed.

**Atomic write pattern (`.partial` → `Path.replace`):** Used for all ETL output files. Must be preserved for `fact_prices_lookback.csv`.

**`_CREATE_DDL` (load_supabase.py):** Multi-statement DDL string; `CREATE TABLE IF NOT EXISTS` only. Will gain a new `fact_prices_lookback` table definition. The existing `fact_prices` table is unchanged.

**`_ENSURE_NULLABLE_DDL` (load_supabase.py):** Existing idempotent migration constant. Will gain four `ALTER TABLE fact_prices_lookback ADD COLUMN IF NOT EXISTS` entries for the four lookback columns.

**`insert_lookback(conn, csv_path)` (load_supabase.py — new):** Truncates `fact_prices_lookback` and inserts all rows from `fact_prices_lookback.csv` using `execute_batch` within a transaction. Effectively a full sync on each run, consistent with the derived/rolling nature of the lookback table.

**Memory profile:** Loading two fact CSVs (~1.3 M rows each) as Python dicts: approximately 200–400 MB per dict. Two dicts simultaneously = ~400–800 MB peak additional RAM. This is a one-time cost per `transform.py` run (not per ZIP), significantly lower operational pressure than the original approach.

**Sorted lexicographic file listing:** `sorted(facts_dir.glob("*.csv"))` on ISO-date-stemmed files produces chronological order. Taking the last 3 elements gives D, D-1, D-2 in reverse chronological order (indices -1, -2, -3).

**Files read (evidence log):**
- `src/transform.py` → confirms `FACT_HEADER`, `build_schema`, sorted ZIP iteration, path constants (`FACTS_DIR`, `SCHEMA_DIR`)
- `src/load_supabase.py` → confirms `_CREATE_DDL`, `_ENSURE_NULLABLE_DDL`, `insert_fact_day` pattern, `execute_batch` usage
- `.aib_memory/context.md` → confirms full architectural picture, column semantics, existing constraints, and memory profile
- `.aib_brain/conventions/analysis-convention.md` → normative structure for this document
- `.aib_brain/conventions/request-convention.md` → normative structure for `request.md`

---

## Research Results

**Pattern scan: existing codebase**

1. **`build_schema` is the structural template for `build_lookback_table`:** The existing `build_schema` function reads sorted CSVs, processes rows, and writes with `.partial` → rename. The new `build_lookback_table` follows the same structural pattern — no new file I/O patterns needed.

2. **Sorted file listing gives reliable chronological order:** The existing pipeline uses `sorted(...)` on ISO-date stems for deterministic chronological processing. Applying the same sort to `data/schema/facts/*.csv` and taking the last 3 entries gives D (latest), D-1, D-2 reliably.

3. **`csv.DictReader` named-column access is format-agnostic:** As verified in the previous analysis run, `csv.DictReader` reads the actual file header; accessing named columns present in any valid fact CSV works correctly. No format detection needed in `load_fact_dict`.

4. **Adding `build_lookback_table` call to `main()` requires minimal changes:** The current `transform.py` main() ends with `save_state()`. The new call simply follows `save_state()`. No refactoring of existing logic required.

5. **`insert_fact_day` pattern is reusable for `insert_lookback`:** `insert_fact_day` uses `csv.DictReader` + `execute_batch` + transaction rollback on error. `insert_lookback` can follow the same pattern with TRUNCATE preceding the insert, since the lookback table is always fully replaced.

6. **No changes to dimension tables, quality reports, or extract.py:** The change is fully contained in `transform.py` (new function), `load_supabase.py` (new DDL + function), and `context.md` (documentation). The 63 existing fact CSVs are read-only inputs to the new derived artifact.

7. **Duplicate key risk in prior-day dicts is unchanged from prior analysis:** Same risk exists — if two rows in a prior-day fact file share the same `(store_key, category_key, product_key)`, the dict retains only the last value. In practice, `store_key` incorporates `company_key`, so distinct companies cannot collide. Within a single company's CSV, the triple should be unique. Risk is low but not provably zero.

---

## External Benchmarking

**Reference 1: Kimball "Periodic Snapshot Fact Table with Convenience Lag Columns" pattern**

- Context: The Kimball data warehousing methodology endorses "pre-aggregated convenience columns" in periodic snapshot facts when downstream tools cannot perform cross-period joins natively. The amended approach — a derived snapshot CSV produced fresh on each ETL run — is a textbook instance of this pattern: the source partitions are immutable; the convenience layer is derivable on demand.
- Takeaway: Separating source-of-truth partitions (the 63 immutable fact CSVs) from the derived convenience layer (`fact_prices_lookback.csv`) is a mature architectural choice. It aligns with the Kimball principle of not polluting historical records with derived data.
- Assessment for this request: Fully applicable and strongly aligned. The amendment improves architectural hygiene over the original scope. Adoption confirmed.
- Caveat: The convenience layer should be documented clearly as derived, and consumers must be directed to source partitions for historical accuracy. This is captured in `context.md` Task 4.

**Reference 2: Analytics engineering lag feature generation (dbt `lag()` window function approach)**

- Context: In modern analytics engineering (dbt, Spark SQL, BigQuery), the canonical approach for getting "yesterday's price" is a `LAG(retail_price, 1) OVER (PARTITION BY store_id, product_id ORDER BY date)` window function applied at query time in a view or materialized table, not baked into any raw file.
- Takeaway: The windowed-SQL approach is preferred in columnar query engines (Snowflake, BigQuery, DuckDB) because it avoids physical duplication of data while still providing lag values on demand. The trade-off is that consumers must have access to the full fact dataset and a query engine that supports window functions.
- Assessment for this request: **Partially applicable — not adopted.** The amended approach (a derived flat file) serves the stated consumer base (spreadsheet users, single-file pandas use cases) without requiring DuckDB. The dbt approach would be the preferred long-term architecture if the project migrates to a SQL-first analytical layer over DuckDB.

**Reference 3: Apache Spark partition-local broadcast join for lag population**

- Context: In large-scale Spark ETL, lagged values are populated at write time by broadcasting the prior partition (prior date) as a join, then left-joining the current day's rows. The Python dict lookup in `load_fact_dict` is the single-node equivalent of this distributed broadcast join.
- Takeaway: The dict-based broadcast join is well-understood, correct in semantics, and widely used for batch ETL lag feature population at local scale. The key operational risks (memory pressure and key deduplication) are the same as documented in the Spark literature.
- Assessment for this request: Fully applicable. The amended approach (loading only 2 prior-day dicts once per run rather than once per ZIP × 63 iterations) is even more memory-efficient than the original scope. Adoption confirmed.

---

## Minimal Spikes and Experiments

**Spike 1: Python stdlib date arithmetic across month boundaries**

- Hypothesis: `date.fromisoformat('2026-02-28') - timedelta(days=1)` correctly yields `2026-02-27`; `date.fromisoformat('2026-03-01') - timedelta(days=1)` yields `2026-02-28`.
- Approach: Logical verification using Python `datetime.date` semantics.
- Outcome: Confirmed. Python `timedelta(days=1)` subtraction correctly crosses month, year, and leap-year boundaries.
- Conclusion: Date arithmetic is safe and correct for prior-day filename computation. (Note: the amended approach uses sorted file listing rather than date arithmetic to find the 3 most recent files — no date math required in `build_lookback_table`.)

**Spike 2: DictReader column-name access on existing 7-column fact files**

- Hypothesis: Using `csv.DictReader` to read a 7-column fact file and accessing `store_key`, `category_key`, `product_key`, `retail_price`, `promo_price` by name works correctly.
- Approach: Logical verification against Python `csv.DictReader` specification.
- Outcome: Confirmed. `csv.DictReader` reads the actual file header; named-column access is correct for any valid fact CSV.
- Conclusion: `load_fact_dict` does not need format detection logic. It simply reads by column name from the existing 7-column files.

**Spike 3: Memory overhead estimation for two prior-day lookback dicts (revised for amended scope)**

- Hypothesis: Loading two fact CSVs (~1.3 M rows each) into Python dicts with tuple keys and string value pairs stays within manageable RAM.
- Approach: Estimation using known row counts and Python object overhead (~650 bytes per entry worst case; lower with CPython string/int interning). At 1.3 M rows per dict: ~845 MB worst case; ~200–400 MB realistic.
- Outcome: Two dicts = 400–800 MB peak. Importantly, under the amended approach, both dicts are loaded **once per entire run** (not once per ZIP), so peak RAM occurs for a brief window only. This is substantially better than the original approach's per-ZIP overhead.
- Conclusion: Memory overhead is acceptable. Releasing dicts after writing `fact_prices_lookback.csv` (before `save_state()` returns) returns the ~400–800 MB to the OS.

**Spike 4: PostgreSQL `ADD COLUMN IF NOT EXISTS` availability on Supabase**

- Hypothesis: Supabase's hosted PostgreSQL supports `ALTER TABLE … ADD COLUMN IF NOT EXISTS …` (available from PostgreSQL 9.6+).
- Approach: Cross-reference with PostgreSQL 15.x feature set confirmed in `context.md`.
- Outcome: Confirmed. Supabase runs PostgreSQL 15.x. `ADD COLUMN IF NOT EXISTS` is fully supported.
- Conclusion: The four `ALTER TABLE fact_prices_lookback ADD COLUMN IF NOT EXISTS … NUMERIC(12,4)` statements are safe to add to `_ENSURE_NULLABLE_DDL`.

**Spike 5: Sorted glob on ISO-date-stemmed CSVs reliably yields chronological order**

- Hypothesis: `sorted(Path("data/schema/facts").glob("*.csv"))` returns files in date-ascending order because ISO date strings (`YYYY-MM-DD`) sort lexicographically the same as chronologically.
- Approach: Logical verification — YYYY-MM-DD string comparison is equivalent to chronological comparison for valid ISO 8601 dates within the same century.
- Outcome: Confirmed. No special date parsing needed; `.stem` comparison for files named `YYYY-MM-DD.csv` is deterministic and correct.
- Conclusion: `sorted(facts_dir.glob("*.csv"))[-3:]` reliably returns the 3 most recent fact dates (D-2, D-1, D) in ascending order.

---

## AI Copilot Suggestions

**Observation 1 — The amended architecture is strictly better than the original for historical data integrity**
The original scope required force-regenerating 63 immutable historical fact CSV files — a destructive, time-consuming, and failure-prone operation that permanently changes data that consumers may have cached or exported. The amendment eliminates this entirely. The new derived artifact can always be regenerated from source without touching the historical record.
- Suggestion: In the `context.md` update (Task 4), explicitly mark `fact_prices_lookback.csv` as "derived — do not treat as source of truth" to prevent future operators from assuming it is the canonical price history.

**Observation 2 — The flat-file option (Q001, Option A) has a hidden limitation for historical lookback**
If `fact_prices_lookback.csv` only reflects the single latest date D, analysts who want to compare prices for D-7 vs D-8 cannot use this file — they must still perform cross-file joins on the raw fact partitions. The file answers only "what were prices yesterday and the day before, relative to the most recent date?"
- Suggestion: Clearly document this limitation in `context.md`. Consider whether date-partitioned lookback files (Q001, Option B) are needed for the target analyst use cases. If analysts primarily want "latest price trend," Option A is sufficient; if they need historical lookback comparisons, Option B is required.

**Observation 3 — TRUNCATE strategy for Supabase `fact_prices_lookback` creates a data gap window**
The proposed `insert_lookback` strategy (TRUNCATE + reinsert) leaves the remote `fact_prices_lookback` table empty between the TRUNCATE and the completion of the batch insert. For a derived snapshot table with ~1.3 M rows, this gap is seconds to minutes depending on network latency to Supabase.
- Suggestion: Wrap TRUNCATE and INSERT in a single database transaction. If Supabase's connection pool or row-level locking rules make this impractical, document the brief gap as an accepted operational characteristic in `context.md`.

**Observation 4 — No edge-case test for `build_lookback_table` on first-ever ETL run**
If `data/schema/facts/` contains zero fact files (first run before any ZIPs are processed), `build_lookback_table` must handle it gracefully. The success criteria and test suite include a "fewer than 3 files" case (T5), but the zero-file case is not explicitly stated.
- Suggestion: Test T5 should explicitly include the zero-file sub-case. The implementation should guard with an early return and a `logging.WARNING` when no fact files exist.

**Scope size assessment:** Smaller than the original scope. The amendment removes the most operationally risky part (force-reprocessing 63 ZIPs) and replaces it with a targeted new-function addition to `transform.py`. The Supabase change is now a new dedicated table (lower risk than altering an existing high-volume table). This is a well-scoped, low-risk change.

---

## Testing

- T0 — Existing fact CSVs unchanged: Check any 3 existing fact CSVs (e.g., `data/schema/facts/2026-04-16.csv`, `2026-04-17.csv`, `2026-04-18.csv`) after running the updated transform. Expected outcome: each file has exactly 7 columns with the header `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price`.

- T1 — Lookback table header validation: Read the header row of `data/schema/fact_prices_lookback.csv`. Expected outcome: header is exactly `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2`.

- T2 — Row count matches latest fact file: Count rows in `data/schema/fact_prices_lookback.csv` (excluding header) and compare to row count in the latest fact file (e.g., `2026-04-18.csv`). Expected outcome: row counts match.

- T3 — Lookback values correct: Sample 10 rows from `fact_prices_lookback.csv` and cross-check `retail_price_day1` values against the D-1 fact file for the same `(store_key, category_key, product_key)`. Expected outcome: values match (or empty string where key is absent from D-1).

- T4 — No-match row has empty lookback: Identify a row in `fact_prices_lookback.csv` whose `(store_key, category_key, product_key)` is absent from the D-1 or D-2 fact file. Expected outcome: the affected `_day1` or `_day2` columns are empty string; no error raised.

- T5 — Fewer-than-3-files edge case: In a test scenario where fewer than 3 fact files exist in `data/schema/facts/`, verify `build_lookback_table` completes without error. Expected outcome: lookback table created with partial lookback; D-2 columns all empty when only D and D-1 exist; all lookback columns empty when only D exists; zero-file case returns early with a WARNING log and no output file written.

- T6 — Column count quick check: `python -c "import csv; r=csv.reader(open('data/schema/fact_prices_lookback.csv')); print(len(next(r)))"`. Expected outcome: `11`.

- T7 — Supabase DDL idempotency: Run `python src/load_supabase.py` twice against a Supabase DB that already has `fact_prices_lookback`. Expected outcome: both runs complete with exit code 0; no errors.

- T8 — Existing unit tests pass: Run `python -m pytest tests/`. Expected outcome: all tests pass.

- T9 — Supabase lookback insert: After running `python src/load_supabase.py`, query the remote `fact_prices_lookback` table. Expected outcome: rows present for the latest fact date; `retail_price_day1` is non-NULL for rows where D-1 fact data exists for the same composite key.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The amended scope is architecturally cleaner than the original. Keeping the 63 historical fact partitions immutable is a sound decision — it avoids re-processing 63 gigabytes of historical data, eliminates the risk of corrupting the historical record during a forced pipeline run, and decouples the derived lookback layer from the source ETL. The `build_lookback_table` function follows the established structural template of `build_schema`, with identical I/O patterns (sorted list, DictReader, atomic write), making it low-risk to implement and maintain.

- The implicit "broadcast join" (Python dict lookup) is the correct single-node equivalent of the distributed pattern; no architectural concern here.
- Risk: If the latest fact partition (D) is missing due to a failed ETL run, `build_lookback_table` will populate the lookback table from an older date without warning. A guard comparing D's date to today's expected date would improve observability.
- Risk: The flat-file option (Q001, Option A) produces a single non-versioned derived file. If a consumer reads the file mid-overwrite (before the atomic rename completes), they see a stale version — this is safe given the `.partial` rename pattern.
- Risk: The Supabase TRUNCATE gap (Observation 3 in AI Copilot Suggestions) is a minor concern for a derived table; acceptable given the low query frequency of this table.
- The design question (Q001) about flat-file vs date-partitioned is a real architectural fork that should be resolved explicitly before implementation.

### Product Owner

The amendment delivers the same analytical value — single-file day-over-day price comparisons — without the significant operational overhead of force-reprocessing 63 historical fact files. This is a better trade-off: analysts get the convenience lookback immediately after the next ETL run; engineers avoid a CPU/IO-intensive one-time backfill operation.

- High business value relative to implementation cost (~80–100 new lines of Python, no data migration).
- The flat-file option (Q001, Option A) directly addresses the stated analyst need: "compare today's price to yesterday's and the day before." No historical multi-day trend analysis is implied by the request.
- Success criteria are concrete and testable. All key analyst concerns (lookback correctness, empty-string semantics, no disruption to existing fact files) are covered.
- The promo_price_day1/day2 empty-string ambiguity (A5) is a minor consumer documentation issue; it should be noted in `context.md`.
- Q002 (Supabase scope) is the only outstanding product decision; the implementation plan is ready for Option A or Option B.

### User (Data Analyst / Data Engineer)

For the data analyst, `fact_prices_lookback.csv` provides exactly what was requested: a single flat file with current prices and the two prior-day prices, usable in any tool (DuckDB, pandas, spreadsheet) without cross-file joins. The 7-column existing fact files are unchanged, so any existing workflows built on them are completely unaffected.

- The new file adds zero friction to existing analyst workflows — it is an additive artifact.
- Empty string in day1/day2 promo columns may be misinterpreted by spreadsheet tools as text; analysts should be advised to treat empty as NULL/missing.
- The file always reflects the latest ETL run date. If the latest ETL ran 3 days ago, the lookback file shows D = that older date, not today. Analysts should check the `date_key` column before drawing conclusions.
- For the data engineer, no manual force-reprocess step is required — the new function runs automatically on each `python src/transform.py` invocation.

### Security Officer

No new attack surface is introduced. This change is entirely internal to the local ETL pipeline and the existing Supabase DDL path. The four new lookback columns carry the same publicly available government retail price data as the existing fact columns. All existing security controls apply unchanged.

- No new external data sources, HTTP calls, or network paths added.
- No new environment variables or secrets required.
- `CREATE TABLE IF NOT EXISTS fact_prices_lookback` is a strictly additive, non-destructive DDL operation; it does not alter existing `fact_prices` data.
- No PII or regulated data is introduced.
- The TRUNCATE + INSERT in `insert_lookback` operates within a database transaction; rollback on error is consistent with the existing `insert_fact_day` pattern.

### Data Governance Officer

The amended architecture significantly improves data governance by preserving immutable source partitions. The 63 historical fact CSVs remain unchanged, making the lineage from raw ZIP → fact partition a clean, point-in-time, non-destructive chain. The new `fact_prices_lookback.csv` is a clearly derived artifact with documented lineage.

- Derived column lineage for `_day1` and `_day2` must be added to the Data Lineage Summary in `context.md` (Task 4): `fact_prices_lookback.csv ← facts/D.csv + facts/D-1.csv + facts/D-2.csv`.
- The semantic ambiguity for empty `promo_price_day1/day2` (A5) is a lineage documentation gap; must be noted in `context.md`.
- Since `fact_prices_lookback.csv` is fully replaced on each run, there is no accumulation of stale data in the local file. However, if an operator corrects a historical fact partition (e.g., replaces `2026-04-17.csv`), the lookback file is automatically refreshed on the next ETL run — no manual intervention needed. This is a governance improvement over the original approach.
- The Supabase `fact_prices_lookback` table (if Q002 → Option A) is a truncate-and-replace derived table; the governance classification is "derived operational snapshot" — it does not represent the authoritative historical record.

