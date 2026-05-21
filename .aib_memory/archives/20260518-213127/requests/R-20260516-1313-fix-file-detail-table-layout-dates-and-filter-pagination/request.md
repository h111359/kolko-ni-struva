## Goal

Fix three usability defects in the `FileRowsPanel` component (the detail table inside the Файлове page):

1. The 12-column detail table must fit the available viewport width without horizontal scrolling — reduce font and cell padding, and allow text wrapping to achieve this.
2. Column headers currently showing "Д-1" and "Д-2" must display the actual calendar date in DD.MM.YYYY format, sourced from `dims.dates`.
3. Client-side filtering currently only filters the currently loaded server-side page; filtered rows must be re-paginated across all available rows — filtering must condense matching rows to the first pages and reduce the page count accordingly.

## Background

The Файлове page shows a file summary table; clicking a file opens `FileRowsPanel`, a 12-column paginated detail table of enriched price-fact rows fetched from `fact_prices_lookback` via `fetchFileRows`. The previous request (R-20260515-1003) added horizontal scroll, sort, and filter. Three usability gaps remain:

- The horizontal scroll wrapper was added as a stop-gap; the product owner prefers a no-scroll layout at standard desktop width.
- Column labels "Д-1" and "Д-2" are opaque shorthand; actual date values from `dims.dates` are already available at runtime.
- `fetchFileRows` is server-paginated; `filteredRows` in the component only filters within the currently loaded server page. When the user types a filter, the matched rows on other server pages are not visible, and the pagination control still shows the unfiltered page count — giving a misleading and broken filter experience.

## Scope

- `react-app/src/components/FileRowsPanel.jsx`

  - Make `COLUMNS` a dynamic derived value (useMemo or function call) that reads actual D-1 and D-2 date strings from `dims.dates` via `formatDateBG` and substitutes them into the day1/day2 column labels.

  - Change data-loading strategy: fetch all rows for the selected file in one logical operation (remove server-side page navigation from the fetch effect — pass `pageIndex=0` and a `pageSize` equal to `totalCount`, or call `fetchFileRows` twice: once for count, once for all rows).

  - Implement fully client-side pagination: derive `displayedRows` by slicing `filteredRows` with `currentPage × PAGE_SIZE`; derive `totalPages` from `Math.ceil(filteredRows.length / PAGE_SIZE)`; reset `currentPage` to 0 when `filterValues` change.

  - Add a CSS class to the detail table (`file-rows-table`) to allow scoped style overrides without affecting the file summary table.

- `react-app/src/App.css`

  - Add `.file-rows-table th` and `.file-rows-table td` rules with reduced padding and font-size that make the 12 columns fit within ~1200px without horizontal overflow.

  - Allow text wrapping in body cells (remove or avoid `white-space: nowrap` on `.file-rows-table td`).

  - The `.table-scroll-wrapper` class itself must remain intact (still used by the summary table in `FileDetailPage`).

## Out of scope

- Changes to `fetchFileRows` in `dataService.js` (the function signature and server-side query logic remain unchanged; the component manages full-page loading by calling with appropriate pageSize).
- Changes to any other page or component (Report 1, 2, 3, RecordDetailModal, FileDetailPage summary table, header, home page).
- Changing the PAGE_SIZE constant for other use cases.
- Modifying Supabase RPC functions or database schema.
- Introducing server-side filter pushdown.

## Constraints

- React app is client-only; no serverless functions.
- `dims` is cached at app startup and must not be re-fetched.
- `formatDateBG` is already exported from `dataService.js` and must be reused.
- The fix must preserve existing keyboard accessibility (`tabIndex`, `onKeyDown`) and `aria-sort` attributes.
- The `.table-scroll-wrapper` must remain functional on the summary table in `FileDetailPage`.
- CSS changes must not break responsive layout at ≤ 600px and ≤ 900px breakpoints defined in `App.css`.
- `npm run build` must exit 0 and produce `dist/` after all changes.

## Success criteria

