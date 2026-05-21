## Goal

Delete the `fact_prices` table from Supabase and update all dependent components — ETL sync script, PostgreSQL RPC helper functions, B-tree indexes, and React app data-fetching layer — to use `fact_prices_lookback` as the sole fact storage, eliminating the redundant dual-fact-table pattern.

## Background

The Supabase database currently holds two fact tables:

- **`fact_prices`** — the rolling-retention fact table: provisioned and populated by `src/load_supabase.py` with the latest 3 local fact dates (date D, D-1, D-2). It has 7 columns: `date_key`, `store_key`, `file_key`, `category_key`, `product_key`, `retail_price`, `promo_price`. It is indexed by two B-tree indexes (`idx_fact_prices_date_key`, `idx_fact_prices_date_store`) and queried by two RPC functions (`get_available_dates`, `get_settlements_for_date`). All three React app reports query this table exclusively.

- **`fact_prices_lookback`** — a derived enriched snapshot: produced by `src/transform.py`'s `build_lookback_table` and synced by `src/load_supabase.py`'s `insert_lookback` (TRUNCATE + full reinsert each run). It has 11 columns — the 7 `fact_prices` base columns plus `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`. It currently contains only rows for the **latest date D** (not for D-1 or D-2), enriched with D-1 and D-2 prices as lookup columns. It is not queried by any React app report.

The user observes that both tables store similar information and wants to consolidate on `fact_prices_lookback`, deleting `fact_prices` and adopting the application to not depend on it. A pre-condition check for information loss between the two tables is explicitly requested before deletion.

## Scope

- Verify column-level and row-level equivalence between `fact_prices` and `fact_prices_lookback` for the base 7 columns of the current date D.

- Remove `fact_prices` DDL (CREATE TABLE statement) from `_CREATE_DDL` in `src/load_supabase.py`.

- Remove `_CREATE_INDEXES` DDL for `idx_fact_prices_date_key` and `idx_fact_prices_date_store`; provision equivalent indexes on `fact_prices_lookback`.

- Remove `insert_fact_day`, `prune_fact_prices` calls and associated helper functions from `src/load_supabase.py`.

- Update RPC functions `get_available_dates()` and `get_settlements_for_date()` in `_CREATE_RPC_FUNCTIONS` to query `fact_prices_lookback` instead of `fact_prices`.

- Update `react-app/src/lib/dataService.js` — `fetchReport1`, `fetchReport2`, `fetchReport3` — to query `fact_prices_lookback` instead of `fact_prices`.

- Drop the `fact_prices` table from the live Supabase database via a `DROP TABLE IF EXISTS` DDL executed in `create_tables()` or a dedicated migration step.

- Update `src/load_supabase.py` `main()` orchestration to remove all `fact_prices` sync steps.

- Update automated tests in `tests/test_load_supabase.py` to reflect removed functions and updated DDL.

- Update `context.md` and `references.md` documentation to reflect the consolidation.

## Out of scope

- Changes to `src/transform.py` or `build_lookback_table` logic (the local `fact_prices_lookback.csv` artifact is unchanged).

- Changes to `src/extract.py` or the download pipeline.

- Changes to `data/schema/facts/` date-partitioned fact CSV files.

- Changes to star-schema dimension tables or their Supabase sync logic.

- Adding new React reports or changing the visual design of existing reports.

- Enabling display of `retail_price_day1` / `promo_price_day1` / `retail_price_day2` / `promo_price_day2` lookback columns in the React app UI (not requested).

## Constraints

- No live Supabase `DROP TABLE` must execute before verifying that `fact_prices_lookback` contains equivalent data for the current date D.
- FK constraints: `fact_prices.date_key → dim_date.date_key`; dropping `fact_prices` first satisfies any FK ordering concern (dim_date is retained).
- `fact_prices_lookback` currently covers only date D; after migration the date selector in the React app will show only D (unless the scope is extended — see `## Questions & Decisions`).
- The rolling retention pruning logic for `fact_prices` must be cleanly removed without breaking the `prune_dim_date` step, which is still needed.
- Python 3.9+ compatibility required for all changes to ETL scripts.
- `npm run build` for the React app must exit 0 after `dataService.js` changes.

## Success criteria

1. `src/load_supabase.py` no longer references `fact_prices` in DDL, insert, or prune operations after the migration.
2. The live Supabase `fact_prices` table is dropped (or absent from the schema after a fresh provisioning run).
3. `get_available_dates()` and `get_settlements_for_date()` RPC functions query `fact_prices_lookback` and return correct results.
4. All three React app reports (Report 1, Report 2, Report 3) return correct data for the current date D when querying `fact_prices_lookback`.
5. `npm run build` exits 0 with no console errors related to the table migration.
6. `venv/bin/python src/load_supabase.py` completes without error after the migration.
7. `python -m pytest tests/` exits 0 after test updates.
8. No `fact_prices` references remain in application source files (`src/`, `react-app/src/`).

