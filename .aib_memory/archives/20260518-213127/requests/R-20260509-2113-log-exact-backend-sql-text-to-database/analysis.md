## Executive Summary
- Request `R-20260509-2113` (`Log exact backend SQL text to database`) asks for a persistent audit trail in PostgreSQL that stores backend-issued SQL text together with timestamps.

- Current workspace evidence shows the existing Query Log feature is intentionally limited to frontend-visible Supabase request intent and explicitly does not guarantee exact backend SQL text.

- The repository-owned backend SQL path is `src/load_supabase.py`, which connects to PostgreSQL through `psycopg2` and emits both direct `execute()` calls and batched writes via `psycopg2.extras.execute_batch()`.

- The largest design fork is scope: logging only the Python ETL sync path is repository-controlled, while logging all product-triggered SQL would require Supabase-managed or server-level capabilities beyond current application ownership.

- The biggest implementation risk is exactness for batched statements, because stock `psycopg2` logging helpers do not transparently cover every batched execution path used in the current sync module.

- This analysis run added or refreshed the implementation-facing sections in `request.md`: `Assumptions`, `Plan`, `Documentation`, `Questions & Decisions`, `Code and Asset Scan for Impacted Components`, and `Internal Review of Request and Product Docs`.

## Domain Knowledge Essentials
- Supabase: hosted PostgreSQL plus API tooling used as the product's cloud database layer.
- ETL sync: the Python process that provisions tables and pushes transformed CSV outputs into Supabase.
- SQL audit log: a durable record of executed database statements used for debugging, forensics, or operational review.
- Query intent log: a higher-level record of what the client asked for, without guaranteeing the exact database SQL text actually executed.
- Timestamped audit entry: a log row containing when a database statement was issued, which is explicitly requested here.
- Operator: the maintainer who runs ETL scripts locally and needs traceability when database sync behavior is suspicious.
- Analyst/debugger: the stakeholder who may inspect query behavior to understand data discrepancies.
- Business process touched: ETL-to-cloud sync observability, not public analytics behavior.
- Business acceptance impact: the request is satisfied only if operators can inspect a durable backend SQL trail that is materially different from the transient browser-session log already in the product.
- KPI impact: improved debugging traceability and lower mean time to identify database-side sync issues; possible tradeoff in sync runtime and log-table growth.

## Technical Knowledge & Terms
- `psycopg2`: the PostgreSQL driver used by `src/load_supabase.py` to connect and execute SQL directly against `DATABASE_URL`.
- `execute_batch`: a `psycopg2.extras` helper that sends repeated SQL statements in grouped batches to reduce round trips.
- DDL (Data Definition Language): SQL that creates or alters schema objects such as tables, functions, and indexes.
- DML (Data Manipulation Language): SQL that inserts, updates, deletes, or truncates data rows.
- `log_statement`: PostgreSQL server setting that can log statement text at the database level.
- pgAudit: a PostgreSQL extension that enriches audit logging with structured statement metadata and object-level context via the standard server logging facility.
- `LoggingConnection`: a `psycopg2.extras` helper that logs queries executed through the connection, but with explicit limitations around some bulk execution paths.
- Idempotent provisioning: rerunning schema setup safely without duplicating or breaking objects already created.
- Evidence -> implication:
- `src/load_supabase.py` provisions schema and performs all repository-owned direct SQL against Supabase -> this file is the primary implementation surface.
- `src/load_supabase.py` calls `psycopg2.connect(db_url)` directly -> application-level SQL interception is feasible in repository code for that path.
- `src/load_supabase.py` uses `execute_batch` for bulk upserts and lookback inserts -> naive cursor logging may miss or misrepresent some high-volume statements.
- `react-app/src/components/QueryLogPage.jsx` states the page shows client intent rather than exact backend SQL -> the request is not already satisfied by the existing UI.
- PostgreSQL logging docs describe `log_statement`, `log_parameter_max_length`, CSV logs, and JSON logs -> server-level logging can capture statement text but depends on database-level privileges/configuration.
- pgAudit documentation describes detailed session/object audit logging through PostgreSQL's logging facility -> there is a mature server-side audit pattern, but it requires privileged extension setup outside normal repo code ownership.
- Files Read:
- `.aib_memory/input.md`
- `.aib_memory/requests_register.md`
- `.aib_memory/instructions.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/analysis-convention.md`
- `.aib_brain/conventions/request-convention.md`
- `README.md`
- `src/load_supabase.py`
- `tests/test_load_supabase.py`
- `react-app/src/lib/queryLog.js`
- `react-app/src/components/QueryLogPage.jsx`

