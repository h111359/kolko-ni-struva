## Goal
Fix the root cause of menu option 6 (local React preview) failing to display Supabase data in the browser. Identify why the issue was not caught by the existing test suite and extend the tests to prevent regressions. Fix all other bugs discovered during investigation. Update documentation to reflect all changes.

## Background
Menu option 6 (`action_local_preview` in `menu.py`) is intended to build the React app and start a local Vite preview server (`http://localhost:4173`), then open the browser for the operator to inspect the app with real Supabase data. The previous request R-20260425-2313 addressed a credential-check gap (added pre-build VITE_ variable validation), but after that fix the symptom persists: the browser opens and the app UI renders, but no Supabase data is loaded. The existing test for option 6 only asserts menu dispatch (`action_local_preview` is called) but does not verify the internal behaviour of the function — specifically the ordering of `webbrowser.open()` relative to starting the preview server, nor the credential validation logic itself.

## Scope
- Diagnose the root cause of the local preview (menu option 6) failing to load Supabase data, even when `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are present in the root `.env` file.

- Verify why the issue was not caught by the existing test suite.

- Add unit tests for `action_local_preview()` (and other untested menu actions if gaps are found) that assert the correct ordering of operations and the credential validation behaviour.

- Fix the confirmed bug(s) in `action_local_preview()`.

- Identify and fix all other bugs found during the investigation.

- Update `context.md` and all relevant documentation to reflect all changes made.

## Out of scope
- No changes to the ETL download, transform, or Supabase sync logic unless a bug is found that directly affects option 6.

- No changes to the Netlify production deployment workflow or the React app's business logic (reports, charts, data service).

- No changes to the Supabase schema, RLS policies, or RPC function definitions.

- No changes to the legacy web app (`build-legacy/web/`).

- No changes to `config.ini` structure or ETL configuration defaults.

- No performance optimizations beyond those required to fix confirmed bugs.

## Constraints
- All Python code must remain compatible with Python 3.9+.

- The React app must remain a client-only Vite + React 18 SPA; no serverless functions or backend changes.

- Credentials must not be hardcoded in any source file; `.env` handling must remain consistent with the existing pattern.

- New test files follow existing conventions: Python tests in `tests/`, JS/JSX tests in `react-app/src/`.

- No breaking changes to any existing menu actions (1–6, 0).

- `npm run build` must continue to exit 0 after all changes.

- The React test suite must not require a live Supabase connection.

- The Python test suite must not require a live Supabase connection or internet access.

## Success criteria
- The root cause of "app loads but no data" is identified, documented, and fixed.

- `action_local_preview()` has unit tests asserting: (a) `webbrowser.open()` is called only after the preview server is ready, (b) the credential validation check returns early with a clear error when VITE_ vars are absent, (c) the build step is invoked before the preview step.

- `python -m pytest tests/` passes with zero failures, including new menu tests.

- `npm run test` in `react-app/` passes with zero failures.

- All other bugs identified during investigation are fixed and covered by at least one regression test.

- `context.md` and all other listed documentation files are updated to reflect all changes.

## Assumptions

- A1: The root cause of "app loads but no data is loaded" is the `webbrowser.open(PREVIEW_URL)` call occurring before `subprocess.run(["npm", "run", "preview"])` starts. The browser opens to a port that is not yet listening, resulting in a "connection refused" error in the browser.
  - Risk if false: There is an additional root cause (e.g., Supabase connectivity, credential embedding) that is masked by the race condition fix.

- A2: The Vite `envDir: '../'` setting correctly resolves to the project root from `react-app/`, and credentials in the root `.env` are correctly embedded in the React bundle at build time. The credential check in `action_local_preview()` is therefore sufficient to guard against missing-credentials failures; no Vite configuration changes are needed.
  - Risk if false: Credentials are not embedded despite being present in `.env`, and a separate Vite configuration fix is needed.

- A3: The `VITE_SUPABASE_ANON_KEY` in the root `.env` is a service_role JWT (confirmed by JWT payload decode). Replacing it with the anon key from the Supabase dashboard will require the operator to manually retrieve the correct key.
  - Risk if false: The key is actually the anon key and the JWT decode result was misread; in that case, the security remediation is unnecessary but harmless.

- A4: Adding `--open` to the `npm run preview` script (or using `subprocess.Popen` + TCP readiness polling) is sufficient to fix the race condition. No changes to the React app source or Vite configuration are needed for the fix itself.
  - Risk if false: The `--open` flag behaves differently across Vite versions or OS environments; in that case, the Popen + polling approach is the fallback.

- A5: New Python tests for `action_local_preview()` can reliably assert call order using `unittest.mock.patch` and `unittest.mock.call`. No external infrastructure is needed.
  - Risk if false: The test for server-start-before-browser-open requires a more complex async or threading test harness.

- A6: A new `tests/test_menu.py` file is the appropriate location for menu action unit tests. Existing tests in `test_deploy_netlify.py` covering menu dispatch (TestMenuOption5, TestMenuOption6) can remain in place to avoid regressions.
  - Risk if false: Moving/splitting tests across files introduces a double-coverage conflict; in that case, tests stay in `test_deploy_netlify.py`.

## Plan

### Task 1: Fix the race condition in `action_local_preview()`
**Intent:** Ensure the Vite preview server is ready to serve requests before the browser is opened.
**Inputs:** `menu.py`, `react-app/package.json` (for the `preview` script command).
**Outputs:** Modified `menu.py` with corrected call order; optionally modified `react-app/package.json` if `--open` flag approach is used.
**External Interfaces:** Vite CLI (`npm run preview`); `webbrowser` module; OS browser.
**Environment & Configuration:** Root `.env` must contain valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (anon key).
**Procedure:**
1. Choose fix approach: (a) pass `--open` to `vite preview` so Vite opens the browser after server is ready, or (b) use `subprocess.Popen` + TCP port polling to detect server readiness before calling `webbrowser.open()`.
2. Apply the chosen approach in `action_local_preview()` in `menu.py`.
3. Remove or relocate the standalone `webbrowser.open()` call if approach (a) is taken; or move it after the readiness poll if approach (b) is taken.
4. Retain the printed URL message for operator visibility regardless of approach.
**Done Criteria:** `action_local_preview()` no longer opens the browser before the preview server is ready. Confirmed by new unit tests (Task 3).
**Dependencies:** None.
**Risk Notes:** The `--open` flag in `vite preview` may require a supported Vite version; verify against the installed Vite 5.x.

### Task 2: Remediate the service_role key security misconfiguration
**Intent:** Replace the service_role JWT in `VITE_SUPABASE_ANON_KEY` with the correct anon (public) key from the Supabase project.
**Inputs:** Supabase project dashboard (Project Settings → API → `anon public` key); root `.env`.
**Outputs:** Updated root `.env` with `VITE_SUPABASE_ANON_KEY` set to the anon key.
**External Interfaces:** Supabase dashboard (operator action required); no code changes needed.
**Environment & Configuration:** Operator must retrieve the anon key from the Supabase dashboard and update `.env`. The service_role key should be rotated in the Supabase dashboard.
**Procedure:**
1. Open Supabase dashboard → Project Settings → API.
2. Copy the `anon public` key (not the `service_role` key).
3. Replace the `VITE_SUPABASE_ANON_KEY` value in root `.env`.
4. Rotate (regenerate) the service_role key in the Supabase dashboard to invalidate the exposed key.
5. Update `DATABASE_URL` in `.env` if it uses the service_role key (psycopg2 connection — service_role is acceptable for server-side ETL, just not for the React bundle).
**Done Criteria:** `VITE_SUPABASE_ANON_KEY` JWT payload contains `"role":"anon"`. Confirmed by test T12.
**Dependencies:** None (operator action; Task 3 adds the regression test).
**Risk Notes:** Rotating the service_role key will break `src/load_supabase.py` if `DATABASE_URL` includes the old service_role credential; verify `DATABASE_URL` uses a separate connection string (which it does — it's a PostgreSQL DSN, not the JWT).

### Task 3: Create `tests/test_menu.py` with `action_local_preview` unit tests
**Intent:** Provide unit test coverage for `action_local_preview()` asserting correct call order and credential validation behavior.
**Inputs:** `menu.py`; `unittest.mock`.
**Outputs:** New `tests/test_menu.py` covering T1–T8 from the Testing section of `analysis.md`.
**External Interfaces:** None (all subprocess, dotenv, webbrowser calls are mocked).
**Environment & Configuration:** Python 3.9+; `unittest` stdlib.
**Procedure:**
1. Create `tests/test_menu.py` with imports and sys.path setup consistent with existing test files.
2. Implement test cases for T1 (missing credentials early return), T2 (build precedes preview), T3 (server start before browser open), T4 (build failure early return), T5 (npm not found early return).
3. Implement test cases for T6 (stats helpers), T7 (read_state missing config), T8 (main loop dispatches all choices).
4. Implement T12 (anon key JWT role assertion) as a configuration verification test.
5. Run `python -m pytest tests/test_menu.py -v` to confirm all tests pass.
**Done Criteria:** All new tests in `test_menu.py` pass; `python -m pytest tests/` total count increases by the number of new tests with zero failures.
**Dependencies:** Task 1 must be complete before T3 can be written (test asserts the fixed order).
**Risk Notes:** Mocking `subprocess.run` and `subprocess.Popen` simultaneously may require careful patch ordering; ensure patches are applied in the right scope.

### Task 4: Add React `App.jsx` tests covering credential error and dimension loading
**Intent:** Cover the credential-error and dimension-loading paths in `App.jsx` with Vitest tests.
**Inputs:** `react-app/src/App.jsx`; `react-app/src/lib/supabase.js`; `react-app/src/lib/dataService.js`.
**Outputs:** New `react-app/src/App.test.jsx` covering T9 and T10.
**External Interfaces:** Mocked Supabase client and `fetchDimensions` function.
**Environment & Configuration:** Vitest + @testing-library/react; jsdom environment.
**Procedure:**
1. Create `react-app/src/App.test.jsx`.
2. Implement T9: mock `credentialsError` to a non-null string; assert error message renders and no Supabase calls are made.
3. Implement T10: mock `credentialsError` to null and `fetchDimensions` to resolve with stub dims; assert date selector populates.
4. Run `npm run test` in `react-app/` to confirm tests pass.
**Done Criteria:** `App.test.jsx` tests pass; `npm run test` total count increases.
**Dependencies:** None.
**Risk Notes:** Mocking module-level `credentialsError` in `supabase.js` requires `vi.mock`; verify the mock strategy is consistent with the existing pattern in `Report1.test.jsx`.

### Task 5: Run full test suite and confirm zero failures
**Intent:** Validate that all Python and React tests pass after the fixes.
**Inputs:** All test files in `tests/` and `react-app/src/`.
**Outputs:** Confirmation of pass counts (printed to terminal).
**External Interfaces:** None.
**Environment & Configuration:** Python 3.9+ with pytest; Node.js with Vitest.
**Procedure:**
1. Run `python -m pytest tests/ -v`.
2. Run `npm run test` in `react-app/`.
3. Confirm zero failures.
**Done Criteria:** Both test suites exit 0 with zero failures.
**Dependencies:** Tasks 1, 2, 3, 4 complete.
**Risk Notes:** None.

### Task 6: Update `context.md` and documentation
**Intent:** Update all documentation to accurately reflect the changes made in Tasks 1–4.
**Inputs:** `.aib_memory/context.md`; `README.md`.
**Outputs:** Updated `context.md` (Testing Strategy section, menu.py module description); updated `README.md` if option 6 behavior is documented there.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Update `.aib_memory/context.md` → Testing Strategy: add mention of `test_menu.py`, updated test counts, and `App.test.jsx`.
2. Update `.aib_memory/context.md` → menu.py module description: note the race condition fix and corrected call order in `action_local_preview()`.
3. Update `.aib_memory/context.md` → Constraints: confirm "anon key only" constraint is now met after key rotation.
4. Check `README.md` for any description of option 6 behavior; update if present.
**Done Criteria:** `context.md` accurately reflects the post-fix state; no stale references to the old behavior remain.
**Dependencies:** Tasks 1–5 complete.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update Testing Strategy section to include `tests/test_menu.py` and `react-app/src/App.test.jsx`; update menu.py module description to reflect corrected `action_local_preview()` call order; confirm Constraints section "anon key only" is accurate after security remediation.
- `README.md` (ref_id: N/A) — Update option 6 description if present to reflect the corrected browser-open timing behavior.

## Questions & Decisions

**Q001**: How should the race condition in `action_local_preview()` be fixed?
- [ ] Option A: Pass `--open` to `vite preview` (modify `npm run preview` script or call `npx vite preview --open` directly), so Vite handles server-ready detection and browser open internally. Removes `webbrowser.open()` from Python.
- [x] Option B: Use `subprocess.Popen` to start the preview server non-blocking, poll `http://localhost:4173` or the TCP port until the server responds, then call `webbrowser.open()`. *(recommended)*
- [ ] Other: ___
> Answer: 