## Assumptions

- A1: `fact_prices_lookback` is a strict superset of `fact_prices` for date D — the base 7 columns are identical for matching (store_key, category_key, product_key) keys in date D. Risk if false: report results would diverge after migration, requiring a reconciliation step before go-live.

- A2: `prune_dim_date` can remain in `load_supabase.py` with its existing logic unchanged; the retained date_keys will now be derived exclusively from `dim_date` and local CSV filenames, with no dependency on `fact_prices`. Risk if false: `dim_date` would not be pruned correctly, causing the date selector to show stale dates.

- A3: The live Supabase database does not have any additional objects (views, materialised views, triggers, foreign keys from other tables) that depend on `fact_prices` beyond what is documented in `context.md`. Risk if false: `DROP TABLE fact_prices CASCADE` may silently drop undocumented dependent objects.

- A4: `react-app/src/lib/dataService.js` can query `fact_prices_lookback` using the identical column selectors currently used for `fact_prices` (`category_key`, `retail_price`, `promo_price`, `product_key`, `store_key`), because these 7 base columns are present in `fact_prices_lookback`. Risk if false: query execution would fail with a column-not-found error.

- A5: The `@supabase/supabase-js` client exposes `fact_prices_lookback` automatically via PostgREST without any additional configuration, as all Supabase tables are auto-exposed via the REST API under default settings. Risk if false: additional Supabase dashboard configuration may be required.

- A6: The user accepts that the date selector in the React app will show only the current date D after migration (since `fact_prices_lookback` covers only D). This assumption will be confirmed or rejected by Q001.
  - Risk if false: scope expands to include changes to `build_lookback_table` in `src/transform.py` to emit rows for all 3 retained dates.

## Plan

### Task 1: Verify data equivalence and document findings
**Intent:** Confirm that `fact_prices_lookback` contains the same base data as `fact_prices` for date D by querying Supabase and comparing row counts and a sample of values.
**Inputs:** Live Supabase database; `DATABASE_URL` from `.env`.
**Outputs:** Console output confirming row count match and sample value comparison; documented finding in implementation.md.
**External Interfaces:** Supabase PostgreSQL via psycopg2.
**Environment & Configuration:** `.env` with `DATABASE_URL`; `venv/bin/python`.
**Procedure:**
1. Connect to Supabase via psycopg2.
2. Query `SELECT COUNT(*) FROM fact_prices WHERE date_key = (SELECT MAX(date_key) FROM fact_prices)`.
3. Query `SELECT COUNT(*) FROM fact_prices_lookback WHERE date_key = (SELECT MAX(date_key) FROM fact_prices_lookback)`.
4. Compare row counts and log result.
5. Query a sample of 5 rows from both tables for date D, comparing `retail_price` and `promo_price`.
6. Record findings in implementation.md.
**Done Criteria:** Row counts match; sample values are identical for the same (store_key, category_key, product_key) composite keys.
**Dependencies:** None.
**Risk Notes:** If counts differ, halt and investigate before proceeding with any deletion.

### Task 2: Update load_supabase.py DDL and provisioning
**Intent:** Remove all `fact_prices` references from `_CREATE_DDL`, `_CREATE_INDEXES`, `_CREATE_RPC_FUNCTIONS`, and `_ENSURE_NULLABLE_DDL`; add a migration DDL step to drop `fact_prices`; add equivalent indexes on `fact_prices_lookback`.
**Inputs:** `src/load_supabase.py`.
**Outputs:** Modified `src/load_supabase.py`.
**External Interfaces:** Supabase PostgreSQL (DDL execution).
**Environment & Configuration:** `venv/bin/python`.
**Procedure:**
1. Remove `CREATE TABLE IF NOT EXISTS fact_prices (...)` block from `_CREATE_DDL`.
2. Add `DROP TABLE IF EXISTS fact_prices CASCADE;` as a `_MIGRATION_DDL` constant and execute it in `create_tables()`.
3. Replace `idx_fact_prices_date_key` and `idx_fact_prices_date_store` in `_CREATE_INDEXES` with equivalent indexes on `fact_prices_lookback`.
4. Update `_CREATE_RPC_FUNCTIONS` to replace `FROM fact_prices` with `FROM fact_prices_lookback` in both `get_available_dates()` and `get_settlements_for_date()`.
5. Remove `_ENSURE_NULLABLE_DDL` lines that reference `fact_prices_lookback ADD COLUMN IF NOT EXISTS` (already applied; keep remaining lines).
**Done Criteria:** `_CREATE_DDL` contains no `fact_prices` CREATE; `_MIGRATION_DDL` block drops `fact_prices`; RPC functions reference `fact_prices_lookback`; indexes target `fact_prices_lookback`.
**Dependencies:** Task 1 (equivalence confirmed).
**Risk Notes:** Test on non-production Supabase instance if available.

