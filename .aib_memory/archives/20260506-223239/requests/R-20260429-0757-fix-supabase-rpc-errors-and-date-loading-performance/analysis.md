# Analysis: R-20260429-0757 — Fix Supabase RPC errors and date loading performance

## Executive Summary

- **Request ID:** R-20260429-0757
- **Request title:** Fix Supabase RPC errors and date loading performance

- **Purpose:** The React Analytics App fails on startup with HTTP 500 (`canceling statement due to statement timeout`) errors from both `get_available_dates()` and `get_settlements_for_date()` Supabase RPC calls. A separate HTTP 404 error also appears in the console. The 500 errors cause the app to fall back to showing all `dim_date` rows in the date selector instead of only dates with real `fact_prices` data, and to fall back to all known settlements in Report 1 instead of only those with data for the selected date.

- **Root cause identified:** The `fact_prices` table in Supabase (~82 million rows) has no indexes on `date_key` or `store_key`. Both RPC functions execute full-table scans that exceed Supabase's statement timeout. The fix is to add `CREATE INDEX IF NOT EXISTS` DDL for `fact_prices(date_key)` and a composite `fact_prices(date_key, store_key)` to `src/load_supabase.py`.

- **404 root cause:** Research indicates the 404 is most likely from a browser's automatic `/favicon.ico` request. Although `react-app/index.html` already suppresses this with `<link rel="icon" href="data:,">`, certain browser-version/extension combinations still attempt `/favicon.ico`. Since no `favicon.ico` exists in `react-app/` or `react-app/dist/`, the Netlify server (or Vite dev server) returns 404. A physical `favicon.ico` file in `react-app/public/` (or an explicit `<link rel="icon" type="image/svg+xml" ...>` referencing an existing asset) would eliminate it conclusively. Alternatively, the 404 could originate from a Supabase endpoint called before the schema is fully provisioned, but given that the Supabase project ID is visible in the other error URLs and the functions are known to exist (they return 500, not 404), the favicon hypothesis is the highest-probability explanation.

