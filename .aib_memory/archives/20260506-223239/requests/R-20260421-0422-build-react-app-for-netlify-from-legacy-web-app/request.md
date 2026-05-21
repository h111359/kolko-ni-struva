## Goal

Build a React web application for deployment on Netlify that replicates the visual styling and core functionality of the legacy `build-legacy/web/` price analysis app, replacing local static file loading with direct data queries to the Supabase-hosted star-schema database.

## Background

The ETL pipeline (`src/extract.py`, `src/transform.py`, `src/load_supabase.py`) downloads, transforms, and syncs daily Bulgarian retail price data to a Supabase-hosted PostgreSQL star-schema database. A legacy vanilla JS web app (`build-legacy/web/`) was previously used to visualize this data from local static files. A React-based replacement is needed that connects directly to Supabase, enabling data browsing from a public URL without local file deployment. The app is intended to be hosted on Netlify.

The Supabase database already contains the star-schema tables (`dim_date`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, `dim_company`, `dim_file`, `fact_prices`, `fact_prices_lookback`) populated by `src/load_supabase.py`.

## Scope

- Create a React application using Vite in a `react-app/` subfolder at the workspace root.

- Replicate the visual design of the legacy app: purple gradient background (`#667eea → #764ba2`), white card layouts, navigation bar with active state, feature cards, custom CSS horizontal bar chart, and results tables.

- Implement 4 views matching the legacy pages: Home/Landing, Report 1 (average price by category for a selected city), Report 2 (products by city and category), Report 3 (locations and products by category).

- Date selector in the header, populated from Supabase `dim_date` table, showing available dates in descending order (newest first); dates formatted as DD.MM.YYYY.

- City dropdowns in Report 1 and Report 2, populated from Supabase `dim_settlement` and filtered through `dim_store` to show only settlements with data for the selected date.

- Category dropdowns in Report 2 and Report 3, populated from Supabase `dim_category`.

- Data fetching via `@supabase/supabase-js` v2 client using `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` environment variables.

- Include `netlify.toml` with `[build] command = "npm run build"` and `publish = "dist"`.

- Include `react-app/.env.example` with placeholder values for both Supabase env vars.

## Out of scope

- Displaying day-1 and day-2 lookback prices from `fact_prices_lookback` (the legacy app does not display them).
- ETL pipeline modifications (`src/extract.py`, `src/transform.py`, `src/load_supabase.py`, `config.ini`, `menu.py`).
- User authentication or authorization within the web app.
- Server-side rendering (SSR) or Netlify serverless functions.
- Changes to the Supabase schema, table DDL, or Row Level Security policies.
- Mobile-specific redesign beyond the existing CSS responsiveness in the legacy app.
- Automated CI/CD pipeline or GitHub Actions.
- Loading data from local `data/schema/` CSV files.
- The `dimension-loader.js` referenced in `build-legacy/web/script.js` (file does not exist; React app replaces this abstraction with direct Supabase queries).

## Constraints

- React 18+ with Vite build tool (`create-react-app` is deprecated and must not be used).
- `@supabase/supabase-js` v2 as the sole database client library.
- Environment variables must use `VITE_` prefix for Vite compatibility; no credentials hardcoded in source files.
- Supabase anon key (public-safe) is used; no service role key or admin credentials in the frontend.
- Chart rendering: replicate the custom CSS horizontal bar chart from the legacy app; no external chart library is required (a lightweight library is acceptable if it produces equivalent output).
- Python ETL scripts and `config.ini` must remain unchanged.
- Netlify free tier compatible (client-side only, no serverless functions required).
- Node.js 18+ required for Vite 5 compatibility.

## Success criteria

1. Running `npm run build` in `react-app/` exits with code 0 and produces a `react-app/dist/` directory.
2. `react-app/netlify.toml` is present with correct `build.command` (`npm run build`) and `build.publish` (`dist`) values.
3. `react-app/.env.example` is present and contains both `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` placeholder entries.
4. No Supabase credentials or URLs are embedded in source files under `react-app/src/`.
5. The Home page renders with the purple gradient header, three feature cards, and CTA section matching the legacy layout.
6. The date selector in the header is populated from Supabase `dim_date` and shows available dates in descending order, pre-selecting the newest.
7. Report 1 renders a horizontal bar chart of average prices by category for a selected city.
8. Report 2 renders a product table filtered by selected city and category, showing at minimum: product name, calculated price, retail price, promo price, store name, chain name, date.
9. Report 3 renders a location+product table filtered by selected category, showing at minimum: city name, product name, price, retail price, promo price, store name, chain name.

