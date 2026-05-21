## Goal

Make the React Analytics App interface responsive, adapting automatically to the user's device type — mobile phones, tablets, and desktop browsers. The interface should detect and respond to viewport width, adjusting layout, typography, spacing, and table display so that all five pages (Home, Report 1, Report 2, Report 3, Query Log) are fully usable on any screen size without horizontal overflow or unreadable elements.

## Background

The current React app (`react-app/`) was ported from a legacy vanilla-JS app and contains only one media query (at `max-width: 900px`) that addresses just the Query Log page. All other pages — Home, Report 1 (horizontal bar chart), Report 2 (7-column product table), Report 3 (7-column location table), and the header/navigation — are designed primarily for desktop viewports. The `RecordDetailModal` uses `width: 90%` which is acceptable, but its `dl` grid layout and internal padding are not adjusted for narrow screens. The `body` padding, header font sizes, landing page padding (50px), fixed 200px chart label column, and results tables (no horizontal scroll) all represent usability problems on mobile devices. The viewport meta tag is already present in `index.html`.

See `.aib_memory/context.md` for the full product context.

## Scope

- Add CSS media queries in `react-app/src/App.css` targeting at least two breakpoints: mobile (≤ 600px) and tablet (≤ 900px).

- Adjust body/global padding for small screens.

- Reduce header title (`h1`) and subtitle font sizes on mobile so they do not overflow.

- Reduce landing page section padding on mobile.

- Make the data tables in Report 2 and Report 3 horizontally scrollable on mobile by wrapping `.results-container` with `overflow-x: auto`.

- Adjust the Report 1 chart bar label width (currently fixed at `200px`) to be flexible on narrow screens.

- Ensure nav buttons remain usable on mobile (appropriate padding, font size; already have `flex-wrap: wrap`).

- Adjust `RecordDetailModal` internal layout for narrow viewports (reduce padding, reflow `dl` grid to single-column if needed).

- Ensure the date selector and control dropdowns remain usable on mobile.

- All five pages must remain visually coherent on viewport widths from 320px to 1920px.

## Out of scope

- Changes to the ETL pipeline (`src/`, `data/`) or any non-React-app files.

- Addition of a CSS framework (e.g. Tailwind, Bootstrap) — pure CSS media queries only.

- Dark mode or theme switching.

- Touch-specific gesture interactions beyond standard browser tap.

- Accessibility improvements beyond what is incidentally introduced by responsive layout changes.

- Changes to `react-app/src/index.css`.

- Changes to Supabase RPCs, `load_supabase.py`, or any backend logic.

## Constraints

- No new third-party CSS libraries may be added.

- All colour values, gradients, and keyframe animations defined in `App.css` must be preserved.

- Class names used by JSX components must not be renamed.

- `npm run build` must exit 0 after changes.

- The viewport meta tag (`width=device-width, initial-scale=1.0`) is already present in `index.html` — do not duplicate it.

- Must not break existing Vitest tests that check JSX rendering; no structural changes to component files unless strictly required by layout.

## Success criteria

- SC-1: On a 375px-wide viewport, no horizontal scrollbar appears on the Home, Report 1, or Report 3 pages.

- SC-2: On a 375px-wide viewport, the Report 2 and Report 3 tables are horizontally scrollable (overflow-x wrapping applied).

- SC-3: On a 375px-wide viewport, the header `h1` text does not overflow and is fully readable.

- SC-4: On a 375px-wide viewport, the landing page card and padding do not create horizontal overflow.

- SC-5: On a 768px-wide viewport (tablet), all five pages display without horizontal overflow and nav buttons remain on screen.

- SC-6: On a 1280px-wide viewport (desktop), all pages look visually identical to the pre-change state (no regression).

- SC-7: `npm run build` exits 0 after changes.

- SC-8: All existing Vitest tests pass without modification.

## Assumptions

