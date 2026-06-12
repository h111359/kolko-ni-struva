from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()
conn = psycopg2.connect(
    os.environ['DATABASE_URL'],
    options='-c statement_timeout=150000000000000'
)
conn.autocommit = True
cur = conn.cursor()
try:
    print("Creating index...")
    cur.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fpl_product_key ON fact_prices_lookback(product_key);")
    print("Index created")
except Exception as e:
    print(e)
