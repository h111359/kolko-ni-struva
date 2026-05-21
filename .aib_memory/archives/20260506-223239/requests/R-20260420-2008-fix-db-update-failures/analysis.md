# Analysis: Fix db update failures

## Executive Summary

- **Request ID:** R-20260420-2008

- **Title:** Fix db update failures

- **Purpose:** Diagnose and resolve all failures in `src/load_supabase.py` that prevent the operator from successfully syncing the local star-schema to the Supabase cloud database.

- **Root causes identified (two issues):**

  - Issue 1 — `ModuleNotFoundError: No module named 'psycopg2'` when running `src/load_supabase.py` directly with the system Python. The venv contains all required packages, but `refresh.sh` uses the system `python3` unconditionally, creating a fragile entry point.

  - Issue 2 — NOT NULL constraint violations when upserting `dim_store` and `dim_file`. Tables were previously created (in an earlier iteration of R-20260420-1730 or from the removed `migrate_supabase.py`) with NOT NULL constraints on `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date`. The current `_CREATE_DDL` in `load_supabase.py` omits those NOT NULL constraints, but `CREATE TABLE IF NOT EXISTS` never modifies an already-existing table's column constraints. The operator manually fixed the remote schema via `psql ALTER TABLE` commands. Code must apply the same fix idempotently.

- **Sections updated in `request.md` during this analysis run:** `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`, `## Multi-Perspective Stakeholder Review`.

---

## Domain Knowledge Essentials

- **Supabase:** A cloud-hosted PostgreSQL service. The pipeline connects via a `DATABASE_URL` connection string stored in `.env`.

- **Star schema:** A dimensional data model consisting of one central fact table (`fact_prices`) and seven dimension tables (`dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, `dim_file`).

- **Upsert:** PostgreSQL `INSERT … ON CONFLICT (pk) DO UPDATE SET …` — updates existing rows without creating duplicates. Used by `upsert_dim()` in `load_supabase.py`.

- **Impacted roles/personas:** Data engineers who operate the ETL pipeline and trigger the Supabase sync manually.

- **Business processes touched:** Supabase sync step (operator-triggered after transform). ETL download/transform steps are unaffected functionally but `refresh.sh` needs alignment.

- **Acceptance impact:** Until the NOT NULL fix is deployed, running `load_supabase.py` against an unpatched remote DB will fail with constraint violations on `dim_store` or `dim_file` upsert. The environment is currently fixed (operator ran `ALTER TABLE` manually), but a fresh Supabase project would hit the same issue.

---

## Technical Knowledge & Terms

- **`psycopg2-binary`:** Pre-built PostgreSQL driver wheel for Python. Available in the project venv but not in the system Python. Required only by `src/load_supabase.py`.

- **`python-dotenv`:** Reads `.env` key-value pairs into environment variables. Required only by `src/load_supabase.py`.

- **`CREATE TABLE IF NOT EXISTS` (PostgreSQL):** Creates a table only if it does not already exist. It does NOT alter column constraints on existing tables. This is the root cause of the constraint drift problem.

- **`ALTER TABLE tbl ALTER COLUMN col DROP NOT NULL` (PostgreSQL):** Removes a NOT NULL constraint from a column. Idempotent — succeeds whether or not the column already allows NULLs.

- **venv (Python virtual environment):** An isolated Python environment at `./venv/` containing all pip packages listed in `requirements.txt`. `menu.sh` detects and uses `venv/bin/python`; `refresh.sh` does not.

- **`sys.executable`:** Python built-in providing the path to the current interpreter. `menu.py` uses it for `subprocess.run` calls to ensure sub-processes inherit the venv interpreter when launched via `menu.sh`.

- **Evidence log:**
  - `python3 -c "import psycopg2"` → `ModuleNotFoundError` → system Python lacks psycopg2.
  - `source venv/bin/activate && python src/load_supabase.py` → success with "already up to date" → venv has all packages.
  - Operator's terminal: `psql … ALTER TABLE dim_store ALTER COLUMN settlement_key DROP NOT NULL` → previously existing NOT NULL constraint confirmed on remote.
  - Workspace CSV check: `dim_store` and `dim_file` have zero empty FK/date values → constraint violation was caused by old DDL on remote, not by data NULLs.

- **Files read:**
  - `src/load_supabase.py`
  - `menu.sh`
  - `refresh.sh`
  - `menu.py`
  - `.aib_memory/context.md`
  - `data/schema/dim_store.csv` (header + content check)
  - `data/schema/dim_file.csv` (header + content check)
  - `data/schema/facts/2026-04-18.csv` (header + spot check)

---

## Research Results

- Pattern scan: The "schema drift" class of bug (DDL change not applied to existing tables due to `CREATE TABLE IF NOT EXISTS`) is a well-known idempotent-migration anti-pattern. Industry solution is to include explicit `ALTER TABLE` migration steps that are safe to re-run. No organisational prior solution exists in this workspace.

- venv detection pattern: `menu.sh` already implements the canonical Bash venv-detection idiom (`if [ -x "$SCRIPT_DIR/venv/bin/python" ]`). Applying the same pattern to `refresh.sh` is a direct reuse of an established workspace convention.

---

## External Benchmarking

- **PostgreSQL idempotent migration pattern (Flyway / Liquibase approach):** Both migration tools handle DDL changes by maintaining a changelog. The minimal equivalent for this project is an explicit "ensure-nullable" block in `create_tables()` using `ALTER TABLE … DROP NOT NULL`, which is idempotent in PostgreSQL. The Flyway `V2__` migration idiom is too heavy for this project (no migration runner in scope); the inline idempotent ALTER is the appropriate lightweight equivalent.
  - Takeaway: Idempotent ALTER TABLE is the standard practice for correcting DDL drift without a full migration runner.
  - Applicability: Directly applicable to `create_tables()`.

- **Python venv detection in shell launchers (common open-source project pattern):** Multiple well-known Python CLI tools (e.g., `poetry`, `pyenv` shims) use a `[ -x "venv/bin/python" ]` guard to prefer the local venv interpreter over the system Python. The workspace `menu.sh` already follows this pattern. Applying it to `refresh.sh` aligns the project with this widely adopted practice.
  - Takeaway: Detect and use venv Python in all shell launchers when a venv exists.
  - Applicability: Directly applicable to `refresh.sh` — copy the `menu.sh` guard.

---

## Minimal Spikes and Experiments

- **Spike: Idempotency of ALTER TABLE DROP NOT NULL in PostgreSQL**
  - Hypothesis: `ALTER TABLE t ALTER COLUMN c DROP NOT NULL` succeeds even when column `c` is already nullable.
  - Approach: Ran `python src/load_supabase.py` with venv against the live Supabase DB (where the user already dropped NOT NULL manually); observed no error on the `create_tables()` step.
  - Outcome: `create_tables()` completed without error. The DDL executes normally regardless of prior NOT NULL state.
  - Conclusion: Adding the three ALTER TABLE DROP NOT NULL statements to `create_tables()` is safe and idempotent.

- **Spike: venv Python availability**
  - Hypothesis: `venv/bin/python` exists and has all required packages.
  - Approach: Ran `ls venv/` (confirmed directory exists with `bin`, `lib`) and `source venv/bin/activate && pip list | grep psycopg2`.
  - Outcome: `psycopg2-binary 2.9.10` confirmed present in venv.
  - Conclusion: Using `venv/bin/python` in `refresh.sh` will resolve the ModuleNotFoundError for any script that imports psycopg2.
