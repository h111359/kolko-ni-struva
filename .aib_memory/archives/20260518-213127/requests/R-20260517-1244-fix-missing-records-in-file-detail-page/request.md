## Goal

Fix the `Файлове` (Files) page in the React app so that clicking a file opens a `FileRowsPanel` that loads and displays **all** records for that file from `fact_prices_lookback`. Currently the panel returns only the first subset of records due to a silent PostgREST row-count cap, making large files appear to have fewer records than stated in the summary row count.

## Background

`FileRowsPanel.jsx` uses a two-pass fetch strategy introduced in R-20260516-1313: Pass 1 fetches one row to obtain `totalCount`; Pass 2 calls `fetchFileRows(fileKey, dims, 0, count)` to load all rows in a single request by using `count` as the `pageSize`. In `fetchFileRows`, this translates to a single Supabase PostgREST call with `.range(0, count-1)`. Supabase's hosted PostgREST enforces a server-side `max_rows` cap (default 1000) regardless of the explicit `Range` header. For files with more than 1000 rows the response is silently capped at 1000 rows, while `totalCount` remains accurate (it comes from a HEAD-only `count: exact` query unaffected by `max_rows`). The result is a visible inconsistency: the summary table shows, say, 3 000 records, but the drill-down panel shows only 1 000. No error is raised in the UI; only a `console.warn` is emitted.

The `fetchAllRows` utility in `dataService.js` already demonstrates the correct pagination pattern (loop using `SUPABASE_PAGE_SIZE = 1000`), but it is not used for file-row loading.

## Scope

- Replace the single-request full-load in `FileRowsPanel.jsx`'s `useEffect` (Pass 2) with a multi-page loop that pages through all rows in `SUPABASE_PAGE_SIZE` chunks, OR delegate the multi-page logic to `dataService.js` via a new exported function.

- Keep `totalCount` sourced from a separate HEAD-only COUNT query (no change to Pass 1 semantics).

- Batch the `dim_product` lookup across all loaded rows in a single `.in()` call (not per page) to avoid N product-lookup queries.

- Update or add unit tests covering the multi-page scenario and the existing single-page path.

- Update `.aib_memory/context.md` to reflect the fix.

## Out of scope

- Changes to how the `Файлове` page filters files by date (D, D-1, D-2 date selection behaviour).
- Changes to `fetchFileStats` (file summary row counts in the list view).
- Any changes to `FileDetailPage.jsx`, `FileRowDetailModal.jsx`, pagination UI, sort, or filter logic — only the data-loading path changes.
- Changes to `load_supabase.py`, ETL pipeline, or the PostgREST `max_rows` server configuration.
- Adding a `file_key_day1` / `file_key_day2` column to track which files contributed D-1/D-2 prices.

## Constraints

- The fix MUST NOT change the shape of data returned by `fetchFileRows` (backward-compatible); existing callers and tests of `fetchFileRows` must continue to pass.
- The fix MUST remain within the client-only React app (`react-app/src/`); no server-side changes.
- `SUPABASE_PAGE_SIZE = 1000` (already defined in `dataService.js`) MUST be used as the page size for all Supabase paginated reads to stay within the PostgREST default cap.
- All Supabase reads MUST continue to flow through `executeLoggedQuery` for session query-log coverage.
- `npm run build` MUST exit 0 after the fix.
- Existing passing tests MUST NOT be broken.

## Success criteria

- SC-1: For a file with more than 1 000 rows in `fact_prices_lookback`, `FileRowsPanel` displays all rows (row count in panel matches `totalCount` from Pass 1).
- SC-2: For a file with ≤ 1 000 rows, behaviour is unchanged (no regression).
- SC-3: The `console.warn` about PostgREST cap no longer fires for normal file loads.
- SC-4: Automated unit tests cover the multi-page fetch path (e.g., mocking a 2 500-row file spread across three pages).
- SC-5: `npm run build` exits 0.

## Assumptions

- A1: The Supabase project's PostgREST `max_rows` setting is 1 000 (the hosted Supabase default). The multi-page loop fix is correct regardless of the exact cap value.
  - Risk if false: If `max_rows` is actually higher (e.g., 10 000), the bug may not manifest for small files but the fix is still architecturally correct and safe.

