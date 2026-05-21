## Executive Summary
- Request `R-20260512-0529` (`Improve slow pages by pushing aggregation to database`) asks for a performance refactor of the React analytics app so heavy report-query work happens in Supabase/PostgreSQL instead of the browser.

- The concrete example in the input is Report 1 (`Цени по категория`), where category grouping and averaging are currently performed in JavaScript after paginating raw fact rows from `fact_prices_lookback`.

- Current workspace evidence shows the same broader pattern in Report 2 and Report 3: they page raw fact rows into the client, enrich rows in JavaScript, and in Report 3 apply a browser-protection cap of 5,000 rows.

- The existing architecture already contains a suitable extension point for this work: `src/load_supabase.py` provisions SQL indexes and RPC functions for the React app, and the frontend already consumes those RPCs through the Supabase client.

- The recommended implementation direction is to extend the current database-function pattern with report-focused SQL/RPC contracts that return reduced result sets, while preserving current lookback semantics for `D`, `D-1`, and `D-2`.

- During this analysis run, `.aib_memory/request.md` was created and populated, including updated `Assumptions`, `Plan`, `Documentation`, `Questions & Decisions`, `Code and Asset Scan for Impacted Components`, and `Internal Review of Request and Product Docs` sections.

## Domain Knowledge Essentials
- `fact_prices_lookback`: the derived analytical fact table that stores the current day (`D`) plus lookback price columns for `D-1` and `D-2`; it is the primary query source for the React reports.
- `D`, `D-1`, `D-2`: the current retained analytical date and the two prior retained dates exposed in the app; correct routing between these dates matters because lookback rows are stored under the current date key.
- `EKATTE`: the Bulgarian settlement code registry used elsewhere in the product to identify settlements; it matters here because settlement filters drive report queries.
- `RPC` (remote procedure call): a database function exposed through Supabase/PostgREST so the browser can request computed data without implementing the logic client-side.
- `PostgREST`: the REST layer behind Supabase table and function access; it allows the React app to call SQL functions and read typed result sets.
- Impacted personas: public or analyst end users waiting for report pages to load, developers maintaining the React data layer, and operators reprovisioning Supabase-side database objects.
- Business processes touched: user exploration of category, settlement, and product pricing data; developer maintenance of performant analytical queries; operator workflow for database provisioning.
- Relevant metrics and acceptance signals: page latency, number of rows transferred to the browser, correctness of grouped and filtered report results, and preservation of current lookback-date behavior.
- Business acceptance impact: the request is satisfied only if users experience materially faster report behavior without losing coverage, filtering correctness, or trust in the results.

## Technical Knowledge & Terms
- `React 18`: the frontend framework used by the app; here it should remain a presentation layer rather than a bulk data-processing engine.
- `Vite`: the frontend build tool used by `react-app/`; it is not directly part of the performance bottleneck but constrains how frontend tests and builds are run.
- `Supabase JS`: the browser client library currently used to query tables and call RPC functions.
- `PostgreSQL aggregate functions`: built-in SQL functions such as `avg` and `count` that can perform grouping and summarization inside the database engine.
- `Table-valued function`: a SQL function that returns rows in a typed shape so PostgREST can expose it like a filtered resource.
- `Lookback routing`: the current logic in `dataService.js` that maps `date_key` selections to `current`, `day1`, and `day2` price columns using `lookbackColumnMap` and `currentDateKey`.
- Runtime constraints: the app is client-only, there is no custom backend service, Supabase anon access is already used for current reads, and database provisioning is owned by Python code in `src/load_supabase.py`.
- Non-functional attributes in scope: performance, correctness, idempotent database provisioning, testability, and low operational friction.

- Files read:
  - `.aib_memory/input.md`
  - `.aib_memory/requests_register.md`
  - `.aib_memory/context.md`
  - `.aib_brain/conventions/analysis-convention.md`
  - `.aib_brain/conventions/request-convention.md`
  - `react-app/src/lib/dataService.js`
  - `react-app/src/components/Report1.jsx`
  - `react-app/src/components/Report2.jsx`
  - `react-app/src/components/Report3.jsx`
  - `src/load_supabase.py`
  - `react-app/src/lib/dataService.test.js`
  - `react-app/src/components/Report1.test.jsx`
  - `tests/test_load_supabase.py`
  - `tests/test_transform.py`
  - `README.md`
  - `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/request.md`

- Evidence log:
  - `react-app/src/lib/dataService.js` shows `fetchReport1()` paginating raw `fact_prices_lookback` rows and averaging them in JavaScript -> Report 1 is a confirmed database-pushdown candidate.
  - `react-app/src/lib/dataService.js` shows `fetchReport2()` paginating raw rows, fetching product names separately, and enriching rows client-side -> Report 2 likely contributes to slowness through network and browser work.
  - `react-app/src/lib/dataService.js` shows `fetchReport3()` paginating raw rows and stopping at 5,000 rows -> the current design explicitly trades correctness or completeness risk for browser safety.
  - `src/load_supabase.py` already provisions RPC functions and supporting indexes for the React app -> the repository already has an accepted pattern for moving query logic into PostgreSQL.
  - `react-app/src/lib/dataService.test.js` and `tests/test_load_supabase.py` provide existing focused test surfaces -> the request can be implemented with narrow regression coverage rather than introducing a new test framework.

