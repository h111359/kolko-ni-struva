## Executive Summary

- **Request ID:** R-20260517-1113
- **Title:** File detail record clickable modal and modern paging

- **High-level purpose:** Enhance the FileRowsPanel table in the Файлове page with two interactive features: (1) clicking any row opens a detail modal exposing all display fields and surrogate keys/IDs from the star-schema tables; (2) the two-button paging strip is replaced with a modern navigation bar (First/Previous/Indicator/Next/Last).

- **Sections updated in request.md:** Assumptions, Plan, Documentation, Questions & Decisions (no questions raised — all forks resolved from existing workspace sources).

- **Scope confirms:** New `FileRowDetailModal.jsx` component; `FileRowsPanel.jsx` modified for row-click state and modern pagination; `App.css` extended; new and extended test files.

## Domain Knowledge Essentials

- **FileRowsPanel:** React component in the Файлове (Files) page that shows individual price-fact records for a selected source file. Each row is an enriched fact record pulled from `fact_prices_lookback` via `fetchFileRows`.
- **Star-schema surrogate keys:** Internal integer keys that link fact rows to dimension tables. `product_key` → `dim_product`; `category_key` → `dim_category`; `store_key` → `dim_store`; `file_key` → `dim_file`; `settlement_key` and `company_key` are attributes of `dim_store` and can be resolved from `dims.stores`.
- **RecordDetailModal:** Existing modal in Report 2 that shows per-row provenance. This request follows the same UX pattern for FileRowsPanel.
- **Pagination:** Client-side pagination over all pre-loaded rows. PAGE_SIZE=100; totalPages = Math.ceil(filteredRows.length / PAGE_SIZE). First/Last buttons jump directly to page 0 and totalPages-1.
- **Data engineers / analysts:** Primary users who need internal keys for debugging and data lineage.

## Technical Knowledge & Terms

- **FileRowsPanel.jsx:** `react-app/src/components/FileRowsPanel.jsx`. Renders the 12-column detail table; currently has `previousPage`/`nextPage` only.
- **fetchFileRows:** `react-app/src/lib/dataService.js` — returns enriched rows with `product_key`, `category_key`, `store_key` already on the row object.
- **dims cache:** Object with `categories` (Map), `stores` (Array), `companies` (Map), `settlements` (Map), `dates` (Array). `settlement_key` and `company_key` are attributes of store entries (`store.settlement_key`, `store.company_key`).
- **RecordDetailModal pattern:** Escape keydown listener via `useEffect`, backdrop `onClick`, stop-propagation on the card `div`, close button in absolute top-right position.
- **Vitest + @testing-library/react:** Testing framework used across all component tests. `fireEvent.click`, `screen.getByRole`, `act` for async.
- **App.css sections:** Existing pagination styles are inline in `FileRowsPanel.jsx`'s JSX (no dedicated class); the new implementation will use `.pagination-controls` class (already referenced in the JSX but has no explicit CSS rule in App.css).

**Files Read:**
- `react-app/src/components/FileRowsPanel.jsx`
- `react-app/src/components/RecordDetailModal.jsx`
- `react-app/src/components/FileRowsPanel.test.jsx`
- `react-app/src/App.css`
- `react-app/src/lib/dataService.js` (fetchFileRows section)
- `.aib_memory/context.md`

## Research Results

- **Pattern match — existing RecordDetailModal:** The existing modal in `RecordDetailModal.jsx` provides a proven implementation pattern (Escape listener via useEffect, backdrop div with onClick, stop-propagation on card). The new `FileRowDetailModal` should follow this pattern exactly for consistency.
- **Surrogate key availability:** All needed keys (`product_key`, `category_key`, `store_key`) are already in the row objects returned by `fetchFileRows`. `settlement_key` and `company_key` require one `Array.find` on `dims.stores` (same resolution used in `RecordDetailModal`). `file_key` is a prop (`fileKey`) of FileRowsPanel and must be forwarded.
- **Pagination pattern:** The current pagination bar uses inline buttons with no CSS class. Adding First/Last requires only two additional `<button>` elements with correct disabled logic. The `currentPage` state is already zero-based.

## External Benchmarking

