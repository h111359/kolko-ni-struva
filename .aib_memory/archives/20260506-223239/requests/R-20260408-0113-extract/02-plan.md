# Plan — Iteration 02

Request: R-20260408-0113 — Extract  
Iteration: 02 (Active)  
Generated: 2026-04-08

---

## Overview

This iteration delivers the **complete, first-time implementation** of all deliverables in request R-20260408-0113. No code exists yet: `src/` is absent, `implementation.md` is empty, and all product-doc stubs retain their seed text. Iteration 01 (Completed 2026-04-08 22:11:26) established the core ETL analysis and rewrote the request; Iteration 02 extends that scope with three new deliverables — a project README.md (item 6), Supabase cloud database setup documentation (item 7), and an incremental daily-sync Supabase migration script (item 8).

Key design decisions from the answered 02-questionnaire.md:  
- Anomaly detection uses a **25 %** threshold applied to three metrics (rows, unique product-code count, unique product-name count) — QID-BF-001-A.  
- Documentation scope is **README.md only** (AIB product-doc stub population excluded) — QID-BF-002-C.  
- Migration script is an **incremental daily sync** (watermark-based) — QID-BF-003-B.  
- Supabase Tier 1 keeps **trade-object granularity for the last 3 days** (`RECENT_DAYS = 3`) — QID-AT-001-B.  
- Bulk loading uses **psycopg2-binary** — QID-AT-002-A.

All nine success criteria (SC1–SC9) are addressed; SC9 is adjusted (3 most-recent days, not 7, in `fact_prices_daily`) per QID-AT-001-B.

---

## Scope of Work

**In Scope**

- `src/pipeline.py` — single integrated entry point: download ZIPs, extract CSVs, populate SCD Type 2 dimensions, write daily fact files, detect anomalies, produce quality reports; backfills all 52 existing ZIPs on first run.
- `data/schema/dim_company.json`, `dim_trade_object.json`, `dim_product.json`, `dim_city.json`, `dim_category.json` — SCD Type 2 JSON dimension files.
- `data/schema/facts/YYYY-MM-DD.json` — one date-partitioned daily fact file per processed ZIP.
- `data/quality/YYYY-MM-DD-report.json` — per-day anomaly reports with per-company status (OK / WARNING / REJECTED).
- UTF-8 BOM handling and double-quoted CSV field normalization for all company CSVs.
- Anomaly detection: 3 metrics, 25 % threshold, 7-day rolling per-company window.
- `README.md` — project root user guide (installation, usage, outputs, quality-report interpretation, brief technical reference); covers both operator and developer audiences.
- `docs/supabase-setup.md` — step-by-step Supabase PostgreSQL setup with full SQL DDL (all 5 dimension tables + 2 fact tables, indexes, FK constraints).
- `src/migrate_supabase.py` — incremental daily sync: Tier 1 = trade-object level last 3 days; Tier 2 = weekly category aggregates for older days; watermark-based; psycopg2-binary.
- `requirements.txt` — add `psycopg2-binary` and `python-dotenv`.
- `.gitignore` — add `.env`, `venv/`, `__pycache__/`, `*.pyc`, `*.partial`, `logs/*.log`, `data/schema/.migrate_watermark.json`.
- `.env` — template file with `DATABASE_URL` placeholder and inline comment.
- Scaffolding of `src/`, `docs/`, `data/schema/`, `data/schema/facts/`, `data/quality/` directories.

**Out of Scope**

- AIB product-doc stub population (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) — explicitly excluded per QID-BF-002-C.
- Additional `docs/` files beyond `docs/supabase-setup.md`.
- Web API, dashboarding, or front-end.
- Real-time alerting or email notifications for anomalies.
- Data archiving or retention enforcement.
- Containerisation or CI/CD pipeline.
- Changes to `data/raw/` layout or format.
- Modification of source nomenclature JSON files (`data/nomenclatures/`).
- Supabase authentication, row-level security, or API key rotation.
- Production scheduling or cron configuration.
- Deletion or modification of `extract.py`.

**Assumptions**

- A1 (carried from 01-analysis): `src/pipeline.py` is the single integrated download + ETL entry point; `extract.py` is kept as-is but is not the primary entry point.
- A2 (carried from 01-analysis): Backfill all 52 existing ZIPs on first run in ascending date order; `--no-backfill` flag skips backfill.
- A6 (carried from 01-analysis): ZIPs are always processed in ascending date order to ensure correct SCD Type 2 timeline.
- A14 (new): `python-dotenv` is used to load `.env` in both `pipeline.py` and `migrate_supabase.py`; script falls back to OS environment if `.env` is absent.
- A15 (new): `docs/` directory does not yet exist and is created as part of Task 1 scaffolding.
- A16 (new): A company's first appearance in the dataset cannot trigger an anomaly (no historical baseline); status defaults to OK.

**Constraints**

- Python ≥ 3.9 only; `psycopg2-binary` permitted as the sole compiled dependency (for `migrate_supabase.py`).
- Must process one ZIP at a time to bound memory peak to approximately 200 MB.
- Must be idempotent: re-running the pipeline against an already-processed ZIP produces no duplicate records.
- `ANOMALY_THRESHOLD = 0.25` (default); configurable via `--threshold` CLI argument in `pipeline.py`.
- `RECENT_DAYS = 3` constant in `migrate_supabase.py` (trade-object Tier 1 window; per QID-AT-001-B).
- `DATABASE_URL` must be read from environment or `.env`; never hardcoded.
- Total Supabase storage (heap + indexes) after full migration ≤ 500 MB.
- `edit_allowed = Y` for all 8 targeted product-doc files per `references.md`; however, editing those stubs is outside this iteration's scope per QID-BF-002-C.

---

## Decision Gates (Blocking Questions & Answers)

1) **Question:** What is the canonical anomaly-detection threshold, and to which metrics does it apply?  
   **Chosen Answer / Value:** 25 % (`ANOMALY_THRESHOLD = 0.25`) applied equally to all three metrics: total row count, unique product-code count, unique product-name count.  
   **Rationale:** Goal item 5 (explicit) overrides the Constraints section artefact (30 %); Iteration 02 overrides Iteration 01 per AIB precedence rule.  
   **Evidence / Reference:** 02-questionnaire.md QID-BF-001-A; 02-analysis.md §Executive Summary; request.md §Goal item 5.  
   **Impact if changed:** Raising to 30 % flags fewer files; lowering to 20 % raises false-positive rate. One-line constant change; no architectural impact.

