Files taken into consideration:
- `.aib_memory/request.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `src/load_supabase.py`
- `tests/test_load_supabase.py`

## Implementation Log

### Entry 2026-05-07 22:55
#### Scope
Add `prune_dim_category(conn)` to `src/load_supabase.py` and wire it into `main()` after `prune_dim_date`, so that after each sync run Supabase `dim_category` retains only `category_key` values referenced by `fact_prices_lookback`. Add four unit tests in `tests/test_load_supabase.py` covering normal pruning, safety guard on empty fact table, rollback on database error, and no-op when all categories are referenced. Update `context.md` to document the new pruning step.

#### Changes
- Updated module docstring in `src/load_supabase.py` to reference R-20260507-2248 and describe the new dim_category prune responsibility.
- Added `prune_dim_category(conn)` function to `src/load_supabase.py` immediately after `prune_dim_date`, following the same commit/rollback discipline; fetches `SELECT DISTINCT category_key FROM fact_prices_lookback`, skips DELETE (safety guard) when result is empty, otherwise executes `DELETE FROM dim_category WHERE category_key NOT IN (...)`.
- Added Step 6 call `prune_dim_category(conn)` to `main()` in `src/load_supabase.py` after the `prune_dim_date` call, with a preceding print statement; inside the existing `try` block.
- Added `prune_dim_category` to the import block in `tests/test_load_supabase.py`.
- Added `TestPruneDimCategory` class to `tests/test_load_supabase.py` with four test methods: `test_prune_removes_unreferenced_rows`, `test_safety_guard_on_empty_fact_table`, `test_rollback_on_db_error`, `test_no_op_when_all_categories_referenced`.
- Updated `.aib_memory/context.md`: added R-20260507-2248 update annotation, updated Functional Capability 6, updated `src/load_supabase.py` module description with `prune_dim_category`, updated Data Retention section.

#### Tests
- unit: `TestPruneDimCategory::test_prune_removes_unreferenced_rows` — pass
- unit: `TestPruneDimCategory::test_safety_guard_on_empty_fact_table` — pass
- unit: `TestPruneDimCategory::test_rollback_on_db_error` — pass
- unit: `TestPruneDimCategory::test_no_op_when_all_categories_referenced` — pass
- unit: full `tests/test_load_supabase.py` suite (33 tests) — pass

#### Outcome
Successful. All 33 tests pass (29 pre-existing + 4 new). `prune_dim_category` is correctly positioned in `main()` after `insert_lookback` and `prune_dim_date`, satisfying the ordering constraint from the request. The safety guard prevents wiping `dim_category` when `fact_prices_lookback` is empty. No new dependencies introduced. Implementation is idempotent.

#### Evidence
- Test run output:

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 33 items

tests/test_load_supabase.py::TestCreateTables::test_commits_after_ddl PASSED
tests/test_load_supabase.py::TestCreateTables::test_create_ddl_does_not_contain_fact_prices_table PASSED
tests/test_load_supabase.py::TestCreateTables::test_executes_ddl_with_dim_date PASSED
tests/test_load_supabase.py::TestCreateTables::test_executes_five_ddl_statements PASSED
tests/test_load_supabase.py::TestCreateTables::test_index_ddl_contains_lookback_composite_date_store_index PASSED
tests/test_load_supabase.py::TestCreateTables::test_index_ddl_contains_lookback_date_key_index PASSED
tests/test_load_supabase.py::TestCreateTables::test_index_ddl_targets_fact_prices_lookback PASSED
tests/test_load_supabase.py::TestUpsertDimSQL::test_upsert_rows_match_csv_content PASSED
tests/test_load_supabase.py::TestUpsertDimSQL::test_upsert_sql_contains_on_conflict_clause PASSED
tests/test_load_supabase.py::TestInsertLookback::test_rollback_on_db_error PASSED
tests/test_load_supabase.py::TestInsertLookback::test_truncates_and_inserts_rows PASSED
tests/test_load_supabase.py::TestInsertLookback::test_truncates_only_when_csv_empty PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_custom_n_parameter PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_ignores_non_csv_files PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_result_contains_latest_local_date PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_returns_all_when_fewer_than_three PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_returns_empty_list_for_absent_directory PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_returns_empty_list_for_empty_directory PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_returns_latest_three_from_many PASSED
tests/test_load_supabase.py::TestGetRetainedLocalDates::test_returns_single_date_when_one_csv PASSED
tests/test_load_supabase.py::TestGetDateKeysForDates::test_passes_date_list_to_query PASSED
tests/test_load_supabase.py::TestGetDateKeysForDates::test_returns_date_keys_from_cursor PASSED
tests/test_load_supabase.py::TestGetDateKeysForDates::test_returns_empty_list_for_empty_input PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_commits_after_delete PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_executes_delete_with_not_in_clause PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_idempotent_when_already_pruned PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_returns_rowcount PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_rollback_on_db_error PASSED
tests/test_load_supabase.py::TestPruneDimDate::test_skips_delete_when_retained_keys_empty PASSED
tests/test_load_supabase.py::TestPruneDimCategory::test_no_op_when_all_categories_referenced PASSED
tests/test_load_supabase.py::TestPruneDimCategory::test_prune_removes_unreferenced_rows PASSED
tests/test_load_supabase.py::TestPruneDimCategory::test_rollback_on_db_error PASSED
tests/test_load_supabase.py::TestPruneDimCategory::test_safety_guard_on_empty_fact_table PASSED

============================== 33 passed in 0.23s ==============================
```