## Assumptions

- A1: Supabase instance has all star-schema tables created and populated by running `src/load_supabase.py` at least once. Risk if false: App queries will return empty data or HTTP errors at runtime.

- A2: Supabase anon key has SELECT access on all star-schema tables (RLS policies allow public read, or RLS is disabled on these tables). Risk if false: All queries return 0 rows or HTTP 401/403; app appears empty with no actionable error shown to user.

- A3: `dim_store` (4,824 rows), `dim_settlement` (266 rows), `dim_category` (369 rows), and `dim_date` (~63 rows growing) are small enough to load fully client-side on startup without latency or memory issues. Risk if false: Initial load is slow; lazy loading or server-side filtering must be added.

- A4: Querying `fact_prices` filtered by `date_key` and a set of `store_key` values (for a given settlement) returns a manageable result set suitable for client-side aggregation. Risk if false: Query result exceeds Supabase row cap or times out; server-side aggregation via RPC needed.

- A5: `dim_product` (118,281 rows) is not loaded in full on startup; product names are fetched as part of filtered fact queries by joining with `dim_product` on the server side or by batched key lookup. Risk if false: Client memory exhaustion and slow initialization.

- A6: The `react-app/` subfolder at workspace root is the correct placement; Netlify build can be configured to build from this subdirectory. Risk if false: Netlify site settings may need `Base directory = react-app` in addition to `netlify.toml`.

## Plan

### Task 1: Initialize React + Vite Project
**Intent:** Bootstrap the React + Vite project in `react-app/` with all required configuration and entry files.
**Inputs:** Current workspace root layout; Vite documentation patterns.
**Outputs:** `react-app/package.json`, `react-app/vite.config.js`, `react-app/index.html`, `react-app/.env.example`, `react-app/netlify.toml`, `react-app/src/main.jsx`, `react-app/src/index.css`.
**External Interfaces:** npm package registry (internet required for `npm install`).
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in `react-app/.env` (based on `.env.example`).
**Procedure:**
1. Create `react-app/` directory.
2. Create `package.json` with `react`, `react-dom`, `@vitejs/plugin-react`, `@supabase/supabase-js`, `vite` as dependencies.
3. Create `vite.config.js`.
4. Create `index.html` as Vite entry point.
5. Create `netlify.toml` and `.env.example`.
6. Create `src/main.jsx` and `src/index.css`.
**Done Criteria:** `npm install` completes; `npm run build` exits 0 with `dist/` produced.
**Dependencies:** None.
**Risk Notes:** Node.js 18+ recommended for Vite 5; verify local node version before running.

### Task 2: Implement Supabase Client
**Intent:** Create a Supabase client singleton loaded from Vite env vars.
**Inputs:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
**Outputs:** `react-app/src/lib/supabase.js`.
**External Interfaces:** Supabase.
**Environment & Configuration:** `import.meta.env.VITE_SUPABASE_URL`, `import.meta.env.VITE_SUPABASE_ANON_KEY`.
**Procedure:**
1. Create `react-app/src/lib/supabase.js`.
2. Import `createClient` from `@supabase/supabase-js`.
3. Export a singleton client instance using both env vars.
**Done Criteria:** File exists; no hardcoded Supabase URLs or keys present.
**Dependencies:** Task 1.
**Risk Notes:** None.

### Task 3: Implement Data Service Layer
**Intent:** Create async data-fetching functions for all dimension loads and report queries.
**Inputs:** `src/lib/supabase.js`; Supabase star-schema tables.
**Outputs:** `react-app/src/lib/dataService.js`.
**External Interfaces:** Supabase REST API via `@supabase/supabase-js`.
**Environment & Configuration:** Supabase anon key; RLS must allow public SELECT.
**Procedure:**
1. Implement `fetchDimensions()` — parallel fetch of `dim_date`, `dim_settlement`, `dim_category`, `dim_store`; returns combined object cached in module scope.
2. Implement `fetchReport1(dateKey, settlementKey, dimStore)` — derive store_keys for the settlement from cached dim_store; query `fact_prices` with `date_key` + `store_key in [...]` filter; aggregate avg price per `category_key` client-side; enrich with category names from `dim_category`.
3. Implement `fetchReport2(dateKey, settlementKey, categoryKey, dims)` — query `fact_prices` with date + store_keys + category filter; batch-fetch product names from `dim_product` by `product_key`; enrich rows with store name and company name from cached dims.
4. Implement `fetchReport3(dateKey, categoryKey, dims)` — query `fact_prices` with date + category filter (with `.range()` pagination up to 5,000 rows); enrich rows with settlement name, store name, company name from cached dims.
5. Handle Supabase default row limit (1,000) with `.range()` or explicit `.limit()` as needed.
**Done Criteria:** All functions return typed arrays without runtime error on valid inputs.
**Dependencies:** Task 2.
**Risk Notes:** Large result sets in Report 3 (all cities for a category) may require pagination; cap at sensible limit if needed.

