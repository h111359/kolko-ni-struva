# UAT Scenarios: R-20260506-2251 — Cross-filter dropdowns and record detail modal

## UAT-01: Bidirectional cross-filtering (SC1, SC2)

**Preconditions:** React app is running against Supabase with at least one date in `dim_date`; `load_supabase.py` has been run with the new RPC functions and `(date_key, category_key)` index provisioned.

**Steps:**
1. Navigate to Report 2 ("Отчет 2: Продукти по населено място и категория").
2. Select a date from the date selector.
3. Select a settlement from the "Населено място:" dropdown (e.g., "Sofia").
4. Observe the "Категория:" dropdown options.
5. Confirm that selecting each listed category produces at least one row in the results table (no empty-result set for any listed category).
6. Now select a category from the filtered list.
7. Observe the "Населено място:" dropdown options.
8. Confirm that selecting each listed settlement produces at least one row in the results table (no empty-result set for any listed settlement).

**Expected outcome:** Each dropdown is restricted to only valid options given the other's selection. No empty result sets occur when using the cross-filtered dropdowns in either direction.

---

## UAT-02: Date change resets dropdowns (SC3)

**Preconditions:** Report 2 is open; a settlement and a category are both selected; results are visible in the table.

**Steps:**
1. Note the currently selected settlement and category.
2. Change the date in the header date selector to a different date.
3. Observe both the "Населено място:" and "Категория:" dropdowns.

**Expected outcome:** Both dropdowns reset to "-- Изберете --". The settlements list reloads for the new date via `fetchSettlementsForDate`. The category dropdown returns to the full unfiltered list of all categories. No results are shown until a new selection is made.

---

## UAT-03: Row click opens detail modal (SC4)

**Preconditions:** Report 2 is showing results (settlement and category both selected).

**Steps:**
1. Click on any row in the results table.
2. Observe the modal dialog that appears.
3. Verify the modal displays: product name, category name, settlement name, store name, company name, effective price, retail price, promo price (if applicable), date, source file name, and file date.
4. Verify the source file name is human-readable (e.g., `lidl_20260506.zip`) and matches the expected ZIP archive for the retailer.

**Expected outcome:** Modal opens with all expected fields populated using Bulgarian labels matching the existing table style. The source file name correctly identifies the archive that submitted the record. No raw surrogate key integers are visible.

---

## UAT-04: Modal close preserves filter state (SC5)

**Preconditions:** Report 2 is showing results; a row detail modal is open.

**Steps:**
1. Note the currently selected settlement and category (dropdown values and results table state).
2. Close the modal using the close button (×).
3. Verify the modal is no longer visible.
4. Verify both dropdown selections are unchanged.
5. Verify the results table is unchanged (no re-fetch occurred).
6. Open the modal again by clicking another row.
7. Close the modal using the Escape key.
8. Repeat verifications from steps 3–5.

**Expected outcome:** Modal dismisses cleanly via both close button and Escape key. Both dropdown selectors retain their values. The results table remains as it was before the modal was opened. No data re-fetch is triggered by closing the modal.
