# Analysis — R-20260507-2248 — Scope dim_category to last 3 days of facts

## Executive Summary

- **Request ID:** R-20260507-2248

- **Request title:** Scope dim_category to last 3 days of facts

- **Purpose:** After discovering (R-20260507-0942) that 271 of 372 `dim_category` entries are anomalous `(unknown:...)` codes originating from historical retailer data quality issues, the operator wants the Supabase `dim_category` table to contain only category entries that are actually referenced by the current `fact_prices_lookback` table (rolling 3-day window). This eliminates historical garbage entries from user-facing analytics without touching the local dimension accumulation logic.

- **Core change:** Add a `prune_dim_category(conn)` function to `src/load_supabase.py` and call it in `main()` after `insert_lookback`. This follows the exact same pattern as the existing `prune_dim_date` step.

- **Quantitative impact:** Local workspace has 372 `dim_category` rows (101 valid + 271 unknown). `fact_prices_lookback` currently references 104 category keys (101 known + 3 unknowns that appear in the last 3 days of data). A prune would eliminate 268 rows from Supabase `dim_category` on the first sync run.

- **Risk level:** Low. The FK constraint flows from `fact_prices_lookback → dim_category`, making it structurally impossible to delete a referenced row. The safety guard (skip prune when fact table is empty) prevents accidental full-wipe.

- **Affected files:** `src/load_supabase.py`, `tests/test_load_supabase.py`.

- **`request.md` sections updated during this analysis run:** Assumptions (§7), Plan (§8), Documentation (§9), Questions & Decisions (§10).

---

## Domain Knowledge Essentials

- **kolkostruva.bg / Bulgarian government retail data:** Retailers submit daily price reports as CSV files inside ZIP archives. The government publishes them without strict column validation, meaning retailer structural errors (wrong column order, sentinel values, empty fields) propagate directly into the archive.

- **dim_category:** A star-schema dimension table mapping a stable surrogate integer key (`category_key`) to a raw category code (`category_code`) and a resolved Bulgarian name (`category_name`). Contains 101 official government-defined product categories (IDs 1–101) plus any anomalous codes accumulated from the raw data stream. SCD Type 1: once a surrogate key is assigned, it is never re-assigned.

- **fact_prices_lookback:** The sole Supabase fact table (since R-20260430-0825). Stores price observations for the last 3 fact dates, with horizontal lookback columns for D-1 and D-2 prices. Truncated and fully reinserted on every sync run. References `dim_category(category_key)` via FK constraint.

- **Rolling 3-day retention window (R-20260429-0825):** `load_supabase.py` already prunes `dim_date` to exactly the 3 newest local fact dates after each sync. The pattern for `dim_category` pruning mirrors this.

- **React app consumer impact:** The React app queries `dim_category` at startup via `fetchDimensions()` and caches it for the session. If Supabase `dim_category` contains 372 rows (268 of which are stale unknowns), the category dropdown in Report 1, Report 2 (cross-filter), and Report 3 will contain hundreds of anomalous entries that users cannot meaningfully filter on. After pruning, only 104 entries will appear — all of them actually present in the live data.

- **Impacted roles/personas:** Data engineers running `load_supabase.py`; end users of the React analytics app filtering by category.

---

## Technical Knowledge & Terms

- **`prune_dim_date(conn, retained_date_keys)`:** Existing function in `load_supabase.py` that deletes `dim_date` rows outside the retained key set. Uses a `DELETE … WHERE date_key NOT IN (...)` pattern with a safety guard against an empty retained set. Commits on success, rolls back on `psycopg2.DatabaseError`.

- **`prune_dim_category(conn)` (proposed):** New function modelled on `prune_dim_date`. Instead of receiving an explicit key list, it derives the set of referenced category keys directly from `fact_prices_lookback` via a subquery: `DELETE FROM dim_category WHERE category_key NOT IN (SELECT DISTINCT category_key FROM fact_prices_lookback)`. Safety guard: if `fact_prices_lookback` is empty (subquery returns zero rows), skip the DELETE to prevent wiping all dim_category rows.

- **FK constraint direction:** `fact_prices_lookback.category_key INTEGER NOT NULL REFERENCES dim_category(category_key)`. This means PostgreSQL will *reject* any attempt to delete a `dim_category` row that is currently referenced by a fact row. The prune query only targets *unreferenced* rows, so no FK violation is possible under correct execution order.

- **Execution ordering requirement:** `prune_dim_category` must be called *after* `insert_lookback` (which TRUNCATEs and reinserts `fact_prices_lookback`). If called before, the prune would see the post-truncate empty table and the safety guard would abort.

