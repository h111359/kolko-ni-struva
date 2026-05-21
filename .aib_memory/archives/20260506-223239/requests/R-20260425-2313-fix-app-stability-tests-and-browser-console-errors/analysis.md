# Analysis: R-20260425-2313 — Fix app stability, tests, and browser console errors

## Executive Summary

- **Request ID:** R-20260425-2313

- **Title:** Fix app stability, tests, and browser console errors

- **High-level purpose:** The request addresses four concerns in a single iteration: (1) diagnosing and fixing the root cause of the local preview (menu option 6) failing to display Supabase data; (2) auditing and eliminating browser console errors and warnings; (3) introducing rigorous, codebase-wide automated test coverage currently absent from three of the five Python ETL modules and all React source files; (4) fixing the confirmed pagination bug in `fetchReport2`.

- **Request scope summary:** Affects `menu.py`, `react-app/src/lib/dataService.js`, `tests/` (new Python test files), and `react-app/` (new Vitest configuration and test files). No changes to ETL transform logic, Supabase schema, or Netlify configuration.

- **Key risk:** The scope is broad — combining a bug fix, a console-audit task, and a full test-coverage initiative. Each sub-goal has its own complexity. The combination increases the risk of scope creep and regression surface.

- **Sections added or updated in `request.md` during this run:** Assumptions (A1–A8), Plan (Tasks 1–10), Documentation, Questions & Decisions (Q001–Q002), Code and Asset Scan for Impacted Components, Internal Review of Request and Product Docs.

- **Files read during analysis:** `.aib_memory/context.md`, `src/load_supabase.py`, `src/extract.py` (context reference), `src/transform.py` (context reference), `src/config_utils.py` (context reference), `src/deploy_netlify.py` (context reference), `menu.py`, `react-app/vite.config.js`, `react-app/src/lib/supabase.js`, `react-app/src/lib/dataService.js`, `react-app/src/App.jsx`, `react-app/src/components/Report1.jsx`, `react-app/src/components/Report2.jsx`, `react-app/src/components/Report3.jsx`, `react-app/src/components/HomePage.jsx`, `react-app/src/main.jsx`, `react-app/package.json`, `tests/test_config_utils.py`, `tests/test_deploy_netlify.py`, `data/schema/dim_settlement.csv` (header only).


## Domain Knowledge Essentials

- **Retail price transparency (Bulgarian government mandate):** Bulgarian law requires retail companies to report daily product prices through the kolkostruva.bg portal. The pipeline processes this government-published open data.

- **EKATTE:** Bulgarian administrative unit registry code. Each settlement has a unique EKATTE code. In the star-schema, the `dim_settlement` table uses column `ekatte` (not `ekatte_code`) to store this code.

- **Fact table partitioning:** Fact rows are stored per calendar date as `data/schema/facts/YYYY-MM-DD.csv`. The Supabase `fact_prices` table aggregates all synced date partitions.

- **Local preview (menu option 6):** Runs `npm run build` then `npm run preview` from `react-app/`. The build step is a production build by Vite, which bakes environment variables into the bundle at compile time. The running preview server serves the compiled bundle — no runtime env var resolution.

- **Operator persona:** The primary user of the local preview is the data engineer who wants to validate the React app against real Supabase data before deploying to Netlify production.

- **End user persona:** Public internet users who access the React app on Netlify to explore Bulgarian retail price data.

- **KPIs affected:** Application reliability (zero console errors on load), operator confidence (green test suite before deploy), data completeness (pagination fix in Report 2 ensures all products are shown).


## Technical Knowledge & Terms

- **Vite build-time env var injection:** Vite's `import.meta.env.VITE_*` variables are replaced at bundle compile time by the Vite build process. They are NOT available at runtime via the OS environment. The `envDir: '../'` in `react-app/vite.config.js` tells Vite to look for `.env` in the project root (parent of `react-app/`). If `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` are absent from the root `.env` when `npm run build` is executed, the bundle will embed `undefined` for both values.

