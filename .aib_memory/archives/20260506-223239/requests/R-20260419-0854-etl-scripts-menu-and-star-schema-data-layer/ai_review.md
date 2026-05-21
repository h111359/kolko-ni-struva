# AI Review — R-20260419-0854: ETL Scripts, Menu, and Star-Schema Data Layer

> **Generated:** 2026-04-20
> **Methodology:** Three independent review passes with distinct personas and analytical depth.

---

## Pass 1 — Data & ETL Analyst Review

**Persona:** Senior Data/ETL Analyst — focuses on data modelling correctness, ETL processing logic, practical usability for analysts, and operational fitness.

### Pros

1. **Sound dimensional modelling approach.** The star-schema design (5 dim tables + partitioned facts) is textbook Kimball. Surrogate keys, natural key enrichment, and facts-driven dimension building are all correct patterns for a dataset of this nature.

2. **Date-partitioned fact files are the right call.** At ~82M rows / ~4 GB total, a single flat CSV would be unusable. The `facts/YYYY-MM-DD.csv` partitioning (~55-78 MB each) hits a sweet spot: individually openable, DuckDB/pandas-queryable, and incrementally processable.

3. **No-rejection policy is pragmatically correct.** For a government-mandated data source with no SLA on data quality, retaining all rows (with NULL prices and `(unknown:X)` dimension entries) avoids silent data loss. Analysts can filter downstream rather than lose data at ingestion.

4. **Atomic writes throughout.** The `.partial` → rename pattern for ZIPs, fact CSVs, dimension CSVs, and config state is consistently applied. This prevents corruption on crash — a real risk for multi-hour transforms of 82M rows.

5. **Idempotency is well-designed.** Skip-existing-facts + stable surrogate key preservation on re-run means the pipeline can be safely re-executed without producing duplicates or reordering keys.

6. **Delimiter auto-detection handles a real data quality issue.** The 3-4 companies using semicolons instead of commas are a confirmed, documented anomaly. The fallback detection strategy is practical and tested.

7. **Config-driven force re-run.** The `last_downloaded_date` / `last_processed_date` override mechanism is elegant — edit a date, re-run, done. No CLI flags, no separate tooling.

8. **Stdlib-only transformation.** No pandas/numpy dependency keeps the install simple and avoids compilation requirements. For a streaming CSV-to-CSV pipeline, stdlib `csv`/`zipfile`/`json` are sufficient.

9. **Comprehensive test plan.** 19 test cases (T1-T19) covering path resolution, idempotency, delimiter handling, force re-run, atomic writes, and data quality validation. Thorough for a project of this scale.

10. **Excellent data profiling.** The `data-profile.md` document reflects genuine exploratory analysis — row counts, price distributions, EKATTE coverage gaps, delimiter anomalies — all verified against actual data.

### Cons

1. **`store_name` denormalization in the fact table.** Store name is a raw string in facts (~82M repeated strings), not a dimension. This inflates fact file sizes significantly. If 5,000 unique stores exist, a `dim_store` with surrogate keys would reduce fact CSV sizes by ~15-25%.

2. **`dim_product` keyed on `(product_code, product_name)` is fragile.** If a retailer fixes a typo in a product name (e.g., "Млeко" → "Мляко"), it creates a new product key. Over time, `dim_product` will balloon with near-duplicate entries from minor name variations. No deduplication or fuzzy-matching strategy is proposed.

3. **No data validation layer.** The no-rejection policy is fine, but there's zero validation reporting. How many NULL prices per date? How many unknown settlements? Analysts need a data quality summary — even a simple `data/schema/quality_report.csv` — to trust the output.

4. **Memory pressure during transformation.** "One date's fact rows at a time (~1.3M rows, ~100 MB peak)" is optimistic. With Python dict overhead per row (8 dict fields × 1.3M rows), actual peak memory is likely 500 MB–1 GB. No memory profiling has been done.

