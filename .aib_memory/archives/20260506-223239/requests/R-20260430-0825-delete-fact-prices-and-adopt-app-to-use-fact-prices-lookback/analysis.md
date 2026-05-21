# Analysis — R-20260430-0825: Delete fact_prices and adopt app to use fact_prices_lookback

## Executive Summary

- **Request ID:** R-20260430-0825

- **Title:** Delete fact_prices and adopt app to use fact_prices_lookback

- **High-level purpose:** Consolidate dual-fact-table Supabase storage by verifying data equivalence between `fact_prices` and `fact_prices_lookback`, then dropping `fact_prices` and migrating the ETL sync, RPC functions, and React app to use `fact_prices_lookback` exclusively.

- **Information loss verdict:** There IS a material information difference. `fact_prices` retains up to 3 distinct date_keys (D, D-1, D-2); `fact_prices_lookback` always contains only 1 date_key (D). Deleting `fact_prices` without first extending `fact_prices_lookback` to cover all retained dates will reduce the React app date selector to a single date. This is the critical design decision requiring user input before implementation can proceed (see Q001).

- **Confirmed equivalence for date D:** For the current latest date D, both tables store identical base columns (`date_key`, `store_key`, `file_key`, `category_key`, `product_key`, `retail_price`, `promo_price`). `fact_prices_lookback` is a superset (adds 4 lookback columns). The base row data for date D is equivalent.

- **Components impacted:** `src/load_supabase.py` (DDL, insert/prune functions, main orchestration), `react-app/src/lib/dataService.js` (all 3 reports), PostgreSQL RPC functions (`get_available_dates`, `get_settlements_for_date`), B-tree indexes, `tests/test_load_supabase.py`, and `context.md`.

- **`request.md` sections added/updated this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.

---

## Domain Knowledge Essentials

- **Star schema:** A data warehouse design pattern with a central fact table (containing measurable events) connected to surrounding dimension tables (descriptive context). Used here to organise daily retail-price observations into queryable analytical structure.

- **Fact table:** Stores quantitative measurements (here: `retail_price`, `promo_price`) keyed to dimension surrogate keys. Two fact tables exist: `fact_prices` (rolling 3-day, base columns only) and `fact_prices_lookback` (single-date, enriched with prior-day price columns).

- **Lookback table:** A derived fact-table variant that embeds prior-period values as additional columns in each row. Here, `fact_prices_lookback` contains each product-store observation for date D plus the same product-store's prices from D-1 and D-2 — eliminating the need for self-joins to compare day-over-day prices.

- **Rolling retention window:** The practice of keeping only the N most recent data periods remotely (here N=3 days), pruning older rows to limit Supabase storage and query volumes. Previously enforced on `fact_prices`; `fact_prices_lookback` already self-manages as a full-replace-each-run table.

- **Dimension table (`dim_date`, `dim_settlement`, etc.):** Lookup tables providing descriptive attributes. `dim_date` is currently pruned to only the retained 3 dates so the React app date selector shows only dates with fact data.

- **EKATTE:** Bulgarian administrative code registry for settlements, used as a natural key in `dim_settlement`.

- **UIC (ЕИК):** Bulgarian company identification number, used as a natural key in `dim_company`.

- **Impacted roles/personas:** Data engineers (ETL operators, run `load_supabase.py`); public end users (read-only React app viewers).

- **Business processes touched:** Cloud sync of the star-schema; React app data retrieval for all three public reports.

---

## Technical Knowledge & Terms

- **`fact_prices`:** PostgreSQL table in Supabase; 7 columns; rolling 3-day retention; indexed by 2 B-tree indexes; referenced by 2 RPC functions; queried by all 3 React app reports.

- **`fact_prices_lookback`:** PostgreSQL table in Supabase; 11 columns; always fully replaced per sync run (TRUNCATE + INSERT); currently represents only date D (the latest fact date); not yet queried by any React report.

- **`build_lookback_table` (`src/transform.py`):** Produces `data/schema/fact_prices_lookback.csv` by iterating date D's fact CSV and looking up D-1 and D-2 prices via composite key `(store_key, category_key, product_key)`. Output is ~1.35M rows (for date D alone) with 11 columns. Not affected by this request.

