## Goal

Fix two user-visible defects in the React Analytics App (react-app/):

1. **Date selector shows all dates**: The header date dropdown populates from `dim_date` in Supabase, which contains every date that the ETL has processed locally. Because `load_supabase.py` uploads one fact day per invocation, many `dim_date` entries have no corresponding rows in `fact_prices`. Users who select those "empty" dates see no results in any report. The dropdown must show only dates for which `fact_prices` data actually exists in Supabase.

2. **"Цени по категория" (Report 1) is incomplete**: The settlement dropdown does not list all cities that have data for the selected date, and the category bar chart may omit categories. Both gaps stem from Supabase query limitations that are not handled in the current client code.

## Background

The product's data layer in Supabase is populated incrementally: `load_supabase.py` upserts all dimension tables (including `dim_date` with all 63+ locally processed dates) but inserts only the newest fact day not yet present in `fact_prices`. As a result, `dim_date` in Supabase has far more rows than `fact_prices` has distinct `date_key` values. The React app fetches `dim_date` unconditionally, causing the date dropdown to list dates with no queryable fact data.

In `fetchSettlementsForDate`, the query fetches up to 10,000 rows from `fact_prices` (which contains ~1.1–1.5 M rows per date). With stores distributed across all fact rows, sampling only 10,000 rows covers a small fraction of all stores, and many settlements are missed. In `fetchReport1`, a single unpaginated query is issued against `fact_prices` with an `.in('store_key', storeKeys)` filter; Supabase's default 1,000-row cap silently truncates the result set, so categories represented beyond the first 1,000 rows do not appear in the chart.

## Scope

- Fix the date selector in `App.jsx` / `dataService.js` so it shows only dates with fact data in Supabase `fact_prices`.

- Fix `fetchSettlementsForDate` in `dataService.js` so it returns all settlements that have at least one fact row on the selected date, regardless of the total fact-row volume.

- Fix `fetchReport1` in `dataService.js` to paginate through all fact rows for the selected date and settlement, ensuring every category present in `fact_prices` appears in the chart.

- Update or extend `load_supabase.py` if the chosen fix requires new Supabase database objects (SQL functions, views, or summary tables).

- Run `npm run build` to verify the React app builds successfully after changes.

## Out of scope

- No changes to the ETL pipeline (`extract.py`, `transform.py`, `config_utils.py`).
- No changes to Report 2 (`Report2.jsx`, `fetchReport2`) or Report 3 (`Report3.jsx`, `fetchReport3`) unless the same root-cause fix is applicable and trivially reusable.
- No changes to the legacy web app (`build-legacy/web/`).
- No changes to Netlify deployment configuration or menu system.
- No addition of automated browser tests or visual regression tests.

## Constraints

- React app must remain client-only (no serverless functions); all queries go through `@supabase/supabase-js` v2.
- No credentials may be hardcoded; env vars use `VITE_` prefix.
- `npm run build` must exit 0 after changes.
- Any new Supabase database objects must be provisioned idempotently in `load_supabase.py` (CREATE OR REPLACE / IF NOT EXISTS).
- If Supabase RPC functions are added, they must use the `anon` role with the existing RLS policy set (public SELECT allowed).
- Python 3.9+ stdlib compatibility must be maintained in all Python files touched.
- Changes must not break existing `tests/` test suite.

## Success criteria

- SC-1: The date dropdown in the React app shows only dates for which at least one `fact_prices` row exists in Supabase; dates without fact data are absent from the dropdown.
- SC-2: The date dropdown contains the dates D, D-1, and D-2 (the last 3 fact-upload dates that the user confirmed exist) when those are the only dates with fact data.
- SC-3: The settlement dropdown in Report 1 ("Цени по категория") lists every city that has at least one store with data on the selected date.
- SC-4: The category bar chart in Report 1 includes all categories that have at least one price observation for the selected city and date; no category is silently omitted.
- SC-5: `npm run build` exits with code 0 after all code changes.
- SC-6: Existing Python tests (`tests/`) continue to pass without modification.

## Assumptions

- A1: The only source of truth for which dates have fact data in Supabase is the `fact_prices` table's distinct `date_key` column values.
  - Risk if false: If fact data spans multiple fact tables or is maintained elsewhere, the RPC function may under-report available dates.

