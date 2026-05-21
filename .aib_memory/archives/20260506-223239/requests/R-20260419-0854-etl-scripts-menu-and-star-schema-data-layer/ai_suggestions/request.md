## Goal

Add an ETL runner script and an interactive menu script to the project root, move `extract.py` from the project root into a new `src/` folder, and build a star-schema data layer under `data/schema/` by parsing and transforming the raw ZIP archives already accumulated in `data/raw/`. The goal is to give the team a one-click ETL trigger, an interactive statistics/action menu, a clean source layout, and a persistently queryable human-readable structured dataset — all without modifying the existing download logic or removing any raw data.

## Background

The project currently contains only a standalone download utility (`extract.py`) at the project root. Raw daily retail-price ZIP archives accumulate in `data/raw/` (63 ZIPs as of 2026-04-19, covering 2026-02-15 through 2026-04-18). Each ZIP contains up to ~200 CSV files, one per reporting retail company (named `<CompanyName>_<UIC>.csv`), with columns: settlement EKATTE code, store name, product name, product code, category code, retail price, and promotional price.

Supporting nomenclature files are available: `data/nomenclatures/cities-ekatte-nomenclature.json` (EKATTE → settlement name mapping) and `data/nomenclatures/product-categories.json` (category id → name list). These enrich the raw data during transformation.

There is no structured pipeline runner, no transformation script, and no dimensional model. A developer must manually run `extract.py`, inspect the raw ZIPs to understand what data is available, and write ad-hoc code to query prices. This request introduces the missing transformation layer and operational scripts.

## Scope

- Create both `refresh.sh` (Linux shell) and `refresh.bat` (Windows batch) runner scripts at the project root; each runs the complete ETL pipeline (download + transformation) in sequence.

- Create a `menu.py` Python script at the project root that launches an interactive terminal session showing statistics (available date range, ZIP count, schema freshness, last downloaded and last processed dates from `state.ini`) and a numbered menu for manual invocation of individual actions (download, transform, or a combined refresh). Create both `menu.sh` (Linux) and `menu.bat` (Windows) one-line launcher scripts at the project root that invoke `python menu.py`.

- Create a `src/` folder and move `extract.py` into it as `src/extract.py`; update all internal path references so the script remains runnable from the project root.

- Create a `data/schema/` folder and populate it with a star-schema dataset in CSV format, derived from all ZIPs in `data/raw/`:
  - `dim_date.csv` — date surrogate key, ISO date, year, month, day, weekday.
  - `dim_company.csv` — company surrogate key, UIC (from filename), company name (from filename).
  - `dim_settlement.csv` — settlement surrogate key, EKATTE code, settlement name (from nomenclature); facts-driven (~256 rows).
  - `dim_category.csv` — category surrogate key, category numeric code, category name (from nomenclature); facts-driven.
  - `dim_product.csv` — product surrogate key, product code, normalized product name, raw product name.
  - `dim_store.csv` — store surrogate key, store name, settlement_key, company_key.
  - `data/schema/facts/YYYY-MM-DD.csv` — date-partitioned fact files. Columns: `date_key, company_key, store_key, settlement_key, category_key, product_key, retail_price, promo_price` (nullable). No fact surrogate key.

- Create a `config.ini` file at the project root containing a `[settings]` section (user-tunable: `opendata_url`, `max_retries`, `retry_delay`, `log_level`). This file is VCS-tracked and contains only human-editable settings.

- Create a `state.ini` file (git-ignored) at the project root containing a `[state]` section (script-managed: `last_downloaded_date`, `last_processed_date`). Both scripts write back their respective state key on successful completion. State file is bootstrapped automatically on first run if absent. Setting `last_downloaded_date` to an earlier date triggers force re-download of ZIPs from that date onward; setting `last_processed_date` triggers re-processing of fact files from that date onward.

- Create `src/config_utils.py` with shared helpers: `load_config(config_path, state_path)`, `save_state(state_path, **kwargs)`. Both use atomic `.partial` → `Path.replace()` writes.

