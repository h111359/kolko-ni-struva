# UAT Scenarios — R-20260425-2313

## UAT-01: Browser console zero errors under normal operating conditions

**Type:** Manual browser validation

**Preconditions:**
- Root `.env` file contains valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.
- `src/load_supabase.py` has been run at least once after 2026-04-22 (to provision `get_available_dates` and `get_settlements_for_date` RPC functions).
- Node.js and npm are installed.

**Procedure:**
1. Run menu option 6 (or `cd react-app && npm run build && npm run preview`) to start local preview.
2. Open `http://localhost:4173` in a browser.
3. Open the browser developer tools (F12 → Console tab).
4. Wait for the app to fully load (date selector shows dates, not "Зареждане...").
5. Navigate to Report 1 and select a settlement from the dropdown. Wait for chart to render.
6. Navigate to Report 2, select a settlement and a category. Wait for table to render.
7. Navigate to Report 3, select a category. Wait for table to render.
8. Return to Home page.
9. Inspect the Console tab throughout all steps.

**Expected outcome:**
- Zero red `console.error` messages at any step.
- Zero yellow `console.warn` messages at any step.
- No unhandled promise rejection notices.
- No React-generated warnings (e.g., `Warning: Each child in a list should have a unique "key" prop`).
- Data is visible in all three reports when filters are selected.

**Pass / Fail criteria:**
- PASS: Console tab shows only network request log entries; zero error, warn, or unhandled-rejection messages.
- FAIL: Any error, warning, or unhandled rejection appears in the console under normal operating conditions.
