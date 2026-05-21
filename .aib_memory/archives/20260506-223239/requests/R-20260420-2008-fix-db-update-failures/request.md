## Goal

Diagnose and fix all failures that prevent `src/load_supabase.py` from successfully updating the Supabase database. The fix must be complete and verified — no unresolved errors at the end.

## Background

The operator runs the Supabase sync either via menu option 5 ("Update Supabase DB") launched from `menu.sh`, or directly (`python src/load_supabase.py`). Both entry points were failing. Two distinct root causes were identified through workspace investigation:

1. **Missing dependency error**: Running `python src/load_supabase.py` directly fails with `ModuleNotFoundError: No module named 'psycopg2'` because the system Python does not have `psycopg2-binary` installed. The package is only installed in the project venv. `menu.sh` correctly uses the venv Python for `menu.py`, and `menu.py` uses `sys.executable` for subprocess calls — so the menu path works. However, `refresh.sh` still invokes `python3` (system Python) unconditionally, creating an inconsistency.

2. **NOT NULL constraint violation**: The Supabase tables were previously created with an older DDL (from R-20260418-2209 or an earlier iteration of R-20260420-1730) that included NOT NULL constraints on `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date`. The current `load_supabase.py` DDL does not include those NOT NULL constraints, but `CREATE TABLE IF NOT EXISTS` never modifies existing tables. The user manually ran `ALTER TABLE` commands to fix the remote schema. To prevent regression, the code must apply those alterations idempotently.

## Scope

- Fix `refresh.sh` to use the venv Python when a venv is present (mirror the pattern already in `menu.sh`), so that all scripts run in the same environment.

- Fix `src/load_supabase.py` — `create_tables()` function — to add idempotent `ALTER TABLE … ALTER COLUMN … DROP NOT NULL` statements for the three nullable columns that were erroneously constrained: `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date`.

- Add or update tests in the request folder to cover the fix (test that `create_tables()` executes the migration SQL, and that `refresh.sh` uses the correct Python).

## Out of scope

- Changes to `src/extract.py`, `src/transform.py`, or `src/config_utils.py`.

- Changes to `menu.sh`, `menu.bat`, `refresh.bat`, or `menu.py`.

- Supabase schema migrations beyond the three NOT NULL drops.

- Bulk historical backfill or new ETL functionality.

- Modifying `requirements.txt`.

## Constraints

- Python 3.9+ compatibility.

- The ALTER TABLE statements MUST be idempotent (PostgreSQL does not error when dropping NOT NULL from an already-nullable column).

- `refresh.sh` changes MUST NOT break existing behaviour when no venv is present (fall through to `python3` as before).

- No new pip packages.

- Do not create a Python virtual environment.

## Success criteria

- `python src/load_supabase.py` invoked with the venv Python succeeds without errors.

- Running `create_tables()` against a Supabase instance that has the old NOT NULL constraints succeeds (ALTER TABLE DROP NOT NULL is idempotent).

- `refresh.sh` uses venv Python when `venv/bin/python` is present; falls back to `python3` otherwise.

- All new tests pass.

## Assumptions

- A1: The project venv at `./venv/` is present and contains all packages listed in `requirements.txt`, including `psycopg2-binary==2.9.10` and `python-dotenv`.
  - Risk if false: `refresh.sh` venv branch would fall back to `python3` (system Python), which already works for extract/transform but not for load_supabase.py.

- A2: PostgreSQL `ALTER TABLE … ALTER COLUMN … DROP NOT NULL` is idempotent (no error when column is already nullable). Confirmed by spike.
  - Risk if false: None — this is guaranteed PostgreSQL behaviour since version 8.x.

- A3: The `_CREATE_DDL` string is executed in a single `cur.execute()` call and PostgreSQL processes all statements in it as a multi-statement batch.
  - Risk if false: Only the first DDL statement would execute; the rest would be silently dropped. In practice, psycopg2 and PostgreSQL support multi-statement strings in `execute()`.