- After each transform run, write `data/schema/manifest.json` containing: run timestamp, row counts per fact file, dimension table sizes, processing duration, and data quality summary (NULL price count, unknown settlement count, unknown category count per date).

- Update `.gitignore` to include: `state.ini`, `data/schema/`, `data/raw/`, `*.partial`.

- Update `README.md` to document the new folder structure, the new scripts, `config.ini` and `state.ini` parameters, SCD policy, state tracking, re-run mechanism, output encoding (UTF-8 no BOM), and the advisory DuckDB note.

## Out of scope

- Cloud sync, database upload, dashboarding, or API exposure.
- Modifying the download logic of `extract.py` beyond path adjustments needed by the move.
- Automated scheduling (cron on Linux; Task Scheduler on Windows).
- ZIP content validation beyond column count and basic format checks.
- Deleting, archiving, or compressing existing raw ZIPs in `data/raw/`.
- Adding a full automated test suite (basic smoke tests are sufficient).
- Any CI/CD pipeline configuration.
- Parallel/multi-process ZIP transformation.

## Constraints

- Python 3.9+ compatibility must be maintained for all new scripts.
- The star-schema CSV files must be human-readable (no binary formats such as Parquet or Avro) and space-efficient (integer surrogate keys; no repeated string values in the fact table).
- New Python dependencies are allowed only if pip-installable without compilation; they must be added to `requirements.txt`.
- The content of `data/raw/` must not be altered, deleted, or compressed.
- Both `.sh` (Linux-native) and `.bat` (Windows-compatible) variants of the runner (`refresh`) and menu launcher scripts must be created; each variant invokes the same underlying Python scripts and produces identical ETL outcomes.
- `extract.py` internal relative path `BASE_DIR` resolves paths relative to the script's own location; relocation must preserve this resolution.
- No secrets or credentials may be introduced; the project has no authentication requirements.
- All output CSVs written as UTF-8 without BOM.

## Success criteria

- Running the refresh script from the project root completes without error, downloads any new ZIPs, and produces or updates all files in `data/schema/`.
- Running the menu script presents a readable readout of statistics (available dates, count, schema state) and a menu with at least three actions; each action executes correctly when selected.
- `src/extract.py` is the sole location of the download script; the project root no longer contains `extract.py`.
- `data/schema/` contains all seven dimension/fact CSV files with correct headers and at least one data row per file.
- Re-running the refresh script when no new ZIPs exist is idempotent: dimension tables are unchanged (byte-identical), fact files contain no duplicate rows.
- `README.md` accurately describes the updated folder structure and new scripts.
- Crash recovery: if transform is interrupted, re-running it produces correct output (no orphaned surrogate keys referencing stale dimension files).
- `data/schema/manifest.json` exists after each transform run with valid row counts and quality stats.

## Assumptions

- A1: Both `.sh` (Linux) and `.bat` (Windows) runner and menu launcher scripts will be created. The `.sh` scripts are the primary development target (Linux OS); `.bat` scripts are provided for Windows compatibility.

- A2: `extract.py` will be runnable from the project root via `python src/extract.py` after relocation; no packaging or installation step is required.

- A3: All ZIPs in `data/raw/` follow the naming pattern `YYYY-MM-DD.zip`. Internal CSVs use either comma or semicolon delimiters; all share the same 7-column Bulgarian header. UTF-8 with optional BOM encoding.
  - Risk if false: Malformed ZIPs or changed column layouts would produce silent data loss; a header-validation guard is required.

- A4: `dim_settlement` is built from the set of EKATTE codes observed in the raw data (facts-driven, ~256 rows). Primary lookup: `cities-ekatte-nomenclature.json`. Secondary lookup: `sof_rai.json` (38 Sofia sub-district `68134-XX` codes). Unresolved codes receive `settlement_name = "(unknown:<ekatte_code>)"`. All rows retained in facts.
  - Risk if false: If full settlement coverage is required, a full-registry load strategy is needed.

- A5: The fact table is date-partitioned: `data/schema/facts/YYYY-MM-DD.csv` (~54–78 MB/file). No fact surrogate key (composite natural key is sufficient for analytical workloads).
  - Risk if false: If a single flat fact table is required, a size vs usability trade-off must be accepted.

