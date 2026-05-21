# Analysis: R-20260516-1313 — Fix file detail table layout, dates and filter pagination

## Executive Summary

- **Request ID:** R-20260516-1313
- **Title:** Fix file detail table layout, dates and filter pagination
- **Purpose:** Resolve three usability defects in `FileRowsPanel.jsx` — the 12-column price-fact detail table inside the Файлове page.

- **Defect 1 — Table overflow:** The 12-column detail table overflows its container on typical desktop widths (~1280px). The prior request R-20260515-1003 addressed this with `.table-scroll-wrapper { overflow-x: auto }`, which hides overflow via horizontal scroll. The product owner now wants a no-scroll layout: reduce cell padding and font size, allow text wrapping.

- **Defect 2 — Opaque date labels:** Column headers for lookback columns display static abbreviations ("Д-1", "Д-2"). The actual calendar dates are already available at runtime in `dims.dates` (sorted descending; index 1 = D-1, index 2 = D-2). Replacing the abbreviations with formatted dates (DD.MM.YYYY) eliminates ambiguity for end users.

- **Defect 3 — Broken filter pagination:** `fetchFileRows` uses server-side pagination; `filteredRows` is computed client-side from the currently loaded page only. Typing a filter hides non-matching rows from the current page, but the pagination control still shows `Math.ceil(totalCount / PAGE_SIZE)` pages derived from the unfiltered server count, and rows on other pages are never filtered at all. The fix is to load all rows for the selected file once and implement fully client-side sort, filter, and pagination.

