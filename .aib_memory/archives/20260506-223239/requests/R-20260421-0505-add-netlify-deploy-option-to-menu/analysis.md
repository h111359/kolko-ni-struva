# Analysis: R-20260421-0505 — Add Netlify Deploy Option to Menu

## Executive Summary

- **Request ID:** R-20260421-0505
- **Request title:** Add Netlify deploy option to menu

- **High-level purpose:** Integrate a Netlify deployment action as option 5 in the interactive terminal menu (`menu.py`), enabling operators to build and deploy the React Analytics App to Netlify without leaving the pipeline tooling. The option must guide the user through acquiring and providing the required credentials, and must fall back to clear manual instructions when the Netlify CLI is unavailable.

- **Scope:** Two source files affected — `menu.py` (modified) and `src/deploy_netlify.py` (new). Tests added under `tests/`. Documentation updated via `aib-context.md`.

- **`request.md` updates in this run:** Sections `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` were populated.

- **Key risk:** Netlify CLI unavailability on operator machine; mitigated by the manual-instructions fallback path.

- **Key constraint:** No new Python packages; only stdlib used in `src/deploy_netlify.py`. Credentials must not be persisted to disk.

---

## Domain Knowledge Essentials

**Kolko Ni Struva (Колко Ни Струва):** Bulgarian government initiative requiring retailers to report daily prices; the product pipeline collects and exposes this data.

**Operator:** The data engineer or analyst who runs the pipeline locally. They use `menu.py` as the primary control interface.

**Netlify:** A US-based web hosting and CI/CD platform. Free tier ("Starter") supports unlimited manual deploys via both the web UI (drag-and-drop) and the Netlify CLI. No git repository is required for CLI or web deploys.

**Manual deploy (Netlify):** Uploading a production build artefact (a compiled `dist/` folder) to Netlify without an attached git repository. Supported on all Netlify tiers, including the free tier.

**Personal access token (Netlify):** A bearer token generated in the Netlify dashboard under User Settings → Applications → Personal access tokens. Used to authenticate CLI operations. Scoped to the user account, not to a specific site.

**Site ID (Netlify):** A UUID assigned to each Netlify site, visible in Site settings → General → Site details. Used by the CLI to target the correct site for deploy.

**Impacted roles/personas:**
- Operator: primary user of the menu; benefits from not needing to remember Netlify CLI syntax.

**Business process touched:** React app deployment (previously a manual out-of-band step).

---

## Technical Knowledge & Terms

**Technologies involved:**
- Python 3.9+ / stdlib (`subprocess`, `shutil`, `os`, `sys`) — used in `src/deploy_netlify.py`.
- Netlify CLI (`netlify-cli`) — npm package; invoked via `netlify deploy --prod --dir <dir>`.
- Node.js / npm — required to run `npm run build` in `react-app/`.
- React + Vite — SPA build tool; `npm run build` produces `react-app/dist/`.
- `menu.py` — existing interactive terminal menu written in Python.

**Key terms:**
- `NETLIFY_AUTH_TOKEN`: environment variable for Netlify personal access token; recognised natively by the Netlify CLI.
- `NETLIFY_SITE_ID`: environment variable for the target Netlify site UUID; recognised natively by the Netlify CLI.
- `shutil.which`: Python stdlib function that resolves a command name to its PATH location, or returns `None` if not found.
- `subprocess.run`: Python stdlib function for spawning child processes; used without `capture_output` to allow stdin/stdout passthrough for interactive prompts.
- `npx`: Node.js package runner; can invoke `netlify` without a global install.

**Files read during analysis:**
- `.aib_memory/context.md`
- `.aib_memory/references.md`
- `menu.py`
- `react-app/netlify.toml`
- `.aib_brain/Concepts.md`

**Non-functional attributes:**
- Security: credentials collected via `input()` and passed in subprocess env; never written to disk.
- Reliability: graceful fallback to manual instructions when CLI absent.
- Compatibility: Python 3.9+; no new dependencies.

