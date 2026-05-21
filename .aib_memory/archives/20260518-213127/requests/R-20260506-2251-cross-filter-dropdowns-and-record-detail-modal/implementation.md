Files taken into consideration:
- `.aib_memory/request.md`
- `.aib_memory/context.md`
- `.aib_memory/requests_register.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`

## Implementation Log

### Entry 2026-05-06 23:47

#### Scope
Implemented bidirectional cross-filtering between the settlement and category dropdowns in Report 2, and added a per-row RecordDetailModal displaying full record provenance including source file name. Modified `src/load_supabase.py`, `react-app/src/lib/dataService.js`, `react-app/src/components/Report2.jsx`; created `react-app/src/components/RecordDetailModal.jsx`; updated tests in `Report2.test.jsx`, `dataService.test.js`, and created `RecordDetailModal.test.jsx`; updated `.aib_memory/context.md`.

#### Changes
- Added `CREATE INDEX IF NOT EXISTS idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)` to `_CREATE_INDEXES` in `src/load_supabase.py`
- Added `get_categories_for_settlement(p_settlement_key bigint, p_date_key bigint) RETURNS SETOF int` and `get_settlements_for_category(p_category_key bigint, p_date_key bigint) RETURNS SETOF int` PostgreSQL RPC functions with `GRANT EXECUTE TO anon` to `_CREATE_RPC_FUNCTIONS` in `src/load_supabase.py`
- Updated `create_tables` docstring in `src/load_supabase.py` to reflect new index and RPC functions
- Added `fetchAllRows('dim_file', 'file_key,file_name,zip_date')` to `Promise.all` in `fetchDimensions()` in `react-app/src/lib/dataService.js`; built `fileMap` as `Map<file_key, {file_name, zip_date}>` and assigned as `_dims.files`
- Added `file_key` to `.select()` column list in `fetchReport2` in `react-app/src/lib/dataService.js`; enriched rows with `fileName` and `zipDate` from `dims.files`
- Exported `fetchCategoriesForSettlement(settlementKey, dateKey, dims)` from `react-app/src/lib/dataService.js`; calls `get_categories_for_settlement` RPC; applies PostgREST v10/v11 guard; falls back to all categories on error
- Exported `fetchSettlementsForCategory(categoryKey, dateKey, dims)` from `react-app/src/lib/dataService.js`; calls `get_settlements_for_category` RPC; applies guard; falls back to all settlements on error
- Rewrote `react-app/src/components/Report2.jsx`: added `filteredCategories`, `filteredSettlements`, `selectedRow` state; `handleSettlementChange` calls `fetchCategoriesForSettlement` and auto-clears `selectedCategory` when not in filtered list; `handleCategoryChange` calls `fetchSettlementsForCategory` and auto-clears `selectedSettlement` plus resets `filteredCategories` to all categories (Q002-A) when settlement drops out; date-change `useEffect` resets both filtered lists; table rows have `onClick` that sets `selectedRow`; `RecordDetailModal` rendered when `selectedRow` is non-null
- Created `react-app/src/components/RecordDetailModal.jsx`: receives `row`, `dims`, `onClose`; resolves category name from `dims.categories`, settlement name via store → `dims.settlements`; displays all enriched fields including `fileName` and `zipDate`; close button and Escape key call `onClose`; `role="dialog"` and `aria-modal="true"`
- Updated `react-app/src/components/Report2.test.jsx`: added `fetchCategoriesForSettlement` and `fetchSettlementsForCategory` to mock; added T1, T2, T4, T5, T9 tests
- Created `react-app/src/components/RecordDetailModal.test.jsx`: T5 (smoke render), T6 (file name), T7 (close button), T8 (Escape key), T16 (null row), backdrop click
- Added T10 (`fetchDimensions` files Map), T11 (`fetchReport2` file enrichment), T1/T1b (`fetchCategoriesForSettlement`), T2/T2b (`fetchSettlementsForCategory`) tests to `react-app/src/lib/dataService.test.js`
- Updated `.aib_memory/context.md`: corrected `load_supabase.py` index description (was `fact_prices`, now `fact_prices_lookback`); added new index and four RPC functions; updated `dataService.js` description; updated `Report2.jsx` description; added `RecordDetailModal.jsx` entry; updated Supabase REST API integration point; updated architectural decision #9; added cross-filter algorithm block

#### Tests
- Unit, react-component: `npm run test` — 58 tests across 7 test files — all passed
- Build: `npm run build` — exits 0, no new warnings, bundle size 362.54 kB

#### Outcome
All implementation tasks completed successfully. All 58 automated tests pass. Build exits 0 with no new warnings. Success criteria SC1–SC7 are satisfied by the implementation. The pre-existing `context.md` error describing indexes on `fact_prices` (the deleted table) has been corrected to reflect `fact_prices_lookback`.

#### Evidence
- Test run output:
```
Test Files  7 passed (7)
      Tests  58 passed (58)
   Start at  23:47:16
   Duration  6.74s
```
- Build output:
```
dist/assets/index-Kuy2WBbD.js   362.54 kB │ gzip: 103.76 kB
✓ built in 2.19s
```
