## Goal
Improve slow React analytics pages by moving as much query iteration, filtering, grouping, and enrichment work as practical from the browser into Supabase/PostgreSQL. The explicit example from the request is the "Цени по категория" page, where category grouping should happen in the database instead of the frontend.

## Background
The active input reports that some pages are very slow and asks for a review of all places that iterate through database results so the work can be pushed back to the database. Product context and current source code show that the React app already uses PostgreSQL RPC functions for some server-side filtering (`get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, `get_settlements_for_category`), but the main report helpers still do significant client-side work. In particular, `react-app/src/lib/dataService.js` currently paginates raw `fact_prices_lookback` rows into the browser for Report 1, performs category averaging in JavaScript, performs row enrichment in JavaScript for Report 2 and Report 3, and hard-caps Report 3 at 5,000 rows to protect the browser. The request is therefore a root-cause performance refactor request centered on database pushdown rather than a cosmetic UI optimization.

## Scope
- Review all current React report helpers and related backend SQL provisioning to identify where the app iterates, aggregates, enriches, or filters large result sets client-side instead of in PostgreSQL.

- Redesign the affected query paths so server-side SQL or RPC functions perform the heavy work for the slow pages, with Report 1 category grouping treated as mandatory scope and Report 2 and Report 3 included wherever their current client-side iteration materially contributes to slowness.

- Preserve current analytical behavior and lookback-date semantics (`D`, `D-1`, `D-2`) while changing where the work is executed.

- Update automated tests for the refactored query path and document any required operator or product-context updates.

## Out of scope
- Replacing the React app architecture with a separate backend service.

- Redesigning page layout, charts, or styling beyond changes required by the new data contract.

- Refactoring ETL components that are unrelated to report-query performance, except for `src/load_supabase.py` changes needed to provision SQL functions, indexes, or other database-side support.

## Constraints
The implementation must stay within the current architecture: a client-only React app querying Supabase/PostgREST and a Python-owned database provisioning path in `src/load_supabase.py`. The request specifically prefers database pushdown and reduced frontend data processing, so any solution that still transfers large raw fact slices merely to aggregate them in React does not satisfy intent. Current lookback behavior based on `fact_prices_lookback`, `currentDateKey`, and `lookbackColumnMap` must remain correct for `D`, `D-1`, and `D-2`. Database changes must remain idempotent and compatible with the existing anon-access pattern used by current RPC functions.

## Success criteria
- Report 1 no longer pages raw fact rows into the browser to compute average price by category; the grouping and averaging happen in PostgreSQL or a Supabase-exposed database function.

- Any other slow report page currently iterating large raw datasets client-side is refactored so the heavy filtering, joining, aggregation, ordering, or pagination work is performed primarily in the database.

- The React app continues to return functionally correct results for current-date and lookback-date queries after the refactor.

- Focused automated tests cover the new database-facing query contracts and the affected frontend helpers/components.

- Documentation and workspace product context are updated to reflect the new performance-oriented query path and any operational implications.

## Assumptions
- A1: The user-reported slowness refers to the active React app in `react-app/`, not the legacy `build-legacy/web/` implementation.
  - Risk if false: Work could optimize the wrong UI surface.

- A2: The highest-value performance fixes are in the report helpers that currently page raw `fact_prices_lookback` rows and process them in JavaScript.
  - Risk if false: The implementation could miss a different bottleneck such as startup dimension loading or an unrelated browser render issue.

- A3: Extending the existing RPC/database-function pattern in `src/load_supabase.py` is acceptable and preferred over introducing a new service layer.
  - Risk if false: A later architectural preference could force rework.

- A4: Maintaining current report semantics is more important than preserving the exact current wire shape between Supabase and the frontend helpers.
  - Risk if false: Backend pushdown could be blocked by an unnecessary requirement to keep internal helper contracts identical.

## Plan
### Task 1: Bound the Slow Query Paths
**Intent:** Identify exactly which report helpers currently do heavyweight client-side iteration and what data shape each one should receive from the database instead.
**Inputs:** `.aib_memory/input.md`, `.aib_memory/context.md`, `react-app/src/lib/dataService.js`, `react-app/src/components/Report1.jsx`, `react-app/src/components/Report2.jsx`, `react-app/src/components/Report3.jsx`.
**Outputs:** A verified list of slow paths, their current client-side workloads, and the database-side contract needed for each.
**External Interfaces:** Supabase/PostgREST query model as represented in the current frontend code.
**Environment & Configuration:** No live credentials required for the analysis and local code trace.
**Procedure:** 1. Trace each report helper from component trigger to Supabase call. 2. Note where raw rows are paged into the client. 3. Note where grouping, joining, sorting, or truncation happens in JavaScript. 4. Distinguish mandatory scope from optional adjacent optimizations. 5. Record the candidate database pushdown targets.
**Done Criteria:** Each in-scope slow page has a clearly identified client-side hotspot and a candidate database-side replacement pattern.
**Dependencies:** None.
**Risk Notes:** Over-scoping low-value pages would dilute the performance work.

### Task 2: Design Database-Side Report Contracts
**Intent:** Define the SQL/RPC layer needed to return already-filtered, already-grouped, or otherwise reduced datasets for the affected pages.
**Inputs:** `src/load_supabase.py`, current RPC functions, current lookback-date routing rules, `fact_prices_lookback` schema assumptions.
**Outputs:** New or updated PostgreSQL functions, views, or indexed query paths suitable for the affected reports.
**External Interfaces:** Supabase PostgreSQL, PostgREST RPC exposure, anon-role execution grants.
**Environment & Configuration:** Must preserve idempotent database provisioning through `src/load_supabase.py`.
**Procedure:** 1. Reuse the existing RPC provisioning pattern where it fits. 2. Encode Report 1 aggregation in SQL. 3. Push Report 2 and Report 3 filtering/enrichment/pagination to SQL where the benefit is material. 4. Verify lookback routing is still correct. 5. Confirm the returned shapes are stable enough for the React helpers.
**Done Criteria:** The database can answer each in-scope report with a reduced result shape that removes the major client-side hotspot.
**Dependencies:** Task 1.
**Risk Notes:** Server-side pushdown that ignores lookback semantics would preserve speed but break correctness.

### Task 3: Refactor Frontend Data Helpers
**Intent:** Replace raw-row browser processing with thin frontend adapters over the new database-side contracts.
**Inputs:** `react-app/src/lib/dataService.js`, any updated report components, outputs from Task 2.
**Outputs:** Updated data helpers and any small component adjustments required by the new result shapes.
**External Interfaces:** Supabase JavaScript client, PostgREST RPC endpoints or table/view queries.
**Environment & Configuration:** Must preserve the current React/Vite runtime and existing environment-variable usage.
**Procedure:** 1. Swap client-side aggregation loops for database-backed reads. 2. Remove unnecessary client enrichment where SQL can return the required fields. 3. Preserve loading, error, and empty-state behavior. 4. Keep query logging meaningful for the new paths. 5. Verify page-level behavior remains correct.
**Done Criteria:** The affected helpers no longer perform the major client-side data processing that caused the slowness.
**Dependencies:** Task 2.
**Risk Notes:** An over-thin contract can still leave hidden heavy transforms in the frontend.

### Task 4: Add Focused Automated Tests
**Intent:** Cover all testable success criteria with regression tests for the new backend contracts and frontend helpers.
**Inputs:** `tests/test_load_supabase.py`, `react-app/src/lib/dataService.test.js`, `react-app/src/components/Report1.test.jsx`, `react-app/src/components/Report2.test.jsx`, `react-app/src/components/Report3.test.jsx`.
**Outputs:** New or updated automated tests plus the narrow commands needed to run them.
**External Interfaces:** Python test runner, React/Vitest test runner.
**Environment & Configuration:** Tests must remain offline and deterministic.
**Procedure:** 1. Add database-provisioning tests for any new SQL function definitions or indexes. 2. Add frontend helper tests for the new query path. 3. Add component tests where UI behavior depends on the changed result shape. 4. Run the narrow affected suites. 5. Fix regressions uncovered by those suites.
**Done Criteria:** All testable success criteria have explicit regression coverage and the affected suites pass.
**Dependencies:** Tasks 2 and 3.
**Risk Notes:** Tests that only assert call counts without asserting returned semantics could miss correctness regressions.

### Task 5: Validate Performance Intent and Functional Correctness
**Intent:** Verify that the refactor improved the query path without changing the observable report outcomes.
**Inputs:** Updated frontend helpers, updated SQL/RPC provisioning, existing query log page, representative report selections.
**Outputs:** Verification evidence for reduced client work and correct report results.
**External Interfaces:** Local React test/dev environment and, if used during implementation, configured Supabase access.
**Environment & Configuration:** May require the existing `.env` values when validating against a live Supabase instance.
**Procedure:** 1. Compare pre-change and post-change query shapes. 2. Confirm Report 1 still returns the correct category coverage. 3. Confirm Report 2 and Report 3 still return correct rows for representative filters. 4. Check that the browser no longer needs to page or aggregate the same large raw datasets. 5. Record any remaining manual performance checks in UAT.
**Done Criteria:** Functional outputs remain correct and the intended database pushdown is observable.
**Dependencies:** Tasks 3 and 4.
**Risk Notes:** A faster path that changes row coverage, ordering, or lookback behavior is not acceptable.

### Task 6: Update Context and Documentation
**Intent:** Reflect the new query strategy and any operator-visible implications in workspace documentation.
**Inputs:** `.aib_memory/context.md`, `README.md`, final implementation details from Tasks 2 through 5.
**Outputs:** Updated product context and repository documentation.
**External Interfaces:** Repository documentation files only.
**Environment & Configuration:** None.
**Procedure:** 1. Update `.aib_memory/context.md` with the new server-side report-query behavior. 2. Update `README.md` if query architecture or operational steps changed. 3. Note any required database reprovisioning or resync action. 4. Reconcile documentation with the shipped code.
**Done Criteria:** Product context and operator docs accurately describe the delivered behavior.
**Dependencies:** Tasks 2 through 5.
**Risk Notes:** Leaving context stale will cause future work to reason from outdated performance assumptions.

## Documentation
- `.aib_memory/context.md` (ref_id: N/A) — update the product context to record which reports now push aggregation/filtering into the database and how lookback semantics are preserved.
- `README.md` (ref_id: N/A) — update repository documentation if new RPC functions, indexes, or reprovisioning steps become part of the supported workflow.

## Questions & Decisions
No open questions at the current threshold. The request is implementable by extending the existing Supabase RPC/database-function pattern that the workspace already uses for server-side filtering.

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| react-app/src/lib/dataService.js | Modified | Contains the current client-side pagination, aggregation, enrichment, and row-cap logic for Reports 1, 2, and 3. |
| react-app/src/components/Report1.jsx | Modified | Consumes the Report 1 helper whose grouping should move into the database. |
| react-app/src/components/Report2.jsx | Modified | Depends on a helper that currently pages raw rows and enriches them client-side. |
| react-app/src/components/Report3.jsx | Modified | Depends on a helper that currently pages raw rows client-side and hard-caps them at 5,000. |
| src/load_supabase.py | Modified | Owns the existing RPC/index provisioning surface and is the correct place to add database-side support for the refactor. |
| react-app/src/lib/queryLog.js | Read-only dependency | Helps validate how the frontend query shape changes after pushdown. |
| react-app/src/lib/dataService.test.js | Modified | Best-fit location for helper-level regression tests of the new query contracts. |
| react-app/src/components/Report1.test.jsx | Modified | Best-fit location for Report 1 UI regression coverage. |
| react-app/src/components/Report2.test.jsx | Modified | Best-fit location for Report 2 UI regression coverage if returned row shape changes. |
| react-app/src/components/Report3.test.jsx | Modified | Best-fit location for Report 3 UI regression coverage if pagination or returned row shape changes. |
| tests/test_load_supabase.py | Modified | Best-fit location for SQL/RPC provisioning tests. |
| .aib_memory/context.md | Modified | Must reflect the new report-query architecture after implementation. |
| README.md | Modified | May need operator-facing notes for reprovisioning or query-architecture changes. |

## Internal Review of Request and Product Docs
- OK: `.aib_memory/input.md` — the user intent is explicit that database pushdown is preferred over frontend data processing.
- OK: `.aib_memory/context.md` — current product context already documents that Report 1 performs client-side average aggregation and that Report 3 has a 5,000-row frontend cap, which directly supports the request rationale.
- Missing info: `.aib_memory/input.md` — the request does not prioritize which slow pages beyond the explicit Report 1 example, so implementation should target the highest-cost client-side report helpers first.
- Cross-ref issue: `.aib_memory/context.md` — the documented architecture still describes Report 1, Report 2, and Report 3 as browser-heavy data paths, so that document will become outdated once the request is implemented.
- OK: `README.md` — the root documentation already explains `src/load_supabase.py` as the provisioning surface for Supabase-side structures, which aligns with the likely implementation path.