## Research Results
- Pattern scan against workspace history shows a recent observability feature already exists, but it is deliberately scoped to browser-session request metadata and not durable backend SQL capture.
- Product context and README agree that the React app is client-only, which means browser traffic does not pass through a repository-owned backend where exact SQL could be intercepted in application code.
- The Python ETL sync module is the only current component in the repo that sends direct SQL to PostgreSQL, so it provides the narrowest falsifiable implementation slice for this request.
- Existing tests for `src/load_supabase.py` rely on mocked connections and SQL-string assertions, which is a good fit for adding audit-table DDL and logging-helper coverage without introducing live database dependencies.
- The current sync workflow mixes schema DDL, direct execute calls, and batch helpers in one module, so any audit solution must address both transactional correctness and recursion avoidance when writing to the log table itself.
- No existing repository document specifies retention, redaction, or privacy rules for a high-volume SQL audit trail, so those become request-level decisions rather than inherited standards.

## External Benchmarking
- PostgreSQL server logging (`log_statement`, CSV log, JSON log) is a proven baseline for capturing statement text at the database layer.
  - Applicability: strong for product-wide SQL capture because it records statements at the server boundary and can include application name, session ID, and statement text.
  - Adoption assessment: useful when the requirement truly means all database traffic, but it depends on privileged PostgreSQL/Supabase settings that repository code alone may not control.
  - Rationale: adapt only if stakeholders confirm server-managed logging is acceptable and deployment ownership exists; otherwise reject for the initial repo-scoped implementation.
- pgAudit is a mature audit extension that enriches PostgreSQL logging with statement class, object name, and structured audit fields.
  - Applicability: strongest for compliance-grade auditing or broad product-wide query forensics.
  - Adoption assessment: technically attractive, but likely too heavy and privilege-dependent for a repository-only change in a managed Supabase environment.
  - Rationale: reject as the default implementation path unless the user explicitly wants database-admin level auditing and accepts extension/configuration prerequisites.
- `psycopg2.extras.LoggingConnection` offers application-level query logging inside the Python client.
  - Applicability: good fit for the existing ETL sync path because `src/load_supabase.py` already owns the connection factory.
  - Adoption assessment: promising for direct `execute()` coverage, but insufficient by itself because psycopg2 documents that some bulk execution paths such as `executemany()` are not logged, and the current code uses `execute_batch()` for high-volume writes.
  - Rationale: adapt the pattern, not the stock helper blindly; a custom logging wrapper is more likely to satisfy the exactness requirement for this codebase.

## Minimal Spikes and Experiments
- **Spike: Backend scope boundary**
  - Hypothesis: The repository contains only one backend path that directly emits SQL to PostgreSQL.
  - Approach: Read product context, README, and the direct connection/setup path in `src/load_supabase.py`.
  - Outcome: The React app is client-only, while `src/load_supabase.py` is the direct `psycopg2` client to PostgreSQL.
  - Conclusion: A repository-owned implementation can reliably target the Python ETL sync path; broader SQL capture would require different architecture or privileged database logging.
- **Spike: Off-the-shelf client logging coverage**
  - Hypothesis: Stock psycopg2 logging helpers will not fully cover the current sync module's batch-heavy execution model.
  - Approach: Compare `psycopg2` logging documentation with the code paths in `src/load_supabase.py` that use `execute_batch`.
  - Outcome: The docs show logging helpers exist, but the sync module's bulk paths require explicit handling beyond naive connection logging.
  - Conclusion: Exact backend SQL capture in this repo likely needs a custom wrapper or helper around both direct executes and batch execution.

## AI Copilot Suggestions
- Finding: The request is underspecified about what “backend” means in a product that mixes a client-only React app with a Python ETL backend.
  - Actionable suggestion: Decide the logging boundary first and keep the first implementation constrained to one execution path unless a broader architecture change is explicitly approved.
- Finding: “Exact SQL text” is easy to say but difficult to guarantee once batch helpers and server-side rewriting enter the picture.
  - Actionable suggestion: Define exactness in terms of the chosen logging boundary and document whether the stored text is application-emitted SQL, server-logged SQL, or structured audit output.
