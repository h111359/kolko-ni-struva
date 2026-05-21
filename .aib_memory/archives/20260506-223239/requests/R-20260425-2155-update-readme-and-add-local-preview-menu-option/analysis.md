## Executive Summary

- Request ID: R-20260425-2155.

- Request title: Update README and add local preview menu option.

- Primary purpose: align operator documentation with the current repository state and add a deterministic pre-deploy local website preview action in the interactive menu.

- Business intent: reduce deployment mistakes by validating the web app locally before Netlify production deploy.

- Scope interpretation: documentation and operator workflow only; ETL logic, Supabase sync logic, and React feature behavior remain unchanged.

- Evidence indicates current drift: README menu section is outdated (still documents options 1-4 from older flow), while menu.py currently exposes options 0-5 including Supabase sync and Netlify deploy.

- Decision integration from request answers: the preview action should default to deployment-like preview mode (npm run build && npm run preview) and should attempt browser auto-open while always printing the URL and tolerating open failures.

- Expected implementation impact: main code change in menu.py, major documentation refresh in README.md, optional context synchronization in .aib_memory/context.md.

- During this analysis run, request.md was updated in the implementation-relevant sections: Assumptions, Plan, Documentation, and Questions & Decisions (answered items applied; no open questions remain).

## Domain Knowledge Essentials

- Local preview: a pre-deployment operator check that validates behavior in a local browser before publishing artifacts to Netlify.

- Deployment-like preview: serving the production build output rather than the hot-reload development server so behavior is closer to what users receive in production.

- Operator workflow: the sequence an engineer follows in menu.py to run ETL/update/deploy actions from the terminal.

- Impacted personas:
  - Data engineer/operator: runs menu actions and needs reliable, low-friction local validation before deploy.
  - Product owner: expects documentation and runtime behavior to match and be reproducible by team members.
  - Analyst/end user (indirect): benefits from reduced risk of broken public deployments.

- Business processes touched:
  - Pre-release validation of React app output.
  - Operational runbook usage through README + menu.
  - Deployment readiness checks.

- Relevant success measures for this request:
  - Menu exposes a clear local preview option.
  - README provides runnable local preview steps.
  - Existing menu actions continue to behave as before.
  - Re-runs remain idempotent (no duplicated menu labels, no conflicting docs).

- Acceptance impact:
  - If done well, non-authors can execute preview+deploy safely from documented steps.
  - If done poorly, operators may skip local verification or run wrong commands, increasing release risk.

## Technical Knowledge & Terms

- Interactive menu (menu.py): Python terminal UI routing user choice to subprocess actions.

- Subprocess invocation: Python process execution mechanism used by menu.py to run scripts; list-form arguments avoid shell injection risk.

- Vite dev server (npm run dev): local development server with fast refresh; useful for development speed but not deployment-like validation.

- Vite preview (npm run preview): serves built dist artifacts for local production-like validation; requires an up-to-date build.

- Browser auto-open: best-effort attempt to open local URL in default browser; can fail in headless or restricted sessions and must degrade gracefully.

- Idempotency: repeated runs converge to the same expected state/output intent without cumulative side effects.

- Non-functional constraints in scope:
  - Keep existing ETL/deploy actions intact.
  - Preserve deterministic menu routing.
  - Avoid secret leakage in docs or command output.

- Evidence log (evidence -> implication):
  - menu.py currently supports options 1-5 plus exit -> new local preview action must preserve numbering integrity and existing route behavior.
  - README.md menu section still documents old 1-4 action set -> documentation drift is confirmed and must be corrected.
  - react-app/package.json exposes dev/build/preview scripts -> production-like preview is technically available without adding new dependencies.
  - AIB prompt requirements require final input reset and strict section formats -> analysis/update artifacts must be deterministic and structurally compliant.

- Files read:
  - .aib_memory/requests_register.md
  - .aib_memory/input.md
  - .aib_memory/references.md
  - .aib_memory/context.md
  - .aib_brain/Concepts.md
  - .aib_brain/conventions/analysis-convention.md
  - .aib_brain/conventions/request-convention.md
  - .aib_memory/requests/R-20260425-2155-update-readme-and-add-local-preview-menu-option/request.md
  - menu.py
  - README.md
  - react-app/package.json

