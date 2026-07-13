# Product Context

## Product

- Kolko Ni Struva ETL Pipeline plus React Analytics App ingests Bulgarian government retail-price open data, transforms it into a local star schema, syncs a rolling analytics subset to Supabase, and exposes the resulting data through a public React single-page application
- Primary actors are data engineers or operators running local ETL commands and public end users browsing the landing-page analytics interface
- Product boundary excludes custom backend API layer, automated scheduling, CI-managed deployment, and bulk historical cloud retention beyond the rolling Supabase window
- Key outcome is repeatable local-to-cloud analytics flow turning daily source ZIP archives into structured retail-price browsing and analysis
- Product operates in public retail-price transparency domain for Bulgaria, collecting, normalizing, and presenting government-published daily price data
- Raw ZIP archives are scraped from state open-data portal, transformed into dimensional warehouse, and queried through browser-facing analytics app
- Key business processes are daily archive discovery and download, star-schema transformation, quality reporting, Supabase synchronization, and public-facing browser analytics
- Operating roles are internal engineering or analyst workflow for ETL maintenance and public anonymous-consumer workflow for React app
- Critical external dependencies are Bulgarian government open-data portal, Supabase-hosted PostgreSQL and PostgREST, Netlify hosting, and local Python and Node.js runtimes

## Concepts

- Anon key is the browser-safe Supabase publishable key consumed by React app through VITE_SUPABASE_PUBLISHABLE_KEY
- EKATTE is the Bulgarian territorial code system used as canonical settlement identifier during transform and in nomenclature files
- Fact lookback table is the fact_prices_lookback dataset storing current-day and day-minus-one/day-minus-two price columns for analytics queries
- Landing page is unified React page bootstrapping with date options plus active visible dataset, lazy-loading remaining selector options on demand while providing cross-filtered browsing, grouping, and flat-table pagination with first, previous, next, and direct page-number navigation over Supabase-backed dataset
- Star schema is dimensional warehouse shape produced under data/schema/ with seven dimensions plus fact layer
- Client-only analytics frontend: public web UI is static React app talking directly to Supabase rather than through custom backend service
- Idempotent pipeline state: ETL scripts designed to re-read and atomically update config state so sequential runs do not corrupt shared state keys
- Pushdown analytics: filtering, grouping, and row-shaping pushed into PostgreSQL RPC functions so browser avoids iterating over raw warehouse slices locally
- Rolling remote retention: cloud-hosted analytic subset intentionally bounded to recent dates and referenced categories instead of mirroring entire local history
- Unified landing-page UX: current React app centers on one stateful landing page rather than multiple report pages

## Requirements

- MUST: System discover daily retail-price ZIP archives from Bulgarian government open-data page and download only files that are new or forced by state thresholds
- MUST: System transform downloaded source archives into seven dimension tables, date-partitioned fact outputs, and quality-report artifacts under data/schema/ and data/quality/
- MUST: System maintain config.ini bootstrap defaults and atomically persist pipeline state keys without overwriting sibling keys written by adjacent ETL steps
- MUST: System provision and sync Supabase-hosted analytics schema including dimension tables, fact_prices_lookback table, derived landing_page_row_projection table, helper indexes, and RPC functions for frontend filters and landing-page queries
- MUST: System provide interactive terminal menu for full refresh, download-only, transform-only, Supabase sync, Netlify deploy, and local React preview actions
- MUST: React app render unified landing page bootstrapping with date options plus active visible result set, lazy-loading selector datasets when user focuses control, supporting first, previous, next, and direct page-number navigation without total-page calculation
- MUST: React app reject missing or non-publishable Supabase browser credentials and surface descriptive user-facing error instead of silently creating dangerous client
- MUST: Deployment tooling build React app and support either Netlify CLI deployment or manual dashboard fallback
- MUST: ETL state-write path be atomic and cross-platform safe
- MUST: Analytics query path reduce browser-side processing by using PostgreSQL RPC pushdown, date-first visible-row bootstrap, and selector RPCs running only for control user actively interacts with
- MUST: Repository keep credentials and generated data out of version control while preserving safe templates and static reference data
- MUST: Product remain operable with local command-line tooling and local tests instead of requiring managed CI pipeline
- MUST: Python 3.9 or newer for ETL layer
- MUST: Node.js 18 or newer for React layer
- MUST: Direct browser access to Supabase with publishable key
- MUST: Direct PostgreSQL connectivity for sync script
- MUST NOT: System include custom backend API
- MUST NOT: System mirror entire local history to cloud; rolling three-date analytics window in Supabase only
- MUST NOT: Browser code use secret keys
- MUST: Local credential management through .env and config.ini
- MUST: Live secrets excluded from version control
- MUST: Deployment flows be manual or operator-triggered rather than unattended release automation
- MUST: Supabase credentials and Netlify credentials provided by operator at runtime or through local environment files

