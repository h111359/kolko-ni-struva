First and only implementation increment for request R-20260429-0825 (Trim Supabase facts to latest 3 days). All success criteria defined in analysis.md were met in this increment.

Files taken into consideration:
- .aib_memory/requests/R-20260429-0825-trim-supabase-facts-to-latest-3-days/request.md
- .aib_memory/requests/R-20260429-0825-trim-supabase-facts-to-latest-3-days/analysis.md
- .aib_memory/context.md
- .aib_memory/references.md

## Implementation Log

### Entry 2026-04-30 09:15

#### Scope
Added rolling 3-day remote retention to `src/load_supabase.py`. On every sync run the module now computes the 3 newest local fact dates, deletes all `fact_prices` rows whose `date_key` falls outside that window, then prunes `dim_date` to match. The retention logic is idempotent: re-running with unchanged local data leaves `fact_prices` row count unchanged and only re-prunes `dim_date` rows that were re-upserted from the full local CSV in the same run. `README.md` operator documentation was updated to describe the new behavior.

#### Changes
- Added `get_retained_local_dates(facts_dir, n=3)` to `src/load_supabase.py`: returns the `n` newest local fact date strings (YYYY-MM-DD) from `data/schema/facts/`, sorted oldest-first; returns `[]` when the directory is absent or empty.
- Added `get_date_keys_for_dates(conn, date_strings)` to `src/load_supabase.py`: queries `SELECT date_key FROM dim_date WHERE date::text = ANY(%s)` with parameterised input; returns `[]` without querying when given an empty list.
- Added `prune_fact_prices(conn, retained_date_keys)` to `src/load_supabase.py`: executes `DELETE FROM fact_prices WHERE date_key NOT IN (...)` with parameterised retained keys; skips delete and returns 0 when the key list is empty; rolls back and re-raises on `psycopg2.DatabaseError`.
- Added `prune_dim_date(conn, retained_date_keys)` to `src/load_supabase.py`: same pattern as `prune_fact_prices` but targets `dim_date`; must be called after `prune_fact_prices` to satisfy the FK constraint.
- Updated `main()` in `src/load_supabase.py`: restructured into 7 sequential steps — provision, upsert dims, compute retained dates and date keys, insert latest fact day if absent (no early return), prune fact_prices, prune dim_date, insert lookback.
- Updated module docstring of `src/load_supabase.py` to document the retention policy.
- Added `TestGetRetainedLocalDates` (8 tests), `TestGetDateKeysForDates` (3 tests), `TestPruneFactPrices` (7 tests), `TestPruneDimDate` (6 tests) to `tests/test_load_supabase.py` (24 new tests).
- Updated mock setup in `tests/test_load_supabase.py`: imported real `psycopg2` as `_real_psycopg2` before mock setup and assigned `_mock_psycopg2.DatabaseError = _real_psycopg2.DatabaseError` to prevent `TypeError` in rollback tests.
- Updated `README.md` `src/load_supabase.py` section to describe the rolling 3-day retention window behavior and idempotency guarantee.

#### Tests
- Unit — `tests/test_load_supabase.py` — 34 passed, 0 failed (full module including 24 new tests).
- Unit — full test suite `tests/` — 110 passed, 1 skipped, 0 failed.
- Live run 1 — `venv/bin/python src/load_supabase.py` against production Supabase — success: pruned 6,694,089 `fact_prices` rows and 70 `dim_date` rows, retained dates `['2026-04-26', '2026-04-27', '2026-04-28']`.
- Live run 2 (idempotency) — `venv/bin/python src/load_supabase.py` — success: pruned 0 `fact_prices` rows (idempotency confirmed), 70 `dim_date` rows pruned (re-pruned after full dim_date upsert from local CSV), inserted 1,353,714 rows into `fact_prices_lookback`, exit code 0.

#### Outcome
Success. All four success criteria from analysis.md are met: SC-1 (only latest 3 local dates retained in remote fact_prices), SC-2 (dim_date pruned to match), SC-3 (idempotency: 0 fact_prices rows deleted on re-run), SC-4 (unit tests pass). No residual risks. No follow-ups required.

#### Evidence
- Unit test run:

```
34 passed in 0.13s
```

- Full suite run:

```
110 passed, 1 skipped in 0.44s
```

- Live run 1 output (pruning):

```
Retained local dates    : ['2026-04-26', '2026-04-27', '2026-04-28']
Pruning remote fact_prices to retained window …
  Pruned 6,694,089 fact_prices rows outside retained window.
Pruning remote dim_date to retained dates …
  Pruned 70 dim_date rows outside retained window.
Supabase sync complete.
```

- Live run 2 output (idempotency):

```
Retained local dates    : ['2026-04-26', '2026-04-27', '2026-04-28']
Fact day 2026-04-28 already present in remote.
Pruning remote fact_prices to retained window …
  Pruned 0 fact_prices rows outside retained window.
Pruning remote dim_date to retained dates …
  Pruned 70 dim_date rows outside retained window.
Syncing fact_prices_lookback …
  Inserted 1,353,714 rows into fact_prices_lookback.
Supabase sync complete.
```
