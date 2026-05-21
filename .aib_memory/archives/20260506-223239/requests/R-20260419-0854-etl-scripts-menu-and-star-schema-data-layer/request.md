## Goal

Add an ETL runner script and an interactive menu script to the project root, move `extract.py` from the project root into a new `src/` folder, and build a star-schema data layer under `data/schema/` by parsing and transforming the raw ZIP archives already accumulated in `data/raw/`. The goal is to give the team a one-click ETL trigger, an interactive statistics/action menu, a clean source layout, and a persistently queryable human-readable structured dataset — all without modifying the existing download logic or removing any raw data.

## Background

The project currently contains only a standalone download utility (`extract.py`) at the project root. Raw daily retail-price ZIP archives accumulate in `data/raw/` (63 ZIPs as of 2026-04-19, covering 2026-02-15 through 2026-04-18). Each ZIP contains up to ~200 CSV files, one per reporting retail company (named `<CompanyName>_<UIC>.csv`), with columns: settlement EKATTE code, store name, product name, product code, category code, retail price, and promotional price.

Supporting nomenclature files are available: `data/nomenclatures/cities-ekatte-nomenclature.json` (EKATTE → settlement name mapping) and `data/nomenclatures/product-categories.json` (category id → name list). These enrich the raw data during transformation.

There is no structured pipeline runner, no transformation script, and no dimensional model. A developer must manually run `extract.py`, inspect the raw ZIPs to understand what data is available, and write ad-hoc code to query prices. This request introduces the missing transformation layer and operational scripts.

## Scope

- Create both `refresh.sh` (Linux shell) and `refresh.bat` (Windows batch) runner scripts at the project root; each runs the complete ETL pipeline (download + transformation) in sequence.

- Create a `menu.py` Python script at the project root that launches an interactive terminal session showing statistics (available date range, ZIP count, schema freshness, last downloaded and last processed dates from `config.ini`) and a numbered menu for manual invocation of individual actions (download, transform, or a combined refresh). Create both `menu.sh` (Linux) and `menu.bat` (Windows) one-line launcher scripts at the project root that invoke `python menu.py`.

- Create a `src/` folder and move `extract.py` into it as `src/extract.py`; update all internal path references so the script remains runnable from the project root.

- Create a `data/schema/` folder and populate it with a star-schema dataset in CSV format, derived from all ZIPs in `data/raw/`:
  - `dim_date.csv` — date surrogate key, ISO date, year, month, day, weekday.
  - `dim_company.csv` — company surrogate key, UIC (from filename), company name (from filename).
  - `dim_settlement.csv` — settlement surrogate key, EKATTE code, settlement name (from nomenclature).
  - `dim_category.csv` — category surrogate key, category numeric code, category name (from nomenclature).
  - `dim_product.csv` — product surrogate key, product code, canonical product name.
  - `fact_prices.csv` — fact surrogate key, date_key, company_key, store_name, settlement_key, product_key, retail_price, promo_price (nullable).

- Create a `config.ini` file at the project root containing a `[settings]` section (user-tunable: `opendata_url`, `max_retries`, `retry_delay`, `log_level`) and a `[state]` section (script-managed: `last_downloaded_date`, `last_processed_date`). All configurable parameters in `src/extract.py` and `src/transform.py` must be read from `config.ini`; both scripts write back their respective state key on successful completion. Scripts bootstrap a default `config.ini` on first run if the file is absent. Setting `last_downloaded_date` to an earlier date triggers force re-download of ZIPs from that date onward; setting `last_processed_date` triggers re-processing of fact files from that date onward.

- Update `README.md` to document the new folder structure, the new scripts, `config.ini` parameters, state tracking, and the updated `extract.py` location.

## Out of scope

- Cloud sync, database upload, dashboarding, or API exposure.
- Modifying the download logic of `extract.py` beyond path adjustments needed by the move.
- Automated scheduling (cron on Linux; Task Scheduler on Windows).
- ZIP content validation, data quality enforcement, or anomaly detection.
- Deleting, archiving, or compressing existing raw ZIPs in `data/raw/`.
- Adding a full automated test suite (basic smoke tests are sufficient).
- Any CI/CD pipeline configuration.

## Constraints

- Python 3.9+ compatibility must be maintained for all new scripts.
- The star-schema CSV files must be human-readable (no binary formats such as Parquet or Avro) and space-efficient (integer surrogate keys; no repeated string values in the fact table beyond store name if no surrogate is assigned).
- New Python dependencies are allowed only if pip-installable without compilation; they must be added to `requirements.txt`.
- The content of `data/raw/` must not be altered, deleted, or compressed.
- Both `.sh` (Linux-native) and `.bat` (Windows-compatible) variants of the runner (`refresh`) and menu launcher scripts must be created; each variant invokes the same underlying Python scripts and produces identical ETL outcomes.
- `extract.py` internal relative path `BASE_DIR` resolves paths relative to the script's own location; relocation must preserve this resolution.
- No secrets or credentials may be introduced; the project has no authentication requirements.

## Success criteria

