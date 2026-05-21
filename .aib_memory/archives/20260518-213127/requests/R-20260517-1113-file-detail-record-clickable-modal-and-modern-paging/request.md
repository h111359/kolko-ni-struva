## Goal

Add a row-click interaction to the FileRowsPanel detail table in the Файлове (Files) page: clicking any data row opens a modal dialog showing all fields of that record together with the surrogate keys and IDs from the fact and dimension tables. Additionally, replace the current two-button Previous/Next paging strip with a modern, slicker pagination control that includes first-page and last-page jump buttons.

## Background

The Файлове page (FileRowsPanel component) currently shows a compact 12-column table of price-fact records for the selected source file. Each row contains enriched display fields (product name, category, settlement, store, company, prices) but the raw surrogate keys (product_key, category_key, store_key, file_key, settlement_key, company_key) are not visible. Users and data engineers need to inspect these internal IDs for debugging, data lineage tracing, and cross-referencing fact rows against the star schema.

The existing pagination strip has only a Previous and Next button, which makes navigating large record sets (hundreds of pages) cumbersome. A slicker control with first/last jump and page number input or numbered buttons would significantly improve usability.

## Scope

- Add `onClick` handler to each `<tr>` in FileRowsPanel's `<tbody>` that sets a `selectedRow` state and opens a detail modal.

- Create a new `FileRowDetailModal` component (new file: `react-app/src/components/FileRowDetailModal.jsx`) that renders all 12 display columns plus surrogate keys/IDs from the fact and dimension tables: `product_key`, `category_key`, `store_key`, `file_key`, `settlement_key` (resolved from dims.stores), `company_key` (resolved from dims.stores).

- The modal must support Escape-key and backdrop-click dismissal, following the same pattern as the existing `RecordDetailModal`.

- Replace the two-button Previous/Next pagination strip in FileRowsPanel with a modern pagination bar that includes: First page button, Previous page button, page indicator with current/total, Next page button, Last page button — all with correct disabled states.

- Add CSS for the new modal and the updated pagination controls in `react-app/src/App.css`.

- Add/update unit tests in `react-app/src/components/FileRowsPanel.test.jsx` and create `react-app/src/components/FileRowDetailModal.test.jsx`.

## Out of scope

- Changes to the RecordDetailModal used by Report 2 (that modal is separate and already complete).
- Changes to the data fetched by fetchFileRows — no new Supabase queries are needed.
- Pagination for the FileDetailPage summary table (only FileRowsPanel paging is in scope).
- Modifying any ETL pipeline Python scripts.

## Constraints

- No new npm packages may be installed.
- No credentials or environment variables may be hardcoded.
- The React app must still pass `npm run build` (Vite) without errors.
- All existing tests must remain passing after the change.
- The modal must be accessible: role="dialog", aria-modal="true", Escape dismissal, focus trap is desirable but not mandatory.
- The file_key for the open file is already held in the `fileKey` prop of FileRowsPanel — it must be passed through to the modal.
- settlement_key and company_key are available from `dims.stores` by looking up the row's `store_key`.

## Success criteria

- SC-1: Clicking any data row in FileRowsPanel opens a modal showing all 12 display fields and the surrogate keys (product_key, category_key, store_key, file_key, settlement_key, company_key).
- SC-2: The modal closes on Escape key press and on backdrop click.
- SC-3: The pagination bar in FileRowsPanel shows First / Previous / Page X of Y / Next / Last buttons with correct disabled states (First and Previous disabled on page 1; Next and Last disabled on the last page).
- SC-4: First and Last buttons jump directly to page 1 and the last page respectively.
- SC-5: All existing FileRowsPanel tests (T1–T15) continue to pass without modification (backward compatibility).
- SC-6: The `npm run build` command completes successfully with no errors.

## Assumptions

- A1: The surrogate keys (product_key, category_key, store_key) are already present in each enriched row object returned by fetchFileRows, so no additional fetch is needed.
  - Risk if false: would need to add file_key to the enriched row or pass it explicitly; currently fileKey is a prop so it can be passed directly.
- A2: settlement_key and company_key can be resolved from dims.stores by matching on store_key in the modal component, consistent with how RecordDetailModal resolves settlement.
  - Risk if false: keys would be unavailable and the modal would show '—' for those fields.
- A3: PAGE_SIZE=100 constant remains unchanged; the modern paging bar does not change pagination logic, only its UI representation.
  - Risk if false: test assertions tied to specific page counts would fail.

## Plan

### Task 1: Create FileRowDetailModal component
**Intent:** Build the new modal dialog that displays all display fields plus all surrogate keys for a clicked FileRowsPanel row.
**Inputs:** `react-app/src/components/RecordDetailModal.jsx` (reference pattern), row object shape from fetchFileRows, dims cache structure.
**Outputs:** `react-app/src/components/FileRowDetailModal.jsx` (new file).
**External Interfaces:** dims (categories Map, stores Array, settlements Map, companies Map); fileKey prop passed from FileRowsPanel.
**Environment & Configuration:** No env vars; browser React environment.
**Procedure:**
1. Create `FileRowDetailModal.jsx` following the same modal pattern as `RecordDetailModal.jsx`.
2. Accept props: `row` (enriched row), `fileKey` (number), `dims` (dimension cache), `onClose` (function).
3. Resolve settlement_key and company_key from dims.stores using row.store_key.
4. Render a `<dl>` grid showing all 12 display fields, then a divider, then all 6 surrogate keys.
5. Add Escape keydown listener and backdrop onClick dismissal.
6. Add the close (×) button in the top-right corner.
**Done Criteria:** Component renders without errors; modal closes on Escape and backdrop click; all fields and keys are shown.
**Dependencies:** None.
**Risk Notes:** None.

