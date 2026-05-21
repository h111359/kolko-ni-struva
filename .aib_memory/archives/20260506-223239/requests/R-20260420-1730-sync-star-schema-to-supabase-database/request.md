## Goal

Create `src/load_supabase.py`, a new ETL module that establishes the star-schema tables in Supabase (CREATE TABLE IF NOT EXISTS), upserts all dimension data, and inserts the most recently available fact day that is not yet present in the remote database.  Connection details are read from `.env` in the project root.  Add a new numbered option to `menu.py` that lets the operator trigger the Supabase upload interactively.

## Background

The pipeline builds a local star-schema under `data/schema/` (seven dimension CSVs + date-partitioned fact CSVs covering 2026-02-15 onward).  Stakeholders now need the data accessible in a cloud-hosted PostgreSQL instance provided by Supabase, so that analysts can query it without direct access to the local machine.

A prior `src/migrate_supabase.py` module was removed in request R-20260418-2209 when the project was stripped down to download-only functionality.  The current request re-introduces cloud sync, aligned to the new star-schema structure and ETL conventions established in R-20260419-0854.

The `.env` file at the project root holds the Supabase connection string (key name was `DATABASE_URL` in the previous implementation).  `python-dotenv` is already listed in `requirements.txt` (currently dormant) and must be activated by the new module.

## Scope

