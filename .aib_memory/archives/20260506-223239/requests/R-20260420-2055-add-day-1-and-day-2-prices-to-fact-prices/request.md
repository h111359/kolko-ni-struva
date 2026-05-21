## Goal

Create a new derived fact table `data/schema/fact_prices_lookback.csv` that, for the most recent available fact date D, presents one row per `(store_key, category_key, product_key)` from D's data supplemented with `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, and `promo_price_day2` values looked up from the D-1 and D-2 fact CSVs respectively, using the same composite key. Where no matching row exists in the prior-day file (or where the prior-day file does not exist), the value is stored as empty (NULL equivalent in CSV). The existing 63 fact CSVs in `data/schema/facts/` must not be modified.

## Background

Analysts consuming `data/schema/facts/` currently must perform self-joins across multiple date-partitioned fact files when computing day-over-day price changes. Adding lookback columns directly to each fact file enables simpler single-file price-change queries using DuckDB, pandas, or spreadsheet tools without requiring cross-file joins. This change is consistent with the existing no-rejection and null-tolerance policies (retail_price is already nullable).

## Scope

- Add a new function `build_lookback_table(facts_dir, output_path)` in `src/transform.py` that:
  - Identifies the 3 most recent fact dates from `data/schema/facts/` (D = latest, D-1, D-2).
  - Loads D-1 and D-2 fact CSVs into in-memory lookup dicts keyed by `(store_key, category_key, product_key)` → `(retail_price, promo_price)` using `csv.DictReader`.
  - For each row in D's fact CSV, outputs an 11-column row: the 7 original columns from D's row plus `retail_price_day1`, `promo_price_day1` (from D-1 dict) and `retail_price_day2`, `promo_price_day2` (from D-2 dict). Missing lookback values are empty string.
  - Writes output atomically (`.partial` → rename) to `data/schema/fact_prices_lookback.csv`.

- Call `build_lookback_table` at the end of `src/transform.py`'s `main()` function (after all fact files for the current run have been written or skipped), so the lookback table always reflects the latest processed state.

- Do NOT modify `FACT_HEADER`, `build_schema`, or any existing fact row assembly in `src/transform.py`.

- Do NOT force-regenerate any of the 63 existing fact CSVs. The existing `data/schema/facts/*.csv` files remain unchanged (7 columns).

- Update `src/load_supabase.py` to add DDL for a new Supabase table `fact_prices_lookback` (11 columns, the four lookback columns nullable) and a new `insert_lookback(conn, csv_path)` function to truncate and reinsert rows on each sync run.

- Update `_ENSURE_NULLABLE_DDL` in `src/load_supabase.py` with idempotent `ALTER TABLE fact_prices_lookback ADD COLUMN IF NOT EXISTS …` guards for the four lookback columns.

- Update `data/schema/` context references in `.aib_memory/context.md` to document the new `fact_prices_lookback.csv` artifact, include it in Core Data Entities, and update the Data Lineage Summary.

## Out of scope

- Lookback beyond 2 days.
- Changes to the existing 63 fact CSVs in `data/schema/facts/` (they remain unchanged at 7 columns).
- Changes to `FACT_HEADER` or the existing `build_schema` function in `src/transform.py`.
- Force-regeneration of any existing fact files.
- Changes to any dimension tables.
- Changes to `src/extract.py` or the download pipeline.
- Changes to quality report columns or quality reporting logic.
- Changes to the EKATTE or product-category nomenclature files.

## Constraints

- `src/transform.py` MUST continue to use only Python 3.9+ stdlib (no new pip packages).
- Atomic writes (`.partial` → rename) must be preserved for all file writes, including `fact_prices_lookback.csv`.
- Idempotency must be maintained: re-running `transform.py` when fact files already exist and no force flag is set must produce no changes to the existing fact CSVs. `fact_prices_lookback.csv` is always regenerated (as a derived artifact, it is a full replacement on each run).
- The composite match key for the lookback join is `(store_key, category_key, product_key)`. A day-1 or day-2 lookup row is identified by the values of these three columns matching across the files.
- Empty string (not the literal string "NULL") is used as the CSV representation of a missing lookback value, consistent with the existing `promo_price` nullability convention.
- Python 3.9 compatibility required for all modified scripts.
- The existing 63 fact CSVs in `data/schema/facts/` MUST NOT be modified, deleted, or truncated by any change introduced in this request.

## Success criteria

