## Goal

Audit the current Netlify deploy process in `src/deploy_netlify.py` and make deployment parameters (NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID) configurable in local configuration files (avoiding interactive prompts). Ensure the implementation is secure, storing credentials safely without exposing them in version control.

## Background

The React app is deployed to Netlify via `src/deploy_netlify.py`, which currently prompts users interactively to enter `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` each time they deploy. This is inefficient when running deployments multiple times or automating deployment workflows. The menu option 5 (Netlify deploy) invokes `deploy_netlify.py` without `capture_output`, allowing stdin passthrough for these interactive prompts. A configurable, secure approach would improve usability while maintaining security by keeping credentials out of version control.

## Scope

- Review and document the current `src/deploy_netlify.py` implementation, specifically the interactive credential collection flow.

- Extend the credential-loading precedence chain: environment variables → `.env` file → interactive prompt (with `.env` as the fallback storage option).

- Create a `.env` template for the deployment script (`.env.example`) documenting the required keys `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID`.

- Update `menu.py` to confirm no modifications are needed to support the new credential-loading flow.

- Ensure the new `.env` file for deployment credentials is properly excluded from version control (`.gitignore`).

- Test that deployments work correctly with credentials sourced from the `.env` file, with proper error messages if credentials are missing.

## Out of scope

- Automated CI/CD pipeline setup or scheduled deployments.

- Integration with external credential management systems (AWS Secrets Manager, HashiCorp Vault, etc.).

- Changing the Netlify site setup or authentication model.

- Modifications to the React app build process or Netlify configuration (`netlify.toml`).

- Retroactive credential migration from Netlify CLI or other existing stores.

## Constraints

- Must maintain backward compatibility: if `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` are present as environment variables, they take precedence.

- Credentials must not be embedded in Python source code or committed to version control.

- The `.env` file must be local-only and automatically excluded via `.gitignore`.

- The interactive fallback must remain available for first-time setup or credential updates without manually editing `.env`.

- Solution must work on both Windows (`refresh.bat`/`menu.bat`) and Linux (`refresh.sh`/`menu.sh`).

- No changes to the `@supabase/supabase-js`-based React app configuration (which uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `react-app/.env`).

## Success criteria

- The Netlify deploy process retrieves `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` in the order: environment variable (if set) → `.env` file (if exists and populated) → interactive prompt.

- A `.env.example` file exists and documents both required keys.

- `.gitignore` includes `.env` (separate file at project root for the ETL deploy script).

- Deployment completes successfully when credentials are provided via `.env`.

- Error messages clearly indicate when credentials are missing or invalid.

- No credentials are exposed in logs or console output except as `***masked***` placeholders.

- All existing tests for `deploy_netlify.py` continue to pass.

## Assumptions

- A1: The `.env` file structure for the ETL deploy script is separate from `react-app/.env` (which contains Supabase keys for the React app). Risk if false: credential namespace collision; manual separation required to avoid overwriting Supabase keys.

- A2: Users will populate `.env` manually on first setup by copying from `.env.example` and entering their Netlify credentials. Risk if false: users may leave the file unpopulated and be prompted interactively, reducing convenience gains.

- A3: `python-dotenv` is already imported in `src/deploy_netlify.py` or will be available in the Python environment. Risk if false: additional dependency installation required; may break existing workflows.

- A4: Netlify CLI is available locally (`netlify` command) as is currently required. Risk if false: deploy process fails with graceful fallback (existing manual-instructions behavior).

## Plan

### Task 1: Audit current deploy_netlify.py implementation
**Intent:** Document the current credential flow, identify integration points, and confirm scope boundaries.
**Inputs:** `src/deploy_netlify.py`, `menu.py`, `.gitignore`
**Outputs:** Analysis findings (inline notes)
**External Interfaces:** Netlify CLI (read-only scan)
**Environment & Configuration:** None
**Procedure:** 
1. Read `src/deploy_netlify.py` and document the `get_credential()` function and overall flow.
2. Verify how `menu.py` option 5 invokes the deploy script.
3. Check `.gitignore` for existing `.env` entries.
4. Confirm `python-dotenv` availability.
**Done Criteria:** Current flow documented; no blocking issues identified.
**Dependencies:** None
**Risk Notes:** None

