## Executive Summary

- **Request ID:** R-20260514-2102

- **Request title:** File row detail view in Файлове page

- **Purpose:** Extends the "Файлове" (Files) page of the React analytics app with a drill-down capability so that clicking any file row in the summary table reveals every individual price fact record contributed by that source file, displaying all attributes (product, category, settlement, store, company) and all price metrics (retail, promo, effective, and lookback day1/day2 columns).

- **Scope summary:** New `fetchFileRows` function in `dataService.js`; new `FileRowsPanel.jsx` component; modifications to `FileDetailPage.jsx` (row click handling, state management); new and updated tests; `context.md` update.

- **Interaction model open:** The UX pattern for how the detail view appears (modal overlay, inline panel below the summary, or replacement of the summary) is not specified in the request and is raised as Q001 in `request.md`.

- **No ETL or backend changes required:** The implementation uses existing Supabase tables (`fact_prices_lookback`, `dim_product`) via the already-established client-side join pattern. No new RPC functions or `load_supabase.py` changes are needed.

- **`request.md` sections added/updated during this analysis run:** `## Assumptions` (A1–A4), `## Plan` (Tasks 1–6), `## Documentation`, `## Questions & Decisions` (Q001), `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.

---

## Domain Knowledge Essentials

**Business terminology:**

- **Файлове / Files page:** The fifth navigation page in the React app; shows the source CSV files submitted by retailers for the selected date. Introduced in R-20260513-2123 as a replacement for the Query Log page.

- **Source file (dim_file):** Each retailer submits one CSV file per day to the government open-data portal; each file is identified by `file_key`, `file_name` (e.g., `Лидл България_131071587.csv`), and `zip_date` (the submission date).

- **Retail price fact:** One row in `fact_prices_lookback` = one product price record reported by one retailer at one store on one date. The "content of the file" means all these individual price records contributed by that file.

- **Retailer (търговец):** A commercial entity that submitted price data. A company may operate multiple stores; each store appears as a `dim_store` row with a foreign key to `dim_company`.

- **Effective price (ефективна цена):** The minimum of `retail_price` and `promo_price` (when promo is non-null and non-zero); computed by `calculatePrice()` in dataService.js.

- **Lookback prices (D-1, D-2):** `fact_prices_lookback` stores prices from the two previous dates alongside the current date's prices in additional columns: `retail_price_day1`, `promo_price_day1` (D-1 prices), `retail_price_day2`, `promo_price_day2` (D-2 prices). These allow the React app to show price comparisons without loading separate fact tables.

**Impacted roles/personas:**

- **End user (analyst / public):** Benefits from visibility into the granular price data behind each file summary, enabling verification and deeper analysis.
- **Data engineer (operator):** May use the detail view to inspect data quality at the file level.

**Business processes touched:**

- Public retail price visualisation via the hosted React web app.

**Acceptance impact:**

- No new business rules are introduced; the feature exposes existing data at a finer granularity. Acceptance criteria are objective and testable (SC1–SC7 in `request.md`).

---

## Technical Knowledge & Terms

**Technologies and components:**

- **React 18 + Vite (SPA):** `react-app/` is a client-only Vite-built app. No server-side rendering; all data fetched from Supabase in the browser via `@supabase/supabase-js` v2.
- **Supabase PostgREST:** Supabase exposes PostgreSQL tables and RPC functions via REST. The React app uses the JS client (`supabase.from(...).select(...)`, `.range()`, `.in()`).
- **Vitest + React Testing Library:** Test framework already set up for the React app. Tests use `vi.mock` for dataService, `render`/`screen`/`act` from `@testing-library/react`.

**Data models and assets:**

- **`fact_prices_lookback` (Supabase):** Sole fact table; 11 columns: `date_key` (INTEGER, FK dim_date), `store_key` (INTEGER, FK dim_store), `file_key` (INTEGER, FK dim_file), `category_key` (INTEGER, FK dim_category), `product_key` (INTEGER, FK dim_product), `retail_price`, `promo_price`, `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2` (all NUMERIC(12,4)). Truncated and reinserted on every ETL sync run.
- **`dim_product` (Supabase, NOT in dims cache):** ~118,281 rows (2026-04-20); columns `product_key`, `product_code`, `product_name`. Too large to preload; must be fetched per-query via `.in('product_key', uniqueKeys)`.
- **`dim_file` (loaded in dims cache as `dims.files`):** Map<file_key, {file_name, zip_date}>; populated at startup by `fetchDimensions()`.
- **dims cache:** Module-level object in `dataService.js` containing settlements, categories, stores, companies, files maps — available synchronously without additional Supabase calls. `dim_product` is explicitly NOT in this cache.

**Key terms:**

- **`fetchAllRows(table, columns)`:** Generic paginator in dataService.js that reads a Supabase table in 1000-row pages using `.range()`. Not directly usable for `fetchFileRows` because it does not support filter conditions; the new function will issue its own paginated query.
- **`executeLoggedQuery(...)`:** Wrapper that measures query duration and records intent/outcome in the in-memory session query log. All new Supabase calls must use this wrapper.
- **`SUPABASE_PAGE_SIZE` (1000):** Default Supabase page limit. The new `fetchFileRows` uses a smaller `pageSize` (100) as the UI pagination unit, but each UI page is still a single Supabase query within the 1000-row API limit.
- **`table-scroll-wrapper`:** CSS class in `App.css` (defined as `overflow-x: auto`) that enables horizontal scroll for wide tables on mobile. Already used in `FileDetailPage.jsx`; must be applied to the new detail table.
- **Client-side join pattern:** Established in `fetchReport2Fallback` and `fetchReport3Fallback`: query fact rows from Supabase → collect unique dimension keys → batch-fetch dimension display names → merge into enriched result. This request follows the same pattern for `fetchFileRows`.

**Non-functional attributes:**

- **Performance:** Two Supabase round-trips per page navigation (one fact rows query, one dim_product batch). Acceptable for interactive use; latency under normal conditions expected to be <500ms per page.
- **Memory:** Page size of 100 rows × ~11 numeric columns + enriched strings = well within browser memory budget; no risk.
- **Security:** No user-supplied text is sent to the database. `file_key` originates from `dims.files` (populated from Supabase on startup), not from user text input. No injection risk.
- **Accessibility:** Close button must be keyboard-reachable; table must use `<thead>`/`<tbody>` semantic markup. `role="dialog"` would apply if modal option is chosen (Q001).

---

## Research Results

**Current FileDetailPage state:**
`FileDetailPage.jsx` renders a 3-column summary table (`<tr>` rows with `<td>` cells for file_name, formatted zip_date, and record count). Rows are sorted alphabetically by file_name. File count is fetched via `fetchFileStats(fileKeys)` which issues batched `{ count: 'exact', head: true }` HEAD queries. No row-level click handler exists. The component receives `selectedDate` (date_key integer) and `dimensions` (dims cache) as props from `App.jsx`.

**fact_prices_lookback query pattern for file_key:**
`fetchFileStats` in dataService.js already queries `fact_prices_lookback` filtered by `file_key` for counts. Extending this to a data fetch (with `.range()`) is a direct extension of the established approach. No `date_key` filter is needed when filtering by `file_key` because: (a) `fact_prices_lookback` is fully truncated on each sync run, so only one set of file_key values exists at any time; (b) `file_key` values are globally unique (assigned by dim_file which is append-only, never truncated).

**dim_product fetch pattern:**
`fetchReport2Fallback` (lines ~400–450 in dataService.js) demonstrates: after fetching fact rows, collect `productKeys = [...new Set(rows.map(r => r.product_key))]`, then query `dim_product` with `.in('product_key', productKeys)`. This pattern is well established and safe for batches up to 1000 unique keys (Supabase `.in()` handles up to 1000 values per call).

**File sizes (from dim_file.csv sample):**
The sample shows 49 files for 2026-02-15 alone. The full dim_file has 13,089 rows across 63 dates = ~208 files per date. Fact table rows per file vary widely. Context.md notes ~1.1–1.5M fact rows per date; split across ~208 files, average is ~5,000–7,000 rows per file. Larger retailers (Лидл, Кауфланд) likely have tens of thousands of rows. Pagination is mandatory.

**Test infrastructure:**
`FileDetailPage.test.jsx` already uses `vi.mock('../lib/dataService', ...)` to mock `fetchFileStats` and `formatDateBG`. The same pattern will be used to mock `fetchFileRows` in new tests. React Testing Library's `act(async () => {...})` pattern handles async state updates (already used in existing tests T1–T3).

**Existing CSS for wide tables:**
The `table-scroll-wrapper` div with `overflow-x: auto` is already present in `FileDetailPage.jsx`'s JSX. A 12-column fact table fits within this wrapper. No new CSS layout architecture is needed; only `cursor: pointer` (or `tr.clickable` class) needs to be added.

**RecordDetailModal relevance:**
`RecordDetailModal.jsx` shows details of a single Report 2 row in a modal dialog. It is NOT reusable for the tabular multi-row use case here. `FileRowsPanel` will be a distinct, purpose-built component.

---

## External Benchmarking

**Master-detail UX pattern (inline panel):** Widely used in enterprise SPA dashboards (Gmail's email list + reading pane, Jira's issue list + detail panel, Grafana's explore view). Clicking a row updates a panel below (or beside) without navigating away. Allows context retention — the user can see how many files exist while reading one file's rows.

**Page-replacement drill-down:** Common in mobile-first and data-heavy contexts (iOS Settings, Google Analytics sub-pages). The master view is replaced; a back button returns to it. Good for large detail views; simpler component state.

**Modal drill-down:** Used by RecordDetailModal in Report 2, and common in table-heavy SaaS apps (Stripe payment detail). Best for compact detail panels (one record); less suited for paginated multi-row tables because the modal height constraint limits visible rows and creates a nested scroll-inside-scroll problem.

**Pagination best practice:** Server-side pagination (`.range()`) is standard for datasets of 1,000+ rows in web apps backed by PostgreSQL. Client-side pagination (load all, slice in React) is only appropriate for datasets guaranteed to be under ~500 rows; given potential file sizes of 10,000+ rows, server-side is required.

**Column density trade-off:** Industry standard for data-dense tables is 5–8 visible columns maximum before horizontal scroll is needed on 1024px viewports. With 12 columns, the table will always require horizontal scroll on standard monitors; this is acceptable for a data-transparency use case where completeness is more important than visual comfort.

---

## Minimal Spikes and Experiments

**No spike needed for pagination:** The Supabase `.range(from, to)` pattern is already used in `fetchAllRows` and all fallback fetch functions. The exact API is known; no experimentation needed.

**No spike needed for dim_product batch fetch:** The `.in('product_key', keys)` pattern is used in `fetchReport2Fallback` and `fetchReport3Fallback`. The exact implementation can be copied with minor adaptation.

**No spike needed for table-scroll-wrapper:** Already present in `FileDetailPage.jsx`; confirmed to work for mobile via existing responsive CSS.

**No spike needed for test mocking of async functions:** The `act(async () => {...})` + `vi.mock` pattern is already in `FileDetailPage.test.jsx`. All needed test infrastructure exists.

**Potential spike — Supabase count query performance:** The `{ count: 'exact', head: true }` query used in `fetchFileStats` is a HEAD request that asks PostgreSQL to execute a COUNT(*) for a filtered query. For a table of ~1.1M rows filtered by a single indexed foreign key (`file_key`), this is expected to be fast (milliseconds) if there is a B-tree index on `file_key`. The context confirms four B-tree indexes on `fact_prices_lookback`; whether one covers `file_key` individually is not explicitly stated. If the count query is slow, the total count can be omitted or approximated. This risk is Low — `file_key` filtering on a ~1M row table is fast even without a dedicated index via a sequential scan.

---

## AI Copilot Suggestions

**1. Interaction model ambiguity is a blocker — resolve Q001 before implementation starts**

The request does not specify how the detail view should appear (modal, inline panel, page replacement). This choice has a cascading impact on component structure, accessibility implementation, CSS layout, and test setup. An inline panel (Option B in Q001) is the recommended default because: (a) it avoids the nested-scroll problem of a modal with a paginated table; (b) it preserves the file list context while the user pages through records; (c) it is the most natural mobile experience (scroll down to read). However, this is a product preference decision. Implementing the wrong model will require a component rework. The analysis recommends resolving Q001 before any code is written.

**2. Column density will produce a poor UX on narrow viewports without careful CSS**

Showing all 12 columns (product, category, settlement, store, company + 6 price columns) in a scrollable table is technically achievable with `table-scroll-wrapper`, but users on mobile (≤ 600px) will need to scroll both vertically (through rows) and horizontally (across columns) simultaneously. The minimum column widths should be constrained so the table doesn't collapse. Consider whether the four lookback price columns (day1/day2) should be visually grouped or styled differently to signal that they are historical comparisons, not the primary prices. This is a cosmetic suggestion; it does not change the scope but will improve usability.

**3. The `fetchFileRows` function's dim_product fetch will create one extra round-trip per page — this is acceptable now but may become a pain point for power users**

The established pattern fetches `dim_product` names per page (per unique product_keys in each page). For a file with 100 rows per page and potentially 100 unique products per page, this adds one additional Supabase call per page navigation. Over 10 pages, that's 10 extra round-trips. For the current use case (single user, on-demand interaction) this is fine. If the feature becomes heavily used, a Supabase RPC that performs the join server-side would eliminate this overhead. The analysis recommends noting this as a future optimisation candidate in the code.

**4. The total row count query (COUNT for totalCount) deserves attention**

The `fetchFileRows` design includes a separate `{ count: 'exact', head: true }` HEAD query per page-one load to show total records. Two improvements worth considering: (a) issue this count query once (when the file is first selected) and cache it in component state, not on every page change — total count doesn't change; (b) validate that `fact_prices_lookback` has an index on `file_key` that makes this COUNT fast. The `fetchFileStats` function already does this per-file count successfully, so the pattern is proven.

**5. The scope is well-bounded and the right size for a single iteration**

The request does not over-reach: no new RPC, no ETL changes, no search/filter capability (correctly deferred). The 6-task plan (dataService function, component, FileDetailPage modification, tests, context update, validation) is deliverable in a single focused session. No scope reduction is recommended.

---

## Testing

- **T1 — Summary table rows are clickable (FileDetailPage):** Render `FileDetailPage` with stub dims (2 matching files). Simulate `fireEvent.click` on a `<tr>`. Expected outcome: `FileRowsPanel` appears in the DOM (e.g., detected by a heading or the file name text rendered by the panel).

- **T2 — FileRowsPanel loading state:** Render `FileRowsPanel` with `fetchFileRows` mocked to return a never-resolving promise. Expected outcome: a loading indicator (e.g., `'Зареждане...'` text or `'…'` cells) is present in the DOM before the fetch resolves.

- **T3 — FileRowsPanel renders enriched rows:** Mock `fetchFileRows` to return `{ rows: [{ productName: 'Хляб', categoryName: 'Хляб', settlementName: 'София', storeName: 'Лидл 1', companyName: 'Лидл България', retail_price: 1.29, promo_price: null, retail_price_day1: 1.35, promo_price_day1: null, retail_price_day2: 1.40, promo_price_day2: null, calculatedPrice: 1.29 }], totalCount: 1 }`. Expected outcome: `'Хляб'`, `'София'`, `'Лидл 1'` appear in the rendered table; price values appear in the appropriate columns.

- **T4 — FileRowsPanel close button dismisses the panel (FileDetailPage integration):** Render `FileDetailPage`, click a file row to open `FileRowsPanel`, then click the close/back button inside the panel. Expected outcome: `FileRowsPanel` is removed from the DOM; the summary table is visible again.

- **T5 — FileRowsPanel empty state:** Mock `fetchFileRows` to return `{ rows: [], totalCount: 0 }`. Expected outcome: a no-data message is displayed (e.g., `'Няма записи'`); no table rows are rendered.

- **T6 — FileRowsPanel error state:** Mock `fetchFileRows` to reject with an error. Expected outcome: an error message is displayed in the panel; no crash occurs.

- **T7 — FileRowsPanel pagination — next page:** Mock `fetchFileRows` to return `{ rows: [...], totalCount: 250 }` (simulating > 1 page at pageSize=100). Click the "next page" button. Expected outcome: `fetchFileRows` is called a second time with `pageIndex = 1`.

- **T8 — `fetchFileRows` function — enrichment correctness:** Call `fetchFileRows` with mocked Supabase responses (fact rows + dim_product data); assert that returned `rows[0]` contains correct `productName`, `categoryName`, `settlementName`, `storeName`, `companyName`, `calculatedPrice`. Expected outcome: all enriched fields match the mocked dimension data.

- **T9 — `fetchFileRows` function — totalCount returned:** Mock Supabase count query to return `{ count: 350 }` and data query to return 100 rows. Expected outcome: `fetchFileRows` returns `{ rows: [...100 rows...], totalCount: 350 }`.

- **T10 — Existing FileDetailPage tests pass without regression:** Run the full test suite (`npm test`). Expected outcome: all pre-existing tests (T1–T5 in the existing `FileDetailPage.test.jsx`) continue to pass; 0 regressions.

- **T11 — Build validation:** Run `npm run build` in `react-app/`. Expected outcome: exit code 0; `dist/` directory produced without errors.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The proposed implementation follows the established client-side join pattern (`fetchReport2Fallback`, `fetchReport3Fallback`) precisely, which eliminates architectural novelty risk. The two-query design (`COUNT` then paginated `SELECT` per page) is correct: the count is issued once on file selection, paginated data on each page navigation. An important detail: `fact_prices_lookback` has four B-tree indexes (per context.md); whether `file_key` is individually indexed is not confirmed. If not, the count and paginated fact queries will fall back to a sequential scan on ~1M rows, which is acceptable for on-demand user interaction but not ideal. A B-tree index on `file_key` already exists if the original DDL included it (the four indexes are noted but not itemised in context.md).

Findings:
- The dim_product batch fetch per page (`.in('product_key', keys)`) is a known N+1 pattern: 2 Supabase calls per page instead of 1. Acceptable for v1; document as future optimisation candidate.
- The 12-column table will require explicit minimum column widths in CSS to prevent collapsed columns on mobile; otherwise `table-scroll-wrapper` will scroll but the table may be nearly unreadable.
- No state management library (Redux/Zustand) is used in this app; component-level `useState` for `currentPage`, `rows`, `totalCount` is correct and consistent with the codebase.
- Risk: If Q001 is answered as Option A (modal), the `FileRowsPanel` component needs `useEffect` for Escape-key handling and `role="dialog"` — this is additional work not currently scoped. The plan should account for ~1 extra task if modal is chosen.

### Product Owner

This feature directly serves the product's core value proposition: transparency into retail prices. Users who notice an unexpectedly high count for a specific retailer's file can now drill into the individual records to verify data quality. The feature is well scoped — summary → detail — and matches the existing Report 2 drill-down pattern (click row → see details).

Findings:
- SC1–SC7 are clear and testable; acceptance criteria are well-formed.
- The missing UX specification (Q001) must be resolved before implementation begins; implementing the wrong pattern will waste effort.
- The absence of search/filter within the file rows is correctly deferred. However, if files regularly have 5,000–10,000 rows, users may find pagination alone frustrating. A follow-up request for in-panel search should be anticipated.
- The Bulgarian-language UI labels in the column headers (Продукт, Категория, etc.) are consistent with the rest of the app; good.
- Displaying all 6 price columns (including D-1 and D-2 lookback) is technically complete but may confuse casual users who don't understand what "Цена Д-1" means. A tooltip or column header abbreviation with a legend would help — low priority, deferred.

### User (end user / analyst)

The feature adds meaningful transparency. Clicking a file row to see its records is intuitive, especially given that Report 2 already uses a similar click-to-details pattern for individual product rows.

Findings:
- The summary table currently lacks any visual affordance (hover highlight, row cursor) indicating that rows are clickable. Adding `cursor: pointer` and a hover background highlight (consistent with `RecordDetailModal` trigger rows in Report 2) will prevent users from missing the feature.
- A file with 5,000 records shown 100 at a time requires 50 page navigations. Navigation controls (prev/next + "Page X of Y") are sufficient, but a jump-to-page input would be appreciated for power users.
- Price formatting should use Bulgarian locale (comma as decimal separator, `toLocaleString('bg-BG')`) consistent with the rest of the app. The existing `(fileCounts.get(...) ?? 0).toLocaleString('bg-BG')` pattern should be followed for price display.
- Mobile: with 12 columns, the table will be very wide. Confirm that column headers wrap or truncate gracefully to avoid a header row that is taller than the data rows.

### Security Officer

No new attack surface is introduced. `file_key` values used to filter `fact_prices_lookback` originate from `dims.files` (populated from Supabase `dim_file` at startup), not from user-controlled text input; there is no injection risk. The Supabase anon key provides SELECT-only access to public price data under RLS.

Findings:
- No PII is exposed: retailer names, product names, and prices are all publicly available government-published data.
- The `.in('product_key', uniqueKeys)` query uses parameterised bindings provided by the Supabase JS client; no raw SQL string interpolation.
- No new environment variables or credentials introduced.
- If the app ever adds user authentication in the future, the file row detail view does not interact with auth state and will remain safe.

### Data Governance Officer

All data displayed in the file row detail view is sourced from the Bulgarian government's kolkostruva.bg open-data portal, which mandates public disclosure of retail prices. There are no data classification, PII, or GDPR concerns. The granularity increase (individual fact rows vs. aggregate counts) is appropriate given the public-domain nature of the data.

Findings:
- Displaying individual price records including retailer-specific product names and prices at store level increases granularity of the publicly surfaced data; this is consistent with the dataset's public classification.
- No new data retention obligations: the file row detail view reads from `fact_prices_lookback`, which is already synced and managed by the ETL pipeline under the existing retention policy.
- The `backend_sql_audit_log` (backend SQL audit) is NOT extended by this change since `fetchFileRows` uses client-side Supabase queries (logged to the in-memory session log only, not to the backend audit table). This is consistent with the existing architecture; no data governance gap.
- Lineage is transparent: each displayed row is traceable to a specific source file via `file_key → dim_file → file_name` (the exact file that contributed the row is displayed in the panel header).
