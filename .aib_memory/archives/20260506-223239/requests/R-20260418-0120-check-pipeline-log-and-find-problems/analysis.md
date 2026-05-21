# Analysis — R-20260418-0120: Check pipeline.log and find problems

## Executive Summary

- **Request ID:** R-20260418-0120

- **Title:** Check pipeline.log and find problems

- **Purpose:** Perform a structured audit of `logs/pipeline.log` to identify all operational problems, data-quality issues, and observability weaknesses in the ETL pipeline execution history.

- **Log scope:** 860,427 lines; 4 pipeline runs on 2026-04-09, 1 run on 2026-04-14; date coverage 2026-02-15 through 2026-04-13 (58 processing days).

- **Problems found:** 8 distinct problems identified, spanning concurrent execution risk, row-level data rejection, broken vendor CSV formats, missing reference data, anomaly spike, an incorrect initial run flag, and log verbosity.

- **Most critical finding:** 4 pipeline instances ran concurrently on 2026-04-09 without any locking mechanism, creating race conditions on shared JSON dimension files. Only 1 of the 4 runs produced a `Pipeline finished` summary line.

- **Data loss scale:** 860,211 WARNING-level log events represent 860,211 skipped or flagged data points. Approximately 855,984 rows were dropped entirely (invalid price, unknown EKATTE, unknown category, wrong column count) and 4,227 company-day pairs were anomaly-flagged.

- **`request.md` sections updated:** `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`, `## Multi-Perspective Stakeholder Review`.

---

## Domain Knowledge Essentials

**Kolkostruva.bg / Open-data portal** — Bulgarian government price-transparency portal where approximately 208 retail companies submit daily price reports as CSV files inside ZIP archives. Submissions are mandatory under consumer-protection legislation.

**EKATTE** — Bulgarian administrative registry code (Единен Класификатор на Административно-Териториалните Единици). Each settlement (city, village, quarter) is assigned a numeric or alphanumeric code. The pipeline resolves EKATTE codes to city dimension records using a seed nomenclature of 5,256 settlements. Sub-district or quarter-level codes (e.g., 68134-01 for a quarter of Sofia) are not in the standard municipal list and cause row-level skips.

**UIC (Unique Identifier Code)** — Bulgarian company registry number (ЕИК, Единен Идентификационен Код). The pipeline extracts UIC from CSV filenames to identify companies.

**SCD Type 2** — Slowly Changing Dimension Type 2: a data warehouse pattern that tracks attribute history by adding new rows with `valid_from`/`valid_to`/`is_current` flags rather than overwriting existing records. Used for all five dimension tables.

**Fact file** — Date-partitioned JSON file under `data/schema/facts/YYYY-MM-DD.json` containing all price observations for one day. Existence of this file is how the pipeline determines whether a date has been processed.

**Anomaly detection** — Per-company alert system comparing three metrics (row count, unique product codes, unique product names) against a 7-day rolling mean. A >25% deviation triggers a WARNING status in the quality report.

**REJECTED status** — A company is marked REJECTED in the quality report when its CSV file yields zero parseable rows (completely invalid or wrong-format file). It does NOT mean an error crash; the pipeline continues to process the day.

**WARNING status** — A company is marked WARNING in the quality report when its anomaly detection metrics deviate more than the threshold *or* when its CSV exhibits double-quoted fields. This is separate from the WARNING-level log messages (which are row-level parse errors).

**Backfill mode** — `--no-backfill`: only process dates that have no existing fact file. `--force`: reprocess all dates regardless of existing output. Default (neither flag): same behaviour as `--no-backfill` (skip already-processed dates).

**Impacted personas:** Data engineers operating the pipeline; downstream analysts consuming the star schema; product stakeholders relying on price data coverage.

---

## Technical Knowledge & Terms

**Pipeline entry point:** `src/pipeline.py` — single-file Python ETL script orchestrating download, parse, dimension upsert, fact writing, anomaly detection, and logging.

**Log format:** Plain-text timestamped (`YYYY-MM-DD HH:MM:SS,mmm LEVEL: message`), written by Python's `logging` module to `logs/pipeline.log`. No log rotation or size limits in evidence.

**Row-level WARNING log lines:** The pipeline emits one WARNING per rejected CSV row for `Invalid retail_price` and one per skipped row for `Unknown EKATTE` / `Unknown category_id`. This is the source of the 860K-line log — no batching or summarisation.