- **`idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)`:** Existing B-tree index (added in R-20260506-2251). The subquery `SELECT DISTINCT category_key FROM fact_prices_lookback` can use this index for an index-only scan, making the prune efficient even at scale.

- **No new indexes needed:** The existing index set supports the prune subquery efficiently.

- **Files read during this analysis:**
  - `src/load_supabase.py` (full)
  - `src/transform.py` (full)
  - `tests/test_load_supabase.py` (full)
  - `data/schema/dim_category.csv` (inspected via script: 372 rows, 101 known, 271 unknown)
  - `data/schema/fact_prices_lookback.csv` (inspected via script: 104 distinct category_keys referenced)
  - `.aib_memory/context.md` (full)
  - `.aib_memory/requests/R-20260507-0942-.../analysis.md` (executive summary reviewed)

---

## Research Results

**Pattern: Dimension pruning consistent with existing `prune_dim_date` pattern**

The codebase already implements an identical pattern for `dim_date` in `load_supabase.py`:
1. After refreshing `fact_prices_lookback`, call `get_date_keys_for_dates` to resolve retained key set.
2. Call `prune_dim_date(conn, retained_date_keys)` to delete stale `dim_date` rows.
3. Safety guard on empty retained set.
4. Commit on success, rollback on `psycopg2.DatabaseError`.

For `dim_category`, the pattern simplifies slightly: no pre-resolution of key list is needed (the subquery retrieves referenced keys directly from `fact_prices_lookback`), since there is no "n newest" parameterisation — any category present in any live fact row should be retained.

**Quantification from workspace scan:**
- 372 total dim_category entries locally.
- 104 referenced in the current `fact_prices_lookback` (last 3 days).
- 268 stale entries to be pruned on first sync post-implementation.
- 3 of the 104 retained entries are technically `(unknown:...)` codes — they appear in the last 3 days of retailer data and will correctly be retained by the prune.

**No impact on `transform.py`:** The local `dim_category.csv` must continue to accumulate all codes ever seen (surrogate key stability is essential for idempotent re-processing). The prune is a Supabase-only operation.

**`tests/test_load_supabase.py` test pattern:** The existing test suite uses mocked psycopg2 connections. The new `prune_dim_category` tests must follow the same `_make_mock_conn()` / `mock_cursor.fetchall` / `_EXECUTE_BATCH` pattern. Four new test cases needed: normal prune, safety guard (empty fact table), rollback on error, and no-op when all categories are referenced.

---

## External Benchmarking

**Benchmark 1: Star-schema dimension trimming to fact window (Kimball Group best practice)**

The Kimball data warehousing methodology recommends that when a rolling retention window is applied to a fact table, dimension tables should be correspondingly trimmed to remove entries no longer referenced by any live fact row. This avoids "orphan dimension rows" that appear in user-facing filters and confuse analysts. The approach recommended is a post-fact-load `DELETE … WHERE NOT EXISTS (SELECT 1 FROM fact … WHERE fact.dim_key = dim.key)` executed within the same ETL transaction window.

- **Takeaway:** The proposed `DELETE FROM dim_category WHERE category_key NOT IN (SELECT DISTINCT category_key FROM fact_prices_lookback)` is textbook Kimball. Applicable directly.
- **Adopted:** Yes — matches the proposed implementation exactly.

**Benchmark 2: PostgreSQL FK safety for referential pruning**

In PostgreSQL, the FK constraint `fact_prices_lookback.category_key REFERENCES dim_category(category_key)` prevents deletion of referenced rows. A `DELETE` targeting only unreferenced rows is therefore safe without any additional application-level guard beyond the empty-set check. PostgreSQL documentation and community practice confirm that DELETE on a parent table with an active FK from a child table will error on referenced rows but silently succeed on unreferenced rows.

- **Takeaway:** No special ordering (beyond "after truncate+reinsert of the fact table") is required. The database enforces referential integrity as a safety net.
- **Adopted:** Yes — confirms the safety guarantee of the implementation.

**Benchmark 3: Idempotent ETL prune operations (dbt and Airbyte pattern)**

Modern ETL frameworks (dbt, Airbyte) implement dimension pruning as idempotent "soft delete" or "hard delete" operations that are safe to re-run. A `DELETE … WHERE NOT IN (subquery)` that targets zero rows on re-run (because the state is already correct) completes instantly with `rowcount = 0` and no side effects. This is the expected behaviour for the proposed `prune_dim_category`.

- **Takeaway:** Idempotency is a first-class requirement. The proposed function satisfies it by design (SQL `DELETE` is idempotent when the predicate matches zero rows on re-run).
- **Adopted:** Yes.

---

## Minimal Spikes and Experiments

**Spike 1: Verify FK constraint direction allows prune**