5. **No checksum verification for downloaded ZIPs.** A partially downloaded or corrupted ZIP will be silently accepted and processed. The transform will likely crash on a bad ZIP, but the corrupt file remains in `data/raw/` and blocks future re-processing (skip-existing logic).

6. **Surrogate keys are sequentially assigned but not persisted atomically with facts.** If the transform crashes mid-run (after processing some ZIPs but before writing dimension CSVs), the next run reloads stale dimension CSVs and may reassign surrogate keys differently for codes seen only in the failed batch. This breaks referential integrity with already-written fact files.

7. **No logging to file.** Console-only logging for a multi-hour 82M-row transform is impractical. If the terminal closes or the user scrolls past the output, diagnostic information is lost.

8. **`config.ini` combines settings and state.** While documented as a trade-off, this is a genuine operational hazard. An accidental edit to `[state]` keys can trigger unwanted re-processing of the entire dataset — a multi-hour operation.

9. **No progress indication for transform.** Processing 63 ZIPs × ~1.3M rows each takes significant time. No progress bar, no ETA, no "processing ZIP 14/63" message is documented.

10. **`fact_key` as a surrogate in the fact table is wasteful.** Each fact row already has a natural composite key: `(date_key, company_key, store_name, product_key)`. A sequential `fact_key` adds ~8 bytes per row × 82M rows = ~656 MB of wasted space across all fact files. Fact surrogates are an anti-pattern in pure analytical workloads.

### Logical Misconceptions

1. **"Dimension from facts guarantees 100% FK coverage"** — This is true by construction but masks a deeper problem: it makes dimension tables unstable. Each new ZIP can add new dim entries, changing row counts and potentially confusing analysts who expect stable reference tables. A hybrid approach (pre-load known codes from nomenclature + upsert unknowns from facts) would be more robust.

2. **"YYYY-MM-DD lexicographic comparison is correct for ISO dates"** — While technically correct, the force re-run logic uses `>=` comparison against `last_processed_date`. If the user sets `last_processed_date = 2026-04-17` intending to re-process only that date, both `2026-04-17` and `2026-04-18` are re-processed. The semantics are "from this date onward," but the UX may surprise users expecting single-date re-processing.

3. **"`dim_product` will have tens of thousands of rows"** — With 83,404 unique product codes in a *single* ZIP, and retailer-local codes that can collide across companies, `dim_product` across 63 ZIPs could easily reach 200K-500K rows. The "tens of thousands" estimate is an undercount that may affect performance assumptions.

4. **"No automated retention policy" is treated as acceptable.** With 63 ZIPs at ~70 MB each (raw) plus 63 fact CSVs at ~65 MB each, the pipeline already uses ~8.7 GB. After a year (365 dates), this grows to ~50 GB. The lack of any retention discussion is a planning gap, not just an out-of-scope deferral.

5. **"`subprocess` list form = no shell injection"** — This is correct but incomplete. The real risk in `menu.py` isn't injection but **process lifecycle management**. If the user hits Ctrl+C during a subprocess call, does the child process also terminate? `subprocess.run` with `check=True` raises `CalledProcessError` but the child might orphan.

### Improvement Ideas

1. **Add `dim_store` dimension.** Extract `(store_name, settlement_key, company_key)` into a dimension table. This normalizes the fact table and enables store-level analysis.

2. **Add a quality report output.** After each transform run, write `data/schema/quality_report.csv` with per-date counts: total rows, NULL prices, unknown settlements, unknown categories, delimiter anomalies.

3. **Add per-ZIP progress logging.** `INFO: Processing ZIP 14/63 (2026-03-02) — 1,119,243 rows` would transform a black-box process into an observable one.

4. **Split `config.ini` into `config.ini` (committed) + `state.ini` (git-ignored).** This eliminates the VCS diff noise issue and reduces accidental state corruption risk.

