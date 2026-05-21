# Колко ни струва — ETL Pipeline

Automated ETL pipeline that scrapes the Bulgarian government open-data portal
[kolkostruva.bg/opendata](https://kolkostruva.bg/opendata), downloads daily
retail-price ZIP archives, and transforms them into a star-schema structured
dataset under `data/schema/` for offline analytical use.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Repository Structure](#repository-structure)
4. [Quick Start](#quick-start)
5. [Scripts](#scripts)
6. [config.ini Reference](#configini-reference)
7. [Star Schema](#star-schema)
8. [SCD Strategy](#scd-strategy)
9. [Quality Report](#quality-report)
10. [Querying the Data](#querying-the-data)
11. [Netlify Deploy & React App Setup](#netlify-deploy--react-app-setup)
12. [Local Preview](#local-preview)
13. [Recovery](#recovery)

---

## Prerequisites

- Python **≥ 3.9**
- `pip`
- Internet access to `kolkostruva.bg`
- Node.js **≥ 18** and `npm` (required for React app local preview and Netlify deploy)

---

## Installation

```bash
# 1. Clone the repository (or unzip the project folder)
cd kolko-ni-struva-2

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Repository Structure

```
kolko-ni-struva-2/
├── .env.example            # Template for required environment variables (commit-safe)
├── config.ini              # User-tunable settings + script-managed state
├── menu.py                 # Interactive terminal menu
├── menu.sh                 # Linux launcher for menu.py
├── menu.bat                # Windows launcher for menu.py
├── refresh.sh              # Linux ETL runner (download + transform)
├── refresh.bat             # Windows ETL runner (download + transform)
├── requirements.txt
├── README.md
├── src/
│   ├── config_utils.py     # Config bootstrap and atomic state-write helpers
│   ├── extract.py          # Download script (scrapes portal, downloads ZIPs)
│   ├── transform.py        # Transformation script (builds star schema)
│   ├── load_supabase.py    # Supabase sync (provisions tables, upserts star-schema)
│   └── deploy_netlify.py   # Netlify deploy (builds React app and deploys to Netlify)
├── react-app/              # React + Vite analytics SPA (deployed to Netlify)
│   ├── src/                # React components and data-service modules
│   ├── index.html
│   ├── package.json
│   └── netlify.toml
├── data/
│   ├── raw/                # Downloaded ZIP archives (YYYY-MM-DD.zip)
│   ├── schema/
│   │   ├── dim_date.csv
│   │   ├── dim_company.csv
│   │   ├── dim_settlement.csv
│   │   ├── dim_category.csv
│   │   ├── dim_product.csv
│   │   ├── dim_store.csv
│   │   ├── dim_file.csv
│   │   └── facts/          # Date-partitioned fact CSVs (YYYY-MM-DD.csv)
│   ├── quality/            # Per-run quality reports
│   └── nomenclatures/      # EKATTE and category lookup files
├── logs/                   # Transform run logs
└── tests/
    ├── test_config_utils.py
    └── test_deploy_netlify.py
```

---

## Quick Start

### Run the full ETL pipeline (Linux)

```bash
./refresh.sh
```

### Run the full ETL pipeline (Windows)

```bat
refresh.bat
```

### Launch the interactive menu (Linux)

```bash
./menu.sh
# or: python3 menu.py
```

### Run scripts individually

```bash
python3 src/extract.py    # Download new ZIPs only
python3 src/transform.py  # Transform ZIPs to schema only
```

### Preview the React app locally before Netlify deploy

1. Install React app dependencies (once):

   ```bash
   cd react-app && npm install && cd ..
   ```

2. Launch the interactive menu and choose option **6**, or run manually:

   ```bash
   # Via menu:
   python3 menu.py
   # Select: 6) Preview React app locally

   # Or directly:
   cd react-app && npm run build && npm run preview
   ```

   The local URL (`http://localhost:4173`) is printed to the terminal. Once the
   preview server is ready, the browser opens automatically. In headless
   environments, copy the URL into your browser manually.
   Press **Ctrl+C** to stop the preview server.

### Inspect session query activity in the React app

After the app loads, open the **🧪 Лог на заявки** page from the main navigation
to inspect the Supabase requests triggered during the current browser session.
The page is intended for debugging suspicious visualized data and shows the
frontend-visible request intent: table or RPC target, selected columns when
available, filters or parameters, timing, row count, and success/error status.
It does **not** guarantee the exact backend SQL text executed inside Supabase.
For repository-owned backend SQL, `src/load_supabase.py` now also writes a
persistent audit trail to the `backend_sql_audit_log` table in PostgreSQL,
including the rendered SQL text, execution timestamp, logical origin label,
and statement count for each emitted statement or batch page. Browser-originated
Supabase traffic from the React app remains outside that persistent backend log.
Reports 1, 2, and 3 now read database-aggregated or database-enriched result
sets via RPC instead of paginating raw `fact_prices_lookback` rows into the
browser. When those report contracts change locally, rerun
`python3 src/load_supabase.py` before validating the React app against Supabase.

---

## Scripts

### `src/extract.py` — Downloader

Scrapes `kolkostruva.bg/opendata`, identifies any ZIP archives not yet present
in `data/raw/`, and downloads them. Each downloaded ZIP is verified with a ZIP
magic-number check; a failed integrity check triggers a re-download.

Re-running when no new ZIPs are available exits cleanly:
```
No new files to download.
```

On completion, writes `last_downloaded_date` to `config.ini [state]`.

### `src/transform.py` — Transformer

Reads all ZIPs in `data/raw/`, parses the CSV files inside each archive, builds
seven dimension tables and date-partitioned fact CSVs under `data/schema/`.
Produces a quality report under `data/quality/` and a log file under `logs/`.
Settlement EKATTE identifiers are canonicalized during transform so padded and
canonical variants such as `068134` and `68134` collapse to the same analytical
settlement identity before `dim_settlement.csv` and dependent dimensions are
written.

On completion, writes `last_processed_date` to `config.ini [state]`.

### `refresh.sh` / `refresh.bat` — ETL Runner

Runs the complete pipeline: `src/extract.py` followed by `src/transform.py`.
Stops on the first non-zero exit code.

### `menu.py` / `menu.sh` / `menu.bat` — Interactive Menu

Displays pipeline statistics at startup (ZIP count, date range, schema
freshness, config state) and a numbered action menu:

```
1) Full refresh        (download + transform + update Supabase)
2) Download only       (python src/extract.py)
3) Transform only      (python src/transform.py)
4) Update Supabase DB  (python src/load_supabase.py)
5) Deploy React app to Netlify
6) Preview React app locally
0) Exit
```

Each action streams output to the terminal. On failure, captured stderr is
printed with a `STDERR:` prefix. The full-refresh action (1) halts on the
first step failure and does not proceed to subsequent steps.

### `src/load_supabase.py` — Supabase Sync

Provisions the eight Supabase star-schema tables, the seven PostgreSQL RPC helper
functions used by the React app, and the persistent `backend_sql_audit_log`
table (all idempotent via `CREATE TABLE IF NOT EXISTS` / `CREATE OR REPLACE`).
Upserts all seven dimension CSVs, fully refreshes `fact_prices_lookback`, and
records the exact rendered SQL text emitted by the repository-owned backend
path together with execution timestamp, logical origin, and statement count.
After the lookback sync, it enforces two rolling retention windows: **3 days**
for retained analytical fact context (`dim_date` + `fact_prices_lookback`
dependencies) and **30 days** for `backend_sql_audit_log`. The browser Query
Log page remains a separate frontend-session diagnostic surface and does not
populate this backend audit table. Reads `DATABASE_URL` from the project-root
`.env` file. The React app now depends on these RPCs after reprovisioning:
`get_available_dates`, `get_settlements_for_date`, `get_categories_for_settlement`,
`get_settlements_for_category`, `get_report_1_category_prices`,
`get_report_2_rows`, and `get_report_3_rows`.

### `src/deploy_netlify.py` — Netlify Deploy

Detects the Netlify CLI (`netlify`); if absent, prints manual deploy
instructions and exits cleanly. When the CLI is available, loads
`NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID` from the project-root `.env` file
or shell environment (with interactive fallback and auto-save to `.env`).
Builds the React app via `npm run build`, then deploys `react-app/dist/` to
Netlify production.

---

## config.ini Reference

`config.ini` at the project root has two sections:

### `[settings]` — User-tunable

| Key           | Default                              | Description                               |
| ------------- | ------------------------------------ | ----------------------------------------- |
| opendata_url  | https://kolkostruva.bg/opendata      | Source URL to scrape for ZIP links        |
| max_retries   | 3                                    | Maximum download/fetch retry attempts     |
| retry_delay   | 10                                   | Base retry delay in seconds (× attempt)   |
| log_level     | INFO                                 | Python logging level (DEBUG/INFO/WARNING) |

### `[state]` — Script-managed

| Key                   | Written by         | Description                                         |
| --------------------- | ------------------ | --------------------------------------------------- |
| last_downloaded_date  | `src/extract.py`   | ISO date of the newest successfully downloaded ZIP  |
| last_processed_date   | `src/transform.py` | ISO date of the newest successfully processed ZIP   |

### Force re-run mechanism

- **Force re-download**: Set `last_downloaded_date` under `[state]` to a past
  date (e.g. `2026-04-10`). On the next run, `src/extract.py` will re-download
  all ZIPs with date ≥ that value.

- **Force re-process**: Set `last_processed_date` under `[state]` to a past
  date (e.g. `2026-04-10`). On the next run, `src/transform.py` will delete
  and re-create all fact files with date ≥ that value.

- **After settlement-normalization logic changes**: Force re-process the local
  schema outputs and then re-sync Supabase so `dim_settlement`, `dim_store`,
  `fact_prices_lookback`, and the React app all use the same canonical
  settlement identity.

  ```bash
  python3 src/transform.py
  python3 src/load_supabase.py
  ```

Both scripts write their respective state key **after** all operations succeed,
and always re-read `config.ini` from disk before writing to avoid overwriting
the sibling key set by the other script in the same pipeline run.

Scripts bootstrap a default `config.ini` with default `[settings]` and empty
`[state]` keys on first run when the file is absent.

---

## Star Schema

All output CSVs are encoded **UTF-8 without BOM**. Integer surrogate keys are
used throughout; no string values are repeated in the fact table beyond
`retail_price` and `promo_price`.

### Dimension tables (`data/schema/`)

| File               | Columns                                            | Description |
| ------------------ | -------------------------------------------------- | ----------- |
| dim_date.csv       | date_key, date, year, month, day, weekday          | One row per distinct ZIP date. weekday: Mon=0, Sun=6 |
| dim_company.csv    | company_key, uic, company_name                     | One row per UIC (company ID), name from ZIP filename |
| dim_settlement.csv | settlement_key, ekatte, settlement_name            | Facts-driven (~256 rows); unknown codes get `(unknown:<code>)` |
| dim_category.csv   | category_key, category_code, category_name         | Facts-driven; built from product-categories.json |
| dim_product.csv    | product_key, product_code, product_name            | Natural key is (product_code, product_name) |
| dim_store.csv      | store_key, store_name, settlement_key, company_key | Snowflake bridge: joins to dim_settlement and dim_company |
| dim_file.csv       | file_key, file_name, zip_date                      | One row per CSV file inside each ZIP (~13,100 rows) |

### Fact table (`data/schema/facts/YYYY-MM-DD.csv`)

Date-partitioned — one CSV per source ZIP. No `fact_key` column.

| Column       | Description                                       |
| ------------ | ------------------------------------------------- |
| date_key     | FK → dim_date.date_key                            |
| store_key    | FK → dim_store.store_key                          |
| file_key     | FK → dim_file.file_key (data lineage)             |
| category_key | FK → dim_category.category_key                    |
| product_key  | FK → dim_product.product_key                      |
| retail_price | Decimal string; empty string = not reported (NULL)|
| promo_price  | Decimal string; empty string = no promotion (NULL)|

Reaching `dim_settlement` and `dim_company` from the fact table requires a join
through `dim_store` (partial snowflake design).

---

## SCD Strategy

**All dimensions use SCD Type 1 (overwrite).** When a dimension attribute
value changes (e.g. a company name update in a new file), the existing row is
updated in-place. No historical tracking is performed. If historical attribute
tracking is required, a migration to SCD Type 2 (add new row with effective
dates) would be needed.

---

## Quality Report

After each transform run a quality report CSV is written to `data/quality/`:

```
data/quality/report_YYYY-MM-DD_HHMMSS.csv
```

Columns: `zip_date, total_rows, null_prices, unknown_settlements,
unknown_categories, delimiter_anomalies`

- **null_prices**: rows where `retail_price` could not be parsed (kept in fact table as empty string).
- **unknown_settlements**: rows where the EKATTE code was not found in the nomenclature files.
- **unknown_categories**: rows where the category code was not found in product-categories.json.
- **delimiter_anomalies**: CSV files inside the ZIP that used semicolon instead of comma as delimiter (auto-handled, counted for visibility).

A transform log is also written to `logs/transform_YYYY-MM-DD_HHMMSS.log`.

---

## Querying the Data

The fact and dimension CSVs are plain UTF-8 files queryable with any tool that
reads CSV. For large-scale queries across all 63+ dates, DuckDB is recommended:

```python
import duckdb
conn = duckdb.connect()
result = conn.execute("""
    SELECT dp.product_name, AVG(CAST(f.retail_price AS DOUBLE)) AS avg_price
    FROM read_csv_auto('data/schema/facts/*.csv') f
    JOIN read_csv_auto('data/schema/dim_product.csv') dp
      ON f.product_key = dp.product_key
    WHERE f.retail_price != ''
    GROUP BY dp.product_name
    ORDER BY avg_price DESC
    LIMIT 20
""").fetchdf()
print(result)
```

pandas also works for single-date analysis:

```python
import pandas as pd
facts = pd.read_csv('data/schema/facts/2026-04-18.csv')
dim_product = pd.read_csv('data/schema/dim_product.csv')
merged = facts.merge(dim_product, on='product_key')
print(merged[['product_name', 'retail_price']].head(20))
```

---

## Netlify Deploy & React App Setup

The React Analytics App is deployed to Netlify via `src/deploy_netlify.py` (invoked
from menu option 5 or directly). Both Python ETL scripts and the React frontend
read configuration from a single `.env` file at the project root.

### One-time credential setup

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in all required credentials:

   **Server-side (Python scripts):**
   ```
   DATABASE_URL=postgresql://postgres:[password]@...
   NETLIFY_AUTH_TOKEN=<your personal access token>
   NETLIFY_SITE_ID=<your site UUID>
   ```

   **Client-side (React frontend — prefixed with VITE_):**
   ```
   VITE_SUPABASE_URL=https://your-project.supabase.co
   VITE_SUPABASE_ANON_KEY=<your Supabase anon key>
   ```

   - **DATABASE_URL**: Supabase Dashboard → Settings → Database → Connection string (URI).
   - **NETLIFY_AUTH_TOKEN**: app.netlify.com → Avatar → User settings →
     Applications → Personal access tokens → New access token.
   - **NETLIFY_SITE_ID**: app.netlify.com → your site →
     Site configuration → General → Site details → Site ID.
   - **VITE_SUPABASE_URL**: Supabase Dashboard → Settings → API → Project URL.
   - **VITE_SUPABASE_ANON_KEY**: Supabase Dashboard → Settings → API → anon (public key).

3. Ensure the Netlify CLI is installed globally:

   ```bash
   npm install -g netlify-cli
   ```

### How environment variables are loaded

All environment variables are read from the single `.env` file at project root:

- **Python scripts** (`src/load_supabase.py`, `src/deploy_netlify.py`) load variables via `python-dotenv`.
- **React frontend** loads `VITE_*` variables via Vite build system (only `VITE_*` prefixed variables are exposed to the browser).

### Credential loading precedence

`src/deploy_netlify.py` loads Netlify credentials in this order:

| Priority | Source | How to use |
|---|---|---|
| 1 (highest) | Shell environment variable | `export NETLIFY_AUTH_TOKEN=...` in your shell profile |
| 2 | `.env` file at project root | Copy `.env.example` → `.env` and fill in values |
| 3 (fallback) | Interactive prompt | Prompted when credential is absent; **auto-saved** to `.env` |

When credentials are entered via the interactive prompt, they are automatically
saved to `.env` so future deploys do not require re-entry.

### Security notes

- `.env` is excluded from version control by `.gitignore`. Never commit `.env`.
- Server-side credentials (`DATABASE_URL`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`) are sensitive secrets and must be treated carefully.
- Client-side credentials (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`) use Supabase's public anon key, which is safe to expose in the browser.
- Credentials are passed to subprocesses via environment variables,
  not as command-line arguments, so they are not visible in process listings.
- `.env.example` (committed) contains only placeholder values — it is safe to
  share.

---

## Local Preview

Before deploying to Netlify, test the React app with a production-like local
build rather than the dev server. The local preview uses `vite preview` which
serves the compiled `dist/` output — the same artifact that Netlify receives.

### Prerequisites

Node.js ≥ 18 and npm must be installed. Install React app dependencies once:

```bash
cd react-app && npm install && cd ..
```

### Running local preview

**Using the menu (recommended):**

```bash
python3 menu.py
# Select: 6) Preview React app locally
```

**Running manually:**

```bash
cd react-app
npm run build && npm run preview
```

The preview server starts at `http://localhost:4173`. The URL is always printed
to the terminal. Once the server is ready, the browser opens automatically.
In headless or restricted environments, copy the URL into your browser manually.

Press **Ctrl+C** to stop the preview server.

### Dev server vs. local preview

| Mode | Command | Hot-reload | Matches production build |
|---|---|---|---|
| Dev server | `npm run dev` | Yes | No |
| Local preview | `npm run build && npm run preview` | No | **Yes** |

Use local preview (`npm run preview`) before Netlify deployment to catch
build-time issues that do not appear in dev mode (e.g., missing `VITE_*`
environment variables, import errors, or asset path mismatches).

---

## Recovery

A full backup of the workspace before the R-20260418-2209 clean-up was archived to:

```
../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz
```

To restore the previous state:

```bash
cd /home/hromar/Desktop/projects
tar -xzf kolko-ni-struva-2-backup-R-20260418-2209.tar.gz
```
