# Product Context

> **Auto-generated** by `aib-context.md` on 2026-04-30 09:15 UTC+3 (updated by R-20260429-0825).
> Updated by R-20260430-0825: deleted `fact_prices`; `fact_prices_lookback` is now the sole Supabase fact table.
> Updated by R-20260430-1505: React app date selector now exposes all 3 dim_date rows (D, D-1, D-2); lookback price columns resolved client-side via `normalizeRow()`.
> Framework definition assets (`.aib_brain/`) are excluded by design — see `.aib_brain/` for AIB framework internals.
> This document is a synthesis of product documentation and workspace sources. It is fully replaced on each execution.

## Product Identity

**Kolko Ni Struva ETL Pipeline + React Analytics App** (version: not explicitly versioned; active as of 2026-04-23).

The product has two integrated layers:

1. **ETL Pipeline:** Downloads daily retail-price ZIP archives from the Bulgarian government open-data portal (kolkostruva.bg/opendata), transforms them into a star-schema structured dataset under `data/schema/`, syncs the star-schema to a Supabase-hosted PostgreSQL database, and provides operator tooling: interactive terminal menu (`menu.py`), ETL runner scripts (`refresh.sh` / `refresh.bat`), and a central configuration file (`config.ini`).

2. **React Analytics App:** A React + Vite single-page application (`react-app/`) deployed on Netlify that queries the Supabase database directly and visualises retail price data in four views (Home, Report 1, Report 2, Report 3), replacing the legacy vanilla-JS app (`build-legacy/web/`).

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

6. Sync the star-schema to a Supabase-hosted PostgreSQL database via `src/load_supabase.py`: provision all eight tables plus two RPC helper functions, upsert all seven dimension CSVs, truncate and reinsert `fact_prices_lookback` on every sync run, and prune `dim_date` to the latest 3 local fact dates so the React app date selector only shows retained dates. (per R-20260420-1730, R-20260422-0902, R-20260429-0825, R-20260430-0825)

7. React Analytics App deployed on Netlify (`react-app/`): four views — Home (landing), Report 1 (avg price by category for selected city — bar chart), Report 2 (products by city and category — 7-column table), Report 3 (locations and products by category — 7-column table). Date selector in header shows all 3 `dim_date` rows (D, D-1, D-2); D-1 and D-2 price views are reconstructed client-side from horizontal lookback columns in `fact_prices_lookback` via `normalizeRow()`. The `get_available_dates()` RPC identifies D (the current date with actual fact rows) and is used to build a `lookbackColumnMap` that routes lookback queries to the correct fact rows. All data from Supabase via `@supabase/supabase-js` v2. (per R-20260421-0422, R-20260422-0902, R-20260430-0825, R-20260430-1505)

### Non-Functional Requirements

- Idempotency: re-running when no new ZIPs exist produces no new output.
- Atomic writes: all file writes use `.partial` temp-file renamed on completion.
- Human-readable outputs: all schema files are UTF-8 CSV.
- Python 3.9+ compatibility for all scripts.
- Retry resilience: HTTP download failures retried up to `max_retries` times with exponential backoff.
- Supabase sync idempotency: re-running when latest local fact date already exists in Supabase exits cleanly; re-running retention pruning with unchanged local inputs leaves `fact_prices` row count unchanged.
- React app: no credentials hardcoded in source files; env vars use `VITE_` prefix; anon key only.
- React app: `npm run build` exits 0 and produces `dist/`; Netlify free-tier compatible.
- React app date selector: shows all 3 `dim_date` rows (D, D-1, D-2); D-1 and D-2 views are synthesized client-side from lookback price columns in `fact_prices_lookback`.
- React app Report 1 settlement dropdown: lists every settlement with at least one store with data on the selected date, regardless of total fact-row volume.
- React app Report 1 category chart: includes all categories with at least one price observation; no silent truncation.

### Known Priorities

Data correctness (no row rejection, no surrogate collision) and idempotency are primary concerns for the ETL layer. Visual fidelity to the legacy app, credential security, and complete result coverage are primary concerns for the React app.

---

## Architecture & Key Decisions

### High-Level Component Map

