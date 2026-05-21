## Goal
Investigate why the React analytics app appears to visualize incorrect data by exposing a dedicated query-log page for the current app session. The page must help the user inspect the database queries triggered by the app across startup and report interactions so the incorrect data path can be diagnosed with concrete evidence.

## Background
The active input says the visualized data seems incorrect and asks for deeper investigation of the queries issued to the database. The current product context shows that the React app is a client-only React + Vite SPA that queries Supabase directly through `@supabase/supabase-js` and shared data-service helpers. Today the app has four pages and no built-in observability surface for database activity, so when a report looks wrong there is no in-app way to inspect which Supabase table or RPC requests were triggered during the active browser session.

## Scope
- Trace all current React-side database reads that occur during app startup and during interactions with the existing report pages.

- Define and add a new app page that displays session-scoped query activity from all components that issue database reads through the current app architecture.

- Capture enough per-entry detail to support debugging of incorrect visualizations, including the query target, filters or parameters, selected fields when available, timing, outcome, and originating app surface.

- Integrate the new page into the current navigation and ensure it reflects query activity generated in the same browser app session.

- Add automated tests for the logging behavior and page rendering, plus any required manual UAT for user-visible debugging flow.

- Update workspace context and operator-facing documentation to reflect the added observability page and any stated limitations of what can be logged from the browser client.

## Out of scope
- Building a full database-audit pipeline or long-term historical query storage outside the current app session.

- Changing ETL transformations, Supabase schema design, or report calculations unless analysis later proves they are needed for this request.

- Logging secrets, credentials, or unrelated browser/network activity.

## Constraints
The React app must remain a client-only Supabase consumer with the current credential model and without introducing server-side secrets into the frontend. The logging behavior must preserve existing report functionality and should not materially change the semantics of the underlying queries. The request must be analyzed against the current architecture, where most database access is routed through `react-app/src/lib/dataService.js` and `react-app/src/lib/supabase.js`. Because the app uses PostgREST and RPC calls through the Supabase browser client, literal backend SQL text may not be directly available from the client layer and any limitation must be documented explicitly. The logging surface must remain scoped to the current session and avoid persisting sensitive data unnecessarily.

## Success criteria
- A new React app page exists and is reachable from the main app navigation for inspecting session query activity.

- Query activity from app startup and all existing report-related database reads is recorded in the same active app session and shown on the new page.

- Each log entry contains enough debugging detail to identify what the app requested from Supabase and whether the request succeeded or failed.

- Automated tests cover the query-log capture path and the new page behavior, and affected test suites pass.

- Documentation and `.aib_memory/context.md` are updated to reflect the new page, its intended debugging role, and any limitation between client-visible request details and true backend SQL text.

## Assumptions
- A1: The debugging surface should cover the active React app in `react-app/`, not the archived legacy app in `build-legacy/web/`.
  - Risk if false: The implementation could instrument the wrong frontend surface and miss the user-visible issue.

- A2: “Current session” means the currently running browser app session and does not require persistence across a full page reload or deployment boundary.
  - Risk if false: The solution would need durable storage or backend support that materially expands scope.

- A3: The current React database-read surface is concentrated in `fetchDimensions()` and the exported report/filter helpers in `react-app/src/lib/dataService.js`, making a shared instrumentation layer practical.
  - Risk if false: Direct ad hoc Supabase calls outside the shared data layer could be missed by the logger.

- A4: Unless explicitly redirected by a decision, the recommended interpretation of “logged SQL queries” is a browser-visible log of Supabase/PostgREST and RPC request intent rather than exact backend SQL text.
  - Risk if false: The request would require database-side auditing or statement-statistics infrastructure instead of, or in addition to, frontend instrumentation.

