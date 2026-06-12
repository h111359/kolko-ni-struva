# Product Context

> **Auto-generated** by `aib-refresh-context.md` on 2026-05-26 20:50 EEST.
> Framework definition assets (`.aib_brain/`) are excluded by design — see `.aib_brain/` for AIB framework internals.
> This document is a synthesis of product documentation and workspace sources. It is fully replaced on each execution.

## Product Identity

This workspace contains a two-layer product named Kolko Ni Struva ETL Pipeline + React Analytics App, with no explicit product version exposed in the repository and an active operational status per README.md, menu.py, and react-app/package.json. It exists to ingest Bulgarian government retail-price open data, transform it into a local star schema, sync a rolling analytics subset to Supabase, and expose the resulting data through a public React single-page application.

- Primary actors are data engineers or operators running the local ETL commands and public end users browsing the landing-page analytics interface, per README.md, menu.py, and react-app/src/App.jsx.

- The product boundary excludes a custom backend API layer, automated scheduling, CI-managed deployment, and bulk historical cloud retention beyond the rolling Supabase window, per README.md and src/load_supabase.py.

- The product’s key outcome is a repeatable local-to-cloud analytics flow that turns daily source ZIP archives into structured retail-price browsing and analysis, per README.md, src/transform.py, and src/load_supabase.py.

## Domain Knowledge

The product operates in the public retail-price transparency domain for Bulgaria, specifically around collecting, normalizing, and presenting government-published daily price data. The repository evidence shows a workflow in which raw ZIP archives are scraped from the state open-data portal, transformed into a dimensional warehouse, and queried through a browser-facing analytics app, per README.md, src/extract.py, src/transform.py, and react-app/src/components/LandingPage.jsx.

- Key business processes are daily archive discovery and download, star-schema transformation, quality reporting, Supabase synchronization, and public-facing browser analytics, per README.md, src/extract.py, src/transform.py, src/load_supabase.py, and menu.py.

- The owning and operating roles are an internal engineering or analyst workflow for ETL maintenance and a public anonymous-consumer workflow for the React app, per README.md, menu.py, and react-app/src/lib/supabase.js.

- Critical external dependencies are the Bulgarian government open-data portal, Supabase-hosted PostgreSQL and PostgREST, Netlify hosting, and local Python and Node.js runtimes, per README.md, .env.example, requirements.txt, and react-app/package.json.

### Glossary

**Anon key**: The browser-safe Supabase publishable key consumed by the React app through `VITE_SUPABASE_PUBLISHABLE_KEY`, per .env.example and react-app/src/lib/supabase.js.

**EKATTE**: The Bulgarian territorial code system used as the canonical settlement identifier during transform and in nomenclature files, per data/nomenclatures/ and src/transform.py.

**Fact lookback table**: The `fact_prices_lookback` dataset that stores current-day and day-minus-one/day-minus-two price columns for analytics queries, per README.md and src/load_supabase.py.

**Landing page**: The unified React page that bootstraps with date options plus the active visible dataset, then lazily loads the remaining selector options on demand while providing cross-filtered browsing, grouping, and flat-table pagination with first, previous, next, and direct page-number navigation over the Supabase-backed dataset, per react-app/src/App.jsx and react-app/src/components/LandingPage.jsx.

**Netlify deploy**: The repository workflow that builds the React app and publishes it through the Netlify CLI or dashboard flow, per README.md, menu.py, and src/deploy_netlify.py.

**Star schema**: The dimensional warehouse shape produced under `data/schema/` with seven dimensions plus a fact layer, per README.md and src/transform.py.

## Concepts

The repository expresses a small set of stable product concepts that guide both the ETL and frontend layers. These concepts are synthesized from README.md, src/transform.py, src/load_supabase.py, react-app/src/App.jsx, and react-app/src/components/LandingPage.jsx.

- **Client-only analytics frontend**: The public web UI is a static React app that talks directly to Supabase rather than through a custom backend service, per react-app/package.json and react-app/src/lib/supabase.js.

- **Idempotent pipeline state**: ETL scripts are designed to re-read and atomically update config state so sequential runs do not corrupt shared state keys, per src/config_utils.py and tests/test_config_utils.py.

- **Pushdown analytics**: Filtering, grouping, and row-shaping are pushed into PostgreSQL RPC functions so the browser avoids iterating over raw warehouse slices locally, per src/load_supabase.py and react-app/src/lib/dataService.js.

