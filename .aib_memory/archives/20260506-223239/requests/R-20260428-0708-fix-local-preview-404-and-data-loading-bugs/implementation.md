Files read during implementation:
- `.aib_memory/requests/R-20260428-0708-fix-local-preview-404-and-data-loading-bugs/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/Concepts.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `react-app/src/lib/dataService.js`
- `react-app/src/lib/dataService.test.js`
- `react-app/src/App.jsx`
- `react-app/src/App.test.jsx`
- `react-app/index.html`

## Implementation Log

### Entry 2026-04-29 07:06

#### Scope

Fix the root causes of the "no data in local preview" symptom (R-20260428-0708). Three bugs identified and fixed: (1) `dataService.js` `fetchDimensions()` and `fetchSettlementsForDate()` used `r.get_available_dates` / `r.get_settlements_for_date` property access unconditionally, which silently produces `undefined` when PostgREST v11+ returns plain integers instead of wrapped objects — this caused the date filter Set to be empty and the date dropdown to show no dates. (2) `react-app/index.html` had no favicon link, causing a browser-generated `GET /favicon.ico` request that always 404s against `vite preview`. (3) `App.jsx` had no user-facing message when `dimensions.dates` was empty, producing a silent blank date selector with no diagnostic information.

#### Changes

- Modified `react-app/src/lib/dataService.js`: replaced `(availDatesRes.data || []).map(r => r.get_available_dates)` with a backward-compatible guard `(typeof r === 'object' && r !== null) ? r.get_available_dates : r` in `fetchDimensions()`. Applied the same guard to `(rpcData || []).map(r => r.get_settlements_for_date)` in `fetchSettlementsForDate()`. Added exported `_resetDimsCache()` function for test isolation.
- Modified `react-app/index.html`: added `<link rel="icon" href="data:,">` in `<head>` to suppress the automatic `/favicon.ico` 404.
- Modified `react-app/src/App.jsx`: extended the date selector render block to show a disabled `<option>` with text "Няма налични дати" when `dimensions` is loaded but `dimensions.dates` is empty.
- Modified `react-app/src/lib/dataService.test.js`: updated file-level header to reflect new test coverage; added `describe('fetchDimensions')` block with tests T2 (wrapped-object format), T3 (raw-integer format), T4 (RPC error fallback), T5 (cache hit); added `describe('fetchSettlementsForDate')` block with test T6 (raw-integer format produces non-empty result).
- Modified `react-app/src/App.test.jsx`: added test T7 verifying that the date selector shows "Няма налички дати" option when `fetchDimensions` resolves with an empty `dates` array.
- Modified `.aib_memory/context.md`: updated `dataService.js` module description to reflect backward-compatible RPC format handling and `_resetDimsCache` export; updated `App.jsx` description to reflect empty-dates placeholder; updated "React date filter via RPC" and "React settlement filter via RPC" algorithm descriptions; updated React testing strategy with new test counts (32 total).

#### Tests

- Unit, `dataService.test.js` T2 (fetchDimensions, wrapped-object RPC format): PASS
- Unit, `dataService.test.js` T3 (fetchDimensions, raw-integer RPC format): PASS
- Unit, `dataService.test.js` T4 (fetchDimensions, RPC error fallback): PASS
- Unit, `dataService.test.js` T5 (fetchDimensions, cache hit): PASS
- Unit, `dataService.test.js` T6 (fetchSettlementsForDate, raw-integer format): PASS
- Unit, `App.test.jsx` T7 (empty-dates placeholder option rendered): PASS
- Full React suite (`npm run test`): 32 tests passed, 0 failed
- Full Python suite (`python -m pytest tests/ -q`): 84 passed, 1 skipped
- Build (`npm run build`): exit 0

#### Outcome

All five implementation tasks completed successfully. The root cause of the "no data" symptom was confirmed as the unconditional wrapped-object property access that silently produces `undefined` for plain-integer RPC responses. The backward-compatible fix handles both PostgREST v10 and v11+ formats. The favicon 404 is eliminated by the `data:,` icon hint. The empty-dates state now shows a user-facing message instead of a blank selector. All 32 React tests and 84 Python tests pass. Build exits 0.

#### Evidence

```
> kolko-ni-struva-react@0.0.0 test
> vitest run

 ✓ src/components/Report1.test.jsx (3 tests) 185ms
 ✓ src/components/Report2.test.jsx (3 tests) 206ms
 ✓ src/App.test.jsx (6 tests) 489ms
 ✓ src/components/HomePage.test.jsx (3 tests) 91ms
 ✓ src/lib/dataService.test.js (14 tests) 69ms
 ✓ src/components/Report3.test.jsx (3 tests) 186ms

 Test Files  6 passed (6)
      Tests  32 passed (32)
   Duration  4.85s
```

```
84 passed, 1 skipped in 0.40s
```

```
vite v5.4.21 building for production...
✓ 78 modules transformed.
dist/index.html  0.55 kB │ gzip: 0.40 kB
✓ built in 1.95s
```
