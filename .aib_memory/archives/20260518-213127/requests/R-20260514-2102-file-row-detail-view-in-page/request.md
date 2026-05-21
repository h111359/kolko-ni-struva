## Goal

Allow users on the "Файлове" (Files) page to click on any file row in the summary table and view the detailed content of that file — displaying every individual price record (fact row) contributed by the selected file, along with all its attributes and metrics.

## Background

The "Файлове" page (`FileDetailPage.jsx`) currently displays a summary table of source CSV files for the selected date, showing file name, submission date, and total record count. While this gives a useful overview of which retailers submitted data, it does not allow users to inspect the individual price records that make up each file. This feature extends the Files page with a drill-down capability that surfaces individual fact rows grouped by source file, providing transparency into the raw pricing data submitted by each retailer. The pattern is consistent with the existing per-row drill-down in Report 2 (RecordDetailModal), extended to a multi-row tabular context.

## Scope

- Make each file summary row in `react-app/src/components/FileDetailPage.jsx` clickable, triggering a detail view for the selected file.

- Add a `fetchFileRows(fileKey, dims, pageIndex, pageSize)` function to `react-app/src/lib/dataService.js` that fetches paginated fact rows from `fact_prices_lookback` filtered by `file_key`, together with a total row count; enriches rows with dimension data (product name from a targeted dim_product batch query, category/store/company/settlement from the cached dims).

- Create a new `react-app/src/components/FileRowsPanel.jsx` component that renders a paginated table of enriched fact rows, covering all attributes (product, category, settlement, store, company) and all price metrics (retail price, promo price, effective price, and lookback price columns day1/day2).

- Integrate `FileRowsPanel` into `FileDetailPage.jsx` so that clicking a file row shows the panel and a close/back control dismisses it.

- Add unit tests: new `react-app/src/components/FileRowsPanel.test.jsx` for the new component; updated `react-app/src/components/FileDetailPage.test.jsx` for click-through and close behaviors.

- Update `.aib_memory/context.md` to reflect the new drill-down capability.

## Out of scope

- Adding a new Supabase RPC function for the file rows query (client-side join pattern is used, consistent with existing fallback functions; no ETL re-deployment required).
- Changes to the ETL pipeline (`src/extract.py`, `src/transform.py`, `src/load_supabase.py`).
- Changes to Report 1, Report 2, or Report 3 pages.
- User-selectable column sorting in the detail view.
- Search or filter within the file row detail view.
- User authentication or authorization changes.

## Constraints

- The detail view must follow the existing responsive CSS conventions (`table-scroll-wrapper`, horizontal overflow, ≤ 600px and ≤ 900px breakpoints in `App.css`).
- `dim_product` is not preloaded in the dims cache (~118K rows); product names must be fetched from Supabase via a targeted `.in()` query for the unique product_keys in each paginated page.
- Server-side pagination via Supabase `.range()` is required; files can have thousands of records.
- The implementation must be compatible with the existing Vitest + React Testing Library test framework.
- No new Supabase credentials or environment variables are needed.
- No hardcoded credentials; env vars use `VITE_` prefix (existing convention).
- All new components must be accessible: semantic table markup, meaningful headings, close button reachable by keyboard.

## Success criteria

- SC1: Clicking a file row in the "Файлове" summary table shows a detail view for that file's individual price records.
- SC2: The detail view renders at minimum: product name, category, settlement, store, company, retail price, promo price, and effective price for each fact row; all lookback price columns (day1/day2 retail and promo) are also displayed.
- SC3: The detail view supports pagination for files with large record counts (≥ 1 000 rows visible across pages).
- SC4: A close/back control in the detail view dismisses it and returns the user to the summary table.
- SC5: The detail view shows a loading state while records are being fetched from Supabase.
- SC6: All new components and functions are covered by unit tests with mocked Supabase calls.
- SC7: The existing test suite (`npm test`) passes without regression after the changes.

## Assumptions

