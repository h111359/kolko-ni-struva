## Goal

Identify and fix the root cause of the local React preview (menu option 6) not showing any data. A JavaScript console error "Failed to load resource: the server responded with a status of 404 (Not Found)" is present. This is a repeating bug that has reportedly been fixed before. All bugs must be found and eliminated, test coverage must be added or improved to prevent regressions, and all existing tests must continue to pass.

## Background

Menu option 6 (`action_local_preview` in `menu.py`) builds the React app via `npm run build` and starts a Vite preview server (`http://localhost:4173`). A previous fix (R-20260426-2150) addressed a race condition where the browser opened before the Vite preview server was ready. That fix used `subprocess.Popen` + TCP port polling (`_wait_for_server()`) to delay opening the browser until the server accepts connections. Despite that fix, the symptom persists: the app appears to load but displays no data.

The React app (`react-app/`) queries a Supabase-hosted PostgreSQL database via `@supabase/supabase-js` v2. On startup, `fetchDimensions()` in `dataService.js` fetches dimension tables and calls the `get_available_dates()` RPC function to filter the date dropdown to only dates with actual fact data. The date dropdown drives all three report views.

## Scope

- Investigate and fix the root cause of the "no data" symptom in local preview mode.

- Investigate and fix the root cause of the "Failed to load resource: 404 (Not Found)" console error.

- Review all data-fetching paths in `dataService.js` for correctness and robustness, especially RPC response format handling for `get_available_dates()` and `get_settlements_for_date()`.

- Add or extend tests in `dataService.test.js` and `App.test.jsx` to cover the identified bug scenarios, including RPC response format variants and empty-data UI states.

- Fix any other bugs found during code inspection.

- Run the full Python and React test suites and confirm zero failures.

- Update `context.md` and other editable documentation files to reflect all changes.

## Out of scope

- No changes to the ETL download, transform, or Supabase sync logic unless a bug is found directly causing the local preview failure.

- No changes to Netlify production deployment or the live Supabase schema beyond fixing identified bugs.

- No changes to the React app's business logic (report queries, chart rendering) unless a bug is found during inspection.

- No changes to `config.ini` structure or ETL configuration.

- No performance optimizations beyond what is needed to fix confirmed bugs.

- No changes to the legacy web app (`build-legacy/web/`).

## Constraints

- All Python code must remain compatible with Python 3.9+.

- The React app must remain a client-only Vite + React 18 SPA; no serverless functions.

- Credentials must not be hardcoded; `.env` handling must remain consistent with the existing pattern.

- New and existing test files follow established conventions: Python tests in `tests/`, JS/JSX tests in `react-app/src/`.

- No breaking changes to any existing menu actions (1–6, 0) or existing test assertions.

- `npm run build` must exit 0 and `npm run test` must pass with zero failures after all changes.

- The Python test suite must not require a live Supabase connection or internet access.

- The React test suite must not require a live Supabase connection.

## Success criteria

- The root cause(s) of "no data in local preview" are identified, documented, and fixed.

- The root cause of the "Failed to load resource: 404" console error is identified and fixed.

- `dataService.js` correctly handles both PostgREST scalar return formats (wrapped objects `{ fn_name: value }` and raw values) for `get_available_dates()` and `get_settlements_for_date()` RPC calls.

- `App.jsx` shows a user-friendly message when `dimensions.dates` is empty after a successful data load (no silent empty state).

- New or updated tests in `dataService.test.js` cover: `fetchDimensions()` with RPC returning wrapped-object format, `fetchDimensions()` with RPC returning raw-value format, `fetchDimensions()` with RPC unavailable (error fallback), and the empty-dates UI state in `App.test.jsx`.

- `python -m pytest tests/` passes with zero failures (excluding the pre-existing T12 service_role skip).

- `npm run test` in `react-app/` passes with zero failures.

- `context.md` and all relevant documentation files are updated to reflect all changes.

## Assumptions

- A1: PostgREST v11+ (used by the current Supabase hosted instance) returns `RETURNS SETOF int` results as a plain JSON array of raw values (e.g., `[20260428, 20260427]`), not as an array of wrapped objects (`[{ get_available_dates: 20260428 }]`). This is the root cause of the silent empty-dates failure.
  - Risk if false: The actual Supabase instance still uses PostgREST v10 behavior. In that case, the wrapped-object format `r.get_available_dates` already works, and the bug is caused by something else (empty `fact_prices`, wrong credentials). The backward-compatible fix handles both formats and is safe regardless.

- A2: The `get_settlements_for_date()` RPC function has the same `RETURNS SETOF int` format vulnerability as `get_available_dates()`. Both must be fixed simultaneously.
  - Risk if false: Only one function is affected. The fix for both is safe and symmetric.

- A3: Adding `<link rel="icon" href="data:,">` to `react-app/index.html` will suppress the browser's automatic `/favicon.ico` request and eliminate the 404 console error.
  - Risk if false: Some browsers ignore the `data:,` icon hint and still request `/favicon.ico`. If so, placing an actual `favicon.ico` in `react-app/public/` is the fallback.

