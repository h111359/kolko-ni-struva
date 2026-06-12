"""
load_supabase.py: Supabase sync module for the kolko-ni-struva star-schema.
Part of the kolko-ni-struva ETL pipeline (requests R-20260420-1730 and
R-20260526-2039).
Responsibilities: provision star-schema tables in Supabase, upsert all seven
dimension CSVs, truncate and reinsert fact_prices_lookback on every sync run,
prune remote dim_date to the latest local fact dates (rolling retention
window), and prune remote dim_category to only the category keys referenced by
the retained fact window.
"""
import csv
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = BASE_DIR / "data" / "schema"
FACTS_DIR = SCHEMA_DIR / "facts"
LANDING_PAGE_ROW_PROJECTION = "landing_page_row_projection"
BATCH_PAGE_SIZE = 2000
PROJECTION_REFRESH_BATCH_SIZE = 250

# ---------------------------------------------------------------------------
# Dim table descriptors: (table_name, csv_path, pk_col, all_columns)
# ---------------------------------------------------------------------------
DIM_TABLES: List[Tuple[str, Path, str, List[str]]] = [
    (
        "dim_date",
        SCHEMA_DIR / "dim_date.csv",
        "date_key",
        ["date_key", "date", "year", "month", "day", "weekday"],
    ),
    (
        "dim_company",
        SCHEMA_DIR / "dim_company.csv",
        "company_key",
        ["company_key", "uic", "company_name"],
    ),
    (
        "dim_settlement",
        SCHEMA_DIR / "dim_settlement.csv",
        "settlement_key",
        ["settlement_key", "ekatte", "settlement_name"],
    ),
    (
        "dim_category",
        SCHEMA_DIR / "dim_category.csv",
        "category_key",
        ["category_key", "category_code", "category_name"],
    ),
    (
        "dim_product",
        SCHEMA_DIR / "dim_product.csv",
        "product_key",
        ["product_key", "product_code", "product_name"],
    ),
    (
        "dim_store",
        SCHEMA_DIR / "dim_store.csv",
        "store_key",
        ["store_key", "store_name", "settlement_key", "company_key"],
    ),
    (
        "dim_file",
        SCHEMA_DIR / "dim_file.csv",
        "file_key",
        ["file_key", "file_name", "zip_date"],
    ),
]

# ---------------------------------------------------------------------------
# DDL definitions
# ---------------------------------------------------------------------------
_CREATE_DDL = f"""
CREATE TABLE IF NOT EXISTS dim_date (
    date_key   INTEGER PRIMARY KEY,
    date       DATE    NOT NULL,
    year       INTEGER NOT NULL,
    month      INTEGER NOT NULL,
    day        INTEGER NOT NULL,
    weekday    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_company (
    company_key  INTEGER PRIMARY KEY,
    uic          TEXT    NOT NULL,
    company_name TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_settlement (
    settlement_key INTEGER PRIMARY KEY,
    ekatte         TEXT,
    settlement_name TEXT
);

CREATE TABLE IF NOT EXISTS dim_category (
    category_key  INTEGER PRIMARY KEY,
    category_code TEXT,
    category_name TEXT
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_key  INTEGER PRIMARY KEY,
    product_code TEXT,
    product_name TEXT
);

CREATE TABLE IF NOT EXISTS dim_store (
    store_key      INTEGER PRIMARY KEY,
    store_name     TEXT,
    settlement_key INTEGER REFERENCES dim_settlement(settlement_key),
    company_key    INTEGER REFERENCES dim_company(company_key)
);

CREATE TABLE IF NOT EXISTS dim_file (
    file_key  INTEGER PRIMARY KEY,
    file_name TEXT,
    zip_date  DATE
);

CREATE TABLE IF NOT EXISTS fact_prices_lookback (
    date_key          INTEGER NOT NULL REFERENCES dim_date(date_key),
    store_key         INTEGER NOT NULL REFERENCES dim_store(store_key),
    file_key          INTEGER NOT NULL REFERENCES dim_file(file_key),
    category_key      INTEGER NOT NULL REFERENCES dim_category(category_key),
    product_key       INTEGER NOT NULL REFERENCES dim_product(product_key),
    retail_price      NUMERIC(12, 4),
    promo_price       NUMERIC(12, 4),
    retail_price_day1 NUMERIC(12, 4),
    promo_price_day1  NUMERIC(12, 4),
    retail_price_day2 NUMERIC(12, 4),
    promo_price_day2  NUMERIC(12, 4)
);

CREATE TABLE IF NOT EXISTS {LANDING_PAGE_ROW_PROJECTION} (
    date_key        INTEGER NOT NULL,
    settlement_key  INTEGER,
    category_key    INTEGER NOT NULL,
    company_key     INTEGER,
    store_key       INTEGER NOT NULL,
    file_key        INTEGER,
    product_key     INTEGER NOT NULL,
    file_name       TEXT,
    product_name    TEXT,
    category_name   TEXT,
    settlement_name TEXT,
    store_name      TEXT,
    company_name    TEXT,
    retail_price    NUMERIC(12, 4),
    promo_price     NUMERIC(12, 4),
    price           NUMERIC(12, 4)
);
"""

# Idempotent schema migration: drop NOT NULL constraints that may exist on
# nullable columns from a previous DDL iteration.  PostgreSQL silently
# succeeds when a column is already nullable, so these statements are safe
# to run on every invocation regardless of the current column state.
# The ADD COLUMN IF NOT EXISTS guards for fact_prices_lookback ensure
# forward-compatibility when the table was created by an older DDL iteration
# that omitted the lookback columns (request R-20260420-2055).
_ENSURE_NULLABLE_DDL = """
ALTER TABLE IF EXISTS dim_store ALTER COLUMN settlement_key DROP NOT NULL;
ALTER TABLE IF EXISTS dim_store ALTER COLUMN company_key DROP NOT NULL;
ALTER TABLE IF EXISTS dim_file ALTER COLUMN zip_date DROP NOT NULL;
ALTER TABLE IF EXISTS fact_prices_lookback ADD COLUMN IF NOT EXISTS retail_price_day1 NUMERIC(12, 4);
ALTER TABLE IF EXISTS fact_prices_lookback ADD COLUMN IF NOT EXISTS promo_price_day1  NUMERIC(12, 4);
ALTER TABLE IF EXISTS fact_prices_lookback ADD COLUMN IF NOT EXISTS retail_price_day2 NUMERIC(12, 4);
ALTER TABLE IF EXISTS fact_prices_lookback ADD COLUMN IF NOT EXISTS promo_price_day2  NUMERIC(12, 4);
"""