- Running the refresh script from the project root completes without error, downloads any new ZIPs, and produces or updates all files in `data/schema/`.
- Running the menu script presents a readable readout of statistics (available dates, count, schema state) and a menu with at least three actions; each action executes correctly when selected.
- `src/extract.py` is the sole location of the download script; the project root no longer contains `extract.py`.
- `data/schema/` contains all six CSV files with correct headers and at least one data row per file.
- Re-running the refresh script when no new ZIPs exist is idempotent: dimension tables are unchanged, the fact table contains no duplicate rows.
- `README.md` accurately describes the updated folder structure and new scripts.

## Assumptions

- A1: Both `.sh` (Linux) and `.bat` (Windows) runner and menu launcher scripts will be created per Q001 Option C. The `.sh` scripts are the primary development target (Linux OS); `.bat` scripts are provided for Windows compatibility and will not run natively on Linux.
  - Risk if false: N/A — confirmed by Q001 answer.

- A2: `extract.py` will be runnable from the project root via `python src/extract.py` after relocation; no packaging or installation step is required.
  - Risk if false: Import resolution or path issues could surface if `src/` is ever added to a package structure.

- A3: All ZIPs in `data/raw/` follow the naming pattern `YYYY-MM-DD.zip`. Internal CSVs use either comma or semicolon delimiters; all share the same 7-column Bulgarian header. UTF-8 with optional BOM encoding.
  - Risk if false: Malformed ZIPs or changed column layouts would produce silent data loss; a header-validation guard is required.

- A4: `dim_settlement` is built from the set of EKATTE codes observed in the raw data (facts-driven), not pre-loaded from the full EKATTE registry (~5,256 entries). Only ~256 distinct codes appear across all 63 ZIPs. Primary lookup: `cities-ekatte-nomenclature.json`. Secondary lookup: `sof_rai.json` (38 Sofia sub-district `68134-XX` codes). Any code not resolved by either source gets `settlement_name = "(unknown:<ekatte_code>)"`. All rows — including those with unresolved EKATTE codes — are included in the fact table.
  - Risk if false: If the user requires pre-populated settlement entries for settlements with zero retail activity, a full-registry load strategy is needed instead.

- A5: The actual dataset is ~82 million valid rows across 63 ZIPs. The fact table is date-partitioned: `data/schema/facts/YYYY-MM-DD.csv` (one file per ZIP date, ~46–68 MB each after fact_key removal). Dimension tables remain as flat CSVs in `data/schema/`.
  - Risk if false: If the user requires a single flat fact table, a design trade-off between file size and usability must be accepted.

- A6: Product codes are retailer-local identifiers, not globally unique. The unique granularity for `dim_product` is the pair `(product_code, product_name)`.
  - Risk if false: If the portal enforces globally unique product codes, the composite key is redundant but harmless.

- A7: No new pip packages are needed beyond the existing `requirements.txt`. All transformation and config logic uses Python stdlib: `zipfile`, `csv`, `json`, `pathlib`, `datetime`, `configparser`, `logging`.
  - Risk if false: If Pandas is used for performance, a venv update and `requirements.txt` change are required.

- A8: The menu script computes statistics at runtime by reading `data/raw/`, `data/schema/facts/`, and `config.ini` directly. For 63 ZIPs, this is instantaneous.
  - Risk if false: At very large scale (500+ ZIPs), menu startup time could increase; acceptable for current scope.

- A9: The transform script uses `utf-8-sig` encoding for all CSV reads, which transparently handles both BOM and non-BOM files. Semicolon-delimited files are handled by delimiter auto-detection. All output CSVs are written with `encoding='utf-8'` (no BOM).
  - Risk if false: A new company joins that uses a third delimiter; the script would silently skip their rows.

- A10: The fact table includes `category_key` as a foreign key to `dim_category`. `dim_category` is built facts-driven. Rows with unknown category codes are retained in the fact table.
  - Risk if false: If the user intended category to be an attribute of `dim_product` only, the fact table schema would require redesign.

- A11: `config.ini` stores both user settings (`[settings]`) and script-managed state (`[state]`) in a single file. The `save_state()` function re-reads `config.ini` from disk immediately before writing to avoid overwriting state keys set by a previously-run script in the same pipeline sequence.
  - Risk if false: If concurrent pipeline processes write to `config.ini` simultaneously, file-level locking would be needed; acceptable for single-operator usage.

- A12: Scripts bootstrap a default `config.ini` with `[settings]` defaults and empty `[state]` keys on first run if the file is absent or has no sections.
  - Risk if false: If a user provides a partial `config.ini` with a `[settings]` section but no `[state]` section, `config.get()` with `fallback=None` handles it gracefully.

- A13: `dim_store` extracts `(store_name, settlement_key, company_key)` from the fact table into a dedicated dimension. The fact table replaces `store_name`, `settlement_key`, and `company_key` with a single `store_key` FK. This creates a partial snowflake schema: joins through `dim_store` are required to reach `dim_settlement` and `dim_company` from the fact table.
  - Risk if false: If the user requires direct settlement/company FKs in the fact table for query convenience, the snowflake design must be reverted to a star with store as an additional dimension alongside settlement and company.

