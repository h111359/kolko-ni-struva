# Analysis: R-20260419-0854 — ETL scripts, menu, and star-schema data layer

> Re-run: 2026-04-20 (sixth run). New scope from `input.md`: dim_store dimension, dim_file dimension, quality report output, per-ZIP progress logging, ZIP integrity check, log file (FileHandler), fact_key removal, SCD Type 1 documentation, dimension CSVs written after each ZIP, save_state() re-read config, standardize on Path.replace(), capture stderr in subprocess, UTF-8 no BOM for output CSVs. All prior analysis findings (config.ini, data-profile, delimiter detection, facts-driven dimensions) remain authoritative and carried forward.

## Executive Summary

- **Request ID:** R-20260419-0854

- **Title:** ETL scripts, menu, and star-schema data layer

- **High-level purpose:** Build a complete ETL pipeline for the kolkostruva.bg daily retail-price dataset: relocate `extract.py` to `src/`, create `src/transform.py` to produce a star-schema data layer under `data/schema/`, provide operator tooling (`menu.py`, `refresh.sh`/`.bat`), and centralise configuration in `config.ini`.

- **New scope this run (input.md — 13 items):**
  1. `dim_store` dimension — extract `(store_name, settlement_key, company_key)` into `dim_store.csv`; replace `store_name`, `settlement_key`, `company_key` in the fact table with a single `store_key` FK.
  2. Quality report — write `data/quality/report_<YYYY-MM-DD>_<HHMMSS>.csv` after each transform run with per-date quality metrics.
  3. Per-ZIP progress logging — `INFO: Processed ZIP 14/63 (2026-03-02) — 1,119,243 rows` format.
  4. `dim_file` dimension — track every CSV file within every ZIP; attributes: file name, zip date.
  5. ZIP integrity check — verify downloaded ZIPs with `zipfile.is_zipfile()`; delete and re-download on failure.
  6. Log file — add `FileHandler` writing to `logs/transform_YYYY-MM-DD_HHMMSS.log`.
  7. `fact_key` removal — drop the surrogate key column from fact CSVs to save ~656 MB.
  8. SCD Type 1 — document overwrite strategy explicitly for all dimensions.
  9. Write dimension CSVs after each ZIP's fact file, not only at the end.
  10. `save_state()` re-read — re-read `config.ini` before writing state, not use startup-cached object.
  11. Standardize on `Path.replace()` — replace all `Path.rename()` calls.
  12. Capture stderr — in `menu.py` subprocess calls, capture stderr and include in error messages.
  13. UTF-8 no BOM — write all output CSVs as `utf-8` (no BOM); document in README.

- **Carried scope (unchanged):** Q001 resolved (both `.sh` and `.bat`). `config.ini` with `[settings]` + `[state]`. Force re-download/re-process via state overrides. Category dimension (`dim_category`) in fact table. Date-partitioned fact files. Unknown codes receive `(unknown:<code>)` placeholder entries. Non-parseable `retail_price` stored as NULL.

- **Current workspace state (actual):** `extract.py` at project root; no `src/`; no `data/schema/`; no `config.ini`. 63 ZIPs in `data/raw/` (2026-02-15 through 2026-04-18). Implementation has not started.

- **Data volume (unchanged):** ~82 million valid rows; date-partitioned fact files (~54-78 MB each before fact_key removal; ~46-68 MB after).

- **Updated fact table schema:** `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price` — 7 columns (was 9). `fact_key`, `company_key`, `settlement_key`, `store_name` removed; `store_key`, `file_key` added.

- **Changes written to `request.md` this run:** All AI sections (7-14) fully replaced: `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`, `## Multi-Perspective Stakeholder Review`.

- **Analysis document scope:** Reasoning artifact only. `implement` MUST NOT read this file.

---

## Domain Knowledge Essentials

- **EKATTE** — Bulgarian administrative-territorial units code registry maintained by the National Statistical Institute (NSI). Each settlement has a unique 5-6 digit code. ~256 distinct codes appear in the raw data; 238 resolved via `cities-ekatte-nomenclature.json`; 18 receive `(unknown:<code>)` entries.

- **UIC (Unified Identification Code / ЕИК)** — Bulgarian national tax registration number; uniquely identifies a legal entity. CSV filenames follow `<CompanyName>_<UIC>.csv`. ~217 unique UICs across 63 ZIPs.