- A2: `load_supabase.py` is re-run by the operator after implementing any new DDL (RPC functions / views). The React app will not break until that re-run occurs, because the fallback behaviour ("no dates shown") is better than "wrong dates shown."
  - Risk if false: If the app is redeployed before RPC functions exist in Supabase, `supabase.rpc()` calls will return an error, blocking dimension load. A defensive fallback in `fetchDimensions` is required.

- A3: The Supabase anon role has `EXECUTE` granted on public schema functions by default (Supabase creates functions in `public` and grants `anon` execute by default when using `CREATE OR REPLACE FUNCTION` without explicit revoke).
  - Risk if false: RPC calls return 403. Fix: add `GRANT EXECUTE ON FUNCTION get_available_dates() TO anon;` to the provisioning DDL.

- A4: The `.in('store_key', storeKeys)` URL stays under the PostgREST 8 KB URI limit for all currently existing settlements (max ~200 stores per settlement at current data volume).
  - Risk if false: Queries for large metro-area settlements silently fail. Mitigation: add URL-length guard or migrate to RPC for `fetchReport1` as well.

- A5: `dim_settlement` column names in Supabase match the current CSV (`settlement_key, ekatte, settlement_name`). The `dataService.js` `fetchDimensions` function fetches `settlement_key, settlement_name, ekatte` — this is consistent with the CSV schema.
  - Risk if false: Settlement map building would fail. Checked from `dim_settlement.csv` context — consistent.

## Plan

### Task 1: Create Supabase RPC functions in load_supabase.py
**Intent:** Provision two idempotent SQL functions in Supabase that return distinct available dates and per-date settlements, enabling the React app to filter without transferring all fact rows to the client.
**Inputs:** `src/load_supabase.py`; active Supabase PostgreSQL connection via `DATABASE_URL`.
**Outputs:** Two new SQL functions in Supabase (`get_available_dates()`, `get_settlements_for_date(bigint)`); `src/load_supabase.py` updated to include their `CREATE OR REPLACE FUNCTION` DDL.
**External Interfaces:** Supabase PostgreSQL (psycopg2 connection).
**Environment & Configuration:** `DATABASE_URL` in `.env`; psycopg2 must be installed. Functions target the `public` schema.
**Procedure:**
1. Add `_CREATE_RPC_FUNCTIONS` DDL string to `load_supabase.py` with `CREATE OR REPLACE FUNCTION get_available_dates()` returning `SETOF int` (`SELECT DISTINCT date_key FROM fact_prices ORDER BY date_key DESC`) and `get_settlements_for_date(p_date_key bigint)` returning `SETOF int` (`SELECT DISTINCT s.settlement_key FROM fact_prices fp JOIN dim_store s ON s.store_key = fp.store_key WHERE fp.date_key = p_date_key`).
2. Add `GRANT EXECUTE ON FUNCTION get_available_dates() TO anon; GRANT EXECUTE ON FUNCTION get_settlements_for_date(bigint) TO anon;` to the DDL.
3. Call `cur.execute(_CREATE_RPC_FUNCTIONS); conn.commit()` inside `create_tables()` after existing DDL.
4. Run `python src/load_supabase.py` to provision.
**Done Criteria:** `load_supabase.py` runs without error; functions appear in Supabase under `Database → Functions`; `SELECT get_available_dates()` in Supabase SQL editor returns one row per uploaded fact date.
**Dependencies:** None.
**Risk Notes:** If `anon` role EXECUTE grant is denied, add explicit grant or use `SECURITY DEFINER` on the function.

