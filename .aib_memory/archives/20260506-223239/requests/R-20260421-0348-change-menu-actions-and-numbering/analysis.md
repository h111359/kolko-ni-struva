# Analysis — R-20260421-0348: Change menu actions and numbering

---

## Executive Summary

- **Request ID:** R-20260421-0348

- **Title:** Change menu actions and numbering

- **Purpose:** Reorder the interactive terminal menu in `menu.py`, extend "Full refresh" to include the Supabase sync step
  (previously optional/separate), and move "Exit" from key `4` to key `0`. The change is confined to a single Python file
  (`menu.py`) plus a documentation update in `context.md`.

- **Scope summary:** Three internal functions in `menu.py` are affected — `print_menu()` (display), `action_full_refresh()`
  (logic), and `main()` (dispatch + prompt). No shell launchers, ETL scripts, or data artifacts are touched.

- **`request.md` updates in this run:** `## Assumptions`, `## Plan`, `## Documentation`,
  `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` added.
  No `## Questions & Decisions` section generated (all decision points resolved autonomously at threshold 3).

---

## Domain Knowledge Essentials

- **Kolko Ni Struva pipeline** — A Bulgarian government open-data ETL pipeline that downloads retail-price ZIP archives,
  transforms them into a star-schema dataset, and optionally syncs to Supabase. Operators interact with it via an
  interactive terminal menu.

- **Operator** — The primary actor who runs the pipeline. Selects actions from the numbered menu; not expected to remember
  internal script names.

- **Full refresh** — An operator-level concept meaning "bring everything fully up to date." Originally defined as
  download + transform. This request extends it to download + transform + sync to Supabase, making it a true end-to-end
  refresh in the operators' mental model.

- **Exit key convention** — Assigning `0` to "Exit" is a standard Unix terminal-menu convention that places the destructive
  (session-ending) action outside the main numbered action range, reducing the risk of accidentally exiting when intending
  to select a high-numbered action.

- **Impacted roles/personas:** Data engineers and pipeline operators who run the ETL workflow daily.

- **Business process affected:** Interactive pipeline execution workflow. The underlying ETL processes
  (download, transform, Supabase sync) are unchanged; only their menu presentation and grouping change.

---

## Technical Knowledge & Terms

- **`menu.py`** — Single-file interactive terminal menu. Three functions are in scope:
  - `print_menu()`: prints the numbered action lines to stdout; pure presentation.
  - `action_full_refresh()`: calls `run_script()` for extract, transform, and (after this change) load_supabase.
  - `main()`: the REPL loop; reads input, dispatches to action functions, handles keyboard interrupt.

- **`run_script(script_path)`** — Wraps `subprocess.run([sys.executable, script_path], check=True, …)`.
  With `check=True`, a non-zero exit from any script raises `CalledProcessError`, which propagates up through
  `action_full_refresh()` and is caught by the `except` block in `run_script()` itself — printing the error and
  returning (not re-raising). This means `action_full_refresh()` calls are sequential; if extract fails, the
  `run_script()` exception handler prints the error and returns, so the next `run_script()` call in
  `action_full_refresh()` is NOT reached.

  *Correction upon reading the code more closely:* `run_script()` handles `CalledProcessError` internally and does
  NOT re-raise. This means `action_full_refresh()` will continue to the next `run_script()` call even if the
  previous one fails. The `request.md` constraint says "if extract or transform fails, load_supabase.py MUST NOT
  be called." This is an architectural consideration that needs to be addressed in the plan: either
  (a) accept the current behaviour (non-fatal partial run, consistent with existing code), or (b) add a return
  value / exception propagation change to `run_script()`. Given the constraint is stated as a requirement,
  the implementation must ensure `action_full_refresh()` stops on first failure.

- **Subprocess list-form invocation** — `[sys.executable, script_path]` (no `shell=True`). Preserved in all changes.

- **`config.ini`** — State and settings file; untouched by this request.

- **`CalledProcessError`** — Python exception raised by `subprocess.run(check=True)` when the child process exits
  with a non-zero status code.

- **Files Read:**
  - `menu.py` (full content) — source of truth for current menu state.
  - `context.md` (REF-0001) — product documentation; describes current menu actions.
  - `.aib_brain/Concepts.md` (REF-0002) — AIB framework reference.
  - `analysis-convention.md` — normative structure for this document.
  - `request-convention.md` — normative structure for `request.md`.

- **Non-functional attributes:**
  - Performance: no impact — menu startup reads filesystem and config only.
  - Security: no new shell commands or user-input injection vectors; list-form subprocess preserved.
  - Reliability: sequential failure propagation must be verified (see spike below).

---

## Research Results

- **Pattern scan:** Reorganising menu action numbers in a small Python REPL loop is a routine localised change.
  No organisational standard or prior request establishes a canonical menu order; the only established convention
  (from `context.md`) is the list-form subprocess invocation and `no shell=True`. Both are preserved.

