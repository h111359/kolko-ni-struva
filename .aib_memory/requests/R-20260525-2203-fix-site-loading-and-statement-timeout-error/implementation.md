This file records the implementation log for request R-20260525-2203 "Fix site loading and statement timeout error".

AIB memory files consulted:
- `.aib_memory/context.md`
- `.aib_memory/analysis-R-20260525-2203.md`
- `.aib_memory/plan-R-20260525-2203.md`
- `.aib_brain/conventions/coding-general.md`
- `.aib_brain/conventions/coding-python.md`
- `.aib_brain/conventions/coding-javascript.md`
- `.aib_brain/conventions/coding-react.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-05-25 23:00
#### Scope
Fix the statement-timeout error caused by `COUNT(*) OVER()` in `get_landing_page_rows` RPC. Split the single RPC into two separate RPCs — `get_landing_page_rows` (rows only) and `get_landing_page_count` (total count) — so neither query materialises the full filtered result set. Update the data service, component, and all affected tests. Re-provision Supabase to deploy the new function and the updated one.

#### Changes
- Removed `COUNT(*) OVER() AS total_count` from the inner SELECT of the `get_landing_page_rows` SQL function body in `src/load_supabase.py`.
- Added new `get_landing_page_count(INT, INT, INT, INT, INT, TEXT, NUMERIC, NUMERIC) RETURNS BIGINT` SQL function in `src/load_supabase.py` with the same eight filter parameters and identical WHERE clause as `get_landing_page_rows`.
- Added `GRANT EXECUTE ON FUNCTION get_landing_page_count(INT, INT, INT, INT, INT, TEXT, NUMERIC, NUMERIC) TO anon;` in `src/load_supabase.py`.
- Updated comment block above the landing-page RPCs in `src/load_supabase.py` to reference R-20260525-2203 and describe `get_landing_page_count`.
- Updated `fetchLandingPageRows` in `react-app/src/lib/dataService.js`: removed `total_count` extraction from row data; changed return value from `{ rows, totalCount }` to `{ rows }` only; updated inline comment to explain the split.
- Added new exported function `fetchLandingPageCount(filters)` in `react-app/src/lib/dataService.js` that calls the `get_landing_page_count` RPC and returns a `Number`.
- Updated file-level JSDoc header in `react-app/src/lib/dataService.js` to mention R-20260525-2203 and `fetchLandingPageCount`.
- Updated `loadRows` in `react-app/src/components/LandingPage.jsx` to call `fetchLandingPageRows` and `fetchLandingPageCount` in parallel via `Promise.all`.
- Updated named imports in `react-app/src/components/LandingPage.jsx` to include `fetchLandingPageCount`.
- Updated file-level JSDoc header in `react-app/src/components/LandingPage.jsx` to reference R-20260525-2203.
- Updated `vi.mock` factory in `react-app/src/components/LandingPage.test.jsx`: added `fetchLandingPageCount: vi.fn()`.
- Updated named imports in `react-app/src/components/LandingPage.test.jsx` to include `fetchLandingPageCount`.
- Updated `makeRowResult` in `react-app/src/components/LandingPage.test.jsx`: removed `total_count` from row object; changed return shape from `{ rows, totalCount }` to `{ rows }` only.
- Updated `beforeEach` in `react-app/src/components/LandingPage.test.jsx`: added `vi.mocked(fetchLandingPageCount).mockResolvedValue(1)`.
- Updated test 7 in `react-app/src/components/LandingPage.test.jsx`: re-added `vi.mocked(fetchLandingPageCount).mockResolvedValue(1)` after `vi.clearAllMocks()`.
- Updated test 10 in `react-app/src/components/LandingPage.test.jsx`: changed mock shape to `{ rows: [] }` and added `vi.mocked(fetchLandingPageCount).mockResolvedValue(0)`.
- Updated test 11 in `react-app/src/components/LandingPage.test.jsx`: removed `total_count` from individual rows, changed mock shape to `{ rows: manyRows }`, added `vi.mocked(fetchLandingPageCount).mockResolvedValue(250)`.
- Updated `fetchLandingPageRows` tests in `react-app/src/lib/dataService.test.js`: removed `totalCount` assertions from all tests; updated test title/description to reflect rows-only return.
- Added `describe('fetchLandingPageCount', ...)` block in `react-app/src/lib/dataService.test.js` with four tests: correct RPC call with params, throw on error, all-null params, returns 0 when data is null.
- Updated file-level JSDoc in `react-app/src/lib/dataService.test.js` to mention `fetchLandingPageCount` and R-20260525-2203.
- Updated `.aib_memory/context.md`: appended R-20260525-2203 update line documenting the RPC split and all affected files.
- Ran `python src/load_supabase.py` to re-provision Supabase: schema and RPC functions updated (RPCs deployed before the long-running fact data sync).

#### Tests
- unit: `react-app/src/components/LandingPage.test.jsx` — 12 tests — pass
- unit: `react-app/src/lib/dataService.test.js` — 31 tests (including 4 new `fetchLandingPageCount` tests) — pass
- unit: `react-app/src/App.test.jsx` — 8 tests — pass
- integration: `python src/load_supabase.py` — schema provisioned, RPCs deployed, fact sync started — pass

#### Outcome
Successful. `get_landing_page_rows` no longer materialises the full filtered result set; `get_landing_page_count` returns only the total count. Both are called in parallel from `loadRows`. All 51 unit tests pass. Supabase RPCs re-provisioned. The site should load without statement-timeout errors.

#### Evidence
- Test run output:

```
 ✓ src/lib/dataService.test.js (31 tests) 294ms
 ✓ src/App.test.jsx (8 tests) 270ms
 ✓ src/components/LandingPage.test.jsx (12 tests) 972ms

 Test Files  3 passed (3)
      Tests  51 passed (51)
```

- Provisioning run output (excerpt):

```
Connecting to Supabase …
Provisioning schema …
Tables created / verified.
Indexes created / verified.
Upserting dimension tables …
  Upserted 99 rows into dim_date.
  ...
Syncing fact_prices_lookback …
```

#### Notes (Optional)
The root cause was the `COUNT(*) OVER()` window function introduced in R-20260525-1400. The fix follows Option B from analysis decision point DP001: a dedicated count RPC with identical filter parameters. The `loadOptions` Promise.all hardening was assessed as out of scope (DP002, Option A). Aligned with analysis sections "Root Cause", "Chosen Fix", and "Out of scope".