- A2: `fact_prices_lookback` contains only rows for the current date D. Filtering by `file_key` alone (no `date_key` filter) is correct and complete for the Файлове page use case.
  - Risk if false: If `fact_prices_lookback` ever held rows for multiple dates, filtering by `file_key` alone would return more rows than intended; ruled out by the ETL truncate-and-reinsert design.

- A3: `fetchFileRows` is used only by `FileRowsPanel`; a new `fetchAllFileRows` function will be added to `dataService.js` while `fetchFileRows` is retained for backward compatibility and test isolation.
  - Risk if false: If other callers of `fetchFileRows` exist and are missed, removing it would break them. Retaining it is safe.

- A4: All `FileRowsPanel.test.jsx` tests currently pass before the change; the existing `fetchFileRows` mock will be supplemented with a `fetchAllFileRows` mock after the function is added.
  - Risk if false: If existing tests are already failing, the test baseline is undefined and Task 3 results may be misleading.

## Plan

### Task 1: Add `fetchAllFileRows` to `dataService.js`
**Intent:** Create a new exported function that fetches all fact rows for a given `file_key` across multiple PostgREST pages and returns the fully enriched row set together with the total count.
**Inputs:** `react-app/src/lib/dataService.js`; `SUPABASE_PAGE_SIZE` constant; `executeLoggedQuery`, `calculatePrice` helpers.
**Outputs:** `react-app/src/lib/dataService.js` with a new `fetchAllFileRows(fileKey, dims)` export.
**External Interfaces:** Supabase `fact_prices_lookback` (HEAD count + paginated SELECT); Supabase `dim_product` (single batch `.in()` query for all unique product keys).
**Environment & Configuration:** React app dev/prod environment; `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` env vars; Supabase anon key.
**Procedure:**
1. Add `fetchAllFileRows(fileKey, dims)` after `fetchFileRows` in `dataService.js`.
2. Issue one HEAD-only COUNT query (same as Pass 1 in `fetchFileRows`) to obtain `totalCount`.
3. Loop with `SUPABASE_PAGE_SIZE` page size until all raw fact rows are accumulated (same pattern as `fetchAllRows`).
4. After the loop, collect all unique `product_key` values and issue a single `dim_product .in()` lookup.
5. Enrich all rows with dimension names and `calculatedPrice`.
6. Return `{ rows, totalCount }`.
**Done Criteria:** `fetchAllFileRows` is exported; called with a mocked 2 500-row dataset it returns all 2 500 rows; `dim_product` lookup called once.
**Dependencies:** None.
**Risk Notes:** If `file_key` has no index, each paginated SELECT is a sequential scan; acceptable for correctness fix; performance improvement via index is a separate follow-up.

### Task 2: Update `FileRowsPanel.jsx` to use `fetchAllFileRows`
**Intent:** Replace the two-pass useEffect with a single `fetchAllFileRows` call, removing the now-unnecessary `console.warn` about the PostgREST cap.
**Inputs:** `react-app/src/components/FileRowsPanel.jsx`; `fetchAllFileRows` from Task 1.
**Outputs:** `react-app/src/components/FileRowsPanel.jsx` (updated import, simplified useEffect).
**External Interfaces:** `fetchAllFileRows` from `dataService.js`.
**Environment & Configuration:** Same as Task 1.
**Procedure:**
1. Add `fetchAllFileRows` to the import from `../lib/dataService`.
2. Replace the two-pass useEffect logic with a single `fetchAllFileRows(fileKey, dims)` call that sets `rows` and `totalCount` from the result.
3. Remove the `console.warn` about the PostgREST cap (it is no longer applicable).
4. Ensure `loading`, `error`, and cancellation logic remain intact.
**Done Criteria:** SC-1 (all rows shown), SC-3 (no console.warn); component renders correctly for a file with > 1 000 rows.
**Dependencies:** Task 1.
**Risk Notes:** Existing tests mock `fetchFileRows`; after this change they must mock `fetchAllFileRows` instead — handled in Task 3.