- A1: A file's rows can be reliably retrieved by filtering `fact_prices_lookback` on `file_key` alone without an additional `date_key` filter, because `fact_prices_lookback` is fully truncated and reinserted on every sync run and file_key values are globally unique across all sync runs.
  - Risk if false: rows from different sync runs could intermingle for a given file_key, producing incorrect record counts or mismatched data; would require adding `date_key` as a second filter.
- A2: Batch-fetching `dim_product` for the unique `product_key` values returned by each paginated page of fact rows provides acceptable performance (≤ 2 Supabase round-trips per page navigation: one for fact rows, one for product names).
  - Risk if false: per-page latency is unacceptable for users; a pre-fetching strategy or a new server-side RPC join would be needed.
- A3: A page size of 100 rows per page in the detail view balances query performance and UI density for both desktop and mobile viewports.
  - Risk if false: users may prefer fewer rows (faster load) or more (less clicking); page size can be adjusted as a constant without architectural change.
- A4: The detail view interaction model (inline panel vs. modal) is an open decision requiring product owner input; see Q001.
  - Risk if false: implementing the wrong model requires a UI rework of `FileDetailPage.jsx` and `FileRowsPanel.jsx` layout.

## Plan

### Task 1: Add `fetchFileRows` to `dataService.js`
**Intent:** Implement a new exported paginated function that retrieves enriched fact rows from `fact_prices_lookback` for a given `file_key`.
**Inputs:** `react-app/src/lib/dataService.js`, dims cache (categories, stores, companies, settlements), Supabase client
**Outputs:** Modified `react-app/src/lib/dataService.js` with new `fetchFileRows(fileKey, dims, pageIndex, pageSize)` export
**External Interfaces:** Supabase `fact_prices_lookback` (table query with `.range()`), Supabase `dim_product` (targeted `.in()` query for product_keys on each page)
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (already present)
**Procedure:**
1. Define `fetchFileRows(fileKey, dims, pageIndex = 0, pageSize = 100)` and export it.
2. Issue two Supabase queries in sequence: (a) `fact_prices_lookback` COUNT with `{ count: 'exact', head: true }` filtered by `file_key` to get `totalCount`; (b) `fact_prices_lookback` SELECT of all fact columns filtered by `file_key`, using `.range(pageIndex * pageSize, (pageIndex + 1) * pageSize - 1)` for the requested page.
3. Collect unique `product_key` values from the returned page and batch-fetch product names from `dim_product` using `.in('product_key', uniqueKeys)`.
4. Enrich each row with: `productName` (from dim_product batch), `categoryName` (from `dims.categories`), `storeName` / `companyName` / `settlementName` (from `dims.stores` / `dims.companies` / `dims.settlements`), and `calculatedPrice` (via `calculatePrice`).
5. Return `{ rows: enrichedRows, totalCount }`.
6. Wrap both Supabase calls with `executeLoggedQuery` for session query logging.
**Done Criteria:** `fetchFileRows` returns `{ rows, totalCount }` with all enriched fields present; logs appear in the session query log.
**Dependencies:** None
**Risk Notes:** If a file has 0 rows in `fact_prices_lookback` (e.g., file is from a date not in the current sync), the count query returns 0 and the function returns `{ rows: [], totalCount: 0 }` cleanly.