- **Failure-propagation gap (current code):** `run_script()` catches `CalledProcessError` internally and does not
  re-raise it. This means the current `action_full_refresh()` (and any future multi-step action) silently continues
  past a failing step. This gap exists today (extract failure does not prevent transform from running). The request
  constraint tightens this by requiring full stop on failure for the extended full-refresh. The implementation plan
  must address this; options include: (a) add a return value to `run_script()` and check it in `action_full_refresh()`;
  (b) re-raise the exception after logging; (c) restructure `action_full_refresh()` to call subprocess directly.
  Option (a) is the least invasive.

---

## External Benchmarking

- **Unix/Linux interactive menu convention (0 = exit):**
  Widely adopted in system-administration CLI menus (e.g., `nmtui`, `raspi-config`, many POSIX tool menus).
  Key takeaway: placing "Exit" at `0` signals to experienced operators that it is intentionally out of the action
  number range, reducing accidental exits. Applicable here without modification.

- **Operational ETL tool menus (e.g., Apache Airflow CLI, Informatica PowerCenter operator consoles):**
  End-to-end pipeline operations are conventionally placed first in numbered menus. Standalone component
  operations (download-only, transform-only) are secondary. This aligns with the requested ordering where
  "Full refresh" is `1`. Adopted directly.

- **Bash/Python REPL menu patterns (open-source ETL boilerplates):**
  Common pattern: top-level actions use a `while True` loop with `input()`, dispatch by string comparison,
  `0` or `q` for exit. Input validation via an `else` branch printing an error message. The existing `menu.py`
  follows this pattern; no structural change needed.

- **Failure propagation in multi-step CLI actions:**
  Standard practice in operational CLIs is to halt the pipeline on first step failure and surface a clear error.
  The current "soft failure" (exception caught internally by `run_script()`) is atypical for multi-step sequences;
  the request constraint to stop on first failure aligns with industry best practice.

---

## Minimal Spikes and Experiments

- **Spike: Failure propagation in `run_script()`**
  - Hypothesis: `run_script()` handles `CalledProcessError` internally without re-raising, meaning a failed step
    does not prevent subsequent `run_script()` calls in the same action function.
  - Approach: Read `run_script()` source in `menu.py` lines 155–182.
  - Outcome: Confirmed. The `except CalledProcessError` block prints the error and returns normally. No re-raise.
    `action_full_refresh()` currently calls `run_script("src/extract.py")` then `run_script("src/transform.py")`
    sequentially without checking the result of the first call.
  - Conclusion: The plan must include a mechanism to stop `action_full_refresh()` on first failure. A return value
    from `run_script()` (returning `True`/`False`) with an early-return guard in `action_full_refresh()` is the
    minimal invasive fix.

- **Spike: Impact of changing `input()` range hint**
  - Hypothesis: The `input()` prompt range hint `"[1-5]"` is purely cosmetic and has no validation logic tied to it.
  - Approach: Read `main()` in `menu.py` lines 210–240.
  - Outcome: Confirmed. The prompt string is a user-facing hint only; the dispatch is handled by `if/elif/else`
    string comparison. Changing to `"[0-4]"` is a one-line cosmetic update with no functional side effects.
  - Conclusion: Safe to change freely.

---

## AI Copilot Suggestions

- **Observation 1 — Silent failure in multi-step actions (implementation risk):**
  The most consequential change in this request is the extension of "Full refresh" to include three sequential
  steps. The current `run_script()` does not propagate failures, so Supabase sync could be skipped silently
  if either extract or transform fails. The fix (returning a boolean from `run_script()` and guarding the
  next call in `action_full_refresh()`) is straightforward and low-risk, but it is a behavioural change beyond
  a pure renaming. The scope in `request.md` does not mention this fix explicitly; the constraint does.
  Recommendation: Confirm this behavioural fix is in scope (it is implied by the constraint) and include it
  as an explicit plan task.

- **Observation 2 — Scope is well-contained; no simplification needed:**
  The request is appropriately scoped. Three function changes in one file plus one documentation update constitute
  the complete delta. There is no over-engineering risk, no abstraction needed, and no cross-module impact.
  Scope is slightly smaller than a typical feature request — this is a positive sign.

- **Observation 3 — Context.md description fidelity (maintainability):**
  `context.md` currently describes "Full refresh" as "(download + transform)" in both the Requirements summary
  and the Architecture section. Both occurrences must be updated. If one is missed, future automated tools
  reading `context.md` will have a stale view of what "Full refresh" does. The plan task for `context.md`
  should explicitly list both occurrences.

- **Observation 4 — `action_full_refresh()` naming remains accurate:**
  The function name `action_full_refresh` continues to be appropriate after the change (it does a full
  end-to-end refresh including cloud). No rename needed.

- **Observation 5 — Test suite impact:**
  The existing `tests/` directory should be checked for any tests that directly test `print_menu()` output,
  the `main()` dispatch table, or the `action_full_refresh()` call sequence. If such tests exist, they will
  need updating. From workspace inspection, `tests/test_config_utils.py` exists but there is no `test_menu.py`.
  No existing tests are broken by this change.

---

## Testing

- T1 — Syntax check: Run `python -m py_compile menu.py`. Expected outcome: exits with code 0, no output.

