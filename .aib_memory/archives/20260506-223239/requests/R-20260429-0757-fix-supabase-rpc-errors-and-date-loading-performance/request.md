## Goal

Fix the runtime errors appearing in the browser console when the React Analytics App loads:
1. A 404 error on an unidentified resource.
2. HTTP 500 (`canceling statement due to statement timeout`) errors on both `get_available_dates` and `get_settlements_for_date` Supabase RPC calls.

As a consequence of the RPC timeouts, the date selector falls back to showing all `dim_date` rows rather than only dates with real `fact_prices` data. The fix must restore correct date filtering (only dates with fact data are shown) and eliminate the timeout by providing the database with the query structures it needs to execute these RPCs within Supabase's statement timeout budget.

## Background

The React Analytics App (`react-app/`) queries the Supabase-hosted PostgreSQL database. On app startup, `fetchDimensions()` in `react-app/src/lib/dataService.js` fires six parallel requests, including `get_available_dates()` and `get_settlements_for_date(p_date_key)` RPC calls.

The `fact_prices` table currently holds approximately 82 million rows across 63+ date partitions (originally stored as date-partitioned CSVs but loaded into a single Supabase table). Neither the `date_key` nor `store_key` columns are indexed in the Supabase table. The RPC functions perform:

- `get_available_dates()`: `SELECT DISTINCT date_key FROM fact_prices ORDER BY date_key DESC` — a full 82M-row scan
- `get_settlements_for_date(p_date_key)`: `SELECT DISTINCT s.settlement_key FROM fact_prices fp JOIN dim_store s ON s.store_key = fp.store_key WHERE fp.date_key = p_date_key` — a full 82M-row scan followed by a JOIN

Supabase's default statement timeout (free tier: ~3 s) is exceeded by these unbounded scans, returning HTTP 500. The app falls back to all `dim_date` rows, showing dates without fact data in the date selector.

The RPC functions were provisioned in R-20260422-0902. No indexes were ever added to `fact_prices`. This request addresses that omission.

## Scope

- Add `CREATE INDEX IF NOT EXISTS` statements for `fact_prices(date_key)` and `fact_prices(date_key, store_key)` to `src/load_supabase.py`'s DDL.

- Execute `src/load_supabase.py` (via menu option 4) so the indexes are created in the live Supabase database.

- Investigate and resolve the 404 error reported in the browser console.

- Verify that after the fix:
  - `get_available_dates()` and `get_settlements_for_date()` no longer return 500.
  - The date selector shows only real fact-present dates.
  - The app loads without 404 or 500 errors.

## Out of scope

- Modifying the RPC function logic (the SQL in `get_available_dates` and `get_settlements_for_date` is correct; indexes alone should eliminate the timeouts).
- Partitioning or restructuring the `fact_prices` table in Supabase.
- Client-side workarounds (memoization, local caching) for the RPC timeout — the root cause must be fixed server-side.
- Any ETL pipeline changes beyond the index DDL addition in `load_supabase.py`.
- Changes to the React app component structure (only `dataService.js` or other lib files may be touched if a code fix is also needed for the 404).

## Constraints

- `fact_prices` contains ~82 million rows; index creation is a blocking DDL operation in PostgreSQL and may take several minutes on the free-tier Supabase instance. The operator must expect a one-time delay when running option 4.
- The Supabase free tier limits statement timeout; all RPC queries must complete within it after indexing.
- `CREATE INDEX IF NOT EXISTS` is idempotent — safe to run on every future `load_supabase.py` invocation.
- No new Python third-party libraries may be introduced.
- All ETL scripts remain Python 3.9+-compatible.
- The fix for `fact_prices` indexes must be backward-compatible with the existing table DDL (no column or constraint changes).

## Success criteria

- SC-1: Browser console shows no 500 errors from `get_available_dates` or `get_settlements_for_date` after the operator runs option 4 (Update Supabase DB).
- SC-2: The date selector in the React app shows only dates for which `fact_prices` rows exist in Supabase (not all `dim_date` rows).
- SC-3: Browser console shows no 404 errors on app load.
- SC-4: `src/load_supabase.py` contains idempotent `CREATE INDEX IF NOT EXISTS` DDL for both `fact_prices(date_key)` and `fact_prices(date_key, store_key)`.
- SC-5: Running `load_supabase.py` a second time (re-run idempotency) completes without error.
- SC-6: All existing automated tests pass after the change.

## Assumptions

- A-1: The `fact_prices` table exists in the live Supabase database with the schema provisioned by `load_supabase.py`. The operator must have run option 4 at least once previously.
  - Risk if false: The DDL changes (index creation) cannot be applied until the table exists.