5. **Add ZIP integrity check.** After download, verify the ZIP can be opened (`zipfile.is_zipfile()`). On failure, delete and re-download.

6. **Write a log file.** Add a `FileHandler` to the logging config. Write to `logs/transform_YYYY-MM-DD_HHMMSS.log`.

7. **Consider `fact_key` removal.** If no downstream system requires a single-column fact identifier, drop `fact_key` to save ~656 MB.

### Alternative Options

1. **Parquet instead of CSV for facts.** The "human-readable" constraint rules this out, but a hybrid approach (CSV as primary + Parquet as optional) would give analysts 10-100x query performance. DuckDB can also read CSVs, so this is advisory.

2. **SQLite as the schema layer.** Instead of flat CSV dimensions + partitioned fact CSVs, write everything to a single `data/schema/prices.db` SQLite file. Queryable with DuckDB, Python sqlite3, or any SQL tool. Still human-inspectable. ~2-3 GB total. However, this conflicts with the "human-readable CSV" hard constraint.

3. **Click-based CLI instead of `menu.py`.** A `click`-based CLI (`python cli.py download`, `python cli.py transform`, `python cli.py status`) would be more scriptable than an interactive menu. But this adds a pip dependency and changes the UX model.

4. **Makefile instead of `refresh.sh`/`refresh.bat`.** A `Makefile` with targets (`make download`, `make transform`, `make all`) is more idiomatic for developer workflows and self-documents dependencies. Cross-platform via GNU Make on Windows. But less accessible to non-developer operators.

---

## Pass 2 — Internet-Researched Best Practices Review

**Persona:** Senior Data Engineer with breadth of industry knowledge — validates design decisions against documented best practices, industry standards, and lessons from similar ETL projects.

### Best Practice Alignment Analysis

#### 1. Kimball Dimensional Modelling (The Data Warehouse Toolkit, 3rd Edition)

**Aligned:**
- Star schema with surrogate keys on all dimensions is the canonical Kimball pattern. ✓
- Fact table stores only foreign keys + measures. ✓
- Date dimension with calendar attributes (year, month, day, weekday) follows the Kimball "Calendar Date Dimension" technique exactly. ✓
- Late-arriving dimension pattern (placeholder rows for unknown codes) is explicitly named in the Kimball techniques catalogue. ✓

**Misaligned:**
- **Fact surrogate key (`fact_key`):** Kimball documents fact surrogates as useful *only* for update/delete operations on fact rows (e.g., real-time ETL correction scenarios). For a pure append-only batch ETL with no fact updates, fact surrogates are explicitly called an anti-pattern. The proposal uses `fact_key` with no stated use case for fact-level updates. **Recommendation: remove `fact_key` from fact CSVs.**
- **Missing `dim_store` (degenerate dimension anti-pattern):** `store_name` as a raw string in the 82M-row fact table is what Kimball calls a "centipede fact table" risk — too many descriptive attributes in the fact row. `store_name` should either be promoted to a `dim_store` dimension or explicitly documented as a degenerate dimension (a dimension stored in the fact table with no separate dimension table). The current design doesn't acknowledge either pattern.
- **SCD strategy is undefined.** Company names, product names, and store names can change over time. The proposal uses Type 1 (overwrite) implicitly but doesn't document this choice. Kimball recommends explicitly declaring your SCD type for each dimension attribute. For this dataset (daily government data over months), at minimum `dim_company.company_name` should have a documented SCD policy.

#### 2. dbt Project Structure Best Practices (dbt Labs)

While dbt as a tool is out of scope, dbt's staging-intermediate-marts layering pattern is instructive:
- **Staging layer = source-conformed models.** The proposed `data/raw/*.zip` → extract is this.
- **Intermediate layer = transformation logic.** The proposed `transform.py` conflates intermediate and mart layers — it does extraction from ZIPs, dimension building, and fact assembly in one monolithic script.
- **Marts layer = business-conformed models.** The `data/schema/` output is this.

