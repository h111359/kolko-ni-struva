## Goal
Update project documentation and operator menu so the website can be tested locally before Netlify deployment.

## Background
The current request asks to align `README.md` with the actual current product state and to explicitly document local website testing before upload to Netlify. It also asks for a new menu action that starts a local web server and opens the site in a browser using a local URL.

## Scope
- Update `README.md` so it reflects the current application state and the real local run workflow for the site.

- Document clear local preview steps for the React app before Netlify deploy, including required prerequisites and commands.

- Add a new action in the interactive menu flow that executes deployment-like local preview (`npm run build && npm run preview`) and prints the local URL.

- Make browser opening best-effort in the new preview action: attempt auto-open, but do not fail the workflow if opening is unavailable.

- Ensure the new menu action integrates with existing menu behavior and does not break current ETL and deploy actions.

## Out of scope
- No changes to ETL data extraction, transformation, or Supabase loading logic.

- No change to Netlify production deployment logic beyond documentation updates.

- No redesign of the React application UI or report behavior.

## Constraints
- Preserve existing cross-platform workflows (Linux and Windows wrappers) unless explicitly required otherwise.

- Keep credentials and secrets handling unchanged; do not expose sensitive values in docs or logs.

- Keep menu behavior deterministic and safe for repeated runs.

- Keep preview behavior resilient in non-GUI/headless terminals by always printing the local URL even if automatic browser opening fails.

- Keep documentation and menu changes aligned with the current repository structure.

## Success criteria
- `README.md` accurately describes the current project architecture and usage flows relevant to local site testing.

- `README.md` includes explicit, runnable local preview steps that allow testing the site before Netlify upload.

- Interactive menu includes a visible option to run local site preview and open the local URL in a browser.

- Existing menu actions continue to work as before after introducing the local preview option.

- Requested documentation and menu updates are verifiable through reproducible commands/tests.

## Assumptions
- A1: The local preview feature is implemented in `menu.py`, while `menu.sh` and `menu.bat` remain thin launchers.
	- Risk if false: cross-platform launcher edits become required and increase regression surface.

- A2: Default preview behavior should be deployment-like (`npm run build && npm run preview`) rather than dev-server mode.
	- Risk if false: pre-deploy validation may diverge from production behavior and reduce release confidence.

- A3: Browser auto-open is best-effort; printing the local URL is sufficient for successful preview in restricted environments.
	- Risk if false: valid terminal-only environments may be treated as false failures.

- A4: Existing menu actions (full refresh, download, transform, Supabase update, Netlify deploy) must preserve current behavior after adding preview.
	- Risk if false: operational regressions could interrupt ETL/deploy workflows.

- A5: `Question threshold` in `.aib_memory/input.md` is parseable and set to level 3 for this analysis run.
	- Risk if false: question-raising behavior could deviate from configured governance rules.

## Plan
### Task 1: Refresh README for Current Product State
**Intent:** Bring README in sync with the current repository behavior and include explicit local preview instructions before deploy.
**Inputs:** `README.md`, `menu.py`, `src/load_supabase.py`, `src/deploy_netlify.py`, `react-app/package.json`.
**Outputs:** Updated `README.md` sections for quick start, menu actions, local preview flow, and deploy prerequisites.
**External Interfaces:** Node/npm and Vite command conventions.
**Environment & Configuration:** Python + Node toolchains; no secret values committed.
**Procedure:** 1) Correct stale menu action descriptions. 2) Add deployment-like local preview instructions. 3) Document browser-open fallback expectation. 4) Ensure commands are runnable as written.
**Done Criteria:** README reflects actual current behavior and pre-deploy local test workflow.
**Dependencies:** None.
**Risk Notes:** Partial edits can leave documentation drift in adjacent sections.

### Task 2: Add Local Preview Action to Menu
**Intent:** Add an operator-facing local preview menu action without breaking existing menu routes.
**Inputs:** `menu.py`, preview decision (build+preview), browser-open fallback rule.
**Outputs:** Updated menu display, action handler, routing branch, and input validation text/range.
**External Interfaces:** Subprocess calls to npm/Vite and OS browser opening API if available.
**Environment & Configuration:** Project root terminal session with `react-app` dependencies installed.
**Procedure:** 1) Add a dedicated action function. 2) Wire choice routing and menu labels. 3) Keep existing options unchanged. 4) Ensure fallback URL output remains available when auto-open fails.
**Done Criteria:** New action is selectable and existing actions preserve behavior.
**Dependencies:** Task 1 (documentation wording alignment).
**Risk Notes:** Menu numbering regressions can cause operator mistakes.

