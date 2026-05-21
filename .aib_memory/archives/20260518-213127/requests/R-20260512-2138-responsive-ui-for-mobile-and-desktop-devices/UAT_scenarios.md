# UAT Scenarios — R-20260512-2138: Responsive UI for mobile and desktop devices

These scenarios require visual inspection in a browser at the specified viewport widths. Use browser DevTools device emulation or a real device.

---

## UAT-01 — Home page at 375px (iPhone SE)

**Precondition:** React app is running locally (`npm run dev`) or deployed on Netlify. Navigate to the Home (Начало) page.

**Viewport:** 375px wide.

**Steps:**
1. Open DevTools, set viewport to 375px × 812px.
2. Navigate to the Home page.
3. Scroll the full page vertically.

**Expected outcome:**
- No horizontal scrollbar appears at any scroll position.
- The header `h1` ("Анализатор на Цени") is fully visible without overflow.
- The landing page content is fully readable; paddings are reasonable (not squeezing content).
- Feature cards stack to a single column.

---

## UAT-02 — Report 1 bar chart at 375px

**Precondition:** Dimensions and settlements are loaded. Select a settlement in the Report 1 dropdown.

**Viewport:** 375px wide.

**Steps:**
1. Navigate to Report 1.
2. Select a settlement from the dropdown.
3. Observe the bar chart once it renders.

**Expected outcome:**
- No horizontal scrollbar appears on the outer page.
- Each chart bar row is fully contained within the visible width.
- Category labels are readable (may wrap or be truncated, but must not cause overflow).
- The price value is visible to the right of the bar.

---

## UAT-03 — Report 2 table at 375px with horizontal scroll

**Precondition:** Dimensions are loaded. Select a settlement and category in Report 2.

**Viewport:** 375px wide.

**Steps:**
1. Navigate to Report 2.
2. Select a settlement and a category.
3. Once the table renders, swipe/scroll the table horizontally.

**Expected outcome:**
- The outer page does not scroll horizontally.
- The results table is independently horizontally scrollable within its container.
- All 7 columns are reachable via horizontal scroll within the table area.
- Row click still opens the RecordDetailModal correctly.

---

## UAT-04 — RecordDetailModal at 375px

**Precondition:** Report 2 table is showing rows.

**Viewport:** 375px wide.

**Steps:**
1. Click a row in the Report 2 table.
2. Observe the modal dialog.

**Expected outcome:**
- The modal appears centred in the viewport.
- The modal does not exceed the viewport width.
- All field labels and values are readable without overflow.
- The close button is visible and tappable.
- Pressing Escape closes the modal.

---

## UAT-05 — Desktop regression at 1280px

**Precondition:** React app loaded in a desktop browser.

**Viewport:** 1280px wide.

**Steps:**
1. Set viewport to 1280px × 900px.
2. Navigate through all five pages: Home, Report 1, Report 2, Report 3, Query Log.
3. Compare visually with the pre-change appearance (screenshots or memory).

**Expected outcome:**
- All pages display exactly as before (no layout shifts, no visual regressions from added media queries).
- Bar chart labels are at their original 200px width.
- Landing page padding is at the original 50px.
- Header `h1` is at the original `2.5em` size.