- A1: End users access the hosted Netlify app primarily on Android (Chrome) and iOS (Safari) mobile browsers. Breakpoints at 600px and 900px cover the vast majority of these devices.
  - Risk if false: chosen breakpoints may not match the actual device distribution, requiring additional breakpoint tuning.

- A2: The global `box-sizing: border-box` reset defined in `react-app/src/index.css` is applied before `App.css` rules, ensuring padding and border values are included in element width calculations throughout the stylesheet.
  - Risk if false: padding reductions in media queries may not produce the expected content widths, causing layout inconsistencies.

- A3: No JSX structural changes are required to `RecordDetailModal.jsx` for the stated success criteria. The existing inline styles (`width: 90%`, `maxHeight: 80vh`, `padding: 24px 32px`, `dl { gridTemplateColumns: 'auto 1fr' }`) produce an acceptable layout on ≥ 320px viewports based on Spike 2 analysis.
  - Risk if false: the modal content overflows on very narrow screens, requiring a JSX class extraction and CSS targeting.

- A4: The `build-legacy/` directory is not updated as part of this request; it is the deprecated reference app and is out of scope.
  - Risk if false: none (legacy app is already superseded by the React app).

- A5: `npm run build` in `react-app/` completes successfully with the existing toolchain (Vite, Node.js, installed `node_modules`) before and after changes — no dependency updates are needed.
  - Risk if false: build failures unrelated to this change may block SC-7 verification.

## Plan

### Task 1: Add responsive media query rules to App.css
**Intent:** Append mobile (≤ 600px) and extended tablet (≤ 900px) media query blocks to `react-app/src/App.css`, covering all six identified gap areas.
**Inputs:** `react-app/src/App.css` (current state); success criteria SC-1 through SC-6.
**Outputs:** Updated `react-app/src/App.css` with new `@media (max-width: 600px)` block and extended `@media (max-width: 900px)` block.
**External Interfaces:** None (CSS-only change; no Supabase, no API calls).
**Environment & Configuration:** Local development environment; no secrets or env vars involved.
**Procedure:**
1. In `App.css`, extend the existing `@media (max-width: 900px)` block to also include: nav button padding reduction; report section padding reduction; results table horizontal scroll (`overflow-x: auto` on `.results-container`).
2. Add a new `@media (max-width: 600px)` block with: `body` padding reduction (20px → 12px); `header h1` font size reduction (2.5em → 1.6em); `header .subtitle` font size reduction; `.landing-page` padding reduction (50px → 20px); `.chart-bar-label` width reduction (200px → 100px) or flex stacking (answer to Q001 determines which); `nav-btn` font size and padding reduction.
3. Verify no rules in the new blocks conflict with existing rules at higher specificity.
**Done Criteria:** `App.css` contains both `@media` blocks; grep confirms presence of `overflow-x: auto` in `.results-container` context and a `chart-bar-label` override within a media query.
**Dependencies:** Q001 must be answered before step 2 (chart label approach).
**Risk Notes:** CSS specificity edge cases may require `!important` on one or two overrides if a rule already carries a class + element selector. Verify via build and visual check.

### Task 2: Run automated tests and build verification
**Intent:** Confirm that the CSS change does not break the Vitest test suite or the Vite production build.
**Inputs:** Updated `react-app/src/App.css`; existing `react-app/src/**/*.test.jsx`.
**Outputs:** Test run summary (all pass); `react-app/dist/assets/index-*.css` regenerated.
**External Interfaces:** Node.js / npm scripts.
**Environment & Configuration:** Local `react-app/` directory; `node_modules` must be installed.
**Procedure:**
1. Run `npm test -- --run` in `react-app/`; confirm exit 0 and zero failing tests.
2. Run `npm run build` in `react-app/`; confirm exit 0 and `dist/` updated.
3. Grep `dist/assets/index-*.css` for `@media (max-width:600px)` and `@media (max-width:900px)` to confirm build output includes the new rules.
**Done Criteria:** SC-7 (exit 0 build) and SC-8 (all Vitest tests pass) are satisfied.
**Dependencies:** Task 1 complete.
**Risk Notes:** Vitest tests are snapshot-free for CSS (they test component rendering, not styles). CSS changes should not affect existing test assertions.

