## Goal

Change the interactive terminal menu (`menu.py`) action numbering and the scope of the "Full refresh" action.

The new menu must have these five entries in this order:

- `1) Full refresh      (download + transform + update supabase)`
- `2) Download only     (python src/extract.py)`
- `3) Transform only    (python src/transform.py)`
- `4) Update Supabase DB  (python src/load_supabase.py)`
- `0) Exit`

"Full refresh" must now run all three steps: download → transform → update Supabase. "Exit" moves from key `4` to key `0`.

## Background

The current menu (`menu.py`, `print_menu()` + `main()`) has the following action numbers:

- `1) Download only`
- `2) Transform only`
- `3) Full refresh (download + transform only — no Supabase)`
- `4) Exit`
- `5) Update Supabase DB`

The operator asked to reorder the actions, give "Full refresh" top position (number 1), extend it to include the Supabase sync step, and change "Exit" to `0`.
This change has no impact on `menu.sh` or `menu.bat` (they remain single-line launchers).

## Scope

- `menu.py` — update `print_menu()` to match the new action text and ordering.

- `menu.py` — update `main()` input prompt to read `[0-4]` instead of `[1-5]`.

- `menu.py` — update `main()` dispatch block: remap keys `0`→Exit, `1`→Full refresh (all three steps), `2`→Download, `3`→Transform, `4`→Supabase.

- `menu.py` — update `action_full_refresh()` to also run `src/load_supabase.py` after download and transform.

- `context.md` (REF-0001) — update the menu action description in the Requirements and Architecture sections.

## Out of scope

- No changes to `menu.sh` or `menu.bat`.

- No changes to `src/extract.py`, `src/transform.py`, or `src/load_supabase.py`.

- No changes to `refresh.sh` or `refresh.bat`.

- No changes to `config.ini`, `data/`, or any schema artifacts.

- No UI or web frontend changes.

## Constraints

- Python 3.9+ compatibility must be preserved.

- Subprocess invocations must remain in list form (no `shell=True`).

- The "Full refresh" action runs all three scripts sequentially; if extract or transform fails, `load_supabase.py` MUST NOT be called (rely on existing `CalledProcessError` propagation via `run_script()`).

- No new pip packages may be introduced.

- `menu.sh` and `menu.bat` launchers are not modified.

## Success criteria

- SC-1: Running `menu.py` and viewing the menu displays actions numbered `1`, `2`, `3`, `4`, `0` in the specified text and order.

- SC-2: Selecting `0` exits the menu cleanly (no error).

- SC-3: Selecting `1` runs `src/extract.py`, then `src/transform.py`, then `src/load_supabase.py` in sequence.

- SC-4: Selecting `2` runs only `src/extract.py`.

- SC-5: Selecting `3` runs only `src/transform.py`.

- SC-6: Selecting `4` runs only `src/load_supabase.py`.

- SC-7: All previous action numbers (`1`–`5` from old menu) are no longer valid; the invalid-input message appears for inputs `5`, `6`, etc.

- SC-8: `context.md` references to the menu action list are updated to reflect the new order and revised "Full refresh" scope.

## Assumptions

- A1: The current `run_script()` does not re-raise `CalledProcessError`; a boolean return value will be added
  to enable early exit in `action_full_refresh()` without breaking any existing callers.
  - Risk if false: If `run_script()` already re-raises (e.g., future refactor), the guard in `action_full_refresh()`
    becomes redundant but harmless.

- A2: No existing test in `tests/` directly asserts on `print_menu()` output, the `main()` dispatch table, or
  `action_full_refresh()` call sequence; therefore no existing tests are broken by this change.
  - Risk if false: If such tests exist, they must be updated alongside `menu.py`.

- A3: The two occurrences of the "Full refresh" description in `context.md` (Requirements Summary and Architecture
  sections) are the only documentation locations that reference the old "(download + transform)" menu entry.
  - Risk if false: Additional documentation files may require updates if other references are discovered.

## Plan

### Task 1: Update `menu.py` — `print_menu()` display