- SC-1: On a standard 1280px-wide desktop viewport, the 12-column detail table renders without horizontal scrollbar (overflow is hidden or fits within the card width).
- SC-2: Column headers for the day1/day2 columns show the actual calendar date in DD.MM.YYYY format (e.g., "Цена 15.05.2026 (лв)") derived from `dims.dates[1].date` and `dims.dates[2].date`.
- SC-3: Typing text into a filter input resets the page to page 1 and shows only matching rows from ALL loaded rows (not just the currently displayed page). The total page count reflects the filtered result size.
- SC-4: Clearing all filter inputs restores the full row set and the full page count.
- SC-5: Pagination controls (Предишна / Следваща) navigate through filtered results correctly.
- SC-6: `npm run build` in `react-app/` exits 0.
- SC-7: Existing automated test suite (`npm test`) passes without new failures.

## Assumptions

- A1: Individual retailer files fetched via `fetchFileRows` will have `totalCount` ≤ 10,000 rows. Full client-side loading is safe for this range.
  - Risk if false: Large files will have slow initial load or may be silently truncated by PostgREST `max_rows`, causing incomplete data display. A console warning will be added to detect this.

- A2: `dims.dates` is always an array with at least 2 entries (D and D-1) when `FileRowsPanel` is mounted. If the array has fewer than 3 entries (no D-2), `dims.dates[2]` will be `undefined`; the day2 column labels will fall back to a "—" placeholder via optional chaining, not crash.
  - Risk if false: D-2 column will show a placeholder label; no runtime error.

- A3: The filter match for numeric columns continues to use bg-BG locale-formatted display strings (e.g., matching "2,50" not "2.50") — consistent with the existing design decision from R-20260515-1003.
  - Risk if false: Users filtering numeric columns need to know the bg-BG decimal separator convention.

- A4: PostgREST `.range(0, totalCount - 1)` overrides the default server-side `max_rows` cap and returns all rows when called explicitly. The existing `fetchFileRows` implementation uses `.range(from, to)` which satisfies this.
  - Risk if false: Rows are silently truncated; the defensive console warning will surface this at runtime.

## Plan

### Task 1: Dynamic column labels in FileRowsPanel
**Intent:** Replace static "Д-1" / "Д-2" column label strings with actual calendar dates sourced from `dims.dates`.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`; `dims.dates` array (available at render time); `formatDateBG` (already imported).
**Outputs:** Modified `FileRowsPanel.jsx` — `COLUMNS` moved from module-level const to a `useMemo`-derived value inside the component; day1 and day2 column labels use `formatDateBG(dims.dates[1]?.date)` and `formatDateBG(dims.dates[2]?.date)` respectively, with "—" fallback when date is absent.
**External Interfaces:** None (no new imports or Supabase calls).
**Environment & Configuration:** None.
**Procedure:**
1. Define a `buildColumns(dates)` pure function outside `FileRowsPanel` that takes `dims.dates` and returns the 12-column definitions array with actual date strings in day1/day2 labels.
2. Inside `FileRowsPanel`, add `const columns = useMemo(() => buildColumns(dims.dates), [dims])` after existing state declarations.
3. Replace all references to `COLUMNS` in the component body with `columns`.
4. Remove the module-level `COLUMNS` constant.
5. Remove the module-level `INITIAL_FILTER_VALUES` constant and derive it from `columns` using `Object.fromEntries(columns.map(c => [c.key, '']))` inside a `useMemo` or as a stable constant derived from `buildColumns`.
**Done Criteria:** Column headers in the rendered table show "Цена DD.MM.YYYY (лв)" and "Промо DD.MM.YYYY (лв)" for day1 and day2; static columns unchanged; no React hook order violations; `eslint` / Vite build clean.
**Dependencies:** None.
**Risk Notes:** `INITIAL_FILTER_VALUES` must also be derived from `columns` (not `COLUMNS`) or the shape mismatch will cause filter state to be incomplete if column keys change. Handle by deriving `initialFilterValues` inside `useMemo` alongside `columns`.

### Task 2: Client-side full-load pagination in FileRowsPanel
**Intent:** Fetch all rows for the selected file at once and implement fully client-side sort, filter, and page slicing so that filtering correctly condenses results across all rows.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`; `fetchFileRows` from `dataService.js` (signature unchanged); `totalCount` returned by the initial fetch.
**Outputs:** Modified `FileRowsPanel.jsx` — loading effect fetches all rows in two passes (COUNT then `range(0, totalCount-1)`); `displayedRows` derived by slicing `filteredRows` with `currentPage × PAGE_SIZE`; `totalPages` derived from `Math.ceil(filteredRows.length / PAGE_SIZE)`; `currentPage` resets to 0 on `filterValues` change.
**External Interfaces:** `fetchFileRows` in `dataService.js` — called twice: once with `pageSize=0` / `head:true` for count (or reuse existing count mechanism), once with `pageIndex=0, pageSize=totalCount` for all rows. No changes to `dataService.js`.
**Environment & Configuration:** None.
**Procedure:**
1. Change the fetch `useEffect` to a two-pass approach:
   a. Call `fetchFileRows(fileKey, dims, 0, 1)` to get `totalCount` (only 1 row fetched for speed, count is accurate).
   b. If `totalCount > 0`, call `fetchFileRows(fileKey, dims, 0, totalCount)` to load all rows.
   c. Store all rows in `setRows(allRows)` state; store `totalCount` in state.
   d. After loading, if `allRows.length < totalCount`, log `console.warn(...)`.