- **Retail price data (kolkostruva.bg)** — Daily reporting mandated by Bulgarian law. Each daily ZIP contains one CSV per reporting retail company (182-216 files per ZIP). Per-row columns: EKATTE code, store name, product name, product code, category code, retail price, promo price.

- **Star schema** — Dimensional modelling pattern. A central fact table references surrogate keys from surrounding dimension tables, minimising string repetition.

- **Snowflake schema** — Variant of star schema where some dimension tables reference other dimensions. With `dim_store` containing `settlement_key` and `company_key`, the schema becomes partially snowflaked: fact → dim_store → dim_settlement / dim_company.

- **SCD Type 1 (Slowly Changing Dimension — overwrite)** — When a dimension attribute changes, the old value is overwritten with the new one. No history is preserved. This is the simplest SCD strategy and is appropriate when historical dimension values are not needed for analysis. All dimensions in this project use SCD Type 1.

- **Dimension from facts** — Dimension tables populated from codes observed in the fact stream, enriched via static nomenclature files. Unknown codes receive `(unknown:<code>)` placeholder rows. Guarantees 100% FK coverage with zero row rejections (Kimball "late-arriving dimension" pattern).

- **No-rejection policy** — All rows with a valid column count are retained. Unknown dimension codes produce placeholder entries; non-parseable retail prices store NULL. No rows discarded.

- **Store dimension** — A conformed dimension representing a physical retail location. Natural key: `(store_name, settlement_key, company_key)`. A store is uniquely identified by its name, the settlement it is in, and the company that operates it. Same store name at different settlements or companies creates separate dimension entries.

- **File dimension** — A data-lineage dimension tracking the origin of each fact row. Natural key: `(file_name, zip_date)`. Each CSV file within each ZIP gets one entry. ~208 files x 63 ZIPs ≈ ~13,100 dimension rows.

- **Quality report** — A per-run diagnostic CSV capturing data quality metrics per date: total rows processed, NULL-price rows, unknown settlement codes, unknown category codes, and delimiter anomalies. Supports data governance and operational monitoring.

- **ETL state tracking** — Persisting checkpoint dates in `config.ini [state]`. Operator can inspect ETL health and override checkpoints for forced re-execution.

- **Impacted roles/personas:** Data engineer (ETL operator), data analyst (consumer of schema outputs and quality reports).

---

## Technical Knowledge & Terms

- **Python 3.9+** — Required runtime. All scripts use only stdlib: `zipfile`, `csv`, `json`, `pathlib`, `datetime`, `subprocess`, `configparser`, `logging`.

- **`configparser` (stdlib)** — INI-file parser. `config.get(section, key, fallback=None)` returns default without `KeyError`. All values stored as strings; dates parsed with `datetime.date.fromisoformat()`.

- **`config.ini` layout:**

  ```ini
  [settings]
  opendata_url = https://kolkostruva.bg/opendata
  max_retries = 3
  retry_delay = 10
  log_level = INFO

  [state]
  last_downloaded_date =
  last_processed_date =
  ```

- **`save_state()` re-read pattern:** The function must re-read `config.ini` from disk immediately before writing, not use a startup-cached `ConfigParser` object. This prevents race conditions where extract and transform run in sequence and the second overwrites changes made by the first.

- **`Path.replace()` vs `Path.rename()`:** `Path.rename()` raises `FileExistsError` on Windows if the destination exists. `Path.replace()` atomically overwrites the destination on both POSIX and Windows. Standardizing on `Path.replace()` ensures correct behaviour across platforms and consistency with the atomic-write pattern.

- **`zipfile.is_zipfile()`** — Stdlib function that reads the first bytes of a file and checks for the ZIP magic number. Returns `True` for valid ZIPs, `False` for corrupted or truncated downloads. Lightweight pre-processing check.

- **`logging.FileHandler`** — Stdlib handler that writes log records to a file. Adding a FileHandler alongside the existing StreamHandler gives console + file logging. File path: `logs/transform_YYYY-MM-DD_HHMMSS.log`.

- **`subprocess.run()` stderr capture:** Using `capture_output=True` (or `stderr=subprocess.PIPE`) captures the child process's stderr. On `CalledProcessError`, `e.stderr` contains the captured bytes, which can be decoded and included in the error message.

- **UTF-8 no BOM:** All output CSV files use `encoding='utf-8'` (not `utf-8-sig`). Input CSV reading continues to use `utf-8-sig` to transparently handle both BOM and non-BOM source files (\ufeff stripped automatically).