- **Material UI / Ant Design pagination components:** Both flagship React component libraries implement a pagination bar with First, Previous, numbered pages or ellipsis, Next, and Last controls. The pattern is universally adopted in data-heavy applications. Key takeaway: the minimum viable "modern" paging bar for a dataset with many pages includes at least First and Last jump buttons; numbered page buttons are optional if a page indicator is shown.
  - Adopted: First and Last buttons added (mandatory for the "directly to first/last page" requirement). Numbered page buttons omitted as they are optional and would require significant additional state and CSS.
- **WAI-ARIA dialog pattern (W3C):** Specifies that modal dialogs must use `role="dialog"`, `aria-modal="true"`, an accessible label (`aria-labelledby`), and must trap focus. Escape key dismissal is mandatory. Backdrop click dismissal is a widely adopted convenience pattern.
  - Adopted: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, Escape keydown handler. Focus trap is desirable but the existing `RecordDetailModal` does not implement it, so this request will not add it (scope parity).

## Minimal Spikes and Experiments

- **Spike: surrogate key availability in row objects**
  - Hypothesis: `product_key`, `category_key`, `store_key` are present in the enriched row objects returned by `fetchFileRows` without needing additional fetches.
  - Approach: Read `fetchFileRows` implementation in `dataService.js`; inspect the `rows.map` enrichment block.
  - Outcome: Confirmed. The enrichment spreads `...row` (which includes `product_key`, `category_key`, `store_key` from the Supabase SELECT) and adds display names on top. No additional fetch needed.
  - Conclusion: The modal can read all three keys directly from the row object prop. `file_key` must be forwarded from the `fileKey` prop; `settlement_key`/`company_key` resolved from `dims.stores`.

- **Spike: CSS for `.pagination-controls`**
  - Hypothesis: `.pagination-controls` class has no existing CSS rule in App.css, meaning the buttons render with default browser styles.
  - Approach: Searched App.css for `.pagination-controls` and `pagination`.
  - Outcome: Confirmed — `.pagination-controls` appears only in `FileRowsPanel.jsx` JSX, not in App.css. The new CSS section must define all layout and button styles for the pagination bar.
  - Conclusion: A new `.pagination-controls` CSS block must be added to App.css.

## AI Copilot Suggestions

- **Modal reuse vs. new component:** A pragmatic argument exists for extending `RecordDetailModal.jsx` with an optional `mode` prop to switch between Report-2 and FileRowsPanel content. However, the two modals have genuinely different content requirements (different fields, different key sets) and the existing `RecordDetailModal` has a stable test suite; coupling them would introduce regression risk and violate the single-responsibility principle. Creating a separate `FileRowDetailModal.jsx` is the right call.
  - Suggestion: Keep them separate. Name the new component clearly to indicate its scope (`FileRowDetailModal`).

- **Pagination UX scope risk:** The request asks for a "slick" pagination bar with first/last navigation. Adding five interactive elements (First, Prev, indicator, Next, Last) is the minimal version. A page-number input field (type=number) that lets users jump to an arbitrary page is a common extension that would cover the same requirement more completely. However, this extends scope without being explicitly requested.
  - Suggestion: Implement exactly the five-element bar (First / Prev / indicator / Next / Last). Document the page-input extension as a potential follow-up.

- **Test coverage for row-click deselect on file change:** The existing `fileKey`-change `useEffect` resets sort, filter, and page. The `selectedRow` state should also be reset to `null` when the file changes, otherwise a stale modal could appear when the user switches files. This is a subtle correctness issue not explicitly mentioned in the request.
  - Suggestion: Reset `selectedRow` to `null` in the same `useEffect` that resets sort, filter, and page.

## Testing

