# Analysis: R-20260426-2150 — Fix option 6 data loading and improve test coverage

## Executive Summary

- **Request ID:** R-20260426-2150

- **Request title:** Fix option 6 data loading and improve test coverage

- **High-level purpose:** Diagnose and fix the root cause of menu option 6 (local React preview) failing to display Supabase data in the browser, despite the previous fix (R-20260425-2313) adding a pre-build credential check. Extend the automated test suite to ensure this class of bug cannot recur.

- **Root cause identified:** `webbrowser.open(PREVIEW_URL)` is called **before** `subprocess.run(["npm", "run", "preview"], ...)` starts the local server. The browser opens to `http://localhost:4173` while the Vite preview server has not yet bound to that port, resulting in "connection refused." The operator sees no data because the browser never successfully loaded the React app — it got an error page instead.

- **Why tests didn't catch it:** The existing `TestMenuOption6` tests in `test_deploy_netlify.py` only assert menu dispatch (that entering "6" calls `action_local_preview()`). They do not verify the internal behavior of `action_local_preview()` — specifically the call order of subprocess launch vs. browser open, nor the credential validation paths. The `action_local_preview()` function has zero internal unit test coverage.

- **Secondary finding:** The `VITE_SUPABASE_ANON_KEY` value in the project's root `.env` file is a **service_role** JWT (the decoded payload contains `"role":"service_role"`), while the established convention and `context.md` explicitly require an anon key. This is a critical security issue: the service_role key is embedded in the React bundle and exposed publicly, bypassing all Supabase Row Level Security policies.

- **Sections added/updated in `request.md` during this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.

---

## Domain Knowledge Essentials

- **Kolko Ni Struva ETL pipeline:** Python-based pipeline that downloads, transforms, and loads Bulgarian government retail-price open data into a Supabase-hosted star-schema database. The pipeline is controlled via an interactive terminal menu (`menu.py`).

- **Menu option 6 (local preview):** Invokes `action_local_preview()` in `menu.py`. Intended workflow: validate VITE_ credentials → build React app (`npm run build`) → start Vite preview server (`npm run preview`) → open browser at `http://localhost:4173`. The preview serves the production-built bundle locally, simulating the Netlify deployment.

- **Vite preview server:** A lightweight HTTP server (`vite preview`) that serves the previously built `react-app/dist/` directory. Default port: 4173. Distinct from the Vite dev server (port 5173). Starts asynchronously from the operator's perspective — it takes 1–3 seconds to bind to the port before serving requests.

- **VITE_ environment variables:** Vite exposes `VITE_`-prefixed variables from `.env` files (specified by `envDir` config) as `import.meta.env.VITE_*` in the client bundle. These values are **inlined at build time** — the preview server does not re-read `.env`. If credentials are missing at build time, the bundle contains empty strings; if credentials are present, the bundle contains the actual values.

- **Supabase anon key vs. service_role key:** The anon key is a public, restricted JWT intended for client-side use; it respects Row Level Security (RLS) policies. The service_role key is a privileged, admin-level JWT that bypasses all RLS; it must never be exposed in client-side code or public repositories.

- **Race condition:** A concurrency defect where a program assumes a resource is ready before it actually is. In this case: the code assumes the Vite preview server is listening on port 4173 at the moment `webbrowser.open()` is called, but the server hasn't been started yet.

- **Impacted persona:** Data engineer / operator using the interactive terminal menu to preview the React app before a production deploy.

---

## Technical Knowledge & Terms

- **`action_local_preview()` (`menu.py`):** Function responsible for the entire option 6 flow: load `.env`, validate VITE_ vars, run `npm run build`, call `webbrowser.open()`, run `npm run preview`. Key defect: browser open call precedes server start call.

- **`subprocess.run(...)` (Python):** Blocking call — it waits for the spawned process to complete before the calling code continues. `subprocess.run(["npm", "run", "build"], ...)` blocks until the build finishes. `subprocess.run(["npm", "run", "preview"], ...)` blocks until the server process exits (i.e., until Ctrl+C). The browser open call between these two is the race.