# ---------------------------------------------------------------------------
# Migration DDL (request R-20260430-0825)
# ---------------------------------------------------------------------------
# The legacy fact_prices table and the removed backend SQL audit table are
# dropped here to keep existing Supabase databases aligned with the current
# schema on every loader run.
_MIGRATION_DDL = """
DROP TABLE IF EXISTS backend_sql_audit_log;
DROP TABLE IF EXISTS fact_prices CASCADE;
DROP FUNCTION IF EXISTS get_landing_page_count(INT, INT, INT, INT, INT, TEXT, NUMERIC, NUMERIC);
"""

_REFRESH_LANDING_PAGE_PROJECTION_SQL = f"""
INSERT INTO {LANDING_PAGE_ROW_PROJECTION} (
    date_key,
    settlement_key,
    category_key,
    company_key,
    store_key,
    file_key,
    product_key,
    file_name,
    product_name,
    category_name,
    settlement_name,
    store_name,
    company_name,
    retail_price,
    promo_price,
    price
)
SELECT
    f.date_key,
    dstore.settlement_key,
    f.category_key,
    dstore.company_key,
    f.store_key,
    f.file_key,
    f.product_key,
    df.file_name,
    dp.product_name,
    dc.category_name,
    dst.settlement_name,
    dstore.store_name,
    dcomp.company_name,
    f.retail_price,
    f.promo_price,
    COALESCE(
        CASE
            WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                THEN LEAST(f.retail_price, f.promo_price)
            ELSE f.retail_price
        END,
        f.retail_price
    ) AS price
FROM fact_prices_lookback f
JOIN dim_product dp ON dp.product_key = f.product_key
JOIN dim_category dc ON dc.category_key = f.category_key
JOIN dim_store dstore ON dstore.store_key = f.store_key
JOIN dim_company dcomp ON dcomp.company_key = dstore.company_key
JOIN dim_settlement dst ON dst.settlement_key = dstore.settlement_key
LEFT JOIN dim_file df ON df.file_key = f.file_key;
"""

_REFRESH_LANDING_PAGE_PROJECTION_BATCH_SQL = f"""
INSERT INTO {LANDING_PAGE_ROW_PROJECTION} (
    date_key,
    settlement_key,
    category_key,
    company_key,
    store_key,
    file_key,
    product_key,
    file_name,
    product_name,
    category_name,
    settlement_name,
    store_name,
    company_name,
    retail_price,
    promo_price,
    price
)
SELECT
    f.date_key,
    dstore.settlement_key,
    f.category_key,
    dstore.company_key,
    f.store_key,
    f.file_key,
    f.product_key,
    df.file_name,
    dp.product_name,
    dc.category_name,
    dst.settlement_name,
    dstore.store_name,
    dcomp.company_name,
    f.retail_price,
    f.promo_price,
    COALESCE(
        CASE
            WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                THEN LEAST(f.retail_price, f.promo_price)
            ELSE f.retail_price
        END,
        f.retail_price
    ) AS price
FROM fact_prices_lookback f
JOIN dim_product dp ON dp.product_key = f.product_key
JOIN dim_category dc ON dc.category_key = f.category_key
JOIN dim_store dstore ON dstore.store_key = f.store_key
JOIN dim_company dcomp ON dcomp.company_key = dstore.company_key
JOIN dim_settlement dst ON dst.settlement_key = dstore.settlement_key
LEFT JOIN dim_file df ON df.file_key = f.file_key
WHERE f.file_key = ANY(%s);
"""

# ---------------------------------------------------------------------------
# Index DDL (R-20260429-0757, updated R-20260512-0529)
# ---------------------------------------------------------------------------
# Targeted B-tree indexes on fact_prices_lookback that allow the RPC helper
# functions and report-oriented SQL functions to satisfy their predicates via
# index scans instead of repeated sequential full-table scans.  All statements
# are idempotent (IF NOT EXISTS) and safe to run on every load_supabase.py
# invocation.
#
# idx_fact_prices_lookback_date_key: enables an index-only scan for
#   get_available_dates() (SELECT DISTINCT date_key FROM fact_prices_lookback).
# idx_fact_prices_lookback_date_store: composite index covering both the WHERE
#   predicate and the JOIN column for get_settlements_for_date().
_CREATE_INDEXES = f"""
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_fact_prices_lookback_date_key
    ON fact_prices_lookback(date_key);

CREATE INDEX IF NOT EXISTS idx_fpl_settlement_key
    ON fact_prices_lookback(store_key);

CREATE INDEX IF NOT EXISTS idx_fpl_category_key
    ON fact_prices_lookback(category_key);

CREATE INDEX IF NOT EXISTS idx_fpl_product_key
    ON fact_prices_lookback(product_key);

CREATE INDEX IF NOT EXISTS idx_fpl_file_key
    ON fact_prices_lookback(file_key);

CREATE INDEX IF NOT EXISTS idx_dim_product_name_trgm
    ON dim_product USING GIN (product_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_dim_product_name_sort
    ON dim_product(product_name, product_key);

CREATE INDEX IF NOT EXISTS idx_dim_store_name_sort
    ON dim_store(store_name, store_key);

CREATE INDEX IF NOT EXISTS idx_lp_row_projection_page
    ON {LANDING_PAGE_ROW_PROJECTION}(
        date_key,
        product_name,
        store_name,
        product_key,
        store_key,
        file_key
    );

CREATE INDEX IF NOT EXISTS idx_lp_row_projection_filter_keys
    ON {LANDING_PAGE_ROW_PROJECTION}(
        date_key,
        settlement_key,
        category_key,
        company_key,
        store_key
    );

CREATE INDEX IF NOT EXISTS idx_lp_row_projection_product_name_trgm
    ON {LANDING_PAGE_ROW_PROJECTION} USING GIN (product_name gin_trgm_ops);
"""

