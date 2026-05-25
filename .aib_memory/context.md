# Product Context

> **Auto-generated** by `aib-refresh-context.md` on 2026-05-25 10:30 EEST.
> Framework definition assets (`.aib_brain/`) are excluded by design — see `.aib_brain/` for AIB framework internals.
> This document is a synthesis of product documentation and workspace sources. It is fully replaced on each execution.

> Updated by R-20260430-0825: deleted `fact_prices`; `fact_prices_lookback` is now the sole Supabase fact table.
> Updated by R-20260430-1505: React app date selector now exposes all 3 dim_date rows (D, D-1, D-2); lookback price columns resolved client-side via `normalizeRow()`.
> Updated by R-20260506-2251: Report 2 bidirectional cross-filtering between settlement and category dropdowns; RecordDetailModal for per-row detail view with source file provenance; dim_file loaded at startup.
> Updated by R-20260507-2248: `prune_dim_category(conn)` added to `src/load_supabase.py`; `dim_category` in Supabase is now pruned to only `category_key` values referenced by `fact_prices_lookback` after each sync run.
> Updated by R-20260508-0743: `src/transform.py` now canonicalizes settlement EKATTE identifiers before `dim_settlement` upsert, and Report 1 disambiguates duplicate settlement labels with EKATTE in the dropdown.
> Updated by R-20260509-2012: React app now included a fifth page, `Лог на заявки`, which records browser-session Supabase table and RPC request intent across startup and report interactions for debugging; the page shows client-visible request metadata, not guaranteed exact backend SQL text.
> Updated by R-20260509-2113: `src/load_supabase.py` now provisions a persistent `backend_sql_audit_log` table in Supabase and records exact rendered backend SQL text for repository-owned PostgreSQL statements with timestamp, origin, and statement-count metadata; audited read queries log through sibling cursors so caller result sets and rowcount semantics remain intact; the log is pruned to a rolling 30-day window.
> Updated by R-20260512-0529: Reports 1, 2, and 3 now use Supabase RPC functions that push category aggregation and row enrichment into PostgreSQL, while the React app keeps lookback-date routing and only falls back to client-side processing when those RPCs are unavailable.
> Updated by R-20260512-2138: `react-app/src/App.css` now includes two responsive breakpoints — mobile (≤ 600px) and tablet (≤ 900px) — covering all five pages; Report 1 bar chart stacks to a column layout on mobile; Report 2 and Report 3 result tables are horizontally scrollable; header, landing page, and nav buttons adapt to narrow viewports.
> Updated by R-20260513-2123: The `Лог на заявки` debugging page has been replaced with a `Файлове` (Files) page; `QueryLogPage.jsx` and its tests were deleted; `FileDetailPage.jsx` was added displaying dim_file source files for the selected date with file name, date, and per-file record count (fetched via `fetchFileStats` in `dataService.js`); `queryLog.js` remains intact as active-but-UI-less infrastructure.
> Updated by R-20260514-2102: `FileDetailPage.jsx` file summary rows are now clickable; clicking a row mounts `FileRowsPanel.jsx`, which fetches and displays a paginated table of individual price-fact records for the selected file via `fetchFileRows` in `dataService.js`; a back/close button dismisses the panel and restores the summary table.
> Updated by R-20260515-1003: `FileRowsPanel.jsx` now supports client-side column sort (click header cycles asc → desc → unsorted, with `aria-sort` attribute and visual indicator) and per-column substring filter (filter input row in `<thead>`, case-insensitive match against display values, resets on file change); `App.css` now defines `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` fixing the overflow of the 12-column table and the file summary table, plus sort/filter CSS rules.
> Updated by R-20260516-1313: `FileRowsPanel.jsx` now loads all rows for the selected file in a two-pass client-side fetch (count then full set) and paginates, filters, and sorts them fully client-side so filter results span all rows rather than a single server page; day1/day2 column headers show actual calendar dates in DD.MM.YYYY format derived from `dims.dates`; the detail table uses compact CSS class `.file-rows-table`.
> Updated by R-20260517-1113: `FileRowsPanel.jsx` detail table rows are now clickable; clicking a row opens `FileRowDetailModal.jsx` — a new modal component showing all 12 display fields and all surrogate keys with Escape and backdrop-click dismissal; the two-button Previous/Next pagination strip has been replaced with a modern five-element bar (First «, Previous ‹, page indicator, Next ›, Last »).
> Updated by R-20260517-1244: `FileRowsPanel.jsx` now loads all rows for the selected file via `fetchAllFileRows` — a new exported function in `dataService.js` that pages through `SUPABASE_PAGE_SIZE` chunks until all rows are accumulated, replacing the previous single-range full-load call that was silently capped at 1,000 rows by the PostgREST `max_rows` default; `dim_product` is queried once in a single batch `.in()` call after all pages are loaded.
> Updated by R-20260518-1052: `fetchReport3` in `dataService.js` is now fully paginated via successive `.range()` calls so all rows for a category are loaded regardless of the PostgREST `max_rows` cap; `Report3.jsx` now includes per-column substring filter inputs, a five-element pagination bar, client-side `filteredRows` derivation via `useMemo`, and a record-count summary.
> Updated by R-20260518-1251: All currency notation (`лв`, `(лв)`) removed from every price display string and column header label across the React app; prices now display as bare two-decimal numeric values; `FileRowsPanel.test.jsx` column-label assertions updated to match.
> Updated by R-20260518-2134: "Ефективна цена" UI label removed from `FileRowsPanel.jsx`, `FileRowDetailModal.jsx`, and `RecordDetailModal.jsx`; `FileRowsPanel` now has 11 columns; `calculatePrice()` and the `calculatedPrice` data field are retained in `dataService.js` and continue to power the Report 2 and Report 3 "Цена" columns.
> Updated by R-20260525-0018: `VITE_SUPABASE_ANON_KEY` renamed to `VITE_SUPABASE_PUBLISHABLE_KEY` across all frontend code, tests, documentation, and configuration; `supabase.js` now rejects `sb_secret_...` and JWT-format keys via `credentialsError`; `SUPABASE_SECRET_KEY` placeholder added to `.env.example` server-side section.
> Updated by R-20260525-1012: `.gitignore` updated — `react-app/node_modules/`, `.netlify/`, `lab/`, `config.ini`, `netlify token.txt`, and curl scratch file excluded from tracking; `config.ini.example` added; `data/*` with `!data/nomenclatures/` and `!data/nomenclatures/**` exceptions added to track EKATTE reference files; git history rewritten to remove both credential files; README.md updated with fresh-install procedure.

---

## Product Identity

**Kolko Ni Struva ETL Pipeline + React Analytics App** is a two-layer product combining a local Python ETL pipeline with a hosted React analytics application, with no explicit version tag and an active operational status as of 2026-05-25.

The ETL pipeline downloads daily retail-price ZIP archives from the Bulgarian government open-data portal (kolkostruva.bg/opendata), transforms them into a seven-dimension star-schema dataset under `data/schema/`, and syncs the result to a Supabase-hosted PostgreSQL database. The React Analytics App is a React + Vite single-page application deployed on Netlify that queries the Supabase database directly and visualises retail price data in five views: Home, Report 1, Report 2, Report 3, and Files.

Primary actors are data engineers and analysts who run the ETL pipeline locally and public end users who access the hosted React app without authentication.

Production status is active: 63+ ZIP archives have been accumulated in `data/raw/`, approximately 82 million fact rows have been produced, and the React app is deployed and accessible via Netlify.

Scope boundaries are: no bulk historical backfill to the cloud database, no API exposure beyond Supabase RLS, no automated scheduling, no CI/CD pipeline, and no serverless functions in the React app.

---

## Domain Knowledge

The product operates in the retail price transparency domain, specifically in the sub-domain of government open-data acquisition, transformation, and public visualisation for Bulgarian consumers.

The Bulgarian government requires retail companies to report daily prices through the kolkostruva.bg portal, and this product automates the collection and structural transformation of those published archives. The React app exposes the resulting structured dataset to end users as an accessible web application.

Key business processes supported by the product are as follows.

- Daily automated download of government-published retail-price ZIP archives from the open-data portal, driven by `src/extract.py`.

- ETL transformation of raw CSV files inside each ZIP into a star-schema data layer, driven by `src/transform.py`.

- Cloud sync of the star-schema to a Supabase-hosted PostgreSQL database, driven by `src/load_supabase.py`.

- Interactive pipeline status and action menu exposing ETL state and operator actions through `menu.py`.

- Public-access retail price visualisation via the five-page React web app deployed to Netlify.

Organizational context is: an internal data engineering team owns and operates the ETL pipeline; the React app is publicly accessible by any end user via the Netlify-hosted URL.

