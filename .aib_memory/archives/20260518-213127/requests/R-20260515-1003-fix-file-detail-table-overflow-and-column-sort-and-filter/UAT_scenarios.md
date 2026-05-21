# UAT Scenarios — R-20260515-1003

## UAT-01 — Visual overflow containment

**Objective:** Verify that the 12-column detail table in `FileRowsPanel` no longer extends beyond the parent `.report-section` card boundary.

**Prerequisites:**
- The React app is running locally (`npm run preview` or `npm run dev` from `react-app/`).
- At least one date with files is available in Supabase.

**Steps:**
1. Open the app in a browser and navigate to the "Файлове" page.
2. Select a date that has files available.
3. Click any file row to open the `FileRowsPanel` drill-down.
4. Observe the detail table at 1440px viewport width.
5. Narrow the browser window to 900px, then to 600px.

**Expected outcome:**
- At all viewport widths, the table does NOT extend visually beyond the parent white card container.
- When the table is wider than the viewport (≤ approx 1200px), a horizontal scrollbar appears inside the card.
- The card's border-radius and box-shadow remain fully visible on all four sides.
- No horizontal page-level scrollbar appears (the table scrolls within the card, not the page).

---

## UAT-02 — Sort and filter usability in FileRowsPanel

**Objective:** Verify that column sort and filter controls are visible, functional, and accessible.

**Prerequisites:** Same as UAT-01; a file with at least 5 rows must be available.

**Steps:**
1. Open a file's detail view in `FileRowsPanel` (as in UAT-01).
2. Click the "Продукт" column header.
3. Observe row order changes to ascending alphabetical order and a sort indicator (e.g., ↑) appears.
4. Click the "Продукт" header again.
5. Observe row order changes to descending order and the indicator changes (e.g., ↓).
6. Click the "Продукт" header a third time.
7. Observe rows return to original fetch order and the indicator is removed.
8. Locate the filter input below the "Продукт" column header.
9. Type part of a product name that appears in at least one but not all visible rows.
10. Observe that only rows containing the typed text in the product name column are shown.
11. Clear the filter input.
12. Observe all rows are restored.
13. Navigate to page 2 (if available) and verify sort/filter still apply correctly.
14. Tab through the column headers and filter inputs to verify keyboard accessibility.

**Expected outcome:**
- Sort indicators are visible and change correctly with each click.
- Filter inputs are present below each column header.
- Typing in a filter hides non-matching rows within the current page.
- Clearing the filter restores all rows.
- Changing the page (pagination) works normally when filters/sort are active.
- All controls are reachable and operable via keyboard Tab + Enter/Space.
