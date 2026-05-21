## Goal

Replace the existing "Лог на заявки" (Query Log) navigation page with a new page that shows detail data per source file from `dim_file`. The new page should display per-file information about the source CSV files that contribute records to the dataset, using the selected date as context.

## Background

The "Лог на заявки" page was introduced in R-20260509-2012 as a debugging tool for developers to inspect browser-session Supabase request activity. It displays client-visible request metadata (not guaranteed exact backend SQL). With the persistent `backend_sql_audit_log` table in Supabase (introduced in R-20260509-2113), the in-browser log's primary diagnostic value for backend debugging has diminished. The product now calls for a more end-user-facing view: a page showing the source files (from `dim_file`) that make up the dataset — each file representing a company's daily price submission. This aligns with the existing `RecordDetailModal` which already surfaces file provenance per record in Report 2.

`dim_file` columns: `file_key` (surrogate key), `file_name` (company-and-UIC slug, e.g. `Лидл България_131071587.csv`), `zip_date` (ISO date of the source ZIP archive). The file map is already loaded in `fetchDimensions()` and cached in `dims.files`.

## Scope

- Remove the "Лог на заявки" nav button from `App.jsx` and its associated `<section>` render block.

- Remove `QueryLogPage.jsx` component file.

- Remove `QueryLogPage.test.jsx` test file.

- Add a new "Файлове" (Files) navigation page to `App.jsx` as the fifth nav item, replacing the Query Log slot.

- Create `FileDetailPage.jsx` component that:
  - Reads `dims.files` (Map<file_key, {file_name, zip_date}>) already available from `fetchDimensions()`.
  - Resolves the `zip_date` string for the selected date by looking up `dims.dates.find(d => d.date_key === selectedDate)?.date` — no lookback routing needed because files are filtered by the actual date selected, not by the fact table's date key.
  - Displays a table of source files for the selected date with at minimum: file name and file date (formatted as DD.MM.YYYY). Record count column is conditional on Q001 resolution.
  - Shows a no-data message when no files are found for the selected date.

- Create `FileDetailPage.test.jsx` with unit tests covering the core rendering paths.

- If Q001 resolves to add an RPC: add a `get_file_stats(p_date_key bigint)` PostgreSQL RPC function in `src/load_supabase.py` and a `fetchFileStats(dateKey, dims)` helper in `dataService.js` that calls the RPC and returns per-file row counts.

## Out of scope