2) **Question:** What deliverables constitute "product user guide and technical documentation" (Goal item 6)?  
   **Chosen Answer / Value:** README.md only — a single thorough file in the project root covering both user and developer audiences. AIB product-doc stubs are NOT populated this iteration.  
   **Rationale:** User explicitly selected option C in QID-BF-002; questionnaire answers are the canonical input for plan generation per AIB convention.  
   **Evidence / Reference:** 02-questionnaire.md QID-BF-002-C.  
   **Impact if changed:** Selecting A or B requires populating 8 additional AIB stub files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01), adding several tasks. SC7's AIB-stub sub-criterion is considered out of scope for this iteration.

3) **Question:** Is `src/migrate_supabase.py` a one-time initial load or an incremental daily sync?  
   **Chosen Answer / Value:** Incremental daily sync (option B): the script uses a watermark and is intended to run daily alongside `pipeline.py`; it pushes each new day's data and prunes data outside the retention window.  
   **Rationale:** User explicitly selected option B in QID-BF-003.  
   **Evidence / Reference:** 02-questionnaire.md QID-BF-003-B; 02-analysis.md §Technical Knowledge migrate_supabase.  
   **Impact if changed:** Selecting A (one-time) removes watermark and upsert logic; halves migration script complexity. Selecting C (idempotent full-reload) simplifies to truncate-and-reload pattern.

4) **Question:** What granularity does Supabase Tier 1 (`fact_prices_daily`) use, and how many days does it cover?  
   **Chosen Answer / Value:** Trade-object level — records contain (fact_date, company_sk, trade_object_sk, product_sk, city_sk, category_sk, retail_price, promo_price); window = last `RECENT_DAYS = 3` days.  
   **Rationale:** User explicitly selected option B in QID-AT-001; the questionnaire noted that option B requires `RECENT_DAYS = 3` and that SC9 must be updated. Trade-object level at 3 days ≈ 3.84 M rows ≈ 300 MB — within the 500 MB budget.  
   **Evidence / Reference:** 02-questionnaire.md QID-AT-001-B; 02-analysis.md §Technical Knowledge two-tier fact strategy.  
   **Impact if changed:** Switching to product-level aggregation (A) allows 7 days at lower storage but loses per-store granularity.

5) **Question:** Which Python library is used for Supabase bulk loading?  
   **Chosen Answer / Value:** `psycopg2-binary` — direct PostgreSQL connection via `DATABASE_URL`; uses `execute_values()` for batch inserts. Added to `requirements.txt`.  
   **Rationale:** Fastest bulk load; user explicitly selected option A in QID-AT-002.  
   **Evidence / Reference:** 02-questionnaire.md QID-AT-002-A; 02-analysis.md §Technical Knowledge psycopg2-binary.  
   **Impact if changed:** Using `supabase-py` (B) is limited to ~1,000 rows per API call; full load would be significantly slower.

6) **Question:** Should the pipeline backfill all 52 existing ZIPs on first run?  
   **Chosen Answer / Value:** Yes — process all 52 ZIPs in ascending date order on first run; `--no-backfill` flag skips backfill.  
   **Rationale:** 01-questionnaire.md was not answered; Assumption A2 from 01-analysis.md carries forward and is consistent with SC1 in request.md.  
   **Evidence / Reference:** 01-analysis.md §Assumptions A2; request.md §Success Criteria SC1; 02-analysis.md §Scope Interpretation.  
   **Impact if changed:** Disabling backfill leaves the schema empty and anomaly detection without a 7-day rolling baseline.

7) **Question:** Should SCD Type 2 be applied to all five dimensions?  
   **Chosen Answer / Value:** Yes — SCD Type 2 (`valid_from`, `valid_to`, `is_current`) is applied to all five: company, trade_object, product, city, category.  
   **Rationale:** All five dimensions are explicitly typed as SCD Type 2 in request.md §Scope.  
   **Evidence / Reference:** request.md §Scope (all five `data/schema/dim_*.json` entries); 02-analysis.md §Scope Interpretation.  
   **Impact if changed:** Using SCD Type 1 for city or category loses historical rename tracking; mismatches request.md and SC2.

---

## Work Breakdown Structure (WBS)

### Task 1: Repository Scaffolding and Dependency Setup

**Intent:** Create all required directories and configuration files, and update dependency declarations so subsequent tasks have a clean, correctly configured workspace.

**Inputs:**
- Existing project root: `extract.py`, `requirements.txt` (7 dependencies), `data/`, `logs/`
- QID-AT-002-A: add `psycopg2-binary`
- QID-BF-003-B: add `python-dotenv` for `.env` loading
- No `.gitignore` currently exists

**Outputs:**
- `src/` directory (empty, populated by later tasks)
- `docs/` directory (empty, populated by Task 8)
- `data/schema/`, `data/schema/facts/`, `data/quality/` directories
- `requirements.txt` (updated: `psycopg2-binary`, `python-dotenv` appended)
- `.gitignore` (new)
- `.env` (new, placeholder only)

**Procedure:**
1. Create `src/`, `docs/`, `data/schema/`, `data/schema/facts/`, `data/quality/` directories.
2. Append `psycopg2-binary` and `python-dotenv` to `requirements.txt`.
3. Create `.gitignore` with entries: `.env`, `venv/`, `__pycache__/`, `*.pyc`, `*.partial`, `logs/*.log`, `data/schema/.migrate_watermark.json`.
4. Create `.env` containing `DATABASE_URL=postgresql://postgres:<password>@<host>:<port>/postgres` with a comment directing the user to obtain the value from the Supabase dashboard.

**Done Criteria:**
- `src/`, `docs/`, `data/schema/facts/`, `data/quality/` all exist.
- `requirements.txt` contains `psycopg2-binary` on its own line.
- `.gitignore` exists and contains the line `.env`.
- `.env` exists and `.gitignore` excludes it.

**Dependencies:** None

**Risk Notes:** Minimal; filesystem and text-file operations only.

---

### Task 2: CSV Parsing and Normalization Module