- **Delimiter auto-detection:** If the first data row produces exactly 1 column containing `;`, re-read with `delimiter=';'`. 3 companies use semicolons consistently across all 63 ZIPs.

- **Updated star-schema layout:**

  | Table | Columns | Key |
  |---|---|---|
  | `dim_date.csv` | date_key, date, year, month, day, weekday | date_key |
  | `dim_company.csv` | company_key, uic, company_name | company_key |
  | `dim_settlement.csv` | settlement_key, ekatte_code, settlement_name | settlement_key |
  | `dim_category.csv` | category_key, category_code, category_name | category_key |
  | `dim_product.csv` | product_key, product_code, product_name | product_key |
  | `dim_store.csv` | store_key, store_name, settlement_key, company_key | store_key |
  | `dim_file.csv` | file_key, file_name, zip_date | file_key |
  | `facts/YYYY-MM-DD.csv` | date_key, store_key, file_key, category_key, product_key, retail_price, promo_price | (no surrogate) |

- **Fact table column changes:**
  - Removed: `fact_key` (saves ~656 MB across 82M rows), `company_key` (in dim_store), `settlement_key` (in dim_store), `store_name` (in dim_store)
  - Added: `store_key` (integer FK), `file_key` (integer FK)
  - Net savings: significant — removing `store_name` (variable-length string) and `fact_key` (integer) outweighs adding two integer FKs.

- **Quality report schema:** `data/quality/report_<YYYY-MM-DD>_<HHMMSS>.csv` with columns: `zip_date, total_rows, null_prices, unknown_settlements, unknown_categories, delimiter_anomalies`. One row per ZIP date processed in the run. Timestamp in filename reflects the processing time.

- **Per-ZIP progress logging format:** `INFO: Processed ZIP 14/63 (2026-03-02) — 1,119,243 rows`. Logged after each ZIP is fully processed (past tense) so the row count is accurate.

- **Files read during this analysis run:**
  - `.aib_memory/input.md` — 13 new scope items
  - `.aib_memory/requests/R-20260419-0854-.../request.md` — full read (all 14 sections)
  - `.aib_memory/requests/R-20260419-0854-.../analysis.md` — prior run (fifth) reviewed for continuity
  - `.aib_memory/context.md` — full read for product context
  - `.aib_brain/Concepts.md` — AIB domain reference
  - `.aib_brain/conventions/analysis-convention.md` — applied for this analysis structure
  - `.aib_brain/conventions/request-convention.md` — applied for request.md section rules
  - `.aib_memory/references.md` — two entries: context.md (product-doc), Concepts.md (domain)
  - `extract.py` (project root) — current download script reviewed
  - `README.md` — current documentation reviewed
  - `requirements.txt` — dependency list reviewed
  - `data/raw/2026-02-15.zip` — sampled for data structure verification
  - `data/nomenclatures/cities-ekatte-nomenclature.json` — EKATTE mapping verified (5,256 dict entries)
  - `data/nomenclatures/product-categories.json` — category mapping verified (101 entries, list of dicts)
  - `data/nomenclatures/Ekatte/sof_rai.json` — Sofia sub-district codes verified (38 entries, list of dicts)

---

## Research Results

- **dim_store as a conformed dimension:** The pattern of extracting a store dimension from the fact table is standard Kimball practice. A store is identified by `(store_name, settlement_key, company_key)` — the combination necessary since different companies can name stores identically. The natural key uses surrogate keys from settlement and company dimensions, creating a hierarchy: fact → dim_store → dim_settlement / dim_company. This is a partial snowflake, acceptable when normalisation benefit outweighs the extra join cost.

- **dim_file for data lineage:** Adding a file-origin dimension is an ETL best practice for auditability. When data quality issues are discovered, the file_key enables tracing any fact row back to its exact source CSV within a specific dated ZIP. The dimension is small (~13,100 rows for 63 ZIPs) and grows linearly with new data.

- **fact_key removal:** Dropping the fact table surrogate key saves ~8 bytes per row x ~82M rows ≈ ~656 MB. Since the fact table is date-partitioned and rows are uniquely identifiable by their foreign key combination (or by position within each partition), a surrogate key provides no analytical value. This aligns with Kimball guidance that fact table surrogates are optional and should be omitted when storage is a concern.

- **SCD Type 1 — overwrite strategy:** All dimensions use simple overwrite semantics. When a dimension attribute changes, the old value is replaced. This is appropriate when: (a) the project does not require historical dimension tracking, (b) dimension changes are infrequent (government-assigned codes rarely change), and (c) simplicity is prioritised. The trade-off is that historical analyses will see current attribute values, not the values at the time of the fact.

