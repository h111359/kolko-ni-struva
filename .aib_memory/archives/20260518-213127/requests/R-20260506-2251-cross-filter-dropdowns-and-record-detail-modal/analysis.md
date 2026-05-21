# Analysis: R-20260506-2251 — Cross-filter dropdowns and record detail modal

## Executive Summary

- **Request ID:** R-20260506-2251

- **Title:** Cross-filter dropdowns and record detail modal

- **High-level purpose:** Improve the usability of the "Продукти" (Report 2) page in the React Analytics App by linking the "Населено място:" (Settlement) and "Категория:" (Category) dropdowns bidirectionally, so each filters the other to only valid combinations for the selected date. Additionally, make each result row clickable to reveal a full-detail modal that shows the source file that contributed the record.

- **Request scope:** React-app-only changes plus Supabase provisioning. Adds two PostgreSQL RPC functions and one composite index to `src/load_supabase.py`; adds `dim_file` startup loading and two cross-filter data functions to `react-app/src/lib/dataService.js`; adds `file_key` enrichment to `fetchReport2`; creates `RecordDetailModal.jsx`; modifies `Report2.jsx` for cross-filter state and modal integration; adds and updates automated tests.

- **Mechanism decision (Q001 resolved):** Option A (RPC approach) is confirmed. Two new PostgreSQL RPC functions — `get_categories_for_settlement` and `get_settlements_for_category` — are added to `load_supabase.py`, following the existing `get_settlements_for_date` pattern.

- **Open question:** Q002 added — UX cascade behavior when category selection auto-clears the settlement selection; awaits developer input before implementation of Task 6.

- **`request.md` updates in this analysis run:**
  - `## Scope`: Conditional Q001 language replaced with concrete RPC approach text.
  - `## Assumptions`: Fully replaced; refined post-Q001 resolution.
  - `## Plan`: Fully replaced; Tasks 1+2 merged/updated for Q001 resolution; duplicate `(date_key, store_key)` index removed from Task 1; tasks renumbered to 8.
  - `## Documentation`: Fully replaced.
  - `## Questions & Decisions`: Q001 applied to Scope and removed; Q002 added.

---

## Domain Knowledge Essentials

**Bulgarian government price transparency mandate:** Retail companies in Bulgaria are legally required to report daily prices to the government via the kolkostruva.bg portal. The product aggregates this public data for visualisation; users are members of the public, journalists, and price-watchdog analysts who need to verify that prices are accurate and traceable.

**EKATTE:** The Bulgarian administrative settlement code registry. Each settlement (city, village, borough) is identified by a standardised EKATTE code used as the settlement identifier in raw source data.

**Settlement / Населено място:** A city, town, or village in Bulgaria. In Report 2, users select a settlement to see which products are sold there and at what prices.

**Category / Категория:** A government-defined product category (e.g., bread, dairy). Prices are reported per product; each product belongs to a category. In Report 2, users select a category to filter the product results.

**Bidirectional cross-filtering (linked dropdowns):** A UX pattern where selecting a value in one filter restricts the options shown in a second filter to only those that would produce at least one result — and vice versa. Eliminates empty-result frustration when users pick incompatible combinations.

**Source file / Файл-источник:** Each day's price data is submitted as a ZIP archive by a retailer. The `dim_file` dimension table records the archive's `file_name` and `zip_date`. The `file_key` foreign key in `fact_prices_lookback` links each price record to its source archive, providing data provenance and auditability.

**D / D-1 / D-2:** The three retained date views in the product. D is the current date with actual fact rows in Supabase; D-1 and D-2 are lookback views synthesized client-side from horizontal price columns in `fact_prices_lookback`. Fact rows are always stored under D's `date_key`; cross-filter queries for D-1/D-2 must use `currentDateKey`.

**Impacted personas:** Public end users of the React app (price transparency audience); data engineers who run `load_supabase.py` to provision the new RPC functions and index.

**Business processes touched:** Public price visualisation via Report 2; Supabase provisioning via `load_supabase.py`.

---

## Technical Knowledge & Terms

**Supabase:** A hosted PostgreSQL + REST API platform. The React app queries it via `@supabase/supabase-js` v2 using the public anonymous (anon) key with Row-Level Security (RLS) allowing public SELECT on dimension/fact tables and EXECUTE on provisioned RPC functions.

**PostgREST:** The REST API layer Supabase uses to expose PostgreSQL functions and tables via HTTP. `supabase.rpc('function_name', params)` translates to a PostgREST call to `/rpc/function_name`.

**PostgREST version guard:** PostgREST v11+ returns `SETOF int` functions as plain integers; v10 wraps them in objects like `{ function_name: value }`. The existing `fetchSettlementsForDate` guards against both formats with: `(typeof r === 'object' && r !== null) ? r.<function_name> : r`. New cross-filter functions must apply the same guard.

**RPC function (PostgreSQL `CREATE OR REPLACE FUNCTION`):** A stored function exposed via PostgREST. The existing pattern uses `STABLE` sql-language functions performing `SELECT DISTINCT ... FROM fact_prices_lookback`. `GRANT EXECUTE ON FUNCTION ... TO anon` is required for each function so PostgREST can call it without elevated privileges.

