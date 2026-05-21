# Product Context

> **Auto-generated** by `aib-context.md` on 2026-05-18 07:13 EEST.
> Updated by R-20260430-0825: deleted `fact_prices`; `fact_prices_lookback` is now the sole Supabase fact table.
> Updated by R-20260430-1505: React app date selector now exposes all 3 dim_date rows (D, D-1, D-2); lookback price columns resolved client-side via `normalizeRow()`.
> Updated by R-20260506-2251: Report 2 bidirectional cross-filtering between settlement and category dropdowns; RecordDetailModal for per-row detail view with source file provenance; dim_file loaded at startup.
> Updated by R-20260507-2248: `prune_dim_category(conn)` added to `src/load_supabase.py`; `dim_category` in Supabase is now pruned to only `category_key` values referenced by `fact_prices_lookback` after each sync run.
> Updated by R-20260508-0743: `src/transform.py` now canonicalizes settlement EKATTE identifiers before `dim_settlement` upsert, and Report 1 disambiguates duplicate settlement labels with EKATTE in the dropdown.
> Updated by R-20260509-2012: React app now includes a fifth page, `Лог на заявки`, which records browser-session Supabase table and RPC request intent across startup and report interactions for debugging; the page shows client-visible request metadata, not guaranteed exact backend SQL text.
> Updated by R-20260509-2113: `src/load_supabase.py` now provisions a persistent `backend_sql_audit_log` table in Supabase and records exact rendered backend SQL text for repository-owned PostgreSQL statements with timestamp, origin, and statement-count metadata; audited read queries log through sibling cursors so caller result sets and rowcount semantics remain intact; the log is pruned to a rolling 30-day window.
> Updated by R-20260512-0529: Reports 1, 2, and 3 now use Supabase RPC functions that push category aggregation and row enrichment into PostgreSQL, while the React app keeps lookback-date routing and only falls back to client-side processing when those RPCs are unavailable.
> Updated by R-20260512-2138: `react-app/src/App.css` now includes two responsive breakpoints — mobile (≤ 600px) and tablet (≤ 900px) — covering all five pages; Report 1 bar chart stacks to a column layout on mobile; Report 2 and Report 3 result tables are horizontally scrollable; header, landing page, and nav buttons adapt to narrow viewports.
> Updated by R-20260513-2123: The `Лог на заявки` debugging page has been replaced with a `Файлове` (Files) page; `QueryLogPage.jsx` and its tests were deleted; `FileDetailPage.jsx` was added displaying dim_file source files for the selected date with file name, date, and per-file record count (fetched via `fetchFileStats` in `dataService.js`); `queryLog.js` remains intact as active-but-UI-less infrastructure.
> Updated by R-20260514-2102: `FileDetailPage.jsx` file summary rows are now clickable; clicking a row mounts `FileRowsPanel.jsx`, which fetches and displays a paginated 12-column table of individual price-fact records for the selected file via `fetchFileRows` in `dataService.js`; a back/close button dismisses the panel and restores the summary table.
> Updated by R-20260515-1003: `FileRowsPanel.jsx` now supports client-side column sort (click header cycles asc → desc → unsorted, with `aria-sort` attribute and visual indicator) and per-column substring filter (filter input row in `<thead>`, case-insensitive match against display values, resets on file change); `App.css` now defines `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` fixing the overflow of the 12-column table and the file summary table, plus sort/filter CSS rules (`.sortable-th`, `.sort-indicator`, `.filter-row th`, `.filter-row th input`).
> Updated by R-20260516-1313: `FileRowsPanel.jsx` now loads all rows for the selected file in a two-pass client-side fetch (count then full set) and paginates, filters, and sorts them fully client-side so filter results span all rows rather than a single server page; day1/day2 column headers show the actual calendar dates in DD.MM.YYYY format derived from `dims.dates`; the detail table uses compact CSS class `.file-rows-table` (reduced padding, font-size, text wrapping) so the 12-column layout fits within ~1200px without horizontal overflow; `.table-scroll-wrapper` is retained in CSS and on the `FileDetailPage` summary table.
> Updated by R-20260517-1113: `FileRowsPanel.jsx` detail table rows are now clickable; clicking a row opens `FileRowDetailModal.jsx` — a new modal component showing all 12 display fields and all surrogate keys (product_key, category_key, store_key, file_key, settlement_key, company_key) with Escape and backdrop-click dismissal; the two-button Previous/Next pagination strip has been replaced with a modern five-element bar (First «, Previous ‹, page indicator, Next ›, Last ») with correct disabled states for the first and last pages.
> Updated by R-20260517-1244: `FileRowsPanel.jsx` now loads all rows for the selected file via `fetchAllFileRows` — a new exported function in `dataService.js` that pages through `SUPABASE_PAGE_SIZE` chunks until all rows are accumulated, replacing the previous single-range full-load call that was silently capped at 1 000 rows by the PostgREST `max_rows` default; `dim_product` is queried once in a single batch `.in()` call after all pages are loaded.
> Updated by R-20260518-1052: `fetchReport3` in `dataService.js` is now fully paginated via successive `.range()` calls (same pattern as `fetchAllFileRows`) so all rows for a category are loaded regardless of the PostgREST `max_rows` cap; the `REPORT3_ROW_CAP` constant and its per-page cap in `fetchReport3Fallback` have been removed; `Report3.jsx` now includes per-column substring filter inputs, a five-element pagination bar (First «, Prev ‹, indicator, Next ›, Last »), client-side `filteredRows` derivation via `useMemo`, category-change state reset, and a record-count summary; `PAGE_SIZE = 100` rows per page; all CSS classes reuse existing definitions from `App.css` (`.filter-row`, `.pagination-controls`, `.pagination-btn`, `.pagination-btn--edge`, `.pagination-indicator`, `.table-scroll-wrapper`).
> Updated by R-20260518-1251: All currency notation (`лв`, `(лв)`) removed from every price display string and column header label across the React app (`Report1.jsx`, `Report2.jsx`, `Report3.jsx`, `RecordDetailModal.jsx`, `FileRowDetailModal.jsx`, `FileRowsPanel.jsx`); prices now display as bare two-decimal numeric values; `FileRowsPanel.test.jsx` column-label assertions updated to match.
> Updated by R-20260518-2134: "Ефективна цена" UI label removed from `FileRowsPanel.jsx` (column dropped from `buildColumns()`), `FileRowDetailModal.jsx` (dt/dd pair removed), and `RecordDetailModal.jsx` (dt/dd pair removed); `FileRowsPanel` now has 11 columns; `calculatePrice()` and the `calculatedPrice` data field are retained in `dataService.js` and continue to power the Report 2 and Report 3 "Цена" columns; two test assertions for "Ефективна цена" removed from `FileRowsPanel.test.jsx` and `FileRowDetailModal.test.jsx`.
> Framework definition assets (`.aib_brain/`) are excluded by design — see `.aib_brain/` for AIB framework internals.
> This document is a synthesis of product documentation and workspace sources. It is fully replaced on each execution.

## Product Identity

**Kolko Ni Struva ETL Pipeline + React Analytics App** (version: not explicitly versioned; active as of 2026-04-23).

The product has two integrated layers:

1. **ETL Pipeline:** Downloads daily retail-price ZIP archives from the Bulgarian government open-data portal (kolkostruva.bg/opendata), transforms them into a star-schema structured dataset under `data/schema/`, syncs the star-schema to a Supabase-hosted PostgreSQL database, and provides operator tooling: interactive terminal menu (`menu.py`), ETL runner scripts (`refresh.sh` / `refresh.bat`), and a central configuration file (`config.ini`).

2. **React Analytics App:** A React + Vite single-page application (`react-app/`) deployed on Netlify that queries the Supabase database directly and visualises retail price data in five views (Home, Report 1, Report 2, Report 3, Files), replacing the legacy vanilla-JS app (`build-legacy/web/`).

Primary actors: data engineers and analysts who run the ETL pipeline locally and access price analytics via the hosted React app.

Production status: active. 63+ ZIP archives accumulated in `data/raw/`; ~82 million fact rows produced; React app deployable to Netlify (public URL, no authentication).

Scope boundaries: no bulk historical backfill to cloud database, no API exposure beyond Supabase RLS, no automated scheduling, no CI/CD pipeline. The React app is client-only (no serverless functions).

---

## Business Context

Business domain: retail price transparency; sub-domain: government open-data acquisition, transformation, and public visualisation.

The Bulgarian government requires retail companies to report daily prices through the kolkostruva.bg portal. The pipeline automates collection and structural transformation of the published ZIP archives. The React app exposes the resulting dataset to end users via a hosted web application.

Key business processes supported:
- Daily automated download of government-published retail-price ZIP archives from kolkostruva.bg/opendata (per `src/extract.py`).
- ETL transformation of raw CSVs into a star-schema data layer for analytical consumption (per `src/transform.py`).
- Cloud sync of the star-schema to a Supabase-hosted PostgreSQL database (per `src/load_supabase.py`).
- Interactive pipeline status/action menu exposing ETL state and operator actions (per `menu.py`).
- Public-access retail price visualisation via the hosted React web app (per `react-app/`).

Organizational context: internal data engineering team; public end users via Netlify.

Critical external dependencies: kolkostruva.bg/opendata (Bulgarian government portal); Supabase (hosted PostgreSQL + REST API); Netlify (React app hosting). Availability and format of the government portal are outside the product team's control.

Domain-specific terminology: EKATTE (Bulgarian administrative code registry for settlements); UIC (Bulgarian company identification code, ЕИК).

---

## Requirements Summary

### Functional Capabilities

1. Scrape kolkostruva.bg/opendata and download any new daily ZIP archives to `data/raw/`. (per `src/extract.py`, `README.md`)

2. Transform all ZIPs in `data/raw/` into a star-schema data layer under `data/schema/`: seven dimension CSVs and date-partitioned fact CSVs in `data/schema/facts/`. (per `src/transform.py`)

3. Manage ETL configuration via `config.ini`: user-tunable settings and machine-written state checkpoints; support force re-download and force re-process by editing state keys. (per `src/config_utils.py`)

4. Provide ETL runner scripts (`refresh.sh` on Linux; `refresh.bat` on Windows) that execute the full pipeline in sequence. (per request.md)

5. Provide an interactive terminal menu (`menu.py`) with numbered actions: 1) full refresh, 2) download only, 3) transform only, 4) update Supabase DB, 5) deploy React app to Netlify, 6) preview React app locally, 0) exit. (per R-20260421-0348, R-20260421-0505, R-20260425-2155)

6. Sync the star-schema to a Supabase-hosted PostgreSQL database via `src/load_supabase.py`: provision all eight analytical tables, seven RPC helper functions, and the persistent `backend_sql_audit_log` table; upsert all seven dimension CSVs; truncate and reinsert `fact_prices_lookback` on every sync run; log exact rendered backend SQL text for repository-owned PostgreSQL statements; prune `dim_date` to the latest 3 local fact dates so the React app date selector only shows retained dates; prune `dim_category` to only the category keys referenced by `fact_prices_lookback`; and prune backend SQL audit rows older than 30 days. (per R-20260420-1730, R-20260422-0902, R-20260429-0825, R-20260430-0825, R-20260507-2248, R-20260509-2113, R-20260512-0529)