- A6: Product codes are retailer-local identifiers, not globally unique. The unique granularity for `dim_product` is the pair `(product_code, normalized_product_name)`. Normalization: `name.strip().lower()` + collapsed whitespace + NFC Unicode normalization. The raw (original) name is stored alongside for display.
  - Risk if false: If the portal enforces globally unique product codes, the composite key is redundant but harmless.

- A7: No new pip packages are needed beyond the existing `requirements.txt`. All transformation and config logic uses Python stdlib.

- A8: Dimension CSVs are written after **each ZIP's fact file** is completed (not just at the end of the full run). This ensures crash recovery correctness — if the process crashes at ZIP N, re-running from ZIP N finds valid dimension CSVs matching all prior fact files.
  - Risk if false: A deferred-write strategy would require a dimension write-ahead log for crash safety.

- A9: `store_name` is promoted to a `dim_store` dimension table keyed on `(store_name, settlement_key, company_key)`. This normalizes the fact table (replacing ~82M string repetitions with integer keys) and enables store-level analytical queries.
  - Risk if false: If store-level analysis is not needed, `store_name` can remain as a degenerate dimension in the fact table.

- A10: `category_key` is included as a foreign key in the fact table. `dim_category` is built facts-driven. Unknown category codes receive `category_name = "(unknown:<code>)"`.

- A11: Settings and state are split into two files: `config.ini` (VCS-tracked, human-edited settings) and `state.ini` (git-ignored, machine-written checkpoints). This eliminates VCS diff noise and reduces accidental state corruption.

- A12: Scripts bootstrap default `config.ini` and `state.ini` on first run if either is absent. Zero-configuration first-run behaviour.

- A13: SCD policy is Type 1 (overwrite) for all dimension attributes. Company names, product names, and settlement names are overwritten with the most recently observed value. No historical tracking of dimension attribute changes.
  - Risk if false: If historical dimension tracking is needed, Type 2 SCD with effective dates is required — significant design change.

- A14: Force re-process comparison uses `>=` (inclusive lower bound). Setting `last_processed_date = 2026-04-17` re-processes both 2026-04-17 and 2026-04-18 (all dates from the checkpoint onward).

## Plan

### Task 0: Create config.ini, state.ini, and config_utils.py
**Intent:** Create the configuration layer: `config.ini` (settings), `state.ini` (ETL state), and a shared Python helper module.
**Inputs:** None (new files)
**Outputs:** `config.ini`, `state.ini`, `src/config_utils.py`, `tests/test_config_utils.py`
**Procedure:**
1. Create `config.ini`:
   ```ini
   [settings]
   opendata_url = https://kolkostruva.bg/opendata
   max_retries = 3
   retry_delay = 10
   log_level = INFO
   ```
2. Create `state.ini`:
   ```ini
   [state]
   ; Written by scripts on successful completion. Set to an earlier date to force re-run.
   last_downloaded_date =
   last_processed_date =
   ```
3. Create `src/config_utils.py` with:
   - `load_config(config_path, state_path)`: reads both files; bootstraps defaults if absent; returns `(config, state)` tuple.
   - `save_state(state_path, **kwargs)`: re-reads `state.ini` immediately before writing (avoids race condition with concurrent scripts), updates keys from kwargs, writes to `.partial`, then `Path.replace()`.
4. Write unit tests in `tests/test_config_utils.py`.
5. Update `.gitignore` to add `state.ini`, `*.partial`.
**Done Criteria:** Both files exist; `config_utils.py` passes tests; missing-file bootstrap confirmed.
**Dependencies:** None

