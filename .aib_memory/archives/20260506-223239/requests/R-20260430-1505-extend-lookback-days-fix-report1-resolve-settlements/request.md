## Goal

Extend the React app date selector to show the last 3 locally-processed fact dates (D, D-1, D-2) by reconstructing virtual D-1 and D-2 price views client-side from the horizontal lookback price columns already present in `fact_prices_lookback` — no ETL or database schema changes. Fix the Report 1 error ("Could not find the table 'public.fact_prices'") that appears on the "Цени по категория" page of the deployed Netlify app by rebuilding and redeploying the React bundle.

## Background

After R-20260430-0825 deleted `fact_prices` and made `fact_prices_lookback` the sole fact table, `fact_prices_lookback` was designed to hold only the latest date D's rows — with D-1 and D-2 prices stored as horizontal columns (`retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`) within each D row. Consequently, the `get_available_dates()` RPC function returns only one date_key (D), and the React app date selector shows only 1 date. The prior 3-day browsable window is inaccessible to users.

The original plan was to extend `build_lookback_table()` to emit rows for all 3 dates (D, D-1, D-2), which would triple the Supabase fact table volume. A scope amendment was applied via `input.md`: ETL and database must remain unchanged. Instead, the React app is updated to reconstruct D-1 and D-2 views client-side by reading the existing horizontal lookback columns and normalizing them before price calculation. `dim_date` already contains all 3 date rows (D, D-1, D-2) after `prune_dim_date()` runs; these are used to populate the date selector once `fetchDimensions()` is updated to stop filtering to only the RPC-returned date.

A runtime error on the "Цени по категория" page ("fetchReport1: Could not find the table 'public.fact_prices' in the schema cache") indicates the Netlify-deployed React app bundle still references `fact_prices`, which was deleted. The local source code is already correct (uses `fact_prices_lookback`), but a rebuild and redeploy are needed.

## Scope