- A14: `dim_file` tracks every CSV file within every ZIP. Natural key: `(file_name, zip_date)`. The fact table includes `file_key` as a FK, enabling lineage tracing. Approximately ~13,100 dimension rows for 63 ZIPs.
  - Risk if false: If the user requires file-level attributes beyond name and date (e.g., file size, row count), the dimension schema must be extended.

- A15: The `fact_key` surrogate column is removed from all fact CSVs. Rows are identifiable by their FK combination within each date-partitioned file. This saves ~656 MB across 82M rows.
  - Risk if false: If downstream consumers rely on a stable fact surrogate key for row-level referencing, they would need to use a composite key or row position instead.

- A16: All dimensions use SCD Type 1 (overwrite). When a dimension attribute value changes (e.g., a company name update), the old value is overwritten with no historical tracking.
  - Risk if false: If historical attribute tracking is later required, a migration to SCD Type 2 (add new row with timestamps) would be needed.

- A17: Dimension CSVs are written after each ZIP's fact file is fully written, providing crash safety. If the transform crashes on ZIP 40/63, dimensions for the first 39 ZIPs are persisted.
  - Risk if false: The I/O overhead of 7 dimension writes x 63 ZIPs = 441 writes is negligible for dimensions under 1 MB each.

- A18: ZIP integrity is checked after download using `zipfile.is_zipfile()`. This verifies the ZIP magic number but does not verify internal CRC checksums. A failed check deletes the file and triggers a re-download.
  - Risk if false: In-archive bit-rot or CRC mismatches would pass `is_zipfile()` but fail during extraction in `transform.py`. `zipfile.ZipFile()` itself raises `BadZipFile` on corrupt entries, providing a second layer of detection.

- A19: `Path.replace()` is used for all atomic file renames throughout the codebase, replacing any existing `Path.rename()` calls. This ensures cross-platform correctness (Windows `Path.rename()` raises `FileExistsError` if destination exists).
  - Risk if false: None — `Path.replace()` is strictly superior for overwrite-on-rename scenarios.

## Plan

### Task 0: Create config.ini and config_utils.py
**Intent:** Create `config.ini` at the project root with `[settings]` and `[state]` sections, and a shared bootstrap/state helper module callable by other scripts.
**Inputs:** None (new files)
**Outputs:** `config.ini` at project root; `src/config_utils.py` (bootstrap, atomic-write, and re-read helpers)
**External Interfaces:** `configparser`, `pathlib` (all stdlib)
**Environment & Configuration:** No secrets; no environment variables
**Procedure:**
1. Create `config.ini` with `[settings]` (opendata_url, max_retries, retry_delay, log_level) and `[state]` (last_downloaded_date, last_processed_date — initially empty).
2. Create `src/config_utils.py` with:
   - `load_config(config_path)`: reads config; if absent or empty sections, bootstraps defaults, writes, returns config.
   - `save_state(config_path, **kwargs)`: creates a fresh `ConfigParser`, re-reads `config_path` from disk, updates `[state]` keys from kwargs, writes to `<config_path>.partial`, then `Path.replace()` atomically.
3. Write a unit test for both helpers in `tests/test_config_utils.py`.
**Done Criteria:** `config.ini` exists with both sections; `save_state()` re-reads config before writing; all file renames use `Path.replace()`; tests pass.
**Dependencies:** None
**Risk Notes:** `save_state()` must NOT accept a cached config object — it must always re-read from disk.

### Task 1: Move extract.py to src/, integrate config, add ZIP integrity check
**Intent:** Relocate `extract.py` to `src/extract.py`, fix `BASE_DIR`, replace hardcoded constants with `config.ini` values, add force re-download via `last_downloaded_date`, add ZIP integrity verification after download, standardize on `Path.replace()`.
**Inputs:** `extract.py` (project root), `src/config_utils.py`
**Outputs:** `src/extract.py` (created); `extract.py` removed from project root; `config.ini` updated with `last_downloaded_date` on success
**External Interfaces:** `configparser` via `config_utils`; HTTP portal; `zipfile.is_zipfile()`
**Environment & Configuration:** `config.ini [settings]` provides `opendata_url`, `max_retries`, `retry_delay`, `log_level`
**Procedure:**
1. Create `src/` directory if absent.
2. Copy `extract.py` to `src/extract.py`.
3. Change `BASE_DIR` to `Path(__file__).resolve().parent.parent`.
4. At the top of `main()`, call `load_config(BASE_DIR / 'config.ini')` and read settings; read `force_from = config.get('state', 'last_downloaded_date', fallback='')`.
5. Extend `to_download` filter: schedule if `name not in existing OR (force_from and date_str >= force_from)`.
6. Replace `tmp.rename(dest_path)` with `tmp.replace(dest_path)` in `download_file()`.
7. After each successful download, verify with `zipfile.is_zipfile(dest_path)`. On failure: delete the file, log a warning, attempt re-download up to `max_retries` times.
8. After all successful downloads, call `save_state(config_path, last_downloaded_date=max_downloaded_date)`.
9. Delete `extract.py` from project root.
**Done Criteria:** `python src/extract.py` runs; `config.ini [state] last_downloaded_date` updated; ZIP integrity verified; `Path.replace()` used throughout; no `Path.rename()` calls remain.
**Dependencies:** Task 0
**Risk Notes:** ZIP integrity check adds one `is_zipfile()` call per download — negligible overhead.