- **Download script (`src/extract.py`):** Scrapes the open-data index page, resolves new or force-scheduled ZIP URLs, and downloads them atomically to `data/raw/`. Reads settings and state from `config.ini`; writes `last_downloaded_date` on success.
- **Transform script (`src/transform.py`):** Reads all ZIPs from `data/raw/`, builds seven dimension tables from observed codes, and writes date-partitioned fact CSVs to `data/schema/facts/`. Calls `build_lookback_table` to produce `data/schema/fact_prices_lookback.csv`. Writes per-run log and quality report.
- **Config helper (`src/config_utils.py`):** Shared stdlib module providing `load_config()` and `save_state()`. Imported by both `extract.py` and `transform.py`.
- **Supabase sync module (`src/load_supabase.py`):** Loads `.env` via `python-dotenv`; reads `DATABASE_URL`; provisions all nine star-schema tables (CREATE TABLE IF NOT EXISTS + nullable migration DDL), two PostgreSQL RPC helper functions (`get_available_dates`, `get_settlements_for_date`), and two B-tree indexes on `fact_prices` (`idx_fact_prices_date_key`, `idx_fact_prices_date_store`) via idempotent `CREATE INDEX IF NOT EXISTS` DDL (R-20260429-0757); upserts all seven dimension CSVs via INSERT … ON CONFLICT DO UPDATE (execute_batch, page size 2000); inserts latest local fact day not yet in Supabase; truncates and reinserts `fact_prices_lookback` on every sync run.
- **Interactive menu (`menu.py`):** Reads `data/raw/`, `data/schema/facts/`, and `config.ini` to display ETL statistics. Numbered action menu (1–6, 0 exit). Invokes scripts via `subprocess` (list form, no `shell=True`). Option 5 invokes `src/deploy_netlify.py` without `capture_output` to allow stdin passthrough for interactive credential prompts. Option 6 runs `npm run build && npm run preview` from `react-app/` for a production-like local preview; the local URL (`http://localhost:4173`) is always printed and a browser open is attempted via `webbrowser.open()` (best-effort, never fails the workflow).
- **Netlify deploy script (`src/deploy_netlify.py`):** Detects Netlify CLI availability via `shutil.which`; if not found, prints manual deploy instructions and exits 0. If found, loads `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` from the project-root `.env` file (via `python-dotenv` `load_dotenv`) at module import time, with shell environment variables taking precedence. When a credential is not available in env or .env, prompts the operator interactively with step-by-step acquisition instructions and auto-saves the entered value to `.env` using `dotenv.set_key`. Builds the React app via `npm run build`, then runs `netlify deploy --prod --dir react-app/dist` with credentials injected in subprocess env (never as CLI args).
- **ETL runner scripts (`refresh.sh`, `refresh.bat`):** Thin OS-native wrappers invoking `src/extract.py` then `src/transform.py`. `refresh.sh` detects and uses `venv/bin/python` when present.
- **Menu launchers (`menu.sh`, `menu.bat`):** One-line OS-native wrappers invoking `menu.py`.
- **React Analytics App (`react-app/`):** Vite-built React 18 SPA. Queries Supabase directly via `@supabase/supabase-js` v2. Four pages: Home, Report 1, Report 2, Report 3. Deployed on Netlify from `react-app/dist/`. No serverless functions.
- **Legacy web app (`build-legacy/web/`):** Retained as reference; replaced by `react-app/` as the active visualisation layer.
- **Configuration file (`config.ini`):** Single INI at project root. `[settings]` user-tunable; `[state]` machine-written.
- **Star-schema outputs (`data/schema/`):** Seven flat dimension CSVs; 63+ date-partitioned fact CSVs in `data/schema/facts/`; derived lookback table.
- **Raw staging (`data/raw/`):** Write target for `src/extract.py`; not auto-pruned.
- **Nomenclature seed files (`data/nomenclatures/`):** EKATTE registry and product category list; consumed by `src/transform.py`.

### Key Integration Points

- **kolkostruva.bg/opendata (external, inbound):** HTTPS download via HTML scraping.
- **Supabase REST API (external, inbound to React app):** `@supabase/supabase-js` v2 queries `fact_prices_lookback`, `dim_*` tables via Supabase PostgREST, and invokes `get_available_dates` / `get_settlements_for_date` RPC functions. Auth: anon key; RLS must allow public SELECT and anon EXECUTE on RPC functions.
- **Supabase PostgreSQL (external, inbound to ETL sync):** Direct PostgreSQL connection via `psycopg2-binary`; `DATABASE_URL` from `.env`.
- **Netlify (external, hosting):** `react-app/netlify.toml` configures build command and publish directory.

### Key Architectural Decisions

1. **Date-partitioned fact table:** `data/schema/facts/YYYY-MM-DD.csv` (~54–78 MB each). A single flat file would be ~3.4–4.9 GB — incompatible with "human-readable" and "minimal space" constraints.

