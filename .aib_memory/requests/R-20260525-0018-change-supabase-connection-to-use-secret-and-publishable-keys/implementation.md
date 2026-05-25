Implementation record for request R-20260525-0018: Change Supabase connection to use secret and publishable keys.

## AIB memory files referenced
- `.aib_memory/requests_register.md`
- `.aib_memory/plan-R-20260525-0018.md` (moved to request folder after implementation)
- `.aib_memory/context.md`
- `.aib_memory/instructions.md`

## Implementation Log

### Entry 2026-05-25 01:30
#### Scope
Hard cutover of the React frontend Supabase key variable from the legacy JWT anon format (`VITE_SUPABASE_ANON_KEY`) to the new publishable key format (`VITE_SUPABASE_PUBLISHABLE_KEY`) across all production code, tests, documentation, and configuration templates. Added a prefix/format validation guard in `react-app/src/lib/supabase.js` that rejects `sb_secret_...` keys and JWT-format (3-dot-segment) keys before the Supabase client is instantiated. Added `SUPABASE_SECRET_KEY` placeholder to `.env.example` server-side section. Documented the required Netlify dashboard manual variable rename in both `.env.example` and `README.md`.

#### Changes
- Modified `react-app/src/lib/supabase.js`: renamed `supabaseAnonKey` to `supabasePublishableKey`; replaced `VITE_SUPABASE_ANON_KEY` env reference with `VITE_SUPABASE_PUBLISHABLE_KEY`; replaced simple missing-credentials check with an IIFE-based validation guard that also rejects `sb_secret_...` keys and 3-segment JWT keys; updated JSDoc comment from "anon key" to "publishable key".
- Modified `menu.py`: replaced all 4 occurrences of `VITE_SUPABASE_ANON_KEY` with `VITE_SUPABASE_PUBLISHABLE_KEY` in `action_local_preview()` — docstring, `os.environ.get()` call, `missing.append()` call, and example string in the error output.
- Modified `tests/test_menu.py`: replaced all 8 occurrences of `VITE_SUPABASE_ANON_KEY` with `VITE_SUPABASE_PUBLISHABLE_KEY`; updated `_VALID_ENV` dict value from `"anon-test-key"` to `"sb_publishable_testkey"`; replaced entire `TestViteAnonKeyRole` class with `TestVitePublishableKeyFormat` containing a prefix-format check instead of a JWT-role decode; removed `base64` and `json` imports (no longer used); updated module docstring.
- Modified `.env.example`: added `SUPABASE_SECRET_KEY` placeholder after `DATABASE_URL` in the server-side section; renamed `VITE_SUPABASE_ANON_KEY` to `VITE_SUPABASE_PUBLISHABLE_KEY` with updated comments and placeholder value; updated "anon key" description to "publishable key"; appended Netlify migration note block.
- Modified `README.md`: renamed `VITE_SUPABASE_ANON_KEY` to `VITE_SUPABASE_PUBLISHABLE_KEY` in 3 occurrences (code block, acquisition description, security note); updated security note wording; inserted `### Migration: VITE_SUPABASE_ANON_KEY → VITE_SUPABASE_PUBLISHABLE_KEY` subsection with sequenced operator instructions and build-time warning.
- Modified `.aib_memory/context.md`: added `Updated by R-20260525-0018` history bullet; updated all 8 `VITE_SUPABASE_ANON_KEY` occurrences to `VITE_SUPABASE_PUBLISHABLE_KEY`; updated `supabase.js` component description to document the new validation guard; updated secrets count from "Five" to "Six" and added `SUPABASE_SECRET_KEY`; updated `menu.py` component description.

#### Tests
- unit: `tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_both_credentials_returns_early` — pass
- unit: `tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_url_prints_variable_name` — pass
- unit: `tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_key_prints_variable_name` — pass
- unit: `tests/test_menu.py::TestActionLocalPreviewCallOrder` (6 tests) — pass
- unit: `tests/test_menu.py::TestVitePublishableKeyFormat::test_vite_publishable_key_has_correct_prefix` — skipped (no `.env` with `VITE_SUPABASE_PUBLISHABLE_KEY`; expected)
- unit: all remaining 14 tests in `tests/test_menu.py` — pass
- Total: 23 passed, 1 skipped, 0 failed

#### Outcome
Successful. All 23 passing tests pass; the 1 skip is expected (prefix validation skips until the operator updates `.env`). No `VITE_SUPABASE_ANON_KEY` references remain in any production file (`.js`, `.py`). Only intentional migration-note references remain in `README.md` and `.env.example`. The `supabase.js` validation guard correctly rejects `sb_secret_...` and JWT-format keys before the Supabase client is created. Backend ETL (`src/load_supabase.py`) and `requirements.txt` were not modified.

#### Evidence
- Test run output:
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3
collected 24 items

tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_both_credentials_returns_early PASSED
tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_key_prints_variable_name PASSED
tests/test_menu.py::TestActionLocalPreviewCredentials::test_missing_url_prints_variable_name PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_browser_not_opened_when_server_does_not_become_ready PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_browser_opened_after_preview_server_starts PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_build_called_before_preview_server_starts PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_build_failure_prevents_preview_server_start PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_npm_not_found_prevents_preview_server_start PASSED
tests/test_menu.py::TestActionLocalPreviewCallOrder::test_npm_not_found_prints_error_message PASSED
tests/test_menu.py::TestVitePublishableKeyFormat::test_vite_publishable_key_has_correct_prefix SKIPPED
======================== 23 passed, 1 skipped in 0.15s =========================
```
- `grep -r "VITE_SUPABASE_ANON_KEY" . --include="*.js" --include="*.py"` returns no matches.
- Modified files: `react-app/src/lib/supabase.js`, `menu.py`, `tests/test_menu.py`, `.env.example`, `README.md`, `.aib_memory/context.md`
