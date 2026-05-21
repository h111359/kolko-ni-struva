## Goal
Restore stable operation of the React analytics app, fix the local preview data display failure, introduce rigorous test coverage across the entire codebase, and eliminate all browser console errors before the next Netlify production deployment.

## Background
The React analytics app is the public-facing visualisation layer of the kolko-ni-struva ETL pipeline. Currently the app is not working in a stable way and the local preview (menu option 6) is not displaying any data — it should connect to Supabase and show price analytics data. The operator also wants comprehensive test coverage across all Python ETL scripts and React source modules, and assurance that no console errors appear in the browser before deploying to production.

## Scope
- Diagnose and fix the root cause of the local preview (menu option 6) failing to display Supabase data.

- Audit and fix all browser console errors and warnings produced by the React app under normal operating conditions (valid credentials present, RPC functions provisioned).

- Create unit tests for `src/extract.py` covering its core functions (page fetching, ZIP link parsing, download logic, incremental check).

- Create unit tests for `src/transform.py` covering delimiter detection, dimension upsert, fact row writing, and quality report generation.

- Create unit tests for `src/load_supabase.py` covering table provisioning, dimension upsert, and fact insertion logic (using mocked psycopg2 connections).

- Extend the test suite with React/JS unit tests using Vitest and React Testing Library, covering `dataService.js` helper functions (`formatDateBG`, `calculatePrice`, `fetchReport2` pagination) and component smoke-render tests for `HomePage`, `Report1`, `Report2`, and `Report3`.

- Fix all confirmed bugs found during analysis and audit, including the pagination gap in `fetchReport2`.

- Validate that all Python tests (`python -m pytest tests/`) and all React tests (`npm run test` in `react-app/`) pass before deploying to production.

## Out of scope
- No changes to the ETL download or transform logic beyond what is strictly needed to fix confirmed bugs.

- No changes to the Supabase schema, RLS policies, or RPC function definitions.

- No changes to the Netlify production deployment workflow or Netlify site environment variables.

- No changes to the legacy web app (`build-legacy/web/`).

- No changes to `config.ini` structure or ETL configuration defaults.

- No performance optimizations beyond what is necessary to fix confirmed stability bugs.

## Constraints
- All Python code must remain compatible with Python 3.9+.

- The React app must remain a client-only Vite + React 18 SPA; no serverless functions or backend are introduced.

- Credentials must not be hardcoded in any source file; `.env` handling must remain consistent with the existing pattern.

- Test files must be placed in `tests/` (Python) and `react-app/src/` (JS/JSX), following existing conventions.

- No breaking changes to existing menu actions (1–6, 0).

- `npm run build` must continue to exit 0 after all changes.

- The React test suite must not require a live Supabase connection (all Supabase calls must be mocked).

## Success criteria
- Menu option 6 (local preview) successfully displays Supabase data in the browser when valid credentials are present in the root `.env` file.

- Browser developer console shows zero errors and zero unexpected warnings under normal operating conditions (valid credentials, RPC functions provisioned).

- `python -m pytest tests/` passes with meaningful coverage across all Python ETL scripts (`extract.py`, `transform.py`, `load_supabase.py`, `config_utils.py`, `deploy_netlify.py`, `menu.py`).

- `npm run test` in `react-app/` passes with coverage across `dataService.js` helper functions and all four page components.

- All confirmed bugs (including `fetchReport2` missing pagination) are fixed and covered by at least one regression test.

- No new `console.warn` or `console.error` calls are introduced beyond the existing graceful-fallback RPC warnings.

## Assumptions

- A1: The local preview data failure is caused by missing `VITE_SUPABASE_URL` and/or `VITE_SUPABASE_ANON_KEY` in the root `.env` file at the time `npm run build` is executed.
  - Risk if false: The failure has a different root cause (e.g., wrong credentials, Supabase RLS, network issue), and the pre-build check does not resolve it.

- A2: The Supabase RPC functions (`get_available_dates`, `get_settlements_for_date`) are already provisioned in the remote database (operator has run `load_supabase.py` after R-20260422-0902). Console warnings from the RPC fallback path do not appear under normal operating conditions.
  - Risk if false: Console warnings appear even with valid credentials; a separate task to re-provision RPC functions would be required.

- A3: The `fetchReport2` missing pagination is a real data-correctness bug — there exist settlement+category combinations with more than 1 000 fact rows for a given date.
  - Risk if false: The bug is theoretical and fixing it has no observable effect; the regression test still has value as a preventive measure.