**Intent:** Replace the five action lines in `print_menu()` with the new order, numbers, and revised "Full refresh" text.

**Inputs:** `menu.py` (current `print_menu()` function, lines ~140–152)

**Outputs:** `menu.py` (updated `print_menu()` function)

**External Interfaces:** None

**Environment & Configuration:** Python 3.9+ runtime; no config changes

**Procedure:**
1. Read `print_menu()` in `menu.py`.
2. Replace the five `print()` statements with:
   - `"    1) Full refresh      (download + transform + update supabase)"`
   - `"    2) Download only     (python src/extract.py)"`
   - `"    3) Transform only    (python src/transform.py)"`
   - `"    4) Update Supabase DB  (python src/load_supabase.py)"`
   - `"    0) Exit"`

**Done Criteria:** `print_menu()` output matches the five-line specification exactly.

**Dependencies:** None

**Risk Notes:** None

---

### Task 2: Update `menu.py` — `run_script()` return value

**Intent:** Return a boolean from `run_script()` so callers can detect failure without catching exceptions.

**Inputs:** `menu.py` (current `run_script()` function)

**Outputs:** `menu.py` (updated `run_script()` function)

**External Interfaces:** None

**Environment & Configuration:** None

**Procedure:**
1. Add `return True` after the successful `subprocess.run()` block.
2. Add `return False` at the end of the `except CalledProcessError` block (after printing the error).

**Done Criteria:** `run_script()` returns `True` on success and `False` on failure; existing error printing
is preserved.

**Dependencies:** None

**Risk Notes:** Existing callers (`action_download`, `action_transform`, `action_update_supabase`) ignore the
return value — this is safe (no breaking change).

---

### Task 3: Update `menu.py` — `action_full_refresh()` with failure guard

**Intent:** Extend full refresh to run all three scripts sequentially and stop on first failure.

**Inputs:** `menu.py` (current `action_full_refresh()` function)

**Outputs:** `menu.py` (updated `action_full_refresh()` function)

**External Interfaces:** `src/extract.py`, `src/transform.py`, `src/load_supabase.py`

**Environment & Configuration:** None

**Procedure:**
1. Update `action_full_refresh()` to use the boolean return value from `run_script()`:
   ```
   if not run_script("src/extract.py"):
       return
   if not run_script("src/transform.py"):
       return
   run_script("src/load_supabase.py")
   ```

**Done Criteria:** All three scripts are called in order; failure of extract prevents transform; failure of
transform prevents load_supabase; failure of load_supabase does not crash the menu.

**Dependencies:** Task 2

**Risk Notes:** None

---

### Task 4: Update `menu.py` — `main()` dispatch table and prompt

**Intent:** Remap key assignments and update the input prompt range hint.

**Inputs:** `menu.py` (`main()` function)

**Outputs:** `menu.py` (`main()` function updated)

**External Interfaces:** None

**Environment & Configuration:** None

**Procedure:**
1. Change the `input()` prompt from `"  Enter choice [1-5]: "` to `"  Enter choice [0-4]: "`.
2. Update the dispatch block:
   - `"0"` → `print("Exiting."); break`
   - `"1"` → `action_full_refresh()`
   - `"2"` → `action_download()`
   - `"3"` → `action_transform()`
   - `"4"` → `action_update_supabase()`
   - `else` → invalid-choice message (update range reference from `1, 2, 3, 4, or 5` to `0, 1, 2, 3, or 4`).
3. Remove the old `"4"` (exit) and `"5"` (Supabase) branches.

**Done Criteria:** All five valid keys dispatch correctly; `0` exits; `5` and above produce the invalid-choice message.

**Dependencies:** Task 1 (logical; no code dependency)

**Risk Notes:** None

---

### Task 5: Run automated tests

**Intent:** Verify all testable Success Criteria are passing after code changes.

**Inputs:** Updated `menu.py`; Python test environment

**Outputs:** Test run result (pass/fail)

**External Interfaces:** `tests/` directory; `python -m py_compile`

**Environment & Configuration:** Python 3.9+ with `unittest` stdlib

