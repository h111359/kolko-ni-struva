## Executive Summary

- **Request ID:** R-20260420-1730

- **Request title:** Sync star-schema to Supabase database

- **Purpose:** Introduce a new module (`src/load_supabase.py`) that provisions a mirror of the local star-schema in a Supabase-hosted PostgreSQL database, upserts all dimension data, and uploads the latest fact day that is not yet present remotely.  A new interactive menu option exposes the upload to the operator without requiring command-line knowledge.

- **Context:** The pipeline currently produces a fully populated local star-schema under `data/schema/` (7 dim CSVs + 63 date-partitioned fact CSVs, ~82 M rows total as of 2026-04-18).  A prior Supabase sync module (`src/migrate_supabase.py`) was removed in R-20260418-2209 when the project was simplified.  This request re-establishes cloud sync capability, aligned to the current schema and ETL conventions from R-20260419-0854.

- **Key design choice:** One-day incremental upload (latest local date not yet in Supabase) to keep per-run transfer small; full historical backfill is explicitly out of scope.

- **Dependency impact:** `psycopg2-binary` must be re-added to `requirements.txt`.  `python-dotenv` (dormant in current `requirements.txt`) must be activated via import in the new module.

- **`request.md` sections updated this run:** `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`, `## Multi-Perspective Stakeholder Review`.  No questions were raised to the user.

---

## Domain Knowledge Essentials

- **Kolko Ni Struva ("How Much Does It Cost Us"):** Bulgarian government transparency initiative requiring large retailers to publish daily retail prices on the portal `kolkostruva.bg/opendata`.  The pipeline downloads and consolidates those prices.

- **Star-schema:** Data modelling pattern with one central fact table (numeric measurements) linked to surrounding dimension tables (descriptive attributes).  Designed for fast analytical reads.

- **Dimension table:** Stores descriptive attributes (company name, product name, settlement name, etc.) with a stable surrogate integer key.  This pipeline has seven: `dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, `dim_file`.

- **Fact table:** Stores measurements — here, retail and promotional prices for one product–store–date combination.  Current schema: `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price`.

- **Upsert (INSERT … ON CONFLICT DO UPDATE):** Idempotent row insertion: inserts a row if the primary key is absent; updates the non-key columns if the key already exists.  Required here to make dimension syncs re-runnable without creating duplicates.

- **EKATTE:** Bulgarian administrative settlement registry (code system).  Used as the natural key in `dim_settlement`.

- **UIC (ЕИК — Единен идентификационен код):** Bulgarian national business identification number.  Natural key in `dim_company`.

- **Operator:** The primary user persona — a data engineer who runs the pipeline locally.  Goals: daily data freshness in Supabase with minimal friction.

- **Analyst:** Secondary persona — consumes Supabase tables for SQL-based retail price analysis.  Not directly impacted by this implementation but is the ultimate beneficiary.

- **Impacted process:** Post-transform upload step added to the operator workflow.  Does not modify the ingestion or transformation processes.

---

## Technical Knowledge & Terms

- **Supabase:** Open-source Firebase alternative backed by PostgreSQL.  Exposes a standard PostgreSQL wire protocol, meaning any PostgreSQL driver (`psycopg2`, `asyncpg`) connects without Supabase-specific SDK.  Also offers a Python `supabase` client SDK but it adds unnecessary abstraction for a bulk-upload use case.

- **psycopg2-binary:** Pre-compiled CPython extension providing the PostgreSQL wire-protocol client.  The `-binary` variant bundles `libpq` (no system library required).  Was present in the old `requirements.txt` (before R-20260418-2209 removed it).  Chosen over `asyncpg` because the upload is synchronous and batch; async adds complexity with no throughput benefit here.

- **DATABASE_URL:** PostgreSQL DSN (Data Source Name) format: `postgresql://user:password@host:port/dbname`.  Supabase project connection strings follow this format.  Prior implementation stored this key in `.env`.

- **python-dotenv:** Reads `key=value` pairs from a `.env` file and injects them into `os.environ`.  Already in `requirements.txt`; not imported by any current production script.  The new module activates it.

- **CREATE TABLE IF NOT EXISTS:** Standard SQL DDL that no-ops when the table already exists.  Safe to run on every module invocation.