### Task 3: Execute Automated Verification
**Intent:** Validate all testable success criteria through reproducible scripted checks.
**Inputs:** Updated `menu.py`, `README.md`, `tests/test_config_utils.py`, `tests/test_deploy_netlify.py`.
**Outputs:** Command evidence for menu text checks, README content checks, and Python test results.
**External Interfaces:** Local shell, pytest.
**Environment & Configuration:** Activated virtualenv; dependencies installed.
**Procedure:** 1) Run targeted test suite. 2) Verify menu output contains preview option and valid input bounds. 3) Verify README contains expected local preview/deploy guidance. 4) Re-run critical checks for idempotency.
**Done Criteria:** Checks pass and no regressions are detected in existing menu actions.
**Dependencies:** Task 2.
**Risk Notes:** Missing command-level checks can hide integration drift.

### Task 4: Perform Manual UAT for Interactive Behavior
**Intent:** Validate user-interactive behavior that cannot be fully asserted with automation.
**Inputs:** Updated menu runtime flow, request-folder `UAT_scenarios.md`.
**Outputs:** Manual validation of preview launch and browser-open fallback behavior.
**External Interfaces:** Operator terminal and local browser environment.
**Environment & Configuration:** Local machine with or without GUI to verify both normal and fallback paths.
**Procedure:** 1) Execute UAT-01 for interactive preview launch. 2) Execute UAT-02 for fallback behavior in constrained environment. 3) Record outcomes in implementation evidence.
**Done Criteria:** Manual checks confirm URL visibility and non-failing fallback behavior.
**Dependencies:** Task 2.
**Risk Notes:** Skipping UAT leaves key UX acceptance unverified.

### Task 5: Synchronize Product Documentation Registry Artifacts
**Intent:** Keep editable product docs aligned with implemented behavior and this request outcome.
**Inputs:** `.aib_memory/context.md`, `.aib_memory/references.md`, implemented deltas.
**Outputs:** Updated context narrative and reconciled editable reference docs.
**External Interfaces:** None.
**Environment & Configuration:** Documentation update workflow only.
**Procedure:** 1) Reflect local preview menu behavior in context.md. 2) Validate editable reference entries remain accurate. 3) Record any discrepancy resolution.
**Done Criteria:** Product-doc references match actual code and README behavior.
**Dependencies:** Tasks 1-4.
**Risk Notes:** Unsynced docs degrade future analysis quality.

## Documentation
- README.md (ref_id: N/A) — Must be updated to reflect current application state and include explicit local preview steps before Netlify deploy.

- .aib_memory/context.md (ref_id: REF-0001) — Must reflect any finalized menu/local-preview behavior changes to keep product-doc context synchronized.

## Questions & Decisions
No open questions.

Applied decisions:
- D1: Local preview defaults to `npm run build && npm run preview` for deployment-like validation.
- D2: Browser opening is best-effort; the local URL is always printed and workflow continues on open failure.

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| README.md | Modified | Requested to reflect current product state and local preview workflow before Netlify deployment. |
| menu.py | Modified | Requested new menu option for local server preview and browser access through local URL. |
| menu.sh | Read-only dependency | Launcher behavior depends on `menu.py` changes but likely does not require direct modification. |
| menu.bat | Read-only dependency | Launcher behavior depends on `menu.py` changes but likely does not require direct modification. |
| react-app/package.json | Read-only dependency | Defines available local server scripts (`dev`, `preview`) used by menu action design. |
| .aib_memory/context.md | Modified | Editable product-doc reference should be synchronized after behavior changes. |

## Internal Review of Request and Product Docs
- OK: `request.md` mandatory sections are present and non-empty for Goal through Success criteria.

- OK: Preview mode ambiguity is resolved by applied decision D1 (deployment-like preview default).

- OK: Browser-open behavior ambiguity is resolved by applied decision D2 (best-effort open with URL fallback).

- Cross-ref issue: `README.md` menu documentation is stale relative to current `menu.py` actions, confirming request validity.
