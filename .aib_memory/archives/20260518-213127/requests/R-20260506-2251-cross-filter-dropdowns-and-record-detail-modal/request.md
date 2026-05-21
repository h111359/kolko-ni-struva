## Goal

Add bidirectional cross-filtering between the "Населено място:" (Settlement) and "Категория:" (Category) dropdown selectors in the "Продукти" page (Report 2) of the React app: selecting a settlement filters the category list to only categories that have price data for that city on the selected date, and vice versa. Additionally, make each row in the product results table clickable to open a modal dialog showing the full record details, with particular emphasis on the source file that contributed the record to the dataset.

## Background

Report 2 ("Отчет 2: Продукти по населено място и категория") currently presents two fully independent dropdown filters for settlement and category. A user selecting a city has no way to know which product categories are represented in that city for the chosen date — the category list shows all categories regardless. This frequently leads to empty result sets when the user picks a combination that yields no fact rows. Bidirectional linked filtering eliminates this friction by restricting each dropdown to only the options that produce results given the other dropdown's current selection.

Each row in the results table currently exposes seven columns (product name, price, retail price, promo price, store, chain, date) but is not interactive. Users have no way to inspect the full provenance of a record — specifically the source CSV file submitted by the retailer — without accessing the raw data directly. A per-row detail modal addresses this transparency gap and supports auditability of the government-provided data.

Performance is an explicit concern from the developer. The fact table (`fact_prices_lookback`) holds millions of rows. Cross-filter lookups must not degrade perceived response time; an efficient data-retrieval mechanism (new RPC functions following the existing pattern, or a pre-computed summary table) is required.

## Scope

- Modify `react-app/src/components/Report2.jsx` to implement bidirectional cross-filtering between the settlement and category dropdowns.

- When a settlement is selected, the category dropdown is filtered to show only categories with at least one price record for that settlement on the selected date.

- When a category is selected, the settlement dropdown is re-filtered to show only settlements that have at least one record in that category for the selected date.

- Changing the selected date resets both dropdowns to "unselected" (existing behavior preserved).

- Implement a data-retrieval mechanism in `react-app/src/lib/dataService.js` to efficiently retrieve the set of available categories for a given (date, settlement) and the set of available settlements for a given (date, category). The mechanism must handle the D/D-1/D-2 lookback routing already established in the codebase.

- Implement two new PostgreSQL RPC functions in `src/load_supabase.py`: `get_categories_for_settlement(p_settlement_key bigint, p_date_key bigint)` returning `SETOF int` (distinct `category_key` values) and `get_settlements_for_category(p_category_key bigint, p_date_key bigint)` returning `SETOF int` (distinct `settlement_key` values via `dim_store` join). Both functions follow the existing `get_settlements_for_date` pattern, query `fact_prices_lookback`, and are granted `EXECUTE` to the `anon` role. (Q001-A resolved)

- Extend `fetchReport2()` in `dataService.js` to include `file_key` in the selected columns.

- Load `dim_file` as part of `fetchDimensions()` and expose it as a `Map<file_key, {file_name, zip_date}>` in the dimensions cache.

- Create `react-app/src/components/RecordDetailModal.jsx`: a modal component that receives a record object and a close handler, and displays all record fields plus source file name and zip date from `dim_file`.

- Modify `Report2.jsx` to attach a click handler to each table row that opens `RecordDetailModal` for that row.

- Add or update automated tests in `react-app/src/components/Report2.test.jsx` to cover the cross-filtering and modal behaviors.

- Create `react-app/src/components/RecordDetailModal.test.jsx` with smoke and content tests.

- Update `.aib_memory/context.md` to reflect the new features.

## Out of scope

- Cross-filtering is not applied to Report 1 or Report 3; they each have a single filter selector and the bidirectional pattern does not apply.
- ETL pipeline scripts (`src/extract.py`, `src/transform.py`) are not modified.
- No changes to data ingestion, transformation, or the local star-schema CSV files.
- No mobile-specific layout or accessibility overhaul beyond what naturally follows from adding a modal (basic keyboard dismissal is in scope).
- No new environment variables or secrets.
- No changes to the Netlify deployment configuration.
- Bulk backfill or historical cross-filter summary computation is not in scope.