### Task 2: Update fetchDimensions to use get_available_dates RPC
**Intent:** Replace the unconditional `dim_date` full load with a two-step approach: call `get_available_dates()` RPC to get fact-present `date_key` values, then filter `dim_date` results to those keys.
**Inputs:** `react-app/src/lib/dataService.js`; Supabase `get_available_dates()` function from Task 1.
**Outputs:** Updated `dataService.js`; `fetchDimensions()` returns only fact-present dates.
**External Interfaces:** Supabase REST (PostgREST) via `supabase.rpc('get_available_dates')`.
**Environment & Configuration:** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` in `react-app/.env`.
**Procedure:**
1. In `fetchDimensions()`, add a parallel call: `supabase.rpc('get_available_dates')` alongside the existing `dim_date` fetch.
2. On success, build a `Set` of available `date_key` integers from the RPC result.
3. Filter `datesRes.data` to only include rows whose `date_key` is in the set, maintaining descending order.
4. If the RPC call errors (function not yet provisioned), fall back to using all dates from `dim_date` and log a console warning.
**Done Criteria:** `fetchDimensions()` returns a `dates` array containing only fact-present dates; the date dropdown in the app shows only those dates; selecting any shown date returns non-empty report data.
**Dependencies:** Task 1.
**Risk Notes:** The fallback (use all dim_date rows if RPC absent) ensures backward compatibility if the operator hasn't re-run `load_supabase.py` yet.

### Task 3: Update fetchSettlementsForDate to use get_settlements_for_date RPC
**Intent:** Replace the `.limit(10000)` fact-row scan with a server-side DISTINCT query via RPC, returning all settlement_keys for the selected date in one efficient round trip.
**Inputs:** `react-app/src/lib/dataService.js`; Supabase `get_settlements_for_date(bigint)` function from Task 1.
**Outputs:** Updated `dataService.js`; `fetchSettlementsForDate()` returns all settlements with fact data.
**External Interfaces:** Supabase REST via `supabase.rpc('get_settlements_for_date', { p_date_key: dateKey })`.
**Environment & Configuration:** Same as Task 2.
**Procedure:**
1. Replace the `fact_prices` query body in `fetchSettlementsForDate` with: `supabase.rpc('get_settlements_for_date', { p_date_key: dateKey })`.
2. The RPC returns an array of `{ get_settlements_for_date: settlement_key }` objects; map to a `Set<number>`.
3. Resolve settlement names from the `dims.settlements` map as before; sort alphabetically.
4. Add a fallback: if the RPC errors, log a console warning and return all settlements from `dims.settlements` (show all cities).
**Done Criteria:** Calling `fetchSettlementsForDate` for the latest date returns the same count of settlements as `SELECT DISTINCT settlement_key FROM fact_prices fp JOIN dim_store s ON s.store_key = fp.store_key WHERE fp.date_key = X` in Supabase SQL editor.
**Dependencies:** Task 1.
**Risk Notes:** RPC return shape may vary; confirm data shape in Supabase SQL editor before finalizing the mapping.

### Task 4: Add pagination to fetchReport1
**Intent:** Replace the single un-paginated `.in('store_key', storeKeys)` query in `fetchReport1` with a paginated loop that retrieves all fact rows for the selected date and settlement, ensuring every category is represented in the bar chart.
**Inputs:** `react-app/src/lib/dataService.js`.
**Outputs:** Updated `fetchReport1()` with while-loop pagination.
**External Interfaces:** Supabase REST via `.range()`.
**Environment & Configuration:** Same as Task 2.
**Procedure:**
1. Refactor the single `supabase.from('fact_prices').select(...).eq(...).in(...)` call into a `while (!done)` loop mirroring `fetchAllRows`, using `.range(from, to)` with `PAGE_SIZE = 1000`.
2. Accumulate all pages into `allRows`; check `data.length < PAGE_SIZE` to detect the final page.
3. Perform client-side category aggregation on `allRows` as before.
4. Verify no change to the downstream `results.sort(...)` logic.
**Done Criteria:** For a large metropolitan settlement (e.g., the settlement with the most stores), the returned `results` array contains the same number of distinct categories as a direct Supabase SQL query: `SELECT DISTINCT category_key FROM fact_prices WHERE store_key IN (...) AND date_key = X`.
**Dependencies:** None (independent of RPC Tasks).
**Risk Notes:** Paginating with a large `.in()` list works for current store counts but will degrade at scale; noted in Assumptions A4.

### Task 5: Run automated tests and build
**Intent:** Verify that Python tests and the React build continue to pass after all code changes.
**Inputs:** `tests/`, `react-app/package.json`, modified source files.
**Outputs:** Test pass report; `react-app/dist/` build artifact.
**External Interfaces:** None.
**Environment & Configuration:** Python venv activated; Node.js 18+ available.
**Procedure:**
1. Run `python -m pytest tests/ -v` from the workspace root; verify exit 0.
2. Run `cd react-app && npm run build`; verify exit 0 and `dist/` produced.
**Done Criteria:** All tests pass; `npm run build` exits 0. (SC-5, SC-6)
**Dependencies:** Tasks 2, 3, 4.
**Risk Notes:** None expected; changes are confined to `dataService.js` and `load_supabase.py`.

### Task 6: Update context.md and references
**Intent:** Update `context.md` to reflect the new RPC functions, the corrected `fetchDimensions` and `fetchSettlementsForDate` behaviour, and note the pagination fix in `fetchReport1`. Ensure references.md remains consistent.
**Inputs:** `.aib_memory/context.md`, `.aib_memory/references.md`.
**Outputs:** Updated `context.md` (Technical Design, Data Architecture, Key Algorithms).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Update `context.md` — `## Technical Design → Module Breakdown → react-app/src/lib/dataService.js`: note the RPC calls for dates and settlements, and the paginated `fetchReport1`.
2. Update `context.md` — `## Technical Design → Module Breakdown → src/load_supabase.py`: note the two new SQL functions provisioned.
3. Update the Key Integration Points section to document the new `get_available_dates` and `get_settlements_for_date` RPC entry points.
4. Verify `references.md` requires no changes (no new reference files).
**Done Criteria:** `context.md` correctly describes post-implementation behaviour; no outdated references to `.limit(10000)` or unconditional `dim_date` full load.
**Dependencies:** Tasks 1–4.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update to reflect new Supabase RPC functions (`get_available_dates`, `get_settlements_for_date`), corrected `fetchDimensions` behaviour (date filtering), corrected `fetchSettlementsForDate` (RPC-based distinct), and paginated `fetchReport1`. Key Integration Points and Module Breakdown sections affected.