- A4: The Python test suite (84 passed, 1 skipped) requires no changes; the race-condition fix and credential validation tests from R-20260426-2150 are correct and sufficient for the Python side.
  - Risk if false: A new Python-side bug is discovered during the broader code inspection. In that case, new Python tests would be added.

- A5: The module-level `_dims` cache in `dataService.js` does not cause test pollution in the new `fetchDimensions()` tests, provided a reset mechanism is exposed.
  - Risk if false: The cache persists between tests, causing unexpected results. Mitigation: add a `_resetDimsCache()` export or use `vi.resetModules()` before each test that calls `fetchDimensions()`.

## Plan

### Task 1: Fix RPC scalar format handling in `dataService.js`
**Intent:** Update `fetchDimensions()` and `fetchSettlementsForDate()` to handle both PostgREST wrapped-object and raw-integer RPC response formats.
**Inputs:** `react-app/src/lib/dataService.js` (current `r.get_available_dates` and `r.get_settlements_for_date` mappings).
**Outputs:** Modified `react-app/src/lib/dataService.js` with backward-compatible format handling and `_resetDimsCache` export.
**External Interfaces:** Supabase PostgREST RPC endpoint.
**Environment & Configuration:** No environment variable changes needed.
**Procedure:**
1. In `fetchDimensions()`, replace `(availDatesRes.data || []).map(r => r.get_available_dates)` with `(availDatesRes.data || []).map(r => (typeof r === 'object' && r !== null) ? r.get_available_dates : r)`.
2. In `fetchSettlementsForDate()`, replace `(rpcData || []).map(r => r.get_settlements_for_date)` with the same type-safe pattern.
3. Add a module-level exported function `export function _resetDimsCache() { _dims = null; }` to support test isolation.
**Done Criteria:** The corrected mapping returns non-empty sets when either format is provided; `_resetDimsCache` is exported.
**Dependencies:** None.
**Risk Notes:** The backward-compatible guard handles both formats; no regression risk if Supabase still uses v10 format.

### Task 2: Fix favicon 404 in `react-app/index.html`
**Intent:** Eliminate the "Failed to load resource: 404" console error caused by the missing favicon.
**Inputs:** `react-app/index.html`.
**Outputs:** Modified `react-app/index.html` with `<link rel="icon" href="data:,">` in the `<head>`.
**External Interfaces:** Browser favicon resolution.
**Environment & Configuration:** None.
**Procedure:**
1. Add `<link rel="icon" href="data:,">` to the `<head>` of `react-app/index.html`, after the `<meta>` tags.
**Done Criteria:** After `npm run build`, `dist/index.html` contains the favicon link. No 404 for `/favicon.ico` is generated when the app loads.
**Dependencies:** None.
**Risk Notes:** `data:,` is an inert empty data URI; zero security risk.

### Task 3: Add empty-dates user-facing message in `App.jsx`
**Intent:** Prevent the silent empty-state where `dimensions` is set but `dimensions.dates` is empty, with no explanation for the user.
**Inputs:** `react-app/src/App.jsx` (date selector render block).
**Outputs:** Modified `react-app/src/App.jsx` with conditional empty-dates placeholder option.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In the date selector option block, add a branch: when `dimensions` is set and `dimensions.dates.length === 0`, render a single disabled placeholder option "Няма налични дати".
**Done Criteria:** When `fetchDimensions()` resolves with empty `dates`, the date selector shows "Няма налични дати" instead of a blank input.
**Dependencies:** Task 1.
**Risk Notes:** UI change only; no data logic affected.

### Task 4: Add `fetchDimensions()` and `fetchSettlementsForDate()` unit tests to `dataService.test.js`
**Intent:** Add test cases covering both RPC response formats, the error fallback, caching behavior, and the settlement raw-integer path.
**Inputs:** `react-app/src/lib/dataService.test.js`, `react-app/src/lib/dataService.js` (after Task 1).
**Outputs:** Extended `dataService.test.js` with new `describe('fetchDimensions')` and `describe('fetchSettlementsForDate')` blocks.
**External Interfaces:** Mocked Supabase client.
**Environment & Configuration:** Vitest mock infrastructure; `_resetDimsCache()` for cache isolation.
**Procedure:**
1. Import `fetchDimensions`, `fetchSettlementsForDate`, and `_resetDimsCache` from `dataService.js`.
2. Write `describe('fetchDimensions')` with tests T2 (wrapped objects), T3 (raw integers), T4 (RPC error fallback), T5 (cache hit).
3. Write `describe('fetchSettlementsForDate')` with test T6 (raw integers produce non-empty result).
4. Each test calls `_resetDimsCache()` in `beforeEach`.
**Done Criteria:** All five new tests pass.
**Dependencies:** Task 1.
**Risk Notes:** Module-level cache reset must be consistent across all `fetchDimensions` tests.