- **`insert_lookback` (`src/load_supabase.py`):** TRUNCATEs `fact_prices_lookback` then reinserts all rows from `data/schema/fact_prices_lookback.csv`. Runs every sync.

- **`insert_fact_day` (`src/load_supabase.py`):** Inserts rows from one date-partitioned fact CSV into `fact_prices`. Will be removed by this request.

- **`prune_fact_prices` / `prune_dim_date` (`src/load_supabase.py`):** Delete rows outside the retained date window. `prune_fact_prices` must be removed; `prune_dim_date` must be preserved (still needed to trim `dim_date` to retained dates matching `fact_prices_lookback`).

- **`get_available_dates()` RPC:** PostgreSQL function returning DISTINCT `date_key` integers from `fact_prices`. Used by the React app to filter the date selector. Must be updated to query `fact_prices_lookback`.

- **`get_settlements_for_date(p_date_key bigint)` RPC:** Returns DISTINCT `settlement_key` integers for a given `date_key` from `fact_prices` via `dim_store` join. Must be updated to query `fact_prices_lookback`.

- **`idx_fact_prices_date_key` / `idx_fact_prices_date_store`:** B-tree indexes on `fact_prices` enabling index-only scans for RPC functions. Must be re-created on `fact_prices_lookback` post-migration.

- **PostgREST:** The HTTP layer that Supabase uses to expose PostgreSQL tables and functions to the React app via `@supabase/supabase-js`. Table renames in PostgreSQL are transparent to PostgREST after schema refresh.

- **`dataService.js`:** React app's data-fetching module. `fetchReport1`, `fetchReport2`, `fetchReport3` all call `supabase.from('fact_prices')`. `fetchDimensions` calls the `get_available_dates` RPC. All require the table name change.

- **FK constraint chain:** `fact_prices(date_key) → dim_date(date_key)`. Dropping `fact_prices` removes this constraint, making `dim_date` pruning simpler but `prune_dim_date` must still reference retained keys from `fact_prices_lookback`.

- **Evidence log:**
  - `src/load_supabase.py` DDL → `fact_prices` has 7 columns; `fact_prices_lookback` has 11 columns; both tables exist.
  - `src/transform.py` `build_lookback_table` → `fact_prices_lookback` always covers exactly one date (D); D-1 and D-2 data embedded as price columns, not as separate rows.
  - `react-app/src/lib/dataService.js` → all three `fetchReport*` functions call `supabase.from('fact_prices')`; none queries `fact_prices_lookback`.
  - Previous implementation log (R-20260429-0825) → `fact_prices_lookback` inserted 1,353,714 rows (1 day); `fact_prices` pruned to 3 days.
  - `dim_date` is pruned by `prune_dim_date` to match `fact_prices` retained keys → after migration, must be driven by `fact_prices_lookback` date_keys.

- **Files read for this analysis:**
  - `.aib_memory/context.md`
  - `src/load_supabase.py` (full)
  - `src/transform.py` (lines 600–760)
  - `react-app/src/lib/dataService.js` (full)
  - `tests/test_load_supabase.py` (lines 1–80)
  - `.aib_memory/requests/R-20260422-0902-fix-date-filter-and-category-prices-report/analysis.md` (excerpt)
  - `.aib_memory/requests/R-20260420-2055-add-day-1-and-day-2-prices-to-fact-prices/analysis.md` (excerpt)
  - `.aib_memory/requests/R-20260429-0825-trim-supabase-facts-to-latest-3-days/implementation.md` (excerpt)

---

## Research Results

**Pattern: single fact table with embedded lookback columns**

Industry practice in retail analytics frequently uses a "wide fact" pattern where the current period's fact table embeds prior-period values as additional columns — precisely what `fact_prices_lookback` already does. This is a common approach to avoid self-joins in reporting queries. The `fact_prices` table is the classic "narrow fact" pattern suitable for multi-period browsing. The coexistence of both was a transitional state from when `fact_prices_lookback` was first introduced (R-20260420-2055) as an enrichment layer on top of `fact_prices`.

**Pattern: RPC function dependency on fact table**

The `get_available_dates()` and `get_settlements_for_date()` RPC functions are tightly coupled to `fact_prices` via hardcoded table references in their DDL. Migrating them requires `CREATE OR REPLACE FUNCTION` — the idempotent form already used — making the update safe and non-disruptive. However, after migration, `get_available_dates()` will return only 1 date_key (from `fact_prices_lookback`, which covers only D), reducing the date selector to a single entry unless the scope is extended.