## Solution

- High-level component map is Python ETL layer in src/, local file-based warehouse in data/, operator console in repository root, Supabase analytics database provisioned by src/load_supabase.py, and React/Vite frontend in react-app/ reading from Supabase directly
- Key integration points are HTTP scraping against government portal through requests and BeautifulSoup, PostgreSQL access through psycopg2, browser-to-Supabase access through @supabase/supabase-js, and deployment to Netlify through CLI commands or manual upload
- Frontend kept client-only and authenticated only by publishable Supabase key, trading backend simplicity for strict dependence on Row Level Security and carefully shaped RPC functions
- Authoritative warehouse stored locally and only current analytics subset pushed to Supabase, trading simpler public querying for bounded cloud storage and explicit sync logic
- Technology stack is Python plus requests, BeautifulSoup, psycopg2, and python-dotenv for ETL and deployment automation, with React, Vite, Vitest, and Supabase JS for frontend
- src/config_utils.py bootstraps config.ini and persists state keys through atomic replacement, enabling adjacent scripts to share settings safely
- src/extract.py scrapes open-data page, parses ZIP links, skips already-downloaded files, downloads with retry logic, and verifies archive integrity before promoting temporary file
- src/transform.py loads nomenclatures, normalizes settlement codes, builds dimensions and fact slices, writes quality reports, and emits transform logs
- src/load_supabase.py provisions DDL, indexes, and RPC functions; uploads local star-schema outputs; prunes remote dimensions; refreshes derived landing_page_row_projection table so both row RPC and selector-option RPCs read from same indexed projection without separate count function
- menu.py is top-level operator entry point exposing stats and dispatching subprocess-driven actions, including local frontend preview and Netlify deployment
- react-app/src/App.jsx mounts single LandingPage feature after credential validation
- react-app/src/components/LandingPage.jsx owns date-first bootstrap, lazy selector loading, filter state, grouping state, pagination state, and guarded asynchronous refresh behavior
- react-app/src/lib/dataService.js encapsulates active Supabase RPC access for landing page, including query logging, flat-row queries, grouped queries, and per-selector option-list fetches
- Principal communication patterns are batch CLI execution between root scripts and Python modules, filesystem handoff between ETL stages and data/, PostgreSQL RPC calls for analytics pushdown, and browser-side React state orchestration over async Supabase requests
- Data sources are government ZIP archive feed, static nomenclature files under data/nomenclatures/, local ETL state in config.ini, and runtime env vars in .env
- Core entities are seven dimensions dim_date, dim_company, dim_settlement, dim_category, dim_product, dim_store, and dim_file, plus fact_prices_lookback fact model and derived landing_page_row_projection query table used by React app
- Data lineage flows from downloaded raw ZIP archives in data/raw/ to transformed CSV outputs in data/schema/ and data/quality/, then into Supabase tables and RPC query surfaces consumed by React app
- Storage locations are local filesystem directories for raw, schema, quality, nomenclature, lab, and logs artifacts, plus Supabase PostgreSQL for public analytics subset
- Access patterns are local script reads and writes during ETL, operator inspection of quality and log outputs, and anonymous browser reads through publishable-key Supabase queries and RPC functions
- Auth and authz delegated to Supabase for browser reads and to direct PostgreSQL credentials for ETL writes, with frontend limited to publishable key and Python sync layer using server-only credentials
- Data protection controls include keeping .env and config.ini out of version control, separating browser-safe vars from server-only vars, and rejecting secret-key formats in browser code
- Secrets management is file-based and operator-managed, with .env.example providing schema and src/deploy_netlify.py optionally persisting prompted values into local .env file for reuse
- Product should be treated as public-data analytics with credential hygiene requirements
- Security risk: client-only architecture depends on correct Supabase publishable-key usage and backend policy config, because no custom middleware layer exists to sanitize or proxy browser traffic
- Effective runbook is combination of README.md and menu.py, documenting or exposing full refresh, partial ETL steps, Supabase sync, Netlify deploy, and local React preview actions
- Observability is file-based and console-oriented, using transform log files in logs/, quality report CSVs in data/quality/, and session query logging in frontend
- Operations manually supervised by owning development or data-maintenance role
- Deployment is operator-triggered: React app built locally, then deployed through Netlify CLI when available or through manual dashboard fallback when not
- Known operational risks include missing local credentials, missing Node or npm binaries, backend query-performance regressions in landing-page analytics path, and temporary inability to deploy SQL changes when Supabase PostgreSQL session forced into transaction_read_only mode
- Repository structure separates ETL and deployment logic in src/, operator commands at root, analytics UI code in react-app/, transformed and reference data under data/, logs under logs/, and Python tests under tests/
- Developer setup requires Python dependencies from requirements.txt, Node dependencies from react-app/package.json, copied config.ini.example, and populated .env file for cloud and deploy actions
- Testing strategy is local and mixed-language: Python unittest-style test modules cover ETL and menu helpers, while Vitest and Testing Library cover React app
- Documented frontend test command is npm test
- Repository supports direct Python-module validation through local test files
- No CI/CD pipeline config present in workspace
- Evidence points to manual validation and operator-run deploy flows rather than automated merge gates
- Known developer-experience pain points include reliance on local credentials, large generated-data directories, and missing test tooling in some environments

