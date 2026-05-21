# Analysis: R-20260515-1003 — Fix file detail table overflow and column sort and filter

## Executive Summary

- **Request ID:** R-20260515-1003

- **Request title:** Fix file detail table overflow and column sort and filter

- **Purpose:** Two additive improvements to the `FileRowsPanel` component in the React Analytics App's "Файлове" page: (1) fix a visual layout defect where the 12-column detail table overflows its parent card container, and (2) add interactive column-header controls for sort (ascending/descending/unsorted cycle) and per-column substring filter (case-insensitive, client-side).

- **Root cause of overflow:** The `.table-scroll-wrapper` CSS class used in `FileRowsPanel.jsx` and `FileDetailPage.jsx` has no CSS rule defined in `App.css`. Without `overflow-x: auto`, the 12-column table extends beyond the `.report-section` container boundary instead of enabling a horizontal scrollbar within the wrapper.

- **Scope:** Changes are isolated to `FileRowsPanel.jsx`, `App.css`, `FileRowsPanel.test.jsx`, and `context.md`. No ETL scripts, Supabase schema, `dataService.js`, or other page components are touched.

- **Open decision:** Q001 asks whether filter/sort should be client-side (current page only) or server-side (across all records). Option A (client-side) is recommended and reflected in the current plan.

