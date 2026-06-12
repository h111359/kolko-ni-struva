from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()
conn = psycopg2.connect(
    os.environ['DATABASE_URL'],
    options='-c statement_timeout=15000'
)
cur = conn.cursor()
try:
    cur.execute("""
EXPLAIN ANALYZE        WITH visible_rows AS (
            SELECT
                f.file_key,
                f.category_key,
                f.store_key,
                f.product_key,
                f.retail_price,
                f.promo_price,
                dp.product_name,
                dstore.store_name
            FROM fact_prices_lookback f
            JOIN dim_product dp   ON dp.product_key   = f.product_key
            JOIN dim_store dstore ON dstore.store_key = f.store_key
            WHERE 1=1 
            ORDER BY
                dp.product_name ASC,
                dstore.store_name ASC,
                f.product_key ASC,
                f.store_key ASC,
                f.file_key ASC
            OFFSET 0 LIMIT 10
        )
        SELECT
            df.file_name,
            vr.product_name,
            dc.category_name,
            dst.settlement_name,
            vr.store_name,
            dcomp.company_name,
            vr.retail_price,
            vr.promo_price,
            -- Effective price is computed only for the visible page rows.
            COALESCE(
                CASE WHEN vr.promo_price IS NOT NULL AND vr.promo_price > 0
                    THEN LEAST(vr.retail_price, vr.promo_price)
                    ELSE vr.retail_price
                END,
                vr.retail_price
            ) AS effective_price
        FROM visible_rows vr
        JOIN dim_category dc   ON dc.category_key   = vr.category_key
        JOIN dim_store dsttbl  ON dsttbl.store_key  = vr.store_key
        JOIN dim_settlement dst ON dst.settlement_key = dsttbl.settlement_key
        JOIN dim_company dcomp ON dcomp.company_key = dsttbl.company_key
        JOIN dim_file df       ON df.file_key       = vr.file_key;
""")
    for row in cur.fetchall():
        print(row)
except Exception as e:
    print(e)