- T1 — FileRowDetailModal renders display fields: Render the modal with a stub row and dims; assert all 12 display field labels and values are present. Expected outcome: all fields visible in the rendered modal.
- T2 — FileRowDetailModal renders surrogate keys: Assert product_key, category_key, store_key, file_key, settlement_key, company_key labels and values are visible. Expected outcome: all key labels and their numeric values are in the document.
- T3 — FileRowDetailModal closes on Escape: Dispatch a keydown Escape event after rendering; assert onClose callback was called. Expected outcome: onClose called once.
- T4 — FileRowDetailModal closes on backdrop click: Click the backdrop element; assert onClose callback was called. Expected outcome: onClose called once.
- T5 — Clicking a row in FileRowsPanel opens the modal: Render FileRowsPanel with one stub row; click the `<tr>` in the tbody; assert the modal heading "Детайли за запис" is in the document. Expected outcome: modal is rendered.
- T6 — Modal closes from FileRowsPanel when onClose is invoked: After opening the modal via row click, trigger Escape; assert the modal heading is gone. Expected outcome: modal unmounts.
- T7 — First button disabled on page 1: Render with one page of data; assert First button is disabled. Expected outcome: First button has disabled attribute.
- T8 — Last button disabled on last page: Render with ≤ PAGE_SIZE rows; assert Last button is disabled. Expected outcome: Last button has disabled attribute.
- T9 — First button jumps to first page: Navigate to page 2 (via Next), then click First; assert page indicator shows "Страница 1 от …". Expected outcome: currentPage resets to 0.
- T10 — Last button jumps to last page: On a two-page result set, click Last from page 1; assert page indicator shows "Страница 2 от 2". Expected outcome: currentPage advances to totalPages-1.

See also existing tests T1–T15 in FileRowsPanel.test.jsx which must continue to pass.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is well-scoped and follows established product patterns. Creating a new `FileRowDetailModal.jsx` rather than extending `RecordDetailModal.jsx` is architecturally sound — the two modals serve different contexts and extending a shared component would introduce unneeded coupling. The modern pagination change is presentational and introduces no architectural risk. The only noteworthy risk is the `fileKey` forwarding: it is a prop of `FileRowsPanel`, not of individual rows, and must be explicitly passed to the modal — this is straightforward but easy to miss.

- Surrogate key resolution from dims is consistent with existing pattern in RecordDetailModal.
- No new Supabase queries required — data is already loaded.
- No breaking changes to existing API surface of FileRowsPanel.
- fileKey forwarding from prop to modal is the single integration point requiring care.

### Product Owner

This feature directly addresses a data-engineering user need: being able to inspect internal IDs from the UI without querying the database directly. The first/last page navigation eliminates a pain point when browsing large files (hundreds of rows). Both features are clearly described and have no ambiguous acceptance criteria.

- Business value: medium-high for data engineers; low for casual users (who rarely need internal keys).
- Scope is appropriately minimal — no feature creep detected.
- Success criteria are measurable and testable.
- Follow-up opportunity: a direct page-number jump input could further reduce friction for very large files.

### User

Clicking on a row to see details is an intuitive, expected behaviour for data tables. The modal showing keys and IDs will be useful to technically savvy users; it may be noisy for casual users who do not know what `product_key: 4271` means. The first/last navigation buttons greatly reduce the effort needed to jump to the end of a 1,000-row file at PAGE_SIZE=100 (10 pages).

- The modal should clearly label which fields are display fields and which are surrogate keys so casual users understand the distinction.
- First/Last buttons should be visually distinct from (or clearly adjacent to) Previous/Next.
- Escape-key dismissal is expected and must work reliably.

### Security Officer

This feature is read-only: it renders data already fetched from Supabase into a modal. No additional queries, no write operations, no authentication bypass. The surrogate keys exposed in the modal are internal IDs with no direct exploitation surface in a read-only public-access app. Row-click state is held in component `useState` — no persistence, no URL exposure.

- No new attack surface introduced.
- No credentials or sensitive data beyond what is already displayed in the table.
- Modal backdrop dismissal must not leak state (reset selectedRow on close — already in plan).

### Data Governance Officer

The surrogate keys displayed in the modal (product_key, category_key, store_key, file_key, settlement_key, company_key) are internal schema identifiers. Exposing them in the UI does not change data lineage or classification; they are already persisted in Supabase and accessible to anyone with the anon key (which is public in the React app by design). No PII is present in the star schema. No retention or compliance impact.

- Internal IDs are not classified as sensitive in the current product context.
- No new data elements are fetched — the modal reuses already-loaded enriched rows.
- Data lineage: the `file_key` shown in the modal directly links a fact row back to its source `dim_file` entry, which improves traceability.