- **Impact on `request.md`:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` sections were added or updated during this analysis run.

---

## Domain Knowledge Essentials

- **EKATTE:** Bulgarian administrative code registry. Uniquely identifies settlements (cities, villages, districts). The `dim_settlement` table maps `settlement_key` ↔ `ekatte` code.
- **Fact table (`fact_prices`):** Central table in the star schema holding ~82 million product price observation rows, each linked via surrogate keys to dimension tables for date, store, file, category, and product.
- **Date selector:** The dropdown at the top of the React app UI letting the end user select which calendar date's data to view. It must show only dates for which `fact_prices` rows exist in Supabase (not all dates in the `dim_date` dimension table).
- **Settlement filter (Report 1):** The city dropdown in Report 1 must show only settlements that have at least one store with price data on the currently selected date — served by the `get_settlements_for_date` RPC.
- **Statement timeout:** Maximum wall-clock time a SQL query is allowed to run before the database server cancels it and returns an error. Supabase free-tier sets this to approximately 3 seconds (the exact value may vary; the symptom "canceling statement due to statement timeout" confirms the limit is being hit).

---

## Technical Knowledge & Terms

- **Supabase PostgREST RPC:** Supabase exposes PostgreSQL functions via a REST endpoint at `/rest/v1/rpc/<function_name>`. The React app calls these functions via `@supabase/supabase-js` `supabase.rpc(...)`.
- **Full table scan:** A sequential scan across every row of a table. On `fact_prices` (~82M rows) with no index on `date_key`, every call to `get_available_dates()` or `get_settlements_for_date()` performs a full scan — on Supabase free tier, this reliably exceeds the statement timeout.
- **B-tree index (`CREATE INDEX`):** A balanced-tree index that allows PostgreSQL to satisfy equality and range predicates on indexed columns in `O(log n)` rather than `O(n)`. A single-column index on `fact_prices(date_key)` enables an **index-only scan** for `get_available_dates()`. A composite index on `fact_prices(date_key, store_key)` allows `get_settlements_for_date` to resolve all `store_key` values for a given `date_key` without touching the heap.
- **Index-only scan:** When all columns referenced by a query are present in the index, PostgreSQL can answer the query from the index alone without reading the table heap — drastically faster than a heap scan.
- **`CREATE INDEX IF NOT EXISTS`:** Idempotent DDL form. Safe to run on every `load_supabase.py` invocation: if the index already exists, the statement is a no-op.
- **Supabase free-tier statement timeout:** Free Supabase projects have a 3-second (or similar) per-statement timeout enforced by the `pg_statement_timeout` GUC. The error message "canceling statement due to statement timeout" is the canonical PostgreSQL message emitted when this limit is exceeded.
- **`STABLE` function volatility:** Both RPC functions are marked `STABLE`, meaning PostgreSQL may cache their result within a single query. This is appropriate (they do not modify data) but does not affect timeout behaviour.
- **`favicon.ico` 404:** Browsers automatically request `/favicon.ico` regardless of `<link rel="icon">` declarations in some configurations. Since `react-app/public/` contains no `favicon.ico`, the Vite dev server and Netlify both return 404 for this request.
- **Files read for this analysis:**
  - `react-app/src/lib/dataService.js` (full)
  - `react-app/src/App.jsx` (lines 1–100)
  - `react-app/src/lib/supabase.js` (full)
  - `react-app/src/components/Report1.jsx` (lines 1–100)
  - `react-app/index.html` (full)
  - `src/load_supabase.py` (lines 1–230)
  - `.aib_memory/context.md` (full)
  - `.aib_memory/references.md` (full)

---

## Research Results

### Pattern scan

**Pattern: Missing index on large fact table causing RPC timeout**
- The `fact_prices` table is the central fact table of the star schema. It has a natural access pattern of filtering by `date_key` (one partition per day). PostgreSQL's planner defaults to a sequential scan when no index exists; on tables of this size this consistently breaches statement timeout limits.
- Evidence: `_CREATE_DDL` in `src/load_supabase.py` (lines 60–160) defines `fact_prices` with a `PRIMARY KEY (date_key, store_key, file_key, category_key, product_key)`. A composite PRIMARY KEY *does* create a B-tree index on that exact key tuple, but the leading column is `date_key` — which means a query `WHERE date_key = X` can use the PK index only if the planner chooses to. However, for `SELECT DISTINCT date_key FROM fact_prices`, the planner may not use the PK index efficiently for a DISTINCT over 63 unique values in 82M rows without an additional single-column index, since the PK is a 5-column composite. For `get_settlements_for_date`, a PK index scan filtered to a specific `date_key` is possible, but the planner must still scan all rows in the PK sub-range for that `date_key`. An explicit `(date_key, store_key)` index exposes only the two needed columns, enabling an index-only scan.

**Revised root cause:**
The `fact_prices` table **does** have a PRIMARY KEY on `(date_key, store_key, file_key, category_key, product_key)`. This index is sufficient for `get_settlements_for_date` theoretically (PK starts with `date_key, store_key`). However, on Supabase free tier, even a PK index scan over a single `date_key` partition (~1.1–1.5M rows) may be slow enough to breach the 3s timeout when combined with the `DISTINCT` aggregation and JOIN — especially given Supabase shared-compute resource contention.

For `get_available_dates()` (`SELECT DISTINCT date_key FROM fact_prices ORDER BY date_key DESC`): PostgreSQL can use the PK index for this query (index skip scan for DISTINCT on leading column). If it is still timing out, it is either due to shared-compute contention on the free tier or because the planner chooses a sequential scan. An explicit single-column `(date_key)` index — smaller and cheaper to scan — and an explicit single-column index on `store_key` for the JOIN column in `get_settlements_for_date` will give the planner cleaner options.

**Evidence → Implication:**
- `fact_prices` PK: `(date_key, store_key, file_key, category_key, product_key)` — implication: PK may theoretically allow `date_key` and `(date_key, store_key)` lookups, but the composite index over 5 columns is much larger on disk and slower to scan than a targeted 1- or 2-column index on a hot access pattern. On a free-tier shared cluster with millisecond-level resource contention, this difference can tip a 2.8s query over the 3s limit.
- Console error `canceling statement due to statement timeout` — implication: the queries are running but not completing in time. They are not failing due to permission or function-not-found issues.
- Console error HTTP 500 on both RPCs — implication: the functions exist and are callable (otherwise they would return 404 or 406).
- Console error HTTP 404 (unidentified URL) — implication: a static resource or API endpoint is missing. The `<link rel="icon" href="data:,">` in `index.html` suppresses the favicon for most environments but is not universally reliable.

**Pattern: Favicon 404 workaround**
- In Vite projects, placing a `favicon.ico` or `favicon.svg` in `public/` causes Vite to copy it to `dist/` and serve it at `/favicon.ico` or `/favicon.svg`, completely eliminating the 404.
- The existing `<link rel="icon" href="data:,">` approach works in most browsers but not all. The safest cross-browser solution is a physical file.

---

## External Benchmarking

**1. PostgreSQL index strategies for star-schema fact tables (PostgreSQL documentation and community patterns):**
- Industry practice for OLAP-style queries on large fact tables is to create targeted indexes on the most selective filter columns. For a date-range or date-equality access pattern, a B-tree index on `date_key` is the standard recommendation.
- PostgreSQL's "index-only scan" (IOS) feature (available since PostgreSQL 9.2) allows queries that only reference indexed columns to be served entirely from the index, with no heap access. For `SELECT DISTINCT date_key FROM fact_prices`, a single-column index on `date_key` enables an IOS that reads at most 63 distinct leaf-page entries from the index, rather than 82M heap rows.
- **Takeaway:** Add `CREATE INDEX IF NOT EXISTS idx_fact_prices_date_key ON fact_prices(date_key)` to enable IOS for `get_available_dates()`.
- **Applicability:** Directly applicable; no adaptation required.

**2. Supabase free-tier statement timeout mitigation (Supabase community and GitHub discussions):**
- The Supabase free tier enforces a statement timeout (commonly cited as 3 seconds). Users with large tables and unbounded sequential scans routinely hit this limit. The recommended mitigation is to add appropriate indexes before deploying RPC functions that query large tables.
- Some community members have also worked around the timeout by caching query results in a materialized view or a small summary table (e.g., a `dim_available_dates` table updated by the ETL sync). This eliminates the scan entirely at query time.
- **Takeaway for this request:** The index approach is preferred (lower complexity, no additional schema object). A materialized summary table is a valid secondary mitigation if indexes alone are still insufficient.
- **Applicability:** Index approach adopted as primary. Summary-table approach documented as a risk mitigation fallback.

**3. Supabase `get_available_dates` RPC timeout — open-source issue patterns:**
- GitHub issues on `supabase/supabase` and `supabase-community` frequently document timeout errors when calling RPCs over large tables without indexes. The consensus fix is: (a) index the filter columns, (b) simplify the SQL in the function (no unnecessary subqueries), (c) on the free tier, consider `SET LOCAL statement_timeout = '30s'` inside the function body if the function can be executed with sufficient privilege (not applicable for anon role).
- **Takeaway:** Options (a) and (b) are applicable. Option (c) requires elevated role and is out of scope.
- **Adoption:** Index approach (a) adopted. Function SQL is already minimal; no change needed.

---

## Minimal Spikes and Experiments

**Spike: Verify that fact_prices has a PK index and assess whether it covers the RPC queries**
- Hypothesis: the existing 5-column PK index on `fact_prices` should allow PostgreSQL to resolve `get_available_dates()` and `get_settlements_for_date()` efficiently enough to avoid timeout.
- Approach: Reviewed `_CREATE_DDL` in `src/load_supabase.py` (lines 60–160); confirmed `PRIMARY KEY (date_key, store_key, file_key, category_key, product_key)` is defined. Cross-referenced PostgreSQL planner behaviour for `SELECT DISTINCT` on leading column of multi-column PK.
- Outcome: A 5-column composite PK index can support `SELECT DISTINCT date_key` (index skip scan) and `WHERE date_key = X` lookups in theory. However, the index itself is much larger (stores 5 column values per entry × 82M rows ≈ tens of GB on disk), and on a free-tier shared cluster with memory pressure, each index page touch involves I/O. The timeout is consistent with this scenario on the Supabase free tier.
- Conclusion: The PK index is insufficient to reliably beat the statement timeout on free-tier shared compute. Targeted single- and two-column indexes on the hot columns are required.

**Spike: Identify source of 404 error**
- Hypothesis: The 404 is from a favicon.ico request not fully suppressed by the `data:,` tag.
- Approach: Reviewed `react-app/index.html` (confirmed `<link rel="icon" href="data:,">` is present). Searched `react-app/` for any `favicon.ico` or physical icon file — none found. Checked that no Supabase RPC or table is called with a URL that would produce 404 (all calls use known-existing endpoints, which return 500 not 404). Checked Netlify configuration for any redirect/proxy rules that could cause a 404.
- Outcome: No physical favicon file exists in `react-app/public/` or `react-app/dist/`. The `data:,` suppression is not 100% reliable across all browsers and browser versions.
- Conclusion: Adding a minimal `favicon.ico` (or `favicon.svg`) to `react-app/public/` will eliminate the 404 definitively. This is the highest-probability fix.

---

## AI Copilot Suggestions

**Observation 1 — Composite PK as a substitute for targeted indexes (design quality)**
The 5-column composite PRIMARY KEY on `fact_prices` was chosen for data integrity (no duplicate rows). Using it as the sole access structure for analytical queries is a classic OLTP-vs-OLAP mismatch. On a table of this size, targeted single- and two-column covering indexes for the specific analytical access patterns (date-only, date+store) should always be added alongside the PK.
- Suggestion: Add two targeted indexes: `idx_fact_prices_date_key ON fact_prices(date_key)` and `idx_fact_prices_date_store ON fact_prices(date_key, store_key)`. The second index (composite) covers both the WHERE predicate and the JOIN column of `get_settlements_for_date`, enabling an index-only scan.

**Observation 2 — RPC functions scanning the heap when an index-only scan is possible (implementation risk)**
`get_settlements_for_date` performs a JOIN between `fact_prices` and `dim_store`. Even with a `(date_key, store_key)` index on `fact_prices`, if the heap is not "clean" (visibility map not up to date), PostgreSQL may fall back to a heap fetch. This is unlikely to be an issue on Supabase's managed Postgres (autovacuum runs regularly), but worth monitoring.
- Suggestion: After adding indexes, verify via `EXPLAIN ANALYZE` in the Supabase SQL editor that both RPC functions use index-only scans. If not, run `VACUUM ANALYZE fact_prices` once to update the visibility map. Add a note to the operator runbook.

**Observation 3 — Scope is appropriately narrow; risk of under-scoping the timeout problem (scope note)**
The request scopes the fix to adding indexes and resolving the 404. This is correct and minimal. However, if the Supabase free tier's compute is severely constrained (e.g., other tenants causing memory pressure), even indexed scans may occasionally time out. The request does not include any fallback mechanism in the RPC functions (e.g., `SET LOCAL statement_timeout = 0`). This is acceptable as a first fix — but if timeouts persist post-index-creation, the next escalation should be a pre-computed summary table for available dates.
- Suggestion: Document the summary-table fallback as a known risk in the implementation notes. Do not implement it now (over-engineering for a likely-unnecessary scenario).

**Observation 4 — Multiple `get_settlements_for_date` calls per page load (maintainability)**
The console errors show `get_settlements_for_date` returning 500 twice. This is because Report 1 calls `fetchSettlementsForDate` in a `useEffect` that fires when `selectedDate` or `dimensions` changes. On first load, both values arrive (dimensions resolved, selectedDate set), potentially triggering one call, and any `dimensions` re-reference could trigger a second. After indexing, this double-call should complete within timeout, but it is still two round-trips per date change.
- Suggestion: Consider memoizing the settlement list per `dateKey` in `dataService.js` so repeated date-change events do not re-fetch the same RPC result. This is a performance improvement, not a correctness fix — do not implement in this request, but document as a follow-up.

---

## Testing

- T1 — Index existence check: After running `load_supabase.py`, query the Supabase SQL editor for `SELECT indexname FROM pg_indexes WHERE tablename='fact_prices'`. Expected outcome: rows named `idx_fact_prices_date_key` and `idx_fact_prices_date_store` (or equivalent names defined in the DDL) are present.

- T2 — `get_available_dates` no-timeout: Call `supabase.rpc('get_available_dates')` from the Supabase SQL editor or a test script after indexing. Expected outcome: query completes in < 3 seconds and returns a list of integer `date_key` values matching the distinct dates in `fact_prices`.

- T3 — `get_settlements_for_date` no-timeout: Call `get_settlements_for_date(<valid_date_key>)` from the Supabase SQL editor after indexing. Expected outcome: query completes in < 3 seconds and returns a list of integer `settlement_key` values.

- T4 — Date selector correctness: Open the deployed React app. Expected outcome: the date selector dropdown contains only dates that have `fact_prices` rows in Supabase (cross-check by counting distinct dates in `fact_prices` via SQL).

- T5 — No 500 console errors: Open the React app in a browser with DevTools open. Expected outcome: no HTTP 500 errors appear in the Network or Console tab on initial load.

- T6 — No 404 console errors: Open the React app. Expected outcome: no HTTP 404 errors appear in the Console or Network tab.

- T7 — Idempotent re-run of `load_supabase.py`: Run the sync script (menu option 4) a second time. Expected outcome: exits with code 0, no errors, `CREATE INDEX IF NOT EXISTS` is a no-op.

- T8 — Existing test suite passes: Run `pytest` from the project root. Expected outcome: all tests in `tests/` pass (exit code 0).

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is technically sound and well-scoped. Adding B-tree indexes to `fact_prices` is the correct, minimal intervention for resolving both the timeout and the resulting incorrect date display. The five-column composite PK already provides referential integrity; targeted single- and two-column indexes on the analytical access patterns are the standard complementary pattern for star-schema fact tables. The risk of over-engineering (e.g., partitioning, materialized views, Supabase Edge Functions) is avoided by keeping the fix in the DDL layer.

- The `CREATE INDEX IF NOT EXISTS` idiom is idempotent and safe for inclusion in every `load_supabase.py` run.
- The initial one-time cost of building indexes on 82M rows must be communicated to the operator — this may take minutes and will temporarily lock no existing reads (PostgreSQL's `CREATE INDEX` builds indexes concurrently by default in many configurations, though Supabase's DDL execution may not expose `CONCURRENTLY`).
- Architecture risk: Supabase's shared free-tier compute remains a single point of failure. If the indexes are added and timeouts persist, escalation to a paid tier or a pre-computed summary table is required.

### Product Owner

The business value is high: users currently see the wrong set of available dates (all dates, not just fact-populated dates), and Report 1's settlement dropdown shows all settlements rather than only those with data on the selected date. Correcting both is a correctness defect, not a feature. The success criteria are measurable and testable. The scope is appropriately narrow — only the database layer and static asset (favicon) are touched.

- Acceptance criteria completeness: SC-1 through SC-6 are clear and testable. SC-4 (code change) and SC-5 (idempotency) validate the implementation; SC-1 through SC-3 validate the user-visible outcome.
- No new user-facing features are introduced; this is a pure defect fix.

### User

From a user perspective, the current broken state is severe: the date selector may show dates with no data, leading to empty report views with no explanation. The fallback behavior (showing all settlements) is confusing because it implies data exists for all cities when it does not for the selected date. Fixing the RPC errors directly restores correct, trustworthy filtering.

- Loading time for date/settlement resolution should improve significantly after indexing — previously the app waited for a timeout (several seconds) before falling back; after the fix, the RPC should complete in < 1 second.
- No UI changes are required; the fix is transparent to the user except for the correct date list appearing and faster load.

### Security Officer

No security surface is added or changed. The two indexes are on non-sensitive columns (`date_key`, `store_key`) of the `fact_prices` table. The `GRANT EXECUTE TO anon` already in place is appropriate (these are read-only filter functions). The 404 fix (favicon file) adds only a static binary asset — no new API surface.

- Adding indexes to a public-read table does not expose additional data; indexes only affect query performance.
- The `CREATE INDEX` DDL runs via the `DATABASE_URL` PostgreSQL connection (service role), which already has full schema access. No privilege escalation occurs.

### Data Governance Officer

The fix is a pure performance and correctness improvement. No data schema changes (column additions, type changes, constraint modifications) are made to `fact_prices`. No data is deleted, migrated, or reclassified. The addition of indexes does not alter data lineage.

- The `context.md` update task should note that `fact_prices` now has two additional indexes.
- No compliance impact: all data processed remains publicly available Bulgarian government retail price data with no PII.