### Task 3: Remove fact_prices insert and prune logic from load_supabase.py
**Intent:** Remove `insert_fact_day`, `prune_fact_prices`, and the related `get_latest_remote_date` orchestration from `main()` in `src/load_supabase.py`.
**Inputs:** `src/load_supabase.py`.
**Outputs:** Modified `src/load_supabase.py`.
**External Interfaces:** None (code removal only).
**Environment & Configuration:** None.
**Procedure:**
1. Remove `insert_fact_day` function.
2. Remove `prune_fact_prices` function.
3. Remove `get_latest_remote_date` function (no longer needed).
4. Remove the `get_latest_remote_date` / `insert_fact_day` / `prune_fact_prices` call blocks from `main()`.
5. Retain `get_retained_local_dates`, `get_date_keys_for_dates`, and `prune_dim_date` (still needed).
**Done Criteria:** No `fact_prices` references remain in `src/load_supabase.py` except in `_MIGRATION_DDL`; `main()` runs without errors.
**Dependencies:** Task 2.
**Risk Notes:** `get_latest_local_date` may still be used — verify before removing.

### Task 4: Update React app dataService.js
**Intent:** Replace all `supabase.from('fact_prices')` calls with `supabase.from('fact_prices_lookback')` in `react-app/src/lib/dataService.js`.
**Inputs:** `react-app/src/lib/dataService.js`.
**Outputs:** Modified `react-app/src/lib/dataService.js`.
**External Interfaces:** Supabase PostgREST via `@supabase/supabase-js`.
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in `.env`.
**Procedure:**
1. Replace `supabase.from('fact_prices')` with `supabase.from('fact_prices_lookback')` in `fetchReport1`.
2. Replace `supabase.from('fact_prices')` with `supabase.from('fact_prices_lookback')` in `fetchReport2`.
3. Replace `supabase.from('fact_prices')` with `supabase.from('fact_prices_lookback')` in `fetchReport3`.
**Done Criteria:** `grep -r "from('fact_prices')" react-app/src/` returns zero matches; `npm run build` exits 0.
**Dependencies:** Task 2 (RPC functions updated).
**Risk Notes:** Column interface is identical; no select() restructuring required.

### Task 5: Update automated tests
**Intent:** Remove test references to deleted functions (`insert_fact_day`, `prune_fact_prices`, `get_latest_remote_date`) and update DDL content assertions to match the new `_CREATE_DDL`; add a test for `insert_lookback`.
**Inputs:** `tests/test_load_supabase.py`.
**Outputs:** Modified `tests/test_load_supabase.py`.
**External Interfaces:** None (unit tests with mocks).
**Environment & Configuration:** `venv/bin/python -m pytest`.
**Procedure:**
1. Remove imports and test cases for deleted functions.
2. Update `_CREATE_DDL` content assertions to not reference `fact_prices`.
3. Add a test for `insert_lookback` covering: happy path (rows inserted); empty CSV edge case (TRUNCATE, 0 inserts).
4. Run `venv/bin/python -m pytest tests/ -v` and confirm all tests pass.
**Done Criteria:** `pytest` exits 0; no test references removed functions; `insert_lookback` is covered.
**Dependencies:** Tasks 2–3.
**Risk Notes:** Ensure `_CREATE_INDEXES` assertions updated for `fact_prices_lookback` indexes.

### Task 6: Run live sync and validate
**Intent:** Execute `load_supabase.py` against the live Supabase database and verify that `fact_prices` is dropped, `fact_prices_lookback` is populated, and RPC functions return correct results.
**Inputs:** Live `.env`; updated `src/load_supabase.py`.
**Outputs:** Console log; implementation.md entry.
**External Interfaces:** Supabase PostgreSQL.
**Environment & Configuration:** `DATABASE_URL` in `.env`.
**Procedure:**
1. Run `venv/bin/python src/load_supabase.py`.
2. Verify exit code 0.
3. Query `SELECT to_regclass('public.fact_prices')` — expect NULL.
4. Query `SELECT COUNT(*) FROM fact_prices_lookback` — expect non-zero.
5. Call `SELECT get_available_dates()` — expect at least 1 row.
**Done Criteria:** All checks pass; exit code 0 on re-run (idempotency).
**Dependencies:** Tasks 2–4.

