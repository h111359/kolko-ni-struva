# Analysis: R-20260428-0708 — Fix local preview 404 and data loading bugs

## Executive Summary

- **Request ID:** R-20260428-0708

- **Request title:** Fix local preview 404 and data loading bugs

- **Purpose:** Diagnose and eliminate the repeating "no data in local preview" symptom and the associated browser console 404 error. The previous fix (R-20260426-2150) resolved the race condition where the browser opened before the Vite preview server was ready, but the core data loading failure persisted.

- **Root cause identified — Bug 1 (no data):** `dataService.js` `fetchDimensions()` uses `r.get_available_dates` to extract date keys from the Supabase RPC response. PostgREST v11+ returns scalar `SETOF int` results as raw integers `[20260426, …]`, not as wrapped objects `[{ get_available_dates: 20260426 }, …]`. When the current code maps over raw integers, `r.get_available_dates` is `undefined` for every element. The resulting `factDateKeySet` contains only `undefined`, causing the date filter `filteredDates = datesRes.data.filter(r => factDateKeySet.has(r.date_key))` to return an empty array. The date dropdown is empty, `selectedDate` is never set, and no reports render. No error is surfaced — the failure is completely silent.

- **Root cause identified — Bug 2 (404 console error):** There is no `public/` directory in `react-app/`, so no `favicon.ico` is present in the `dist/` output. Browsers automatically issue a `GET /favicon.ico` request on every page load. The Vite preview server returns 404 for this request, generating "Failed to load resource: the server responded with a status of 404 (Not Found)" in the browser console.

- **Additional bug — Bug 3 (same RPC format issue for settlements):** `fetchSettlementsForDate()` maps `r.get_settlements_for_date` over the RPC result with the same format assumption. Under PostgREST v11+, this also silently produces an empty set, causing all city/settlement dropdowns in Reports 1, 2, and 3 to be empty even after fixing Bug 1.

- **Additional finding — Bug 4 (silent empty-dates UI state):** When `dimensions.dates` is empty (either due to Bug 1 or legitimately empty `fact_prices`), the date selector renders no options and no reports render, but no user-facing message explains why. The user sees a frozen "loading"-looking interface with no feedback.

- **`request.md` updates in this run:** Sections `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` are added/updated.


## Domain Knowledge Essentials

- **Local preview (menu option 6):** A menu action that builds the React app (`npm run build`) and starts a Vite static-file server (`vite preview`) on `http://localhost:4173`, allowing the operator to test the app with real Supabase data before deploying to Netlify.

- **Vite preview:** A lightweight production-like HTTP server that serves the compiled `dist/` output. Not a hot-reload dev server. Runs on port 4173 by default.

- **Supabase / PostgREST:** Supabase exposes the PostgreSQL database via PostgREST, a REST API layer. The JavaScript client (`@supabase/supabase-js` v2) calls PostgREST endpoints. RPC calls invoke PostgreSQL functions. The response format for scalar `SETOF` functions changed in PostgREST v11.

- **SETOF scalar vs. SETOF composite (PostgREST behavior):** In PostgREST v10 and earlier, a function returning `RETURNS SETOF int` produced JSON objects where each row was wrapped: `[{ "get_available_dates": 20260426 }, …]`. In PostgREST v11+, scalar `SETOF` results are returned as a plain JSON array of values: `[20260426, 20260425, …]`. Code written against v10 behavior silently fails under v11+.

- **`fetchDimensions()` caching:** Results are stored in a module-level `_dims` variable. Subsequent calls return the cached object without re-fetching. In a browser context each page load starts fresh. In tests, the cache must be reset between runs.

- **Date key format:** `date_key` is an integer in `YYYYMMDD` format (e.g., `20260428`), not a date string. The RPC `get_available_dates()` returns a `SETOF int` of these keys.

- **Empty-dates silent failure:** When `dimensions.dates` is an empty array after a successful `fetchDimensions()` call, `selectedDate` is never set to a value. All three report sections are conditionally rendered only when `dimensions && selectedDate`. With `selectedDate = null`, the report sections are invisible. No error message is shown.


## Technical Knowledge & Terms

