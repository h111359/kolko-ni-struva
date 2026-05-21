## Goal

Prune `dim_category` in the Supabase database so it retains only category entries that are actually referenced by `fact_prices_lookback` after each sync run — eliminating historical unknown/anomalous category entries from previous ZIP archives that are no longer present in the current 3-day fact window.

## Background

Request R-20260507-0942 investigated and documented 271 `(unknown:...)` entries in `dim_category.csv`, tracing them to retailer data quality issues in historical ZIPs (Kaufland empty codes, АВАНТИ -1 sentinel codes, ЖАНЕТ large-integer codes, ГРИЗЛИ column-swap bugs, and isolated single-occurrence errors). The pipeline's no-rejection policy is confirmed correct — these entries should be accumulated locally.

However, the Supabase `dim_category` table is populated by upserting the entire local `dim_category.csv`, which accumulates all codes ever seen across 63+ ZIP archives. Since `fact_prices_lookback` is already scoped to the last 3 fact dates (rolling retention window per R-20260429-0825), and `dim_date` is already pruned to match, the `dim_category` table in Supabase currently contains obsolete entries that are not referenced by any live fact row. These stale entries surface in React app dropdowns and category filters, polluting the user-facing analytics with historically anomalous codes.

The fix should follow the existing pruning pattern established by `prune_dim_date` in `load_supabase.py`: after refreshing `fact_prices_lookback`, delete `dim_category` rows that are no longer referenced by any fact row.

## Scope

- Add a `prune_dim_category(conn)` function to `src/load_supabase.py` that deletes from `dim_category` all rows whose `category_key` is not present in `fact_prices_lookback`.

- Call `prune_dim_category` in `main()` of `src/load_supabase.py` after `insert_lookback` (which truncates and reinserts `fact_prices_lookback`) and after `prune_dim_date`, so the prune is based on the fully refreshed fact table.

- Add unit tests for `prune_dim_category` in `tests/test_load_supabase.py` covering: normal pruning, safety guard for empty result set, rollback on database error, and no-op when all categories are referenced.

- Update `src/load_supabase.py` import/export surface to expose `prune_dim_category` for test import.

## Out of scope

- Changes to `src/transform.py` or the local `dim_category.csv` accumulation logic — local dimension CSVs retain all historical codes for surrogate-key stability.

- Pruning other dimension tables (`dim_product`, `dim_store`, `dim_company`, `dim_settlement`, `dim_file`) — only `dim_category` is in scope per the request.

- Changes to the React app, Supabase RPC functions, or DDL provisioning logic.

- Historical backfill or cleanup of already-deployed Supabase instances beyond what the new prune step provides on the next sync run.

## Constraints

- The prune must execute AFTER `insert_lookback` completes (since `insert_lookback` truncates and reinserts `fact_prices_lookback` — the source of truth for "currently referenced" category keys).

- The prune must include a safety guard: if the subquery returns no referenced category keys (e.g. `fact_prices_lookback` is empty), the DELETE must be skipped to avoid wiping all dim_category rows.

- The implementation must be idempotent: re-running `load_supabase.py` when the remote state is already correct must be a safe no-op.

- FK constraint direction: `fact_prices_lookback.category_key REFERENCES dim_category(category_key)` — deleting unreferenced `dim_category` rows does not violate this constraint. The implementation must not attempt to delete referenced rows.

- No changes to DDL or table schema; the prune is a DML-only operation.

- Python 3.9+ stdlib + psycopg2; no new dependencies.

## Success criteria

1. After a successful `load_supabase.py` run, `dim_category` in Supabase contains only `category_key` values that appear in `fact_prices_lookback`.

2. Re-running `load_supabase.py` on an already-pruned database produces a 0-row prune log message and leaves `dim_category` unchanged.

3. All new unit tests in `tests/test_load_supabase.py` for `prune_dim_category` pass.

4. All existing tests in `tests/test_load_supabase.py` continue to pass without modification.

5. No FK constraint violation is raised during the prune step under any condition (empty fact table, partially populated fact table, or fully populated fact table).

## Assumptions

- A1: The local `dim_category.csv` must NOT be modified — surrogate key stability for local re-processing depends on accumulating all historical codes.
  - Risk if false: Surrogate key collision or re-assignment on re-processing would corrupt the star schema.