### Task 1: Move extract.py to src/ and integrate config
**Intent:** Relocate `extract.py` to `src/extract.py`, fix `BASE_DIR`, replace hardcoded constants with config values, add force re-download logic.
**Inputs:** `extract.py` (project root), `src/config_utils.py`
**Outputs:** `src/extract.py` (created); `extract.py` removed from project root; `state.ini` updated on success
**Procedure:**
1. Create `src/` directory if absent.
2. Copy `extract.py` to `src/extract.py`.
3. Change `BASE_DIR` to `Path(__file__).resolve().parent.parent`.
4. At the top of `main()`, call `load_config()` and read settings from `config.ini`, state from `state.ini`.
5. Extend `to_download` filter: schedule if `name not in existing OR (force_from and date_str >= force_from)`.
6. After successful downloads, call `save_state(state_path, last_downloaded_date=max_downloaded_date)`.
7. Add file-based logging: `FileHandler` writing to `logs/extract_YYYY-MM-DD_HHMMSS.log`.
8. Delete `extract.py` from project root.
**Done Criteria:** `python src/extract.py` runs from project root; `state.ini` updated after run; force re-download works.
**Dependencies:** Task 0

### Task 2: Create src/transform.py — star-schema transformation
**Intent:** Write a transformation script that reads all `data/raw/*.zip`, builds seven dimension tables and date-partitioned fact CSVs under `data/schema/`, with crash-safe dimension writes and data quality reporting.
**Inputs:** `data/raw/*.zip`, nomenclature files, `config.ini`, `state.ini`, `src/config_utils.py`
**Outputs:** `data/schema/dim_*.csv` (6 dimension tables), `data/schema/facts/YYYY-MM-DD.csv`, `data/schema/manifest.json`
**Procedure:**
1. Create `data/schema/` and `data/schema/facts/` if absent.
2. Load config and state via `config_utils`.
3. Load existing dimension CSVs (preserve stable surrogate keys) into memory dicts.
4. Load nomenclature dicts (EKATTE + sof_rai.json + product-categories.json).
5. For each ZIP in sorted `data/raw/`:
   a. Skip if fact file exists AND no force-reprocess trigger applies.
   b. For each CSV in the ZIP:
      - Auto-detect delimiter (comma vs semicolon fallback).
      - Validate column count (7). Log and skip malformed rows.
      - Normalize product name: `name.strip().lower()`, collapse whitespace, NFC normalization.
      - Upsert all dimension entries (date, company, settlement, category, product, store).
      - Parse `retail_price` (NULL if non-parseable); parse `promo_price` (NULL if empty).
      - Buffer fact rows.
   c. Write fact CSV to `facts/<date>.csv.partial` → rename.
   d. **Write all dimension CSVs atomically after each ZIP** (crash safety — ensures dims match facts on disk).
   e. Collect quality stats: total rows, NULL prices, unknown settlements, unknown categories.
   f. Log progress: `INFO: Processing ZIP 14/63 (2026-03-02) — 1,119,243 rows`.
6. Write `data/schema/manifest.json` with run metadata and per-date quality stats.
7. Call `save_state(state_path, last_processed_date=max_processed_date)`.
**Done Criteria:** 6 dim CSVs + 63 fact CSVs produced; `dim_settlement` ~256 rows; `dim_store` populated; no `fact_key` column; manifest.json valid; crash at any ZIP leaves consistent state.
**Dependencies:** Tasks 0, 1

### Task 3: Create refresh runner scripts
**Intent:** Create `refresh.sh` (Linux) and `refresh.bat` (Windows) at project root.
**Inputs:** `src/extract.py`, `src/transform.py`
**Outputs:** `refresh.sh`, `refresh.bat`
**Procedure:**
1. Write `refresh.sh`:
   ```sh
   #!/bin/bash
   set -e
   echo "[refresh] Step 1: Downloading new ZIPs..."
   python3 src/extract.py
   echo "[refresh] Step 2: Building star-schema..."
   python3 src/transform.py
   echo "[refresh] Done."
   ```
2. `chmod +x refresh.sh`.
3. Write `refresh.bat` with equivalent Windows batch.
**Done Criteria:** `./refresh.sh` completes both steps without error.
**Dependencies:** Tasks 1, 2