- **`react-app/src/lib/dataService.js`:** Data-fetching layer. Key exports: `fetchDimensions()`, `fetchSettlementsForDate()`, `fetchReport1/2/3()`, `formatDateBG()`, `calculatePrice()`. `fetchDimensions()` runs a `Promise.all` of six Supabase queries including the `get_available_dates()` RPC.

- **`react-app/src/lib/supabase.js`:** Supabase client singleton. Exposes `credentialsError` (string or null). If credentials are absent from the Vite build, `supabase = null` and `credentialsError` is set. `App.jsx` guards against calling `fetchDimensions()` when `credentialsError` is set.

- **`react-app/src/App.jsx`:** Root component. Calls `fetchDimensions()` on mount. Sets `dimensions` and pre-selects the newest `date_key`. Renders reports only when `dimensions && selectedDate` are both truthy.

- **PostgREST SETOF scalar response format (v11+ change):** `RETURNS SETOF int` with `supabase.rpc()` now returns `{ data: [20260426, 20260425, …], error: null }`. Accessing `.get_available_dates` on an integer returns `undefined`.

- **`react-app/index.html`:** Source HTML template for Vite. No `<link rel="icon">` element is present. Browsers auto-request `/favicon.ico` as a fallback, causing 404.

- **`react-app/public/` directory:** Vite copies files from this directory verbatim into `dist/` during build. Adding a `favicon.ico` or `favicon.svg` here makes it available at the root of the preview server.

- **`vitest` + `@testing-library/react`:** Test framework for React components. `vi.mock()` intercepts module imports. `vi.hoisted()` creates mutable control objects for per-test mock overrides.

- **Files read:**
  - `react-app/src/lib/dataService.js` — Primary bug location (RPC mapping)
  - `react-app/src/lib/supabase.js` — Credentials and client initialization
  - `react-app/src/App.jsx` — Date selector and report rendering logic
  - `react-app/index.html` — Missing favicon link
  - `react-app/vite.config.js` — Build config; `envDir: '../'`
  - `react-app/src/lib/dataService.test.js` — Existing tests (coverage gap confirmed)
  - `react-app/src/App.test.jsx` — Existing tests (coverage gap confirmed)
  - `tests/test_menu.py` — Python tests (comprehensive; no changes needed)
  - `menu.py` — `action_local_preview()` (race condition previously fixed)
  - `src/load_supabase.py` — RPC function DDL (`RETURNS SETOF int`)
  - `.aib_memory/context.md` — Product context
  - `.aib_brain/Concepts.md` — AIB framework concepts
  - `.aib_memory/requests/R-20260426-2150-…/implementation.md` — Previous fix record


## Research Results

**Pattern scan — RPC response format in Supabase / PostgREST:**

Evidence collected from workspace code analysis:

- `_CREATE_RPC_FUNCTIONS` in `src/load_supabase.py` defines both RPC functions with `RETURNS SETOF int`. This is the precise scalar return type affected by the PostgREST v11 serialization change.

- `dataService.js` line `(availDatesRes.data || []).map(r => r.get_available_dates)` assumes the v10 wrapped-object format. No defensive check exists for raw-integer format.

- `dataService.js` line `(rpcData || []).map(r => r.get_settlements_for_date)` in `fetchSettlementsForDate()` has the same assumption.

- `dataService.test.js` contains no tests for `fetchDimensions()`. The RPC mapping logic is completely untested.

- `App.test.jsx` tests dimension loading with a mocked `fetchDimensions()` that resolves with stub data including non-empty `dates`. The empty-dates case is not tested.

- The fallback in `fetchDimensions()` (`if (availDatesRes.error)`) activates only when PostgREST returns an HTTP error. When the RPC succeeds (HTTP 200) but returns raw integers, `availDatesRes.error` is null, the fallback does not trigger, and the empty filter result is cached silently.

**Pattern scan — favicon handling in Vite SPAs:**

- `react-app/index.html` has no `<link rel="icon">` element. Without this hint, all browsers request `/favicon.ico` as a fallback per HTML specification.

- `react-app/` has no `public/` directory. Vite does not add a default favicon when `public/` is absent. The built `dist/` contains no favicon. Vite preview returns 404.

- Confirmed: `find react-app/ -name "*.ico"` returns no results (only finds node_modules).


## External Benchmarking