- **`webbrowser.open(url)` (Python):** Requests the OS to open the given URL in the default browser. It returns immediately (non-blocking). If the target server is not listening when the OS makes the HTTP request, the browser shows "Connection refused" or equivalent.

- **`envDir: '../'` (vite.config.js):** Directs Vite to load `.env` files from the parent of the Vite config's root directory (`react-app/`), i.e., the project root. This is correctly configured; Vite finds and reads `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` from the root `.env` at build time.

- **`credentialsError` (supabase.js):** Module-level constant in `react-app/src/lib/supabase.js`. Set to a Bulgarian error string if either `VITE_SUPABASE_URL` or `VITE_SUPABASE_ANON_KEY` is falsy in the built bundle. App.jsx uses `credentialsError` to short-circuit the dimension-loading `useEffect` and display an error message.

- **`TestMenuOption6` class (`tests/test_deploy_netlify.py`):** Existing tests that verify menu wiring (dispatch) but not the internal behavior of `action_local_preview()`. These tests mock `action_local_preview` entirely, so the race condition and credential validation logic inside the function are never exercised.

- **Service_role JWT:** Supabase JWT with `"role":"service_role"` in the payload. Detectable by base64-decoding the payload segment. Unlike the anon key, the service_role key bypasses RLS, allowing unrestricted database access.

- **Files read during analysis:** `menu.py`, `react-app/src/lib/supabase.js`, `react-app/src/lib/dataService.js`, `react-app/src/App.jsx`, `react-app/vite.config.js`, `react-app/package.json`, `tests/test_deploy_netlify.py`, `.aib_memory/context.md`, `.aib_memory/requests/R-20260425-2313-.../request.md`, `.aib_memory/requests/R-20260425-2313-.../implementation.md`.

- **Evidence log:**
  - `webbrowser.open(PREVIEW_URL)` appears on the line immediately before `subprocess.run(["npm", "run", "preview"])` → confirms the race condition exists in source.
  - `envDir: '../'` in `vite.config.js` → confirms Vite reads `.env` from project root; credentials should be correctly embedded.
  - VITE_SUPABASE_ANON_KEY JWT payload `"role":"service_role"` → confirms the wrong key type is configured.
  - `TestMenuOption6` uses `patch.object(menu, "action_local_preview")` → confirms the internal function behavior is not tested.

---

## Research Results

1. **Pattern scan against prior workspace solutions:** Previous request R-20260425-2313 identified "missing VITE_ credentials" (A1) as the root cause of option 6 data failure and addressed it by adding a pre-build credential check. Assumption A1 stated "Risk if false: The failure has a different root cause." The current analysis confirms A1 was false for the persistent symptom: credentials ARE present; the actual defect is the browser/server ordering. The prior fix was a partial fix — it prevents the failure mode of missing credentials, but not the race condition.

2. **Pattern scan against testing conventions:** The `test_deploy_netlify.py` file conflates deploy tests with menu dispatch tests. The naming convention (`test_deploy_netlify.py` ≠ `test_menu.py`) and the scope of `TestMenuOption6` (dispatch-only) indicate that `action_local_preview()` internals were explicitly not in scope during R-20260425-2313, which focused on a specific set of identified gaps. This created a blind spot.

3. **Pattern scan against security convention:** `context.md` explicitly states "Supabase anon key only; no service role key" as a non-functional requirement. The current `.env` violates this requirement. The service_role key being used as `VITE_SUPABASE_ANON_KEY` means it is baked into the React bundle served publicly, contradicting both the stated requirement and sound security practice.

---

## External Benchmarking

- **Electron-style preload pattern (server-ready detection):** A widely used pattern in desktop and local-server apps is to start the server process, poll the target port until it accepts TCP connections (e.g., using `socket.create_connection`), and only then open the browser. This avoids the fixed-sleep anti-pattern and is reproducibly reliable across OS environments. Adoption: this pattern is appropriate and should be applied to `action_local_preview()`. It requires adding a TCP readiness poll loop between server start and browser open.
  - Takeaway: poll-then-open is a production-standard pattern for local dev server tooling.
  - Applicability: direct adoption; no adaptation needed beyond Python socket API usage.

