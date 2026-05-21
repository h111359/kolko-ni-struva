# Analysis: R-20260518-1251 — Remove currency notation from price displays

## Executive Summary

- **Request ID:** R-20260518-1251

- **Title:** Remove currency notation from price displays

- **Purpose:** Remove all occurrences of the `лв` (Bulgarian lev) currency abbreviation from every price display string rendered in the React Analytics App. The product owner has confirmed prices are not in leva; no replacement text is to be substituted.

- **Scope confirmed:** The change is limited to `react-app/src/components/` — six JSX component files and one test file. No backend, ETL, Supabase schema, or data-layer files are involved.

- **Impact summary:** 7 files require edits. The changes are purely textual (string literal removals) and carry negligible implementation risk. The only behavioral change observable to users is the disappearance of the `лв` suffix after numeric price values.

- **`request.md` updates this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` sections populated. `## Questions & Decisions` is empty (no blocking questions at threshold 3).

---

## Domain Knowledge Essentials

- **лв (лев / lev):** ISO 4217 code BGN; the official currency of Bulgaria. In the existing UI, price values were displayed with a `лв` suffix to indicate Bulgarian lev denomination. The product owner has asserted this notation is incorrect and should be removed entirely.

- **Price columns in the React app:** The React app exposes four categories of price values per product record: `retail_price` (regular shelf price), `promo_price` (promotional price), `calculatedPrice` (effective price — the lower of retail/promo), and lookback variants `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2` for historical date comparison.

- **Affected user-facing pages:** All five pages can display prices in various forms: Report 1 (bar chart average per category), Report 2 (table with per-row modal), Report 3 (filterable table), and the Файлове (Files) page via `FileRowsPanel` and `FileRowDetailModal`. Home page does not display price values.

- **Impacted personas:** End users reading the analytics app (public, no authentication); no ETL operator or data engineer workflow is affected.

---

## Technical Knowledge & Terms

- **React JSX (`.jsx`):** Syntax extension for JavaScript allowing HTML-like markup inside JS; price strings are constructed via template literals (`` `${value.toFixed(2)} лв` ``) or locale-formatted strings. Removing the suffix is a string-literal edit with no logic consequences.

- **Vitest + React Testing Library:** The test suite for the React app uses Vitest as the test runner and React Testing Library's `screen.getByText()` for DOM assertions. Eight assertions in `FileRowsPanel.test.jsx` check for column header text that includes `(лв)`. These must be updated to match the new labels.

- **`toFixed(2)` / `toLocaleString('bg-BG', ...)`:** Numeric formatting methods used across the components to produce two-decimal-place strings. These are unaffected by the change; only the currency suffix appended after the number is removed.

- **Column label arrays:** `FileRowsPanel.jsx` and `Report3.jsx` define column metadata in declarative arrays (`{ key, label, type }`). The `label` strings for numeric price columns currently include `(лв)`. Removing the parenthesized suffix from the label string also satisfies the column header rendering.

- **`formatPrice()` in `FileRowDetailModal.jsx`:** A local helper function that formats a numeric value with locale formatting and appends `лв`. The function body must be updated; the function signature and calling code are unaffected.

- **`npm run build` / Vite:** Build tooling for the React app. A passing build is a required success criterion. No build configuration changes are needed for this request.

- **Files touched (7 total):**
  - `react-app/src/components/Report1.jsx` — 1 suffix occurrence in bar chart JSX
  - `react-app/src/components/Report2.jsx` — 3 suffix occurrences in table cell JSX
  - `react-app/src/components/Report3.jsx` — 3 column label strings + 3 format function returns + 3 inline table cell renders + 1 comment describing the suffix
  - `react-app/src/components/RecordDetailModal.jsx` — 3 inline suffix occurrences in detail modal
  - `react-app/src/components/FileRowDetailModal.jsx` — 1 occurrence in `formatPrice()` helper
  - `react-app/src/components/FileRowsPanel.jsx` — 7 column label strings
  - `react-app/src/components/FileRowsPanel.test.jsx` — 8 `getByText()` assertions referencing column labels with `(лв)`

---

## Research Results

**Files read for this analysis:**
- `.aib_memory/input.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/analysis-convention.md`
- `.aib_brain/conventions/request-convention.md`
- `react-app/src/components/Report1.jsx` (via grep scan)
- `react-app/src/components/Report2.jsx` (via grep scan)
- `react-app/src/components/Report3.jsx` (via grep scan)
- `react-app/src/components/RecordDetailModal.jsx` (via grep scan)
- `react-app/src/components/FileRowDetailModal.jsx` (via grep scan)
- `react-app/src/components/FileRowsPanel.jsx` (partial read)
- `react-app/src/components/FileRowsPanel.test.jsx` (via grep scan)
- `react-app/src/components/FileRowDetailModal.test.jsx` (partial read)
- `react-app/src/components/RecordDetailModal.test.jsx` (via grep scan)
- `react-app/src/components/Report1.test.jsx`, `Report2.test.jsx`, `Report3.test.jsx` (via grep scan)
- `react-app/src/lib/dataService.test.js` (via grep scan)