**Recommendation:** Even without dbt, the transform script should have clear internal separation: (1) CSV parsing/cleaning, (2) dimension upsert, (3) fact assembly. This makes the code testable in isolation and allows future refactoring into separate pipeline stages.

#### 3. ETL Idempotency Best Practices

Industry consensus (Airflow, Prefect, Dagster documentation):
- **Idempotent transforms must produce byte-identical output on re-run.** The proposal claims idempotency but doesn't guarantee byte-identical output — dimension CSVs are rewritten on every run even if unchanged. True idempotency would skip dimension writes if no new codes were observed.
- **Checkpoint-based incremental processing is the standard pattern.** The `last_processed_date` approach is correct, but the comparison logic (`>=`) means the boundary date is always re-processed. Industry standard is `>` (exclusive lower bound) to avoid redundant work on the checkpoint date itself.

#### 4. Data Quality Monitoring (Great Expectations, dbt Tests, Soda)

Modern data pipelines universally include a data quality layer:
- **Row count assertions:** Expected row count per date ± threshold.
- **Null rate monitoring:** Track % NULL prices per date over time.
- **Referential integrity checks:** Every FK in facts references a valid dim key.
- **Freshness checks:** Alert if no new data arrives within expected SLA.

The proposal has **zero** data quality monitoring. This is a significant gap by current industry standards. Even a simple CSV-based quality report would address this.

#### 5. Configuration Management (12-Factor App)

- **The `config.ini` approach is acceptable for local batch tools.** 12-Factor prefers environment variables, but for a non-deployed local script, INI files are more practical.
- **However, mixing settings and state violates separation of concerns.** Industry best practice (documented in Airflow, Luigi, Prefect) is to separate user intent (configuration) from system state (checkpoints). Two files: `config.ini` (VCS-tracked, human-edited) + `state.json` or `state.ini` (git-ignored, machine-written).

#### 6. Error Handling and Observability

- **No structured logging.** Modern pipelines emit structured JSON logs for aggregation/alerting. While overkill for a local script, at minimum a file-based log is expected.
- **No error recovery beyond retries.** If `transform.py` crashes mid-batch (e.g., at ZIP 40/63), there's no mechanism to resume from ZIP 40. The entire batch must re-run. A per-ZIP checkpoint would solve this.
- **No alerting on data anomalies.** A price spike to 10,000 BGN or a sudden 50% drop in row count would go unnoticed.

#### 7. Python ETL Pipeline Patterns

- **Streaming vs. batching:** The design correctly uses streaming (one ZIP at a time) rather than loading all 82M rows into memory. This is the right pattern for stdlib Python.
- **`csv.DictReader` vs. `csv.reader`:** The proposal doesn't specify which. `csv.reader` (positional) is faster and has lower memory overhead; `csv.DictReader` is more readable but creates a dict per row (significant overhead at 1.3M rows/ZIP).
- **Generator patterns:** For 82M rows, Python generators would reduce memory pressure further. The proposal buffers all rows for one date (~1.3M) before writing — acceptable but not optimal.

### Additional Improvement Ideas (Research-Driven)

1. **Add a manifest file.** After each transform run, write `data/schema/manifest.json` containing: run timestamp, row counts per fact file, dimension sizes, processing duration, Python version, and data quality summary. This is the pipeline's "receipt" and enables debugging without re-running.

2. **Implement per-ZIP checkpointing.** Instead of a single `last_processed_date`, write a `data/schema/.processed` marker file after each ZIP completes. On resume, skip ZIPs with existing markers. This prevents multi-hour re-processing after a crash at ZIP 60/63.

3. **Add schema validation for source CSVs.** Before processing each CSV, validate: (a) column count is 7, (b) EKATTE code matches `^\d{4,6}(-\d{2})?$` pattern, (c) price is numeric or empty. Log violations but don't reject rows.