**Intent:** Implement the function that opens a company CSV from a ZIP archive or pre-extracted directory, handles UTF-8 BOM encoding, normalizes double-quoted CSV fields, and returns a structured list of clean row dicts ready for dimension upsert and fact loading.

**Inputs:**
- request.md §Background: 7 CSV columns, UTF-8 BOM encoding, double-quoted field anomaly description
- 01-analysis.md §Technical Knowledge: explicit double-quoted CSV anomaly definition
- `data/raw/2026-02-15/` (pre-extracted folder format) and `data/raw/YYYY-MM-DD.zip` (ZIP format) as real test targets

**Outputs:**
- `src/pipeline.py` (partial): `parse_csv_file(source, filename) → list[dict]`; `source` is either a `zipfile.ZipFile` or a `pathlib.Path` folder

**Procedure:**
1. Open the CSV file handle from either a `ZipFile` member or a direct `Path`; decode with `utf-8-sig` codec.
2. Read first data row with `csv.reader`; detect double-quoted-field anomaly: if every non-empty field in the row starts with a literal `"`, activate strip-extra-quotes mode for all rows.
3. Re-read all rows via `csv.DictReader` with expected column headers; in strip-extra-quotes mode, apply `field.strip().strip('"')` to every field value.
4. Validate column count equals 7; return `[]` and emit a `logging.WARNING` entry if validation fails.
5. Coerce `retail_price` to `float`; treat empty `promo_price` as `None`.
6. Return `list[dict]` with keys: `city_ekatte`, `trade_object`, `product_name`, `product_code`, `category_id`, `retail_price`, `promo_price`.

**Done Criteria:**
- Given the pharmacy-chain CSV from `data/raw/2026-02-15/` that exhibits double-quoted fields, `parse_csv_file` returns a non-empty list with correctly typed `float` prices.
- Given a standard CSV (no double-quoting), `parse_csv_file` returns correct rows without modification.
- Given a file with wrong column count, `parse_csv_file` returns `[]` and a WARNING is visible in the log.

**Dependencies:** Task 1 (`src/` directory)

**Risk Notes:** Inspect at least one pharmacy CSV before implementation to confirm the double-quoting pattern is consistent across all rows (not mixed). If only some rows are double-quoted, row-level detection is needed.

---

### Task 3: SCD Type 2 Dimension Module

**Intent:** Implement dimension loading, deduplication, and SCD Type 2 upsert logic for all five dimensions; seed city and category dimensions from existing nomenclature files on first run.

**Inputs:**
- `data/nomenclatures/cities-ekatte-nomenclature.json` (EKATTE → city name)
- `data/nomenclatures/product-categories.json` (101 category entries, IDs 1–101)
- request.md §Scope: natural keys per dimension (UIC for company; UIC + name for trade object; UIC + product_code for product; EKATTE for city; category_id for category)
- 02-analysis.md §Domain Knowledge: SCD Type 2 definition

**Outputs:**
- `src/pipeline.py` (partial): `DimensionStore` class with `load()`, `upsert_company()`, `upsert_trade_object()`, `upsert_product()`, `upsert_city()`, `upsert_category()`, `save()` methods
- `data/schema/dim_company.json`, `dim_trade_object.json`, `dim_product.json`, `dim_city.json`, `dim_category.json` (created on first run; updated on subsequent runs)

**Procedure:**
1. Define `DimensionStore` that loads all five JSON files into in-memory `dict` keyed by natural key; creates empty structures if files do not exist.
2. On init, if `dim_city.json` is empty, seed it from `cities-ekatte-nomenclature.json`; if `dim_category.json` is empty, seed it from `product-categories.json`.
3. Implement `upsert_*(natural_key, attributes, as_of_date) → int` (returns surrogate key SK) for each dimension:
   - Not found: insert with `sk = max_sk + 1`, `valid_from = as_of_date`, `valid_to = None`, `is_current = True`.
   - Found, same tracked attributes: return existing SK.
   - Found, attributes changed: close old record (`valid_to = as_of_date - 1 day`, `is_current = False`); insert new record.
4. Implement `save()` that writes all five JSON files atomically (write to `.tmp` file, then `os.replace`).

**Done Criteria:**
- After seeding, `dim_city.json` contains ≥ 200 records and `dim_category.json` contains exactly 101 records.
- Calling `upsert_company(uic, name, date)` twice with identical inputs returns the same SK.
- Calling `upsert_product(uic, code, changed_name, date)` after a prior record produces two records — one with `is_current = False`, one with `is_current = True`.
- `save()` writes valid, parseable JSON to all five paths.

**Dependencies:** Task 1 (`src/` directory, `data/schema/` exist)

**Risk Notes:** `dim_product.json` will grow to 416 K+ records across 52 days; load the full file into RAM once per pipeline run, not once per company CSV.

---

### Task 4: Anomaly Detection Module

**Intent:** Implement per-day, per-company anomaly detection with a 7-day rolling window across three metrics (total row count, unique product-code count, unique product-name count) and produce per-day quality report JSON files.

**Inputs:**
- 02-analysis.md §Technical Knowledge: anomaly-detection metrics definition
- request.md §Goal item 5 and §Constraints: threshold 25 %, 7-day rolling per-company window
- QID-BF-001-A: 25 % threshold applied equally to all three metrics
- `data/schema/facts/` (previously written fact files supply the rolling history)

**Outputs:**
- `src/pipeline.py` (partial): `AnomalyDetector` class or module-level functions: `load_company_metrics(uic, lookback, facts_dir)`, `detect_anomalies(day, company_data_map, threshold) → dict`
- `data/quality/YYYY-MM-DD-report.json` per processed day

Report JSON schema (per-company entry):
- `uic` | `company_name` | `status` (OK / WARNING / REJECTED) | `flags` (list of: `metric`, `observed`, `rolling_mean`, `deviation_pct`) | `notes`

**Procedure:**
1. Implement `load_company_metrics(uic, lookback=7, facts_dir)`: scan the `lookback` most-recent fact JSON files before the current day; compute per-company row count, unique product-code count, unique product-name count from those files.
2. Implement `detect_anomalies(day, company_data_map, threshold=0.25)`:
   - `company_data_map`: `{uic → list[row_dict]}` for this day's parsed CSVs.
   - For each company: if `company_data_map[uic]` is an empty list due to parse failure → status `REJECTED`.
   - If no historical data (first occurrence) → status `OK`.
   - Otherwise: compute observed metrics; if any metric deviates more than `threshold` from rolling mean → status `WARNING`; populate `flags` list.
