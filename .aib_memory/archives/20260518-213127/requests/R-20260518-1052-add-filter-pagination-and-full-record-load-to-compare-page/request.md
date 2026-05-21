## Goal

Add per-column substring filtering, client-side pagination, and full-result-set loading to the "🗺️ Сравнение по места" page (Report 3) in the React app. The filtering and pagination UI must match the pattern established in the "📁 Файлове" page (`FileRowsPanel`). The current `get_report_3_rows` RPC call is subject to PostgREST's `max_rows` default cap and thus silently truncates result sets that exceed 1 000 rows; this must be fixed so all matching rows are loaded before client-side operations are applied.

## Background

Report 3 ("Сравнение по места") lets the user select a product category and date, then displays every price fact row for that category across all settlements, stores, and products. With large popular categories this result set can exceed PostgREST's default `max_rows` limit (1 000 rows), causing silent truncation identical to the issue solved in R-20260517-1244 for the `Файлове → FileRowsPanel` component.

The "Файлове" page's `FileRowsPanel.jsx` already implements the full client-side pattern: paginated multi-pass fetch (`fetchAllFileRows`), per-column substring filter inputs in the table header, a modern five-element pagination bar, client-side sort, and page-reset-on-filter. The developer explicitly requests that the same pattern be applied to Report 3.

The `fetchReport3` function in `dataService.js` uses a single `.rpc()` call without `.range()` pagination, so it can silently receive only the first 1 000 rows. The fallback `fetchReport3Fallback` applies a `REPORT3_ROW_CAP = 5000` hard ceiling, also truncating large categories. Both paths need to be replaced or supplemented with a paginated multi-pass fetch.

## Scope

- Add a paginated multi-pass fetch for `get_report_3_rows` RPC results in `dataService.js`, analogous to `fetchAllFileRows`, so all rows for the selected category and date are loaded regardless of PostgREST `max_rows`.

- Update the fallback path `fetchReport3Fallback` in `dataService.js` to remove the `REPORT3_ROW_CAP` ceiling and paginate through all rows without a hard cap.

- Add client-side per-column substring filter inputs (one input per table column) to `Report3.jsx`, matching the `FileRowsPanel` filter-row pattern (case-insensitive match, resets page to 1 on change).

- Add client-side pagination to `Report3.jsx`: five-element bar (First «, Previous ‹, page indicator, Next ›, Last ») with correct disabled states. Page size configurable via a local constant (default 100 rows per page, matching `FileRowsPanel`).

- Filter and pagination must operate across the complete loaded row set (client-side), not page-by-page server-side.

- Update `Report3.test.jsx` to cover the new filter and pagination UI.

- Update `dataService.test.js` (or create a focused test block) to verify that `fetchReport3` issues multiple RPC range calls for result sets exceeding `SUPABASE_PAGE_SIZE`.

- Update `.aib_memory/context.md` to reflect the changes.

## Out of scope

- Adding sort capability (click-header column sort) to Report 3 — not requested.

- Row-click modal for Report 3 (RecordDetailModal pattern) — not requested.

- Cross-filter dropdowns in Report 3 — not requested; that is a Report 2 feature.

- Changes to `src/load_supabase.py` or the `get_report_3_rows` PostgreSQL function — the fix is client-side fetch pagination only.

- Changes to Reports 1 or 2.

- Changes to the `FileRowsPanel` or `FileDetailPage` components.

## Constraints

- The fix must not require any Supabase schema or RPC function changes; it must work by chaining `.range()` on the existing `supabase.rpc()` call.

- Filtering must be fully client-side on the complete loaded dataset, not server-side.

- Existing behaviour when fewer rows than `SUPABASE_PAGE_SIZE` are returned must be unchanged (single-pass load).

- React app's `npm run build` must exit 0 after changes.

- All existing tests must continue to pass; new tests must also pass.

- Page size default: 100, matching `FileRowsPanel`.

- No new npm dependencies may be introduced.

## Success criteria

- SC-1: When a category with > 1 000 fact rows is selected, the total loaded row count in the UI matches the actual row count in `fact_prices_lookback` for that category and date (no silent truncation).

- SC-2: The Report 3 results table displays per-column filter inputs in the table header. Typing in a filter input narrows visible rows to those containing the substring (case-insensitive). Clearing the input restores all rows.