- A-2: The Supabase free-tier statement timeout is approximately 3 seconds. The current unindexed RPC queries exceed this limit due to the 82M-row full table scan on shared compute.
  - Risk if false: If the timeout is higher (e.g., on a paid tier), the issue may be intermittent rather than consistent; the index fix still improves performance but the urgency profile changes.

- A-3: A single-column B-tree index on `fact_prices(date_key)` and a composite index on `fact_prices(date_key, store_key)` are sufficient to bring both RPC functions within the statement timeout on Supabase free tier.
  - Risk if false: If shared-compute contention is severe, indexed scans may still occasionally time out; a pre-computed summary table for available dates would then be required as a follow-up.

- A-4: The unidentified 404 in the browser console is from a favicon.ico request. Placing a minimal `favicon.ico` in `react-app/public/` (which Vite copies to `dist/`) will eliminate it.
  - Risk if false: If the 404 originates from a missing Supabase endpoint or misconfigured Netlify redirect, a different fix is required; the implementation task should verify the exact 404 URL in DevTools before applying the favicon fix.

- A-5: `CREATE INDEX IF NOT EXISTS` DDL placed in `create_tables()` (or a dedicated `create_indexes()` call in `load_supabase.py`) will be executed on every run of option 4 without disrupting existing tables or data.
  - Risk if false: If Supabase's PostgREST connection enforces DDL restrictions for the role used by `DATABASE_URL`, index creation may fail; this is unlikely since `DATABASE_URL` uses the service/admin role.

## Plan

### Task 1: Add index DDL to `src/load_supabase.py`
**Intent:** Add idempotent `CREATE INDEX IF NOT EXISTS` statements for `fact_prices(date_key)` and `fact_prices(date_key, store_key)` to the DDL executed by `load_supabase.py`.
**Inputs:** `src/load_supabase.py` (current `_CREATE_RPC_FUNCTIONS` or a new `_CREATE_INDEXES` constant); `_CREATE_DDL` block for reference.
**Outputs:** `src/load_supabase.py` updated with two `CREATE INDEX IF NOT EXISTS` statements and a call to execute them in `create_tables()`.
**External Interfaces:** Supabase PostgreSQL (DDL executed via psycopg2 `DATABASE_URL` connection).
**Environment & Configuration:** `DATABASE_URL` in `.env` (project root); Supabase project ID `ekootljybgoenduwprbw`.
**Procedure:**
1. Add a new DDL constant `_CREATE_INDEXES` containing both `CREATE INDEX IF NOT EXISTS` statements.
2. Execute `_CREATE_INDEXES` as a fourth `cur.execute()` call inside `create_tables()`, within the same `with conn.cursor() as cur` block, before `conn.commit()`.
3. Add a print confirmation `"Indexes created / verified."` after `conn.commit()`.
**Done Criteria:** `src/load_supabase.py` contains both index DDL statements; `create_tables()` executes them; file parses without error (`python -c "import src.load_supabase"`).
**Dependencies:** None.
**Risk Notes:** `CREATE INDEX` on 82M rows is a long-running DDL; it will block only other DDL (not reads/writes). May take 5–15 minutes on Supabase free tier. Operator must be informed.

### Task 2: Add favicon to `react-app/public/`
**Intent:** Eliminate the 404 error by providing a physical favicon file that Vite copies to `dist/` and serves at `/favicon.ico`.
**Inputs:** `react-app/public/` directory; `react-app/index.html`.
**Outputs:** `react-app/public/favicon.ico` (minimal 1×1 or 16×16 icon file); optionally update `<link rel="icon">` in `index.html` to reference it explicitly.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Create a minimal `favicon.ico` in `react-app/public/` (can be a 1-pixel transparent icon or a simple 16×16 branded icon).
2. Verify Vite includes it in `dist/` by running `npm run build` and checking `dist/favicon.ico` exists.
**Done Criteria:** `react-app/public/favicon.ico` exists; `npm run build` completes and `dist/favicon.ico` is present; browser console shows no 404 on app load.
**Dependencies:** None.
**Risk Notes:** If the 404 URL identified in DevTools is not `/favicon.ico`, this task's approach must be adjusted during implementation.

### Task 3: Run `load_supabase.py` to apply indexes
**Intent:** Execute option 4 (Update Supabase DB) to apply the new index DDL to the live Supabase `fact_prices` table.
**Inputs:** Updated `src/load_supabase.py`; `.env` with valid `DATABASE_URL`.
**Outputs:** Two new indexes on `fact_prices` in Supabase; console output confirming `"Indexes created / verified."`.
**External Interfaces:** Supabase PostgreSQL (live production database).
**Environment & Configuration:** `DATABASE_URL` in `.env`.
**Procedure:**
1. Run `python menu.py` and select option 4, or run `python src/load_supabase.py` directly.
2. Wait for completion (may take several minutes for index build).
3. Confirm no errors in output.
**Done Criteria:** Script exits 0; output includes `"Indexes created / verified."`; indexes present in Supabase (verify via SQL editor or `pg_indexes`).
**Dependencies:** Task 1.
**Risk Notes:** One-time long-running DDL; operator must not interrupt the process.