- `data/schema/fact_prices_lookback.csv` exists after each successful transform run and contains exactly 11 columns with the header: `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price, retail_price_day1, promo_price_day1, retail_price_day2, promo_price_day2`.
- All 63 existing fact CSVs in `data/schema/facts/` remain unchanged (7 columns with header `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price`).
- For a row in `fact_prices_lookback.csv` with a matching `(store_key, category_key, product_key)` in the D-1 fact file, `retail_price_day1` and `promo_price_day1` are copied correctly from D-1's row.
- For a row in `fact_prices_lookback.csv` with a matching `(store_key, category_key, product_key)` in the D-2 fact file, `retail_price_day2` and `promo_price_day2` are copied correctly from D-2's row.
- Rows in `fact_prices_lookback.csv` with no match in the D-1 or D-2 fact file have empty string for the respective lookback columns.
- When fewer than 2 prior-day fact files exist, the affected lookback columns in `fact_prices_lookback.csv` are all empty string; no error raised.
- `src/load_supabase.py` DDL includes a `fact_prices_lookback` table definition with all 11 columns; re-running sync does not fail.
- Existing unit and smoke tests continue to pass.

## Assumptions

- A1: The composite key `(store_key, category_key, product_key)` is functionally unique per day within a single fact file. Since `store_key` encodes `(store_name, settlement_key, company_key)`, two rows from different companies cannot share the same `store_key`. Within a single company's CSV, the same product in the same store is expected to appear once. The lookback dict will retain the last row if duplicates exist, which is considered acceptable.
  - Risk if false: Silently incorrect lookback values for duplicate-key rows; no error raised.

- A2: `build_lookback_table` is invoked at the end of each `transform.py` main() run, after all fact files have been processed. This means the lookback table always reflects the latest available fact data.
  - Risk if false: The lookback table could reflect a stale state if called before the latest fact file is written.

- A3: The prior-day lookback dicts are built from at most 2 prior-day fact CSVs (~1.3 M rows each). Combined peak RAM overhead is approximately 400–800 MB for two dicts simultaneously, which is manageable on the target execution hardware.
  - Risk if false: If fact files grow significantly larger, memory pressure warrants a streaming or chunked approach.

- A4: PostgreSQL on Supabase is version 15.x and supports `ALTER TABLE … ADD COLUMN IF NOT EXISTS`.
  - Risk if false: Migration statements fail; manual DDL change required.

- A5: The `promo_price` convention (empty string = no promo) applies equally to day1/day2 columns. An empty string in day1/day2 means either: (a) there was no matching prior-day row, or (b) promo was absent on that day. The distinction is not tracked separately.
  - Risk if false: Analysts may misinterpret empty day1/day2 promo_price as "no match" when it could mean "no promo that day"; documentation should clarify.

- A6: The new `fact_prices_lookback.csv` is a full-replacement artifact (atomically overwritten on each transform run), not incrementally appended. This is consistent with a "periodic snapshot convenience derivation" pattern.
  - Risk if false: If errors occur mid-write, the `.partial` → rename pattern prevents corrupt partial files from being consumed.

## Plan

### Task 1: Create `build_lookback_table` function in `src/transform.py`
**Intent:** Implement a new function that reads the latest 3 fact CSVs from `data/schema/facts/` and produces `data/schema/fact_prices_lookback.csv` with 11 columns.
**Inputs:** `src/transform.py`; existing fact CSVs in `data/schema/facts/`
**Outputs:** Modified `src/transform.py` with new `LOOKBACK_HEADER` constant, `load_fact_dict` helper, and `build_lookback_table(facts_dir, output_path)` function.
**External Interfaces:** None (stdlib only; no new dependencies)
**Environment & Configuration:** No config changes required.
**Procedure:**
1. Define `LOOKBACK_HEADER = ["date_key", "store_key", "file_key", "category_key", "product_key", "retail_price", "promo_price", "retail_price_day1", "promo_price_day1", "retail_price_day2", "promo_price_day2"]`.
2. Add `load_fact_dict(fact_path)` helper: reads a fact CSV (if it exists) into a dict keyed by `(store_key, category_key, product_key)` → `(retail_price, promo_price)` using `csv.DictReader`. Returns empty dict if file absent.
3. Implement `build_lookback_table(facts_dir, output_path)`:
   a. List all `*.csv` files in `facts_dir`, sort lexicographically (date-ascending); identify D (latest), D-1 (second-latest if present), D-2 (third-latest if present).
   b. If no fact files exist, log a warning and return without writing output.
   c. Load D-1 and D-2 into dicts via `load_fact_dict`.
   d. Open D for row-by-row iteration via `csv.DictReader`; for each row, produce an 11-element output row appending lookback values (empty string if no match).
   e. Write rows to `output_path.partial` via `csv.writer`; rename to `output_path` on success.
