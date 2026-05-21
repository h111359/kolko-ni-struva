# Request

## Goal

Corrective changes are required to the ETL pipeline (`src/pipeline.py`) and Supabase migration script (`src/migrate_supabase.py`):

1. **Reduce local fact-file size**: the 25 daily fact JSON files in `data/schema/facts/` total ~4.7 GB on disk because each record repeats all field names (named-key JSON). Change the fact file format to csv (character separated values) file for the fact file.

2. **Preserve rows with unknown dimension FKs**: rows whose EKATTE city code or category_id is not found in the dimension store are currently silently dropped in `build_facts()`. Instead, auto-insert a placeholder dimension record (city or category) for the unknown natural key, and use its surrogate key in the fact row. The user must later update the `data/nomenclatures/` source files.

## Background

- `src/pipeline.py` downloads daily retail-price CSVs from kolkostruva.bg, parses them, maintains a JSON-based SCD Type 2 star schema under `data/schema/`, and writes per-day fact files to `data/schema/facts/YYYY-MM-DD.json`.
- `src/migrate_supabase.py` incrementally syncs the local JSON star schema into a Supabase PostgreSQL database using a two-tier strategy (Tier 1: last 3 days at row granularity; Tier 2: weekly category aggregates).
- Supabase free tier has a 500 MB storage cap. The migration script is designed to stay within this limit (~367 MB estimated per `docs/supabase-setup.md`), but this has not been verified against a live database.
- 16 distinct EKATTE codes in the raw source data (e.g. 98226, 4279) are absent from `data/nomenclatures/cities-ekatte-nomenclature.json`, causing ~229 780 "row skipped" warnings per the pipeline log and silent data loss.

## Scope

1. **`src/pipeline.py` — `write_fact_file()` function:** Replace JSON serialisation with `csv.DictWriter`. Output file: `data/schema/facts/YYYY-MM-DD.csv`. Columns (in order): `date`, `company_sk`, `trade_object_sk`, `product_sk`, `city_sk`, `category_sk`, `retail_price`, `promo_price`. Header row included. Empty string represents `null` for `promo_price`. Atomic write via `.partial` temp-file rename preserved. The `metadata` block (date, company_count, row_count) is dropped.

2. **`src/pipeline.py` — `main()`, two fact-file existence checks:** Change `.json` to `.csv` at lines 732 (`--no-backfill` filter) and 754 (skip-if-exists guard).

3. **`src/pipeline.py` — `DimensionStore` class:** Add two new methods:
   - `insert_placeholder_city(ekatte: str, as_of_date: date) -> int` — calls `_upsert("city", ekatte, {"ekatte": ekatte, "city_name": "[UNKNOWN EKATTE:{ekatte}]", "is_unresolved": True}, as_of_date)`.
   - `insert_placeholder_category(category_id: str, as_of_date: date) -> int` — calls `_upsert("category", category_id, {"category_id": category_id, "category_name": "[UNKNOWN ID:{category_id}]", "is_unresolved": True}, as_of_date)`.
   The `is_unresolved` flag is stored in `dim_city.json` / `dim_category.json` only; it is not propagated to Supabase.

4. **`src/pipeline.py` — `build_facts()` function:** Replace the two `if city_sk is None: ... continue` and `if category_sk is None: ... continue` blocks. When `get_city_sk()` or `get_category_sk()` returns `None`, call the corresponding `insert_placeholder_*` method to obtain the SK and emit a WARNING log: `"Unknown EKATTE %s in %s — placeholder inserted, update nomenclature"` (or equivalent for category).

5. **`src/migrate_supabase.py` — `_available_fact_dates()`:** Change `if p.suffix == ".json"` to `if p.suffix == ".csv"`.

6. **`src/migrate_supabase.py` — `sync_tier1()`:** Change `fact_path = facts_dir / f"{d_str}.json"` to `.csv`. Replace `json.loads(fact_path.read_text(...))` + `data.get("facts", [])` with CSV reading via `csv.DictReader`. Add a coercion helper (or inline) that converts string fields to: `company_sk` / `trade_object_sk` / `product_sk` / `city_sk` / `category_sk` → `int | None`; `retail_price` / `promo_price` → `float | None` (empty string → `None`).

7. **`src/migrate_supabase.py` — `sync_tier2()`:** Change `if p.suffix != ".json"` to `.csv`. Replace JSON reading with CSV reading + same type coercion as Tier 1.

8. **`README.md` — Output Reference / Fact files section:** Update documented format from JSON (`metadata` + `facts` array) to CSV (header row + data rows). Provide a representative sample CSV snippet.

9. **`.aib_memory/context.md` — Functional capabilities #4:** Update "JSON fact file" to "CSV fact file".

## Out of scope

- Changes to the Supabase DDL (table schemas, indexes, column types). The `is_unresolved` flag is stored only in local JSON dimension files and is not synced to Supabase.
- Changes to the anomaly-detection or quality-report logic (`data/quality/`).
- Data re-download from kolkostruva.bg (pipeline already has the 25 days of ZIPs/folders).
- Any front-end, API, or dashboard layer.
- Populating currently empty product-doc stubs in `.aib_memory/docs/` (separate reverse-engineering task).

## Constraints

- Python 3.10+; only Python standard library additions permitted for the compression change.
- No new pip packages required for this change.
- Supabase DDL must not change.
- The `pipeline.py --force` re-run must be idempotent: running it twice must produce the same output.

## Success criteria

1. Running `python src/pipeline.py --force` produces `data/schema/facts/YYYY-MM-DD.csv` for every date in `data/raw/`. No `.partial` files remain. No exception is raised.
2. Running `python src/pipeline.py --force` a second time produces identical CSV files (byte-for-byte same row sets, order may vary by SK); days_processed count equals the number of dates with raw data.
3. `data/schema/dim_city.json` contains at least one record with `"is_unresolved": true` for each EKATTE code present in raw data but absent from `data/nomenclatures/cities-ekatte-nomenclature.json` (16 codes known at time of writing: including 98226, 4279).
4. Running `python src/pipeline.py --force` twice does not produce additional placeholder records beyond those created on the first run (stable SK and `is_unresolved` flag after re-run).
5. Running `python src/migrate_supabase.py` against a Supabase test instance completes without Python exceptions or database errors. Tier 1 and Tier 2 rows match the row counts in the corresponding CSV files (after type-coercion).
6. `python src/pipeline.py --no-backfill` does not re-process dates that already have a `.csv` fact file.