- Finding: A log-every-query table can create non-trivial storage and performance pressure, especially during large ETL upserts.
  - Actionable suggestion: Require an explicit retention decision and test the logging approach against batch-heavy sync operations before treating it as production-safe.
- Finding: The existing frontend Query Log creates a naming collision risk because operators may assume it already covers this request.
  - Actionable suggestion: Update docs and UI copy where needed so frontend request logging and backend SQL auditing are presented as separate observability layers.
- Scope note: The current request appears slightly larger than necessary if it is interpreted as all product-triggered SQL; it becomes appropriately scoped if limited to the repository-owned Python backend path first.

## Testing
- T1 — Audit table DDL presence: Inspect the schema-provisioning SQL in `src/load_supabase.py` after implementation. Expected outcome: automated assertion confirms the audit table definition and any required supporting indexes/columns are present.
- T2 — Direct statement logging helper: Exercise the logging wrapper for a normal `cursor.execute()` path with mocked connection/cursor objects. Expected outcome: a timestamped log-row insert is issued with the expected SQL text and recursion protection for audit-table writes.
- T3 — Batch statement logging coverage: Exercise the batch execution path used for dimension upserts or lookback inserts. Expected outcome: automated assertion confirms the chosen batch-logging design records the intended SQL payload for each approved batch operation.
- T4 — Targeted unit-test run: Run the focused backend test slice covering `tests/test_load_supabase.py`. Expected outcome: the targeted suite exits successfully and covers the new audit behavior without requiring a live database.
- T5 — Re-run idempotency: Execute provisioning logic twice in the mocked test path. Expected outcome: the second run succeeds without duplicate-object failures and does not regress existing create-table behavior.
- T6 — Documentation content check: Inspect `README.md` and `.aib_memory/context.md` after implementation. Expected outcome: automated content assertions confirm the docs clearly state backend audit scope and distinguish it from the frontend session query log.

## Multi-Perspective Stakeholder Review
### Senior Solution Architect
This request is technically feasible if it is constrained to the Python ETL sync path, because the repository already owns that connection boundary. It becomes architecturally different if it is interpreted as all product SQL, because the React app bypasses any custom backend and talks to Supabase directly.

- The narrow repo-owned solution lives in `src/load_supabase.py` and fits the current architecture.
- Full-product SQL capture likely requires server logging, extensions, or a new middleware/backend layer.
- Batch execution coverage and self-logging recursion are the main design integrity risks.
- A precise definition of “exact SQL” is necessary before implementation can be evaluated fairly.

### Product Owner
The business value is clear: operators want durable visibility into backend database activity, not just a transient browser-session log. The scope wording, however, leaves room for materially different interpretations that change cost and delivery risk.

- The request solves a real debugging gap left by the current frontend Query Log page.
- Acceptance criteria should explicitly say which backend path is covered.
- Retention policy is missing even though “log every SQL query” implies ongoing storage cost.
- A minimal first increment focused on ETL sync has better delivery odds than a product-wide audit redesign.

### User
An operator or analyst will benefit from a durable log only if it is easy to trust what it covers and what it does not. Confusion between the existing Query Log page and the requested backend SQL log would reduce usability.

- Users need a clear explanation that the current browser-session log is not the same artifact.
- Timestamped records improve troubleshooting only when the source scope is obvious.
- If log rows are too noisy or too voluminous, inspection will become less useful over time.
- Consistent wording in docs matters because the product already has one “query log” concept.

### Security Officer
Logging full SQL text can materially increase exposure, because statements may include values that were previously transient only in process memory. The request is permissible, but only with explicit acknowledgment of sensitive-data and privilege boundaries.

- Full SQL text may include business data values and should be treated as sensitive operational data.
- Server-level logging or pgAudit may require elevated privileges not currently exercised by repository code.
- In-database retention should be bounded unless there is a clear compliance reason to keep everything indefinitely.
- The audit table itself must avoid becoming a new unrestricted data-exposure surface.

### Data Governance Officer
This request creates a new data asset with its own lineage and retention obligations. Even if it is “just logs,” it still contains derived operational data about how the product writes to PostgreSQL.

- The audit table needs explicit lineage: source is backend SQL emitted by repository-owned sync code.
- Retention and purge policy are mandatory governance questions, not optional implementation details.
- The log should be documented separately from the analytical star schema so users do not confuse it with business facts.
- If parameter values are stored, classification may be broader than simple operational metadata.