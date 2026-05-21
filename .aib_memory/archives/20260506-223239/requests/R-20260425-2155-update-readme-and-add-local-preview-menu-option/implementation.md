Files taken into consideration:
- .aib_memory/requests_register.md
- .aib_memory/references.md
- .aib_memory/context.md (REF-0001, product-doc)
- .aib_brain/Concepts.md (REF-0002, domain)
- .aib_brain/conventions/context-convention.md
- .aib_brain/conventions/coding-general-convention.md
- .aib_brain/conventions/coding-python-convention.md
- .aib_brain/conventions/implementation-convention.md
- .aib_memory/requests/R-20260425-2155-update-readme-and-add-local-preview-menu-option/request.md

## Implementation Log

### Entry 2026-04-25 22:10
#### Scope
Implemented request R-20260425-2155: updated README.md to reflect the current product state with accurate menu options, added explicit local preview steps and prerequisites, and added a new option 6 to menu.py that runs `npm run build && npm run preview` from react-app/ with best-effort browser opening via webbrowser.open(). Updated tests and synchronized context.md.

#### Changes
- Modified `menu.py`: updated module docstring; added `import webbrowser`; added `REACT_DIR` and `PREVIEW_URL` module constants; added `action_local_preview()` function implementing npm build + vite preview with best-effort browser open; updated `print_menu()` to include option 6; updated `main()` loop to dispatch choice "6" to `action_local_preview()` and updated input prompt and invalid-choice message to reflect range 0–6.
- Modified `README.md`: updated Table of Contents to include "Netlify Deploy & React App Setup" (item 11) and "Local Preview" (item 12); added Node.js ≥ 18 and npm to Prerequisites; updated Repository Structure to include `.env.example`, `src/load_supabase.py`, `src/deploy_netlify.py`, `react-app/` subtree, and `tests/test_deploy_netlify.py`; updated Quick Start with local preview steps (npm install, menu option 6, and manual command); replaced stale Scripts > menu.py section (old 4-option menu) with accurate 6-option description plus descriptions for `src/load_supabase.py` and `src/deploy_netlify.py`; added new "Local Preview" section with prerequisites, usage (via menu and manually), dev-vs-preview comparison table.
- Modified `tests/test_deploy_netlify.py`: renamed `test_invalid_choice_message_includes_5` to `test_invalid_choice_message_includes_6`, updated invalid input from "6" (now valid) to "9", updated assertion to check for "6" in output; added `TestMenuOption6` class with three tests: `test_print_menu_contains_option_6`, `test_print_menu_contains_preview_label`, `test_choice_6_dispatches_to_action_local_preview`.
- Modified `.aib_memory/context.md` (REF-0001): updated functional capability #5 to include option 6 and reference R-20260425-2155; updated menu.py component description to document option 6 behavior (npm build + preview, PREVIEW_URL constant, best-effort webbrowser.open).

#### Tests
- unit: `tests/test_config_utils.py` — 8 tests — all pass
- unit: `tests/test_deploy_netlify.py` — 24 tests (including 3 new TestMenuOption6 tests) — all pass
- integration: menu print_menu() output verified via `python -c "import menu; menu.print_menu()"` — option 6 visible — pass
- integration: README grep checks — "Local Preview" present (2 occurrences), "npm run build && npm run preview" present (3 occurrences), "6)" present (3 occurrences) — pass

#### Outcome
All 32 automated tests pass with no regressions. README now accurately describes the current product architecture including the React app, Supabase sync, Netlify deploy, and the new local preview workflow. Menu option 6 is operational and wired to action_local_preview(). Browser open is best-effort and always falls back to the printed URL. No blockers or residual risks.

#### Evidence
- `python -m pytest tests/ -v` output: 32 passed in 0.13s
- `python -c "import menu; menu.print_menu()"` output confirms option `6) Preview React app locally` is present
- `grep -c "Local Preview" README.md` → 2
- `grep -c "npm run build && npm run preview" README.md` → 3
