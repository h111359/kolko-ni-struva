## Executive Summary

- **Request ID:** R-20260430-1505

- **Title:** Extend lookback days, fix Report1, resolve settlements

- **High-level purpose (re-scoped):** Originally aimed at (1) extending `build_lookback_table()` to emit 3 date rows via ETL, (2) fixing a stale Netlify bundle causing Report 1 to crash, and (3) enriching `dim_settlement` via `ek_raion.json`. A scope amendment was applied via `input.md`: ETL and database are frozen; the 3-date selector is now achieved by a frontend-only reconstruction of D-1 and D-2 price views from the horizontal lookback columns already present in `fact_prices_lookback`. Settlement enrichment is dropped from scope.

- **Revised approach:** `fact_prices_lookback` already stores D-1 and D-2 prices horizontally (`retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`). The React app is changed to expose all 3 `dim_date` rows in the date selector and, when a lookback date is selected, to query the D row set using the appropriate lookback columns then normalize before price calculation.

- **Report 1 fix:** Unchanged from previous analysis — a Netlify rebuild and redeploy is required to eliminate the stale `fact_prices` reference in the deployed bundle.

- **Settlement enrichment:** Dropped entirely per user amendment. The 25 unknown settlement entries remain as-is. A future dedicated request is recommended.