### Task 2: Create src/transform.py — star-schema with dim_store, dim_file, quality report, logging
**Intent:** Write the transformation script that reads all ZIPs, builds seven dimension tables (including dim_store and dim_file) and date-partitioned fact CSVs (without fact_key), with per-ZIP progress logging, dimension writes after each ZIP, quality report output, log file via FileHandler, UTF-8 no BOM output, and SCD Type 1 semantics.
**Inputs:** `data/raw/*.zip`, nomenclature files, `config.ini`, `src/config_utils.py`
**Outputs:** `data/schema/dim_date.csv`, `dim_company.csv`, `dim_settlement.csv`, `dim_category.csv`, `dim_product.csv`, `dim_store.csv`, `dim_file.csv`; `data/schema/facts/YYYY-MM-DD.csv` (one per ZIP date); `data/quality/report_<YYYY-MM-DD>_<HHMMSS>.csv`; `logs/transform_YYYY-MM-DD_HHMMSS.log`; `config.ini [state] last_processed_date` updated
**External Interfaces:** `zipfile`, `csv`, `json`, `pathlib`, `datetime`, `configparser`, `logging` (all stdlib)
**Environment & Configuration:** `config.ini [settings]` for `log_level`; `[state]` for `last_processed_date`
**Procedure:**
1. Create `data/schema/`, `data/schema/facts/`, `data/quality/`, and `logs/` directories if absent.
2. Configure logging: `StreamHandler` for console + `FileHandler` for `logs/transform_YYYY-MM-DD_HHMMSS.log` (timestamp = script start time).
3. Load config; read `force_from = config.get('state', 'last_processed_date', fallback='')`.
4. Load existing dim dicts from CSVs (idempotency: preserve surrogate keys). This includes all 7 dims.
5. Load nomenclature dicts: primary `cities-ekatte-nomenclature.json` + secondary `sof_rai.json`; category `product-categories.json`.
6. Initialize quality counters dict: `{zip_date: {total_rows, null_prices, unknown_settlements, unknown_categories, delimiter_anomalies}}`.
7. Sort ZIPs in `data/raw/`. For each ZIP (with index for progress logging):
   a. Determine `date_str` from filename. Check skip condition: fact file exists AND (`force_from` is empty OR `date_str < force_from`). If skip, continue.
   b. If force re-process: delete existing fact file if present.
   c. For each CSV in the ZIP:
      - Auto-detect delimiter; count delimiter anomalies if semicolon detected.
      - Upsert `dim_file` for `(csv_name, date_str)`.
      - For each valid-column-count row:
        - Upsert dim entries: date, company, settlement, category, product.
        - Upsert `dim_store` for `(store_name, settlement_key, company_key)`.
        - Get `file_key` from dim_file.
        - Buffer fact row: `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price`.
        - Track quality counters: null prices, unknown settlements, unknown categories.
   d. Write fact rows to `facts/<date_str>.csv.partial` (encoding='utf-8'); `Path.replace()` to `.csv`.
   e. Write all 7 dimension CSVs atomically (`.partial` → `Path.replace()`; encoding='utf-8').
   f. Log progress: `INFO: Processed ZIP <i>/<total> (<date_str>) — <row_count> rows`.
8. Write quality report: `data/quality/report_<YYYY-MM-DD>_<HHMMSS>.csv` (encoding='utf-8') with one row per processed date.
9. Call `save_state(config_path, last_processed_date=max_processed_date)`.
**Done Criteria:** 7 dimension CSVs + 63 fact CSVs produced; fact CSVs have no `fact_key` column; `dim_store.csv` has `(store_key, store_name, settlement_key, company_key)` columns; `dim_file.csv` has `(file_key, file_name, zip_date)` columns; quality report written; log file written; all output CSVs are UTF-8 no BOM; dimensions written after each ZIP; progress logged per ZIP.
**Dependencies:** Tasks 0, 1
**Risk Notes:** Memory holds all dim dicts (small) + one date's fact rows at a time (~1.3M rows). dim_store grows to tens of thousands of entries but remains manageable.

### Task 3: Create refresh runner scripts (both .sh and .bat)
**Intent:** Create `refresh.sh` (Linux) and `refresh.bat` (Windows) ETL runner scripts at the project root.
**Inputs:** `src/extract.py`, `src/transform.py`
**Outputs:** `refresh.sh` and `refresh.bat` at project root
**External Interfaces:** Python interpreter via system PATH
**Environment & Configuration:** No hard-coded absolute paths
**Procedure:**
1. Write `refresh.sh`: `#!/bin/bash`, `set -e`, calls `python3 src/extract.py` then `python3 src/transform.py` with echo messages.
2. Run `chmod +x refresh.sh`.
3. Write `refresh.bat`: `@echo off`, calls `python src\extract.py || exit /b %ERRORLEVEL%` then `python src\transform.py || exit /b %ERRORLEVEL%`.
**Done Criteria:** `./refresh.sh` completes both steps without non-zero exit.
**Dependencies:** Tasks 1, 2
**Risk Notes:** Use `python3` in `.sh` and `python` in `.bat`.

