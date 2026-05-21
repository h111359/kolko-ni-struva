# Analysis — R-20260518-1052: Add filter, pagination, and full record load to Compare page

## Executive Summary

- **Request ID:** R-20260518-1052

- **Request title:** Add filter, pagination, and full record load to Compare page

- **High-level purpose:** Bring the "🗺️ Сравнение по места" (Report 3) page to feature parity with the "📁 Файлове" page by: (a) fixing silent result-set truncation caused by PostgREST's `max_rows` default cap, (b) adding per-column substring filter inputs, and (c) adding a five-element client-side pagination bar.

- **Root cause of the bug:** `fetchReport3` in `dataService.js` issues a single `supabase.rpc()` call with no `.range()` pagination. PostgREST silently caps responses at 1 000 rows by default (`max_rows` setting). The fallback path adds a further hard ceiling of 5 000 rows (`REPORT3_ROW_CAP`). Neither path guarantees full result coverage for large categories.

- **Established fix pattern:** The identical problem was solved for the `FileRowsPanel` component in R-20260517-1244 by introducing `fetchAllFileRows`, a paginated multi-pass loop using `.range()`. This request applies the same loop to the `fetchReport3` RPC path and removes the fallback cap.

- **UI pattern source:** Per-column filter inputs and the five-element pagination bar are copied from `FileRowsPanel.jsx`, which already defines the canonical client-side table interaction pattern for this codebase.

- **Scope summary:** Three files modified (`dataService.js`, `Report3.jsx`, test files), no schema or RPC changes, no new npm dependencies, no CSS additions required (all needed classes already exist in `App.css`).

- **`request.md` updates in this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` were written/replaced. `## Questions & Decisions` is empty (no blocking ambiguities above threshold 3).

---

## Domain Knowledge Essentials

**Retail price fact row:** A single observed price for one product at one store on one date, captured in `fact_prices_lookback`. Each row carries surrogate keys for product, category, store, settlement, company, and file, plus retail and promo price columns for the current date and two lookback days.

**Category (Категория):** A product classification hierarchy level. In Report 3 the user picks one category and sees all price facts across all settlements and stores for that category. Popular categories (e.g., bread, dairy) can have tens of thousands of rows per date.

**Settlement (Населено място):** A Bulgarian administrative settlement identified by EKATTE code. Report 3 spans all settlements for the chosen category — no settlement pre-filter is applied, unlike Report 2.

**PostgREST `max_rows`:** A server-side safety limit on Supabase's PostgREST layer that caps the maximum number of rows returned per HTTP response. The Supabase-hosted default is 1 000. Clients must use `Range` headers (exposed via `.range(from, to)` in the JS client) to page through larger result sets.

**Affected business process:** Public-facing price analytics. End users comparing prices across settlements for large categories currently see a silently incomplete table, which undermines the product's core value proposition of transparent price comparison.

**Primary actor:** End users of the Netlify-hosted React app who use Report 3 to compare prices across cities for a selected product category.

---

## Technical Knowledge & Terms

**Technologies and components involved:**
- React 18 + Vite SPA (`react-app/`), deployed to Netlify.
- `@supabase/supabase-js` v2 — client library; supports `.range(from, to)` chaining on both table `.select()` and `.rpc()` calls.
- `get_report_3_rows` — existing PostgreSQL RPC function provisioned by `src/load_supabase.py`; returns enriched rows for a given `(date_key, category_key, price_offset)` triple.
- `dataService.js` — module-scoped data-fetching layer; `fetchReport3` and `fetchReport3Fallback` are the functions under change.
- `Report3.jsx` — the React component that renders category selector, loading state, and results table.
- `App.css` — global stylesheet; already contains `.pagination-controls`, `.pagination-btn`, `.pagination-btn--edge`, `.pagination-indicator`, `.filter-row`, `.filter-row th`, `.filter-row th input` classes.

**Data model / runtime constraints:**
- `fact_prices_lookback` is the sole fact table in Supabase; `get_report_3_rows` queries it with `date_key`, `category_key`, and a price-offset string.
- `SUPABASE_PAGE_SIZE = 1000` is the existing page-chunk constant in `dataService.js`; it is reused as the chunk size for the new pagination loop.
- `dim_product` is not returned inline by `get_report_3_rows`; the RPC already returns `product_name` in its result set, so no additional `.in()` batch query is needed for Report 3 (unlike the fallback path).

