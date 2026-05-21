# Request

## Goal

Build a Python 3 ETL pipeline (`src/pipeline.py`) that:

1. Downloads daily ZIP price files from `https://kolkostruva.bg/opendata` that are not yet present in `data/raw/`.

2. Extracts and parses each company's CSV file from each unprocessed ZIP (handling UTF-8 BOM encoding and double-quoted CSV anomalies).

3. Populates a JSON-based star schema (`data/schema/`) with five SCD Type 2 dimension files and date-partitioned daily fact files.

4. Maintains nomenclature dimensions automatically, adding new companies, trade objects, and products as slowly-changing dimensions (SCD Type 2).

5. Detects anomalous or malformed company files by comparing each file against the same company's historical submissions and checks for significant (more than **25%**) deviation in unique product-code count, total row count, and unique product-name count against the 7-day rolling mean; writes a per-day anomaly report to `data/quality/`.

6. Creates a `README.md` project user guide (installation, usage, output description) and populates the stub AIB technical documentation files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) with project-specific content.

7. Creates `docs/supabase-setup.md` — a step-by-step instruction document for setting up the Supabase PostgreSQL database from the local JSON star-schema, including the full SQL DDL to create all tables, indexes, and foreign keys.

8. Creates `src/migrate_supabase.py` — a standalone Python script that reads local JSON star-schema data and loads it into Supabase PostgreSQL using a two-tier strategy: (a) Tier 1: last 7 days of data at daily product-level aggregation (`avg_retail_price`, `min_promo_price` across trade objects and cities); (b) Tier 2: all older data aggregated at weekly category-level (`avg_retail_price`, `avg_promo_price`, `product_count`, `submission_count`). Total migrated data must remain within **500 MB** of Supabase storage including indexes.

## Background

The project collects daily retail prices from the Bulgarian government's open-data portal (kolkostruva.bg). An existing script `extract.py` scrapes and downloads daily ZIP archives into `data/raw/`. As of 2026-04-07, 52 daily ZIP files (2026-02-15 to 2026-04-07) are present. No analytical data store exists yet; all nomenclature data is in JSON files under `data/nomenclatures/`.

Key source data characteristics (verified from `data/raw/`):
- ZIP naming: `YYYY-MM-DD.zip`; ~208 company CSV files per ZIP; ~1.28M rows per ZIP; ~20 MB per ZIP.
- CSV filename format: `CompanyName (LegalName)_UIC.csv` (UIC = Единен идентификационен код / EIK).
- CSV columns (7, UTF-8 BOM encoded): "Населено място" (EKATTE city code), "Търговски обект" (trade object name), "Наименование на продукта" (product name), "Код на продукта" (company-specific product code), "Категория" (category ID 1–101), "Цена на дребно" (retail price), "Цена в промоция" (promo price, may be empty).
- Nomenclatures: `cities-ekatte-nomenclature.json` (EKATTE to city name), `product-categories.json` (101 category IDs and names including 86–101 for pharmaceutical products).
- Known data quality issue: some files (e.g., pharmacy chains) have double-quoted CSV field values that require normalization during parsing.

## Scope

- `src/pipeline.py` — single entry point integrating download, ETL, and quality checks.
- `src/migrate_supabase.py` — standalone Supabase migration script (one-time initial load).
- `README.md` — project user guide (installation, configuration, usage, outputs).
- `docs/supabase-setup.md` — Supabase database setup instructions with full SQL DDL.
- `.env` — environment variable file (contains `DATABASE_URL`; must be added to `.gitignore`).
- `data/schema/dim_company.json` — SCD Type 2; natural key = UIC.
- `data/schema/dim_trade_object.json` — SCD Type 2; natural key = (UIC, trade-object-name).
- `data/schema/dim_product.json` — SCD Type 2; natural key = (UIC, product-code).
- `data/schema/dim_city.json` — SCD Type 2; natural key = EKATTE code; seeded from nomenclature.
- `data/schema/dim_category.json` — SCD Type 2; natural key = category ID; seeded from nomenclature.
- `data/schema/facts/YYYY-MM-DD.json` — one fact file per day; records contain (date, company_sk, trade_object_sk, product_sk, city_sk, category_sk, retail_price, promo_price).
- `data/quality/YYYY-MM-DD-report.json` — per-day anomaly report; per-company status: OK / WARNING / REJECTED.
- Backfill: process all 52 existing ZIPs on first run.
- Logging: write to `logs/` using Python `logging`.
- Documentation updates: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01.

## Out of scope

- Web API, dashboarding, or front-end.
- Real-time alerting or email notifications for anomalies.
- Data archiving, deletion, or retention policy.
- Containerisation or CI/CD pipeline.
- Changes to the `data/raw/` directory layout or format.
- Modification of source nomenclature JSON files (`data/nomenclatures/`).
- Supabase incremental daily sync (migration script is one-time initial load only).
- Supabase row-level security, authentication policies, or API key rotation.

## Constraints

- Python 3 (≥3.9) only; `psycopg2-binary` permitted as an exception (self-contained native library) for the migration script.
- Must process one ZIP at a time to bound memory to one day's data (~200 MB peak).
- Source site is public and unauthenticated; no credential management required for download.
- Must be idempotent: re-running the pipeline against a ZIP that has already been processed must produce no duplicate records.
- Anomaly detection threshold (default **25%** deviation from 7-day rolling mean across three metrics: row count, unique product-code count, unique product-name count) must be configurable via a script-level constant or `--threshold` CLI argument.
- `DATABASE_URL` for Supabase must be read from the `DATABASE_URL` environment variable (or `.env` file); never hardcoded.
- Total Supabase storage after migration must not exceed **500 MB** (including table heap and indexes).

## Success criteria

- SC1: `python src/pipeline.py` processes all 52 existing ZIPs without crash; 52 daily fact files exist under `data/schema/facts/`.
- SC2: Dimension files contain correct SCD Type 2 records (with `valid_from`, `valid_to`, `is_current`) for all companies, trade objects, products, cities, and categories from raw data; no missing surrogate key in fact files.
- SC3: A quality report exists at `data/quality/YYYY-MM-DD-report.json` for each processed day; a pharmacy-chain file with double-quoted CSV fields from 2026-02-15 is flagged with status `WARNING` and reason citing double-quoted CSV fields.
- SC4: Re-running the script a second time when no new ZIPs are available produces no new fact or dimension records (idempotency verified).
- SC5: A newly downloaded ZIP is processed within the same pipeline run that downloads it; its fact file appears in `data/schema/facts/` after the run completes.
- SC6: The anomaly threshold constant is configurable via a script-level constant or `--threshold` CLI argument.
- SC7: `README.md` exists in the project root; it covers installation, running the pipeline, and interpreting quality reports. All eight AIB product-doc stub files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) are populated with project-specific content (no longer contain only `_This file is seeded by AIB initialize._`).
- SC8: `docs/supabase-setup.md` exists; it contains valid PostgreSQL DDL (CREATE TABLE statements for all dimension and fact tables) and a step-by-step guide for applying it in Supabase.
- SC9: `python src/migrate_supabase.py` loads all local JSON data into Supabase without error when `DATABASE_URL` is set. After migration, total Supabase storage usage is ≤500 MB. Tier 1 table (`fact_prices_daily`) contains rows only for the 7 most recent days; Tier 2 table (`fact_prices_weekly_hist`) contains weekly aggregates for all older days.