### Task 4: Create interactive menu script and launchers
**Intent:** Create `menu.py` with ETL statistics display, `state.ini` status, and action menu.
**Inputs:** `data/raw/`, `data/schema/facts/`, `config.ini`, `state.ini`
**Outputs:** `menu.py`, `menu.sh`, `menu.bat`
**Procedure:**
1. Stats block: ZIP count, date range, fact CSV count, newest fact date, freshness delta, `state.ini` values.
2. Numbered menu: 1) Download only, 2) Transform only, 3) Full refresh, 4) Exit.
3. Use `subprocess.run([sys.executable, 'src/extract.py'], check=False)` — inspect returncode and print a meaningful error on failure rather than raising `CalledProcessError`.
4. Loop until Exit.
5. Write `menu.sh` and `menu.bat` launchers.
**Done Criteria:** Menu shows correct stats; each action executes; Exit is clean.
**Dependencies:** Tasks 0–3

### Task 5: Update README.md and .gitignore
**Intent:** Document new structure, scripts, config/state split, SCD policy, output encoding, and DuckDB advisory.
**Inputs:** Completed Tasks 0–4
**Outputs:** Updated `README.md`, updated `.gitignore`
**Procedure:**
1. Update Repository Structure section.
2. Document `config.ini` (settings) and `state.ini` (state) — separate files, separate purposes.
3. Document force re-run mechanism.
4. Document SCD Type 1 policy.
5. Document output encoding: UTF-8 without BOM.
6. Document `dim_store` and fact table schema (no `fact_key`).
7. Add DuckDB advisory note.
8. Update `.gitignore`: `state.ini`, `data/schema/`, `data/raw/`, `*.partial`, `logs/*.log`.
**Done Criteria:** README accurately describes all components; `.gitignore` updated.
**Dependencies:** Tasks 0–4

### Task 6: Smoke test end-to-end
**Intent:** Verify the complete pipeline on existing 63 ZIPs.
**Procedure:**
1. Run `python src/transform.py`; confirm 6 dim CSVs and 63 fact files created.
2. Check `dim_settlement.csv` ~256 rows; `dim_store.csv` populated; `dim_product.csv` uses normalized names.
3. Check fact files have no `fact_key` column; include `store_key`.
4. Check `state.ini [state] last_processed_date` is set.
5. Verify `manifest.json` exists with valid content.
6. Run `./refresh.sh`; confirm both steps complete.
7. Run `python menu.py`; verify statistics and exercise each menu item.
**Done Criteria:** All CSVs valid; state populated; manifest present.
**Dependencies:** Tasks 0–5

### Task 7: Verify idempotency and crash recovery
**Intent:** Confirm re-run produces byte-identical output; verify crash recovery correctness.
**Procedure:**
1. Record SHA-256 hashes of all dim CSVs and 5 sampled fact CSVs.
2. Re-run `python src/transform.py`.
3. Compare hashes — all must match.
4. Simulate crash: delete the last 3 fact CSVs and re-run. Verify only those 3 are regenerated; all dim CSVs remain valid; no surrogate key corruption.
**Done Criteria:** Byte-identical on full re-run; correct recovery on simulated crash.
**Dependencies:** Task 6

### Task 8: Data profile validation
**Intent:** Confirm profiled data characteristics are reflected in schema outputs.
**Procedure:**
1. Verify `dim_settlement.csv` ~256 rows with `(unknown:<code>)` entries.
2. Verify `dim_category.csv` ≤ 118 entries.
3. Verify fact file for 2026-02-15 has ~1.28M rows.
4. Verify ~35% promo_price fill rate, ~65% NULL.
5. Verify NULL retail_price for non-parseable rows (not absent).
6. Verify semicolon-delimited company rows are included (UICs 202935695, 823077024, 128614343).
**Done Criteria:** All checks pass within 5% tolerance.
**Dependencies:** Task 6

## Testing