### Task 2: Create `FileRowsPanel.jsx`
**Intent:** Render a paginated table of enriched fact rows for a selected file, with all attributes and metrics.
**Inputs:** `react-app/src/components/` directory; `fetchFileRows` from dataService; `formatDateBG`, `calculatePrice` helpers
**Outputs:** New `react-app/src/components/FileRowsPanel.jsx`
**External Interfaces:** `fetchFileRows` (dataService.js)
**Environment & Configuration:** None
**Procedure:**
1. Create `FileRowsPanel.jsx` accepting props: `fileKey` (number), `fileMeta` ({ file_name, zip_date }), `dims`, `onClose` (function).
2. Manage state: `rows` (array), `totalCount` (number), `loading` (bool), `error` (string|null), `currentPage` (number, 0-indexed), `pageSize` (constant 100).
3. `useEffect` on `[fileKey, currentPage]`: call `fetchFileRows(fileKey, dims, currentPage, pageSize)`, update state.
4. Render: close/back button (calls `onClose`), file header showing `fileMeta.file_name`, `formatDateBG(fileMeta.zip_date)`, and `totalCount` records.
5. Render the fact-rows table inside a `table-scroll-wrapper` div (for mobile horizontal scroll). Columns: Продукт, Категория, Населено място, Магазин, Верига, Цена (лв), Промо цена (лв), Ефективна цена (лв), Цена Д-1 (лв), Промо Д-1 (лв), Цена Д-2 (лв), Промо Д-2 (лв).
6. Render loading state (`'…'` or spinner text), error message, empty-state message.
7. Render prev/next pagination controls, showing current page number and total pages.
**Done Criteria:** Component renders rows in correct columns; loading state shown while fetch is in progress; close button triggers `onClose`; pagination controls advance/retreat pages; wide table scrolls horizontally on mobile.
**Dependencies:** Task 1
**Risk Notes:** With 12 table columns, horizontal scroll is mandatory on all viewport widths below ~1200px; `table-scroll-wrapper` already handles this.

### Task 3: Modify `FileDetailPage.jsx`
**Intent:** Make file summary rows clickable and integrate `FileRowsPanel` as a drill-down detail view.
**Inputs:** `react-app/src/components/FileDetailPage.jsx`, `react-app/src/components/FileRowsPanel.jsx`
**Outputs:** Modified `react-app/src/components/FileDetailPage.jsx`
**External Interfaces:** `FileRowsPanel` component
**Environment & Configuration:** None
**Procedure:**
1. Import `FileRowsPanel` from `./FileRowsPanel`.
2. Add state `selectedFile` (null or `{ file_key, file_name, zip_date }`); default null.
3. In the file summary table `<tbody>`, add `onClick` handler on each `<tr>` that sets `selectedFile` to the clicked file's metadata.
4. Add `style={{ cursor: 'pointer' }}` (or a CSS class) to each clickable `<tr>`.
5. Conditionally render `<FileRowsPanel>` when `selectedFile` is non-null, passing `fileKey={selectedFile.file_key}`, `fileMeta={selectedFile}`, `dims={dimensions}`, `onClose={() => setSelectedFile(null)}`.
**Done Criteria:** Clicking a file row shows `FileRowsPanel` for that file; close control in the panel clears `selectedFile` and shows the summary table.
**Dependencies:** Tasks 1, 2
**Risk Notes:** None.