### Task 4: Create interactive menu script and launchers
**Intent:** Create `menu.py` with statistics display and action menu; capture stderr in subprocess calls and include in error messages. Create `menu.sh`/`menu.bat` launchers.
**Inputs:** `data/raw/`, `data/schema/facts/`, `config.ini`
**Outputs:** `menu.py`, `menu.sh`, `menu.bat` at project root
**External Interfaces:** `pathlib`, `datetime`, `subprocess`, `sys`, `configparser` via `config_utils` (all stdlib)
**Environment & Configuration:** No secrets
**Procedure:**
1. Stats block: count ZIPs, fact CSVs, min/max dates, schema freshness, config state.
2. Numbered menu: 1) Download only, 2) Transform only, 3) Full refresh, 4) Exit.
3. Each action: `subprocess.run([sys.executable, 'src/extract.py'], check=True, capture_output=True, text=True)`. On success, print stdout. On `CalledProcessError`: print `e.stdout`, then print `e.stderr` with prefix "STDERR:" in the error message.
4. Loop until Exit.
5. Write `menu.sh`: `#!/bin/bash\nexec python3 menu.py "$@"`; `chmod +x`.
6. Write `menu.bat`: `@echo off\npython menu.py %*`.
**Done Criteria:** Menu shows correct stats; each action executes; stderr captured and displayed on error; Exit terminates cleanly.
**Dependencies:** Tasks 0, 1, 2, 3
**Risk Notes:** `capture_output=True` with `text=True` decodes stdout/stderr as strings. List-form subprocess prevents shell injection.

### Task 5: Update README.md
**Intent:** Revise `README.md` to document updated layout, all new scripts, `config.ini`, star-schema with dim_store/dim_file, SCD Type 1 strategy, quality report, UTF-8 no BOM, and removed fact_key.
**Inputs:** `README.md`, completed Tasks 0–4
**Outputs:** Updated `README.md`
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Update Usage section: replace `python extract.py` with `python src/extract.py`.
2. Add descriptions of `refresh.sh`/`refresh.bat` and `menu.py`/launchers.
3. Add Repository Structure section.
4. Add `config.ini` section with `[settings]`, `[state]`, and force re-run mechanism.
5. Document star-schema: all 7 dimensions + fact columns (no fact_key). Include dim_store and dim_file descriptions.
6. Document SCD strategy: explicitly state Type 1 — overwrite for all dimensions.
7. Document quality report: location, columns, usage.
8. Document UTF-8 no BOM for all output CSVs.
9. Add advisory note about DuckDB/pandas for querying.
**Done Criteria:** README accurately describes all components; SCD Type 1 documented; UTF-8 no BOM noted; no references to `extract.py` at root.
**Dependencies:** Tasks 0–4
**Risk Notes:** None

### Task 6: Smoke test end-to-end
**Intent:** Verify the complete pipeline runs correctly on the existing 63 ZIPs.
**Inputs:** All Tasks 0–5 complete, existing `data/raw/` ZIPs
**Outputs:** Populated `data/schema/`, populated `data/schema/facts/`, quality report, log file, updated `config.ini`
**External Interfaces:** None
**Environment & Configuration:** Active venv with requirements installed
**Procedure:**
1. Run `python src/transform.py`; confirm 7 dimension CSVs and 63 fact files are created.
2. Check `dim_store.csv` has reasonable row count (stores x settlements x companies observed).
3. Check `dim_file.csv` has ~13,100 rows.
4. Check fact files have 7 columns (no fact_key), include `store_key` and `file_key`.
5. Check quality report exists in `data/quality/`.
6. Check log file exists in `logs/`.
7. Check `config.ini [state] last_processed_date` is set.
8. Run `./refresh.sh`; confirm both steps complete.
9. Run `python menu.py`; verify statistics and exercise each menu item.
**Done Criteria:** All outputs exist with correct schemas; no unhandled exceptions.
**Dependencies:** Tasks 0–5
**Risk Notes:** Transformation processes ~82M rows — may take significant time.

### Task 7: Verify idempotency
**Intent:** Confirm re-running transform when no new ZIPs exist produces no changes.
**Inputs:** Populated `data/schema/` from Task 6
**Outputs:** No file changes
**External Interfaces:** None
**Procedure:**
1. Record SHA-1 hashes of all 7 dimension CSVs and 5 sampled fact CSVs.
2. Re-run `python src/transform.py`.
3. Compare hashes.
**Done Criteria:** All hashes match; config state unchanged.
**Dependencies:** Task 6

