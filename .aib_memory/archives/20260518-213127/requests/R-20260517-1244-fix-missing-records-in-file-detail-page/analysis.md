# Analysis: R-20260517-1244 — Fix missing records in Файлове file detail page

## Executive Summary

- **Request ID:** R-20260517-1244

- **Request title:** Fix missing records in Файлове file detail page

- **High-level purpose:** The `FileRowsPanel` component in the Файлове page loads all fact rows for a selected file using a single Supabase PostgREST `.range(0, count-1)` call. Hosted Supabase PostgREST enforces a server-side `max_rows` cap (default 1 000) that silently truncates the response regardless of the explicit `Range` header. Files with more than 1 000 rows appear to load completely (because `totalCount` is accurate), but the displayed rows stop at 1 000. The fix replaces the single oversized range call with a multi-page pagination loop using the already-defined `SUPABASE_PAGE_SIZE = 1 000` constant — the same pattern used by `fetchAllRows` for dimension tables.

- **Affected files:** `react-app/src/lib/dataService.js`, `react-app/src/components/FileRowsPanel.jsx`, `react-app/src/components/FileRowsPanel.test.jsx`, `.aib_memory/context.md`.

- **`request.md` updates during this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` sections were written. No `## Questions & Decisions` were raised (all decision points resolved autonomously at severity ≤ 2).

---

## Domain Knowledge Essentials

- **Факт-таблица (Fact table):** `fact_prices_lookback` — the sole Supabase fact table; holds one row per (date, store, file, category, product) combination for the current date D, plus lookback price columns for D-1 and D-2. Truncated and reinserted on every ETL sync run.

- **Dim_file:** Dimension table storing metadata (file name, submission date `zip_date`) for every source CSV file ever received. `fact_prices_lookback` has a single `file_key` foreign key referencing the D-day source file for each row. D-1 and D-2 prices are stored as columns on D rows — there are no `file_key_day1` / `file_key_day2` columns.

- **Файлове page (Files page):** The fifth navigation page. Shows source CSV files for the currently selected date. Clicking a file row opens `FileRowsPanel` with the full record drill-down.

- **FileRowsPanel:** React component that loads and displays a paginated, sortable, filterable table of enriched `fact_prices_lookback` rows for one file. Pagination, sort, and filter are all client-side after the full row set is loaded.

- **Impacted roles:** End users of the React app (retail-price analysts, data engineers reviewing file-level data quality).

- **Business process touched:** File-level data quality review — verifying that all records from a submitted source file are correctly ingested and visible in the system.

- **KPI / correctness indicator:** Row count displayed in `FileRowsPanel` must equal the "Записи" count shown in the file summary table on `FileDetailPage`.

---

## Technical Knowledge & Terms

- **PostgREST `max_rows`:** A server-side configuration parameter in PostgREST (the REST layer that Supabase exposes over PostgreSQL) that hard-caps the number of rows returned in a single API response. Hosted Supabase defaults this to 1 000. Even with an explicit `Range: 0-4999` HTTP header, the server returns at most `max_rows` rows (rows 0–999) and sets `Content-Range: 0-999/5000`. The client receives 1 000 rows, not 5 000.

- **Supabase JS `.range(from, to)`:** Generates the PostgREST `Range` HTTP header. Does NOT bypass `max_rows`; it only instructs PostgREST which slice of the result set to return, subject to the cap.

- **`{ count: 'exact', head: true }` query:** A HEAD-only HTTP request that returns zero rows but includes a `Content-Range` header reporting the total matching row count. Unaffected by `max_rows`. Used correctly in `fetchFileRows` for the count pass.

- **`SUPABASE_PAGE_SIZE = 1 000`:** Module constant in `dataService.js` matching the PostgREST default cap; used by `fetchAllRows` (dimension table loader) and the fallback report queries to paginate correctly.

- **Two-pass strategy:** `FileRowsPanel` useEffect: Pass 1 fetches one row to get `totalCount`; Pass 2 calls `fetchFileRows(fileKey, dims, 0, count)`. Pass 2 is the bug site: it issues `.range(0, count-1)` expecting all rows, but receives at most 1 000.

- **`fetchAllRows`:** Private helper in `dataService.js` that loops `.range(from, to)` in `SUPABASE_PAGE_SIZE` chunks until `data.length < SUPABASE_PAGE_SIZE`. Correct pagination pattern; already used for dimension loading but not yet for file-row loading.