## Plan
### Task 1: Inventory Query Entry Points
**Intent:** Confirm every current React-side database access path that must feed the session log.
**Inputs:** `.aib_memory/input.md`, `.aib_memory/context.md`, `react-app/src/App.jsx`, `react-app/src/lib/dataService.js`, `react-app/src/lib/supabase.js`, existing React components.
**Outputs:** Verified list of startup, report, and filter query paths with owning modules.
**External Interfaces:** Supabase browser client API surface.
**Environment & Configuration:** React app runtime with existing `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` behavior.
**Procedure:** 1. Read the shared data layer and startup flow. 2. Map each exported fetch helper and the page that triggers it. 3. Confirm whether any direct Supabase calls bypass the shared helper layer. 4. Record the minimal instrumentation boundary that covers all relevant reads.
**Done Criteria:** Every query source that should appear in the log is mapped to an owning function or module.
**Dependencies:** None.
**Risk Notes:** Missing a direct call site would produce incomplete session logs and reduce debugging trust.

### Task 2: Finalize Logging Semantics and Session Model
**Intent:** Translate the request into a concrete logging contract that fits the current browser-based Supabase architecture.
**Inputs:** Findings from Task 1, `.aib_memory/context.md`, external benchmarking on PostgREST and Supabase observability, Q001 if answered.
**Outputs:** Agreed log-entry shape, session lifecycle, and instrumentation approach.
**External Interfaces:** Supabase/PostgREST request model; optional Supabase database observability features if chosen.
**Environment & Configuration:** Current client-only architecture; no new secrets in frontend code.
**Procedure:** 1. Compare client-visible request metadata with true database-side SQL capture options. 2. Resolve the requested meaning of “SQL queries” using the existing decision threshold flow. 3. Define the fields each entry must capture. 4. Define when the session log starts, clears, and updates.
**Done Criteria:** A single logging contract exists that can be implemented without architectural ambiguity.
**Dependencies:** Task 1.
**Risk Notes:** Choosing the wrong logging level can create either misleading output or unnecessary database-side complexity.

### Task 3: Implement Shared Query Logging Layer
**Intent:** Add the smallest shared instrumentation surface that records query activity from all relevant components.
**Inputs:** `react-app/src/lib/dataService.js`, `react-app/src/lib/supabase.js`, final logging contract from Task 2.
**Outputs:** Shared session log store and instrumented query helpers.
**External Interfaces:** Supabase table queries and RPC calls.
**Environment & Configuration:** Existing React/Vite frontend runtime and module structure.
**Procedure:** 1. Add a shared logger or store for session entries. 2. Wrap or centralize relevant Supabase query calls. 3. Capture start, completion, timing, and error state. 4. Preserve existing returned data contracts for the report components. 5. Verify startup and report flows still function.
**Done Criteria:** Relevant queries are recorded without breaking current report behavior.
**Dependencies:** Task 2.
**Risk Notes:** Over-instrumentation inside each component would be harder to maintain and easier to apply inconsistently.

### Task 4: Add Query Log Page and Navigation
**Intent:** Expose the captured session log through a dedicated debugging page in the React app.
**Inputs:** `react-app/src/App.jsx`, `react-app/src/App.css`, existing page layout patterns, shared log store from Task 3.
**Outputs:** New page component, navigation entry, and readable log presentation.
**External Interfaces:** Session log store only.
**Environment & Configuration:** Existing React component structure and current visual language.
**Procedure:** 1. Add a new page identifier and navigation button. 2. Create the query-log page component. 3. Render session entries with status, origin, parameters, and timing. 4. Add an empty state and failure state handling where needed. 5. Confirm logs update as the user navigates reports.
**Done Criteria:** The user can open the new page and inspect query activity from the active session.
**Dependencies:** Task 3.
**Risk Notes:** A page that only shows opaque raw objects will not be useful for debugging incorrect visualizations.

### Task 5: Add Automated Validation
**Intent:** Cover all testable success criteria for session query logging and page rendering.
**Inputs:** Existing tests in `react-app/src/App.test.jsx`, `react-app/src/lib/dataService.test.js`, and component test files; implementation from Tasks 3 and 4.
**Outputs:** New or updated tests plus runnable commands for the affected slices.
**External Interfaces:** Vitest and Testing Library.
**Environment & Configuration:** No live network access; Supabase client mocked in tests.
**Procedure:** 1. Add unit coverage for query-log capture. 2. Add component coverage for the new page and navigation. 3. Verify startup queries and report-triggered queries appear in the log. 4. Run the narrow React test suite for touched files. 5. Re-run to confirm deterministic results.
**Done Criteria:** All testable success criteria have automated coverage and the affected test commands pass.
**Dependencies:** Tasks 3 and 4.
**Risk Notes:** Weak mocks could prove only rendering, not that the intended query metadata is captured.