- T2 — Menu display text: Import `menu` and call `print_menu()` in a test; capture stdout. Expected outcome:
  Line 1 contains `"1) Full refresh"` and `"download + transform + update supabase"`;
  Line 2 contains `"2) Download only"`;
  Line 3 contains `"3) Transform only"`;
  Line 4 contains `"4) Update Supabase DB"`;
  Line 5 contains `"0) Exit"`.

- T3 — Input prompt range hint: Read the source of `main()` via ast or grep. Expected outcome: prompt string
  contains `"[0-4]"` and NOT `"[1-5]"`.

- T4 — Full refresh calls three scripts in order: Mock `run_script` in a unit test; call `action_full_refresh()`;
  assert calls are `["src/extract.py", "src/transform.py", "src/load_supabase.py"]` in that order.
  Expected outcome: assertion passes.

- T5 — Full refresh stops on first failure: Mock `run_script` to return `False` on first call; assert only one
  call is made and load_supabase is not reached. Expected outcome: assertion passes.

- T6 — Old key `5` invalid: In `main()` dispatch, assert that input `"5"` produces the invalid-choice message,
  not a script execution. Expected outcome: output contains "Invalid choice".

- T7 — Key `0` exits cleanly: Supply input `"0"` via stdin mock; assert `main()` returns without error.
  Expected outcome: function returns normally; output contains "Exiting".

- T8 — Keys `2`, `3`, `4` dispatch correctly: Supply each key; assert `run_script` is called with the correct
  script path. Expected outcomes: `"2"` → `src/extract.py`; `"3"` → `src/transform.py`;
  `"4"` → `src/load_supabase.py`.

- T9 — Re-run idempotency of menu.py changes: Run `python -m py_compile menu.py` twice; confirm exit code 0
  both times. Expected outcome: deterministic success.

- T10 — context.md updated: Grep `context.md` for the string `"download + transform"` in the menu description
  context. Expected outcome: zero matches; replaced by `"download + transform + update supabase"` (or equivalent).

*UAT scenarios requiring visual/interactive verification:*

See `UAT_scenarios.md` — UAT-01 (visual menu rendering in terminal), UAT-02 (keyboard interrupt on key `0`).

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

This request introduces a well-bounded, low-complexity change: three function edits in one Python file and one
documentation update. The only architectural nuance is the failure-propagation gap in `run_script()` — currently
a silent soft-fail pattern — which the request constraint requires to be fixed. The fix (boolean return + guard)
is minimally invasive and does not change the function signature in a breaking way. No cross-module interface
is affected. The change is fully reversible.

- The addition of `src/load_supabase.py` to the full-refresh sequence is architecturally coherent with the
  product's intent of having a single "everything up to date" operator action.
- The `run_script()` failure propagation fix should be treated as a correctness fix, not a feature addition.
- No new dependencies, no new modules, no interface contracts to update.
- Risk: If `tests/` grows in future to include `test_menu.py`, the new dispatch table must be reflected there.

### Product Owner

The change directly improves the operator experience by grouping the most common end-to-end operation as
action `1` and using the familiar `0 = exit` convention. "Full refresh" now truly means "everything," removing
the need for operators to remember to also run action `5` manually after a full refresh.

- Business value is clear and immediate: fewer operator steps for the most common workflow.
- Scope is precise; no acceptance criteria are ambiguous.
- Success Criteria SC-1 through SC-8 are well-defined. SC-7 (old keys are invalid) is a useful regression guard.
- No rollout risk beyond re-learning three key assignments for operators.

### User (Operator)

From the operator's perspective, this is a welcome change. "Full refresh" at `1` is the logical first choice
for daily use. Placing "Exit" at `0` follows universal convention and reduces accidental quit events.

- Operators who rely on muscle memory for the old `3`/`4`/`5` assignments will need a brief adjustment period.
- The `[0-4]` prompt hint makes the valid range immediately visible.
- No documentation visible to the operator changes (this is a terminal-only tool).
- Minimal friction: the change is additive in clarity, not in complexity.

### Security Officer

This change introduces no new attack surface. Subprocess invocations remain list-form with `sys.executable`;
no `shell=True` is introduced. The change does not touch authentication, credential handling, or external
network calls. `src/load_supabase.py` already exists as an operator action; moving it into "Full refresh"
does not change its security posture (it still reads `DATABASE_URL` from `.env` via `python-dotenv`).

- No new user-input vectors are created.
- The boolean return from `run_script()` does not expose additional information to callers.
- No permissions, secrets, or environmental variables are affected.
- Low security risk overall.

### Data Governance Officer

Including Supabase sync in "Full refresh" makes the cloud database more likely to receive updates on each
operator run, which improves remote data freshness and lineage consistency. No new data is created or
transformed; the sync mechanism (`src/load_supabase.py`) is unchanged.

- Data lineage is unaffected: the sync still reads from `data/schema/` (local star-schema) and uploads to
  Supabase. Nothing changes in the data flow.
- No new retention or classification obligations arise from a menu reorder.
- Operators who previously ran "Full refresh" without syncing Supabase will now automatically sync —
  this is a policy alignment improvement.
- No compliance impact identified.