7. React Analytics App deployed on Netlify (`react-app/`): five views — Home (landing), Report 1 (avg price by category for selected city — bar chart), Report 2 (products by city and category — 7-column table with bidirectional cross-filtering between settlement and category dropdowns, and a per-row RecordDetailModal showing full provenance including source file name from `dim_file`), Report 3 (locations and products by category — 7-column table with per-column substring filter inputs and a five-element pagination bar; full result set loaded via `fetchReport3` paginated multi-pass fetch bypassing PostgREST `max_rows` cap — R-20260518-1052), and Files (source-file detail page listing dim_file entries for the selected date with file name, submission date, and per-file record count from `fact_prices_lookback`; each file row is clickable and opens a `FileRowsPanel` drill-down component that loads all rows for the file via a paginated multi-pass client-side fetch (count, then `SUPABASE_PAGE_SIZE` chunks until all rows are loaded) and displays a compact 11-column table of individual price-fact records with product, category, settlement, store, company, and all price metrics including lookback columns; day1/day2 column headers show actual calendar dates in DD.MM.YYYY format derived from `dims.dates`; pagination, sort, and filter are fully client-side across all loaded rows so filter results are not limited to the current page; the table uses the `.file-rows-table` scoped CSS class (reduced padding, font-size, text wrapping) that fits 11 columns within ~1200px without horizontal overflow; column headers are sortable by click cycling asc → desc → unsorted with `aria-sort` and visual indicator; a filter input row in `<thead>` supports per-column case-insensitive substring filtering across all loaded rows; filtering resets the page to 1; sort and filter reset on file change; each detail row is clickable and opens `FileRowDetailModal.jsx` showing all 11 display fields and surrogate keys (product_key, category_key, store_key, file_key, settlement_key, company_key) with Escape and backdrop-click dismissal; pagination uses a modern five-element bar First «, Previous ‹, page indicator, Next ›, Last » with correct disabled states). Date selector in header shows all 3 `dim_date` rows (D, D-1, D-2); the frontend still derives the selected lookback offset from `lookbackColumnMap`, but Reports 1, 2, and 3 now pass that offset to Supabase RPCs so PostgreSQL performs aggregation and enrichment before results reach the browser. The `get_available_dates()` RPC identifies D (the current date with actual fact rows) and is used to build a `lookbackColumnMap` that routes lookback queries to the correct fact rows. Report 1 settlement options are disambiguated with EKATTE when duplicate visible names still exist in the loaded dimension data. All data from Supabase via `@supabase/supabase-js` v2. (per R-20260421-0422, R-20260422-0902, R-20260430-0825, R-20260430-1505, R-20260506-2251, R-20260508-0743, R-20260509-2012, R-20260509-2113, R-20260512-0529, R-20260513-2123, R-20260514-2102, R-20260516-1313, R-20260517-1113)

### Non-Functional Requirements

- Idempotency: re-running when no new ZIPs exist produces no new output.
- Atomic writes: all file writes use `.partial` temp-file renamed on completion.
- Human-readable outputs: all schema files are UTF-8 CSV.
- Python 3.9+ compatibility for all scripts.
- Retry resilience: HTTP download failures retried up to `max_retries` times with exponential backoff.
- Supabase sync idempotency: re-running when latest local fact date already exists in Supabase exits cleanly; re-running retention pruning with unchanged local inputs leaves `fact_prices` row count unchanged.
- Backend SQL auditability: repository-owned PostgreSQL statements emitted by `src/load_supabase.py` are persisted with rendered SQL text, execution timestamp, logical origin, and statement-count metadata in `backend_sql_audit_log`; audited read queries preserve fetchable results by emitting the audit insert through a sibling cursor.
- React app: no credentials hardcoded in source files; env vars use `VITE_` prefix; anon key only.
- React app: `npm run build` exits 0 and produces `dist/`; Netlify free-tier compatible.
- React app: responsive layout via CSS media queries at ≤ 900px (tablet) and ≤ 600px (mobile); all five pages are usable without horizontal overflow from 320px to 1920px viewport width; minimum touch target height 44px for form controls on mobile.
- React app date selector: shows all 3 `dim_date` rows (D, D-1, D-2); D-1 and D-2 views are synthesized client-side from lookback price columns in `fact_prices_lookback`.
- React app Report 1 settlement dropdown: lists every settlement with at least one store with data on the selected date, regardless of total fact-row volume, and disambiguates duplicate visible names with EKATTE.
- React app Report 1 category chart: includes all categories with at least one price observation; no silent truncation.
- ETL settlement identity: semantically identical EKATTE formatting variants are canonicalized before `dim_settlement` and `dim_store` natural keys are assigned, preventing analytical splits such as `68134` versus `068134`.

### Known Priorities

Data correctness (no row rejection, no surrogate collision) and idempotency are primary concerns for the ETL layer. Visual fidelity to the legacy app, credential security, and complete result coverage are primary concerns for the React app.

---

## Architecture & Key Decisions

### High-Level Component Map

- **Download script (`src/extract.py`):** Scrapes the open-data index page, resolves new or force-scheduled ZIP URLs, and downloads them atomically to `data/raw/`. Reads settings and state from `config.ini`; writes `last_downloaded_date` on success.
- **Transform script (`src/transform.py`):** Reads all ZIPs from `data/raw/`, builds seven dimension tables from observed codes, and writes date-partitioned fact CSVs to `data/schema/facts/`. Calls `build_lookback_table` to produce `data/schema/fact_prices_lookback.csv`. Writes per-run log and quality report.
- **Config helper (`src/config_utils.py`):** Shared stdlib module providing `load_config()` and `save_state()`. Imported by both `extract.py` and `transform.py`.
- **Supabase sync module (`src/load_supabase.py`):** Loads `.env` via `python-dotenv`; reads `DATABASE_URL`; provisions all eight analytical tables, the `backend_sql_audit_log` table, seven PostgreSQL RPC helper functions, and five B-tree indexes via idempotent DDL; upserts all seven dimension CSVs via INSERT … ON CONFLICT DO UPDATE; truncates and reinserts `fact_prices_lookback` on every sync run; records exact rendered SQL text for direct statements and batched page executions issued by the repository-owned backend path while using sibling cursors for audit inserts so SELECT result sets remain fetchable; and prunes audit rows older than 30 days.
- **Interactive menu (`menu.py`):** Reads `data/raw/`, `data/schema/facts/`, and `config.ini` to display ETL statistics. Numbered action menu (1–6, 0 exit). Invokes scripts via `subprocess` (list form, no `shell=True`). Option 5 invokes `src/deploy_netlify.py` without `capture_output` to allow stdin passthrough for interactive credential prompts. Option 6 runs `npm run build && npm run preview` from `react-app/` for a production-like local preview; the local URL (`http://localhost:4173`) is always printed and a browser open is attempted via `webbrowser.open()` (best-effort, never fails the workflow).
- **Netlify deploy script (`src/deploy_netlify.py`):** Detects Netlify CLI availability via `shutil.which`; if not found, prints manual deploy instructions and exits 0. If found, loads `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` from the project-root `.env` file (via `python-dotenv` `load_dotenv`) at module import time, with shell environment variables taking precedence. When a credential is not available in env or .env, prompts the operator interactively with step-by-step acquisition instructions and auto-saves the entered value to `.env` using `dotenv.set_key`. Builds the React app via `npm run build`, then runs `netlify deploy --prod --dir react-app/dist` with credentials injected in subprocess env (never as CLI args).
- **ETL runner scripts (`refresh.sh`, `refresh.bat`):** Thin OS-native wrappers invoking `src/extract.py` then `src/transform.py`. `refresh.sh` detects and uses `venv/bin/python` when present.
- **Menu launchers (`menu.sh`, `menu.bat`):** One-line OS-native wrappers invoking `menu.py`.
- **React Analytics App (`react-app/`):** Vite-built React 18 SPA. Queries Supabase directly via `@supabase/supabase-js` v2. Five pages: Home, Report 1, Report 2, Report 3, Files. Deployed on Netlify from `react-app/dist/`. No serverless functions.
- **Legacy web app (`build-legacy/web/`):** Retained as reference; replaced by `react-app/` as the active visualisation layer.
- **Configuration file (`config.ini`):** Single INI at project root. `[settings]` user-tunable; `[state]` machine-written.
- **Star-schema outputs (`data/schema/`):** Seven flat dimension CSVs; 63+ date-partitioned fact CSVs in `data/schema/facts/`; derived lookback table.
- **Raw staging (`data/raw/`):** Write target for `src/extract.py`; not auto-pruned.
- **Nomenclature seed files (`data/nomenclatures/`):** EKATTE registry and product category list; consumed by `src/transform.py`.

### Key Integration Points