- **`fetchFileRows`:** Exported function in `dataService.js` designed for server-side pagination (`pageIndex`, `pageSize`). Used exclusively by `FileRowsPanel`. Makes three round-trips per call: HEAD count, SELECT page, dim_product `.in()`.

- **Technologies involved:** React 18, Vite, @supabase/supabase-js v2, PostgREST (Supabase-hosted), Vitest / @testing-library/react.

- **Files read during this analysis:**
  - `react-app/src/components/FileRowsPanel.jsx`
  - `react-app/src/lib/dataService.js`
  - `react-app/src/components/FileDetailPage.jsx`
  - `react-app/src/components/FileRowsPanel.test.jsx`
  - `react-app/src/lib/supabase.js`
  - `react-app/src/lib/dataService.test.js`
  - `src/load_supabase.py` (DDL section for `fact_prices_lookback` table and indexes)
  - `data/schema/dim_file.csv` (partial, for schema confirmation)
  - `.aib_memory/context.md`
  - `.aib_memory/requests_register.md`

---

## Research Results

**Pattern scan:**

- **Prior art in the same codebase:** `fetchAllRows` in `dataService.js` (used for all dimension tables) already implements the correct multi-page loop. The fallback functions `fetchReport1Fallback` and `fetchReport2Fallback` each implement the same loop independently. `fetchReport3Fallback` adds a `REPORT3_ROW_CAP` safety limit (5 000 rows) to avoid memory exhaustion on large categories. The pagination pattern is well-established in the codebase.

- **Bug reproduction evidence:** `FileRowsPanel.jsx` contains a `console.warn` stating "PostgREST max_rows cap may have applied" when `allRows.length < count`. This was written as a defensive check when the two-pass approach was introduced in R-20260516-1313, confirming the risk was known but the fix was deferred.

- **Index gap:** `fact_prices_lookback` has composite indexes on `(date_key)`, `(date_key, store_key)`, `(date_key, category_key)`, and `(date_key, store_key, category_key)`. There is no index on `(file_key)`. The `.eq('file_key', fileKey)` query issued by `fetchFileRows` therefore requires a full sequential scan on a table with ~82 million rows.

- **Evidence log:**
  - `console.warn("...PostgREST max_rows cap may have applied")` in `FileRowsPanel.jsx` → developer acknowledged the cap risk at implementation time.
  - `SUPABASE_PAGE_SIZE = 1 000` constant in `dataService.js` → the correct page size is already standardized and ready to use.
  - `fetchAllRows` in `dataService.js` → the exact multi-page loop pattern exists in the codebase.
  - No `file_key` index in `load_supabase.py` DDL → each page fetch is a sequential scan; latency risk increases with pagination depth.

---

## External Benchmarking

- **PostgREST `max-rows` (PostgREST official documentation and Supabase platform docs):** PostgREST enforces `max-rows` as a hard cap per response regardless of the `Range` header. The documented client-side remedy for fetching more rows than `max-rows` is to issue multiple paginated requests using non-overlapping `Range` offsets until a response returns fewer rows than the page size. Supabase's own "Fetching all rows" guide documents this exact loop pattern and warns that the default row limit applies to all table reads.
  - Key takeaway: The existing `fetchAllRows` pattern is already the documented best practice. The fix mechanically applies this pattern to the file-row loading path.
  - Applicability: Full adoption; no adaptation needed.

- **Supabase JS v2 `.range()` semantics (@supabase/supabase-js documentation and community Q&A):** `.range(from, to)` sets the `Range` HTTP header but does not override `max_rows`. A `.range(0, 9 999)` call on a PostgREST instance with `max_rows = 1 000` returns exactly 1 000 rows and sets `Content-Range: 0-999/N`. The `data` array has 1 000 items; `count` returns N (total matching rows from the header). This behaviour is consistent across all Supabase JS v2 releases. Relying on `.range(0, count-1)` for bulk reads when `count > max_rows` is architecturally incorrect.
  - Key takeaway: Confirms the root cause. The correct architecture is a pagination loop, not a single large range request.
  - Applicability: Confirms diagnosis; supports the fix direction.

---

## Minimal Spikes and Experiments