# ---------------------------------------------------------------------------
# RPC function DDL (request R-20260422-0902, updated R-20260512-0529)
# ---------------------------------------------------------------------------
# Idempotent helper functions used by the React app to filter selectors and to
# return already-aggregated or already-enriched report data without
# transferring raw fact rows to the client.  GRANT statements ensure the
# Supabase anon role can invoke them.
_CREATE_RPC_FUNCTIONS = f"""
CREATE OR REPLACE FUNCTION get_available_dates()
RETURNS SETOF int
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT date_key FROM fact_prices_lookback ORDER BY date_key DESC;
$$;

CREATE OR REPLACE FUNCTION get_settlements_for_date(p_date_key bigint)
RETURNS SETOF int
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT s.settlement_key
    FROM fact_prices_lookback fp
    JOIN dim_store s ON s.store_key = fp.store_key
    WHERE fp.date_key = p_date_key;
$$;

GRANT EXECUTE ON FUNCTION get_available_dates() TO anon;
GRANT EXECUTE ON FUNCTION get_settlements_for_date(bigint) TO anon;

CREATE OR REPLACE FUNCTION get_categories_for_settlement(p_settlement_key bigint, p_date_key bigint)
RETURNS SETOF int
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT fp.category_key
    FROM fact_prices_lookback fp
    WHERE fp.date_key = p_date_key
      AND fp.store_key IN (
          SELECT s.store_key
          FROM dim_store s
          WHERE s.settlement_key = p_settlement_key
      );
$$;

CREATE OR REPLACE FUNCTION get_settlements_for_category(p_category_key bigint, p_date_key bigint)
RETURNS SETOF int
LANGUAGE sql
STABLE
AS $$
    SELECT DISTINCT s.settlement_key
    FROM fact_prices_lookback fp
    JOIN dim_store s ON s.store_key = fp.store_key
    WHERE fp.date_key = p_date_key
      AND fp.category_key = p_category_key;
$$;

CREATE OR REPLACE FUNCTION get_report_1_category_prices(
    p_date_key bigint,
    p_settlement_key bigint,
    p_price_offset text DEFAULT 'current'
)
RETURNS TABLE(category_key integer, avg_price numeric)
LANGUAGE sql
STABLE
AS $$
    WITH priced_rows AS (
        SELECT
            fp.category_key,
            CASE
                WHEN p_price_offset = 'day1' THEN
                    CASE
                        WHEN fp.promo_price_day1 IS NOT NULL AND fp.promo_price_day1 > 0
                            THEN LEAST(COALESCE(fp.retail_price_day1, 0), fp.promo_price_day1)
                        ELSE COALESCE(fp.retail_price_day1, 0)
                    END
                WHEN p_price_offset = 'day2' THEN
                    CASE
                        WHEN fp.promo_price_day2 IS NOT NULL AND fp.promo_price_day2 > 0
                            THEN LEAST(COALESCE(fp.retail_price_day2, 0), fp.promo_price_day2)
                        ELSE COALESCE(fp.retail_price_day2, 0)
                    END
                ELSE
                    CASE
                        WHEN fp.promo_price IS NOT NULL AND fp.promo_price > 0
                            THEN LEAST(COALESCE(fp.retail_price, 0), fp.promo_price)
                        ELSE COALESCE(fp.retail_price, 0)
                    END
            END AS effective_price
        FROM fact_prices_lookback fp
        JOIN dim_store ds ON ds.store_key = fp.store_key
        WHERE fp.date_key = p_date_key
          AND ds.settlement_key = p_settlement_key
    )
    SELECT
        priced_rows.category_key,
        AVG(priced_rows.effective_price) AS avg_price
    FROM priced_rows
    GROUP BY priced_rows.category_key
    ORDER BY avg_price ASC, priced_rows.category_key ASC;
$$;

CREATE OR REPLACE FUNCTION get_report_2_rows(
    p_date_key bigint,
    p_settlement_key bigint,
    p_category_key bigint,
    p_price_offset text DEFAULT 'current'
)
RETURNS TABLE(
    product_key integer,
    category_key integer,
    file_key integer,
    retail_price numeric,
    promo_price numeric,
    calculated_price numeric,
    product_name text,
    store_name text,
    company_name text,
    file_name text,
    zip_date date
)
LANGUAGE sql
STABLE
AS $$
    WITH selected_rows AS (
        SELECT
            fp.product_key,
            fp.category_key,
            fp.file_key,
            CASE
                WHEN p_price_offset = 'day1' THEN fp.retail_price_day1
                WHEN p_price_offset = 'day2' THEN fp.retail_price_day2
                ELSE fp.retail_price
            END AS retail_price,
            CASE
                WHEN p_price_offset = 'day1' THEN fp.promo_price_day1
                WHEN p_price_offset = 'day2' THEN fp.promo_price_day2
                ELSE fp.promo_price
            END AS promo_price,
            dp.product_name,
            ds.store_name,
            dc.company_name,
            df.file_name,
            df.zip_date
        FROM fact_prices_lookback fp
        JOIN dim_store ds ON ds.store_key = fp.store_key
        JOIN dim_company dc ON dc.company_key = ds.company_key
        JOIN dim_product dp ON dp.product_key = fp.product_key
        LEFT JOIN dim_file df ON df.file_key = fp.file_key
        WHERE fp.date_key = p_date_key
          AND ds.settlement_key = p_settlement_key
          AND fp.category_key = p_category_key
    )
    SELECT
        selected_rows.product_key,
        selected_rows.category_key,
        selected_rows.file_key,
        selected_rows.retail_price,
        selected_rows.promo_price,
        CASE
            WHEN selected_rows.promo_price IS NOT NULL AND selected_rows.promo_price > 0
                THEN LEAST(COALESCE(selected_rows.retail_price, 0), selected_rows.promo_price)
            ELSE COALESCE(selected_rows.retail_price, 0)
        END AS calculated_price,
        selected_rows.product_name,
        selected_rows.store_name,
        selected_rows.company_name,
        selected_rows.file_name,
        selected_rows.zip_date
    FROM selected_rows
    ORDER BY calculated_price ASC, selected_rows.product_name ASC, selected_rows.store_name ASC;
$$;

CREATE OR REPLACE FUNCTION get_report_3_rows(
    p_date_key bigint,
    p_category_key bigint,
    p_price_offset text DEFAULT 'current'
)
RETURNS TABLE(
    product_key integer,
    category_key integer,
    retail_price numeric,
    promo_price numeric,
    calculated_price numeric,
    settlement_name text,
    product_name text,
    store_name text,
    company_name text
)
LANGUAGE sql
STABLE
AS $$
    WITH selected_rows AS (
        SELECT
            fp.product_key,
            fp.category_key,
            CASE
                WHEN p_price_offset = 'day1' THEN fp.retail_price_day1
                WHEN p_price_offset = 'day2' THEN fp.retail_price_day2
                ELSE fp.retail_price
            END AS retail_price,
            CASE
                WHEN p_price_offset = 'day1' THEN fp.promo_price_day1
                WHEN p_price_offset = 'day2' THEN fp.promo_price_day2
                ELSE fp.promo_price
            END AS promo_price,
            dsett.settlement_name,
            dp.product_name,
            ds.store_name,
            dc.company_name
        FROM fact_prices_lookback fp
        JOIN dim_store ds ON ds.store_key = fp.store_key
        LEFT JOIN dim_settlement dsett ON dsett.settlement_key = ds.settlement_key
        JOIN dim_company dc ON dc.company_key = ds.company_key
        JOIN dim_product dp ON dp.product_key = fp.product_key
        WHERE fp.date_key = p_date_key
          AND fp.category_key = p_category_key
    )
    SELECT
        selected_rows.product_key,
        selected_rows.category_key,
        selected_rows.retail_price,
        selected_rows.promo_price,
        CASE
            WHEN selected_rows.promo_price IS NOT NULL AND selected_rows.promo_price > 0
                THEN LEAST(COALESCE(selected_rows.retail_price, 0), selected_rows.promo_price)
            ELSE COALESCE(selected_rows.retail_price, 0)
        END AS calculated_price,
        selected_rows.settlement_name,
        selected_rows.product_name,
        selected_rows.store_name,
        selected_rows.company_name
    FROM selected_rows
    ORDER BY calculated_price ASC, selected_rows.settlement_name ASC, selected_rows.product_name ASC;
$$;

GRANT EXECUTE ON FUNCTION get_categories_for_settlement(bigint, bigint) TO anon;
GRANT EXECUTE ON FUNCTION get_settlements_for_category(bigint, bigint) TO anon;
GRANT EXECUTE ON FUNCTION get_report_1_category_prices(bigint, bigint, text) TO anon;
GRANT EXECUTE ON FUNCTION get_report_2_rows(bigint, bigint, bigint, text) TO anon;
GRANT EXECUTE ON FUNCTION get_report_3_rows(bigint, bigint, text) TO anon;

-- -----------------------------------------------------------------------
-- Landing-page cross-filter option RPCs (R-20260525-1400)
-- -----------------------------------------------------------------------
-- Each RPC returns the valid option list for one dimension filter given
-- the current values of the other four active filters.  All filters are
-- optional (NULL = unfiltered).  The option path now reads from the same
-- landing_page_row_projection surface as the visible row path so selector
-- interactions stay aligned with the narrowed frontend request model.

CREATE OR REPLACE FUNCTION get_lp_options_settlement(
    p_date_key     INT,
    p_category_key INT,
    p_company_key  INT,
    p_store_key    INT
)
RETURNS TABLE(settlement_key INT, name TEXT)
LANGUAGE sql
STABLE
AS $$
    WITH filtered_settlements AS (
        SELECT DISTINCT settlement_key, settlement_name
        FROM {LANDING_PAGE_ROW_PROJECTION}
        WHERE settlement_key IS NOT NULL
          AND (p_date_key     IS NULL OR date_key       = p_date_key)
          AND (p_category_key IS NULL OR category_key   = p_category_key)
          AND (p_company_key  IS NULL OR company_key    = p_company_key)
          AND (p_store_key    IS NULL OR store_key      = p_store_key)
    )
    SELECT
        settlement_key,
        settlement_name AS name
    FROM filtered_settlements
    ORDER BY settlement_name, settlement_key;
$$;

CREATE OR REPLACE FUNCTION get_lp_options_category(
    p_date_key       INT,
    p_settlement_key INT,
    p_company_key    INT,
    p_store_key      INT
)
RETURNS TABLE(category_key INT, name TEXT)
LANGUAGE sql
STABLE
AS $$
    WITH filtered_categories AS (
        SELECT DISTINCT category_key, category_name
        FROM {LANDING_PAGE_ROW_PROJECTION}
        WHERE (p_date_key       IS NULL OR date_key        = p_date_key)
          AND (p_settlement_key IS NULL OR settlement_key  = p_settlement_key)
          AND (p_company_key    IS NULL OR company_key     = p_company_key)
          AND (p_store_key      IS NULL OR store_key       = p_store_key)
    )
    SELECT
        category_key,
        category_name AS name
    FROM filtered_categories
    ORDER BY category_name, category_key;
$$;

CREATE OR REPLACE FUNCTION get_lp_options_company(
    p_date_key       INT,
    p_settlement_key INT,
    p_category_key   INT,
    p_store_key      INT
)
RETURNS TABLE(company_key INT, name TEXT)
LANGUAGE sql
STABLE
AS $$
    WITH filtered_companies AS (
        SELECT DISTINCT company_key, company_name
        FROM {LANDING_PAGE_ROW_PROJECTION}
        WHERE company_key IS NOT NULL
          AND (p_date_key       IS NULL OR date_key        = p_date_key)
          AND (p_settlement_key IS NULL OR settlement_key  = p_settlement_key)
          AND (p_category_key   IS NULL OR category_key    = p_category_key)
          AND (p_store_key      IS NULL OR store_key       = p_store_key)
    )
    SELECT
        company_key,
        company_name AS name
    FROM filtered_companies
    ORDER BY company_name, company_key;
$$;

CREATE OR REPLACE FUNCTION get_lp_options_store(
    p_date_key       INT,
    p_settlement_key INT,
    p_category_key   INT,
    p_company_key    INT
)
RETURNS TABLE(store_key INT, store_name TEXT)
LANGUAGE sql
STABLE
AS $$
    WITH filtered_stores AS (
        SELECT DISTINCT store_key, store_name
        FROM {LANDING_PAGE_ROW_PROJECTION}
        WHERE (p_date_key       IS NULL OR date_key        = p_date_key)
          AND (p_settlement_key IS NULL OR settlement_key  = p_settlement_key)
          AND (p_category_key   IS NULL OR category_key    = p_category_key)
          AND (p_company_key    IS NULL OR company_key     = p_company_key)
    )
    SELECT
        store_key,
        store_name
    FROM filtered_stores
    ORDER BY store_name, store_key;
$$;

CREATE OR REPLACE FUNCTION get_lp_options_date(
    p_settlement_key INT,
    p_category_key   INT,
    p_company_key    INT,
    p_store_key      INT
)
RETURNS TABLE(date_key INT, date DATE)
LANGUAGE sql
STABLE
AS $$
    WITH filtered_date_keys AS (
                SELECT DISTINCT date_key
                FROM {LANDING_PAGE_ROW_PROJECTION}
                WHERE (p_settlement_key IS NULL OR settlement_key = p_settlement_key)
                    AND (p_category_key   IS NULL OR category_key   = p_category_key)
                    AND (p_company_key    IS NULL OR company_key    = p_company_key)
                    AND (p_store_key      IS NULL OR store_key      = p_store_key)
    )
    SELECT
        dd.date_key,
        dd.date
    FROM filtered_date_keys keys
    JOIN dim_date dd ON dd.date_key = keys.date_key
    ORDER BY dd.date_key DESC;
$$;

GRANT EXECUTE ON FUNCTION get_lp_options_settlement(INT, INT, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_lp_options_category(INT, INT, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_lp_options_company(INT, INT, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_lp_options_store(INT, INT, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_lp_options_date(INT, INT, INT, INT) TO anon;
GRANT SELECT ON {LANDING_PAGE_ROW_PROJECTION} TO anon;

-- -----------------------------------------------------------------------
-- Landing-page main data RPCs (R-20260525-1400, updated R-20260525-2203)
-- -----------------------------------------------------------------------
-- get_landing_page_rows: server-side paginated flat detail rows backed by a
--   read-optimized materialized projection; returns rows only (no window count).
-- get_landing_page_grouped: dynamic two-level GROUP BY aggregation; group
--   column names are validated against a whitelist before %I interpolation
--   to prevent SQL injection (security-critical).

CREATE OR REPLACE FUNCTION get_landing_page_rows(
    p_date_key       INT,
    p_settlement_key INT,
    p_category_key   INT,
    p_company_key    INT,
    p_store_key      INT,
    p_product_name   TEXT,
    p_price_min      NUMERIC,
    p_price_max      NUMERIC,
    p_offset         INT,
    p_limit          INT
)
RETURNS JSON
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_sql TEXT;
    v_json JSON;
BEGIN
    v_sql := '
        SELECT COALESCE(json_agg(row_to_json(t)), ''[]''::json)
        FROM (
            SELECT
                file_name,
                product_name,
                category_name,
                settlement_name,
                store_name,
                company_name,
                retail_price,
                promo_price,
                price
            FROM {LANDING_PAGE_ROW_PROJECTION}
            WHERE 1=1 ';

    IF p_date_key IS NOT NULL THEN
        v_sql := v_sql || ' AND date_key = $1 ';
    END IF;

    IF p_settlement_key IS NOT NULL THEN
        v_sql := v_sql || ' AND settlement_key = $2 ';
    END IF;

    IF p_category_key IS NOT NULL THEN
        v_sql := v_sql || ' AND category_key = $3 ';
    END IF;

    IF p_company_key IS NOT NULL THEN
        v_sql := v_sql || ' AND company_key = $4 ';
    END IF;

    IF p_store_key IS NOT NULL THEN
        v_sql := v_sql || ' AND store_key = $5 ';
    END IF;

    IF p_product_name IS NOT NULL THEN
        v_sql := v_sql || ' AND product_name ILIKE ''%'' || $6 || ''%'' ';
    END IF;

    IF p_price_min IS NOT NULL THEN
        v_sql := v_sql || ' AND price >= $7 ';
    END IF;

    IF p_price_max IS NOT NULL THEN
        v_sql := v_sql || ' AND price <= $8 ';
    END IF;

    v_sql := v_sql || '
            ORDER BY
                product_name ASC,
                store_name ASC,
                product_key ASC,
                store_key ASC,
                file_key ASC
            OFFSET $9 LIMIT $10
        ) t';

    EXECUTE v_sql INTO v_json USING p_date_key, p_settlement_key, p_category_key, p_company_key, p_store_key, p_product_name, p_price_min, p_price_max, p_offset, p_limit;
    RETURN v_json;
END;
$$;

CREATE OR REPLACE FUNCTION get_landing_page_grouped(
    p_date_key       INT,
    p_settlement_key INT,
    p_category_key   INT,
    p_company_key    INT,
    p_store_key      INT,
    p_product_name   TEXT,
    p_price_min      NUMERIC,
    p_price_max      NUMERIC,
    p_group_by_1     TEXT,
    p_group_by_2     TEXT
)
RETURNS JSON
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    -- Whitelist of valid grouping dimension column names from the inner subquery.
    -- Any name outside this list is rejected before identifier interpolation.
    v_valid_dims CONSTANT TEXT[] := ARRAY[
        'settlement_name', 'category_name', 'company_name', 'store_name', 'date_key'
    ];
    v_select_group2 TEXT := '';
    v_groupby_extra TEXT := '';
    v_sql           TEXT;
    v_result        JSON;
BEGIN
    -- Security gate: reject group-by values not in the whitelist.
    -- %I provides identifier quoting, but validation is the primary defence.
    IF NOT (p_group_by_1 = ANY(v_valid_dims)) THEN
        RAISE EXCEPTION 'Invalid grouping dimension: %', p_group_by_1;
    END IF;
    IF p_group_by_2 IS NOT NULL AND NOT (p_group_by_2 = ANY(v_valid_dims)) THEN
        RAISE EXCEPTION 'Invalid grouping dimension: %', p_group_by_2;
    END IF;

    -- Build optional second-level GROUP BY SQL fragments using validated identifiers.
    IF p_group_by_2 IS NOT NULL THEN
        v_select_group2 := format(', %I AS group2', p_group_by_2);
        v_groupby_extra := format(', %I', p_group_by_2);
    END IF;

    -- Dynamically assemble the aggregation query.
    -- %I: identifier quoting for validated group-by names.
    -- %s: pre-built SQL fragments that already carry %I quoting.
    -- %%: escapes to a literal % inside the ILIKE pattern.
    v_sql := format($q$
        SELECT COALESCE(json_agg(row_to_json(g)), '[]'::json)
        FROM (
            SELECT
                %I AS group1
                %s,
                AVG(eff_price)    AS price_avg,
                MIN(eff_price)    AS price_min,
                MAX(eff_price)    AS price_max,
                AVG(CASE WHEN promo_price IS NOT NULL AND promo_price > 0 THEN promo_price END)
                                  AS promo_avg,
                MIN(CASE WHEN promo_price IS NOT NULL AND promo_price > 0 THEN promo_price END)
                                  AS promo_min,
                MAX(CASE WHEN promo_price IS NOT NULL AND promo_price > 0 THEN promo_price END)
                                  AS promo_max
            FROM (
                SELECT
                    dc.category_name,
                    dst.settlement_name,
                    dcomp.company_name,
                    dstore.store_name,
                    f.date_key,
                    f.promo_price,
                    COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price
                        END,
                        f.retail_price
                    ) AS eff_price
                FROM fact_prices_lookback f
                JOIN dim_product dp    ON dp.product_key    = f.product_key
                JOIN dim_category dc   ON dc.category_key   = f.category_key
                JOIN dim_store dstore  ON dstore.store_key  = f.store_key
                JOIN dim_company dcomp ON dcomp.company_key = dstore.company_key
                JOIN dim_settlement dst ON dst.settlement_key = dstore.settlement_key
                WHERE 1=1
                %s
            ) inner_data
            GROUP BY %I %s
            ORDER BY %I
        ) g
    $q$, p_group_by_1, v_select_group2,
    
    (CASE WHEN p_date_key IS NOT NULL THEN ' AND f.date_key = $1 ' ELSE '' END) || 
    (CASE WHEN p_settlement_key IS NOT NULL THEN ' AND dstore.settlement_key = $2 ' ELSE '' END) || 
    (CASE WHEN p_category_key IS NOT NULL THEN ' AND f.category_key = $3 ' ELSE '' END) || 
    (CASE WHEN p_company_key IS NOT NULL THEN ' AND dstore.company_key = $4 ' ELSE '' END) || 
    (CASE WHEN p_store_key IS NOT NULL THEN ' AND f.store_key = $5 ' ELSE '' END) || 
    (CASE WHEN p_product_name IS NOT NULL THEN ' AND dp.product_name ILIKE ''%%'' || $6 || ''%%'' ' ELSE '' END) || 
    (CASE WHEN p_price_min IS NOT NULL THEN ' AND COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) >= $7 ' ELSE '' END) || 
    (CASE WHEN p_price_max IS NOT NULL THEN ' AND COALESCE(
                        CASE WHEN f.promo_price IS NOT NULL AND f.promo_price > 0
                            THEN LEAST(f.retail_price, f.promo_price)
                            ELSE f.retail_price END,
                        f.retail_price) <= $8 ' ELSE '' END),
    
    p_group_by_1, v_groupby_extra, p_group_by_1);

    EXECUTE v_sql INTO v_result
    USING p_date_key, p_settlement_key, p_category_key, p_company_key, p_store_key,
          p_product_name, p_price_min, p_price_max;
    RETURN v_result;
END;
$$;

GRANT EXECUTE ON FUNCTION get_landing_page_rows(INT, INT, INT, INT, INT, TEXT, NUMERIC, NUMERIC, INT, INT) TO anon;
GRANT EXECUTE ON FUNCTION get_landing_page_grouped(INT, INT, INT, INT, INT, TEXT, NUMERIC, NUMERIC, TEXT, TEXT) TO anon;
"""