- **`credentialsError` guard in `supabase.js`:** When either VITE_ key is falsy, `supabase.js` exports a non-null `credentialsError` string and exports `null` as the Supabase client. `App.jsx` reads `credentialsError` in its initial state and skips the `fetchDimensions()` call if it is truthy. This prevents null-pointer crashes but means the app shows a Bulgarian-language error message and no data.

- **Supabase PostgREST default row cap:** Supabase's PostgREST layer returns at most 1 000 rows per unauthenticated query unless `.range()` is used to paginate. Queries without `.range()` silently truncate at 1 000 rows.

- **React Strict Mode double-invoke:** `main.jsx` wraps the app in `<React.StrictMode>`. In development (`npm run dev`), React intentionally renders components twice to surface side effects. In production builds (`npm run build`), Strict Mode double-render is disabled. Console warnings visible in dev may not appear in production.

- **Module-level dimension cache (`_dims`):** `dataService.js` caches the full dimension response in a module-level variable. Once populated, the cache is never invalidated within a single page session. A failed initial load leaves `_dims = null` permanently for the session, requiring a page refresh.

- **Vitest:** Vite-native unit test runner. Configured via `vitest.config.js` or inside `vite.config.js`. Uses the same Vite transform pipeline, making it the natural choice for React + Vite projects. Supports `jsdom` or `happy-dom` for DOM environment emulation.

- **React Testing Library (RTL):** DOM-oriented testing library. Renders React components into a DOM environment (jsdom) and exposes queries (`getByText`, `getByRole`, etc.) to assert rendered output without coupling tests to implementation details.

- **pytest:** Python's standard unit testing framework. `python -m pytest tests/` discovers all `test_*.py` files under `tests/`. Coverage reporting via `pytest-cov`.

- **RPC functions (Supabase):** `get_available_dates()` and `get_settlements_for_date(p_date_key bigint)` are PostgreSQL functions provisioned by `load_supabase.py`. They require `GRANT EXECUTE TO anon`. If not provisioned, `dataService.js` falls back gracefully but emits `console.warn`.

- **Files read evidence log:**

  | Evidence | Implication |
  |---|---|
  | `react-app/vite.config.js` has `envDir: '../'` | VITE_ vars are loaded from project root `.env` at build time only |
  | `react-app/src/lib/supabase.js` exports `credentialsError` when VITE_ keys are falsy | Missing `.env` keys cause no-data display without crashing |
  | `react-app/src/lib/dataService.js` `fetchReport2` uses a single `.from().select()` without `.range()` | Report 2 silently truncates at 1 000 rows when a category+settlement has > 1 000 products |
  | `react-app/package.json` has no `test` script and no Vitest/Jest dependency | Zero automated tests for the React app currently |
  | `tests/` contains only `test_config_utils.py` and `test_deploy_netlify.py` | `extract.py`, `transform.py`, and `load_supabase.py` have no tests |
  | `data/schema/dim_settlement.csv` header is `settlement_key,ekatte,settlement_name` | The DB column and `dataService.js` query are both `ekatte`; `context.md` incorrectly documents it as `ekatte_code` |
  | `main.jsx` uses `<React.StrictMode>` | Double renders in dev; not a bug in production |


## Research Results

### Pattern scan — local preview data failure