3. Write `data/quality/YYYY-MM-DD-report.json` (list of per-company entries, sorted by UIC).

**Done Criteria:**
- `data/quality/2026-02-15-report.json` exists after processing 2026-02-15.
- The pharmacy-chain company whose CSV exhibits double-quoted fields appears in the report with `status = "WARNING"` and a `notes` entry explicitly citing "double-quoted CSV fields" (SC3 requirement).
- Re-running anomaly detection for a day that already has a report produces no corrupt or duplicate file.
- A company with no prior fact data is assigned `status = "OK"`.

**Dependencies:** Task 2 (parsed rows), Task 3 (dimension lookup for company names), Task 5 (fact files provide historical window — see risk note)

**Risk Notes:** During backfill, Task 6 writes fact files in ascending day order before calling anomaly detection for that same day; historical lookup correctly finds N-1 through N-7 days already written during the current backfill run. Processing order must be strictly ascending (enforced by Task 6).

---

### Task 5: Fact Loading Module

**Intent:** Transform parsed CSV rows for a single day into fact records using surrogate keys from the dimension store and write the result as an atomic daily fact JSON file.

**Inputs:**
- Parsed row dicts from Task 2 (`parse_csv_file`)
- Dimension surrogate keys from Task 3 (`DimensionStore`)
- request.md §Scope: fact record schema — (date, company_sk, trade_object_sk, product_sk, city_sk, category_sk, retail_price, promo_price)

**Outputs:**
- `src/pipeline.py` (partial): `build_facts(day, company_uic, rows, dim_store) → list[dict]`; `write_fact_file(day, facts) → None`
- `data/schema/facts/YYYY-MM-DD.json` (one file per processed day, atomically written)

Fact JSON structure: metadata header `{date, company_count, row_count}` followed by `facts` array.

**Procedure:**
1. In `build_facts`, for each row: call `upsert_*` on `DimensionStore` to resolve all five SKs; if `city_ekatte` does not resolve to a known SK, log WARNING and skip the row (do not emit a fact with a null FK).
2. Return the complete list of fact dicts for one company; the caller in Task 6 accumulates facts across all companies for the same day.
3. In `write_fact_file`, write `{metadata, facts}` JSON to a `.partial` temp file; atomically rename to `data/schema/facts/YYYY-MM-DD.json`.
4. Idempotency: Task 6 checks if the fact file already exists before initiating parsing; skips the day if file is present and `--force` is absent.

**Done Criteria:**
- After processing 2026-02-15, `data/schema/facts/2026-02-15.json` exists and contains integer surrogate keys and `float` retail prices.
- `data/schema/facts/2026-02-15.json` contains no `null` value for `city_sk` or `category_sk` (all must resolve from seeded dimensions).
- Running the pipeline a second time for the same date produces no new fact file (idempotency, per SC4).

**Dependencies:** Task 2 (parsed rows), Task 3 (DimensionStore for surrogate key resolution)

**Risk Notes:** Peak memory: accumulate all rows for one day (≈ 1.28 M rows × ~150 bytes) before writing — approximately 192 MB, within the one-ZIP-at-a-time constraint.

---

### Task 6: Main Pipeline Entry Point (src/pipeline.py)

**Intent:** Integrate download, CSV parsing, dimension management, fact loading, and anomaly detection into a single executable entry point with CLI interface, structured logging to `logs/`, and full backfill support.

**Inputs:**
- `extract.py` (download logic to adapt — scraping and file-download functions)
- Tasks 2–5 (all module-level classes and functions implemented in `src/pipeline.py`)
- request.md §Constraints: `--threshold` CLI argument, idempotency, logging to `logs/`
- QID-BF-003-B: newly downloaded ZIPs are processed in the same run that downloads them

**Outputs:**
- `src/pipeline.py` (complete, executable)
- `logs/pipeline.log` (appended each run via `FileHandler`)

**Procedure:**
1. Implement CLI with `argparse`: `--threshold FLOAT` (default 0.25), `--no-backfill`, `--force`.
2. Configure `logging`: `FileHandler` → `logs/pipeline.log`; `StreamHandler` → console; level INFO; timestamp prefix.
3. Adapt download functions from `extract.py`: scrape `https://kolkostruva.bg/opendata` for `.zip` links; download new ZIPs to `data/raw/`; collect a list of newly-downloaded date strings.
4. Build candidate-date list: enumerate all dates available in `data/raw/` (as ZIP files or pre-extracted directories) sorted ascending; if `--no-backfill`, restrict to dates with no existing fact file AND dates just downloaded.
5. Instantiate `DimensionStore` once; call `load()`.
6. For each candidate date in ascending order:
   - If `data/schema/facts/YYYY-MM-DD.json` exists and `--force` absent: log SKIP and continue.
   - Open the ZIP (or pre-extracted folder); enumerate company CSV filenames.
   - For each company CSV: call `parse_csv_file`; on parse failure (empty return), record company as REJECTED in anomaly map.
   - Call `build_facts(day, uic, rows, dim_store)` per company; accumulate day-level fact list.
   - Call `dim_store.save()` after all companies for this day are processed.
   - Call `write_fact_file(day, all_facts)`.
   - Call `detect_anomalies` and write quality report.
7. Log final summary: days processed, rows written, companies flagged WARNING or REJECTED.

**Done Criteria:**
- `python src/pipeline.py` exits with code 0 after processing all 52 ZIPs (SC1); `ls data/schema/facts/ | wc -l` returns 52.
- Re-running immediately produces no new fact or dimension records (SC4).
- `python src/pipeline.py --threshold 0.1` runs without error; anomaly reports reflect 10 % threshold (SC6).
- `logs/pipeline.log` exists and contains per-day processing lines.

**Dependencies:** Tasks 1–5

**Risk Notes:** Processing 52 days × 1.28 M rows is CPU-bound; estimate 10–30 minutes on a typical machine. Log progress per ZIP. Memory bounded by one-day-at-a-time design.

