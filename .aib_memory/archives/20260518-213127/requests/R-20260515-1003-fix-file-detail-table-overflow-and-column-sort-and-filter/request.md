## Goal

Fix the visual overflow of the detail-records table in the `FileRowsPanel` component (rendered inside the "Файлове" / Files page) so that the table is contained within its parent container and does not extend beyond the visible area. In the same component, add interactive column-header controls that allow the user to sort rows by clicking a column title and filter rows by typing a substring into a per-column filter input (case-insensitive).

## Background

The "Файлове" page (R-20260513-2123, R-20260514-2102) includes a `FileRowsPanel` component that displays a paginated 12-column table of individual price-fact records for a selected source file. The panel uses a `table-scroll-wrapper` div intended to provide horizontal scrolling when the 12 columns exceed the viewport width. However, the `.table-scroll-wrapper` CSS class has no rule defined in `App.css`, so the table overflows the parent `.report-section` container instead of scrolling within it. This produces a broken layout where the table visually extends behind and beyond the card boundary.

The same panel currently has no sort or filter controls on its column headers, limiting the user's ability to explore the data: all 100 rows per page are displayed in fetch order with no way to rank by price or narrow by product/store name.

## Scope

- Fix the overflow of the `FileRowsPanel` detail table by adding the missing `.table-scroll-wrapper` CSS rule (at minimum `overflow-x: auto`) to `react-app/src/App.css`, ensuring the 12-column table scrolls horizontally within the panel card rather than breaking out.

- Add sort behaviour to `FileRowsPanel`: clicking a column header cycles through ascending → descending → unsorted states; a visual indicator (arrow or symbol) shows the active sort column and direction.

- Add per-column substring filter inputs to `FileRowsPanel`: each column header area includes a text input; typing into an input hides rows whose value for that column does not contain the entered substring (case-insensitive); numeric price columns are filtered by the formatted display string.

- Add any supporting CSS rules to `App.css` needed to style the sort indicators and filter input row without breaking the existing responsive layout.

- Update `react-app/src/components/FileRowsPanel.test.jsx` with test cases covering sort and filter behaviour.

- Update `.aib_memory/context.md` to reflect the changes.

## Out of scope

- Server-side filtering or sorting (i.e., passing filter/sort parameters to `fetchFileRows` or the Supabase query). The decision on scope (client vs server) is captured in Q001.

- Changes to `FileDetailPage.jsx` beyond what is strictly necessary for the overflow fix (the summary table in `FileDetailPage` already uses `table-scroll-wrapper`; the same CSS fix resolves it as a side-effect).

- Changes to `dataService.js`, `supabase.js`, or any ETL scripts.

- Changes to Report 1, Report 2, Report 3, or any other page component.

- Adding sort or filter to the file summary table in `FileDetailPage` (three-column summary only; not requested).

## Constraints

- The React app must remain buildable (`npm run build` exits 0) and all existing Vitest tests must continue to pass after the changes.

- All new UI interactions (sort, filter) must be implemented in React state without introducing new npm dependencies.

- The fix must not alter the existing responsive CSS breakpoints at 900px and 600px in a way that breaks other pages; new `.table-scroll-wrapper` base CSS must be additive.

- The sort and filter operate on the currently loaded page's rows (client-side on `rows` state). Per Q001, the scope of filtering across paginated data is a pending decision.

- New CSS must follow the existing class-naming and formatting conventions in `App.css` (no inline styles for layout rules that could be in CSS; use existing colour tokens `#667eea`, `#764ba2`).

- No hardcoded credentials or new environment variables.

## Success criteria

- SC-1: The `FileRowsPanel` detail table no longer overflows the parent `.report-section` card; it scrolls horizontally within the wrapper on viewports narrower than the full table width.

- SC-2: Clicking a column header in `FileRowsPanel` sorts the visible rows by that column's value; a second click reverses the sort; a third click returns to original fetch order.

- SC-3: Typing text into a column's filter input hides rows whose value in that column does not include the typed string (case-insensitive substring match); clearing the input restores all rows.

- SC-4: Sort and filter controls are keyboard-accessible (focusable, operable via Enter/Space for sort headers, standard text input behaviour for filters).

- SC-5: All existing `FileRowsPanel.test.jsx` tests continue to pass; new tests cover at minimum: sort ascending, sort descending, sort toggle to unsorted, filter shows only matching rows, filter cleared restores all rows.

- SC-6: `npm run build` from `react-app/` exits 0 with no new errors or warnings.

## Assumptions

- A1: The `table-scroll-wrapper` class is used in both `FileRowsPanel.jsx` and `FileDetailPage.jsx`; adding the base CSS rule fixes overflow in both components simultaneously.
  - Risk if false: Only one component is affected; the other may need a separate class or inline style.

- A2: The sort and filter operate on the currently loaded `rows` state array (client-side, current page only). A total of 100 rows per page is sufficient for the expected use case without server-side filtering.
  - Risk if false: Users with large files (many thousands of rows) will find per-page filtering insufficient; server-side implementation would be needed (addressed by Q001).