- **`request.md` sections added/updated in this run:** `## Assumptions` (A1–A5), `## Plan` (Tasks 1–6), `## Documentation` (1 entry), `## Questions & Decisions` (Q001), `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.

---

## Domain Knowledge Essentials

- **Файлове page ("Files" page):** The fifth navigation page in the React Analytics App. Lists source CSV files submitted by retailers for the selected date, fetched from `dim_file`. Each row is clickable and opens the `FileRowsPanel` drill-down.

- **FileRowsPanel:** A drill-down panel that shows individual price-fact records (`fact_prices_lookback` rows) for a single selected source file. Displays 12 columns: product name, category, settlement, store, company chain name, retail price, promo price, effective price, and four lookback price columns (Д-1 retail, Д-1 promo, Д-2 retail, Д-2 promo). Paginated at 100 rows per page.

- **dim_file:** Supabase dimension table mapping a `file_key` surrogate to `file_name` (the retailer's submitted CSV filename) and `zip_date` (the date of the ZIP archive that contained it). Used as a foreign key in `fact_prices_lookback`.

- **fact_prices_lookback:** The sole Supabase fact table. Each row represents one retail price observation for a (product, file, date) combination, with current and lookback (Д-1, Д-2) price columns. Filtered by `file_key` to produce the `FileRowsPanel` result set.

- **Lookback columns (Д-1, Д-2):** "Д" is short for "Ден" (Day in Bulgarian). Д-1 = yesterday's price; Д-2 = two days ago. These are pre-computed columns in `fact_prices_lookback` for efficient cross-date price comparison.

- **EKATTE:** Bulgarian administrative code registry for settlements. Not directly relevant to this request; mentioned for context on the dimension model.

- **Affected roles:** End users (retail-price analysts) who use the "Файлове" page to explore per-file price data. The overflow defect affects all users of this page regardless of viewport width.

---

## Technical Knowledge & Terms

- **`overflow-x: auto` (CSS):** When set on a block container, the browser adds a horizontal scrollbar only when the content width exceeds the container width. This is the standard CSS mechanism for containing wide tables within a card-layout parent. Without this, content bleeds outside the card boundary.

- **`table-scroll-wrapper`:** A `<div>` wrapping the `<table>` in `FileRowsPanel.jsx` and `FileDetailPage.jsx`. The class name was defined in JSX but omitted from `App.css`, making it a no-op container.

- **`useMemo` (React):** A hook that memoizes a computed value, recomputing only when its dependency array changes. The recommended pattern for derived data (sorted/filtered rows) in React function components — avoids re-sorting/re-filtering on every render unrelated to the dependency.

- **`useState` (React):** The standard hook for managing component-local interactive state. Used here for `sortConfig` (column + direction) and `filterValues` (one key per column).

- **Vitest + React Testing Library:** The existing test stack in `react-app/`. `@testing-library/react` provides `render`, `screen`, `fireEvent`; Vitest provides `describe`, `it`, `expect`, `vi`. All new tests must use these without additional dependencies.

- **Case-insensitive substring match:** `value.toLowerCase().includes(filter.toLowerCase())`. Standard JavaScript string operation; no locale-specific collation needed for this use case.

- **`aria-sort` attribute:** The ARIA attribute on `<th>` elements that communicates sort direction to screen readers. Values: `'ascending'`, `'descending'`, `'none'`.

- **bg-BG locale formatting:** `toLocaleString('bg-BG', { minimumFractionDigits: 2 })` formats `2.5` as `"2,50"` (comma decimal separator). Filter on numeric columns must match this formatted string, not the raw float.

- **Files read for this analysis:**
  - `.aib_memory/input.md` — original user request
  - `.aib_memory/context.md` — product context
  - `react-app/src/components/FileRowsPanel.jsx` — primary component
  - `react-app/src/components/FileDetailPage.jsx` — parent component
  - `react-app/src/App.css` — stylesheet
  - `react-app/src/components/FileRowsPanel.test.jsx` — existing test suite
  - `.aib_brain/conventions/analysis-convention.md`
  - `.aib_brain/conventions/request-convention.md`

---

## Research Results

### Pattern scan

- **Overflow fix pattern:** The `.results-container { overflow-x: auto; }` rule added in R-20260512-2138 (responsive UI) is the established workspace pattern for horizontal table containment. The `table-scroll-wrapper` class follows the same intent but missed a corresponding CSS declaration. The fix is a direct application of the existing workspace pattern.

- **Prior table scroll implementations:** `FileDetailPage.jsx` (summary table) and `FileRowsPanel.jsx` (detail table) both use `table-scroll-wrapper`. The class is consistent across both but is unstyled. Fixing the class definition resolves both components simultaneously.

- **Sort/filter pattern in the React app:** No existing component in the app implements column-level sort or filter. The `RecordDetailModal` (R-20260506-2251) is a pure display component. Reports 1–3 use server-side RPCs for filtering. This request introduces the first client-side interactive table feature.

- **Evidence log:**
  - `App.css` has no `.table-scroll-wrapper` rule → overflow is uncontained → fix: add `overflow-x: auto`.
  - `App.css` has `.results-container { overflow-x: auto }` in media queries → proves the workspace intent for table scroll containment.
  - `FileRowsPanel.jsx` `rows` state holds the current page's fetched rows → sort/filter can be applied as a `useMemo` derivation without new data fetches.
  - `FileRowsPanel.test.jsx` uses `vi.mocked(fetchFileRows)` to inject rows → new sort/filter tests can use the same injection pattern.

---

## External Benchmarking

- **React sortable table best practices (industry pattern):** The dominant React ecosystem pattern for sortable tables in non-library implementations uses `useState` for sort configuration (column + direction) and `useMemo` for the derived sorted array. This avoids unnecessary re-sorts and keeps the sort logic co-located with the component. Libraries like `@tanstack/react-table` implement this same pattern with additional features. For this request's scope (single component, no external dependency requirement), the raw `useState`+`useMemo` pattern is the correct fit — it matches the app's existing zero-external-state-library philosophy and keeps the bundle unchanged.
  - Key takeaway: `useMemo([...rows], [sortConfig])` is the established pattern; a stable sort (preserving original order for equal elements) is preferred.
  - Applicability: adopt directly; no adaptation needed.

- **Per-column filter input in HTML tables (UI pattern):** A widely used pattern in data-intensive admin UIs (seen in AG Grid, DataTables.net, and bespoke React tables) places a secondary `<thead>` row containing one input per column. The input is visually distinguished from the data header row (different background, smaller font). This pattern is accessible (inputs have `aria-label` or `<label>`), keyboard-navigable, and does not require JavaScript framework extensions.
  - Key takeaway: second `<tr>` in `<thead>` with one `<input>` per column is the standard DOM approach; no need for a floating filter panel or modal.
  - Applicability: adopt directly; the existing `<thead>` gradient must be overridden for the filter row background to avoid white text on white input.

- **CSS `overflow-x: auto` for wide tables (W3C/MDN standard):** The W3C CSS specification defines `overflow-x: auto` as the correct value for "provide scrollbar only when needed". Using `overflow-x: scroll` always shows the scrollbar; `overflow-x: hidden` clips content. `auto` is the user-friendly default for table wrappers.
  - Key takeaway: `overflow-x: auto` on the wrapper; `width: 100%` on the table ensures the table fills the wrapper before triggering scroll.
  - Applicability: adopt directly; matches the existing `.results-container` pattern in the workspace.

---

## Minimal Spikes and Experiments

- **Spike: Does `.table-scroll-wrapper` have any CSS rule in `App.css`?**
  - Hypothesis: The overflow defect is caused by a missing CSS rule for `.table-scroll-wrapper`.
  - Approach: `grep -n "table-scroll-wrapper" react-app/src/App.css`.
  - Outcome: Zero matches. The class is present in JSX but absent from CSS.
  - Conclusion: Adding `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` is the complete fix. No structural JSX changes needed.

- **Spike: Are sort and filter feasible without new npm packages?**
  - Hypothesis: JavaScript `Array.prototype.sort`, `Array.prototype.filter`, `useMemo`, and `useState` are sufficient.
  - Approach: Review `FileRowsPanel.jsx` structure; confirm `rows` is a plain array of enriched objects; confirm all display values are already computed strings or numbers in the row objects.
  - Outcome: `rows` is a `useState`-managed array of plain objects with keys `productName`, `categoryName`, `settlementName`, `storeName`, `companyName`, `retail_price`, `promo_price`, `calculatedPrice`, `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`. All values are already available at render time.
  - Conclusion: No new packages needed. Sort and filter can be applied via `useMemo` derivations on the `rows` array.

---

## AI Copilot Suggestions

- **Observation 1 — Scope of filtering is the key UX risk.** Client-side filtering on 100 rows per page is useful for quick row scanning but is semantically incomplete: filtering for "Лидл" in the product column when the file has 5,000 rows will only match against the 100 rows currently loaded, not the full dataset. Users familiar with spreadsheet or database filtering will expect global-dataset behaviour. The plan correctly raises Q001 for this decision, and Option A (client-side) is recommended as a pragmatic starting point. However, if this page is intended for data quality auditing or investigation workflows, Option B (server-side) may be unavoidable in a follow-up.
  - Suggestion: After Option A is implemented, add a visible notice on the filter inputs ("Филтрира текущата страница") so users understand the scope limitation without confusion.

- **Observation 2 — CSS fix is minimal and correct; the missing class is a completeness gap in R-20260514-2102.** The `table-scroll-wrapper` class was introduced without a corresponding CSS rule in R-20260514-2102. This is a straightforward oversight — the JSX wraps the table but the wrapper has no effect. The one-line CSS fix is complete and low-risk. No JSX changes are needed for the overflow fix. The fix simultaneously resolves both `FileRowsPanel` and `FileDetailPage` since both use the same class.
  - Suggestion: When closing this request, add a note to the convention or review process to verify that every new CSS class name introduced in JSX has a corresponding rule in `App.css`.

- **Observation 3 — Sort stability matters for paginated data.** JavaScript's `Array.prototype.sort` is not guaranteed to be stable in all environments (though modern V8, SpiderMonkey, and JavaScriptCore all implement stable sort as of ES2019). Since rows within a page have no guaranteed order from Supabase (they are returned in storage order), users may notice that rows with equal sort-column values appear in different orders across re-renders. Using a stable sort (which JS now guarantees per spec) preserves the original fetch order as a tiebreaker, giving a predictable result.
  - Suggestion: Implement sort using the idiomatic `[...rows].sort(compareFn)` pattern (spread to avoid mutating state); rely on JavaScript's guaranteed stable sort behaviour per ECMAScript 2019+.

- **Observation 4 — Scope appears appropriately sized for the stated goal.** The two improvements (overflow fix and sort/filter) are logically grouped as a single request because they apply to the same component. The overflow fix is a 1–2 line change; the sort/filter is the bulk of the work. The overall request is small-to-medium in scope and does not carry hidden complexity unless Q001 is answered with Option B (server-side), which would materially expand scope.
  - Suggestion: Implement in task order (CSS fix first, sort second, filter third) so the overflow fix can be deployed standalone if needed.

---

## Testing

- T1 — Overflow fix CSS rule exists: Verify that `App.css` contains `.table-scroll-wrapper` with `overflow-x: auto`. Expected outcome: `grep "overflow-x: auto" react-app/src/App.css` returns at least one match on a line within the `.table-scroll-wrapper` rule block.

- T2 — Build passes: Run `npm run build` from `react-app/`. Expected outcome: exits 0 with no new errors or warnings; `dist/` directory is produced.

- T3 — Existing tests pass: Run `npx vitest run` from `react-app/`. Expected outcome: all pre-existing test cases pass; no regressions.

- T4 — Sort ascending (SC-2): In `FileRowsPanel.test.jsx`, render with two rows having distinct product names; click the Продукт column header; assert the rows in the DOM are ordered A→Z. Expected outcome: first row in DOM contains the alphabetically earlier product name.

- T5 — Sort descending (SC-2): Click the Продукт column header a second time; assert Z→A order. Expected outcome: first row in DOM contains the alphabetically later product name.

- T6 — Sort reset (SC-2): Click the Продукт column header a third time; assert the original fetch order is restored. Expected outcome: rows appear in the order returned by `fetchFileRows` mock.

- T7 — Filter shows only matching rows (SC-3): In `FileRowsPanel.test.jsx`, render with two rows having distinct product names; type the name of one product into the Продукт filter input; assert only the matching row is present in the DOM. Expected outcome: one row in `<tbody>`, containing the matched product name.

- T8 — Filter cleared restores all rows (SC-3): After T7, clear the filter input; assert both rows are present in the DOM. Expected outcome: two rows in `<tbody>`.

- T9 — Filter resets on file change (SC-3): Set a filter value; simulate `fileKey` prop change (re-render with new `fileKey`); assert filter input is cleared and all new rows are displayed. Expected outcome: filter state is reset; no residual filter applied to the new file's rows.

- T10 — Sort indicator aria attribute (SC-4): After clicking a column header once, assert the `aria-sort` attribute on that `<th>` is `"ascending"`. After clicking again, assert `"descending"`. After a third click, assert `"none"` or attribute is absent. Expected outcome: `aria-sort` value matches the active sort direction.

- UAT-01 — Visual overflow containment: See `UAT_scenarios.md` — UAT-01. Manual verification that the 12-column table no longer extends beyond the parent card boundary.

- UAT-02 — Sort and filter usability: See `UAT_scenarios.md` — UAT-02. Manual verification that sort indicators are visible, filter inputs are accessible, and the interaction feels responsive.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The overflow fix is a single-line CSS correction with zero architectural risk — it closes a completeness gap from R-20260514-2102. The sort/filter feature is correctly scoped as a client-side, single-component enhancement using idiomatic React patterns (`useState` + `useMemo`). No new dependencies, no changes to the data layer or API surface. The pagination boundary (100 rows/page) is the main architectural constraint: the plan correctly surfaces this as Q001 rather than silently implementing a potentially misleading UX.

- Risk: If Q001 is answered with Option B (server-side), the scope expands significantly to include changes to `dataService.js`, the Supabase query structure, and potentially a new RPC function.
- Risk: `table-scroll-wrapper` is used in two components; the CSS fix is correctly shared. Future components adding wide tables should follow the same wrapper class convention.
- Recommendation: Approve the plan as scoped; resolve Q001 before implementation to avoid scope creep during the task.

### Product Owner

The overflow defect is a visible layout bug that reduces trust in the product's visual quality. Fixing it is high-priority and low-risk. The sort/filter addition directly improves the usefulness of the "Файлове" drill-down page, which is currently a read-only display. The success criteria are measurable and complete. The one ambiguity (Q001) is correctly escalated.

- Scope is clear and deliverable in a single iteration.
- No new pages or navigation changes; the feature is additive within an existing component.
- The client-side filter scope (Option A) is acceptable for the stated goal; a follow-up request can address server-side if analysts need full-dataset search.

### User

The overflow defect is the most immediately noticeable problem — the table visually "breaks out" of its card, making it hard to read and scroll. Fixing it will significantly improve the readability of the detail records view. The sort/filter feature adds meaningful self-service exploration capability that analysts currently lack.

- Sorting by price columns will let users quickly identify the cheapest or most expensive products in a file.
- Filtering by product name or store will let users drill into specific retailers or product lines without scrolling through all 100 rows.
- The per-page filter scope limitation (Option A) may frustrate users with large files; a visible notice per AI Copilot Suggestion 1 would mitigate confusion.

### Security Officer

No new data exposure. The component reads enriched rows already fetched and cached in the browser. Sort and filter operations are pure client-side array transformations — no additional Supabase queries are issued, no new network requests are made, and no new user input reaches the backend. Filter inputs are bound to React state and never interpolated into SQL or API calls. No authentication or authorization changes.

- The existing anon key + RLS posture is unchanged.
- No new environment variables, secrets, or credentials involved.
- Input from filter fields is used only for `String.prototype.toLowerCase().includes()` comparison — no eval, no dynamic query construction, no XSS risk from the filter value itself (React renders text content safely).

### Data Governance Officer

No data model changes. No new tables, columns, or RPC functions in Supabase. The sort and filter operations consume data already present in the `fact_prices_lookback` result set fetched by `fetchFileRows`. No new data is written, retained, or exported as a result of this request.

- `fact_prices_lookback` retention policy (rolling 3-day window via `dim_date` pruning) is unaffected.
- `backend_sql_audit_log` is unaffected; no new SQL statements are issued.
- No PII is introduced; all displayed data is retail price observations from the government open-data portal.
- Data lineage is unchanged; `dim_file` → `fact_prices_lookback` chain is unmodified.