**Q002**: Should the `VITE_SUPABASE_ANON_KEY` security remediation (replacing service_role key with anon key) be included as a mandatory deliverable in this request, or documented as a separate urgent action item?
- [x] Option A: Include as a mandatory deliverable — the anon key replacement is a blocking prerequisite for the local preview to connect to Supabase without security risk; test T12 enforces it. *(recommended)*
- [ ] Option B: Document as a separate urgent action item — the race condition fix and test coverage are the primary scope; the key rotation is an operator action that can be tracked separately.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `menu.py` | Modified | Fix race condition in `action_local_preview()` — correct call order of server start vs. browser open. |
| `react-app/package.json` | Modified (possible) | May require adding `--open` flag to the `preview` script if Option A is chosen for Q001. |
| `tests/test_menu.py` | Created | New unit test file covering `action_local_preview()` internal behavior and other menu helpers. |
| `react-app/src/App.test.jsx` | Created | New Vitest test file covering App.jsx credential-error and dimension-loading paths. |
| `.env` | Modified | Replace `VITE_SUPABASE_ANON_KEY` service_role value with the correct anon key (operator action). |
| `.aib_memory/context.md` | Modified | Update Testing Strategy, menu.py module description, and Constraints after fixes. |
| `README.md` | Modified (possible) | Update option 6 behavior description if present. |

## Internal Review of Request and Product Docs

- OK: `request.md` — All 12 mandatory sections present; sections 1–6 are non-empty; content is consistent with the workspace state.
- Ambiguity: `request.md` — The request says "Fix all other issues before completion" which could be interpreted broadly. Scoped to bugs found during this investigation (race condition + security key misconfiguration); broader bug hunting is out of scope.
- OK: `context.md` (REF-0001) — Accurately describes the current codebase state (as of R-20260425-2313) with one exception: it states "anon key only; no service role key" under React app constraints, but the actual `.env` contains a service_role key. The constraint is correct; the `.env` violates it. No documentation contradiction; this is a configuration defect.
- Missing info: `references.md` — No reference entry for `README.md`; if `README.md` documents option 6 behavior, it should be added to `references.md` for future tracking.
- Cross-ref issue: `context.md` Testing Strategy — Lists 24 tests in `test_deploy_netlify.py` covering "menu.py option integration"; this will need updating after `tests/test_menu.py` is created to avoid implying all menu tests live in `test_deploy_netlify.py`.
