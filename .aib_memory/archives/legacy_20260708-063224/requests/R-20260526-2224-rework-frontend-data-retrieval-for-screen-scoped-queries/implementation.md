Implementation record for request R-20260526-2224.

Files in .aib_memory taken into consideration:
- .aib_memory/instructions.md
- .aib_memory/requests_register.md
- .aib_memory/context.md
- .aib_memory/requests/R-20260526-2224-rework-frontend-data-retrieval-for-screen-scoped-queries/plan-R-20260526-2224.md

## Implementation Log

### Entry 2026-05-27 05:48
#### Scope
Implemented the screen-scoped landing-page query redesign for the React frontend and the Supabase SQL contract. The change removed the eager dimension bootstrap, switched the landing page to a date-first startup path, and aligned the projection-backed RPC surface with the visible flat and grouped views.

#### Changes
- Reworked react-app/src/App.jsx so the app mounts the landing page immediately after credential validation instead of blocking on a global dimensions fetch.
- Refactored react-app/src/components/LandingPage.jsx to bootstrap with date options plus the active rows view, and to load the remaining selector options lazily on focus.
- Narrowed react-app/src/lib/dataService.js to the active landing-page RPC helpers and removed the obsolete eager dimension bootstrap and count helper paths.
- Updated react-app/src/App.test.jsx, react-app/src/components/LandingPage.test.jsx, and react-app/src/lib/dataService.test.js to cover the date-first bootstrap, lazy selector loading, and the reduced helper surface.
- Updated src/load_supabase.py so landing-page option RPCs read from landing_page_row_projection and removed the unused get_landing_page_count function from the maintained SQL surface.
- Removed the dead database probe scripts test_db_count.py, test_db_count_filter.py, and test_db_count_price.py because they only targeted the deleted count RPC.
- Updated README.md and .aib_memory/context.md to describe the new landing-page startup and selector-query model.

#### Tests
- unit: react-app/src/App.test.jsx, react-app/src/components/LandingPage.test.jsx, react-app/src/lib/dataService.test.js via `cd react-app && npm test -- src/App.test.jsx src/components/LandingPage.test.jsx src/lib/dataService.test.js` — pass
- unit: full React suite via `cd react-app && npm test` — pass
- build: production frontend build via `cd react-app && npm run build` — pass
- unit: Supabase loader contract via `python -m unittest tests.test_load_supabase` — pass

#### Outcome
Successful implementation. The landing page now requests only the active visible dataset at startup, defers selector RPCs until the user interacts with a control, and no longer depends on the removed count RPC. Residual risk is limited to real-dataset performance characteristics in the deployed Supabase environment, which still need live runtime observation through the frontend query log.

#### Evidence
- Path: react-app/src/App.jsx
- Path: react-app/src/components/LandingPage.jsx
- Path: react-app/src/lib/dataService.js
- Path: src/load_supabase.py
- Path: README.md
- Path: .aib_memory/context.md
- Command output:
```bash
cd react-app && npm test
cd react-app && npm run build
python -m unittest tests.test_load_supabase
```

#### Notes (Optional)
Aligned with the active request plan for R-20260526-2224 and completed without introducing a backend API layer.