### Task 3: Update tests to cover the multi-page path
**Intent:** Extend `FileRowsPanel.test.jsx` (and add `dataService.test.js` cases if needed) to cover multi-page loading, edge cases, and error propagation.
**Inputs:** `react-app/src/components/FileRowsPanel.test.jsx`; `react-app/src/lib/dataService.test.js`.
**Outputs:** Updated test files covering T1–T6, T9 (manual — UAT_scenarios.md).
**External Interfaces:** Vitest mock of `fetchAllFileRows`.
**Environment & Configuration:** Vitest + @testing-library/react.
**Procedure:**
1. Update the `vi.mock` in `FileRowsPanel.test.jsx` to export `fetchAllFileRows` instead of (or in addition to) `fetchFileRows`.
2. Update existing tests to use the new mock.
3. Add T2 test: mock returns 2 500 rows (e.g., resolved in one call for simplicity in unit test), assert all 2 500 displayed.
4. Add T3 test: mock returns exactly 1 000 rows, assert 1 000 displayed.
5. Add T5 test: mock rejects, assert error state.
6. Add `dataService.test.js` test for `fetchAllFileRows` covering the multi-page loop (2 pages of 1 000 + 1 page of 500).
**Done Criteria:** SC-4 satisfied; `npm test` exits 0.
**Dependencies:** Task 1, Task 2.
**Risk Notes:** None.

### Task 4: Run test suite and build validation
**Intent:** Confirm SC-4, SC-5 — all tests pass and the production build succeeds.
**Inputs:** `react-app/` directory.
**Outputs:** Test run summary; build output in `react-app/dist/`.
**External Interfaces:** Vitest, Vite build.
**Environment & Configuration:** Node.js; `npm` in `react-app/`.
**Procedure:**
1. Run `npm test` from `react-app/`; confirm exit 0.
2. Run `npm run build` from `react-app/`; confirm exit 0 and `dist/` produced.
**Done Criteria:** SC-5 (`npm run build` exits 0); T7 (`npm test` exits 0).
**Dependencies:** Task 3.
**Risk Notes:** If build or tests fail, diagnose and fix before proceeding.

### Task 5: Update documentation
**Intent:** Reflect the corrected loading strategy in `context.md` so downstream AIB runs have accurate product context.
**Inputs:** `.aib_memory/context.md`.
**Outputs:** Updated `.aib_memory/context.md`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In `context.md` Functional Capabilities section 7, update the `FileRowsPanel` description: replace "two-pass client-side fetch (count then full set)" with "paginated multi-pass client-side fetch (count, then SUPABASE_PAGE_SIZE chunks until all rows are loaded)".
2. Add an `Updated by R-20260517-1244` note at the top of the document.
**Done Criteria:** `context.md` accurately describes the fixed loading strategy.
**Dependencies:** Task 4 (update after confirmed fix).
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update Functional Capabilities section 7 to reflect the multi-page pagination strategy replacing the single-range full-set call in `FileRowsPanel`; add `Updated by R-20260517-1244` header note.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

- `react-app/src/components/FileRowsPanel.jsx` — two-pass `useEffect` where Pass 2 makes the single oversized range call; this is the primary change site.
- `react-app/src/lib/dataService.js` — `fetchFileRows` function (existing server-side pagination function); a new `fetchAllFileRows` export will likely be added here, OR the Pass 2 loop will move into `FileRowsPanel`.
- `react-app/src/components/FileRowsPanel.test.jsx` — must be extended with a multi-page scenario test.
- `react-app/src/lib/dataService.test.js` — may need a `fetchAllFileRows` test if the function is added.
- `react-app/src/lib/dataService.js` constant `SUPABASE_PAGE_SIZE = 1000` — referenced by the new pagination loop.
- `.aib_memory/context.md` — requires update to reflect the corrected loading strategy.

## Internal Review of Request and Product Docs

- Context.md records the two-pass approach introduced in R-20260516-1313 as "count then full set via `range(0, totalCount-1)`". After this fix, the description should be updated to "count then paginated full set via `SUPABASE_PAGE_SIZE` chunks".
- The `console.warn` in `FileRowsPanel.jsx` (lines ~147-151) was added as a safety net for exactly this scenario; it can be retained or removed after the fix is confirmed.
- No conflicts found with existing closed requests.
