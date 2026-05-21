# Analysis — R-20260413-2055-bugfixing / Iteration 01

---

## 1. Executive Summary

- **Request ID:** R-20260413-2055-bugfixing

- **Request title:** Bugfixing — CSV fact files + unknown-FK placeholder records

- **Iteration ID:** 01

- **High-level purpose:** Two corrective changes to `src/pipeline.py` and `src/migrate_supabase.py`:
  1. Replace the named-key JSON fact-file format (`YYYY-MM-DD.json`) with a flat CSV format (`YYYY-MM-DD.csv`) to reduce local disk footprint.
  2. Auto-insert placeholder dimension records (city or category) for unknown natural keys instead of silently dropping fact rows.

- **Storage finding:** The request estimates ~4.7 GB for 25 fact files. Actual measurement at analysis time shows **58 files totalling 11.86 GB** (pipeline continued collecting data after the request was written). The CSV conversion is even more impactful: measured 151 bytes/row (JSON) vs ~35 bytes/row (CSV) — an estimated **~76% reduction per file**, yielding a projected total of approximately 2.8 GB.

- **Data-loss finding:** The request cites 16 unknown EKATTE codes causing ~229,780 skipped rows per run. Code review confirms this: `build_facts()` calls `get_city_sk()` and `get_category_sk()`, both of which return `None` for unknown keys, and the calling code `continue`s (drops the row) with a WARNING log. The fix is a "get-or-create-placeholder" pattern inside `DimensionStore`.

- **No earlier iterations.** This is iteration 01.

- **No conflicts** with existing documented requirements; the request is additive/corrective.

---

## 2. Scope Interpretation

- **In scope (explicit):**

  - Change fact-file format from named-key JSON to CSV (comma-separated values, `.csv` extension) in `src/pipeline.py`.

  - Update `src/migrate_supabase.py` to read `.csv` fact files instead of `.json` (both Tier 1 and Tier 2 sync paths, and the `_available_fact_dates()` helper).

  - Add placeholder dimension-record auto-insertion in `DimensionStore` for unknown EKATTE codes (`dim_city`) and unknown `category_id` values (`dim_category`).

  - Add `is_unresolved: true` flag on placeholder records in local JSON dimension files only.

  - Ensure idempotency: two consecutive `pipeline.py --force` runs produce identical output.

- **Out of scope (explicit):**

  - Supabase DDL changes (no column additions to dimension tables, no `is_unresolved` column in Supabase).

  - Anomaly-detection or quality-report logic (`data/quality/`).

  - Re-downloading raw data from kolkostruva.bg.

  - Front-end, API, or dashboard layer.

  - Populating product-doc stubs in `.aib_memory/docs/`.

- **Implicitly in scope (implicit rule - AIB framework):**

  - Update `README.md` Output Reference section to reflect the new CSV fact-file format (the current docs describe `YYYY-MM-DD.json` structure in detail).

  - Update `.aib_memory/context.md` to reflect the format change (the context document currently states JSON fact files).

---

## 3. Domain Knowledge Essentials

- **ETL pipeline (Extract-Transform-Load):** Automated process that downloads retail-price data, normalises it, and writes it to structured storage. Changes to the output format (JSON → CSV) affect both the write (pipeline) and read (migration) stages.

- **Star schema:** A data-warehouse design with a central fact table referencing multiple dimension tables. Here the fact is a price observation; dimensions are company, trade object, product, city, and category.

- **SCD Type 2 (Slowly Changing Dimension):** A versioning strategy where attribute changes create a new dimension record (with `valid_from`/`valid_to`/`is_current` fields) rather than overwriting the old one. Surrogate keys (`sk`) are assigned per version.

- **EKATTE code:** Bulgarian national settlement identifier (5–6 digits). The pipeline maps raw EKATTE values from CSV rows to `city_sk` via `dim_city.json`. Codes absent from `cities-ekatte-nomenclature.json` are currently dropped.

- **UIC (Единен идентификационен код):** Bulgarian company registration number used as the natural key for companies.