2. **Dimension from facts (no pre-load):** dimension tables populated from codes observed in the fact stream, enriched via static nomenclature files. Unknown codes receive `(unknown:<code>)` entries. Extended EKATTE lookup (R-20260501-0003) resolves non-canonical codes via three-step normalisation (exact → zero-padded to 5 digits → leading-zeros stripped) and consults seven nomenclature sources; genuinely unresolvable codes retain the `(unknown:<code>)` placeholder.

3. **`config.ini` for ETL control:** one INI file with `[settings]` and `[state]`. `configparser` is Python 3.9+ stdlib.

4. **No-rejection policy:** all rows with valid column count retained. Non-parseable `retail_price` stores NULL. Unknown dimension codes produce placeholder entries.

5. **Stdlib-only Python for transformation:** `src/transform.py` and `src/config_utils.py` use only Python stdlib.

6. **Dual-platform OS launchers (`.sh` + `.bat`):** thin cross-platform wrappers.

7. **React app architecture (client-only, Supabase direct):** Queries Supabase from the browser using the public anon key. No backend or serverless functions. Dimension tables loaded once at startup and cached in module scope. dim_product (~118K rows) never fully loaded; product names fetched via batched key lookups in report queries.

8. **5 000-row cap for Report 3:** fetchReport3 paginates up to 5 000 rows to prevent client memory exhaustion on high-volume categories.

9. **RPC functions for date filter and settlement filter (R-20260422-0902, R-20260430-0825):** `get_available_dates()` and `get_settlements_for_date(bigint)` are idempotent PostgreSQL functions provisioned by `load_supabase.py`. They allow the React app to obtain accurate filter sets without transferring large volumes of raw fact rows to the client. Both functions include `GRANT EXECUTE TO anon` so PostgREST can invoke them without elevated privileges. Both functions query `fact_prices_lookback` since R-20260430-0825.

---

## Technical Design

### Module Breakdown

- **`src/extract.py`:** Functions: `setup_logging`, `fetch_page`, `parse_zip_links`, `existing_filenames`, `download_file`, `main`. `BASE_DIR = Path(__file__).resolve().parent.parent`. Reads `config.ini`; writes `last_downloaded_date` on success.

- **`src/transform.py`:** Loads `config.ini`; reads `last_processed_date`; loads existing dimension CSVs; loads nomenclature dicts; initialises rotating log. Per ZIP: skips if fact exists and no force trigger; otherwise processes all CSVs, upserts all seven dimensions, writes buffered fact rows atomically. On completion: writes dimension CSVs atomically; writes quality report; calls `config_utils.save_state()`. Key nomenclature functions (R-20260501-0003): `load_settlement_names()` builds the EKATTE→name lookup from seven sources (`cities-ekatte-nomenclature.json`, `sof_rai.json`, `ek_atte.json`, `ek_kmet.json`, `ek_raion.json` (keyed on `raion` field), `ek_obl.json`, `ek_obst.json`); all file reads are absent-file-guarded. `resolve_settlement_name(code, lookup)` probes in three steps: exact → `code.zfill(5)` → `code.lstrip('0')`, returning `(unknown:<code>)` if all probes fail. `patch_unknown_settlements(dim_path, lookup)` reads `dim_settlement.csv`, applies `resolve_settlement_name()` to every `(unknown:...)` row, and atomically rewrites the file via `write_dim()` — preserving all surrogate keys — then returns the update count. `patch_unknown_settlements()` is called from `main()` after `build_schema()` on every run.

- **`src/config_utils.py`:** `load_config(config_path)`: reads/bootstraps INI. `save_state(config, config_path, **kwargs)`: atomic INI write via `.partial` rename.

- **`src/load_supabase.py`:** Loads `.env`; validates `DATABASE_URL`; `create_tables(conn)` executes four DDL blocks: `_CREATE_DDL` (CREATE TABLE IF NOT EXISTS), `_ENSURE_NULLABLE_DDL` (nullable migration), `_CREATE_RPC_FUNCTIONS` (provision `get_available_dates` and `get_settlements_for_date`), and `_CREATE_INDEXES` (`CREATE INDEX IF NOT EXISTS idx_fact_prices_date_key ON fact_prices(date_key)` and `CREATE INDEX IF NOT EXISTS idx_fact_prices_date_store ON fact_prices(date_key, store_key)` — added in R-20260429-0757 to eliminate full-table scan timeouts). Iterates `DIM_TABLES` to upsert dimensions in FK-dependency order; determines upload need via `get_latest_local_date` / `get_latest_remote_date`; calls `insert_fact_day` for newest unpresent partition (no early return). Enforces rolling 3-day remote retention (R-20260429-0825): `get_retained_local_dates(facts_dir, n=3)` returns the 3 newest local fact date strings; `get_date_keys_for_dates(conn, date_strings)` resolves their surrogate keys from `dim_date`; `prune_fact_prices(conn, retained_date_keys)` deletes `fact_prices` rows whose `date_key` is not in the retained set; `prune_dim_date(conn, retained_date_keys)` deletes `dim_date` rows outside the retained set (called after `prune_fact_prices` to honour FK constraint); all pruning functions skip the DELETE and return 0 when the retained key list is empty, and roll back on `psycopg2.DatabaseError`. Truncates and reinserts `fact_prices_lookback` on every sync run. All DB writes use `execute_batch` (page 2000). Transaction rollback on error. Both RPC functions GRANTed EXECUTE to anon role.