def _chunk_rows(rows: List[tuple], page_size: int) -> List[List[tuple]]:
    """
    Split rows into stable execute_batch-sized pages.

    Args:
        rows: Parameter rows scheduled for batched execution.
        page_size: Maximum number of rows per batch page.

    Returns:
        List of row pages in original order.
    """
    return [rows[index:index + page_size] for index in range(0, len(rows), page_size)]


def execute_sql(
    cur: "psycopg2.extensions.cursor",
    sql: str,
    params: Optional[tuple] = None,
) -> None:
    """
    Execute one SQL statement on the caller cursor.

    Args:
        cur: Open cursor used for the current transaction.
        sql: SQL template or literal statement text.
        params: Bound parameters for the SQL template, when present.
    """
    cur.execute(sql, params)


def execute_batch_rows(
    cur: "psycopg2.extensions.cursor",
    sql: str,
    rows: List[tuple],
    page_size: int = BATCH_PAGE_SIZE,
) -> None:
    """
    Execute batched SQL in stable pages.

    Args:
        cur: Open cursor used for the current transaction.
        sql: Parameterized SQL template for one logical statement.
        rows: Parameter rows to execute.
        page_size: Maximum number of parameter rows per emitted batch page.
    """
    for page_rows in _chunk_rows(rows, page_size):
        psycopg2.extras.execute_batch(cur, sql, page_rows, page_size=len(page_rows))