- New module `src/load_supabase.py`:

  - Loads `.env` via `python-dotenv` and reads the connection string.

  - Creates all seven star-schema tables in Supabase if they do not already exist, using DDL that mirrors the local CSV schemas (`dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, `dim_file`, `fact_prices`).

  - Upserts current dimension data from the seven dim CSVs under `data/schema/` into the corresponding Supabase tables using INSERT … ON CONFLICT DO UPDATE.

  - Determines the most recent local fact date not yet uploaded to Supabase and inserts its rows into `fact_prices` (idempotent: if the latest local date already exists in Supabase, it logs "already up to date" and exits cleanly).

  - Reads connection string from `.env`; validates that it is present before attempting any DB operation.

  - Uses `psycopg2-binary` for the PostgreSQL connection (same approach as the previous implementation).

- `requirements.txt`: add `psycopg2-binary` pinned to a current stable release.

- `menu.py`: add option 5) "Update Supabase DB" that invokes `src/load_supabase.py` via `run_script()`.  Exit choice moves from 4 to 5 (or a separate new numbered slot is added and Exit remains 4 with upload as option 5 — see Q001).

- `.env.example`: create a template file (committed) documenting the required variable (`DATABASE_URL`) without real credentials.

## Out of scope

- Bulk historical backfill of all 63+ fact dates to Supabase.

- Supabase schema migrations or schema versioning (ALTER TABLE statements).

- Supabase Storage, Auth, Edge Functions, or REST API layer.

- Web dashboard or API exposure on top of Supabase.

- Automated scheduling or CI/CD pipeline integration.

- Modifying `src/extract.py` or `src/transform.py`.

- Modifying `refresh.sh` / `refresh.bat` to auto-upload.

## Constraints

- Python 3.9+ compatibility.

- Connection details MUST be read from `.env`; no credentials hardcoded or written to `config.ini`.

- `.env` file MUST NOT be committed to VCS (already absent from workspace; operator responsibility to add it to `.gitignore`).

- Module MUST be idempotent: re-running when the latest day is already in Supabase must produce no data change and exit cleanly.

- `psycopg2-binary` is the only new runtime dependency; no additional packages beyond what is in `requirements.txt`.

- Existing scripts (`extract.py`, `transform.py`, `menu.py`) must not be broken — backwards-compatible additions only.

- The module MUST NOT be called automatically by `refresh.sh` / `refresh.bat`; it is operator-triggered only.

- Error handling: DB connection failures and missing `.env` must surface as clear error messages, not stack traces.

## Success criteria

- `python src/load_supabase.py` connects to Supabase, creates tables if absent, upserts all dim rows, and inserts the latest local fact date rows.

- Re-running with no new local fact data prints "already up to date" and exits with code 0.

- Running from a blank Supabase project (no tables) creates all eight tables with correct column types and constraints, then populates them.

- Selecting the new menu option from `menu.py` executes `load_supabase.py` and surfaces any errors to the operator.

- No credentials appear in any committed files.

- `pip install -r requirements.txt` resolves without errors after adding `psycopg2-binary`.

## Assumptions

- A1: The `.env` file will be present at the project root before the first run of `load_supabase.py`; the operator creates it manually.
  - Risk if false: Module exits with a clear error ("DATABASE_URL not set"); no silent failure or crash.

- A2: `DATABASE_URL` in `.env` points to a Supabase PostgreSQL endpoint accessible from the operator's machine at the time of script execution (port 5432, direct connection).
  - Risk if false: Connection error surfaced; no data is written. Operators using the pooler port (6543) may experience mid-batch connection drops on large uploads.

- A3: The `psycopg2-binary==2.9.10` (or later 2.9.x) wheel is installable in the operator's Python 3.9+ environment without OS-level `libpq`.
  - Risk if false: Operator may need to install `libpq-dev` (Debian/Ubuntu) or use `psycopg[binary]` alternative; documented in README.

- A4: Local `data/schema/` dim CSVs and fact CSVs are fully up-to-date (transform has been run) before invoking `load_supabase.py`.
  - Risk if false: An outdated or missing latest fact date is silently skipped; operator should run transform first.

- A5: Supabase project has a PostgreSQL instance that supports standard SQL DDL and the `INSERT … ON CONFLICT DO UPDATE` construct (PostgreSQL 9.5+).  Supabase currently provisions PostgreSQL 15.x; this assumption holds.
  - Risk if false: DDL syntax or upsert construct incompatible — would require query adaptation.

- A6: The surrogate keys produced locally by `transform.py` are stable (not regenerated on each run) so they can serve as explicit primary keys in the remote database without collision.
  - Risk if false: Key instability would corrupt foreign key integrity in Supabase.  Mitigation: document that `data/schema/dim_*.csv` files must not be deleted between local transform runs and Supabase uploads.

- A7: Uploading one day's fact rows (~1.3 M rows) via `execute_batch` with page size 2000 completes within a reasonable operator-acceptable time window (< 10 minutes on typical broadband to Supabase EU region).
  - Risk if false: Operator may need to switch to `COPY FROM STDIN` for faster bulk load; this optimization path is documented in the module docstring.

- A8: The menu's current Exit option (4) will be renumbered to 5 and the new Supabase option will be added as option 5, shifting Exit to 5 — OR a new option 5 is appended and Exit stays at 4 (see Q001, resolved as: Exit stays at 4, new option appended as 5).
  - Risk if false: Menu numbering inconsistency confuses operators. Resolved by Q001 answer.

## Plan

### Task 1: Add psycopg2-binary and activate python-dotenv
**Intent:** Update `requirements.txt` to include `psycopg2-binary` so the new module can connect to PostgreSQL.
**Inputs:** `requirements.txt`
**Outputs:** `requirements.txt` (modified)
**External Interfaces:** PyPI (pip install)
**Environment & Configuration:** Python 3.9+; no secrets involved.
**Procedure:**
1. Append `psycopg2-binary==2.9.10` to `requirements.txt`.
2. Verify `python-dotenv` is already present (it is; no action needed).
**Done Criteria:** `pip install -r requirements.txt` completes without error; `import psycopg2` succeeds in Python 3.9+.
**Dependencies:** None
**Risk Notes:** None; pre-built wheel available for all target platforms.

### Task 2: Create .env.example
**Intent:** Provide a committed template documenting the required environment variable without exposing real credentials.
**Inputs:** None (new file)
**Outputs:** `.env.example` (created at project root)
**External Interfaces:** None
**Environment & Configuration:** N/A
**Procedure:**
1. Create `.env.example` with `DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres`.
2. Add a comment line explaining port 5432 requirement for direct connection.
**Done Criteria:** `.env.example` exists at project root; contains `DATABASE_URL` key with placeholder value and usage comment.
**Dependencies:** None
**Risk Notes:** None.

### Task 3: Create src/load_supabase.py
**Intent:** Implement the Supabase sync module: provision tables, upsert dims, insert latest fact day.
**Inputs:** `.env` (DATABASE_URL), `data/schema/dim_*.csv`, `data/schema/facts/*.csv`
**Outputs:** `src/load_supabase.py` (created); Supabase tables populated/updated.
**External Interfaces:** Supabase PostgreSQL (psycopg2 connection); local filesystem (dim CSVs, fact CSVs).
**Environment & Configuration:** `DATABASE_URL` from `.env`; no config.ini keys required.
**Procedure:**
1. Load `.env` with `dotenv.load_dotenv()`; read `DATABASE_URL` with `os.getenv`; fail with a clear message if absent.
2. Implement `create_tables(conn)`: execute CREATE TABLE IF NOT EXISTS DDL for all eight tables (`dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, `dim_file`, `fact_prices`) with correct column types and INTEGER (not SERIAL) primary keys.
3. Implement `upsert_dim(conn, table, csv_path, pk_col, columns)`: reads CSV, runs `INSERT … ON CONFLICT (pk_col) DO UPDATE SET …` via `execute_batch`, page size 2000, within a single transaction.
4. Implement `get_latest_remote_date(conn)`: queries `SELECT MAX(d.date) FROM fact_prices fp JOIN dim_date d ON fp.date_key = d.date_key`; returns None if table is empty.
5. Implement `get_latest_local_date(facts_dir)`: returns the stem of the newest `.csv` in `data/schema/facts/`.
6. Implement `insert_fact_day(conn, date_str, csv_path)`: reads the fact CSV, inserts all rows via `execute_batch` (page 2000) into `fact_prices`; wraps in a transaction with rollback on error.
7. Implement `main()`: call steps 2-6 in order; log progress and "already up to date" when remote date equals local date; exit cleanly.
**Done Criteria:** `python src/load_supabase.py` connects, creates tables if absent, upserts dims, inserts latest fact day, exits 0. Re-run when up-to-date prints message and exits 0.
**Dependencies:** Task 1 (psycopg2 available), Task 2 (.env.example for documentation)
**Risk Notes:** DATABASE_URL must never appear in log output (log only its presence/absence).

### Task 4: Update menu.py — add option 5 (Update Supabase DB)
**Intent:** Expose `load_supabase.py` as a numbered menu option so operators can trigger it interactively.
**Inputs:** `menu.py`
**Outputs:** `menu.py` (modified)
**External Interfaces:** None (calls `run_script("src/load_supabase.py")`)
**Environment & Configuration:** N/A
**Procedure:**
1. In `print_menu()`, add line: `print("    5) Update Supabase DB  (python src/load_supabase.py)")`.
2. In `main()`, add `elif choice == "5": action_supabase()` branch.
3. Add `action_supabase()` function that calls `run_script("src/load_supabase.py")`.
4. Update the input prompt from `[1-4]` to `[1-5]`.
5. Exit option stays at 4.
**Done Criteria:** Running menu.py shows 5 options; selecting 5 invokes load_supabase.py; Exit (4) still works; invalid choices still show error.
**Dependencies:** Task 3
**Risk Notes:** None.

### Task 5: Update README.md
**Intent:** Document the new Supabase sync capability, setup instructions, and `.env` requirements.
**Inputs:** `README.md`
**Outputs:** `README.md` (modified)
**External Interfaces:** None
**Environment & Configuration:** N/A
**Procedure:**
1. Add a "Supabase Sync" section describing: (a) setup (create `.env` from `.env.example`), (b) direct connection port requirement, (c) how to run (`python src/load_supabase.py` or menu option 5), (d) incremental nature (latest day only), (e) full backfill approach (run manually per date if needed).
**Done Criteria:** README.md contains Supabase section with setup, usage, and constraints clearly explained.
**Dependencies:** Tasks 1–4 completed.
**Risk Notes:** None.

## Testing

- T1 — table creation on empty DB: Run `python src/load_supabase.py` against a Supabase project with no tables. Expected outcome: All eight tables are created; `\dt` in psql shows all eight; script exits 0.

- T2 — dimension upsert idempotency: Run `python src/load_supabase.py` twice against a Supabase project that already has dim data. Expected outcome: Second run updates rows but does not create duplicates; row counts in Supabase dim tables match local CSV row counts.

- T3 — incremental fact insert (new day): Ensure latest local fact date is absent in Supabase, then run the module. Expected outcome: Fact rows for the latest date appear in `fact_prices`; row count matches the local fact CSV row count; script exits 0.

- T4 — already up-to-date detection: After T3, re-run `python src/load_supabase.py` with no new local fact date. Expected outcome: Script prints "already up to date", makes no DB writes, exits 0.

- T5 — missing `.env` guard: Remove `.env` (or unset DATABASE_URL) and run the module. Expected outcome: Script prints a clear error message containing "DATABASE_URL" and "not set" (or similar), exits with non-zero code, makes no DB connection attempt.

- T6 — menu option 5 invocation: Launch `menu.py`, select option 5. Expected outcome: `load_supabase.py` is invoked; its output (success or error) is displayed; returning to menu shows statistics; option 4 (Exit) still exits cleanly.

- T7 — menu backwards compatibility: Launch `menu.py` and verify options 1, 2, 3, and 4 (Exit) behave identically to pre-request behaviour. Expected outcome: All four original options work as before; only option 5 is new.

- T8 — credential non-disclosure: Run the module with valid credentials and inspect stdout/stderr output. Expected outcome: The DATABASE_URL value (containing password) does not appear in any log line.

- T9 — requirements install: Run `pip install -r requirements.txt` in a clean virtualenv. Expected outcome: All packages install without error; `import psycopg2` succeeds.

## Documentation

- `README.md` (ref_id: N/A) — Add Supabase sync section: setup, `.env` creation from `.env.example`, usage instructions, incremental-load note, direct connection (port 5432) note.

- `.aib_memory/context.md` (ref_id: REF-0001) — Must be regenerated after implementation to reflect new module `src/load_supabase.py`, updated `requirements.txt`, new `.env.example`, and updated `menu.py`.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `src/load_supabase.py` | Created | New Supabase sync module — core deliverable. |
| `requirements.txt` | Modified | Add `psycopg2-binary==2.9.10`. |
| `.env.example` | Created | Committed credential template for operator onboarding. |
| `menu.py` | Modified | Add option 5 (Update Supabase DB), new action function, updated input prompt range. |
| `README.md` | Modified | Add Supabase sync setup and usage documentation. |
| `.env` | Read-only dependency | Read by `load_supabase.py` via `python-dotenv`; not committed; must exist on operator machine. |
| `data/schema/dim_date.csv` | Read-only dependency | Source for `dim_date` upsert. |
| `data/schema/dim_company.csv` | Read-only dependency | Source for `dim_company` upsert. |
| `data/schema/dim_settlement.csv` | Read-only dependency | Source for `dim_settlement` upsert. |
| `data/schema/dim_category.csv` | Read-only dependency | Source for `dim_category` upsert. |
| `data/schema/dim_product.csv` | Read-only dependency | Source for `dim_product` upsert. |
| `data/schema/dim_store.csv` | Read-only dependency | Source for `dim_store` upsert. |
| `data/schema/dim_file.csv` | Read-only dependency | Source for `dim_file` upsert. |
| `data/schema/facts/<latest-date>.csv` | Read-only dependency | Source for incremental fact insert. |
| `src/extract.py` | Read-only dependency | Not modified; no impact. |
| `src/transform.py` | Read-only dependency | Not modified; no impact. |
| `src/config_utils.py` | Read-only dependency | Not modified; not imported by new module. |
| `refresh.sh` / `refresh.bat` | Read-only dependency | Not modified; Supabase upload is operator-triggered only. |
| `.aib_memory/context.md` | Modified (post-implement) | Must be regenerated to reflect new module and dependency. |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal, Background, Scope, Out of scope, Constraints, and Success criteria are all present, non-empty, and consistently scoped.

- OK: `context.md` (REF-0001) — Accurately notes `python-dotenv` is dormant (`not imported by any production script`). The new module activates it; context.md must be regenerated post-implementation.

- Ambiguity: `request.md § Scope` — The input text says "creation if not exists or update with the latest stage" which could mean: (a) upsert all dims + insert only the latest fact day, or (b) something more complex. Interpreted as (a), consistent with the upsert pattern and the explicit out-of-scope exclusion of bulk historical backfill. This interpretation is codified in Scope and Constraints.

- Missing info: `.env` file does not exist in the workspace (confirmed by file search); operator must create it. Documented in Assumptions (A1) and Tasks (Task 2) and Testing (T5).

- Cross-ref issue: `context.md` states "Scope boundaries: no cloud sync, no database upload" — this will be outdated after implementation. Confirmed for post-implementation context regeneration in Documentation section.

- OK: `requirements.txt` — `python-dotenv` present but inactive. `psycopg2-binary` absent. Consistent with plan to add it in Task 1.

- OK: `menu.py` — Current menu has options 1–4 (Exit=4). New option 5 can be appended cleanly. `run_script()` helper is reusable without modification.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The proposed design is architecturally sound. Using `psycopg2-binary` with direct PostgreSQL connection to Supabase is the right choice for a bulk-insert script — it avoids unnecessary SDK abstraction and aligns with the stdlib-preference already established in the codebase. The incremental approach (latest local date not yet in remote DB) is the correct scoping for day-to-day use; historical backfill is correctly deferred.

Key architectural risks:
- Surrogate keys must remain stable between local and remote; any deletion of local dim CSVs would desynchronise surrogates. Documented in Assumptions (A6); requires operator education.
- The upload script does not update `config.ini` state (no `last_uploaded_date` checkpoint). If the operator needs to replay an upload (e.g., after a partial failure), there is no automated re-trigger mechanism. A future iteration could add an `[state]` key for this. Acceptable for v1 given idempotency of all operations.
- `execute_batch` is adequate for the current volume (~1.3 M rows/day) but may become slow as fact accumulation grows. `COPY FROM STDIN` migration path is documented.

### Product Owner

The request directly addresses the stated business need: making the locally-built star-schema accessible in Supabase for cloud-based analysis. The scope is appropriately narrow (latest day only, operator-triggered), which keeps the implementation risk low while delivering immediate value.

Key business concerns:
- Operators unfamiliar with Supabase setup will benefit from clear `.env.example` and README documentation (covered in Tasks 2 and 5).
- The "already up to date" exit path is important UX — operators who run the menu option without triggering a transform first should receive a clear, non-alarming message.
- Out-of-scope historical backfill may become a near-term follow-up request. Success criteria for this request do not require it, which is appropriate.

### User

As an operator running the interactive menu, the new option 5 provides a one-keystroke path to Supabase upload, consistent with the existing menu pattern. No new CLI syntax to learn.

Key user experience concerns:
- Upload for a single fact day (~1.3 M rows) may take several minutes; the menu will appear blocked during this time. Since `run_script()` uses `subprocess.run(check=True, capture_output=True)`, output is displayed only on completion — the operator sees no progress indicator. A streaming output option would improve perceived responsiveness but is out of scope for v1.
- If `.env` is missing and the operator selects option 5, the error message must clearly explain what is missing and how to fix it (not a raw stack trace).

### Security Officer

Credential handling is the primary security concern for this request.

Key security findings:
- `DATABASE_URL` must never be logged or printed — even partially. The module must log only `"DATABASE_URL set"` or `"DATABASE_URL not set"`. This is codified in Assumptions (A7) and Testing (T8).
- `.env` must not be committed to VCS. The `.env.example` pattern (committed template without credentials) addresses this. Operators must also have `.env` in `.gitignore`; this should be verified and documented.
- `psycopg2` with `DATABASE_URL` uses TLS by default for Supabase connections (Supabase enforces TLS). No additional SSL configuration required in the application code; verify with Supabase project settings.
- No SQL injection risk: DDL uses parameterised queries via `execute_batch` with positional placeholders (`%s`), not string formatting.
- Connection timeout: long-running uploads may leave a dangling connection if the script is killed. Using a `with conn:` context manager ensures rollback on exception.

### Data Governance Officer

This request introduces a cloud data store as a secondary replica of the local star-schema. Data governance implications:

Key data governance findings:
- The Supabase database contains PII-adjacent data (retail company names, Bulgarian settlement names, product names, prices). While none is directly personal, the combination could indirectly identify purchasing patterns at the store level. The Supabase project access controls (Row Level Security, API keys) must be configured by the operator; that is out of scope for this request but must be noted in documentation.
- Data lineage: Supabase tables are derived from `data/schema/` which is derived from `data/raw/` which is sourced from kolkostruva.bg/opendata (Bulgarian government). The lineage chain is clear and traceable.
- Retention: no retention policy is defined for Supabase data in this request. Operators should be guided to apply Supabase project retention policies consistent with the government open-data license (data is public; no personal data retention concern).
- Replication lag: Supabase may be one day behind local schema (operator must run upload after transform). This lag is acceptable for the analytical use case but must be communicated to analysts.