- T1 — extract.py relocation: Run `python src/extract.py` with network disabled. Expected: starts, reads config, fails gracefully with network error.
- T2 — path resolution: `RAW_DIR` ends with `/data/raw` relative to project root, not `/src/data/raw`.
- T3 — transform creates schema: Delete `data/schema/`; run transform. Expected: 6 dim CSVs + 63 fact CSVs created.
- T4 — dim_date content: Header is `date_key,date,year,month,day,weekday`; valid ISO dates.
- T5 — dim_settlement facts-driven: ~256 rows; 18 unknown codes with `(unknown:<code>)`.
- T6 — dim_store populated: Contains unique `(store_name, settlement_key, company_key)` tuples.
- T7 — fact file row count: 2026-02-15.csv between 1,250,000 and 1,310,000 rows.
- T8 — no fact_key column: Fact CSVs start with `date_key`, not `fact_key`.
- T9 — delimiter handling: Fact files include rows from UICs 202935695, 823077024, 128614343.
- T10 — idempotency: Two sequential runs produce byte-identical dim CSVs and fact CSVs.
- T11 — crash recovery: Delete last 3 fact CSVs; re-run; only those 3 regenerated; dims valid.
- T12 — refresh.sh end-to-end: Both steps complete with zero exit code.
- T13 — menu statistics: ZIP count, date range, and state values match filesystem/state.ini.
- T14 — menu exit: Clean exit code 0.
- T15 — promo_price nullability: ~65% NULL, ~35% filled.
- T16 — unknown code handling: dim CSVs have valid surrogate keys; fact rows reference them.
- T17 — non-parseable retail_price: Rows appear with empty retail_price, not absent.
- T18 — config bootstrap: Delete `config.ini` and `state.ini`; run extract. Both bootstrapped.
- T19 — state written after success: `state.ini [state] last_processed_date` set to newest date.
- T20 — force re-download: Set `last_downloaded_date = 2026-04-17`; verify re-download of 04-17 and 04-18.
- T21 — force re-process: Set `last_processed_date = 2026-04-17`; verify re-generation of 04-17 and 04-18 fact CSVs; earlier files unchanged.
- T22 — manifest.json: Valid JSON; per-date row counts and quality stats present.
- T23 — product name normalization: Verify `dim_product` uses normalized names as key component; raw names stored separately.
- T24 — progress logging: Console output shows `Processing ZIP N/63` messages during transform.

## Documentation

- `README.md` — Update for new structure, config/state split, schema columns, DuckDB advisory.
- `.gitignore` — Add `state.ini`, `data/schema/`, `data/raw/`, `*.partial`, `logs/*.log`.

## Questions & Decisions

(No open questions — all decisions documented in Assumptions.)

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `extract.py` | Deleted | Moved to `src/extract.py` |
| `src/` | Created | New source folder |
| `src/extract.py` | Created | Relocated; `BASE_DIR` adjusted; config integration; force re-download |
| `src/transform.py` | Created | Star-schema transformation with crash-safe dim writes |
| `src/config_utils.py` | Created | Shared config/state helpers with race-condition-safe state writes |
| `config.ini` | Created | User-tunable settings only (VCS-tracked) |
| `state.ini` | Created | Machine-written ETL state (git-ignored) |
| `refresh.sh` | Created | Linux ETL runner |
| `refresh.bat` | Created | Windows ETL runner |
| `menu.py` | Created | Interactive menu with improved error display |
| `menu.sh` | Created | Linux menu launcher |
| `menu.bat` | Created | Windows menu launcher |
| `data/schema/` | Created | Star-schema output directory |
| `data/schema/dim_date.csv` | Created | Date dimension |
| `data/schema/dim_company.csv` | Created | Company dimension |
| `data/schema/dim_settlement.csv` | Created | Settlement dimension (~256 rows, facts-driven) |
| `data/schema/dim_category.csv` | Created | Category dimension |
| `data/schema/dim_product.csv` | Created | Product dimension with normalized + raw names |
| `data/schema/dim_store.csv` | Created | **New** store dimension (normalizes fact table) |
| `data/schema/facts/YYYY-MM-DD.csv` | Created (×63) | Date-partitioned facts; no `fact_key`; includes `store_key` |
| `data/schema/manifest.json` | Created | **New** run metadata and quality stats |
| `.gitignore` | Modified | Add `state.ini`, `data/schema/`, `data/raw/`, `*.partial` |
| `README.md` | Modified | Full documentation update |
| `tests/test_config_utils.py` | Created | Smoke tests for config/state helpers |