- `react-app/src/lib/dataService.js` — `fetchDimensions()`: remove RPC-based `dim_date` filtering; expose all 3 `dim_date` rows in `dates`; add `currentDateKey` (D's date_key, derived from RPC result) and `lookbackColumnMap` (`Map<date_key, 'current'|'day1'|'day2'>`) to the returned dims object.

- `react-app/src/lib/dataService.js` — `fetchSettlementsForDate()`: when the selected date is a lookback offset (`'day1'` or `'day2'`), call the `get_settlements_for_date` RPC with `dims.currentDateKey` (D's key) instead of the selected lookback date_key, since all fact rows are stored under D's key.

- `react-app/src/lib/dataService.js` — `fetchReport1()`, `fetchReport2()`, `fetchReport3()`: resolve price offset from `dims.lookbackColumnMap`; for lookback dates, query `fact_prices_lookback` using `dims.currentDateKey` and select the appropriate lookback price columns; normalize rows via a new `normalizeRow(row, offset)` helper before price calculation or return.

- `react-app/src/lib/dataService.js` — new private `normalizeRow(row, offset)` helper: remaps `retail_price_day1 → retail_price` and `promo_price_day1 → promo_price` (or `day2` variant) for lookback rows; returns row unchanged for `'current'` offset.

- `react-app/src/App.test.jsx`: update `makeStubDims()` to include `currentDateKey` and `lookbackColumnMap`; add a test asserting 3 date options appear in the selector.

- React app rebuild (`npm run build`) and Netlify redeploy (menu option 5) to fix the stale bundle referencing `fact_prices`.

## Out of scope

- Any changes to `src/transform.py`, `src/load_supabase.py`, `data/schema/fact_prices_lookback.csv`, or `data/schema/dim_settlement.csv` — ETL pipeline and database are frozen for this request.

- Changes to `data/nomenclatures/` files or EKATTE code resolution logic — settlement enrichment is deferred to a future request.

- Historical backfill of more than 3 dates in `fact_prices_lookback` in Supabase.

- Resolving unknown settlement entries (`dim_settlement.csv` retains its 25 unknown entries).

- Changes to any Supabase table schema or RPC functions.

- Changes to Report UI component files (`Report1.jsx`, `Report2.jsx`, `Report3.jsx`) — the normalization in `dataService.js` makes existing component code work correctly without modification.

- Changes to `App.jsx` beyond the existing behavior (date selector initialization and pass-through remain unchanged).

## Constraints

- No changes to `src/transform.py`, `src/load_supabase.py`, or any Supabase table schema or RPC functions.

- `fact_prices_lookback` remains a single-date table (D rows only); its size and schema are frozen.

- The `get_available_dates()` and `get_settlements_for_date()` RPC functions remain unchanged.

- `calculatePrice()` function signature and implementation remain unchanged.

- No new npm dependencies in `react-app/`.

- React app must remain client-only (no serverless functions).

- Python 3.9+ stdlib-only constraint for `src/transform.py` and `src/config_utils.py` (unaffected by this request).

## Success criteria

- SC1: The React app date selector displays 3 distinct dates (D, D-1, D-2) after Netlify redeploy.

- SC2: Report 1 ("Цени по категория") on the Netlify-deployed app loads without error and displays data correctly for each selectable date.

- SC3: When D-1 is selected, all three reports use `retail_price_day1`/`promo_price_day1` as the effective price columns; when D-2 is selected, `retail_price_day2`/`promo_price_day2` are used. The "Дата" column in Reports 2 and 3 shows the correct D-1 or D-2 label.

- SC4: Settlement dropdown in Reports 1 and 2 is correctly populated for all 3 selectable dates (not empty for D-1 and D-2).

- SC5: All existing automated tests pass without modification (test suite exits 0); new tests for `fetchDimensions` 3-date output, `lookbackColumnMap` construction, and `normalizeRow()` behavior pass.

- SC6: Re-running `load_supabase.py` (idempotency check) produces the same Supabase row count with no errors (fact_prices_lookback unchanged; ETL not touched).

## Assumptions

- A1: `dim_date` always contains exactly 3 rows (D, D-1, D-2) after `load_supabase.py` runs `prune_dim_date`. Using all `dim_date` rows (without RPC filtering) is safe as a "3 available dates" source.
  - Risk if false: If `dim_date` has more rows (e.g., operator bypasses prune), the date selector may show extra dates, and the `lookbackColumnMap` offset derivation (based on sorted position) may be wrong.

- A2: `get_available_dates()` RPC reliably returns exactly 1 date_key (D), allowing the app to identify the "current" date and build the `lookbackColumnMap`. If RPC returns 0 results, `currentDateKey = null` and the app falls back to showing all `dim_date` rows without offset mapping (safe degradation).
  - Risk if false: If RPC returns more than 1 date_key (shouldn't happen with single-date lookback table), the offset map would need to identify D as the max date_key.

- A3: `retail_price_day1`/`promo_price_day1` and `retail_price_day2`/`promo_price_day2` are correctly populated in `fact_prices_lookback` for products that had prices on D-1 and D-2. NULL values for products new on D are acceptable; `calculatePrice()` handles NULL `promo_price` gracefully, and NULL `retail_price` becomes 0.00 лв (consistent with no-rejection policy). See Q001 for user decision on zero-price row filtering.
  - Risk if false: If many lookback columns are NULL (e.g., only 1 local fact date exists), D-1/D-2 views show mostly zeros.

- A4: The stale Netlify bundle (referencing `fact_prices`) is the sole cause of the Report 1 error. No Supabase PostgREST schema cache issue requires separate remediation.
  - Risk if false: Even after rebuilding, a PostgREST schema cache refresh may be needed; Supabase refreshes automatically within minutes of DDL changes.

- A5: `App.jsx` correctly initializes `selectedDate` from `dims.dates[0].date_key` (the most recent date, D). Since `dims.dates` will include 3 rows sorted descending, index 0 remains D and first-load behavior is unchanged.
  - Risk if false: None — sort order is guaranteed by the existing `.order('date', { ascending: false })` in `fetchDimensions()`.

- A6: Report component files (`Report1.jsx`, `Report2.jsx`, `Report3.jsx`) do not need modification. The `normalizeRow()` normalization in `dataService.js` remaps lookback columns to `retail_price`/`promo_price` before returning to components; the `calculatePrice()` call in `fetchReport*` functions uses the normalized values; the "Дата" column in Report2/Report3 uses `dimensions.dates.find(d => d.date_key === selectedDate)?.date` which correctly resolves D-1/D-2 dates once they are in `dims.dates`.
  - Risk if false: If any component directly reads `row.retail_price` outside of `calculatePrice()`, it would show the normalized value (which is the lookback price after normalization) — this is the intended behavior.

## Plan

### Task 1: Extend `fetchDimensions()` in `dataService.js`
**Intent:** Include all 3 `dim_date` rows in `dims.dates` and expose `currentDateKey` and `lookbackColumnMap` in the returned dims object.
**Inputs:** `react-app/src/lib/dataService.js`, Supabase `dim_date` table, `get_available_dates()` RPC.
**Outputs:** Updated `fetchDimensions()` with new `currentDateKey` and `lookbackColumnMap` properties on `_dims`.
**External Interfaces:** Supabase PostgREST (`dim_date` SELECT, `get_available_dates` RPC).
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in `.env`.
**Procedure:**
1. Remove the `filteredDates = datesRes.data.filter(r => factDateKeySet.has(r.date_key))` line; set `filteredDates = datesRes.data` unconditionally (all dim_date rows).
2. After building `factDateKeySet`, compute `currentDateKey`: extract the single value from `factDateKeySet` using `factDateKeySet.values().next().value`, or `null` if RPC errored or returned 0 results.
3. Build `lookbackColumnMap` as a new `Map`: if `currentDateKey` is known and `filteredDates` has ≥ 1 row, map `filteredDates[0].date_key → 'current'`, `filteredDates[1]?.date_key → 'day1'` (if present), `filteredDates[2]?.date_key → 'day2'` (if present).
4. Add `currentDateKey` and `lookbackColumnMap` to the `_dims` object before the module-level cache assignment.
**Done Criteria:** `fetchDimensions()` returns `dims.dates` with 3 entries (when dim_date has 3 rows); `dims.lookbackColumnMap.get(D_date_key) === 'current'`; `dims.lookbackColumnMap.get(D1_date_key) === 'day1'`.
**Dependencies:** None.
**Risk Notes:** If RPC is unavailable, `currentDateKey = null` and `lookbackColumnMap` is populated using only the sorted `dim_date` position (index 0 = D, index 1 = D-1, index 2 = D-2). Since `dim_date` is always sorted descending, positional derivation is safe as a fallback.

### Task 2: Update `fetchSettlementsForDate()` and report fetch functions in `dataService.js`
**Intent:** Route settlement and report queries to D's date_key when a lookback date is selected, and select the correct price columns.
**Inputs:** `react-app/src/lib/dataService.js` (Task 1 updated).
**Outputs:** Updated `fetchSettlementsForDate`, `fetchReport1`, `fetchReport2`, `fetchReport3`; new `normalizeRow` private helper.
**External Interfaces:** Supabase PostgREST.
**Environment & Configuration:** None.
**Procedure:**
1. Add private `normalizeRow(row, offset)` helper: if `offset === 'current'` or falsy, return `row` unchanged; otherwise return `{...row, retail_price: row[\`retail_price_\${offset}\`], promo_price: row[\`promo_price_\${offset}\`]}`.
2. In `fetchSettlementsForDate(dateKey, dims)`: compute `const offset = dims.lookbackColumnMap?.get(dateKey) ?? 'current'`; if `offset !== 'current'`, use `dims.currentDateKey` as the RPC argument instead of `dateKey`.
3. In `fetchReport1(dateKey, settlementKey, dims)`: compute `offset` and `queryDateKey` (use `dims.currentDateKey` when `offset !== 'current'`); set `priceColumns` based on offset (`'retail_price_day1,promo_price_day1'` for `'day1'`, `'retail_price_day2,promo_price_day2'` for `'day2'`, `'retail_price,promo_price'` for `'current'`); after fetching all pages, apply `allRows = allRows.map(r => normalizeRow(r, offset))` before aggregation.
4. Apply the same offset/queryDateKey/priceColumns/normalizeRow pattern to `fetchReport2` and `fetchReport3`.
**Done Criteria:** Calling any report function with D-1's date_key results in a Supabase query using D's key and selecting `retail_price_day1,promo_price_day1`; normalized rows have `retail_price === retail_price_day1` value.
**Dependencies:** Task 1.
**Risk Notes:** `retail_price_day1` may be NULL for products new on D; `calculatePrice()` returns 0 in that case — acceptable per A3. See Q001 for potential row-filtering decision.

### Task 3: Update automated tests
**Intent:** Update `App.test.jsx` stubs and add dataService unit tests for lookback column mapping behavior.
**Inputs:** `react-app/src/App.test.jsx`, `react-app/src/lib/dataService.js` (Tasks 1, 2 updated).
**Outputs:** Updated `react-app/src/App.test.jsx`; new or extended test file for `dataService.js`.
**External Interfaces:** Vitest test runner (`npm test` inside `react-app/`).
**Environment & Configuration:** Node.js + npm; Vitest + Testing Library.
**Procedure:**
1. In `App.test.jsx`, update `makeStubDims()` to add `currentDateKey: 20260426` and `lookbackColumnMap: new Map([[20260426, 'current']])`.
2. Add a test to `App.test.jsx` that passes a stub with 3 dates and asserts 3 `<option>` elements appear in the date selector.
3. Add a `dataService.test.js` (or extend existing dataService test file) with: (a) test for `normalizeRow` day1 remapping; (b) test for `normalizeRow` identity for 'current'; (c) test for `lookbackColumnMap` shape with 3 dim_date rows and 1-element RPC result.
4. Run `npm test` in `react-app/`; confirm all tests pass.
**Done Criteria:** `npm test` exits 0; all pre-existing tests pass; new tests added in steps 2 and 3 pass.
**Dependencies:** Tasks 1, 2.
**Risk Notes:** Supabase mock must be extended to handle `get_available_dates` returning a 1-element array for `lookbackColumnMap` tests.

### Task 4: Rebuild and redeploy React app
**Intent:** Fix the stale Netlify bundle that still references `fact_prices`.
**Inputs:** `react-app/src/` (updated from Tasks 1–2), `.env` with `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`.
**Outputs:** `react-app/dist/` rebuilt; Netlify deployment updated.
**External Interfaces:** Netlify (via `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID`).
**Environment & Configuration:** Node.js + npm; Netlify CLI.
**Procedure:**
1. Menu option 5 (`src/deploy_netlify.py`) — builds and deploys to Netlify.
2. After deploy, open Netlify URL in incognito browser window.
3. Verify date selector shows 3 dates (UAT-02).
4. Verify Report 1 loads without error (UAT-01).
5. Test D-1 and D-2 selections show different data (UAT-03).
**Done Criteria:** UAT-01, UAT-02, UAT-03 pass (see UAT_scenarios.md).
**Dependencies:** Tasks 1–3.
**Risk Notes:** Netlify free-tier build minutes; deploy typically completes in < 2 minutes.

### Task 5: Update documentation and context
**Intent:** Update `context.md` to reflect the new frontend lookback column reconstruction approach.
**Inputs:** `.aib_memory/context.md`, `.aib_memory/references.md`.
**Outputs:** Updated `context.md`.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In `context.md` → `## Technical Design → Module Breakdown → react-app/src/lib/dataService.js`: update `fetchDimensions()` description to include `currentDateKey` and `lookbackColumnMap`; update `fetchReport*` descriptions to mention lookback column routing and `normalizeRow()`.
2. In `context.md` → `## Data Architecture → Lookback fact (derived)`: note that D-1/D-2 price views are reconstructed client-side from horizontal columns; fact table remains single-date.
3. In `context.md` → Key Architectural Decisions: add decision note about frontend lookback reconstruction (citing R-20260430-1505).
4. Update the `Updated by` note at the top of `context.md`.
**Done Criteria:** `context.md` accurately reflects post-R-20260430-1505 state; all changed components described correctly.
**Dependencies:** Tasks 1–4.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update `react-app/src/lib/dataService.js` module breakdown to describe `fetchDimensions()` `currentDateKey`/`lookbackColumnMap` additions, `normalizeRow()` helper, and updated `fetchReport*` lookback routing; update Lookback fact (derived) architecture description to note client-side D-1/D-2 reconstruction; add Key Architectural Decision for frontend lookback reconstruction; update timestamp.

## Questions & Decisions

**Q001**: When a product appears in D's `fact_prices_lookback` but has a NULL lookback price (`retail_price_day1` is NULL — product was added on D with no prior-day data), how should Reports 1, 2, and 3 handle that row when D-1 or D-2 is selected?
- [ ] Option A: Include the row with 0.00 лв as the effective price (consistent with the no-rejection ETL policy; `calculatePrice()` already returns 0 for NULL retail_price)
- [x] Option B: Filter out rows where the relevant lookback column is NULL before returning from the report function (cleaner UX; avoids misleading zero prices) *(recommended)*
- [ ] Other: ___
> Answer:

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/lib/dataService.js` — `fetchDimensions()` | Modified | Remove RPC-based dim_date filtering; expose all 3 dim_date rows in `dates`; add `currentDateKey` and `lookbackColumnMap` to dims. |
| `react-app/src/lib/dataService.js` — `fetchSettlementsForDate()` | Modified | Use `dims.currentDateKey` for RPC call when selected date is a lookback offset (D-1 or D-2). |
| `react-app/src/lib/dataService.js` — `fetchReport1()` | Modified | Select appropriate lookback price columns; normalize rows via `normalizeRow()` before aggregation. |
| `react-app/src/lib/dataService.js` — `fetchReport2()` | Modified | Select appropriate lookback price columns; normalize rows via `normalizeRow()` before return. |
| `react-app/src/lib/dataService.js` — `fetchReport3()` | Modified | Select appropriate lookback price columns; normalize rows via `normalizeRow()` before return. |
| `react-app/src/lib/dataService.js` — `normalizeRow()` | Created | Private helper: remap `retail_price_day1/2` → `retail_price` and `promo_price_day1/2` → `promo_price`. |
| `react-app/src/App.test.jsx` | Modified | Update `makeStubDims()` to include `currentDateKey` and `lookbackColumnMap`; add 3-date selector test. |
| `react-app/dist/` | Modified | Rebuilt artifact; fixes stale `fact_prices` reference in deployed Netlify bundle. |
| `.aib_memory/context.md` | Modified | Update dataService module breakdown and lookback fact architecture per Task 5. |
| `src/transform.py` | Read-only dependency | No changes; ETL frozen per scope amendment. |
| `src/load_supabase.py` | Read-only dependency | No changes; DB frozen per scope amendment. |

## Internal Review of Request and Product Docs

- Amendment applied: `input.md` `## Input` — User explicitly stated "ETL and the database shall not be restructured (no schema change). Preserve the size of the fact table. Only the frontend should be modified." Scope change applied to Goal, Background, Scope, Out of scope, Constraints, Success criteria, Assumptions, Plan, Code Scan. Old Q001/Q002 (about `build_lookback_table` and dim_settlement enrichment) removed as both topics are now out of scope.
- OK: `request.md` Goal — Updated to reflect frontend-only reconstruction approach. Clear and testable.
- OK: `request.md` Scope — All change sites correctly identified. Confined to `react-app/src/lib/dataService.js` and `App.test.jsx`.
- OK: `request.md` Out of scope — Explicitly excludes ETL, database, and settlement enrichment.
- OK: `request.md` SC1–SC6 — All reframed to test frontend behavior (column routing, settlement filter, date selector) rather than ETL artifacts.
- OK: `context.md` (REF-0001) — Accurately reflects current state as of R-20260430-0825. `fact_prices_lookback` has horizontal lookback columns, confirmed suitable for client-side reconstruction.
- OK: `dataService.js` `fetchDimensions()` — `filteredDates` RPC-filter is the correct change point; confirmed from code inspection.
- OK: `Report2.jsx` "Дата" column — Uses `dimensions.dates.find(d => d.date_key === selectedDate)?.date`; correctly shows D-1/D-2 labels after dims.dates fix. No component change needed.
- Missing info: `App.test.jsx` `makeStubDims()` — Does not include `currentDateKey` or `lookbackColumnMap`. Must be updated in Task 3 to avoid test failures when component code accesses `dims.lookbackColumnMap`.