**Done Criteria:** `build_lookback_table` present in `src/transform.py`; `LOOKBACK_HEADER` defined; existing `FACT_HEADER` and `build_schema` are untouched.
**Dependencies:** None
**Risk Notes:** Dict build may produce incorrect values if duplicate keys exist in prior-day file (see A1).

### Task 2: Wire `build_lookback_table` into `transform.py` main flow
**Intent:** Call `build_lookback_table` at the end of `transform.py` main() so it runs after all fact files are written or skipped.
**Inputs:** Modified `src/transform.py` from Task 1
**Outputs:** `data/schema/fact_prices_lookback.csv` generated on each transform run.
**External Interfaces:** None
**Environment & Configuration:** No config changes required.
**Procedure:**
1. In `transform.py`'s `main()` function, after `save_state()` is called, add a call to `build_lookback_table(FACTS_DIR, SCHEMA_DIR / "fact_prices_lookback.csv")`.
2. Confirm `FACTS_DIR` and `SCHEMA_DIR` path constants (or their equivalents) are in scope; pass as explicit arguments if needed.
**Done Criteria:** Running `python src/transform.py` produces `data/schema/fact_prices_lookback.csv`; existing fact CSVs are unchanged.
**Dependencies:** Task 1
**Risk Notes:** None.

### Task 3: Update Supabase DDL and sync for new `fact_prices_lookback` table
**Intent:** Add DDL and upload logic for the new `fact_prices_lookback` Supabase table in `src/load_supabase.py`.
**Inputs:** `src/load_supabase.py`; `data/schema/fact_prices_lookback.csv`
**Outputs:** Modified `src/load_supabase.py` with new DDL, `_ENSURE_NULLABLE_DDL` entries, and `insert_lookback(conn, csv_path)` function.
**External Interfaces:** Supabase PostgreSQL (via `DATABASE_URL` in `.env`)
**Environment & Configuration:** No new env vars; existing `DATABASE_URL` in `.env`.
**Procedure:**
1. Add `CREATE TABLE IF NOT EXISTS fact_prices_lookback (date_key INTEGER, store_key INTEGER, file_key INTEGER, category_key INTEGER, product_key INTEGER, retail_price NUMERIC(12,4), promo_price NUMERIC(12,4), retail_price_day1 NUMERIC(12,4), promo_price_day1 NUMERIC(12,4), retail_price_day2 NUMERIC(12,4), promo_price_day2 NUMERIC(12,4))` to `_CREATE_DDL`.
2. Add four `ALTER TABLE fact_prices_lookback ADD COLUMN IF NOT EXISTS … NUMERIC(12,4)` statements to `_ENSURE_NULLABLE_DDL`.
3. Implement `insert_lookback(conn, csv_path)`: truncate `fact_prices_lookback` and insert all rows from `fact_prices_lookback.csv` using `execute_batch` (page size 2000) within a transaction; handle missing or empty file gracefully.
4. Call `insert_lookback` from `main()` after the existing `insert_fact_day` call.
**Done Criteria:** Running `python src/load_supabase.py` creates `fact_prices_lookback` in Supabase and populates it; re-running succeeds with no error; existing `fact_prices` table and data are unaffected.
**Dependencies:** Tasks 1 and 2 (lookback CSV must exist for upload).
**Risk Notes:** TRUNCATE + reinsert means a brief window with an empty remote table; acceptable for a derived snapshot artifact.

### Task 4: Update `context.md`
**Intent:** Document the new `fact_prices_lookback.csv` artifact in the product knowledge base.
**Inputs:** `.aib_memory/context.md`
**Outputs:** Updated `.aib_memory/context.md` with new artifact row in Core Data Entities and updated Data Lineage Summary.
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Add a new row to the Core Data Entities table for `fact_prices_lookback`: file `data/schema/fact_prices_lookback.csv`; 11 columns including the four lookback columns; grain = one row per latest-day product observation with 2-day lookback; derived from last 3 fact CSVs.
2. Add note that `_day1` and `_day2` columns are empty string when no prior-day match exists; document the promo_price ambiguity (A5).
3. Extend the Data Lineage Summary to show `fact_prices_lookback.csv` derives from `data/schema/facts/D.csv`, `D-1.csv`, `D-2.csv` (the 3 most recent fact files).
**Done Criteria:** `context.md` Core Data Entities table includes `fact_prices_lookback`; lineage diagram updated.
**Dependencies:** Task 1 (new artifact name confirmed).
**Risk Notes:** None.