- **Placeholder record:** A dimension record auto-created for an unknown natural key, marked with `is_unresolved: true`, so fact rows are preserved rather than discarded. The placeholder allows full downstream query joins while signalling to operators that the nomenclature file needs updating.

- **Impacted roles:**
  - Pipeline operators: observe reduced disk footprint and fewer WARNING log lines.
  - Data analysts: gain access to previously dropped rows; can identify unknown EKATTE/category_id values via `is_unresolved` flag in dimension files.
  - Supabase consumers: unaffected (Tier 1 and Tier 2 data volume may increase once dropped rows are recovered).

- **Business process touched:** Daily data collection and normalisation; downstream Supabase sync.

---

## 4. Technical Knowledge & Terms

- **`src/pipeline.py`:** Main ETL script. Manages download, CSV parsing, `DimensionStore` (SCD Type 2), fact-file writing, and anomaly detection. ~850 lines fully read during this analysis.

- **`src/migrate_supabase.py`:** Incremental sync script. Reads local JSON dimension files and fact files; upserts to Supabase PostgreSQL via `psycopg2`. ~440 lines fully read.

- **`DimensionStore`:** Python class in `pipeline.py` that manages five in-memory dimension caches backed by `data/schema/dim_*.json` files. Key methods relevant to this change:
  - `get_city_sk(ekatte)` — returns `int | None`; needs extension to "get-or-create".
  - `get_category_sk(category_id)` — same pattern.
  - `_upsert(dim, natural_key_str, new_attrs, as_of_date)` — generic SCD Type 2 upsert; idempotent for same attrs.
  - `save()` — writes all in-memory dimension data to `dim_*.json` atomically.

- **`build_facts()`:** Standalone function in `pipeline.py`; calls `get_city_sk` and `get_category_sk`, drops rows if either returns `None`. This is the primary point of data loss addressed by Change 2.

- **`write_fact_file()`:** Writes `YYYY-MM-DD.json` atomically via `.json.partial` rename. Must be changed to write `YYYY-MM-DD.csv`.

- **Fact file format (current):**
  ```json
  {"metadata": {"date": "...", "company_count": N, "row_count": N},
   "facts": [{"date": "...", "company_sk": N, "trade_object_sk": N,
               "product_sk": N, "city_sk": N, "category_sk": N,
               "retail_price": 11.24, "promo_price": null}]}
  ```
  151 bytes/row average (measured on 2026-02-15: 1,267,531 rows, 191 MB).

- **Fact file format (target):**
  ```
  date,company_sk,trade_object_sk,product_sk,city_sk,category_sk,retail_price,promo_price
  2026-02-15,1,1,1,3805,17,11.24,
  ```
  ~35 bytes/row (measured estimate on same file: ~44 MB target).

- **Atomic write pattern:** Both pipeline.py and migrate_supabase.py use `tmp.write_text(...)` → `os.replace(tmp, path)`. This pattern must be preserved for CSV fact files.

- **`_available_fact_dates()` in migrate_supabase.py (line 183-189):** Iterates `FACTS_DIR`, filters `p.suffix == ".json"`. Must change to `.csv`.

- **`sync_tier1()` in migrate_supabase.py (lines 197-280):** Constructs `fact_path = facts_dir / f"{d_str}.json"`, reads with `json.loads()`, accesses `data.get("facts", [])`. All three lines require change.

- **`sync_tier2()` in migrate_supabase.py (lines 293-395):** Iterates `facts_dir`, filters `p.suffix != ".json"`, reads with `json.loads()`, accesses `data.get("facts", [])`. Requires same changes.

- **Type coercion issue:** JSON parsing yields Python-native types (`int`, `float`, `None`). CSV `DictReader` yields strings for all fields. `migrate_supabase.py` arithmetic (`entry["retail_sum"] += rp`) and SQL parameterisation rely on numeric types. A helper function is needed to coerce CSV string fields to `int | None` and `float | None`.

- **`promo_price` nullability:** In JSON: `null` → Python `None`. In CSV: empty string `""`. The coercion helper must map `""` → `None`.