- SC-3: Filter results span all loaded rows, not just the current page. Applying a filter resets the visible page to 1.

- SC-4: The results table shows at most 100 rows per page. A five-element pagination bar (First «, Previous ‹, page indicator, Next ›, Last ») is rendered below the table. The edge buttons are disabled on the first and last page respectively.

- SC-5: Changing the category or date selection resets filters and pagination to their default state (page 1, all filters cleared).

- SC-6: `npm run build` exits 0 with no TypeScript / ESLint blocking errors after all changes.

- SC-7: All pre-existing and new automated tests pass.

## Assumptions

- A1: PostgREST supports `.range()` chaining on `.rpc()` calls for the Supabase JS client v2; this has been confirmed by the precedent in `fetchAllFileRows` (which uses `.range()` on table queries) and by PostgREST's documented pagination support for RPC endpoints.
  - Risk if false: The RPC pagination loop will not work and an alternative approach (e.g., adding `p_offset`/`p_limit` parameters to the PostgreSQL function) would be required — scope increase.

- A2: The `get_report_3_rows` RPC returns rows in a stable order so that paginating via successive `.range()` calls produces a consistent full result set without duplicates or gaps.
  - Risk if false: Rows near page boundaries could be missed or duplicated; the RPC function would need an explicit `ORDER BY` added — Supabase schema change.

- A3: Per-column filter inputs for the 7-column Report 3 table will not require horizontal overflow handling; the existing `.table-scroll-wrapper` CSS class in `App.css` is sufficient.
  - Risk if false: Minor CSS work needed to add the wrapper or adjust the filter row styling.

- A4: The `SUPABASE_PAGE_SIZE` constant (1 000) defined in `dataService.js` is the correct chunk size to use for the RPC pagination loop, consistent with the rest of the data layer.
  - Risk if false: No risk — this is an internal constant and can be changed independently.

- A5: The `Report3` component currently holds all rows in a single `rows` state array; adding client-side filtering and pagination on top of that array without introducing `useMemo` or `useCallback` will not cause perceptible performance degradation for result sets up to ~50 000 rows.
  - Risk if false: `useMemo` should be added for sort/filter derivations (as in `FileRowsPanel`); this is low-effort and is already assumed to be included in the plan.

## Plan

### Task 1: Add paginated multi-pass RPC fetch for Report 3 in dataService.js
**Intent:** Replace the single-shot `supabase.rpc()` call in `fetchReport3` with a loop that chains `.range()` until all rows are fetched, removing the PostgREST `max_rows` cap.
**Inputs:** `react-app/src/lib/dataService.js` — `fetchReport3` and `fetchReport3Fallback` functions; `SUPABASE_PAGE_SIZE` constant; `fetchAllFileRows` as reference implementation.
**Outputs:** Modified `react-app/src/lib/dataService.js` — `fetchReport3` now paginates via `.range()` and `fetchReport3Fallback` drops `REPORT3_ROW_CAP`.
**External Interfaces:** Supabase `get_report_3_rows` RPC; PostgREST `.range()` support on RPC endpoints.
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in `.env`; no new config keys.
**Procedure:**
1. In `fetchReport3`, replace the single `executeLoggedQuery` call with a `while (!done)` loop that calls `supabase.rpc(REPORT_3_RPC, {...}).range(from, to)` and accumulates pages.
2. Keep error/fallback logic: if the first-page call returns an error, fall through to `fetchReport3Fallback`.
3. In `fetchReport3Fallback`, remove the `REPORT3_ROW_CAP` ceiling from the `while` loop condition and remove the `truncated` log flag.
4. Update the `REPORT3_ROW_CAP` constant comment to indicate it is no longer used and remove it, or remove the constant outright.
**Done Criteria:** `fetchReport3` issues multiple `.range()` calls when the first page returns exactly `SUPABASE_PAGE_SIZE` rows; returns the accumulated full array. `fetchReport3Fallback` no longer caps at 5 000 rows.
**Dependencies:** None.
**Risk Notes:** If PostgREST does not honour `.range()` on this RPC, the loop will never terminate for the edge case where row count is an exact multiple of `SUPABASE_PAGE_SIZE` (off-by-one on done detection). Guard: terminate when returned page is < `SUPABASE_PAGE_SIZE`.