- **INSERT … ON CONFLICT (pk) DO UPDATE SET …:** PostgreSQL-specific upsert syntax that handles concurrent inserts safely.  Requires a UNIQUE or PRIMARY KEY constraint on the conflict target.  Natural keys (e.g., `uic` for companies) and surrogate keys (e.g., `date_key`) are both valid conflict targets depending on whether surrogate keys are stable across environments.

- **Surrogate key stability risk:** The local dim tables maintain stable integer surrogates (`company_key = 1` always maps to the same UIC as long as the dim CSV is not deleted).  If Supabase is provisioned from scratch, the same surrogate must be reproduced.  Uploading the full dim tables (not just natural keys) ensures surrogate consistency between local and remote.

- **Incremental fact upload strategy:** Upload only the latest local fact date not yet present in Supabase.  Detection method: query `MAX(d.date)` from the remote `fact_prices` joined to `dim_date`, compare to `MAX(stem)` from local `data/schema/facts/*.csv`.  If equal, skip upload.

- **Batch insert performance:** Each fact file contains ~1.3 M rows (82 M / 63 dates).  Inserting row-by-row would be unacceptably slow.  Using `psycopg2`'s `execute_batch` (or `copy_from` for maximum throughput) is required.  `execute_batch` with a page size of 1000–5000 rows is the recommended pattern for balanced throughput and memory usage.

- **Connection pooling:** PgBouncer is active by default on Supabase's transaction-mode pooler (port 6543).  For bulk insert (single script run), using the direct connection (port 5432) avoids pooler session-mode restrictions.  The `DATABASE_URL` in `.env` should point to port 5432 for direct connections.  This is a known Supabase operational detail; the module must document it.

- **Files read during this analysis:**
  - `.aib_memory/context.md` (REF-0001) — full product context
  - `src/extract.py` — download module, reference for coding conventions
  - `menu.py` — interactive menu, target for new option
  - `config.ini` — settings/state structure
  - `requirements.txt` — current package list
  - `data/schema/dim_*.csv` (headers) — column schemas for DDL generation
  - `data/schema/facts/2026-04-18.csv` (header + 3 rows) — fact table schema
  - `.aib_memory/requests/R-20260418-2209-keep-raw-download-and-nomenclatures/analysis.md` — prior Supabase removal context
  - `.aib_brain/Concepts.md` (REF-0002) — AIB framework reference

---

## Research Results

### Pattern scan

- **Atomic write pattern (already established):** Both `extract.py` and `transform.py` use `.partial` temp-file + atomic rename for all file writes.  The new module does not write local files; its atomic unit is a database transaction.  Standard `psycopg2` `conn.commit()` / `conn.rollback()` provides transaction atomicity.

- **Coding conventions in this codebase:**
  - `BASE_DIR = Path(__file__).resolve().parent.parent` for project-root resolution.
  - `subprocess.run([sys.executable, …], check=True, capture_output=True)` for subprocess calls in `menu.py`.
  - `config_utils.load_config()` and `config_utils.save_state()` for config I/O (not applicable to the DB module; the new module has no `config.ini` interaction).
  - Logging via `logging.basicConfig` with `stream=sys.stdout` and a consistent timestamp format.

- **Previous Supabase module (`src/migrate_supabase.py`):** Removed in R-20260418-2209.  Per the analysis of that request: it was a standalone module with no shared code with `extract.py`.  The current request is consistent with this pattern — `load_supabase.py` will also be a standalone module.  Connection used `DATABASE_URL` from `.env`.

- **`python-dotenv` usage pattern:** `load_dotenv()` at module top before `os.getenv()` calls.  Already in `requirements.txt`; safe to activate.

- **Supabase connection string format:** Supabase projects expose a "Connection string" in the project settings (Settings → Database → Connection string).  It follows the `postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres` format.  The port may be 5432 (direct) or 6543 (pooler).  Direct is preferred for bulk upload.

---

## External Benchmarking

- **Supabase Bulk Data Loading (Supabase official documentation and engineering blog):**  The Supabase engineering blog documents two recommended approaches for bulk loading into PostgreSQL: (1) chunked `execute_batch` via `psycopg2` for structured Python pipelines, and (2) `COPY FROM STDIN` via `psycopg2.copy_expert` for maximum throughput.  For a single ~1.3 M-row daily fact file, `execute_batch` with chunk sizes of 2000–5000 rows achieves acceptable throughput (typically 50 k–200 k rows/sec depending on network latency to Supabase).  `COPY FROM STDIN` is up to 10× faster but requires constructing a CSV-formatted byte stream in Python.

  - Takeaway: Use `execute_batch` for the initial implementation (simpler, lower risk); document `COPY FROM STDIN` as an optimization path if upload latency becomes a user complaint.

  - Applicability: Directly applicable.  Adopt `execute_batch` with page size 2000.

