# UAT Scenarios — R-20260518-1251: Remove currency notation from price displays

## UAT-01 — Visual verification of price display across all app pages

**Type:** Manual visual inspection  
**Trigger:** After implementation is deployed to Netlify (or previewed locally via `npm run dev`).

**Precondition:** The React app is running and data is loaded from Supabase for at least one available date.

**Steps:**

1. Open Report 1. Select any settlement from the dropdown. Observe the bar chart labels.
   - **Expected:** Each bar shows a plain numeric value with two decimal places (e.g., `3.50`). No `лв` suffix appears after any price value.

2. Open Report 2. Select any settlement and category combination that returns results.
   - **Expected:** The `Цена`, `Цена на дребно`, and `Цена в промоция` table columns show bare numeric values with two decimal places. No `лв` appears in any price cell.
   - Click any row to open the `RecordDetailModal`. Verify that calculated price, retail price, and promotional price fields show bare numeric values. No `лв` suffix.

3. Open Report 3. Select any category that returns results.
   - **Expected:** Column headers read `Цена`, `Цена на дребно`, `Цена в промоция` (no `(лв)` in parentheses). Price cells show bare numeric values. No `лв` anywhere in the table.

4. Open the Файлове page. Select a date and click any file row to open the `FileRowsPanel`.
   - **Expected:** Column headers read `Цена`, `Промо цена`, `Ефективна цена`, `Цена <date>`, `Промо <date>`, etc. — all without `(лв)`. Price cells show bare numeric values.
   - Click any row to open `FileRowDetailModal`. Verify that all price fields (Ефективна цена, Цена на дребно, Цена в промоция, lookback columns) display bare numeric values with no `лв` suffix.

**Pass criteria:** No occurrence of `лв` or `(лв)` is visible anywhere in the UI across all four price-bearing views. All numeric values retain two decimal places.
