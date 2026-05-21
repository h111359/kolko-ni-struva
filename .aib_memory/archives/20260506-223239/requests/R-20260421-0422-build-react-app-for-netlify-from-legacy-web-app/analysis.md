# Analysis: R-20260421-0422 — Build React app for Netlify from legacy web app

## Executive Summary

- **Request ID:** R-20260421-0422

- **Title:** Build React app for Netlify from legacy web app

- **Purpose:** Replace the legacy vanilla JS static-file web app (`build-legacy/web/`) with a React + Vite application that reads price data directly from the Supabase-hosted star-schema database and can be deployed to Netlify without any local file distribution.

- **Scope summary:** A new `react-app/` subfolder is created at workspace root. It contains a Vite-bootstrapped React 18 application with full styling parity to the legacy app, four page views (Home, Report 1, Report 2, Report 3), a date selector, city and category filters, and a Supabase data service layer. No changes to ETL scripts or database schema are made.

- **Key risk:** Supabase Row Level Security (RLS) configuration is not documented in context.md. If all star-schema tables are not readable by the anon key, the app will appear empty. This must be validated before deployment.

- **Key architectural decision:** Dimension tables (small: 266 to 4,824 rows) are loaded fully into client memory on app startup. Fact queries are filtered server-side by `date_key` and `store_key` set, then aggregated client-side. This avoids needing Supabase RPC functions and FK constraints, which are not documented as existing.

- **`request.md` updates this run:** Sections `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` added.

- **UAT scenarios:** Visual and interactive tests requiring browser validation are documented in `UAT_scenarios.md` in this request folder.


## Domain Knowledge Essentials

**Business terminology:**

- **kolkostruva.bg:** Bulgarian government retail price transparency portal. Companies are legally required to report daily prices; archives are published as ZIP downloads at `/opendata`.

- **EKATTE:** Bulgarian national administrative-territorial code registry. Each settlement (city, village, district) has a unique EKATTE code used as the natural key in `dim_settlement`.

- **UIC (ЕИК):** Bulgarian company identification number. Used as the natural key in `dim_company`.

- **Star schema:** A dimensional data warehouse pattern with one central fact table and multiple dimension tables. The fact table (`fact_prices`) holds numeric measures (prices); dimension tables hold descriptive attributes (product name, city name, category name, etc.).

- **Retail price / Promo price:** `retail_price` is the standard shelf price; `promo_price` is a promotional price (empty when no promotion applies). Effective/calculated price = `min(retail_price, promo_price)` when promo is present and non-zero.

**Impacted roles/personas:**

- **End users (price analysts / general public):** Browse and compare retail prices by city, category, and date via the web interface.

- **Data engineers:** No direct impact — ETL pipeline unchanged.

**Business processes touched:**

- Price browsing and comparison (4 report views).
- Date-based time series exploration (date selector).

**Acceptance impact:** Successful deployment delivers the existing analysis capability to a wider audience via a public Netlify URL, removing the requirement to run a local Python ETL environment simply to view data.


## Technical Knowledge & Terms

**Technologies and components involved:**

- **React 18:** Component-based JavaScript UI library. Functional components with `useState`, `useEffect` hooks. No class components.

- **Vite:** Fast ES-module build tool and dev server for modern web apps. Replaces the deprecated `create-react-app`. Entry point is `index.html`; outputs to `dist/`. Environment variables accessed via `import.meta.env.VITE_*`.

- **@supabase/supabase-js v2:** Official JavaScript client for Supabase. Provides `createClient(url, anonKey)` returning a client with `.from(table).select().eq().in().range()` query builder.

- **Supabase:** Hosted PostgreSQL with a REST API layer (PostgREST) and an auto-generated JavaScript client. Tables in the star schema are directly queryable via the client. Row Level Security (RLS) controls which rows the anon key can read.

- **Netlify:** Static site hosting platform. Reads `netlify.toml` for build configuration. Supports SPA routing via redirect rules. Build command: `npm run build`; publish directory: `dist`.

- **PostgREST row limit:** Supabase PostgREST returns a default maximum of 1,000 rows per request unless `.range()` or `.limit()` is used explicitly. Must be handled for large result sets.

- **VITE_ prefix:** Vite exposes only environment variables prefixed with `VITE_` to client-side code. Variables without this prefix are server-only and inaccessible in the browser bundle.

**Data models involved:**