def create_tables(conn: "psycopg2.extensions.connection") -> None:
    """
    Provision the star-schema tables, apply nullable migrations, run the
    fact_prices migration (DROP TABLE IF EXISTS), provision the landing-page
    row projection and RPC helper functions, and create targeted indexes.

    Execution order:
    1. _CREATE_DDL         — CREATE TABLE IF NOT EXISTS for all eight tables
                             (fact_prices_lookback is the sole fact table).
    2. _ENSURE_NULLABLE_DDL — idempotent nullable-column migration guards.
    3. _MIGRATION_DDL      — DROP TABLE IF EXISTS backend_sql_audit_log and
                             DROP TABLE IF EXISTS fact_prices CASCADE;
                             removes retired tables on every run (idempotent).
    4. _CREATE_RPC_FUNCTIONS — provision get_available_dates(),
                             get_settlements_for_date(),
                             get_categories_for_settlement(),
                             get_settlements_for_category(), and the
                             report-oriented RPC helpers against
                             fact_prices_lookback.
    5. _CREATE_INDEXES     — CREATE INDEX IF NOT EXISTS on fact_prices_lookback,
                             including the report-oriented composite indexes.

    Args:
        conn: Open psycopg2 connection to the Supabase PostgreSQL database.

    Side effects:
        Issues five DDL execute calls within a single transaction on conn;
        commits on success.  All DDL blocks are idempotent and safe to run
        on every invocation.
    """
    with conn.cursor() as cur:
        execute_sql(cur, _MIGRATION_DDL)
        execute_sql(cur, _CREATE_DDL)
        # Apply the nullable migration after table creation so that any pre-existing
        # tables with erroneous NOT NULL constraints are corrected idempotently.
        execute_sql(cur, _ENSURE_NULLABLE_DDL)
        # Provision the landing-page projection and RPC helper functions.
        execute_sql(cur, _CREATE_RPC_FUNCTIONS)
        # Create targeted indexes on fact_prices_lookback so the RPC functions
        # execute via index-only scans.  Both use IF NOT EXISTS and are idempotent.
        execute_sql(cur, _CREATE_INDEXES)
    conn.commit()
    print("Tables created / verified.")
    print("Indexes created / verified.")