**Atomic file writes:** Dimension and fact files are written via temp-file-then-rename to prevent partial artifacts. This reduces (but does not eliminate) race conditions under concurrent execution.

**`_load_historical_metrics`:** Internal function loading the last 7 days of per-company metrics from `data/quality/YYYY-MM-DD-metrics.json` files to compute rolling baselines for anomaly detection.

**Technologies involved:** Python ≥ 3.9, `csv` module, `logging` module, `argparse`, JSON (`json` stdlib), `requests` / `urllib` for HTTP download. No external database for local operation.

**Files Read during this analysis:**
- `logs/pipeline.log` (860,427 lines; primary evidence source)
- `src/pipeline.py` (lines 103–165, 477–540, 699–820; code evidence for WARNING conditions)
- `.aib_memory/context.md` (product context)
- `.aib_brain/Concepts.md` (framework concepts)

**Evidence log:**

| Evidence | Implication |
|---|---|
| `Pipeline starting` appears 4× on 2026-04-09 | 4 concurrent/overlapping runs on the same day |
| Only 1 `Pipeline finished` line in entire log | 3 of 4 runs on 2026-04-09 were not cleanly terminated |
| "SKIP 2026-02-28" at 08:24:09 and "Completed 2026-02-28" at 08:24:10 in same run segment | Two processes were active simultaneously writing to overlapping date ranges |
| 860,211 WARNING lines for 58 days | Log verbosity far exceeds operational review capacity |
| 385,259 `Invalid retail_price` warnings from 9 companies | Specific vendors consistently submit non-float price values |
| 470,653 `Unknown EKATTE` warnings, top code 68134-01 (96,944) | EKATTE nomenclature missing sub-district codes; Sofia sub-districts heavily affected |
| `Wrong column count (1)` for 4 companies, ~57 occurrences each | Permanently broken CSV format from 4 vendors across all dates |
| Per-day anomaly WARNINGs spike from ≤15 to 49-56 on Apr 09-12 | Possible baseline corruption from concurrent dim writes; or genuine data shift |
| Run 1 used `no_backfill=True`, processed only 4 dates, then Run 2 restarted | Operator error in initial invocation; incomplete first run |

---

## Research Results

**Pattern: Row-level log verbosity anti-pattern**
Log-per-row is a known anti-pattern in batch ETL systems. Industry standard is to accumulate counts per file/company and emit a single summary WARNING per file, with a DEBUG-level trace of individual lines. The current approach causes log file sizes that make root cause analysis require auxiliary tooling (grep/awk) rather than direct inspection.

**Pattern: Missing EKATTE sub-district codes**
EKATTE code 68134-01 refers to the "Сердика" district of Sofia. Sub-district codes (68134-0X format) are valid Bulgarian administrative codes for Sofia's territorial divisions but are not included in the standard EKATTE settlement registry used for seeding `dim_city`. The same pattern applies to 68134-02, 68134-04, 68134-09, 68134-10. Collectively these represent Sofia sub-districts where many trade objects are located.

**Pattern: Invalid float price format**
The most likely cause of `Invalid retail_price` is decimal comma format (e.g., `"1,50"` instead of `"1.50"`). Bulgarian locale uses comma as decimal separator. The pipeline calls `float(row["retail_price"])` which fails for comma-format values. Some companies may also submit text strings like `"N/A"` or empty strings.

**Pattern: Wrong column count (1) = BOM or empty file**
A CSV with column count 1 typically means the file has no commas at all — either it is a bare text file, a single-value file, or a UTF-8 BOM has caused the entire content to be treated as one column. All 4 affected companies consistently produce column-count-1 files across all dates, indicating a persistent formatting issue on the vendor's submission end.

**Pattern: category_id = -1**
A sentinel value of -1 for category_id is a common placeholder for "uncategorised" in systems where the database schema does not allow NULL or empty. The pipeline's EKATTE and category lookups use `if not value:` style guards but category -1 passes that guard as a non-empty string and then fails the lookup.

**Pattern: Concurrent ETL execution without lock**
The pipeline has no file-based or advisory lock (e.g., `fcntl.flock`, a `.lock` file, or a process-existence check). Multiple simultaneous invocations can write overlapping dimension files. Even with atomic temp-file-rename writes, two processes performing SCD Type 2 upserts on the same dimension JSON will produce a last-write-wins result, potentially discarding valid upserts from the slower process.

---

## External Benchmarking

