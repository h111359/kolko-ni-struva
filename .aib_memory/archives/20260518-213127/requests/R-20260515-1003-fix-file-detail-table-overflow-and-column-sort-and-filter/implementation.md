Files read during this implementation run:
- .aib_memory/instructions.md (empty)
- .aib_memory/requests_register.md
- .aib_memory/request.md
- .aib_memory/context.md
- .aib_brain/conventions/implementation-convention.md
- .aib_brain/conventions/coding-general-convention.md
- .aib_brain/conventions/coding-javascript-convention.md
- .aib_brain/conventions/coding-react-convention.md
- .aib_brain/conventions/coding-css-convention.md
- react-app/src/components/FileRowsPanel.jsx
- react-app/src/components/FileRowsPanel.test.jsx
- react-app/src/components/FileDetailPage.jsx
- react-app/src/App.css (selected sections)

## Implementation Log

### Entry 2026-05-15 10:30

#### Scope
Fixed the missing `.table-scroll-wrapper` CSS rule in `App.css` so the 12-column `FileRowsPanel` detail table scrolls horizontally within the panel card instead of overflowing it. Added client-side sort (click column header to cycle asc → desc → unsorted) and per-column substring filter (filter input row in thead, case-insensitive) to `FileRowsPanel.jsx`. Added supporting CSS rules for sortable headers and filter inputs. Updated `FileRowsPanel.test.jsx` with five new tests covering sort and filter behaviour. Updated `context.md` to reflect the changes.

#### Changes
- Added `.table-scroll-wrapper { overflow-x: auto; width: 100%; }` rule to `react-app/src/App.css` in the Results Table section, fixing the horizontal overflow of the `FileRowsPanel` detail table and the `FileDetailPage` summary table as a side-effect.
- Added sort/filter CSS rules to `react-app/src/App.css`: `.results-table th.sortable-th` (cursor/user-select), `.results-table th.sortable-th:hover` (lighter gradient), `.sort-indicator` (margin/opacity), `.filter-row th` (white background override), `.filter-row th input` (full-width styling), and `.filter-row th input:focus` (brand-colour focus ring).
- Rewrote `react-app/src/components/FileRowsPanel.jsx`: replaced hardcoded 12-column header/body markup with a `COLUMNS` definition array; added `useMemo` import; added `sortConfig` and `filterValues` state; added `handleSort`, `handleFilterChange`, `getDisplayValue`, `getAriaSortValue`, and `getSortIndicator` helpers; added `sortedRows` and `filteredRows` derived via `useMemo`; added a reset `useEffect` on `fileKey` change; added a filter input row in `thead`; changed column header `<th>` elements to include `className="sortable-th"`, `aria-sort`, `tabIndex`, `onKeyDown`, a `col-label` span, and a `sort-indicator` span; rendered `filteredRows` in `tbody` via COLUMNS map.
- Added five new unit tests (T9–T13) to `react-app/src/components/FileRowsPanel.test.jsx` covering: sort ascending, sort descending, sort cleared on third click, filter case-insensitive match hides non-matching rows, filter cleared restores all rows.
- Updated `react-app/src/App.css` file-level header comment to reference R-20260515-1003 sort/filter additions.
- Updated `.aib_memory/context.md` to record R-20260515-1003 changes.

#### Tests
- Unit (Vitest + React Testing Library): `react-app/src/components/FileRowsPanel.test.jsx` — 13/13 pass (8 pre-existing T1–T8 + 5 new T9–T13).
- Unit (Vitest): full suite across all 9 test files — 85/85 pass; no regressions.
- Build: `npm run build` from `react-app/` — exit 0, `dist/` produced, no errors or warnings.

#### Outcome
Success. All four success criteria met: SC-1 (overflow fixed), SC-2 (sort with visual indicator and aria-sort), SC-3 (case-insensitive substring filter with per-column inputs), SC-4 (keyboard accessible via tabIndex and onKeyDown on sort headers, standard input behaviour for filters), SC-5 (all 13 tests pass), SC-6 (build exits 0). No unresolved blockers or regressions.

#### Evidence
- Test run result: 85 tests across 9 files — all pass.
  ```
  src/components/FileRowsPanel.test.jsx  13/13 pass
  (all other 8 test files)               72/72 pass
  ```
- Build result: `npm run build` exit code 0, `dist/` present.

#### Notes (Optional)
A3 applies: numeric price columns are filtered by the bg-BG locale-formatted display string (e.g., type "2,50" not "2.50" to match a price of 2.50). The col-label span wrapper inside each sortable `<th>` preserves backward-compatible `getByText('column-name')` behaviour in existing tests when the sort-indicator span adds extra text content to the th element.