### Task 4: Verify fix in browser
**Intent:** Confirm the React app loads without 404/500 errors and the date selector shows correct dates.
**Inputs:** Deployed React app on Netlify (or local preview); browser DevTools.
**Outputs:** Confirmation that no 404/500 errors appear in Console; date selector shows only fact-present dates.
**External Interfaces:** Supabase REST API (RPC calls from browser); Netlify CDN.
**Environment & Configuration:** Production Netlify URL; or local preview (`npm run preview` via menu option 6).
**Procedure:**
1. Open the app in a browser with DevTools > Console tab open.
2. Reload the page and observe Console and Network tabs.
3. Confirm no 500 or 404 errors.
4. Cross-check date selector values against `SELECT DISTINCT date FROM dim_date JOIN fact_prices USING(date_key)` in Supabase SQL editor.
**Done Criteria:** No HTTP 4xx/5xx errors on load; date selector values match fact-present dates.
**Dependencies:** Task 3 (indexes applied); Task 2 (favicon added and deployed).
**Risk Notes:** If deployed on Netlify, a fresh deploy may be needed after favicon fix (Task 2).

### Task 5: Automated tests and idempotency check
**Intent:** Run the existing test suite and re-run `load_supabase.py` to confirm the changes are backward-compatible and idempotent.
**Inputs:** `tests/` directory; updated `src/load_supabase.py`.
**Outputs:** All tests passing; `load_supabase.py` second run exits 0.
**External Interfaces:** None (tests are unit tests with mocked Supabase).
**Environment & Configuration:** Python 3.9+ venv; `requirements.txt` dependencies installed.
**Procedure:**
1. Run `pytest` from project root; confirm all tests pass.
2. Run `load_supabase.py` a second time; confirm `CREATE INDEX IF NOT EXISTS` is a no-op (no error).
**Done Criteria:** `pytest` exit code 0; second `load_supabase.py` run exits 0 with no error output.
**Dependencies:** Task 1.
**Risk Notes:** Existing `tests/test_load_supabase.py` may need an additional test case for the index DDL constant — add if not present.

### Task 6: Update `context.md` and documentation
**Intent:** Reflect the new indexes and favicon in the workspace context and documentation.
**Inputs:** `.aib_memory/context.md`; this `request.md`.
**Outputs:** Updated `context.md` noting `fact_prices` indexes; no other documentation changes required.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Update the `fact_prices` entry in `context.md` (Technical Design > Module Breakdown > `src/load_supabase.py`) to note the two new indexes.
2. Update the Architecture > Key Decisions section if needed.
**Done Criteria:** `context.md` accurately reflects the `fact_prices` index additions.
**Dependencies:** Tasks 1–3 complete.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update `src/load_supabase.py` description to include the two new `fact_prices` indexes; update Key Architectural Decisions if a new decision entry is warranted.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/load_supabase.py` | Modified | Add `_CREATE_INDEXES` DDL constant and execute it in `create_tables()`. |
| `react-app/public/favicon.ico` | Created | Add physical favicon file to eliminate browser 404 error. |
| `react-app/index.html` | Modified (possible) | May update `<link rel="icon">` to reference `/favicon.ico` explicitly. |
| `.aib_memory/context.md` | Modified | Reflect new `fact_prices` indexes in architecture documentation. |
| `tests/test_load_supabase.py` | Modified (possible) | Add test for index DDL constant presence if not already covered. |

## Internal Review of Request and Product Docs

- OK: `request.md` — All 12 mandatory sections present and sections 1–6 are non-empty.
- OK: `context.md` — Accurately documents the existing RPC functions and their timeout fallback behaviour.
- OK: `src/load_supabase.py` — `_CREATE_RPC_FUNCTIONS` correctly provisions both RPC functions with `GRANT EXECUTE TO anon`. No index DDL present (confirmed gap).
- Missing info: `context.md` — Does not mention the absence of `fact_prices` indexes, which is the root cause of this request. Will be corrected in Task 6.
- OK: `references.md` — `REF-0001` (context.md) is the only product-doc; `REF-0002` (Concepts.md) is domain-only. No additional product docs require update for this request.
- Ambiguity: `request.md` (this doc) — The exact URL of the 404 error is unknown from the input (the user's copy-paste did not include the URL). Resolution: implementation Task 2 includes a DevTools verification step before applying the favicon fix.