- A2: `prune_dim_category` will be called in `main()` after `insert_lookback` and after `upsert_dim` for `dim_category`. No other ordering is safe.
  - Risk if false: If called before `insert_lookback`, the empty post-TRUNCATE fact table triggers the safety guard (benign no-op but confusing). If called before `upsert_dim`, newly added categories might be pruned immediately.

- A3: The FK constraint `fact_prices_lookback.category_key REFERENCES dim_category(category_key)` is enforced by PostgreSQL at runtime, providing a database-level safety net against deleting referenced rows.
  - Risk if false: If the constraint is disabled or not enforced, a bug in `insert_lookback` could cause `fact_prices_lookback` to silently lose rows, leading the prune to delete still-needed categories.

- A4: Up to 3 `(unknown:...)` category entries will remain in Supabase `dim_category` after pruning because they appear in the live last-3-days fact data. This is correct and expected per the no-rejection policy.
  - Risk if false: If those 3 entries disappear from fact data in future dates, they will be pruned automatically on the next sync run. No residual.

- A5: The existing `idx_fpl_date_cat ON fact_prices_lookback(date_key, category_key)` index is sufficient for the `SELECT DISTINCT category_key` subquery. No new index is needed.
  - Risk if false: Without the index, the prune subquery would perform a full sequential scan of `fact_prices_lookback`. At 3-day lookback scale this is still fast (<1 second), but an index makes it index-only.

## Plan

### Task 1: Add `prune_dim_category` function to `src/load_supabase.py`
**Intent:** Implement the prune function that deletes unreferenced `dim_category` rows from Supabase.
**Inputs:** `src/load_supabase.py` (existing); `prune_dim_date` function as structural model.
**Outputs:** New `prune_dim_category(conn)` function added to `src/load_supabase.py`.
**External Interfaces:** Supabase PostgreSQL via psycopg2.
**Environment & Configuration:** DATABASE_URL from `.env`; no new config keys.
**Procedure:**
1. Read `prune_dim_date` function in `load_supabase.py` as the reference implementation.
2. Add `prune_dim_category(conn)` function below `prune_dim_date`. The function: (a) queries `SELECT DISTINCT category_key FROM fact_prices_lookback`; (b) if result is empty, prints safety guard message and returns 0; (c) otherwise executes `DELETE FROM dim_category WHERE category_key NOT IN (…)` with the fetched keys as parameters; (d) commits on success; (e) rolls back and re-raises on `psycopg2.DatabaseError`.
3. Add a `print` statement consistent with other prune functions: `f"  Pruned {deleted:,} dim_category rows outside retained window."`.
**Done Criteria:** Function is present, callable, and follows error-handling/commit/rollback discipline of `prune_dim_date`.
**Dependencies:** None.
**Risk Notes:** None — DML-only, FK constraint provides safety net.

### Task 2: Wire `prune_dim_category` into `main()` in `src/load_supabase.py`
**Intent:** Ensure `prune_dim_category` is called at the correct position in the sync orchestration.
**Inputs:** `src/load_supabase.py` `main()` function; Task 1 output.
**Outputs:** `main()` updated to call `prune_dim_category(conn)` after `prune_dim_date`.
**External Interfaces:** Same psycopg2 connection used by all other steps.
**Environment & Configuration:** No changes needed.
**Procedure:**
1. Locate the `prune_dim_date(conn, retained_date_keys)` call in `main()`.
2. Add `prune_dim_category(conn)` call immediately after, with a preceding `print("Pruning remote dim_category to retained fact window …")`.
**Done Criteria:** `main()` contains `prune_dim_category(conn)` after `prune_dim_date`; the call is inside the `try` block.
**Dependencies:** Task 1.
**Risk Notes:** Ordering is the key correctness invariant — must be after `insert_lookback`.