### Task 5: Run automated tests and verify outputs
**Intent:** Verify all success criteria are met and no regressions introduced.
**Inputs:** Modified `src/transform.py`; `data/schema/fact_prices_lookback.csv`; existing test suite.
**Outputs:** Test results; verified fact CSV and lookback file column counts.
**External Interfaces:** Supabase (for T7 and T9; requires `.env`)
**Environment & Configuration:** `.env` with valid `DATABASE_URL` for Supabase tests.
**Procedure:**
1. Run `python src/transform.py`; verify `fact_prices_lookback.csv` is created.
2. Execute T0–T6 (file existence, header, row count, lookback values, no-match, edge case, column count).
3. Run `python -m pytest tests/` (T8: unit tests pass).
4. If Supabase available: run T7 (DDL idempotency), T9 (lookback insert).
**Done Criteria:** All T0–T9 pass; no regressions in existing tests.
**Dependencies:** Tasks 1–4 complete.
**Risk Notes:** T7 and T9 require active Supabase connection.

## Testing

- T0 — Existing fact CSVs unchanged: Check any 3 existing fact CSVs (e.g., `data/schema/facts/2026-04-16.csv`, `2026-04-17.csv`, `2026-04-18.csv`) after running the updated transform. Expected outcome: each file has exactly 7 columns with the header `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price`.

- T1 — Lookback table header validation: Read the header row of `data/schema/fact_prices_lookback.csv`. Expected outcome: header is exactly `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2`.

- T2 — Row count matches latest fact file: Count rows in `data/schema/fact_prices_lookback.csv` (excluding header) and compare to row count in the latest fact file (e.g., `2026-04-18.csv`). Expected outcome: row counts match.

- T3 — Lookback values correct: Sample 10 rows from `fact_prices_lookback.csv` and cross-check `retail_price_day1` values against the D-1 fact file for the same `(store_key, category_key, product_key)`. Expected outcome: values match (or empty string where key is absent from D-1).

- T4 — No-match row has empty lookback: Identify a row in `fact_prices_lookback.csv` whose `(store_key, category_key, product_key)` is absent from the D-1 or D-2 fact file. Expected outcome: the affected `_day1` or `_day2` columns are empty string; no error raised.

- T5 — Fewer-than-3-files edge case: In a test scenario where fewer than 3 fact files exist, verify `build_lookback_table` completes without error. Expected outcome: lookback table is created; D-2 columns are all empty string when only D and D-1 exist; all lookback columns empty when only D exists.

- T6 — Column count quick check: `python -c "import csv; r=csv.reader(open('data/schema/fact_prices_lookback.csv')); print(len(next(r)))"`. Expected outcome: `11`.

- T7 — Supabase DDL idempotency: Run `python src/load_supabase.py` twice against a Supabase DB that already has `fact_prices_lookback`. Expected outcome: both runs complete with exit code 0; no errors.

- T8 — Existing unit tests pass: Run `python -m pytest tests/`. Expected outcome: all tests pass.

- T9 — Supabase lookback insert: After running `python src/load_supabase.py`, query the remote `fact_prices_lookback` table. Expected outcome: rows present for the latest fact date; `retail_price_day1` is non-NULL for rows with a D-1 match.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Add `fact_prices_lookback.csv` to Core Data Entities table; update Data Lineage Summary to show derivation from last 3 fact CSVs; add note on empty-string semantics for lookback columns and promo_price ambiguity.

## Questions & Decisions

**Q001**: What should be the output format and location of the new lookback table?
- [ ] Option A: Single flat file `data/schema/fact_prices_lookback.csv`, fully rebuilt on each transform run from the latest D fact file enriched with D-1 and D-2 lookback. *(recommended)*
- [ ] Option B: Date-partitioned folder `data/schema/facts_lookback/YYYY-MM-DD.csv`, one file per date D, each computed from D, D-1, D-2 — same incremental skip-if-exists logic as existing facts.
- [ ] Other: ___
> Answer: 