Critical external dependencies are: kolkostruva.bg/opendata (Bulgarian government portal providing source ZIP archives), Supabase (hosted PostgreSQL plus REST API consumed by both the ETL sync and the React app), and Netlify (hosting for the React app static build). Availability and format of the government portal are outside the product team's control.

### Glossary

**Anon key**: The Supabase publishable API key (`VITE_SUPABASE_PUBLISHABLE_KEY`) that is safe for client-side browser use; distinct from the service_role key and must never grant privileged access.

**dim_***: The set of dimension tables in the star schema, comprising `dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, and `dim_file`.

**EKATTE**: The Bulgarian administrative code registry for territorial units (settlements), used as the canonical identity key for the settlement dimension.

**Lookback table**: `fact_prices_lookback`, the derived fact table that consolidates current-day (D), D-1, and D-2 retail and promo prices into a single denormalised row per product observation.

**RPC**: Remote procedure call function provisioned in PostgreSQL via PostgREST and invoked by the React app for server-side aggregation and filtering, reducing the volume of raw fact rows transferred to the browser.

**Star schema**: The dimensional data model produced by the ETL pipeline, consisting of seven dimension tables and one main fact table partitioned by date under `data/schema/facts/`.

**UIC (ЕИК)**: The Bulgarian company identification code used as the natural key for the company dimension (`dim_company`).

---

## Concepts

The product embeds several guiding principles that shape every design and implementation decision. They are listed alphabetically below.

- **Client-only frontend**: The React app is deployed as a static SPA that queries Supabase directly from the browser using the anon key, with no custom backend API layer or serverless functions.

- **Dimension from facts**: Dimension tables are populated from codes observed in the raw fact stream and enriched via static nomenclature files, rather than being pre-loaded from an authoritative master data source; unknown codes receive `(unknown:<code>)` placeholder entries.

- **Idempotent ETL**: Re-running any ETL step when inputs have not changed produces no new output and does not corrupt or duplicate existing data.

- **No-rejection policy**: Every row with a valid column count is retained by the pipeline; non-parseable prices are stored as NULL and unknown dimension codes produce placeholder entries rather than being silently discarded.

- **Publish-first then push**: Local CSV outputs are produced and verified before any Supabase sync, so the local star schema is always the authoritative source of truth and the cloud is a derived read replica.

- **Report-query pushdown**: Aggregation and enrichment operations for React reports are executed in PostgreSQL through named RPC functions, reducing browser memory use and repeated client-side iteration over `fact_prices_lookback`.

- **Rolling retention window**: Only the latest three local fact dates are retained in Supabase, keeping the React app date selector bounded and remote storage predictable.

- **Settlement canonicalization**: Raw settlement identifiers are normalized to their canonical EKATTE form before dimension natural-key assignment, collapsing encoding variants such as `068134` and `68134` into a single analytical identity.

- **Stdlib-only ETL core**: The Python transformation module (`src/transform.py`) and config module (`src/config_utils.py`) use only Python standard-library dependencies to minimize the install footprint for the ETL layer.

---

## Constraints & Assumptions

The product operates under the following technical and organizational constraints, and relies on the stated assumptions, each of which carries a risk if violated.

### Technical Constraints

- Python 3.9+ is required; the ETL transformation core (`src/transform.py`) and config module (`src/config_utils.py`) use only Python standard-library dependencies.

- The React app requires Node.js 18+ (Node 22 verified); it uses Vite 5 and `@supabase/supabase-js` v2 as its sole database client; no server-side rendering is used.

- Source ZIP filenames must follow the `YYYY-MM-DD.zip` naming convention; internal CSV files must use a 7-column Bulgarian retail-price format with comma or semicolon delimiters and UTF-8 encoding with optional BOM.

- The React app uses the Supabase anon key only; no service-role key is exposed to the browser; no backend or serverless functions are used.

- Git tracking was initialized as part of R-20260525-1012 and git history was rewritten to remove previously committed credential files; a tarball backup (`../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz`, 1.4 GB) remains available as the pre-git rollback mechanism.

### Organizational Constraints

- Source data format and availability depend on kolkostruva.bg; this dependency is entirely outside the product team's control.

- Supabase RLS policies must allow public SELECT on all star-schema tables and EXECUTE on all seven React-facing RPC functions for the React app to function correctly.

### Assumptions

The following assumptions were documented at the times indicated; risks are noted for each.

- A1: The Supabase instance has all star-schema tables populated by `src/load_supabase.py`; if false, app queries return empty data.

- A2: The Supabase anon key has SELECT access on all star-schema tables; if false, all queries return zero rows or HTTP 401/403.

- A3: All ZIPs follow `YYYY-MM-DD.zip` naming and internal CSVs use 7 columns with comma or semicolon delimiters and UTF-8 encoding; this assumption must be revisited if kolkostruva.bg changes its ZIP naming or CSV column layout.

- A4: `dim_settlement` (~266 rows), `dim_category` (~369 rows), `dim_store` (~4,824 rows), and `dim_date` (~63 rows) are small enough to load fully client-side without latency issues.

- A5: `dim_product` (~118,281 rows) is never fully loaded client-side; product names are fetched via batched `.in()` key lookups after all fact pages are accumulated.

- A6: `normalize_settlement_code()` collapses padded EKATTE variants before dimension natural keys are assigned; a future source-data variant outside current canonicalization rules could still produce duplicate analytical identities until the normalizer is extended.

- A7: The only authoritative source for which dates have fact data in Supabase is `fact_prices_lookback.date_key`; the `get_available_dates()` RPC reflects this; must be revisited if fact data is spread across multiple tables (per R-20260422-0902, R-20260430-0825).

- A8: The Supabase anon role has EXECUTE on all React-facing RPC functions granted by the `_CREATE_RPC_FUNCTIONS` DDL; the operator must re-run `python src/load_supabase.py` to provision these functions after each deployment (per R-20260422-0902, R-20260512-0529).

- A9: B-tree indexes on `fact_prices_lookback` are sufficient to keep filter and report RPCs within the Supabase free-tier statement timeout (~3s); if severe shared-compute contention occurs, additional pre-computed summaries are the escalation path (per R-20260429-0757, R-20260430-0825, R-20260512-0529).

### Validity Horizon

Key assumptions should be revisited under the following trigger conditions.

- Revisit A3 if kolkostruva.bg changes the ZIP naming convention or CSV column layout.

- Revisit A1 and A2 if Supabase RLS policies change or credentials rotate.

- Revisit A7 and A8 if the star schema is restructured or additional fact tables are introduced.

- Revisit the fallback-only browser path if report-RPC provisioning ever becomes operationally unreliable.

---

## Requirements

The product fulfils the following functional requirements (FR) and non-functional requirements (NFR), carried forward in full from prior planning records. All requirements retain their original detail.

### Functional Requirements

- FR-001: The pipeline MUST scrape kolkostruva.bg/opendata and download any new daily ZIP archives atomically to `data/raw/`, verifying ZIP integrity with `zipfile.is_zipfile()` before the atomic `.partial`-to-final rename (per `src/extract.py`, `README.md`).

- FR-002: The pipeline MUST transform all ZIPs in `data/raw/` into a star-schema data layer under `data/schema/`: seven dimension CSVs and date-partitioned fact CSVs in `data/schema/facts/`, plus a derived lookback fact table at `data/schema/fact_prices_lookback.csv` (per `src/transform.py`).

- FR-003: The pipeline MUST manage ETL configuration via `config.ini` with a `[settings]` section for user-tunable parameters and a `[state]` section for machine-written checkpoints; operators MUST be able to force re-download or re-process by editing state key values (per `src/config_utils.py`).

- FR-004: ETL runner scripts (`refresh.sh` on Linux; `refresh.bat` on Windows) MUST execute the full download-then-transform pipeline in sequence and exit non-zero on the first step failure.

- FR-005: An interactive terminal menu (`menu.py`) MUST provide numbered actions: 1) full refresh, 2) download only, 3) transform only, 4) update Supabase DB, 5) deploy React app to Netlify, 6) preview React app locally, 0) exit (per R-20260421-0348, R-20260421-0505, R-20260425-2155).

- FR-006: The Supabase sync module (`src/load_supabase.py`) MUST provision all eight analytical tables, the `backend_sql_audit_log` table, seven PostgreSQL RPC helper functions, and five B-tree indexes via idempotent DDL on every sync run (per R-20260420-1730, R-20260422-0902, R-20260509-2113, R-20260512-0529).

- FR-007: The Supabase sync MUST upsert all seven dimension CSVs via INSERT … ON CONFLICT DO UPDATE and MUST truncate then reinsert `fact_prices_lookback` on every sync run (per R-20260420-1730, R-20260430-0825).

- FR-008: The Supabase sync MUST log exact rendered backend SQL text for repository-owned PostgreSQL statements with timestamp, logical origin, and statement-count metadata in `backend_sql_audit_log`; audited read queries MUST use sibling cursors so caller result sets and rowcount semantics remain intact (per R-20260509-2113).

- FR-009: The Supabase sync MUST prune `dim_date` to the 3 newest local fact dates, prune `dim_category` to only the `category_key` values referenced by `fact_prices_lookback`, and prune `backend_sql_audit_log` rows older than 30 days on every sync run (per R-20260429-0825, R-20260507-2248, R-20260509-2113).

- FR-010: The React app MUST be deployable to Netlify from `react-app/dist/` and provide five pages: Home (landing), Report 1 (average price by category for a selected city with a horizontal CSS bar chart), Report 2 (products by city and category with a 7-column table, bidirectional cross-filtering, and a RecordDetailModal), Report 3 (locations and products by category with a 7-column table, per-column substring filter, a five-element pagination bar, and full result-set loading via paginated multi-pass fetch), and Files (source-file detail page with per-file record counts and a FileRowsPanel drill-down) (per R-20260421-0422, R-20260422-0902, R-20260506-2251, R-20260513-2123, R-20260518-1052).

- FR-011: The Files page FileRowsPanel MUST load all rows for the selected file via a multi-pass client-side paginated fetch (`fetchAllFileRows`) and display a compact 11-column table with fully client-side sort (cycling asc → desc → unsorted with `aria-sort` and visual indicator), per-column substring filter across all loaded rows, and a five-element pagination bar (per R-20260514-2102, R-20260515-1003, R-20260517-1244, R-20260518-2134).

- FR-012: FileRowsPanel day1 and day2 column headers MUST show actual calendar dates in DD.MM.YYYY format derived from `dims.dates`; each detail row MUST be clickable and MUST open `FileRowDetailModal.jsx` showing all 11 display fields and surrogate keys with Escape and backdrop-click dismissal (per R-20260516-1313, R-20260517-1113).

- FR-013: The React app date selector MUST show all 3 `dim_date` rows (D, D-1, D-2); D-1 and D-2 views MUST be synthesized client-side from lookback price columns in `fact_prices_lookback` via `normalizeRow()` (per R-20260430-0825, R-20260430-1505).

- FR-014: Reports 1, 2, and 3 MUST pass the selected lookback offset to Supabase RPCs so PostgreSQL performs aggregation and enrichment before results reach the browser; a browser-side fallback path MUST be retained for when RPCs are not yet provisioned (per R-20260512-0529).

- FR-015: The React app `supabase.js` singleton MUST reject keys starting with `sb_secret_` or matching the 3-segment JWT format by setting a non-null `credentialsError` and MUST NOT instantiate the Supabase client when `credentialsError` is set (per R-20260525-0018).

- FR-016: Menu option 6 MUST validate `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` before invoking `npm run build`, MUST start `npm run preview` non-blocking via `subprocess.Popen`, MUST poll `localhost:4173` until the server is ready, and MUST then open the browser (per R-20260426-2150).

- FR-017: `src/deploy_netlify.py` MUST auto-save interactively entered Netlify credentials to `.env` via `dotenv.set_key`, MUST build the React app via `npm run build`, and MUST deploy via `netlify deploy --prod --dir react-app/dist` with credentials injected in subprocess env (never as CLI args).

### Non-Functional Requirements

- NFR-001: The ETL pipeline MUST be idempotent; re-running when no new ZIPs exist MUST produce no new output and MUST not corrupt existing data.

- NFR-002: All file writes by the ETL pipeline MUST use a `.partial` temp-file renamed atomically on completion to prevent partial output files.

- NFR-003: All schema output files MUST be UTF-8 CSV (human-readable outputs).

- NFR-004: All Python ETL scripts MUST be compatible with Python 3.9+.

- NFR-005: HTTP download failures MUST be retried up to `max_retries` times with exponential backoff before the script exits non-zero.

- NFR-006: Supabase sync MUST be idempotent; re-running when the latest local fact date already exists in Supabase MUST exit cleanly without duplicating rows.

- NFR-007: Backend SQL audit records MUST include rendered SQL text, execution timestamp, logical origin, and statement-count metadata; audited read queries MUST preserve fetchable result sets by routing audit inserts through sibling cursors.

- NFR-008: The React app MUST NOT hardcode credentials in source files; browser-exposed environment variables MUST use the `VITE_` prefix; only the Supabase anon key is used client-side.

- NFR-009: `npm run build` MUST exit 0 and produce `react-app/dist/`; the build MUST be Netlify free-tier compatible.

- NFR-010: The React app MUST have a responsive layout via CSS media queries at ≤ 900px (tablet) and ≤ 600px (mobile); all five pages MUST be usable without horizontal overflow from 320px to 1920px viewport width; minimum touch target height is 44px for form controls on mobile.

- NFR-011: The React app date selector MUST show all 3 `dim_date` rows (D, D-1, D-2) and MUST synthesize D-1 and D-2 views client-side from lookback price columns without a second Supabase query.

- NFR-012: The React app Report 1 settlement dropdown MUST list every settlement with at least one store with data on the selected date and MUST disambiguate duplicate visible names with EKATTE suffixes.

- NFR-013: The React app Report 1 category chart MUST include all categories with at least one price observation with no silent truncation.

- NFR-014: Semantically identical EKATTE formatting variants MUST be canonicalized before `dim_settlement` and `dim_store` natural keys are assigned, preventing analytical splits such as `68134` versus `068134`.

### Known Priorities (MoSCoW)

Data correctness (no row rejection, no surrogate collision) and idempotency are Must-Have for the ETL layer. Visual fidelity to the legacy app, credential security, and complete result coverage without PostgREST `max_rows` truncation are Must-Have for the React app. Formal CI/CD, automated scheduling, and SLO targets are currently Won't Have.

---

## Architecture & Decisions

The product follows a local-first ETL-then-cloud architecture: local CSV outputs under `data/schema/` are always the authoritative analytical source of truth, and Supabase serves as a bounded read replica for the React app.

### High-Level Component Map

The system is composed of the following components, each with a single stated responsibility.

- `src/extract.py` — Scrapes the open-data index page, resolves new or force-scheduled ZIP URLs, and downloads them atomically to `data/raw/`; reads settings and state from `config.ini` and writes `last_downloaded_date` on success.

- `src/transform.py` — Reads all ZIPs from `data/raw/`, builds seven dimension tables from observed codes enriched by nomenclature files, writes date-partitioned fact CSVs to `data/schema/facts/`, and produces `data/schema/fact_prices_lookback.csv` via `build_lookback_table`.

- `src/config_utils.py` — Shared stdlib module providing `load_config()` and atomic `save_state()`; imported directly by both `extract.py` and `transform.py`.

- `src/load_supabase.py` — Loads `.env` via `python-dotenv`; provisions all star-schema tables, audit table, RPC functions, and indexes via idempotent DDL; upserts dimension CSVs; truncates and reinserts `fact_prices_lookback`; routes statements through `execute_sql()` and `execute_batch_with_audit()` so exact rendered SQL is persisted to `backend_sql_audit_log`; enforces rolling retention windows.

- `src/deploy_netlify.py` — Detects Netlify CLI availability; loads or interactively prompts for `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID`; auto-saves entered credentials to `.env`; builds and deploys the React app to Netlify.

- `menu.py` — Displays ETL statistics and provides a numbered action menu (1–6, 0 exit); invokes ETL scripts via `subprocess.run` in list form with no `shell=True`; option 5 passes through stdin for interactive credential prompts; option 6 validates env vars, starts `npm run preview` non-blocking, polls until ready, and opens the browser.

- `refresh.sh` / `refresh.bat` — Thin OS-native wrappers invoking `src/extract.py` then `src/transform.py`; `refresh.sh` detects and uses `venv/bin/python` when present.

- `menu.sh` / `menu.bat` — One-line OS-native wrappers invoking `menu.py`.

- React Analytics App (`react-app/`) — Vite-built React 18 SPA querying Supabase directly via `@supabase/supabase-js` v2; five pages deployed to Netlify from `react-app/dist/`; no serverless functions.

- `config.ini` — Single INI at project root with `[settings]` (user-tunable) and `[state]` (machine-written) sections.

- `data/schema/` — Seven flat dimension CSVs, 63+ date-partitioned fact CSVs under `data/schema/facts/`, and the derived lookback table.

- `data/raw/` — Write target for `src/extract.py`; not auto-pruned.

- `data/nomenclatures/` — Static EKATTE registry and product-category reference files consumed by `src/transform.py`.

### Key Integration Points

The following external integration points exist in the system.

- kolkostruva.bg/opendata (external, inbound to ETL): HTTPS download via HTML scraping and BeautifulSoup link resolution; the portal's availability and format are outside the product team's control.

- Supabase REST API (external, inbound to React app): `@supabase/supabase-js` v2 queries `dim_*` tables via PostgREST and invokes the seven named RPC functions; auth uses the anon key; RLS must allow public SELECT and anon EXECUTE on all RPC functions.

- Supabase PostgreSQL (external, inbound to ETL sync): direct PostgreSQL connection via `psycopg2-binary`; `DATABASE_URL` loaded from project-root `.env`.

- Netlify (external, hosting): `react-app/netlify.toml` configures `build.command = "npm run build"` and `publish = "dist"`; `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` must be set as Netlify site environment variables.

### Key Architectural Decisions

The following decisions are recorded in ADR style.

- ADR-01 (Date-partitioned fact table): `data/schema/facts/YYYY-MM-DD.csv` files (~54–78 MB each) were chosen over a single flat file (~3.4–4.9 GB) to keep outputs human-readable and manageable within the "no external dependencies" constraint.

- ADR-02 (Dimension from facts, no pre-load): Dimension tables are populated from codes observed in the fact stream and enriched via static nomenclature files; unknown codes receive `(unknown:<code>)` entries; this avoids a pre-load dependency on an external master data source and preserves all rows.

- ADR-03 (config.ini for ETL control): A single INI file with `[settings]` and `[state]` sections uses `configparser` from the Python 3.9+ standard library, eliminating an external config dependency.

- ADR-04 (No-rejection policy): All rows with a valid column count are retained; non-parseable `retail_price` values store NULL; this ensures no government-published row is silently discarded.

- ADR-05 (Stdlib-only Python ETL core): `src/transform.py` and `src/config_utils.py` use only Python stdlib to minimize the install footprint; external dependencies are confined to the download and sync modules.

- ADR-06 (Dual-platform OS launchers): `.sh` and `.bat` wrappers provide thin cross-platform ETL entry points without requiring platform detection inside Python scripts.

- ADR-07 (Client-only React app, Supabase direct): The React app queries Supabase from the browser using the public anon key; no backend or serverless functions are needed because all data is public-access government price data with no PII.

- ADR-08 (Report-query pushdown, R-20260512-0529): Category averaging for Report 1 and row enrichment for Reports 2 and 3 execute in PostgreSQL through report-oriented RPCs to reduce browser memory use and repeated client-side iteration over `fact_prices_lookback`.

- ADR-09 (RPC functions for date filter, cross-filter, and reports, R-20260422-0902, R-20260512-0529): Seven idempotent PostgreSQL functions (`get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, `get_settlements_for_category`, `get_report_1_category_prices`, `get_report_2_rows`, `get_report_3_rows`) are provisioned by `load_supabase.py` and granted EXECUTE to anon, allowing accurate filter sets and fully enriched report result sets without transferring large volumes of raw fact rows to the browser.