**Pattern: TRUNCATE-based full replacement vs. incremental upsert**

`fact_prices_lookback` uses a TRUNCATE + full reinsert pattern — appropriate for a derived snapshot table where the source is always fully regenerated. This is architecturally cleaner for a lookback table than the incremental insert + prune pattern used for `fact_prices`.

**Pattern: index migration for renamed/replaced table**

Standard database migration practice: create indexes on the new table before dropping the old one, test queries against new indexes, then drop old table. The idempotent `CREATE INDEX IF NOT EXISTS` pattern already used in this codebase makes this safe.

---

## External Benchmarking

- **Wide-fact / slowly changing lookback pattern (Kimball dimensional modelling):** In Kimball's methodology, embedding prior-period measures in the current period's fact row (rather than joining back to prior fact snapshots) is called a "periodic snapshot with embedded comparison values." This is exactly `fact_prices_lookback`. The single-source-of-truth principle Kimball advocates supports the user's goal of eliminating `fact_prices` once `fact_prices_lookback` fully covers the needed query patterns.
  - **Takeaway:** The migration is architecturally aligned with dimensional modelling best practice — if `fact_prices_lookback` covers all required query patterns, consolidation is sound.
  - **Applicability:** Directly applicable; the key condition is that `fact_prices_lookback` must be queryable for all the date ranges the app requires.

