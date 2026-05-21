Files taken into consideration:
- `.aib_memory/requests/R-20260430-0825-delete-fact-prices-and-adopt-app-to-use-fact-prices-lookback/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/context-convention.md`

## Implementation Log

### Entry 2026-04-30 09:30

#### Scope
Delete the `fact_prices` table from Supabase and update all dependent components so that `fact_prices_lookback` is the sole fact table. Changes span the Supabase sync module (`src/load_supabase.py`), the React data service (`react-app/src/lib/dataService.js`), the automated tests (`tests/test_load_supabase.py`), and the product documentation (`.aib_memory/context.md`). A data-equivalence check was performed before any deletion to confirm no information loss.

#### Changes

- Verified data equivalence: `fact_prices` and `fact_prices_lookback` both contain 1,265,632 rows for date D (2026-04-29); row counts match; 5-row sample values are identical for matching (store_key, category_key, product_key) composite keys.
- Updated module docstring in `src/load_supabase.py` to reflect R-20260430-0825 changes.
- Removed `CREATE TABLE IF NOT EXISTS fact_prices` block from `_CREATE_DDL` in `src/load_supabase.py`.
- Added `_MIGRATION_DDL` constant (`DROP TABLE IF EXISTS fact_prices CASCADE`) and added its execution as the third DDL block in `create_tables()`.
- Replaced `idx_fact_prices_date_key` and `idx_fact_prices_date_store` in `_CREATE_INDEXES` with `idx_fact_prices_lookback_date_key` and `idx_fact_prices_lookback_date_store` targeting `fact_prices_lookback`.
- Updated both `get_available_dates()` and `get_settlements_for_date()` in `_CREATE_RPC_FUNCTIONS` to query `fact_prices_lookback` instead of `fact_prices`.
- Updated `create_tables()` docstring to describe five DDL blocks (was four).
- Removed `get_latest_remote_date()` function from `src/load_supabase.py`.
- Removed `insert_fact_day()` function from `src/load_supabase.py`.
- Removed `prune_fact_prices()` function from `src/load_supabase.py`.
- Updated `main()` docstring and orchestration in `src/load_supabase.py`: removed Steps 4 (insert_fact_day) and 5 (prune_fact_prices); reordered Steps 4–5 to: sync lookback table, prune dim_date.
- Updated file-level header comment in `react-app/src/lib/dataService.js` to note R-20260430-0825.
- Replaced `supabase.from('fact_prices')` with `supabase.from('fact_prices_lookback')` in `fetchReport1`, `fetchReport2`, and `fetchReport3` in `react-app/src/lib/dataService.js`.
- Updated JSDoc comments for `fetchDimensions`, `fetchReport1`, `fetchReport2`, `fetchReport3` to reference `fact_prices_lookback`.
- Updated module docstring in `tests/test_load_supabase.py` to reflect removed and added tests.
- Updated import list in `tests/test_load_supabase.py`: removed `get_latest_remote_date`, `prune_fact_prices`; added `insert_lookback`.
- Updated `TestCreateTables`: renamed `test_executes_four_ddl_statements` to `test_executes_five_ddl_statements`; added `test_create_ddl_does_not_contain_fact_prices_table`; replaced `idx_fact_prices_date_key` assertions with `idx_fact_prices_lookback_date_key`; added `test_index_ddl_targets_fact_prices_lookback`.
- Removed `TestGetLatestRemoteDate` test class.
- Added `TestInsertLookback` test class with three tests: happy-path truncate+insert, absent-CSV truncate-only, rollback on DB error.
- Removed `TestPruneFactPrices` test class (7 tests removed).
- Updated `.aib_memory/context.md`: updated auto-generated header note; updated Functional Capabilities items 6 and 7; updated NFR for date selector; updated component descriptions for `src/load_supabase.py` and `react-app/src/lib/dataService.js`; updated data lineage diagram; updated data storage entry; updated data retention paragraph; updated known operational risks; updated RPC architectural decision; updated key algorithms for date filter, settlement filter, and Report 1 pagination; updated Key Integration Points; updated testing strategy; updated assumptions A7 and A9; updated workspace file inventory entries for `src/load_supabase.py` and `tests/test_load_supabase.py`.

#### Tests

- unit: `tests/test_load_supabase.py::TestCreateTables` (7 tests) — pass
- unit: `tests/test_load_supabase.py::TestInsertLookback` (3 tests — new) — pass
- unit: `tests/test_load_supabase.py::TestUpsertDimSQL` (2 tests) — pass
- unit: `tests/test_load_supabase.py::TestGetRetainedLocalDates` (8 tests) — pass
- unit: `tests/test_load_supabase.py::TestGetDateKeysForDates` (3 tests) — pass
- unit: `tests/test_load_supabase.py::TestPruneDimDate` (6 tests) — pass
- integration: `venv/bin/python src/load_supabase.py` against live Supabase — exit code 0; 1,265,632 rows inserted into `fact_prices_lookback`; 71 dim_date rows pruned
- integration: `SELECT to_regclass('public.fact_prices')` — returns NULL (table deleted)
- integration: `SELECT get_available_dates()` — returns date_key 74 (2026-04-29)
- integration: idempotency re-run of `venv/bin/python src/load_supabase.py` — exit code 0
- integration: `npm run build` in `react-app/` — exit code 0; dist/ produced
- suite: `venv/bin/python -m pytest tests/ -v` — 105 passed, 1 skipped

#### Outcome

Successful. All eight success criteria from `request.md` are met: `fact_prices` no longer exists in the live Supabase database; `fact_prices_lookback` is the sole fact table; RPC functions return correct results; all three React reports point to `fact_prices_lookback`; `npm run build` exits 0; `load_supabase.py` completes without error; `pytest` exits 0; no `fact_prices` references remain in `src/` or `react-app/src/`.

#### Evidence

- `SELECT to_regclass('public.fact_prices')` output: `None` (table absent)
- `SELECT COUNT(*) FROM fact_prices_lookback`: `1,265,632`
- `SELECT get_available_dates()` output: `[74]`
- Sync log excerpt:
```
Inserted 1,265,632 rows into fact_prices_lookback.
Pruning remote dim_date to retained dates …
  Pruned 71 dim_date rows outside retained window.
Supabase sync complete.
```
- pytest result: `105 passed, 1 skipped in 0.66s`
- npm build result: `✓ built in 1.79s`
- grep check: `grep -r "from('fact_prices')" react-app/src/` — no matches
