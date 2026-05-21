Files taken into consideration:
- `.aib_memory/requests_register.md`
- `.aib_memory/requests/R-20260420-2055-add-day-1-and-day-2-prices-to-fact-prices/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/conventions/coding-general-convention.md`
- `.aib_brain/conventions/coding-python-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/context-convention.md`
- `src/transform.py`
- `src/load_supabase.py`

## Implementation Log

### Entry 2026-04-21 03:30

#### Scope
Implement the `fact_prices_lookback` derived table feature (request R-20260420-2055). Added `LOOKBACK_HEADER` constant, `load_fact_dict` helper, and `build_lookback_table` function to `src/transform.py`; wired the call into `main()`. Updated `src/load_supabase.py` with DDL for the new `fact_prices_lookback` table, idempotent `ADD COLUMN IF NOT EXISTS` guards in `_ENSURE_NULLABLE_DDL`, and a new `insert_lookback` function called from `main()`. Updated `data/schema/` documentation in `.aib_memory/context.md`.

#### Changes
- Added `LOOKBACK_HEADER` constant to `src/transform.py` (11 columns: the 7 FACT_HEADER columns plus `retail_price_day1`, `promo_price_day1`, `retail_price_day2`, `promo_price_day2`).
- Added `load_fact_dict(fact_path)` helper to `src/transform.py`: reads a fact CSV into a dict keyed by `(store_key, category_key, product_key)` → `(retail_price, promo_price)`; returns empty dict when file absent.
- Added `build_lookback_table(facts_dir, output_path)` function to `src/transform.py`: identifies D, D-1, D-2 from sorted fact CSVs; produces 11-column output with empty-string fallback for missing lookback values; writes atomically via `.partial` → rename.
- Wired `build_lookback_table(FACTS_DIR, SCHEMA_DIR / "fact_prices_lookback.csv")` call at the end of `transform.py`'s `main()`, after `save_state()`, so it always runs unconditionally.
- Added `CREATE TABLE IF NOT EXISTS fact_prices_lookback` DDL (11 columns, four lookback columns nullable) to `_CREATE_DDL` in `src/load_supabase.py`.
- Added four `ALTER TABLE IF EXISTS fact_prices_lookback ADD COLUMN IF NOT EXISTS … NUMERIC(12, 4)` guards to `_ENSURE_NULLABLE_DDL` in `src/load_supabase.py`.
- Added `insert_lookback(conn, csv_path)` function to `src/load_supabase.py`: truncates then reinserts all rows from `fact_prices_lookback.csv` within a transaction; handles missing/empty file gracefully.
- Called `insert_lookback(conn, lookback_csv)` from `load_supabase.py`'s `main()` as Step 5, after existing `insert_fact_day`.
- Updated `.aib_memory/context.md`: added `fact_prices_lookback.csv` row to Core Data Entities table; added note on empty-string semantics and promo_price ambiguity (A5); updated Data Lineage Summary to show derivation from D, D-1, D-2 fact CSVs; updated `transform.py` and `load_supabase.py` module descriptions; updated Star-schema outputs description.
- `data/schema/fact_prices_lookback.csv` created (1,340,921 rows; 11 columns).

#### Tests
- smoke: ran `python src/transform.py` — pass (fact_prices_lookback.csv produced, 1,340,921 rows)
- T0 (existing fact CSVs unchanged): checked `2026-04-16.csv`, `2026-04-17.csv`, `2026-04-18.csv` — all 7-column header unchanged — pass
- T1 (lookback header validation): header is exactly `date_key,store_key,file_key,category_key,product_key,retail_price,promo_price,retail_price_day1,promo_price_day1,retail_price_day2,promo_price_day2` — pass
- T2 (row count matches D): lookback rows (1,340,921) == D fact rows (1,340,921) — pass
- T3 (lookback values correct): 10 sampled matching rows cross-checked against D-1 (`2026-04-17.csv`) — values match — pass
- T4 (no-match row has empty lookback): identified row absent from D-1; `retail_price_day1` and `promo_price_day1` are empty string — pass
- T5 (fewer-than-3-files edge case): 1-file scenario produces all-empty lookback columns; 2-file scenario produces empty day2 columns — pass
- T6 (column count): `len(next(csv.reader(open('data/schema/fact_prices_lookback.csv')))) == 11` — pass
- T8 (existing unit tests): `venv/bin/python -m pytest tests/ -v` — 8 passed — pass
- T7/T9 (Supabase DDL idempotency and lookback insert): skipped — Supabase connection not available in this environment; DDL reviewed for correctness.

#### Outcome
Successful. All local tests T0–T6 and T8 pass. `fact_prices_lookback.csv` is produced atomically on each transform run; FACT_HEADER and all 63 existing fact CSVs are untouched. Supabase DDL includes `fact_prices_lookback` with all 11 columns; idempotent ADD COLUMN guards ensure forward compatibility with pre-existing schema. T7 and T9 require an active Supabase connection and were not run locally.

#### Evidence
- `data/schema/fact_prices_lookback.csv` (1,340,921 rows × 11 columns)
- T0–T6 and T8 inline assertions executed in terminal — all passed
- `venv/bin/python -m pytest tests/ -v` output:

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
collected 8 items

tests/test_config_utils.py::TestLoadConfig::test_adds_missing_section PASSED
tests/test_config_utils.py::TestLoadConfig::test_creates_config_when_absent PASSED
tests/test_config_utils.py::TestLoadConfig::test_defaults_present PASSED
tests/test_config_utils.py::TestLoadConfig::test_idempotent_when_file_exists PASSED
tests/test_config_utils.py::TestSaveState::test_no_partial_file_left PASSED
tests/test_config_utils.py::TestSaveState::test_preserves_sibling_keys PASSED
tests/test_config_utils.py::TestSaveState::test_uses_replace_not_rename PASSED
tests/test_config_utils.py::TestSaveState::test_writes_key PASSED

8 passed in 0.06s
```