- `dim_date` (~63 rows): `date_key, date, year, month, day, weekday`
- `dim_settlement` (266 rows): `settlement_key, ekatte_code, settlement_name`
- `dim_category` (369 rows): `category_key, category_code, category_name`
- `dim_product` (118,281 rows): `product_key, product_code, product_name` — **must not be fully loaded**
- `dim_store` (4,824 rows): `store_key, store_name, settlement_key, company_key` — loaded fully
- `dim_company` (217 rows): `company_key, uic, company_name`
- `fact_prices`: `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price` — ~1.1–1.5M rows per date; queried with filters

**Non-functional attributes:**

- **Performance:** Dimension data loaded once on startup (< 10K rows total, excluding `dim_product`). Fact queries filtered to subset per report; expected result sizes 100–50K rows depending on city/category selectivity. Pagination needed for Report 3 (all-cities query for popular categories).

- **Security:** Supabase anon key is embedded in the browser bundle. This is by design (it is a public-safe read-only key). No secret keys should appear in source code. Supabase RLS is the access control boundary.

- **Reliability:** No server-side logic to fail. Supabase downtime would render the app unable to load data; graceful error states needed.

**Evidence log:**

| Evidence | Implication |
| --- | --- |
| `build-legacy/web/script.js` loads `data.csv` + custom `DimensionLoader` | React app must replicate the same enrichment logic (dim JOIN), but with Supabase queries instead of static files |
| `build-legacy/web/style.css` uses classes `chart-bar`, `chart-bar-visual`, `chart-bar-value` | These CSS class names must be preserved in the React port to match visual output |
| `context.md`: `dim_store` has 4,824 rows; `dim_settlement` 266 rows | Both fit comfortably in client memory; loading them once on startup is feasible |
| `context.md`: `dim_product` has 118,281 rows | Too large to load on startup; product names fetched as part of filtered fact queries only |
| `context.md`: `load_supabase.py` inserts only the latest local fact date per run | Supabase may have fewer dates than local `data/schema/facts/`; date selector shows only what is in `dim_date` in Supabase |
| `context.md`: FK constraints between fact_prices and dim_store not explicitly documented | Client-side JOIN (using cached dim_store) is safer than relying on PostgREST FK-based nested SELECT |
| `script.js` references `import DimensionLoader from './dimension-loader.js'` | `dimension-loader.js` does not exist in `build-legacy/web/`; legacy app was incomplete/required a build step not preserved |

**Files read for this analysis:**

- `build-legacy/web/index.html`
- `build-legacy/web/style.css`
- `build-legacy/web/script.js`
- `.aib_memory/context.md`
- `.aib_memory/references.md`
- `.aib_brain/Concepts.md`
- `.aib_brain/conventions/analysis-convention.md`
- `.aib_brain/conventions/request-convention.md`


## Research Results

**Pattern scan — comparable prior solutions and organizational standards:**

1. **Legacy app data flow pattern:** The `build-legacy/web/script.js` implements a dimension-enrichment pattern (equivalent to a client-side star schema JOIN) on a flat fact CSV file. The React app inherits this pattern but replaces the flat CSV with Supabase queries. The three report types (aggregate bar chart, filtered product table, filtered location table) map directly onto three query patterns: GROUP BY category, SELECT with city+category filter, SELECT with category filter.

2. **Missing dimension-loader.js:** The `import DimensionLoader from './dimension-loader.js'` in `script.js` references a non-existent file. The legacy app was either never functional as a standalone deployment or required a bundling step that produced a combined JS. The React app does not inherit this gap — it implements the dimension-loading logic internally in `dataService.js`.

3. **Supabase query strategy (no FK constraints assumed):** Since FK constraints are not documented as created in `load_supabase.py` DDL, nested PostgREST selects (which require declared FK relationships) may not work. The safer pattern is: load all dim tables on startup (except `dim_product`), filter fact queries by `date_key` + derived `store_key` set, then JOIN client-side. This is consistent with the original legacy app's client-side JOIN approach.

4. **Date formatting:** The legacy formats dates as `DD.MM.YYYY` in the selector dropdown using a `formatDateBG()` function. The React app should replicate this in the date selector component.

5. **Calculated price logic:** The legacy `calculatePrice()` function returns `min(retail_price, promo_price)` when promo is non-null and non-zero, else `retail_price`. This same logic applies in the React app for Report 2 and Report 3 price display.


## External Benchmarking

**1. Vite + React + Supabase as the standard stack for Netlify SPA deployments**

This is the current industry-standard pattern for building read-only analytics SPAs deployed on Netlify. The `@supabase/supabase-js` v2 client is designed to be used directly in browser bundles with the anon key. The recommended Netlify configuration is a `netlify.toml` with `[build] command = "npm run build"` and `publish = "dist"`. This pattern is well-established and does not require server-side rendering.