**Evidence log:**
- `menu.py` uses `subprocess.run([sys.executable, ...], check=True, capture_output=True)` for ETL scripts → implementation must use a different call (no `capture_output`) for the interactive deploy script.
- `react-app/netlify.toml` sets `publish = "dist"` and `command = "npm run build"` → deploy CLI command should target `react-app/dist`.
- Netlify CLI recognises `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` environment variables natively → credentials can be injected cleanly via `env` parameter of `subprocess.run`.

---

## Research Results

**Pattern scan:**
- Existing menu actions follow a `run_script(path) -> bool` pattern with `capture_output=True`. The deploy action requires stdin passthrough for interactive credential collection; a direct `subprocess.run` call (no `capture_output`) is the established Python pattern for interactive child processes.
- Environment variable injection via `subprocess.run(env=...)` is the standard pattern for passing secrets to child processes without exposing them through command-line arguments (which are visible in `ps` output).
- The `shutil.which` + `npx` two-step availability check is the standard pattern for optional tool detection in Python scripts.

---

## External Benchmarking

**Netlify CLI automated deploy (free tier):**
- The Netlify Starter (free) tier fully supports manual deploys via the CLI with `netlify deploy --prod`. No paid subscription is required. This is documented in Netlify's official CLI reference. Takeaway: automated deploy via CLI is viable at no cost; the "manual instructions fallback" is a usability safety net, not a tier-limitation workaround.
  - Assessment: adopt CLI deploy as the primary path.

**Python interactive credential collection patterns:**
- Industry-standard CLIs (AWS CLI, Heroku CLI, Firebase CLI) collect missing credentials interactively using prompts with instructional text. The `getpass` module is used for password-like inputs to prevent terminal echo; for tokens (which operators paste from a dashboard), plain `input()` is acceptable because the value is not a password and echo aids verification. Takeaway: plain `input()` with instructional prefix is appropriate for Netlify tokens.
  - Assessment: adopt plain `input()` with clear instructional text; do not use `getpass` (tokens are long alphanumeric strings not sensitive in the same way as passwords, and operators benefit from seeing what they pasted).

---

## Minimal Spikes and Experiments

**Spike 1 — Netlify CLI env var contract:**
- Confirmed via Netlify CLI documentation: setting `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` in the process environment is the documented, stable method for non-interactive CLI authentication. No additional flags required.
- Implication: the deploy script can pass credentials via `subprocess.run(env={...})` with no CLI flag arguments.

**Spike 2 — subprocess stdin passthrough:**
- `subprocess.run(cmd)` without `capture_output=True` inherits the parent's stdin/stdout/stderr by default in Python 3.9+. This means interactive prompts from the child process are shown in the terminal. Confirmed: this is the correct approach for `src/deploy_netlify.py`.

---

## AI Copilot Suggestions

1. **Credential acquisition instructions quality (usability risk):** The instructions shown to the operator before each `input()` prompt are the primary UX surface. Vague instructions (e.g., "enter your token") will frustrate first-time operators. The instructions must include the exact navigation path in the Netlify dashboard (e.g., User Settings → Applications → Personal access tokens → New access token) and explain what the token is used for. Same for Site ID. Suggestion: embed numbered step-by-step instructions as multi-line strings in the prompt text.

2. **`npx netlify` first-run confirmation prompt (integration risk):** On machines where `netlify-cli` is not globally installed, `npx netlify <args>` may print "Need to install the following packages: netlify@X.X.X — Ok to proceed?" and wait for input, interrupting the deploy flow. This could confuse operators. Suggestion: consider checking for the global `netlify` binary only (via `shutil.which('netlify')`) and if absent, fall back directly to manual instructions rather than attempting `npx`. This reduces complexity and avoids the `npx` confirmation UX issue. Alternatively, run `npx --yes netlify` but this auto-installs without consent.

3. **Scope appears right-sized:** The request is well-bounded. Adding a deploy action to the menu without touching the React app source, ETL scripts, or Netlify configuration is a minimal, reversible change. However, there is a simplification opportunity: since `src/deploy_netlify.py` is the only consumer of the deploy logic and it has interactive I/O, the implementation could live directly in `menu.py` as an `action_deploy_netlify()` function rather than a separate script — this avoids the subprocess indirection. However, keeping it as a separate script maintains consistency with the existing pattern and keeps `menu.py` focused on dispatch only. Either approach is valid.

---

## Testing