---

### Task 7: README.md

**Intent:** Create a thorough `README.md` in the project root covering installation, pipeline operation, migration script usage, output reference, and quality-report interpretation for both operator and developer audiences, per QID-BF-002-C.

**Inputs:**
- request.md §Goal and §Scope
- Task 6 (`pipeline.py` CLI interface and output paths)
- Task 9 (`migrate_supabase.py` interface; `docs/supabase-setup.md` pointer)
- 02-analysis.md §Domain Knowledge (affected personas: pipeline operator, data analyst, Supabase admin)

**Outputs:**
- `README.md` (new, project root)

**Procedure:**
1. Write the following sections in order: Project Overview, Prerequisites (Python ≥ 3.9, pip), Installation (clone → pip install → .env setup), Configuration (environment variables, `.env`, constants in script), Running the Pipeline (`python src/pipeline.py` with flag examples), Output Reference (`data/schema/`, fact file format, dimension file format), Running Supabase Migration (prerequisites, `python src/migrate_supabase.py`), Interpreting Quality Reports (statuses OK/WARNING/REJECTED, flag fields, example JSON snippet), Data Model Overview (brief star schema and SCD Type 2 description), Pointer to `docs/supabase-setup.md` for full database DDL.
2. Include fenced code blocks for all commands.
3. Describe anomaly detection logic (three metrics, threshold, rolling window) in plain language.
4. Ensure no placeholder text remains in any section.

**Done Criteria:**
- `README.md` exists in the project root.
- File contains at minimum the sections: Installation, Running the Pipeline, Output Reference, Interpreting Quality Reports.
- No placeholder or template text (e.g., "TODO") remains.
- SC7 (README.md existence and content) is satisfied.

**Dependencies:** Task 6 (pipeline CLI and output paths must be known before documenting them)

**Risk Notes:** None.

---

### Task 8: docs/supabase-setup.md

**Intent:** Create a step-by-step Supabase PostgreSQL setup document containing the complete SQL DDL for all seven tables (five dimension tables, two fact tables), all indexes, and all foreign key constraints.

**Inputs:**
- request.md §Goal item 7 and §Scope (table names, surrogate key names)
- QID-AT-001-B: Tier 1 schema includes `trade_object_sk` and `city_sk`; `RECENT_DAYS = 3`
- 02-analysis.md §Technical Knowledge: two-tier fact strategy, volume estimates

**Outputs:**
- `docs/supabase-setup.md` (new)

**Procedure:**
1. Write prerequisites: Supabase account, project creation, navigating to the SQL editor.
2. Write `CREATE TABLE` DDL for all five dimension tables:
   - `dim_company(company_sk SERIAL PRIMARY KEY, uic TEXT NOT NULL, company_name TEXT, legal_name TEXT, valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL)`
   - `dim_trade_object(trade_object_sk SERIAL PRIMARY KEY, uic TEXT NOT NULL, trade_object_name TEXT NOT NULL, valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL)`
   - `dim_product(product_sk SERIAL PRIMARY KEY, uic TEXT NOT NULL, product_code TEXT NOT NULL, product_name TEXT, category_id INT, valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL)`
   - `dim_city(city_sk SERIAL PRIMARY KEY, ekatte TEXT NOT NULL, city_name TEXT, valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL)`
   - `dim_category(category_sk SERIAL PRIMARY KEY, category_id INT NOT NULL, category_name TEXT, valid_from DATE NOT NULL, valid_to DATE, is_current BOOLEAN NOT NULL)`
3. Write `CREATE TABLE` DDL for `fact_prices_daily` (Tier 1, trade-object level): columns `id BIGSERIAL PRIMARY KEY, fact_date DATE NOT NULL, company_sk INT REFERENCES dim_company, trade_object_sk INT REFERENCES dim_trade_object, product_sk INT REFERENCES dim_product, city_sk INT REFERENCES dim_city, category_sk INT REFERENCES dim_category, retail_price NUMERIC(10,2), promo_price NUMERIC(10,2)`.
4. Write `CREATE TABLE` DDL for `fact_prices_weekly_hist` (Tier 2): columns `id BIGSERIAL PRIMARY KEY, week_start DATE NOT NULL, company_sk INT REFERENCES dim_company, category_sk INT REFERENCES dim_category, avg_retail_price NUMERIC(10,4), avg_promo_price NUMERIC(10,4), product_count INT, submission_count INT`.
5. Write `CREATE INDEX` statements: on `fact_prices_daily(fact_date, company_sk)`, `fact_prices_daily(product_sk, fact_date)`, `fact_prices_daily(category_sk)`, `fact_prices_weekly_hist(week_start, company_sk)`, `fact_prices_weekly_hist(category_sk)`.
6. Write the step-by-step guide: paste DDL in Supabase SQL editor → execute → obtain `DATABASE_URL` from Supabase dashboard (Settings → Database) → set in `.env`.
7. Add a note that DDL should be verified against actual Supabase PostgreSQL before production use.

**Done Criteria:**
- `docs/supabase-setup.md` exists.
- File contains `CREATE TABLE` statements for all seven tables (5 dimension + 2 fact).
- File contains `CREATE INDEX` statements for all five listed indexes.
- File contains at least three numbered instructional steps.
- SC8 is satisfied.

**Dependencies:** Task 1 (`docs/` directory)

**Risk Notes:** DDL uses PostgreSQL-specific syntax (`SERIAL`, `REFERENCES`); valid for Supabase (managed PostgreSQL). Developer must paste into the Supabase SQL editor to validate before migration.

---

### Task 9: src/migrate_supabase.py (Incremental Daily Sync)

**Intent:** Implement the standalone incremental daily sync script that reads local JSON star-schema data and syncs it to Supabase PostgreSQL using the two-tier strategy and a local watermark file, staying within 500 MB total storage.

**Inputs:**
- QID-BF-003-B: incremental daily sync with watermark
- QID-AT-001-B: Tier 1 = trade-object level, `RECENT_DAYS = 3`
- QID-AT-002-A: `psycopg2-binary`, `python-dotenv`
- `data/schema/` (all dim JSON and fact JSON files, written by pipeline)
- `docs/supabase-setup.md` (authoritative table schema)
- `DATABASE_URL` from `.env` / environment