**Procedure:**
1. Run `python -m py_compile menu.py` — must exit 0.
2. Run any existing tests: `python -m pytest tests/ -v` (or `python -m unittest discover tests/`).
3. Write and run a targeted unit test for: T2 (menu display), T3 (prompt range), T4 (full refresh call order),
   T5 (failure guard), T6 (old key 5 invalid), T7 (key 0 exits), T8 (keys 2/3/4 dispatch).
4. Run `python -m py_compile menu.py` again to confirm idempotency (T9).
5. Run `grep -n "download + transform" context.md` to confirm T10 (zero matches for old string).

**Done Criteria:** All test cases T1–T10 pass; no regressions in existing tests.

**Dependencies:** Tasks 1–4

**Risk Notes:** UAT scenarios require manual verification (see `UAT_scenarios.md`).

---

### Task 6: Update `context.md`

**Intent:** Reflect the new menu action order and revised "Full refresh" scope in the product documentation.

**Inputs:** `context.md` (REF-0001); updated `menu.py`

**Outputs:** `context.md` (two occurrences updated)

**External Interfaces:** None

**Environment & Configuration:** None

**Procedure:**
1. Locate the menu action list in "Functional Capabilities" section (item 5) — update to new order and
   revised "Full refresh" description.
2. Locate the `menu.py` component description in "Component Map" — update the action list from
   `"download only, transform only, full refresh, exit, and update Supabase DB"` to the new order
   and revised full-refresh scope.
3. Verify no other occurrence of the old `"(download + transform)"` menu description remains.

**Done Criteria:** `context.md` accurately describes the new menu; `grep "download + transform"` in
menu-description context returns zero matches.

**Dependencies:** Tasks 1–4

**Risk Notes:** `context.md` is auto-regenerated by `aib-context.md` on next context run; manual edit
here is a forward-record until the next context regeneration.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update menu action descriptions in Functional Capabilities
  (item 5) and Architecture Component Map (`menu.py` entry) to reflect the new action order, revised key
  assignments, and extended "Full refresh" scope (download + transform + update supabase).

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `menu.py` | Modified | Update `print_menu()`, `run_script()` return value, `action_full_refresh()`, and `main()` dispatch table and prompt. |
| `.aib_memory/context.md` | Modified | Update menu action descriptions in Functional Capabilities and Architecture sections. |
| `menu.sh` | Read-only dependency | Launcher invokes `menu.py`; no changes required. |
| `menu.bat` | Read-only dependency | Launcher invokes `menu.py`; no changes required. |
| `src/extract.py` | Read-only dependency | Called by `action_full_refresh()`; no changes. |
| `src/transform.py` | Read-only dependency | Called by `action_full_refresh()`; no changes. |
| `src/load_supabase.py` | Read-only dependency | Called by `action_full_refresh()` (new) and `action_update_supabase()` (unchanged); no changes. |
| `tests/test_config_utils.py` | Read-only dependency | Existing tests not impacted; no menu tests present. |

## Internal Review of Request and Product Docs

- OK: `request.md` — All 12 mandatory sections present in correct order; sections 1–6 are non-empty.

- OK: `request.md § Scope` — Clearly identifies four change points in `menu.py` plus one documentation update.

- OK: `request.md § Constraints` — Failure-propagation constraint is explicit and testable.

- OK: `context.md § Functional Capabilities item 5` — Current description matches current `menu.py` code;
  will require update.

- Ambiguity: `context.md § Component Map (menu.py)` — Lists "full refresh, exit, and update Supabase DB"
  as three of five actions; does not specify action numbers. Minor ambiguity in update scope: both the
  action text and the concept of "full refresh includes Supabase" must be updated.

- OK: `request.md § Success criteria` — SC-7 (old keys invalid) provides a useful regression boundary.
  SC-8 (context.md updated) is deterministic and grep-verifiable.

- Missing info: No `test_menu.py` exists in `tests/`; new targeted tests must be written as part of Task 5.
  This is expected and accounted for in the plan.
