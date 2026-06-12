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
    cur.execute("EXPLAIN ANALYZE SELECT get_landing_page_rows(NULL, NULL, NULL, NULL, NULL, 'мляко', NULL, NULL, 0, 10)")
    for row in cur.fetchall():
        print(row)
except Exception as e:
    print(e)
