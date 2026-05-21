## Goal
Create persistent database-side logging for backend-issued SQL so the product stores each backend SQL statement together with its execution timestamp for later inspection.

## Background
The current product already has a React Query Log page, but both the product context and the UI copy state that it records frontend-visible Supabase request intent rather than the exact SQL text executed by the backend. The only repository-owned backend component that currently sends raw SQL directly to PostgreSQL is `src/load_supabase.py`, which uses `psycopg2` to provision schema objects and sync ETL outputs into Supabase. The new request asks for an in-database log table that stores the exact SQL text sent from the backend to the database, with timestamps, so operators can inspect backend database activity without relying on transient browser-session logs.

## Scope
- Provision a dedicated SQL audit log table in the Supabase/PostgreSQL database used by `src/load_supabase.py`.

- Capture backend-issued SQL text together with execution timestamp and enough origin metadata to inspect what the repository-owned backend sent to PostgreSQL.

- Integrate the logging path into the Python database sync flow in `src/load_supabase.py`, including schema-provisioning and data-sync statements emitted by that module.

- Add automated coverage for the provisioned audit schema and the logging helpers, and update product documentation/context to describe the new capability and its limits.

## Out of scope
- Capturing browser-originated Supabase/PostgREST traffic issued directly from `react-app/`, because the current React app is client-only and does not pass through a repository-owned backend.
- Building a new React page or operator UI for browsing the persistent SQL log unless separately requested.
- Changing Supabase instance-wide logging settings outside repository-owned code unless that approach is explicitly chosen.

## Constraints
- The current product has no custom server backend for React traffic; the direct backend-to-database path in this repository is `src/load_supabase.py`.
- The request explicitly requires exact SQL text plus timestamp storage in a database table.
- The solution must preserve the current idempotent ETL sync workflow and avoid avoidable regressions in large-batch load performance.
- The current sync layer relies on `psycopg2` and `psycopg2.extras.execute_batch`, so batched statements must be considered explicitly.
- Any approach that depends on Supabase-managed PostgreSQL server configuration or privileged extensions may exceed what this repository can enforce by code alone.

## Success criteria
- A backend SQL audit table is provisioned in the target PostgreSQL database and stores timestamped SQL log records.
- Running the repository-owned backend sync path records backend-issued SQL into that table for the approved scope.
- Automated tests cover the schema/logging behavior and confirm re-run safety for repeated provisioning.
- Documentation and product context clearly distinguish the new backend SQL audit trail from the existing frontend session query log.

## Assumptions
- A1: The current request targets SQL issued by `src/load_supabase.py`, because this repository has no other persistent backend component that sends direct SQL to PostgreSQL.
  - Risk if false: The delivered solution would miss browser-originated or Supabase-managed traffic the requester expected.
- A2: “Exact SQL text” means the SQL string emitted by the selected logging mechanism at the application or database boundary, even when batch helpers collapse multiple executions into grouped statements.
  - Risk if false: The implementation could be rejected because the recorded text differs from the requester's interpretation of exactness.
- A3: Re-running `src/load_supabase.py` is the accepted mechanism for applying schema changes related to the new audit table.
  - Risk if false: The provisioned schema could diverge from the deployment path the operator expects.
- A4: Log growth and retention policy are implementation-relevant and need an explicit decision before shipping a high-volume audit table.
  - Risk if false: The log table could grow without bounds or be pruned more aggressively than stakeholders expect.

## Plan
### Task 1: Confirm Logging Boundary
**Intent:** Lock the intended logging scope so implementation targets the correct backend execution path.
**Inputs:** `.aib_memory/request.md`, `.aib_memory/context.md`, answers to `Q001` and `Q002`.
**Outputs:** Finalized request scope and constraints embedded in the active request.
**External Interfaces:** Supabase/PostgreSQL logging boundary; repository-owned Python sync path.
**Environment & Configuration:** No new environment required; decision must respect current Supabase deployment control.
**Procedure:** 1. Resolve whether logging is limited to `src/load_supabase.py` or must cover broader database traffic. 2. Resolve retention expectations for the audit table. 3. Update scope/constraints language if the answers narrow or expand implementation. 4. Record any accepted limitations in docs.
**Done Criteria:** The target execution path and retention approach are unambiguous and implementation can proceed without hidden scope forks.
**Dependencies:** None.
**Risk Notes:** Mis-scoping this task creates architectural rework later.

### Task 2: Design Audit Table And Logging API
**Intent:** Define the schema and helper surface required to store timestamped SQL log records safely.
**Inputs:** `src/load_supabase.py`, external logging research, approved scope decisions.
**Outputs:** Updated DDL and internal helper design for backend SQL audit logging.
**External Interfaces:** PostgreSQL table DDL; `psycopg2` connection/cursor behavior.
**Environment & Configuration:** Must work with existing `DATABASE_URL` connection flow; no hardcoded secrets.
**Procedure:** 1. Add the audit table DDL and indexes if needed. 2. Define what metadata accompanies the SQL text and timestamp. 3. Decide how logging is invoked for direct executes and batch helpers. 4. Preserve idempotent provisioning semantics.
**Done Criteria:** The sync module can create/verify the audit table and has a clear internal interface for recording statements.
**Dependencies:** Task 1.
**Risk Notes:** Overly detailed schema increases write overhead and retention pressure.