- **Vite CLI `--open` flag:** Vite's own CLI provides a `--open` flag for `vite dev` and `vite preview` that opens the browser **after** the server is ready. This is implemented by Vite internally using a server-ready hook. For use from `menu.py`, this would mean passing `--open` to `npm run preview` instead of calling `webbrowser.open()` separately. This is the simplest possible fix.
  - Takeaway: `vite preview --open` is the idiomatic solution when using Vite CLI directly.
  - Applicability: highly applicable; adopting this approach removes the Python-side browser-open call entirely, eliminating the race condition at the source. The `PREVIEW_URL` print statement can be retained for operator visibility.

- **Python `subprocess.Popen` with readiness polling (e.g., FastAPI local dev scripts):** Open-source FastAPI and Django management scripts use `subprocess.Popen` (non-blocking) to start the server, then poll with `socket.connect_ex` or `http.client`, and finally open the browser. This approach is more portable than the `--open` flag, avoids Vite internals, and allows explicit control from Python.
  - Takeaway: `Popen` + poll is the correct Python-side approach when the server start must be managed by the orchestrating script.
  - Applicability: applicable as an alternative to the `--open` flag if the Vite-side solution is not preferred.

---

## Minimal Spikes and Experiments

- **Spike: Verify that `webbrowser.open` precedes `subprocess.run("npm run preview")`**
  - Hypothesis: The race condition is present in the current source.
  - Approach: Read `action_local_preview()` in `menu.py` and inspect the call order.
  - Outcome: Confirmed. `webbrowser.open(PREVIEW_URL)` appears on line ~330 (after the build block), followed by `subprocess.run(["npm", "run", "preview"], cwd=REACT_DIR)` on ~337.
  - Conclusion: The race condition is a confirmed source-level defect.

- **Spike: Verify Vite `envDir` configuration correctly points to project root**
  - Hypothesis: `envDir: '../'` in `react-app/vite.config.js` resolves to the project root where `.env` lives.
  - Approach: Read `react-app/vite.config.js` and verify the `envDir` value; cross-reference with the `.env` file location.
  - Outcome: `envDir: '../'` is set. The `.env` file is at project root. From `react-app/`, `'../'` = project root. Vite docs confirm `envDir` is relative to the Vite root (directory of vite.config.js).
  - Conclusion: Credentials are correctly embedded at build time. The "no data" symptom is not caused by missing credentials in the bundle.

- **Spike: Detect service_role vs. anon key in `.env`**
  - Hypothesis: The `VITE_SUPABASE_ANON_KEY` in `.env` may be the wrong key type.
  - Approach: Base64-decode the JWT payload segment from the `.env` value.
  - Outcome: Decoded payload contains `"role":"service_role"`, not `"role":"anon"`. The configured key is the service_role key.
  - Conclusion: A critical security misconfiguration exists. The service_role key must be replaced with the anon key from the Supabase project dashboard.

---

## AI Copilot Suggestions

- **Scope appears correct.** The request targets a well-defined, persistent bug (race condition + test gap) and requests documentation updates. It does not over-specify the implementation. Scope is appropriate.

- **Observation 1 (Design quality — server readiness): The two-step "print URL, then open browser, then start server" design in `action_local_preview` is fundamentally inverted.** The browser open should be the LAST step after the server is confirmed ready, not a best-effort call in between. This design error was introduced during R-20260421-0348 or R-20260425-2155 and was not identified during R-20260425-2313 because the root cause was misattributed to credentials. The recommended fix (using `vite preview --open` or a Popen + port-polling approach) eliminates the race at the design level rather than patching it.

- **Observation 2 (Security — service_role key in public bundle): Using the service_role key as the anon key is a critical, production-blocking security defect.** Anyone who can view the browser's JavaScript source can extract this key and gain unrestricted access to the entire Supabase database, bypassing all RLS policies. This must be remedied before the next Netlify deployment: the anon key (labeled "anon public" in the Supabase dashboard API settings) must replace the service_role key in `.env`. The service_role key should be considered compromised and rotated immediately in the Supabase dashboard. This security fix is tightly coupled to this request (it affects the local preview's Supabase connectivity) and should be included in scope.

