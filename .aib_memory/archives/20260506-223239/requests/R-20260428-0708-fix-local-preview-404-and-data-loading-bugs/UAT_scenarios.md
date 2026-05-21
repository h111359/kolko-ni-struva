# UAT Scenarios: R-20260428-0708 — Fix local preview 404 and data loading bugs

## UAT-01: End-to-end local preview with real Supabase data

**Type:** Manual — requires a live Supabase connection and populated database.

**Prerequisites:**
- Root `.env` contains valid `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (anon key, not service_role).
- `load_supabase.py` has been run and provisioned at least one day of fact data to Supabase.
- Browser devtools are open to the Console tab before launching.

**Steps:**
1. From the project root, run `./menu.sh` (Linux) and choose option 6 (local preview).
2. The terminal should print "Building React app for local preview..." followed by "Starting preview server — local URL: http://localhost:4173".
3. The browser should open automatically to `http://localhost:4173`.

**Expected outcomes:**
- The browser console contains NO "Failed to load resource: the server responded with a status of 404 (Not Found)" error for the favicon.
- The date selector in the app header is populated with at least one date.
- Selecting a date and navigating to Report 1 shows the city selector populated with at least one settlement.
- Selecting a city shows a bar chart with at least one category bar.
- The browser console may show PostgREST `console.warn` messages only if the RPC functions are not provisioned (informational, not a failure).

**Pass criteria:** No favicon 404 in console; date dropdown is non-empty; Report 1 renders data for any selected date and city.

**Fail criteria:** Any of — favicon 404 present; date dropdown is empty with no message; date dropdown shows "Няма налични дати" when fact data IS present in Supabase; Report 1 shows no bars after a city is selected.