Confirmed from `_CREATE_DDL` in `load_supabase.py`:
```sql
CREATE TABLE IF NOT EXISTS fact_prices_lookback (
    ...
    category_key INTEGER NOT NULL REFERENCES dim_category(category_key),
    ...
);
```
The FK is on `fact_prices_lookback`, *referencing* `dim_category`. Deleting from `dim_category` where `category_key NOT IN (SELECT DISTINCT category_key FROM fact_prices_lookback)` targets only rows that have *no* referencing rows in `fact_prices_lookback`. PostgreSQL will not raise an FK violation for these deletions.

**Spike 2: Verify existing index covers the subquery**

The subquery `SELECT DISTINCT category_key FROM fact_prices_lookback` can use `idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)` as a partial index scan or the table itself given its size (3-day window ≈ 3 × ~54–78 MB of raw data, but after star-schema factorisation, the number of distinct category_keys in `fact_prices_lookback` is small — confirmed 104 by workspace scan). No additional index is needed.

**Spike 3: Quantify prune volume**

Workspace measurement (Python script against local `dim_category.csv` and `fact_prices_lookback.csv`):
- Total dim_category rows: 372
- Rows referenced in fact_prices_lookback: 104
- Rows to be pruned: 268 (72% of all dim_category entries are stale)

This confirms the change has significant user-facing impact (React app will show 104 categories instead of 372).

---

## AI Copilot Suggestions

**Observation 1 — Scope is appropriately narrow and well-precedented**

The request is a clean, well-bounded extension of an existing pattern. `prune_dim_date` is the canonical model; the proposed `prune_dim_category` is structurally identical minus the external key-list resolution step. The implementation risk is very low: the FK constraint provides a hardware safety net, and the safety guard mirrors the existing pattern. No design decision is ambiguous.

*Suggestion:* Implement `prune_dim_category` as a direct structural twin of `prune_dim_date` — same error handling pattern, same commit/rollback discipline, same print statements. Consistency with the existing pattern is more valuable than any micro-optimisation.

**Observation 2 — Consider whether other dimensions should follow the same pattern (scope creep risk)**

`dim_category` is not the only dimension that accumulates stale entries. `dim_product` (natural key: `product_code + product_name`) and `dim_file` also accumulate from all historical ZIPs. `dim_store`, `dim_company`, and `dim_settlement` likely have similar accumulation. The request explicitly scopes to `dim_category` only, which is reasonable for a focused first step — but the implementation should be designed so future pruning of other dimensions is straightforward (e.g. same function signature pattern).

*Suggestion:* Do NOT generalise to all dimensions in this request (keep scope tight). However, name and structure `prune_dim_category` in a way that makes a future `prune_dim_product`, `prune_dim_file`, etc. obvious by analogy.

**Observation 3 — The 3-unknown-categories retained in the last 3 days are worth monitoring**

The workspace scan found 3 `(unknown:...)` category keys in the current `fact_prices_lookback`. These will survive the prune because they are referenced by live fact rows. This is correct behaviour (the prune must not break the FK constraint), but it means a small number of unknown categories will still appear in the React app's category dropdown after the change.

*Suggestion:* Do not attempt to fix this in this request — it is a retailer data quality issue outside scope. The 268 stale unknowns are the material problem. The 3 active unknowns are a known-acceptable residual per the no-rejection policy. Consider a future quality alert or filter in the React app if the number of active unknowns grows.

**Observation 4 — Execution ordering in `main()` is the key correctness invariant**

If `prune_dim_category` is called before `insert_lookback`, the post-TRUNCATE empty fact table triggers the safety guard and the prune is skipped (a benign but confusing no-op). If called before `upsert_dim` for dim_category, recently-added categories might be pruned before they appear in the fact table. The correct position is: after `insert_lookback`, after all `upsert_dim` calls.

*Suggestion:* In `main()`, place the `prune_dim_category` call immediately after `prune_dim_date` — both operate on the post-insert-lookback fact table state, and grouping them visually communicates that they are paired retention operations.

---

## Testing

- **T1 — prune_dim_category removes unreferenced rows:** Mock connection; `mock_cursor.fetchall` returns `[(1,), (2,)]` (two referenced category_keys from the subquery); verify `cursor.execute` was called with a SQL string containing `DELETE FROM dim_category` and the referenced keys; verify `conn.commit()` called once. Expected outcome: function returns deleted row count; `DELETE` SQL executed; commit called.

- **T2 — prune_dim_category safety guard on empty fact table:** Mock connection; `mock_cursor.fetchall` returns `[]` (empty subquery — fact table is empty); verify `cursor.execute` was called for the SELECT subquery but NOT for a DELETE statement; verify `conn.commit()` not called. Expected outcome: function returns 0; no DELETE executed; safety guard message printed.