### Task 2: Extend deploy_netlify.py with .env file support
**Intent:** Add `.env` file reading capability while preserving interactive fallback.
**Inputs:** `src/deploy_netlify.py`, Python stdlib (`os`, `pathlib`)
**Outputs:** Modified `src/deploy_netlify.py` with new credential-loading precedence
**External Interfaces:** `.env` file I/O
**Environment & Configuration:** NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID env vars; `.env` file at project root
**Procedure:**
1. Import `dotenv` (or implement manual `.env` parsing if not available).
2. Modify credential loading: environment variables → `.env` file → interactive prompt.
3. Ensure credentials loaded from `.env` are not logged or exposed in subprocess calls.
4. Add clear debug logging to indicate credential source (e.g., "Credentials loaded from environment" vs. "Credentials loaded from .env file").
5. Preserve existing interactive prompt as fallback.
**Done Criteria:** `deploy_netlify.py` reads credentials in correct precedence order; no credentials exposed in logs.
**Dependencies:** Task 1
**Risk Notes:** If `python-dotenv` is unavailable, implement simple key=value `.env` file parsing.

### Task 3: Create .env.example template and update .gitignore
**Intent:** Provide a secure template for local credential storage and ensure `.env` is excluded from VCS.
**Inputs:** Current `.gitignore`
**Outputs:** `.env.example` created; `.gitignore` updated with `.env` entry
**External Interfaces:** File system
**Environment & Configuration:** None
**Procedure:**
1. Create `.env.example` at project root with placeholder entries:
   ```
   NETLIFY_AUTH_TOKEN=your_netlify_auth_token_here
   NETLIFY_SITE_ID=your_netlify_site_id_here
   ```
2. Add clear comments explaining where to find these values (Netlify UI).
3. Check `.gitignore` and add `.env` (project-root `.env`, not `react-app/.env`).
4. Verify no existing `.env` file is committed; if found, document removal steps.
**Done Criteria:** `.env.example` exists with clear documentation; `.gitignore` includes `.env`; no active `.env` file in VCS.
**Dependencies:** Task 1
**Risk Notes:** None

### Task 4: Verify menu.py and subprocess integration
**Intent:** Ensure menu.py option 5 continues to work correctly with the new credential flow.
**Inputs:** `menu.py`, modified `src/deploy_netlify.py`
**Outputs:** Confirmation that no changes needed; inline notes if adjustments required
**External Interfaces:** subprocess invocation
**Environment & Configuration:** None
**Procedure:**
1. Verify `menu.py` option 5 invokes `src/deploy_netlify.py` with `subprocess.run([sys.executable, 'src/deploy_netlify.py'])` and no `capture_output`.
2. Confirm this allows stdin passthrough for interactive prompts (existing behavior preserved).
3. Test that env vars from the calling shell are propagated to the subprocess (standard behavior).
**Done Criteria:** Menu option 5 works with new credential-loading flow; existing functionality preserved.
**Dependencies:** Task 2
**Risk Notes:** None

### Task 5: Automated testing of credential loading and masking
**Intent:** Define and run automated tests to verify credential precedence, error handling, and log masking.
**Inputs:** Modified `src/deploy_netlify.py`, test framework (pytest or unittest)
**Outputs:** Test results; all tests passing
**External Interfaces:** Filesystem (`.env` temp files); subprocess (credential loading verification)
**Environment & Configuration:** Temporary `.env` files with mock credentials
**Procedure:**
1. Create test cases for credential precedence (env var → `.env` → prompt).
2. Test error handling when credentials are missing.
3. Test that credentials are not logged or exposed in console output.
4. Run `pytest tests/test_deploy_netlify.py` to verify existing tests still pass.
5. Add new test cases for `.env` file loading if the test suite allows.
**Done Criteria:** All existing tests pass; new credential-loading behavior verified via tests.
**Dependencies:** Task 2
**Risk Notes:** Mocking interactive prompts may require refactoring `get_credential()` function if not already testable.