## Research Results

- Pattern scan against current workspace standards:
  - Existing menu actions are thin wrappers around script/subprocess runners; the new preview option should follow the same action-function + menu-route pattern to keep maintainability and readability consistent.
  - Existing deploy flow already supports interactive user prompts through direct subprocess passthrough; preview flow should preserve interactive terminal visibility rather than over-capturing output.
  - README currently mixes accurate ETL descriptions with stale menu enumerations, indicating section-level updates are required instead of incremental line tweaks.

- Similar solution patterns from existing product behavior:
  - Option-specific action handlers (action_download, action_transform, etc.) reduce branching complexity and make menu testing straightforward.
  - Deterministic user input validation ([0-5]) currently guards menu behavior; adding preview requires expanding bounds and invalid-input message safely.
  - Wrapper launchers (menu.sh/menu.bat) remain thin and OS-neutral; preview logic belongs in menu.py, not wrapper scripts.

- Practical implications for this request:
  - Introduce exactly one new action branch for local preview and adjust the visible menu map accordingly.
  - Keep legacy options unchanged to avoid operator retraining costs.
  - Fully refresh README sections that describe menu actions and local workflow, not only append a small note.

## External Benchmarking

- Benchmark 1: Vite CLI guidance distinguishes development server and preview server roles.
  - Takeaway: vite preview is intended for local inspection of production build output and expects build artifacts to exist first.
  - Applicability: strongly applicable because request asks for pre-Netlify local test, which is best represented by production-like behavior.
  - Decision: adopt as default behavior (build then preview), while still documenting dev mode for iterative development.

- Benchmark 2: Python webbrowser module defines best-effort browser opening and explicit boolean success/failure semantics.
  - Takeaway: browser open attempts can fail by environment and should not crash workflow if URL is still available.
  - Applicability: directly applicable for menu UX across Linux/Windows/headless environments.
  - Decision: adopt best-effort open + always print URL + continue on failure.

- Benchmark 3: Netlify CLI docs emphasize local build validation and environment-based deploy practices.
  - Takeaway: local validation before deploy reduces production surprises; deploy commands rely on consistent environment setup.
  - Applicability: aligns with request objective to add explicit local verification step before deploy.
  - Decision: adapt by documenting local preview as a standard pre-deploy checkpoint in README.

## Minimal Spikes and Experiments

- Spike: Preview mode feasibility from existing scripts
  - Hypothesis: The repository already supports a deployment-like local preview command without adding tooling.
  - Approach: Inspect react-app/package.json scripts and map to menu action requirements.
  - Outcome: build and preview scripts are already present (vite build, vite preview).
  - Conclusion: no dependency spike needed; implementation can call existing npm scripts.

- Spike: Browser-open reliability requirement
  - Hypothesis: Automatic browser opening is environment-dependent and must be non-blocking.
  - Approach: Review Python webbrowser behavior and existing workspace run contexts (terminal-first operator flow).
  - Outcome: open is best-effort and may return false/fail in some contexts.
  - Conclusion: graceful fallback behavior is required and should be explicit in both code intent and README.

## AI Copilot Suggestions

- Observation 1 (scope quality): The request is well-targeted but risks under-specifying how the preview process should behave when prerequisites are missing (node modules not installed, port occupied, browser unavailable).
  - Actionable suggestion: include explicit failure/fallback messaging expectations in documentation and test intent, so behavior stays operator-friendly under partial setup.

- Observation 2 (implementation risk): Menu numbering changes can silently break operator muscle memory and any script-driven interaction checks.
  - Actionable suggestion: preserve existing action semantics and append/insert the preview action with clearly documented numbering changes and regression checks.

- Observation 3 (maintainability): README currently contains mixed-generation content with stale sections; patching one subsection may leave hidden inconsistencies.
  - Actionable suggestion: treat README updates as a coherence pass across quick start, menu actions, and deploy flow instead of a single isolated edit.

