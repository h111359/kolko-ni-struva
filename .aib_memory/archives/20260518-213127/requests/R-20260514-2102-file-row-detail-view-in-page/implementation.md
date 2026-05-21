Files taken into consideration:
- `.aib_memory/request.md` — authoritative source for scope, plan, and constraints
- `.aib_memory/context.md` — product context (updated as part of this implementation)
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-05-14 21:30

#### Scope
Implemented the file row detail drill-down feature for the Файлове (Files) page. Added `fetchFileRows` to `dataService.js`, created the new `FileRowsPanel.jsx` component, modified `FileDetailPage.jsx` to make file summary rows clickable, added `FileRowsPanel.test.jsx`, and updated `FileDetailPage.test.jsx` with click-through and close-behavior tests. Updated `context.md` to reflect the new capability.

#### Changes
- Added `fetchFileRows(fileKey, dims, pageIndex, pageSize)` exported function to `react-app/src/lib/dataService.js`: issues a HEAD-only COUNT, a paginated SELECT of all fact columns filtered by `file_key`, and a targeted `.in()` batch query for product names; enriches rows with category, store, company, and settlement names from cached dims; returns `{ rows, totalCount }`.
- Created `react-app/src/components/FileRowsPanel.jsx`: paginated 12-column fact-row table with loading state, error state, empty state, back button, and prev/next pagination; uses `table-scroll-wrapper` for mobile horizontal scroll; `PAGE_SIZE = 100`.
- Modified `react-app/src/components/FileDetailPage.jsx`: imported `FileRowsPanel`; added `selectedFile` state (null or `{ file_key, file_name, zip_date }`); updated `useEffect` to reset `selectedFile` on date change; added `onClick` and `cursor: pointer` to each summary `<tr>`; conditionally renders `FileRowsPanel` when `selectedFile` is non-null, passing `onClose={() => setSelectedFile(null)}`.
- Created `react-app/src/components/FileRowsPanel.test.jsx`: 8 unit tests covering loading state, column rendering, empty state, error state, close-button callback, next-page navigation, previous-page disabled state, and header content.
- Updated `react-app/src/components/FileDetailPage.test.jsx`: added `fetchFileRows` to the `vi.mock('../lib/dataService')` factory; added `fetchFileRows` to the `vi.mocked` setup in `beforeEach`; added T6 (click file row shows FileRowsPanel) and T7 (click back button restores summary table).
- Updated `.aib_memory/context.md`: added R-20260514-2102 update banner; updated Functional Capabilities item 7 React app description; updated `react-app/src/lib/dataService.js` module breakdown entry with `fetchFileRows`; updated `react-app/src/components/FileDetailPage.jsx` module breakdown entry; added new `react-app/src/components/FileRowsPanel.jsx` module breakdown entry.

#### Tests
- Unit, `react-app/src/components/FileRowsPanel.test.jsx` (8 tests, all pass): T1 loading indicator, T2 column rendering with enriched rows, T3 empty state, T4 error state, T5 close-button callback, T6 next-page pagination, T7 previous-page disabled, T8 header content.
- Unit, `react-app/src/components/FileDetailPage.test.jsx` (7 tests, all pass, 2 new): T6 click-through to FileRowsPanel, T7 close restores summary.
- Full suite `npm test` (react-app): 9 test files, 80 tests, 0 failures.

#### Outcome
All success criteria met. SC1: clicking a file row opens the detail panel. SC2: 12 columns rendered (product, category, settlement, store, company, retail, promo, effective, Д-1 retail, Д-1 promo, Д-2 retail, Д-2 promo). SC3: pagination with page size 100 supports large record counts. SC4: back button dismisses the panel. SC5: loading indicator shown while fetching. SC6: all new components and functions covered by unit tests with mocked Supabase. SC7: full test suite passes with no regressions.

#### Evidence
- Test run output:
```
Test Files  9 passed (9)
Tests       80 passed (80)
Duration    ...
```
- New files: `react-app/src/components/FileRowsPanel.jsx`, `react-app/src/components/FileRowsPanel.test.jsx`
- Modified files: `react-app/src/lib/dataService.js`, `react-app/src/components/FileDetailPage.jsx`, `react-app/src/components/FileDetailPage.test.jsx`, `.aib_memory/context.md`