### Task 5: Add empty-dates App test to `App.test.jsx`
**Intent:** Add test T7 verifying that the empty-dates UI state renders a user-facing message.
**Inputs:** `react-app/src/App.test.jsx`, `react-app/src/App.jsx` (after Task 3).
**Outputs:** Extended `App.test.jsx` with T7 test.
**External Interfaces:** Mocked `fetchDimensions`.
**Environment & Configuration:** None.
**Procedure:**
1. Add a test in the `describe('App')` block that mocks `fetchDimensions` to resolve with `{ dates: [], settlements: new Map(), categories: new Map(), stores: [], companies: new Map() }`.
2. Assert that the date selector contains an option with text "Няма налични дати".
**Done Criteria:** T7 passes.
**Dependencies:** Task 3.
**Risk Notes:** None.

### Task 6: Run full test suites and verify zero failures (T8, T9, T10)
**Intent:** Confirm all existing and new tests pass with zero failures.
**Inputs:** All modified source and test files.
**Outputs:** Test run output confirming T8 (Python: ≥84 passed, ≤1 skipped), T9 (React: ≥31 passed), T10 (build exit 0).
**External Interfaces:** `pytest`, `npm run test`, `npm run build`.
**Procedure:**
1. Run `python -m pytest tests/ -q` from project root with venv activated.
2. Run `npm run test` in `react-app/`.
3. Run `npm run build` in `react-app/`.
**Done Criteria:** All three pass.
**Dependencies:** Tasks 1–5.
**Risk Notes:** None.

### Task 7: Update `context.md` and documentation
**Intent:** Reflect all changes in the canonical product context and relevant documentation.
**Inputs:** `.aib_memory/context.md`, `README.md`.
**Outputs:** Updated `context.md`; updated `README.md` if applicable.
**Procedure:**
1. Update `context.md` `dataService.js` module description to reflect backward-compatible RPC format handling and `_resetDimsCache` export.
2. Update testing strategy counts and descriptions.
3. Review and update `README.md` local preview section if it mentions the 404 or data-loading behavior.
**Done Criteria:** `context.md` accurately reflects the new code behavior; testing counts are correct.
**Dependencies:** Tasks 1–6.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update `dataService.js` module description to reflect backward-compatible RPC format handling; update testing strategy counts and descriptions for new `dataService.test.js` tests and `App.test.jsx` additions.

- `README.md` (ref_id: N/A) — Review and update the "Local Preview" section if troubleshooting notes mention the 404 or data-loading issue.

## Questions & Decisions

**Q001**: Should the `get_available_dates()` and `get_settlements_for_date()` PostgreSQL functions be updated from `RETURNS SETOF int` to `RETURNS TABLE (date_key int)` / `RETURNS TABLE (settlement_key int)` to guarantee consistent PostgREST object-wrapping regardless of version?
- [x] Option A: Fix client-side only (backward-compatible `typeof r === 'object'` guard in `dataService.js`); leave SQL functions unchanged. *(recommended)*
- [ ] Option B: Fix both client-side AND update SQL DDL in `load_supabase.py`; re-run `load_supabase.py` to provision the updated functions.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/lib/dataService.js` | Modified | Fix RPC scalar format handling for `get_available_dates()` and `get_settlements_for_date()`; add `_resetDimsCache` export. |
| `react-app/index.html` | Modified | Add `<link rel="icon" href="data:,">` to eliminate favicon 404. |
| `react-app/src/App.jsx` | Modified | Add empty-dates user-facing message when `dimensions.dates.length === 0`. |
| `react-app/src/lib/dataService.test.js` | Modified | Add `fetchDimensions()` tests (T2–T5) and `fetchSettlementsForDate()` raw-integer test (T6). |
| `react-app/src/App.test.jsx` | Modified | Add empty-dates UI state test (T7). |
| `.aib_memory/context.md` | Modified | Update module description and testing counts to reflect changes. |
| `README.md` | Modified | Update local preview troubleshooting section if applicable. |
| `src/load_supabase.py` | Read-only dependency | Read to confirm RPC SQL function signature (`RETURNS SETOF int`); not modified in this iteration (Q001 Option A). |
| `react-app/vite.config.js` | Read-only dependency | Confirmed `envDir: '../'` is correct; no changes needed. |
| `react-app/dist/` | Created (rebuilt) | Rebuilt by `npm run build`; contains updated `index.html` with favicon link. |

## Internal Review of Request and Product Docs

- OK: `request.md` — All 12 mandatory sections present; sections 1–6 are non-empty and consistent with the input.

- OK: `context.md` (REF-0001) — Accurately describes `dataService.js` module but does not mention the PostgREST version sensitivity or empty-dates behavior. Will be updated in Task 7.

- Missing info: `context.md` — No mention of the PostgREST v11 format change or its impact on `SETOF` scalar return type. This gap allowed the bug to persist across two iterations.

- Ambiguity: `request.md` `## Scope` — "Review all data-fetching paths" is broad; scoped here to `dataService.js` RPC calls only based on root-cause analysis. No ETL or Supabase sync changes are needed.

- Cross-ref issue: `analysis.md` references `UAT_scenarios.md` (T1) — this file must be created as part of this request to document the manual end-to-end scenario.