- **`menu.py`:** Displays ETL statistics; numbered menu 1–6, 0 exit; full refresh halts on first step failure; calls `subprocess.run([sys.executable, 'src/...'], check=True)` for ETL scripts; calls `subprocess.run([sys.executable, 'src/deploy_netlify.py'])` (no `capture_output`) for option 5 to allow interactive credential prompts. Option 6 (`action_local_preview`) validates `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set (via `python-dotenv` + `os.environ`) before invoking `npm run build`; prints an actionable error with an example and returns without building if either key is empty. After a successful build, starts `npm run preview` via `subprocess.Popen` (non-blocking), polls `localhost:4173` with `_wait_for_server()` until the server is ready, then opens the browser — eliminating the race condition where the browser opened before the server was listening (R-20260426-2150).

- **`src/deploy_netlify.py`:** Functions: `find_netlify_cmd`, `print_manual_instructions`, `get_credential`, `_save_credential_to_env`, `build_react_app`, `deploy_to_netlify`, `main`. Uses stdlib plus `python-dotenv` (`load_dotenv`, `set_key`). At module import, captures `_SHELL_ENV_KEYS` (shell-provided env vars) then calls `load_dotenv(BASE_DIR / ".env")` to load project-root `.env` into `os.environ` without overriding shell values. `get_credential()` checks env (shell or .env), logging the source; falls back to interactive prompt. `_save_credential_to_env()` uses `set_key` to persist interactively entered credentials to `.env`. `main()` checks whether each credential is pre-loaded and calls `_save_credential_to_env()` for any that were absent (entered interactively). Targets `react-app/dist/` for deploy. Falls back to manual instructions when Netlify CLI absent.

- **`react-app/src/lib/supabase.js`:** Supabase client singleton using `import.meta.env.VITE_SUPABASE_URL` and `import.meta.env.VITE_SUPABASE_ANON_KEY` (loaded by Vite from project-root `.env` file). No hardcoded credentials.

- **`react-app/src/lib/dataService.js`:** `fetchAllRows(table, columns)` — generic paginator (1000-row pages, `.range()`). `fetchDimensions()` — parallel load of dim_date, dim_settlement, dim_category, dim_store, dim_company plus `get_available_dates()` RPC; exposes ALL dim_date rows in `dates` (D, D-1, D-2); derives `currentDateKey` (D's key) from RPC result (null if RPC unavailable); builds `lookbackColumnMap` (Map<date_key, 'current'|'day1'|'day2'> by positional index in sorted dim_date); both added to the module-level `_dims` cache object (R-20260430-1505). `_resetDimsCache()` — exported test-only helper that clears `_dims` to enable test isolation. `normalizeRow(row, offset)` — exported helper; remaps `retail_price_day1/promo_price_day1` (or day2 variant) to canonical `retail_price/promo_price` fields before price calculation; identity for 'current' or falsy offset (R-20260430-1505). `fetchSettlementsForDate(dateKey, dims)` — resolves offset from `lookbackColumnMap`; for D-1/D-2, calls RPC with `dims.currentDateKey` instead of the lookback date_key; falls back to all settlements if RPC unavailable (R-20260430-1505). `fetchReport1(dateKey, settlementKey, dims)` — resolves offset/queryDateKey/priceColumns from `lookbackColumnMap`; selects correct price columns; applies `normalizeRow()` to all rows before aggregation; paginates with PAGE_SIZE=1000; client-side avg per category_key sorted ascending by avgPrice. `fetchReport2(dateKey, settlementKey, categoryKey, dims)` — same offset/queryDateKey/priceColumns/normalizeRow pattern; paginates ALL fact rows; batch-fetches dim_product, enriches with store/company, sorted by calculatedPrice. `fetchReport3(dateKey, categoryKey, dims)` — same pattern; max 5 000 rows; batch-fetches dim_product, enriches with settlement/store/company, sorted by calculatedPrice. Exported helpers: `formatDateBG(dateStr)`, `calculatePrice(row)`, `normalizeRow(row, offset)`.

- **`react-app/src/App.jsx`:** Root component. `useEffect` fetches dimensions on mount; manages `activePage`, `selectedDate`, `dimensions`, `loadError` state. Renders header (title, subtitle, date selector, 4-button nav), four page sections (each conditionally shown), footer. The date selector shows a disabled "Няма налични дати" placeholder option when `dimensions` is loaded but `dimensions.dates` is empty (no fact data in Supabase), preventing a silent empty-state.

- **`react-app/src/App.css`:** Full port of `build-legacy/web/style.css`; preserves all class names, hex colours (#667eea, #764ba2), gradients, keyframe animations, and responsive layout.

- **`react-app/src/components/HomePage.jsx`:** Stateless landing page with welcome heading, intro text (link to kolkostruva.bg), three feature cards, CTA section.

- **`react-app/src/components/Report1.jsx`:** City selector (populated via `fetchSettlementsForDate`); horizontal CSS bar chart from `fetchReport1`; bar widths proportional to avgPrice scaled to 60% of container; reloads settlements when date changes.

- **`react-app/src/components/Report2.jsx`:** City + category selectors; 7-column product table from `fetchReport2` (product name, calculated price, retail price, promo price, store, chain, date); both selectors reset when date changes.

- **`react-app/src/components/Report3.jsx`:** Category selector; 7-column location+product table from `fetchReport3` (city, product name, calculated price, retail price, promo price, store, chain); loading indicator shown for large categories.

### Key Algorithms and Processing Logic

**ZIP discovery:** `parse_zip_links` parses kolkostruva.bg/opendata HTML, extracts `.zip` hrefs via BeautifulSoup, resolves relative URLs with `urllib.parse.urljoin`, returns sorted descending deduplicated list. ZIPs verified with `zipfile.is_zipfile()` before atomic rename.

**Incremental download with force re-download:** compares ZIP filenames against `data/raw/`. Scheduled if absent OR date string >= `last_downloaded_date` override. Written via `.partial` → atomic rename.

**Delimiter auto-detection:** attempt comma-delimited parse; if first data row has one column containing `;`, re-read using `;` delimiter. Strip BOM from header rows in both passes.

**Dimension upsert:** load existing dimension CSV into `{natural_key: surrogate_key}` at startup. New code: assign `max_key + 1`; enrichment at insert time. Full dimension table written atomically at end of each run. Surrogate keys stable as long as dimension CSVs are not deleted.

**React effective price calculation:** `min(retail_price, promo_price)` where promo_price non-null and non-zero; otherwise `retail_price`. Implemented in `dataService.calculatePrice()`.

**React dimension caching:** `fetchDimensions()` result stored in module-level `_dims`; subsequent calls return cached object without re-fetching.

**React date selector via lookbackColumnMap (R-20260422-0902, R-20260428-0708, R-20260430-0825, R-20260430-1505):** `fetchDimensions()` calls `get_available_dates()` in parallel with dimension table fetches. All dim_date rows are exposed in `dims.dates` (D, D-1, D-2) without filtering. The RPC result is used only to derive `currentDateKey` (D's key): builds a Set of fact-present date_key integers using backward-compatible mapping (`(typeof r === 'object' && r !== null) ? r.get_available_dates : r` — handles PostgREST v10 wrapped-object and v11+ plain-integer formats), then extracts the single value as `currentDateKey`. `lookbackColumnMap` is built positionally from the sorted dim_date array (index 0 → 'current', index 1 → 'day1', index 2 → 'day2'). If RPC is unavailable, `currentDateKey = null` and the map is still built positionally from dim_date; lookback queries degrade gracefully.

**React settlement filter via RPC (R-20260422-0902, R-20260428-0708, R-20260430-0825, R-20260430-1505):** `fetchSettlementsForDate(dateKey, dims)` resolves the offset from `dims.lookbackColumnMap`; for D-1/D-2 offsets, calls `get_settlements_for_date(p_date_key)` with `dims.currentDateKey` (D's key) because fact rows are stored under D in `fact_prices_lookback`. For the 'current' offset, uses `dateKey` directly. The RPC result is mapped using the same backward-compatible guard: `(typeof r === 'object' && r !== null) ? r.get_settlements_for_date : r`. Settlement names resolved from `dims.settlements`. Fallback to all known settlements if RPC errors.

**React Report 1 full pagination with lookback normalization (R-20260422-0902, R-20260430-0825, R-20260430-1505):** `fetchReport1` resolves offset, queryDateKey, and priceColumns from `lookbackColumnMap` before querying. Paginates through all `fact_prices_lookback` rows for the resolved date and settlement using `.range(from, to)` with `PAGE_SIZE = 1000`. Applies `normalizeRow(r, offset)` to all rows after pagination to remap lookback price columns to canonical fields. Client-side avg-per-category aggregation performed on the complete normalized `allRows` array.

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
                                                   get_available_dates(), get_settlements_for_date())

Supabase -> react-app (Netlify) -> end users (browser)
```