**Key terms:**
- **`REPORT3_ROW_CAP`:** A 5 000-row ceiling applied in `fetchReport3Fallback`; will be removed by this request.
- **Paginated multi-pass fetch:** A `while (!done)` loop that issues successive `.range()` calls and concatenates pages until fewer than `SUPABASE_PAGE_SIZE` rows are returned, signalling end-of-data.
- **Client-side filter:** Substring matching applied in the browser against the full loaded row set, not sent to the database. Resets pagination to page 1 on change.
- **Five-element pagination bar:** UI pattern: `«` (First), `‹` (Previous), page indicator, `›` (Next), `»` (Last), with edge buttons disabled at boundary pages.
- **`useMemo`:** React hook used to memoize expensive derivations (filteredRows, displayedRows) so they are not recomputed on every render unless dependencies change.

**Files read during analysis:**
- `react-app/src/components/Report3.jsx`
- `react-app/src/components/FileRowsPanel.jsx`
- `react-app/src/lib/dataService.js` (full)
- `react-app/src/components/Report3.test.jsx`
- `react-app/src/App.jsx`
- `react-app/src/App.css` (reference for existing CSS classes)
- `.aib_memory/context.md`

**Evidence log:**
- `dataService.js:23` → `const REPORT3_ROW_CAP = 5000` — confirms hard ceiling exists.
- `dataService.js:1046-1090` → `fetchReport3` uses a single `.rpc()` with no `.range()` — confirms the PostgREST cap is not bypassed.
- `dataService.js:499-564` → `fetchReport3Fallback` has `while (!done && allRows.length < REPORT3_ROW_CAP)` — confirms fallback also truncates.
- `FileRowsPanel.jsx:1-end` → Full client-side pagination + per-column filter implementation is present and well-tested.
- `App.css` → `.pagination-controls`, `.filter-row` and related CSS classes exist.
- `App.jsx:88` → Report 3 nav label is `'🗺️ Сравнение по места'` — confirms target page identity.

---

## Research Results

**Pattern scan:**

1. **Multi-pass paginated RPC fetch (existing in codebase):** `fetchAllFileRows` in `dataService.js` implements the exact loop pattern needed: `while (!done)` + `.range(from, to)` + accumulate + check `data.length < SUPABASE_PAGE_SIZE`. The same pattern applied to `.rpc()` calls is documented in Supabase JS client v2 and confirmed to work via `.range()` chaining. The RPC fix is a direct application of this existing pattern.

2. **Client-side filter-and-pagination on loaded rows (existing in codebase):** `FileRowsPanel.jsx` is the canonical implementation. It uses three `useState` hooks (rows, currentPage, filterValues), two `useMemo` derivations (sortedRows/filteredRows, displayedRows), and two `useEffect` hooks for reset on file change and on filter change. The `Report3.jsx` upgrade is a reduced version (no sort, no row-click modal).

3. **No prior cross-report generalisation:** No shared hook or component for "paginated filterable table" has been extracted across Report 2, Report 3, and FileRowsPanel. This is consistent with the codebase's "per-component" pattern; extracting a shared component is explicitly out of scope.

---

## External Benchmarking

**1. PostgREST pagination via `Range` header (Supabase / PostgREST documentation)**

PostgREST supports HTTP `Range` request headers to paginate both table queries and RPC function calls. Supabase's JS client exposes this as `.range(from, to)` chainable on `.from().select()` and on `.rpc()` responses. The termination condition — page returned fewer rows than requested — is a universally accepted pattern for cursor-free offset pagination. This is directly applicable and has already been proven in this codebase by `fetchAllRows` and `fetchAllFileRows`.

- Takeaway: `.range()` on RPC calls is production-safe and requires no schema change.
- Adopted: Yes, directly.

**2. Client-side table filtering with React `useMemo` (React community best practice)**

The canonical React pattern for filtering large arrays is to derive filtered results via `useMemo` with the raw row array and filter string as dependencies. This avoids re-deriving the filtered set on unrelated renders. Libraries such as `react-table` / `TanStack Table` wrap this pattern, but for a 7-column table with up to ~50 000 rows and straightforward substring matching, the inline `useMemo` approach used in `FileRowsPanel` is simpler, dependency-free, and sufficient.

- Takeaway: `useMemo`-based client-side filter is appropriate for this scale; no library needed.
- Adopted: Yes, inline implementation matching existing codebase pattern.

**3. Offset pagination vs. cursor pagination for analytical tables (industry literature)**

Offset pagination (`.range(from, to)`) is adequate when the result set is fully loaded into the client before pagination is applied (client-side pagination). The known downsides of offset pagination — page drift when rows are inserted mid-fetch — are not relevant here because the full set is accumulated in a single sequential load before any UI interaction occurs, and the data is append-only (daily ETL sync, no concurrent mutations during user sessions).

- Takeaway: Offset-based multi-pass fetch is safe for this read-only, ETL-loaded dataset.
- Adopted: Yes.