## Questions & Decisions

**Q001**: What strategy should be used to retrieve distinct available dates from `fact_prices` and distinct settlements per date, given that supabase-js v2 does not expose SELECT DISTINCT natively?
- [x] Option A: Create two Supabase SQL functions (`get_available_dates()` and `get_settlements_for_date(bigint)`) via `CREATE OR REPLACE FUNCTION` in `load_supabase.py`, and call them via `supabase.rpc()` in `dataService.js`. *(recommended)*
- [ ] Option B: Show all dates from `dim_date` always, but add a "no data" message when a selected date returns empty results (no query change; UX workaround only).
- [ ] Option C: For dates — paginate exhaustively through `fact_prices` client-side to deduplicate `date_key`; for settlements — do the same. (Correct but extremely slow: ~1100–1500 API calls per page load.)
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `react-app/src/lib/dataService.js` | Modified | Fix `fetchDimensions` (date filtering), `fetchSettlementsForDate` (RPC), `fetchReport1` (pagination). |
| `src/load_supabase.py` | Modified | Add `_CREATE_RPC_FUNCTIONS` DDL with `get_available_dates()` and `get_settlements_for_date(bigint)` SQL functions. |
| `.aib_memory/context.md` | Modified | Update tech design sections to reflect new RPC functions and corrected query behaviour. |
| `react-app/src/components/Report1.jsx` | Read-only dependency | Consumes `fetchSettlementsForDate` and `fetchReport1`; no direct change required. |
| `react-app/src/App.jsx` | Read-only dependency | Consumes `fetchDimensions`; no direct change required. |
| `.aib_memory/requests/R-20260422-0902-fix-date-filter-and-category-prices-report/UAT_scenarios.md` | Created | Manual acceptance test scenarios for UAT-01 and UAT-02. |

## Internal Review of Request and Product Docs

- OK: `request.md` — All six mandatory sections (Goal through Success criteria) are present, non-empty, and internally consistent.
- OK: `context.md` (REF-0001) — Accurately describes the current `fetchDimensions`, `fetchSettlementsForDate`, and `fetchReport1` behaviour as of 2026-04-21. The defects described in this request are visible in the documented logic (`.limit(10000)`, absent pagination).
- Ambiguity: `request.md § Goal` — "3 dates (day, day-1 and day-2)" is mentioned by the user in `input.md` but could mean "show exactly 3 dates" or "approximately 3 dates are expected given the current sync state." Resolved in SC-2 as: the dropdown shows all dates with fact data, which the user expects to be D, D-1, and D-2 at the current load state. This interpretation is recorded in Assumption A1.
- Missing info: `context.md` does not document the Supabase default row cap (1 000 rows) or the PostgREST URI length limit as known constraints. These are relevant to future query design and should be added post-implementation.
- Cross-ref issue: `context.md § Requirements Summary — Item 7` states "Date selector in header from `dim_date`" without noting the data-completeness constraint. Post-implementation, this should read "Date selector filtered to dates with fact data in `fact_prices`."