### Task 8: Data profile and quality validation
**Intent:** Validate data characteristics and quality report accuracy.
**Inputs:** Populated `data/schema/` and quality report from Task 6
**Outputs:** Console validation; no new files
**Procedure:**
1. Check `dim_settlement.csv` ~256 rows; `dim_category.csv` ≤ 118 rows.
2. Check `dim_store.csv` has valid store_name, settlement_key, company_key values.
3. Check `dim_file.csv` entries match actual ZIP contents.
4. Spot-check one fact file for correct store_key/file_key FK values, promo_price nullability, NULL retail_price rows.
5. Verify quality report CSVs: total_rows matches actual fact file row counts; null_prices/unknown_settlements/unknown_categories counts are plausible.
6. Verify no BOM in output CSVs (`hexdump -C <file> | head -1` should not show `ef bb bf`).
**Done Criteria:** All checks pass.
**Dependencies:** Task 6

## Testing

- T1 — extract.py relocation: Run `python src/extract.py` with network disabled. Expected outcome: Script starts, reads `config.ini`, logs its scrape URL, and fails gracefully with a network error (no `ModuleNotFoundError`, no path-resolution error).

- T2 — src/extract.py path resolution: Confirm `BASE_DIR` resolves to project root. Expected outcome: `BASE_DIR / 'data' / 'raw'` points to `<project_root>/data/raw`, not `<project_root>/src/data/raw`.

- T3 — transform.py creates schema: Delete `data/schema/` if it exists; run `python src/transform.py`. Expected outcome: `data/schema/` with 7 dimension CSVs and 63 fact CSVs created.

- T4 — dim_date.csv content: Inspect `dim_date.csv`. Expected outcome: Header `date_key,date,year,month,day,weekday`; rows contain valid integer keys and ISO dates matching ZIP filenames.

- T5 — dim_settlement.csv facts-driven: Inspect `dim_settlement.csv`. Expected outcome: ~256 rows (not 5,256). Unknown codes have `settlement_name` matching `(unknown:<code>)`.

- T6 — dim_store.csv content: Inspect `dim_store.csv`. Expected outcome: Header `store_key,store_name,settlement_key,company_key`; settlement_key and company_key values are valid integer FKs; no duplicate `(store_name, settlement_key, company_key)` triples.

- T7 — dim_file.csv content: Inspect `dim_file.csv`. Expected outcome: Header `file_key,file_name,zip_date`; ~13,100 rows; file_name entries match CSV filenames from ZIPs; zip_date entries match ZIP date range 2026-02-15 through 2026-04-18.

- T8 — fact file schema (no fact_key): Inspect a fact file header. Expected outcome: `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price` — exactly 7 columns, no `fact_key`, no `company_key`, no `settlement_key`, no `store_name`.

- T9 — fact file row count: Run `wc -l data/schema/facts/2026-02-15.csv`. Expected outcome: ~1,250,000–1,310,000 rows.

- T10 — Delimiter handling: Confirm semicolon-delimited company rows appear in fact files. Expected outcome: Fact files include rows from UICs 202935695, 823077024, 128614343.

- T11 — Idempotency: Run `python src/transform.py` twice; compare SHA-1 hashes of all dimension CSVs and 5 sampled fact CSVs. Expected outcome: All hashes identical.

- T12 — refresh.sh end-to-end: Run `./refresh.sh`. Expected outcome: Both steps complete without non-zero exit codes.

- T13 — menu statistics accuracy: Launch `python menu.py`; verify ZIP count, date range, config state. Expected outcome: Values match filesystem and `config.ini`.

- T14 — menu stderr capture: Launch `python menu.py`, trigger an action that fails (e.g., by temporarily making `src/extract.py` exit with error). Expected outcome: Error message includes captured stderr content.

- T15 — promo price nullability: Inspect a fact file. Expected outcome: `promo_price` column is empty for ~65% of rows.

- T16 — Unknown code handling: Inspect dim CSVs for unknown EKATTE/category codes. Expected outcome: `(unknown:<code>)` entries present with valid surrogate keys referenced in fact files.

- T17 — Non-parseable retail_price: Inspect fact file for known non-parseable price rows. Expected outcome: Rows appear with `retail_price` column empty (NULL).

- T18 — config.ini bootstrap: Delete `config.ini`; run `python src/extract.py`. Expected outcome: `config.ini` auto-created with defaults; no `FileNotFoundError`.

- T19 — config.ini state written: Run `python src/transform.py`. Expected outcome: `config.ini [state] last_processed_date` set to newest ZIP date.

- T20 — Force re-download: Set `last_downloaded_date = 2026-04-17`; run extract. Expected outcome: ZIPs for 2026-04-17 onward re-downloaded.

- T21 — Force re-process: Set `last_processed_date = 2026-04-17`; run transform. Expected outcome: Fact CSVs for 2026-04-17 onward re-generated; earlier files unchanged.

- T22 — save_state re-read: Run extract then transform in sequence. Expected outcome: `config.ini` has both `last_downloaded_date` and `last_processed_date` correctly set (transform did not overwrite download state).

- T23 — ZIP integrity check: Corrupt a ZIP file (truncate to 100 bytes). Run `src/extract.py` with force re-download for that date. Expected outcome: Corrupted ZIP detected by `is_zipfile()`, deleted, and re-downloaded.