## Constraints

- Performance must not degrade: the cross-filter data mechanism must not trigger full-table scans on each dropdown interaction; indexed queries or a pre-computed summary table are required.
- The React app remains strictly client-only (no serverless functions).
- All Supabase calls must continue to use the public anon key with RLS-permitted SELECT or EXECUTE access.
- Cross-filtering must correctly handle the D/D-1/D-2 lookback offset routing already implemented (fact rows for D-1/D-2 are stored under D's `date_key` in `fact_prices_lookback`; the `currentDateKey` must be used for lookback queries).
- `npm run build` must exit 0 with no new warnings after all changes.
- All existing automated tests must remain green.
- No credentials, tokens, or PII may appear in source files.

## Success criteria

- SC1: When a settlement is selected in Report 2, the category dropdown renders only categories that have at least one price record for that settlement on the selected date.
- SC2: When a category is selected in Report 2, the settlement dropdown is re-filtered to show only settlements that have at least one record in that category for the selected date.
- SC3: Selecting a new date resets both the settlement and category dropdowns and restores their unfiltered default lists (existing behavior preserved for the settlement dropdown; category dropdown unfiltered default is all categories).
- SC4: Clicking a row in the Report 2 results table opens a modal dialog showing all record details, including the source file name (from `dim_file.file_name`) and file date.
- SC5: Closing the modal (via close button or Escape key) dismisses it and returns focus to the table without resetting the filter selections or re-fetching data.
- SC6: `npm run build` exits 0 with no new warnings.
- SC7: All automated tests (`npm run test`) pass after changes.

## Assumptions

- A1: The "Продукти" page refers to Report 2 ("Отчет 2: Продукти по населено място и категория") — the only report view with both a settlement and a category selector simultaneously.
  - Risk if false: Wrong component is modified; cross-filter is applied to an unintended view.

- A2: `fact_prices_lookback` in Supabase contains a `file_key` column (confirmed from local CSV header). No schema migration is required to expose file provenance per record; only the `SELECT` column list in `fetchReport2` needs updating.
  - Risk if false: `file_key` is absent from Supabase and the modal cannot display source file info without a DDL change.

- A3: `dim_file` has approximately 600 rows in Supabase (~200 retailers × 3 retained dates). This is small enough to load at startup within a single paginated `fetchAllRows` call without perceptible delay.
  - Risk if false: `dim_file` is larger than expected (e.g., pruning does not cover it and rows accumulate historically), causing a startup delay.

- A4: Cross-filtering applies only to the currently selected date context (D, D-1, or D-2). Lookback date (D-1, D-2) cross-filter queries must use `currentDateKey` (D's `date_key`), consistent with the existing `fetchSettlementsForDate` implementation.
  - Risk if false: Cross-filter for D-1/D-2 returns incorrect or empty results.

- A5: `fact_prices_lookback` in Supabase does not currently have a composite index on `(date_key, category_key)`. A new index is required to support efficient `get_settlements_for_category` queries without full-table scans. The existing `idx_fact_prices_lookback_date_store ON (date_key, store_key)` already covers `get_categories_for_settlement`.
  - Risk if false: If the `(date_key, category_key)` index already exists, the `CREATE INDEX IF NOT EXISTS` DDL is idempotent and harmless.

- A6: The new RPC functions will return settlement_keys or category_keys consistent with the existing backward-compatibility guard already present in `fetchSettlementsForDate` (PostgREST v11+ plain integers / v10 wrapped objects). The same guard must be applied to both new JS caller functions.
  - Risk if false: The PostgREST version handling deviates from existing behavior, causing type errors in the cross-filter result mapping.

- A7: The currently selected settlement must be auto-cleared if it disappears from the re-filtered settlement list after a category selection. Retaining an invalid selection would produce a confusing empty-results state.
  - Risk if false: The auto-clear UX is undesirable; a different interaction design is required (pending Q002 answer for cascade behavior).

## Plan

### Task 1: Update `load_supabase.py` — new index and RPC functions
**Intent:** Provision the composite index and two cross-filter RPC functions required by the React app.
**Inputs:** `src/load_supabase.py` (`_CREATE_INDEXES` and `_CREATE_RPC_FUNCTIONS` constants).
**Outputs:** Updated `src/load_supabase.py` with one new `CREATE INDEX IF NOT EXISTS` statement and two new `CREATE OR REPLACE FUNCTION` blocks.
**External Interfaces:** Supabase PostgreSQL (applied at next `load_supabase.py` run).
**Environment & Configuration:** `DATABASE_URL` in `.env`; no new secrets.
**Procedure:**
1. Open `src/load_supabase.py`.
2. In `_CREATE_INDEXES`, append `CREATE INDEX IF NOT EXISTS idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key);`. Do NOT add a second `(date_key, store_key)` index — `idx_fact_prices_lookback_date_store` already covers that.
3. In `_CREATE_RPC_FUNCTIONS`, append `get_categories_for_settlement(p_settlement_key bigint, p_date_key bigint) RETURNS SETOF int` — queries `fact_prices_lookback` for DISTINCT `category_key` values where `store_key IN (SELECT store_key FROM dim_store WHERE settlement_key = p_settlement_key)` and `date_key = p_date_key`.
4. Append `get_settlements_for_category(p_category_key bigint, p_date_key bigint) RETURNS SETOF int` — queries `fact_prices_lookback` joined to `dim_store` for DISTINCT `settlement_key` values where `category_key = p_category_key` and `date_key = p_date_key`.
5. Add `GRANT EXECUTE ON FUNCTION get_categories_for_settlement(bigint, bigint) TO anon;` and `GRANT EXECUTE ON FUNCTION get_settlements_for_category(bigint, bigint) TO anon;`.
**Done Criteria:** All DDL present in the constants; `load_supabase.py` is syntactically valid; running it idempotently creates the index and functions without error; T13, T14, T19 pass.
**Dependencies:** None.
**Risk Notes:** Index creation on a large `fact_prices_lookback` table may take several minutes on first run.

### Task 2: Add cross-filter JS functions to `dataService.js`
**Intent:** Implement the front-end data functions that call the new RPCs and apply lookback routing.
**Inputs:** `react-app/src/lib/dataService.js`; the two new Supabase RPC functions from Task 1.
**Outputs:** Two new exported async functions in `dataService.js`: `fetchCategoriesForSettlement(settlementKey, dateKey, dims)` and `fetchSettlementsForCategory(categoryKey, dateKey, dims)`.
**External Interfaces:** Supabase PostgREST (`supabase.rpc('get_categories_for_settlement', ...)`, `supabase.rpc('get_settlements_for_category', ...)`).
**Environment & Configuration:** No new secrets; anon key with GRANT EXECUTE.
**Procedure:**
1. Add `fetchCategoriesForSettlement(settlementKey, dateKey, dims)`: resolve offset from `dims.lookbackColumnMap`; for D-1/D-2 use `dims.currentDateKey`; call `supabase.rpc('get_categories_for_settlement', { p_settlement_key: settlementKey, p_date_key: queryDateKey })`; apply PostgREST version guard; map keys to `{category_key, name}` objects from `dims.categories`; sort by name; return array. Fallback to all categories on RPC error.
2. Add `fetchSettlementsForCategory(categoryKey, dateKey, dims)`: same pattern; call `supabase.rpc('get_settlements_for_category', ...)`; map to `{settlement_key, name}` from `dims.settlements`; sort alphabetically. Fallback to all settlements on RPC error.
**Done Criteria:** Both functions exported; T1, T2, T12 pass in the test suite.
**Dependencies:** Task 1 (RPC functions must exist in Supabase).

### Task 3: Load `dim_file` in `fetchDimensions()`
**Intent:** Add `dim_file` to the startup dimension cache so file names are available for modal enrichment.
**Inputs:** `react-app/src/lib/dataService.js` (`fetchDimensions` function and `_dims` cache).
**Outputs:** `fetchDimensions()` returns `_dims.files` as `Map<file_key, {file_name, zip_date}>`.
**External Interfaces:** Supabase `dim_file` table (SELECT `file_key,file_name,zip_date`).
**Environment & Configuration:** Same anon key; no new secrets.
**Procedure:**
1. Add `fetchAllRows('dim_file', 'file_key,file_name,zip_date')` to the `Promise.all` call in `fetchDimensions()`.
2. Build a `Map<file_key, {file_name, zip_date}>` from the result.
3. Assign as `_dims.files` in the returned cache object.
**Done Criteria:** `fetchDimensions()` returns an object with a `files` Map; T10 passes; existing tests are not broken.
**Dependencies:** None.

### Task 4: Extend `fetchReport2` to include `file_key`
**Intent:** Add `file_key` to columns fetched per fact row so the modal can display source file info.
**Inputs:** `react-app/src/lib/dataService.js` (`fetchReport2` function).
**Outputs:** Each enriched row in the `fetchReport2` result includes `file_key`, `fileName`, and `zipDate`.
**External Interfaces:** Supabase `fact_prices_lookback` (column addition to SELECT list).
**Environment & Configuration:** No changes.
**Procedure:**
1. Add `file_key` to the `.select()` column string in `fetchReport2`.
2. In the enrichment step, look up `dims.files.get(row.file_key)` and assign `fileName` and `zipDate` to each enriched row.
**Done Criteria:** T11 passes; `fetchReport2` mock test confirms each returned row has `file_key`, `fileName`, and `zipDate`.
**Dependencies:** Task 3 (`dims.files` must be populated).

### Task 5: Create `RecordDetailModal` component
**Intent:** Implement the modal dialog that shows full record details for a clicked table row.
**Inputs:** An enriched row object from `fetchReport2` (with product, store, company, and file info), a close handler, and the `dimensions` cache.
**Outputs:** `react-app/src/components/RecordDetailModal.jsx`.
**External Interfaces:** None (pure React component).
**Environment & Configuration:** None.
**Procedure:**
1. Create `RecordDetailModal.jsx` with props: `row` (enriched row object), `dims` (dimension cache), and `onClose` (function).
2. Render a backdrop overlay and a centered dialog card with Bulgarian field labels: product name, category name (from `dims.categories`), settlement name (via store → dims.stores → dims.settlements), store name, company name, effective price, retail price, promo price (if non-null), date (formatted via `formatDateBG`), source file name (`fileName`), file date (`zipDate`).
3. Add a close button that calls `onClose`.
4. Add a `useEffect` that listens for the Escape key and calls `onClose`.
5. Add `role="dialog"` and `aria-modal="true"` to the dialog element.
**Done Criteria:** `RecordDetailModal.test.jsx` passes; component renders all expected fields; Escape dismisses it; T5, T6, T7, T8, T15 pass.
**Dependencies:** Task 4 (row object must include file info).

### Task 6: Modify `Report2.jsx` — cross-filtering and modal integration
**Intent:** Wire the cross-filter data functions into Report 2's dropdown state and add row-click modal behavior.
**Inputs:** `react-app/src/components/Report2.jsx`; `fetchCategoriesForSettlement` and `fetchSettlementsForCategory` from Task 2; `RecordDetailModal` from Task 5.
**Outputs:** Updated `Report2.jsx` with bidirectional cross-filter logic and modal state management.
**External Interfaces:** `dataService.js` cross-filter functions; `RecordDetailModal` component.
**Environment & Configuration:** None.
**Procedure:**
1. Import `fetchCategoriesForSettlement`, `fetchSettlementsForCategory` from `dataService.js`; import `RecordDetailModal`.
2. Add state: `filteredCategories` (initialized to all categories), `filteredSettlements` (initialized to the settlements array), `selectedRow` (null).
3. When settlement selection changes: call `fetchCategoriesForSettlement`; set `filteredCategories`. If `selectedCategory` is no longer in `filteredCategories`, clear `selectedCategory`.
4. When category selection changes: call `fetchSettlementsForCategory`; set `filteredSettlements`. If `selectedSettlement` is no longer in `filteredSettlements`, clear `selectedSettlement` and (per Q002 answer) update `filteredCategories` accordingly.
5. Render the category `<select>` from `filteredCategories` and the settlement `<select>` from `filteredSettlements`. Add a `cursor: pointer` style and hover highlight to `<tr>` elements.
6. On date change: reset `filteredCategories` to all categories and `filteredSettlements` to full settlements list after `fetchSettlementsForDate` reloads.
7. Add `onClick` to each `<tr>` in the results table that sets `selectedRow`.
8. Conditionally render `<RecordDetailModal row={selectedRow} dims={dimensions} onClose={() => setSelectedRow(null)} />` when `selectedRow` is non-null.
**Done Criteria:** UAT-01 through UAT-04 pass; T1–T9 pass; T3 behavior aligned with Q002 answer.
**Dependencies:** Tasks 2, 5. Q002 must be answered before step 4.
**Risk Notes:** Step 4 depends on Q002 answer; implement the Q002-A (recommended) path by default and adjust if Q002-B is selected.

### Task 7: Add/update automated tests
**Intent:** Ensure all new behaviors are covered by automated tests.
**Inputs:** `react-app/src/components/Report2.test.jsx`; new `react-app/src/components/RecordDetailModal.test.jsx`.
**Outputs:** Updated `Report2.test.jsx`; new `RecordDetailModal.test.jsx`.
**External Interfaces:** Vitest, Testing Library (`@testing-library/react`, `@testing-library/user-event`).
**Environment & Configuration:** None.
**Procedure:**
1. Update `Report2.test.jsx` mock for `dataService` to add `fetchCategoriesForSettlement` and `fetchSettlementsForCategory` mock functions.
2. Add tests: T1 (category filter), T2 (settlement re-filter), T3 (auto-clear), T4 (date-change reset), T5 (modal opens on row click), T9 (modal close preserves filter), T12 (lookback routing).
3. Create `RecordDetailModal.test.jsx` with: smoke render (T5), file name display (T6), close button (T7), Escape key (T8).
4. Add tests for `fetchDimensions` files Map (T10) and `fetchReport2` file enrichment (T11) in `dataService.test.js` (create if absent).
5. Run `npm run test` and confirm all pass.
**Done Criteria:** `npm run test` exits 0; T1–T19 intent is covered; T16 (file existence) passes.
**Dependencies:** Tasks 5, 6.

### Task 8: Update documentation and context
**Intent:** Reflect the new features and corrected facts in `.aib_memory/context.md` and affected documentation.
**Inputs:** `.aib_memory/context.md`, `README.md`.
**Outputs:** Updated `.aib_memory/context.md`; `README.md` updated if it describes Report 2 features.
**External Interfaces:** None.
**Procedure:**
1. Update the `Report2.jsx` description in `context.md` to include bidirectional cross-filtering state and the `RecordDetailModal`.
2. Update `dataService.js` description: `fetchDimensions()` now loads `dim_file` as `_dims.files`; two new cross-filter functions (`fetchCategoriesForSettlement`, `fetchSettlementsForCategory`); `fetchReport2` returns `file_key`, `fileName`, `zipDate`.
3. Update `load_supabase.py` description: new `(date_key, category_key)` index; new RPC functions `get_categories_for_settlement` and `get_settlements_for_category`. Correct the pre-existing error that described `_CREATE_INDEXES` as targeting `fact_prices` — it targets `fact_prices_lookback`.
4. Check `README.md` for Report 2 description; update if present.
**Done Criteria:** `context.md` accurately describes the post-implementation state of all modified components; the `fact_prices` index error is corrected.
**Dependencies:** Tasks 1–7 completed.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update descriptions of `Report2.jsx` (bidirectional cross-filtering, `RecordDetailModal`), `dataService.js` (`dim_file` loading, `fetchCategoriesForSettlement`, `fetchSettlementsForCategory`, `fetchReport2` `file_key` enrichment), and `load_supabase.py` (new `(date_key, category_key)` index, two new RPC functions). Correct the pre-existing error that described `_CREATE_INDEXES` as targeting `fact_prices` — it targets `fact_prices_lookback`.
- `README.md` (ref_id: N/A) — Inspect for Report 2 description; update if the README documents app capabilities at the report level.

## Questions & Decisions

**Q002**: When a category selection causes the currently-selected settlement to be auto-cleared (per A7), how should `filteredCategories` (the filtered category list currently based on that settlement) be updated?
- [x] Option A: Reset `filteredCategories` to the full unfiltered category list (all categories from `dims.categories`), since no settlement is now selected. *(recommended — consistent with the state when no settlement is selected; avoids showing a filtered category list with no corresponding settlement)*
- [ ] Option B: Keep `filteredCategories` as the list filtered by the previously-selected settlement, so the user can see which categories that settlement had data for before the auto-clear.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/components/Report2.jsx` | Modified | Add bidirectional cross-filtering state and logic; add row-click handler and modal mount; update settlement/category render from filtered arrays. |
| `react-app/src/lib/dataService.js` | Modified | Add `dim_file` loading to `fetchDimensions()`; add `file_key` to `fetchReport2` select and enrichment; add cross-filter data functions (RPC callers or table readers, per Q001). |
| `react-app/src/components/RecordDetailModal.jsx` | Created | New modal component displaying full record details including source file name. |
| `react-app/src/components/Report2.test.jsx` | Modified | Add tests for cross-filtering, modal open/close, and filter state preservation. |
| `react-app/src/components/RecordDetailModal.test.jsx` | Created | Smoke render, content display, close button, and Escape key tests for the new modal component. |
| `src/load_supabase.py` | Modified | Add composite indexes on `fact_prices_lookback(date_key, category_key)` and `(date_key, store_key)` to `_CREATE_INDEXES`; if Q001-A: add new RPC functions to `_CREATE_RPC_FUNCTIONS` with GRANT EXECUTE; if Q001-B: add summary table DDL and population logic. |
| `.aib_memory/context.md` | Modified | Update product context to reflect new Report 2 features and modified module descriptions. |
| `README.md` | Read-only dependency | Inspect for Report 2 description; update if present. |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal, Background, Scope, Out of scope, Constraints, Success criteria are all non-empty and internally consistent.
- Ambiguity: `request.md` § Scope — The phrase "each detail record should be clickable and should show a modal with the full info from the record" leaves "full info" undefined. Resolved by assumption: the modal displays all human-readable enriched fields (product, category, settlement, store, company, prices, date, source file name); raw surrogate keys are excluded.
- Ambiguity: `request.md` § Scope — "The performance should not suffer" is not quantified. Interpreted as: cross-filter network round-trips should complete in under 2 seconds on a typical broadband connection, consistent with existing report load times.
- Missing info: `request.md` — No explicit handling defined for the case where the currently selected settlement is no longer in the re-filtered settlement list after a category selection. Resolved via A7: auto-clear the settlement selection and prompt the user.
- Cross-ref issue: `context.md` — Describes `load_supabase.py` as provisioning indexes on `fact_prices` (the deleted table). These index statements are now dead code; the new request adds indexes on `fact_prices_lookback` which is the active fact table. This discrepancy should be noted and corrected in the documentation task.
- OK: `context.md` — Correctly identifies `fact_prices_lookback` as the sole fact table since R-20260430-0825.
- OK: `context.md` — `fetchDimensions()` description accurately reflects the current module-level cache pattern; `dim_file` addition is consistent with it.