- **Rolling remote retention**: The cloud-hosted analytic subset is intentionally bounded to recent dates and referenced categories instead of mirroring the entire local history, per src/load_supabase.py and tests/test_load_supabase.py.

- **Unified landing-page UX**: The current React app centers on one stateful landing page rather than multiple report pages, per react-app/src/App.jsx, react-app/src/components/LandingPage.jsx, and README.md.

## Constraints & Assumptions

The current workspace shows several hard technical and operational constraints plus a few explicit assumptions that shape the design. These are evidenced by README.md, config.ini.example, .env.example, src/config_utils.py, src/load_supabase.py, react-app/package.json, and react-app/src/lib/supabase.js.

- Technical constraints include Python 3.9 or newer for the ETL layer, Node.js 18 or newer for the React layer, direct browser access to Supabase with a publishable key, and direct PostgreSQL connectivity for the sync script, per README.md, requirements.txt, react-app/package.json, and .env.example.

- Technical constraints also include no custom backend API, a rolling three-date analytics window in Supabase, and a browser-side prohibition on secret keys, per README.md, src/load_supabase.py, and react-app/src/lib/supabase.js.

- Organizational constraints include local credential management through `.env` and `config.ini`, exclusion of live secrets from version control, and manual or operator-triggered deployment flows rather than unattended release automation, per .gitignore, .env.example, config.ini.example, README.md, and src/deploy_netlify.py.

- An explicit current-state assumption is that Supabase credentials and Netlify credentials are provided by the operator at runtime or through local environment files, with high confidence because both Python and React bootstraps hard-fail or warn on missing values, per .env.example, menu.py, src/deploy_netlify.py, and react-app/src/lib/supabase.js.

- The current validity horizon for these assumptions is the next change to deployment topology, cloud data retention policy, or credential-loading strategy, because those surfaces are implemented directly in the checked-in scripts rather than in an external platform config, per src/load_supabase.py, src/deploy_netlify.py, and react-app/src/lib/supabase.js.

## Requirements

