## Executive Summary

- **Request ID:** R-20260513-2123

- **Request title:** Replace query log page with file detail page

- **High-level purpose:** Remove the developer-facing "Лог на заявки" (Query Log) debug page from the React app's navigation and replace it with a user-facing "Файлове" (Files) page that displays the source CSV files contributing data to the selected date, sourced from the already-loaded `dim_file` dimension table.

- **Motivation:** The Query Log page was a debugging affordance added in R-20260509-2012. With the persistent `backend_sql_audit_log` table (R-20260509-2113) providing backend-level SQL traceability, the in-browser session log has diminishing utility for end users. The new page exposes actionable data provenance information that complements existing analytics views.

- **Scope of `request.md` changes this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` were populated from empty placeholders.

- **Key risk:** Ambiguity in "detail data per file" — the implementation must decide whether to show a simple file list, file list with record counts (requires a Supabase query per page render), or a drilldown view. The request scope defines record counts as the target; a Q-block is raised for confirmation.

- **Files Read:** `App.jsx`, `QueryLogPage.jsx`, `QueryLogPage.test.jsx`, `queryLog.js`, `dataService.js`, `App.test.jsx`, `RecordDetailModal.jsx`, `dim_file.csv`, `context.md`, `analysis-convention.md`, `request-convention.md`.

---

## Domain Knowledge Essentials

**Source file (dim_file):** Each row in `dim_file` represents one CSV file submitted by a retail company to the Bulgarian government's open-data portal for a specific date. The file name encodes the company display name and UIC (e.g. `Лидл България_131071587.csv`). One ZIP archive per date contains many such CSV files — one per reporting company.

**UIC (ЕИК — Единен идентификационен код):** Bulgarian unique company identification code, embedded in the source file name after the underscore (`_`). Not a surrogate key; it identifies the legal entity.

**zip_date:** The date of the ZIP archive from which the file was extracted. Stored in `dim_file.zip_date` as ISO date string (YYYY-MM-DD). Corresponds to the date the company reported prices.

**fact_prices_lookback:** The sole Supabase fact table (since R-20260430-0825). Contains current and two-day lookback price columns per row. Rows are keyed by `date_key`, `store_key`, `product_key`, `category_key`, `file_key`. Each fact row references a `file_key` from `dim_file`.

**Lookback offset routing:** The app holds three dim_date rows (D, D-1, D-2). Fact rows are stored under D's `date_key` in Supabase; lookback prices are accessed via `retail_price_day1`/`promo_price_day1` columns, not separate date rows. Queries for D-1/D-2 must use `dims.currentDateKey` as the filter, not the selected date's `date_key`.

**Impacted roles/personas:** End users of the React analytics app (price analysts, general public) and developers who previously used the Query Log page for debugging.

**Business processes touched:** Price analytics visualization; data provenance display.

---

## Technical Knowledge & Terms

**dim_file:** Supabase table and local CSV at `data/schema/dim_file.csv`. Columns: `file_key` (integer surrogate key), `file_name` (text slug), `zip_date` (date). Already fetched and cached at app startup in `dims.files` (Map<file_key, {file_name, zip_date}>).

**dims.files:** Module-level cache in `dataService.js`. Populated by `fetchDimensions()` from `dim_file`. Already available to all page components via the `dimensions` prop passed from `App.jsx`.

**queryLog.js:** Session-scoped in-memory store for browser-visible Supabase query activity. Exports: `getQueryLogSnapshot`, `subscribeToQueryLog`, `addQueryLogEntry`, `clearQueryLog`, `_resetQueryLog`. Used by `dataService.js` (`executeLoggedQuery`, `fetchAllRows`) to record query telemetry. NOT tied to any display component after `QueryLogPage.jsx` is removed — it becomes infrastructure without a UI consumer but remains valid code.

**fact_prices_lookback:** Supabase table. Columns include `date_key`, `store_key`, `product_key`, `category_key`, `file_key`, `retail_price`, `promo_price`, `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`. Querying `COUNT(*) GROUP BY file_key` for a given `date_key` yields per-file record counts.

**resolveReportQuery:** Internal `dataService.js` helper that resolves the offset label and the actual `date_key` to use in Supabase queries, handling D-1/D-2 routing transparently.

**useSyncExternalStore:** React 18 hook used by `QueryLogPage.jsx` to subscribe to the external `queryLog.js` store. Not needed by the new file page since `dims.files` is passed as a prop from parent state.

**App.jsx PAGES constant:** Enumerates page identifiers used for the `activePage` state. Must be updated to replace `QUERY_LOG` with a `FILES` entry.

**Technologies involved:** React 18, Vite, `@supabase/supabase-js` v2, Vitest, `@testing-library/react`, CSS media queries.

**Evidence log:**
- `dims.files` is already populated from `dim_file` at startup → new page needs no extra dimension fetch.
- `fact_prices_lookback` has `file_key` column → per-file record counts are achievable via `.select('file_key').eq('date_key', ...).then(aggregate client-side)` or a Supabase `.select('file_key, count')` with `.group('file_key')` if the PostgREST aggregation feature is available.
- The `resolveReportQuery` helper already manages lookback routing → `fetchFileStats` can reuse it.
- `App.css` already has `.results-table`, `.report-section`, `.no-data` classes → consistent styling is achievable with zero new CSS classes (though new ones may be added for the files table).

**Files Read (required bullet):**
- `react-app/src/App.jsx` — root component with PAGES, nav, and page sections
- `react-app/src/components/QueryLogPage.jsx` — page to be removed
- `react-app/src/components/QueryLogPage.test.jsx` — tests to be removed
- `react-app/src/lib/queryLog.js` — session log infrastructure (retained)
- `react-app/src/lib/dataService.js` — data-fetching layer, RPC helpers, `resolveReportQuery`
- `react-app/src/App.test.jsx` — root component tests
- `react-app/src/components/RecordDetailModal.jsx` — reference for `dims.files` usage
- `data/schema/dim_file.csv` — sample of dim_file contents
- `.aib_memory/context.md` — product context

---

## Research Results

**Pattern scan — Page replacement in React SPAs:** Removing a route/page from a React app without a router (this app uses a simple `activePage` state rather than React Router) requires: (1) removing the nav button, (2) removing the conditional render block, (3) deleting the component file and its tests. This is a well-established direct state-machine edit pattern with no implicit dependencies beyond the import chain.

**Pattern scan — dim_file record count aggregation:** The `fact_prices_lookback` table has a `file_key` foreign key. Client-side aggregation after fetching all `file_key` values for the selected date is feasible but expensive at high row counts (~82M total rows, though only a single date's rows are fetched at a time — estimated 500K–1M rows per date). A better approach is a Supabase query selecting only `file_key` with no other columns, relying on index scan, then grouping client-side; or using a Supabase RPC function to push the `COUNT(*) GROUP BY file_key` to PostgreSQL. The request scope explicitly excludes adding a Supabase RPC function, so client-side aggregation of `file_key` values (single-column read, indexed) is the mandated path.

**Pattern scan — Session log without a consumer UI:** After removing `QueryLogPage.jsx`, `queryLog.js` becomes an infrastructure module with active producers (`dataService.js`) but no consumer UI. This is architecturally equivalent to a metrics collector without a display endpoint — a valid pattern when future re-use or backend forwarding is anticipated. The `MAX_QUERY_LOG_ENTRIES = 250` cap prevents unbounded memory growth.

**Organizational standards scan:** All existing report pages follow the prop contract `{ selectedDate, dimensions }`. The new `FileDetailPage` must follow the same interface. Existing pages use the `.report-section` wrapper class and `.results-table` for tabular data, `.no-data` for empty state.

---

## External Benchmarking

**Data provenance pages in analytics dashboards (general pattern):**
Industry analytics tools (Superset, Metabase, Redash) typically provide a "Data Sources" or "File Registry" view showing ingested files with metadata (source name, ingestion date, record count, status). This request aligns with that pattern at a simpler scale.
- Key takeaway: grouping by source file and showing counts is a standard provenance UI affordance.
- Applicability: directly applicable — `dim_file` maps to "source file" and `fact_prices_lookback.file_key` provides the grouping key.
- Assessment: adopt — the pattern is well-established and directly serves the user's need.

**Replacing developer debug pages with end-user pages as products mature:**
Common lifecycle pattern in React apps: debug/observability pages (Redux DevTools panels, query inspectors) are removed or moved to a developer-only route as the product stabilizes. The removal of the Query Log page follows this standard maturation path.
- Key takeaway: the underlying `queryLog.js` infrastructure can be kept for potential future operator tools without coupling it to end-user nav.
- Applicability: confirms the scope decision to retain `queryLog.js` while removing only the UI page.
- Assessment: adopt reasoning; this validates the "remove page, keep module" decision.

**Client-side aggregation vs. server-side aggregation for file-count queries:**
PostgREST (used by Supabase) supports `GROUP BY` aggregation via the `columns` parameter with aggregate functions in newer versions (v12+). However, Supabase's client library surface does not expose a stable cross-version `.groupBy()` method, and the existing codebase already guards against PostgREST version differences (v10 vs v11 unwrapping). Fetching only `file_key` values and aggregating client-side avoids version fragility at the cost of transferring more data than a `COUNT(*)` query would return. Given typical per-date row counts (~1M rows) and a single-column fetch, estimated payload is ~4–8 MB — acceptable for an analytics tool but should be noted as a performance risk.
- Key takeaway: client-side aggregation is simpler and version-stable; server-side is more efficient but introduces PostgREST version risk and would require a new RPC (explicitly out of scope).
- Assessment: accept client-side approach per request constraint; flag as a future optimization candidate.

---

## Minimal Spikes and Experiments

**Spike: dim_file rows available via dims.files for file detail page**
- Hypothesis: `dims.files` (Map<file_key, {file_name, zip_date}>) populated by `fetchDimensions()` contains all file records needed to render the files page without an additional Supabase fetch.
- Approach: Read `dataService.js` `fetchDimensions()` implementation; verify that `dim_file` is fetched and stored in `fileMap`.
- Outcome: Confirmed. `fetchAllRows('dim_file', 'file_key,file_name,zip_date', ...)` is executed at startup and stored in `_dims.files` as a `Map<file_key, {file_name, zip_date}>`.
- Conclusion: No additional startup fetch is needed. The file list is available from props.

**Spike: fact_prices_lookback file_key fetch feasibility for count aggregation**
- Hypothesis: A single-column Supabase query on `fact_prices_lookback` selecting only `file_key` filtered by `date_key` can return all file key values for a given date, enabling client-side count aggregation.
- Approach: Reviewed `dataService.js` `fetchAllRows` pagination pattern; reviewed `fact_prices_lookback` schema from `context.md`; counted ~82M total rows across all dates.
- Outcome: The `fetchAllRows` paginator fetches in 1,000-row pages. For a single date with ~1M rows, this results in ~1,000 paginated requests — not feasible. A more efficient approach is to use a single Supabase query with `.select('file_key').eq('date_key', ...).limit(large_number)` or recognize that `file_key` is not aggregated by a Supabase paginator but rather the TOTAL set of file_key values per date must be retrieved. At 1M rows this is 1,000 pages of 1,000 rows each — approximately 1,000 round-trip HTTP requests.
- Conclusion: The client-side aggregation approach with `fetchAllRows` is NOT feasible for large date sets (~1M rows per day). A single `.select('file_key').eq('date_key', ...).order('file_key')` query limited to a large page size would still require multiple round trips. **The most practical approach within the "no new RPC" constraint is to accept that record counts may not be available in the initial implementation, and instead show a file list from `dims.files` filtered by the selected date's `zip_date`.** This requires resolving which `zip_date` corresponds to the selected date via `dims.lookbackColumnMap` + `dims.dates`. Record count display is deferred or raised as Q-block.

No-spike note: Responsive layout applicability — no spike needed. Existing `.report-section`, `.results-table`, and `.no-data` CSS classes are already defined and already cover responsive breakpoints in `App.css`.

---

## AI Copilot Suggestions

- **The "record count per file" requirement may be undeliverable without an RPC.** The out-of-scope constraint that prohibits a new Supabase RPC function is in direct tension with the Scope section's requirement to show "a record count per file from `fact_prices_lookback`". As shown in the Minimal Spikes section, fetching per-file counts client-side for a ~1M-row date requires ~1,000 paginated round-trips — an unacceptable UX. Consider either: (a) relaxing the "no new RPC" constraint and adding a lightweight `get_file_stats(p_date_key bigint)` RPC function, or (b) removing the record count column from the page scope and displaying only file name and date.
  - Actionable suggestion: Raise Q001 to decide whether to add a minimal RPC or drop the count column entirely.

- **The scope of the Query Log removal is well-bounded but leaves orphaned infrastructure.** Retaining `queryLog.js` and all its `dataService.js` call sites after the UI page is removed creates dead-end telemetry — entries are appended to an in-memory buffer that no component reads. This is acceptable for now but accumulates maintenance debt.
  - Actionable suggestion: Consider adding a code comment to `queryLog.js` noting that it is retained for future operator tooling use, to prevent well-meaning future contributors from removing it without understanding the intent.

- **Five-page constraint is met but the fifth slot's new content has different character than the other four pages.** Reports 1–3 are date-driven analytical queries over `fact_prices_lookback`. The new Files page is closer to a dimension browser (navigating `dim_file`). This is architecturally consistent with the app's structure but may surprise users who expect all pages to be analytical views.
  - Actionable suggestion: Use a distinct but recognizable nav label (e.g. "📁 Файлове") and include a brief explanatory subtitle on the page explaining what source files are and why they matter for data provenance.

- **The scope correctly defers the complex drilldown case.** Allowing per-file drilldown into individual records would essentially duplicate a filtered Report 2, and the current data model (no `file_key` filter in existing RPCs) would require additional backend work.
  - Actionable suggestion: The scope is appropriately sized for one iteration; a follow-up request could add drilldown if needed.

- **Scope note:** The scope appears slightly larger than the stated goal only because of the record count requirement. Without record counts, the implementation is a straightforward file list filtered by date from already-loaded `dims.files` — a very small change. The record count requirement is the dominant complexity driver and should be explicitly confirmed or removed.

---

## Testing

- T1 — FileDetailPage renders without crashing: Mount `FileDetailPage` with stub `dimensions` containing a non-empty `files` Map and a valid `selectedDate`. Expected outcome: component renders without throwing.

- T2 — FileDetailPage shows no-data message when dims.files is empty: Mount with `dimensions.files = new Map()`. Expected outcome: a user-facing "Няма налични файлове" (or equivalent) message is present in the DOM.

- T3 — FileDetailPage shows no-data message when no files match selected date: Mount with dims.files containing files for a different date than selectedDate. Expected outcome: the no-data message is rendered; no table rows are present.

- T4 — FileDetailPage renders file rows for the selected date: Mount with dims.files containing two files with `zip_date` matching the selected date's resolved date string. Expected outcome: two rows appear in the table, each showing the formatted date and file name.

- T5 — FileDetailPage applies lookback date resolution: Mount with a D-1 `selectedDate` where the resolved zip_date differs from the raw date string. Expected outcome: files are filtered by the resolved date (D's zip_date), not the raw D-1 date.

- T6 — App renders five nav buttons after change: Render `App` with mocked dimensions; verify exactly five nav buttons are present and none is labelled "Лог на заявки". Expected outcome: five nav buttons; no Query Log label.

- T7 — App shows Files page on nav button click: Render `App` with mocked dimensions; click the Files nav button. Expected outcome: the Files page section becomes active and is visible.

- T8 — QueryLogPage.jsx deleted: File existence check at `react-app/src/components/QueryLogPage.jsx`. Expected outcome: file does not exist.

- T9 — QueryLogPage.test.jsx deleted: File existence check at `react-app/src/components/QueryLogPage.test.jsx`. Expected outcome: file does not exist.

- T10 — queryLog.js not modified: `queryLog.js` exports `getQueryLogSnapshot`, `subscribeToQueryLog`, `addQueryLogEntry`, `clearQueryLog`, `_resetQueryLog`. Expected outcome: all five exports still present and callable.

- T11 — Build success: Run `npm run build` in `react-app/`. Expected outcome: exit code 0, `dist/` directory created.

- T12 — Test suite passes: Run `npm run test` in `react-app/`. Expected outcome: exit code 0, no failing tests. See UAT_scenarios.md — UAT-01 for visual/responsive validation.

- T13 — Re-run idempotency: Navigate to Files page, switch selected date; the displayed files update to match the new date. Expected outcome: no stale file rows remain from the previous date selection. See UAT_scenarios.md — UAT-01.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is technically straightforward: a component swap in a client-only React SPA with no backend changes. The architectural risk is low. The most significant technical concern is the record count requirement — fetching per-file fact counts without a server-side RPC is infeasible at the actual data volume (~1M rows per date requires ~1,000 round-trip Supabase requests). The design must resolve this before implementation begins. Retaining `queryLog.js` as unused infrastructure is acceptable under the "no over-engineering" constraint, but it should be explicitly noted to prevent inadvertent future removal. The new page inherits the existing `dims.files` cache cleanly with no new startup cost.

- The record count requirement conflicts with the "no new RPC" constraint at production data volumes.
- `queryLog.js` becomes infrastructure with no UI consumer — acceptable but should be documented.
- The new page is architecturally clean: it reads from already-loaded dimension data.
- No backend, no ETL, no Supabase schema changes — very low deployment risk.

### Product Owner

Replacing a developer debug page with a data provenance page is high-value for end users who want to understand where the price data came from. Showing which companies filed data on a given date addresses a legitimate analytics use case. The success criteria are clear and testable. However, if the record count column is dropped (to avoid the RPC constraint), the page becomes a simple file list which may feel sparse — communicating this trade-off to the user is important. The nav label "Файлове" is adequate but a tooltip or subtitle explaining the page's purpose would improve discoverability.

- High business value: exposes data provenance to end users.
- Record count column is desirable but conflicts with current constraints — needs explicit decision.
- Five-page layout constraint is preserved; no nav overflow risk.
- Success criteria cover all user-visible outcomes adequately.

### User

End users navigating to the new "Файлове" page will see a list of retail companies that submitted price data for the selected date. This is meaningful for users who want to verify data coverage (e.g. "Did Lidl submit data today?"). The removal of the "Лог на заявки" page removes a confusing developer-facing tab from the public nav. The new page follows the same date selector interaction model as other pages, which is consistent and easy to learn.

- Removing the Query Log tab reduces nav clutter for non-technical users.
- The new page answers the practical question "which companies reported prices today?"
- File names include UIC codes which are not meaningful to end users — consider showing only the company display name extracted from the file name.
- Loading state must be present if record counts are shown, to avoid blank tables.

### Security Officer

This change introduces no new attack surface. The new page reads from already-loaded `dims.files` data and, if record counts are implemented, issues a read-only Supabase query with no user-supplied parameters beyond the already-sanitized `selectedDate` (an integer surrogate key). No credentials are introduced. The removal of the Query Log page reduces the information visible to users about internal query patterns, which is a marginal security improvement. No authentication/authorization changes are needed since the app uses the public anon key with RLS-controlled read access.

- No new attack surface from the page addition.
- Removing the Query Log page reduces internal query metadata visible to public users.
- `selectedDate` is already an integer key; no injection risk.
- `dims.files` is pre-loaded read-only data with no user input path.

### Data Governance Officer

The `dim_file` data exposed on the new page includes company display names and UIC codes. UIC codes are public business registration identifiers in Bulgaria (part of the government's open-data disclosure). Exposing them in a public-facing page is consistent with the product's data source (kolkostruva.bg/opendata) and raises no GDPR concerns for legal entities. The `zip_date` field is an operational metadata field with no personal data implications. The removal of the Query Log page removes session-level query metadata from the public UI, which is a positive data minimization outcome. No changes to data retention, classification, or lineage are introduced by this request.

- UIC codes in file names are public business identifiers — no compliance concern.
- Removing the Query Log UI reduces session metadata exposure.
- No changes to `dim_file` schema, retention, or lineage.
- No personal data is introduced or removed.