### Task 6: Manual integration testing with live .env file
**Intent:** Verify the end-to-end deploy process works correctly with credentials sourced from `.env`.
**Inputs:** `.env` file with valid Netlify credentials
**Outputs:** Successful deployment to Netlify; verification log
**External Interfaces:** Netlify CLI; Netlify API
**Environment & Configuration:** NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID in `.env`
**Procedure:**
1. Create a local `.env` file with valid test credentials (Netlify personal access token + site ID).
2. Run `python src/deploy_netlify.py` via menu option 5 and verify deployment succeeds without interactive prompts.
3. Verify no credentials appear in console output (only `***masked***` placeholders if any log output).
4. Confirm the React app is deployed to Netlify correctly.
5. Document any error messages encountered and verify they are helpful.
**Done Criteria:** Deployment succeeds; credentials not exposed; process completes without user interaction when `.env` populated.
**Dependencies:** Task 2, Task 3, Task 5
**Risk Notes:** Requires real Netlify credentials; ensure test account or disposable site is used.

### Task 7: Documentation update
**Intent:** Update `README.md`, `context.md`, and any other editable documentation to reflect the new credential-loading process.
**Inputs:** Modified `src/deploy_netlify.py`, `.env.example`, `.gitignore`
**Outputs:** Updated documentation files (README.md, context.md)
**External Interfaces:** Documentation files
**Environment & Configuration:** None
**Procedure:**
1. Update README.md: add section on local Netlify credential setup, .env.example usage, and security best practices.
2. Update `context.md` (REF-0001): document the new credential-loading precedence in the "Configuration and Parameterization" table and security section.
3. Ensure `.env.example` template is clearly documented in the developer setup section.
4. Add a note that credentials must never be committed to version control.
**Done Criteria:** README and context.md clearly document the new setup process; all editable references updated.
**Dependencies:** Task 2, Task 3
**Risk Notes:** None

## Documentation

- [README.md](README.md) (ref_id: N/A) — Update with local credential setup instructions and `.env.example` usage.

- [.aib_memory/context.md]((.aib_memory/context.md) (ref_id: REF-0001) — Update Configuration and Parameterization table, Security & Compliance section, and Developer Setup section to reflect `.env`-based credential loading.

- [.env.example](.env.example) (ref_id: N/A) — Create new template for Netlify credentials.

- [.gitignore](.gitignore) (ref_id: N/A) — Add `.env` entry if not already present.

## Questions & Decisions

**Q001**: If `python-dotenv` is not available in the current environment, should we add it as a dependency in `requirements.txt` or implement simple manual `.env` parsing?
- [x] Option A: Add `python-dotenv` to requirements.txt *(recommended)*
- [ ] Option B: Implement manual `.env` key=value parsing in Python
- [ ] Other: ___
> Answer:

**Q002**: Should credentials entered interactively (when not in `.env` or env vars) be automatically saved to `.env` for future runs, or should users manually manage `.env`?
- [x] Option A: Auto-save to `.env` *(recommended)*
- [ ] Option B: Keep manual; users must edit `.env` to avoid repeated prompts
- [ ] Other: ___
> Answer:

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `src/deploy_netlify.py` | Modified | Add `.env` file reading capability; extend credential-loading precedence chain |
| `.env.example` | Created | New template documenting required Netlify credentials |
| `.gitignore` | Modified | Add `.env` to exclude from version control |
| `menu.py` | Read-only dependency | Verify no changes needed for subprocess invocation |
| `README.md` | Modified | Document local credential setup and `.env` usage |
| `.aib_memory/context.md` | Modified | Update Configuration and Parameterization table, Security section, and Developer Setup |
| `tests/test_deploy_netlify.py` | Read-only dependency | Verify existing tests still pass; may extend with `.env` loading tests |
| `react-app/.env` | Read-only dependency | Confirm separation from project-root `.env` |

## Internal Review of Request and Product Docs

- OK: Request aligns with product context; Netlify deploy process documented in context.md.

- OK: `.env` and environment-variable-based credential management is consistent with product's stated security approach (no hardcoded credentials).

- OK: No conflicts with existing documentation; `.env` exclusion already standard practice (confirmed in context.md).

- Cross-ref issue: `context.md` Security & Compliance section mentions `.env` for Supabase but not for Netlify deploy credentials; will be clarified in documentation update task.

- Missing info: Current tests in `tests/test_deploy_netlify.py` do not appear to cover `.env` file loading; Task 5 will address test coverage gaps.