- **Quality report pattern:** Writing a per-run quality report CSV is a lightweight alternative to full data quality frameworks (Great Expectations, dbt tests). The report provides immediate visibility into data issues without adding new dependencies. Per-date row counts, NULL metrics, and unknown-code counts are minimum viable quality indicators.

- **Per-ZIP progress logging:** Adding structured progress messages transforms the transform script from a black-box into an observable pipeline. The format `Processed ZIP 14/63 (2026-03-02) — 1,119,243 rows` provides position (14/63), scope (date), and magnitude (row count) in a single line.

- **save_state() re-read:** Reading the config file immediately before writing prevents a subtle bug: if `extract.py` writes `last_downloaded_date`, and then `transform.py` uses a startup-cached config object when writing `last_processed_date`, it would overwrite the download state. Re-reading before writing ensures both keys are preserved.

- **Path.replace() standardisation:** `Path.rename()` fails on Windows when the destination exists (`FileExistsError`). `Path.replace()` atomically overwrites on both POSIX and Windows. The current `extract.py` uses `tmp.rename(dest_path)` at line 64 — a latent Windows bug in the force-redownload path. Standardising on `Path.replace()` fixes this.

- **ZIP integrity check:** `zipfile.is_zipfile()` reads only the first bytes — fast. Checking immediately after download catches truncated or corrupted downloads before they enter the pipeline. The delete-and-re-download pattern is safe: the download already uses `.partial` → atomic rename, so a re-download overwrites cleanly.

- **Pattern scan — workspace:** No existing `src/`, `data/schema/`, `data/quality/`, `config.ini`. `extract.py` uses `Path.rename()` (line 64). No `FileHandler` in logging. No quality reporting. No store or file dimensions planned prior to this input.

---

## External Benchmarking

- **Kimball Group — Store Dimension Design (The Data Warehouse Toolkit):**
  - Kimball recommends a store dimension as a core conformed dimension in retail schemas, with attributes including store name, location (settlement/region), and operating company.
  - Takeaway adopted: `dim_store` with `(store_name, settlement_key, company_key)` follows this pattern. The partial snowflake (dim_store referencing dim_settlement and dim_company) is explicitly sanctioned by Kimball when the dimension hierarchy is natural and frequently queried.
  - Applicability: high. The normalisation benefit (removing repeated store names from ~82M fact rows) aligns with the project's space-efficiency constraint.

- **Kimball Group — SCD Type 1 Overwrite:**
  - Type 1 is the simplest SCD strategy. The old dimension value is overwritten with no history preserved. Kimball notes this is appropriate when historical attribute tracking is not a business requirement.
  - Takeaway adopted: all seven dimensions use Type 1. The project has no requirement for historical dimension tracking. Government-assigned codes (EKATTE, UIC, category IDs) change very infrequently.
  - Applicability: high. Document this choice explicitly in README and analysis.

- **Great Expectations — Data quality validation framework:**
  - Great Expectations defines "expectations" that produce structured validation reports after each pipeline run.
  - Takeaway: the quality report concept is adopted; the full framework is rejected (introduces pip dependency). A lightweight CSV report with per-date metrics achieves 80% of the observability value with zero new dependencies.
  - Applicability: concept adopted, framework rejected.

- **dbt data tests — Post-transform assertions:**
  - dbt runs SQL-based data tests after transformations (unique, not_null, referential integrity).
  - Takeaway: the quality report fulfils a similar role without requiring SQL engine or dbt installation.
  - Applicability: concept adopted, tool rejected.

- **Apache Airflow — Task-level logging:**
  - Airflow writes per-task log files with timestamps, enabling operators to diagnose failures from logs alone.
  - Takeaway adopted: the `FileHandler` writing to `logs/transform_YYYY-MM-DD_HHMMSS.log` provides equivalent per-run log persistence.
  - Applicability: logging pattern adopted; Airflow out of scope.

- **Singer.io — Bookmark state and atomic writes:**
  - Singer taps write state atomically after each successful sync. The state file is re-read before writing to handle sequential pipeline stages.
  - Takeaway adopted: `save_state()` re-reads `config.ini` before writing, matching the Singer fresh-read-then-merge-then-write pattern.
  - Applicability: high. Pattern directly implemented.

---

## Minimal Spikes and Experiments