- T24 — Per-ZIP progress logging: Run `python src/transform.py`; inspect console and log file output. Expected outcome: 63 progress messages in format `Processed ZIP <n>/63 (<date>) — <count> rows`.

- T25 — Quality report: Run `python src/transform.py`; inspect `data/quality/`. Expected outcome: Report CSV exists with 63 rows (one per date), columns `zip_date,total_rows,null_prices,unknown_settlements,unknown_categories,delimiter_anomalies`.

- T26 — Log file: Run `python src/transform.py`; inspect `logs/`. Expected outcome: Log file exists at `logs/transform_YYYY-MM-DD_HHMMSS.log` with full transform output.

- T27 — UTF-8 no BOM output: Inspect first bytes of any output CSV. Expected outcome: No BOM (`\xef\xbb\xbf`) present; file is valid UTF-8.

- T28 — Path.replace consistency: Grep `src/` for `Path.rename` or `.rename(`. Expected outcome: Zero occurrences; all atomic renames use `.replace()`.

- T29 — Dimension write after each ZIP: Start transform and kill after ~10 ZIPs; inspect `data/schema/`. Expected outcome: Dimension CSVs contain entries from the processed ZIPs (not empty or stale).

- T30 — config atomic write safety: Kill transform mid-run; inspect `config.ini`. Expected outcome: No `.partial` orphan; `config.ini` is valid.

## Documentation

- `README.md` (ref_id: N/A) — Update Usage section for `src/extract.py`; add descriptions of all scripts; add `config.ini` documentation; document star-schema with 7 dimensions (including dim_store, dim_file); document SCD Type 1 strategy; document quality report; document UTF-8 no BOM; document removed fact_key; add DuckDB/pandas advisory.

- `.aib_memory/context.md` (ref_id: REF-0001) — Must be regenerated after implementation to reflect the final system state including dim_store, dim_file, quality report, log file, updated fact schema, and all other changes.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `extract.py` | Deleted | Moved to `src/extract.py`; original at project root removed |
| `src/` | Created | New source folder for Python scripts |
| `src/extract.py` | Created | Relocated download utility; `BASE_DIR` adjusted; config integration; ZIP integrity check; `Path.replace()` standardised |
| `src/transform.py` | Created | Star-schema transformation: 7 dims (incl. dim_store, dim_file), no fact_key, per-ZIP progress logging, dims after each ZIP, quality report, FileHandler logging, UTF-8 no BOM, SCD Type 1 |
| `src/config_utils.py` | Created | `load_config()` (bootstrap) and `save_state()` (re-read + atomic write via `Path.replace()`) |
| `config.ini` | Created | Central config: `[settings]` + `[state]` with re-read-before-write semantics |
| `refresh.sh` | Created | Linux ETL runner |
| `refresh.bat` | Created | Windows ETL runner |
| `menu.py` | Created | Interactive menu with stderr capture in subprocess calls |
| `menu.sh` | Created | Linux menu launcher |
| `menu.bat` | Created | Windows menu launcher |
| `data/schema/` | Created | Star-schema output directory |
| `data/schema/dim_date.csv` | Created | Date dimension |
| `data/schema/dim_company.csv` | Created | Company dimension |
| `data/schema/dim_settlement.csv` | Created | Settlement dimension (~256 rows, facts-driven) |
| `data/schema/dim_category.csv` | Created | Category dimension (≤118 rows, facts-driven) |
| `data/schema/dim_product.csv` | Created | Product dimension |
| `data/schema/dim_store.csv` | Created | Store dimension (store_name, settlement_key, company_key) — normalises fact table |
| `data/schema/dim_file.csv` | Created | File dimension (file_name, zip_date) — data lineage tracking |
| `data/schema/facts/` | Created | Partitioned fact table folder |
| `data/schema/facts/YYYY-MM-DD.csv` | Created (x63) | Date-partitioned fact files; 7 columns (no fact_key); store_key and file_key FKs |
| `data/quality/` | Created | Quality report output directory |
| `data/quality/report_*.csv` | Created | Per-run quality report: per-date counts of total rows, null prices, unknown settlements, unknown categories, delimiter anomalies |
| `logs/transform_*.log` | Created | Per-run transform log file via FileHandler |
| `README.md` | Modified | Updated for new layout, all scripts, config, 7-dim schema, SCD Type 1, quality report, UTF-8 no BOM |
| `requirements.txt` | Read-only dependency | No new runtime dependencies |
| `data/nomenclatures/cities-ekatte-nomenclature.json` | Read-only dependency | Settlement name resolution |
| `data/nomenclatures/product-categories.json` | Read-only dependency | Category name resolution |
| `data/nomenclatures/Ekatte/sof_rai.json` | Read-only dependency | Sofia sub-district secondary EKATTE source |
| `data/raw/*.zip` | Read-only dependency | Source data; re-downloaded only on force override or integrity failure |

## Internal Review of Request and Product Docs

- Omission (noted): `request.md § Scope` (human section, not modified) describes original 6-dimension schema with `store_name` in fact table and `fact_key` column. The AI sections (Plan, Code Scan) carry the updated 7-dimension schema with `dim_store`, `dim_file`, no `fact_key`. This is a known discrepancy between the human-authored Scope and the AI-generated Plan driven by `input.md` items.