- A4: The three problematic NOT NULL constraints (`dim_store.settlement_key`, `dim_store.company_key`, `dim_file.zip_date`) are the only schema drift issues. No other columns were erroneously created with NOT NULL against current intent.
  - Risk if false: Other NOT NULL violations could surface on a fresh Supabase project; operator would need to re-run the sync after diagnosing.

## Plan

### Task 1: Fix `refresh.sh` to use venv Python
**Intent:** Ensure `refresh.sh` uses the project venv Python when available, consistent with `menu.sh`.
**Inputs:** Current `refresh.sh`; `menu.sh` as the pattern reference.
**Outputs:** Updated `refresh.sh` with venv detection guard.
**External Interfaces:** None.
**Environment & Configuration:** `./venv/bin/python` at project root.
**Procedure:**
1. Read current `refresh.sh`.
2. Add venv detection: if `$SCRIPT_DIR/venv/bin/python` is executable, set `PYTHON` to it; otherwise set `PYTHON` to `python3`.
3. Replace `python3` invocations with `$PYTHON`.
**Done Criteria:** `refresh.sh` invokes venv Python when venv is present; falls back to `python3` otherwise. Script runs successfully with venv active.
**Dependencies:** None.
**Risk Notes:** None; the fallback preserves existing behavior.

### Task 2: Fix `create_tables()` to apply idempotent NOT NULL drops
**Intent:** Prevent schema drift from old DDL by adding ALTER TABLE DROP NOT NULL for the three affected nullable columns.
**Inputs:** `src/load_supabase.py` — `_CREATE_DDL` constant and `create_tables()` function.
**Outputs:** Updated `src/load_supabase.py` with a new `_ENSURE_NULLABLE_DDL` constant and additional `cur.execute` call in `create_tables()`.
**External Interfaces:** Supabase PostgreSQL (via psycopg2 connection passed to `create_tables()`).
**Environment & Configuration:** `DATABASE_URL` in `.env`.
**Procedure:**
1. Add a new module-level constant `_ENSURE_NULLABLE_DDL` containing the three ALTER TABLE statements.
2. In `create_tables()`, after `cur.execute(_CREATE_DDL)`, add a second `cur.execute(_ENSURE_NULLABLE_DDL)` call.
3. Update the `create_tables()` docstring to describe the new migration step.
**Done Criteria:** Calling `create_tables()` against the live Supabase DB produces no error. `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date` are confirmed nullable.
**Dependencies:** Task 1 (must be able to run with venv Python).
**Risk Notes:** ALTER TABLE acquires a brief ACCESS EXCLUSIVE lock; safe on a lightly loaded development DB. No data is modified.

### Task 3: Write tests
**Intent:** Verify both fixes with deterministic unit tests.
**Inputs:** `src/load_supabase.py`; test framework (`unittest`, no new deps).
**Outputs:** `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/test_fixes.py`.
**External Interfaces:** Mocked psycopg2 connection (no real DB connection required).
**Environment & Configuration:** Python 3.9+; venv.
**Procedure:**
1. Test that `create_tables()` executes exactly two SQL statements (CREATE DDL + ALTER DDL) in the correct order using a mock cursor.
2. Test that `_ENSURE_NULLABLE_DDL` contains the three expected ALTER TABLE clauses.
3. Verify `refresh.sh` contains the venv detection guard string.
**Done Criteria:** All tests pass with `python -m pytest test_fixes.py -v` (or `python -m unittest` if pytest unavailable).
**Dependencies:** Task 1, Task 2.
**Risk Notes:** None.

## Testing

- T1 — test_create_tables_executes_two_sql_calls: Call `create_tables()` with a mock psycopg2 connection and assert that `cur.execute()` is called exactly twice — once for `_CREATE_DDL` and once for `_ENSURE_NULLABLE_DDL`. Expected outcome: both calls occur in order; `conn.commit()` is called once.

- T2 — test_ensure_nullable_ddl_contains_required_alters: Assert that `_ENSURE_NULLABLE_DDL` contains the strings `dim_store` and `settlement_key`, `company_key`, and `dim_file` and `zip_date`. Expected outcome: all five sub-strings present.

- T3 — test_refresh_sh_uses_venv_detection: Read the content of `refresh.sh` and assert it contains `venv/bin/python`. Expected outcome: string present.