- A3: Numeric price columns are formatted to strings for display; filter on price columns matches the formatted display value (e.g. "2,50" in bg-BG locale).
  - Risk if false: Users expecting to filter by "2.5" (dot decimal) may not get matches; additional locale-aware numeric comparison may be needed.

- A4: No new npm packages are needed; React `useState` and `useMemo` are sufficient to implement sort and filter.
  - Risk if false: A table-management library is required, changing the dependency footprint.

- A5: The existing Vitest + React Testing Library test setup in `react-app/` supports new tests without configuration changes.
  - Risk if false: Additional test infrastructure setup is needed before new tests can run.

## Plan

### Task 1: Fix table overflow with CSS
**Intent:** Add the missing `.table-scroll-wrapper` CSS rule so the 12-column table scrolls within its container instead of overflowing.
**Inputs:** `react-app/src/App.css`; knowledge that `.table-scroll-wrapper` is used in `FileRowsPanel.jsx` and `FileDetailPage.jsx` but has no CSS rule.
**Outputs:** Updated `react-app/src/App.css` with a new `.table-scroll-wrapper` base rule.
**External Interfaces:** None.
**Environment & Configuration:** No environment changes.
**Procedure:**
1. Locate the Results Table section in `App.css` (around line 382).
2. Add `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` immediately before or after `.results-container`.
3. Verify no existing rule conflicts with the new rule.
**Done Criteria:** The `.table-scroll-wrapper` class has an `overflow-x: auto` rule in `App.css`; the table no longer overflows the panel card in a browser preview.
**Dependencies:** None.
**Risk Notes:** The fix is additive; no existing rule is removed.

### Task 2: Add sort state and behaviour to FileRowsPanel
**Intent:** Allow the user to sort the currently displayed rows by clicking any column header.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`; 12 column definitions; the `rows` state array.
**Outputs:** Updated `FileRowsPanel.jsx` with sort state, sortable `<th>` elements, sort indicator, and sorted row rendering via `useMemo`.
**External Interfaces:** None (client-side only).
**Environment & Configuration:** No environment changes.
**Procedure:**
1. Add `sortConfig` state: `{ column: null, direction: 'asc' }`.
2. Add `handleSort(columnKey)` that cycles null → 'asc' → 'desc' → null.
3. Derive `sortedRows` from `rows` via `useMemo` using `sortConfig`.
4. Attach `onClick={handleSort(columnKey)}` and `aria-sort` attribute to each `<th>`.
5. Add a sort direction indicator (e.g., ↑ ↓ or neutral) inside the `<th>`.
6. Render `sortedRows` in `<tbody>` instead of raw `rows`.
**Done Criteria:** Clicking a column header sorts visible rows; second click reverses; third click restores fetch order. `aria-sort` attribute is set correctly.
**Dependencies:** Task 1 (CSS must support the visual indicator styling).
**Risk Notes:** Sorting strings vs numbers requires type-aware comparison; price columns contain floats, text columns contain strings.

### Task 3: Add per-column filter state and UI to FileRowsPanel
**Intent:** Allow the user to filter visible rows by typing a substring into a column's filter input.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`; 12 column definitions; `sortedRows` from Task 2.
**Outputs:** Updated `FileRowsPanel.jsx` with `filterValues` state (one key per column), a filter input row in `<thead>`, and filtered row rendering via `useMemo`.
**External Interfaces:** None (client-side only).
**Environment & Configuration:** No environment changes.
**Procedure:**
1. Add `filterValues` state: `{ product: '', category: '', settlement: '', store: '', company: '', retail_price: '', promo_price: '', calculatedPrice: '', retail_price_day1: '', promo_price_day1: '', retail_price_day2: '', promo_price_day2: '' }`.
2. Add `filteredRows` derived from `sortedRows` via `useMemo`: include rows where every non-empty filter value appears as a case-insensitive substring in the corresponding column's display value.
3. Add a second `<tr>` row inside `<thead>` with `<td>` or `<th>` cells each containing a text input bound to the corresponding filter key.
4. Set `aria-label` on each filter input describing the column it filters.
5. Render `filteredRows` in `<tbody>` instead of `sortedRows`.
6. Reset `filterValues` and `sortConfig` to initial state when `fileKey` changes (add to the `useEffect` that resets `currentPage`).
**Done Criteria:** Typing in a filter input hides rows without a match; clearing restores all rows; filter resets on file change.
**Dependencies:** Task 2.
**Risk Notes:** Numeric columns formatted with `toLocaleString('bg-BG')` use comma as decimal separator; users must type "2,50" not "2.50" to match. Record this in A3.

