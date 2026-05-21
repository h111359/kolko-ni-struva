# UAT Scenarios — R-20260422-0902

## UAT-01: Visual date dropdown verification in browser

**Purpose:** Confirm the date dropdown only shows dates with actual fact data in Supabase.

**Preconditions:**
- The updated React app has been built (`npm run build` exited 0) and served locally or deployed to Netlify.
- At least one `load_supabase.py` run has been completed (at least one fact day in `fact_prices`).

**Steps:**
1. Open the React app in a browser.
2. Observe the "Дата на данните" (date) dropdown in the header.
3. Note all dates listed in the dropdown.
4. In the Supabase SQL editor, run: `SELECT DISTINCT d.date FROM fact_prices fp JOIN dim_date d ON d.date_key = fp.date_key ORDER BY d.date DESC;`
5. Compare the dates shown in step 3 with the SQL result from step 4.

**Expected outcome:** The dropdown lists exactly those dates returned by the SQL query — neither more nor fewer. Selecting each shown date returns non-empty report content.

**Failure sign:** Any date appears in the dropdown with no data in reports, or any date with fact data is missing from the dropdown.

---

## UAT-02: Settlement list completeness in Report 1

**Purpose:** Confirm that the city dropdown in Report 1 ("Цени по категория") lists every settlement that has fact data for the selected date.

**Preconditions:**
- React app running with the updated code.
- A date with data is selected.

**Steps:**
1. Open Report 1 by clicking "Цени по категория."
2. Note all cities listed in the "Населено място" dropdown.
3. In the Supabase SQL editor, run: `SELECT DISTINCT ds.settlement_name FROM fact_prices fp JOIN dim_store s ON s.store_key = fp.store_key JOIN dim_settlement ds ON ds.settlement_key = s.settlement_key WHERE fp.date_key = <selected_date_key> ORDER BY ds.settlement_name;`
4. Compare counts and names.

**Expected outcome:** Every settlement name from the SQL result appears in the dropdown. The count may differ slightly due to name sorting, but no settlement is absent.

**Failure sign:** A settlement name present in the SQL result is absent from the dropdown.
