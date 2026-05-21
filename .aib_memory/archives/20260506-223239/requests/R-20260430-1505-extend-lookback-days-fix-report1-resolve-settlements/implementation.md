Files taken into consideration during this implementation:

- `.aib_memory/requests/R-20260430-1505-extend-lookback-days-fix-report1-resolve-settlements/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/Concepts.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`

## Implementation Log

### Entry 2026-04-30 23:44

#### Scope

Extend the React app date selector to show all 3 dim_date rows (D, D-1, D-2) by reconstructing lookback price views client-side from the horizontal lookback columns in `fact_prices_lookback`. Updated `fetchDimensions()` to expose all dim_date rows and build a `lookbackColumnMap`. Added `normalizeRow()` helper to remap day1/day2 price columns before aggregation. Updated `fetchSettlementsForDate`, `fetchReport1`, `fetchReport2`, and `fetchReport3` to route lookback queries to the current date's rows. Fixed the stale Netlify bundle that still referenced `fact_prices` by rebuilding and redeploying.

#### Changes

- Updated `react-app/src/lib/dataService.js` — `fetchDimensions()`: removed RPC-based date filtering; `filteredDates` now equals all `dim_date` rows; added `currentDateKey` (extracted from RPC result, null on error); added `lookbackColumnMap` (positional Map keyed by date_key → 'current'|'day1'|'day2'); added both fields to the `_dims` cache object; updated JSDoc.
- Updated `react-app/src/lib/dataService.js` — added exported `normalizeRow(row, offset)` helper after `calculatePrice`; remaps `retail_price_day1/promo_price_day1` (or day2 variant) to canonical `retail_price/promo_price` fields; identity for 'current' or falsy offset.
- Updated `react-app/src/lib/dataService.js` — `fetchSettlementsForDate()`: resolves `offset` from `lookbackColumnMap`; uses `dims.currentDateKey` as the RPC argument for D-1/D-2 offsets; updated JSDoc.
- Updated `react-app/src/lib/dataService.js` — `fetchReport1()`: added offset/queryDateKey/priceColumns resolution; select string uses template literal with priceColumns; `normalizeRow()` applied to allRows before aggregation; updated JSDoc.
- Updated `react-app/src/lib/dataService.js` — `fetchReport2()`: same offset/queryDateKey/priceColumns/normalizeRow pattern; pre-aggregation normalization added; updated JSDoc.
- Updated `react-app/src/lib/dataService.js` — `fetchReport3()`: same offset/queryDateKey/priceColumns/normalizeRow pattern; pre-enrichment normalization added; updated JSDoc.
- Updated `react-app/src/App.test.jsx`: added `within` to testing-library import; updated `makeStubDims()` to include `currentDateKey: 20260426` and `lookbackColumnMap: new Map([[20260426, 'current']])`; added SC1 test asserting 3 date options appear in the selector with a 3-date dims stub.
- Updated `react-app/src/lib/dataService.test.js`: added `normalizeRow` to import; fixed pre-existing test bug — `fetchReport2 pagination` test mock referenced `'fact_prices'` instead of `'fact_prices_lookback'`; updated T6 dims stub to include `lookbackColumnMap` and `currentDateKey`; added `normalizeRow` describe block (4 tests: identity for 'current', identity for falsy, day1 remap, day2 remap); added `fetchDimensions lookbackColumnMap` describe block (SC1 test: 3 dim_date rows + 1-element RPC → correct map shape).
- Rebuilt React app: `npm run build` inside `react-app/` produced `dist/assets/index-DzMkpij9.js` (357 KB).
- Redeployed to Netlify production: `python src/deploy_netlify.py` — deploy ID `69f3bf5028d6d7f15dd7bcee`, live at https://kolko-ni-struva.netlify.app.

#### Tests

- Unit — `npm test -- --run` in `react-app/`: 38 tests across 6 files — all passed (exit 0).
- Unit — `normalizeRow` suite (4 tests): identity for 'current', identity for null/undefined, day1 remap, day2 remap — all passed.
- Unit — `fetchDimensions lookbackColumnMap` SC1 test: 3 dim_date rows + 1-element RPC → dims.dates length 3, currentDateKey = 20260426, map has correct 'current'/'day1'/'day2' values — passed.
- Unit — SC1 App.test.jsx 3-date selector test: renders 3 option elements — passed.
- Unit — pre-existing `fetchReport2 pagination` test: fixed table-name bug (`fact_prices` → `fact_prices_lookback`); test now passes (1050 rows returned correctly).
- Integration — React build: `vite build` completed successfully; 78 modules transformed, no errors.
- Deployment — Netlify production deploy: completed successfully; production URL confirmed live.

#### Outcome

Success. All 38 automated tests pass. The React app bundle is rebuilt and redeployed to Netlify, replacing the stale bundle that referenced the deleted `fact_prices` table. The date selector now exposes all 3 dim_date rows (D, D-1, D-2). Report 1, 2, and 3 correctly resolve lookback price columns for D-1 and D-2 dates via `normalizeRow()`. Settlement dropdown is correctly populated for all 3 dates by routing the RPC to D's key. No ETL, database schema, or Supabase RPC changes were made. SC6 (idempotency of load_supabase.py) is not in scope for this implementation run (ETL is frozen); confirmed no ETL files were modified.

#### Evidence

```
 Test Files  6 passed (6)
      Tests  38 passed (38)
   Start at  23:44:10
   Duration  4.48s
```

```
vite v5.4.21 building for production...
✓ 78 modules transformed.
dist/assets/index-DzMkpij9.js   357.21 kB │ gzip: 102.39 kB
✓ built in 2.32s
```

```
✔ Deploy is live!
Deployed to production URL: https://kolko-ni-struva.netlify.app
Deploy ID: 69f3bf5028d6d7f15dd7bcee
```

#### Notes (Optional)

Pre-existing bug fixed: `fetchReport2 pagination` test in `dataService.test.js` referenced `'fact_prices'` (deleted table) instead of `'fact_prices_lookback'`. This bug was silent before this request because the test was silently failing with a mock fallback that returned `{}` (no `.select` method), causing a TypeError. Fixed as part of SC5 compliance.