**Q002**: Should `src/load_supabase.py` be updated to upload the new lookback table to Supabase?
- [ ] Option A: Yes — provision a new `fact_prices_lookback` Supabase table and truncate+reinsert rows from the local lookback CSV on each sync run. *(recommended)*
- [ ] Option B: No — the Supabase sync scope is unchanged; the lookback table is local-only.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/transform.py` | Modified | New `LOOKBACK_HEADER` constant, `load_fact_dict` helper, `build_lookback_table` function added; `build_lookback_table` called from `main()` |
| `data/schema/fact_prices_lookback.csv` | Created | New derived lookback artifact; fully replaced on each transform run |
| `src/load_supabase.py` | Modified | New DDL for `fact_prices_lookback` table; `_ENSURE_NULLABLE_DDL` entries; new `insert_lookback` function called from `main()` |
| `.aib_memory/context.md` | Modified | New artifact documented in Core Data Entities; Data Lineage Summary updated |
| `data/schema/facts/*.csv` (63 files) | Read-only dependency | Used as sources for lookback table computation; must not be modified |

## Internal Review of Request and Product Docs

- OK: `request.md § Goal` — Clearly states the new derived table approach and the immutability constraint on all 63 existing fact CSVs.
- OK: `request.md § Background` — Rationale (eliminating cross-file joins) remains valid; unchanged.
- OK: `request.md § Scope` — Scope bullets are internally consistent after amendment; existing fact CSVs explicitly excluded from modification.
- Ambiguity: `request.md § Scope` — Supabase update (Q002) is conditionally scoped; the Scope describes the Supabase work assuming Q002 → Option A; resolution required via Q002 before implementation.
- Ambiguity: `request.md § Scope` — Output location of the new table (Q001) defaults to a flat file in the Plan; a date-partitioned folder is a documented alternative; user decision needed before implementation.
- OK: `request.md § Out of scope` — Explicitly lists no changes to existing 63 fact CSVs; consistent with amendment.
- OK: `request.md § Constraints` — All constraints are compatible with the new approach; "always regenerate" behavior of lookback CSV is noted.
- Cross-ref issue: `request.md § Constraints` — Atomic writes constraint now explicitly covers `fact_prices_lookback.csv`; this has been added to the Constraints text.
- OK: `request.md § Success criteria` — Criteria are measurable and aligned with the amended scope.
- OK: `.aib_memory/context.md` (REF-0001) — Current context only lists the 7-column fact entity; `fact_prices_lookback` is not yet documented. Task 4 addresses this.
- OK: `.aib_brain/Concepts.md` (REF-0002) — No contradictions found; defines AIB framework, not product schema.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/transform.py` | Modified | Add `load_lookback_dict` helper; extend `FACT_HEADER`; update `build_schema` to load prior-day dicts per ZIP and append four lookback values to each fact row |
| `src/load_supabase.py` | Modified | Add four new `NUMERIC(12,4)` columns to `fact_prices` in `_CREATE_DDL`; add `ADD COLUMN IF NOT EXISTS` migration statements to `_ENSURE_NULLABLE_DDL`; extend `insert_fact_day` column list from 7 to 11 columns to populate lookback values in the remote table |
| `data/schema/facts/*.csv` | Modified | All 63 existing fact files must be force-regenerated with the new 11-column schema |
| `.aib_memory/context.md` | Modified | Update fact schema description in Core Data Entities table |
| `config.ini` | Modified | Set `last_processed_date = 2026-02-15` to trigger full force re-process; reset by script on completion |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal is precise and scoped; all 14 mandatory sections present; sections 1–6 non-empty.
- OK: `.aib_memory/context.md` — `FACT_HEADER` and fact grain documented accurately; confirms 7 current columns.
- Ambiguity: `request.md § Constraints` — "empty string" vs "NULL" is the chosen representation. This aligns with the existing `promo_price` convention (empty string when absent) but differs from the strict SQL NULL semantics of the Supabase column (which will be PostgreSQL NULL). This dual representation (empty string in CSV, NULL in DB) is the existing pattern for `retail_price` and `promo_price` and is consistent — no action needed beyond documenting in context.md.
- Missing info: No test covers the edge case where a prior-day fact file is partially written (e.g., interrupted during atomic write, leaving a `.partial` file). The lookup function should only read `.csv` files (not `.partial`), which is guaranteed by using `FACTS_DIR / f"{d_str}.csv"` directly. No action needed.
- Cross-ref issue (resolved): `src/load_supabase.py` `insert_fact_day` function uses `csv.DictReader` with a hardcoded 7-column list (`date_key`, `store_key`, `file_key`, `category_key`, `product_key`, `retail_price`, `promo_price`). Confirmed via code inspection (line 281). The four new columns must be added to this list so the INSERT populates them. Task 3 of the Plan has been updated to include this step.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The proposed change follows the existing fact-extension pattern cleanly: `FACT_HEADER` is the single schema definition point; `build_schema` is the single write path; adding a per-ZIP lookback dict load is architecturally consistent with how the transform already handles in-memory dimension upsert. The `load_lookback_dict` helper is a clean single-responsibility function. The force re-process mechanism already supports full historical regeneration — no bespoke backfill scripting is needed.
- Concern: Peak RAM of ~800 MB for two prior-day dicts is significant for a local single-process pipeline. Recommend per-ZIP dict creation (create, use, release per iteration) over a global pre-load approach.
- Concern: `insert_fact_day` in `load_supabase.py` must also be updated to include the four new columns in its INSERT statement.
- Concern: The `DIM_TABLES` list in `load_supabase.py` handles dimension upsert; the fact insert is handled separately. Verify that `insert_fact_day` reads the fact CSV column-by-name and includes the four new columns in the INSERT list.
- Risk: Without a schema migration for the existing remote `fact_prices` table, old uploaded rows will have NULL for the four new columns. This is accepted — re-upload of fact data is operator-triggered.

### Product Owner

The request is well-stated and the scope is clearly bounded. Adding lookback columns directly in the fact file directly improves analyst productivity by eliminating cross-file join complexity — a concrete, measurable benefit. Success criteria are testable and specific. The force re-process requirement is a known operational cost (full ~63-ZIP re-run) that the operator must plan for.
- Concern: The documentation (context.md) must clearly communicate that empty `retail_price_day1` can mean either "product not present on prior day" or "prior-day file does not exist" — consumers need to understand this limitation.
- Concern: The `promo_price_day1/day2` columns inherit the same ambiguity as `promo_price` today (empty = no promo OR no prior-day match). This is acceptable but should be explicitly noted in documentation.

### User (Data Analyst)

This change eliminates the need to manually join `data/schema/facts/2026-03-15.csv` with `data/schema/facts/2026-03-14.csv` to compute yesterday's price. Loading a single file in pandas or DuckDB and immediately having `retail_price_day1` is a significant usability improvement.
- Positive: Works with spreadsheet tools that cannot perform cross-file joins.
- Concern: Empty string for "no prior-day data" may be misinterpreted as 0 or NULL by some spreadsheet tools. Analysts should be advised to treat empty as NULL/missing in their tool.
- Concern: For the first two dates (2026-02-15 and 2026-02-16), day1/day2 columns being empty may confuse analysts who do not know the dataset starts there.

### Security Officer

No new attack surface introduced. This change reads from local filesystem CSVs (already trusted within the pipeline security boundary) and writes to the same CSVs. The Supabase DDL migration uses `ADD COLUMN IF NOT EXISTS` — a strictly additive, non-destructive DDL operation. No credentials, PII, or sensitive data is introduced by this change.
- Observation: The four new columns carry the same data classification as existing `retail_price` and `promo_price` columns — publicly available government retail price data. No elevated data protection requirements.

### Data Governance Officer

Adding derived columns (lookback prices) to the fact table changes the provenance structure: these columns are not directly sourced from the raw ZIP archives but are computed from prior fact files which are themselves derived from the ZIPs. This derivation chain should be documented in `context.md` under Data Lineage Summary.
- Concern: If a prior-day fact file is regenerated (e.g., due to a source data correction), the lookback columns in all subsequent days pointing to that prior day will become stale and incorrect. The operator must be aware that correcting historical data requires re-running transform from the corrected date forward.
- Concern: The Data Lineage Summary in context.md currently shows a two-hop lineage (ZIP → fact). The four new columns add a fact-to-fact derivation hop that must be documented: `facts/D-1.csv → facts/D.csv (day1 columns)`. This must be updated in context.md.
- Recommendation: Add a note in context.md that `retail_price_day1/day2` and `promo_price_day1/day2` are **derived columns** (computed from prior fact files) and not original source values.