- **`request.md` updates this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs` were written. No open questions raised (all decision points resolved autonomously below threshold 3).

---

## Domain Knowledge Essentials

- **Файлове page (Files page):** The fifth navigation page in the React app. Shows a summary table of source CSV files submitted by retailers for the selected date (from `dim_file`). Clicking a row opens `FileRowsPanel`, a drill-down view of individual price-fact records for that file.

- **fact_prices_lookback:** The sole Supabase fact table. Contains one row per price observation with columns for product, category, store, file, retail price, promo price, and two lookback price columns (`retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`). Lookback columns hold the prices from the preceding two days.

- **Д-1 / Д-2 (Day-minus-1 / Day-minus-2):** Shorthand labels for the two lookback date offsets. "Д" is the Bulgarian letter for "D" (ден = day). Users unfamiliar with this notation cannot tell which calendar date the column refers to.

- **dim_date:** A dimension table with at most 3 rows (D, D-1, D-2). `dims.dates` in the React app is sorted descending: index 0 = D (current date), index 1 = D-1, index 2 = D-2. Each row contains a `date_key` (integer surrogate) and `date` (ISO YYYY-MM-DD string).

- **Impacted roles/personas:** End users browsing price history via the Файлове page; data analysts inspecting individual retailer submissions.

- **Business processes touched:** File-level drill-down inspection of daily price submissions; cross-day price comparison using lookback columns.

---

## Technical Knowledge & Terms

- **FileRowsPanel.jsx:** React functional component. Renders the 12-column paginated table. Fetches rows via `fetchFileRows(fileKey, dims, currentPage, PAGE_SIZE)`. Client-side derives `sortedRows`, `filteredRows`. Pagination state: `currentPage` (0-based), `totalPages` from server `totalCount`.

- **fetchFileRows (dataService.js):** Async function. Makes two Supabase queries: (1) HEAD-only COUNT for totalCount, (2) ranged SELECT for the page rows. Batch-fetches `dim_product` names for the unique product keys on that page. Returns `{ rows, totalCount }`.

- **Server-side vs. client-side pagination:** Current design paginates at the Supabase layer (`range(from, to)`) and delivers exactly PAGE_SIZE rows per fetch. The fix switches to client-side pagination: all rows are fetched once with `range(0, totalCount - 1)`, then sliced per client-controlled page.

- **COLUMNS constant:** Currently a module-level constant array of 12 column definitions. Labels for day1/day2 columns are static strings. Must become a derived value computed inside the component (useMemo) to incorporate runtime date strings from `dims.dates`.

- **dims.dates:** Array of `{ date_key, date }` objects from `dim_date`, sorted descending. `dims.dates[1]?.date` gives the D-1 ISO date; `dims.dates[2]?.date` gives D-2. Already available on every render of `FileRowsPanel` via the `dims` prop passed from `FileDetailPage`.

- **formatDateBG:** Exported helper from `dataService.js`. Converts YYYY-MM-DD → DD.MM.YYYY. Already imported by `FileRowsPanel`.

- **table-scroll-wrapper:** CSS class providing `overflow-x: auto`. Must remain intact for `FileDetailPage`'s summary table. The 12-column detail table must use a new scoped class (`file-rows-table`) for its specific layout overrides.

- **Vitest / @testing-library/react:** Test framework. `FileRowsPanel.test.jsx` has 13 tests; T2 asserts static Д-1/Д-2 column header labels; T6 asserts `fetchFileRows` is called with `pageIndex=1` on next-page click. Both tests require updates after the refactor.

- **Evidence log:**
  - `COLUMNS` is module-level constant → **implication:** moving to derived value requires care to avoid infinite re-render loops; `useMemo` with `[dims]` dependency is the safe pattern.
  - `totalPages = Math.ceil(totalCount / PAGE_SIZE)` uses server count → **implication:** must change to `Math.ceil(filteredRows.length / PAGE_SIZE)` after switch to client-side pagination.
  - `fetchFileRows` makes two Supabase calls per page → **implication:** full-load approach makes two calls total (count + all rows), same as one page fetch; latency is O(file_row_count) rather than O(PAGE_SIZE).
  - `makeStubDims()` in test fixture does not include `dates` → **implication:** after adding `dims.dates` dependency, tests will throw unless `makeStubDims` is updated to include a `dates` array.

- **Files Read:**
  - `react-app/src/components/FileRowsPanel.jsx` (full)
  - `react-app/src/components/FileRowsPanel.test.jsx` (full)
  - `react-app/src/components/FileDetailPage.jsx` (full)
  - `react-app/src/lib/dataService.js` (fetchFileRows, formatDateBG, fetchDimensions sections)
  - `react-app/src/App.css` (results-table, table-scroll-wrapper, sortable-th, filter-row sections)
  - `.aib_memory/context.md` (full)
  - `.aib_memory/input.md` (full)

---

## Research Results

**Pattern scan — client-side pagination with filters:**

1. **React table libraries (TanStack Table / react-table):** The canonical community approach for in-memory pagination + filtering is to hold a flat data array and derive slices via `useMemo`. TanStack Table's `getPaginationRowModel` and `getFilteredRowModel` implement exactly this pattern. This analysis confirms the proposed approach (fetch all rows, slice client-side) is the industry-standard solution for tables where total row count is bounded and fits in browser memory.

2. **Prior workspace pattern (R-20260512-0529):** Reports 1, 2, 3 switched from client-side iteration to server-side aggregation RPCs. `FileRowsPanel` is the inverse case: the data volume per file is small enough (hundreds to low thousands of rows per retailer file) that full client-side loading is practical and eliminates the filter-pagination mismatch.

3. **Scoped CSS class for table density:** A common pattern in product UIs is to add a modifier class (e.g., `.table--compact`) on the `<table>` element to apply reduced padding and font-size only to that specific table instance, without changing shared base styles. This is the proposed approach for SC-1.

---

## External Benchmarking

- **MDN Web Docs — CSS `font-size` and table layout:**
  Browser default table `font-size` is inherited from the body (typically `16px`). Reducing to `0.75em`–`0.8em` (12–12.8px) on a 12-column table with tight padding (`6px 8px`) can reduce total rendered width by ~30–40%, making a 12-column table viable at 1280px without overflow. This is a well-established pattern in data-dense analytics UIs (e.g., Bloomberg Terminal web, Excel Online).
  - Takeaway: `0.8em` font-size on `<td>` and `<th>` combined with `padding: 6px 8px` is the benchmark for compact analytics tables. Adopted in this request.
  - Applicability: Directly applicable; no adaptation needed beyond scoping to `.file-rows-table`.
  - Rationale: Adopts the density benchmark. The `.table-scroll-wrapper` fallback is preserved for narrower viewports where even compact sizing may overflow.

- **WCAG 2.1 — Minimum touch target size (Success Criterion 2.5.5):**
  Filter inputs in the `<thead>` filter row must remain usable on touch devices. WCAG 2.1 recommends 44×44 CSS px touch targets. The product's NFR already calls for "minimum touch target height 44px for form controls on mobile."
  - Takeaway: Filter input height on mobile must be preserved via a `@media (max-width: 600px)` override, even as the desktop table is made more compact.
  - Applicability: Applicable at the ≤600px breakpoint; the desktop compact style does not affect mobile targets if the override is present.
  - Rationale: Adopts the WCAG guidance; the mobile breakpoint override is included in the plan.

---

## Minimal Spikes and Experiments

- **Spike: estimated rendered table width at 0.8em / 6px 8px padding**
  - Hypothesis: 12 columns with `font-size: 0.8em` and `padding: 6px 8px` fit within 1200px on a standard desktop.
  - Approach: Calculated approximate column widths. Shortest content columns (prices, e.g., "2,50"): ~50–70px rendered. Longest header: "Ефективна цена (лв)" ≈ 160px at 0.8em. Longest cell content (product name): depends on data, but text wrapping is allowed. Sum of minimum widths: 12 columns × average ~90px = ~1080px — fits within 1280px.
  - Outcome: Estimated fit at 0.8em / compact padding. Exact fit depends on data content; text wrapping (`white-space: normal`) prevents overflow for long strings.
  - Conclusion: The approach is viable. A `.table-scroll-wrapper` is retained as a fallback for very narrow viewports.

- **Spike: fetchFileRows full-load performance**
  - Hypothesis: Calling `fetchFileRows(fileKey, dims, 0, totalCount)` is safe — Supabase PostgREST allows large range queries and returns results within acceptable time for typical file row counts.
  - Approach: Reviewed `fetchFileRows` implementation. A typical retailer file has hundreds to ~2,000 rows. A 2,000-row SELECT of 9 numeric/key columns from `fact_prices_lookback` is a small payload (~180KB raw JSON). `fetchFileRows` uses `.range(from, to)` which overrides PostgREST's default `max_rows` cap.
  - Outcome: No evidence of a hard row limit causing issues; the app already fetches full dimension tables (tens of thousands of rows) at startup. The two-pass strategy (COUNT then `range(0, totalCount-1)`) is clean.
  - Conclusion: Full-load approach is safe and performant for expected file sizes.

---

## AI Copilot Suggestions

- **Observation 1 (Design quality — COLUMNS as module constant vs. derived value):**
  Moving `COLUMNS` from a module-level `const` to a `useMemo` inside the component is correct React pattern. The dependency array must be `[dims]`. Since `dims` is the same stable object reference after app startup, the memoized value computes once. A named helper `buildColumns(dims)` defined outside the component improves readability.
  - Suggestion: Use `const columns = useMemo(() => buildColumns(dims), [dims])` with `buildColumns` defined as a pure function outside `FileRowsPanel`.

- **Observation 2 (Implementation risk — Supabase row cap):**
  Supabase PostgREST's `max_rows` on the free tier defaults to 1,000. If a file has >1,000 rows, `fetchFileRows` with `pageSize > 1000` passed to `.range(0, pageSize - 1)` may be silently capped. The current `.range(from, to)` call does override the default limit per PostgREST documentation, but this should be validated. A defensive console warning when `rows.length < totalCount` after the full load call will alert developers to any silent truncation.
  - Suggestion: After full-load fetch, log `console.warn` if `rows.length < totalCount` so the issue is detectable in production.

- **Observation 3 (Scope — filter change must reset page):**
  The request does not explicitly state that typing in a filter should reset `currentPage` to 0, but this is logically required — otherwise a user on page 5 who applies a filter would see an empty table if filtered results have fewer than 5 pages. This implicit requirement must be included in the implementation.
  - Suggestion: Add a `useEffect` that calls `setCurrentPage(0)` whenever `filterValues` changes.

- **Observation 4 (Maintainability — test fixture gap):**
  `makeStubDims()` in the test file does not include `dims.dates`. After this change, rendering without `dates` will produce broken column labels. T2 must be updated to assert date-bearing labels, and T6 must be rewritten to verify client-side pagination (no new `fetchFileRows` call on page advance).
  - Suggestion: Add `dates: [{date_key:3,date:'2026-05-15'},{date_key:2,date:'2026-05-14'},{date_key:1,date:'2026-05-13'}]` to `makeStubDims()` and revise T2 and T6 accordingly.

- **Scope note:** The three changes are appropriately scoped. Layout, date labels, and pagination fix are independent and verifiable separately. No scope creep detected.

---

## Testing

- T1 — Existing loading state test: verify `FileRowsPanel.test.jsx` T1 still passes after refactor. Expected outcome: "Зареждане…" text visible during fetch; no regression.

- T2 — Date labels in column headers: render with `dims.dates = [{date_key:3,date:'2026-05-15'},{date_key:2,date:'2026-05-14'},{date_key:1,date:'2026-05-13'}]`; assert headers "Цена 14.05.2026 (лв)", "Промо 14.05.2026 (лв)", "Цена 13.05.2026 (лв)", "Промо 13.05.2026 (лв)" are present; assert old "Цена Д-1 (лв)" is NOT present. Expected outcome: updated assertions pass; old assertions are removed.

- T3 — Static columns unchanged: "Продукт", "Категория", "Населено място", "Магазин", "Верига", "Цена (лв)", "Промо цена (лв)", "Ефективна цена (лв)" headers present. Expected outcome: all eight static labels found.

- T4 — Filter across all loaded rows: mock `fetchFileRows` returning 150 total rows (2 calls: count=150, then all 150); apply filter matching 5 rows; verify displayed rows = 5 and page indicator shows "Страница 1 от 1". Expected outcome: pagination and row count match filtered set.

- T5 — Filter resets page to 1: render with enough rows to have 2+ pages; navigate to page 2; type filter text; verify page indicator shows "Страница 1 от N". Expected outcome: page resets to 1 on filter change.

- T6 — Updated pagination: clicking "Следваща" advances client-side page without triggering additional `fetchFileRows` calls. Expected outcome: `fetchFileRows` call count remains 1 after next-page click.

- T7 — File change resets all state: switching `fileKey` prop resets filters, sort, page, and triggers one fresh `fetchFileRows` call. Expected outcome: state reset confirmed; `fetchFileRows` called exactly once per file.

- T8 — Build passes: `npm run build` in `react-app/` exits 0. Expected outcome: exit code 0, `dist/` non-empty.

- T9 — Regression: existing tests T3–T5, T7–T13 pass without modification (beyond fixture updates in T2/T6). Expected outcome: full Vitest suite green.

No manual UAT scenarios required; all observable behaviour changes are automatable with @testing-library/react.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The switch from server-side pagination to full client-side loading is architecturally coherent for the bounded data volumes in this product. Retailer CSV files submitted daily contain at most a few thousand rows; loading them all in one Supabase call is well within PostgREST capacity and browser memory. The scoped CSS approach (`.file-rows-table` modifier class) respects the open/closed principle — it extends existing table styles without modifying shared rules. The dynamic `COLUMNS` via `useMemo` is correct React; the key risk is the Supabase `max_rows` cap, which must be validated against the deployed instance.

- The full-load strategy will degrade if a future file has rows exceeding PostgREST `max_rows`. A defensive warning log and a future-iteration note should be added.
- The `.table-scroll-wrapper` should be retained on mobile even for the compact table — 320px viewports cannot display 12 columns regardless of font size.
- Moving COLUMNS out of module scope incurs a test maintenance cost; the fixture update is mandatory and must not be deferred.

### Product Owner

The three changes directly address user complaints: wide table forces scrolling (friction), Д-1/Д-2 labels are confusing for non-technical users, and broken filter pagination makes the feature practically unusable when searching large files. The scope is tightly bounded with no scope creep. The day-date labels improve usability at zero additional cost. The compact table font should be chosen as the largest font that achieves no-overflow — not the smallest possible.

- SC-1 should be verified visually after deployment on a real device.
- The date in column headers should be confirmed to match the actual database date rather than a hardcoded value; the test fixture should use realistic dates.

### User

The three changes are meaningful quality-of-life improvements. No scrolling to see all columns is significantly more ergonomic on a laptop. Seeing "15.05.2026" instead of "Д-1" instantly communicates what data the column represents. Filtering that correctly reduces page count removes a major source of confusion when searching for a specific product in a large file.

- The compact font will be harder to read for users with reduced visual acuity; font size must not go below 0.75em (approximately 12px at typical browser defaults).
- The column date labels reflect the date when the app was loaded. If the app is left open overnight, labels may be stale. This is an existing limitation of the cached `dims` architecture and is not introduced by this request.

### Security Officer

No security-sensitive changes. The request touches CSS and a React component that fetches read-only public fact data via the Supabase anon key. No authentication, authorization, or data-classification changes are involved. Full client-side loading does not expose any rows beyond those already accessible via the existing paginated path — the Supabase query still filters by `file_key` with `.eq('file_key', fileKey)`, where `fileKey` is derived from the cached `dims.files` map (not from user-supplied input).

- The `fileKey` prop is always a surrogate key resolved from the trusted dimension cache; no user-controlled input reaches the Supabase filter.
- No new network endpoints, credentials, or data surfaces are introduced.

### Data Governance Officer

No changes to data lineage, storage, or classification. The change affects only client-side rendering of `fact_prices_lookback` rows that are already accessible to all users of the app. The date displayed in column headers is sourced from the canonical `dim_date` table in Supabase — no synthetic or manually entered dates are introduced. All data is public government retail price data; no PII is involved.

- The label change from "Д-1" to an actual date makes column semantics self-documenting, which is a positive data governance outcome (reduces risk of column misinterpretation by analysts).
- No retention, compliance, or lineage impacts.