---

### Task 2: Add client-side filter and pagination state to Report3.jsx
**Intent:** Add `useState` hooks and `useMemo` derivations for filter values, current page, and filtered/paginated row slices, mirroring the pattern in `FileRowsPanel`.
**Inputs:** `react-app/src/components/Report3.jsx`; `react-app/src/components/FileRowsPanel.jsx` as reference; `SUPABASE_PAGE_SIZE` constant replaced by local `PAGE_SIZE = 100`.
**Outputs:** Modified `react-app/src/components/Report3.jsx` — state hooks, `useMemo` for `filteredRows` and `displayedRows`, `totalPages`, reset effect.
**External Interfaces:** None (client-side only).
**Environment & Configuration:** None.
**Procedure:**
1. Add `PAGE_SIZE = 100` constant at module top.
2. Add state: `currentPage` (0-based), `filterValues` (object keyed by column keys, default empty strings).
3. Define `COLUMNS` array (7 entries matching current table columns) with `key` and `label` fields; initialize `filterValues` from `COLUMNS`.
4. Add a `useEffect` that resets `currentPage` and `filterValues` whenever `selectedCategory` or `selectedDate` changes.
5. Add a `useEffect` that resets `currentPage` to 0 when `filterValues` changes.
6. Derive `filteredRows` via `useMemo`: apply all non-empty filter values as case-insensitive substring matches on the display strings.
7. Derive `displayedRows` as `filteredRows.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)`.
8. Compute `totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE))`.
**Done Criteria:** Filtering and pagination state are correctly derived from `rows`; selecting a new category or date clears all filter inputs and resets to page 1.
**Dependencies:** Task 1 (rows array now contains complete result set).
**Risk Notes:** None.

---

### Task 3: Update Report3.jsx table markup with filter inputs and pagination bar
**Intent:** Render filter input row in `<thead>` and five-element pagination bar below the table, copying the established pattern from `FileRowsPanel.jsx`.
**Inputs:** Modified `react-app/src/components/Report3.jsx` from Task 2; `FileRowsPanel.jsx` pagination markup as reference.
**Outputs:** Modified `react-app/src/components/Report3.jsx` — updated JSX with filter row and pagination controls.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add a filter `<tr className="filter-row">` immediately after the header row in `<thead>`, with one `<th>` per column containing an `<input type="text">` with `aria-label`.
2. Replace `{rows.map(...)}` with `{displayedRows.map(...)}` in `<tbody>`.
3. Add a record count summary line: "Показани X от Y записа" above or below the table.
4. Add the five-element pagination bar (`«`, `‹`, `Страница N от M`, `›`, `»`) below the `</table>`, using existing `.pagination-controls`, `.pagination-btn`, `.pagination-btn--edge`, `.pagination-indicator` CSS classes already defined in `App.css`.
**Done Criteria:** Filter inputs and pagination bar render in the browser; filter narrows rows; pagination bar navigates pages; edge buttons disabled correctly.
**Dependencies:** Task 2.
**Risk Notes:** None. CSS classes are already defined; no new CSS needed.

---

### Task 4: Update Report3.test.jsx with filter and pagination assertions
**Intent:** Extend the existing test file to cover: filter input presence, filter narrows rows, pagination bar renders, page navigation works, category/date change resets state.
**Inputs:** `react-app/src/components/Report3.test.jsx`; `react-app/src/components/FileRowsPanel.test.jsx` as reference for test patterns.
**Outputs:** Modified `react-app/src/components/Report3.test.jsx`.
**External Interfaces:** None (Vitest + React Testing Library; all Supabase calls mocked).
**Procedure:**
1. Add test: filter inputs render for each column label.
2. Add test: typing in a filter input narrows the displayed rows.
3. Add test: pagination bar renders "Страница 1 от N" indicator.
4. Add test: clicking next page button increments the current page.
5. Add test: changing selectedCategory resets filter values.
**Done Criteria:** All new and existing tests pass under `npm test`.
**Dependencies:** Task 3.
**Risk Notes:** None.

---