- A4: Vitest is the appropriate test runner for the React app and is compatible with the existing Vite 5.x + React 18 + `@supabase/supabase-js` v2 stack.
  - Risk if false: Compatibility issues require an alternative runner (Jest + Babel) or significant test configuration effort.

- A5: Python tests for `extract.py`, `transform.py`, and `load_supabase.py` use `unittest.mock` for all external I/O (HTTP, file system, psycopg2); no live Supabase or internet connection is required to run the test suite.
  - Risk if false: Tests require live infrastructure, making them environment-dependent and unsuitable for CI.

- A6: The `Question threshold` is set to 3 (level 3 and above triggers a Q-block). This threshold was read from `input.md ## Options` as `[x] 3`.
  - Risk if false: Questions below threshold are raised unnecessarily or critical questions above threshold are suppressed.

- A7: The column name for the settlement EKATTE code in both the Supabase `dim_settlement` table and the `data/schema/dim_settlement.csv` file is `ekatte`, not `ekatte_code`. The `context.md` documentation error does not affect the running application.
  - Risk if false: The database was provisioned with `ekatte_code` by a now-corrected DDL; the column name mismatch would cause Supabase queries to return null for that field.

- A8: React key warnings (using row index as `key={i}` in Report2 and Report3 tables) are acceptable for the current app use case (read-only, non-reorderable result sets) and do not produce visible browser console warnings in production builds.
  - Risk if false: React emits key-related warnings in production; these must be fixed to satisfy the zero-console-warnings criterion.

## Plan

