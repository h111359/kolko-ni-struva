# Product Context

## Product

This workspace contains a two-layer product named Kolko Ni Struva ETL Pipeline + React Analytics App. It exists to ingest Bulgarian government retail-price open data, transform it into a local star schema, sync a rolling analytics subset to Supabase, and expose the resulting data through a public React single-page application.

- Primary actors are data engineers or operators running the local ETL commands and public end users browsing the landing-page analytics interface.
- The product boundary excludes a custom backend API layer, automated scheduling, CI-managed deployment, and bulk historical cloud retention beyond the rolling Supabase window.
- The product's key outcome is a repeatable local-to-cloud analytics flow that turns daily source ZIP archives into structured retail-price browsing and analysis.

**Domain Knowledge**: The product operates in the public retail-price transparency domain for Bulgaria, collecting, normalizing, and presenting government-published daily price data. Raw ZIP archives are scraped from the state open-data portal, transformed into a dimensional warehouse, and queried through a browser-facing analytics app.

**Glossary**:
- **Anon key**: The browser-safe Supabase publishable key consumed by the React app through `VITE_SUPABASE_PUBLISHABLE_KEY`.
- **EKATTE**: The Bulgarian territorial code system used as the canonical settlement identifier during transform and in nomenclature files.
- **Fact lookback table**: The `fact_prices_lookback` dataset that stores current-day and day-minus-one/day-minus-two price columns for analytics queries.
- **Landing page**: The unified React page that bootstraps with date options plus the active visible dataset, then lazily loads the remaining selector options on demand while providing cross-filtered browsing, grouping, and flat-table pagination.
- **Star schema**: The dimensional warehouse shape produced under `data/schema/` with seven dimensions plus a fact layer.

## Concepts

- **Client-only analytics frontend**: The public web UI is a static React app that talks directly to Supabase rather than through a custom backend service.
- **Idempotent pipeline state**: ETL scripts are designed to re-read and atomically update config state so sequential runs do not corrupt shared state keys.
- **Pushdown analytics**: Filtering, grouping, and row-shaping are pushed into PostgreSQL RPC functions so the browser avoids iterating over raw warehouse slices locally.
- **Rolling remote retention**: The cloud-hosted analytic subset is intentionally bounded to recent dates and referenced categories instead of mirroring the entire local history.
- **Unified landing-page UX**: The current React app centers on one stateful landing page rather than multiple report pages.

**Constraints & Assumptions**: Technical constraints include Python 3.9 or newer for the ETL layer, Node.js 18 or newer for the React layer, direct browser access to Supabase with a publishable key, no custom backend API, a rolling three-date analytics window in Supabase, and a browser-side prohibition on secret keys. Organizational constraints include local credential management through `.env` and `config.ini`, exclusion of live secrets from version control, and manual or operator-triggered deployment flows.

## Requirements

- `FR-001`: The system must discover daily retail-price ZIP archives from the Bulgarian government open-data page and download only files that are new or forced by state thresholds.
- `FR-002`: The system must transform the downloaded source archives into seven dimension tables, date-partitioned fact outputs, and quality-report artifacts under `data/schema/` and `data/quality/`.
- `FR-003`: The system must maintain `config.ini` bootstrap defaults and atomically persist pipeline state keys without overwriting sibling keys written by adjacent ETL steps.
- `FR-004`: The system must provision and sync a Supabase-hosted analytics schema that includes dimension tables, the `fact_prices_lookback` table, a derived `landing_page_row_projection` table, helper indexes, and RPC functions for frontend filters and landing-page queries.
- `FR-005`: The system must provide an interactive terminal menu for full refresh, download-only, transform-only, Supabase sync, Netlify deploy, and local React preview actions.
- `FR-006`: The React app must render a unified landing page that bootstraps with date options plus the active visible result set, lazily loads selector datasets when the user focuses a control, and supports first, previous, next, and direct page-number navigation without total-page calculation.
- `FR-007`: The React app must reject missing or non-publishable Supabase browser credentials and surface a descriptive user-facing error instead of silently creating a dangerous client.
- `FR-008`: The deployment tooling must build the React app and support either Netlify CLI deployment or a manual dashboard fallback.
- `NFR-001`: The ETL state-write path must be atomic and cross-platform safe.
- `NFR-002`: The analytics query path must reduce browser-side processing by using PostgreSQL RPC pushdown, a date-first visible-row bootstrap, and selector RPCs that only run for the control the user is actively interacting with.
- `NFR-003`: The repository must keep credentials and generated data out of version control while preserving safe templates and static reference data.
- `NFR-004`: The product must remain operable with local command-line tooling and local tests instead of requiring a managed CI pipeline.

## Solution

**Architecture**: The current architecture is a local ETL pipeline plus a static React frontend backed by Supabase. The high-level component map is a Python ETL layer in `src/`, a local file-based warehouse in `data/`, an operator console in the repository root, a Supabase analytics database provisioned by `src/load_supabase.py`, and a React/Vite frontend in `react-app/` that reads from Supabase directly.

**Key Design Decisions**:
- Keep the frontend client-only and authenticated only by a publishable Supabase key, trading backend simplicity for strict dependence on Row Level Security and carefully shaped RPC functions.
- Store the authoritative warehouse locally and push only the current analytics subset to Supabase, trading simpler public querying for bounded cloud storage and explicit sync logic.