- **kolkostruva.bg/opendata (external, inbound):** HTTPS download via HTML scraping.
- **Supabase REST API (external, inbound to React app):** `@supabase/supabase-js` v2 queries `dim_*` tables via Supabase PostgREST and invokes `get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, `get_settlements_for_category`, `get_report_1_category_prices`, `get_report_2_rows`, and `get_report_3_rows` RPC functions. Auth: anon key; RLS must allow public SELECT and anon EXECUTE on RPC functions.
- **Supabase PostgreSQL (external, inbound to ETL sync):** Direct PostgreSQL connection via `psycopg2-binary`; `DATABASE_URL` from `.env`.
- **Netlify (external, hosting):** `react-app/netlify.toml` configures build command and publish directory.

### Key Architectural Decisions

1. **Date-partitioned fact table:** `data/schema/facts/YYYY-MM-DD.csv` (~54–78 MB each). A single flat file would be ~3.4–4.9 GB — incompatible with "human-readable" and "minimal space" constraints.

2. **Dimension from facts (no pre-load):** dimension tables populated from codes observed in the fact stream, enriched via static nomenclature files. Unknown codes receive `(unknown:<code>)` entries. Extended EKATTE lookup (R-20260501-0003) resolves non-canonical codes via three-step normalisation (exact → zero-padded to 5 digits → leading-zeros stripped) and consults seven nomenclature sources; genuinely unresolvable codes retain the `(unknown:<code>)` placeholder.

3. **`config.ini` for ETL control:** one INI file with `[settings]` and `[state]`. `configparser` is Python 3.9+ stdlib.

4. **No-rejection policy:** all rows with valid column count retained. Non-parseable `retail_price` stores NULL. Unknown dimension codes produce placeholder entries.

5. **Stdlib-only Python for transformation:** `src/transform.py` and `src/config_utils.py` use only Python stdlib.

6. **Dual-platform OS launchers (`.sh` + `.bat`):** thin cross-platform wrappers.

7. **React app architecture (client-only, Supabase direct):** Queries Supabase from the browser using the public anon key. No backend or serverless functions. Dimension tables loaded once at startup and cached in module scope. dim_product (~118K rows) never fully loaded; Reports 1, 2, and 3 now consume RPC result sets that already contain grouped or enriched rows.

8. **Report-query pushdown:** category averaging for Report 1 and row enrichment for Reports 2 and 3 are executed in PostgreSQL through report-oriented RPCs, reducing browser memory use and repeated client-side iteration over `fact_prices_lookback`.

9. **RPC functions for date filter, cross-filter, and reports (R-20260422-0902, R-20260430-0825, R-20260506-2251, R-20260512-0529):** `get_available_dates()`, `get_settlements_for_date(bigint)`, `get_categories_for_settlement(bigint, bigint)`, `get_settlements_for_category(bigint, bigint)`, `get_report_1_category_prices(bigint, bigint, text)`, `get_report_2_rows(bigint, bigint, bigint, text)`, and `get_report_3_rows(bigint, bigint, text)` are idempotent PostgreSQL functions provisioned by `load_supabase.py`. They allow the React app to obtain accurate filter sets and report result sets without transferring large volumes of raw fact rows to the client. All functions include `GRANT EXECUTE TO anon` so PostgREST can invoke them without elevated privileges. All functions query `fact_prices_lookback` directly or through joins on its foreign keys.

---

## Technical Design

### Module Breakdown

- **`src/extract.py`:** Functions: `setup_logging`, `fetch_page`, `parse_zip_links`, `existing_filenames`, `download_file`, `main`. `BASE_DIR = Path(__file__).resolve().parent.parent`. Reads `config.ini`; writes `last_downloaded_date` on success.

- **`src/transform.py`:** Loads `config.ini`; reads `last_processed_date`; loads existing dimension CSVs; loads nomenclature dicts; initialises rotating log. Per ZIP: skips if fact exists and no force trigger; otherwise processes all CSVs, upserts all seven dimensions, writes buffered fact rows atomically. On completion: writes dimension CSVs atomically; writes quality report; calls `config_utils.save_state()`. Key nomenclature functions (R-20260501-0003, R-20260508-0743): `load_settlement_names()` builds the EKATTE→name lookup from seven sources (`cities-ekatte-nomenclature.json`, `sof_rai.json`, `ek_atte.json`, `ek_kmet.json`, `ek_raion.json` (keyed on `raion` field), `ek_obl.json`, `ek_obst.json`); all file reads are absent-file-guarded. `resolve_settlement_name(code, lookup)` probes in three steps: exact → `code.zfill(5)` → `code.lstrip('0')`, returning `(unknown:<code>)` if all probes fail. `normalize_settlement_code(code)` canonicalizes raw settlement identifiers before `dim_settlement` natural-key assignment by stripping redundant leading zeros, preserving raion suffixes, and padding short numeric EKATTE values back to 5 digits. `patch_unknown_settlements(dim_path, lookup)` reads `dim_settlement.csv`, applies `resolve_settlement_name()` to every `(unknown:...)` row, and atomically rewrites the file via `write_dim()` — preserving all surrogate keys — then returns the update count. `patch_unknown_settlements()` is called from `main()` after `build_schema()` on every run.

- **`src/config_utils.py`:** `load_config(config_path)`: reads/bootstraps INI. `save_state(config, config_path, **kwargs)`: atomic INI write via `.partial` rename.

- **`src/load_supabase.py`:** Loads `.env`; validates `DATABASE_URL`; `create_tables(conn)` executes five DDL blocks for the star-schema tables, audit table, nullable migrations, legacy `fact_prices` removal, RPC functions, and indexes. The module routes direct statements through `execute_sql()` and batched statements through `execute_batch_with_audit()` so the repository-owned backend path logs exact rendered SQL text to `backend_sql_audit_log` together with `executed_at`, `origin`, and `statement_count`. Direct-statement audit inserts run on sibling cursors so callers that fetch rows or inspect rowcount on the original cursor keep valid DB-API state after the audited statement. `upsert_dim()` and `insert_lookback()` still emit 2,000-row execute-batch pages, but each emitted page is also persisted as one audit row. `get_retained_local_dates(facts_dir, n=3)` returns the 3 newest local fact date strings; `get_date_keys_for_dates(conn, date_strings)` resolves their surrogate keys from `dim_date`; `prune_dim_date(conn, retained_date_keys)` deletes `dim_date` rows outside the retained set; `prune_dim_category(conn)` deletes `dim_category` rows not referenced by `fact_prices_lookback`; and `prune_sql_audit_log(conn, retention_days=30)` deletes backend SQL audit rows older than the rolling 30-day window. All pruning functions roll back on `psycopg2.DatabaseError`.

- **`menu.py`:** Displays ETL statistics; numbered menu 1–6, 0 exit; full refresh halts on first step failure; calls `subprocess.run([sys.executable, 'src/...'], check=True)` for ETL scripts; calls `subprocess.run([sys.executable, 'src/deploy_netlify.py'])` (no `capture_output`) for option 5 to allow interactive credential prompts. Option 6 (`action_local_preview`) validates `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set (via `python-dotenv` + `os.environ`) before invoking `npm run build`; prints an actionable error with an example and returns without building if either key is empty. After a successful build, starts `npm run preview` via `subprocess.Popen` (non-blocking), polls `localhost:4173` with `_wait_for_server()` until the server is ready, then opens the browser — eliminating the race condition where the browser opened before the server was listening (R-20260426-2150).

- **`src/deploy_netlify.py`:** Functions: `find_netlify_cmd`, `print_manual_instructions`, `get_credential`, `_save_credential_to_env`, `build_react_app`, `deploy_to_netlify`, `main`. Uses stdlib plus `python-dotenv` (`load_dotenv`, `set_key`). At module import, captures `_SHELL_ENV_KEYS` (shell-provided env vars) then calls `load_dotenv(BASE_DIR / ".env")` to load project-root `.env` into `os.environ` without overriding shell values. `get_credential()` checks env (shell or .env), logging the source; falls back to interactive prompt. `_save_credential_to_env()` uses `set_key` to persist interactively entered credentials to `.env`. `main()` checks whether each credential is pre-loaded and calls `_save_credential_to_env()` for any that were absent (entered interactively). Targets `react-app/dist/` for deploy. Falls back to manual instructions when Netlify CLI absent.

- **`react-app/src/lib/supabase.js`:** Supabase client singleton using `import.meta.env.VITE_SUPABASE_URL` and `import.meta.env.VITE_SUPABASE_ANON_KEY` (loaded by Vite from project-root `.env` file). No hardcoded credentials.