- **`request.md` sections updated in this run:** `## Goal`, `## Background`, `## Scope`, `## Out of scope`, `## Constraints`, `## Success criteria`, `## Assumptions` (A1–A6, replaces A1–A7), `## Plan` (Tasks 1–5, replaces Tasks 1–7), `## Documentation`, `## Questions & Decisions` (old Q001/Q002 removed; new Q001 added), `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.


---

## Domain Knowledge Essentials

**D, D-1, D-2** — Latest processed fact date (D) and the two preceding dates. The React date selector should offer all three for price comparison.

**Lookback fact table (`fact_prices_lookback`)** — Supabase fact table with 11 columns: `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price, retail_price_day1, promo_price_day1, retail_price_day2, promo_price_day2`. Contains only D's rows; D-1 and D-2 prices are stored as horizontal columns within each D row.

**Virtual date view** — Client-side reconstruction of D-1 or D-2 price data by reading the lookback columns from D's rows, without requiring separate DB rows for D-1 or D-2. The React app creates 3 selectable dates from a single physical date's data.

**`get_available_dates()` RPC** — PostgreSQL function in Supabase returning `DISTINCT date_key FROM fact_prices_lookback`. With the DB frozen, this continues to return exactly 1 value (D). The app uses it only to identify which `dim_date` row is "D" and derive the lookback offset map.

**`dim_date`** — Dimension table pruned by `prune_dim_date()` in `load_supabase.py` to exactly 3 rows (D, D-1, D-2 sorted descending). These 3 rows are the basis for the date selector after the frontend fix.

**lookbackColumnMap** — A new JS `Map<date_key, 'current'|'day1'|'day2'>` computed in `fetchDimensions()` from the 3 `dim_date` rows and the RPC-identified current date_key. Routes each date selection to the correct price columns.

**normalizeRow(row, offset)** — New private helper in `dataService.js`. Remaps `retail_price_day1 → retail_price` and `promo_price_day1 → promo_price` (or day2 equivalent) so the existing `calculatePrice()` function works without modification.

**calculatePrice(row)** — Existing pure function: `min(retail_price, promo_price)` if promo is non-null/non-zero; else `retail_price`. No changes to this function.

**Impacted roles/personas:** Public end users (date selector, Report 1 fix); data engineer (no workflow change — ETL frozen).

**Business processes touched:** Date-based price comparison; Report 1 category price chart access.


---

## Technical Knowledge & Terms

**`fetchDimensions()` (current):** Calls `get_available_dates()` RPC and filters `dim_date` rows to only the RPC-returned date_key (D). Result: only 1 date in the selector.

**`fetchDimensions()` (post-fix):** Uses all `dim_date` rows (all 3). Retains the RPC call to identify `currentDateKey` (D) and build `lookbackColumnMap`. Adds `currentDateKey` and `lookbackColumnMap` to the returned `_dims` object.

**`fetchSettlementsForDate(dateKey, dims)` (post-fix):** When `dims.lookbackColumnMap.get(dateKey)` is `'day1'` or `'day2'`, calls the RPC with `dims.currentDateKey` instead of `dateKey` (since all fact data is under D's key).

**`fetchReport1/2/3` (post-fix):** Resolve price offset from `dims.lookbackColumnMap`; if lookback, use `dims.currentDateKey` as query key and select appropriate columns (`retail_price_day1,promo_price_day1` or day2 variant); normalize rows via `normalizeRow(row, offset)` before aggregation or return.

**Supabase PostgREST `.select(columns)` pattern:** Column list string determines which columns are fetched. For lookback dates, only the 2 relevant price columns are selected (not all 6). This minimises network transfer.

**Report 2 / Report 3 "Дата" column:** Rendered via `dimensions.dates.find(d => d.date_key === selectedDate)?.date`. After the fix, `dims.dates` includes all 3 date rows; this expression correctly returns D-1 or D-2's date string when those dates are selected — no component changes needed.

**Runtime constraints:**
- `fact_prices_lookback` row count unchanged (~1.1–1.5 M rows); no performance delta.
- `dim_date` has 3 rows; all 3 used for date selector; no RPC filtering.
- Supabase query payload for lookback reports: 2 price columns (not 4 or 6); bandwidth unchanged.

**Non-functional attributes:**
- `_dims` is module-cached; `currentDateKey` and `lookbackColumnMap` must be written before caching.
- React app remains client-only; no serverless functions or DB changes.
- Python 3.9+ ETL scripts: not touched.

**Files read:**
- `react-app/src/lib/dataService.js` — confirmed `filteredDates` RPC filter, SELECT column strings, `calculatePrice()` implementation.
- `react-app/src/components/Report2.jsx` — confirmed "Дата" column uses `dimensions.dates.find(...)`.
- `react-app/src/App.jsx` — confirmed `selectedDate` init from `dims.dates[0].date_key`, date selector rendering.
- `react-app/src/App.test.jsx` — confirmed `makeStubDims()` shape needing `currentDateKey`/`lookbackColumnMap`.
- `.aib_memory/context.md` — confirmed `dim_date` 3-row prune, RPC function DDL intent, lookback column schema.


---

## Research Results

**Pattern: client-side data pivot from horizontal fact columns**

Reading price data from horizontal columns (`day1`, `day2`) and presenting them as if they were separate rows is a client-side pivot (wide-to-tall). This pattern is common in analytical frontends where widening a fact table (adding time-dimension columns) is cheaper than multiplying row count. Libraries such as React Table and AG Grid expose column-accessor functions for exactly this use case. The key insight from these patterns: normalize at the service boundary (`dataService.js`), not in render logic, to keep component code free of price-column branching.

**Pattern: Supabase query column selection for multi-offset pivoting**

PostgREST's `.select(columns)` string controls which columns are returned. Selecting only the 2 relevant price columns per offset (rather than all 6) follows the minimal-transfer principle and avoids over-fetching. This is consistent with the existing `fetchReport1` code which already selects a minimal column set.

**Pattern: RPC-as-source-of-truth for active date**

The `get_available_dates()` RPC returns only fact-present date_keys. Using it to identify D (even though we show all 3 `dim_date` rows) preserves the correctness contract: if Supabase has no fact data, `currentDateKey` is null and all reports degrade gracefully. This aligns with the existing fallback pattern already present in `fetchDimensions()`.

**Prior request pattern scan:**

R-20260422-0902 (Fix date filter) established the RPC-filtered date selector. R-20260430-0825 froze `fact_prices_lookback` as single-date with horizontal lookback columns. The current request completes the "horizontal" design intent by teaching the frontend to use those columns.


---

## External Benchmarking

**Benchmark 1 — Client-side column normalization in analytical React apps**

Industry practice (React Query, TanStack Query patterns) normalizes fetched data at the query/service layer before exposing to component state. Remapping `retail_price_day1 → retail_price` in the service function keeps the component layer agnostic to the physical column schema. The component and the existing `calculatePrice()` function remain unchanged — this is the recommended approach.

- Key takeaway: Normalize at service boundary; reuse existing pure functions.
- Applicability: Direct. Adopted via `normalizeRow()` helper in `dataService.js`.
- Adoption rationale: No component changes; no new dependencies; backward-compatible.

**Benchmark 2 — PostgREST conditional column selection**

Supabase/PostgREST documentation and open-source Supabase client examples show conditional `.select()` strings for context-dependent column fetching. Selecting `retail_price_day1,promo_price_day1` for a D-1 query rather than `*` reduces data volume and avoids returning null columns for the unused D's price fields.

- Key takeaway: Use offset-specific column lists; not `*` for lookback queries.
- Applicability: Direct. Adopted in `fetchReport1/2/3` column selection logic.
- Rejection of `*`: Would return all 11 columns per row including 4 unused price columns — unnecessary bandwidth.

**Benchmark 3 — Progressive enhancement in date selectors**

UX best practice for date range selectors: preserve the most recent date as the default selection; additional historical dates are available but not pre-selected. The current `App.jsx` already implements this (`dims.dates[0].date_key` as initial `selectedDate`). No UX change needed; the enhancement is additive.

- Key takeaway: Retain current initialization; new dates appear as additional options.
- Applicability: Direct. No App.jsx changes required.


---

## Minimal Spikes and Experiments

**Spike 1: RPC behavior for D-1/D-2 date_keys**
- Hypothesis: `get_settlements_for_date(D-1_date_key)` returns 0 results since `fact_prices_lookback` contains no rows with D-1's `date_key`.
- Approach: Inspect `load_supabase.py` DDL for `get_settlements_for_date`; it executes `SELECT DISTINCT settlement_key FROM fact_prices_lookback JOIN dim_store ... WHERE date_key = X`.
- Outcome: Confirmed — querying with D-1's key returns empty. All fact rows are under D's `date_key`.
- Conclusion: Settlement filtering for D-1/D-2 must pass `dims.currentDateKey` to the RPC, not the selected lookback date_key.

**Spike 2: Report 2 "Дата" column behavior for D-1/D-2 after dims.dates fix**
- Hypothesis: `dimensions.dates.find(d => d.date_key === selectedDate)?.date` correctly returns D-1/D-2's date string once `dims.dates` includes all 3 rows.
- Approach: Read `Report2.jsx` table cell rendering; the expression uses `selectedDate` directly to look up the date string from `dims.dates`.
- Outcome: Confirmed — when `selectedDate = D-1_date_key` and D-1 is in `dims.dates`, the find returns the D-1 date string. Same for Report 3.
- Conclusion: No Report2.jsx or Report3.jsx changes needed for date label display.

**Spike 3: `calculatePrice()` with NULL `retail_price_day1`**
- Hypothesis: `parseFloat(null)` = `NaN`; `NaN || 0` = 0; so products with NULL lookback prices show as 0.00 лв.
- Approach: Inspect `calculatePrice()` source: `const retail = parseFloat(row.retail_price) || 0`.
- Outcome: Confirmed — NULL retail_price becomes 0.00 лв. Products present on D but absent on D-1 (NULL `retail_price_day1`) display as 0.00 лв for D-1 view. Q001 raised to confirm preferred behavior.
- Conclusion: Functional but potentially confusing UX. User decision pending (Q001).

**Spike 4: `dims._dims` cache and new properties**
- Hypothesis: Adding `currentDateKey` and `lookbackColumnMap` to `_dims` before the module-level cache assignment is safe and does not break `_resetDimsCache()`.
- Approach: Review `_resetDimsCache()` source: `_dims = null`. Setting new properties on `_dims` before assignment is benign; `_resetDimsCache()` clears the whole object.
- Outcome: Confirmed — no impact on cache reset behavior.
- Conclusion: Safe to add `currentDateKey` and `lookbackColumnMap` to the `_dims` object.


---

## AI Copilot Suggestions

**Observation 1 — Design quality: frontend coupling to physical column names**

The frontend is now coupled to `fact_prices_lookback`'s physical column naming convention (`retail_price_day1`, `retail_price_day2`). If a future ETL request renames these columns (e.g., to `prev_retail_price_1`), the `normalizeRow()` helper breaks silently at runtime without a compile-time error. The risk is low in the current single-developer context, but it is worth documenting the coupling explicitly in `context.md` and in a code comment in `normalizeRow()`.

- Suggestion: Add a comment in `dataService.js` near `normalizeRow()` linking it to the `fact_prices_lookback` column schema and citing R-20260430-1505 as the introducing request.

**Observation 2 — Simplification opportunity: RPC call may be eliminatable**

The `get_available_dates()` RPC is now used only to identify `currentDateKey` (D). Since `prune_dim_date()` guarantees `dim_date[0]` (sorted descending) is always D, `currentDateKey` could be derived as `filteredDates[0].date_key` without a network round-trip. However, the RPC also serves as a correctness guard: if Supabase has no fact data (e.g., sync not yet run), `currentDateKey = null` is the correct sentinel. Eliminating the RPC would lose this safety check.

- Suggestion: Retain the RPC call for correctness. Add a comment explaining the dual purpose (identify D, guard against empty fact table). Do not eliminate.

**Observation 3 — Testability: `normalizeRow()` and `lookbackColumnMap` construction are pure and fully unit-testable**

Both `normalizeRow()` and the `lookbackColumnMap` derivation logic are pure functions with no Supabase dependency. The existing test suite mocks `fetchDimensions()` entirely and does not test `dataService.js` internals. These new logic units are prime candidates for isolated unit tests.

- Suggestion: Add a `dataService.test.js` (or extend existing coverage) with tests for `normalizeRow()` with each offset, and for `lookbackColumnMap` shape given a 3-row `dim_date` and a 1-element RPC result.

**Observation 4 — Scope size assessment: well-calibrated**

The frontend-only scope is materially smaller than the ETL approach and achieves equivalent user-facing outcomes. Dropping settlement enrichment is correct — it is a distinct data quality concern. No scope creep risk. The approach is clean and non-invasive: all changes are confined to `dataService.js`, with one stub update in `App.test.jsx`.

- Suggestion: No scope changes recommended.


---

## Testing

- T1 — `fetchDimensions` returns 3 dates (SC1): Mock Supabase to return 3 `dim_date` rows and RPC returning 1 date_key. Expected outcome: `dims.dates.length === 3`.

- T2 — `lookbackColumnMap` populated correctly (SC1): Same setup as T1. Expected outcome: `dims.lookbackColumnMap.get(D_key) === 'current'`; `dims.lookbackColumnMap.get(D1_key) === 'day1'`; `dims.lookbackColumnMap.get(D2_key) === 'day2'`.

- T3 — `normalizeRow` remaps day1 columns (SC3): Call `normalizeRow({retail_price: 1.0, retail_price_day1: 2.5, promo_price_day1: 2.0}, 'day1')`. Expected outcome: returned object has `retail_price === 2.5` and `promo_price === 2.0`; `retail_price_day1` still present.

- T4 — `normalizeRow` identity for 'current' (SC3): Call `normalizeRow(row, 'current')`. Expected outcome: object returned unchanged.

- T5 — `fetchReport1` queries with D's date_key for D-1 selection (SC3): Mock Supabase, spy on `.eq('date_key', X)`. Call `fetchReport1(D1_key, settlementKey, dims)`. Expected outcome: Supabase receives `date_key = D_key` (not `D1_key`).

- T6 — `fetchReport1` selects day1 columns for D-1 (SC3): Spy on `.select(columns)`. Call `fetchReport1(D1_key, ...)`. Expected outcome: select string includes `retail_price_day1,promo_price_day1`.

- T7 — `fetchSettlementsForDate` calls RPC with D's key for D-1 (SC6): Call with `D1_key`. Expected outcome: RPC called with `dims.currentDateKey` (D_key).

- T8 — Date selector shows 3 options in App (SC1): Render App with stub dims containing 3 dates. Expected outcome: 3 `<option>` elements in the date selector (queryable by `getByLabelText('Дата на данните')`).

- T9 — All pre-existing tests pass (SC5): Run `npm test` in `react-app/`. Expected outcome: all prior tests exit 0.

- T10 — Report 1 loads without error on Netlify (SC2): See UAT_scenarios.md — UAT-01.

- T11 — Date selector shows 3 dates on deployed Netlify app (SC1): See UAT_scenarios.md — UAT-02.

- T12 — D-1 selection shows different prices than D in Report 1 (SC3): See UAT_scenarios.md — UAT-03.


---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The frontend-only approach is technically sound and architecturally well-contained. All changes are limited to `dataService.js` (the service layer), which is the correct locus for data-shape transformation. The coupling between frontend column names and the `fact_prices_lookback` physical schema is the sole architectural debt introduced; it is manageable with clear documentation. The `dim_date` 3-row assumption is safe as long as `prune_dim_date()` is not bypassed, which is a known invariant of the current ETL. The lookback column mapping approach avoids any DB schema migration or ETL change, reducing risk significantly compared to the original plan.

- The `normalizeRow()` helper is a clean service-layer concern; it does not leak into component code.
- Adding `currentDateKey` and `lookbackColumnMap` to the existing `_dims` shape is backward-compatible; no component props change.
- The RPC call retained for correctness guard is appropriate; do not eliminate it.

### Product Owner

The frontend-only scope is the correct trade-off: delivers the 3-date selector user value without ETL complexity or database migration risk. The Report 1 fix (Netlify rebuild) is retained and addresses a visible production blocker. Dropping settlement enrichment is a minor regression in data quality but correctly deferred. All success criteria are measurable and testable. SC1 (3 dates visible) and SC2 (Report 1 error fixed) represent the highest-value outcomes for end users.

- Acceptance criteria are achievable within the sprint boundary.
- Settlement enrichment should be logged as a future backlog item.

### User

The change makes 3 dates selectable in the header date picker — a direct improvement over the current single-date view and restoration of the browsable window users previously had via `fact_prices`. The date column in Reports 2 and 3 will correctly label rows as D-1 or D-2 when those dates are selected. Products with no prior-day price data (NULL lookback columns) will appear as 0.00 лв — this is a minor friction point, addressed via Q001. The Report 1 error fix removes a blocking failure on the live app, immediately restoring the category price chart.

- 3-date browsing allows simple trend comparison without requiring new features.
- Products showing 0.00 лв for historical dates may prompt user questions; a future enhancement could omit or flag such rows.

### Security Officer

This change introduces no new security surface. The React app continues to use the public anon key for all Supabase queries. No new RPC functions or tables are created. The `normalizeRow()` helper and `lookbackColumnMap` logic operate exclusively on client-side fetched data and introduce no injection vector. The column names used in `normalizeRow()` are hardcoded string literals — not user-supplied — so there is no risk of client-side field injection. No new credentials are introduced. The Netlify rebuild uses the same existing `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID`. OWASP Top 10 is not impacted by these changes.

### Data Governance Officer

The scope amendment (no ETL changes) means `dim_settlement.csv` retains its 25 unknown entries. This is documented data quality debt; the deferred settlement enrichment should be tracked as a backlog item and addressed in a future request. The `fact_prices_lookback` table schema and Supabase row count remain unchanged — no lineage or retention impact. The 3-date virtual views are a purely presentational concern; no data is written, transformed, or deleted by this request. The lineage for D-1/D-2 price views traces directly to `fact_prices_lookback`'s horizontal columns, which in turn derive from `data/schema/facts/*.csv` via `build_lookback_table()` — lineage is fully traceable. No GDPR or compliance implications; all data is publicly sourced Bulgarian government retail price data.