**Outputs:**
- `src/migrate_supabase.py` (new, standalone script)
- `data/schema/.migrate_watermark.json` (local watermark; gitignored)

**Procedure:**
1. On startup: load `.env` via `python-dotenv`; read `DATABASE_URL` from environment; exit with code 1 and a descriptive error if absent.
2. Define script-level constants: `RECENT_DAYS = 3`, `TIER2_WEEK_DOW = 0` (ISO Monday as week start).
3. Implement `connect(url) → psycopg2.connection`; test with a lightweight query; fail fast on connection error.
4. Implement `sync_dimensions(conn, schema_dir)`: for each of the five dimension JSON files, use `psycopg2.extras.execute_values()` with `ON CONFLICT (uic, valid_from) DO UPDATE SET ...` (natural key + valid_from as conflict target) to upsert all records.
5. Load watermark from `data/schema/.migrate_watermark.json` (default: earliest available fact date if file absent).
6. Compute `cutoff_date = max_available_fact_date - timedelta(days=RECENT_DAYS - 1)`.
7. Implement `sync_tier1(conn, watermark, cutoff_date, facts_dir)`: for each fact date in (`watermark`, `max_fact_date`] that is ≥ `cutoff_date`, load fact JSON and insert rows into `fact_prices_daily` using `execute_values()`; delete rows from `fact_prices_daily` where `fact_date < cutoff_date`.
8. Implement `sync_tier2(conn, watermark, cutoff_date, facts_dir)`: for each fact date in (`watermark`, `cutoff_date`) (dates transitioning out of Tier 1), aggregate: group by (ISO week start, company_sk, category_sk), compute avg and count; upsert into `fact_prices_weekly_hist`.
9. Update watermark to `max_fact_date`; write `data/schema/.migrate_watermark.json`.
10. Log rows inserted/updated per table; handle exceptions with `conn.rollback()` and a meaningful error message; exit code 1 on failure.

**Done Criteria:**
- `python src/migrate_supabase.py` exits code 0 when `DATABASE_URL` is set and Supabase is reachable.
- `fact_prices_daily` contains rows only for the 3 most-recent fact dates after a completed migration (SC9 adjusted per QID-AT-001-B).
- `fact_prices_weekly_hist` contains weekly aggregates for all dates before the 3-day window.
- Re-running the script on the same data produces no additional rows (sync idempotency).
- If `DATABASE_URL` is not set, script exits code 1 with a descriptive message (no traceback).
- Total Supabase storage after full initial load ≤ 500 MB (volume estimate from 02-analysis.md §Technical Knowledge supports this; to be verified empirically).

**Dependencies:** Task 1 (`.env`, `requirements.txt`), Task 3 (dimension files), Task 5 (fact files), Task 8 (table schema known)

**Risk Notes:** `psycopg2-binary` requires outbound access to Supabase on port 5432 (direct) or 6543 (connection pooler). If blocked by firewall, the script will fail at `connect()`. `data/schema/.migrate_watermark.json` is environment-specific; it is gitignored and must not be shared in version control.

---

### Task 10: Integration Verification

**Intent:** Validate all nine success criteria (SC1–SC9) against the fully implemented system; record results in `implementation.md`; apply any corrective code changes.

**Inputs:**
- Outputs of Tasks 1–9 (all deliverables)
- request.md §Success Criteria SC1–SC9
- `data/raw/` containing 52 ZIPs

**Outputs:**
- Corrective code patches (if any SC fails)
- `implementation.md` (iteration 02 entry documenting test results)

**Procedure:**
1. SC1: Run `python src/pipeline.py`; verify exit code 0; run `ls data/schema/facts/ | wc -l` = 52.
2. SC2: Inspect `dim_company.json` and `dim_product.json` for `valid_from`, `valid_to`, `is_current` fields; spot-check one company across multiple dates for correct SCD history.
3. SC3: Open `data/quality/2026-02-15-report.json`; locate the pharmacy-chain company with double-quoted CSV; verify `status = "WARNING"` and `notes` cites "double-quoted CSV fields".
4. SC4: Run `python src/pipeline.py` a second time; verify no new fact files and no new dimension records appear.
5. SC5: Copy and rename an existing ZIP to a new date-name under `data/raw/`; run pipeline; verify the new date's fact file appears.
6. SC6: Run `python src/pipeline.py --threshold 0.1`; verify script accepts the argument and the 2026-02-15 quality report would have been produced with 10 % threshold (re-run against known data if needed).
7. SC7: Verify `README.md` exists; check for Installation and Usage sections.
8. SC8: Verify `docs/supabase-setup.md` exists; `grep -i "CREATE TABLE" docs/supabase-setup.md` returns ≥ 7 matches.
9. SC9: If `DATABASE_URL` is available, run `python src/migrate_supabase.py`; query Supabase to confirm `fact_prices_daily` contains exactly 3 days of data and `fact_prices_weekly_hist` contains non-zero rows. If `DATABASE_URL` is unavailable, mark SC9 as deferred in `implementation.md`.

**Done Criteria:**
- SC1–SC8 all pass.
- SC9 documented as passed (if Supabase available) or as deferred with rationale.
- `implementation.md` contains the iteration 02 entry with changes, test results, and outcome.

**Dependencies:** Tasks 1–9

**Risk Notes:** SC9 requires an active Supabase project with the DDL applied. If unavailable during development, the migration script logic is verified through code review and unit-style testing of the connection/aggregation logic only.

---

## Dependencies & Interfaces

**Internal Task Dependencies**

