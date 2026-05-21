Implementation log for request R-20260512-0529 covering the report-query pushdown refactor.

Files from .aib_memory taken into consideration during this implement run:
- `.aib_memory/request.md`
- `.aib_memory/analysis.md`
- `.aib_memory/context.md`
- `.aib_memory/requests_register.md`

## Implementation Log

### Entry 2026-05-12 08:05
#### Scope
Implemented the performance refactor for the slow React report pages by moving Report 1 aggregation and Report 2/3 enrichment into Supabase/PostgreSQL RPC functions. Updated the React data layer to consume those RPCs with lookback-aware routing, preserved compatibility fallbacks for unreprovisioned databases, and refreshed the operator-facing documentation and product context.

#### Changes
- Added `get_report_1_category_prices`, `get_report_2_rows`, and `get_report_3_rows` to `src/load_supabase.py`, plus the `idx_fpl_date_store_category` index and updated DDL coverage in `tests/test_load_supabase.py`.
- Refactored `react-app/src/lib/dataService.js` so Reports 1, 2, and 3 call RPCs with `current` / `day1` / `day2` lookback offsets instead of paging raw `fact_prices_lookback` rows in the browser.
- Kept compatibility fallback helpers in `react-app/src/lib/dataService.js` so the app still functions, with console warnings, until `src/load_supabase.py` is rerun against the target Supabase instance.
- Replaced obsolete frontend pagination assertions in `react-app/src/lib/dataService.test.js` with report-RPC contract tests covering lookback routing, response mapping, and session query logging.
- Updated `README.md` and `.aib_memory/context.md` to document the seven React-facing RPC functions, the report-query pushdown architecture, and the required reprovisioning step.

#### Tests
- unit: `pytest tests/test_load_supabase.py -q` — pass.
- unit: `cd react-app && npm test -- src/lib/dataService.test.js src/components/Report1.test.jsx src/components/Report2.test.jsx src/components/Report3.test.jsx` — pass.

#### Outcome
Successful. Reports 1, 2, and 3 now prefer database-computed result sets, which removes the main browser-side aggregation and enrichment hotspots while preserving existing lookback-date semantics. Residual risk remains operational rather than functional: the fast path depends on rerunning `python src/load_supabase.py` against the deployed Supabase database so the new RPCs and index exist remotely.

#### Evidence
- Path: `src/load_supabase.py`
- Path: `tests/test_load_supabase.py`
- Path: `react-app/src/lib/dataService.js`
- Path: `react-app/src/lib/dataService.test.js`
- Path: `README.md`
- Path: `.aib_memory/context.md`
- Command output:
```text
pytest tests/test_load_supabase.py -q
44 passed in 1.58s
```
- Command output:
```text
cd react-app && npm test -- src/lib/dataService.test.js src/components/Report1.test.jsx src/components/Report2.test.jsx src/components/Report3.test.jsx
All 45 tests in 4 files passed successfully.
```

#### Notes (Optional)
The deployed React app will fall back to slower client-side processing until the target Supabase environment has been reprovisioned with `python src/load_supabase.py`.