### Task 4: Add `FileRowsPanel.test.jsx` and update `FileDetailPage.test.jsx`
**Intent:** Provide unit test coverage for `FileRowsPanel` and the new click-through behaviour in `FileDetailPage`.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`, `react-app/src/components/FileDetailPage.test.jsx`
**Outputs:** New `react-app/src/components/FileRowsPanel.test.jsx`; updated `react-app/src/components/FileDetailPage.test.jsx`
**External Interfaces:** Vitest, React Testing Library (`render`, `screen`, `act`, `fireEvent`)
**Environment & Configuration:** None
**Procedure:**
1. Create `FileRowsPanel.test.jsx`: mock `fetchFileRows` and `formatDateBG` from `dataService`; write tests for loading state, rows rendering (column presence), empty state, error state, close-button callback, and prev/next pagination.
2. Update `FileDetailPage.test.jsx`: add a test that clicking a file row (via `fireEvent.click`) causes `FileRowsPanel` to appear in the DOM; add a test that clicking the close button in `FileRowsPanel` removes it and restores the summary table.
3. Mock `fetchFileRows` in all new tests so no live Supabase calls occur.
**Done Criteria:** All new tests pass with `npm test`; no regressions in existing FileDetailPage tests.
**Dependencies:** Tasks 2, 3
**Risk Notes:** `FileRowsPanel` calls `fetchFileRows` asynchronously; wrap renders in `act(async () => { ... })` to flush async state updates before assertions.

### Task 5: Update `context.md`
**Intent:** Reflect the new file row detail view capability in the product context document.
**Inputs:** `.aib_memory/context.md`
**Outputs:** Updated `.aib_memory/context.md`
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Add an update banner entry at the top of `context.md` referencing R-20260514-2102.
2. In the Functional Capabilities section (item 7, React app description), update the "Files" page description to mention clickable file rows and the `FileRowsPanel` detail view.
3. In the Module Breakdown for `react-app/src/components/FileDetailPage.jsx`, update the entry to mention the clickable rows and `FileRowsPanel` integration.
4. Add a new entry for `react-app/src/components/FileRowsPanel.jsx`.
5. In the dataService.js Module Breakdown entry, add `fetchFileRows` to the list of exported functions.
**Done Criteria:** `context.md` accurately describes the new capability without contradicting existing content.
**Dependencies:** Tasks 1–3
**Risk Notes:** None.

### Task 6: Run test suite and build validation
**Intent:** Confirm all tests pass and the build compiles cleanly after implementation.
**Inputs:** Full `react-app` test suite; Vite build
**Outputs:** Test run output; `react-app/dist/` build artefact
**External Interfaces:** Node.js / npm
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` must be set (or the build will emit a warning; no crash expected since credentials validation is runtime, not build-time)
**Procedure:**
1. Run `npm test` in `react-app/` and verify 0 failing tests.
2. Run `npm run build` in `react-app/` and verify exit code 0.
3. Address any test failures or build errors before closing the task.
**Done Criteria:** `npm test` exits 0; `npm run build` exits 0.
**Dependencies:** Tasks 1–4
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` — Update to reflect the new file row detail view capability in the Files page and the new `fetchFileRows` function in dataService.js.

## Questions & Decisions

**Q001**: How should the file row detail view appear when a user clicks a file row in the "Файлове" summary table?
- [ ] Option A: Modal overlay (similar to RecordDetailModal) — a dialog opens over the page, closes on Escape or ✕ button
- [ ] Option B: Inline panel below the summary table — the detail table expands below the file list, user scrolls down to it *(recommended)*
- [ ] Option C: Replace the summary table — the file list is replaced by the detail view, with a ← Back button to return
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/components/FileDetailPage.jsx` | Modified | Add click handler on rows, `selectedFile` state, `FileRowsPanel` integration |
| `react-app/src/components/FileRowsPanel.jsx` | Created | New paginated detail view component for file row data |
| `react-app/src/components/FileRowsPanel.test.jsx` | Created | Unit tests for `FileRowsPanel` |
| `react-app/src/components/FileDetailPage.test.jsx` | Modified | Add tests for row click-through and `FileRowsPanel` integration |
| `react-app/src/lib/dataService.js` | Modified | Add exported `fetchFileRows` function |
| `react-app/src/App.css` | Modified | Add `cursor: pointer` style for clickable file rows (if not already covered by existing `.results-table tbody tr` rules) |
| `.aib_memory/context.md` | Modified | Update product context to reflect new capability |

## Internal Review of Request and Product Docs

- OK: The request is consistent with the existing architecture — client-side fact enrichment via dims cache and targeted dim_product batch queries is the established pattern (fetchReport2Fallback, fetchReport3Fallback).
- Missing info: The request does not specify the UX interaction model (modal, inline panel, or page replacement). Raised as Q001.
- Ambiguity: "All attributes and metrics" is interpreted as all 12 columns of `fact_prices_lookback` enriched with dimension display names; this results in a 12-column detail table. This interpretation is accepted but will produce a very wide table requiring horizontal scroll.
- OK: `fact_prices_lookback` column set is fully defined in `src/load_supabase.py` DDL. No missing schema knowledge.
- OK: The existing `table-scroll-wrapper` CSS class in `FileDetailPage.jsx` (and `App.css`) already handles horizontal scroll; no new CSS architecture is needed beyond adding cursor styles for clickable rows.
- Cross-ref issue: `context.md` describes `FileDetailPage.jsx` as listing dim_file entries with 3 columns (file_name, date, record count) — this will be outdated after implementation; tracked in Documentation section.