The local preview failure matches a well-known Vite pattern: build-time environment variable injection requires the `.env` file (or matching shell variables) to be present at the moment `vite build` executes. The `action_local_preview()` function in `menu.py` runs `npm run build` inside `react-app/` without verifying that `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set. If the root `.env` is absent or incomplete, the build silently embeds empty strings. The `credentialsError` path in `supabase.js` then activates, displaying only the error message.

No prior request has addressed this validation gap. Menu option 5 (`action_deploy_netlify`) validates credentials before building because `deploy_netlify.py` does explicit credential checking; menu option 6 (`action_local_preview`) has no equivalent check.

### Pattern scan — `fetchReport2` pagination

`fetchReport2` in `dataService.js` uses a single Supabase query without `.range()`. The `fetchReport1` and `fetchReport3` equivalents both paginate correctly (Report 1 with full pagination, Report 3 capped at 5 000 rows). Report 2 is the only report function missing pagination, making it a consistency gap and a potential data-correctness bug for busy settlement+category combinations.

### Pattern scan — console warnings

Two `console.warn` calls exist in `dataService.js`. Both are guarded by the error path of the respective RPC calls (`availDatesRes.error` and `rpcError`). If the operator has run `load_supabase.py` after R-20260422-0902 (which provisions the RPC functions), neither warning fires. If RPC functions are absent, both fire on every page load. The warnings do not constitute unhandled errors but represent a degraded data path.

### Pattern scan — test coverage gaps

Three Python ETL modules have zero test coverage: `src/extract.py`, `src/transform.py`, `src/load_supabase.py`. These modules contain the most complex and risky logic in the codebase (network I/O, file I/O, database writes). The existing tests cover only `config_utils.py` and `deploy_netlify.py`.


## External Benchmarking

- **Vitest for React + Vite projects:** The Vite ecosystem recommends Vitest as the default test runner for Vite-based projects. Vitest reuses the same Vite config (including `envDir`, plugins, and module resolution), meaning the same `.env` mock patterns used in app code work in tests. React Testing Library integrates with Vitest via `@testing-library/react` and a `jsdom` environment declaration. This approach is adopted by the majority of production Vite + React projects. Applicability: high; the test stack should be Vitest + `@testing-library/react` + `jsdom`.
  - Key takeaway: Vitest + RTL eliminates a separate Jest config and aligns with the existing Vite toolchain.
  - Applicability: adopt for this request.

- **pytest + pytest-mock for Python ETL tests:** `pytest-mock` (wrapping `unittest.mock`) is the standard approach for mocking `requests`, `psycopg2`, and file system I/O in ETL pipelines. Widely adopted in data engineering projects. The existing `test_deploy_netlify.py` already uses `unittest.mock.patch`, so using `pytest-mock` extends the existing pattern.
  - Key takeaway: Use `unittest.mock` (already used) or `pytest-mock` for mocking HTTP and DB calls. No new patterns required.
  - Applicability: adopt; pattern already established in existing tests.

- **Vite env var validation patterns (industry practice):** In production Vite applications, it is common to add a startup guard in the Supabase client module (or a dedicated `env.js`) that throws a descriptive error when required env vars are absent. This pattern surfaces missing config earlier (at build time or module load time) rather than silently rendering an empty UI. Some projects use a `validate-env.js` script called as a pre-build step.
  - Key takeaway: Adding an env var check in `menu.py`'s `action_local_preview()` before `npm run build` is a lightweight, menu-native implementation of the same pattern.
  - Applicability: adopt; the check belongs in `menu.py` since the build is always invoked from there for local preview.

- **Pagination correctness in Supabase PostgREST clients:** PostgREST's default row limit (1 000 without a `Range` header) is well-documented and a common source of silent data truncation. All production Supabase clients in data-intensive applications paginate or explicitly set a higher count header. The pattern in `fetchReport1` (paginate until last page) and `fetchReport3` (cap at 5 000 rows, paginate in pages of 1 000) are both standard. `fetchReport2` is inconsistent with these patterns.
  - Key takeaway: `fetchReport2` must be updated to paginate using the same `.range()` approach as `fetchReport1`.
  - Applicability: adopt.


## Minimal Spikes and Experiments

- **Spike: Vite env var embedding mechanism**
  - Hypothesis: `VITE_*` variables are embedded at `vite build` time from the `envDir` path; they are not resolved at `vite preview` serve time.
  - Approach: Inspected `react-app/vite.config.js` (`envDir: '../'`), `react-app/src/lib/supabase.js` (reads `import.meta.env.VITE_SUPABASE_URL`), and the Vite documentation model for build vs. serve.
  - Outcome: Confirmed — `import.meta.env` values are replaced by string literals during `vite build`. At preview time, the server just serves the pre-built static files; no env var resolution occurs.
  - Conclusion: The local preview will never show Supabase data unless `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are present in the project root `.env` at the moment `npm run build` is executed. The fix must happen before `npm run build`.