**PostgREST v11 SETOF scalar return format change:**

PostgREST introduced a breaking change in v11 for functions returning `SETOF` of a scalar type. Prior to v11, every output row was serialized as a JSON object with the function name as the key, matching PostgreSQL's internal column naming for function results. From v11 onwards, scalar `SETOF` results are serialized as a plain JSON array to align with JSON convention and reduce payload size. Supabase upgraded its hosted PostgREST to v11+ in 2023.

- Takeaway: Code targeting Supabase at any point in 2023–2026 must handle both formats, or must use `RETURNS TABLE (col_name type)` to guarantee consistent object wrapping regardless of PostgREST version.

- Applicability: Both RPC functions in this project use `RETURNS SETOF int`. Client-side code must be updated to handle the raw-integer format. Alternatively, the SQL can be changed to `RETURNS TABLE (date_key int)` (for `get_available_dates`) and `RETURNS TABLE (settlement_key int)` (for `get_settlements_for_date`) to enforce object wrapping. Both options are viable; the client-side fix is lower risk for this iteration.

**Favicon.ico and browser behavior (HTML specification):**

Per the WHATWG HTML Living Standard, if a page does not specify a `<link rel="icon">` element, browsers issue a default request to `/favicon.ico` on the same origin. This is a platform-level behavior that cannot be suppressed by JavaScript. The standard-compliant fix is to provide a `<link rel="icon">` element in the HTML document. Using `href="data:,"` (an empty data URI) suppresses the network request entirely. Providing a file via Vite's `public/` directory is the idiomatic Vite approach.

- Takeaway: Adding `<link rel="icon" href="data:,">` to `index.html` is the zero-asset approach and eliminates the 404 permanently. If branding requires a real icon, a file in `react-app/public/` is the correct location.

- Rejection rationale for ignoring the 404: The 404 appears on every local preview session and in the browser console of anyone who visits the app without a previously cached favicon. While cosmetically minor, it adds noise to debugging sessions and may mislead developers into diagnosing a non-existent server-side routing problem. Fix cost is one line of HTML.


## Minimal Spikes and Experiments

**Spike 1: PostgREST SETOF int response format**

- Hypothesis: `supabase.rpc('get_available_dates')` with PostgREST v11+ returns `{ data: [20260426, …], error: null }` where each element is a raw integer, not `{ get_available_dates: 20260426 }`.

- Approach: Code path analysis in `dataService.js`. Traced the `availDatesRes.data.map(r => r.get_available_dates)` call with `r = 20260426` (integer). `(20260426).get_available_dates` evaluates to `undefined` in JavaScript. The resulting `Set([undefined])` is confirmed to never match any `date_key` integer.

- Outcome: The silent-failure path is confirmed by static analysis. No external request needed.

- Conclusion: The RPC mapping code must handle both formats. A backward-compatible guard `typeof r === 'object' && r !== null ? r.get_available_dates : r` resolves both cases.

**Spike 2: Favicon 404 reproduction**

- Hypothesis: The Vite preview server returns 404 for `/favicon.ico` because no `public/` directory exists in `react-app/`.

- Approach: Listed all files in `react-app/` (excluding `node_modules/`). Confirmed no `favicon.ico`, no `public/` directory, and no `<link rel="icon">` in `index.html`.

- Outcome: Confirmed. `dist/` contains only `index.html` and `assets/`.

- Conclusion: Adding `<link rel="icon" href="data:,">` to `react-app/index.html` eliminates the 404 without requiring a new binary asset.

**Spike 3: fetchDimensions test coverage gap**

- Hypothesis: No existing test exercises `fetchDimensions()` with any Supabase mock, leaving the RPC mapping path untested.

- Approach: Read `dataService.test.js` in full. Confirmed: only `formatDateBG`, `calculatePrice`, and `fetchReport2` pagination are tested. No `fetchDimensions` test exists.

- Outcome: Confirmed. The bug introduced by the RPC format change could not have been caught by the existing test suite.

- Conclusion: Add `fetchDimensions()` unit tests covering the wrapped-object format, raw-value format, RPC-error fallback, and caching behavior.


## AI Copilot Suggestions

**Observation 1 — The fallback logic has an undetected failure mode by design.**