4. **Consider ELT over ETL.** Instead of transforming CSVs into CSVs, load raw CSVs into a DuckDB database and run SQL transformations. DuckDB is already recommended for analysts. This would be 10-50x faster, produce a queryable database, and keep transformations in declarative SQL. However, it adds a pip dependency (`duckdb`).

5. **Add `--dry-run` flag to `transform.py`.** Report what would be processed without writing any files. Useful for validating force-reprocess scope before committing to a multi-hour run.

---

## Pass 3 — Solution Architect & Fullstack Developer Review

**Persona:** Very experienced Solution Architect and Fullstack Developer — examines the proposal for architectural issues, implementation errors, operational hazards, scalability concerns, and missed edge cases.

### Critical Issues

#### Issue 1: Surrogate Key Instability on Crash Recovery

**Severity: HIGH**

The dimension CSVs are written atomically at the **end** of the transform run (after all ZIPs are processed). Fact CSVs are written per-ZIP during processing. If the process crashes at ZIP 40/63:
- Fact CSVs for ZIPs 1-39 already exist on disk with surrogate keys assigned during this run.
- Dimension CSVs were **not** written (they're written at the end).
- On re-run, dimension CSVs are reloaded from their **pre-run state** (stale).
- New codes first seen in ZIPs 1-39 get surrogate keys that may differ from the crashed run's assignments.
- **Result:** Facts 1-39 reference stale surrogate keys; referential integrity is broken.

**Fix:** Write dimension CSVs after EACH ZIP's fact file is written, not just at the end. Or: write dimension updates to a WAL (write-ahead log) that persists assignments incrementally.

#### Issue 2: Race Condition in Config State Updates

**Severity: MEDIUM**

If `extract.py` and `transform.py` run concurrently (e.g., user runs `refresh.sh` in one terminal and `transform.py` in another):
- Both read `config.ini` at startup.
- `extract.py` finishes and writes `last_downloaded_date`.
- `transform.py` finishes and calls `save_state()`, which reads the current config, updates `last_processed_date`, and writes the entire file — **overwriting** the `last_downloaded_date` update from `extract.py`.

**Fix:** `save_state()` should re-read the config immediately before writing, not use the startup-cached config object. Better: use separate state files per script.

#### Issue 3: `tmp.rename(dest_path)` Fails Cross-Filesystem

**Severity: LOW** (unlikely in normal usage)

`download_file()` uses `tmp.rename(dest_path)` which fails if `/tmp` is on a different filesystem than `data/raw/`. The code creates `tmp` as `dest_path.with_suffix(dest_path.suffix + ".partial")` so both are in the same directory — this is actually safe. However, the pattern should use `os.replace()` instead of `Path.rename()` for consistency. `Path.rename()` on Linux is POSIX rename (atomic, same filesystem). `os.replace()` is explicitly documented as cross-platform atomic replacement.

**Correction:** No actual bug here, but `Path.replace()` (used in config_utils) and `Path.rename()` (used in download_file) are inconsistent. Standardize on `Path.replace()` throughout.

#### Issue 4: No Timeout for Transform Processing

**Severity: MEDIUM**

If a ZIP contains malformed data that causes an infinite loop in CSV parsing (e.g., a CSV with no newlines — a single multi-GB line), the transform will hang indefinitely with no timeout or watchdog.

**Fix:** Add a per-ZIP processing timeout. If a single ZIP takes longer than a configurable threshold (e.g., 30 minutes), log an error and skip to the next zip.

#### Issue 5: `menu.py` subprocess.run with check=True Swallows Context

**Severity: LOW**

When `subprocess.run([sys.executable, 'src/extract.py'], check=True)` raises `CalledProcessError`, the error message includes the return code but not the child process's stderr. The operator sees "Command returned non-zero exit status 1" with no actionable information.

**Fix:** Use `subprocess.run(..., check=False)` and manually inspect `returncode`, or capture stderr and include it in the error message.

#### Issue 6: Dimension CSV Encoding Inconsistency

**Severity: LOW**

Source CSVs use `utf-8-sig` (BOM). The proposal reads with `utf-8-sig` but doesn't specify the output encoding for dimension and fact CSVs. If written as `utf-8` (no BOM), downstream tools expecting BOM (e.g., Excel on Windows) will display Cyrillic characters as mojibake. If written as `utf-8-sig`, non-Excel tools may display a spurious `\ufeff`.

**Fix:** Write all output CSVs as `utf-8` (no BOM) and document this in README. BOM in output files is an anti-pattern for data pipeline outputs.

#### Issue 7: Product Name Normalization Gap

**Severity: MEDIUM** (data quality)

`dim_product` is keyed on `(product_code, product_name)`. Bulgarian text has casing, whitespace, and Unicode normalization variations:
- "Мляко краве 3.6% 1л" vs "мляко краве 3.6% 1 л" vs "Мляко Краве 3,6% 1л"
- These are the same product but create different dim entries.

Over 63 ZIPs, this will cause `dim_product` to grow with near-duplicates. Across 365 days, this becomes a significant data quality issue.

**Fix:** Normalize product names before keying: `name.strip().lower()` + collapse whitespace + NFC Unicode normalization. Store the original name as `product_name_raw` and the normalized name as the key component.

#### Issue 8: Missing `.gitignore` Updates

**Severity: LOW**

The proposal creates `config.ini`, `data/schema/`, and potentially log files. None are added to `.gitignore`. The discussion mentions "operators should add `config.ini` to `.gitignore`" but doesn't include it in the implementation plan.

**Fix:** Add to `.gitignore`: `config.ini`, `data/schema/`, `data/raw/`, `*.partial`, `logs/`.

### Architecture Observations

1. **Monolithic transform.py.** A single 500+ line script handling ZIP extraction, CSV parsing, delimiter detection, dimension upsert, fact buffering, and file I/O. This is acceptable for the current scale but becomes unmaintainable at 1000+ lines. Consider splitting into: `src/parser.py` (CSV/ZIP handling), `src/dimensions.py` (dim upsert logic), `src/transform.py` (orchestration).

2. **No dependency injection or configuration object.** Functions like `fetch_page()` use module-level globals (`MAX_RETRIES`, `RETRY_DELAY`). After the `config.ini` migration, these become config-read values passed through call chains. A simple `Config` dataclass would clean up the parameter threading.

3. **Sequential ZIP processing.** Each ZIP is processed sequentially. With `concurrent.futures.ProcessPoolExecutor`, dimension-building could remain sequential while fact CSV writing parallelizes across ZIPs. However, this conflicts with the shared mutable dimension dicts. Not recommended unless dimension building is separated into a first pass.

4. **No versioning of schema outputs.** If the fact CSV format changes (e.g., adding a column), old and new fact files in `data/schema/facts/` become incompatible. A `data/schema/VERSION` file or a version column in fact CSVs would enable migration detection.

### Summary of Findings by Severity

| Severity | Count | Key Issues |
|---|---|---|
| HIGH | 1 | Surrogate key instability on crash |
| MEDIUM | 3 | Config race condition, transform timeout, product name normalization |
| LOW | 4 | rename vs replace, subprocess error context, encoding, .gitignore |

### Overall Assessment

The proposed solution is **well-designed for its stated scope** — a local batch ETL pipeline for a single data engineer. The star schema is correctly modelled, the idempotency design is sound (with the crash recovery caveat), and the operational UX (config-driven force re-run, interactive menu) is thoughtful.

**The three most impactful improvements would be:**
1. Fix the surrogate key crash recovery issue (write dims after each ZIP).
2. Split `config.ini` into `config.ini` + `state.ini`.
3. Add a `dim_store` dimension to normalize the fact table.

The proposal is ready for implementation with these corrections applied.