---

## Technical Design

The product is split into a Python ETL layer and a React frontend layer; the two layers share only the Supabase database as a communication boundary.

### Module Breakdown

The following modules and components make up the implementation.

- `src/extract.py` defines functions `setup_logging`, `fetch_page`, `parse_zip_links`, `existing_filenames`, `download_file`, and `main`; `BASE_DIR` resolves to the project root via `Path(__file__).resolve().parent.parent`.

- `src/transform.py` loads `config.ini`, reads `last_processed_date`, loads existing dimension CSVs, initializes nomenclature dicts, and initializes a rotating log; per ZIP it skips if the fact file already exists and no force trigger is set, then processes all CSVs, upserts all seven dimensions, and writes buffered fact rows atomically.

- `src/transform.py` key nomenclature functions: `load_settlement_names()` builds the EKATTE-to-name lookup from seven sources (primary JSON plus six extended NSI registry files); `resolve_settlement_name(code, lookup)` probes in three steps (exact → `code.zfill(5)` → `code.lstrip('0')`) and returns `(unknown:<code>)` if all probes fail.

- `src/transform.py` canonicalization: `normalize_settlement_code(code)` strips redundant leading zeros, preserves raion suffixes, and pads short numeric EKATTE values back to 5 digits; `patch_unknown_settlements(dim_path, lookup)` reads `dim_settlement.csv`, applies `resolve_settlement_name()` to every `(unknown:...)` row, and atomically rewrites the file preserving all surrogate keys.