### Task 4: Implement App Root and Navigation
**Intent:** Create App component with header, date selector, navigation bar, and page switching.
**Inputs:** `build-legacy/web/index.html`, `build-legacy/web/style.css`.
**Outputs:** `react-app/src/App.jsx`, `react-app/src/App.css`.
**External Interfaces:** `dataService.fetchDimensions`.
**Environment & Configuration:** None.
**Procedure:**
1. Implement `App.jsx`: call `fetchDimensions()` on mount; manage state: `activePage`, `selectedDate`, `dimensions`, `loading`.
2. Render header matching legacy: title "📊 Анализатор на Цени", subtitle, date selector (formatted DD.MM.YYYY), nav buttons.
3. Port `style.css` to `App.css`, preserving all class names, colors (`#667eea`, `#764ba2`), gradients, and responsive rules.
4. Conditionally render page components based on `activePage`.
5. Pass `selectedDate`, `dimensions` as props to page components.
**Done Criteria:** App renders with header, nav, and page switching; visual design matches legacy.
**Dependencies:** Tasks 1, 3.
**Risk Notes:** None.

### Task 5: Implement Home Page Component
**Intent:** Render landing page with feature cards and CTA section.
**Inputs:** `build-legacy/web/index.html` (home section HTML).
**Outputs:** `react-app/src/components/HomePage.jsx`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Create `HomePage` functional component.
2. Port landing content (heading, intro text, 3 feature cards icons/titles/descriptions, CTA) from legacy HTML.
**Done Criteria:** Home page renders with all 3 feature cards and CTA section.
**Dependencies:** Task 4.
**Risk Notes:** None.

### Task 6: Implement Report 1 Component
**Intent:** Render average price by category for selected city as a horizontal bar chart.
**Inputs:** Legacy `generateReport1` / `renderBarChart` logic; `dataService.fetchReport1`.
**Outputs:** `react-app/src/components/Report1.jsx`.
**External Interfaces:** `dataService`.
**Procedure:**
1. Create `Report1` component with city select dropdown.
2. On city selection: call `fetchReport1`; store aggregated results in state.
3. Render horizontal bar chart using same CSS structure as legacy (`chart-bar`, `chart-bar-label`, `chart-bar-visual`, `chart-bar-value`).
**Done Criteria:** Bar chart renders on city selection; bar widths proportional to avg price; price shown as `X.XX лв`.
**Dependencies:** Tasks 3, 4.
**Risk Notes:** None.

### Task 7: Implement Report 2 Component
**Intent:** Render products table filtered by city and category.
**Inputs:** Legacy `generateReport2` / `renderProductTable` logic; `dataService.fetchReport2`.
**Outputs:** `react-app/src/components/Report2.jsx`.
**Procedure:**
1. Create `Report2` with city and category select dropdowns.
2. On both selected: call `fetchReport2`; render products table.
3. Table columns (matching legacy): product name, calculated price (min of retail/promo), retail price, promo price, store, chain, date.
**Done Criteria:** Table renders with all 7 columns when both dropdowns are selected.
**Dependencies:** Tasks 3, 4.
**Risk Notes:** None.

### Task 8: Implement Report 3 Component
**Intent:** Render locations and products table filtered by category.
**Inputs:** Legacy `generateReport3` / `renderLocationTable` logic; `dataService.fetchReport3`.
**Outputs:** `react-app/src/components/Report3.jsx`.
**Procedure:**
1. Create `Report3` with category select dropdown.
2. On category selected: call `fetchReport3`; render location+product table.
3. Table columns (matching legacy): city, product name, calculated price, retail price, promo price, store, chain.
**Done Criteria:** Table renders with all 7 columns on category selection.
**Dependencies:** Tasks 3, 4.
**Risk Notes:** May be slow for high-volume categories; show a loading indicator.