- Omission (noted): `request.md § Scope` does not mention quality report, per-ZIP progress logging, log file, ZIP integrity check, or SCD Type 1. These are new scope items from `input.md` incorporated into the AI sections only.

- Omission (noted): `request.md § Out of scope` lists "ZIP content validation" — the new ZIP integrity check (`is_zipfile()`) partially overlaps this exclusion. However, `is_zipfile()` is a download-phase integrity check (verifying the container), not content validation (verifying CSV data within). The distinction is: integrity = "is this a valid ZIP file?" vs. validation = "is the data inside correct?". The former is now in scope per `input.md`; the latter remains out of scope.

- OK: `request.md` six mandatory sections (Goal through Success criteria) remain intact and non-empty.

- OK: `references.md` — two entries; `context.md` (product-doc) read in full; `Concepts.md` (domain) read in full.

- OK: `python-dotenv` remains in `requirements.txt` but is unused. Harmless orphan; no action required.

- Missing info: `config.ini` VCS strategy not specified. Assumption A11 documents the single-file trade-off.

- Cross-ref note: `context.md` was regenerated in prior run (fifth) to reflect post-implementation state. After this implementation (with dim_store, dim_file, etc.), `context.md` will need another regeneration to capture the final state.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The addition of `dim_store` and `dim_file` strengthens the dimensional model significantly. `dim_store` eliminates the denormalized `store_name` string from ~82M fact rows — a major space and consistency improvement. The partial snowflake trade-off (fact → dim_store → dim_settlement/dim_company) is acceptable given that store-level analysis is the primary new use case, and settlement/company queries can join through dim_store with minimal overhead. `dim_file` adds data lineage capability that is invaluable for debugging data quality issues.

- Removing `fact_key` saves ~656 MB with no analytical loss — fact surrogates are not needed when the table is date-partitioned and rows are FK-addressable.
- Writing dimensions after each ZIP provides crash resilience without meaningful I/O overhead.
- `save_state()` re-read pattern correctly addresses the sequential-pipeline state overwrite bug.
- `Path.replace()` standardisation fixes a latent Windows compatibility issue.
- Risk: the partial snowflake requires an extra join for settlement/company queries. Acceptable for the project scale; document the join pattern in README.

### Product Owner

The 13 new scope items deliver substantial operational and analytical improvements. The quality report provides immediate data governance visibility without adding dependencies. Per-ZIP progress logging makes long-running transforms observable. The dim_store dimension enables a new analysis axis (store-level price tracking) that was previously impossible. UTF-8 no BOM standardisation eliminates encoding ambiguity for downstream consumers.

- SCD Type 1 is the correct choice for the current project scope — no historical dimension tracking is needed. Documenting this explicitly sets correct expectations for analysts.
- ZIP integrity check addresses a real operational risk (silent corruption during download).
- The log file provides persistent run diagnostics for post-hoc debugging.
- Risk: 13 new items increase implementation complexity. The plan maintains ≤9 tasks by incorporating new items into existing tasks where they naturally fit.

### User

From the operator's perspective, per-ZIP progress logging is the highest-impact improvement — it transforms the transform script from a silent black box into an observable process. The quality report provides a one-file summary of data health. The log file means the operator doesn't need to scroll terminal history to diagnose a failure.

- `dim_store` removes the repeated store name string from fact files, making them smaller and faster to load in spreadsheet tools.
- `dim_file` enables answering "which source file did this data come from?" — useful when investigating data anomalies.
- ZIP integrity check prevents silently processing corrupted downloads.
- UTF-8 no BOM simplifies downstream tool compatibility.

### Security Officer

No new security surface is introduced by the 13 items. All new dimensions and reports are derived from the same public government data already in the pipeline.

- `zipfile.is_zipfile()` reads only file header bytes — no decompression-based attacks (ZIP bombs) are triggered at the validation stage.
- Quality report contains aggregate counts only — no PII, no sensitive data.
- Log files may contain file paths and error messages — ensure no sensitive data leaks into error traces (currently none; all data is public).
- `subprocess.run()` with `capture_output=True` captures stderr as bytes/string — no shell injection risk (list-form invocation preserved).
- No new network connections, no new authentication, no new credential storage.

### Data Governance Officer

The new items significantly improve data governance posture. `dim_file` provides complete data lineage: every fact row can be traced to its source file and ZIP date. The quality report formalises data quality monitoring with per-date metrics. SCD Type 1 documentation clarifies the dimension change policy for compliance and audit purposes.

- Quality report columns (null_prices, unknown_settlements, unknown_categories, delimiter_anomalies) cover the key data quality indicators for this dataset.
- UTF-8 no BOM standardisation ensures consistent encoding across all output artifacts — eliminates a common interoperability issue.
- `dim_store` normalisation reduces data redundancy, improving consistency (store attributes are maintained in one place).
- Risk: SCD Type 1 means historical dimension values are lost on update. If regulatory requirements later mandate historical tracking, a migration to Type 2 would be needed. Current assessment: not required for publicly mandated retail price data.
