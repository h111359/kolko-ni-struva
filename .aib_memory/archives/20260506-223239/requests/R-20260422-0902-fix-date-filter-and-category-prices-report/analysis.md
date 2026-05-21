# Analysis: R-20260422-0902 — Fix date filter and category prices report

## Executive Summary

- **Request ID:** R-20260422-0902
- **Title:** Fix date filter and category prices report

- **Purpose:** Two separate but related defects degrade the usability of the React analytics app. The date dropdown lists dates with no queryable fact data, and Report 1 ("Цени по категория") silently omits cities and categories due to unbounded Supabase query limitations.

- **Root cause — date filter:** `fetchDimensions()` loads all rows from `dim_date` in Supabase (63+), but `load_supabase.py` inserts only the newest local fact day into `fact_prices` per run. Dates present in `dim_date` but absent from `fact_prices` produce empty report pages when selected.

- **Root cause — settlement truncation:** `fetchSettlementsForDate` issues a `.limit(10000)` query against a table with ~1.1–1.5 M rows per date. At best, the first 10k rows cover ~37 of 4,824 total stores; most settlements are not represented.

- **Root cause — category truncation:** `fetchReport1` runs a single unpaginated `.in('store_key', …)` query. Supabase's default 1 000-row cap silently truncates rows, so categories whose products appear beyond row 1 000 are absent from the bar chart.

- **Fix strategy:** Server-side distinct queries via Supabase RPC functions (provisioned idempotently in `load_supabase.py`) for dates and settlements; client-side pagination for `fetchReport1`. An open question (Q001) addresses the choice of implementation strategy.