- T4 — integration smoke: Run `python src/load_supabase.py` with venv Python and assert exit code 0. Expected outcome: prints "already up to date" or "Supabase sync complete" with no error.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update `## Architecture & Key Decisions` (refresh.sh venv note) and `## Technical Design` (load_supabase.py create_tables description).

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `refresh.sh` | Modified | Add venv detection guard to use venv Python when available. |
| `src/load_supabase.py` | Modified | Add `_ENSURE_NULLABLE_DDL` constant and second `cur.execute` in `create_tables()`. |
| `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/test_fixes.py` | Created | New unit tests for both bug fixes. |
| `.aib_memory/context.md` | Modified | Update component descriptions to reflect changes. |

## Internal Review of Request and Product Docs

- OK: `src/load_supabase.py` — module docstring and all public function docstrings are present and well-formed.
- OK: `refresh.sh` — existing script is well-commented and minimal; pattern is consistent with `menu.sh`.
- OK: `menu.sh` — venv detection pattern is the reference for Task 1; correctly implemented with `[ -x "$SCRIPT_DIR/venv/bin/python" ]`.
- Ambiguity: `context.md § Technical Design` — describes `refresh.sh` as `python3 src/extract.py then python3 src/transform.py` without mentioning venv; will be updated after implementation.
- Ambiguity: `context.md § Technical Design` — describes `create_tables()` without mentioning the `_ENSURE_NULLABLE_DDL` migration step; will be updated after implementation.
- OK: No contradictions found between `request.md` and `context.md` for the two targeted fixes.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect
Both fixes are minimal and backward-compatible. The venv detection pattern in `refresh.sh` mirrors the established `menu.sh` convention, reducing code drift. The idempotent ALTER TABLE approach is the lightweight alternative to a migration runner (Flyway/Liquibase), which would be over-engineering for this single-developer pipeline. The risk of targeting only three columns is bounded by the evidence: the operator only had to fix these three, and workspace inspection confirms no other nullable-column mismatches.

- Adding `_ENSURE_NULLABLE_DDL` as a separate constant rather than inlining in _CREATE_DDL keeps the DDL sections semantically distinct.
- The fallback to `python3` in `refresh.sh` preserves backward compatibility when no venv exists.
- No architectural regressions introduced.
- Test coverage is purely unit/mock; no CI infrastructure required.

### Product Owner
The fix addresses a documented operator-facing failure (menu option 5 and direct script execution). The success criteria are measurable and testable. Scope is tightly bounded to two files plus tests; no new features are introduced. Business value: operators can reliably run the Supabase sync without manual DB surgery.

- Clear acceptance: "python src/load_supabase.py exits cleanly with exit code 0."
- No new user-facing behaviour changes.
- Documentation update to `context.md` preserves the product doc quality standard.

### User
The operator will notice the fix only by the absence of failure. No menu changes, no workflow changes. `refresh.sh` now uses the same Python as the menu scripts, which is what operators would intuitively expect.

- No new steps required.
- Error message surfacing is unchanged (existing error paths remain).
- Operators who currently run `./refresh.sh` will now get the same Python environment as `./menu.sh`.

### Security Officer
Both changes are low-risk from a security standpoint. `refresh.sh` reads the venv path from `$SCRIPT_DIR` (no user input, no injection surface). The ALTER TABLE statements modify no data and add no new attack surface. `DATABASE_URL` handling is unchanged.

- No credentials introduced.
- No new subprocess invocations with user-controlled input.
- HTTPS and `.env` secret handling unchanged.

### Data Governance Officer
No data model changes. The ALTER TABLE DROP NOT NULL operations do not change data — they only relax constraints that were incorrectly applied. Dimension and fact data lineage is unaffected. The sync remains idempotent and operator-triggered. No new data retention implications.

- Data correctness: relaxing NOT NULL allows NULLs for FK columns in dim_store (permitted by design — partial-snowflake); and for zip_date in dim_file (permitted if source data lacks a date).
- Lineage: unchanged.
- Compliance: no PII involved; no regulatory impact.