- `src/config_utils.py` provides `load_config(config_path)` (reads or bootstraps INI with default `[settings]` and `[state]` sections) and `save_state(config, config_path, **kwargs)` (atomic INI write via `.partial` rename).

- `src/load_supabase.py` provides `create_tables(conn)` (idempotent DDL for all star-schema tables, audit table, migration blocks, RPC functions, and indexes), `execute_sql()` (single-statement audited execution via sibling cursor), and `execute_batch_with_audit()` (batched audited execution where each emitted page is persisted as one audit row).

- `src/load_supabase.py` pruning functions: `get_retained_local_dates(facts_dir, n=3)` returns the 3 newest local fact date strings; `get_date_keys_for_dates(conn, date_strings)` resolves their surrogate keys; `prune_dim_date(conn, retained_date_keys)` deletes `dim_date` rows outside the retained set; `prune_dim_category(conn)` deletes `dim_category` rows not referenced by `fact_prices_lookback`; `prune_sql_audit_log(conn, retention_days=30)` deletes audit rows older than 30 days.

- `menu.py` displays ETL statistics, numbered menu 1–6 / 0 exit, halts full refresh on first step failure, invokes scripts via `subprocess.run([sys.executable, ...], check=True)`, and uses no `capture_output` for option 5 to allow interactive credential passthrough; option 6 validates env vars via `python-dotenv` and `os.environ` before building, then polls `localhost:4173` with `_wait_for_server()` to eliminate the browser-open race condition.

- `src/deploy_netlify.py` defines `find_netlify_cmd`, `print_manual_instructions`, `get_credential`, `_save_credential_to_env`, `build_react_app`, `deploy_to_netlify`, and `main`; at module import it captures `_SHELL_ENV_KEYS` then calls `load_dotenv` without overriding shell values; falls back to manual instructions when Netlify CLI is absent.

- `react-app/src/lib/supabase.js` is the Supabase client singleton using `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`; it rejects keys starting with `sb_secret_` or matching the 3-segment JWT format by setting `credentialsError` with a descriptive message; no client is created when `credentialsError` is non-null (per R-20260525-0018).

- `react-app/src/lib/dataService.js` exports `fetchDimensions()`, `fetchSettlementsForDate()`, `fetchCategoriesForSettlement()`, `fetchSettlementsForCategory()`, `fetchReport1()`, `fetchReport2()`, `fetchReport3()`, `fetchFileStats()`, `fetchFileRows()`, `fetchAllFileRows()`, `formatDateBG()`, `calculatePrice()`, and `normalizeRow()`; a module-level `_dims` cache avoids re-fetching dimensions across calls.

- `react-app/src/lib/dataService.js` pagination: `fetchAllFileRows` and `fetchReport3` use multi-pass paginated fetches — a HEAD COUNT followed by successive `SUPABASE_PAGE_SIZE` (1,000) range calls until all rows are accumulated — bypassing the PostgREST `max_rows` default cap (per R-20260517-1244, R-20260518-1052).

- `react-app/src/lib/queryLog.js` is a session-scoped in-memory store for frontend-visible query activity; it is active-but-UI-less infrastructure retained after the Query Log page was removed in R-20260513-2123.

- `react-app/src/App.jsx` is the root component; it fetches dimensions on mount, manages `activePage`, `selectedDate`, `dimensions`, and `loadError` state, renders the header with title and five-button nav, and shows a disabled placeholder when `dimensions.dates` is empty.

- `react-app/src/components/Report1.jsx` renders a city selector populated via `fetchSettlementsForDate`, displaying `displayLabel` when duplicate settlement names need EKATTE disambiguation, and a horizontal CSS bar chart from `fetchReport1` with bar widths proportional to `avgPrice`.

- `react-app/src/components/Report2.jsx` renders city and category selectors with bidirectional cross-filtering (R-20260506-2251): selecting a settlement restricts the category dropdown via `fetchCategoriesForSettlement`, and selecting a category restricts the settlement dropdown via `fetchSettlementsForCategory`; if the current selection drops out of the re-filtered list it is auto-cleared; each 7-column table row opens `RecordDetailModal`.

- `react-app/src/components/RecordDetailModal.jsx` is a modal dialog (R-20260506-2251) displaying full enriched record details for a clicked Report 2 row; it closes via close button or Escape key and uses `role="dialog"` and `aria-modal="true"`.

- `react-app/src/components/Report3.jsx` renders a category selector and a 7-column location-plus-product table from `fetchReport3`, with per-column substring filter inputs, a five-element pagination bar, and a record-count summary (per R-20260518-1052).

- `react-app/src/components/FileDetailPage.jsx` filters `dims.files` by `zip_date` matching the selected date, fetches per-file record counts via `fetchFileStats`, renders a clickable summary table, and mounts `FileRowsPanel` for the selected file; it resets `selectedFile` on date change (per R-20260513-2123, R-20260514-2102).