### Task 2: Integrate row-click and modal into FileRowsPanel
**Intent:** Wire the row onClick handler in FileRowsPanel to show FileRowDetailModal for the clicked row.
**Inputs:** `FileRowsPanel.jsx` (existing), `FileRowDetailModal.jsx` (Task 1).
**Outputs:** `react-app/src/components/FileRowsPanel.jsx` (modified).
**External Interfaces:** None beyond existing.
**Environment & Configuration:** None.
**Procedure:**
1. Add `useState(null)` for `selectedRow` state.
2. Add `onClick` and `style={{ cursor: 'pointer' }}` to each `<tr>` in `<tbody>`, setting `selectedRow` to the clicked row.
3. Import and render `<FileRowDetailModal>` conditionally when `selectedRow !== null`, passing `row={selectedRow}`, `fileKey={fileKey}`, `dims={dims}`, `onClose={() => setSelectedRow(null)}`.
4. Reset `selectedRow` to null on file change (add to the existing fileKey-change useEffect).
**Done Criteria:** Clicking a row opens the modal; the modal dismisses and row is deselected on close.
**Dependencies:** Task 1.
**Risk Notes:** None.

### Task 3: Replace pagination controls with modern paging bar
**Intent:** Replace the two-button Previous/Next strip with First/Previous/Indicator/Next/Last controls.
**Inputs:** `FileRowsPanel.jsx` pagination section (lines ~388-404).
**Outputs:** `react-app/src/components/FileRowsPanel.jsx` (modified pagination section).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Replace the existing `<div className="pagination-controls">` block with a new block containing First, Previous, page indicator span, Next, and Last buttons.
2. Apply correct disabled states: First and Previous disabled when `currentPage === 0`; Next and Last disabled when `currentPage >= totalPages - 1`.
3. Assign appropriate `aria-label` values to each button.
**Done Criteria:** All five pagination elements render; First jumps to page 0; Last jumps to totalPages-1; disabled states are correct.
**Dependencies:** None (independent of Task 1 and 2).
**Risk Notes:** None.

### Task 4: Add CSS for modal and updated pagination
**Intent:** Style the FileRowDetailModal and the new pagination bar.
**Inputs:** `react-app/src/App.css` (existing); RecordDetailModal inline styles (reference).
**Outputs:** `react-app/src/App.css` (modified).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add a `.file-row-detail-modal` section with backdrop, card, dl grid, divider, and close-button styles.
2. Update or confirm `.pagination-controls` CSS accommodates the new five-element bar layout with proper gap, alignment, and disabled appearance.
3. Add responsive rules inside existing breakpoints if needed.
**Done Criteria:** Modal and pagination render correctly at 1200px, 900px, and 600px viewport widths.
**Dependencies:** Tasks 1 and 3.
**Risk Notes:** None.

### Task 5: Write/update unit tests
**Intent:** Add tests for the row-click modal and new pagination buttons; ensure existing tests T1–T15 still pass.
**Inputs:** `FileRowsPanel.test.jsx` (existing); `RecordDetailModal.test.jsx` (reference).
**Outputs:** `react-app/src/components/FileRowDetailModal.test.jsx` (new); `react-app/src/components/FileRowsPanel.test.jsx` (appended).
**External Interfaces:** vitest, @testing-library/react.
**Environment & Configuration:** None.
**Procedure:**
1. Create `FileRowDetailModal.test.jsx` with tests: modal renders with display fields, modal renders surrogate keys, modal closes on Escape, modal closes on backdrop click.
2. Append to `FileRowsPanel.test.jsx`: clicking a row opens the modal (selectedRow set), modal closes when onClose is called, First button disabled on page 1, Last button disabled on last page, First button jumps to page 1, Last button jumps to last page.
3. Run `npm test` and confirm all tests pass.
**Done Criteria:** All new tests pass; T1–T15 still pass; no console errors.
**Dependencies:** Tasks 1, 2, 3.
**Risk Notes:** None.

### Task 6: Update context.md and documentation
**Intent:** Record the changes introduced by this request in .aib_memory/context.md.
**Inputs:** `.aib_memory/context.md` (existing), `.aib_brain/conventions/context-convention.md`.
**Outputs:** `.aib_memory/context.md` (appended update line and updated Functional Capabilities section).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Read context-convention.md to confirm update rules.
2. Append an update note to the auto-generated header block.
3. Update the Functional Capabilities item 7 to mention FileRowDetailModal and the modern pagination bar.
**Done Criteria:** context.md reflects the new modal and paging bar; no other sections changed.
**Dependencies:** Tasks 1-4.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — update Functional Capabilities item 7 to reference FileRowDetailModal and first/last page navigation.

## Questions & Decisions

No open questions. All decision forks are resolvable from the existing codebase and conventions.

## Code and Asset Scan for Impacted Components

- `react-app/src/components/FileRowsPanel.jsx` — primary file: add row onClick, modal state, modern pagination.
- `react-app/src/components/FileRowDetailModal.jsx` — new file: row detail modal.
- `react-app/src/App.css` — styling for modal and pagination.
- `react-app/src/components/FileRowsPanel.test.jsx` — existing tests extended with new modal and pagination tests.
- `react-app/src/components/FileRowDetailModal.test.jsx` — new test file for the modal.

## Internal Review of Request and Product Docs

Request is consistent with the product's existing modal pattern (RecordDetailModal), star-schema dimension key structure, and the FileRowsPanel data flow. The fileKey is already a prop so it can be forwarded to the modal without additional fetches. The modern pagination change is purely presentational with no data-layer impact.