def refresh_landing_page_projection(
    conn: "psycopg2.extensions.connection",
) -> None:
    """
    Rebuild the landing-page derived table after retained-window changes.

    Args:
        conn: Open psycopg2 connection to the Supabase PostgreSQL database.

    Side effects:
        Truncates and repopulates the derived table that backs the landing-page row and
        count RPCs so anonymous pagination reads the latest retained data.
    """
    with conn.cursor() as cur:
        execute_sql(cur, "SELECT DISTINCT file_key FROM fact_prices_lookback ORDER BY file_key")
        file_keys = [row[0] for row in cur.fetchall()]

        execute_sql(cur, f"TRUNCATE TABLE {LANDING_PAGE_ROW_PROJECTION}")
        for batch_start in range(0, len(file_keys), PROJECTION_REFRESH_BATCH_SIZE):
            batch_keys = file_keys[batch_start:batch_start + PROJECTION_REFRESH_BATCH_SIZE]
            execute_sql(cur, _REFRESH_LANDING_PAGE_PROJECTION_BATCH_SQL, (batch_keys,))

        if not file_keys:
            execute_sql(cur, _REFRESH_LANDING_PAGE_PROJECTION_SQL)
        execute_sql(cur, f"ANALYZE {LANDING_PAGE_ROW_PROJECTION}")
    conn.commit()
    print("Landing-page projection refreshed.")