### Task 6: Update Context and Documentation
**Intent:** Record the added query-log page and its observability limits for future work.
**Inputs:** `.aib_memory/context.md`, `README.md`, final implementation behavior, any resolved decision from Q001.
**Outputs:** Updated product context and operator-facing documentation.
**External Interfaces:** Repository documentation files.
**Environment & Configuration:** None beyond repository write access.
**Procedure:** 1. Update `.aib_memory/context.md` with the new page and logging behavior. 2. Update `README.md` with debugging usage notes if relevant. 3. Document limitations around client-visible request details versus backend SQL visibility. 4. Reconcile the docs with the implemented UI and tests.
**Done Criteria:** Documentation matches the delivered behavior and known limitations.
**Dependencies:** Tasks 3 through 5.
**Risk Notes:** If limitations are undocumented, future debugging work may assume the page exposes true backend SQL when it does not.

## Documentation
- .aib_memory/context.md (ref_id: N/A) — update the product context to describe the new query-log page and how session query visibility works.
- README.md (ref_id: N/A) — add or adjust operator/developer guidance for using the new debugging page and understanding its limits.

## Questions & Decisions
**Q001**: What should the new page display as the “SQL queries” for this browser-based Supabase app?
- [ ] Option A: True database-side SQL statements captured through Supabase/Postgres observability or auditing, even if that requires DB-side setup and may not map cleanly to only the current browser session.
- [ ] Option B: App-session Supabase request logs that show table or RPC target, selected columns, filters or parameters, timing, and result status as a practical proxy for the issued query intent. *(recommended)*
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| react-app/src/App.jsx | Modified | The app currently defines four pages and main navigation; a new query-log page must be integrated here. |
| react-app/src/App.css | Modified | The new page needs styling consistent with the current app UI. |
| react-app/src/lib/dataService.js | Modified | This is the main shared query surface for startup, report, and filter reads that should feed the session log. |
| react-app/src/lib/supabase.js | Modified | The shared Supabase client is the narrowest place to add or support reusable instrumentation if needed. |
| react-app/src/components/Report1.jsx | Read-only dependency | Existing report component triggers logged queries and is part of the cross-component coverage requirement. |
| react-app/src/components/Report2.jsx | Read-only dependency | Existing report component triggers logged queries and is part of the cross-component coverage requirement. |
| react-app/src/components/Report3.jsx | Read-only dependency | Existing report component triggers logged queries and is part of the cross-component coverage requirement. |
| react-app/src/App.test.jsx | Modified | Best-fit location for navigation and page-rendering regression coverage. |
| react-app/src/lib/dataService.test.js | Modified | Best-fit location for query-log capture and shared data-layer regression tests. |
| react-app/src/components/ | Created | A new query-log page component will likely be added under the existing components structure. |
| .aib_memory/context.md | Modified | Product context must record the additional page and observability behavior. |
| README.md | Modified | Documentation should explain how to use the page and what query details it does or does not expose. |

## Internal Review of Request and Product Docs
- OK: `.aib_memory/input.md` — the user intent is concrete about adding a new page for session query inspection in order to debug incorrect visualized data.
- OK: `.aib_memory/context.md` — the product context clearly states that the React app is a client-only SPA that queries Supabase directly through the browser, which constrains what query detail is naturally visible from the frontend.
- Ambiguity: `.aib_memory/input.md` — the phrase “logged SQL queries” can mean either exact backend SQL text or a frontend-visible log of Supabase/PostgREST request intent, and those imply materially different solutions.
- Missing info: `.aib_memory/input.md` — the request does not specify whether logs must survive a browser refresh or only the current in-memory session; the current analysis resolves this to the active session unless directed otherwise.
- Cross-ref issue: `.aib_memory/context.md` — the product context currently says the React app has four views, while this request introduces a likely fifth page and therefore requires a context update after implementation.