- **T3 — prune_dim_category rollback on database error:** Mock connection; `mock_cursor.execute` raises `psycopg2.DatabaseError`; verify `conn.rollback()` called exactly once; verify `psycopg2.DatabaseError` is re-raised. Expected outcome: rollback called; exception propagates.

- **T4 — prune_dim_category no-op when all categories referenced:** Mock connection; `mock_cursor.fetchall` returns a set of referenced keys identical to all rows; simulate `cursor.rowcount = 0` after DELETE; verify `conn.commit()` called and return value is 0. Expected outcome: DELETE executes (zero affected rows); commit called; no error.

- **T5 — All existing tests continue to pass:** Run `python -m pytest tests/test_load_supabase.py -v` after implementation. Expected outcome: all pre-existing tests pass without modification.

- **T6 — `main()` calls prune_dim_category after insert_lookback:** Integration check via call-order inspection in tests; or confirm via code review that `prune_dim_category(conn)` appears after `insert_lookback(conn, lookback_csv)` in `main()`. Expected outcome: source ordering confirmed correct.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The proposed change is architecturally consistent and low-risk. It extends an established pruning pattern (`prune_dim_date`) with a structurally isomorphic function. The FK constraint provides a database-level safety net; the safety guard prevents accidental full-wipe. Execution ordering is the only material correctness risk, and it is clearly specified. The change does not alter DDL, indexes, or any RPC function. No cross-component impact beyond `load_supabase.py` and its test file.

- The DML-only approach (no DDL changes) is the correct choice.
- The subquery `SELECT DISTINCT category_key FROM fact_prices_lookback` leverages the existing `idx_fpl_date_cat` index; no new index is needed.
- The safety guard pattern (skip if subquery returns empty set) mirrors `prune_dim_date` and is a well-established defensive idiom for retention operations.
- Risk of over-deletion is structurally prevented by the FK constraint; if PostgreSQL ever raises an FK violation, it would indicate a bug in `insert_lookback` (not in `prune_dim_category`), making the failure mode clearly attributable.

### Product Owner

The change directly improves user experience: the React app's category dropdowns will show 104 entries instead of 372. 268 of those 372 entries are anomalous `(unknown:...)` codes that users cannot meaningfully act on. Eliminating them reduces noise in Report 1's bar chart, Report 2's cross-filter, and Report 3's category selector.

- Business value is immediate and tangible: cleaner category filter = less confusion for end users.
- Acceptance criterion is clear and testable: post-sync Supabase `dim_category` row count ≤ 104.
- No new user-visible features or UI changes required — the improvement is automatic once the next `load_supabase.py` run completes.
- Residual 3 active unknown categories are acceptable per the no-rejection policy.

### User (React App End User)

Before this change, opening the category dropdown in Report 1, Report 2, or Report 3 shows 372 options, most of which are `(unknown:...)` garbage. After the change, only 104 options appear — all of them real product categories with Bulgarian names. Users can meaningfully browse and filter.

- Friction reduced: scanning a 372-item dropdown for a real category is cumbersome; a 104-item dropdown is usable.
- No behavioral change in how reports work; just fewer (and better) options in the filter.
- Edge case: if a user had previously saved a bookmark or deep-link referencing a now-pruned category key, the category filter will show no results (the category no longer exists in the React app's cached dim_category). This is acceptable — those category codes were anomalous and had no valid products in the live data.

### Security Officer

No security impact. The change is a DML DELETE on a non-sensitive dimension table (product category codes and names — no PII). The operation is performed via the existing authenticated psycopg2 connection using `DATABASE_URL` from `.env`. No new credentials, endpoints, or attack surface introduced.

- The subquery does not expose any sensitive data path.
- The safety guard prevents accidental data loss in the event of an empty fact table.
- No change to RLS policies, anon key access, or public API surface.

### Data Governance Officer

The change does not affect the local `dim_category.csv`, which retains the full historical record of all category codes ever encountered. Surrogate key stability is preserved locally. The Supabase database is explicitly a derived, scoped view of the local star schema (rolling 3-day window); pruning `dim_category` in Supabase to match the live fact window is consistent with the established retention policy.

- Data lineage: local `dim_category.csv` remains the authoritative historical record. Supabase is the serving layer.
- Retention policy: the 3-day rolling window is already established for `dim_date` and `fact_prices_lookback`. Extending it to `dim_category` is a consistent application of the same policy.
- Compliance: no regulatory data retention obligation applies to these retail price category codes.
- Audit trail: the `prune_dim_category` print output (`Pruned N dim_category rows…`) provides an operator-visible record of each prune event. No structured audit log is required for this data type.