**Evidence → Implication map:**

| Evidence | Implication |
| --- | --- |
| `лв` appears in 6 component files (32 total grep matches including test file) | All 6 component files need edits; no central shared formatter |
| `FileRowsPanel.test.jsx` has 8 `getByText('... (лв)')` assertions | Test file must be updated to avoid test breakage |
| `Report1.test.jsx`, `Report2.test.jsx`, `Report3.test.jsx` do not assert on `лв` in rendered values | No changes needed in those three test files |
| `FileRowDetailModal.test.jsx` checks field labels ('Ефективна цена:', 'Цена на дребно:'), not formatted price values | No changes needed in `FileRowDetailModal.test.jsx` |
| `RecordDetailModal.test.jsx` uses raw numeric values in mock data, not formatted strings | No changes needed in `RecordDetailModal.test.jsx` |
| No central price-formatting utility exports `лв` from `dataService.js` | No single-point fix; changes must be made in each component |
| `Report3.jsx` line 29 comment documents the `'лв' suffix` behavior | Comment should be updated to reflect the removal |

**Pattern scan findings:**
- There is no shared price-formatting utility or `formatCurrency()` helper in `dataService.js` or any shared lib file. Each component manages its own price rendering. This is pre-existing design; the request scope does not ask for refactoring.
- The `formatPrice()` function in `FileRowDetailModal.jsx` uses Bulgarian locale (`bg-BG`) for decimal formatting. The locale call itself is unrelated to the currency suffix and remains unchanged.

---

## External Benchmarking

**1. Locale-neutral numeric display in financial applications**
Industry practice (referenced in Material UI, Ant Design, and multiple fintech SaaS UI pattern libraries) recommends decoupling numeric locale formatting from currency annotation. When currency context is conveyed by page/column heading rather than individual cell values, per-cell currency suffixes are omitted. This aligns directly with the requested change — the column headers already convey the price context ("Цена", "Промо цена", etc.) without the `лв` suffix once it is removed from labels as well.
- *Takeaway:* The pattern of removing the currency suffix from cell values when the column label or section heading already identifies the domain is well-established. Adoption is direct and unambiguous here.