- **`--no-backfill` check (pipeline.py line 732):** `if not (FACTS_DIR / f"{d}.json").exists()` — must change to `.csv`.
- **Skip check (pipeline.py line 754-755):** `fact_path = FACTS_DIR / f"{day_str}.json"` — must change to `.csv`.

- **Transition (existing JSON files):** 58 existing `.json` fact files will remain on disk after the code change. The pipeline will re-process all dates on the next run (since `.csv` files don't yet exist and the skip check now looks for `.csv`). Old `.json` files become orphans; they are not automatically removed by the current request scope.

- **Non-functional:**
  - Python `csv` module is stdlib — no new pip dependency.
  - `os.replace()` atomic rename preserved.
  - Supabase column lists in `sync_dimensions()` are explicit; `is_unresolved` is not listed → safely ignored during Supabase upsert.

---

## 5. Assumptions

- Assumption A1: The metadata block (`date`, `company_count`, `row_count`) embedded in the current JSON fact file is **not consumed programmatically** by any other logic and can be dropped from the CSV file without breaking downstream.
  - Rationale: Code inspection of `migrate_supabase.py` confirms it only accesses `data.get("facts", [])` and never reads the `metadata` key. `pipeline.py` computes `row_count` from `len(all_facts)` independently before calling `write_fact_file()`.
  - Risk if false: A downstream consumer (not visible in this workspace) relies on the metadata header — it would break silently.
  - Falsification method: Run `grep -r "metadata" src/` and search any external tooling for reads of `YYYY-MM-DD.json`.

- Assumption A2: The CSV fact file **will include a header row** listing column names.
  - Rationale: Required by `csv.DictReader` in `migrate_supabase.py` (cleanest update path); also improves human readability and tooling compatibility.
  - Risk if false: If no header is expected, `migrate_supabase.py` CSV reader would need positional indexing.
  - Falsification method: Confirm with user; default to header-included.

- Assumption A3: The **delimiter is comma** (`,`), i.e., standard CSV, not tab or pipe.
  - Rationale: Request says "csv (character separated values)" — standard interpretation is comma. Python `csv` module defaults to comma. No multi-value string fields exist in fact rows (all fields are numeric or date strings).
  - Risk if false: Not significant — trivially configurable.
  - Falsification method: No action needed; default confirmed.

- Assumption A4: Existing 58 JSON fact files will be **left in place** (not deleted automatically) after the code change. The pipeline re-run will write new CSV files; JSON orphans are cleaned up manually later.
  - Rationale: The request does not mention deleting old files. Auto-deletion would be a destructive operation requiring confirmation.
  - Risk if false: Orphan JSON files consume ~12 GB disk space until manually removed.
  - Falsification method: Ask user whether old `.json` files should be automatically replaced/deleted.

- Assumption A5: Placeholder dimension records should use the naming convention **`[UNKNOWN EKATTE:{code}]`** for city name and **`[UNKNOWN ID:{id}]`** for category name to make them visually distinct from real records.
  - Rationale: A structured, searchable prefix helps operators filter placeholder records in downstream queries. Request does not specify the format.
  - Risk if false: User may prefer a different naming scheme; trivially changeable.
  - Falsification method: Ask user during questionnaire (open question for User owner).

- Assumption A6: The `is_unresolved` flag on placeholder records is **stored in the `dim_*.json` files as a top-level field on the record** and **not propagated to Supabase** (column absent from DDL; not listed in `sync_dimensions()` column arrays).
  - Rationale: The request explicitly states "stored only in local JSON dimension files and is not synced to Supabase." Current `sync_dimensions()` column lists for `dim_city` and `dim_category` do not include `is_unresolved`. The `rec.get(c)` access pattern in the migration script will simply not extract the field.
  - Risk if false: If the Supabase DDL is ever altered to add `is_unresolved`, a re-sync would be needed.
  - Falsification method: Verify DDL in `docs/supabase-setup.md` — confirmed no `is_unresolved` column.

- Assumption A7: **Re-running `pipeline.py --force`** after placeholder records have been written to `dim_city.json` / `dim_category.json` will **not duplicate** those records. The existing `_upsert()` mechanism checks attribute equality before creating a new SCD version; a placeholder re-inserted with the same attrs returns the existing SK unchanged.
  - Rationale: `_upsert()` reads `existing = current.get(natural_key_str)` and compares tracked attributes. Placeholder attrs (`city_name`, `is_unresolved`) are stable across re-runs for the same EKATTE.
  - Risk if false: If `_upsert` is modified incorrectly, duplicates could inflate dimension tables.
  - Falsification method: Unit-test `_upsert` with same attrs twice and assert single record and stable SK.

---

## 6. Impact Assessment

### 6.1 Affected Components / Areas

| Component / Asset | Location | Change type |
|---|---|---|
| Fact file writer | `src/pipeline.py` → `write_fact_file()` | Modify |
| Fact-file skip check (main loop) | `src/pipeline.py` → `main()` line 754 | Modify |
| No-backfill existence check | `src/pipeline.py` → `main()` line 732 | Modify |
| Placeholder city insertion | `src/pipeline.py` → `DimensionStore` | Add |
| Placeholder category insertion | `src/pipeline.py` → `DimensionStore` | Add |
| Row-skip logic in `build_facts()` | `src/pipeline.py` → `build_facts()` | Modify |
| Fact-date discovery | `src/migrate_supabase.py` → `_available_fact_dates()` | Modify |
| Tier 1 sync | `src/migrate_supabase.py` → `sync_tier1()` | Modify |
| Tier 2 sync | `src/migrate_supabase.py` → `sync_tier2()` | Modify |
| Fact files on disk | `data/schema/facts/YYYY-MM-DD.json` (58 files) | Deprecate (orphaned) |
| Fact files on disk | `data/schema/facts/YYYY-MM-DD.csv` (new) | Add |
| Local dimension files | `data/schema/dim_city.json`, `dim_category.json` | Modify (new `is_unresolved` field on placeholders) |
| README | `README.md` — Output Reference section | Modify |
| Product context | `.aib_memory/context.md` | Modify |

### 6.2 Change Type and Dependencies

- **`write_fact_file()` (pipeline.py):**
  - Change type: Modify (JSON writer → CSV writer using `csv.writer`)
  - Dependencies: `os.replace()` atomic pattern preserved; `FACTS_DIR` unchanged.
  - Sequencing: Must be done before migrate_supabase.py changes (fact files must exist as CSV for sync to work).

- **`main()` skip/backfill checks (pipeline.py):**
  - Change type: Modify (two `.json` → `.csv` string references)
  - Dependencies: depend on `write_fact_file()` change.
  - Sequencing: Change atomically with `write_fact_file()`.

- **`DimensionStore` placeholder methods (pipeline.py):**
  - Change type: Add (`upsert_placeholder_city()`, `upsert_placeholder_category()`)
  - Dependencies: Reuses `_upsert()` internally; no new external dependencies.
  - Sequencing: Independent of CSV change; can be done in any order.

- **`build_facts()` (pipeline.py):**
  - Change type: Modify (replace `continue` skip with placeholder call + log change)
  - Dependencies: Depends on new `DimensionStore` methods.

- **`migrate_supabase.py` (three locations):**
  - Change type: Modify
  - Dependencies: Depend on CSV fact files existing (pipeline change first).
  - Sequencing: After pipeline.py changes and a re-run that generates CSV files, OR simultaneously if the CSV reader gracefully handles missing files.

### 6.3 Domain Impacts

- DOMAIN (ARCH): Fact-file format changes from JSON to CSV. The storage layer remains the same (`data/schema/facts/`). No architectural topology change.
  - Relevant: RQT — "Write one date-partitioned JSON fact file per day" becomes CSV.

- DOMAIN (CMP): Two source files modified (`pipeline.py`, `migrate_supabase.py`). New methods added to `DimensionStore`.

- DOMAIN (DATA): Fact file schema changes. CSV header row defines column order. `is_unresolved` field added to dim_city and dim_category records for placeholder entries. Previously dropped rows (~229,780/run) are now included in fact output.

- DOMAIN (DEV): Python stdlib `csv` module used; no new pip packages. Type coercion logic added in `migrate_supabase.py`.

- DOMAIN (DSR): No impact.

- DOMAIN (FNL): No impact.

- DOMAIN (KNW): README and context.md require updates to reflect new fact-file format.

- DOMAIN (RQT): RQT change — "Write one date-partitioned JSON fact file" → "...CSV fact file". Non-functional idempotency requirement satisfied by existing `_upsert` mechanism and atomic CSV writes.

- DOMAIN (OBS): Log message `"Unknown EKATTE %s in %s, row skipped"` (WARNING level) will change to `"Unknown EKATTE %s in %s — placeholder inserted, update nomenclature"`. Volume of WARNING lines drops significantly for cities; new WARNING tone differs semantically (data preserved, not dropped).

- DOMAIN (OPR): Operators running `python src/pipeline.py` after the change will see all 58 dates re-processed on the first run (existing `.csv` files absent). This takes ~5–15 minutes depending on hardware (estimate based on 58 files × 208 companies each).

- DOMAIN (SEC): No security impact. No new network calls, no credentials involved.

### 6.4 Constraints

- Python 3.10+; only stdlib additions (`csv` module) — already used implicitly by `pipeline.py`.
- No new `pip` packages.
- Supabase DDL must not change.
- `--force` re-run must be idempotent (second run produces same files).
- Atomic writes (`os.replace`) must be preserved.
- Existing SCD Type 2 versioning logic must not be altered.

### 6.5 Required Documentation Updates

- `README.md` — Output Reference / Fact files section:
  - Required update? **YES**
  - Reason: Currently documents JSON format with `metadata` + `facts` array. Must be updated to CSV format with header row example.

- `.aib_memory/context.md` — Requirements Summary, Functional capabilities #4:
  - Required update? **YES**
  - Reason: Currently states "Write one date-partitioned JSON fact file per day to `data/schema/facts/`". Must reflect CSV.

### 6.6 Decision Points

**DP-1: What to do with the `metadata` block (date, company_count, row_count)?**
- Option A (recommended): Drop metadata entirely. `date` is in the filename; `row_count` is computable from line count; `company_count` is not consumed anywhere.
- Option B: Store metadata as a separate `YYYY-MM-DD.meta.json` sidecar file.
- Option C: Add a comment line `# date=...,company_count=...,row_count=...` as the first CSV line (non-standard but readable).
- **Recommended:** Option A — simplest, no new files, all consumers confirmed to not read metadata.

**DP-2: What happens to existing 58 JSON fact files?**
- Option A (recommended): Leave in place. Pipeline auto-re-generates CSV files on next run. Operator manually deletes JSON files when satisfied with CSV output.
- Option B: Pipeline `write_fact_file()` deletes the corresponding `.json` file if it exists when writing a new `.csv`. Automatic, but destructive.
- Option C: Add a one-time migration script `migrate_facts_json_to_csv.py`.
- **Recommended:** Option A for safety. Document the transition in README. Option B could be added as an explicit `--cleanup-json` flag if desired.

**DP-3: Placeholder naming convention for unknown keys.**
- Option A (recommended): `city_name = "[UNKNOWN EKATTE:{ekatte}]"`, `category_name = "[UNKNOWN ID:{category_id}]"` — structured, grep-able prefix.
- Option B: `city_name = "UNKNOWN"`, `category_name = "UNKNOWN"` — simpler but loses the identity of the key in the name.
- **Recommended:** Option A — retains the natural key in the name, enabling operators to identify without querying the `ekatte` field.

---

## 7. Research Plan and Findings

**Methodology:** Full workspace scan — read all relevant source files, measured actual file sizes, estimated CSV byte overhead, traced all call paths.

**Evidence summary:**

| Evidence | Implication |
|---|---|
| `write_fact_file()` writes JSON with named-key dicts (151 B/row measured) | CSV at 35 B/row yields ~76% reduction; 11.86 GB → ~2.8 GB estimated |
| `migrate_supabase.py` uses `data.get("facts", [])` — never reads `metadata` | Metadata can be safely dropped from CSV output |
| Lines 183-184, 217-226, 307, 338 in `migrate_supabase.py` reference `.json` suffix/loading | 5 targeted edits required in migrate_supabase.py for CSV |
| `p.suffix == ".json"` in `_available_fact_dates()` | Must change to `.csv`; watermark file is separate (`.migrate_watermark.json`) — unaffected |
| Line 732: `if not (FACTS_DIR / f"{d}.json").exists()` | Must change to `.csv` for `--no-backfill` correctness |
| Line 754: `fact_path = FACTS_DIR / f"{day_str}.json"` | Must change to `.csv` for skip-on-existing correctness |
| `get_city_sk()` / `get_category_sk()` return `None`; `build_facts()` skips | Two `continue` blocks replaced with placeholder-insert + log |
| `_upsert()` checks attribute equality before versioning (skip_fields excludes `is_unresolved`) | `is_unresolved` IS checked for attr changes — idempotent if same value reused |
| `sync_dimensions()` dim_city columns: `["city_sk", "ekatte", "city_name", "valid_from", "valid_to", "is_current"]` | `is_unresolved` not extracted → not sent to Supabase → DDL unchanged |
| No `is_unresolved` column in Supabase DDL (`docs/supabase-setup.md` confirmed) | Placeholder records sync cleanly as regular entries |
| `extract.py` at workspace root: standalone download-only script | Does not read or write fact files — unaffected |

**Gaps and unknowns:**
- No external consumers of fact JSON files are visible in this workspace. Cannot rule out external tooling reading `YYYY-MM-DD.json`.
- The 16 specific unknown EKATTE codes are mentioned in the request (98226, 4279 cited); a full list is not provided. This is acceptable — the placeholder mechanism handles any unknown code at runtime.
- The exact format desired for placeholder names is not specified in the request.

**Proposed validation actions:**
- After implementation: run `pipeline.py --force` once, verify CSV files exist and are non-empty.
- Run `migrate_supabase.py` against a test DB and confirm Tier 1 and Tier 2 upserts succeed.
- Run `pipeline.py --force` a second time; verify no new CSV files differ (idempotency).
- Query `dim_city.json` for records with `is_unresolved: true` and confirm count matches expected unknown EKATTE codes.

**Files read:**

- `.aib_memory/context.md` — product identity, requirements summary, confirmed JSON fact file spec.
- `.aib_memory/references.md` — no `product-doc` type entries; no required-read product docs beyond context.
- `.aib_memory/requests/R-20260413-2055-bugfixing/request.md` — active request, both change items.
- `.aib_memory/requests/R-20260413-2055-bugfixing/iterations.md` — confirmed iteration 01 Active.
- `.aib_memory/requests/R-20260413-2055-bugfixing/implementation.md` — empty log; no prior work.
- `.aib_brain/Concepts.md` — AIB framework concepts; confirmed action contracts.
- `.aib_brain/conventions/analysis-convention.md` — mandatory structure; all sections followed.
- `.aib_brain/conventions/request-convention.md` — request rewrite format requirements.
- `src/pipeline.py` — fully read (850 lines); all relevant functions traced.
- `src/migrate_supabase.py` — fully read (440 lines); all fact-reading paths identified.
- `README.md` — Output Reference section confirms documented JSON format.
- `docs/supabase-setup.md` — Supabase DDL confirmed; no `is_unresolved` column.
- `data/nomenclatures/cities-ekatte-nomenclature.json` — 5,256 known EKATTE codes (dict keyed by EKATTE string).
- `data/nomenclatures/product-categories.json` — 101 categories (list of `{id, name}`).
- `data/schema/dim_city.json` — current record structure confirmed; no `is_unresolved` field.
- `data/schema/facts/2026-02-15.json` — measured 191 MB, 1,267,531 rows, 151 B/row; CSV estimate 44 MB.

---

## 8. Rewrite Proposal of the Request

*See updated `request.md` file (written as part of this analysis output).*

---

## 9. Solution Options

### Option A — Recommended: CSV fact files + get-or-create placeholder (stdlib only)

**Overview:** Replace `write_fact_file()` with a CSV writer using Python's `csv.DictWriter`. Update all fact-file consumers in `pipeline.py` and `migrate_supabase.py` to use `.csv`. Add `insert_placeholder_city()` and `insert_placeholder_category()` methods to `DimensionStore` that delegate to the existing `_upsert()` and set `is_unresolved=True` in the record.

**Benefits:**
- No new dependencies — `csv` module is Python stdlib.
- 76% storage reduction per file; estimated total from 11.86 GB → ~2.8 GB.
- ~229,780 previously dropped rows per day recovered into fact files.
- Idempotency preserved via existing `_upsert()` equality check.
- `is_unresolved` flag enables targeted nomenclature updates.
- Minimal footprint: ~12 targeted line changes across two files.

**Trade-offs:**
- First run after deployment re-processes all 58 dates (old `.csv` absent) — 5–15 min compute.
- Old JSON files orphaned on disk until manually removed (~12 GB).
- Metadata (company_count, row_count) dropped from file; row_count computable, company_count lost.
- `migrate_supabase.py` needs explicit type coercion (int/float/None) for CSV string values — small but required addition.

**Constraints:** Python 3.10+; stdlib only; no DDL change; idempotent.

**Risks:** See Section 12.

**Effort:** Low — ~12 targeted edits, no new abstractions.

**Acceptance-test ideas:**
1. `python src/pipeline.py --force` writes `YYYY-MM-DD.csv` for all 58 dates, no `.partial` files remain.
2. Re-run `--force` produces identical CSV byte-for-byte for at least one date.
3. `dim_city.json` contains records with `"is_unresolved": true` for all previously unknown EKATTE codes.
4. Row count in a sample CSV equals the row count previously reported minus previously skipped rows.
5. `python src/migrate_supabase.py` completes without errors against a test Supabase instance.

---

### Option B: Keep JSON, add `gzip` compression

**Overview:** Compress fact files as `YYYY-MM-DD.json.gz` using `gzip` (Python stdlib). No format schema change.

**Benefits:**
- Format schema unchanged (same field names, same null handling).
- ~70–75% compression ratio on repetitive JSON — similar size reduction.
- Lower migration risk to `migrate_supabase.py` (only decompression wrapper needed).

**Trade-offs:**
- Request explicitly says "Change the fact file format to csv" — this option does not satisfy the stated requirement.
- Compressed files are not human-readable without a tool.
- `migrate_supabase.py` requires `gzip.open()` wrapper but field types remain Native Python types (no coercion needed).

**Constraints:** Same (stdlib, no DDL change).

**Risks:** Does not address request scope — would require explicit user approval to substitute.

**Effort:** Very low — only 3–4 changes.

**Acceptance-test ideas:** Same as Option A but files end in `.json.gz`.

**Not recommended** — does not satisfy the explicit requirement to change format to CSV.

---

**Recommendation: Option A.** It directly satisfies both stated requirements with minimal code changes, no new dependencies, and preserved idempotency. The trade-offs (1-time re-processing run, orphaned JSON files, type coercion) are all manageable and documented.

---

## 10. Affected Documentation

| ref_id | document_title | path | reason_for_inclusion |
|--------|----------------|------|----------------------|
| REF-0001 | Context | `.aib_memory/context.md` | Functional capabilities #4 states JSON fact files; must be updated to CSV. |
| — | README | `README.md` | Output Reference section documents JSON fact file format; must be updated. |

---

## 11. Operational & Documentation Implications

**Runbooks:** None exist formally. A transition note should be added to README describing: (a) first `pipeline.py` run after upgrade re-processes all dates; (b) old `.json` files can be safely deleted after verifying CSV output.

**Monitoring/logging:** WARNING log message for unknown EKATTE/category changes from "row skipped" to "placeholder inserted." Operators should be informed that the WARNING count drop does NOT mean data quality improved — it means rows are now captured with an unresolved flag. A new `is_unresolved: true` filter query in `dim_city.json` / `dim_category.json` serves as the operational indicator.

**Data quality rules:** The `data/quality/YYYY-MM-DD-report.json` files are NOT affected (anomaly detection operates on raw CSVs, not fact files). However, after the placeholder change, `company_map[uic]` for companies with unknown EKATTEs will now include those rows in `rows` fed to `detect_anomalies()` — this could slightly reduce anomaly warning rates for affected companies (more rows means closer to historical baseline). This is a correct side effect.

**Product documentation:** `README.md` and `.aib_memory/context.md` — see Section 6.5.

---

## 12. Risks

- Risk R1: Orphaned JSON fact files (12 GB) remain on disk post-deployment and are never cleaned up.
  - Probability: Medium
  - Impact: Low (disk waste, no functional breakage)
  - Mitigation: Document cleanup step in README. Optionally implement `--cleanup-json` flag in `write_fact_file()`.
  - Owner (role): Pipeline operator

- Risk R2: External tooling outside this workspace reads `YYYY-MM-DD.json` files directly and breaks silently after CSV conversion.
  - Probability: Low (no such tooling visible in workspace)
  - Impact: High (silent data-pipeline failure for the consumer)
  - Mitigation: Before deployment, search workspace and any CI/CD config for `.json` fact-file references. Announce format change to all consumers.
  - Contingency: Keep JSON writing in parallel for one transition period (write both formats), then remove JSON writer.
  - Owner (role): Developer

- Risk R3: Type coercion in `migrate_supabase.py` for CSV string values omits an edge case (e.g., `None` vs `""` for `promo_price` in Tier 2 aggregation), causing arithmetic errors or NULL constraint violations in Supabase.
  - Probability: Medium (the `promo_sum` path adds `pp` if not None — `""` would be falsy in Python but type-coercion must be explicit)
  - Impact: Medium (Tier 2 sync failure or wrong averages)
  - Mitigation: Implement a `_coerce_fact_row(row: dict) -> dict` helper in `migrate_supabase.py` and unit-test it with edge cases: `""`, `"0"`, `"0.0"`, `None`.
  - Owner (role): Developer

- Risk R4: `_upsert()` placeholder record triggers unintended SCD Type 2 versioning on a subsequent `--force` run if `is_unresolved` attribute is evaluated differently.
  - Probability: Low (code logic confirmed: `skip_fields` excludes only `sk`, `valid_from`, `valid_to`, `is_current`; `is_unresolved` is included in equality check; same value on re-run → no change detected)
  - Impact: Medium (spurious new dim records, inflated SKs over repeated runs)
  - Mitigation: Write a test: insert placeholder, save, reload, call `get_city_sk` again, assert same SK returned.
  - Owner (role): Developer

- Risk R5: The first pipeline run after deployment re-processes all 58 dates and takes 5–15 minutes, potentially conflicting with a scheduled daily run.
  - Probability: Low (no cron/scheduler visible in workspace)
  - Impact: Low (temporary compute load)
  - Mitigation: Schedule the first post-upgrade run manually at an off-peak time.
  - Owner (role): Pipeline operator

---

## 13. Open Questions & Next Actions

| # | Question | Owner | Resolution path |
|---|---|---|---|
| OQ-1 | Should the pipeline automatically delete the corresponding `.json` file when writing a new `.csv` for the same date (e.g., on `--force` or on any write)? | User | No concrete resolution path — requires user decision (see DP-2). |
| OQ-2 | What naming format is preferred for placeholder dimension record names? (e.g., `[UNKNOWN EKATTE:98226]` vs `UNKNOWN`) | User | No concrete resolution path — arbitrary choice; see DP-3. |

*Section 13 contains 2 items with owner = User and no concrete resolution path → auto-triggers `create-questionnaire`.*

---

--- I am done with the analysis ---
