## Executive Summary
- Request ID: R-20260425-1445.

- Request title: Unify all `.env` files into root config.

- Purpose: simplify environment configuration to one root `.env` while preserving behavior and security posture across ETL, deploy, and React app flows.

- Current state includes four env artifacts (`.env`, `.env.example`, `react-app/.env`, `react-app/.env.example`) and mixed consumption paths.

- Python modules (`src/load_supabase.py`, `src/deploy_netlify.py`) already align to root `.env`; React currently depends on `react-app/.env` through Vite defaults.

- Main design fork is how React should consume root values: direct Vite root env loading vs generated compatibility artifact.

- Risks are concentrated in client/server variable boundary handling, migration breakage, and documentation drift.

- This run updated `request.md` sections: `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs`.

## Domain Knowledge Essentials
- Environment configuration: deploy-varying settings (credentials, endpoints, IDs) that must stay outside source code and versioned plaintext secrets.

- Canonical configuration source: the single authoritative location operators should edit during setup.

- ETL operator: person running local pipeline scripts (`extract`, `transform`, `load_supabase`) and menu actions.

- Deployment operator: person deploying React artifacts to Netlify and managing deploy credentials.

- End user (analytics consumer): browser user of the React app; indirectly affected if env misconfiguration breaks frontend data access.

- Processes touched:
  - Local onboarding and setup (`README.md` and env templates).
  - ETL database sync (`DATABASE_URL` consumption).
  - Netlify deploy credentials and CLI execution.
  - React runtime configuration for Supabase URL/anon key.

- Relevant business acceptance impact:
  - Setup friction should drop (one env file).
  - No service outage or build failure should be introduced.
  - No new secret exposure route should be introduced.

## Technical Knowledge & Terms
- `.env`: key-value file loaded into process environment by tooling; intended for local/deploy configuration, not versioned secrets.

- `python-dotenv`: Python library that loads `.env` into `os.environ`; default behavior keeps existing shell variables as higher priority.

- Vite: frontend build tool used by `react-app`; exposes only variables with `VITE_` prefix to client bundle.

- `envDir`: Vite configuration option controlling which directory `.env` files are loaded from.

- `VITE_*`: client-exposed environment variable namespace; values are bundled into frontend build and therefore must not contain private secrets.

- Shell-over-file precedence: runtime environment variables already present in process environment override values loaded from `.env` files.

- Evidence log:
  - Evidence: `find` inventory returned `.env`, `.env.example`, `react-app/.env`, `react-app/.env.example`.
  - Implication: request scope is valid and non-trivial; consolidation requires frontend and docs updates, not only Python.

  - Evidence: `src/load_supabase.py` and `src/deploy_netlify.py` load root `.env`.
  - Implication: server-side path is already aligned; highest-risk change area is React env resolution and docs consistency.

  - Evidence: `react-app/src/lib/supabase.js` reads `import.meta.env.VITE_SUPABASE_URL` and currently instructs creating `react-app/.env`.
  - Implication: user guidance and possibly Vite config must change for single-file objective.

  - Evidence: `.gitignore` includes `.env`.
  - Implication: baseline VCS secret protection exists and must be preserved.

  - Evidence: `.aib_memory/context.md` documents two env locations and precedence.
  - Implication: context documentation becomes stale after implementation unless explicitly updated.

- Files Read:
  - `.aib_memory/requests_register.md`
  - `.aib_memory/input.md`
  - `.aib_memory/references.md`
  - `.aib_memory/context.md`
  - `.aib_brain/Concepts.md`
  - `.aib_brain/conventions/analysis-convention.md`
  - `.aib_brain/conventions/request-convention.md`
  - `README.md`
  - `.env.example`
  - `react-app/.env.example`
  - `.gitignore`
  - `src/load_supabase.py`
  - `src/deploy_netlify.py`
  - `react-app/src/lib/supabase.js`

## Research Results
- Pattern scan against workspace standards and prior requests:
  - Current scripts prefer environment-driven configuration and avoid hardcoded secrets.
  - Existing deploy flow already uses root `.env` and shell precedence, matching desired simplification principles.
  - Previous project pattern keeps `.env.example` committed and `.env` ignored, which should remain unchanged.

- Scope interpretation from evidence:
  - The request is primarily configuration and documentation refactoring, with likely small code/config adaptation in Vite path resolution.
  - Functional risk is concentrated in React runtime because Python modules are already root-aligned.
  - Security risk is concentrated in accidental misuse of non-`VITE_` variables on client side.

- Deterministic constraints identified:
  - Any solution must keep React able to read `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
  - Any solution must keep `DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, and `NETLIFY_SITE_ID` usable by Python/deploy flows.
  - `request.md` requires Q-blocks for unresolved decisions at or above threshold.

## External Benchmarking
- Benchmark reference: Twelve-Factor config principle.
  - Takeaway: deploy-varying config should live in environment, not code or scattered config files.
  - Applicability: strongly applicable; supports consolidation toward one canonical env source.
  - Adoption rationale: adopt as guiding principle because it directly addresses drift and secret management concerns.

- Benchmark reference: Vite env behavior and prefix boundary.
  - Takeaway: only `VITE_` variables are exposed to client bundle; non-prefixed variables remain unavailable client-side.
  - Applicability: critical for safely mixing server and client variables in one root `.env`.
  - Adoption rationale: adopt to enforce explicit safe boundary between browser-exposed and private values.

- Benchmark reference: python-dotenv precedence and root `.env` usage.
  - Takeaway: loader can read project `.env` while preserving shell-provided overrides by default.
  - Applicability: aligns with existing deploy script behavior and supports non-breaking migration.
  - Adoption rationale: adopt to keep compatibility with current operational patterns and avoid regressions.