- `react-app/src/components/FileRowsPanel.jsx` loads all rows via `fetchAllFileRows(fileKey, dims)` in a single `useEffect`, manages `sortConfig`, `filterValues`, `currentPage`, and `rows` state, derives `sortedRows` and `filteredRows` via `useMemo`, renders column headers as sortable `<th>` elements with `aria-sort`, a second filter-input `<tr>` in `<thead>`, and a five-element pagination bar (per R-20260515-1003, R-20260516-1313, R-20260517-1113, R-20260517-1244).

- `react-app/src/components/FileRowDetailModal.jsx` shows all 11 display fields and surrogate keys (`product_key`, `category_key`, `store_key`, `file_key`, `settlement_key`, `company_key`) for a clicked FileRowsPanel row; dismisses on Escape or backdrop click (per R-20260517-1113).

- `react-app/src/App.css` is a full port of the legacy CSS preserving all class names, hex colours (#667eea, #764ba2), gradients, and keyframe animations; it includes two responsive breakpoints (≤ 900px and ≤ 600px), `.table-scroll-wrapper { overflow-x: auto; width: 100%; }`, and sort/filter classes (per R-20260512-2138, R-20260515-1003).

### Key Algorithms and Processing Logic

The following algorithms are central to the product's operation.

- ZIP discovery: `parse_zip_links` parses kolkostruva.bg/opendata HTML via BeautifulSoup, extracts `.zip` hrefs, resolves relative URLs via `urllib.parse.urljoin`, and returns a sorted descending deduplicated list; ZIPs are verified with `zipfile.is_zipfile()` before the atomic rename.

- Incremental download with force re-download: ZIP filenames are compared against `data/raw/`; a file is scheduled if absent OR if its date string is greater than or equal to the `last_downloaded_date` override; writes proceed via `.partial` then atomic rename.

- Delimiter auto-detection: an initial comma-delimited parse is attempted; if the first data row has one column containing `;`, the file is re-read using `;` as the delimiter; BOM is stripped from header rows in both passes.

- Dimension upsert: at startup the existing dimension CSV is loaded into a `{natural_key: surrogate_key}` dict; new codes are assigned `max_key + 1`; the full dimension table is written atomically at end of each run; settlement natural keys are canonicalized before the upsert to collapse EKATTE encoding variants.

- React effective price calculation: `calculatePrice(row)` returns `min(retail_price, promo_price)` when `promo_price` is non-null and non-zero; otherwise it returns `retail_price`; this powers the "Цена" column in Reports 2 and 3.

- React dimension caching: `fetchDimensions()` stores its result in module-level `_dims`; subsequent calls return the cached object without re-fetching; `_resetDimsCache()` is exported as a test-only helper.

- React date selector via `lookbackColumnMap`: `fetchDimensions()` calls `get_available_dates()` in parallel with dimension table fetches; all `dim_date` rows are exposed in `dims.dates`; `currentDateKey` is derived from the RPC result using a PostgREST v10/v11 backward-compatibility guard; `lookbackColumnMap` is built positionally (index 0 → 'current', index 1 → 'day1', index 2 → 'day2') and degrades gracefully if the RPC is unavailable (per R-20260422-0902, R-20260430-0825).

- React settlement filter via RPC: `fetchSettlementsForDate(dateKey, dims)` resolves the offset from `dims.lookbackColumnMap`; for D-1/D-2 offsets it calls `get_settlements_for_date` with `dims.currentDateKey`; duplicate visible names receive `displayLabel` values suffixed with EKATTE; falls back to all settlements on RPC error (per R-20260508-0743).

- React Report 2 cross-filtering: `handleSettlementChange` calls `fetchCategoriesForSettlement` on settlement selection; `handleCategoryChange` calls `fetchSettlementsForCategory`; if the current selection drops out of the re-filtered list it is auto-cleared; date change resets both filter lists to their full defaults (per R-20260506-2251, Q002-A behavior).

- Multi-pass paginated fetch: `fetchAllFileRows` and `fetchReport3` issue a HEAD-only COUNT then loop with `SUPABASE_PAGE_SIZE` (1,000) per page until all rows are accumulated; for `fetchAllFileRows` a single batch `dim_product .in()` lookup is performed after all pages are loaded, replacing the previous approach silently capped at 1,000 rows by PostgREST `max_rows` (per R-20260517-1244, R-20260518-1052).

### Configuration and Parameterization

The product uses two configuration surfaces: `config.ini` for the ETL pipeline and `.env` for secrets and Vite build variables.

- `opendata_url` in `config.ini [settings]` defaults to the kolkostruva.bg open-data path and is tunable by the operator.

- `max_retries` in `config.ini [settings]` defaults to `3` and controls the HTTP download retry count.

- `retry_delay` in `config.ini [settings]` defaults to `10` seconds and serves as the exponential backoff base.

- `log_level` in `config.ini [settings]` defaults to `INFO`.

- `last_downloaded_date` in `config.ini [state]` is written by `extract.py` on success; set it manually to force re-download of a specific date range.

- `last_processed_date` in `config.ini [state]` is written by `transform.py` on success; set it manually to force re-process.

- `DATABASE_URL` in `.env` is required for ETL Supabase sync; no default; must be supplied by the operator.

- `NETLIFY_AUTH_TOKEN` in `.env` or shell env is required for Netlify deploy; auto-saved to `.env` on first interactive entry; shell env takes precedence over `.env`.

- `NETLIFY_SITE_ID` in `.env` or shell env is required for Netlify deploy; auto-saved to `.env` on first interactive entry; shell env takes precedence over `.env`.

- `VITE_SUPABASE_URL` in `.env` is required for the React build; exposed to the browser via Vite.

- `VITE_SUPABASE_PUBLISHABLE_KEY` in `.env` is the Supabase anon key; exposed to the browser via Vite; must not be a secret key or JWT-format key (enforced by `supabase.js`).

- `SUPABASE_SECRET_KEY` in `.env` is a server-side placeholder documented in `.env.example` for future use; it is not currently consumed by any Python module or script.

### Inter-Component Communication

ETL execution is batch sequential: `config_utils.py` is imported directly by ETL scripts; `menu.py` launches ETL scripts via `subprocess.run` in list form with no `shell=True`. React app data flow is unidirectional: `App.jsx` fetches dimensions once on mount and propagates `selectedDate` and `dimensions` props down to page components, which manage their own query and UI state locally.

---

## Data Architecture

The product ingests government-published retail price ZIP archives, transforms them into a seven-dimension star schema, and exposes the latest retained window via Supabase to the React app. No PII is processed at any stage.

### Data Sources

The following data sources are consumed by the product.

- kolkostruva.bg/opendata (primary, external): daily ZIP archives downloaded via HTTPS; owner is the Bulgarian government; format is ZIP containing 7-column UTF-8 CSV files with comma or semicolon delimiters; refresh cadence is daily; source availability is outside the product team's control.

- EKATTE nomenclature (`data/nomenclatures/cities-ekatte-nomenclature.json`): 5,256 entries with canonical 5-digit padded keys; static reference; primary settlement name lookup source consumed by `src/transform.py`.

- Sofia district nomenclature (`data/nomenclatures/Ekatte/sof_rai.json`): 38 Sofia sub-district codes; static reference; consulted as a secondary lookup source.

- Extended EKATTE registry files (`data/nomenclatures/Ekatte/ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`): full NSI EKATTE registry consulted as supplementary lookup sources after the primary file (per R-20260501-0003); `ek_raion.json` uses the `raion` field (e.g. `68134-04`) as key, all others use `ekatte`.

- Product categories (`data/nomenclatures/product-categories.json`): 101 category ID-to-name entries; static reference consumed by `src/transform.py`.

### Core Data Entities

The star schema consists of seven dimension tables and one main fact table; entity details are as follows.

- `dim_date` (`data/schema/dim_date.csv`): columns `date_key, date, year, month, day, weekday`; one row per calendar date; ~63 rows in the local dataset.

- `dim_company` (`data/schema/dim_company.csv`): columns `company_key, uic, company_name`; one row per UIC; ~217 rows.

- `dim_settlement` (`data/schema/dim_settlement.csv`): columns `settlement_key, ekatte, settlement_name`; one row per EKATTE code observed in facts; ~266 rows; canonical EKATTE codes assigned after `normalize_settlement_code()` processing.

- `dim_category` (`data/schema/dim_category.csv`): columns `category_key, category_code, category_name`; one row per category code observed in facts; ~369 rows; pruned in Supabase to only those referenced by `fact_prices_lookback`.

- `dim_product` (`data/schema/dim_product.csv`): columns `product_key, product_code, product_name`; one row per `(product_code, product_name)` pair; ~118,281 rows; never fully loaded client-side.

- `dim_store` (`data/schema/dim_store.csv`): columns `store_key, store_name, settlement_key, company_key`; one row per `(store_name, settlement_key, company_key)` triple; ~4,824 rows.

- `dim_file` (`data/schema/dim_file.csv`): columns `file_key, file_name, zip_date`; one row per company CSV inside each ZIP; ~13,089 rows; used for source-file provenance in RecordDetailModal and FileDetailPage.

- Partitioned fact table (`data/schema/facts/YYYY-MM-DD.csv`): columns `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price`; one row per product price observation; ~1.1–1.5 million rows per file; ~54–78 MB per file; 63+ files accumulated.

- Derived lookback fact (`data/schema/fact_prices_lookback.csv`): 11 columns including 4 lookback price columns for D, D-1, and D-2; one row per observation in the latest fact date D enriched with D-1 and D-2 prices; ~1.1–1.5 million rows; fully replaced on each transform run.

### Data Lineage Summary

The end-to-end data flow is as follows.

- kolkostruva.bg/opendata HTML is scraped by `src/extract.py` which downloads ZIP archives to `data/raw/YYYY-MM-DD.zip`.

- ZIP archives in `data/raw/` plus nomenclature JSON files in `data/nomenclatures/` are read by `src/transform.py`, which writes `data/schema/dim_*.csv`, `data/schema/facts/YYYY-MM-DD.csv`, and `data/schema/fact_prices_lookback.csv`.

- Star-schema CSV outputs in `data/schema/` are read by `src/load_supabase.py`, which upserts dimension data and syncs `fact_prices_lookback` to Supabase, also provisioning `backend_sql_audit_log` and seven RPC functions.

- Supabase data is queried directly by the React app deployed on Netlify, which delivers the analytics views to end users in the browser.

### Data Storage

Local and remote storage locations are described below.

- Raw staging (`data/raw/`): ZIP archives accumulate indefinitely; not auto-pruned by any pipeline step; excluded from VCS by `.gitignore`.

- Star-schema outputs (`data/schema/`): seven flat dimension CSVs and 63+ date-partitioned fact CSVs under `data/schema/facts/`; derived lookback table at `data/schema/fact_prices_lookback.csv`; committed to VCS via `.gitignore` exceptions.

- Supabase (cloud): eight analytical tables plus `backend_sql_audit_log`; seven RPC helper functions; four B-tree indexes on `fact_prices_lookback` (`idx_fact_prices_lookback_date_key`, `idx_fact_prices_lookback_date_store`, `idx_fpl_date_cat`, `idx_fpl_date_store_category`); one executed-at index on `backend_sql_audit_log`; `fact_prices` was deleted in R-20260430-0825.

- Nomenclatures (`data/nomenclatures/`): static lookup files that are never modified by any pipeline script; committed to VCS.

### Data Access Patterns

The React app loads small dimension tables (`dim_date`, `dim_settlement`, `dim_category`, `dim_store`, `dim_company`, `dim_file`) once at startup and caches them in module scope; the date list is filtered to fact-present dates via `get_available_dates()`; settlement lists per date are resolved via `get_settlements_for_date()`; Reports 1, 2, and 3 are fetched through RPCs that return grouped or enriched result sets keyed to the selected lookback offset. `dim_product` (~118K rows) is never fully loaded client-side; product names are fetched via batched `.in()` key lookups after all fact rows are accumulated. Analysts may also access `data/schema/` CSVs directly with tools such as DuckDB or pandas.

### Data Retention

Local raw ZIPs and fact CSVs accumulate indefinitely with no automated pruning. Remote Supabase retention is enforced on every sync run: `dim_date` is pruned to the 3 newest local fact dates, `dim_category` is pruned to only the category keys referenced by `fact_prices_lookback`, and `backend_sql_audit_log` is pruned to the last 30 days. After settlement canonicalization changes, operators must rebuild local schema outputs via `python3 src/transform.py` and re-run `python3 src/load_supabase.py` so `dim_settlement`, `dim_store`, and `fact_prices_lookback` are regenerated against the same canonical settlement identity before the React app reads Supabase again.

---

## Security & Compliance

The product processes publicly available Bulgarian government retail price data with no PII; the primary security concerns are preventing credential exposure in source control and preventing secret keys from reaching the browser.

### Authentication and Authorization

The ETL pipeline is a local batch script with no network-exposed service and no user authentication mechanism. The React app uses unauthenticated public access with the Supabase anon key loaded from `VITE_SUPABASE_PUBLISHABLE_KEY`. Supabase RLS must allow public SELECT on all star-schema tables; the anon role must have EXECUTE on all seven React-facing RPC functions provisioned by `_CREATE_RPC_FUNCTIONS` DDL.

### Data Protection

The following data protection measures are in place.

- ETL download uses HTTPS transport from kolkostruva.bg.

- Local storage is unencrypted; source data is publicly available government data with no PII collected or stored.

- `config.ini` contains no credentials and is excluded from VCS by `.gitignore`.

- `.env` (project root) contains all six environment keys and is excluded from VCS by `.gitignore`; git history was rewritten in R-20260525-1012 to remove previously committed credential files.

- `.env.example` is committed and contains only placeholder values, serving as the single consolidated credential template.

- `backend_sql_audit_log` stores fully rendered SQL text issued by `src/load_supabase.py`; operators should treat it as sensitive operational telemetry because literal values from ETL upserts and refresh statements are persisted there.

### Secrets Management

Six environment keys are consolidated into a single project-root `.env` file. `DATABASE_URL` is used by the Python ETL sync to Supabase; `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` are used for Netlify deployment; `SUPABASE_SECRET_KEY` is a server-side placeholder not currently consumed by any module; `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` are used by the React frontend via Vite build. In Netlify production, credentials must be injected via Netlify site environment variables and never committed. Credential loading precedence for Netlify deploy is: shell environment variable (highest) → project-root `.env` (via `python-dotenv`) → interactive prompt (auto-saved to `.env` for future runs).

### Regulatory and Compliance Requirements

No explicit compliance framework applies. The pipeline and app process publicly available government retail price data; no PII is collected or stored, and no GDPR, SOC2, or HIPAA obligations have been identified.

### Known Security Considerations

The following security considerations are documented for operator awareness.

- Download URLs are resolved from the trusted kolkostruva.bg HTML source; no ZIP content hash verification is performed beyond `zipfile.is_zipfile()`.

- `subprocess` calls in `menu.py` use list-form with no `shell=True`, eliminating shell injection risk from any operator-controlled inputs.

- The React app has no hardcoded credentials; the anon key is public-safe by Supabase design and is validated by `supabase.js` to reject secret and JWT-format keys before client instantiation.

- RPC functions use `SECURITY INVOKER` (default); the anon role is explicitly granted EXECUTE; there is no privilege escalation path from the React app.

- Netlify deploy credentials are passed to subprocess via environment dict, not as CLI args, so they are not visible in process listings or logs.

- Netlify credentials auto-saved to `.env` use default file permissions of 0644 on Linux; `chmod 0600 .env` is recommended on shared machines.

---

## Operations

The product is operated manually; no automated scheduling or CI/CD-triggered deployment is configured.

### Running the Pipeline

The following commands cover the primary operational workflows.

- Full ETL on Linux: `./refresh.sh`.

- Interactive menu on Linux: `./menu.sh` or `python menu.py`.

- Supabase sync only (requires `.env` with `DATABASE_URL`): `python src/load_supabase.py`.

- Netlify deploy (interactive; prompts for credentials if env vars are not set): `python src/deploy_netlify.py` or menu option 5.

- Local production-like preview: menu option 6 or manually via `cd react-app && npm run build && npm run preview`; local URL is `localhost:4173`.

### Running and Deploying the React App

Local development requires running `npm run dev` from `react-app/` after `npm install` and copying `.env.example` to `.env` with real credentials. Production build is `npm run build` from `react-app/`, which produces `react-app/dist/`. Netlify deployment is configured via `react-app/netlify.toml` with `build.command = "npm run build"` and `publish = "dist"`; `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` must be set as Netlify site environment variables.

### Config Control

The following overrides are available to operators.

- To force re-download: set `[state] last_downloaded_date = YYYY-MM-DD` in `config.ini` to a date before the desired range.

- To force re-process: set `[state] last_processed_date = YYYY-MM-DD` in `config.ini` to a date before the desired range.

- After settlement-key normalization changes: run `python3 src/transform.py` then `python3 src/load_supabase.py` to rebuild local dimensions and re-sync Supabase before validating Report 1 in the React app.

- `config.ini` is bootstrapped automatically with default values on first run via `config_utils.load_config()`.

### Logging and Observability

`src/transform.py` writes `logs/transform_YYYYMMDD_HHMMSS.log` (one per run) and `data/quality/report_YYYYMMDD_HHMMSS.csv` (quality report for each transform run). The React app emits browser console warnings when RPC functions are not yet provisioned in Supabase. No monitoring dashboards or alerting thresholds are configured.

### Known Operational Risks

The following operational risks are documented with their mitigations.

- External portal availability: `extract.py` retries up to `max_retries` times then exits non-zero; no automated recovery after exhausted retries is implemented.

- Raw data accumulation: `data/raw/` and `data/schema/facts/` are not auto-pruned and will grow indefinitely without manual operator intervention.

- Supabase anon read access: if RLS blocks public SELECT, all React app queries return empty data with no visible error to the end user.

- RPC functions not yet provisioned: if `load_supabase.py` has not been re-run after a React-facing RPC change, the app falls back to slower browser-side processing and emits a console warning; no data is lost.

- Stale remote settlement dimensions: after a settlement-normalization change, the deployed React app may still show duplicate settlement labels until `src/load_supabase.py` is re-run against Supabase.

- Supabase statement timeout (free tier ~3s): mitigated by four B-tree indexes on `fact_prices_lookback`; severe shared-compute contention may still cause timeouts with additional pre-computed summaries as the escalation path.

### Recovery

A full workspace tarball backup (`../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz`, 1.4 GB) is available as the pre-git rollback mechanism; to restore, run `tar -xzf ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` from the parent directory. Git tracking was initialized as part of R-20260525-1012, providing incremental rollback from that point forward.

### SLO / SLA

No formal SLO or SLA targets are defined.

---

## Development Practices

The product uses pytest for Python ETL tests and Vitest with @testing-library/react for React frontend tests; no CI/CD pipeline is configured.

### Repository Structure

The workspace is organized as follows.

- `src/` — Python ETL scripts: `extract.py`, `transform.py`, `config_utils.py`, `load_supabase.py`, and `deploy_netlify.py`.

- `tests/` — Python unit and smoke test suite covering all ETL modules and menu; 117 tests pass, 1 skipped.

- `react-app/` — React + Vite SPA for Netlify deployment with all frontend source, tests, and build configuration.

- `react-app/src/lib/` — Supabase client singleton (`supabase.js`), data service layer (`dataService.js`), and query log module (`queryLog.js`).

- `react-app/src/components/` — Page components (HomePage, Report1, Report2, Report3, FileDetailPage, FileRowsPanel, FileRowDetailModal, RecordDetailModal) each with a co-located Vitest test file.

- `react-app/netlify.toml` — Netlify build configuration specifying the build command and publish directory.

- `react-app/vite.config.js` — Vite build configuration with `envDir` set to the project root so Vite loads variables from the root `.env` file.

- `data/raw/` — Downloaded ZIP archives; accumulated from ETL runs; not committed to VCS.

- `data/schema/` — Star-schema CSV outputs including seven dimension files, 63+ partitioned fact files, and the derived lookback table.

- `data/nomenclatures/` — Static EKATTE and product-category reference files; committed to VCS.

- `logs/` — ETL transform run logs and AIB framework action logs.

- Root files: `config.ini`, `.env`, `.env.example`, `config.ini.example`, `refresh.sh`, `refresh.bat`, `menu.py`, `menu.sh`, `menu.bat`, `README.md`, `requirements.txt`.

### Developer Setup

Python ETL setup requires the following steps.

- Python 3.9+ is required.

- Create and activate a virtual environment: `python3 -m venv .venv && source .venv/bin/activate` on Linux.

- Install dependencies: `pip install -r requirements.txt`.

- Copy `.env.example` to `.env` and fill in all six credential variables.

- Run `./refresh.sh` or `python menu.py` to verify the setup.

React app setup requires the following steps.

- Node.js 18+ is required; Node 22 has been verified.

- Install dependencies: `cd react-app && npm install`.

- Run `npm run dev` for local development, `npm run build` for production build, or `npm run preview` for local production-like preview after build.

### Testing Strategy

Python ETL tests use pytest and are run with `venv/bin/python -m pytest tests/`. Coverage areas are: `test_config_utils.py` (8 tests for `load_config` and `save_state`), `test_deploy_netlify.py` (24 tests for credential loading, deploy logic, and interactive prompts), `test_extract.py` (9 tests for ZIP discovery, incremental-skip, and atomic rename logic), `test_transform.py` (24 tests for delimiter detection, EKATTE resolution, settlement canonicalization, and dim patch — per R-20260501-0003), `test_load_supabase.py` (32 tests for DDL, upsert, pruning, and retention — per R-20260429-0825, R-20260430-0825), and `test_menu.py` (23 tests for action dispatch, credential validation, and stats helpers; T12 skipped pending service_role-to-anon key rotation in root `.env`). Total: 117 tests pass, 1 skipped.

React app tests use Vitest and @testing-library/react and are run with `npm run test` in `react-app/`. Coverage areas are: `dataService.test.js` (29 tests for helper functions, RPC formats, cross-filter, lookback mapping, and multi-page file row loading — T-FAR-1 through T-FAR-4 added per R-20260517-1244; T-R3-1 and T-R3-2 added per R-20260518-1052), `FileRowsPanel.test.jsx` (23 tests for loading, sort, filter, pagination, 2500-row full load, and 1000-row no-regression), `Report3.test.jsx` (15 tests for filter, pagination, and full-result-set loading), and component tests for FileDetailPage, FileRowDetailModal, RecordDetailModal, Report1, Report2, HomePage, and App. Total: 115 tests pass.

### CI/CD

No CI/CD pipeline configuration is present in the repository.

### Branching and Code Conventions

No formal branching strategy or `CONTRIBUTING.md` is documented. Git tracking was initialized as part of R-20260525-1012 with rewritten history to remove committed credential files; all future changes should be committed to the repository. No automated linting or type-checking configuration is present.

---

## Workspace File Inventory

The workspace file inventory below lists all key files and directories. Excluded from this inventory are `.git/`, `node_modules/` (including `react-app/node_modules/`), `__pycache__/`, `.venv/`, `venv/`, `.pytest_cache/`, and `.mypy_cache/`. The `.aib_brain/` and `.aib_memory/` directories are listed as summary entries only; their internal files are not enumerated individually.

- `.aib_brain/` — AIB framework internals directory containing conventions, prompt templates, runner scripts, tools, and documentation; internal files are not listed individually.

- `.aib_memory/` — AIB framework memory directory containing context, plan, analysis, requests register, request artifacts, and session files; internal files are not listed individually.

- `.env` — Project-root environment file containing all six credential and Vite build variable keys; excluded from VCS by `.gitignore`.

- `.env.example` — Committed placeholder template for `.env` with no real credentials; serves as the single consolidated setup guide.

- `.gitignore` — VCS exclusion rules covering `data/*` (with `!data/nomenclatures/` and `!data/nomenclatures/**` exceptions), `config.ini`, `.env.*` (except `.env.example`), `lab/`, `.netlify/`, and credential scratch files; updated in R-20260525-1012.

- `.netlify/` — Netlify CLI local state directory; present in workspace but excluded from VCS.

- `.vscode/` — VS Code workspace settings directory.

- `README.md` — Primary product documentation covering prerequisites, installation, fresh-install procedure, ETL pipeline usage, star schema reference, React app setup, and Netlify deployment.

- `config.ini` — User-tunable ETL settings (`[settings]`) and machine-written ETL state checkpoints (`[state]`); excluded from VCS by `.gitignore`.

- `config.ini.example` — Committed placeholder template for `config.ini`; added in R-20260525-1012.

- `data/nomenclatures/` — Static EKATTE registry and product-category reference files consumed by `src/transform.py`; committed to VCS via `.gitignore` exceptions.

- `data/nomenclatures/Ekatte/` — Contains 12 NSI EKATTE registry JSON and text files (`ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`, `sof_rai.json`, and supporting files); individual items are not listed.

- `data/nomenclatures/Ekatte.zip` — Archive of the Ekatte directory; not consumed directly by pipeline scripts.

- `data/nomenclatures/EkatteXLS/` — Contains 12 XLS-format EKATTE reference files mirroring the JSON registry; not consumed by current pipeline scripts; individual items are not listed.

- `data/nomenclatures/EkatteXLS.zip` — Archive of the EkatteXLS directory; not consumed directly by pipeline scripts.

- `data/nomenclatures/cities-ekatte-nomenclature.json` — Primary EKATTE settlement lookup with 5,256 canonical 5-digit padded entries; the first source consulted by `load_settlement_names()`.

- `data/nomenclatures/product-categories.json` — Product category ID-to-name mapping with 101 entries consumed by `src/transform.py`.

- `data/nomenclatures/unknown_categories_explanation.md` — Documentation explaining the handling of unknown product category codes in the pipeline.

- `data/quality/` — Contains 26 per-run quality report CSV files following the pattern `report_YYYY-MM-DD_HHMMSS.csv`; individual items are not listed.

- `data/raw/` — Downloaded ZIP archives (`YYYY-MM-DD.zip`) accumulated from ETL runs; excluded from VCS; not auto-pruned.

- `data/schema/dim_category.csv` — Category dimension table with `category_key`, `category_code`, and `category_name` columns.

- `data/schema/dim_company.csv` — Company dimension table with `company_key`, `uic`, and `company_name` columns.

- `data/schema/dim_date.csv` — Date dimension table with `date_key`, `date`, `year`, `month`, `day`, and `weekday` columns.

- `data/schema/dim_file.csv` — File dimension table tracking each company CSV inside each ZIP with `file_key`, `file_name`, and `zip_date` columns.

- `data/schema/dim_product.csv` — Product dimension table with `product_key`, `product_code`, and `product_name` columns (~118,281 rows).

- `data/schema/dim_settlement.csv` — Settlement dimension table with `settlement_key`, `ekatte`, and `settlement_name` columns; EKATTE codes are stored in canonical form after `normalize_settlement_code()` processing.

- `data/schema/dim_store.csv` — Store dimension table with `store_key`, `store_name`, `settlement_key`, and `company_key` columns.

- `data/schema/fact_prices_lookback.csv` — Derived lookback fact table with 11 columns consolidating D, D-1, and D-2 prices; fully replaced on each transform run.

- `data/schema/facts/` — Contains 63 or more date-partitioned fact CSV files following the pattern `YYYY-MM-DD.csv` (~54–78 MB each); individual items are not listed.

- `lab/` — Exploration data directory excluded from VCS; contains at least one per-date subdirectory (`2026-05-13/`) with over 100 per-company CSV files following the pattern `<chain-name> (<company-legal-name>)_<uic>.csv`; individual items are not listed.

- `logs/` — Contains 38 or more transform run logs following the pattern `transform_YYYY-MM-DD_HHMMSS.log`, several AIB framework action logs following the pattern `aib-action-YYYYMMDD-HHMMSS-<action>.log`, and `pipeline.log`; individual items are not listed.

- `menu.bat` — Windows launcher script invoking `menu.py`.

- `menu.py` — Interactive terminal menu providing numbered ETL and deploy actions (1–6, 0 exit).

- `menu.sh` — Linux launcher script invoking `menu.py`.

- `package-lock.json` — Root-level npm lock file present in the workspace root.

- `react-app/` — React + Vite SPA directory; the primary frontend component of the product.

- `react-app/index.html` — Vite entry HTML for the React SPA.

- `react-app/netlify.toml` — Netlify build configuration specifying `npm run build` and `dist` as the publish directory.

- `react-app/package.json` — React app npm package manifest declaring React 18, Vite 5, `@supabase/supabase-js` v2, Vitest, and `@testing-library/react` dependencies.

- `react-app/public/` — Static public assets directory served by Vite unchanged.

- `react-app/src/App.css` — Global stylesheet porting the legacy CSS with responsive breakpoints at ≤ 900px and ≤ 600px, plus sort/filter table styles added in R-20260515-1003.

- `react-app/src/App.jsx` — Root React component managing page-navigation state, date selection, and dimension data fetching on mount.

- `react-app/src/App.test.jsx` — Vitest tests for the App root component covering startup flows and date-selector empty-state behavior.

- `react-app/src/components/FileDetailPage.jsx` — Source-file detail page listing `dim_file` entries for the selected date with per-file record counts and drill-down via FileRowsPanel.

- `react-app/src/components/FileDetailPage.test.jsx` — Vitest tests for FileDetailPage file listing, date filtering, and drill-down behavior.

- `react-app/src/components/FileRowDetailModal.jsx` — Modal component showing all 11 display fields and surrogate keys for a clicked FileRowsPanel row; dismisses on Escape or backdrop click.

- `react-app/src/components/FileRowDetailModal.test.jsx` — Vitest tests for FileRowDetailModal render, display fields, close button, Escape key, and backdrop-click dismissal.

- `react-app/src/components/FileRowsPanel.jsx` — Drill-down panel loading all rows for a selected file via `fetchAllFileRows` with client-side sort, per-column substring filter, and five-element pagination.

- `react-app/src/components/FileRowsPanel.test.jsx` — Vitest tests for FileRowsPanel loading, row rendering, sort, filter, pagination, 2500-row full load, and 1000-row no-regression (23 tests total).

- `react-app/src/components/HomePage.jsx` — Stateless landing page component with welcome heading, intro text, feature cards, and CTA section.

- `react-app/src/components/HomePage.test.jsx` — Vitest smoke test for the HomePage component render.

- `react-app/src/components/RecordDetailModal.jsx` — Modal dialog showing full enriched record details for a clicked Report 2 row; closes via close button or Escape key.

- `react-app/src/components/RecordDetailModal.test.jsx` — Vitest tests for RecordDetailModal render and dismissal behavior.

- `react-app/src/components/Report1.jsx` — Report 1 page showing average price by category for a selected city with a horizontal CSS bar chart and EKATTE-disambiguated settlement labels.

- `react-app/src/components/Report1.test.jsx` — Vitest tests for Report 1 including duplicate settlement label disambiguation behavior.

- `react-app/src/components/Report2.jsx` — Report 2 page showing products by city and category with bidirectional cross-filtering, a 7-column result table, and RecordDetailModal integration.

- `react-app/src/components/Report2.test.jsx` — Vitest tests for Report 2 cross-filter and modal opening behaviors.

- `react-app/src/components/Report3.jsx` — Report 3 page showing locations and products by category with per-column filter, five-element pagination, and full paginated result-set loading.

- `react-app/src/components/Report3.test.jsx` — Vitest tests for Report 3 filter, pagination, and full-result-set loading (15 tests).

- `react-app/src/index.css` — Base index stylesheet providing global resets for the React app.

- `react-app/src/lib/dataService.js` — Data service module providing all Supabase fetch helpers, dimension caching, lookback routing, RPC invocation, and multi-pass pagination logic.

- `react-app/src/lib/dataService.test.js` — Vitest tests covering data service helpers, RPC contract formats, cross-filter functions, lookback mapping, and multi-page file row loading (29 tests).

- `react-app/src/lib/queryLog.js` — Session-scoped in-memory query log; active-but-UI-less infrastructure retained after the Query Log page was removed in R-20260513-2123.

- `react-app/src/lib/supabase.js` — Supabase client singleton with credential validation that rejects secret keys and JWT-format keys before client instantiation.

- `react-app/src/main.jsx` — Vite React app entry point mounting `<App />` into the DOM.

- `react-app/src/test-setup.js` — Vitest global test setup file configuring `@testing-library/jest-dom` matchers.

- `react-app/test_output.txt` — Captured test output file present in the react-app directory.

- `react-app/vite.config.js` — Vite build configuration setting `envDir` to `'../'` so Vite loads environment variables from the project-root `.env` file.

- `refresh.bat` — Windows ETL runner script invoking `src/extract.py` then `src/transform.py` in sequence.

- `refresh.sh` — Linux ETL runner script invoking `src/extract.py` then `src/transform.py`; detects and uses `venv/bin/python` when present.

- `requirements.txt` — Python dependency list: `requests==2.32.5`, `beautifulsoup4==4.12.0`, `psycopg2-binary==2.9.10`, and `python-dotenv`.

- `src/config_utils.py` — Shared ETL config helper providing `load_config()` (reads or bootstraps `config.ini`) and atomic `save_state()` using `.partial` rename.

- `src/deploy_netlify.py` — Netlify deploy script handling CLI detection, credential loading and interactive prompting, React build invocation, and `netlify deploy --prod` execution.

- `src/extract.py` — ETL download script that scrapes kolkostruva.bg and downloads new daily ZIP archives atomically to `data/raw/`.

- `src/load_supabase.py` — Supabase sync module that provisions star-schema tables and RPC functions, upserts dimension data, syncs the lookback fact table, manages the backend SQL audit log, and enforces rolling retention windows.

- `src/transform.py` — ETL transformation script that builds the seven-dimension star schema and the derived lookback fact table from raw ZIP archives using only Python standard-library dependencies.

- `tests/test_config_utils.py` — Unit tests for `config_utils.py` `load_config` and `save_state` functions (8 tests).

- `tests/test_deploy_netlify.py` — Unit tests for `deploy_netlify.py` credential loading, `get_credential` logic, and deploy invocation (24 tests).

- `tests/test_extract.py` — Unit tests for `extract.py` ZIP discovery, incremental-skip logic, and atomic download rename (9 tests).

- `tests/test_load_supabase.py` — Unit tests for `load_supabase.py` DDL provisioning, upsert, pruning, and retention window functions (32 tests).

- `tests/test_menu.py` — Unit tests for `menu.py` action dispatch, credential validation, ETL stats helpers, and local preview behavior (23 tests; T12 skipped).

- `tests/test_transform.py` — Unit tests for `transform.py` delimiter detection, EKATTE name resolution, settlement canonicalization, and in-place dim patch functions (24 tests).