### Task 9: Validate Build and Run Tests
**Intent:** Confirm all success criteria and test cases pass.
**Inputs:** Completed `react-app/` implementation.
**Outputs:** Test results; `react-app/dist/`.
**External Interfaces:** npm, Node.js, Supabase (for UAT scenarios).
**Environment & Configuration:** `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `react-app/.env`.
**Procedure:**
1. Run `npm install` in `react-app/`; verify 0 errors.
2. Run `npm run build`; verify exit 0 and `dist/` exists.
3. Verify `netlify.toml` and `.env.example` content (T2, T3, T4, T5).
4. Scan `react-app/src/` for hardcoded credentials (T3).
5. Run `npm run preview`; manually execute UAT scenarios T6–T9 from `UAT_scenarios.md`.
**Done Criteria:** All T1–T10 test cases pass.
**Dependencies:** Tasks 1–8.
**Risk Notes:** Build will fail at runtime (not compile time) if `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` are absent or wrong.

### Task 10: Update Documentation
**Intent:** Update `context.md` to reflect the new React frontend component.
**Inputs:** Completed `react-app/`; `.aib_memory/context.md`.
**Outputs:** Updated `.aib_memory/context.md`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add `react-app/` to the Architecture section of `context.md` (component description, technology stack, Netlify deployment target).
2. Note Supabase anon key access pattern in Security section.
3. Update developer setup to include React app startup steps.
**Done Criteria:** `context.md` reflects all introduced changes without stale references.
**Dependencies:** Tasks 1–8.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Add `react-app/` to Architecture and Technology Stack sections; note Netlify deployment and Supabase anon-key access pattern; update Developer Setup.

## Questions & Decisions

*(none — all decision points resolved autonomously during analysis; see analysis.md for documented reasoning)*

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/` (new directory) | Created | Root folder for all React app files |
| `react-app/package.json` | Created | NPM project configuration with React, Vite, Supabase client |
| `react-app/vite.config.js` | Created | Vite build tool configuration |
| `react-app/index.html` | Created | Vite entry HTML |
| `react-app/netlify.toml` | Created | Netlify deployment configuration (build command, publish dir) |
| `react-app/.env.example` | Created | Environment variable template (no real credentials) |
| `react-app/src/main.jsx` | Created | React app entry point |
| `react-app/src/App.jsx` | Created | Root app component with navigation and date selector |
| `react-app/src/App.css` | Created | Global CSS ported from `build-legacy/web/style.css` |
| `react-app/src/index.css` | Created | Base CSS reset |
| `react-app/src/lib/supabase.js` | Created | Supabase client singleton |
| `react-app/src/lib/dataService.js` | Created | Data-fetching service functions for all reports |
| `react-app/src/components/HomePage.jsx` | Created | Landing page with feature cards |
| `react-app/src/components/Report1.jsx` | Created | Average price by category component |
| `react-app/src/components/Report2.jsx` | Created | Products by city and category component |
| `react-app/src/components/Report3.jsx` | Created | Locations and products by category component |
| `build-legacy/web/index.html` | Read-only dependency | Reference for HTML structure and Bulgarian text content |
| `build-legacy/web/style.css` | Read-only dependency | Reference for all visual styling and CSS classes |
| `build-legacy/web/script.js` | Read-only dependency | Reference for report logic, data enrichment, and rendering |
| `.aib_memory/context.md` | Modified | Add React frontend component to Architecture section |

## Internal Review of Request and Product Docs

- Ambiguity: `input.md` — "similar functionality" does not specify whether day-1/day-2 lookback prices from `fact_prices_lookback` should be shown. Resolved: excluded from scope by referencing legacy app behavior, which does not display them.
- Missing info: `build-legacy/web/script.js` — references `import DimensionLoader from './dimension-loader.js'` but `dimension-loader.js` does not exist in `build-legacy/web/`. Legacy app was likely incomplete or dependent on a build step. React app replaces this abstraction with direct Supabase queries.
- Missing info: `context.md` — does not confirm whether FK constraints are defined in the Supabase DDL created by `load_supabase.py`. Assumption A4 covers the workaround (client-side dim_store lookup rather than server-side FK join).
- Cross-ref issue: `context.md` → `load_supabase.py` inserts only the latest local fact date not yet in Supabase per run. Supabase may have fewer fact dates than the local 63-file dataset. The React app works with whatever dates are present in `dim_date` (already correct by design).
- OK: Success criteria are precise and testable against observable outcomes.
- OK: `build-legacy/web/style.css` provides a complete visual design reference for the React port.
- OK: Supabase schema dimensions and fact table columns are fully documented in `context.md`.
