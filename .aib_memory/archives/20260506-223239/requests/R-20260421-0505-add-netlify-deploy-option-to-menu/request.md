## Goal

Add option 5 to the interactive terminal menu (`menu.py`) to deploy the React app (`react-app/`) to Netlify. The option must interactively guide the user through providing the required Netlify deployment parameters (auth token, site ID) with clear instructions on how to acquire each value. If automated CLI-based deployment is not feasible (e.g., Node.js or Netlify CLI not available), option 5 must print step-by-step manual deployment instructions instead.

## Background

The product's React Analytics App (`react-app/`) is designed to be deployed on Netlify (configured via `react-app/netlify.toml`). Currently the menu has four actions (1–4) plus exit (0). Deploying to Netlify requires a manual out-of-band step that is not integrated into the operator workflow. Integrating a deploy option into the menu reduces operator friction and centralises all pipeline actions in one place.

Netlify supports free-tier automated CLI deployments via `netlify-cli` (npm package). A deploy requires a Netlify personal access token (`NETLIFY_AUTH_TOKEN`) and a site ID (`NETLIFY_SITE_ID`). These credentials may be pre-set as environment variables or collected interactively at run time.

If the Netlify CLI is not installed and cannot be invoked via `npx`, the deploy action falls back to printing clear manual instructions (build locally, then drag-and-drop the `dist/` folder in the Netlify dashboard).

## Scope

- Add option `5) Deploy React app to Netlify` to `menu.py`.

- Add `action_deploy_netlify()` function in `menu.py` to orchestrate the deploy flow.

- Create `src/deploy_netlify.py` as the standalone deploy script invoked by `menu.py` action 5; the script: checks for Netlify CLI availability, collects `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` interactively if not set in environment, builds the React app via `npm run build`, and runs `netlify deploy --prod`.

- If Netlify CLI is unavailable, `src/deploy_netlify.py` prints manual deploy instructions.

- Update `print_menu()` in `menu.py` to include option 5 and update the input prompt to `[0-5]`.

- Update the main loop dispatch in `menu.py` to route choice `"5"` to `action_deploy_netlify()`.

- Add automated tests for the new deploy script in the request folder.

- Update `context.md` and editable entries in `references.md` to reflect the new capability.

## Out of scope

- CI/CD pipeline or automatic scheduled deploys.
- Setting up a git repository or Netlify git-integration (no git repo in project).
- Storing credentials persistently between runs (no secrets persistence to disk).
- Netlify CLI installation automation (not permitted to install software unless requested).
- Any changes to the React app source code, Vite config, or `netlify.toml`.
- Any changes to ETL scripts (`src/extract.py`, `src/transform.py`, `src/load_supabase.py`).

## Constraints

- No new third-party Python packages may be installed; only Python 3.9+ stdlib is used in `src/deploy_netlify.py`.
- `menu.py` invokes the deploy script via `subprocess.run` without `capture_output=True` (to allow stdin passthrough for interactive prompts).
- Netlify CLI (`netlify`) is expected to be available on `PATH` or via `npx netlify`; its installation is the operator's responsibility.
- Credentials (`NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`) MUST NOT be stored to disk or written to any config file.
- The deploy action falls back to manual instructions if the CLI is not available.
- All Python code must comply with `coding-general-convention.md` and `coding-python-convention.md`.

## Success criteria

- SC-1: `menu.py` `print_menu()` output includes `5) Deploy React app to Netlify` and the input prompt reads `[0-5]`.
- SC-2: Entering `5` at the menu dispatches to `action_deploy_netlify()` / `src/deploy_netlify.py`.
- SC-3: `src/deploy_netlify.py` detects missing `NETLIFY_AUTH_TOKEN` and prompts the user with clear acquisition instructions before proceeding.
- SC-4: `src/deploy_netlify.py` detects missing `NETLIFY_SITE_ID` and prompts the user with clear acquisition instructions before proceeding.
- SC-5: When Netlify CLI is not available, `src/deploy_netlify.py` prints a clear manual-deploy instruction block.
- SC-6: All new code passes automated unit tests.

## Assumptions

- A1: Node.js and npm are available on the operator's machine (required to build the React app via `npm run build`).
  - Risk if false: Build step will fail; the script must handle this with a clear error message.
- A2: Netlify CLI (`netlify`) may or may not be on `PATH`; the script handles both cases.
  - Risk if false: If no fallback is implemented, the option would crash silently.
- A3: The operator has or can obtain a Netlify account and personal access token via the Netlify dashboard.
  - Risk if false: Deployment cannot proceed; instructions must be sufficient to guide the operator.
- A4: `react-app/netlify.toml` already exists and configures the correct build command and publish directory.
  - Risk if false: Netlify CLI deploy may not use the right directory; the deploy command targets `react-app/dist` explicitly.