- Observation 4 (testability): Manual interaction paths (menu + browser open) are partly non-automatable, which can hide regressions if only unit tests are run.
  - Actionable suggestion: pair scripted checks with explicit UAT scenarios and require at least one reproducible manual acceptance run before closure.

- Scope sizing note: The scope appears appropriate and slightly conservative; it is not larger than necessary to meet the stated goal, but documentation synchronization in .aib_memory/context.md is an important adjacent task that should remain in scope.

## Testing

- T1 — Analysis artifact exists: Verify .aib_memory/requests/R-20260425-2155-update-readme-and-add-local-preview-menu-option/analysis.md exists and contains all mandatory section headings in required order. Expected outcome: file exists and heading sequence matches convention.

- T2 — Request assumptions refreshed: Verify request.md contains a replaced ## Assumptions section with A1..An entries and risk-if-false lines. Expected outcome: assumptions align to current decisions and no stale threshold ambiguity assumption remains.

- T3 — Menu option presence and bounds: Run menu.py in a controlled invocation and inspect menu text for the new local preview option and updated input bounds. Expected outcome: option is visible, and invalid input guidance references the updated valid range.

- T4 — README content alignment: Validate README sections include explicit local preview steps before deploy and updated menu action mapping. Expected outcome: documentation reflects current and newly added menu behavior with runnable commands.

- T5 — Existing action regression: Execute targeted checks for existing menu actions (download/transform/update/deploy dispatch paths) without changing ETL logic. Expected outcome: existing action routes remain callable and unchanged in intent.

- T6 — Automated test suite run: Execute Python tests (at least tests/test_config_utils.py and tests/test_deploy_netlify.py). Expected outcome: tests pass with no regressions introduced by documentation/menu workflow changes.

- T7 — Idempotent re-run verification: Re-run analysis/update checks and ensure no duplicate sections or conflicting menu/docs entries are produced. Expected outcome: artifacts converge to stable content.

- T8 — Manual operator UX verification: Validate interactive menu selection and browser-open fallback behavior in a real operator terminal session. Expected outcome: selecting preview starts local server flow, URL is printed, and failure to auto-open does not terminate flow. See UAT_scenarios.md — UAT-01 and UAT-02.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect
The request is technically straightforward but touches a high-traffic operator entry point (menu.py), so preserving route stability is essential. Using existing Vite scripts minimizes design churn and keeps architecture coherent.

- The change should remain isolated to menu orchestration and docs to avoid cross-layer regressions.
- Deployment-like preview mode aligns better with release confidence than dev mode.
- Risk concentration is in menu numbering/routing errors rather than algorithmic complexity.
- Documentation drift correction is as important as code edits for operational integrity.

### Product Owner
The request has clear user value: lower risk before public deploy and clearer onboarding/documentation. Acceptance criteria are measurable, but they depend on both runtime and docs being synchronized.

- Business value is immediate for release confidence and team handover.
- Scope is clear and bounded; no ETL rework is required.
- Success criteria are testable through visible menu behavior and runnable README steps.
- A manual acceptance checkpoint is needed because browser UX cannot be fully asserted in unit tests.

### User
From an operator standpoint, an explicit local preview action reduces uncertainty and command memorization. The most important user outcome is predictable behavior when running from terminal-only environments.

- A visible menu option reduces friction compared to remembering npm command chains.
- Printing the local URL is mandatory for usability when auto-open fails.
- Clear README steps help occasional users execute preview/deploy safely.
- Unexpected renumbering without docs updates would create user confusion.

### Security Officer
The request has low direct security impact, but command execution and documentation handling still require caution around secrets and environment leakage.

- No new authentication flow is introduced; existing .env practices remain unchanged.
- Browser-open behavior should avoid logging sensitive values (only local URL should be shown).
- No additional network surface beyond local preview server is required.
- Documentation should avoid embedding credential examples with real values.

### Data Governance Officer
Data lineage and data model are unaffected, but operational docs are governance artifacts and must stay traceable to actual behavior.

- No schema, retention, or classification changes are introduced.
- Context documentation should be synchronized when operator workflow changes.
- Test evidence should confirm no ETL/data pipeline side effects.
- Request traceability remains strong if analysis, request updates, and UAT references stay consistent.