- **Spike: `fetchReport2` pagination**
  - Hypothesis: `fetchReport2` does not paginate and may silently return < total rows.
  - Approach: Compared `fetchReport2` source in `dataService.js` with `fetchReport1` and `fetchReport3`.
  - Outcome: `fetchReport1` paginates via `while (!done) { ... .range(from, to) }`. `fetchReport3` paginates with a 5 000-row cap. `fetchReport2` uses a single `.from('fact_prices').select().eq().eq().in()` with no `.range()` — confirming the pagination gap.
  - Conclusion: `fetchReport2` will silently truncate results at 1 000 rows. The fix is to add the same `.range()` pagination loop as `fetchReport1`.

- **Spike: Column name `ekatte` vs `ekatte_code`**
  - Hypothesis: `context.md` may have a documentation inconsistency about the settlement dimension column name.
  - Approach: Read header of `data/schema/dim_settlement.csv`; inspected `DIM_TABLES` descriptor in `load_supabase.py`; inspected `fetchAllRows('dim_settlement', 'settlement_key,settlement_name,ekatte')` in `dataService.js`.
  - Outcome: The CSV header and DB column are both `ekatte`. `context.md` incorrectly documents the column as `ekatte_code`. `dataService.js` uses the correct column name `ekatte`.
  - Conclusion: No code bug; documentation-only discrepancy. `context.md` must be corrected.

- **Spike: Browser console errors under valid credentials**
  - Hypothesis: Under valid credentials and provisioned RPC functions, the React app produces zero console errors.
  - Approach: Reviewed all `console.*` calls in React source files; traced error handling paths in `App.jsx`, `dataService.js`, and page components.
  - Outcome: Zero `console.error` calls in React source. Two `console.warn` calls in `dataService.js` are guarded by RPC error paths and do not fire when RPC functions are provisioned. No unhandled promise rejections in the main application flow (all async calls are wrapped in try/catch). React Strict Mode double-render is production-disabled.
  - Conclusion: With provisioned RPC functions and valid credentials, the app should produce zero console output in production. The prerequisite is that `load_supabase.py` has been run after R-20260422-0902.


## AI Copilot Suggestions

- **Observation 1 — Scope breadth creates execution risk.** This request bundles four distinct concerns: a local preview bug fix, a browser console audit, comprehensive test coverage for 5 previously untested modules, and a data pagination fix. Each sub-goal is individually reasonable, but together they form one of the largest scopes in this project's history. The risk is that the iteration becomes a multi-week effort with unclear completion gates.
  - Suggestion: Define explicit "done" criteria for each sub-goal independently. If the test coverage initiative is blocking a quicker fix for the local preview and pagination bugs, consider splitting this request: one focused fix request (local preview + pagination + console) and a separate dedicated test-coverage request. The analysis plan reflects a combined approach, but the implementer should be aware of the split risk.

- **Observation 2 — Test coverage scope for `transform.py` is non-trivial.** `src/transform.py` performs multi-step ZIP extraction, CSV parsing with delimiter auto-detection, dimension upsert, and atomic file writes. Unit-testing this module requires careful mocking of `zipfile`, file system paths, and the dimension state. Under-investment in test design here will produce brittle tests that break on minor refactors rather than catching real regressions.
  - Suggestion: Prioritize integration-style tests that run `transform.py` against a small synthetic ZIP fixture with known content, rather than unit-testing individual internal functions. This approach catches more real-world regressions with fewer mocks.

- **Observation 3 — The React test scope may be larger than the stated success criterion implies.** "Cover the whole code" in the input is ambitious. `dataService.js` alone makes six Supabase calls that all require mocking. Each page component has multiple render states (loading, error, empty, data-loaded). A complete test suite for the React layer is a non-trivial standalone project.
  - Suggestion: Limit the React test scope to: (a) helper function unit tests (`formatDateBG`, `calculatePrice`, pagination logic); (b) smoke-render tests for each component (renders without crashing under mocked props); (c) the `fetchReport2` pagination regression test. Full interactive behavior tests (user clicks dropdown → data loads) should be scoped to UAT scenarios rather than automated component tests, to keep the test suite maintainable.