---

## Minimal Spikes and Experiments

**No executable spikes required.** All three technical building blocks needed by this request exist in the current codebase:

1. The paginated multi-pass RPC fetch is a direct copy of the `fetchAllFileRows` pattern already proven in production (R-20260517-1244).
2. The filter-and-pagination UI is a direct copy of the `FileRowsPanel` pattern already proven in production (R-20260516-1313).
3. The CSS classes needed for filter inputs and pagination bar are already in `App.css`.

The only novel element is chaining `.range()` on `.rpc()` specifically (as opposed to `.from().select()`). This is documented PostgREST behaviour and used in Supabase's official documentation. If it does not work as expected, the fallback is to add `p_offset`/`p_limit` parameters to the PostgreSQL RPC function — but this is a known-good pattern that does not require a spike.

---

## AI Copilot Suggestions

**1. Consider extracting a shared `usePaginatedFilter` hook (design quality / maintainability)**

The filter-and-pagination pattern is now being applied to Report 3 for the second time (first in `FileRowsPanel`). A custom hook `usePaginatedFilter(rows, columns, PAGE_SIZE)` returning `{filterValues, setFilterValues, currentPage, setCurrentPage, filteredRows, displayedRows, totalPages}` would eliminate the copy-paste between the two components and make future applications trivial. This is explicitly out of scope for this request (the developer asked only for Report 3), but it is worth flagging as near-term refactoring that will pay off when (not if) a third table gets the same treatment.

**2. The fallback path `fetchReport3Fallback` is now largely redundant (simplification opportunity)**

Once the primary `fetchReport3` RPC path is paginated, the fallback is only reached when the RPC itself fails (network or permission error). In that case, having a full paginated fallback is correct, but removing `REPORT3_ROW_CAP` from the fallback means it will attempt to load potentially hundreds of thousands of rows client-side — appropriate when the RPC is unavailable in production and the user is actively using the page. This is the right behaviour. However, consider whether the fallback should also emit a user-visible warning (e.g., `console.warn` already exists; optionally surface it in the UI with a dismissible banner) so operators know the RPC degraded.

**3. Scope is appropriately minimal (scope assessment)**

The developer asked for three things: filtering, pagination, and full record loading. The plan delivers exactly those three. There is no scope creep. The decision not to add column sort (which `FileRowsPanel` has but was not requested) is correct — keep this out of scope.

**4. Test coverage gap: no integration test for the multi-pass RPC loop (testability risk)**

The existing `Report3.test.jsx` tests are smoke tests (render, heading, dropdown present). After this request, the pagination and filter states will have logic worth testing. The plan includes new tests for `Report3.test.jsx` and `dataService.test.js`. Ensure the `dataService.test.js` test explicitly mocks `.range()` chaining on `.rpc()` — this is the most likely mock setup to be incorrect on first attempt (the Vitest mock chain for `supabase.rpc(...).range(...)` requires a careful return-value chain mock, as seen in existing test setup).

**5. Performance note for very large categories (implementation risk)**

Categories with 50 000–100 000 rows will load entirely into browser memory before pagination is applied. For the `FileRowsPanel` (max ~10 000 rows per file per the existing code comment), this was accepted. For Report 3, a popular category could legitimately have 100 000+ rows for a national-scale date. Consider adding a loading progress indicator (e.g., "Зареждане... X записа заредени") while pages accumulate — the plan currently shows a generic loading spinner, which may feel unresponsive for very large categories. This is a UX quality issue, not a correctness issue.

---

## Testing

- T1 — Filter inputs render: After selecting a category, verify 7 filter input elements are present in the table header (one per column). Expected outcome: 7 `<input type="text">` elements with aria-labels are in the DOM.

- T2 — Filter narrows rows: Load mock rows with two rows having different settlementName values; type one value in the settlement filter input; verify only the matching row is displayed. Expected outcome: `tbody` renders exactly 1 `<tr>`.

- T3 — Filter resets page: Apply a filter that reduces rows to < `PAGE_SIZE`; assert `currentPage` resets to 0. Expected outcome: "Страница 1 от 1" indicator is visible.

- T4 — Pagination bar renders: When mock data has > 100 rows, verify the five-element pagination bar is present with correct labels. Expected outcome: `«`, `‹`, `Страница 1 от N`, `›`, `»` buttons/span visible.

- T5 — First/Last button disabled on boundary pages: Verify `«` and `‹` are disabled on page 1; `›` and `»` are disabled on last page. Expected outcome: `disabled` attribute present on correct buttons.

- T6 — Category change resets state: Change `selectedCategory` prop; verify filter inputs are cleared and page resets to 1. Expected outcome: all filter inputs have empty value; pagination indicator shows "Страница 1 от N".

