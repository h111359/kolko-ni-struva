## Goal
Unify the current environment variable setup into a single `.env` file in the repository root while preserving existing functionality and security quality.

## Background
The current setup uses both root-level and `react-app/` env files. This duplicates setup instructions, increases drift risk, and complicates onboarding. The request is to simplify to one root env file while keeping operational behavior and security guarantees unchanged.

## Scope
- Identify all current environment-variable files and consumer modules in Python scripts and the React app.

- Define a single root `.env` strategy that supports ETL/Supabase sync, Netlify deploy flow, and React Vite runtime values.

- Update code/configuration and documentation that currently assume separate `react-app/.env` usage.

- Preserve existing shell-over-file precedence and secret handling behavior.

## Out of scope
- Rotating, changing, or reissuing existing secrets.
- Changing deployment providers (Supabase/Netlify) or introducing a backend service.
- Redesigning business functionality unrelated to configuration loading.

## Constraints
- Existing functionality must remain unchanged from a user perspective.
- Security quality must remain at least equivalent to the current state.
- The solution must stay compatible with the current Linux shell/Python workflow and React Vite build flow.
- No secret values may be committed into repository-tracked artifacts.

## Success criteria
- A single root `.env` file strategy is implemented and used as the canonical source for runtime configuration.
- Existing workflows continue to work without functional regressions.
- Secret-handling behavior is not degraded (no new secret leakage paths in tracked files, docs, or logs).
- Project documentation clearly reflects the new setup steps and file responsibilities.

## Assumptions
- A1: A root `.env` file can safely hold both server-side values (for Python scripts) and client-exposed `VITE_` values, provided only `VITE_` variables are consumed by Vite client code.
  - Risk if false: React build/runtime fails or sensitive keys are accidentally exposed to browser code.
- A2: Vite configuration can be adjusted so `react-app` resolves environment variables from the repository root `.env` without breaking existing commands.
  - Risk if false: A second `.env` file remains required, failing the single-file objective.
- A3: `.env` stays excluded from version control and no script prints secret values, preserving current confidentiality level.
  - Risk if false: Security quality regresses through secret disclosure in repo or logs.
- A4: Existing deploy/runtime environments (local shell, Netlify, CI-like shells) can continue overriding `.env` values through process environment precedence.
  - Risk if false: Environment-specific overrides stop working and deployments become brittle.

## Plan
### Task 1: Baseline Environment Inventory
**Intent:** Establish a verified map of all current env files, keys, and consumer code paths.
**Inputs:** `.env.example`, `react-app/.env.example`, `.env`, `react-app/.env`, `src/load_supabase.py`, `src/deploy_netlify.py`, `react-app/src/lib/supabase.js`, `README.md`.
**Outputs:** Confirmed inventory of keys and file touchpoints; migration mapping documented in request artifacts.
**External Interfaces:** None.
**Environment & Configuration:** Local dev shell and existing Python/Node toolchain.
**Procedure:**
1. Enumerate env files and example templates.
2. Trace each key to the script/module that consumes it.
3. Identify coupling assumptions on file location.
4. Confirm precedence behavior (shell env over file env).
**Done Criteria:** Every env key and consumer path is identified and no unknown env dependency remains.
**Dependencies:** None.
**Risk Notes:** Missing a consumer leads to latent runtime breakage after migration.

### Task 2: Single Root Env Design
**Intent:** Define the target root-only configuration model without reducing security posture.
**Inputs:** Task 1 output, Vite env rules, python-dotenv behavior, current security constraints in request.
**Outputs:** Final key naming/allocation model and compatibility decisions.
**External Interfaces:** Vite env loading mechanism and python-dotenv loader behavior.
**Environment & Configuration:** Root `.env` as canonical source; shell env override retained.
**Procedure:**
1. Classify keys into browser-exposed (`VITE_`) and server-only.
2. Define root `.env.example` as the single onboarding template.
3. Define migration handling for `react-app/.env` deprecation.
4. Capture unresolved high-impact forks as Q-blocks.
**Done Criteria:** A deterministic target model exists for all keys and consumers.
**Dependencies:** Task 1.
**Risk Notes:** Incorrect boundary between client/server keys can create security regression.

### Task 3: Implement Loader and Config Changes
**Intent:** Update code and configuration so all components consume variables from root `.env`.
**Inputs:** Tasks 1-2 outputs, `vite.config.js`, `src/load_supabase.py`, `src/deploy_netlify.py`, `react-app/src/lib/supabase.js`.
**Outputs:** Updated loaders/config ensuring root `.env` is authoritative.
**External Interfaces:** Vite build pipeline, local environment loader.
**Environment & Configuration:** Existing venv and Node runtime.
**Procedure:**
1. Adjust Vite env directory resolution to root or equivalent supported pattern.
2. Remove hard dependency on `react-app/.env` location in user-facing messaging and docs.
3. Preserve current shell-over-file precedence for credentials.
4. Validate that no secrets are emitted to logs.
**Done Criteria:** React and Python flows run correctly with only root `.env` present.
**Dependencies:** Task 2.
**Risk Notes:** Misconfigured env resolution causes client startup/build failures.