### Task 3: Update documentation and context
**Intent:** Reflect the responsive CSS change in `.aib_memory/context.md` and note the UAT scenarios file.
**Inputs:** Updated `react-app/src/App.css`; current `.aib_memory/context.md`; `.aib_memory/UAT_scenarios.md`.
**Outputs:** Updated `.aib_memory/context.md` entry for the React app's CSS responsive state.
**External Interfaces:** None.
**Environment & Configuration:** No special environment required.
**Procedure:**
1. Add a line to the `> Updated by` header block in `context.md` referencing R-20260512-2138 and summarising the responsive CSS change.
2. Update the `## Requirements Summary → Non-Functional Requirements` section in `context.md` to note that `App.css` now includes mobile and tablet media queries.
3. Confirm `UAT_scenarios.md` exists at `.aib_memory/UAT_scenarios.md` (created during analysis).
**Done Criteria:** `context.md` contains a reference to R-20260512-2138; `UAT_scenarios.md` is present.
**Dependencies:** Task 1 complete.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update to reflect that `react-app/src/App.css` now includes mobile (≤ 600px) and tablet (≤ 900px) media query breakpoints covering all five pages.
- `.aib_memory/UAT_scenarios.md` (ref_id: N/A) — Created during analysis; contains manual browser viewport test scenarios UAT-01 through UAT-05.

## Questions & Decisions

**Q001**: How should the Report 1 bar chart label column (`chart-bar-label`) be handled on mobile (≤ 600px) viewports?
- [ ] Option A: Reduce the fixed width from 200px to approximately 100px, with `text-overflow: ellipsis` clipping long category names. Preserves the horizontal bar layout visually.
- [ ] Option B: Switch each bar row to `flex-direction: column` (stacked: label on top, bar below, value below bar). Fully readable for long Bulgarian category names, but changes the chart's visual character. *(recommended)*
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/App.css` | Modified | Add `@media (max-width: 600px)` and extend `@media (max-width: 900px)` blocks for responsive layout. |
| `react-app/src/components/RecordDetailModal.jsx` | Read-only dependency | Inline styles reviewed via Spike 2; no change required for this request's success criteria. |
| `react-app/index.html` | Read-only dependency | Viewport meta tag already present; no change required. |
| `react-app/package.json` | Read-only dependency | No new dependencies needed; verified. |
| `react-app/dist/assets/index-*.css` | Modified (build output) | Regenerated by `npm run build` after `App.css` changes; not edited manually. |
| `.aib_memory/context.md` | Modified | Update to reference R-20260512-2138 and summarise the responsive CSS change. |
| `.aib_memory/UAT_scenarios.md` | Created | Manual browser viewport test scenarios for this request. |

## Internal Review of Request and Product Docs

- OK: `request.md` § Goal — Clear, single-sentence intent with well-defined scope.
- OK: `request.md` § Success criteria — SC-1 through SC-8 are measurable and largely objective.
- Ambiguity: `request.md` § Scope — "Adjust the Report 1 chart bar label width to be flexible on narrow screens" does not specify whether the fix should be a reduced fixed width or a stacked layout. Two materially different visual outcomes arise from this ambiguity. Raised as Q001.
- OK: `context.md` — Correctly describes `App.css` as ported from the legacy app; no contradictions with the request scope.
- OK: `context.md` — Confirms no mobile responsiveness was added as part of any prior request (the sole media query at 900px was for the Query Log page added implicitly with the Query Log feature).
- Missing info: `request.md` § Constraints — Does not specify a minimum supported viewport width. The plan assumes 320px based on the lowest common denominator for modern mobile devices. No contradiction with stated constraints.