- **Observation 3 (Testability — `action_local_preview` is inherently hard to unit-test as designed): The function mixes credential I/O, build subprocess, browser subprocess, and server subprocess into one function with no injection points.** This makes it impossible to assert call order in tests without heavy patching. A structural improvement (even a minimal one: extract a `_start_preview_and_open_browser(react_dir, preview_url)` helper) would make the ordering testable with a simple mock-call-order assertion. The new tests should at minimum verify: (a) build is called before preview, (b) browser is opened after server starts, (c) early return occurs when credentials are absent.

- **Observation 4 (Maintainability — `TestMenuOption6` in wrong file): The option-6 tests live in `test_deploy_netlify.py`, which primarily covers `src/deploy_netlify.py`.** This is a naming and organizational issue. A `test_menu.py` file covering all menu actions (including `action_local_preview`) would be more maintainable and make coverage gaps easier to detect. New tests for `action_local_preview` should be placed in a new `tests/test_menu.py`.

---

## Testing

- T1 — action_local_preview missing credentials returns early: Call `action_local_preview()` with `VITE_SUPABASE_URL` and/or `VITE_SUPABASE_ANON_KEY` absent from `os.environ`; mock `load_dotenv` to no-op and `subprocess.run`. Expected outcome: function returns without calling any subprocess; an error message containing the missing variable name is printed to stdout.

- T2 — action_local_preview build step called before preview step: Call `action_local_preview()` with valid mocked credentials; mock `subprocess.run` and `webbrowser.open`. Expected outcome: the `npm run build` subprocess call precedes the preview server start; assertions on mock call order pass.

- T3 — action_local_preview server start before browser open: Call `action_local_preview()` with valid mocked credentials; verify via mock call order that browser open occurs only after the preview server start is initiated. Expected outcome: mock call order shows build → server start → browser open.

- T4 — action_local_preview build failure causes early return: Call `action_local_preview()` where the `npm run build` mock raises `subprocess.CalledProcessError`. Expected outcome: function returns early; preview server subprocess is not called; error message is printed.

- T5 — action_local_preview npm not found causes early return: Call `action_local_preview()` where the `npm run build` mock raises `FileNotFoundError`. Expected outcome: function returns early; error message containing "npm not found" or equivalent is printed.

- T6 — count_zips, zip_date_range, count_fact_files, schema_freshness with empty directory: Call each stats helper on a temporary empty directory. Expected outcome: correct zero/default values returned.

- T7 — read_state with missing config file: Call `read_state()` with a path that does not exist. Expected outcome: returns `("", "")`.

- T8 — main loop dispatches all choices 1–6 and 0: Drive `main()` with sequential inputs ["1","2","3","4","5","6","0"]; mock all action functions and stats helpers. Expected outcome: each action function called once; exit on "0".

- T9 — React App renders without crashing when credentialsError is non-null: Render `App` with `credentialsError` set to a non-null string (simulated missing credentials). Expected outcome: error message text is visible; dimension fetch is not initiated (no Supabase calls). See UAT_scenarios.md — UAT-01.

- T10 — React App shows loading state then renders date selector after dimension fetch: Render `App` with mocked `fetchDimensions` that resolves to a stub dims object. Expected outcome: date selector becomes populated with at least one option; no error message is shown.

- T11 — vite preview --open (or Popen + poll) eliminates race: If `--open` flag approach is adopted, verify via `npm run test` that the build still exits 0; if Popen+poll is adopted, verify the poll loop correctly detects the port becoming available. Expected outcome: option 6 integration test passes; no timeout occurs within 30-second bound. See UAT_scenarios.md — UAT-02.

- T12 — service_role key replaced by anon key: Decode the `VITE_SUPABASE_ANON_KEY` JWT in `.env` and assert the payload contains `"role":"anon"`. Expected outcome: assertion passes, confirming the key type is correct. (This is a configuration verification test, not a code test.)

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The race condition between `webbrowser.open()` and `subprocess.run(["npm", "run", "preview"])` is a straightforward but impactful ordering defect. The architectural fix options (Vite `--open` flag or `Popen` + TCP poll) are both well-established patterns with clear trade-offs: the `--open` flag delegates browser management to Vite (simpler, less Python code) while the `Popen` approach keeps full control in Python (more testable, more portable). The absence of `test_menu.py` is a structural gap: `action_local_preview()` is the most complex function in `menu.py` and deserved its own test file. The service_role key in the bundle is an architectural security violation that invalidates the "anon key only" constraint and must be remediated as a blocking fix.