### Task 3: Instrument Backend SQL Emission
**Intent:** Capture backend-issued SQL from the approved path without breaking the sync workflow.
**Inputs:** `src/load_supabase.py`, `psycopg2` logging capabilities, current DDL/DML execution flow.
**Outputs:** Modified sync path that records approved SQL statements into the audit table.
**External Interfaces:** `psycopg2.connect`, cursor execution, `psycopg2.extras.execute_batch`.
**Environment & Configuration:** Must run in the existing Python 3.9+ environment with current dependencies.
**Procedure:** 1. Wrap or extend connection/cursor handling for statement capture. 2. Cover both ordinary `execute()` calls and batched writes. 3. Prevent recursive self-logging loops for inserts into the audit table. 4. Keep failure handling compatible with the existing transaction model.
**Done Criteria:** Approved SQL statements are persisted with timestamps during a normal sync run and the sync still completes successfully.
**Dependencies:** Task 2.
**Risk Notes:** Batch logging and recursion control are the main correctness risks.

### Task 4: Add Automated Test Coverage
**Intent:** Protect the new audit behavior with fast repository-local checks.
**Inputs:** `tests/test_load_supabase.py`, modified sync helpers, success criteria.
**Outputs:** Expanded unit tests covering DDL, logging helper behavior, and rerun safety.
**External Interfaces:** Python unittest runner.
**Environment & Configuration:** Must remain runnable without a live database by using mocks.
**Procedure:** 1. Add tests for the audit table DDL. 2. Add tests for direct statement logging. 3. Add tests for batched statement logging or its chosen abstraction. 4. Add rerun/idempotency assertions for provisioning behavior.
**Done Criteria:** Targeted tests fail without the feature and pass with the feature; all testable success criteria are represented.
**Dependencies:** Tasks 2 and 3.
**Risk Notes:** Tests that overfit string formatting can become brittle if SQL assembly changes.

### Task 5: Execute Focused Validation
**Intent:** Verify the changed slice using the narrowest available automated checks.
**Inputs:** Updated Python source and tests.
**Outputs:** Test execution evidence for the request scope.
**External Interfaces:** `python -m unittest` or equivalent targeted test invocation.
**Environment & Configuration:** Local Python environment with repository dependencies installed.
**Procedure:** 1. Run the targeted `tests/test_load_supabase.py` suite. 2. Fix any audit-log regressions surfaced by the test run. 3. Re-run the same targeted suite until it passes. 4. Record any environment blocker if execution cannot complete.
**Done Criteria:** Focused automated validation for the touched slice exits successfully or a concrete blocker is documented.
**Dependencies:** Task 4.
**Risk Notes:** Mock-based tests do not prove Supabase privilege compatibility.

### Task 6: Update Documentation And Product Context
**Intent:** Keep repository docs aligned with the delivered backend logging behavior and limitations.
**Inputs:** `README.md`, `.aib_memory/context.md`, final implementation behavior.
**Outputs:** Updated operator documentation and workspace product context.
**External Interfaces:** None.
**Environment & Configuration:** Documentation must reflect actual runtime requirements and any retention/config constraints.
**Procedure:** 1. Document what the backend SQL log captures. 2. Document what remains out of scope, especially frontend Supabase traffic. 3. Update product context with the new database artifact and behavior. 4. Note any discrepancies found while implementing.
**Done Criteria:** Docs and context match the shipped behavior and no longer describe the old state as complete.
**Dependencies:** Tasks 1 through 5.
**Risk Notes:** Stale docs will cause operators to confuse frontend request logging with backend SQL logging.

## Documentation
- README.md (ref_id: N/A) — document the backend SQL audit table, how it is populated, and how it differs from the frontend session query log.
- .aib_memory/context.md (ref_id: N/A) — record the new audit-table capability and its scope boundaries in the product context.

## Questions & Decisions
**Q001**: Which database traffic must this request log?
- [ ] Option A: Only SQL issued by `src/load_supabase.py` through the repository-owned `psycopg2` backend path. *(recommended)*
- [x] Option B: All SQL ultimately triggered by the product, including browser-originated Supabase traffic executed inside Supabase-managed services.
- [ ] Other: ___
> Answer: 

**Q002**: What retention policy should apply to the SQL audit table?
- [ ] Option A: Keep log rows indefinitely until manually purged.
- [x] Option B: Apply a bounded rolling-retention policy managed by repository code. *(recommended)*
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| src/load_supabase.py | Modified | Owns the direct backend-to-PostgreSQL SQL path and schema provisioning flow. |
| tests/test_load_supabase.py | Modified | Needs coverage for audit-table DDL and statement logging behavior. |
| README.md | Modified | Must explain the new backend SQL audit capability and its limitations. |
| .aib_memory/context.md | Modified | Must record the new product capability after implementation. |
| react-app/src/lib/queryLog.js | Read-only dependency | Existing session log demonstrates the current frontend-only logging surface and its limitation. |
| react-app/src/components/QueryLogPage.jsx | Read-only dependency | Existing UI text explicitly says it does not guarantee exact backend SQL text. |

## Internal Review of Request and Product Docs
- OK: `.aib_memory/context.md` — confirms the existing React Query Log page records client-visible request metadata rather than exact backend SQL text.
- OK: `README.md` — documents the same frontend logging limitation and supports the need for a separate backend audit trail.
- Ambiguity: `.aib_memory/request.md` — the phrase “from the backend to the database” can reasonably mean only the Python ETL sync path or a broader product-wide SQL path.
- Missing info: `.aib_memory/request.md` — retention and purge expectations for a potentially high-volume SQL log table are not specified.
- Missing info: `.aib_memory/request.md` — required metadata beyond timestamp and SQL text, such as source operation, status, or duration, is not specified.