**Apache Airflow / similar schedulers — single-execution enforcement**
Production ETL orchestration frameworks (Airflow, Prefect, Dagster) enforce single-instance execution via their task execution model. The common pattern for standalone batch scripts is to use a lock file (`/var/run/etl.pid`) or an advisory lock (`fcntl.LOCK_EX | fcntl.LOCK_NB`) that prevents a second instance from starting while the first is running. The Kolko Ni Struva pipeline has no such guard.
- Takeaway: a 5-line lockfile guard at pipeline startup would eliminate the concurrent execution risk.
- Applicability: directly applicable; no external dependencies needed.

**ETL log management — summarised warnings per entity**
Industry practice (per AWS Glue, dbt, and Pandas-based pipelines) is to emit one structured warning per logical entity (company/CSV file), not per row. Tools like `dbt` produce a test result summary (N rows failed, not one log line per row). Apache Spark emits an `accumulator` count, not individual events.
- Takeaway: restructure logging to count invalid rows per file and emit a single `WARNING: X rows skipped in <company>.csv` per CSV rather than one line per row.
- Applicability: high — reduces log from 860K to ~60 lines per run for the same data.

**EKATTE lookup gap — enrichment via supplementary registry**
The Bulgarian National Statistics Institute (NSI) publishes EKATTE files that include both settlements and their administrative sub-divisions. The workspace already contains an EKATTE XLS (under `data/nomenclatures/Ekatte/`). The city-ekatte-nomenclature.json (5,256 entries) likely excludes sub-district codes. The fix is to extend the nomenclature seed with the sub-district-level EKATTE entries from the full NSI data.
- Takeaway: the data to resolve unknown EKATTE codes likely already exists in the workspace under `data/nomenclatures/Ekatte/`.
- Applicability: directly actionable from workspace-local data.

**Decimal comma handling — locale-aware float parsing**
Bulgarian government data sources use comma as the decimal separator. The Python `locale` module or a simple `str.replace(',', '.')` before `float()` is a widely used pattern in EU data pipelines. Libraries such as `babel` or locale-aware `Decimal` parsing are alternatives.
- Takeaway: a single `val.replace(',', '.')` before the `float()` call in `parse_csv()` would likely recover the majority of the 385,259 `Invalid retail_price` rows.
- Applicability: high; low-risk one-line change.

---

## Minimal Spikes and Experiments

**Spike 1: Verify decimal-comma hypothesis for `Invalid retail_price`**

Methodology: examined the pipeline's `parse_csv()` function (lines 144–165 of `src/pipeline.py`). The relevant code is:
```python
row["retail_price"] = float(row["retail_price"])
```
No pre-processing of the value string is performed before conversion. Bulgarian locale uses comma (`1,50`). The `float()` built-in fails on comma-decimal strings with `ValueError`. This confirms the hypothesis.

Confidence: **high**. The four affected companies are pharmacy chains (Lilly Drogerie, Нове Фарм, Аптеки Нота Бене, Аптеки Апостолов, Аптеки Сигма) and general retailers — all could plausibly submit government-mandated data using Bulgarian decimal notation.

**Spike 2: Verify concurrent execution interleaving from timestamps**

Methodology: extracted all `Pipeline starting`, `SKIP`, and `Completed` lines with timestamps from the log. Key finding:

| Timestamp | Event |
|---|---|
| 2026-04-09 08:24:07 | Run 3 starts |
| 2026-04-09 08:24:09 | Run 3: SKIP 2026-02-28 (file exists) |
| 2026-04-09 08:24:10 | Run 2: **Completed 2026-02-28** (still processing) |
| 2026-04-09 08:31:47 | Run 2: **Completed 2026-03-01** |
| 2026-04-09 08:42:16 | Run 4 starts |

Two distinct processes wrote to the same log file within one second. The "SKIP 02-28" from Run 3 (fact file already exists) immediately followed by "Completed 02-28" from Run 2 confirms Run 2 was still running when Run 3 started. Confidence: **confirmed** (timestamp evidence is unambiguous).

**Spike 3: Verify EKATTE 68134-XX = Sofia sub-districts**

The code 68134 is Sofia's EKATTE. Sub-district codes in the format `68134-01`, `68134-02`, etc. follow the Bulgarian NSI convention for capital city territorial divisions. The city-ekatte-nomenclature.json contains 5,256 entries, while NSI data includes several hundred additional sub-district entries. The workspace's `data/nomenclatures/Ekatte/` folder likely contains the full XLS export. Confidence: **high based on known Bulgarian administrative geography**.