This section synthesizes the active functional and non-functional requirements currently evidenced in README.md, config.ini.example, .env.example, menu.py, src/*.py, react-app/src/*.jsx, and the test suite. The repository does not contain a standalone formal requirements register, so these IDs are synthesized from current workspace behavior with medium confidence.

- `FR-001`: The system must discover daily retail-price ZIP archives from the Bulgarian government open-data page and download only files that are new or forced by state thresholds, per README.md, src/extract.py, and tests/test_extract.py.

- `FR-002`: The system must transform the downloaded source archives into seven dimension tables, date-partitioned fact outputs, and quality-report artifacts under `data/schema/` and `data/quality/`, per README.md, src/transform.py, and tests/test_transform.py.

- `FR-003`: The system must maintain `config.ini` bootstrap defaults and atomically persist pipeline state keys without overwriting sibling keys written by adjacent ETL steps, per src/config_utils.py and tests/test_config_utils.py.

- `FR-004`: The system must provision and sync a Supabase-hosted analytics schema that includes dimension tables, the `fact_prices_lookback` table, a derived `landing_page_row_projection` table, helper indexes, and RPC functions for frontend filters and landing-page queries, per README.md, src/load_supabase.py, and tests/test_load_supabase.py.

- `FR-005`: The system must provide an interactive terminal menu for full refresh, download-only, transform-only, Supabase sync, Netlify deploy, and local React preview actions, per menu.py and tests/test_menu.py.

- `FR-006`: The React app must render a unified landing page that bootstraps with date options plus the active visible result set, lazily loads selector datasets when the user focuses a control, and supports first, previous, next, and direct page-number navigation without total-page calculation, per react-app/src/App.jsx, react-app/src/components/LandingPage.jsx, and react-app/src/components/LandingPage.test.jsx.

- `FR-007`: The React app must reject missing or non-publishable Supabase browser credentials and surface a descriptive user-facing error instead of silently creating a dangerous client, per .env.example and react-app/src/lib/supabase.js.

- `FR-008`: The deployment tooling must build the React app and support either Netlify CLI deployment or a manual dashboard fallback, per README.md, src/deploy_netlify.py, and tests/test_deploy_netlify.py.

- `NFR-001`: The ETL state-write path must be atomic and cross-platform safe, per src/config_utils.py and tests/test_config_utils.py.

- `NFR-002`: The analytics query path must reduce browser-side processing by using PostgreSQL RPC pushdown, a date-first visible-row bootstrap, and selector RPCs that only run for the control the user is actively interacting with, per src/load_supabase.py and react-app/src/lib/dataService.js.

- `NFR-003`: The repository must keep credentials and generated data out of version control while preserving safe templates and static reference data, per .gitignore, .env.example, and config.ini.example.

- `NFR-004`: The product must remain operable with local command-line tooling and local tests instead of requiring a managed CI pipeline, per README.md, menu.py, and react-app/package.json.

## Architecture & Decisions

The current architecture is a local ETL pipeline plus a static React frontend backed by Supabase. This synthesis is based on README.md, menu.py, src/load_supabase.py, src/deploy_netlify.py, react-app/package.json, and react-app/src/App.jsx.

- The high-level component map is a Python ETL layer in `src/`, a local file-based warehouse in `data/`, an operator console in the repository root, a Supabase analytics database provisioned by `src/load_supabase.py`, and a React/Vite frontend in `react-app/` that reads from Supabase directly.

- Key integration points are HTTP scraping against the government portal through `requests` and BeautifulSoup, PostgreSQL access through psycopg2, browser-to-Supabase access through `@supabase/supabase-js`, and deployment to Netlify through CLI commands or manual upload, per requirements.txt, src/extract.py, src/load_supabase.py, react-app/package.json, and src/deploy_netlify.py.

- A current architectural decision is to keep the frontend client-only and authenticated only by a publishable Supabase key, trading backend simplicity for strict dependence on Row Level Security and carefully shaped RPC functions, per README.md and react-app/src/lib/supabase.js.

- Another active decision is to store the authoritative warehouse locally and push only the current analytics subset to Supabase, trading simpler public querying for bounded cloud storage and explicit sync logic, per README.md and src/load_supabase.py.

- The technology stack is Python plus requests, BeautifulSoup, psycopg2, and python-dotenv for ETL and deployment automation, with React, Vite, Vitest, and Supabase JS for the frontend, per requirements.txt and react-app/package.json.

## Technical Design

The codebase is organized into a small set of modules with clear responsibilities across ETL, deployment, and frontend analytics. This section synthesizes README.md, menu.py, src/config_utils.py, src/extract.py, src/transform.py, src/load_supabase.py, src/deploy_netlify.py, react-app/src/App.jsx, react-app/src/components/LandingPage.jsx, react-app/src/lib/dataService.js, and react-app/src/lib/supabase.js.

- `src/config_utils.py` bootstraps `config.ini` and persists state keys through atomic replacement, enabling adjacent scripts to share settings safely.

- `src/extract.py` scrapes the open-data page, parses ZIP links, skips already-downloaded files, downloads with retry logic, and verifies archive integrity before promoting a temporary file.

- `src/transform.py` loads nomenclatures, normalizes settlement codes, builds dimensions and fact slices, writes quality reports, and emits transform logs.

- `src/load_supabase.py` provisions DDL, indexes, and RPC functions; uploads local star-schema outputs; prunes remote dimensions; and refreshes the derived `landing_page_row_projection` table so both the row RPC and the selector-option RPCs can read from the same indexed projection without a separate count function.

- `menu.py` is the top-level operator entry point that exposes stats and dispatches subprocess-driven actions, including local frontend preview and Netlify deployment.

- `react-app/src/App.jsx` mounts the single `LandingPage` feature after credential validation, while `react-app/src/components/LandingPage.jsx` owns the date-first bootstrap, lazy selector loading, filter state, grouping state, pagination state, and guarded asynchronous refresh behavior.

- `react-app/src/lib/dataService.js` encapsulates the active Supabase RPC access for the landing page, including query logging, flat-row queries, grouped queries, and per-selector option-list fetches.

- The principal communication patterns are batch CLI execution between root scripts and Python modules, filesystem handoff between ETL stages and `data/`, PostgreSQL RPC calls for analytics pushdown, and browser-side React state orchestration over async Supabase requests.

## Data Architecture

The workspace implements a star-schema data flow from downloaded ZIP archives to local CSV outputs and then to a trimmed Supabase warehouse. This section is based on README.md, config.ini.example, src/transform.py, src/load_supabase.py, data/schema/, data/nomenclatures/, and the related tests.

- Data sources are the government ZIP archive feed, static nomenclature files under `data/nomenclatures/`, local ETL state in `config.ini`, and runtime environment variables in `.env`, per README.md, config.ini.example, .env.example, src/extract.py, and src/transform.py.

- Core entities are the seven dimensions `dim_date`, `dim_company`, `dim_settlement`, `dim_category`, `dim_product`, `dim_store`, and `dim_file`, plus the `fact_prices_lookback` fact model and the derived `landing_page_row_projection` query table used by the React app, per data/schema/ and src/load_supabase.py.

- Data lineage flows from downloaded raw ZIP archives in `data/raw/` to transformed CSV outputs in `data/schema/` and `data/quality/`, then into Supabase tables and RPC query surfaces consumed by the React app, per README.md, src/transform.py, src/load_supabase.py, and react-app/src/lib/dataService.js.

- Storage locations are local filesystem directories for raw, schema, quality, nomenclature, lab, and logs artifacts, plus Supabase PostgreSQL for the public analytics subset, per README.md, src/load_supabase.py, and the directory layout.

- Access patterns are local script reads and writes during ETL, operator inspection of quality and log outputs, and anonymous browser reads through publishable-key Supabase queries and RPC functions, per menu.py, src/load_supabase.py, react-app/src/lib/supabase.js, and react-app/src/lib/dataService.js.

## Security & Compliance

The workspace shows a pragmatic security model built around local secret files, Git exclusion rules, and a strict distinction between browser-safe and server-only credentials. This synthesis uses .gitignore, .env.example, src/deploy_netlify.py, menu.py, and react-app/src/lib/supabase.js.

- Authentication and authorization are delegated to Supabase for browser reads and to direct PostgreSQL credentials for ETL writes, with the frontend limited to a publishable key and the Python sync layer using server-only credentials, per .env.example and react-app/src/lib/supabase.js.

- Data protection controls include keeping `.env` and `config.ini` out of version control, separating browser-safe variables from server-only variables, and rejecting secret-key formats in browser code, per .gitignore, .env.example, and react-app/src/lib/supabase.js.

- Secrets management is file-based and operator-managed in the current repository, with `.env.example` providing the schema and `src/deploy_netlify.py` optionally persisting prompted values into a local `.env` file for reuse, per .env.example and src/deploy_netlify.py.

- No explicit regulatory framework is documented in the workspace. The safest evidence-backed statement is that the product should be treated as public-data analytics with credential hygiene requirements, per README.md and .env.example.

- A current security risk is the client-only architecture’s dependence on correct Supabase publishable-key usage and backend policy configuration, because no custom middleware layer exists to sanitize or proxy browser traffic, per README.md and react-app/src/lib/supabase.js.

## Operations

The repository contains enough operational evidence to describe day-to-day usage, monitoring surfaces, and deployment behavior, even though it does not contain a formal runbook directory. This section is based on README.md, menu.py, src/deploy_netlify.py, src/transform.py, logs/, and data/quality/.

- The effective runbook is the combination of README.md and `menu.py`, which document or expose full refresh, partial ETL steps, Supabase sync, Netlify deploy, and local React preview actions.

- Observability is file-based and console-oriented, using transform log files in `logs/`, quality report CSVs in `data/quality/`, and session query logging in the frontend, per src/transform.py and react-app/src/lib/queryLog.js.

- No explicit SLO, SLA, or on-call rotation is documented in the workspace. Operations therefore appear to be manually supervised by the owning development or data-maintenance role, per README.md and menu.py.

- Deployment is operator-triggered: the React app is built locally, then deployed through Netlify CLI when available or through a manual dashboard fallback when it is not, per README.md and src/deploy_netlify.py.

- Known operational risks include missing local credentials, missing Node or npm binaries, backend query-performance regressions in the landing-page analytics path, and temporary inability to deploy SQL changes whenever the Supabase PostgreSQL session is forced into `transaction_read_only = on`, per .env.example, src/deploy_netlify.py, menu.py, and src/load_supabase.py.

## Development Practices

Development in this repository is centered on local commands, file-based outputs, and targeted unit tests rather than on a formal CI pipeline. This synthesis uses README.md, requirements.txt, react-app/package.json, .gitignore, and the `tests/` plus frontend test files.

- The repository structure separates ETL and deployment logic in `src/`, operator commands at the root, analytics UI code in `react-app/`, transformed and reference data under `data/`, logs under `logs/`, and Python tests under `tests/`, per README.md and the workspace layout.

- Developer setup requires Python dependencies from `requirements.txt`, Node dependencies from `react-app/package.json`, a copied `config.ini.example`, and a populated `.env` file for cloud and deploy actions, per README.md, requirements.txt, config.ini.example, and .env.example.

- Testing strategy is local and mixed-language: Python `unittest`-style test modules cover ETL and menu helpers, while Vitest and Testing Library cover the React app. The documented frontend test command is `npm test`, and the repository also supports direct Python-module validation through local test files, per react-app/package.json and the `tests/` tree.

- No CI/CD pipeline configuration is present in the non-excluded workspace. The evidence points to manual validation and operator-run deploy flows rather than automated merge gates, per the repository root and README.md.

- Known developer-experience pain points include reliance on local credentials, large generated-data directories, and missing test tooling in some environments, because the repository depends on local Python, Node, and cloud access rather than a fully provisioned automated runner, per README.md, .env.example, and the current workspace contents.

## Workspace File Inventory

This inventory lists the non-excluded directories and files currently present in the workspace, sorted by path. Descriptions are synthesized from the current workspace structure and the evidence summarized above.

- `.env` — Local environment file for private runtime credentials and deployment values.

- `.env.example` — Commit-safe template documenting required server-side and browser-side environment variables.

- `.gitignore` — Repository ignore rules for secrets, generated data, build outputs, and local runtime artifacts.

- `README.md` — Primary operator and developer guide for ETL setup, star-schema outputs, and React deployment.

- `config.ini` — Local settings and ETL state file consumed by the Python scripts.

- `config.ini.example` — Template for the default ETL settings and empty pipeline state keys.

- `data/` — Root directory for reference inputs, generated warehouse outputs, raw archives, and quality artifacts.

- `data/nomenclatures/` — Static reference-data folder for EKATTE and product-category lookups used during transform.

- `data/nomenclatures/Ekatte.zip` — Archived EKATTE reference bundle stored alongside the extracted JSON files.

- `data/nomenclatures/Ekatte/` — Contains 12 EKATTE reference files following the pattern `ek_*.json` plus related lookup artifacts; individual items are not listed.

- `data/nomenclatures/EkatteXLS.zip` — Archived EKATTE XLS reference bundle stored alongside the extracted workbook files.

- `data/nomenclatures/EkatteXLS/` — Contains 13 spreadsheet reference files following the pattern `*.xls` and related workbook outputs; individual items are not listed.

- `data/nomenclatures/cities-ekatte-nomenclature.json` — Primary settlement-code to settlement-name lookup used during transform.

- `data/nomenclatures/product-categories.json` — Category-code reference mapping consumed during transform and sync.

- `data/nomenclatures/unknown_categories_explanation.md` — Notes describing unresolved or unknown source category cases.

- `data/quality/` — Contains 29 quality-report CSV files following the pattern `report_YYYY-MM-DD_HHMMSS.csv`; individual items are not listed.

- `data/raw/` — Contains 100 downloaded archive files following the pattern `YYYY-MM-DD.zip`; individual items are not listed.

- `data/schema/` — Local star-schema output directory for dimensions, fact aggregates, and fact partitions.

- `data/schema/dim_category.csv` — Current local category dimension export.

- `data/schema/dim_company.csv` — Current local company dimension export.

- `data/schema/dim_date.csv` — Current local date dimension export.

- `data/schema/dim_file.csv` — Current local source-file dimension export.

- `data/schema/dim_product.csv` — Current local product dimension export.

- `data/schema/dim_settlement.csv` — Current local settlement dimension export.

- `data/schema/dim_store.csv` — Current local store dimension export.

- `data/schema/fact_prices_lookback.csv` — Consolidated lookback fact export used as the basis for Supabase analytics sync.

- `data/schema/facts/` — Contains 100 date-partitioned fact CSV files following the pattern `YYYY-MM-DD.csv`; individual items are not listed.

- `lab/` — Folder for exploratory or ad hoc data snapshots outside the core ETL outputs.

- `lab/2026-05-13/` — Contains 210 per-company CSV snapshot files following the pattern `<brand>_<uic>.csv`; individual items are not listed.

- `lab/2026-05-13.zip` — Archived version of the dated lab snapshot folder.

- `logs/` — Contains 41 operational log files following the patterns `transform_*.log`, `aib-action-*.log`, and `pipeline.log`; individual items are not listed.

- `menu.bat` — Windows launcher for the interactive ETL menu.

- `menu.py` — Interactive operator console for pipeline stats, ETL actions, Supabase sync, deploy, and preview workflows.

- `menu.sh` — POSIX shell launcher for the interactive ETL menu.

- `package-lock.json` — Root npm lockfile currently tracked in the workspace.

- `patch_grouped.py` — Standalone Python helper script present at the repository root for grouped patching work.

- `react-app/` — React and Vite single-page analytics application deployed separately from the ETL scripts.

- `react-app/dist/` — Built frontend output directory for preview and deployment artifacts.

- `react-app/index.html` — HTML entry point for the Vite-built React application.

- `react-app/netlify.toml` — Netlify configuration for the React app deployment target.

- `react-app/package-lock.json` — Lockfile for the React app’s npm dependencies.

- `react-app/package.json` — React app manifest defining Vite, Vitest, React, and Supabase JS dependencies and scripts.

- `react-app/public/` — Public static asset directory copied into the built frontend output.

- `react-app/public/favicon.ico` — Frontend favicon asset.

- `react-app/src/` — Source directory for the React app components, styles, and data-access modules.

- `react-app/src/App.css` — Root application stylesheet for the analytics SPA.

- `react-app/src/App.jsx` — Root React component that validates browser credentials and mounts the landing page.

- `react-app/src/App.test.jsx` — Frontend test module for the root application behavior.

- `react-app/src/components/` — Feature-component directory for the landing-page UI.

- `react-app/src/components/LandingPage.jsx` — Unified landing-page component handling filters, grouping, and direct page-number pagination without total-page calculation.

- `react-app/src/components/LandingPage.test.jsx` — Frontend test module covering landing-page filters, grouping, and direct page-number pagination behavior.

- `react-app/src/index.css` — Global CSS for the React application shell.

- `react-app/src/lib/` — Frontend data-access and client-integration helper directory.

- `react-app/src/lib/dataService.js` — Supabase data layer for dimensions, landing-page rows, grouped queries, optional counts, and query logging.

- `react-app/src/lib/dataService.test.js` — Frontend test module for data-service helpers and RPC contracts.

- `react-app/src/lib/queryLog.js` — In-memory browser-session query log store for frontend request visibility.

- `react-app/src/lib/supabase.js` — Shared Supabase client bootstrap and credential-validation guard for browser access.

- `react-app/src/main.jsx` — React application bootstrap entry point used by Vite.

- `react-app/src/test-setup.js` — Shared frontend test setup for the Vitest environment.

- `react-app/test_output.txt` — Saved frontend test output artifact present in the app workspace.

- `react-app/vite.config.js` — Vite build and test configuration for the React app.

- `refresh.bat` — Windows wrapper for the full ETL refresh flow.

- `refresh.sh` — POSIX shell wrapper for the full ETL refresh flow.

- `requirements.txt` — Python dependency manifest for scraping, HTML parsing, PostgreSQL sync, and dotenv loading.

- `src/` — Python module directory for ETL, sync, and deployment logic.

- `src/config_utils.py` — Config bootstrap and atomic state-write helpers shared by the ETL scripts.

- `src/deploy_netlify.py` — Netlify deployment helper that builds the React app and manages credential loading.

- `src/extract.py` — Downloader that scrapes the open-data portal and saves new ZIP archives into `data/raw/`.

- `src/load_supabase.py` — Supabase sync module that provisions schema objects, uploads current warehouse data, and defines analytics RPC functions.

- `src/transform.py` — Transformer that converts raw archives into the local star schema and quality-report outputs.

- `tests/` — Python test directory for ETL helpers, sync behavior, deployment helpers, and menu actions.

- `tests/test_config_utils.py` — Unit tests for config bootstrap, atomic writes, and sibling-state preservation.

- `tests/test_deploy_netlify.py` — Unit tests for Netlify CLI fallback, credential handling, and menu integration.

- `tests/test_extract.py` — Unit tests for ZIP link parsing, download scheduling, and atomic rename behavior in the extractor.

- `tests/test_load_supabase.py` — Unit tests for Supabase DDL, RPC, retention, and batch-insert helper behavior.

- `tests/test_menu.py` — Unit tests for menu dispatch, local preview, and credential-validation behavior.

- `tests/test_transform.py` — Unit tests for delimiter detection, dimension upserts, quality reporting, and settlement lookup behavior.

--- I am done with the context update ---
