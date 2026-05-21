Implementation log for R-20260421-0348: Change menu actions and numbering.

Files taken into consideration:
- `.aib_memory/requests/R-20260421-0348-change-menu-actions-and-numbering/request.md`
- `.aib_memory/context.md` (REF-0001)
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-04-21 03:55

#### Scope

Updated `menu.py` to reorder the action menu, extend "Full refresh" to include all three ETL steps (download → transform → update Supabase) with failure-stop behaviour, and move "Exit" to key `0`. Updated `context.md` to reflect the new menu state in four places (Requirements Summary, Architecture Component Map, Technical Design module breakdown, and Workspace File Inventory).

#### Changes

- Updated `print_menu()` in `menu.py`: replaced five `print()` action lines with new order — 1) Full refresh (download + transform + update supabase), 2) Download only, 3) Transform only, 4) Update Supabase DB, 0) Exit.
- Updated `run_script()` in `menu.py`: changed return type from `None` to `bool`; added `return True` on success and `return False` in the `except CalledProcessError` block; updated docstring with `Returns:` field.
- Updated `action_full_refresh()` in `menu.py`: replaced unconditional sequential `run_script()` calls with failure-guarded conditional sequence — stops on first failure; added third step `run_script("src/load_supabase.py")`; updated docstring.
- Updated `main()` in `menu.py`: changed input prompt from `[1-5]` to `[0-4]`; remapped dispatch — `"0"` → exit, `"1"` → full refresh, `"2"` → download, `"3"` → transform, `"4"` → Supabase; removed old `"4"` (exit) and `"5"` (Supabase) branches; updated invalid-choice message.
- Updated Requirements Summary item 5 in `.aib_memory/context.md` to describe new action numbering and extended full-refresh scope.
- Updated Architecture Component Map `menu.py` entry in `.aib_memory/context.md` to describe new action numbering and failure-stop full refresh.
- Updated Technical Design `menu.py` entry in `.aib_memory/context.md` to reflect new numbered menu and exit key.
- Updated Workspace File Inventory `menu.py` entry in `.aib_memory/context.md` to reflect new action numbering.
- Updated `context.md` preamble timestamp to 2026-04-21 03:55 UTC+3.
- Created `test_menu_r20260421_0348.py` in request folder: 20 unit tests covering SC-1 through SC-8, T2–T3, T4–T5, T6–T8, T10.

#### Tests

- unit: `TestPrintMenu.test_action_1_is_full_refresh` — pass (SC-1)
- unit: `TestPrintMenu.test_action_2_is_download_only` — pass (SC-1)
- unit: `TestPrintMenu.test_action_3_is_transform_only` — pass (SC-1)
- unit: `TestPrintMenu.test_action_4_is_update_supabase` — pass (SC-1)
- unit: `TestPrintMenu.test_action_0_is_exit` — pass (SC-1)
- unit: `TestPrintMenu.test_menu_order` — pass (SC-1)
- unit: `TestPrintMenu.test_no_action_5` — pass (SC-7)
- unit: `TestRunScriptReturnValue.test_returns_true_on_success` — pass
- unit: `TestRunScriptReturnValue.test_returns_false_on_failure` — pass
- unit: `TestActionFullRefresh.test_calls_all_three_scripts_on_success` — pass (SC-3)
- unit: `TestActionFullRefresh.test_stops_after_extract_failure` — pass (SC-3 failure guard)
- unit: `TestActionFullRefresh.test_stops_after_transform_failure` — pass (SC-3 failure guard)
- unit: `TestMainDispatch.test_key_0_exits_cleanly` — pass (SC-2)
- unit: `TestMainDispatch.test_key_1_calls_full_refresh` — pass (SC-3)
- unit: `TestMainDispatch.test_key_2_calls_download` — pass (SC-4)
- unit: `TestMainDispatch.test_key_3_calls_transform` — pass (SC-5)
- unit: `TestMainDispatch.test_key_4_calls_supabase` — pass (SC-6)
- unit: `TestMainDispatch.test_key_5_is_invalid` — pass (SC-7)
- unit: `TestMainDispatch.test_key_range_in_prompt` — pass (T3)
- unit: `TestContextMdUpdated.test_old_menu_description_absent` — pass (SC-8 / T10)
- syntax: `python -m py_compile menu.py` — pass (T1)
- Total: 20 passed, 0 failed, 0 skipped

#### Outcome

Successful. All 20 unit tests pass. All Success Criteria SC-1 through SC-8 are satisfied by automated tests. Manual UAT scenarios (UAT-01 through UAT-03 in `UAT_scenarios.md`) require interactive terminal verification. No unresolved test failures or blockers.

#### Evidence

- Path: `menu.py` (updated)
- Path: `.aib_memory/context.md` (updated)
- Path: `.aib_memory/requests/R-20260421-0348-change-menu-actions-and-numbering/test_menu_r20260421_0348.py` (created)

```
Ran 20 tests in 0.020s

OK
```