- From Task: 1 | To Task: 2 | Dependency Type: FS | Critical: Y | Notes: `src/` directory must exist before writing `pipeline.py` code
- From Task: 1 | To Task: 3 | Dependency Type: FS | Critical: Y | Notes: `data/schema/` must exist before dimension files can be written
- From Task: 1 | To Task: 8 | Dependency Type: FS | Critical: Y | Notes: `docs/` directory must exist before creating `supabase-setup.md`
- From Task: 2 | To Task: 4 | Dependency Type: FS | Critical: Y | Notes: parsed rows supply the observed metrics for anomaly detection
- From Task: 2 | To Task: 5 | Dependency Type: FS | Critical: Y | Notes: parsed rows are the input to `build_facts`
- From Task: 3 | To Task: 4 | Dependency Type: FS | Critical: Y | Notes: dimension store provides company name lookup for report labelling
- From Task: 3 | To Task: 5 | Dependency Type: FS | Critical: Y | Notes: dimension store provides surrogate key resolution for fact records
- From Task: 5 | To Task: 4 | Dependency Type: SS | Critical: Y | Notes: anomaly detection reads prior-day fact files; fact files for day N must be written before anomaly detection for day N+1 (handled by ascending-order processing in Task 6)
- From Task: 2 | To Task: 6 | Dependency Type: FS | Critical: Y | Notes: parsing module must be complete before orchestration layer is written
- From Task: 3 | To Task: 6 | Dependency Type: FS | Critical: Y | Notes: dimension module must be complete before orchestration layer is written
- From Task: 4 | To Task: 6 | Dependency Type: FS | Critical: Y | Notes: anomaly detection module must be complete before orchestration layer
- From Task: 5 | To Task: 6 | Dependency Type: FS | Critical: Y | Notes: fact loading module must be complete before orchestration layer
- From Task: 6 | To Task: 7 | Dependency Type: FS | Critical: Y | Notes: CLI flags and output paths must be finalized before README documents them
- From Task: 3 | To Task: 9 | Dependency Type: FS | Critical: Y | Notes: dimension JSON files must be design-stable before migration upsert logic is written
- From Task: 5 | To Task: 9 | Dependency Type: FS | Critical: Y | Notes: fact JSON file structure must be stable before migration reads them
- From Task: 8 | To Task: 9 | Dependency Type: FS | Critical: N | Notes: table DDL should be known before writing migration inserts; not strictly blocking but reduces rework
- From Task: 1 | To Task: 10 | Dependency Type: FS | Critical: Y | Notes: all scaffolding must be done
- From Task: 9 | To Task: 10 | Dependency Type: FS | Critical: Y | Notes: all deliverables must exist before integration verification

**External Interfaces**

- Interface: kolkostruva.bg/opendata | Direction: In | Protocol/Contract: HTTP GET, HTML scraping (BeautifulSoup) | Version: current (unauthenticated) | Notes: scrape `.zip` links; no API key required; same logic as `extract.py`
- Interface: data/raw/ ZIP files | Direction: In | Protocol/Contract: ZIP archive; internal CSV files; UTF-8 BOM | Version: YYYY-MM-DD.zip naming convention | Notes: read-only; some dates are pre-extracted folders
- Interface: data/nomenclatures/ JSON files | Direction: In | Protocol/Contract: JSON (flat key-value structure) | Version: current | Notes: read-only; must not be modified
- Interface: Supabase PostgreSQL | Direction: Out | Protocol/Contract: PostgreSQL wire protocol via psycopg2-binary; connection string `postgresql://...` | Version: PostgreSQL 15 (Supabase default) | Notes: outbound port 5432 or 6543; DATABASE_URL from environment

---

## Environment & Configuration

**Environments:** Development (local machine, Python ≥ 3.9 virtual environment)

**Config Keys**

- Key: ANOMALY_THRESHOLD | Scope: Global | Default: 0.25 | Allowed Range/Values: 0.0–1.0 (float) | Source: `src/pipeline.py` script-level constant; overridable via `--threshold` CLI | Change Control: edit constant in script or pass CLI argument
- Key: RECENT_DAYS | Scope: Global | Default: 3 | Allowed Range/Values: 1–30 (int) | Source: `src/migrate_supabase.py` script-level constant | Change Control: edit constant in script
- Key: OPENDATA_URL | Scope: Global | Default: https://kolkostruva.bg/opendata | Allowed Range/Values: valid URL string | Source: `src/pipeline.py` | Change Control: edit constant in script
- Key: DATABASE_URL | Scope: Env | Default: (none — must be set) | Allowed Range/Values: valid PostgreSQL connection string `postgresql://user:password@host:port/dbname` | Source: `.env` file or OS environment variable | Change Control: update `.env`; never commit to version control

**Secrets Handling:** `DATABASE_URL` is the sole secret. It is read at runtime from the `.env` file (via `python-dotenv`) or from the OS environment. The `.env` file is listed in `.gitignore` and must never be committed to version control. The script emits a clear error and exits code 1 if `DATABASE_URL` is absent; it never logs its value.

---

## Testing Strategy (This Iteration)

**Test Types:** Integration (primary); Manual end-to-end; Code-review-based unit verification

**Coverage Targets:** All nine success criteria (SC1–SC9) must pass; no formal unit-test coverage percentage target is set for this iteration.

**Data / Fixtures:**
- `data/raw/` with 52 existing ZIPs is the primary fixture (real source data already present).
- For SC3 (double-quoted CSV anomaly): `data/raw/2026-02-15/` contains a real pharmacy-chain file that exhibits the anomaly — use as the authoritative regression fixture.
- For SC5 (new ZIP processing): copy and rename an existing ZIP to a future date under `data/raw/` as a synthetic test fixture; delete after verification.

**Test Execution:**
1. `pip install -r requirements.txt` in the virtual environment.
2. `python src/pipeline.py` (full backfill run, SC1–SC4, SC6).
3. `python src/pipeline.py --threshold 0.1` (SC6 CLI flag).
4. Inspect specific output files per SC2, SC3, SC7, SC8.
5. `python src/migrate_supabase.py` (SC9; requires DATABASE_URL).

**Acceptance Evidence:**
- Terminal output showing exit code 0 for `pipeline.py`.
- `ls data/schema/facts/ | wc -l` output = 52.
- `cat data/quality/2026-02-15-report.json` showing the pharmacy WARNING entry.
- `logs/pipeline.log` tail showing the final summary line.
- `docs/supabase-setup.md` content reviewed for all seven CREATE TABLE statements.
- Migration log output (SC9, if Supabase available).

---

## Observability & Quality Gates

**Key Metrics / Logs**

- `logs/pipeline.log`: per-day entries including date processed, companies parsed, rows written to fact file, companies flagged WARNING, companies REJECTED.
- `data/quality/YYYY-MM-DD-report.json`: per-company status and flag detail; serves as the primary data-quality audit trail.
- Dimension file sizes: `dim_product.json` size growth serves as a proxy for correct SCD accumulation.