## Research Results
- Existing workspace pattern already favors server-side filtering when the browser would otherwise transfer unnecessary rows.
  - `get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, and `get_settlements_for_category` are all SQL functions provisioned in `src/load_supabase.py` and consumed from the frontend.
  - Implication: the requested refactor should extend the established SQL/RPC path instead of inventing a parallel architecture.

- Report 1 is the clearest root-cause hotspot in the current code.
  - `fetchReport1()` derives settlement store keys locally, pages every matching fact row into the browser, normalizes lookback columns, and computes average price per category in a JavaScript object accumulator.
  - Implication: a database `GROUP BY` with server-side effective-price calculation is the most direct fix for the example named in the request.

- Report 2 and Report 3 use the same anti-pattern at a larger row shape.
  - Both helpers fetch raw fact rows, normalize lookback columns in JavaScript, then enrich rows with product/store/company data client-side.
  - Implication: database pushdown should cover not only aggregation but also filtering, joining, ordering, and pagination where those operations currently happen in the browser.

- The current Report 3 implementation already contains an explicit symptom of browser overload.
  - The helper stops after 5,000 rows and logs whether the result was truncated.
  - Implication: performance work must also consider correctness and explicit pagination semantics, not just speed.

- Existing documentation will become stale immediately after implementation.
  - `.aib_memory/context.md` currently describes Report 1 as client-side aggregation and Report 3 as browser-capped.
  - Implication: context and README updates are part of request completion, not optional cleanup.

## External Benchmarking
- Supabase Database Functions guidance.
  - Takeaway: Supabase explicitly recommends database functions for data-intensive operations and supports returning row sets to clients.
  - Applicability: strong; this workspace already provisions and grants execute permissions on SQL functions through `src/load_supabase.py`.
  - Adoption rationale: use the same function-based pattern for heavy report queries instead of keeping bulk processing in the browser.
  - Rejection rationale: none for the core read path; this is aligned with the existing stack and operating model.

- PostgREST Functions as RPC guidance.
  - Takeaway: typed table-valued functions can be filtered, ordered, limited, and in some cases inlined, which keeps API behavior close to normal resource reads while letting the database own the heavy logic.
  - Applicability: high for Report 2 and Report 3, where the frontend currently needs joined or already-filtered row sets.
  - Adoption rationale: table-valued functions are a good fit when the frontend still needs rows, but not the full raw fact slice.
  - Adaptation rationale: use strict return types and stable parameter names so the frontend helpers remain predictable and testable.

- PostgreSQL aggregate-function guidance.
  - Takeaway: aggregates such as `avg`, `count`, `json_agg`, and ordered aggregates exist precisely to summarize row sets in the database, with optimizer support including partial/parallel aggregation in eligible cases.
  - Applicability: strongest for Report 1 grouping and any future summary-level reports.
  - Adoption rationale: use SQL aggregation for category averages and similar rollups instead of JavaScript accumulation loops.
  - Rejection rationale: avoid overusing JSON aggregation when simple typed rows are sufficient, because large JSON payloads can recreate transfer costs in a different format.

## Minimal Spikes and Experiments
- **Spike: Report 1 aggregation locus**
  - Hypothesis: Report 1 slowness is rooted in client-side grouping of raw fact rows.
  - Approach: Read `fetchReport1()` in `react-app/src/lib/dataService.js` and trace the control flow from `Report1.jsx` into the Supabase query path.
  - Outcome: The helper pages every matching fact row from `fact_prices_lookback`, normalizes lookback prices in JavaScript, and computes average price per category in the browser.
  - Conclusion: The request example points at a confirmed root cause, not a speculative optimization target.

- **Spike: Broader report-path client workload**
  - Hypothesis: more than one slow page is caused by the same browser-side data-processing pattern.
  - Approach: Read `fetchReport2()` and `fetchReport3()` plus the existing SQL-function provisioning in `src/load_supabase.py`.
  - Outcome: Both report helpers currently page raw rows and enrich them client-side, while the backend already provisions other report-supporting RPC functions and indexes.
  - Conclusion: the performance request should be implemented as a broader report-query pushdown effort, with Report 1 as mandatory scope and Report 2/3 as adjacent high-value scope.

## AI Copilot Suggestions
- Finding: the request is directionally correct but broader than necessary if interpreted as “rewrite every page.”
  - Suggestion: keep the implementation centered on the helpers that currently fetch raw `fact_prices_lookback` slices into the browser, because that is where the evidence-backed performance waste is today.

- Finding: moving computation to SQL without preserving `D`/`D-1`/`D-2` semantics would create a fast but wrong system.
  - Suggestion: treat current lookback routing as a non-negotiable contract and make it explicit in every new database-side query shape and test.

- Finding: Report 3 already shows that the current design protects the browser by truncating data rather than solving the query shape.
  - Suggestion: replace implicit browser-protection caps with explicit server-side pagination or scoped result contracts so users and tests can reason about completeness.

- Finding: the existing `load_supabase.py` ownership boundary is a strength and should not be bypassed.
  - Suggestion: keep new SQL functions, grants, and indexes in that provisioning path so the system remains auditable and idempotent.

- Scope note: the scope appears slightly larger than necessary if it includes every page indiscriminately, but appropriately sized if it is constrained to Report 1 plus any report helpers that still transfer large raw datasets and process them in the browser.

## Testing
- T1 — Request artifact creation: `.aib_memory/request.md`, `.aib_memory/analysis.md`, and the active request input archive exist with the expected request ID and title. Expected outcome: all files exist and contain the current request identity.
- T2 — Backend provisioning contract: targeted Python tests verify that `src/load_supabase.py` provisions any new report-oriented SQL functions, grants, and indexes required by the refactor. Expected outcome: the focused `tests/test_load_supabase.py` slice passes and DDL strings include the new contracts.
- T3 — Report 1 database aggregation: targeted frontend/helper tests verify that Report 1 no longer pages raw fact rows for category averaging and still returns the correct grouped result shape. Expected outcome: the affected `react-app/src/lib/dataService.test.js` and `react-app/src/components/Report1.test.jsx` tests pass.
- T4 — Report 2 database-side reduction: targeted frontend/helper tests verify that Report 2 relies on a reduced server-side contract rather than browser-side raw-row enrichment wherever the refactor touches it. Expected outcome: the affected `react-app/src/lib/dataService.test.js` and `react-app/src/components/Report2.test.jsx` tests pass.
- T5 — Report 3 server-side pagination or scoped result contract: targeted tests verify that Report 3 no longer depends on the old blind 5,000-row browser cap as its primary safety mechanism. Expected outcome: the affected `react-app/src/lib/dataService.test.js` and `react-app/src/components/Report3.test.jsx` tests pass.
- T6 — Focused test-suite execution: run the narrow Python and React suites covering the changed slice. Expected outcome: both commands exit successfully with no new failures in the touched area.
- T7 — Idempotent reprovisioning: re-running the relevant `load_supabase.py` provisioning path after no logical SQL changes produces no conflicting DDL behavior. Expected outcome: repeated provisioning remains safe and stable.
- T8 — Manual performance and UX validation: verify representative page loads, filter changes, and perceived responsiveness for the affected reports. Expected outcome: See `UAT_scenarios.md` — `UAT-01`, `UAT-02`, and `UAT-03`.

## Multi-Perspective Stakeholder Review
### Senior Solution Architect
The request is technically feasible and aligns with the system’s existing architectural seam: SQL functions provisioned by Python and consumed from a client-only React app. The main design risk is not feasibility but discipline: if the refactor only moves one calculation while leaving other heavy browser-side joins and pagination intact, the system will remain inconsistent and difficult to reason about.

- The current stack already supports server-side query logic through `src/load_supabase.py`, so no new platform layer is required.
- Lookback-date semantics are the main architectural invariant and must be preserved across any new SQL contracts.
- Report 3 needs an explicit completeness strategy, not just a faster version of the current truncation behavior.

### Product Owner
The user value is straightforward: faster report pages and less waiting. The scope is sufficiently clear for implementation because the request gives a concrete example and the code identifies the broader matching pattern, but acceptance should stay tied to observable behavior rather than only internal refactoring claims.

- Report 1 is mandatory because it is explicitly named in the request.
- “Some pages are slow” should be interpreted as “fix the evidence-backed slow report paths,” not “touch every page.”
- Acceptance should check both speed intent and unchanged analytical correctness.

### User
From the user perspective, the important outcome is that selecting dates, settlements, and categories feels responsive and returns complete, trustworthy results. Users do not care whether the logic lives in React or SQL, but they will notice if filters change behavior, results disappear, or slow pages remain slow.

- Faster initial response and filter changes are the primary visible win.
- Any change in row ordering, completeness, or lookback-date behavior will be perceived as a bug even if performance improves.
- Manual UAT is required because responsiveness and interaction smoothness are user-facing qualities, not just unit-test outcomes.

### Security Officer
The request does not inherently expand the security model, but new SQL functions exposed to anon users increase the importance of privilege discipline and predictable parameter handling. The current workspace already grants execute access on selected functions, so new database-side contracts must follow the same least-privilege review.

- Prefer `security invoker` defaults unless a stronger reason exists.
- Ensure new functions expose only the minimum columns needed by the frontend.
- Keep grants explicit and aligned with existing anon-read expectations.

### Data Governance Officer
This request changes data access shape rather than source lineage, but it still affects how analytical results are derived and documented. Moving logic into SQL improves traceability if the function definitions are versioned and tested, yet it also means product documentation must clearly describe where business calculations now live.

- Data lineage remains the same source-to-report path, but the computation locus shifts from browser code to SQL.
- Documentation must record the new query strategy so future analysis does not assume old client-side behavior.
- Tests should prove that report outputs did not drift when the logic moved layers.