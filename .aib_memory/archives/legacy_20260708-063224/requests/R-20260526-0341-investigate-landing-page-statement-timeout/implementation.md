Implementation record for request R-20260526-0341.

Files considered:
- .aib_memory/requests_register.md
- .aib_memory/context.md
- .aib_memory/plan-R-20260526-0341.md
- .aib_memory/input.md

## Implementation Log

### Entry 2026-05-26 03:58
#### Scope
Implemented the chosen Alternative A fix for the landing-page statement-timeout defect while preserving the existing browse-and-filter UX. The change refactors the backend row RPC to page a thinner visible-row slice first, aligns the frontend async state handling with that backend path, updates focused regression coverage, and records the final behavior in product memory.

#### Changes
- Refactored `src/load_supabase.py` so `get_landing_page_rows` now pages a `visible_rows` slice first, using only the joins needed for filter and sort resolution before enriching the visible page rows with category, company, settlement, and file data.
- Added focused database support in `src/load_supabase.py` for preserved landing-page search and sort behavior via `pg_trgm`, a trigram product-name index, and sort-oriented indexes for product and store names.
- Updated `react-app/src/components/LandingPage.jsx` so refresh request tokens fence flat-row, grouped-row, and deferred-count updates, preventing stale async responses from overwriting newer filter state.
- Updated `react-app/src/lib/dataService.js` documentation to match the implemented deferred-count behavior.
- Added a landing-page regression test in `react-app/src/components/LandingPage.test.jsx` that proves an older deferred count response is ignored after a newer refresh.
- Updated `.aib_memory/context.md` to replace the stale parallel-fetch description with the implemented visible-row-first row strategy and stale-response guard.

#### Tests
- integration: `python -m py_compile src/load_supabase.py` — pass
- unit: `cd react-app && npm test -- --run src/components/LandingPage.test.jsx src/lib/dataService.test.js` — pass
- unit: `cd react-app && npm test` — pass
- integration: `pytest tests/test_load_supabase.py -q` — not run (`pytest` is unavailable in this environment)

#### Outcome
Successful implementation. The landing-page row path now does less work before page limiting, the frontend ignores stale async responses, and the full React test suite passes. Residual risk remains on true production-query performance until the updated SQL is deployed and exercised against the live Supabase dataset, because this environment does not provide backend integration tests.

#### Evidence
- Path: `src/load_supabase.py`
- Path: `react-app/src/components/LandingPage.jsx`
- Path: `react-app/src/components/LandingPage.test.jsx`
- Path: `.aib_memory/context.md`
- Full frontend test summary:
  ```text
  Test Files  3 passed (3)
       Tests  52 passed (52)
  ```
- Focused frontend test summary:
  ```text
  Test Files  2 passed (2)
       Tests  44 passed (44)
  ```

#### Notes (Optional)
The backend-specific Python test slice could not be executed here because `pytest` is not installed, so backend validation is limited to a successful `py_compile` check plus the frontend contract tests.