2. Change `totalPages` derivation from `Math.ceil(totalCount / PAGE_SIZE)` to `Math.ceil(filteredRows.length / PAGE_SIZE)`.
3. Change `displayedRows` (new derived value) to `filteredRows.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)`.
4. Replace `{filteredRows.map(...)}` in the JSX with `{displayedRows.map(...)}`.
5. Add a `useEffect` watching `filterValues` that calls `setCurrentPage(0)` when any filter changes.
6. Remove `currentPage` from the fetch effect's dependency array (pagination is now client-side).
**Done Criteria:** Applying a filter resets to page 1 and shows only matching rows from all loaded rows; `totalPages` reflects filtered row count; next/prev page navigates within filtered set without re-fetching; file change still triggers a fresh fetch.
**Dependencies:** Task 1 (columns must be dynamic before this task to avoid stale filter-key shape).
**Risk Notes:** Two-pass fetch adds one round-trip on file open. For empty files (`totalCount=0`), skip the second fetch. For very large files, the second fetch may be slow; the loading indicator covers this.

### Task 3: Compact CSS for file-rows-table
**Intent:** Add scoped CSS class `.file-rows-table` with reduced padding and font-size so the 12-column table fits within ~1280px without horizontal overflow.
**Inputs:** `react-app/src/App.css`; `react-app/src/components/FileRowsPanel.jsx` (add class to `<table>`).
**Outputs:** Modified `App.css` — new `.file-rows-table th` and `.file-rows-table td` rules; modified `FileRowsPanel.jsx` — `<table>` receives `className="results-table file-rows-table"`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In `FileRowsPanel.jsx`, change `<table className="results-table">` to `<table className="results-table file-rows-table">`.
2. In `App.css`, after the `.results-table` block, add:
   - `.file-rows-table th { padding: 6px 8px; font-size: 0.8em; white-space: normal; }` 
   - `.file-rows-table td { padding: 5px 8px; font-size: 0.8em; white-space: normal; word-break: break-word; }`
3. Inside `@media (max-width: 600px)`, add `.file-rows-table th input { min-height: 44px; }` to maintain touch target height for filter inputs on mobile.
**Done Criteria:** No horizontal scrollbar visible on a 1280px viewport; text in cells wraps instead of extending the table; `.table-scroll-wrapper` still functions on the summary table in `FileDetailPage`; mobile filter inputs remain at least 44px tall.
**Dependencies:** None.
**Risk Notes:** Very long product names will wrap across multiple lines, increasing row height. This is the intended behaviour (per request: "wrap text").