**Spike: Verify that `{ count: 'exact', head: true }` is unaffected by `max_rows`**
- Hypothesis: The HEAD-only count query returns the true total count even when `max_rows` would truncate a data-fetching query for the same filter.
- Approach: Reviewed PostgREST source behaviour and Supabase documentation. A HEAD request with `Prefer: count=exact` does not transfer data rows; PostgREST executes a `COUNT(*)` internally and returns the result via the `Content-Range` header. `max_rows` applies only to data-row responses.
- Outcome: Confirmed. `totalCount` from Pass 1 is always accurate. The inconsistency (accurate count, truncated rows) is by design in PostgREST.
- Conclusion: Pass 1 in `FileRowsPanel` is correct and needs no change. Only Pass 2 needs the multi-page fix.

**Spike: Check whether a `file_key` index exists in `load_supabase.py` DDL**
- Hypothesis: There may be an index on `fact_prices_lookback(file_key)` enabling efficient per-file queries.
- Approach: Searched `src/load_supabase.py` for `file_key` in index DDL statements using grep.
- Outcome: No `file_key` index found. Existing indexes cover `(date_key)`, `(date_key, store_key)`, `(date_key, category_key)`, `(date_key, store_key, category_key)`.
- Conclusion: Queries filtering only by `file_key` are expensive on a large table. The fix will issue multiple such queries per file load. A `file_key` index would improve performance but is out of scope for this request.

---

## AI Copilot Suggestions

> **This section is a reasoning artifact only. `implement` MUST NOT read or act on it.**

- **Observation 1 — Design smell: `fetchFileRows` is overloaded for two conflicting purposes.**
  The function was designed for server-side pagination (`pageIndex`, `pageSize` parameters) but is being used as a full-set bulk loader by passing `count` as `pageSize`. These are semantically incompatible; the `console.warn` safety net is evidence that the design intent broke down at the call site.
  - Suggestion: Introduce a clearly named function dedicated to bulk loading (e.g., `fetchAllFileRows`) and leave `fetchFileRows` for server-side pagination. This makes the intent explicit and prevents future developers from making the same wrong assumption.

- **Observation 2 — Performance risk: redundant product lookups per page if `fetchFileRows` is called in a loop.**
  `fetchFileRows` issues a `dim_product .in()` query per invocation. If the multi-page loop calls `fetchFileRows` N times, there will be N product lookups. For a 5 000-row file (5 pages) this means 5 round-trips to `dim_product` instead of 1.
  - Suggestion: Accumulate all raw fact rows across all pages first, then issue a single consolidated product lookup for the union of unique `product_key` values. This is the more efficient design and avoids rate-limit pressure on the Supabase free tier.

- **Observation 3 — Missing `file_key` index is a latent performance problem that this fix makes more visible.**
  Every `fetchFileRows` call (now multiple per file load) performs a sequential scan on `fact_prices_lookback` (~82 million rows). For files with many rows, each page fetch can take several seconds.
  - Suggestion: Consider adding `CREATE INDEX IF NOT EXISTS idx_fact_prices_lookback_file_key ON fact_prices_lookback(file_key)` to `load_supabase.py` as a low-cost follow-up. It is a one-line DDL change that makes all per-file queries O(log N).

- **Observation 4 — Scope is appropriately narrow and low-risk.**
  The request correctly excludes UI, pagination controls, sort, filter, modal, and ETL changes. The risk of regression is low. The scope is well-calibrated to the stated goal.

- **Observation 5 — Test gap for multi-page scenario must be closed.**
  All existing tests in `FileRowsPanel.test.jsx` assume a single `fetchFileRows` call resolves the entire row set. The multi-page scenario (multiple calls each returning exactly `SUPABASE_PAGE_SIZE` rows except the last) is untested. This gap should be closed as part of the fix to prevent silent future regressions.

---

## Testing

- **T1 — Single-page load (≤ 1 000 rows): no regression.** Load a file with 500 rows. Expected: `FileRowsPanel` displays 500 rows; no console.warn emitted; `totalCount` and displayed row count match.

- **T2 — Multi-page load (> 1 000 rows): full set returned.** Load a file with 2 500 rows (mocked as 3 pages: 1 000 + 1 000 + 500). Expected: `FileRowsPanel` displays 2 500 rows; no console.warn emitted; displayed row count equals `totalCount = 2 500`.

- **T3 — Edge: exactly `SUPABASE_PAGE_SIZE` rows.** Load a file with exactly 1 000 rows (first page returns 1 000 rows; second page returns 0 rows). Expected: `FileRowsPanel` displays 1 000 rows; no console.warn; count matches.

- **T4 — Empty file (0 rows): no regression.** Load a file with 0 rows. Expected: `FileRowsPanel` shows empty state message; no error; no console.warn.