### Task 1: Investigate and document the local preview root cause
**Intent:** Confirm the exact root cause of menu option 6 failing to display Supabase data.
**Inputs:** `menu.py`, `react-app/vite.config.js`, `react-app/src/lib/supabase.js`, root `.env` file (if present).
**Outputs:** Confirmed root cause documented in implementation record; readiness assessment for Task 2.
**External Interfaces:** Vite build process (observation only).
**Environment & Configuration:** Project root `.env`; Vite `envDir` setting.
**Procedure:**
1. Read the root `.env` to verify whether `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are present and non-empty.
2. Confirm `react-app/vite.config.js` `envDir: '../'` setting.
3. Confirm `supabase.js` `credentialsError` logic — exports non-null when either key is falsy.
4. Confirm `App.jsx` skips `fetchDimensions()` when `credentialsError` is truthy.
5. Record finding: missing VITE_ keys → empty bundle → credential error shown → no data displayed.
**Done Criteria:** Root cause confirmed and consistent with A1. If root cause differs, revise A1 and Tasks 2–3 accordingly.
**Dependencies:** None.
**Risk Notes:** If credentials are present and correct but data still does not display, a different root cause exists (RLS, network, wrong key).

---

### Task 2: Add pre-build credential validation to `action_local_preview()`
**Intent:** Prevent `npm run build` from running when VITE_ credentials are absent, providing a clear actionable error message.
**Inputs:** `menu.py`; root `.env` logic pattern from `deploy_netlify.py`.
**Outputs:** Modified `menu.py` — `action_local_preview()` validates VITE_ key presence before build.
**External Interfaces:** Root `.env` file (read-only check).
**Environment & Configuration:** Root `.env`; `python-dotenv` (already in `requirements.txt`).
**Procedure:**
1. Before calling `subprocess.run(["npm", "run", "build"], ...)`, read the root `.env` via `python-dotenv` `load_dotenv()`.
2. Check `os.environ.get('VITE_SUPABASE_URL')` and `os.environ.get('VITE_SUPABASE_ANON_KEY')`.
3. If either is absent or empty: print an actionable error message (do not print the values) and return without running the build.
4. Confirm the check does not expose credential values in stdout or logs.
**Done Criteria:** Running `action_local_preview()` with missing VITE_ keys prints an error and exits without running `npm run build` or `npm run preview`. Running with valid keys proceeds normally.
**Dependencies:** Task 1.
**Risk Notes:** `load_dotenv()` must be called after confirming the `.env` path exists; avoid overriding shell env vars.

---

### Task 3: Fix `fetchReport2` pagination in `dataService.js`
**Intent:** Replace the single Supabase query in `fetchReport2` with a paginated loop matching the `fetchReport1` pattern, to prevent silent result truncation at 1 000 rows.
**Inputs:** `react-app/src/lib/dataService.js` (current `fetchReport2` implementation).
**Outputs:** Modified `dataService.js` — `fetchReport2` paginates using `.range(from, to)` in a `while (!done)` loop.
**External Interfaces:** Supabase `fact_prices` table (same query, paginated).
**Environment & Configuration:** Supabase anon key (unchanged).
**Procedure:**
1. Replace the single `supabase.from('fact_prices').select().eq().eq().in()` query in `fetchReport2` with a `while (!done)` pagination loop using the same `PAGE_SIZE = 1000` pattern as `fetchReport1`.
2. Preserve the `.eq('date_key', dateKey)`, `.eq('category_key', categoryKey)`, and `.in('store_key', storeKeys)` filters.
3. Preserve the downstream product-name batch fetch and enrichment logic unchanged.
**Done Criteria:** T3 test passes (mocked client returning 1 050 rows across two pages yields 1 050 enriched rows). Existing Report 2 behavior with < 1 000 rows is unchanged.
**Dependencies:** None.
**Risk Notes:** Pagination adds round trips; for categories with many rows the report may be slower. This is acceptable given the data-correctness requirement.

---

### Task 4: Audit and fix browser console warnings
**Intent:** Confirm zero console errors and warnings in the React app under normal operating conditions.
**Inputs:** React source files (`App.jsx`, `dataService.js`, page components), Supabase RPC function status.
**Outputs:** Any required source changes (e.g., React key fixes if Assumption A8 is false); updated `UAT_scenarios.md` pass confirmation.
**External Interfaces:** Running local preview (UAT).
**Environment & Configuration:** Root `.env` with valid credentials; provisioned RPC functions.
**Procedure:**
1. Run local preview with valid credentials.
2. Open browser DevTools Console.
3. Navigate through all four pages and trigger each report.
4. Record any console messages.
5. If React key warnings appear (`key={i}` in tables), replace with a stable key derived from row data fields.
6. If RPC warnings appear, confirm `load_supabase.py` has been run; document in implementation record.
**Done Criteria:** UAT-01 passes. Zero errors and warnings in browser console.
**Dependencies:** Task 2 (must have valid local preview to audit).
**Risk Notes:** RPC warning requires `load_supabase.py` re-run if functions were not provisioned.

---

### Task 5: Create unit tests for `src/extract.py`
**Intent:** Provide automated test coverage for the download script's core functions.
**Inputs:** `src/extract.py`; `tests/` existing structure.
**Outputs:** New file `tests/test_extract.py` with unit tests covering: `parse_zip_links`, `existing_filenames`, incremental download skip logic, and atomic rename behavior.
**External Interfaces:** Mocked `requests.get` (HTML page and ZIP binary); mocked filesystem via `tempfile.TemporaryDirectory`.
**Environment & Configuration:** Python 3.9+; `unittest.mock`.
**Procedure:**
1. Create `tests/test_extract.py`.
2. Test `parse_zip_links` with synthetic HTML containing `.zip` hrefs.
3. Test incremental skip: mock `existing_filenames` to return the latest filename; assert `requests.get` for the file URL is not called.
4. Test atomic rename: verify no `.partial` file left after a successful download mock.
5. Run `python -m pytest tests/test_extract.py -v` to confirm all tests pass.
**Done Criteria:** All tests in `test_extract.py` pass. At least 4 test cases covering the functions listed above.
**Dependencies:** None.
**Risk Notes:** `extract.py` may need minor refactoring to make `parse_zip_links` and `existing_filenames` importable as standalone functions (confirm they are already top-level functions, not only called inside `main()`).

---

### Task 6: Create unit tests for `src/transform.py`
**Intent:** Provide automated test coverage for the transform script's core logic.
**Inputs:** `src/transform.py`; `tests/` existing structure.
**Outputs:** New file `tests/test_transform.py` with tests covering: delimiter auto-detection, dimension upsert (new code vs existing code path), atomic fact file write, and quality report generation.
**External Interfaces:** Mocked filesystem using `tempfile.TemporaryDirectory`; synthetic ZIP fixture created in-memory using `zipfile.ZipFile`.
**Environment & Configuration:** Python 3.9+; `unittest.mock`; `zipfile` (stdlib).
**Procedure:**
1. Create `tests/test_transform.py`.
2. Build a small in-memory ZIP with one synthetic CSV (semicolon-delimited) using `io.BytesIO` and `zipfile.ZipFile`.
3. Test delimiter auto-detection by calling the detection logic with a row containing a semicolon-enclosed value.
4. Test dimension upsert: call the dimension update function with a new code; assert surrogate key is `max_key + 1`.
5. Test atomic write: confirm no `.partial` file left after successful write mock.
6. Run `python -m pytest tests/test_transform.py -v`.
**Done Criteria:** All tests pass. At least 4 test cases.
**Dependencies:** None.
**Risk Notes:** If delimiter detection logic is embedded in `main()` rather than an extractable function, minor refactoring (extracting a helper) may be needed.

---

### Task 7: Create unit tests for `src/load_supabase.py`
**Intent:** Provide automated test coverage for the Supabase sync module's table provisioning and data insertion functions.
**Inputs:** `src/load_supabase.py`; `tests/` existing structure.
**Outputs:** New file `tests/test_load_supabase.py` with tests covering: `create_tables` DDL invocation, `get_latest_remote_date` cursor result parsing, and upsert conflict clause format.
**External Interfaces:** Mocked `psycopg2.connect` returning a mock cursor; mocked `csv` reading via synthetic `tempfile`.
**Environment & Configuration:** Python 3.9+; `unittest.mock`; no live database required.
**Procedure:**
1. Create `tests/test_load_supabase.py`.
2. Mock `psycopg2.connect` to return a mock connection with a mock cursor.
3. Test `create_tables`: assert mock cursor's `execute` is called with SQL containing `CREATE TABLE IF NOT EXISTS dim_date`.
4. Test `get_latest_remote_date`: mock cursor `fetchone` returning `(20260424,)`; assert function returns `20260424`.
5. Test that the upsert SQL for a dimension table contains `ON CONFLICT` and `DO UPDATE`.
6. Run `python -m pytest tests/test_load_supabase.py -v`.
**Done Criteria:** All tests pass. At least 3 test cases. No live database connection required.
**Dependencies:** None.
**Risk Notes:** `load_supabase.py` calls `load_dotenv()` at import time; tests must patch or prevent this from failing when `.env` is absent.

---

### Task 8: Configure Vitest and add React unit tests
**Intent:** Introduce Vitest as the test runner for the React app and add tests for helper functions and component smoke renders.
**Inputs:** `react-app/package.json`; `react-app/vite.config.js`; `react-app/src/lib/dataService.js`; all four page components.
**Outputs:** Updated `react-app/package.json` (test script, Vitest + RTL dev dependencies); test files in `react-app/src/`; updated `react-app/vite.config.js` (test environment config if needed).
**External Interfaces:** Mocked Supabase client (`vi.mock('./lib/supabase')` pattern).
**Environment & Configuration:** Node.js; Vitest; `@testing-library/react`; `jsdom`.
**Procedure:**
1. Add Vitest and RTL to `react-app/package.json` devDependencies: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.
2. Add `"test": "vitest run"` to `package.json` scripts.
3. Configure `test.environment: 'jsdom'` in `react-app/vite.config.js` under the `test` key.
4. Create `react-app/src/lib/dataService.test.js`: tests for `formatDateBG`, `calculatePrice`, and the `fetchReport2` pagination regression (T3).
5. Create `react-app/src/components/HomePage.test.jsx`: smoke render test (renders without crashing).
6. Create smoke render tests for Report1, Report2, Report3 with mocked props and mocked Supabase module.
7. Run `npm run test` in `react-app/` to confirm all tests pass.
**Done Criteria:** `npm run test` exits 0. All helper function tests pass. All four component smoke render tests pass. T3 pagination regression test passes.
**Dependencies:** Task 3 (pagination fix must be in place before the T3 regression test is written).
**Risk Notes:** Mocking `import.meta.env` in Vitest requires setting test env vars in `vite.config.js` `define` block or via Vitest `env` option. Supabase client must be mocked via `vi.mock`.

---

### Task 9: Run full test suite; verify all tests pass
**Intent:** Confirm that all Python and React tests pass as a combined gate before marking tasks complete.
**Inputs:** `tests/` (all Python test files); `react-app/` (Vitest test files).
**Outputs:** Test run output (recorded in implementation record); green status for both suites.
**External Interfaces:** None (all external calls mocked).
**Environment & Configuration:** Python 3.9+ virtualenv with test dependencies; Node.js with `npm install` run in `react-app/`.
**Procedure:**
1. Run `python -m pytest tests/ -v` from project root; confirm exit 0.
2. Run `npm run test` in `react-app/`; confirm exit 0.
3. Record pass/fail counts in implementation record.
**Done Criteria:** Both commands exit 0 with zero test failures.
**Dependencies:** Tasks 2–8 (all code and test changes in place).
**Risk Notes:** If a test fails after all tasks are complete, treat as a blocker — do not mark the iteration done.

---

### Task 10: Update `context.md` and documentation
**Intent:** Correct the `ekatte` / `ekatte_code` documentation inconsistency in `context.md` and record all changes made in this iteration.
**Inputs:** `.aib_memory/context.md`; `tests/` new files; `react-app/package.json` changes; `menu.py` changes; `dataService.js` changes.
**Outputs:** Updated `.aib_memory/context.md` (corrected column name, updated test coverage section, updated module breakdown for `menu.py` and `dataService.js`).
**External Interfaces:** None.
**Procedure:**
1. In `context.md`, find all occurrences of `ekatte_code` in the `dim_settlement` description and replace with `ekatte`.
2. Update the "Development Practices" section to reflect new test files (`test_extract.py`, `test_transform.py`, `test_load_supabase.py`) and the React test suite (Vitest).
3. Update `menu.py` module breakdown to reflect the VITE_ credential check in `action_local_preview()`.
4. Update `dataService.js` module breakdown to reflect `fetchReport2` pagination.
**Done Criteria:** `context.md` contains no `ekatte_code` references; new test files and changed modules are documented.
**Dependencies:** Tasks 2–9 (all changes complete before documentation is finalized).
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update to correct `ekatte_code` → `ekatte` column name in dim_settlement description; add new test files to development practices; update module breakdowns for `menu.py` and `dataService.js`.

## Questions & Decisions

**Q001**: Should the React test suite use Vitest (Vite-native runner) or Jest (with Babel transform)?
- [ ] Option A: Use Jest with `babel-jest` and `@babel/preset-react`
- [x] Option B: Use Vitest (Vite-native, shares Vite config, no separate Babel setup) *(recommended)*
- [ ] Other: ___
> Answer: 

**Q002**: For the local preview fix, should `action_local_preview()` in `menu.py` validate VITE_ credentials before running `npm run build`, or should the fix be documentation-only (updating README)?
- [ ] Option A: Documentation-only (update README with credential prerequisite)
- [x] Option B: Add pre-build env var check in `action_local_preview()` and print a clear error message if missing *(recommended)*
- [ ] Option C: Add check and silently skip build (no error message)
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `menu.py` | Modified | Add VITE_ credential validation in `action_local_preview()` before `npm run build` |
| `react-app/src/lib/dataService.js` | Modified | Fix `fetchReport2` missing pagination loop |
| `react-app/package.json` | Modified | Add Vitest, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` devDependencies; add `test` script |
| `react-app/vite.config.js` | Modified | Add `test.environment: 'jsdom'` configuration block |
| `react-app/src/lib/dataService.test.js` | Created | Unit tests for `formatDateBG`, `calculatePrice`, `fetchReport2` pagination |
| `react-app/src/components/HomePage.test.jsx` | Created | Smoke render test for `HomePage` |
| `react-app/src/components/Report1.test.jsx` | Created | Smoke render test for `Report1` with mocked props |
| `react-app/src/components/Report2.test.jsx` | Created | Smoke render test for `Report2` with mocked props |
| `react-app/src/components/Report3.test.jsx` | Created | Smoke render test for `Report3` with mocked props |
| `tests/test_extract.py` | Created | Unit tests for `src/extract.py` core functions |
| `tests/test_transform.py` | Created | Unit tests for `src/transform.py` delimiter detection and dimension logic |
| `tests/test_load_supabase.py` | Created | Unit tests for `src/load_supabase.py` DDL and data sync functions |
| `.aib_memory/context.md` | Modified | Correct `ekatte_code` → `ekatte`; update test coverage and module breakdowns |
| `react-app/src/components/Report2.jsx` | Modified | Potentially fix `key={i}` if React key warnings confirmed during Task 4 audit |
| `react-app/src/components/Report3.jsx` | Modified | Potentially fix `key={i}` if React key warnings confirmed during Task 4 audit |

## Internal Review of Request and Product Docs

- OK: `context.md` — accurately describes the overall architecture, ETL pipeline, and React app structure.

- Contradiction: `context.md` Core Data Entities table — lists `dim_settlement` columns as `settlement_key, ekatte_code, settlement_name`, but the actual CSV header (`data/schema/dim_settlement.csv`), the `DIM_TABLES` descriptor in `load_supabase.py`, and the Supabase DDL all use `ekatte` (not `ekatte_code`). The application code (`dataService.js`) correctly uses `ekatte`. Documentation must be corrected in Task 10.

- Missing info: `context.md` Development Practices / Repository Structure — does not mention the absence of tests for `extract.py`, `transform.py`, and `load_supabase.py`. After this request, the section must be updated to reflect the new test files.

- Missing info: `context.md` Operations / Running the Pipeline — does not document the prerequisite that `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` must be present in the root `.env` before menu option 6 (local preview) will show data.

- OK: `request.md` sections 1–6 — consistent with the input content, non-empty, and precise enough for deterministic analysis and planning.

- OK: `references.md` — two entries (`context.md` as `product-doc`, `Concepts.md` as `domain`); both present and accessible.