- T1 — Manual instructions fallback: When neither `netlify` binary nor `npx` is on PATH, `deploy_netlify.py` prints the manual instructions block and exits 0. Expected outcome: stdout contains "Manual deploy instructions" heading and process exits with code 0.
- T2 — Auth token prompt: When `NETLIFY_AUTH_TOKEN` is not set in env, the `get_credential()` helper prints acquisition instructions and reads from stdin. Expected outcome: mocked `input()` returns the test value; function returns that value without raising.
- T3 — Site ID prompt: When `NETLIFY_SITE_ID` is not set in env, the helper prints acquisition instructions and reads from stdin. Expected outcome: mocked `input()` returns the test value; function returns that value.
- T4 — Menu option 5 present: `print_menu()` output includes the string `5)`. Expected outcome: `"5)"` appears in captured stdout.
- T5 — Menu invalid choice: Entering `"6"` at the main loop prints the invalid-choice message. Expected outcome: message contains the string "Invalid choice".
- See UAT_scenarios.md — UAT-01 (end-to-end deploy with live Netlify credentials).

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect
The request introduces a thin orchestration wrapper over the Netlify CLI. Architecturally, keeping `src/deploy_netlify.py` as a separate script (rather than embedding deploy logic in `menu.py`) maintains the single-responsibility principle and keeps `menu.py` as a pure dispatch layer — consistent with the existing pattern. The use of stdlib-only (`subprocess`, `shutil`, `os`) is appropriate and avoids dependency creep. The credential-in-env injection pattern is idiomatic and avoids shell-injection risk. One architectural concern: the deploy script builds the React app internally (`npm run build`) — this couples a frontend build step to a Python script, which may be surprising. However, given the product's scope (no CI/CD, single operator), this coupling is acceptable and reduces operator steps.

- No new runtime dependencies introduced.
- Credential injection via subprocess env is secure and idiomatic.
- Fallback to manual instructions makes the option resilient to environment variation.
- `npm run build` coupling in a Python script is pragmatic for this scope.
- No architectural debt introduced.

### Product Owner
This change addresses a real operator friction point: deploying the React app requires manually remembering Netlify CLI syntax and credential management. Integrating it into the existing menu centralises all pipeline actions. The fallback to manual instructions ensures the option has value even in environments where the CLI is not installed.

- Business value is clear and directly usable by the operator.
- Scope is minimal; no risk of scope creep.
- The interactive credential prompt with instructions is a good UX pattern for a CLI tool.
- The "manual instructions" fallback is a good degraded-mode UX.
- Success criteria are testable and aligned with the stated goal.

### User (Operator)
As the operator, I currently have to open a separate terminal, remember the `netlify` CLI syntax, set environment variables, and run the build manually. Having option 5 in the existing menu I already use is convenient. The credential prompts with step-by-step instructions are helpful for first-time setup. The fallback instructions are useful when running on a machine without the CLI.

- Reduces context-switching for deploy operations.
- Instructional prompts lower the barrier for first-time Netlify users.
- The build step being included in the deploy action eliminates a common mistake (deploying stale `dist/`).
- If Node.js is not installed, the build will fail with an error; the error message should be clear.

### Security Officer
The credential handling approach (read from env or prompt, pass via subprocess env, never write to disk) is correct. The tokens are not echoed to log files. No credentials are stored in `config.ini` or any other persistent file. The subprocess call uses list form (no shell=True), preventing shell injection. The tokens are only in memory for the duration of the deploy script.

- No credentials written to disk — compliant.
- Subprocess list form — no shell injection risk.
- Tokens visible in process environment during subprocess lifetime — acceptable risk given local single-operator use.
- User should be advised not to commit `.env` or config files with embedded tokens — already addressed by existing `.gitignore` conventions (no git repo currently).
- No new attack surface introduced.

### Data Governance Officer
This change affects only the deployment mechanism for the React app, which is a public-access visualisation layer over publicly available government data. No PII is processed. The deploy action does not alter the data pipeline or the data stored in Supabase. The change has no data lineage, retention, or classification impact.

- No data lineage impact.
- No new data retention requirements.
- No PII or classified data involved.
- Netlify deployment does not change the data access model (anon key, public SELECT RLS).
- No compliance impact.