- **T5 — Error state propagation on page N > 1.** A Supabase error is thrown on page 2 of a multi-page load. Expected: `FileRowsPanel` shows the error message; loading indicator clears; no partial rows displayed.

- **T6 — Product lookup batched once per file load.** For a 2-page file, `dim_product .in()` is called exactly once with all unique product keys from both pages combined.

- **T7 — Existing passing tests remain green.** `npm test` from `react-app/` exits 0 after the change.

- **T8 — Build passes.** `npm run build` from `react-app/` exits 0.

- **T9 — Idempotency: re-loading the same file.** Close and re-click the same file row in the UI. Expected: panel reloads all rows correctly; no stale data from the previous load.

> T1–T8 are automatable as unit tests or build assertions. T9 requires manual verification; see UAT_scenarios.md — UAT-01.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The root cause is a "assume the API is unlimited" design error. The two-pass strategy in `FileRowsPanel` was architecturally sound when scoped to server-side pagination but was repurposed for bulk loading in R-20260516-1313 without adapting the data-fetch strategy. The `fetchAllRows` utility in the same module already encodes the correct pattern; not reusing it is a DRY violation that directly caused this defect. The missing `file_key` index compounds the problem: pagination will issue multiple sequential scans on an 82-million-row table. The fix scope is minimal and appropriate; the index gap merits a follow-up task.

Findings:
- `fetchFileRows` (server-side pagination API) and `FileRowsPanel` (bulk client-side load) have conflicting semantic contracts that should be resolved by interface clarity.
- `fetchAllRows` exists as the correct abstraction; its pattern should be applied, not reinvented.
- The `file_key` index gap is a pre-existing performance risk that becomes more visible after the fix.
- The `console.warn` was the correct defensive signal; it should be retired once the fix is confirmed working.

### Product Owner

The bug creates a visible data-quality concern: the summary table shows the correct count but the drill-down shows fewer rows. This undermines confidence in the tool's accuracy, which is one of its primary purposes. The fix is high-priority with low risk (no API changes, no schema changes, no UI changes). Acceptance is straightforward: for any large file, confirm that the row count in the panel matches the count shown in the summary list.

Findings:
- Impact on user trust is significant; the discrepancy looks like a data-loss bug even though the ETL is correct.
- Fix is low-risk, high-value, and immediately observable.
- SC-1 (panel count equals summary count) is directly testable without any infrastructure changes.
- The D-1 / D-2 file drill-down always showing 0 rows is a separate schema-design constraint — not in scope here but may generate follow-up questions from users.

### User

When I click a large file and see 1 000 rows even though the list shows "3 000 записи", I assume something is broken or data is missing. I cannot distinguish a truncated load from a real data gap. After the fix the row count in the panel will match the summary, which is what I expect. A slightly slower load for large files is acceptable if it means seeing complete data.

Findings:
- The visible count discrepancy is confusing and erodes trust in the product.
- Slightly slower load for large files is a fair tradeoff for correctness.
- The fix is transparent: no UI changes, no new interactions to learn.
- D-1/D-2 file drill-down showing 0 rows may confuse users browsing non-current dates; out of scope here.

### Security Officer

No security-relevant changes are introduced. The fix modifies only the client-side pagination loop. No new Supabase tables, RPC functions, env variables, or credentials handling is involved. The multi-page loop makes additional Supabase requests per file load but uses the same anon key and the same RLS context as the current path. No new data is exposed beyond what was already accessible.

Findings:
- No authentication or authorization model change.
- No new credential handling.
- No additional data exposure: file rows are already queryable; the fix retrieves all of them instead of the first 1 000.
- Marginally higher Supabase request rate for large files is within acceptable bounds and consistent with existing paginated dimension fetches.

### Data Governance Officer

The fix has no impact on data lineage, retention, classification, or compliance. `fact_prices_lookback` is read-only from the React app's perspective; the ETL pipeline governs what is stored. Displaying all rows in the drill-down does not change what is stored. The `dim_file` table correctly records source-file provenance; this is unchanged. The fix improves data completeness visibility without introducing new data flows or storage changes.

Findings:
- No lineage impact: more rows from an existing table are read; no new sources or sinks.
- No retention impact: no data is stored or deleted by the fix.
- No classification impact: retail price data is already public via the same app.
- Compliance: all data is from the Bulgarian government open-data portal; no PII is involved.
