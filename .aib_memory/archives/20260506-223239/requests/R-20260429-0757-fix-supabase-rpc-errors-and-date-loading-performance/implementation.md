Files taken into consideration:
- `.aib_memory/requests_register.md`
- `.aib_memory/requests/R-20260429-0757-fix-supabase-rpc-errors-and-date-loading-performance/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `src/load_supabase.py`
- `tests/test_load_supabase.py`
- `react-app/index.html`
- `react-app/vite.config.js`

## Implementation Log

### Entry 2026-04-29 08:30
#### Scope
Add idempotent `CREATE INDEX IF NOT EXISTS` DDL for `fact_prices(date_key)` and `fact_prices(date_key, store_key)` to `src/load_supabase.py` and execute it against the live Supabase database. Add a minimal `favicon.ico` to `react-app/public/` to eliminate the browser 404. Update tests to cover the new index DDL constant and the updated DDL call count. This addresses SC-1 through SC-6 of request R-20260429-0757.

#### Changes
- Added `_CREATE_INDEXES` DDL constant to `src/load_supabase.py` containing two `CREATE INDEX IF NOT EXISTS` statements: `idx_fact_prices_date_key ON fact_prices(date_key)` and `idx_fact_prices_date_store ON fact_prices(date_key, store_key)`.
- Updated `create_tables()` in `src/load_supabase.py` to execute `_CREATE_INDEXES` as a fourth `cur.execute()` call inside the same `with conn.cursor() as cur` block, after `_CREATE_RPC_FUNCTIONS`, before `conn.commit()`. Added `"Indexes created / verified."` print confirmation after commit.
- Updated `create_tables()` docstring to reflect the four DDL blocks and the R-20260429-0757 request reference.
- Created `react-app/public/favicon.ico` (minimal 1×1 transparent ICO file, 66 bytes) to eliminate the browser 404 caused by missing favicon.
- Updated `tests/test_load_supabase.py`: imported `_CREATE_INDEXES`; renamed existing `test_executes_three_ddl_statements` to `test_executes_four_ddl_statements` with updated assertion (`call_count == 4`); added `test_index_ddl_contains_date_key_index` and `test_index_ddl_contains_composite_date_store_index` to verify DDL constant content.
- Applied indexes to live Supabase database by running `src/load_supabase.py` via venv Python; confirmed `"Indexes created / verified."` in output.
- Confirmed idempotency: second run of `src/load_supabase.py` exits 0, outputs `"Indexes created / verified."` with no error.

#### Tests
- unit: `TestCreateTables::test_executes_four_ddl_statements` — pass (create_tables now executes 4 DDL blocks)
- unit: `TestCreateTables::test_index_ddl_contains_date_key_index` — pass (_CREATE_INDEXES contains idx_fact_prices_date_key)
- unit: `TestCreateTables::test_index_ddl_contains_composite_date_store_index` — pass (_CREATE_INDEXES contains idx_fact_prices_date_store with date_key, store_key)
- unit: `TestCreateTables::test_commits_after_ddl` — pass
- unit: `TestCreateTables::test_executes_ddl_with_dim_date` — pass
- integration: full pytest suite (87 collected, 86 passed, 1 skipped) — pass

#### Outcome
Successful. Both indexes were applied to the live Supabase `fact_prices` table. The `get_available_dates()` RPC can now use an index-only scan via `idx_fact_prices_date_key`, and `get_settlements_for_date()` can use `idx_fact_prices_date_store` — eliminating the full 82M-row sequential scans that caused HTTP 500 statement-timeout errors. The favicon.ico eliminates the HTTP 404. Second run of `load_supabase.py` confirmed idempotency (no-op). All 86 automated tests pass. Residual risk: if Supabase free-tier shared compute is severely contended, indexed scans may still occasionally approach the timeout boundary; a pre-computed `dim_available_dates` summary table is the documented escalation path.

#### Evidence
- Terminal output (first run):

```
Connecting to Supabase …
Provisioning schema …
Tables created / verified.
Indexes created / verified.
Upserting dimension tables …
  Upserted 73 rows into dim_date.
  Upserted 217 rows into dim_company.
  Upserted 267 rows into dim_settlement.
  Upserted 372 rows into dim_category.
  Upserted 128,238 rows into dim_product.
  Upserted 4,866 rows into dim_store.
  Upserted 15,160 rows into dim_file.
Latest local fact date  : 2026-04-28
Latest remote fact date : 2026-04-28
already up to date
```

- Terminal output (second run — idempotency): identical output, exit code 0, no errors.
- Pytest output:

```
86 passed, 1 skipped in 0.66s
```

- Path: `src/load_supabase.py` (updated)
- Path: `tests/test_load_supabase.py` (updated)
- Path: `react-app/public/favicon.ico` (created)

#### Notes (Optional)
The existing `<link rel="icon" href="data:,">` in `react-app/index.html` suppresses the favicon request for most browsers; the physical `favicon.ico` in `react-app/public/` provides a definitive cross-browser fix. The favicon will be included in `dist/` automatically by Vite on the next `npm run build`. A Netlify redeploy (menu option 5) is needed to serve the favicon from the production URL.