**Technology Stack**: Python plus requests, BeautifulSoup, psycopg2, and python-dotenv for ETL and deployment automation, with React, Vite, Vitest, and Supabase JS for the frontend.

**Technical Design**:
- `src/config_utils.py` bootstraps `config.ini` and persists state keys through atomic replacement, enabling adjacent scripts to share settings safely.
- `src/extract.py` scrapes the open-data page, parses ZIP links, skips already-downloaded files, downloads with retry logic, and verifies archive integrity before promoting a temporary file.
- `src/transform.py` loads nomenclatures, normalizes settlement codes, builds dimensions and fact slices, writes quality reports, and emits transform logs.
- `src/load_supabase.py` provisions DDL, indexes, and RPC functions; uploads local star-schema outputs; prunes remote dimensions; and refreshes the derived `landing_page_row_projection` table.
- `menu.py` is the top-level operator entry point that exposes stats and dispatches subprocess-driven actions, including local frontend preview and Netlify deployment.
- `react-app/src/App.jsx` mounts the single `LandingPage` feature after credential validation.
- `react-app/src/components/LandingPage.jsx` owns the date-first bootstrap, lazy selector loading, filter state, grouping state, pagination state, and guarded asynchronous refresh behavior.
- `react-app/src/lib/dataService.js` encapsulates the active Supabase RPC access for the landing page.

**Data Architecture**: Core entities are the seven dimensions `dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, and `dim_file`, plus the `fact_prices_lookback` fact model and the derived `landing_page_row_projection` query table. Data lineage flows from downloaded raw ZIP archives in `data/raw/` to transformed CSV outputs in `data/schema/` and `data/quality/`, then into Supabase tables and RPC query surfaces consumed by the React app.

**Security**: Authentication and authorization are delegated to Supabase for browser reads and to direct PostgreSQL credentials for ETL writes. Data protection controls include keeping `.env` and `config.ini` out of version control, separating browser-safe variables from server-only variables, and rejecting secret-key formats in browser code. A current security risk is the client-only architecture's dependence on correct Supabase publishable-key usage and backend policy configuration.

**Operations**: The effective runbook is the combination of README.md and `menu.py`, which document or expose full refresh, partial ETL steps, Supabase sync, Netlify deploy, and local React preview actions. Observability is file-based and console-oriented, using transform log files in `logs/`, quality report CSVs in `data/quality/`, and session query logging in the frontend. Deployment is operator-triggered: the React app is built locally, then deployed through Netlify CLI when available or through a manual dashboard fallback.

**Development Practices**: Developer setup requires Python dependencies from `requirements.txt`, Node dependencies from `react-app/package.json`, a copied `config.ini.example`, and a populated `.env` file for cloud and deploy actions. Testing strategy is local and mixed-language: Python `unittest`-style test modules cover ETL and menu helpers, while Vitest and Testing Library cover the React app. No CI/CD pipeline configuration is present in the workspace.

## File Structure

**Core Files**:
- `menu.py` — Interactive operator console for pipeline stats, ETL actions, Supabase sync, deploy, and preview workflows
- `menu.bat`, `menu.sh` — Launcher scripts for the interactive ETL menu
- `refresh.bat`, `refresh.sh` — Wrapper scripts for the full ETL refresh flow
- `config.ini`, `config.ini.example` — Local settings and ETL state file
- `.env`, `.env.example` — Environment file for runtime credentials and deployment values
- `README.md` — Primary operator and developer guide
- `requirements.txt` — Python dependency manifest

**Source Code**:
- `src/config_utils.py` — Config bootstrap and atomic state-write helpers
- `src/extract.py` — Downloader that scrapes the open-data portal
- `src/transform.py` — Transformer that converts raw archives into the local star schema
- `src/load_supabase.py` — Supabase sync module
- `src/deploy_netlify.py` — Netlify deployment helper

**Data Directories**:
- `data/raw/` — Downloaded archive files (100 files)
- `data/schema/` — Local star-schema output directory for dimensions and facts
- `data/schema/facts/` — Date-partitioned fact CSV files (100 files)
- `data/nomenclatures/` — Static reference-data folder for EKATTE and product-category lookups
- `data/quality/` — Quality-report CSV files (29 files)
- `logs/` — Operational log files (41 files)
- `lab/` — Folder for exploratory or ad hoc data snapshots

**React Application**:
- `react-app/` — React and Vite single-page analytics application
- `react-app/src/App.jsx` — Root React component
- `react-app/src/components/LandingPage.jsx` — Unified landing-page component
- `react-app/src/lib/supabase.js` — Shared Supabase client bootstrap
- `react-app/src/lib/dataService.js` — Supabase data layer for dimensions and landing-page rows
- `react-app/src/lib/queryLog.js` — In-memory browser-session query log store
- `react-app/package.json` — React app manifest
- `react-app/vite.config.js` — Vite build and test configuration

**Tests**:
- `tests/` — Python test directory for ETL helpers, sync behavior, deployment helpers, and menu actions
- `react-app/src/` — Frontend test modules alongside component files
