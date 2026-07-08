Implementation record for the active landing-page timeout investigation request.

Considered .aib_memory files:
- .aib_memory/requests_register.md
- .aib_memory/context.md
- .aib_memory/plan-R-20260526-0436.md
- .aib_memory/instructions.md

## Implementation Log

### Entry 2026-05-26 08:40
#### Scope
Investigated the remaining anonymous landing-page timeout on the first flat-table load and implemented repository-side query-path changes in the Supabase loader plus focused frontend coverage. The work targeted the deployed row RPC, the landing-page option RPCs, and the request-mount behavior that must preserve the initial current-date filter.

#### Changes
- Added a derived `landing_page_row_projection` structure and supporting indexes in `src/load_supabase.py` so landing-page row reads have a dedicated indexed surface.
- Refactored `get_landing_page_rows` and `get_landing_page_count` in `src/load_supabase.py` back to parameter-specific dynamic SQL so filtered anon calls can use the current-date index path instead of a generic `OR` plan.
- Reworked the landing-page option RPCs in `src/load_supabase.py` to deduplicate narrow keys first and join dimension labels after the reduction step.
- Changed the projection refresh path in `src/load_supabase.py` from `REFRESH MATERIALIZED VIEW` to table-style refresh logic and then to batched `file_key` inserts after the live deployment path hit storage and connection limits.
- Updated source-level documentation in `src/load_supabase.py`, `react-app/src/lib/dataService.js`, and `.aib_memory/context.md` to describe the projection-backed row path and the current deployment blocker.
- Strengthened `tests/test_load_supabase.py` to cover the projection DDL and refresh path and tightened `react-app/src/components/LandingPage.test.jsx` so the initial mount asserts the first date key is passed into the row RPC.

#### Tests
- unit: `python -m unittest tests.test_load_supabase` — pass
- unit: `cd react-app && npm test` — pass
- build: `cd react-app && npm run build` — pass
- integration: `python test_db.py` against the configured database — pass
- integration: anon-role RPC probe through `@supabase/supabase-js` for `get_landing_page_rows` and option RPCs — fail before the latest undeployed SQL could be applied
- browser: local preview at `http://127.0.0.1:4175/` with the current deployed database state — fail, still surfaced `fetchLandingPageRows: canceling statement due to statement timeout`

#### Outcome
Repository code and local automated validation are in a good state, and the investigation isolated the anonymous-path bottleneck to the deployed SQL planning path rather than the React mount state. The request is not complete because the live Supabase database is currently blocking write-side deployment with `transaction_read_only = on`, so the updated SQL could not be applied and the browser re-check could not be completed against the final code.

#### Evidence
- Path: `src/load_supabase.py`
- Path: `tests/test_load_supabase.py`
- Path: `react-app/src/components/LandingPage.test.jsx`
- Path: `react-app/src/lib/dataService.js`
- Path: `.aib_memory/context.md`
- Command: `python -m unittest tests.test_load_supabase`
- Command: `cd react-app && npm test`
- Command: `cd react-app && npm run build`
- Command: `python test_db.py`
- Log snippet:
  ```text
  transaction_read_only = on
  ReadOnlySqlTransaction cannot execute CREATE TABLE in a read-only transaction
  ```
- Log snippet:
  ```text
  {"label":"rows_date_100","duration":4169,"rowCount":null,"error":"canceling statement due to statement timeout"}
  {"label":"opt_category_100","duration":3130,"rowCount":null,"error":"canceling statement due to statement timeout"}
  ```

#### Notes (Optional)
The request remains Active because the deployment and live-browser verification criteria are blocked by the current Supabase database mode. Once the database accepts write transactions again, rerun `python src/load_supabase.py`, then repeat the anonymous RPC probe and the local preview-browser verification.