- **Spike: dim_store natural key uniqueness**
  - Hypothesis: The combination `(store_name, ekatte_code, uic)` — which becomes `(store_name, settlement_key, company_key)` after dim lookups — is unique enough to serve as the dim_store natural key.
  - Approach: Sampled `data/raw/2026-02-15.zip`. Extracted all `(store_name, ekatte_code, uic)` triples from the 208 CSVs. Checked for duplicate triples within a single ZIP.
  - Outcome: No duplicate triples found. Each company-settlement-store combination produces a unique entry. The same company may have multiple stores in the same settlement with different names.
  - Conclusion: `(store_name, settlement_key, company_key)` is a valid natural key. Adopted.

- **Spike: dim_file row count estimation**
  - Hypothesis: dim_file will have ~13,100 rows (63 ZIPs x ~208 files/ZIP).
  - Approach: Counted files in first and last ZIPs. `2026-02-15.zip` has 208 files; `2026-04-18.zip` has ~216 files (companies join over time).
  - Outcome: Estimated 63 x ~210 ≈ 13,230 rows. Small dimension; no memory or performance concern.
  - Conclusion: dim_file is feasible. Adopted.

- **Spike: fact_key removal space savings**
  - Hypothesis: Dropping the fact_key column saves ~656 MB.
  - Approach: 82M rows x 8 bytes average (integer string representation in CSV including comma delimiter) ≈ 656 MB. Each per-date file (~1.3M rows) saves ~10 MB.
  - Outcome: Savings confirmed by arithmetic. The fact table has no use case for a surrogate key.
  - Conclusion: Drop fact_key. Adopted.

- **Spike: zipfile.is_zipfile() reliability**
  - Hypothesis: `zipfile.is_zipfile()` reliably detects truncated/corrupted downloads.
  - Approach: Tested with a valid ZIP from `data/raw/2026-02-15.zip` (returns True). Would return False for truncated files.
  - Outcome: Adequate for detecting gross corruption (truncated downloads). Does not catch in-archive bit-rot.
  - Conclusion: Sufficient for the stated use case. Adopted.

- **Spike: Path.replace() vs Path.rename() on existing extract.py**
  - Hypothesis: `extract.py` line 64 uses `tmp.rename(dest_path)` which would fail on Windows if `dest_path` exists.
  - Approach: Reviewed `extract.py` line 64: `tmp.rename(dest_path)`. In the force-redownload flow, `dest_path` already exists — `rename()` would fail on Windows.
  - Outcome: Confirmed latent Windows bug in force-redownload path.
  - Conclusion: Standardise on `Path.replace()` throughout. Adopted.

- **Spike: save_state() re-read correctness**
  - Hypothesis: Re-reading config before writing prevents state key loss in sequential runs.
  - Approach: Scenario analysis — `extract.py` writes `last_downloaded_date`, then `transform.py` with startup-cached config would overwrite it if not re-reading.
  - Outcome: Re-reading is essential for sequential pipeline safety.
  - Conclusion: `save_state()` must create a fresh `ConfigParser` and `read(config_path)` before updating keys. Adopted.

- **Spike: Dimension write after each ZIP**
  - Hypothesis: Writing dimension CSVs after each ZIP (instead of batch at end) provides crash safety.
  - Approach: 7 dimension CSVs x 63 writes = 441 file writes. Each dimension is small (<1 MB). Total I/O overhead: negligible.
  - Outcome: Acceptable overhead. Crash recovery is significantly improved.
  - Conclusion: Write dimension CSVs after each ZIP's fact file. Adopted.

- **Spike: Quality report CSV feasibility**
  - Hypothesis: Accumulating per-date quality metrics during transform and writing a single report CSV at the end is feasible.
  - Approach: 63 dates x 5 counters = 315 integer values in memory. Trivial.
  - Outcome: Confirmed. No concerns.
  - Conclusion: Adopted.

- **Spike: configparser atomic write safety (carried)**
  - Outcome: `.partial` → `Path.replace()` is POSIX-atomic. Confirmed.

- **Spike: dim_settlement facts-driven row count (carried)**
  - Outcome: ~256 rows (238 named + 18 unknown). Confirmed.

- **Spike: Actual row volume (carried)**
  - Outcome: ~82M total rows. Confirmed.

- **Spike: Semicolon delimiter prevalence (carried)**
  - Outcome: 3 semicolon-delimited files per ZIP. Auto-detection mandatory. Confirmed.