## Plan

### Task 1: Create `src/deploy_netlify.py`
**Intent:** Implement the standalone Netlify deploy script that guides the operator through credential collection, builds the React app, and deploys via CLI (or prints manual instructions if CLI is unavailable).
**Inputs:** Environment variables `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`; `react-app/` directory; Netlify CLI on `PATH` or via `npx`.
**Outputs:** `src/deploy_netlify.py` (new file); deploy result or manual instruction text on stdout.
**External Interfaces:** `subprocess` (npm, netlify CLI); stdin for interactive prompts.
**Environment & Configuration:** `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` env vars; Node.js and npm must be installed; Netlify CLI optional (fallback to instructions if missing).
**Procedure:**
1. Check if `netlify` command is on PATH (via `shutil.which`).
2. If not on PATH, check if `npx netlify` is available.
3. If neither available, print manual deploy instructions block and exit.
4. Read `NETLIFY_AUTH_TOKEN` from env; if missing, print acquisition instructions and prompt interactively.
5. Read `NETLIFY_SITE_ID` from env; if missing, print acquisition instructions and prompt interactively.
6. Run `npm run build` inside `react-app/` via subprocess; abort on failure.
7. Run `netlify deploy --prod --dir react-app/dist` with collected credentials in env via subprocess.
**Done Criteria:** Script exits 0 on success; prints clear error and exits non-zero on failure; prints manual instructions when CLI not found.
**Dependencies:** None.
**Risk Notes:** `npx netlify` first-run may prompt for install confirmation; handled by checking exit code.

### Task 2: Update `menu.py`
**Intent:** Add option 5 to the menu display, dispatch, and input prompt.
**Inputs:** `menu.py` (existing); `src/deploy_netlify.py` (from Task 1).
**Outputs:** Updated `menu.py`.
**External Interfaces:** `subprocess.run` to invoke `src/deploy_netlify.py`.
**Environment & Configuration:** None additional.
**Procedure:**
1. Add `5) Deploy React app to Netlify` line to `print_menu()`.
2. Update input prompt from `[0-4]` to `[0-5]`.
3. Add `action_deploy_netlify()` function that invokes `src/deploy_netlify.py` via `subprocess.run` without `capture_output` (stdin/stdout passthrough).
4. Add `elif choice == "5": action_deploy_netlify()` to the main loop.
5. Update `else` branch error message to reflect `0-5` range.
**Done Criteria:** `print_menu()` output contains option 5; choice `"5"` dispatches correctly; `"6"` prints invalid-choice message.
**Dependencies:** Task 1.
**Risk Notes:** None.

### Task 3: Write automated tests
**Intent:** Verify the new deploy script and menu changes with unit tests.
**Inputs:** `src/deploy_netlify.py`, `menu.py`.
**Outputs:** `tests/test_deploy_netlify.py` (new file); test run output.
**External Interfaces:** `unittest`, `unittest.mock`.
**Environment & Configuration:** No credentials or Node.js required for unit tests (all subprocess calls mocked).
**Procedure:**
1. Test that when Netlify CLI not found and `npx` not found, manual instructions are printed and sys.exit(0) is called.
2. Test that when `NETLIFY_AUTH_TOKEN` is missing, the credential prompt function returns the prompted value.
3. Test that when `NETLIFY_SITE_ID` is missing, the credential prompt function returns the prompted value.
4. Test that `print_menu()` output includes `5)`.
5. Run `python -m pytest tests/test_deploy_netlify.py -v`.
**Done Criteria:** All tests pass; `pytest` exits 0.
**Dependencies:** Task 1, Task 2.
**Risk Notes:** None.

### Task 4: Update documentation
**Intent:** Reflect the new Netlify deploy option in `context.md` and `references.md`.
**Inputs:** `context.md`, `references.md`, all prior changes.
**Outputs:** Updated `context.md`.
**External Interfaces:** None.
**Procedure:**
1. Execute `aib-context.md` prompt to fully regenerate `context.md`.
**Done Criteria:** `context.md` references menu option 5 and `src/deploy_netlify.py`.
**Dependencies:** Tasks 1–3.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update to reflect new menu option 5 and `src/deploy_netlify.py` in the architecture and operations sections.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

- `menu.py` — Direct modification: add option 5, update prompt, add action function.
- `src/deploy_netlify.py` — New file.
- `tests/test_deploy_netlify.py` — New file.
- `react-app/netlify.toml` — Read-only reference; no changes needed.
- `react-app/` — Build target; no source changes.

## Internal Review of Request and Product Docs

- Request scope is well-bounded. All ETL scripts, React source, and infra config are explicitly out of scope.
- Success criteria are measurable and testable.
- No credentials stored to disk; security constraint explicit.
- Fallback to manual instructions ensures the option is always useful regardless of CLI availability.