### Task 3: Add unit tests for `prune_dim_category` in `tests/test_load_supabase.py`
**Intent:** Cover all testable success criteria with mocked psycopg2 tests.
**Inputs:** `tests/test_load_supabase.py` (existing); `prune_dim_category` function (Task 1).
**Outputs:** New `TestPruneDimCategory` class with 4 test methods added to `tests/test_load_supabase.py`.
**External Interfaces:** Mocked psycopg2 (same mock setup as existing tests).
**Environment & Configuration:** None.
**Procedure:**
1. Add `prune_dim_category` to the import block at the top of the test file.
2. Add `TestPruneDimCategory` class after the last existing test class.
3. Implement: `test_prune_removes_unreferenced_rows`, `test_safety_guard_on_empty_fact_table`, `test_rollback_on_db_error`, `test_no_op_when_all_categories_referenced`.
**Done Criteria:** 4 new tests; all pass; all existing tests continue to pass.
**Dependencies:** Task 1.
**Risk Notes:** None.

### Task 4: Run test suite and verify
**Intent:** Confirm all tests pass after the implementation.
**Inputs:** `tests/test_load_supabase.py`; `src/load_supabase.py` (modified).
**Outputs:** Test run output confirming all tests pass.
**External Interfaces:** Python test runner (`python -m pytest tests/test_load_supabase.py -v` or `python -m unittest`).
**Environment & Configuration:** Activated virtualenv with test dependencies installed.
**Procedure:**
1. Run `python -m pytest tests/test_load_supabase.py -v` from project root with virtualenv active.
2. Confirm zero failures, zero errors.
**Done Criteria:** All tests green, including new `TestPruneDimCategory` tests.
**Dependencies:** Tasks 1–3.
**Risk Notes:** None.

### Task 5: Update `context.md` and documentation
**Intent:** Reflect the new pruning step in the product context document.
**Inputs:** `.aib_memory/context.md`; `src/load_supabase.py` module description in context.
**Outputs:** `.aib_memory/context.md` updated with `prune_dim_category` in the module breakdown and sync orchestration description.
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Find the `src/load_supabase.py` module description in `context.md`.
2. Add `prune_dim_category(conn, retained_date_keys)` to the pruning function list alongside `prune_dim_date`.
3. Update the `main()` description to mention the dim_category prune step.
4. Add a request reference annotation `(R-20260507-2248)` to the updated lines.
**Done Criteria:** `context.md` accurately reflects the new sync step; no other sections altered.
**Dependencies:** Tasks 1–2.
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: N/A) — Update `src/load_supabase.py` module breakdown to add `prune_dim_category` and update `main()` description with the dim_category prune step (R-20260507-2248).

## Questions & Decisions

No questions raised. All decision points were resolvable from existing workspace documentation and codebase analysis:
- Implementation model: `prune_dim_date` in `load_supabase.py` — direct structural model adopted. (Severity 1 — trivial.)
- Safety guard behaviour: skip prune when fact table is empty — consistent with `prune_dim_date` safety guard. (Severity 2 — minor.)
- Execution position in `main()`: after `insert_lookback` and after `prune_dim_date` — only valid position per the ordering constraint. (Severity 2 — minor.)

## Code and Asset Scan for Impacted Components

**Directly modified files:**
- `src/load_supabase.py` — new `prune_dim_category(conn)` function added; `main()` updated to call it.
- `tests/test_load_supabase.py` — new `TestPruneDimCategory` test class with 4 test methods added; `prune_dim_category` added to import block.

**Indirectly affected (documentation update only):**
- `.aib_memory/context.md` — module breakdown for `src/load_supabase.py` to be updated.

**No changes required:**
- `src/transform.py` — dimension accumulation logic unchanged.
- `data/schema/dim_category.csv` — local dimension file unchanged.
- `react-app/` — no React app changes; reduced dim_category row count is automatically reflected via `fetchDimensions()` next load.
- All other `src/`, `tests/`, and `data/` files — unaffected.

## Internal Review of Request and Product Docs

**Consistency check:**
- Rolling 3-day retention: consistent with `prune_dim_date` and `get_retained_local_dates` patterns already in `load_supabase.py`. The new `prune_dim_category` extends the same retention policy to the category dimension.
- FK constraint correctness: confirmed from `_CREATE_DDL` — `fact_prices_lookback.category_key REFERENCES dim_category(category_key)`. Prune targets only unreferenced rows; no FK violation possible.
- Idempotency: consistent with the non-functional requirement for all `load_supabase.py` operations.
- No-rejection policy: unchanged. Local `dim_category.csv` still accumulates all codes. Only the Supabase serving layer is pruned.
- Context.md accuracy: the current context.md does not mention `prune_dim_category`. An update is required and included in the Documentation section.
