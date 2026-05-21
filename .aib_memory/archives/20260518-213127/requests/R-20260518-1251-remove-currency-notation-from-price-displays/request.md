## Goal

Remove all occurrences of the Bulgarian lev currency notation (`лв`, `(лв)`, `лв.`, and similar variants) from price display strings across the React Analytics App. Prices should be displayed as bare numeric values only, with no currency suffix or prefix. No replacement text of any kind should be substituted.

## Background

The Kolko Ni Struva React app displays retail price data sourced from the Bulgarian government open-data portal. Prices in the underlying data are stored as raw numeric values. The UI currently appends the currency abbreviation `лв` (Bulgarian lev) to every formatted price in all five views. The product owner has confirmed the prices are not denominated in leva and requests that any currency indication be removed entirely to avoid misleading users.

## Scope

- Remove `лв` suffix from all inline price rendering expressions in JSX across all components.

- Remove `(лв)` from column header labels in `FileRowsPanel.jsx` and `Report3.jsx` column definition arrays.

- Remove `лв` suffix from the `formatPrice()` helper in `FileRowDetailModal.jsx`.

- Remove `лв` suffix from the bar-chart value label in `Report1.jsx`.

- Remove `лв` suffix from all inline price cell renders in `Report2.jsx`, `Report3.jsx`, and `RecordDetailModal.jsx`.

- Update the automated test in `FileRowsPanel.test.jsx` to match the new column header labels (without `(лв)`).

- Update any code comments in the affected files that describe the `лв` suffix format.

## Out of scope

- Changes to ETL pipeline scripts (`src/`), Supabase schema, or raw data values.
- Changes to any file outside `react-app/src/components/`.
- Adding any alternative currency indicator (ISO code, symbol, or otherwise).
- Changing numeric precision or formatting (still two decimal places, locale-agnostic `toFixed(2)`).
- Changes to `dataService.js` or any non-component JS module.

## Constraints

- No replacement text: the currency notation must be deleted, not substituted.
- Numeric formatting (two decimal places) must remain unchanged.
- All six test files in `react-app/src/` must continue to pass after changes.
- The build (`npm run build` in `react-app/`) must exit 0.

## Success criteria

- SC-1: No occurrence of `лв` or `(лв)` appears in any rendered UI string or column label across the five React app pages.
- SC-2: All price values continue to display with two decimal places.
- SC-3: `npm test` (Vitest) passes for all component test files, including `FileRowsPanel.test.jsx` with updated label assertions.
- SC-4: `npm run build` exits 0 in `react-app/`.
- SC-5: No new occurrences of currency notation are introduced in comments intended to describe UI output format.

## Assumptions

- A1: The `лв` suffix in `FileRowDetailModal.jsx`'s `formatPrice()` is the only function-scoped formatter; no equivalent utility exists in `dataService.js` or shared libs.
  - Risk if false: Additional occurrences missed by grep would survive the change, breaking SC-1.

- A2: No end-to-end or Playwright tests exist that assert on rendered price values with currency suffix; the only automated assertions requiring update are the 8 `getByText()` calls in `FileRowsPanel.test.jsx`.
  - Risk if false: Additional test files may fail after implementation, requiring further updates.

- A3: The `bg-BG` locale in `FileRowDetailModal.jsx`'s `toLocaleString` call is used solely for decimal/thousands formatting and is unrelated to the `лв` suffix; removing the suffix does not break the locale formatting.
  - Risk if false: None — the locale call and the currency suffix are independent string concatenations.

- A4: `npm test` and `npm run build` can be run without environment variables (Supabase keys) present, as component tests use Vitest mocks and the build step does not require live credentials.
  - Risk if false: Test run or build would fail in environments without `.env` file; developer must ensure env file exists before verifying SC-3 and SC-4.

## Plan

### Task 1: Remove currency notation from all JSX components
**Intent:** Delete every `лв` suffix from price rendering expressions and column label strings in the six affected component files, and update the stale code comment in `Report3.jsx`.
**Inputs:** `react-app/src/components/Report1.jsx`, `Report2.jsx`, `Report3.jsx`, `RecordDetailModal.jsx`, `FileRowDetailModal.jsx`, `FileRowsPanel.jsx`
**Outputs:** Same six files with `лв` removed from all price display strings and column labels.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. In `Report1.jsx`: remove ` лв` from the bar chart value JSX expression.
2. In `Report2.jsx`: remove ` лв` from the three price cell template literals.
3. In `Report3.jsx`: remove ` (лв)` from three column label strings; remove ` лв` from three `formatPrice` / format-function return strings; remove ` лв` from three inline table cell render expressions; update the comment on line 29 to no longer reference `'лв' suffix`.
4. In `RecordDetailModal.jsx`: remove ` лв` from the three inline price display template literals.
5. In `FileRowDetailModal.jsx`: remove ` лв` from the `formatPrice()` return string.
6. In `FileRowsPanel.jsx`: remove ` (лв)` from all seven column label strings.
**Done Criteria:** `grep -r 'лв' react-app/src/components/` returns zero matches.
**Dependencies:** None.
**Risk Notes:** Pattern is pure string deletion; no logic risk. Verify `toFixed(2)` and `toLocaleString` calls are preserved.

