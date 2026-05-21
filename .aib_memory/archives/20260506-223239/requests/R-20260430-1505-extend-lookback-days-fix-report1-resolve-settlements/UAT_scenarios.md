# UAT Scenarios — R-20260430-1505

Manual acceptance test scenarios requiring visual inspection or end-to-end browser validation.
These scenarios cannot be expressed as automated assertions.

---

## UAT-01 — Report 1 loads without error on Netlify

**Precondition:** Netlify app has been redeployed via menu option 5 (Task 4).

**Steps:**
1. Open the Netlify deployment URL in an incognito/private browser window.
2. Navigate to the "Цени по категория" page (Report 1).
3. Select any city from the settlement dropdown.
4. Observe the chart area.

**Expected outcome:** The category price bar chart renders without any error message. No "Could not find the table 'public.fact_prices'" error or similar console error appears. The settlement dropdown is populated with city names.

**Fail condition:** Any error message visible on the page, or browser console shows a Supabase table-not-found error.

---

## UAT-02 — Date selector shows 3 dates on deployed Netlify app

**Precondition:** Netlify app has been redeployed via menu option 5 (Task 4).

**Steps:**
1. Open the Netlify deployment URL in an incognito/private browser window.
2. Inspect the "Дата на данните:" selector in the page header.
3. Click the selector to expand the option list.

**Expected outcome:** The selector contains exactly 3 options corresponding to dates D, D-1, and D-2 (displayed in Bulgarian DD.MM.YYYY format). The default selected date is the most recent (D).

**Fail condition:** Only 1 date option visible, or more than 3 dates visible, or selector shows "Няма налични дати".

---

## UAT-03 — Selecting D-1 shows different price data than D in Report 1

**Precondition:** UAT-01 and UAT-02 pass.

**Steps:**
1. Open the Netlify deployment URL in an incognito/private browser window.
2. Navigate to "Цени по категория" (Report 1).
3. Select a high-volume city (e.g., София or Пловдив) from the city dropdown.
4. Note the average prices for several categories at date D.
5. Change the date selector to D-1.
6. Select the same city again (settlement dropdown resets on date change).
7. Compare category average prices between D and D-1.

**Expected outcome:** Category average prices differ visibly between D and D-1 for at least a subset of categories (price fluctuation is expected across days). The chart updates and no error appears. The "Дата" label in Report 2 and Report 3 also reflects the selected D-1 date.

**Fail condition:** Prices are identical between D and D-1 for all categories (indicating that D prices are being used for both), or an error message appears.
