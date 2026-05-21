# UAT Scenarios — R-20260426-2150

## UAT-01: React App renders error state when credentials are missing

**Type:** Manual end-to-end inspection

**Precondition:** The root `.env` file does NOT contain `VITE_SUPABASE_URL` and/or `VITE_SUPABASE_ANON_KEY` (or they are empty).

**Steps:**
1. Remove or blank the VITE_ variables in the root `.env`.
2. Select option 6 from the menu.
3. Observe the build output in the terminal.
4. Observe the browser when it opens.

**Expected outcome:** The menu prints an actionable error message (mentioning the missing variable names and providing an example) and exits without running the build. The browser does not open at all. If the build IS attempted (e.g., by bypassing the check), the browser shows the Bulgarian credentials-error message ("Липсват Supabase credentials...") and no data is fetched.

---

## UAT-02: End-to-end option 6 local preview with valid credentials

**Type:** Manual end-to-end validation

**Precondition:** Root `.env` contains valid `VITE_SUPABASE_URL` and a correct **anon** `VITE_SUPABASE_ANON_KEY` (confirm by decoding the JWT payload and verifying `"role":"anon"`). Supabase is accessible; star-schema tables are populated.

**Steps:**
1. Select option 6 from the menu.
2. Wait for the build to complete (terminal shows "Building React app for local preview...").
3. Observe when the browser opens relative to when the preview server starts.
4. Once the browser is open, observe the date selector in the header.
5. Select a date and navigate to Report 1.
6. Select a settlement and observe the price chart.

**Expected outcome:**
- The browser opens ONLY after the Vite preview server is ready to serve requests (no "connection refused" error in the browser).
- The date selector populates with at least one date; no "Зареждане..." state persists.
- Report 1 renders a bar chart with price data for the selected date and settlement.
- No error messages are shown in the UI.
- Browser developer console shows zero errors.