- Race condition is a design-level defect, not a cosmetic bug — it requires structural remediation, not a workaround.
- The `--open` flag approach is preferred: fewer moving parts, idiomatic Vite usage, removes the Python-side browser open call entirely.
- A new `tests/test_menu.py` is the correct deliverable; shoe-horning option-6 tests into `test_deploy_netlify.py` was a scope artifact of the previous request.
- Service_role key rotation must be treated as a production-blocking blocker independent of this bug.

### Product Owner

The persistent failure of option 6 undermines operator confidence in the local preview workflow and delays production deployments (operators cannot validate locally). The previous fix (R-20260425-2313) was well-intentioned but addressed a different symptom, leaving the root cause unresolved. The success criteria in this request are measurable and aligned with the product's non-functional requirements.

- Business value is clear: restoring the local preview workflow is directly on the critical path to confident production deploys.
- The security finding (service_role key) is a production-blocking risk that should be escalated immediately; it was not addressed in prior requests.
- Scope is appropriately narrow; the request does not introduce new features.
- The test coverage requirement ("all should be caught by the tests") is a strong, defensible success criterion.

### User

The operator selects option 6 expecting to see the React app with real Supabase data in the browser. Instead, the browser opens to an error page or blank state, requiring either a manual refresh or recognition that the timing is off. This is confusing and friction-inducing. After the fix, the operator should see the browser open to a fully loaded app with no manual steps required.

- The current UX is: "select 6 → browser errors → manually wait and refresh → maybe data loads." Post-fix expectation: "select 6 → wait for build → browser opens → data is loaded."
- The operator has no way to know whether the blank/error state is caused by a race, missing credentials, or a Supabase issue. Better error messaging and reliable sequencing would both reduce friction.
- The security key issue is invisible to the operator unless they inspect the JS bundle; the fix (rotating to anon key) has zero UX impact.

### Security Officer

The `VITE_SUPABASE_ANON_KEY` being set to a service_role JWT is a **Critical (Level 5)** finding. The service_role key, once embedded in the React bundle, is publicly accessible to anyone who loads the production Netlify deployment. An attacker can extract the key from the JavaScript source and use it to perform unrestricted read/write/delete operations on all Supabase tables, bypassing every RLS policy. The key must be rotated immediately in the Supabase dashboard, and the anon key (not the service_role key) must be placed in `.env`. Until rotation, the production deployment at Netlify exposes the entire database to arbitrary manipulation.

- Critical risk: service_role key in public bundle bypasses ALL RLS — treat as active breach risk until rotated.
- Rotation of the compromised service_role key in Supabase dashboard is mandatory and urgent.
- No security impact from the race condition or test gaps beyond the key exposure.
- Recommend adding a CI guard (e.g., a test that decodes `VITE_SUPABASE_ANON_KEY` and asserts `role == "anon"`) to prevent future key misconfiguration.

### Data Governance Officer

The service_role key in the React bundle grants public read access to all Supabase tables, including any personally identifiable data or business-sensitive pricing data. While the current dataset (Bulgarian government retail prices) is public domain, the unrestricted write access via service_role could allow malicious data injection that corrupts the star-schema. Data lineage is not at risk from the race condition or test gaps themselves. Documentation updates (context.md) should accurately reflect the corrected key type after remediation.

- Data integrity risk: service_role key allows arbitrary upserts/deletes to the live Supabase database from any browser.
- No data lineage or compliance impact from the race condition fix.
- `context.md` currently states "anon key only" — correct behavior once the key is rotated; no documentation correction needed for the stated requirement, only for the actual state.
- Test T12 (anon key assertion) serves as an ongoing compliance check and should be kept in the permanent test suite.