### Data Storage

- **Raw staging (`data/raw/`):** ZIP archives; not auto-pruned.
- **Star-schema outputs (`data/schema/`):** Seven flat dimension CSVs; 63+ date-partitioned fact CSVs; derived lookback table.
- **Supabase (cloud):** Eight relational tables, two RPC helper functions, and two B-tree indexes (`idx_fact_prices_lookback_date_key`, `idx_fact_prices_lookback_date_store`) on `fact_prices_lookback`; queried by the React app via anon key. `fact_prices` was deleted in R-20260430-0825.
- **Nomenclatures (`data/nomenclatures/`):** Static lookup files; not modified by scripts.

### Data Access Patterns

React app: dimension tables loaded once at startup (small dims cached in module scope); date list filtered to fact-present dates via `get_available_dates()` RPC; settlement list per date resolved via `get_settlements_for_date()` RPC; fact queries for Report 1 paginated in full (PAGE_SIZE 1 000); fact queries for Report 3 capped at 5 000 rows per fetch. dim_product (~118K rows) never fully loaded client-side. Analysts may also access `data/schema/` CSVs directly with DuckDB or pandas.

### Data Retention

Local: Raw ZIPs and local fact CSVs under `data/raw/` and `data/schema/facts/` accumulate indefinitely (no automated pruning).