### Task 4: Update FileRowsPanel.test.jsx
**Intent:** Update the test file to reflect the new dynamic column labels and client-side pagination, and add tests covering the filter-pagination fix.
**Inputs:** `react-app/src/components/FileRowsPanel.test.jsx`; updated `FileRowsPanel.jsx`.
**Outputs:** Modified `FileRowsPanel.test.jsx` — `makeStubDims()` includes `dates` array; T2 asserts date-bearing column labels; T6 rewritten to verify client-side page advance without additional `fetchFileRows` calls; new tests T14 (filter resets page) and T15 (filter works across all rows).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add `dates: [{ date_key: 3, date: '2026-05-15' }, { date_key: 2, date: '2026-05-14' }, { date_key: 1, date: '2026-05-13' }]` to `makeStubDims()`.
2. Update T2: replace assertions for 'Цена Д-1 (лв)', 'Промо Д-1 (лв)', 'Цена Д-2 (лв)', 'Промо Д-2 (лв)' with '14.05.2026' and '13.05.2026' label assertions.
3. Rewrite T6: mock `fetchFileRows` to return 101 rows on the first call; click "Следваща"; assert `fetchFileRows` call count is still 1 (no second server call) and pagination indicator shows page 2.
4. Add T14: apply a filter on a 150-row mock; assert page indicator shows "Страница 1 от 1" after filtering to 5 rows.
5. Add T15: navigate to page 2 then apply filter; assert page resets to 1.
**Done Criteria:** `npm test` in `react-app/` exits 0 with all 15+ tests passing.
**Dependencies:** Tasks 1 and 2.
**Risk Notes:** The two-pass fetch in Task 2 changes how `fetchFileRows` is called (potentially twice per file open). Mock setup in tests must account for multiple calls by returning appropriate values per call.

### Task 5: Automated tests and build verification
**Intent:** Run the full Vitest suite and Vite build to confirm no regressions.
**Inputs:** `react-app/` (updated sources).
**Outputs:** Terminal output confirming all tests pass and build exits 0.
**External Interfaces:** None.
**Environment & Configuration:** Node.js; `npm` in `react-app/`.
**Procedure:**
1. Run `npm test -- --run` in `react-app/` and confirm exit 0.
2. Run `npm run build` in `react-app/` and confirm exit 0 and `dist/` is non-empty.
**Done Criteria:** Both commands exit 0; no test failures; no build errors.
**Dependencies:** Tasks 1–4.
**Risk Notes:** None anticipated.

### Task 6: Update context.md
**Intent:** Record the changes made in this request in `.aib_memory/context.md`.
**Inputs:** `.aib_memory/context.md`; this request summary.
**Outputs:** Updated `.aib_memory/context.md` — append R-20260516-1313 update note to the header block; update the Requirements Summary section 7 to reflect the new column label behaviour and client-side pagination.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add `> Updated by R-20260516-1313: FileRowsPanel now loads all rows for the selected file in a single client-side fetch and paginates/filters them fully client-side; day1/day2 column headers show the actual calendar dates in DD.MM.YYYY format derived from dims.dates; the detail table uses compact CSS class .file-rows-table (reduced padding and font-size, text wrapping) for a no-horizontal-scroll layout at standard desktop widths.` to the auto-generated header block.
2. Update the Functional Capabilities bullet for `FileRowsPanel` to reflect the client-side pagination and date-label changes.
**Done Criteria:** `.aib_memory/context.md` contains the R-20260516-1313 update note and accurately describes the new behaviour.
**Dependencies:** Tasks 1–3.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update header block and Functional Capabilities section 7 to reflect client-side pagination, actual date labels in day1/day2 columns, and compact CSS class for the file detail table.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

- `react-app/src/components/FileRowsPanel.jsx` — primary change target: COLUMNS, data fetch strategy, pagination logic.
- `react-app/src/App.css` — scoped table style overrides for `.file-rows-table`.
- `react-app/src/lib/dataService.js` — `fetchFileRows` and `formatDateBG` referenced but NOT modified.
- `react-app/src/components/FileDetailPage.jsx` — parent component; passes `dims` to `FileRowsPanel`; not modified.
- `react-app/src/App.test.jsx` — may require updates if snapshot tests capture column labels.
- `tests/` — no Python-layer changes; no ETL test impact.

## Internal Review of Request and Product Docs

- The requested table layout change (no horizontal scroll) is a deliberate reversal of the approach taken in R-20260515-1003, which added `.table-scroll-wrapper`. Scope is correctly limited to the 12-column detail table using the new scoped CSS class.
- The date label fix is low-risk; `dims.dates` is already stable at component render time.
- The pagination fix is the highest-complexity item: switching from server-side to fully client-side pagination requires a different loading pattern (fetch all rows upfront). For files with very large row counts this may increase initial load time. This trade-off is acceptable given the product owner's preference for correct filter behaviour.