- T7 — fetchReport3 paginated fetch: Unit test in `dataService.test.js`; mock `supabase.rpc().range()` to return `SUPABASE_PAGE_SIZE` rows on first call and 5 rows on second call; assert total returned count = `SUPABASE_PAGE_SIZE + 5` and that `.rpc` was called with `.range(0, 999)` then `.range(1000, 1999)`. Expected outcome: test passes; multi-pass loop confirmed.

- T8 — npm run build exit 0: Run `npm run build` from `react-app/`; assert exit code 0 and `dist/` directory exists. Expected outcome: build succeeds without errors.

- T9 — All pre-existing tests pass: Run `npm test` from `react-app/`; assert no test failures for `Report1`, `Report2`, `FileRowsPanel`, `FileDetailPage`, `HomePage`, `RecordDetailModal`, `App`, and `dataService` test suites. Expected outcome: 0 failing tests.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is architecturally sound and consistent with the codebase's established patterns. The paginated RPC loop is a direct application of the `fetchAllFileRows` precedent. The client-side filter approach is appropriate given the data is already fully loaded. No new external dependencies are introduced, and all affected code is confined to two files plus tests.

Risk: For very large categories (100 000+ rows), fully loading the result set into browser memory before any pagination is applied could cause perceptible latency or memory pressure on low-end devices. The correct long-term solution is server-side pagination on `get_report_3_rows` (adding `p_offset`/`p_limit` PostgreSQL parameters), but this is out of scope and requires a schema change. The client-side approach is acceptable as a pragmatic interim solution given the typical dataset profile.

- The paginated loop termination condition (`data.length < SUPABASE_PAGE_SIZE`) is the correct and established pattern in this codebase.
- Removing `REPORT3_ROW_CAP` from the fallback is the correct decision; the cap was an arbitrary ceiling, not a safety constraint.
- CSS reuse (existing classes from `App.css`) minimises change surface and risk of visual regression.
- Mocking `.range()` on `.rpc()` in Vitest requires careful chain setup; the test task should explicitly document the mock chain.

### Product Owner

The request addresses a real correctness defect that undermines the product's primary value proposition: transparent price comparison. A user selecting a popular category (bread, dairy, beverages) may currently see only 1 000 of 20 000+ rows, which is both misleading and undetectable without cross-referencing row counts. Fixing this is high priority.

The added filtering and pagination are directly requested features that bring Report 3 to parity with the existing "Файлове" page, setting a consistent interaction expectation across the app.

- Success criteria are measurable and unambiguous.
- No regression risk to Reports 1 or 2.
- No change to the Netlify deployment process.
- The feature will be immediately visible to all users upon the next Netlify deploy.

### User

Users of the "Сравнение по места" page currently cannot see all prices for popular categories. This is a silent data-completeness bug — no error is shown, but results are incomplete. The fix delivers three tangible improvements:

1. **Completeness**: All rows are now visible.
2. **Discoverability via filter**: Users can narrow a large result set by typing in any column.
3. **Navigation**: Pagination makes long result sets browsable.

- Filter inputs follow the same pattern as the "Файлове" page, so users who have used that page will find them familiar.
- The pagination bar uses Bulgarian labels (`Страница N от M`) consistent with the rest of the UI.
- Potential friction: for very large categories, initial loading may take several seconds while multiple round-trips complete. A meaningful loading state (ideally showing progress count) would reduce user anxiety during the wait.

### Security Officer

This request introduces no new network endpoints, no user-supplied data sent to the database, and no authentication changes. All data flows are read-only queries from an existing anon-key Supabase session.

- Filter strings are applied entirely client-side (in-browser string matching) — they are never sent to the database, eliminating any SQL injection risk.
- Pagination parameters are generated internally as integer offsets — no user-controlled values reach the Supabase query directly.
- The anon key is already in use for all existing queries; no privilege escalation occurs.
- No new environment variables or secrets are introduced.

No security concerns are raised by this request.

### Data Governance Officer

This request changes only how data is displayed and fetched, not what data is stored or how it is retained.

- No new data is written to Supabase; all changes are read-only fetch logic.
- No new columns, tables, or RPC functions are added.
- The change does not affect `backend_sql_audit_log` coverage (the RPC path is not a direct SQL statement emitted by `load_supabase.py`, so it falls outside the audit-log scope as currently defined).
- Removing `REPORT3_ROW_CAP` means more rows are transferred to the browser per session; this has no data-retention or classification implications.
- No PII or sensitive data categories are exposed by this change that were not already exposed in the existing Report 3 table.

No data governance concerns are raised by this request.