Remote (Supabase): `src/load_supabase.py` enforces a rolling 3-day retention window on every sync run. After the lookback sync, `dim_date` is pruned to the 3 newest local fact dates. The sync is idempotent: re-running with unchanged local inputs leaves the `fact_prices_lookback` row count unchanged. This ensures the React app date selector only shows dates with retained fact data.

---

## Security & Compliance

### Authentication and Authorization

ETL pipeline: local batch script; no network-exposed service; no user authentication. React app: unauthenticated public access; Supabase anon key (public-safe). Supabase RLS must allow public SELECT on all star-schema tables. Supabase anon role must have EXECUTE on `get_available_dates()` and `get_settlements_for_date(bigint)` (granted by `_CREATE_RPC_FUNCTIONS` DDL).

### Data Protection

- ETL download: HTTPS transport from kolkostruva.bg.
- Local storage: unencrypted; source data is publicly available government data — no PII processed.
- `config.ini`: no credentials; should be added to `.gitignore`.
- `.env` (project-root): contains all five environment keys: three server-side secrets (`DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`) and two client-safe keys (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`); excluded from VCS by `.gitignore`. `.env.example` committed (placeholder only, single consolidated template). No service role key in the React app.

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
- `config.ini` bootstrapped automatically on first run.

### Logging

- `src/transform.py` writes `logs/transform_YYYYMMDD_HHMMSS.log` (one per run) and `data/quality/report_YYYYMMDD_HHMMSS.csv`.
- React app: browser console only; no server-side logging. Console warnings logged when RPC functions are not yet provisioned in Supabase.

### Known Operational Risks

- External portal availability: `extract.py` retries up to `max_retries` times then exits non-zero.
- Raw data accumulation: not auto-pruned.
- Report 3 row cap: capped at 5 000 rows; high-volume categories may not show all data.
- Supabase anon read access required: if RLS blocks public SELECT, all React app queries return empty data.
- RPC functions not provisioned: if `load_supabase.py` has not been re-run after R-20260422-0902, the date dropdown shows all dim_date dates and the settlement dropdown shows all settlements (graceful fallback, no error shown to user).
- Supabase statement timeout (free tier ~3s): mitigated by B-tree indexes `idx_fact_prices_lookback_date_key` and `idx_fact_prices_lookback_date_store` on `fact_prices_lookback` (R-20260429-0757, retargeted in R-20260430-0825). If free-tier shared-compute contention is severe, a pre-computed `dim_available_dates` summary table is the documented escalation path.

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
- React app: Vitest + @testing-library/react test suite (`npm run test` in `react-app/`). `src/lib/dataService.test.js` covers `formatDateBG` (3 tests), `calculatePrice` (5 tests), `fetchReport2` pagination regression (1 test), `fetchDimensions` with wrapped-object RPC format (T2), raw-integer RPC format (T3), RPC error fallback (T4), and cache hit (T5) (4 tests), `fetchSettlementsForDate` raw-integer path (T6, 1 test), `normalizeRow` (4 tests: identity for 'current', identity for falsy, day1 remap, day2 remap), and `fetchDimensions lookbackColumnMap` construction (SC1: 3-row dim_date + 1-element RPC → correct map) — 19 tests total (R-20260430-1505). Component smoke tests for all four page components: `HomePage.test.jsx`, `Report1.test.jsx`, `Report2.test.jsx`, `Report3.test.jsx` (3 tests each). `src/App.test.jsx` covers credentials-error display, no-fetch-on-error, date-selector population, fetch-error display, empty-dates placeholder (T7), and 3-date selector (SC1) — 7 tests total (R-20260426-2150, R-20260428-0708, R-20260430-1505). All 38 React tests pass.

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
- A6 (ETL): `dim_settlement` built facts-driven (266 observed rows); settlement name resolved via `resolve_settlement_name()` (R-20260501-0003) using seven EKATTE nomenclature sources; genuinely unresolvable codes retain `(unknown:<code>)`. Risk if false: any new source-data code variant outside the three-step normalisation would remain unresolved; placeholder mechanism handles it gracefully.
- A7 (React app, R-20260422-0902, R-20260430-0825): The only authoritative source for which dates have fact data in Supabase is `fact_prices_lookback.date_key`. The `get_available_dates()` RPC reflects this. Risk if false: date dropdown may under-report available dates if fact data is spread across multiple tables.
- A8 (React app, R-20260422-0902): Supabase anon role has EXECUTE on `get_available_dates()` and `get_settlements_for_date(bigint)` as granted by `_CREATE_RPC_FUNCTIONS` DDL. The operator must re-run `python src/load_supabase.py` to provision these functions in Supabase after deployment. Until then, the app falls back gracefully (shows all dates / all settlements) with a console warning.
- A9 (R-20260429-0757, R-20260430-0825): B-tree indexes `idx_fact_prices_lookback_date_key` and `idx_fact_prices_lookback_date_store` on `fact_prices_lookback` are sufficient to bring `get_available_dates()` and `get_settlements_for_date()` within Supabase free-tier statement timeout. Risk if false: severe shared-compute contention may still cause timeouts; escalation path is a pre-computed `dim_available_dates` summary table.

### Validity Horizon

- Revisit A3 if kolkostruva.bg changes the ZIP naming convention or CSV column layout.
- Revisit A1/A2 if Supabase RLS policies change or credentials rotate.
- Revisit Report 3 5 000-row cap if high-volume categories require full result sets.
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
- `.aib_memory/requests/R-20260418-0120-check-pipeline-log-and-find-problems/` — Request folder.
- `.aib_memory/requests/R-20260418-2209-keep-raw-download-and-nomenclatures/` — Request folder.
- `.aib_memory/requests/R-20260419-0854-etl-scripts-menu-and-star-schema-data-layer/` — Request folder.
- `.aib_memory/requests/R-20260420-1730-sync-star-schema-to-supabase-database/` — Request folder.
- `.aib_memory/requests/R-20260420-2008-fix-db-update-failures/` — Request folder.
- `.aib_memory/requests/R-20260420-2055-add-day-1-and-day-2-prices-to-fact-prices/` — Request folder.
- `.aib_memory/requests/R-20260421-0348-change-menu-actions-and-numbering/` — Request folder.
- `.aib_memory/requests/R-20260421-0422-build-react-app-for-netlify-from-legacy-web-app/` — Request folder; contains `request.md` and `implementation.md`.
- `.aib_memory/requests/R-20260421-0505-add-netlify-deploy-option-to-menu/` — Request folder.
- `.aib_memory/requests/R-20260422-0902-fix-date-filter-and-category-prices-report/` — Request folder; contains `request.md` and `implementation.md`.
- `.aib_memory/requests/R-20260425-1304-secure-netlify-deploy-configuration/` — Request folder.
- `.aib_memory/requests/R-20260425-1445-unify-all-env-files-into-root-config/` — Request folder.
- `.aib_memory/requests/R-20260425-2155-update-readme-and-add-local-preview-menu-option/` — Request folder; contains `request.md` and `implementation.md`.
- `.aib_memory/requests/R-20260426-2150-fix-local-preview-race-condition/` — Request folder.
- `.aib_memory/requests/R-20260428-0708-fix-rpc-result-mapping-for-postgrest-v11/` — Request folder.
- `.aib_memory/requests/R-20260429-0757-add-indexes-and-favicon-to-remove-timeouts/` — Request folder.
- `.aib_memory/requests/R-20260429-0825-trim-supabase-facts-to-latest-3-days/` — Request folder; contains `request.md`, `analysis.md`, and `implementation.md`.
- `build-legacy/` — Legacy web application directory; retained as reference.
- `build-legacy/web/index.html` — Legacy HTML entry point (vanilla JS).
- `build-legacy/web/script.js` — Legacy report generation and chart rendering logic.
- `build-legacy/web/style.css` — Legacy CSS; ported to `react-app/src/App.css`.
- `config.ini` — Central pipeline configuration; `[settings]` and `[state]` sections.
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
- `logs/` — ETL and AIB framework log files.
- `menu.bat` — Windows menu launcher.
- `menu.py` — Interactive terminal menu; ETL statistics and action runner.
- `menu.sh` — Linux menu launcher.
- `react-app/` — React + Vite SPA for Netlify deployment.
- `react-app/index.html` — Vite HTML entry point.
- `react-app/netlify.toml` — Netlify build configuration (`command = "npm run build"`, `publish = "dist"`).
- `react-app/package.json` — npm package manifest; React 18, Vite 5, @supabase/supabase-js v2.
- `react-app/vite.config.js` — Vite configuration with React plugin; envDir set to load root `.env` for VITE_ variables.
- `react-app/src/App.css` — Global application styles; port of `build-legacy/web/style.css`.
- `react-app/src/App.jsx` — Root React component; global state, date selector, navigation.
- `react-app/src/index.css` — CSS reset and body base.
- `react-app/src/main.jsx` — React 18 `createRoot` entry point.
- `react-app/src/components/HomePage.jsx` — Landing page with feature cards and CTA.
- `react-app/src/components/Report1.jsx` — Report 1: avg price by category for selected city (bar chart).
- `react-app/src/components/Report2.jsx` — Report 2: products by city and category (7-column table).
- `react-app/src/components/Report3.jsx` — Report 3: locations and products by category (7-column table).
- `react-app/public/favicon.ico` — Minimal 1x1 transparent ICO file (66 bytes); eliminates browser 404 on favicon requests (R-20260429-0757); copied to `dist/` by Vite on build.
- `react-app/src/lib/dataService.js` — All Supabase data-fetching functions and client-side aggregation logic; includes RPC-based date and settlement filtering (R-20260422-0902).
- `react-app/src/lib/supabase.js` — Supabase client singleton.
- `react-app/dist/` — Production build output (generated by `npm run build`; not committed to VCS).
- `README.md` — Project readme.
- `refresh.bat` — Windows ETL runner (download + transform).
- `refresh.sh` — Linux ETL runner (download + transform); detects venv.
- `requirements.txt` — Python package dependencies for ETL scripts.
- `src/config_utils.py` — Shared configuration helpers (`load_config`, `save_state`).
- `src/extract.py` — Download script; scrapes open-data index and downloads new ZIPs.
- `src/load_supabase.py` — Supabase sync module; provisions all eight star-schema tables, two RPC helper functions (`get_available_dates`, `get_settlements_for_date` — both query `fact_prices_lookback`), and two B-tree indexes on `fact_prices_lookback`; upserts dimensions; truncates and reinserts `fact_prices_lookback` on every sync run; enforces rolling 3-day remote retention on `dim_date` (R-20260429-0825). `fact_prices` was deleted and all related ETL steps removed in R-20260430-0825.
- `src/transform.py` — ETL transformation engine; produces star-schema dimension and fact CSVs.
- `src/deploy_netlify.py` — Netlify deploy helper; builds React app and runs Netlify CLI deploy.
- `tests/test_config_utils.py` — Smoke tests for `src/config_utils.py` (8 tests).
- `tests/test_deploy_netlify.py` — Unit tests for `src/deploy_netlify.py` and menu.py integration (24 tests; covers CLI detection, credential loading, auto-save, and menu options 5–6).
- `tests/test_extract.py` — Unit tests for `src/extract.py` (9 tests; covers ZIP discovery, incremental-skip, and atomic rename logic).
- `tests/test_load_supabase.py` — Unit tests for `src/load_supabase.py` (32 tests; covers DDL provisioning including migration DDL and lookback indexes, `insert_lookback`, dimension upsert, retention pruning — R-20260430-0825).
- `tests/test_menu.py` — Unit tests for `menu.py` (23 tests; covers stats helpers, action dispatch, local-preview credential validation, and anon-key JWT role check; 1 skipped).
- `tests/test_transform.py` — Unit tests for `src/transform.py` (24 tests; covers delimiter detection, dim upsert, dim CSV load/write, quality-report write, extended EKATTE loading, three-step normalisation, and in-place dim patch — R-20260501-0003).
