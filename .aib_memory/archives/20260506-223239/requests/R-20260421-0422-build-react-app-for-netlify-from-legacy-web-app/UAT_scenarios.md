# UAT Scenarios — R-20260421-0422

Manual test scenarios requiring visual inspection or live Supabase connectivity. Execute with the React app running locally via `npm run dev` (or `npm run preview` after build) with a valid `.env` file containing real Supabase credentials.

---

## UAT-01 — Date Selector Populated from Supabase

**Precondition:** App is running; `.env` contains valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`; Supabase `dim_date` table has at least one row.

**Steps:**
1. Open the app in a browser (e.g., `http://localhost:5173`).
2. Observe the "Дата на данните:" selector in the header.

**Pass criteria:**
- The date selector is populated with at least one date value.
- Dates are displayed in `DD.MM.YYYY` format (e.g., `21.04.2026`).
- The newest date is pre-selected.
- Dates are listed in descending order (newest first).

**Fail criteria:**
- Selector shows only the placeholder or is empty.
- Dates appear in raw `YYYY-MM-DD` format.

---

## UAT-02 — Report 1: Average Price by Category (Bar Chart)

**Precondition:** UAT-01 passes; at least one city has data for the selected date.

**Steps:**
1. Click the "📈 Цени по категория" navigation button.
2. Select any city from the "Населено място" dropdown.
3. Observe the chart area below the dropdown.

**Pass criteria:**
- Horizontal bar chart renders with at least one bar.
- Each bar shows a category name on the left.
- Each bar's visual width is proportional to the average price relative to the maximum.
- Price value is shown on the right in the format `X.XX лв`.
- Bars are sorted by price in ascending order (cheapest category bar at the top).

**Fail criteria:**
- Chart area remains blank after city selection.
- "Няма данни за показване" displayed when city has data.
- Price values absent or unformatted.

---

## UAT-03 — Report 2: Products by City and Category (Table)

**Precondition:** UAT-01 passes; at least one city and one category have data for the selected date.

**Steps:**
1. Click the "📋 Продукти" navigation button.
2. Select a city from the "Населено място" dropdown.
3. Select a category from the "Категория" dropdown.
4. Observe the table in the results area.

**Pass criteria:**
- A table renders with the following 7 column headers (in Bulgarian): Наименование на продукта, Цена, Цена на дребно, Цена в промоция, Търговски обект, Верига, Дата.
- Each row shows a product with a numeric price in `X.XX лв` format.
- Rows are sorted by price ascending (cheapest product first).
- When only one dropdown is selected (not both), the table area shows no results (consistent with legacy behavior).

**Fail criteria:**
- Table absent after both dropdowns selected.
- Table shows wrong/missing columns.
- Prices unformatted or absent.

---

## UAT-04 — Report 3: Locations by Category (Table)

**Precondition:** UAT-01 passes; at least one category has data for the selected date.

**Steps:**
1. Click the "🗺️ Сравнение по места" navigation button.
2. Select a category from the "Категория" dropdown.
3. Observe the table in the results area.

**Pass criteria:**
- A table renders with the following 7 column headers: Населено място, Наименование на продукта, Цена, Цена на дребно, Цена в промоция, Търговски обект, Верига.
- At least one row from a different city than Report 2 results (confirms multi-city data).
- Rows sorted by price ascending.

**Fail criteria:**
- Table absent after category selected.
- Only one city shown regardless of category scope.

---

## UAT-05 — Visual Design Match with Legacy App

**Precondition:** App is running; at least the Home page loads.

**Steps:**
1. Open the app in a browser.
2. Compare visually with the legacy app's HTML/CSS reference.

**Pass criteria:**
- Header has a purple-blue gradient background (approximate color `#667eea` → `#764ba2`).
- Page title "📊 Анализатор на Цени" visible in white text in the header.
- Navigation buttons styled with semi-transparent backgrounds and white text; active page button has white background with purple text.
- Home page shows 3 feature cards on a light gradient background.
- CTA section at the bottom of the Home page has a purple gradient background with white text.
- Report sections use a white card with rounded corners and a box shadow.
- No unstyled HTML (no raw `<div>` elements with default browser styling visible).

**Fail criteria:**
- Plain white background instead of gradient.
- Nav buttons unstyled or default browser button style.
- Feature cards absent or unstyled.