## File Structure

.env - local env file for private runtime credentials and deployment values
.env.example - commit-safe template documenting required server-side and browser-side env vars
.gitignore - repository ignore rules for secrets, generated data, build outputs, local runtime artifacts
README.md - primary operator and developer guide for ETL setup, star-schema outputs, React deployment
config.ini - local settings and ETL state file consumed by Python scripts
config.ini.example - template for default ETL settings and empty pipeline state keys
data/ - root directory for reference inputs, generated warehouse outputs, raw archives, quality artifacts
  nomenclatures/ - static reference-data folder for EKATTE and product-category lookups used during transform
    Ekatte.zip - archived EKATTE reference bundle stored alongside extracted JSON files
    Ekatte/ - contains 12 EKATTE reference files following pattern ek_*.json plus related lookup artifacts
    EkatteXLS.zip - archived EKATTE XLS reference bundle stored alongside extracted workbook files
    EkatteXLS/ - contains 13 spreadsheet reference files following pattern *.xls and related workbook outputs
    cities-ekatte-nomenclature.json - primary settlement-code to settlement-name lookup used during transform
    product-categories.json - category-code reference mapping consumed during transform and sync
    unknown_categories_explanation.md - notes describing unresolved or unknown source category cases
  quality/ - contains 29 quality-report CSV files following pattern report_YYYY-MM-DD_HHMMSS.csv
  raw/ - contains 100 downloaded archive files following pattern YYYY-MM-DD.zip
  schema/ - local star-schema output directory for dimensions, fact aggregates, fact partitions
    dim_category.csv - current local category dimension export
    dim_company.csv - current local company dimension export
    dim_date.csv - current local date dimension export
    dim_file.csv - current local source-file dimension export
    dim_product.csv - current local product dimension export
    dim_settlement.csv - current local settlement dimension export
    dim_store.csv - current local store dimension export
    fact_prices_lookback.csv - consolidated lookback fact export used as basis for Supabase analytics sync
    facts/ - contains 100 date-partitioned fact CSV files following pattern YYYY-MM-DD.csv