### Task 2: Update FileRowsPanel test assertions
**Intent:** Update the 8 `getByText()` assertions in `FileRowsPanel.test.jsx` to match the new column header labels without `(лв)`.
**Inputs:** `react-app/src/components/FileRowsPanel.test.jsx`
**Outputs:** Updated `FileRowsPanel.test.jsx` with corrected label strings.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Replace `'Цена (лв)'` with `'Цена'`.
2. Replace `'Промо цена (лв)'` with `'Промо цена'`.
3. Replace `'Ефективна цена (лв)'` with `'Ефективна цена'`.
4. Replace dynamic date-prefixed label assertions: `'Цена 14.05.2026 (лв)'` → `'Цена 14.05.2026'`; `'Промо 14.05.2026 (лв)'` → `'Промо 14.05.2026'`; `'Цена 13.05.2026 (лв)'` → `'Цена 13.05.2026'`; `'Промо 13.05.2026 (лв)'` → `'Промо 13.05.2026'`.
**Done Criteria:** `npm test` in `react-app/` passes with all FileRowsPanel tests green.
**Dependencies:** Task 1.
**Risk Notes:** None.

### Task 3: Run automated tests and build
**Intent:** Verify SC-3 and SC-4 — all Vitest tests pass and `npm run build` exits 0.
**Inputs:** Updated component files and test file from Tasks 1–2.
**Outputs:** Test run output (pass/fail report); `react-app/dist/` build artefacts.
**External Interfaces:** Node.js runtime, Vite build toolchain.
**Environment & Configuration:** Requires `.env` file in `react-app/` with valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` for build step; mocked in tests.
**Procedure:**
1. Run `cd react-app && npm test` and verify all tests pass.
2. Run `npm run build` and verify exit code 0 and `dist/` produced.
3. Confirm `grep -r 'лв' react-app/src/components/` returns zero matches.
**Done Criteria:** `npm test` exits 0; `npm run build` exits 0; grep returns no matches.
**Dependencies:** Tasks 1, 2.
**Risk Notes:** Build requires env file; if absent, create a `.env` from `.env.example` before build.

### Task 4: Update context.md and documentation
**Intent:** Reflect the currency notation removal in `context.md` and any other documentation impacted.
**Inputs:** `.aib_memory/context.md`
**Outputs:** Updated `.aib_memory/context.md` with a new update line for R-20260518-1251.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Add a new update line to `.aib_memory/context.md` describing the change made by R-20260518-1251.
2. Review `README.md` to confirm it contains no references to `лв` in price display descriptions; update if present.
**Done Criteria:** `context.md` contains an update line for R-20260518-1251; `README.md` has no stale `лв` references.
**Dependencies:** Tasks 1, 2, 3.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Add update entry for R-20260518-1251 describing the removal of `лв` notation from all price displays in the React app.
- `README.md` (ref_id: N/A) — Review for any references to `лв` in UI description sections; update if present (low probability).

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/components/Report1.jsx` | Modified | Remove `лв` suffix from bar chart price value display (1 occurrence) |
| `react-app/src/components/Report2.jsx` | Modified | Remove `лв` suffix from 3 price cell template literals |
| `react-app/src/components/Report3.jsx` | Modified | Remove `(лв)` from 3 column labels; remove `лв` from 3 format-function returns + 3 inline renders; update 1 code comment |
| `react-app/src/components/RecordDetailModal.jsx` | Modified | Remove `лв` suffix from 3 inline price display expressions |
| `react-app/src/components/FileRowDetailModal.jsx` | Modified | Remove `лв` suffix from `formatPrice()` helper return string |
| `react-app/src/components/FileRowsPanel.jsx` | Modified | Remove `(лв)` from 7 column label strings in the column definition array |
| `react-app/src/components/FileRowsPanel.test.jsx` | Modified | Update 8 `getByText()` assertions to match new column labels without `(лв)` |
| `.aib_memory/context.md` | Modified | Add update entry for R-20260518-1251 |
| `README.md` | Read-only dependency | Review for stale `лв` references; no change expected |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal, Background, Scope, Out of scope, Constraints, and Success criteria are all present, non-empty, and consistent with each other.
- OK: `context.md` — Product context is current (last update R-20260518-1052). No contradiction with the request: removing a display suffix does not affect any described ETL, Supabase, or RPC behaviour.
- Missing info: `request.md` — No mention of whether `README.md` describes `лв` in UI documentation. Research scan of `README.md` content for `лв` should be performed during implementation Task 4.
- OK: `input.md` — Input text is clear and unambiguous: remove `лв` and similar notation everywhere, replace with nothing.
- OK: Success criteria SC-1 through SC-5 are each testable and traceable to specific file changes or automated checks.