### Task 4: Consolidate Templates and Legacy Artifacts
**Intent:** Align example files and remove duplicated env template drift.
**Inputs:** `.env.example`, `react-app/.env.example`, decisions from Task 2.
**Outputs:** Consolidated example template strategy and cleaned legacy files per decision.
**External Interfaces:** None.
**Environment & Configuration:** Git-tracked templates only (no real secrets).
**Procedure:**
1. Merge required key documentation into root template.
2. Update or retire `react-app/.env.example` according to approved decision.
3. Ensure placeholders remain non-sensitive.
4. Verify `.gitignore` still protects real secret files.
**Done Criteria:** Onboarding requires one template source with no conflicting guidance.
**Dependencies:** Tasks 2-3.
**Risk Notes:** Partial consolidation can confuse setup and produce support overhead.

### Task 5: Automated Test Coverage for Scope
**Intent:** Prove functional parity, security parity, and idempotent behavior for the unified env setup.
**Inputs:** Existing tests, updated code/config, success criteria.
**Outputs:** Executed automated checks and pass/fail evidence.
**External Interfaces:** Python test runner, Node build command.
**Environment & Configuration:** Isolated test env values; no production secrets.
**Procedure:**
1. Add/adjust unit tests for env resolution paths and fallback precedence.
2. Run Python tests for deploy/load modules.
3. Run React build with root `.env`-sourced `VITE_` values.
4. Re-run commands to confirm idempotent outcomes.
**Done Criteria:** All testable success criteria have passing automated checks.
**Dependencies:** Tasks 3-4.
**Risk Notes:** Incomplete tests can hide regressions in rarely used paths.

### Task 6: Update Context and Product Documentation
**Intent:** Keep product knowledge and user-facing setup docs consistent with the final behavior.
**Inputs:** `README.md`, `.aib_memory/context.md`, `.aib_memory/references.md`, implementation outcomes.
**Outputs:** Updated docs and context reflecting single root `.env` strategy and resolved decisions.
**External Interfaces:** AIB context generation/update workflow.
**Environment & Configuration:** Documentation artifacts listed in references with `edit_allowed=Y`.
**Procedure:**
1. Update setup instructions and env key locations in README.
2. Update `.aib_memory/context.md` to reflect new env architecture.
3. Validate alignment between docs and actual code paths.
4. Record any remaining discrepancy explicitly.
**Done Criteria:** No contradiction remains between docs and implementation.
**Dependencies:** Tasks 3-5.
**Risk Notes:** Documentation drift can reintroduce multi-file env usage unintentionally.

## Documentation
- README.md (ref_id: N/A) — setup steps and env-file responsibilities must change to single root `.env` guidance.
- .aib_memory/context.md (ref_id: REF-0001) — product context currently describes two `.env` file locations and must reflect the unified model.

## Questions & Decisions
**Q001**: For React runtime variables, which approach should define the final architecture for reading `VITE_` keys from a single root `.env`?
- [x] Option A: Configure Vite to load env from repository root and remove dependency on `react-app/.env`.
- [ ] Option B: Keep `react-app/.env` and generate/sync it from root `.env` via script.
- [ ] Other: ___
> Answer: 

**Q002**: What should be done with `react-app/.env.example` after unifying env setup?
- [x] Option A: Remove it and keep only root `.env.example` as the single template source. *(recommended)*
- [ ] Option B: Keep it as a compatibility stub that points to root `.env` usage.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| .env | Modified | Becomes the canonical single env source at repository root. |
| .env.example | Modified | Must include all required keys (Python, Netlify, React VITE keys) in one template. |
| react-app/.env | Deleted | Removed or deprecated to satisfy single-file objective (decision-dependent). |
| react-app/.env.example | Modified | Must be retired or converted to compatibility guidance (decision-dependent). |
| react-app/vite.config.js | Modified | Needed if Vite env directory is redirected to root `.env`. |
| react-app/src/lib/supabase.js | Modified | User-facing guidance currently points to `react-app/.env`; must align with unified setup. |
| src/load_supabase.py | Read-only dependency | Already consumes root `.env`; acts as compatibility baseline. |
| src/deploy_netlify.py | Read-only dependency | Already consumes root `.env`; must remain behaviorally unchanged. |
| README.md | Modified | Setup and env documentation currently references multiple env files. |
| tests/test_deploy_netlify.py | Modified | May need assertion updates if env-file expectations/messages change. |

## Internal Review of Request and Product Docs
- Ambiguity: request.md — “single file in root” does not prescribe React-side loading mechanism (`envDir` vs sync artifact), creating a significant design fork.
- Missing info: `.aib_memory/input.md` — Question threshold row has two checked values (`1` and `3`), which is non-deterministic and defaults threshold behavior to 3.
- Contradiction: README.md — menu section still documents a 4-option menu, while current product context documents options including Supabase update and Netlify deploy.
- Cross-ref issue: `.aib_memory/references.md` — path for Concepts uses backslash (`.aib_brain\Concepts.md`) while workspace paths are slash-based.
- OK: `.aib_memory/context.md` — documents current two-location env model and identifies all currently relevant env keys and precedence rules.