### Task 7: Validate React app and run build
**Intent:** Confirm `npm run build` succeeds and the React app works correctly against `fact_prices_lookback`.
**Inputs:** Updated `react-app/src/lib/dataService.js`; Supabase with `fact_prices_lookback`.
**Outputs:** `react-app/dist/`.
**External Interfaces:** Supabase PostgREST.
**Environment & Configuration:** `.env` with Vite env vars.
**Procedure:**
1. Run `cd react-app && npm run build` — expect exit 0.
2. Run `npm run preview` (or menu option 6) and open the app.
3. Check date selector shows the available date(s).
4. Load Report 1, 2, 3 for the available date.
5. Check browser console for errors.
**Done Criteria:** Build exits 0; all three reports render with data; no console errors referencing `fact_prices`.
**Dependencies:** Task 4.

### Task 8: Update context.md and documentation
**Intent:** Update `context.md` to reflect single-fact-table architecture; remove `fact_prices` references from component descriptions and integration points.
**Inputs:** `.aib_memory/context.md`.
**Outputs:** Updated `.aib_memory/context.md`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Update the `src/load_supabase.py` component description to remove `fact_prices` provisioning, insert, and prune references.
2. Update the `react-app/src/lib/dataService.js` component description to reference `fact_prices_lookback`.
3. Update the RPC function descriptions to reference `fact_prices_lookback`.
4. Update the data architecture table to remove `fact_prices` row.
5. Update the star-schema data flow diagram description.
**Done Criteria:** No `fact_prices` (without `_lookback` suffix) references remain in `context.md`.
**Dependencies:** Tasks 2–4.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Remove all `fact_prices` component descriptions and data flow references; update to single-fact-table (`fact_prices_lookback`) architecture.

## Questions & Decisions

**Q001**: `fact_prices_lookback` currently contains only date D (the latest date). `fact_prices` contains 3 dates (D, D-1, D-2). After migration, the React app date selector will show only 1 date instead of 3. Is this information loss acceptable, or should `fact_prices_lookback` be extended to cover all 3 retained dates before deleting `fact_prices`?
- [ ] Option A: Accept single-date-only — migrate as-is; date selector will show only date D. Scope stays within `src/load_supabase.py` and `react-app/src/lib/dataService.js`. *(recommended if multi-date browsing is not used)*
- [ ] Option B: Extend `fact_prices_lookback` to cover all 3 retained dates — requires changes to `src/transform.py`'s `build_lookback_table` to emit rows for D, D-1, and D-2; then migrate. Scope expands significantly.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/load_supabase.py` | Modified | Remove `fact_prices` DDL, insert, prune functions; update RPC DDL and indexes; add migration DROP TABLE |
| `react-app/src/lib/dataService.js` | Modified | Replace `'fact_prices'` with `'fact_prices_lookback'` in fetchReport1, fetchReport2, fetchReport3 |
| `tests/test_load_supabase.py` | Modified | Remove tests for deleted functions; update DDL assertions; add `insert_lookback` test |
| `.aib_memory/context.md` | Modified | Remove `fact_prices` references; update to single-fact-table architecture description |
| Supabase `fact_prices` table | Deleted | Dropped via `DROP TABLE IF EXISTS fact_prices CASCADE` in migration DDL |
| Supabase `fact_prices_lookback` table | Modified | New indexes added (`idx_fact_prices_lookback_date_key`, `idx_fact_prices_lookback_date_store`) |
| Supabase `get_available_dates()` RPC | Modified | Updated to `SELECT DISTINCT date_key FROM fact_prices_lookback` |
| Supabase `get_settlements_for_date()` RPC | Modified | Updated to join `fact_prices_lookback` instead of `fact_prices` |
| `src/load_supabase.py` `_ENSURE_NULLABLE_DDL` | Modified | Review ADD COLUMN IF NOT EXISTS guards (already applied; may be simplified) |

## Internal Review of Request and Product Docs

- OK: `request.md` — All 12 mandatory sections present and in order; sections 1–6 are non-empty and content is derived from `input.md`.
- Ambiguity: `input.md` — "Check if there is no loss of information between those two tables" does not define what counts as acceptable loss (e.g., losing multi-date browsing). Resolved by raising Q001.
- Missing info: `request.md` — The request does not specify whether the live Supabase `DROP TABLE` should occur as part of the sync DDL or as a manual operation. Resolved in Plan as a `_MIGRATION_DDL` block in `create_tables()`.
- Cross-ref issue: `context.md` — References to `fact_prices` in "Key Integration Points" section (`Supabase REST API (external, inbound to React app): queries fact_prices, dim_*`) will be outdated after migration. Flagged in Documentation section.
- OK: `references.md` — REF-0001 (`context.md`) is the only product-doc; correctly identifies it as the primary reference.
- Ambiguity: `request.md` — Note on "loockback" (misspelling of "lookback") in the original input — interpreted as `fact_prices_lookback`; no functional ambiguity.