- **`react-app/src/lib/dataService.js`:** `fetchAllRows(table, columns)` — generic paginator (1000-row pages, `.range()`) with session query logging. `fetchDimensions()` — parallel load of dim_date, dim_settlement, dim_category, dim_store, dim_company, dim_file plus `get_available_dates()` RPC; exposes ALL dim_date rows in `dates` (D, D-1, D-2); derives `currentDateKey` (D's key) from RPC result (null if RPC unavailable); builds `lookbackColumnMap` (Map<date_key, 'current'|'day1'|'day2'>); builds `files` as Map<file_key, {file_name, zip_date}> from dim_file for source-file provenance in RecordDetailModal and FileDetailPage; all stored in module-level `_dims` cache. `_resetDimsCache()` — exported test-only helper. `normalizeRow(row, offset)` — remaps lookback price columns to canonical fields; identity for 'current' or falsy offset. `fetchSettlementsForDate(dateKey, dims)` — resolves offset; for D-1/D-2 uses `dims.currentDateKey`; annotates settlement options with `displayLabel` and appends EKATTE when duplicate visible names are present; falls back to all settlements on RPC error. `fetchCategoriesForSettlement(settlementKey, dateKey, dims)` — calls `get_categories_for_settlement` RPC; applies PostgREST v10/v11 guard; maps keys to category objects from `dims.categories`; falls back to all categories on RPC error. `fetchSettlementsForCategory(categoryKey, dateKey, dims)` — calls `get_settlements_for_category` RPC; maps keys to settlement objects; falls back to all settlements on RPC error. `fetchReport1(dateKey, settlementKey, dims)` — calls `get_report_1_category_prices` with the selected lookback offset and only falls back to client aggregation when the RPC is unavailable. `fetchReport2(dateKey, settlementKey, categoryKey, dims)` — calls `get_report_2_rows` and returns already enriched product rows, with fallback to the older client path only when needed. `fetchReport3(dateKey, categoryKey, dims)` — calls `get_report_3_rows` and returns already enriched settlement/store/company rows, again with a compatibility fallback path. `fetchFileStats(fileKeys)` — issues batched (20 per batch) parallel HEAD COUNT(*) queries against `fact_prices_lookback` per file_key and returns a Map<file_key, count> for the Files summary table. `fetchFileRows(fileKey, dims, pageIndex, pageSize)` — retained for backward compatibility; issues a HEAD-only COUNT and a single paginated SELECT against `fact_prices_lookback` filtered by file_key; batch-fetches product names from `dim_product` for the unique keys on the current page; enriches rows; returns `{ rows, totalCount }`. `fetchAllFileRows(fileKey, dims)` — multi-pass loader (R-20260517-1244); issues a HEAD-only COUNT, then loops with `SUPABASE_PAGE_SIZE` (1 000) per page until all rows are accumulated; performs a single batch `dim_product .in()` lookup after all pages are loaded; enriches rows with category, store, company, and settlement names from cached dims; returns `{ rows, totalCount }` for FileRowsPanel, replacing the single-range call that was silently capped at 1 000 rows by PostgREST `max_rows`. All startup, report, and RPC reads append browser-session entries to `react-app/src/lib/queryLog.js` (active-but-UI-less infrastructure; the Query Log page was removed in R-20260513-2123 but the module remains intact). Exported helpers: `formatDateBG(dateStr)`, `calculatePrice(row)`, `normalizeRow(row, offset)`, `fetchFileStats(fileKeys)`, `fetchFileRows(fileKey, dims, pageIndex, pageSize)`, `fetchAllFileRows(fileKey, dims)`.

- **`react-app/src/App.jsx`:** Root component. `useEffect` fetches dimensions on mount; manages `activePage`, `selectedDate`, `dimensions`, `loadError` state. Renders header (title, subtitle, date selector, 5-button nav), five page sections (each conditionally shown), footer. The date selector shows a disabled "Няма налични дати" placeholder option when `dimensions` is loaded but `dimensions.dates` is empty (no fact data in Supabase), preventing a silent empty-state.

- **`react-app/src/lib/queryLog.js`:** Session-scoped in-memory store for frontend-visible query activity. Exposes snapshot, subscription, append, clear, and test-reset helpers so the app can record Supabase request intent without introducing backend persistence. The Query Log UI page was removed in R-20260513-2123; this module is retained as active-but-UI-less infrastructure that may have future use.

- **`react-app/src/components/FileDetailPage.jsx`:** Source-file detail page (R-20260513-2123, updated R-20260514-2102) that lists dim_file entries for the selected date. Filters `dims.files` by `zip_date` matching the selected date's ISO date string; fetches per-file record counts from `fact_prices_lookback` via `fetchFileStats`; renders a summary table with file name, submission date (DD.MM.YYYY), and record count columns where each row has `cursor: pointer` and an `onClick` that sets `selectedFile` state. When `selectedFile` is non-null, renders `FileRowsPanel` in place of the summary table; the panel's `onClose` callback clears `selectedFile` and restores the summary. Resets `selectedFile` to null on date change. Shows a no-data message when no files match the selected date.

- **`react-app/src/components/FileRowsPanel.jsx`:** Drill-down panel (R-20260514-2102, updated R-20260517-1244) rendered by `FileDetailPage` when the user clicks a file summary row. Accepts `fileKey`, `fileMeta`, `dims`, and `onClose` props. Manages `rows`, `totalCount`, `loading`, `error`, `currentPage`, `sortConfig`, and `filterValues` state. The `COLUMNS` constant array defines all 11 column keys, labels, and types (string/numeric). A single `useEffect` hook fetches all rows on `[fileKey]` via `fetchAllFileRows(fileKey, dims)` (R-20260517-1244), replacing the previous `[fileKey, currentPage]` dep loop that was silently capped at 1 000 rows by PostgREST `max_rows`; a separate `useEffect` resets sort, filter, and page to initial state when `fileKey` changes. `sortedRows` (via `useMemo`) applies the active `sortConfig`; string columns use lowercase comparison, numeric columns compare raw float values with missing values sorted last. `filteredRows` (via `useMemo`) applies all non-empty `filterValues` as case-insensitive substring matches against the display value for each column (numeric columns matched via bg-BG formatted string per A3). Column headers rendered via COLUMNS map as `<th class="sortable-th">` with `onClick`/`onKeyDown` for `handleSort`, `aria-sort`, a `col-label` span (preserves `getByText` selector compatibility), and a `sort-indicator` span with `aria-hidden`. A second `<tr class="filter-row">` in `<thead>` contains `<input>` elements with `aria-label` per column bound to `handleFilterChange`. Tbody renders `filteredRows` via COLUMNS map. `getDisplayValue` helper unifies render and filter comparison. `formatPrice` formats numeric values in bg-BG locale. Pagination controls unchanged.

- **`react-app/src/App.css`:** Full port of `build-legacy/web/style.css`; preserves all class names, hex colours (#667eea, #764ba2), gradients, keyframe animations, and responsive layout. Updated in R-20260512-2138 to add a two-breakpoint responsive system: `@media (max-width: 900px)` covers table horizontal scroll, report section padding, and nav button sizing; `@media (max-width: 600px)` covers body padding, header font size, landing page padding, date selector stacking, chart bar stacking (column layout per bar entry), results table horizontal scroll, and touch-target sizing for dropdowns. Updated in R-20260515-1003 to add `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` (Results Table section, fixes 11-column FileRowsPanel overflow and FileDetailPage summary table overflow), `.results-table th.sortable-th` (cursor: pointer, user-select: none, hover gradient), `.sort-indicator` (margin-left: 6px, opacity: 0.7, font-size: 0.85em), `.filter-row th` (white background override for the filter input row), `.filter-row th input` (full-width box-model, 0.85em font, #ddd border, 4px border-radius), and `.filter-row th input:focus` (brand-colour focus ring).

- **`react-app/src/components/HomePage.jsx`:** Stateless landing page with welcome heading, intro text (link to kolkostruva.bg), three feature cards, CTA section.

- **`react-app/src/components/Report1.jsx`:** City selector (populated via `fetchSettlementsForDate`); renders `displayLabel` when duplicate settlement names need EKATTE disambiguation; horizontal CSS bar chart from `fetchReport1`; bar widths proportional to avgPrice scaled to 60% of container; reloads settlements when date changes.

- **`react-app/src/components/Report2.jsx`:** City + category selectors with bidirectional cross-filtering (R-20260506-2251): selecting a settlement invokes `fetchCategoriesForSettlement` to restrict the category dropdown; selecting a category invokes `fetchSettlementsForCategory` to restrict the settlement dropdown; if the current selection drops out of the re-filtered list it is auto-cleared (Q002-A behavior). Date change resets both dropdowns. 7-column product table from `fetchReport2` (product name, calculated price, retail price, promo price, store, chain, date). Each table row is clickable and opens `RecordDetailModal` for that row.

- **`react-app/src/components/RecordDetailModal.jsx`:** Modal dialog (R-20260506-2251) that displays full enriched record details for a clicked Report 2 row: product name, category, settlement, store, company, retail price, promo price (when non-null), source file name and zip date from `dims.files`. Closes via close button or Escape key. Uses `role="dialog"` and `aria-modal="true"`.

- **`react-app/src/components/Report3.jsx`:** Category selector; 7-column location+product table from `fetchReport3` (city, product name, calculated price, retail price, promo price, store, chain); loading indicator shown for large categories.

### Key Algorithms and Processing Logic

**ZIP discovery:** `parse_zip_links` parses kolkostruva.bg/opendata HTML, extracts `.zip` hrefs via BeautifulSoup, resolves relative URLs with `urllib.parse.urljoin`, returns sorted descending deduplicated list. ZIPs verified with `zipfile.is_zipfile()` before atomic rename.

**Incremental download with force re-download:** compares ZIP filenames against `data/raw/`. Scheduled if absent OR date string >= `last_downloaded_date` override. Written via `.partial` → atomic rename.

**Delimiter auto-detection:** attempt comma-delimited parse; if first data row has one column containing `;`, re-read using `;` delimiter. Strip BOM from header rows in both passes.

**Dimension upsert:** load existing dimension CSV into `{natural_key: surrogate_key}` at startup. New code: assign `max_key + 1`; enrichment at insert time. Settlement natural keys are canonicalized before upsert so padded and canonical EKATTE variants collapse to the same analytical identity. Full dimension table written atomically at end of each run. Surrogate keys stable as long as dimension CSVs are not deleted.

**React effective price calculation:** `min(retail_price, promo_price)` where promo_price non-null and non-zero; otherwise `retail_price`. Implemented in `dataService.calculatePrice()`.

**React dimension caching:** `fetchDimensions()` result stored in module-level `_dims`; subsequent calls return cached object without re-fetching.

**React date selector via lookbackColumnMap (R-20260422-0902, R-20260428-0708, R-20260430-0825, R-20260430-1505):** `fetchDimensions()` calls `get_available_dates()` in parallel with dimension table fetches. All dim_date rows are exposed in `dims.dates` (D, D-1, D-2) without filtering. The RPC result is used only to derive `currentDateKey` (D's key): builds a Set of fact-present date_key integers using backward-compatible mapping (`(typeof r === 'object' && r !== null) ? r.get_available_dates : r` — handles PostgREST v10 wrapped-object and v11+ plain-integer formats), then extracts the single value as `currentDateKey`. `lookbackColumnMap` is built positionally from the sorted dim_date array (index 0 → 'current', index 1 → 'day1', index 2 → 'day2'). If RPC is unavailable, `currentDateKey = null` and the map is still built positionally from dim_date; lookback queries degrade gracefully.

**React settlement filter via RPC (R-20260422-0902, R-20260428-0708, R-20260430-0825, R-20260430-1505, R-20260508-0743):** `fetchSettlementsForDate(dateKey, dims)` resolves the offset from `dims.lookbackColumnMap`; for D-1/D-2 offsets, calls `get_settlements_for_date(p_date_key)` with `dims.currentDateKey` (D's key) because fact rows are stored under D in `fact_prices_lookback`. For the 'current' offset, uses `dateKey` directly. The RPC result is mapped using the same backward-compatible guard: `(typeof r === 'object' && r !== null) ? r.get_settlements_for_date : r`. Settlement names resolved from `dims.settlements`, and duplicate visible names receive `displayLabel` values suffixed with EKATTE to prevent ambiguous Report 1 selection. Fallback to all known settlements if RPC errors.

**React report RPC pushdown with lookback routing (R-20260512-0529):** `fetchReport1`, `fetchReport2`, and `fetchReport3` resolve the selected offset from `lookbackColumnMap`, route D-1/D-2 requests through `dims.currentDateKey`, and pass the offset label to report-specific Supabase RPCs. PostgreSQL then computes category averages or joins dimension metadata before returning the result set. Each helper retains a compatibility fallback to the older browser-side path when the RPC has not yet been provisioned in Supabase.

**React Report 2 cross-filtering (R-20260506-2251):** `handleSettlementChange` in `Report2.jsx` calls `fetchCategoriesForSettlement(settlementKey, dateKey, dims)` on settlement selection; the result replaces `filteredCategories` state. If `selectedCategory` is not in the new filtered list it is cleared. `handleCategoryChange` calls `fetchSettlementsForCategory(categoryKey, dateKey, dims)`; if `selectedSettlement` is not in the new filtered list it is cleared and `filteredCategories` is reset to all categories (Q002-A: consistent with no-settlement state). Date change resets both `filteredCategories` and `filteredSettlements` to their full defaults. Both cross-filter RPC functions use the same PostgREST v10/v11 backward-compatibility guard and `currentDateKey` lookback routing as the existing `fetchSettlementsForDate`.

### Configuration and Parameterization

| Key | Section / File | Default | Tunable by |
|---|---|---|---|
| `opendata_url` | `config.ini [settings]` | `https://kolkostruva.bg/opendata` | Operator |
| `max_retries` | `config.ini [settings]` | `3` | Operator |
| `retry_delay` | `config.ini [settings]` | `10` | Operator |
| `log_level` | `config.ini [settings]` | `INFO` | Operator |
| `last_downloaded_date` | `config.ini [state]` | (empty) | Script on success; Operator for force re-download |
| `last_processed_date` | `config.ini [state]` | (empty) | Script on success; Operator for force re-process |
| `DATABASE_URL` | `.env` (project root) | (none; required) | Operator |
| `NETLIFY_AUTH_TOKEN` | `.env` (project root) or shell env | (none; required for deploy) | Operator; auto-saved to `.env` on first interactive entry |
| `NETLIFY_SITE_ID` | `.env` (project root) or shell env | (none; required for deploy) | Operator; auto-saved to `.env` on first interactive entry |
| `VITE_SUPABASE_URL` | `.env` (project root) | (none; required) | Operator |
| `VITE_SUPABASE_ANON_KEY` | `.env` (project root) | (none; required) | Operator |

### Inter-Component Communication

ETL: batch sequential. `config_utils.py` imported by ETL scripts directly. `menu.py` launches ETL scripts via `subprocess.run` (list-form; no `shell=True`). React app: unidirectional data flow — `App.jsx` fetches dimensions once and propagates `selectedDate` + `dimensions` props to page components.

---

## Data Architecture

### Data Sources

- **kolkostruva.bg/opendata (primary, external):** Daily ZIP archives via HTTP download. Owner: Bulgarian government.
- **EKATTE nomenclature (`data/nomenclatures/cities-ekatte-nomenclature.json`):** 5,256 entries (canonical 5-digit padded keys). Static reference; primary settlement lookup source.
- **Sofia district nomenclature (`data/nomenclatures/Ekatte/sof_rai.json`):** 38 Sofia sub-district codes. Static reference.
- **Extended EKATTE registry files (`data/nomenclatures/Ekatte/ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`):** Full NSI EKATTE registry; consulted as supplementary lookup sources after the primary file (R-20260501-0003). `ek_raion.json` uses the `raion` field (e.g. `68134-04`) as key; all others use `ekatte`.
- **Product categories (`data/nomenclatures/product-categories.json`):** 101 category ID-to-name entries. Static reference.

### Core Data Entities

| Entity | File | Columns | Grain | Actual size (2026-04-20) |
|---|---|---|---|---|
| Date dimension | `data/schema/dim_date.csv` | `date_key, date, year, month, day, weekday` | One row per calendar date | 63 rows |
| Company dimension | `data/schema/dim_company.csv` | `company_key, uic, company_name` | One row per UIC | 217 rows |
| Settlement dimension | `data/schema/dim_settlement.csv` | `settlement_key, ekatte, settlement_name` | One row per EKATTE code observed in facts | 266 rows |
| Category dimension | `data/schema/dim_category.csv` | `category_key, category_code, category_name` | One row per category code observed in facts | 369 rows |
| Product dimension | `data/schema/dim_product.csv` | `product_key, product_code, product_name` | One row per `(product_code, product_name)` pair | 118,281 rows |
| Store dimension | `data/schema/dim_store.csv` | `store_key, store_name, settlement_key, company_key` | One row per `(store_name, settlement_key, company_key)` | 4,824 rows |
| File dimension | `data/schema/dim_file.csv` | `file_key, file_name, zip_date` | One row per company CSV file inside each ZIP | 13,089 rows |
| Fact (partitioned) | `data/schema/facts/YYYY-MM-DD.csv` | `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price` | One row per product price observation | ~1.1–1.5 M rows/file; ~54–78 MB/file; 63 files |
| Lookback fact (derived) | `data/schema/fact_prices_lookback.csv` | 11 columns incl. 4 lookback price columns | One row per observation in latest fact date D, enriched with D-1 and D-2 prices | ~1.1–1.5 M rows; fully replaced per transform run |

### Data Lineage Summary

```
kolkostruva.bg/opendata (HTML)
  -> src/extract.py -> data/raw/YYYY-MM-DD.zip

data/raw/YYYY-MM-DD.zip  \
data/nomenclatures/*.json  -> src/transform.py -> data/schema/dim_*.csv
                                               -> data/schema/facts/YYYY-MM-DD.csv

data/schema/ -> src/load_supabase.py -> Supabase (dim_*, fact_prices_lookback,
                                                   backend_sql_audit_log,
                                                   get_available_dates(), get_settlements_for_date())

Supabase -> react-app (Netlify) -> end users (browser)
```

### Data Storage

- **Raw staging (`data/raw/`):** ZIP archives; not auto-pruned.
- **Star-schema outputs (`data/schema/`):** Seven flat dimension CSVs; 63+ date-partitioned fact CSVs; derived lookback table.
- **Supabase (cloud):** Nine relational tables: eight analytical tables plus `backend_sql_audit_log`; seven RPC helper functions (`get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, `get_settlements_for_category`, `get_report_1_category_prices`, `get_report_2_rows`, `get_report_3_rows` — all query `fact_prices_lookback` directly or through dimension joins; all GRANTED EXECUTE to anon); four B-tree indexes on `fact_prices_lookback`; and one executed-at index on `backend_sql_audit_log`. The React app queries the analytical tables and RPC functions via anon key; the backend SQL audit table is populated by `src/load_supabase.py` for operator inspection. `fact_prices` was deleted in R-20260430-0825.
- **Nomenclatures (`data/nomenclatures/`):** Static lookup files; not modified by scripts.

### Data Access Patterns

React app: dimension tables loaded once at startup (small dims cached in module scope); date list filtered to fact-present dates via `get_available_dates()` RPC; settlement list per date resolved via `get_settlements_for_date()` RPC; Reports 1, 2, and 3 fetched through RPCs that return grouped or enriched result sets keyed to the selected lookback offset. dim_product (~118K rows) never fully loaded client-side. Analysts may also access `data/schema/` CSVs directly with DuckDB or pandas.

### Data Retention

Local: Raw ZIPs and local fact CSVs under `data/raw/` and `data/schema/facts/` accumulate indefinitely (no automated pruning).

Remote (Supabase): `src/load_supabase.py` enforces two rolling retention windows on every sync run. After the lookback sync, `dim_date` is pruned to the 3 newest local fact dates and `dim_category` is pruned to only the `category_key` values referenced by `fact_prices_lookback` (R-20260507-2248). The same run also prunes `backend_sql_audit_log` to the last 30 days of repository-owned backend SQL history. The sync is idempotent: re-running with unchanged local inputs leaves the retained analytical window unchanged while refreshing audit rows only for the statements emitted by that run. This ensures the React app date selector only shows dates with retained fact data, category dropdowns do not expose stale historical entries, and the backend SQL audit trail remains bounded.

When settlement canonicalization changes, operators must rebuild local schema outputs and re-run `src/load_supabase.py` so `dim_settlement`, `dim_store`, and `fact_prices_lookback` are regenerated against the same canonical settlement identity before the React app reads Supabase again.

---

## Security & Compliance

### Authentication and Authorization

ETL pipeline: local batch script; no network-exposed service; no user authentication. React app: unauthenticated public access; Supabase anon key (public-safe). Supabase RLS must allow public SELECT on all star-schema tables. Supabase anon role must have EXECUTE on all seven React-facing RPC functions provisioned by `_CREATE_RPC_FUNCTIONS` DDL.

### Data Protection

- ETL download: HTTPS transport from kolkostruva.bg.
- Local storage: unencrypted; source data is publicly available government data — no PII processed.
- `config.ini`: no credentials; should be added to `.gitignore`.
- `.env` (project-root): contains all five environment keys: three server-side secrets (`DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`) and two client-safe keys (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`); excluded from VCS by `.gitignore`. `.env.example` committed (placeholder only, single consolidated template). No service role key in the React app.
- `backend_sql_audit_log`: stores fully rendered SQL text issued by `src/load_supabase.py`; operators should treat it as sensitive operational telemetry because literal values from ETL upserts and refresh statements are persisted there.

### Secrets Management

Five environment keys are consolidated into a single `.env` file at project root: (1) `DATABASE_URL` for Python ETL sync to Supabase; (2) `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` for Netlify deployment; (3) `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for React frontend via Vite build (VITE_-prefixed variables are client-exposed). The single root `.env` serves both Python scripts and React build. In Netlify production, inject via Netlify site environment variables (not committed `.env` files).

Credential loading precedence for Netlify deploy: shell environment variable (highest) → project-root `.env` (via `python-dotenv`) → interactive prompt (auto-saved to `.env` for future runs).

React build environment: Vite configured to load `.env` from repository root via `envDir: '../'`; only VITE_-prefixed variables are exposed to the browser.

### Regulatory and Compliance Requirements

No explicit compliance framework. Pipeline and app process publicly available government retail price data; no PII collected or stored.

### Known Security Considerations

- Download URLs resolved from trusted HTML source.
- No ZIP content hash verification.
- `subprocess` calls in `menu.py` use list-form; no shell injection risk.
- React app: no hardcoded credentials; anon key is public-safe by Supabase design.
- RPC functions use `SECURITY INVOKER` (default); anon role is explicitly GRANTed EXECUTE; no privilege escalation.
- Netlify deploy credentials (`NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`) are passed to subprocess via environment dict, not as CLI args; not visible in process listings or logs.
- Project-root `.env` is excluded from VCS by `.gitignore`; `.env.example` (committed) contains only placeholders.
- Netlify credentials auto-saved to `.env` on first interactive entry; file permissions default to 0644 on Linux (user-writable); best practice is `chmod 0600 .env` on shared machines.

---

## Operations

### Running the Pipeline

```bash
# Full ETL (Linux)
./refresh.sh

# Interactive menu (Linux)
./menu.sh

# Sync latest fact day to Supabase and provision RPC functions (requires .env with DATABASE_URL)
python src/load_supabase.py

# Deploy React app to Netlify (interactive; prompts for credentials if env vars not set)
python src/deploy_netlify.py
# Or via menu option 5

# Preview React app locally before Netlify deploy (production-like build)
# Via menu:
python menu.py   # then choose option 6
# Or manually:
cd react-app && npm run build && npm run preview
# Local URL: http://localhost:4173 (printed and opened in browser, best-effort)
```

### Running / Deploying the React App

```bash
# Local development
cd react-app
cp .env.example .env   # fill in VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
npm install
npm run dev

# Production build
npm run build          # produces react-app/dist/
```

Netlify deployment: set base directory to `react-app`; `netlify.toml` configures `build.command = "npm run build"` and `publish = "dist"`. Inject `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` as Netlify site environment variables.

### Config Control

- To force re-download: set `[state] last_downloaded_date = YYYY-MM-DD` in `config.ini`.
- To force re-process: set `[state] last_processed_date = YYYY-MM-DD` in `config.ini`.
- After settlement-key normalization changes: run `python3 src/transform.py` and then `python3 src/load_supabase.py` to rebuild local dimensions/facts and re-sync Supabase before validating Report 1 in the React app.
- `config.ini` bootstrapped automatically on first run.

### Logging

- `src/transform.py` writes `logs/transform_YYYYMMDD_HHMMSS.log` (one per run) and `data/quality/report_YYYYMMDD_HHMMSS.csv`.
- React app: browser console warnings when RPC functions are not yet provisioned in Supabase.

### Known Operational Risks

- External portal availability: `extract.py` retries up to `max_retries` times then exits non-zero.
- Raw data accumulation: not auto-pruned.
- Supabase anon read access required: if RLS blocks public SELECT, all React app queries return empty data.
- RPC functions not provisioned: if `load_supabase.py` has not been re-run after a React-facing RPC change, the app falls back to slower browser-side processing for the affected report path and emits a console warning.
- Stale remote settlement dimensions: after a settlement-normalization change, local verification may be correct while the deployed React app still shows duplicate settlement labels until `src/load_supabase.py` is re-run against Supabase.
- Supabase statement timeout (free tier ~3s): mitigated by B-tree indexes `idx_fact_prices_lookback_date_key`, `idx_fact_prices_lookback_date_store`, `idx_fpl_date_cat`, and `idx_fpl_date_store_category` on `fact_prices_lookback`. If free-tier shared-compute contention is severe, additional pre-computed summaries remain the escalation path.

### Recovery

A full workspace backup is stored at `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` (1.4 GB). To restore: `tar -xzf ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` from the parent directory.

### SLO / SLA

Not formally defined.

---

## Development Practices

### Repository Structure

- `src/` — Python ETL scripts (`extract.py`, `transform.py`, `config_utils.py`, `load_supabase.py`, `deploy_netlify.py`).
- `tests/` — Python unit and smoke test suite (117 tests pass, 1 skipped); covers all ETL modules and menu.
- `react-app/` — React + Vite SPA for Netlify deployment.
  - `react-app/src/lib/` — Supabase client singleton and data service layer.
  - `react-app/src/components/` — Page components (HomePage, Report1, Report2, Report3).
  - `react-app/src/App.jsx` + `App.css` — Root component and global styles.
  - `react-app/netlify.toml` — Netlify build configuration.
  - `react-app/vite.config.js` — Vite build config (envDir set to load root `.env`).
- `build-legacy/web/` — Legacy vanilla-JS app; retained as reference; replaced by `react-app/`.
- `data/raw/` — Raw ZIP archives.
- `data/schema/` — Star-schema CSV outputs.
- `data/nomenclatures/` — Static EKATTE and product-category reference files.
- `logs/` — ETL and AIB framework logs.
- Root: `config.ini`, `.env`, `.env.example`, `refresh.sh`, `refresh.bat`, `menu.py`, `menu.sh`, `menu.bat`, `README.md`, `requirements.txt`.

### Developer Setup

**Python ETL:**
1. Python 3.9+ required.
2. `python3 -m venv venv && source venv/bin/activate` (Linux).
3. `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and fill in `DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, and `NETLIFY_SITE_ID`.
5. Run `./refresh.sh` and/or `python menu.py`.

**Netlify Deploy Credential Setup:**
1. Copy `.env.example` to `.env` (if not already done): `cp .env.example .env`.
2. Fill in `NETLIFY_AUTH_TOKEN` (Netlify personal access token) and `NETLIFY_SITE_ID` (site UUID) in `.env`.
3. Alternatively, run menu option 5 or `python src/deploy_netlify.py` and enter credentials at the interactive prompt; they will be auto-saved to `.env` for future runs.
4. Credential loading precedence: shell environment variable → `.env` file → interactive prompt.

**React App:**
1. Node.js 18+ required (Node 22 verified).
2. `cd react-app && cp .env.example .env` — fill in `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
3. `npm install`.
4. `npm run dev` (development server), `npm run build` (production build), or `npm run preview` (local production-like preview after build).

### Testing Strategy

- Python ETL: `tests/test_config_utils.py` smoke tests for `load_config()` and `save_state()` (8 tests). Unit tests for `src/deploy_netlify.py` and menu.py option dispatch (24 tests in `test_deploy_netlify.py`). Unit tests for `src/extract.py` covering `parse_zip_links`, `existing_filenames`, incremental-skip, and atomic rename logic (9 tests in `test_extract.py`). Unit tests for `src/transform.py` covering delimiter detection, dim upsert, dim load/write, quality-report write, extended EKATTE file loading (`TestLoadSettlementNames`: raion-code resolution, metadata-row skip, absent-file handling), three-step code normalisation (`TestResolveSettlementName`: zero-padding, leading-zero strip, unresolvable, exact-match precedence, empty string), and in-place dim patch (`TestPatchUnknownSettlements`: targeted update, surrogate key preservation, idempotency, absent-file) (24 tests in `test_transform.py` — R-20260501-0003). Unit tests for `src/load_supabase.py` covering `create_tables` (5 DDL calls including migration DDL and index DDL — R-20260430-0825), `_CREATE_INDEXES` constant content and target table, `_CREATE_DDL` exclusion of `fact_prices`, `upsert_dim_sql`, `insert_lookback` (3 tests — R-20260430-0825), `get_retained_local_dates` (8 tests), `get_date_keys_for_dates` (3 tests), `prune_dim_date` (6 tests) — R-20260429-0825 (32 tests total in `test_load_supabase.py`). Unit tests for `menu.py` covering `action_local_preview()` call order and credential validation, stats helpers, `read_state`, main loop dispatch, and anon-key JWT role security check (23 tests in `test_menu.py`; T12 anon-key test currently skipped pending service_role → anon key rotation in root `.env`). 117 Python tests pass, 1 skipped (`venv/bin/python -m pytest tests/`).
- React app: Vitest + @testing-library/react test suite (`npm run test` in `react-app/`). `src/lib/dataService.test.js` covers helper formatting, price calculation, wrapped-object and raw-integer RPC formats, settlement/category cross-filter RPCs, lookback mapping, dim_file loading, report-RPC contracts for Reports 1, 2, and 3, and `fetchAllFileRows` multi-page loading (29 tests: 25 pre-existing + 4 added in R-20260517-1244 for T-FAR-1 through T-FAR-4). `FileDetailPage.test.jsx` covers file list rendering, date filtering, click-to-drill-down, close-panel behavior, and `fetchAllFileRows` integration (R-20260513-2123, updated R-20260517-1244). `FileRowDetailModal.test.jsx` covers smoke render, display fields, close button, Escape key, and backdrop-click dismissal (R-20260517-1113). `FileRowsPanel.test.jsx` covers loading state, row rendering (all 12 columns), empty state, error state, close-button callback, pagination, header display, sort ascending, sort descending, sort cleared on third click, case-insensitive filter match, filter cleared restoring rows, 2500-row 25-page full load, and exactly 1000 rows no-regression (23 tests total — T1–T21 pre-existing, T22–T23 added in R-20260517-1244). Other component tests cover Report 1 duplicate-settlement labels, Report 2 cross-filter/modal behavior, Report 3 filter/pagination/full-load behavior (15 tests: 3 pre-existing smoke + 12 added in R-20260518-1052), `RecordDetailModal`, and `App` startup/date-selector flows. `dataService.test.js` gained 2 new tests for `fetchReport3` pagination (T-R3-1, T-R3-2 in R-20260518-1052). Full suite: 115 tests pass after R-20260518-1052 (`npm run test` in `react-app/`).

### CI/CD

No CI/CD pipeline configuration is present.

### Branching and Code Conventions

Not documented. No `CONTRIBUTING.md`. No git repository initialized. The pre-R-20260418-2209 tarball is the sole rollback mechanism.

---

## Constraints & Assumptions

### Technical Constraints

- Python 3.9+ required; ETL core uses only Python stdlib.
- React app: Node.js 18+ required; Vite 5; `@supabase/supabase-js` v2 as sole DB client; no SSR.
- No git repository initialized; tarball backup is the sole rollback mechanism.
- Source ZIP filenames follow `YYYY-MM-DD.zip`; internal CSV structure is 7-column Bulgarian retail-price format.
- React app: Supabase anon key only; no service role key; no server-side rendering.

### Organizational Constraints

- Source data format and availability depend on kolkostruva.bg; outside product team's control.
- Supabase RLS policies must allow public SELECT on all star-schema tables for the React app to function.

### Assumptions

- A1 (React app): Supabase instance has all star-schema tables populated by `src/load_supabase.py`. Risk if false: App queries return empty data.
- A2 (React app): Supabase anon key has SELECT access on all star-schema tables. Risk if false: All queries return 0 rows or HTTP 401/403.
- A3 (ETL): All ZIPs follow `YYYY-MM-DD.zip` naming; internal CSVs use 7 columns with comma or semicolon delimiters; encoding is UTF-8 with optional BOM.
- A4 (React app): dim_settlement (266 rows), dim_category (369 rows), dim_store (4,824 rows), dim_date (~63 rows) are small enough to load fully client-side without latency issues.
- A5 (React app): dim_product (118,281 rows) is never fully loaded; product names fetched via batched key lookups.
- A6 (ETL): `dim_settlement` is built facts-driven from canonicalized settlement identifiers; `normalize_settlement_code()` collapses padded EKATTE variants such as `068134` and `68134` before `dim_settlement` and `dim_store` natural keys are assigned, while settlement names are still resolved via `resolve_settlement_name()` using seven EKATTE nomenclature sources. Risk if false: a future source-data variant outside the current canonicalization rules could still produce duplicate analytical identities until the normalizer is extended.
- A7 (React app, R-20260422-0902, R-20260430-0825): The only authoritative source for which dates have fact data in Supabase is `fact_prices_lookback.date_key`. The `get_available_dates()` RPC reflects this. Risk if false: date dropdown may under-report available dates if fact data is spread across multiple tables.
- A8 (React app, R-20260422-0902, R-20260512-0529): Supabase anon role has EXECUTE on all React-facing RPC functions granted by `_CREATE_RPC_FUNCTIONS` DDL. The operator must re-run `python src/load_supabase.py` to provision these functions in Supabase after deployment. Until then, the app falls back gracefully with a console warning.
- A9 (R-20260429-0757, R-20260430-0825, R-20260512-0529): B-tree indexes `idx_fact_prices_lookback_date_key`, `idx_fact_prices_lookback_date_store`, `idx_fpl_date_cat`, and `idx_fpl_date_store_category` on `fact_prices_lookback` are sufficient to keep the filter and report RPCs within Supabase free-tier statement timeout. Risk if false: severe shared-compute contention may still cause timeouts; escalation path is additional pre-computed summary structures.

### Validity Horizon

- Revisit A3 if kolkostruva.bg changes the ZIP naming convention or CSV column layout.
- Revisit A1/A2 if Supabase RLS policies change or credentials rotate.
- Revisit the fallback-only browser path if report-RPC provisioning ever becomes operationally unreliable.
- Revisit A7/A8 if the star schema is restructured or additional fact tables are introduced.

---

## Glossary

**BOM**: Byte Order Mark — a Unicode character (`\ufeff`) at the start of some UTF-8 CSV files; must be stripped before parsing.

**Date-partitioned facts**: A storage strategy where the fact table is split into one file per date (`data/schema/facts/YYYY-MM-DD.csv`).

**Dimension from facts**: A dimension-loading strategy where surrogate key entries are created only for codes actually observed in the fact stream.

**DuckDB**: A fast in-process analytical SQL engine; not a build dependency but the recommended tool for querying partitioned star-schema fact files.

**EKATTE**: A Bulgarian administrative-territorial units code registry maintained by the NSI; each settlement has a unique 5–6 digit code.

**ETL**: Extract, Transform, Load.

**No-rejection policy**: All rows with a structurally valid column count retained; unknown codes produce placeholder dimension entries; non-parseable prices store NULL.

**RPC (Supabase)**: Remote Procedure Call invoked via `supabase.rpc()` against a PostgreSQL function in the public schema; returns a JSON array; used here for `get_available_dates` and `get_settlements_for_date`.

**Star schema**: A dimensional modelling pattern with a central fact table referencing surrogate keys from surrounding dimension tables.

**Surrogate key**: An integer primary key generated by the ETL process; stable across re-runs once assigned.

**UIC (ЕИК)**: Unified Identification Code — the Bulgarian national tax registration number uniquely identifying a legal entity.

---

## Workspace File Inventory

- `.aib_memory/` — AIB framework memory directory.
- `.aib_memory/context.md` — This file; unified workspace context.
- `.aib_memory/references.md` — Registry of product documentation files tracked by AIB.
- `.aib_memory/requests_register.md` — Register of all AIB requests with state and folder references.
- `.aib_memory/requests/` — Per-request artifact folders.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/` — Request folder for R-20260506-2251.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/UAT_scenarios.md` — UAT scenarios for cross-filter-dropdowns-and-record-detail-modal.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/analysis.md` — Analysis artifact for cross-filter-dropdowns-and-record-detail-modal.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/implementation.md` — Implementation log for cross-filter-dropdowns-and-record-detail-modal.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/inputs/` — Input artifacts for R-20260506-2251 request.
- `.aib_memory/requests/R-20260506-2251-cross-filter-dropdowns-and-record-detail-modal/request.md` — Request definition for cross-filter-dropdowns-and-record-detail-modal.
- `.aib_memory/requests/R-20260507-0942-investigate-and-clean-unknown-dim-category-entries/` — Request folder for R-20260507-0942.
- `.aib_memory/requests/R-20260507-0942-investigate-and-clean-unknown-dim-category-entries/analysis.md` — Analysis artifact for investigate-and-clean-unknown-dim-category-entries.
- `.aib_memory/requests/R-20260507-0942-investigate-and-clean-unknown-dim-category-entries/implementation.md` — Implementation log for investigate-and-clean-unknown-dim-category-entries.
- `.aib_memory/requests/R-20260507-0942-investigate-and-clean-unknown-dim-category-entries/inputs/` — Input artifacts for R-20260507-0942 request.
- `.aib_memory/requests/R-20260507-0942-investigate-and-clean-unknown-dim-category-entries/request.md` — Request definition for investigate-and-clean-unknown-dim-category-entries.
- `.aib_memory/requests/R-20260507-2248-scope-dim-category-to-last-3-days-of-facts/` — Request folder for R-20260507-2248.
- `.aib_memory/requests/R-20260507-2248-scope-dim-category-to-last-3-days-of-facts/analysis.md` — Analysis artifact for scope-dim-category-to-last-3-days-of-facts.
- `.aib_memory/requests/R-20260507-2248-scope-dim-category-to-last-3-days-of-facts/implementation.md` — Implementation log for scope-dim-category-to-last-3-days-of-facts.
- `.aib_memory/requests/R-20260507-2248-scope-dim-category-to-last-3-days-of-facts/inputs/` — Input artifacts for R-20260507-2248 request.
- `.aib_memory/requests/R-20260507-2248-scope-dim-category-to-last-3-days-of-facts/request.md` — Request definition for scope-dim-category-to-last-3-days-of-facts.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/` — Request folder for R-20260508-0743.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/UAT_scenarios.md` — UAT scenarios for investigate-category-prices-page-calculation.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/analysis.md` — Analysis artifact for investigate-category-prices-page-calculation.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/implementation.md` — Implementation log for investigate-category-prices-page-calculation.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/inputs/` — Input artifacts for R-20260508-0743 request.
- `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/request.md` — Request definition for investigate-category-prices-page-calculation.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/` — Request folder for R-20260509-2012.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/UAT_scenarios.md` — UAT scenarios for add-sql-query-log-page-for-current-session.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/analysis.md` — Analysis artifact for add-sql-query-log-page-for-current-session.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/implementation.md` — Implementation log for add-sql-query-log-page-for-current-session.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/inputs/` — Input artifacts for R-20260509-2012 request.
- `.aib_memory/requests/R-20260509-2012-add-sql-query-log-page-for-current-session/request.md` — Request definition for add-sql-query-log-page-for-current-session.
- `.aib_memory/requests/R-20260509-2113-log-exact-backend-sql-text-to-database/` — Request folder for R-20260509-2113.
- `.aib_memory/requests/R-20260509-2113-log-exact-backend-sql-text-to-database/analysis.md` — Analysis artifact for log-exact-backend-sql-text-to-database.
- `.aib_memory/requests/R-20260509-2113-log-exact-backend-sql-text-to-database/implementation.md` — Implementation log for log-exact-backend-sql-text-to-database.
- `.aib_memory/requests/R-20260509-2113-log-exact-backend-sql-text-to-database/inputs/` — Input artifacts for R-20260509-2113 request.
- `.aib_memory/requests/R-20260509-2113-log-exact-backend-sql-text-to-database/request.md` — Request definition for log-exact-backend-sql-text-to-database.
- `.aib_memory/requests/R-20260510-0038-fix-supabase-retention-prune-crash/` — Request folder for R-20260510-0038.
- `.aib_memory/requests/R-20260510-0038-fix-supabase-retention-prune-crash/analysis.md` — Analysis artifact for fix-supabase-retention-prune-crash.
- `.aib_memory/requests/R-20260510-0038-fix-supabase-retention-prune-crash/implementation.md` — Implementation log for fix-supabase-retention-prune-crash.
- `.aib_memory/requests/R-20260510-0038-fix-supabase-retention-prune-crash/inputs/` — Input artifacts for R-20260510-0038 request.
- `.aib_memory/requests/R-20260510-0038-fix-supabase-retention-prune-crash/request.md` — Request definition for fix-supabase-retention-prune-crash.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/` — Request folder for R-20260512-0529.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/UAT_scenarios.md` — UAT scenarios for improve-slow-pages-by-pushing-aggregation-to-database.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/analysis.md` — Analysis artifact for improve-slow-pages-by-pushing-aggregation-to-database.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/implementation.md` — Implementation log for improve-slow-pages-by-pushing-aggregation-to-database.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/inputs/` — Input artifacts for R-20260512-0529 request.
- `.aib_memory/requests/R-20260512-0529-improve-slow-pages-by-pushing-aggregation-to-database/request.md` — Request definition for improve-slow-pages-by-pushing-aggregation-to-database.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/` — Request folder for R-20260512-2138.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/UAT_scenarios.md` — UAT scenarios for responsive-ui-for-mobile-and-desktop-devices.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/analysis.md` — Analysis artifact for responsive-ui-for-mobile-and-desktop-devices.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/implementation.md` — Implementation log for responsive-ui-for-mobile-and-desktop-devices.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/inputs/` — Input artifacts for R-20260512-2138 request.
- `.aib_memory/requests/R-20260512-2138-responsive-ui-for-mobile-and-desktop-devices/request.md` — Request definition for responsive-ui-for-mobile-and-desktop-devices.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/` — Request folder for R-20260513-2123.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/UAT_scenarios.md` — UAT scenarios for replace-query-log-page-with-file-detail-page.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/analysis.md` — Analysis artifact for replace-query-log-page-with-file-detail-page.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/implementation.md` — Implementation log for replace-query-log-page-with-file-detail-page.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/inputs/` — Input artifacts for R-20260513-2123 request.
- `.aib_memory/requests/R-20260513-2123-replace-query-log-page-with-file-detail-page/request.md` — Request definition for replace-query-log-page-with-file-detail-page.
- `.aib_memory/requests/R-20260514-2102-file-row-detail-view-in-page/` — Request folder for R-20260514-2102.
- `.aib_memory/requests/R-20260514-2102-file-row-detail-view-in-page/analysis.md` — Analysis artifact for file-row-detail-view-in-page.
- `.aib_memory/requests/R-20260514-2102-file-row-detail-view-in-page/implementation.md` — Implementation log for file-row-detail-view-in-page.
- `.aib_memory/requests/R-20260514-2102-file-row-detail-view-in-page/inputs/` — Input artifacts for R-20260514-2102 request.
- `.aib_memory/requests/R-20260514-2102-file-row-detail-view-in-page/request.md` — Request definition for file-row-detail-view-in-page.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/` — Request folder for R-20260515-1003.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/UAT_scenarios.md` — UAT scenarios for fix-file-detail-table-overflow-and-column-sort-and-filter.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/analysis.md` — Analysis artifact for fix-file-detail-table-overflow-and-column-sort-and-filter.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/implementation.md` — Implementation log for fix-file-detail-table-overflow-and-column-sort-and-filter.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/inputs/` — Input artifacts for R-20260515-1003 request.
- `.aib_memory/requests/R-20260515-1003-fix-file-detail-table-overflow-and-column-sort-and-filter/request.md` — Request definition for fix-file-detail-table-overflow-and-column-sort-and-filter.
- `.aib_memory/requests/R-20260516-1313-fix-file-detail-table-layout-dates-and-filter-pagination/` — Request folder for R-20260516-1313.
- `.aib_memory/requests/R-20260516-1313-fix-file-detail-table-layout-dates-and-filter-pagination/analysis.md` — Analysis artifact for fix-file-detail-table-layout-dates-and-filter-pagination.
- `.aib_memory/requests/R-20260516-1313-fix-file-detail-table-layout-dates-and-filter-pagination/implementation.md` — Implementation log for fix-file-detail-table-layout-dates-and-filter-pagination.
- `.aib_memory/requests/R-20260516-1313-fix-file-detail-table-layout-dates-and-filter-pagination/inputs/` — Input artifacts for R-20260516-1313 request.
- `.aib_memory/requests/R-20260516-1313-fix-file-detail-table-layout-dates-and-filter-pagination/request.md` — Request definition for fix-file-detail-table-layout-dates-and-filter-pagination.
- `.aib_memory/requests/R-20260517-1113-file-detail-record-clickable-modal-and-modern-paging/` — Request folder for R-20260517-1113.
- `.aib_memory/requests/R-20260517-1113-file-detail-record-clickable-modal-and-modern-paging/analysis.md` — Analysis artifact for file-detail-record-clickable-modal-and-modern-paging.
- `.aib_memory/requests/R-20260517-1113-file-detail-record-clickable-modal-and-modern-paging/implementation.md` — Implementation log for file-detail-record-clickable-modal-and-modern-paging.
- `.aib_memory/requests/R-20260517-1113-file-detail-record-clickable-modal-and-modern-paging/inputs/` — Input artifacts for R-20260517-1113 request.
- `.aib_memory/requests/R-20260517-1113-file-detail-record-clickable-modal-and-modern-paging/request.md` — Request definition for file-detail-record-clickable-modal-and-modern-paging.
- `.aib_memory/requests/R-20260517-1244-fix-missing-records-in-file-detail-page/` — Request folder for R-20260517-1244.
- `.aib_memory/requests/R-20260517-1244-fix-missing-records-in-file-detail-page/implementation.md` — Implementation log for fix-missing-records-in-file-detail-page.
- `.aib_memory/requests/R-20260517-1244-fix-missing-records-in-file-detail-page/inputs/` — Input artifacts for R-20260517-1244 request.
- `build-legacy/` — Legacy web application directory; retained as reference.
- `build-legacy/web/index.html` — Legacy HTML entry point (vanilla JS).
- `build-legacy/web/script.js` — Legacy report generation and chart rendering logic.
- `build-legacy/web/style.css` — Legacy CSS; ported to `react-app/src/App.css`.
- `config.ini` — Central pipeline configuration; `[settings]` and `[state]` sections.
- `curl https ekootljybgoenduwprbw.txt` — Local text file capturing a raw curl command output (reference artifact; not used by scripts).
- `data/` — Root data directory.
- `data/nomenclatures/` — Static EKATTE and product-category reference files.
- `data/nomenclatures/cities-ekatte-nomenclature.json` — Primary EKATTE-to-settlement-name mapping (5,256 entries).
- `data/nomenclatures/product-categories.json` — Product category ID-to-name mapping (101 entries).
- `data/nomenclatures/Ekatte/` — Full EKATTE registry files from NSI.
- `data/nomenclatures/Ekatte/sof_rai.json` — Sofia sub-district codes (38 entries).
- `data/nomenclatures/Ekatte/ek_atte.json` — Full settlement EKATTE registry (5,257 entries); supplementary lookup source (R-20260501-0003).
- `data/nomenclatures/Ekatte/ek_kmet.json` — Кметства (village mayor settlements) registry (3,042 entries); supplementary lookup source (R-20260501-0003).
- `data/nomenclatures/Ekatte/ek_raion.json` — City district (raion) registry; codes use dash format `XXXXX-YY` (R-20260501-0003).
- `data/nomenclatures/Ekatte/ek_obl.json` — Oblast (province) registry (29 entries); supplementary lookup source (R-20260501-0003).
- `data/nomenclatures/Ekatte/ek_obst.json` — Obshtina (municipality) registry (266 entries); supplementary lookup source (R-20260501-0003).
- `data/nomenclatures/EkatteXLS/` — Excel and text versions of the EKATTE administrative-unit registry files from NSI.
- `data/nomenclatures/EkatteXLS/Ekat_str.txt` — EKATTE structure documentation text file.
- `data/nomenclatures/EkatteXLS/Ekat_ver.txt` — EKATTE version notes text file.
- `data/nomenclatures/EkatteXLS/ek_atte.xlsx` — Excel version of the full settlement EKATTE registry.
- `data/nomenclatures/EkatteXLS/ek_doc.xlsx` — EKATTE documentation workbook.
- `data/nomenclatures/EkatteXLS/ek_kmet.xlsx` — Excel version of the кметства registry.
- `data/nomenclatures/EkatteXLS/ek_obl.xlsx` — Excel version of the oblast registry.
- `data/nomenclatures/EkatteXLS/ek_obst.xlsx` — Excel version of the obshtina registry.
- `data/nomenclatures/EkatteXLS/ek_raion.xlsx` — Excel version of the city-district (raion) registry.
- `data/nomenclatures/EkatteXLS/ek_reg1.xlsx` — Excel version of EKATTE region register part 1.
- `data/nomenclatures/EkatteXLS/ek_reg2.xlsx` — Excel version of EKATTE region register part 2.
- `data/nomenclatures/EkatteXLS/ek_sobr.xlsx` — Excel version of the EKATTE supplementary register.
- `data/nomenclatures/EkatteXLS/sof_rai.xlsx` — Excel version of the Sofia sub-district codes.
- `data/nomenclatures/unknown_categories_explanation.md` — Explanation of unknown category codes observed in the product dimension.
- `data/quality/` — Quality reports from `src/transform.py` runs.
- `data/raw/` — Raw ZIP archive storage; not auto-pruned.
- `data/schema/` — Star-schema CSV outputs.
- `data/schema/dim_category.csv` — Category dimension table.
- `data/schema/dim_company.csv` — Company dimension table.
- `data/schema/dim_date.csv` — Date dimension table (63 rows).
- `data/schema/dim_file.csv` — File dimension table (13,089 rows).
- `data/schema/dim_product.csv` — Product dimension table (118,281 rows).
- `data/schema/dim_settlement.csv` — Settlement dimension table (266 rows).
- `data/schema/dim_store.csv` — Store dimension table (4,824 rows).
- `data/schema/fact_prices_lookback.csv` — Derived lookback fact table (11 columns; fully replaced per transform run).
- `data/schema/facts/` — Date-partitioned fact CSVs (one file per date; ~54–78 MB each).
- `lab/` — Laboratory workspace directory; contains dated snapshots of raw retailer CSV files for ad-hoc inspection and analysis.
- `lab/2026-05-13/` — Snapshot of retailer CSV files extracted from `2026-05-13.zip` for analysis (209 individual company CSV files).
- `lab/2026-05-13.zip` — Raw ZIP archive for the 2026-05-13 date; source of the CSV files in the `2026-05-13/` subdirectory.
- `logs/` — ETL and AIB framework log files.
- `menu.bat` — Windows menu launcher.
- `menu.py` — Interactive terminal menu; ETL statistics and action runner.
- `menu.sh` — Linux menu launcher.
- `netlify token.txt` — Plaintext file storing a Netlify authentication token for manual reference; should not be committed to VCS.
- `react-app/` — React + Vite SPA for Netlify deployment.
- `react-app/index.html` — Vite HTML entry point.
- `react-app/netlify.toml` — Netlify build configuration (`command = "npm run build"`, `publish = "dist"`).
- `react-app/package.json` — npm package manifest; React 18, Vite 5, @supabase/supabase-js v2.
- `react-app/test_output.txt` — Captured output from a previous Vitest run; retained as reference artifact.
- `react-app/vite.config.js` — Vite configuration with React plugin; envDir set to load root `.env` for VITE_ variables.
- `react-app/src/App.css` — Global application styles; port of `build-legacy/web/style.css`.
- `react-app/src/App.jsx` — Root React component; global state, date selector, navigation.
- `react-app/src/App.test.jsx` — Integration tests for App.jsx: credentials-error, date-selector population, empty-dates placeholder, 3-date selector (7 tests).
- `react-app/src/index.css` — CSS reset and body base.
- `react-app/src/main.jsx` — React 18 `createRoot` entry point.
- `react-app/src/test-setup.js` — Vitest test setup file; configures @testing-library/jest-dom matchers.
- `react-app/src/components/FileDetailPage.jsx` — Source-file detail page listing dim_file entries for the selected date with file name, submission date, and record count; file rows are clickable to open `FileRowsPanel` (R-20260513-2123).
- `react-app/src/components/FileDetailPage.test.jsx` — Unit tests for FileDetailPage.jsx covering file list rendering, date filtering, click-to-drill-down, close-panel behavior, and `fetchAllFileRows` mock (R-20260513-2123, updated R-20260517-1244).
- `react-app/src/components/FileRowDetailModal.jsx` — Modal dialog showing all 11 display fields and surrogate keys for a clicked FileRowsPanel row; dismisses via Escape or backdrop click (R-20260517-1113).
- `react-app/src/components/FileRowDetailModal.test.jsx` — Unit tests for FileRowDetailModal.jsx: smoke render, display fields, close button, Escape key, backdrop click (R-20260517-1113).
- `react-app/src/components/FileRowsPanel.jsx` — Drill-down panel showing a paginated 11-column price-fact table for a selected dim_file entry; uses `fetchAllFileRows` for multi-pass loading, with client-side sort, filter, and pagination (R-20260514-2102, updated R-20260517-1244).
- `react-app/src/components/FileRowsPanel.test.jsx` — Unit tests for FileRowsPanel.jsx: loading state, row rendering, empty/error states, pagination, sort, filter, 2500-row load, and exactly 1000 rows regression (23 tests; R-20260514-2102, updated R-20260517-1244).
- `react-app/src/components/HomePage.jsx` — Landing page with feature cards and CTA.
- `react-app/src/components/HomePage.test.jsx` — Smoke tests for HomePage.jsx (3 tests).
- `react-app/src/components/RecordDetailModal.jsx` — Modal dialog showing full record provenance for a clicked Report 2 row; closes via button or Escape key (R-20260506-2251).
- `react-app/src/components/RecordDetailModal.test.jsx` — Unit tests for RecordDetailModal.jsx: smoke render, file name, close button, Escape key, null row guard, backdrop click (7 tests; R-20260506-2251).
- `react-app/src/components/Report1.jsx` — Report 1: avg price by category for selected city (bar chart).
- `react-app/src/components/Report1.test.jsx` — Smoke tests for Report1.jsx (3 tests).
- `react-app/src/components/Report2.jsx` — Report 2: products by city and category; 7-column table with bidirectional cross-filtering between settlement and category dropdowns; row click opens RecordDetailModal (R-20260506-2251).
- `react-app/src/components/Report2.test.jsx` — Tests for Report2.jsx: cross-filter dispatch, date-change reload, row-click modal, close-modal preserves filters (8 tests; R-20260506-2251).
- `react-app/src/components/Report3.jsx` — Report 3: locations and products by category; 7-column table with per-column substring filter inputs, five-element pagination bar (PAGE_SIZE=100), record count summary, and category-change state reset; full result set loaded without row cap (R-20260518-1052).
- `react-app/src/components/Report3.test.jsx` — Tests for Report3.jsx: smoke render, heading, category dropdown, 7 filter inputs render, filter narrows rows, record count summary, pagination indicator, first/prev disabled on page 1, last/next disabled on single page, next/last enabled with >100 rows, category change resets filters (15 tests: 3 pre-existing + 12 added in R-20260518-1052).
- `react-app/public/favicon.ico` — Minimal 1x1 transparent ICO file (66 bytes); eliminates browser 404 on favicon requests (R-20260429-0757); copied to `dist/` by Vite on build.
- `react-app/src/lib/dataService.js` — All Supabase data-fetching functions and client-side aggregation logic; includes RPC-based date/settlement/cross-filter querying, `dim_file` provenance loading, `fetchFileRows` (paginated single-range, retained for backward compatibility), `fetchAllFileRows` (multi-pass loader that pages through all rows in `SUPABASE_PAGE_SIZE` chunks — R-20260517-1244), and `fetchReport3` (multi-pass paginated loader via `.range()` calls, no row cap — R-20260518-1052) (R-20260422-0902, R-20260506-2251).
- `react-app/src/lib/dataService.test.js` — Unit tests for dataService.js: formatDateBG, calculatePrice, fetchDimensions, fetchSettlementsForDate, normalizeRow, fetchCategoriesForSettlement, fetchSettlementsForCategory, fetchReport2 file enrichment, fetchAllFileRows multi-page loading, and fetchReport3 paginated RPC with .range() (31 tests: 25 pre-existing + 4 added in R-20260517-1244 + 2 added in R-20260518-1052).
- `react-app/src/lib/queryLog.js` — Session-scoped in-memory store for frontend-visible Supabase query activity; exposes snapshot, subscription, append, clear, and test-reset helpers; active-but-UI-less infrastructure retained after the Query Log page was removed in R-20260513-2123.
- `react-app/src/lib/supabase.js` — Supabase client singleton.
- `react-app/dist/` — Production build output (generated by `npm run build`; not committed to VCS).
- `README.md` — Project readme.
- `refresh.bat` — Windows ETL runner (download + transform).
- `refresh.sh` — Linux ETL runner (download + transform); detects venv.
- `requirements.txt` — Python package dependencies for ETL scripts.
- `src/config_utils.py` — Shared configuration helpers (`load_config`, `save_state`).
- `src/extract.py` — Download script; scrapes open-data index and downloads new ZIPs.
- `src/load_supabase.py` — Supabase sync module; provisions all eight star-schema tables, four RPC helper functions (`get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`, `get_settlements_for_category` — all query `fact_prices_lookback`), and three B-tree indexes on `fact_prices_lookback`; upserts dimensions; truncates and reinserts `fact_prices_lookback` on every sync run; enforces rolling 3-day remote retention on `dim_date` (R-20260429-0825, R-20260506-2251). `fact_prices` was deleted and all related ETL steps removed in R-20260430-0825.
- `src/transform.py` — ETL transformation engine; produces star-schema dimension and fact CSVs.
- `src/deploy_netlify.py` — Netlify deploy helper; builds React app and runs Netlify CLI deploy.
- `tests/test_config_utils.py` — Smoke tests for `src/config_utils.py` (8 tests).
- `tests/test_deploy_netlify.py` — Unit tests for `src/deploy_netlify.py` and menu.py integration (24 tests; covers CLI detection, credential loading, auto-save, and menu options 5–6).
- `tests/test_extract.py` — Unit tests for `src/extract.py` (9 tests; covers ZIP discovery, incremental-skip, and atomic rename logic).
- `tests/test_load_supabase.py` — Unit tests for `src/load_supabase.py` (32 tests; covers DDL provisioning including migration DDL and lookback indexes, `insert_lookback`, dimension upsert, retention pruning — R-20260430-0825).
- `tests/test_menu.py` — Unit tests for `menu.py` (23 tests; covers stats helpers, action dispatch, local-preview credential validation, and anon-key JWT role check; 1 skipped).
- `tests/test_transform.py` — Unit tests for `src/transform.py` (24 tests; covers delimiter detection, dim upsert, dim CSV load/write, quality-report write, extended EKATTE loading, three-step normalisation, and in-place dim patch — R-20260501-0003).
