Implementation record for R-20260518-1251: Remove currency notation from price displays.

Files taken into consideration:
- `.aib_memory/request.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-javascript-convention.md`
- `.aib_brain/conventions/coding-react-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/context-convention.md`

## Implementation Log

### Entry 2026-05-18 21:16
#### Scope
Removed all `лв` and `(лв)` currency notation from every price display string and column header label across the six affected React component files. Updated the `FileRowsPanel.test.jsx` column-label assertions to match the new labels. Verified SC-1 through SC-5 by running the full Vitest suite and the Vite production build. Updated `context.md` with the R-20260518-1251 change record.

#### Changes
- Modified `react-app/src/components/Report1.jsx`: removed ` лв` from the bar-chart value JSX expression (1 occurrence).
- Modified `react-app/src/components/Report2.jsx`: removed ` лв` from three price cell template literals in the result table rows.
- Modified `react-app/src/components/Report3.jsx`: removed ` (лв)` from three column label strings in `COLUMNS`; updated the code comment in `getDisplayValue` to no longer reference the `лв` suffix; removed ` лв` from three `getDisplayValue` return expressions; removed ` лв` from three inline `<td>` price render expressions.
- Modified `react-app/src/components/RecordDetailModal.jsx`: removed ` лв` from three inline price display template literals.
- Modified `react-app/src/components/FileRowDetailModal.jsx`: removed ` лв` from the `formatPrice()` helper return string; the `toLocaleString` call is preserved unchanged.
- Modified `react-app/src/components/FileRowsPanel.jsx`: removed ` (лв)` from all seven column label strings in the column definition array.
- Modified `react-app/src/components/FileRowsPanel.test.jsx`: updated eight `getByText()` assertions to match the new column labels without `(лв)`.
- Modified `.aib_memory/context.md`: appended update entry for R-20260518-1251 describing the currency notation removal.

#### Tests
- unit: `npm test -- --run` (Vitest) across all 10 test files — pass (115/115 tests)
- build: `npm run build` (Vite production build in `react-app/`) — pass (exit code 0, `dist/` produced)
- grep: `grep -r 'лв' react-app/src/components/` — pass (zero matches across all component files including test file)

#### Outcome
Successful. All six component files and the test file are updated; no `лв` or `(лв)` remains in any rendered UI string, column label, or format function. All 115 Vitest tests pass; Vite build exits 0. SC-1 through SC-5 are fully satisfied. No follow-ups required.

#### Evidence
- Test run result:
```
Test Files  10 passed (10)
     Tests  115 passed (115)
  Start at  21:16:25
  Duration  13.51s
```
- Build result:
```
vite v5.4.21 building for production...
✓ 83 modules transformed.
dist/index.html                   0.55 kB │ gzip:   0.41 kB
dist/assets/index-CLIQlBf0.css   10.41 kB │ gzip:   2.80 kB
dist/assets/index-DpL5ZJSB.js   383.55 kB │ gzip: 108.78 kB
✓ built in 2.45s
```
- Grep result: zero matches returned by `grep -r 'лв' react-app/src/components/`
