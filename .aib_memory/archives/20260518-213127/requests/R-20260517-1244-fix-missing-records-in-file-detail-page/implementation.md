Files taken into consideration:
- `.aib_memory/instructions.md` (empty)
- `.aib_memory/requests_register.md`
- `.aib_memory/request.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-05-18 12:00
#### Scope
Fix `FileRowsPanel.jsx` so that clicking a source file on the Файлове page loads **all** fact rows from `fact_prices_lookback`, not just the first 1 000 that the PostgREST `max_rows` cap silently returned. A new `fetchAllFileRows` function was added to `dataService.js` implementing the multi-page pagination loop. `FileRowsPanel.jsx` was updated to call `fetchAllFileRows` instead of the previous two-pass single-range pattern. Unit tests were extended to cover the multi-page path. `context.md` and `FileDetailPage.test.jsx` were updated to reflect the change.

#### Changes
- Added `fetchAllFileRows(fileKey, dims)` export to `react-app/src/lib/dataService.js`: issues one HEAD-only COUNT query, then loops through `SUPABASE_PAGE_SIZE` pages until all raw fact rows are accumulated, issues a single batch `dim_product .in()` lookup after all pages are collected, enriches all rows, and returns `{ rows, totalCount }`.
- Updated `react-app/src/components/FileRowsPanel.jsx`: replaced two-pass `useEffect` (Pass 1 count + Pass 2 single-range full-set call) with a single `fetchAllFileRows(fileKey, dims)` call; removed the `console.warn` about the PostgREST cap; updated file-level header and component JSDoc to reflect the new strategy.
- Updated `react-app/src/components/FileRowsPanel.test.jsx`: replaced `fetchFileRows` mock with `fetchAllFileRows` mock throughout all 21 existing tests; simplified two-pass mock setups (T6, T14, T15, T20, T21) to single-call mocks; updated T6 call-count assertion from 2 to 1; added T22 (2 500-row multi-page scenario, SC-4) and T23 (exactly 1 000 rows, no-regression).
- Updated `react-app/src/lib/dataService.test.js`: added `fetchAllFileRows` describe block with four tests: T-FAR-1 (3-page loop, 2 500 rows, single dim_product query), T-FAR-2 (single-page 500 rows), T-FAR-3 (empty file, no page or product queries), T-FAR-4 (error propagation).
- Updated `react-app/src/components/FileDetailPage.test.jsx`: replaced `fetchFileRows` mock with `fetchAllFileRows` mock; updated T6 call assertion to match new signature `(fileKey, dims)`.
- Updated `.aib_memory/context.md`: added `Updated by R-20260517-1244` header note; updated Functional Capabilities section 7 description of `FileRowsPanel` from "two-pass client-side fetch (count then full set)" to "paginated multi-pass client-side fetch (count, then SUPABASE_PAGE_SIZE chunks until all rows are loaded)".

#### Tests
- unit: `FileRowsPanel.test.jsx` T1–T21 (existing) — pass
- unit: `FileRowsPanel.test.jsx` T22 (2 500 rows, all displayed, 1 fetchAllFileRows call) — pass
- unit: `FileRowsPanel.test.jsx` T23 (exactly 1 000 rows, no truncation) — pass
- unit: `dataService.test.js` T-FAR-1 (multi-page loop, 2 500 rows, dim_product once) — pass
- unit: `dataService.test.js` T-FAR-2 (single-page, 500 rows) — pass
- unit: `dataService.test.js` T-FAR-3 (empty file, no extra queries) — pass
- unit: `dataService.test.js` T-FAR-4 (error propagation throws) — pass
- unit: `FileDetailPage.test.jsx` T6, T7 (fetchAllFileRows call signature) — pass
- build: `npm run build` from `react-app/` — exit 0

#### Outcome
Successful. All 106 tests pass (100 pre-existing + 6 new). `npm run build` exits 0. SC-1 through SC-5 are met: the PostgREST cap is bypassed by the page loop, no `console.warn` fires, multi-page tests cover files > 1 000 rows, single-page regression is confirmed, and the build is green. `fetchFileRows` is retained in `dataService.js` for backward compatibility (A3).

#### Evidence
- Test run output: 10 test files, 106 tests, 0 failures.
- Build output: `npm run build` exits 0, `react-app/dist/` produced.

#### Notes (Optional)
`fetchFileRows` is retained unchanged in `dataService.js` for backward compatibility per assumption A3. If the function is confirmed unused by other callers in a future cleanup pass, it can be removed then.
