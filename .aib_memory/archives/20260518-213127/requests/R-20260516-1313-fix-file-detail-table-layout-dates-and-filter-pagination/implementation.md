Files taken into consideration:
- `.aib_memory/request.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/coding-css-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `react-app/src/components/FileRowsPanel.jsx`
- `react-app/src/App.css`
- `react-app/src/components/FileRowsPanel.test.jsx`
- `react-app/src/components/FileDetailPage.test.jsx`

## Implementation Log

### Entry 2026-05-16 08:45
#### Scope
Three usability defects fixed in `FileRowsPanel`: (1) day1/day2 column headers now show actual calendar dates in DD.MM.YYYY format from `dims.dates`; (2) all rows for the selected file are loaded in a two-pass client-side fetch so filtering and pagination span the complete row set; (3) compact scoped CSS class `.file-rows-table` (reduced padding, font-size, text wrapping) makes the 12-column table fit within ~1200px without horizontal overflow. Automated tests updated and two new tests added. `context.md` updated.

#### Changes
- Modified `react-app/src/components/FileRowsPanel.jsx`: removed module-level `COLUMNS` and `INITIAL_FILTER_VALUES` constants; added pure `buildColumns(dates)` function that derives day1/day2 column labels from `formatDateBG(dims.dates[1]?.date)` and `formatDateBG(dims.dates[2]?.date)` with '—' fallback; added `const columns = useMemo(() => buildColumns(dims.dates), [dims])` inside component; changed `filterValues` initial state to use `buildColumns([])` key derivation; replaced single-pass server-paginated fetch with two-pass approach (pass 1 fetches 1 row for `totalCount`, pass 2 fetches `range(0, totalCount-1)` for all rows); removed `currentPage` from fetch effect dependency array; added `useEffect` watching `filterValues` to reset `currentPage` to 0 on filter changes; derived `totalPages` from `Math.ceil(filteredRows.length / PAGE_SIZE)` and `displayedRows` from `filteredRows.slice(currentPage * PAGE_SIZE, ...)` (previously `filteredRows` rendered directly); replaced `<div className="table-scroll-wrapper"><table className="results-table">` with `<table className="results-table file-rows-table">` (removed scroll wrapper div from the detail panel); updated all `COLUMNS` references in `sortedRows`, `filteredRows` and JSX to use `columns`; added `console.warn` for A1 risk (PostgREST truncation detection); updated file-level header comment.
- Modified `react-app/src/App.css`: added `> Updated in R-20260516-1313` note to file header; added `/* File Rows Detail Table (compact layout) */` section with `.file-rows-table th` (padding 6px 8px, font-size 0.8em, white-space normal) and `.file-rows-table td` (padding 5px 8px, font-size 0.8em, white-space normal, word-break break-word) rules after the filter-row block; added `.file-rows-table th input { min-height: 44px; }` inside `@media (max-width: 600px)`.
- Modified `react-app/src/components/FileRowsPanel.test.jsx`: updated file-level header comment to reference R-20260516-1313; added `dates` array to `makeStubDims()` (dates[0]='2026-05-15', dates[1]='2026-05-14', dates[2]='2026-05-13'); updated T2 to assert date-bearing column labels ('Цена 14.05.2026 (лв)', 'Промо 14.05.2026 (лв)', 'Цена 13.05.2026 (лв)', 'Промо 13.05.2026 (лв)'); rewrote T6 to use `mockResolvedValueOnce` twice (pass 1 count + pass 2 all rows), assert 2 initial fetchFileRows calls, clear mock, click next, assert 0 additional calls and 'Страница 2 от 2'; updated T8 assertion from regex `/13\.05\.2026/` to exact string `'13.05.2026'` to avoid ambiguity with same date in column labels; added T14 (filter reduces page count across all loaded rows) and T15 (applying filter while on page 2 resets to page 1).
- Modified `react-app/src/components/FileDetailPage.test.jsx`: updated T6 assertion from `toHaveBeenCalledWith(1, expect.anything(), 0, 100)` to `toHaveBeenCalledWith(1, expect.anything(), 0, 1)` to match the new two-pass pass-1 call signature.
- Updated `.aib_memory/context.md`: added R-20260516-1313 update note to auto-generated header block; updated Functional Capabilities item 7 to describe two-pass client-side loading, date-bearing column headers, filter spanning all rows, and `.file-rows-table` compact CSS.

#### Tests
- unit: FileRowsPanel T1–T15 (Vitest) — all 15 pass
- unit: FileDetailPage T1–T7 (Vitest) — all 7 pass
- unit: App.test.jsx (8 tests) — pass
- unit: dataService.test.js (30 tests) — pass
- unit: Report1/2/3, RecordDetailModal, HomePage tests — all pass
- build: `npm run build` in `react-app/` — exits 0, dist/index.html produced

#### Outcome
All success criteria met. SC-1: compact `.file-rows-table` CSS removes horizontal overflow at ~1200px. SC-2: day1/day2 headers show actual calendar dates from `dims.dates`. SC-3/SC-4/SC-5: filter and pagination now operate across all loaded rows; page resets to 1 on filter change. SC-6: `npm run build` exits 0. SC-7: 87 tests pass, 0 failures.

#### Evidence
- Test run output:
```
 ✓ src/components/FileDetailPage.test.jsx (7 tests)
 ✓ src/App.test.jsx (8 tests)
 ✓ src/components/FileRowsPanel.test.jsx (15 tests)
 ✓ src/components/Report2.test.jsx (8 tests)
 ✓ src/components/RecordDetailModal.test.jsx (9 tests)
 ✓ src/lib/dataService.test.js (30 tests)
 ✓ src/components/Report1.test.jsx (4 tests)
 ✓ src/components/Report3.test.jsx (3 tests)
 ✓ src/components/HomePage.test.jsx (3 tests)
 Test Files  9 passed (9)
       Tests  87 passed (87)
```
- Build output:
```
vite v5.4.21 building for production...
✓ 82 modules transformed.
dist/index.html  0.55 kB │ gzip: 0.40 kB
dist/assets/index-Bi8hley1.css  8.32 kB │ gzip: 2.28 kB
dist/assets/index-BWlgrPIo.js  377.73 kB │ gzip: 107.81 kB
✓ built in 2.25s
```