- **Kimball data warehouse incremental load pattern (Kimball Group, "The Data Warehouse Toolkit"):**  The standard pattern for incremental fact table loads: (1) identify the high-water mark (last loaded date in the target), (2) load only rows with a source date > the high-water mark, (3) update the high-water mark on success.  Dimension tables are handled via SCD Type 1 (overwrite) or Type 2 (versioned rows); for this pipeline, SCD Type 1 via upsert is appropriate because dimension corrections (e.g., company name change) should propagate to the remote database.

  - Takeaway: High-water mark detection via `SELECT MAX(d.date) FROM fact_prices fp JOIN dim_date d ON fp.date_key = d.date_key` is the standard approach.  Adopt this for the latest-date detection in `load_supabase.py`.

  - Applicability: Directly adopted.

- **12-Factor App: Config (factor III — store config in the environment):**  Credentials and environment-specific connection strings must be stored in the environment (via `.env` files or OS env vars), not in code or VCS.  `python-dotenv` is the idiomatic Python implementation of this factor.

  - Takeaway: `.env` with `DATABASE_URL` is the correct approach; `.env.example` (committed, no credentials) is the standard companion file for onboarding documentation.

  - Applicability: Directly adopted.  `.env.example` must be created.

- **OWASP ASVS 6.4 (Secret Management):**  Application secrets (database passwords, API keys) must not be embedded in source code, configuration files committed to VCS, or log output.  The `.env` pattern, combined with a `.gitignore` entry, satisfies this requirement.

  - Takeaway: Confirm that `DATABASE_URL` value is never logged (only the presence/absence of the key).  Reject the connection string value from any `logging` call.

  - Applicability: Directly adopted as a code constraint.

---

## Minimal Spikes and Experiments

- **Spike: psycopg2-binary availability for Python 3.9+ on Linux**
  - Hypothesis: `psycopg2-binary` 2.9.x is installable via pip into the current Python 3.9+ environment without OS-level `libpq` dependency.
  - Approach: Checked PyPI release history and Supabase documentation; confirmed `-binary` wheel availability for Python 3.9–3.13 on Linux x86_64 and ARM64 as of 2026.
  - Outcome: `psycopg2-binary==2.9.10` (latest stable as of Q1 2026) is available as a pre-built wheel.
  - Conclusion: No compilation needed; safe to pin in `requirements.txt`.

- **Spike: Supabase direct connection vs. pooler for bulk insert**
  - Hypothesis: Port 5432 (direct connection) is required for reliable `execute_batch` with large row counts; port 6543 (PgBouncer transaction pooler) may close the connection mid-batch.
  - Approach: Reviewed Supabase documentation on connection modes; transaction-mode pooler does not support prepared statements but does support standard `execute_batch` (which uses simple query protocol); however, connection lifetime constraints on the pooler can interrupt long-running bulk inserts.
  - Outcome: Supabase docs recommend port 5432 for persistent, long-running operations and scripts; port 6543 for short-lived API calls.
  - Conclusion: Document in `.env.example` and module docstring that `DATABASE_URL` should use port 5432 for the bulk-insert module.

- **Spike: Surrogate key collision risk between local and remote**
  - Hypothesis: Because the module uploads the full dim CSVs including surrogate keys, and the surrogate key is always the local sequence, inserts to a fresh Supabase DB will reproduce faithfully with no collision.  On re-run, ON CONFLICT DO UPDATE keeps them consistent.
  - Approach: Reviewed local dim CSV structure (headers: `company_key, uic, company_name`, etc.); surrogates are integer primary keys generated locally by `transform.py` with no SERIAL or SEQUENCE in the DB.  Upload inserts explicit (not auto-generated) surrogate values.
  - Outcome: No collision risk when uploading explicit surrogates with ON CONFLICT DO UPDATE.
  - Conclusion: DDL must define surrogate columns as plain INTEGER PRIMARY KEY (not SERIAL), to allow explicit inserts rather than auto-increment.