- **Observation 4 — Scope appears appropriate overall, but the test coverage sub-goal is larger than the bug-fix sub-goals.** The local preview fix and pagination fix are each small (< 20 LOC). The console audit is nearly complete (nothing to fix if RPC functions are provisioned). The test coverage initiative is the dominant effort in this request. The success criteria reflect this correctly.
  - Suggestion: Ensure the plan tasks are sequenced so the bug fixes (Tasks 1–4) are delivered first and independently verifiable. Test coverage tasks (Tasks 5–9) should be implementable in any order after.


## Testing

- T1 — Local preview credential check: Run `menu.py` option 6 with a root `.env` that has valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. Expected outcome: Build succeeds, preview server starts, browser shows populated date selector and page content (not credential error message).

- T2 — Local preview missing credential detection: Run `menu.py` option 6 with `VITE_SUPABASE_URL` absent from `.env` (or an empty `.env`). Expected outcome: `action_local_preview()` prints an actionable error message and exits before running `npm run build`, without leaving a corrupted build artifact.

- T3 — fetchReport2 pagination: Call `fetchReport2` with a mocked Supabase client that returns exactly 1 000 rows on the first page and 50 rows on the second. Expected outcome: The returned array has 1 050 rows, confirming pagination is active.

- T4 — Browser console zero errors (UAT): Load the production preview in a browser with valid credentials and provisioned RPC functions. Expected outcome: DevTools console shows zero errors and zero warnings. See UAT_scenarios.md — UAT-01.

- T5 — fetchDimensions caches result: Call `fetchDimensions()` twice with a mocked Supabase client. Expected outcome: The Supabase client's `from()` method is called only once for `dim_date` (not twice), confirming module-level cache is used.

- T6 — formatDateBG: Call `formatDateBG('2026-04-25')`. Expected outcome: Returns `'25.04.2026'`.

- T7 — calculatePrice promo active: Call `calculatePrice({ retail_price: '5.00', promo_price: '3.50' })`. Expected outcome: Returns `3.5`.

- T8 — calculatePrice no promo: Call `calculatePrice({ retail_price: '5.00', promo_price: null })`. Expected outcome: Returns `5.0`.

- T9 — extract.py ZIP link parsing: Call `parse_zip_links` with synthetic HTML containing two `.zip` href attributes. Expected outcome: Returns a list of two absolute ZIP URLs in descending sorted order.

- T10 — extract.py incremental download skip: Simulate `existing_filenames` returning a set containing the latest ZIP filename. Expected outcome: `download_file` is not called (no new download initiated).

- T11 — transform.py delimiter auto-detection: Pass a CSV row containing a single semicolon-delimited field. Expected outcome: Re-read uses `;` delimiter; first data row has the expected number of columns.

- T12 — load_supabase.py create_tables DDL: Call `create_tables(conn)` with a mocked psycopg2 connection. Expected outcome: The mock cursor's `execute` method is called at least once with DDL containing `CREATE TABLE IF NOT EXISTS dim_date`.

- T13 — load_supabase.py get_latest_remote_date: Mock a psycopg2 cursor that returns `[(20260424,)]`. Expected outcome: `get_latest_remote_date()` returns `20260424`.

- T14 — Python test suite passes: Run `python -m pytest tests/ -v`. Expected outcome: All tests pass, exit code 0.

- T15 — React test suite passes: Run `npm run test` in `react-app/`. Expected outcome: All tests pass, exit code 0.

- T16 — Re-run idempotency (local preview): Run menu option 6 twice in succession. Expected outcome: Second run succeeds and shows data without requiring manual intervention.

> See UAT_scenarios.md — UAT-01 for the browser console visual verification scenario.


## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request correctly targets the most critical stability gaps: missing Vite build-time credential validation (a developer experience failure), a data correctness bug in `fetchReport2`, and the absence of automated tests for the most complex ETL modules. The architecture remains sound — no new components, no new dependencies beyond a test runner. The primary architectural risk is the breadth of the test scope: generating tests for `extract.py` and `transform.py` requires significant mocking investment, and poorly scoped tests may couple to implementation rather than behavior, becoming a maintenance burden rather than a safety net.