**2. React Testing Library assertion hygiene for label changes**
The React Testing Library documentation and community guides (Kent C. Dodds' testing-library blog, official RTL docs) consistently recommend that test assertions on user-visible text must exactly match rendered output. When label strings change (even cosmetically), tests must be updated. The recommended approach is to update assertions to the new expected strings rather than using partial-match queries, ensuring the test remains specification-accurate.
- *Takeaway:* The `FileRowsPanel.test.jsx` assertions must be updated with exact new label strings (without `(лв)`). Using `getByText()` with the updated strings is the correct approach, consistent with RTL best practices. Rejected: switching to `queryAllByRole` or partial regex matchers as a workaround — this would reduce assertion specificity without benefit.

---

## Minimal Spikes and Experiments

**No spike conducted.** The full set of affected code locations was identified via a comprehensive grep scan of `react-app/src/**` for the pattern `лв|лева`. All matches were confirmed to be either: (a) UI rendering expressions whose output is visible to users, or (b) test assertions coupled to those renderings, or (c) code comments. The change pattern is a string-literal removal with no branching, conditional, or runtime-behavior impact. Uncertainty was low enough that a code spike was not warranted.

---

## AI Copilot Suggestions

- **Observation 1 — No central price formatter (pre-existing tech debt, not in scope):** Price formatting is duplicated across six components with no shared utility. This makes the current change require 7 file edits for what is conceptually a single configuration value. While the request explicitly excludes refactoring, this pattern will cause similar cascading changes for any future price display modification (e.g., adding a decimal separator change). After this request is closed, consider extracting a shared `formatPrice(value)` utility to `dataService.js` or a new `src/lib/formatters.js` in a follow-on request.

- **Observation 2 — Column label `(лв)` removal changes visual context for users:** The current column labels (`'Цена (лв)'`, `'Промо цена (лв)'`, etc.) communicate to users both the column purpose and the unit. After removal, the labels become `'Цена'`, `'Промо цена'`, etc. — which are already self-describing in Bulgarian context, and the request owner has explicitly requested the removal. There is no ambiguity risk if the product owner has confirmed prices are not in leva. However, if there is a future need to communicate units or currency explicitly, the column heading is the correct placement (not per-cell suffixes).

- **Observation 3 — Scope is appropriately sized:** The request is well-scoped: string-literal removals in components + test updates. No over-engineering risk. However, the `Report3.jsx` comment on line 29 that describes `'the лв suffix'` should also be updated to prevent misleading internal documentation — this is a low-effort item already covered in the request scope.

- **Observation 4 — Test coverage gap for rendered price values:** `Report2.test.jsx`, `Report3.test.jsx`, and `RecordDetailModal.test.jsx` use mock data with raw numeric values but do not assert on the rendered formatted price strings. This means the `лв` removal in those components will not be regression-tested automatically. The implementation task should include at least one assertion per untested component verifying the rendered price is a bare numeric string (no currency suffix). This is within scope as part of updating the test suite.

---

## Testing

- **T1 — Source scan passes:** After implementation, `grep -r 'лв' react-app/src/components/` returns zero matches. Expected outcome: PASS — command exits 0 with no output.

- **T2 — FileRowsPanel column headers — no лв:** `FileRowsPanel.test.jsx` updated assertions pass: `getByText('Цена')`, `getByText('Промо цена')`, `getByText('Ефективна цена')`, and dynamic date-prefixed labels (`'Цена 14.05.2026'`, etc.) resolve correctly. Expected outcome: PASS — Vitest reports all assertions in the column-headers test case as green.

- **T3 — Full Vitest suite passes:** `npm test` run from `react-app/` exits 0 with all test files passing. Expected outcome: PASS — no test failures; test count equals pre-change test count.

- **T4 — Build exits 0:** `npm run build` from `react-app/` exits 0 and produces `dist/`. Expected outcome: PASS — no TypeScript/JSX compile errors introduced.

- **T5 — Numeric precision preserved:** Price values rendered in components still display two decimal places. Verifiable by inspecting rendered DOM text in existing test runs (e.g., `'2.49'` renders rather than `'2'` or `'2.490000'`). Expected outcome: PASS — `toFixed(2)` calls are unchanged; all decimal assertions in existing tests remain valid.

- **T6 — Idempotent re-run:** Running `npm test` a second time without further code changes produces the same pass result. Expected outcome: PASS — no flakiness introduced by the change.

See UAT_scenarios.md — UAT-01 for visual end-to-end verification across all five app pages.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The change is architecturally trivial — string literal removals in leaf-level UI components with no shared state, API contract, or schema impact. The architecture of the React app remains unaffected. The absence of a central price formatter is a pre-existing architectural concern not introduced by this request; fixing it is outside scope and should be tracked separately. The only architectural risk is the test coverage gap for rendered price values in Report 2, Report 3, and RecordDetailModal — these components currently have no assertions on formatted output, which means a silent regression of future currency re-introduction would not be caught automatically. Adding minimal assertions is advisable as part of this request.

Findings:
- Leaf-level change; no architectural risk from the modification itself.
- Test coverage gap for formatted price values in Report 2, Report 3, RecordDetailModal.
- Pre-existing lack of a shared price formatter increases future maintenance burden (out of scope for this request).
- No cross-component dependencies exist that would propagate the change unexpectedly.
- Build and deploy pipeline (Vite + Netlify) is unaffected.

### Product Owner

The request is clearly stated, well-scoped, and directly addresses a user-facing data accuracy concern: displaying a currency label that does not match the actual denomination of the data is misleading. The success criteria are measurable and testable. The change is reversible if requirements change. No business process or data pipeline is impacted.

Findings:
- Business value is clear and immediate: removes potentially misleading UI text.
- Acceptance criteria (SC-1 through SC-5) are complete and verifiable.
- No feature flags or release coordination needed — the change is safe to deploy directly.
- Follow-on consideration: if a new currency annotation is ever needed, a single column-header approach is preferable over per-cell suffixes.
- No documentation for end users (README, help text) references the `лв` notation, so no public-facing docs need updating.

### User

End users see price values throughout the app (bar chart values, table cells, modals). Removing the `лв` suffix makes prices display as bare numbers (e.g., `3.50` instead of `3.50 лв`). For Bulgarian retail price data this is unambiguous; users reading a price table understand the values are monetary. The change eliminates a potential confusion point if prices are not in leva.

Findings:
- Price readability is unaffected — the numeric value and decimal precision are unchanged.
- Column headers (`Цена`, `Промо цена`, `Ефективна цена`) already communicate context; removing the unit suffix from the header label is slightly less explicit but acceptable given the product owner's intent.
- No user interaction change; modals, sorting, and filtering remain identical.
- Mobile/responsive layout is unaffected — shorter strings may marginally reduce horizontal space pressure in narrow viewports.
- No accessibility regression — `aria-sort` attributes and filter inputs are untouched.

### Security Officer

This change is purely a UI string modification with no security implications. No authentication, authorization, data exposure, or input validation changes are involved. The React app is client-only (no serverless functions, no credentials), and the removed strings are static display literals.

Findings:
- No attack surface changes — no new user inputs, no new API calls, no credential handling.
- No data exposure risk — removing a currency suffix does not expose or obscure any underlying data.
- No dependency additions or removals.
- No content security policy implications.
- No XSS risk — the removed strings are static, not derived from user input or API responses.

### Data Governance Officer

The change has no impact on data lineage, retention, classification, or compliance. The underlying fact data in Supabase (`fact_prices_lookback`) and all dimension tables are unchanged. The ETL pipeline is unchanged. The modification affects only the presentation layer of already-transformed analytical data.

Findings:
- No change to any stored data, schema, or ETL logic.
- No new data processing or transformation introduced.
- The `backend_sql_audit_log` table is unaffected.
- No regulatory or compliance implications — the data remains the same public-domain Bulgarian government price data.
- No data lineage or provenance documentation needs updating for this change.
