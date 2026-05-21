Implementation record for request R-20260421-0505 — Add Netlify deploy option to menu.

Files considered from `.aib_memory/`:
- `.aib_memory/context.md` (REF-0001, product-doc)
- `.aib_memory/references.md`
- `.aib_memory/requests/R-20260421-0505-add-netlify-deploy-option-to-menu/request.md`

## Implementation Log

### Entry 2026-04-21 05:10

#### Scope
Added option 5 ("Deploy React app to Netlify") to the interactive terminal menu (`menu.py`) and created the standalone deploy script (`src/deploy_netlify.py`). The deploy script detects Netlify CLI availability, guides the operator through credential acquisition with step-by-step instructions, builds the React app, and deploys to Netlify — or falls back to manual instructions when the CLI is absent. Menu prompt updated from `[0-4]` to `[0-5]`.

#### Changes
- Created `src/deploy_netlify.py` — new standalone Netlify deploy script with functions: `find_netlify_cmd`, `print_manual_instructions`, `get_credential`, `build_react_app`, `deploy_to_netlify`, `main`. Stdlib-only; no new dependencies.
- Updated `menu.py` `print_menu()` — added `5) Deploy React app to Netlify` option.
- Updated `menu.py` `main()` — changed input prompt from `[0-4]` to `[0-5]`; added `elif choice == "5": action_deploy_netlify()` dispatch; updated invalid-choice message to reference `0-5`.
- Added `action_deploy_netlify()` function to `menu.py` — invokes `src/deploy_netlify.py` via `subprocess.run` without `capture_output` to allow stdin passthrough.
- Created `tests/test_deploy_netlify.py` — 13 unit tests covering CLI detection, manual instructions fallback, credential prompt helpers, menu option presence, and dispatch routing.
- Updated `.aib_memory/context.md` — reflected new menu option 5, `src/deploy_netlify.py` module, updated repository structure and operations sections.
- Created `analysis.md` in request folder.
- Created `UAT_scenarios.md` in request folder (UAT-01: end-to-end deploy with live credentials).
- Created `request.md` in request folder.
- Archived original input to `inputs/input-archive-2026-04-21_050827.md`.
- Reset `input.md` with active request ID.

#### Tests
- Unit (13 tests in `tests/test_deploy_netlify.py`): all passed — `python -m pytest tests/test_deploy_netlify.py -v` → 13 passed in 0.07s.
  - TestFindNetlifyCmd: 2 tests — CLI found on PATH, CLI not on PATH.
  - TestPrintManualInstructions: 2 tests — heading present, Netlify URL present.
  - TestGetCredential: 4 tests — env var present, prompt on missing env var, prompt for site ID, empty input exits 1.
  - TestMainNoCliAvailable: 1 test — main() prints instructions and exits 0 when no CLI.
  - TestMenuOption5: 4 tests — option 5 in menu output, Netlify label in menu, invalid choice references 5, choice 5 dispatches to action.

#### Outcome
Success. All success criteria met: SC-1 through SC-6 verified. The menu now includes option 5 with correct dispatch. `src/deploy_netlify.py` handles credential collection, build, and deploy. Manual instructions fallback works when CLI is absent. All 13 unit tests pass. No unresolved failures or blockers.

#### Evidence
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 13 items

tests/test_deploy_netlify.py::TestFindNetlifyCmd::test_returns_netlify_list_when_found_on_path PASSED
tests/test_deploy_netlify.py::TestFindNetlifyCmd::test_returns_none_when_not_on_path PASSED
tests/test_deploy_netlify.py::TestPrintManualInstructions::test_output_contains_expected_heading PASSED
tests/test_deploy_netlify.py::TestPrintManualInstructions::test_output_contains_netlify_url PASSED
tests/test_deploy_netlify.py::TestGetCredential::test_exits_when_user_enters_empty_value PASSED
tests/test_deploy_netlify.py::TestGetCredential::test_prompts_for_site_id_when_env_not_set PASSED
tests/test_deploy_netlify.py::TestGetCredential::test_prompts_user_when_env_not_set PASSED
tests/test_deploy_netlify.py::TestGetCredential::test_returns_env_value_when_set PASSED
tests/test_deploy_netlify.py::TestMainNoCliAvailable::test_main_prints_manual_instructions_and_exits_0_when_no_cli PASSED
tests/test_deploy_netlify.py::TestMenuOption5::test_choice_5_dispatches_to_action_deploy_netlify PASSED
tests/test_deploy_netlify.py::TestMenuOption5::test_invalid_choice_message_includes_5 PASSED
tests/test_deploy_netlify.py::TestMenuOption5::test_print_menu_contains_netlify_label PASSED
tests/test_deploy_netlify.py::TestMenuOption5::test_print_menu_contains_option_5 PASSED

============================== 13 passed in 0.07s ==============================
```