**Quality Gates**

- QG1: `python src/pipeline.py` exits code 0 with 52 fact files present (SC1). Required before marking iteration complete.
- QG2: No fact file contains a `null` surrogate key for `city_sk` or `category_sk` (all dimension lookups resolve). Required to satisfy SC2.
- QG3: `data/quality/2026-02-15-report.json` contains a WARNING entry for the pharmacy-chain double-quoted CSV file (SC3). Required.
- QG4: Second run of `pipeline.py` produces zero new records across fact and dimension files (idempotency; SC4). Required.
- QG5: `README.md` and `docs/supabase-setup.md` exist with project-specific content (SC7 partial, SC8). Required.
- QG6: `migrate_supabase.py` exits code 1 with a descriptive message when `DATABASE_URL` is absent. Required for security correctness.

---

## Documentation Touchpoints

- Doc Path: `README.md` | Change Type: create | Update Trigger: Task 7 | Edit Allowed: Y (not in references.md; new file) | Notes: Project root; covers user and developer audiences per QID-BF-002-C
- Doc Path: `docs/supabase-setup.md` | Change Type: create | Update Trigger: Task 8 | Edit Allowed: Y (not in references.md; new file) | Notes: Full DDL + step-by-step setup guide
- Doc Path: `.aib_memory/docs/04 Technology/Data Sources/DATA-01.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Data Models/DATA-02.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Data Workspace/DATA-03.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Data Workspace/DATA-04.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Data Workspace/DATA-07.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Compute/CMP-01.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/02 Domain/Terms and Concepts/KNW-01.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/docs/04 Technology/Observability/OBS-01.md` | Change Type: no-change | Update Trigger: N/A | Edit Allowed: Y | Notes: Out of scope this iteration per QID-BF-002-C; stub content unchanged
- Doc Path: `.aib_memory/requests/R-20260408-0113-extract/implementation.md` | Change Type: update | Update Trigger: Task 10 | Edit Allowed: Y | Notes: Append iteration 02 entry with changes, test results, outcome

---

## Milestones

- Milestone: M1 | Description: Core ETL pipeline operational — all 52 ZIPs processed without error | Due: On completion of Task 6 | Depends On: Tasks 1–5 | Exit Criteria: QG1 and QG4 pass; 52 fact files exist; `logs/pipeline.log` shows no unhandled exceptions

- Milestone: M2 | Description: All deliverables implemented — README, supabase-setup.md, migrate_supabase.py present | Due: On completion of Task 9 | Depends On: Tasks 7, 8, 9 | Exit Criteria: README.md, docs/supabase-setup.md, src/migrate_supabase.py all exist and contain project-specific content; no placeholder text

- Milestone: M3 | Description: Integration verified — all SC1–SC9 results documented | Due: On completion of Task 10 | Depends On: All tasks | Exit Criteria: SC1–SC8 pass; SC9 documented as passed or deferred; implementation.md updated with iteration 02 entry

---

## Risks & Mitigations

- R1: Supabase port 5432 / 6543 blocked by network firewall — P: Low, I: High — Mitigation: document port requirements and troubleshooting steps in `docs/supabase-setup.md`; SC9 verification deferred to an environment with access.

- R2: `dim_product.json` grows very large (416 K+ SCD records for 52 days) causing slow serialization — P: Medium, I: Medium — Mitigation: load full dimension into RAM once per pipeline run (not per ZIP); use `orjson` or `ujson` for faster JSON I/O if standard `json` is too slow; confirmed acceptable by 02-analysis.md volume estimates.

- R3: `kolkostruva.bg` site changes HTML structure, breaking scraping — P: Low, I: Medium — Mitigation: `extract.py` is kept as an independent fallback; `pipeline.py` logs scraping errors explicitly; ZIPs can be placed in `data/raw/` manually if scraping fails.

- R4: Memory peak for a day with an unusually large ZIP exceeds 200 MB — P: Low, I: Medium — Mitigation: one-ZIP-at-a-time processing already bounds peak; if observed, stream rows to the fact list in batches and flush to disk incrementally.

- R5: Double-quoted CSV normalization regex or heuristic does not correctly handle all pharmacy-chain file variants — P: Medium, I: Low — Mitigation: inspect at least two pharmacy CSV files before implementing; design normalization as a separate function covered by targeted test cases (SC3 regression fixture).

- R6: SC9 Supabase storage exceeds 500 MB after full migration — P: Low, I: High — Mitigation: volume estimates in 02-analysis.md show ~300 MB for Tier 1 (3 days, trade-object level) + Tier 2 + dimensions well within budget; monitor with `SELECT pg_size_pretty(pg_database_size('postgres'))` after migration; if exceeded, reduce `RECENT_DAYS` to 2.

---

## Acceptance & Handover

**Iteration Acceptance Criteria**

- All QG1–QG6 quality gates pass.
- SC1 through SC8 verified (SC9 verified if DATABASE_URL available, else deferred).
- `implementation.md` contains a dated iteration 02 entry.
- No Python exceptions propagate to the user during normal pipeline operation (all errors are caught, logged, and reported as WARNING / REJECTED in quality reports or as graceful exit-1 messages in the migration script).

**Handover Artifacts**

- `src/pipeline.py` — primary deliverable; executable entry point
- `src/migrate_supabase.py` — Supabase sync script
- `README.md` — project root user guide
- `docs/supabase-setup.md` — Supabase DDL and setup guide
- `data/schema/` — populated dimension JSON files and 52 daily fact files
- `data/quality/` — 52 anomaly report JSON files
- `requirements.txt` — updated with `psycopg2-binary` and `python-dotenv`
- `.gitignore` — new file
- `.env` — template (never contains real credentials)
- `logs/pipeline.log` — pipeline execution log from backfill run

**Post-Iteration Follow-ups**

- Consider populating AIB product-doc stubs (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) in a follow-up iteration if technical documentation is needed for the project (deferred per QID-BF-002-C).
- Consider adding a daily scheduler (e.g., cron or systemd timer) to run `pipeline.py` and `migrate_supabase.py` automatically once the one-time setup is validated.
- Evaluate incremental Supabase load performance once SC9 is validated against a real Supabase instance; adjust `RECENT_DAYS` if storage budget is tighter than estimated.