- Key takeaway: Vite is the correct replacement for `create-react-app`; it is faster, lighter, and actively maintained.
- Applicability: Directly applicable. No adaptation needed.

**2. Client-side star-schema JOIN for small dimension tables**

In the business intelligence (BI) SPA pattern, small dimension tables (tens to low thousands of rows) are commonly loaded once into client memory and used for client-side lookups. This is the pattern used by tools like Apache Superset's single-page embeds and Metabase's public dashboard embeds when operating against materialized data. The threshold for "small enough to load fully" is typically under 50,000 rows per table.

- Key takeaway: Loading `dim_store` (4,824), `dim_settlement` (266), `dim_category` (369), `dim_company` (217) fully on startup is consistent with industry practice for BI SPAs.
- Applicability: Directly applicable. `dim_product` (118,281) exceeds the threshold and should not be loaded fully — product names must be fetched on demand or joined server-side.
- Adoption: Adopted for all dimension tables except `dim_product`.

**3. Netlify SPA redirect configuration**

Single-page applications with client-side routing require a catch-all redirect rule on Netlify to ensure deep links return the `index.html` rather than a 404. The standard `netlify.toml` pattern is:

```
[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

- Key takeaway: Without this redirect rule, refreshing a non-root URL on Netlify returns a 404.
- Applicability: Applicable. The React app uses client-side page switching (not URL routing), but the redirect is a safe-to-add defensive measure that follows standard practice.
- Adoption: Include the redirect rule in `netlify.toml`.

**4. VITE_ environment variable security model**

Vite's documentation and the broader React + Vite ecosystem community establish that public read-only API keys (Supabase anon key, public Stripe publishable key, etc.) are safe to include in client bundles via `VITE_` env vars, as their only capability is reading data that is intentionally public. The security boundary is enforced by the server (Supabase RLS), not by key secrecy.

- Key takeaway: Supabase anon key in `VITE_SUPABASE_ANON_KEY` is the correct and safe pattern.
- Applicability: Directly applicable. No adaptation needed.
- Rejection note: Using the Supabase service role key in a frontend app would be a critical security vulnerability; it must never appear in any `VITE_` variable.


## Minimal Spikes and Experiments

**Spike: Confirm legacy app is a genuine static file deployment**

- Hypothesis: `build-legacy/web/` is a complete, self-contained static web app deployable to Netlify as-is.
- Approach: Read all files in `build-legacy/web/` (index.html, style.css, script.js). Check for all imports and external dependencies.
- Outcome: `script.js` imports `DimensionLoader` from `./dimension-loader.js`, which does not exist in the directory. Three files are present; the referenced fourth file is absent. The app cannot run without `dimension-loader.js`.
- Conclusion: The legacy app is incomplete as a standalone deployment. The React app is a clean-room implementation that replicates the functionality without depending on the missing file.

**Spike: Verify dimension table sizes fit client-side loading constraints**

- Hypothesis: All dimension tables except `dim_product` can be loaded fully on startup without performance issues.
- Approach: Cross-reference row counts from `context.md` against typical browser memory constraints (~50 MB for small JSON payloads).
- Outcome: `dim_store` 4,824 rows × ~100 bytes/row ≈ 480 KB; `dim_settlement` 266 rows × ~50 bytes ≈ 13 KB; `dim_category` 369 rows × ~50 bytes ≈ 18 KB. `dim_product` 118,281 rows × ~80 bytes ≈ 9.5 MB — borderline but exceeds the target for startup load.
- Conclusion: All dim tables except `dim_product` can be loaded fully. `dim_product` should be fetched on-demand or via server-side join.

**Spike: Assess Supabase anon key access model for analytics tables**

- Hypothesis: The star-schema tables in Supabase are accessible with just the anon key (no login required) because they contain public government open data.
- Approach: Reviewed Supabase documentation on RLS and checked context.md for any mention of RLS setup in `load_supabase.py`.
- Outcome: `context.md` documents that `load_supabase.py` creates tables and upserts data, but does not mention RLS policies. No `GRANT` or `CREATE POLICY` statements are referenced. In Supabase, when RLS is enabled on a table with no permissive policies, the anon key receives zero rows. When RLS is disabled, anon key can SELECT freely.
- Conclusion: The operator must verify RLS state. If tables have RLS enabled with no permissive policy, they will need to add `CREATE POLICY ... USING (true)` for SELECT access. This is flagged as Assumption A2 — if false, the app will appear empty.


## AI Copilot Suggestions

**Observation 1 — Supabase RLS configuration is an unverified prerequisite that will silently break the app**

The entire app depends on Supabase tables being readable with the anon key. If RLS is enabled with no permissive SELECT policy (the Supabase default when creating tables programmatically without explicit policy setup), every query returns zero rows with no error message. The app will render "Няма данни за показване" everywhere, which will look like a data problem rather than a permissions problem. This is a common point of confusion for developers new to Supabase.

- Suggestion: Before or as part of Task 1, add a Supabase SQL migration snippet to the repository (e.g., `supabase-setup.sql` or documented in README) that grants SELECT to `anon` on all star-schema tables, or that creates permissive RLS policies. This makes the prerequisite explicit and repeatable.

**Observation 2 — Report 3 with a popular category may load tens of thousands of rows**

Report 3 queries `fact_prices` filtered only by `date_key` and `category_key` — no city filter applied. A popular category may have tens of thousands of rows for a single date (e.g., a broad food category across 266 settlements). This query can be slow and may hit Supabase's row cap.

- Suggestion: In the data service implementation, add a hard limit of 5,000 rows for Report 3 with a visible user notification ("Showing top 5,000 results, sorted by price") rather than silently truncating or erroring. If the request is extended in the future to support filtering by city in Report 3, this limit becomes less necessary.

**Observation 3 — The scope is well-defined but the app will have no loading indicator infrastructure**

The legacy app sets `document.body.style.cursor = 'wait'` as a crude loading indicator. A React app should use proper loading/error state management, but the request scope is "similar functionality" which might lead to a minimal implementation that shows blank screens during async fetches.

- Suggestion: Budget time in each report component for a `loading` boolean and a simple "Зарежда се..." (Loading...) text placeholder. This is a small implementation detail that significantly improves perceived UX and is consistent with "similar functionality" expectations.

**Observation 4 — Scope note: this is a medium-complexity port with one architectural uplift**

The scope is appropriately sized. The UI port is straightforward (3 reports + 1 landing page). The architectural uplift (replacing local file fetching with Supabase queries) is the only genuine complexity. The risk is concentrated in two areas: the Supabase anon key / RLS setup, and the Report 3 query volume. Both are flagged in Assumptions A2 and A4. The scope does not appear inflated; no simplification opportunity presents itself.


## Testing

- T1 — React app build: Run `npm run build` in `react-app/`. Expected outcome: Exit code 0; `react-app/dist/` directory created with `index.html` inside.

- T2 — Source files exist: Verify presence of `react-app/src/lib/supabase.js`, `react-app/src/lib/dataService.js`, `react-app/src/App.jsx`, `react-app/src/components/HomePage.jsx`, `react-app/src/components/Report1.jsx`, `react-app/src/components/Report2.jsx`, `react-app/src/components/Report3.jsx`. Expected outcome: All 7 files present.

- T3 — No hardcoded credentials: Run `grep -rE "supabase\.co|eyJ[a-zA-Z0-9_-]" react-app/src/` (matches Supabase URLs and JWT-format tokens). Expected outcome: Zero matches.

- T4 — netlify.toml correctness: Read `react-app/netlify.toml`; verify `command` contains `npm run build` and `publish` contains `dist`. Expected outcome: Both values present as specified.

- T5 — .env.example keys present: Run `grep -c "VITE_SUPABASE_URL\|VITE_SUPABASE_ANON_KEY" react-app/.env.example`. Expected outcome: Output `2` (both lines present).

- T6 — Build idempotency: Run `npm run build` a second time without changes. Expected outcome: Exit code 0; `dist/` replaced without error.

- T7 — Date selector populated (UAT): Start app against Supabase; verify date selector shows at least one date. See UAT_scenarios.md — UAT-01.

- T8 — Report 1 bar chart renders (UAT): Select Report 1, select a city. See UAT_scenarios.md — UAT-02.

- T9 — Report 2 product table renders (UAT): Select Report 2, select city and category. See UAT_scenarios.md — UAT-03.

- T10 — Report 3 location table renders (UAT): Select Report 3, select a category. See UAT_scenarios.md — UAT-04.

- T11 — Visual design match (UAT): Verify header gradient, active nav button state, feature cards. See UAT_scenarios.md — UAT-05.

- T12 — Missing env vars handled gracefully: Run the dev server without `VITE_SUPABASE_URL` set (empty `.env`). Expected outcome: App renders with visible error or loading state; browser console shows a Supabase client initialization error; app does not crash silently or expose any unexpected data.


## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The architectural approach is sound: separate the ETL pipeline (unchanged) from the read-only analytics frontend (new). Using Supabase as the backend eliminates the need for a dedicated API layer and leverages the already-existing sync from `load_supabase.py`. Choosing Vite + React over vanilla JS is the correct modernization step given the planned scope; the legacy vanilla JS app's dependency on a missing `dimension-loader.js` demonstrates the fragility of the un-bundled approach.

The main architectural risk is the Supabase RLS state, which is not verified by any existing tooling. The client-side dimension JOIN strategy (avoiding FK-based PostgREST nested selects) de-risks the unknown FK constraint state, but it means the app loads dimension data eagerly on startup — adding latency before any report can be viewed. A preloader or skeleton state is needed.

- The `dim_product` (118K rows) boundary condition is correctly identified: not loading it fully on startup is the right call, but the implementation must ensure product names are fetched efficiently (batch by `product_key` IN clause or via Supabase nested select on the fact query).
- The Netlify SPA redirect rule is a necessary addition to `netlify.toml` for correct browser behavior on refresh or direct URL access.
- No backend changes are required, which is the simplest possible architecture given the existing Supabase setup.

### Product Owner

The request delivers clear business value: making the price analysis capability available to a broader audience without requiring local ETL setup. The four report types replicate the existing feature set, which has presumably been validated through prior use of the legacy app.

The success criteria are specific and testable, with good coverage of both deployment artifacts and functional outcomes. The scope boundary (no lookback prices, no auth, no mobile redesign) is appropriate for an MVP port.

- One acceptance criterion gap: there is no explicit criterion for appropriate handling of the "Supabase is unreachable" or "tables are empty" state. Users who encounter an all-empty app should receive a clear message, not blank pages.
- The date selector pre-selecting the newest date (SC-6) aligns with user expectation of "show me the latest data first".
- There is no success criterion for load time; for a production release, a lightweight performance target (e.g., "first meaningful paint under 5 seconds on a 10 Mbps connection") would be recommended.

### User

The experience mirrors the legacy app, which the user base is presumably familiar with. Date selection, city/category dropdowns, and automatic report refresh on selection match the legacy interaction model and minimize learning curve.

- Users unfamiliar with Supabase or the underlying data pipeline see no pipeline concepts exposed; the app presents a clean data browsing interface.
- A loading indicator during data fetch (currently not in scope but mentioned in AI Copilot Suggestions) is important for perceived responsiveness; without it, users may think the app is broken when waiting for Report 3 to load.
- Bulgarian-language labels (already present in the legacy HTML) should be preserved; the port should not inadvertently Anglicize UI text.
- The app's dependency on Supabase connectivity means it is only as available as Supabase. Users on an unstable connection may experience partial or empty results without a clear explanation.

### Security Officer

The use of Supabase anon key in the frontend is the standard accepted pattern for read-only public data. Supabase's RLS system is the correct enforcement boundary. The main risks are:

- **RLS not configured (unverified):** If the star-schema tables have no permissive SELECT policy for the anon role, the app leaks nothing but also provides no data. This is a misconfiguration risk, not a data exposure risk.
- **No service role key in frontend (mandatory):** The service role key bypasses all RLS. It must never appear in `VITE_*` variables or source code. The scope correctly excludes it.
- **No user input sent to the server:** All user input (city, category, date) selects from dropdowns populated from Supabase data; there is no free-text search that could be used for injection. Supabase parameterizes all queries via the client library.
- **`react-app/.gitignore` should exclude `.env`:** The `.env` file (containing the real Supabase URL and anon key) must not be committed to VCS. The `.env.example` is the only safe-to-commit credentials file.
- No authentication, PII, write operations, or sensitive data processing is in scope. Attack surface is low.

### Data Governance Officer

The data displayed in the React app originates from the Bulgarian government's public retail price mandate (kolkostruva.bg). It contains no personally identifiable information: only prices, product names, store names, and settlement names.

- **Data freshness:** The React app shows data as of the last `load_supabase.py` run. Users have no visibility into data staleness. A "data as of [date]" indicator (already partially served by the date selector) is the appropriate disclosure.
- **Data lineage:** Fact and dimension data flows from `kolkostruva.bg/opendata → data/raw/ → data/schema/ → Supabase (via load_supabase.py) → React app (via anon key)`. This lineage is preserved in `context.md`; the React app does not introduce any new lineage branches.
- **Data retention in browser:** Dimension and fact data loaded into the browser are held only in JavaScript memory for the session duration; no persistent local storage, cookies, or IndexedDB is used.
- **Compliance:** No regulatory requirements apply (GDPR etc.) given the absence of PII. The app processes publicly mandated government data.
- **Cross-reference accuracy:** The React app reads dimension names from Supabase tables, which were enriched by `src/transform.py` using the EKATTE and product-category nomenclature files. Accuracy of names depends on the quality of those nomenclature files and the `(unknown:<code>)` placeholder logic. No new data accuracy risk is introduced by the React app itself.