- **PostgreSQL table deprecation patterns (pg-zero-downtime, Braintree engineering):** Common patterns include: (1) create a view aliased to the old table name to ease the transition, (2) add `DROP TABLE` to the migration DDL as an idempotent step after data is confirmed in the new table, (3) remove old DDL from provisioning scripts. The idempotent `CREATE TABLE IF NOT EXISTS` pattern here means `DROP TABLE IF EXISTS fact_prices` can be safely added once the table is confirmed empty or ready for removal.
  - **Takeaway:** Adding `DROP TABLE IF EXISTS fact_prices` to `create_tables()` is a clean, idempotent approach that handles both first-run (table doesn't exist) and migration-run (table exists) scenarios.
  - **Applicability:** Directly applicable; the same idempotency philosophy already used throughout this codebase.

---

## Minimal Spikes and Experiments

**Spike: verify fact_prices_lookback date coverage**
- Hypothesis: `fact_prices_lookback` always contains exactly one distinct `date_key` (date D), not 3.
- Approach: Read `src/transform.py`'s `build_lookback_table` source; trace the iteration — it reads only `fact_d` (the last element of sorted fact CSVs) and writes one row per row in that file. D-1 and D-2 data appear only as embedded price lookup columns, not as additional rows with different `date_key` values.
- Outcome: Confirmed. `build_lookback_table` iterates only over `fact_d` rows; all output rows share one `date_key`. The previous implementation run inserted 1,353,714 rows — consistent with ~1 day of data.
- Conclusion: **`fact_prices_lookback` covers 1 date; `fact_prices` covers up to 3 dates. Information loss for D-1 and D-2 separate date views is real and must be addressed in the design decision.**

**Spike: React app query surface for fact_prices**
- Hypothesis: All three React app reports (`fetchReport1`, `fetchReport2`, `fetchReport3`) call `supabase.from('fact_prices')`, not `supabase.from('fact_prices_lookback')`.
- Approach: Read `react-app/src/lib/dataService.js` in full.
- Outcome: Confirmed. All three fetch functions reference `'fact_prices'`. No function references `'fact_prices_lookback'`.
- Conclusion: All three reports require a table name change. The column interface (`category_key`, `retail_price`, `promo_price`, `product_key`, `store_key`) is identical between `fact_prices` and `fact_prices_lookback`'s base columns — no query restructuring needed beyond the table name.

**Spike: prune_dim_date independence from fact_prices**
- Hypothesis: `prune_dim_date` can be retained after deleting `fact_prices` if it receives retained date_keys derived from `fact_prices_lookback` instead of `fact_prices`.
- Approach: Read `prune_dim_date` in `src/load_supabase.py` — it accepts a `retained_date_keys` parameter and runs `DELETE FROM dim_date WHERE date_key NOT IN (...)`. The caller in `main()` derives retained keys via `get_retained_local_dates(FACTS_DIR)` and `get_date_keys_for_dates(conn, retained_dates)` from `dim_date`, independent of `fact_prices`.
- Outcome: `prune_dim_date` does not depend on `fact_prices` at all — the retained keys are derived from local CSV filenames and `dim_date`.
- Conclusion: `prune_dim_date` can be retained as-is. Only `prune_fact_prices` and `insert_fact_day` need removal.

---

## AI Copilot Suggestions

- **The information gap is the real risk — address it explicitly before any deletion.** The user premises that "the same information is stored in `fact_prices_lookback`" — this is not currently true for multi-date browsing. If the date selector collapses from 3 dates to 1, that is a visible product regression. Before any `DROP TABLE`, a concious decision must be made (see Q001). If preserving 3-date browsing is required, `build_lookback_table` should be extended to produce rows for all 3 retained dates (not just D), and `fact_prices_lookback` DDL must reflect a multi-date-key allowance — which is a non-trivial change in transform.py scope.
  - Suggestion: Frame Q001 explicitly around the date browsing regression; if the user accepts single-date-only, the migration is straightforward; if not, expand the scope to include changes to `build_lookback_table`.

- **The DROP TABLE approach in `create_tables()` is clean but may surprise on first run.** Adding `DROP TABLE IF EXISTS fact_prices` to the idempotent `create_tables()` function means every future `load_supabase.py` run will attempt to drop `fact_prices`. This is safe if `fact_prices` is never re-created, but if the old DDL accidentally remains in a partial state, the drop will silently succeed, potentially confusing future debugging. Consider adding a comment block explaining that this is a migration DDL step.
  - Suggestion: Add a clearly labelled `_MIGRATION_DDL` block that runs `DROP TABLE IF EXISTS fact_prices CASCADE` and is separate from the idempotent provisioning DDL — making its migration-once intent explicit and auditable.

- **Scope is well-sized for the stated goal.** The request correctly avoids touching `transform.py`, `extract.py`, or dimension tables. The surface area — 1 Python module, 1 JS module, 2 RPC functions, 2 indexes, 1 test file — is compact and manageable. No scope creep risk from the current definition.
  - Suggestion: Confirm Q001 before implementation to prevent a mid-task scope expansion from "migrate table name" to "extend lookback CSV to cover 3 dates."

- **Test coverage gap: `insert_lookback` is not currently covered in the test suite.** `tests/test_load_supabase.py` imports `insert_lookback` is not listed in the current imports. After migration, `insert_lookback` becomes the primary fact sync function and should have explicit test coverage, especially for the TRUNCATE-then-INSERT pattern and the empty-CSV edge case.
  - Suggestion: Add at least one test for `insert_lookback` covering the happy path and the zero-row edge case as part of the test update task.

---

## Testing

- **T1 — No fact_prices DDL in provisioned schema:** Run `venv/bin/python src/load_supabase.py` against a clean test database. Execute `SELECT to_regclass('public.fact_prices')`. Expected outcome: returns `NULL` (table does not exist).

- **T2 — fact_prices_lookback is queryable for reports:** After sync, execute a query equivalent to `SELECT category_key, retail_price, promo_price FROM fact_prices_lookback WHERE date_key = <D> AND store_key IN (...)`. Expected outcome: returns non-empty rows matching Report 1 expected output.

- **T3 — get_available_dates RPC returns at least one date:** Call `supabase.rpc('get_available_dates')` via the React app or psycopg2 directly after migration. Expected outcome: returns exactly 1 date_key integer (date D's key).

- **T4 — get_settlements_for_date RPC returns correct settlements:** Call `supabase.rpc('get_settlements_for_date', { p_date_key: <D> })` after migration. Expected outcome: returns at least one settlement_key integer matching a known store for date D.

- **T5 — React app Report 1 renders correctly:** Load the React app date selector; select the available date; select a settlement. Expected outcome: Report 1 bar chart renders with category data; no console errors referencing `fact_prices`.

- **T6 — React app Reports 2 and 3 render correctly:** Select a category from Report 1; navigate to Report 2 and Report 3. Expected outcome: Tables render with product/store/company data; no errors.

- **T7 — load_supabase.py exits 0 on re-run (idempotency):** Run `venv/bin/python src/load_supabase.py` twice consecutively. Expected outcome: Both runs exit 0; second run produces "already present" or similar message for fact sync; `fact_prices_lookback` row count unchanged.

- **T8 — npm run build exits 0:** Run `cd react-app && npm run build`. Expected outcome: exits 0; `dist/` produced; no build errors referencing `fact_prices`.

- **T9 — pytest suite passes:** Run `venv/bin/python -m pytest tests/ -v`. Expected outcome: all tests pass (exit 0); no import errors or test failures caused by removed functions.

- **T10 — No fact_prices references in source files:** Run `grep -r "fact_prices[^_]" src/ react-app/src/`. Expected outcome: zero matches (all references are to `fact_prices_lookback`).

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The consolidation from two fact tables to one is architecturally sound — the "narrow fact + wide lookback" dual-table pattern was always a transitional state. The key risk is that `fact_prices_lookback`'s current single-date-key design breaks the multi-date browsing that `fact_prices` enables. If the product needs 3-date browsing, `build_lookback_table` must emit rows for all 3 retained dates, which pulls `transform.py` into scope. If only the current date is needed, the migration is straightforward. The `prune_dim_date` function is correctly identified as table-independent and can be retained. Index creation on `fact_prices_lookback` before dropping `fact_prices` is the correct migration sequence.

- The FK from `fact_prices` → `dim_date` is automatically resolved when `fact_prices` is dropped.
- Adding `DROP TABLE IF EXISTS fact_prices CASCADE` as a migration DDL step is idempotent and safe.
- RPC functions update via `CREATE OR REPLACE` — no privilege escalation required.
- Architecture is cleaner post-migration: single fact table, single sync pattern (TRUNCATE + reinsert), no prune logic needed for facts.

### Product Owner

The migration achieves the consolidation goal and removes dead technical weight. The main business risk is the date selector regression: if users currently select D-1 or D-2 to compare prices across days, losing that capability is a visible feature regression. The user's request says "check if there is no loss of information" — the analysis confirms there IS loss (multi-date browsing for D-1 and D-2 becomes unavailable in the app). User confirmation is essential before proceeding. If confirmed acceptable, the success criteria are clear and testable.

- No new business capability is introduced; this is a consolidation task.
- The Q001 decision is the only blocker to implementation.

### User (End User of React App)

From an end-user perspective, the impact depends entirely on the Q001 decision. If the date selector currently shows D-2, D-1, and D and the user relies on viewing D-1 or D-2 data, they will notice the regression when the selector collapses to a single date. If users primarily view the latest date D (which is the most common use case for a daily price checker), the impact is minimal. No visual or interaction changes to the reports themselves are planned — only the underlying data source changes.

- Users will not see a UI change beyond the date selector possibly showing fewer options.
- If Q001 is answered in favour of single-date-only, no user-facing migration notice is planned.

### Security Officer

No authentication, authorisation, or credential changes are involved. The tables being dropped and migrated are query-side resources accessible via the Supabase anon key with public SELECT/EXECUTE grants. Dropping `fact_prices` does not expose any new data surface. The RPC function grants (`GRANT EXECUTE TO anon`) are idempotent and retained on `fact_prices_lookback`-based functions. No credential handling in source code changes.

- No OWASP Top 10 impact identified.
- `DROP TABLE CASCADE` in the migration DDL is correctly scoped to `fact_prices` only; no risk of cascading to dimension tables since `fact_prices_lookback` does not have a FK referencing `fact_prices`.

### Data Governance Officer

The migration merges two tables into one, reducing data redundancy. `fact_prices_lookback` is a derived table (transform output), not a source-of-truth table — it is always regeneratable from `data/schema/facts/` and the local ETL. Deleting `fact_prices` from Supabase is not a data loss event because the source-of-truth data remains in local `data/schema/facts/` CSV files. The rolling retention window was explicitly designed (R-20260429-0825) to limit remote storage to 3 days; this is preserved. Data lineage remains clear: kolkostruva.bg → `data/raw/` → `data/schema/facts/` → `data/schema/fact_prices_lookback.csv` → Supabase `fact_prices_lookback`.

- `fact_prices` in Supabase is ephemeral (3-day rolling window) — its deletion from Supabase does not affect data retention compliance.
- Documentation update to `context.md` must reflect the single-fact-table architecture accurately.