- The local preview fix is low-risk and high-value: a pre-build env var check in `menu.py` resolves the data display failure without touching the React build configuration.
- Adding Vitest to `react-app/package.json` is a standard, low-risk dependency addition; it does not affect the production build output.
- `fetchReport2` pagination fix brings consistency with `fetchReport1` and `fetchReport3`; the change is localized to one function in `dataService.js`.
- Risk: If `transform.py` tests are implemented as integration tests requiring a real filesystem and ZIP fixtures, test execution time may increase materially. Consider synthetic fixture design carefully.
- Risk: The `load_supabase.py` tests require mocking psycopg2 at a low level; incorrect mock setup may produce tests that pass even when the production code is broken.

### Product Owner

This request directly addresses operator frustration (local preview not working) and pre-production confidence (console errors, test coverage). Both are blocking concerns for production readiness. The success criteria are measurable: zero console errors, green test suite, data visible in local preview. The scope is larger than a typical single-request iteration but the user has explicitly requested comprehensive coverage.

- Business value is high: a reliable local preview reduces the risk of deploying a broken React app to production, where it is publicly visible.
- The acceptance criteria are appropriately specific and testable.
- Risk: The request conflates a quick bug fix (local preview, pagination) with a long-term quality initiative (test coverage). If resources are constrained, the bug fixes should be prioritized over test coverage for immediate production safety.
- The "Cover the whole code" intent is ambitious; it is scoped in the request to a realistic subset (helper functions, smoke renders, ETL functions). This scoping is appropriate.

### User

The primary end-user impact of this request is indirect: a more stable and correctly paginated app means Report 2 shows complete product listings rather than silently cutting off at 1 000 rows. The local preview fix benefits the operator, not the end user directly. Browser console error elimination is a professionalism/reliability signal.

- End users may currently see incomplete Report 2 results for busy settlement+category combinations without knowing data is missing. The pagination fix is a silent but meaningful improvement.
- No visible UI changes are expected from this request; the user experience remains the same except for potential additional Report 2 rows.
- The credential error message shown when VITE_ keys are absent is correctly shown only to the operator (in local preview context), not to production end users.
- Risk: If the test suite is introduced but not maintained, it becomes stale and creates false confidence. Stakeholders should be aware that test maintenance is a recurring commitment.

### Security Officer

No new credentials, API keys, or secrets are introduced by this request. The test suite must use mocked Supabase connections and must not embed real credentials in test files or fixtures. The local preview pre-build check must not log or print the credential values to stdout.

- The env var validation in `action_local_preview()` must check only for the presence (non-empty) of the VITE_ vars, not print their values.
- Vitest test files must mock `import.meta.env` values using Vitest's built-in env override mechanism (e.g., `import.meta.env.VITE_SUPABASE_URL = 'https://test.supabase.co'` in test setup), not by reading real `.env` values.
- Python test files must not import or use real psycopg2 connections; mocking must be complete.
- No new file permissions or secret storage changes are required.
- Risk: If test fixtures include hardcoded Supabase URLs (even fake ones) that resemble production URLs, they may be mistakenly used in production contexts. Use clearly fake values (e.g., `https://test.supabase.co`, `test-anon-key`).

### Data Governance Officer

This request has no direct impact on data lineage, retention, or classification. The `fetchReport2` pagination fix is a data completeness improvement: it ensures that all product rows meeting the selected filter criteria are returned and displayed. The test coverage for ETL modules improves auditability of data transformations.

- No schema changes; no new data sources; no new data stored.
- The pagination fix in `fetchReport2` affects display completeness only — no data is modified or deleted.
- `context.md` contains a documentation error (`ekatte_code` vs `ekatte` for `dim_settlement`); correcting this improves data lineage traceability.
- Risk: If the `load_supabase.py` tests mock database operations at too high a level, they may not catch real data integrity regressions (e.g., incorrect upsert conflict resolution). Recommend that at least one test verifies the SQL conflict clause format.