### Task 5: Update dataService.test.js for paginated fetchReport3
**Intent:** Add a test verifying `fetchReport3` issues multiple `.rpc().range()` calls when the first page returns `SUPABASE_PAGE_SIZE` rows.
**Inputs:** `react-app/src/lib/dataService.test.js`; existing `fetchReport3` test block.
**Outputs:** Modified `react-app/src/lib/dataService.test.js`.
**External Interfaces:** Vitest mock of `supabase.rpc`.
**Procedure:**
1. Add test case: mock `supabase.rpc().range()` to return `SUPABASE_PAGE_SIZE` rows on first call and 5 rows on second call.
2. Call `fetchReport3(dateKey, categoryKey, dims)` and assert total returned row count is `SUPABASE_PAGE_SIZE + 5`.
3. Assert `supabase.rpc` was called twice with the correct `.range()` arguments.
**Done Criteria:** Test passes; `fetchReport3` pagination loop is verified.
**Dependencies:** Task 1.
**Risk Notes:** None.

---

### Task 6: Run full test suite and build
**Intent:** Verify all pre-existing and new tests pass and `npm run build` exits 0.
**Inputs:** All modified files from Tasks 1–5.
**Outputs:** Test pass confirmation; `react-app/dist/` build artifacts.
**External Interfaces:** Vitest test runner; Vite build.
**Environment & Configuration:** Node.js, npm; `.env` with Supabase credentials for build.
**Procedure:**
1. Run `npm test` from `react-app/` and confirm all tests pass.
2. Run `npm run build` from `react-app/` and confirm exit 0.
**Done Criteria:** No failing tests; build succeeds.
**Dependencies:** Tasks 1–5.
**Risk Notes:** None.

---

### Task 7: Update context.md and documentation
**Intent:** Record the changes made by this request in `.aib_memory/context.md`.
**Inputs:** `.aib_memory/context.md`; summary of changes from Tasks 1–6.
**Outputs:** Updated `.aib_memory/context.md`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Append a new update line to the auto-generated header in `context.md` noting the Report 3 filtering, pagination, and full-record-load changes.
2. Update the Report 3 description in the `Functional Capabilities` section of `context.md` to mention client-side filter, pagination, and full-load fetch.
**Done Criteria:** `context.md` reflects the new Report 3 behaviour.
**Dependencies:** Tasks 1–6 complete.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update Report 3 description to reflect per-column filter, pagination, and full-record multi-pass fetch; add update header line.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/lib/dataService.js` | Modified | Replace single-shot RPC call in `fetchReport3` with paginated loop; remove `REPORT3_ROW_CAP` ceiling from `fetchReport3Fallback`. |
| `react-app/src/components/Report3.jsx` | Modified | Add filter state, pagination state, `useMemo` derivations, filter input row in `<thead>`, and five-element pagination bar. |
| `react-app/src/components/Report3.test.jsx` | Modified | Add tests for filter UI, pagination UI, and state reset on category/date change. |
| `react-app/src/lib/dataService.test.js` | Modified | Add test for `fetchReport3` multi-page RPC pagination. |
| `.aib_memory/context.md` | Modified | Reflect Report 3 filter/pagination/full-load changes. |
| `react-app/src/components/FileRowsPanel.jsx` | Read-only dependency | Reference implementation for filter-row and pagination bar patterns. |
| `react-app/src/lib/dataService.js` (fetchAllFileRows) | Read-only dependency | Reference implementation for multi-pass paginated fetch pattern. |
| `react-app/src/App.css` | Read-only dependency | Provides `.pagination-controls`, `.pagination-btn`, `.pagination-btn--edge`, `.pagination-indicator`, `.filter-row` CSS classes; no changes needed. |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal, Scope, Constraints, and Success criteria are consistent with each other and traceable to the input.
- OK: `context.md` — Confirms Report 3 currently renders without pagination; confirms `FileRowsPanel` pattern is the established standard.
- Ambiguity: `input.md` — "filtering like the one in Файлове" could mean per-column filter inputs OR the category dropdown filter on the page level. Resolved as per-column filter inputs matching `FileRowsPanel` based on context (the category selector already exists; "filtering" refers to the table-level filter row).
- Missing info: `input.md` — Page size (rows per page) for pagination is not specified. Resolved by adopting `PAGE_SIZE = 100` consistent with `FileRowsPanel`.
- OK: `context.md` — PostgREST `max_rows` issue is previously documented (R-20260517-1244) and the fix pattern is established.