def upsert_dim(
    conn: "psycopg2.extensions.connection",
    table: str,
    csv_path: Path,
    pk_col: str,
    columns: List[str],
) -> int:
    """
    Upsert all rows from a dimension CSV into the corresponding Supabase table.

    Uses INSERT … ON CONFLICT (pk_col) DO UPDATE SET … executed in a single
    transaction via execute_batch (page size 2000).

    Args:
        conn:     Open psycopg2 connection.
        table:    Name of the target PostgreSQL table.
        csv_path: Path to the local dimension CSV file.
        pk_col:   Name of the primary-key column used as the conflict target.
        columns:  Ordered list of all column names in the CSV / table.

    Returns:
        Number of rows processed.

    Raises:
        FileNotFoundError: If csv_path does not exist.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Dimension CSV not found: {csv_path}")

    # Build non-pk column list for the DO UPDATE SET clause.
    update_cols = [c for c in columns if c != pk_col]
    set_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)

    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        f" ON CONFLICT ({pk_col}) DO UPDATE SET {set_clause}"
    )

    rows: List[tuple] = []
    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Convert empty strings to None for nullable numeric FK columns.
            rows.append(tuple(_coerce(row[c]) for c in columns))

    with conn.cursor() as cur:
        execute_batch_rows(cur, sql, rows)
    conn.commit()
    print(f"  Upserted {len(rows):,} rows into {table}.")
    return len(rows)


def _coerce(value: str) -> Optional[str]:
    """
    Convert an empty CSV cell string to None; leave non-empty strings intact.

    Args:
        value: Raw cell value from csv.DictReader.

    Returns:
        None for empty/blank strings; original string otherwise.
    """
    stripped = value.strip()
    return None if stripped == "" else stripped


def get_latest_local_date(facts_dir: Path) -> Optional[str]:
    """
    Return the stem (YYYY-MM-DD) of the newest fact CSV in facts_dir.

    Args:
        facts_dir: Directory containing date-partitioned fact CSV files
                   named YYYY-MM-DD.csv.

    Returns:
        ISO date string of the newest fact file, or None when directory is
        empty or absent.
    """
    if not facts_dir.exists():
        return None
    stems = sorted(p.stem for p in facts_dir.iterdir() if p.suffix == ".csv")
    return stems[-1] if stems else None


def get_retained_local_dates(facts_dir: Path, n: int = 3) -> List[str]:
    """
    Return the n newest local fact date strings (YYYY-MM-DD) in ascending order.

    These dates define the rolling retention window that remote fact_prices and
    dim_date must be pruned to on every sync run (request R-20260429-0825).
    When fewer than n fact files exist, all available dates are returned.

    Args:
        facts_dir: Directory containing date-partitioned fact CSV files
                   named YYYY-MM-DD.csv.
        n:         Number of newest dates to retain.  Defaults to 3.

    Returns:
        List of ISO date strings, oldest-first, of length min(n, total_files).
        Returns an empty list when the directory is absent or contains no CSVs.
    """
    if not facts_dir.exists():
        return []
    stems = sorted(p.stem for p in facts_dir.iterdir() if p.suffix == ".csv")
    # Slice the sorted list so only the n newest dates are kept.
    return stems[-n:] if stems else []


def get_date_keys_for_dates(
    conn: "psycopg2.extensions.connection",
    date_strings: List[str],
) -> List[int]:
    """
    Query remote dim_date for the date_key integers matching the given date strings.

    Used to translate the string-based retained-date window into the integer
    date_key values needed by the DELETE predicates against fact_prices and
    dim_date (request R-20260429-0825).

    Args:
        conn:         Open psycopg2 connection.
        date_strings: List of ISO date strings (YYYY-MM-DD) to look up.

    Returns:
        List of date_key integers whose dim_date.date column matches one of the
        supplied strings.  Empty list if date_strings is empty or no rows match.
    """
    if not date_strings:
        return []
    with conn.cursor() as cur:
        # Cast the Python list to a PostgreSQL text array; compare via CAST to
        # avoid locale-dependent date formatting differences.
        execute_sql(cur, "SELECT date_key FROM dim_date WHERE date::text = ANY(%s)", (date_strings,))
        rows = cur.fetchall()
    return [r[0] for r in rows]


def prune_dim_date(
    conn: "psycopg2.extensions.connection",
    retained_date_keys: List[int],
) -> int:
    """
    Delete all dim_date rows whose date_key is not in the retained set.

    Must be called AFTER prune_fact_prices to avoid FK-constraint violations:
    fact_prices rows reference dim_date, so dim_date rows can only be removed
    after all referencing fact rows are gone (request R-20260429-0825).

    Includes a safety guard: if retained_date_keys is empty, the function
    skips the delete and returns 0.

    Args:
        conn:               Open psycopg2 connection.
        retained_date_keys: List of date_key integers to keep.  Rows with any
                            other date_key are deleted.

    Returns:
        Number of rows deleted.

    Raises:
        psycopg2.DatabaseError: On any database error; transaction is rolled
            back before re-raising.
    """
    if not retained_date_keys:
        # Safety guard: never wipe all rows when the retention set is undefined.
        print("  Retention skip: no retained date keys resolved; dim_date unchanged.")
        return 0

    placeholders = ", ".join(["%s"] * len(retained_date_keys))
    sql = f"DELETE FROM dim_date WHERE date_key NOT IN ({placeholders})"
    try:
        with conn.cursor() as cur:
            execute_sql(cur, sql, tuple(retained_date_keys))
            deleted = cur.rowcount
        conn.commit()
    except psycopg2.DatabaseError:
        conn.rollback()
        raise

    print(f"  Pruned {deleted:,} dim_date rows outside retained window.")
    return deleted


def prune_dim_category(
    conn: "psycopg2.extensions.connection",
) -> int:
    """
    Delete all dim_category rows whose category_key is not referenced by
    any row in fact_prices_lookback.

    Must be called AFTER insert_lookback completes so that
    fact_prices_lookback contains the fully refreshed 3-day fact window
    (request R-20260507-2248).  Deleting unreferenced dim_category rows does
    not violate the FK constraint direction, which runs from fact to dimension.

    Includes a safety guard: if the SELECT DISTINCT subquery returns no
    category keys (fact_prices_lookback is empty), the DELETE is skipped and
    the function returns 0 to avoid wiping all dim_category rows.

    Args:
        conn: Open psycopg2 connection to the Supabase PostgreSQL database.

    Returns:
        Number of dim_category rows deleted.

    Raises:
        psycopg2.DatabaseError: On any database error; transaction is rolled
            back before re-raising.
    """
    try:
        # Fetch the set of category_keys currently referenced by the retained
        # fact window.  This subquery is the authoritative source of "live"
        # category keys after insert_lookback has fully refreshed the table.
        with conn.cursor() as cur:
            execute_sql(cur, "SELECT DISTINCT category_key FROM fact_prices_lookback")
            rows = cur.fetchall()

        referenced_keys = [r[0] for r in rows]

        if not referenced_keys:
            # Safety guard: an empty fact table would cause NOT IN (...) to
            # delete every dim_category row, which is never the intended
            # behaviour.  Skip the prune and leave dim_category unchanged.
            print(
                "  Safety guard: fact_prices_lookback contains no rows;"
                " dim_category unchanged."
            )
            return 0

        placeholders = ", ".join(["%s"] * len(referenced_keys))
        sql = f"DELETE FROM dim_category WHERE category_key NOT IN ({placeholders})"
        with conn.cursor() as cur:
            execute_sql(cur, sql, tuple(referenced_keys))
            deleted = cur.rowcount
        conn.commit()
    except psycopg2.DatabaseError:
        conn.rollback()
        raise

    print(f"  Pruned {deleted:,} dim_category rows outside retained window.")
    return deleted


def insert_lookback(
    conn: "psycopg2.extensions.connection",
    csv_path: Path,
) -> int:
    """
    Truncate and reinsert all rows from the lookback CSV into fact_prices_lookback.

    The table is always fully replaced on each sync run because
    fact_prices_lookback is a derived snapshot artifact (see request
    R-20260420-2055, Assumption A6).  Uses execute_batch (page size 2000)
    within a single transaction; rolls back and re-raises on error.

    Args:
        conn:     Open psycopg2 connection.
        csv_path: Path to data/schema/fact_prices_lookback.csv.  If the file
                  is absent or empty, the table is truncated and the function
                  returns 0 without raising an error.

    Returns:
        Number of rows inserted.

    Raises:
        psycopg2.DatabaseError: On any database error; transaction is rolled
            back before re-raising.
    """
    columns = [
        "date_key",
        "store_key",
        "file_key",
        "category_key",
        "product_key",
        "retail_price",
        "promo_price",
        "retail_price_day1",
        "promo_price_day1",
        "retail_price_day2",
        "promo_price_day2",
    ]
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    insert_sql = (
        f"INSERT INTO fact_prices_lookback ({col_list}) VALUES ({placeholders})"
    )

    rows: List[tuple] = []
    if csv_path.exists():
        with open(csv_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(tuple(_coerce(row[c]) for c in columns))

    try:
        with conn.cursor() as cur:
            # Full replacement: truncate first, then reinsert.
            execute_sql(cur, "TRUNCATE TABLE fact_prices_lookback")
            if rows:
                execute_batch_rows(cur, insert_sql, rows)
        conn.commit()
    except psycopg2.DatabaseError:
        conn.rollback()
        raise

    print(f"  Inserted {len(rows):,} rows into fact_prices_lookback.")
    return len(rows)


def main() -> None:
    """
    Orchestrate the Supabase sync: provision tables (dropping legacy
    fact_prices via migration DDL), upsert dims, prune remote dim_date to the
    rolling 3-day retention window, and refresh fact_prices_lookback.

    The retention window is defined as the latest 3 local fact dates found in
    data/schema/facts/ (request R-20260429-0825).  fact_prices_lookback is
    always fully replaced (TRUNCATE + reinsert) on every sync run.
    fact_prices was removed in request R-20260430-0825.

    Exits with code 1 on missing DATABASE_URL or connection failure,
    surfacing a clear error message without a stack trace.

    Side effects:
        Reads .env from the project root via python-dotenv.
        Reads dim CSVs from data/schema/.
        Reads the latest fact CSV from data/schema/facts/.
        Writes to the Supabase PostgreSQL database.
    """
    # Load .env from the project root so DATABASE_URL is available.
    load_dotenv(BASE_DIR / ".env")
    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print(
            "ERROR: DATABASE_URL is not set. "
            "Create a .env file at the project root (see .env.example).",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Connecting to Supabase …")
    try:
        conn = psycopg2.connect(db_url)
    except psycopg2.OperationalError as exc:
        print(f"ERROR: Could not connect to the database: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        # Step 1: Provision tables.
        print("Provisioning schema …")
        create_tables(conn)

        # Step 2: Upsert all dimension tables in FK-dependency order so that
        # referenced rows exist before dependent tables are populated.
        print("Upserting dimension tables …")
        for table, csv_path, pk_col, columns in DIM_TABLES:
            upsert_dim(conn, table, csv_path, pk_col, columns)

        # Step 3: Determine the rolling retention window from local fact files.
        # Retained dates are the newest 3 local fact partitions; remote dim_date
        # will be pruned to exactly these dates after the lookback sync.
        latest_local = get_latest_local_date(FACTS_DIR)
        if latest_local is None:
            print("No local fact files found. Run transform.py first.")
            return

        retained_dates = get_retained_local_dates(FACTS_DIR)
        # Resolve remote date_key integers AFTER dim_date has been upserted
        # (Step 2) so that all retained dates are guaranteed to exist in dim_date.
        retained_date_keys = get_date_keys_for_dates(conn, retained_dates)

        print(f"Latest local fact date  : {latest_local}")
        print(f"Retained local dates    : {retained_dates}")

        # Step 4: Sync the derived lookback table (always full replacement).
        # fact_prices_lookback is the sole fact table after R-20260430-0825.
        lookback_csv = SCHEMA_DIR / "fact_prices_lookback.csv"
        print("Syncing fact_prices_lookback …")
        insert_lookback(conn, lookback_csv)

        # Step 5: Prune remote dim_date to match the retained fact dates so
        # the React app date selector shows only dates with fact data.
        # No FK constraint from fact_prices_lookback to dim_date requires ordering
        # changes here — lookback was just fully replaced, so we prune after.
        print("Pruning remote dim_date to retained dates …")
        prune_dim_date(conn, retained_date_keys)

        # Step 6: Prune remote dim_category to only the category keys that are
        # referenced by the retained fact window (R-20260507-2248).  Must be
        # called after insert_lookback (Step 4) so the fact table reflects
        # the fully refreshed data, and after upsert_dim for dim_category
        # (Step 2) so newly added categories are not immediately pruned.
        print("Pruning remote dim_category to retained fact window …")
        prune_dim_category(conn)

        # Step 7: Refresh the denormalized landing-page projection after all
        # retained-window mutations so the anon RPC reads the current snapshot.
        print("Refreshing landing-page projection …")
        refresh_landing_page_projection(conn)

        print("Supabase sync complete.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