## Minimal Spikes and Experiments
- **Spike: Env file inventory and consumer mapping**
  - Hypothesis: multiple env files exist and are consumed by different runtime layers.
  - Approach: enumerate env files and inspect key consumer modules in Python and React.
  - Outcome: confirmed four env artifacts and split consumption (Python root-aligned, React app-local by default).
  - Conclusion: request requires cross-layer change, not simple file deletion.

- **Spike: External behavior consistency check**
  - Hypothesis: consolidation can preserve precedence and security if client/server boundaries are maintained.
  - Approach: compare workspace patterns with Twelve-Factor, Vite env semantics, and python-dotenv behavior.
  - Outcome: no conflict found; root canonical env model is viable with explicit `VITE_` boundary and Vite config alignment.
  - Conclusion: simplification is feasible without lowering security quality.

## AI Copilot Suggestions
- Observation: The request goal is correct, but the phrase “single `.env` in root” hides one significant frontend design decision.
  - Suggestion: lock the React env-loading strategy early (direct root loading vs generated mirror) to avoid rework and ambiguous implementation.

- Observation: Security quality can regress silently if a private key is accidentally referenced in client code after unification.
  - Suggestion: add explicit guardrails in docs/tests that only `VITE_` keys are client-consumed and no non-`VITE_` secret appears in frontend code paths.

- Observation: Existing Python flows are already root-`.env` based, so backend-side changes should remain minimal.
  - Suggestion: concentrate implementation effort on Vite config and documentation cleanup, then verify with targeted regression tests.

- Observation: Documentation drift already exists (menu options in README vs current context), which can compound migration confusion.
  - Suggestion: prioritize documentation alignment as part of done criteria, not as a deferred clean-up.

- Scope calibration note: scope appears slightly larger than the user wording suggests because frontend loader behavior and template deprecation decisions introduce architecture-level branching.

## Testing
- T1 — Env file consolidation baseline: Verify only one canonical setup path is documented for configuration (`README.md`, templates). Expected outcome: no active setup instruction requires editing `react-app/.env` directly unless explicitly marked as compatibility fallback.

- T2 — Root template completeness: Validate root `.env.example` contains all required keys (`DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`). Expected outcome: all required keys present exactly once with non-secret placeholders.

- T3 — Python loader regression: Run `python -m unittest tests/test_deploy_netlify.py` and related env-loading tests. Expected outcome: all tests pass and preserve shell-over-file precedence behavior.

- T4 — Supabase sync env read sanity: Execute `python src/load_supabase.py` in a controlled missing-credential scenario. Expected outcome: deterministic non-zero exit with missing `DATABASE_URL` message and no secret value output.

- T5 — React build with root env: Run React build with Vite reading from root env source. Expected outcome: `npm run build` exits 0 and frontend compiles without requiring `react-app/.env`.

- T6 — Content safety check: Search repository tracked files for real secret values and ensure `.gitignore` still excludes `.env`. Expected outcome: no secret leakage in tracked files and `.env` remains ignored.

- T7 — Idempotency re-run: Re-run tests/build after no further changes. Expected outcome: same pass results and no additional config artifacts regenerated unexpectedly.

- T8 — Success criteria traceability check: Map each success criterion to at least one automated assertion above. Expected outcome: complete SC-to-test coverage matrix with no uncovered criterion.

## Multi-Perspective Stakeholder Review
### Senior Solution Architect
The request is technically feasible and aligns with existing architecture because Python modules are already root-env oriented. The main architecture risk is frontend env-source resolution and avoiding parallel compatibility layers that become permanent.

- Feasibility is high with low backend disruption.
- Highest design risk is introducing a temporary sync workaround that persists indefinitely.
- Architecture integrity improves if one canonical source is enforced in code and docs.
- Decision Q001 should be resolved before implementation to avoid divergent paths.

### Product Owner
The requested simplification delivers direct operator value by reducing setup complexity and confusion. Acceptance criteria are mostly clear, but final expected behavior for legacy `react-app/.env` presence should be explicitly decided.

- Clear user value: fewer setup steps and less drift.
- Scope is meaningful and bounded, but one decision remains unresolved.
- Success criteria are measurable if tied to concrete tests.
- Documentation updates are essential to realize business value.

### User
For operators and contributors, one root env file reduces friction and onboarding time. Friction can still occur if old docs or error messages continue to point to `react-app/.env`.

- Improved usability from a single place to edit config.
- Risk of confusion if compatibility behavior is undocumented.
- Better supportability if errors reference the new canonical location.
- Predictability improves when setup steps are consistent across scripts/apps.

### Security Officer
Security posture can remain equivalent or improve if client/server variable boundaries are explicitly enforced. The biggest concern is accidental client exposure of sensitive non-`VITE_` keys through code misuse.

- Keep `.env` out of VCS and maintain no-secret logging discipline.
- Enforce strict guidance: only `VITE_` keys are allowed in frontend consumption.
- Preserve shell override precedence for secure deploy-time injection.
- Add regression checks for leak-prevention in docs and code references.

### Data Governance Officer
The change is configuration-structural and does not alter business data lineage, retention, or schema. Governance impact is primarily documentation accuracy and traceability of operational setup.

- No change expected to data lineage from source to schema to app.
- No retention-policy impact from env consolidation itself.
- Classification boundaries remain: credentials are sensitive, anon key is public-safe.
- Governance quality depends on synchronized updates to context and setup documentation.
