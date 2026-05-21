Implementation record for request R-20260518-2134: Remove column Ефективна цена from all pages.

## Files taken into consideration
- `.aib_memory/plan-R-20260518-2134.md` (authoritative scope and procedure)
- `.aib_memory/context.md` (workspace product context)
- `.aib_memory/instructions.md` (empty — no persistent workspace instructions)

## Implementation Log

### Entry 2026-05-18 21:45
#### Scope
Remove all UI occurrences of the "Ефективна цена" label from the React analytics app. The column is deleted from the `buildColumns()` function in `FileRowsPanel.jsx` (Files page table), the dt/dd display pair is removed from `FileRowDetailModal.jsx` (Files page row-detail modal), and the dt/dd display pair is removed from `RecordDetailModal.jsx` (Report 2 record-detail modal). Two test assertions that checked for the presence of the removed elements are deleted. The underlying `calculatedPrice` data field and `calculatePrice()` function in `dataService.js` are retained unchanged because they continue to power the Report 2 and Report 3 "Цена" columns.

#### Changes
- Deleted line `{ key: 'calculatedPrice', label: 'Ефективна цена', type: 'numeric' }` from `buildColumns()` in `react-app/src/components/FileRowsPanel.jsx`; function now returns 11 column definitions instead of 12.
- Removed `<dt>Ефективна цена:</dt>` and `<dd>{formatPrice(row.calculatedPrice)}</dd>` from `react-app/src/components/FileRowDetailModal.jsx`; dl structure remains valid.
- Removed `<dt style={{ fontWeight: 600, color: '#555' }}>Ефективна цена:</dt>` and its sibling `<dd>` from `react-app/src/components/RecordDetailModal.jsx`; dl structure remains valid.
- Removed assertion `expect(screen.getByText('Ефективна цена')).toBeInTheDocument()` from `react-app/src/components/FileRowsPanel.test.jsx`.
- Removed assertion `expect(screen.getByText('Ефективна цена:')).toBeInTheDocument()` from `react-app/src/components/FileRowDetailModal.test.jsx`.
- Added "Updated by R-20260518-2134" entry to `.aib_memory/context.md` preamble.
- Updated column/field counts in `.aib_memory/context.md`: "12-column" → "11-column", "12 display fields" → "11 display fields", "fits 12 columns" → "fits 11 columns" across Requirements, Technical Design, and Workspace File Inventory sections.
- Removed "effective price" from RecordDetailModal field list in `.aib_memory/context.md` Technical Design section.

#### Tests
- unit: Vitest full suite (`react-app/`) — 10 test files, 115 tests — all pass (exit code 0)

#### Outcome
Successful. The string "Ефективна цена" no longer appears in any source file under `react-app/src/`. The `FileRowsPanel` table renders 11 column headers. All 115 Vitest tests pass with no failures. `calculatePrice()` and `calculatedPrice` data fields are intact in `dataService.js` and continue to serve Report 2 and Report 3.

#### Evidence
- Vitest result: 10 test files, 115 tests, 0 failures, exit code 0.
- Workspace grep for "Ефективна цена" in `react-app/src/**` returned 0 matches after changes.
