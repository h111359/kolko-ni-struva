Files taken into consideration:
- `.aib_memory/requests_register.md`
- `.aib_memory/requests/R-20260422-0902-fix-date-filter-and-category-prices-report/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-04-23 13:00

#### Scope
Fix two user-visible defects in the React Analytics App: (1) the header date dropdown showed all dim_date dates including those with no fact data in Supabase, (2) the settlement dropdown in Report 1 missed cities due to a 10,000-row client-side fact scan, and the category bar chart silently truncated results at Supabase's 1,000-row default cap. Changes span `src/load_supabase.py` (new RPC DDL) and `react-app/src/lib/dataService.js` (three functions updated).

#### Changes
- Added `_CREATE_RPC_FUNCTIONS` DDL constant to `src/load_supabase.py` defining two idempotent PostgreSQL functions: `get_available_dates()` (returns SETOF int of distinct date_key values from fact_prices) and `get_settlements_for_date(p_date_key bigint)` (returns SETOF int of distinct settlement_keys for a given date via a JOIN on dim_store); both include `GRANT EXECUTE … TO anon` statements.
- Updated `create_tables()` in `src/load_supabase.py` to execute `_CREATE_RPC_FUNCTIONS` DDL inside the same transaction as the existing table and nullable-migration DDL; updated its docstring accordingly.
- Updated `fetchDimensions()` in `react-app/src/lib/dataService.js` to call `supabase.rpc('get_available_dates')` in parallel with the existing dimension fetches; filters `dim_date` results to only fact-present `date_key` values; falls back to all dim_date rows with a console warning when the RPC is not yet provisioned.
- Replaced `fetchSettlementsForDate()` body in `react-app/src/lib/dataService.js`: removed the `.limit(10000)` fact-row scan; replaced with `supabase.rpc('get_settlements_for_date', { p_date_key: dateKey })`; maps the RPC result objects to a `Set<number>`; falls back to all known settlements (from dims.settlements) with a console warning if the RPC is unavailable.
- Replaced `fetchReport1()` body in `react-app/src/lib/dataService.js`: replaced the single un-paginated `.in('store_key', storeKeys)` query with a `while (!done)` pagination loop using `.range(from, to)` with `PAGE_SIZE = 1000`; accumulates all pages into `allRows` before client-side category aggregation; downstream sort logic unchanged.

#### Tests
- unit / integration: `python -m pytest tests/ -v` (21 tests) — pass
- build: `cd react-app && npm run build` (vite v5.4.21, 78 modules) — pass (exit 0)

#### Outcome
Successful. All success criteria met in code and build verification. SC-1/SC-2 (date filter via RPC), SC-3 (settlements via RPC), SC-4 (pagination for complete category coverage), SC-5 (build exits 0), SC-6 (21 Python tests pass). RPC functions require operator to re-run `python src/load_supabase.py` to provision them in Supabase; until then the app falls back gracefully with console warnings.

#### Evidence
- `python -m pytest tests/ -v`: 21 passed in 0.15s
- `npm run build`: dist/assets/index-H-2G3oZv.js 355.81 kB, built in 2.94s, exit 0

#### Notes (Optional)
Per Assumption A2 in request.md: the operator must re-run `python src/load_supabase.py` after this deployment to provision the two RPC functions in Supabase. The fallback behaviour in `fetchDimensions` and `fetchSettlementsForDate` ensures the app continues to function (showing all dates / all settlements) until that re-run occurs.