### Task 4: Add CSS for sort and filter UI
**Intent:** Style the sortable column headers and the filter input row so they are visually coherent with the existing table design.
**Inputs:** `react-app/src/App.css`; existing `.results-table th` rules; brand colours.
**Outputs:** Updated `react-app/src/App.css` with new rules for `.sortable-th`, `.sort-indicator`, `.filter-row input` (or equivalent class names).
**External Interfaces:** None.
**Environment & Configuration:** No environment changes.
**Procedure:**
1. Add `.results-table th.sortable-th { cursor: pointer; user-select: none; }` to the Results Table section.
2. Add `.sort-indicator { margin-left: 6px; opacity: 0.7; }` for the sort arrow.
3. Add `.filter-row th { background: white; padding: 6px 8px; }` and `.filter-row input { width: 100%; box-sizing: border-box; padding: 4px 6px; font-size: 0.85em; border: 1px solid #ddd; border-radius: 4px; }`.
4. Ensure the filter row does not break the thead gradient background for data headers.
**Done Criteria:** Column headers show a pointer cursor and sort indicator; filter inputs are visually contained within column widths; existing thead gradient is preserved for data header row.
**Dependencies:** Task 1.
**Risk Notes:** Filter row lives inside `<thead>` which has the gradient; the filter `<tr>` needs an explicit background override to remain white/light.

### Task 5: Write tests for sort and filter
**Intent:** Cover the new sort and filter behaviour with automated unit tests.
**Inputs:** `react-app/src/components/FileRowsPanel.test.jsx`; existing test fixtures (`makeStubRow`, `makeStubDims`).
**Outputs:** Updated `FileRowsPanel.test.jsx` with at least 5 new test cases covering: sort ascending, sort descending, sort toggle to unsorted, filter shows only matching rows, filter cleared restores all rows.
**External Interfaces:** Vitest + React Testing Library.
**Environment & Configuration:** No configuration changes.
**Procedure:**
1. Add a helper that returns a two-row stub response (rows with distinct sortable values).
2. Write T-sort-asc: click product header → rows appear in ascending product name order.
3. Write T-sort-desc: click product header twice → rows appear in descending order.
4. Write T-sort-reset: click product header three times → rows appear in original fetch order.
5. Write T-filter-match: type "хляб" into product filter → only matching rows visible.
6. Write T-filter-clear: after filtering, clear input → all rows visible.
**Done Criteria:** `npm run test` (or `npx vitest run`) passes all existing and new test cases.
**Dependencies:** Tasks 2, 3.
**Risk Notes:** Bulgarian case-insensitive matching — the test stub should use `.toLowerCase()` consistent with the implementation.

### Task 6: Update context.md and documentation
**Intent:** Reflect the changes made to `FileRowsPanel.jsx` and `App.css` in the workspace product context.
**Inputs:** `.aib_memory/context.md`; completed Tasks 1–5.
**Outputs:** Updated `.aib_memory/context.md` with a change note for R-20260515-1003.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add an "Updated by R-20260515-1003" note at the top of `context.md` summarising: table overflow fix via `.table-scroll-wrapper` CSS rule; sort and filter added to `FileRowsPanel`.
2. Update the `FileRowsPanel.jsx` module breakdown entry to reflect the new sort/filter state.
3. Update the responsive layout NFR entry to note that `.table-scroll-wrapper` now has an explicit rule.
**Done Criteria:** `context.md` mentions R-20260515-1003 and accurately reflects the new component capabilities.
**Dependencies:** Tasks 1–5.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update to reflect new `FileRowsPanel` sort/filter functionality and `.table-scroll-wrapper` CSS fix introduced by R-20260515-1003.

## Questions & Decisions

**Q001**: Should column sort and filter in `FileRowsPanel` apply only to the currently loaded page (100 rows, client-side), or should they apply across all records for the selected file (requiring filter/sort parameters to be passed through `fetchFileRows` to the Supabase query)?
- [ ] Option A: Client-side only — sort and filter the current page's 100 rows in the browser. Simple implementation; no changes to `dataService.js` or Supabase queries. *(recommended)*
- [x] Option B: Server-side — pass filter text and sort column/direction to `fetchFileRows`; modify the Supabase query to apply `ilike` filters and `order` clauses; reset pagination on filter change. Richer UX for large files but significantly broader scope.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

- `react-app/src/components/FileRowsPanel.jsx` — primary component receiving sort/filter state and rendering changes.
- `react-app/src/components/FileDetailPage.jsx` — indirectly fixed by the `.table-scroll-wrapper` CSS rule (its 3-column summary table also uses this class).
- `react-app/src/App.css` — receives new `.table-scroll-wrapper` base rule plus sort/filter UI CSS rules.
- `react-app/src/components/FileRowsPanel.test.jsx` — receives new test cases.
- `.aib_memory/context.md` — documentation update.

## Internal Review of Request and Product Docs

- The request is well-scoped to two independently deliverable improvements (overflow fix + sort/filter) that share the same component. The overflow fix is trivially small (one CSS rule); the sort/filter feature is the main implementation body.
- The "Файлове" page was introduced in R-20260513-2123 and the `FileRowsPanel` drill-down in R-20260514-2102; both are stable and their test suites pass. The changes in this request are additive only.
- No ETL scripts, Supabase schema, or dimension-loading logic is affected.
- The responsive layout (R-20260512-2138) established breakpoints and scroll rules for `.results-container` but omitted `.table-scroll-wrapper`. This request corrects that gap.
- Q001 is the only open decision; Option A is recommended and expected to be confirmed given the stated goal focuses on UI interaction quality, not full-dataset query capability.