**`fact_prices_lookback`:** The sole fact table in Supabase since R-20260430-0825. Holds fact rows only for D (the current date) with horizontal lookback columns for D-1 and D-2 prices. Cross-filter queries for D-1/D-2 must receive `currentDateKey` (D's key) not the lookback date's key.

**`dim_file`:** Dimension table with columns `file_key`, `file_name`, `zip_date`. Estimated ~600 rows (A3). Each `fact_prices_lookback` row has a `file_key` FK linking it to its source archive.

**`file_key`:** Foreign key in `fact_prices_lookback` referencing `dim_file.file_key`. Must be added to the SELECT list in `fetchReport2` and enriched with `fileName` and `zipDate` from `dims.files`.

**`lookbackColumnMap`:** A `Map<date_key, 'current'|'day1'|'day2'>` built by `fetchDimensions()`. Maps each dim_date row to its positional offset label. All report and cross-filter functions use this to route queries to the correct date key and price columns.

**`currentDateKey`:** The `date_key` for D (the date with actual fact rows in Supabase), derived from `get_available_dates()` RPC. Cross-filter RPCs for D-1/D-2 must receive this key instead of the lookback date's key.

**Composite B-tree index:** A PostgreSQL index on multiple columns. A `(date_key, category_key)` index on `fact_prices_lookback` enables an index-only scan for `get_settlements_for_category` (filtering by `date_key` and `category_key`). The existing `idx_fact_prices_lookback_date_store ON (date_key, store_key)` already covers `get_categories_for_settlement` (which filters by `date_key` and an `IN` list of `store_key` values from `dim_store`). Only the `(date_key, category_key)` index is new.

**React state additions in `Report2.jsx`:** `filteredCategories` (subset of all categories, updated on settlement select), `filteredSettlements` (subset of all settlements, updated on category select), `selectedRow` (the row object for the modal, or null).

**Modal accessibility (WAI-ARIA):** `role="dialog"` and `aria-modal="true"` are required for screen reader compatibility. Escape key dismissal via `useEffect` is in scope. Full focus trap is out of scope but noted as a known limitation.

**Vitest + Testing Library:** The existing test framework for the React app. Tests mock `../lib/dataService` and `../lib/supabase` at the module level via `vi.mock`. New tests follow the pattern established in `Report2.test.jsx`.

**Files read:**
- `react-app/src/lib/dataService.js` — confirmed `fetchDimensions` structure, `fetchReport2` column list, RPC pattern in `fetchSettlementsForDate`, PostgREST version guard implementation.
- `react-app/src/components/Report2.jsx` — confirmed current state: two independent dropdowns, 7-column table, no row click handlers, no modal, no cross-filter state.
- `react-app/src/components/Report2.test.jsx` — confirmed `vi.mock` pattern for `dataService`.
- `src/load_supabase.py` (lines 170–260) — confirmed `_CREATE_INDEXES` already has `(date_key, store_key)`; `_CREATE_RPC_FUNCTIONS` pattern for new function DDL.
- `.aib_memory/context.md` — architecture, dimension structure, RPC patterns, constraint details.
- `.aib_memory/request.md` — full request scope, assumptions, Q001 answer.
- `.aib_memory/input.md` — question threshold 3; Q001 answered (Option A checked).

---

## Research Results

**Pattern scan against workspace conventions:**

- `fetchSettlementsForDate` in `dataService.js` is the exact template for new cross-filter functions: `supabase.rpc()` call, lookback routing via `dims.lookbackColumnMap` and `dims.currentDateKey`, PostgREST version guard, alphabetical sort, fallback to full list on error.

- `_CREATE_RPC_FUNCTIONS` in `load_supabase.py` is the established DDL insertion point: `CREATE OR REPLACE FUNCTION ... RETURNS SETOF int ... LANGUAGE sql STABLE ... GRANT EXECUTE ON FUNCTION ... TO anon`. New functions must follow this exact pattern.

- `_CREATE_INDEXES` uses `CREATE INDEX IF NOT EXISTS` for idempotency. The existing `idx_fact_prices_lookback_date_store ON fact_prices_lookback(date_key, store_key)` is already present; only `(date_key, category_key)` is a genuinely new index.

- `fetchDimensions()` uses `Promise.all` with `fetchAllRows()` for parallel dimension loading. Adding `dim_file` extends the existing `Promise.all` call with one additional `fetchAllRows('dim_file', 'file_key,file_name,zip_date')` entry.

- `Report2.test.jsx` establishes the `vi.mock` module-level mock pattern for `dataService`; new cross-filter function mocks extend the same mock object.

**Findings from code analysis:**

- `context.md` describes `_CREATE_INDEXES` as targeting `fact_prices` but the actual code targets `fact_prices_lookback`. This is a pre-existing documentation discrepancy; the documentation task must correct it.
- `fetchReport2` currently selects `product_key,store_key,category_key,${priceColumns}`. Adding `file_key` extends this list; enrichment adds `fileName` and `zipDate` from `dims.files.get(row.file_key)`.
- `Report2.jsx` renders the category dropdown from all `dimensions.categories` with no filtering. The cross-filter implementation adds a `filteredCategories` state variable that starts as all categories and is narrowed on settlement selection.

---

## External Benchmarking

**Cascading/dependent dropdown pattern (React):**
- Widely used in e-commerce filter UIs (vehicle make/model/year selectors, country/city pickers). The canonical React pattern uses `useEffect` with dependency on the first dropdown's value, or an `onChange` handler, to fetch and update the second dropdown's options.
- Key takeaway: debouncing is recommended when the dependent fetch involves a network round-trip. For this product, the RPC is expected to be fast (indexed query, small integer result set) but a per-dropdown loading state should still be shown to prevent user interaction with stale options.
- Applicability: directly applicable. The proposed implementation matches this well-established pattern.
- Adoption decision: adopted. The `onChange`-triggered fetch for cross-filter state maps naturally onto the existing `useEffect`-driven data loading in `Report2.jsx`.

**WAI-ARIA Modal Dialog pattern (ARIA 1.2 specification):**
- Requires: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to dialog title, focus moved into the dialog on open, focus returned to the triggering element on close, Escape key closes the dialog.
- Key takeaway: without focus management, keyboard-only users cannot interact with modal content or dismiss it via the close button. The Escape `useEffect` listener partially addresses dismissal but does not move focus.
- Applicability: partially in scope. `role="dialog"`, `aria-modal="true"`, and Escape key handler are in scope. Full focus trap is excluded per the request.
- Adoption decision: partially adopted. Focus management gap is flagged in AI Copilot Suggestions as a known limitation.

**Server-side DISTINCT cross-filter queries in PostgreSQL:**
- The pattern `SELECT DISTINCT dimension_key FROM fact_table WHERE filter_column = $1` is standard in analytics databases. With a composite index on `(filter_column, dimension_key)`, the query uses an index-only scan without touching heap data.
- Key takeaway: composite index column order matters — `(date_key, category_key)` is optimal because `date_key` is always an equality predicate, making `category_key` the fast scan dimension.
- Applicability: directly applicable. The `(date_key, category_key)` index provides exactly this access pattern for `get_settlements_for_category`.
- Adoption decision: adopted. The request specifies this approach.

**Pre-computed cross-filter summary table (alternative benchmark):**
- BI tools such as Apache Superset and Metabase use pre-computed summary tables or materialized views to enable instant client-side filtering without per-interaction network calls.
- Key takeaway: for this product's data volume (3 retained dates × ~400 settlements × ~50 categories), a fully pre-computed table loaded at startup would be small enough to enable sub-millisecond client-side filtering. The RPC approach adds a network round-trip per dropdown change.
- Applicability: applicable but not selected (Q001-A was chosen).
- Adoption decision: deferred. If RPC response latency proves unacceptable in production, this approach should be revisited as a follow-up request.

---

## Minimal Spikes and Experiments

No spikes were conducted. Uncertainty was low enough not to require them, based on the following rationale:

- The SQL structure for both new RPC functions is directly derivable from the existing `get_settlements_for_date` function in `_CREATE_RPC_FUNCTIONS`. The `SELECT DISTINCT ... FROM fact_prices_lookback` pattern with a `dim_store` JOIN is proven and in production.

- The `fetchDimensions` extension for `dim_file` is mechanically identical to the existing dimension loads. `fetchAllRows('dim_file', 'file_key,file_name,zip_date')` requires no new abstraction.

- The `fetchReport2` column extension (`file_key` addition to SELECT) is a one-column change to an existing paginated query with no behavioral ambiguity.

- The PostgREST version guard for new RPC return values is already proven working in the existing `fetchSettlementsForDate` implementation and can be directly reused without modification.

- The modal conditional-render pattern (`selectedRow && <RecordDetailModal ...>`) is idiomatic React with no feasibility uncertainty.

---

## AI Copilot Suggestions

- **Observation 1 — Duplicate index in the original plan:** The prior Task 1 specified adding both a `(date_key, category_key)` index and a `(date_key, store_key)` index, but `idx_fact_prices_lookback_date_store ON fact_prices_lookback(date_key, store_key)` already exists in `_CREATE_INDEXES`. The `IF NOT EXISTS` guard prevents duplication but the plan was misleading. The updated plan (Task 1) adds only `idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)`, which is the only genuinely new index. Implementing the original plan without correction would have introduced a confusing no-op DDL statement.
  - Suggestion: confirm during implementation that only the `(date_key, category_key)` index is added to `_CREATE_INDEXES`.

- **Observation 2 — Per-interaction network latency from the RPC approach:** Every dropdown selection triggers a PostgREST round-trip. In a slow-connection scenario, the user may select a settlement and experience a visible delay before the category dropdown narrows. The current `Report2.jsx` has a single `loading` state for the report data fetch but no dedicated loading state for cross-filter fetches.
  - Suggestion: add a distinct `crossFilterLoading` state variable in `Report2.jsx` and disable or visually indicate the affected dropdown while the cross-filter RPC is in flight. This prevents the user from interacting with a stale dropdown and signals that filtering is in progress.

- **Observation 3 — Modal focus management is incomplete for keyboard accessibility:** The scope includes `role="dialog"`, `aria-modal="true"`, and Escape key dismissal, but does not include moving keyboard focus into the dialog on open or returning it to the triggering row on close. Without this, keyboard-only users cannot reach the close button or read the dialog content using standard navigation, and screen readers will not announce the dialog correctly.
  - Suggestion: add `autoFocus` to the close button element (or `tabIndex={-1}` + `.focus()` on the dialog container in a `useEffect`) and store a `ref` to the clicked `<tr>` element to restore focus on close. This is approximately 8–10 lines of additional code and substantially improves accessibility compliance for a public-facing transparency tool.

- **Observation 4 — Scope is appropriately sized for the goal:** The eight tasks decompose cleanly into backend provisioning, frontend data layer, component creation, component wiring, and test/documentation. No gold-plating is visible; cross-filtering is correctly confined to Report 2. The `dim_file` loading adds a startup fetch that is naturally small given the rolling 3-date retention window. The scope is neither inflated nor under-specified relative to the stated goal.

- **Observation 5 — `dim_file` row count assumption relies on the rolling retention window:** A3 estimates ~600 rows because only 3 dates are retained. However, `dim_file` rows for pruned dates are not currently pruned by `load_supabase.py` (this is a pre-existing gap noted in the Data Governance review). If `dim_file` accumulates historically (i.e., the prune does not cover it), the startup load could grow unboundedly.
  - Suggestion: verify whether `prune_dim_date` transitively removes `dim_file` rows via FK cascade or explicit DELETE, and document the gap explicitly in the context update task if it does not.

---

## Testing

- T1 — Categories filtered on settlement select (SC1): When a settlement is selected in Report 2, `fetchCategoriesForSettlement` is called and the category dropdown renders only the returned options. Expected outcome: category `<select>` contains only options returned by the mocked `fetchCategoriesForSettlement`; options not in the result set are absent.

- T2 — Settlements re-filtered on category select (SC2): When a category is selected, `fetchSettlementsForCategory` is called and the settlement dropdown re-renders with only the returned options. Expected outcome: settlement `<select>` contains only options from the mocked `fetchSettlementsForCategory` result.

- T3 — Auto-clear of settlement when excluded by category filter: When category selection causes the current settlement to no longer appear in `filteredSettlements`, `selectedSettlement` is cleared. Expected outcome: settlement `<select>` value is empty string after category selection that excludes the prior settlement.

- T4 — Date change resets both dropdowns (SC3): Selecting a new date resets `selectedSettlement`, `selectedCategory`, `filteredCategories`, and `filteredSettlements` to defaults. Expected outcome: both selectors show "-- Изберете --"; category dropdown shows the full category list.

- T5 — Modal opens on row click (SC4): Clicking a results row sets `selectedRow` and renders `RecordDetailModal` in the DOM. Expected outcome: element with `role="dialog"` is present in the DOM after click.

- T6 — Modal displays file name (SC4): `RecordDetailModal` renders `fileName` from the `dims.files` Map for the given `file_key`. Expected outcome: the `file_name` string from the mock appears in the rendered modal output.

- T7 — Modal close button (SC5): Clicking the close button calls the `onClose` prop. Expected outcome: `onClose` mock is called exactly once.

- T8 — Modal Escape key dismiss (SC5): Pressing Escape while the modal is open calls `onClose`. Expected outcome: `onClose` mock is called exactly once on Escape `keydown`.

- T9 — Closing modal preserves filter state (SC5): After `onClose` is invoked, `selectedSettlement` and `selectedCategory` retain their pre-click values. Expected outcome: dropdown values unchanged after modal close.

- T10 — `fetchDimensions` returns `files` Map: `fetchDimensions()` with a `dim_file` mock returns an object where `dims.files` is a `Map<file_key, {file_name, zip_date}>`. Expected outcome: `dims.files.get(mockFileKey)` returns the expected mock object.

- T11 — `fetchReport2` rows include `file_key`, `fileName`, `zipDate`: Each enriched row from `fetchReport2` has `file_key`, `fileName`, and `zipDate` properties. Expected outcome: `row.file_key` is defined; `row.fileName` matches the expected value from the `dims.files` mock; `row.zipDate` is defined.

- T12 — Lookback routing in cross-filter RPC calls: For a D-1 `selectedDate`, `fetchCategoriesForSettlement` and `fetchSettlementsForCategory` are invoked with `currentDateKey` (D's key), not the D-1 `date_key`. Expected outcome: the mock cross-filter functions receive `currentDateKey` as the `dateKey` argument.

- T13 — New RPC functions present in `load_supabase.py`: `_CREATE_RPC_FUNCTIONS` contains `get_categories_for_settlement` and `get_settlements_for_category` definitions. Expected outcome: both function names are present as strings in `src/load_supabase.py`.

- T14 — New index present in `load_supabase.py`: `_CREATE_INDEXES` contains `idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)`. Expected outcome: that exact string is present in `src/load_supabase.py`.

- T15 — `RecordDetailModal.jsx` file exists (SC4): File `react-app/src/components/RecordDetailModal.jsx` is present with non-zero size. Expected outcome: file system check confirms file exists.

- T16 — `RecordDetailModal.test.jsx` file exists (SC7): File `react-app/src/components/RecordDetailModal.test.jsx` is present. Expected outcome: file system check confirms file exists.

- T17 — `npm run test` passes (SC7): All automated tests pass after changes. Expected outcome: `npm run test` exits with code 0; no failing test cases reported.

- T18 — `npm run build` exits 0 (SC6): Build completes without error or new warnings. Expected outcome: `npm run build` exits with code 0; no new ESLint or Vite warnings.

- T19 — `load_supabase.py` re-run idempotency: Running `load_supabase.py` a second time produces no errors from the new DDL. Expected outcome: second run exits 0; `CREATE INDEX IF NOT EXISTS` and `CREATE OR REPLACE FUNCTION` complete without error.

- UAT-01 (SC1, SC2): See UAT_scenarios.md — UAT-01: Manual verification that selecting a settlement narrows the category list and selecting a category narrows the settlement list bidirectionally.

- UAT-02 (SC3): See UAT_scenarios.md — UAT-02: Manual verification that changing the date resets both dropdowns to unselected.

- UAT-03 (SC4): See UAT_scenarios.md — UAT-03: Manual verification that clicking a result row opens the detail modal with all expected fields, including source file name.

- UAT-04 (SC5): See UAT_scenarios.md — UAT-04: Manual verification that closing the modal (close button and Escape) dismisses it without resetting filter selections.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

This request extends an existing RPC-driven filter pattern in a well-structured client-only React SPA. The chosen mechanism (Q001-A, RPC functions following the `get_settlements_for_date` precedent) is the lowest-risk path: no schema additions, no ETL changes, and the two new PostgreSQL functions are simple `STABLE sql`-language functions. The key deployment dependency — the `(date_key, category_key)` index must exist before the new RPC produces sub-second results on the full fact table — is correctly handled because `load_supabase.py` provisions both DDL blocks in a single idempotent run.

- The lookback routing requirement is the highest technical risk: cross-filter RPC calls for D-1/D-2 must use `currentDateKey` (D's key), not the lookback date_key. A subtle routing error returns empty filter sets for two of the three date views with no visible error message. The existing `fetchSettlementsForDate` implementation provides a tested template that must be replicated exactly.
- Combining index and RPC DDL into the existing `create_tables` function is architecturally correct and maintains `load_supabase.py` as the sole Supabase provisioning entry point.
- The `dims.files` Map provides O(1) file name lookup per row during enrichment in `fetchReport2`, avoiding N+1 Supabase queries. This is the correct approach.
- A pre-existing documentation discrepancy exists: `context.md` describes `_CREATE_INDEXES` as targeting `fact_prices` but the actual code targets `fact_prices_lookback`. This must be corrected in Task 8.

### Product Owner

This feature directly eliminates a documented user friction: selecting incompatible settlement+category combinations that yield no results. By restricting each dropdown to valid options, the empty-result state becomes unreachable via the cross-filtered dropdowns. The source file provenance in the modal addresses a secondary transparency need supporting trust in government-published data.

- The six success criteria (SC1–SC7) are well-defined and independently testable. SC1 and SC2 cover the bidirectional filter behavior; SC3 covers state reset on date change; SC4 and SC5 cover the modal lifecycle; SC6 and SC7 are quality gates.
- A minor acceptance gap: the success criteria do not specify the user-visible feedback when a settlement is auto-cleared after a conflicting category selection (A7). Without an on-screen message, users may be confused about why their city disappeared. This should be addressed in the UI implementation.
- The "full record details" modal field list should use Bulgarian labels matching the existing table headers, not raw field names. This is a UI detail resolvable during Task 5 implementation without a new Q-block.
- The out-of-scope boundary (Reports 1 and 3 unchanged) is correctly maintained.

### User

The bidirectional cross-filtering removes the most common empty-result failure mode. A user selecting a small city can now immediately see which product categories have data for that city, without trial and error. The record detail modal provides access to provenance information that price-watchdog users need to verify source data quality.

- Making table rows clickable introduces an interactive affordance that is currently absent. A hover highlight and pointer cursor on `<tr>` elements would signal row clickability and improve discoverability.
- The auto-clear of a settlement when it conflicts with a category selection (A7) may surprise users. A brief on-screen message explaining the auto-clear (e.g., "Selected city cleared — not available for this category") would reduce confusion significantly.
- The Escape key dismissal and close button are standard user expectations for modal dialogs and are correctly in scope.
- The date selector remains unchanged; resetting both dropdowns on date change preserves existing user expectations and is the correct behavior.

### Security Officer

This feature introduces no new authentication surfaces. The two new RPC functions are granted to the `anon` role, consistent with all existing RPC functions (`get_available_dates`, `get_settlements_for_date`). They return integer keys only — no PII, no sensitive commercial data.

- `dim_file.file_name` and `dim_file.zip_date` are government-published archive metadata. They are public data; no sensitive information is exposed via the modal.
- The `file_key` column added to `fetchReport2` is a surrogate integer key. No data exposure risk.
- All Supabase calls continue using the anon key with SELECT/EXECUTE permissions. No new secrets, environment variables, or authentication flows are introduced.
- The new RPC function SQL uses parameterised inputs (`p_settlement_key bigint`, `p_category_key bigint`, `p_date_key bigint`) — PostgREST translates these from the JSON body of the POST request, preventing SQL injection.
- No credentials, PII, or sensitive data paths are introduced by this request.

### Data Governance Officer

This request reads from an existing column (`file_key`) in `fact_prices_lookback` and from an existing dimension table (`dim_file`), both populated by the current ETL pipeline. No new data is produced, retained, or classified.

- `dim_file` contains government-published archive metadata (file name and zip date). This is public data with no retention or classification obligations beyond the existing rolling 3-date policy.
- The `file_key` linkage from fact rows to `dim_file` surfaces an auditable data lineage chain in the UI: each price record is traceable to the specific ZIP archive submitted by the retailer. This strengthens the transparency value of the product.
- Cross-filter RPC functions aggregate server-side and return only integer keys — no raw PII or commercially sensitive price data is exposed in a new channel.
- A pre-existing data governance gap: `prune_dim_date` removes `dim_date` rows outside the rolling 3-date window but does not explicitly prune `dim_file` rows for those dates. If there is no FK cascade from `dim_date` to `dim_file`, historical `dim_file` rows accumulate indefinitely. This gap is outside the scope of this request but should be documented in the context update.

- **Scope summary:** Changes span `react-app/src/components/Report2.jsx`, `react-app/src/lib/dataService.js`, a new `react-app/src/components/RecordDetailModal.jsx` component, conditionally `src/load_supabase.py` (for new RPC functions or a summary table depending on Q001), and corresponding test files.

- **Key risk:** The cross-filter retrieval mechanism (RPC functions vs. pre-computed summary table) is an open architectural decision (see Q001 in `request.md`). The implementation approach diverges meaningfully depending on the answer and affects `load_supabase.py` scope.

- **`request.md` sections updated this run:** `## Goal`, `## Background`, `## Scope`, `## Out of scope`, `## Constraints`, `## Success criteria` (all drafted new); `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs` (generated or updated).

---

## Domain Knowledge Essentials

**Retailer price data (kolkostruva.bg/opendata):** Bulgarian government regulation requires retail companies to submit daily price lists. Each submission is a CSV file inside a dated ZIP archive. The source CSV file is the unit of data provenance for any individual price record.

**Settlement (Населено място):** An administrative unit in Bulgaria (town, village) identified by an EKATTE code. In the app's star-schema this maps to `dim_settlement`. In Report 2 the settlement represents the geographic location of the store selling the product.

**Category (Категория):** A product group classification (e.g., dairy, bakery, produce). In the star-schema this maps to `dim_category`. Not all categories are sold in all cities; the set of (settlement, category) pairs with data varies day by day as retailers submit differing product assortments.

**Source file (Файл-източник):** The individual CSV file within the daily ZIP archive from which a price record originated. Stored in `dim_file` (columns: `file_key`, `file_name`, `zip_date`). Each fact row in `fact_prices_lookback` carries a `file_key` FK linking it to its source file, enabling full data lineage per record.

**D / D-1 / D-2 lookback:** The React app shows prices for three dates (today, yesterday, day-before-yesterday). Fact rows for all three dates are stored in a single Supabase table (`fact_prices_lookback`) under D's `date_key`, with separate price columns for D-1 and D-2 (`retail_price_day1`, `promo_price_day1`, etc.). Queries for D-1 and D-2 must therefore use D's `currentDateKey`, not the date_key of D-1 or D-2 themselves.

**Impacted roles/personas:**
- End users of the React app (retail price analysts, journalists, consumers): they interact with the dropdown filters and the detail modal.
- Data engineers (internal): any schema or ETL changes to `load_supabase.py` affect the Supabase provisioning step.

**Business process touched:** Retail price discovery and provenance inspection. Cross-filtering reduces empty-result frustration; the detail modal enables data quality verification by exposing the contributing source file.

---

## Technical Knowledge & Terms

**`fact_prices_lookback`:** The sole Supabase fact table (since R-20260430-0825). Columns relevant to this request: `date_key`, `store_key`, `file_key`, `category_key`, `product_key`, `retail_price`, `promo_price`, `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`. Confirmed via local CSV header inspection.

**`dim_file`:** Dimension table with columns `file_key`, `file_name`, `zip_date`. One row per source CSV file per date. Approximately 200+ rows per date; with a 3-day rolling retention window, around 600+ rows total in Supabase at any time. Confirmed from local `data/schema/dim_file.csv` sample.

**`dim_settlement_category` (hypothetical):** A potential pre-computed summary table holding DISTINCT (date_key, settlement_key, category_key) tuples from `fact_prices_lookback`. Would be populated by `load_supabase.py` and loaded at startup by `fetchDimensions()`. Its existence depends on the resolution of Q001.

**`get_settlements_for_date` RPC:** Existing PostgreSQL function provisioned by `load_supabase.py`. Returns DISTINCT settlement_keys for a given `p_date_key` by querying `fact_prices_lookback`. GRANTed EXECUTE to anon. The pattern for any new cross-filter RPCs would mirror this function.

**`lookbackColumnMap`:** A `Map<date_key, 'current'|'day1'|'day2'>` built at dimension-load time from `dim_date` position. Used throughout `dataService.js` to route queries and select price columns for lookback dates. Any new cross-filter function must read and apply this map.

**`currentDateKey`:** The `date_key` of D (the date with actual fact rows in Supabase). D-1 and D-2 queries must use this key, not their own `date_key`, because all lookback data is stored under D in `fact_prices_lookback`.

**`fetchDimensions()`:** Module-level cached async function in `dataService.js`. Loads dim_date, dim_settlement, dim_category, dim_store, dim_company, and calls `get_available_dates` RPC in parallel. Returns a single `_dims` object. Adding `dim_file` here is a minor extension.

**`fetchReport2()`:** Paginates fact rows filtered by `(date_key, category_key, store_key IN [stores for settlement])`. Currently selects `product_key, store_key, category_key, <price_columns>`. Needs `file_key` added to the select list.

**`RecordDetailModal`:** New React component. A modal overlay pattern: a semi-transparent backdrop, a centered dialog card with all record fields, a close button, and Escape-key listener. No third-party modal library is required given the existing CSS-only approach of the app.

**`Report2.jsx`:** Current cross-filtering state: the settlements list is reloaded on date change via `fetchSettlementsForDate`; the categories list is built from all `dimensions.categories` entries without any settlement-dependent filtering. This is the primary file to modify.

**Technologies involved:** React 18, Vite, Supabase PostgREST, `@supabase/supabase-js` v2, Vitest + Testing Library (test suite), PostgreSQL (Supabase-hosted).

**Non-functional attributes:**
- Performance: cross-filter queries must avoid full-table scans. The existing `get_settlements_for_date` RPC uses a DISTINCT query on `fact_prices_lookback`; without an index on `(date_key, category_key)` or `(date_key, settlement_key, category_key)`, new cross-filter RPCs or table queries could be slow. A composite index or a pre-computed table is required.
- Security: no new data exposure; `dim_file` contains only file names and dates — no PII or secrets.
- Testability: the modal and cross-filter state changes are unit-testable with mocked `dataService` functions.

**Files read:**
- `.aib_memory/request.md` — newly drafted for this request.
- `.aib_memory/context.md` — full product context including all existing RPC functions and React component descriptions.
- `react-app/src/components/Report2.jsx` — full current implementation.
- `react-app/src/lib/dataService.js` — full current data-service implementation.
- `react-app/src/components/Report2.test.jsx` — existing test suite for Report2.
- `data/schema/dim_file.csv` — confirmed file_key, file_name, zip_date columns.
- `data/schema/fact_prices_lookback.csv` (header only) — confirmed file_key column present in fact rows.
- `.aib_brain/conventions/analysis-convention.md` — this convention.
- `.aib_brain/conventions/request-convention.md` — request convention.

---

## Research Results

**Pattern: bidirectional linked filter dropdowns in data-grid UIs.** This pattern is widely established in BI dashboards and data exploration tools. The two canonical implementation strategies found across production React codebases are:

1. **On-demand server-side filter:** On each dropdown selection, call a server endpoint (or RPC) that returns the valid values for the other dropdown given the current selection and date context. This follows the existing `get_settlements_for_date` RPC pattern already in the codebase.

2. **Pre-fetched cross-reference table:** Load the full set of valid (settlement, category) pairs for the active date at startup. Client-side filter the dropdowns without additional network calls. This is the "summary matching table" approach the developer hinted at.

**Pattern: detail modal per table row.** Standard in data tables: clicking a row opens an overlay/drawer with enriched details. Common React implementation: controlled state (`selectedRow`, `setSelectedRow`), conditional render of the modal component, Escape key listener via `useEffect`. No external library needed for simple overlays.

**Pattern scan against existing codebase conventions:**
- The existing `get_settlements_for_date` RPC is the established precedent for server-side filtered lookups.
- `fetchDimensions()` already loads and caches several dimension tables; adding `dim_file` follows the established pattern.
- The existing `normalizeRow()` and `lookbackColumnMap` idioms must be applied to any new cross-filter function that touches lookback data.

---

## External Benchmarking

**React controlled dropdown cross-filtering (industry standard):** Multiple production React applications (Material UI DataGrid, AG Grid, Ant Design Table examples) implement linked filter dropdowns by either (a) pre-loading a cross-reference index at startup or (b) calling a debounced API on each selection. The pre-load approach is recommended when the cross-reference set is bounded and small (< 100 k pairs); the on-demand API approach is preferred for unbounded or frequently changing cross-reference sets. For this codebase, the (date, settlement, category) tuple space with a 3-day rolling window is bounded and manageable.

- Takeaway: a pre-loaded summary table eliminates per-interaction latency but requires an additional provisioning step in `load_supabase.py`. This is the architecturally cleaner long-term choice for a dataset of this bounded size.
- Applicability: applicable with moderate adaptation (the existing `fetchDimensions()` cache pattern maps directly onto a pre-loaded cross-reference table).
- Adoption decision: **pending Q001 resolution.** RPC approach is simpler to implement now; summary table is more performant and scalable.

**Supabase/PostgREST DISTINCT query patterns:** PostgREST supports `SELECT DISTINCT` via PostgreSQL functions (RPC). The existing `get_settlements_for_date` function uses this pattern and is already proven in production for this codebase. Extending with two new RPC functions (`get_categories_for_settlement`, `get_settlements_for_category`) is a low-risk, well-precedented approach.

- Takeaway: RPC functions with `DISTINCT` are performant when combined with a composite index on `fact_prices_lookback(date_key, settlement_key, category_key)`. Without such an index, a DISTINCT scan over millions of rows could be slow.
- Applicability: directly applicable; `load_supabase.py` already provisions RPC functions via `CREATE OR REPLACE FUNCTION`.
- Adoption decision: applicable regardless of Q001 outcome; the composite index is needed in both the RPC and summary-table approaches (for populating the summary table efficiently).

---

## Minimal Spikes and Experiments

**Spike: Confirm `file_key` column presence in `fact_prices_lookback`.**
- Hypothesis: `fact_prices_lookback` in Supabase has a `file_key` column available for fetching in React queries.
- Approach: Read the header row of `data/schema/fact_prices_lookback.csv` (the local source file used to populate Supabase).
- Outcome: Header confirmed as `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2`. `file_key` is present.
- Conclusion: No schema change is required to expose file provenance per record; `fetchReport2` only needs to add `file_key` to its select list.

**Spike: Estimate `dim_file` row count for startup-load feasibility.**
- Hypothesis: `dim_file` is small enough to load at startup without perceptible delay.
- Approach: Inspected `data/schema/dim_file.csv` sample; confirmed ~200+ entries per date. With a 3-day rolling window, Supabase holds approximately 600 rows.
- Outcome: 600 rows fits comfortably within a single Supabase paginated fetch (page size 1000); load time is negligible.
- Conclusion: `dim_file` can be added to `fetchDimensions()` without startup performance concern.

**Spike: Verify the `get_settlements_for_date` RPC as a pattern template.**
- Hypothesis: The RPC provisioning code in `load_supabase.py` is structured to allow additional RPC functions to be added with minimal changes.
- Approach: Reviewed context.md; `_CREATE_RPC_FUNCTIONS` is a string constant passed to `create_tables(conn)`. Adding new functions means appending to this constant.
- Outcome: Confirmed — the provisioning block is a single SQL string; new `CREATE OR REPLACE FUNCTION` blocks can be appended.
- Conclusion: Adding new cross-filter RPC functions to `load_supabase.py` requires only adding SQL to `_CREATE_RPC_FUNCTIONS` and `GRANT EXECUTE TO anon` statements.

---

## AI Copilot Suggestions

- **Cross-filter UX symmetry is incomplete if only one direction triggers a re-filter.** The request specifies bidirectional filtering, but a subtle UX gap exists: after the user selects a city (which filters categories) and then picks a category (which re-filters cities), the currently selected city might no longer appear in the re-filtered city list if the data is sparse. The implementation must handle the case where the currently selected settlement becomes invalid after a category-triggered city re-filter — and either auto-clear or auto-retain the selection with a visual cue.
  - Suggestion: Define a clear rule before implementation: if the currently selected settlement is not in the new city list after a category selection, clear the settlement selection (and the result rows) and show a prompt. Document this rule in the success criteria.

- **The `fact_prices_lookback` table may lack a composite index on `(date_key, category_key)` needed for cross-filter RPC performance.** The existing indexes in `load_supabase.py` are `idx_fact_prices_date_key ON fact_prices(date_key)` and `idx_fact_prices_date_store ON fact_prices(date_key, store_key)`. These are on `fact_prices`, not on `fact_prices_lookback`. A DISTINCT query over `fact_prices_lookback` filtering on `(date_key, category_key)` or `(date_key, settlement_key)` (via store join) without a supporting index could perform a full table scan on millions of rows. This is a high-risk implementation gap regardless of whether RPCs or a summary table are chosen.
  - Suggestion: Add `CREATE INDEX IF NOT EXISTS idx_fact_prices_lookback_date_cat ON fact_prices_lookback(date_key, category_key)` and `idx_fact_prices_lookback_date_store ON fact_prices_lookback(date_key, store_key)` to `_CREATE_INDEXES` in `load_supabase.py`. These should be created before the cross-filter mechanism is exercised.

- **Scope is appropriately sized for the stated goal — but the modal implementation is underspecified.** The request says "full info from the record." This leaves open what constitutes "full info." The fact row contains `date_key, store_key, file_key, category_key, product_key, retail_price, promo_price` plus lookback price columns. Most of these are foreign keys that require human-readable label resolution. Failing to define what the modal should show precisely risks an implementation that either shows raw surrogate keys (uninformative) or duplicates all enrichment already visible in the table row (redundant).
  - Suggestion: The plan should specify exactly which fields are shown in the modal — recommended: product name, category name, settlement name, store name, company name, effective price, retail price, promo price, date (formatted), and source file name + file date. Surrogate keys (product_key, store_key, etc.) should NOT appear in the modal UI.

- **No existing integration test coverage for Supabase RPC functions.** The test suite mocks all `dataService` functions. New RPC functions provisioned in `load_supabase.py` will not be covered by any automated test in the React layer. The risk is that a PostgreSQL syntax error in a new RPC goes undetected until `load_supabase.py` is actually run against a live Supabase instance.
  - Suggestion: Add a validation step in the plan: manually run `load_supabase.py` against a dev/staging Supabase instance after adding new RPC functions, and verify they appear in the Supabase function list before relying on them in the React app.

---

## Testing

- T1 — Category dropdown filters on settlement select: After selecting a settlement in Report 2, the category dropdown renders fewer items than the full category list. Expected outcome: The category `<select>` contains only options matching categories returned by the cross-filter data function for that (settlement, date) pair; the unfiltered count is greater than the filtered count in test fixtures.

- T2 — Settlement dropdown re-filters on category select: After a settlement is selected and then a category is selected, the settlement dropdown is re-rendered with only settlements valid for that category. Expected outcome: The settlement `<select>` contains fewer options than the initial full list (given test fixture data with sparse coverage).

- T3 — Invalid settlement cleared after category-triggered re-filter: If the currently selected settlement is not present in the re-filtered settlement list after a category is chosen, the settlement selection is cleared. Expected outcome: `selectedSettlement` state is empty string and results table shows no rows.

- T4 — Date change resets both dropdowns: Changing `selectedDate` prop resets both settlement and category to empty string. Expected outcome: Both `<select>` elements show the default "-- Изберете --" option with no value, and the results table is empty.

- T5 — Modal opens on row click: When a row is clicked in the results table, `RecordDetailModal` is rendered. Expected outcome: A modal element appears in the DOM with role `dialog`.

- T6 — Modal shows source file name: The modal content includes the `file_name` from the matched `dim_file` entry for the row's `file_key`. Expected outcome: The modal DOM contains the file name string from the test fixture.

- T7 — Modal closes on close button click: Clicking the close button inside the modal removes it from the DOM. Expected outcome: No element with role `dialog` is present after the close button is clicked.

- T8 — Modal closes on Escape key: Pressing the Escape key while the modal is open dismisses it. Expected outcome: No element with role `dialog` is present after the keydown event.

- T9 — Filter selections not reset after modal close: After opening and closing the modal, the settlement and category dropdowns retain their previously selected values. Expected outcome: Both `<select>` elements show the same selected values as before the modal was opened.

- T10 — Build exits 0: `npm run build` in `react-app/` exits with code 0. Expected outcome: Exit code is 0; no new console warnings about missing props or unresolved modules.

- T11 — Existing tests remain green: `npm run test` in `react-app/` produces no failing tests. Expected outcome: All previously passing tests continue to pass; no regressions.

- T12 — Cross-filter with lookback date (D-1): When D-1 is the selected date, the cross-filter mechanism uses `currentDateKey` (D's key) for the Supabase query. Expected outcome: The data fetch is called with D's `date_key`, not D-1's `date_key`.

- T13 — `dim_file` loaded in dimensions cache: `fetchDimensions()` returns a `files` property that is a `Map` keyed on `file_key`. Expected outcome: The returned `_dims.files` is a Map with at least one entry matching the test fixture.

- T14 — `fetchReport2` includes `file_key` in each result row: Each row returned by `fetchReport2` has a `file_key` property. Expected outcome: `result[0].file_key` is a defined, non-null integer in the mocked test.

See UAT_scenarios.md — UAT-01, UAT-02, UAT-03 for manual validation scenarios that cannot be fully expressed as automated assertions.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request introduces a sensible and well-bounded UX improvement to an existing feature. The bidirectional cross-filter requirement maps cleanly onto the existing RPC function pattern (`get_settlements_for_date`) and does not require any changes to the ETL layer unless the summary-table approach is chosen. The main architectural risk is performance: `fact_prices_lookback` holds millions of rows, and any new DISTINCT query without a composite index could degrade to a full-table scan. The current `load_supabase.py` provisions indexes only on `fact_prices` (the deleted table), so `fact_prices_lookback` likely has no helpful composite index yet. Addressing this is critical before going live.

- The open Q001 decision (RPC vs. summary table) blocks implementation planning for `load_supabase.py`; resolving it should be the first implementation step.
- Adding `dim_file` to `fetchDimensions()` is low-risk and consistent with the existing caching approach.
- The `RecordDetailModal` component can be implemented entirely within the React layer with no backend changes, making it the lower-risk half of this request.
- A composite index on `fact_prices_lookback(date_key, category_key)` is needed regardless of the Q001 outcome and should be provisioned proactively.

### Product Owner

This request delivers measurable user value: eliminating empty result states (caused by incompatible filter combinations) directly reduces task-abandonment in the most data-rich report view. The detail modal closes a data-provenance gap that is relevant to journalists and analysts who need to trace a price back to its original government-submitted file. The success criteria are clearly defined and verifiable. The scope is well-bounded and does not introduce breaking changes to other report pages.

- SC3 (date-reset behavior) correctly preserves existing UX expectations for settlement selection.
- The request does not define what happens when the currently selected settlement disappears after a category re-filter — this gap should be resolved (see AI Copilot Suggestions).
- No explicit acceptance criteria cover the lookback date scenario (D-1/D-2 cross-filtering); adding a success criterion covering this would improve completeness.

### User

The bidirectional linked filter will significantly reduce the frustration of seeing "Няма данни за показване" after selecting a city/category combination that yields no results. The current behavior requires trial-and-error; the new behavior guides the user to valid combinations. The detail modal satisfies the curiosity of power users who want to know the data source, without cluttering the table view for casual users.

- The filtering should feel instantaneous; if the cross-filter involves a network call per selection, a brief loading indicator is needed to prevent the user from interpreting a loading pause as unresponsiveness.
- The modal must be dismissible with both click-outside and Escape key for standard UX expectations.
- If the settlement selection is auto-cleared after a category selection invalidates it, users should see a clear explanatory message, not a silent reset.

### Security Officer

This request presents minimal additional security surface. The only new data exposed is `dim_file` (file names and dates from government-submitted CSV files — no PII, no credentials). All existing security constraints (anon key only, RLS-enforced SELECT, no hardcoded credentials) continue to apply. The new RPC functions (if chosen) must include `GRANT EXECUTE TO anon` to match the existing pattern and must not expose any data beyond what is already accessible via table SELECT.

- No authentication or authorization changes are introduced.
- No new environment variables or secrets.
- Modal content is rendered from the same Supabase-sourced data already used in the table; no additional data pathways are opened.
- A minor note: `file_name` values originate from government-submitted CSV filenames. While these are non-sensitive, the modal should escape/display them as plain text, not render them as links or executable content.

### Data Governance Officer

`dim_file` provides data lineage at the record level: every price fact can be traced to its source government-submitted CSV file. Exposing this in the UI increases transparency and supports the product's public accountability mission. No new data is collected, transmitted beyond the existing Supabase→browser path, or retained at the client beyond a single session's memory. The rolling 3-day retention window for `fact_prices_lookback` and `dim_file` in Supabase is unaffected by this request.

- The cross-filter summary table (if chosen) would hold derived data (DISTINCT tuples) from `fact_prices_lookback`; its retention policy should mirror the source table's 3-day rolling window.
- No new classification categories are introduced; all data exposed is already public (government open-data).
- No compliance impact identified (no GDPR, no financial data, no health data involved).