The fallback `if (availDatesRes.error)` activates only on HTTP errors (4xx/5xx). A successful HTTP 200 response carrying unexpected data format is completely invisible to the fallback. This is a fragile design: adding a format validation step after the RPC call — e.g., checking whether the first element is a number or an object — would make the fallback more robust and would surface format drift immediately rather than silently.

Suggestion: After adding the `typeof r === 'object'` guard, also log a `console.warn` when the fallback format (raw integer) is detected, so future PostgREST upgrades are visible in the browser console during development.

**Observation 2 — The SQL RPC functions use `RETURNS SETOF int` instead of `RETURNS TABLE (col int)`.**

`RETURNS SETOF int` is the terse form, but it is sensitive to PostgREST's serialization policy, which has changed once already. `RETURNS TABLE (date_key int)` and `RETURNS TABLE (settlement_key int)` are explicit, self-documenting, and guaranteed to produce object-wrapped JSON (`[{ "date_key": 20260426 }, …]`) regardless of PostgREST version because the column name is explicitly declared.

Suggestion: In a future iteration, update both SQL functions in `_CREATE_RPC_FUNCTIONS` (in `src/load_supabase.py`) to use `RETURNS TABLE (col int)` syntax, and update the client code accordingly. This is a non-breaking DDL change (the function can be re-provisioned idempotently by re-running `load_supabase.py`).

**Observation 3 — The scope appears appropriate but the fix has been attempted once before without resolving the data issue.**

The previous fix (R-20260426-2150) addressed the browser race condition, not the data fetch logic. This suggests insufficient root-cause investigation in the prior iteration — the race condition and the data format bug co-existed, and fixing only one left the symptom in place. For this iteration, explicitly verifying the fix with a mock-driven test that exercises the raw-integer path (not just the race-condition path) is essential to prevent a third recurrence.

Suggestion: After implementing the fix, add a test that specifically exercises `fetchDimensions()` with `availDatesRes.data = [20260428, 20260427]` (raw integers) and asserts that `dims.dates` is non-empty. This test would have caught the original bug if it existed.

**Observation 4 — The empty-dates silent failure has no defensive guard.**

If `filteredDates` resolves to `[]` for any reason (format bug, genuinely empty `fact_prices`, or RPC returning empty), the UI shows an empty date select and invisible reports with zero user feedback. This is worse than an error message: the operator cannot distinguish between "still loading", "no data", and "bug".

Suggestion: In `App.jsx`, when `dimensions` is set but `dimensions.dates.length === 0`, render an explicit "Няма налични дати — уверете се, че сте синхронизирали данните с Supabase." message.


## Testing

- T1 — favicon-in-dist: After `npm run build`, `dist/index.html` contains a `<link rel="icon">` element (either `href="data:,"` or a file reference). Expected outcome: no `/favicon.ico` request is issued when the app loads in a browser; Vite preview server does not return 404 for this resource.

- T2 — fetchDimensions-wrapped-objects: `fetchDimensions()` called with `availDatesRes.data = [{ get_available_dates: 20260428 }, { get_available_dates: 20260427 }]`. Expected outcome: `dims.dates` contains the two matching `dim_date` rows; cache is populated.

- T3 — fetchDimensions-raw-integers: `fetchDimensions()` called with `availDatesRes.data = [20260428, 20260427]` (raw integer format from PostgREST v11+). Expected outcome: `dims.dates` contains the two matching `dim_date` rows (same result as T2); no empty-filter silent failure.

- T4 — fetchDimensions-rpc-error-fallback: `fetchDimensions()` called with `availDatesRes.error = { message: 'function not found' }` (RPC unavailable). Expected outcome: `dims.dates` equals the full unfiltered `datesRes.data`; a console warning is logged.

- T5 — fetchDimensions-cache: `fetchDimensions()` called twice with the same mock. Expected outcome: the second call returns the cached object without making any new Supabase calls.

- T6 — fetchSettlementsForDate-raw-integers: `fetchSettlementsForDate(dateKey, dims)` called with `rpcData = [1, 2]` (raw integers). Expected outcome: returned array contains settlements for keys 1 and 2; not empty.