lab/ - folder for exploratory or ad hoc data snapshots outside core ETL outputs
  2026-05-13/ - contains 210 per-company CSV snapshot files following pattern brand_uic.csv
  2026-05-13.zip - archived version of dated lab snapshot folder
logs/ - contains 41 operational log files following patterns transform_*.log, aib-action-*.log, pipeline.log
menu.bat - Windows launcher for interactive ETL menu
menu.py - interactive operator console for pipeline stats, ETL actions, Supabase sync, deploy, preview workflows
menu.sh - POSIX shell launcher for interactive ETL menu
package-lock.json - root npm lockfile currently tracked in workspace
patch_grouped.py - standalone Python helper script present at repository root for grouped patching work
react-app/ - React and Vite single-page analytics application deployed separately from ETL scripts
  dist/ - built frontend output directory for preview and deployment artifacts
  index.html - HTML entry point for Vite-built React application
  netlify.toml - Netlify config for React app deployment target
  package-lock.json - lockfile for React app npm dependencies
  package.json - React app manifest defining Vite, Vitest, React, Supabase JS dependencies and scripts
  public/ - public static asset directory copied into built frontend output
    favicon.ico - frontend favicon asset
  src/ - source directory for React app components, styles, data-access modules
    App.css - root application stylesheet for analytics SPA
    App.jsx - root React component validating browser credentials and mounting landing page
    App.test.jsx - frontend test module for root application behavior
    components/ - feature-component directory for landing-page UI
      LandingPage.jsx - unified landing-page component handling filters, grouping, direct page-number pagination without total-page calculation
      LandingPage.test.jsx - frontend test module covering landing-page filters, grouping, direct page-number pagination behavior
    index.css - global CSS for React application shell
    lib/ - frontend data-access and client-integration helper directory
      dataService.js - Supabase data layer for dimensions, landing-page rows, grouped queries, optional counts, query logging
      dataService.test.js - frontend test module for data-service helpers and RPC contracts
      queryLog.js - in-memory browser-session query log store for frontend request visibility
      supabase.js - shared Supabase client bootstrap and credential-validation guard for browser access
    main.jsx - React application bootstrap entry point used by Vite
    test-setup.js - shared frontend test setup for Vitest env
  test_output.txt - saved frontend test output artifact present in app workspace
  vite.config.js - Vite build and test config for React app
refresh.bat - Windows wrapper for full ETL refresh flow
refresh.sh - POSIX shell wrapper for full ETL refresh flow
requirements.txt - Python dependency manifest for scraping, HTML parsing, PostgreSQL sync, dotenv loading
src/ - Python module directory for ETL, sync, deployment logic
  config_utils.py - config bootstrap and atomic state-write helpers shared by ETL scripts
  deploy_netlify.py - Netlify deployment helper building React app and managing credential loading
  extract.py - downloader scraping open-data portal and saving new ZIP archives into data/raw/
  load_supabase.py - Supabase sync module provisioning schema objects, uploading current warehouse data, defining analytics RPC functions
  transform.py - transformer converting raw archives into local star schema and quality-report outputs
tests/ - Python test directory for ETL helpers, sync behavior, deployment helpers, menu actions
  test_config_utils.py - unit tests for config bootstrap, atomic writes, sibling-state preservation
  test_deploy_netlify.py - unit tests for Netlify CLI fallback, credential handling, menu integration
  test_extract.py - unit tests for ZIP link parsing, download scheduling, atomic rename behavior in extractor
  test_load_supabase.py - unit tests for Supabase DDL, RPC, retention, batch-insert helper behavior
  test_menu.py - unit tests for menu dispatch, local preview, credential-validation behavior
  test_transform.py - unit tests for delimiter detection, dimension upserts, quality reporting, settlement lookup behavior
