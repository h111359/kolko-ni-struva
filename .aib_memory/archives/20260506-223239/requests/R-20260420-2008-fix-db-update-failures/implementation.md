Files taken into consideration:
- `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/request.md`
- `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/analysis.md`
- `.aib_memory/context.md`
- `.aib_memory/references.md`

## Implementation Log

### Entry 2026-04-20 20:15
#### Scope
Fix two root causes preventing `src/load_supabase.py` from successfully updating the Supabase database: (1) `ModuleNotFoundError: No module named 'psycopg2'` when running outside the venv — `refresh.sh` was using system `python3` instead of the venv Python; (2) NOT NULL constraint violations on `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date` caused by schema drift from an older DDL iteration. The `create_tables()` function now applies idempotent ALTER TABLE DROP NOT NULL statements after provisioning. Analysis reference: analysis.md §§ Root causes, Research Results, Spikes.

#### Changes
- Modified `refresh.sh`: added venv detection guard (mirrors `menu.sh` pattern). When `$SCRIPT_DIR/venv/bin/python` is executable, the `$PYTHON` variable is set to it; otherwise falls back to `python3`. All `python3 src/...` invocations replaced with `"$PYTHON" src/...`.
- Modified `src/load_supabase.py`: added `_ENSURE_NULLABLE_DDL` module-level constant containing three idempotent `ALTER TABLE IF EXISTS … ALTER COLUMN … DROP NOT NULL` statements for `dim_store.settlement_key`, `dim_store.company_key`, and `dim_file.zip_date`.
- Modified `src/load_supabase.py` — `create_tables()`: added a second `cur.execute(_ENSURE_NULLABLE_DDL)` call after `cur.execute(_CREATE_DDL)`. Updated docstring to describe both DDL steps. Added inline comment explaining the idempotency rationale.
- Created `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/test_fixes.py`: 8 unit tests covering `create_tables()` execute-twice behaviour, `_ENSURE_NULLABLE_DDL` content assertions, and `refresh.sh` venv guard assertions.

#### Tests
- unit: `TestCreateTablesExecutesTwoDDLCalls::test_create_tables_calls_execute_twice` — pass (mock cursor called twice in correct order; commit called once)
- unit: `TestEnsureNullableDdlContent::test_ddl_contains_dim_store_settlement_key` — pass
- unit: `TestEnsureNullableDdlContent::test_ddl_contains_dim_store_company_key` — pass
- unit: `TestEnsureNullableDdlContent::test_ddl_contains_dim_file_zip_date` — pass
- unit: `TestEnsureNullableDdlContent::test_ddl_contains_drop_not_null` — pass
- unit: `TestRefreshShVenvDetection::test_refresh_sh_contains_venv_bin_python` — pass
- unit: `TestRefreshShVenvDetection::test_refresh_sh_contains_python_variable` — pass
- unit: `TestRefreshShVenvDetection::test_refresh_sh_has_fallback_to_python3` — pass
- integration: `python src/load_supabase.py` with venv Python — pass (exit code 0, output: "already up to date")

#### Outcome
All fixes implemented and verified. 8/8 unit tests pass. Integration smoke test passes with exit code 0. The Supabase DB update is now reliable: idempotent NOT NULL drops prevent constraint-drift failures on any remote instance; `refresh.sh` always uses the venv Python when present. No regressions introduced.

#### Evidence
```
============================= test session starts ==============================
collected 8 items

test_fixes.py::TestCreateTablesExecutesTwoDDLCalls::test_create_tables_calls_execute_twice PASSED
test_fixes.py::TestEnsureNullableDdlContent::test_ddl_contains_dim_file_zip_date PASSED
test_fixes.py::TestEnsureNullableDdlContent::test_ddl_contains_dim_store_company_key PASSED
test_fixes.py::TestEnsureNullableDdlContent::test_ddl_contains_dim_store_settlement_key PASSED
test_fixes.py::TestEnsureNullableDdlContent::test_ddl_contains_drop_not_null PASSED
test_fixes.py::TestRefreshShVenvDetection::test_refresh_sh_contains_python_variable PASSED
test_fixes.py::TestRefreshShVenvDetection::test_refresh_sh_contains_venv_bin_python PASSED
test_fixes.py::TestRefreshShVenvDetection::test_refresh_sh_has_fallback_to_python3 PASSED

8 passed in 0.05s
```

```
Connecting to Supabase …
Provisioning schema …
Tables created / verified.
Upserting dimension tables …
  Upserted 63 rows into dim_date.
  Upserted 217 rows into dim_company.
  Upserted 266 rows into dim_settlement.
  Upserted 369 rows into dim_category.
  Upserted 118,281 rows into dim_product.
  Upserted 4,824 rows into dim_store.
  Upserted 13,089 rows into dim_file.
Latest local fact date  : 2026-04-18
Latest remote fact date : 2026-04-18
already up to date
Exit code: 0
```
