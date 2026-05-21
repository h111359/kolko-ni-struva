# UAT Scenarios — R-20260513-2123

## UAT-01: Visual and responsive validation of the new Files page

**Purpose:** Validate that the new "Файлове" page renders correctly across viewport sizes and that date-switching updates the displayed files without stale data.

**Preconditions:**
- The React app is deployed or running locally with Supabase connected.
- At least one date with data is available in the date selector.
- `dim_file` has at least one row for the selected date's resolved `zip_date`.

**Steps:**
1. Open the app in a desktop browser (≥ 900px viewport width).
2. Click the "Файлове" (or equivalent) nav button.
3. Verify the Files page is shown with a table of source files for the default selected date.
4. Verify each row shows: file name, formatted date (DD.MM.YYYY), and (if implemented) record count.
5. Select a different date from the date selector.
6. Verify the table updates to show files for the newly selected date; no stale rows from the previous date remain.
7. Resize the viewport to ≤ 600px (mobile).
8. Verify the table is horizontally scrollable (no overflow clipping content).
9. Verify all interactive elements (date selector, nav buttons) meet the 44px touch-target minimum.

**Expected outcomes:**
- The Files page displays correctly at all viewport sizes.
- Date switching updates the file list without stale content.
- No horizontal overflow occurs at mobile widths.
- The "Лог на заявки" nav button is absent from the nav bar.

**Pass/Fail criteria:** All steps produce expected outcomes with no visual defects or JavaScript console errors.