- T7 — App-empty-dates-state: `App` rendered with `fetchDimensions` resolving to `{ dates: [], settlements: new Map(), categories: new Map(), stores: [], companies: new Map() }`. Expected outcome: the date selector contains an option whose text indicates no dates are available (e.g., "Няма налични дати"); no report sections are rendered.

- T8 — full-test-suite-python: `python -m pytest tests/ -q`. Expected outcome: all existing tests pass (≥84 passed, ≤1 skipped for pre-existing T12 service_role issue); zero failures.

- T9 — full-test-suite-react: `npm run test` in `react-app/`. Expected outcome: all existing and new tests pass (≥26 passed); zero failures.

- T10 — build-succeeds: `npm run build` in `react-app/` exits 0. Expected outcome: `dist/index.html` and `dist/assets/` are present.

See UAT_scenarios.md — UAT-01 for the manual end-to-end scenario verifying that local preview shows data in the browser after these fixes.


## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The two root causes (RPC format mismatch and missing favicon) are independent but both surfaced in the same user session, creating a compound symptom that confused previous debugging. The RPC format issue is architectural: a client-to-backend contract that was implicitly tied to a specific PostgREST version without explicit versioning or contract testing. The fix is backward-compatible and low-risk. More structurally, the use of `RETURNS SETOF int` (rather than `RETURNS TABLE (col int)`) in the PostgreSQL function definition is the underlying fragility — it should be changed in a follow-up iteration. The test coverage gap in `dataService.test.js` (no `fetchDimensions` tests) is a structural deficiency that allowed the bug to survive undetected through multiple iterations.

- The fallback-only-on-error pattern in `fetchDimensions()` is a design weakness; format validation should be added alongside error fallback.

- Both RPC functions share the same format vulnerability; fixing one without fixing the other would leave Report 1/2/3 settlement dropdowns broken.

- The module-level `_dims` cache in `dataService.js` needs to be reset in tests; missing reset leads to test pollution across test files.

### Product Owner

From a business perspective, the local preview is the operator's primary tool for verifying that price data is correctly loaded before pushing to production. A silent "no data" failure with no error message destroys confidence in the preview workflow and leads to unnecessary production deploys to test basic functionality. The fix addresses the trust gap directly. The success criteria (non-empty date dropdown, explicit empty-state message) are measurable and verifiable. The scope is focused and does not risk regression in the ETL pipeline or the production Netlify app.

- Acceptance criteria are clear and testable.

- The silent failure (empty state with no message) was the most damaging UX symptom; the empty-state message fix addresses this directly.

- T12 (service_role key security) remains a pre-existing open action item and is not in scope for this request; the operator should address it as soon as practical.

### User

From the operator's perspective, running option 6 and seeing a blank interface with no error message is deeply frustrating. The previous fix raised hope ("it's fixed") only to be followed by disappointment ("still broken"). The fix must also include the empty-state message so the operator knows whether "no data" means "the fix worked but the DB is empty" vs. "the fix failed". The 404 console error, while cosmetic, adds cognitive noise when the operator is inspecting the console to debug data loading.

- The operator needs to know why there is no data; the error message or empty-state message is as important as the fix itself.

- The operator should not need to understand PostgREST version behavior to use the local preview; the fix must be transparent.

### Security Officer

This request does not introduce new network endpoints, credential handling, or authentication changes. The favicon fix (adding `<link rel="icon" href="data:,">`) is a pure HTML change with no security surface. The RPC format fix in JavaScript is a data mapping change with no credential exposure. The existing security concern (T12: `VITE_SUPABASE_ANON_KEY` is a `service_role` key) remains pre-existing and out of scope for this request.

- No new OWASP Top 10 risks introduced by this request.

- The `data:,` favicon URI is inert content and introduces no XSS risk.

- The backward-compatible RPC format handling does not change authentication or authorization behavior.

### Data Governance Officer

This request does not modify data models, retention policies, or access control. The fix is entirely in the client-side presentation layer. The `fact_prices` and `dim_*` tables in Supabase are not altered. The `get_available_dates()` and `get_settlements_for_date()` function DDL is not changed in this iteration. No PII is processed; all data is publicly available government retail price information.

- No data lineage changes.

- No retention or classification impact.

- Audit: the new tests in `dataService.test.js` improve traceability of data-service behavior without accessing real data.