- **`request.md` sections updated during this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`.

---

## Domain Knowledge Essentials

**Retail price dimension (dim_date):** A calendar-grain table created locally by `transform.py` for every ZIP archive processed. After cloud sync, `dim_date` in Supabase reflects all locally processed dates, regardless of whether the matching fact rows have been uploaded.

**Fact table (fact_prices):** Row-level price observations partitioned by ETL date. Each `load_supabase.py` run inserts one new date partition. After N sync runs, `fact_prices` contains at most N distinct `date_key` values out of the 63+ in `dim_date`.

**Lookback fact table (fact_prices_lookback):** A derived single-date snapshot containing the latest processed day (D) enriched with D-1 and D-2 price columns. The table is always fully replaced on each sync run and always reflects exactly one `date_key`. It is not used by any React report query.

**Settlement / city:** Identified by `ekatte_code` from the Bulgarian EKATTE administrative registry. In the app, a "city" is one row in `dim_settlement` linked to one or more `dim_store` rows. The settlement dropdown in Report 1 is dynamically filtered to cities that have fact data for the chosen date.

**Impacted personas:**
- End users (public browser users): experience the empty-date and missing-city/category defects.
- Data engineers: responsible for running `load_supabase.py` and rebuilding the React app.

---

## Technical Knowledge & Terms

**PostgREST / supabase-js v2:** The Supabase client communicates with PostgreSQL via PostgREST, a REST interface. `supabase-js` wraps PostgREST calls. PostgREST's default row limit is 1 000 (configurable server-side but not by the client directly). Group-by, DISTINCT, and window functions are not exposed by native `supabase-js` chainable methods — they require Supabase RPC (stored functions) or manual pagination.

**Supabase RPC:** Calling a PostgreSQL function via `supabase.rpc('function_name', params)`. Functions are created in the Supabase project's `public` schema. To be callable with the anon key, they must have `SECURITY DEFINER` semantics or the `anon` role must have `EXECUTE` granted.

**Supabase anon role + RLS:** Row-level security must allow `SELECT` on targeted tables. The project already relies on public SELECT RLS. New RPC functions accessing `fact_prices` must be configured so the anon role can invoke them.

**Pagination via `.range()`:** `supabase-js` exposes `PostgREST`'s `Range` header through `.range(from, to)`. This is how `fetchAllRows` currently pages through large dimension tables. Applying the same pattern to `fetchReport1` is the fix for category truncation.

**`.in()` URL length risk:** `supabase-js` encodes `.in('store_key', storeKeys)` into a PostgREST query-string parameter like `store_key=in.(1,2,3,…)`. With hundreds of store keys, the URL may approach or exceed the default 8 KB PostgREST URI limit, silently returning an error or empty result instead of truncating rows.

**Files read for this analysis:**
- `react-app/src/App.jsx`
- `react-app/src/lib/dataService.js`
- `react-app/src/lib/supabase.js`
- `react-app/src/components/Report1.jsx`
- `react-app/src/components/Report2.jsx`
- `src/load_supabase.py`
- `data/schema/dim_date.csv` (header + first 20 rows)
- `.aib_memory/context.md`
- `.aib_brain/Concepts.md`
- `.aib_memory/references.md`

---

## Research Results

**Pattern: incremental fact loading vs. full dimension sync.** The architecture syncs dimensions fully (all 63+ dates) but facts incrementally (one day per run). This is a standard data-warehouse ingest pattern, but it requires the presentation layer to derive available fact dates from the fact table itself, not from the dimension. The current code derives available dates from the dimension, which is the common mistake.

**Pattern: unbounded `.in()` filters in REST APIs.** A well-known PostgREST/Supabase limitation: using `.in()` with a large array generates a URL parameter whose length grows linearly with the array size. Supabase's default PostgREST config limits URI size to 8 KB; at ~8 bytes per integer key plus separators, ~500 store_keys pushes the limit. The current code does not guard against this. Observed store count is 4,824; a settlement with, say, 200 stores would generate a URL well under the limit, but larger metro areas (Sofia) with hundreds of stores could approach or exceed it.

**Pattern: silent row truncation in REST paginated APIs.** When a Supabase query returns exactly 1000 rows (the PostgREST default max), no error is raised and no `has_more` indicator is returned by `supabase-js`. The caller must detect the page boundary itself (check `data.length === PAGE_SIZE` and issue the next range). `fetchAllRows` implements this correctly; `fetchReport1` does not.

---

## External Benchmarking

**React + Supabase pagination best practices (Supabase official docs and community patterns):**
- Supabase documentation explicitly recommends using `.range()` loops for large tables and provides the same `PAGE_SIZE` boundary-check pattern used in `fetchAllRows`. The omission in `fetchReport1` is a deviation from the project's own established pattern.
- Takeaway: Apply `fetchAllRows`-style pagination to `fetchReport1`. Applicable directly; no new dependencies.

**PostgreSQL DISTINCT via server-side function (industry standard):**
- In any REST-over-SQL architecture where the client cannot issue SELECT DISTINCT natively, the standard practice is to expose a thin SQL function (`RETURNS TABLE`) that executes the DISTINCT internally and is called via RPC. This is the recommended Supabase pattern documented in the Supabase "Database Functions" guide.
- Applicable for both `get_available_dates()` and `get_settlements_for_date(date_key)`.
- Takeaway: Create two idempotent SQL functions in `load_supabase.py`; call via `supabase.rpc()`. This is the industry-standard approach and avoids any client-side DISTINCT workaround.

**Summary table (materialized micro-dimension) pattern:**
- Some architectures maintain a `fact_snapshot` or `fact_summary` table that records which combinations of key dimensions (e.g., date × settlement) have data. Amazon Redshift and Google BigQuery recommend this for dashboard filter widgets to avoid expensive DISTINCT scans on large fact tables. For this scale (~1.1–1.5 M rows/day), an RPC with a DISTINCT scan over `fact_prices` will be fast (milliseconds on a properly indexed integer column). A summary table adds ETL complexity for little gain at this scale.
- Takeaway: An RPC is sufficient at current data volume; a summary table is premature optimization. Reject for this request.

---

## Minimal Spikes and Experiments

**Spike: Estimate distinct store coverage from a 10 000-row sample of fact_prices**
- Hypothesis: `fetchSettlementsForDate`'s `.limit(10000)` covers fewer than 50% of all stores that appear in a day's worth of facts.
- Approach: Statistical estimate. With ~1.3 M rows/day spread across 4,824 stores, assuming uniform distribution: probability that a given store is absent from a 10k sample ≈ `(1 − 10000/1300000)^(1300000/4824)` ≈ `(0.99231)^269.5` ≈ `e^(−2.064)` ≈ 0.127. So ~87.3% of stores appear in 10k rows. However, the distribution is highly skewed (large supermarket chains with many products dominate; small stores may have only 10–50 rows). Small-store settlements are disproportionately missed.
- Outcome: The 10 000-row limit likely covers the top ~87% of stores by row volume, but because store distribution is skewed, small settlements with few products are systematically excluded.
- Conclusion: The limit causes genuine data loss for small-town settlements. The fix must be server-side or exhaustive.

**Spike: Verify that `fetchReport1` hits the 1 000-row Supabase cap**
- Hypothesis: A city like Sofia with hundreds of stores and dozens of products per category will generate >1 000 fact rows for a single date+settlement combination.
- Approach: Extrapolation from known data. 4,824 stores total; if even 3% of stores are in Sofia = ~145 stores. With 369 categories and a mix of products, a conservative estimate: 145 stores × 5 product rows per category per store = 725 per category, but total rows across all categories easily exceeds 1 000. For a large city with ~200 stores and full product ranges, total fact rows for one date easily reaches 50 000–200 000.
- Outcome: The single un-paginated `.in('store_key', storeKeys)` call definitely truncates at 1 000 rows for any large metropolitan area.
- Conclusion: Pagination is required. The fix is to apply `fetchAllRows`-style while loop to the `fetchReport1` query.

**Spike: Confirm no spike needed for the `.in()` URL length issue**
- Hypothesis: For typical settlements (< 200 stores) the `.in()` list stays under the 8 KB URI limit.
- Approach: Estimate URL length: 200 store_keys × ~6 characters each + overhead ≈ 1.3 KB. Well under 8 KB.
- Outcome: URL length is not the primary failure mode for settlements. Row-count truncation in `fetchSettlementsForDate` is.
- Conclusion: No special URL-length mitigation needed beyond the pagination fix.

---

## AI Copilot Suggestions

- **The date/fact-data mismatch is an architectural smell, not just a bug.** The current design upserts all dimension data (including dates) regardless of fact data completeness, then relies on the UI to filter. A more robust architecture would either (a) not upsert a `dim_date` entry until the corresponding facts are uploaded, or (b) maintain the `fact_prices` RPC as the authoritative source for available dates going forward. The immediate fix (RPC to query distinct dates) is correct, but the team should also consider whether `load_supabase.py` should gate `dim_date` upsert on fact upload success.
  - Suggestion: In `load_supabase.py`, upsert `dim_date` for a given date only after the fact rows for that date have been successfully inserted. This prevents the drift problem from recurring.

- **`fetchReport1` deviation from the established pagination pattern is a maintainability risk.** The project already has a correct, reusable `fetchAllRows` helper. `fetchReport1` reinvents the query without reusing it, and the missing pagination creates a silent correctness bug. The inconsistency will recur if new queries are added without copying the pattern.
  - Suggestion: Consider encapsulating the paginated `.in()` pattern into a shared helper (e.g., `fetchFactRows(dateKey, storeKeys)`) to make the pattern explicit and avoid future repetition. This is low-scope within the current request.

- **The `.in('store_key', storeKeys)` filter in `fetchReport1` and `fetchReport2` will face URL-length and performance limits if settlements grow to hundreds of stores.** Sofia, for example, could realistically have 300+ stores. At large scale, the `.in()` approach breaks down and a settlement_key-indexed `dim_store` join via RPC would be more reliable.
  - Suggestion: The RPC approach for settlements (Q001-A) should also be evaluated for `fetchReport1` — passing `settlement_key` to a SQL function instead of a client-side store_key list would eliminate the URL-length risk entirely and potentially improve query performance.

- **Scope assessment:** The request is precise and well-bounded. All three defects have clear, independently testable fixes. No scope creep risk. The only open architectural question is the RPC vs. client-side approach for distinct queries (Q001), which is the right question to raise before implementation.

---

## Testing

- **T1 — Date dropdown populated from fact data only:** Open the deployed app; observe that the date dropdown contains only dates for which `fact_prices` rows exist in Supabase. Confirm that at most D, D-1, and D-2 dates appear (matching the user-stated expectation of 3 dates). Expected outcome: No "empty" dates selectable; selecting any shown date returns non-empty results in all reports.

- **T2 — Date dropdown build-time assertion:** After implementation, `npm run build` exits 0 and produces `dist/`. Expected outcome: Exit code 0; no TypeScript/JSX or import errors.

- **T3 — Settlement dropdown completeness (SC-3):** Select the latest date and open Report 1. Compare the cities shown in the dropdown against a known query of `SELECT DISTINCT s.settlement_key FROM fact_prices fp JOIN dim_store s ON s.store_key = fp.store_key WHERE fp.date_key = <latest date_key>` run directly in Supabase SQL editor. Expected outcome: City counts match; no settlement with fact data is absent from the dropdown.

- **T4 — Category chart completeness (SC-4):** Select a large metropolitan settlement (e.g., the one with the highest store count) and count the category bars displayed in Report 1. Compare against a direct `SELECT DISTINCT category_key FROM fact_prices WHERE date_key = X AND store_key IN (...)` in Supabase. Expected outcome: Bar count matches distinct categories in the DB; no "silent" omission.

- **T5 — Python test suite passes (SC-6):** Run `python -m pytest tests/ -v` from the workspace root. Expected outcome: All tests pass; exit code 0.

- **T6 — Re-run idempotency of load_supabase.py:** Run `python src/load_supabase.py` twice in sequence with no new local fact data. Expected outcome: Second run exits 0 with "No new fact data to upload" message; no duplicate RPC functions or errors from new DDL.

- **T7 — UAT: Visual date dropdown verification in browser.** See UAT_scenarios.md — UAT-01.
- **T8 — UAT: Settlement list completeness validation against user expectations.** See UAT_scenarios.md — UAT-02.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The three defects are correctly isolated to the data-service layer. The proposed RPC approach is appropriate: it pushes DISTINCT logic to the database engine where it can leverage indexes rather than transferring millions of rows to the client. One architectural concern: the `fetchReport1` fix using `.in('store_key', storeKeys)` with pagination still carries the O(N) URL-scaling risk for very large settlements. The longer-term design should pass `settlement_key` directly to a SQL function to avoid this. The choice to provision RPCs from `load_supabase.py` is consistent with the existing DDL-in-Python pattern and avoids introducing a separate migration tool.

- Root cause of date drift is architectural (dim upserted independently of fact upload).
- RPC-based DISTINCT is the correct and scalable approach at current data volume.
- `fetchReport1` pagination is a direct fix; URL-length risk should be noted for future scale.
- No changes to the ETL core are required for the pagination fix.
- load_supabase.py DDL extension is idempotent if implemented with `CREATE OR REPLACE`.

### Product Owner

Both defects directly harm user trust. A user selecting a date and seeing no data infers the product is broken, not that the date is "empty." The settlement omission means users in smaller cities cannot access the report at all — a functional gap. Fixing these two defects is high-priority from a product perspective. The success criteria are measurable and testable.

- Date dropdown defect causes highest user-visible harm (apparent product failure).
- Settlement omission is a functional exclusion for small-city users.
- Category omission in large cities compounds the trust issue in the main report.
- No acceptance criteria ambiguity; all three are verifiable.
- Q001 (implementation strategy) should be resolved before implementation to avoid rework.

### User

Currently, selecting a "no data" date and seeing a blank page gives no explanation. The UX would benefit from a loading state or "no data for this date" message, but the fundamental fix — removing non-data dates from the dropdown — is the right first step. Report 1's city list looks incomplete to any user who notices their own city is missing. The category chart looks sparse for large cities.

- Empty-date UX is confusing; removing such dates is the correct fix.
- City dropdown truncation is invisible to users — they simply can't find their city.
- Category chart incompleteness is subtle but undermines analytical trust.
- No UI redesign is in scope; fixes are data-correctness-level, not UX-level.
- Consider adding an explanatory notice if the city list loads slowly after the RPC is introduced.

### Security Officer

No new security risks are introduced by this request. The Supabase RPC functions, if implemented, must:
- Use `SECURITY INVOKER` (or `DEFINER` with the `anon` role explicitly granted EXECUTE).
- Not accept free-text parameters that could be used in SQL injection (integer `date_key` parameter is type-safe).
- Return only aggregated or filtered keys — no raw user data is exposed.
- Be tested against an authenticated and unauthenticated request to confirm the anon key can invoke them.

The client-side fix for `fetchReport1` pagination introduces no new attack surface.

- Integer parameter RPC is injection-safe.
- No new data exposure beyond what currently exists.
- Anon-role EXECUTE grant on new functions must be verified.
- No credentials or service-role keys are added.

### Data Governance Officer

The root cause of the date drift (dim_date upserted ahead of facts) is a data-quality concern: the dimension table claims completeness it does not have at the fact level. While all source data is public (Bulgarian government retail prices) with no PII, dimensional completeness is still a correctness property. The fix (filtering to fact-present dates) addresses the symptom; a future D-Q measure should be added to `load_supabase.py` to log dimension/fact date lag.

- No PII involved; no compliance risk.
- Dim/fact date completeness lag is a data-quality matter, not a security matter.
- `data/quality/report_*.csv` does not currently report on Supabase sync completeness.
- Recommend adding a new quality metric: rows uploaded to Supabase fact_prices per run.
- Data lineage for the new RPC functions should be noted in context.md.