- Removing the `queryLog.js` module or its instrumentation calls in `dataService.js` — the session logging infrastructure may have future use and is not referenced by the removed page only (it still supports the backend audit log indirectly via the developer's mental model). Removing it would require touching `dataService.js` heavily and is not part of this request.

- Adding drilldown capability to the file detail page (e.g. clicking a file to see its individual records).

- Changes to `src/load_supabase.py` or any backend ETL scripts.

- Changes to `RecordDetailModal.jsx` or any other existing report components.

- Adding a Supabase RPC function for per-file counts — client-side aggregation from `fact_prices_lookback` is acceptable for this view given the file count per date is typically small (< 200 files).

## Constraints

- The React app is client-only (no serverless functions); all data comes from Supabase via `@supabase/supabase-js` v2.
- The `queryLog.js` module MUST remain intact; only the UI page referencing it is removed.
- The new page MUST respect the responsive layout conventions from `App.css` (≤ 900px tablet, ≤ 600px mobile breakpoints).
- The new page MUST use the globally selected date (`selectedDate` prop) for filtering, consistent with how other report pages behave.
- No credentials hardcoded in source files; env vars use `VITE_` prefix.
- `npm run build` must continue to exit 0 and produce `dist/` after changes.
- The app must continue to show exactly five nav buttons after this change.

## Success criteria

- SC-1: The "Лог на заявки" nav button no longer appears in the rendered app.
- SC-2: `QueryLogPage.jsx` and `QueryLogPage.test.jsx` are deleted from the workspace.
- SC-3: A "Файлове" (or equivalent Bulgarian label for Files) nav button appears in the nav bar as the fifth button.
- SC-4: Navigating to the new page displays a table of source files for the selected date, with file name, date, and record count columns.
- SC-5: When no files exist for the selected date, a user-facing no-data message is shown instead of an empty table.
- SC-6: `npm run build` exits 0 after all changes.
- SC-7: `npm run test` passes with no regressions; `QueryLogPage.test.jsx` tests are replaced by `FileDetailPage.test.jsx` tests.
- SC-8: `queryLog.js` is not modified and its exports remain intact.

## Assumptions

- A1: Each date has fewer than 200 unique source files in `dim_file`. Based on observed dim_file data and the typical number of Bulgarian retail reporting companies, the per-date file list fits in a single browser render without pagination.
  - Risk if false: File list could require pagination or virtual scrolling to remain usable.

- A2: `zip_date` values in `dim_file` correspond exactly to the `date` strings in `dim_date` for all three selectable dates (D, D-1, D-2). Filtering `dims.files` by `zip_date === selectedDateStr` (where `selectedDateStr` is from `dims.dates`) correctly isolates files for the selected date.
  - Risk if false: If `zip_date` formats differ from `dim_date.date` formats (e.g. time zone offset), filtering would produce empty results; a normalisation step would be needed.

- A3: The `queryLog.js` module and all its call sites in `dataService.js` remain untouched. The removal of `QueryLogPage.jsx` leaves `queryLog.js` as active-but-UI-less infrastructure, which is intentional.
  - Risk if false: None expected; keeping the module does not break any functionality.

- A4: The file name format in `dim_file.file_name` is `<display_name>_<UIC>.csv`. Displaying the raw `file_name` is acceptable for the first iteration; no parsing or transformation is required.
  - Risk if false: If file names contain characters that break table layout, additional sanitisation may be needed.

## Plan

### Task 1: Remove Query Log page from App
**Intent:** Delete the Query Log component files and strip all references from App.jsx.
**Inputs:** `react-app/src/App.jsx`, `react-app/src/components/QueryLogPage.jsx`, `react-app/src/components/QueryLogPage.test.jsx`
**Outputs:** `QueryLogPage.jsx` deleted; `QueryLogPage.test.jsx` deleted; `App.jsx` updated (import removed, `PAGES.QUERY_LOG` removed, nav button removed, `<section>` block removed).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Delete `react-app/src/components/QueryLogPage.jsx`.
2. Delete `react-app/src/components/QueryLogPage.test.jsx`.
3. Remove the `QueryLogPage` import from `App.jsx`.
4. Remove the `QUERY_LOG: 'query-log'` entry from the `PAGES` constant in `App.jsx`.
5. Remove the `{ page: PAGES.QUERY_LOG, label: '🧪 Лог на заявки' }` nav entry.
6. Remove the `<section ... id="query-log">` block rendering `<QueryLogPage />`.
**Done Criteria:** `QueryLogPage.jsx` and `QueryLogPage.test.jsx` do not exist; `App.jsx` has no reference to `QueryLogPage` or `PAGES.QUERY_LOG`; `npm run build` exits 0.
**Dependencies:** None.
**Risk Notes:** Removing the import will cause a build error if any other file imports `QueryLogPage` — scan before deletion.

### Task 2: Create File Detail page component
**Intent:** Build `FileDetailPage.jsx` that lists source files for the selected date from `dims.files`.
**Inputs:** `react-app/src/App.jsx` (prop contract reference), `react-app/src/lib/dataService.js` (helper reference), `dims.files` Map, `dims.dates` array, `selectedDate` integer prop.
**Outputs:** `react-app/src/components/FileDetailPage.jsx` (new file).
**External Interfaces:** Supabase `fact_prices_lookback` only if Q001 resolves to Option B (RPC for record counts); otherwise no new Supabase queries.
**Environment & Configuration:** None beyond existing `VITE_SUPABASE_*` env vars.
**Procedure:**
1. Resolve the `zip_date` string from `dims.dates` for the current `selectedDate`.
2. Filter `dims.files` entries by `zip_date === selectedDateStr` to obtain the list of files to display.
3. Render a table with columns: file name (`file_name`), date (formatted via `formatDateBG`), and record count if Q001 resolves to Option B.
4. Show a no-data message when no files match the selected date.
5. Apply `.report-section` and `.results-table` CSS classes for styling consistency.
**Done Criteria:** Component renders without errors; shows file rows for a date with data; shows no-data message for a date without data.
**Dependencies:** Task 1 (App.jsx slot available).
**Risk Notes:** If `dims.dates` does not contain the selected `date_key`, `selectedDateStr` resolves to `undefined` and no files are shown — this is correct no-data behaviour.

### Task 3: Wire File Detail page into App.jsx
**Intent:** Add the new Files page to App.jsx navigation and rendering pipeline.
**Inputs:** `react-app/src/App.jsx`, `react-app/src/components/FileDetailPage.jsx`.
**Outputs:** `react-app/src/App.jsx` updated (new `FILES` page constant, new nav button, new `<section>` block).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add `FILES: 'files'` to the `PAGES` constant.
2. Import `FileDetailPage` from `./components/FileDetailPage`.
3. Add `{ page: PAGES.FILES, label: '📁 Файлове' }` to the nav array.
4. Add a `<section ... id="files">` block rendering `<FileDetailPage selectedDate={selectedDate} dimensions={dimensions} />` when `dimensions && selectedDate`.
**Done Criteria:** Clicking the "Файлове" nav button shows the Files page; the app has exactly five nav buttons.
**Dependencies:** Task 1, Task 2.
**Risk Notes:** None.

### Task 4: Automated tests for File Detail page
**Intent:** Create `FileDetailPage.test.jsx` covering the core rendering paths from the Testing section.
**Inputs:** `react-app/src/components/FileDetailPage.jsx`, `react-app/src/App.jsx`.
**Outputs:** `react-app/src/components/FileDetailPage.test.jsx` (new file); `react-app/src/App.test.jsx` updated if Query Log removal breaks existing assertions.
**External Interfaces:** None (all Supabase calls mocked).
**Environment & Configuration:** Vitest, `@testing-library/react`.
**Procedure:**
1. Write tests T1–T5 (FileDetailPage renders, empty dims.files, no-match date, file rows, date resolution).
2. Update `App.test.jsx` to remove any assertions on the Query Log nav label and verify the Files nav label.
3. Run `npm run test` and verify all pass.
**Done Criteria:** `npm run test` exits 0; no tests reference deleted `QueryLogPage`.
**Dependencies:** Task 1, Task 2, Task 3.
**Risk Notes:** Existing `App.test.jsx` may reference nav labels — check and update.

### Task 5: Update documentation
**Intent:** Reflect the page replacement in context.md and any affected documentation files.
**Inputs:** `.aib_memory/context.md`, `README.md`.
**Outputs:** `.aib_memory/context.md` updated; `README.md` updated if applicable.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In `context.md`, replace all references to the Query Log page ("Лог на заявки") with the new Files page ("Файлове").
2. Update the `## Requirements Summary` functional capability 7 to reflect the page swap.
3. Update the `## Technical Design` module descriptions to remove `QueryLogPage.jsx` consumer references and add `FileDetailPage.jsx`.
4. Scan `README.md` for any mentions of the Query Log page and update if found.
**Done Criteria:** `context.md` no longer mentions "Лог на заявки" as a nav page; "Файлове" page is described.
**Dependencies:** Task 1, Task 2, Task 3.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update all references to five-page nav to replace "Лог на заявки" with "Файлове"; update functional capability 7 and module breakdown descriptions.
- `README.md` (ref_id: N/A) — Remove or update any reference to the Query Log page if present.

## Questions & Decisions

**Q001**: The request scope describes showing "a record count per file from `fact_prices_lookback`". Analysis shows client-side aggregation is infeasible at production scale (~1M rows per date → ~1,000 Supabase paginated round-trips). How should record counts be handled?
- [ ] Option A: Omit the record count column entirely; show only file name and date *(recommended)*
- [ ] Option B: Add a new `get_file_stats(p_date_key bigint)` PostgreSQL RPC function to push the COUNT(*) GROUP BY to Supabase and expose it via a `fetchFileStats` helper in `dataService.js`
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/components/QueryLogPage.jsx` | Deleted | Query Log page is removed per request |
| `react-app/src/components/QueryLogPage.test.jsx` | Deleted | Tests for the removed page |
| `react-app/src/components/FileDetailPage.jsx` | Created | New file detail page component |
| `react-app/src/components/FileDetailPage.test.jsx` | Created | Tests for the new file detail page |
| `react-app/src/App.jsx` | Modified | Remove PAGES.QUERY_LOG, add PAGES.FILES, swap nav button and section |
| `react-app/src/App.test.jsx` | Modified | Update nav button count and label assertions to reflect page swap |
| `react-app/src/lib/dataService.js` | Modified (conditional) | Add `fetchFileStats` helper only if Q001 resolves to Option B |
| `src/load_supabase.py` | Modified (conditional) | Add `get_file_stats` RPC only if Q001 resolves to Option B |
| `.aib_memory/context.md` | Modified | Reflect page swap in product context documentation |
| `README.md` | Read-only dependency | Scan for references to Query Log page; update if found |
| `react-app/src/lib/queryLog.js` | Read-only dependency | Retained; not modified; still used by dataService.js |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal is concise and actionable; clearly specifies both the removal and the addition.
- Ambiguity: `request.md` § Scope — Original statement about using `dims.lookbackColumnMap` and `dims.currentDateKey` for file filtering was incorrect; corrected during analysis. The file list is filtered by the date string of the selected date directly from `dims.dates`.
- Ambiguity: `request.md` § Scope — "record count per file from `fact_prices_lookback`" conflicts with the "no new RPC" Out of Scope constraint at production data volumes. Q001 raised to resolve.
- OK: `context.md` — Accurately reflects five-page nav including "Лог на заявки"; will need update after implementation.
- OK: `context.md` — `dims.files` Map is described as already loaded at startup; consistent with the file detail page implementation approach.
- Cross-ref issue: `request.md` § Success criteria SC-7 — References `QueryLogPage.test.jsx` being replaced; if Q001 resolves to Option B, `dataService.js` tests may also need updating — not explicitly listed in SC-7.
- Missing info: `request.md` § Scope — No explicit statement about loading state when Q001 = Option A (no counts). Clarified by assumption: if Option A, no loading state is needed since all file data is already in `dims.files`.
