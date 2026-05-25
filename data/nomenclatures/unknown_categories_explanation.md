# Unknown Category Entries in dim_category

**Last updated:** 2026-05-07  
**Investigated by:** R-20260507-0942 — Investigate and clean unknown dim_category entries  
**Scope:** All 271 `(unknown:...)` entries in `data/schema/dim_category.csv`

> **Note:** This file is a point-in-time snapshot. If new `(unknown:...)` entries appear after future
> transform runs, re-run the investigation or re-invoke request R-20260507-0942 to update this file.

---

## Background

`data/schema/dim_category.csv` maps a surrogate `category_key` to the raw category code submitted by
retailers and to the resolved human-readable category name. The Bulgarian government portal defines
101 mandatory product categories (IDs 1–101) in `data/nomenclatures/product-categories.json`.

When `src/transform.py` encounters a category code that is not present in that JSON, it stores the
entry as `(unknown:<code>)`. As of 2026-05-07, 271 of the 372 rows in `dim_category.csv` are
`(unknown:...)` entries (~73%). All 271 have been traced to specific retailers and specific
data-quality failure modes; none represent random corruption.

The pipeline uses a no-rejection policy: it stores all codes regardless of validity, so that data
is never silently discarded. The `(unknown:...)` entries are the intentional audit trail of this
policy.

---

## Summary Table

| Group | Count (dim_category rows) | category_key range | Source | Failure mode | Recommended action |
|---|---|---|---|---|---|
| A | 1 | 102 | Кауфланд България (Kaufland) | Empty Категория column | Retain as-is |
| B | 1 | 103 | АВАНТИ (АВАНТИ 777 ЕООД) | Sentinel value -1 | Retain as-is |
| C | 1 | 369 | ТЪРГОВСКА ВЕРИГА ЖАНЕТ (ЖАНЕТ ООД) | Internal numeric ID as category | Retain as-is |
| D | 248 | 104–368 (interleaved) | ГРИЗЛИ (ДИЕЛ ЕООД) | Columns 3 and 4 swapped in 3 ZIPs | Re-ingest 3 dates (see below) |
| E | 17 | 118–337 (interleaved) | ГРИЗЛИ (ДИЕЛ ЕООД) | Same column-swap, 630xxx product codes | Re-ingest 3 dates (see below) |
| F | 3 | 370, 371, 372 | Various (T Market, Валди, unknown) | Single-occurrence retailer errors | Retain as-is |

---

## Group A — Empty category code

- **category_key:** 102
- **category_code:** `` (empty string)
- **category_name:** `(unknown:)`
- **Source retailer:** Кауфланд България (Kaufland) — file `Кауфланд България_131129282.csv`
- **Frequency:** ~124 rows per daily ZIP, consistent across all dates in the archive.
- **Root cause:** Kaufland's export leaves the Категория column blank for some products. This is
  a data quality issue in Kaufland's submission pipeline. The empty code consistently appears in
  every ZIP in the archive (2026-02-15 through 2026-05-06).
- **Fact rows affected:** ~124 rows per day × 81 days = ~10,000 fact rows reference category_key 102.
- **Recommended action:** Retain as-is. This is an upstream data quality issue outside the
  operator's control. For analytics, filter or label rows with `category_key = 102` as
  "Kaufland — category not provided."

---

## Group B — Sentinel value -1

- **category_key:** 103
- **category_code:** `-1`
- **category_name:** `(unknown:-1)`
- **Source retailer:** АВАНТИ (АВАНТИ 777 ЕООД) — file `АВАНТИ (АВАНТИ 777 ЕООД)_105568755.csv`
- **Frequency:** ~89 rows per daily ZIP. First appeared in the 2026-03-28 ZIP; consistent in all
  subsequent ZIPs.
- **Root cause:** АВАНТИ uses `-1` as a sentinel value for products that have no assigned category.
  This is a retailer-side convention not aligned with the government's 1–101 category range.
- **Fact rows affected:** ~89 rows per day × ~40 days (2026-03-28 onward) = ~3,560 fact rows.
- **Recommended action:** Retain as-is. For analytics, filter or label rows with `category_key = 103`
  as "АВАНТИ — uncategorised product."

---

## Group C — Large internal numeric ID

- **category_key:** 369
- **category_code:** `1972047017`
- **category_name:** `(unknown:1972047017)`
- **Source retailer:** ТЪРГОВСКА ВЕРИГА ЖАНЕТ (ЖАНЕТ ООД) — file
  `ТЪРГОВСКА ВЕРИГА ЖАНЕТ (ЖАНЕТ ООД)_102827804.csv`
- **Frequency:** Present in every ZIP from 2026-04-18 onward. Multiple rows per daily ZIP.
- **Root cause:** ЖАНЕТ submits what appears to be an internal product or item ID as the category
  code rather than a value from the mandated 1–101 range.
- **Fact rows affected:** Estimated several hundred fact rows.
- **Recommended action:** Retain as-is. For analytics, filter or label rows with `category_key = 369`
  as "ЖАНЕТ — invalid category code (internal ID submitted)."

---

## Groups D and E — ГРИЗЛИ column-swap anomaly

- **Group D:** 248 dim_category entries, category_code values matching pattern `0XXXXX` (6-digit
  zero-padded, e.g. `001314`, `003902`, `005611`).
- **Group E:** 17 dim_category entries, category_code values matching pattern `63XXXX` (e.g.
  `630214`, `630525`, `631873`).
- **Combined category_key range:** keys 104–368 (interleaved with other entries added between
  those dates).
- **Source retailer:** ГРИЗЛИ (ДИЕЛ ЕООД) — file `ГРИЗЛИ (ДИЕЛ ЕООД)_823077024.csv`
- **Affected ZIP dates:**

| Date | ГРИЗЛИ rows in that ZIP | Status |
|---|---|---|
| 2026-02-23 | 154 | **SWAPPED** — columns 3 and 4 reversed |
| 2026-03-16 | 70 | **SWAPPED** — columns 3 and 4 reversed |
| 2026-04-07 | 1,119 | **SWAPPED** — columns 3 and 4 reversed |

- **All other ZIP dates (78 of 81):** ГРИЗЛИ file has correct column order.

### Root cause

ГРИЗЛИ submits semicolon-delimited files. The `detect_delimiter` function in `src/transform.py`
correctly identifies `;` as the delimiter for ГРИЗЛИ files. However, on the 3 dates listed above,
ГРИЗЛИ's export script swapped the Код на продукта (column 3, product code) and Категория
(column 4, category code) columns in the data rows (the header row remained correctly ordered).

Because `transform.py` reads `row[4]` as the category field, it stored ГРИЗЛИ's 6-digit product
codes in the category slot. These product codes are not in `product-categories.json`, so they were
stored as `(unknown:XXXXXX)` in `dim_category`.

Evidence: The 265 code values in Groups D and E overlap 100% with product codes in
`data/schema/dim_product.csv`. A normal ГРИЗЛИ row from a non-swap date has e.g.
`row[3]='52'` (category), `row[4]='001314'` (product code), while a swap-date row has
`row[3]='52'` (category) in the wrong column and `row[4]='001314'` (product code) read as category.

### Consequence

The ~1,343 fact rows ingested from ГРИЗЛИ on those 3 dates carry structurally incorrect category
assignments. Their `category_key` values point to Groups D/E dimension entries (product codes
stored as categories) rather than the correct category (e.g., category 52 = Плодове и зеленчуци).

These 265 dim_category entries are **orphan entries from the perspective of correct analytics** —
they exist in the dimension table but their meaning is "product code accidentally stored as
category code."

### Recommended action

**Option 1 — Document only (no data change, lowest risk):**  
Retain all dim_category rows as-is. Filter `category_key` values 104–368 out of category-level
analytics (they represent the ГРИЗЛИ column-swap anomaly). Label them as "ГРИЗЛИ — column swap
error (dates: 2026-02-23, 2026-03-16, 2026-04-07)."

**Option 2 — Re-ingest the 3 affected dates (corrects fact rows, higher effort):**  
To restore correct category assignments for the affected fact rows:

1. Identify and back up the existing fact rows with `file_key` values corresponding to
   `2026-02-23.zip/ГРИЗЛИ...`, `2026-03-16.zip/ГРИЗЛИ...`, and `2026-04-07.zip/ГРИЗЛИ...`
   in `data/schema/dim_file.csv`.
2. Delete those fact rows from the relevant fact CSV files.
3. Verify the column order in ГРИЗЛИ's files for those 3 dates (header should confirm:
   column 3 = Код на продукта, column 4 = Категория; data for the 3 swap dates has this reversed).
4. Re-run `transform.py` with corrected handling for those 3 files — either by temporarily
   swapping columns 3 and 4 when reading from those specific dates, or by accepting the data as
   miscategorised (if the original file cannot be corrected).

> Note: Because ГРИЗЛИ corrected the column order after 2026-04-07, all subsequent ZIPs are
> unaffected and do not require re-ingestion.

---

## Group F — Single-occurrence retailer errors

Three entries, each from a distinct one-time anomaly. All have category_key values 370–372
(added in the most recent transform runs).

### F1 — category_code `0`

- **category_key:** 370
- **Source retailer:** T Market (Максима България ЕООД) — file in 2026-05-05.zip
- **Frequency:** Single occurrence (1 row in 1 ZIP).
- **Root cause:** T Market submitted `0` as a category code — likely an export default or null
  placeholder. `0` is outside the valid 1–101 range.
- **Recommended action:** Retain as-is. Single-occurrence anomaly; low impact.

### F2 — category_code `102`

- **category_key:** 371
- **Source:** Not traceable in the current archive (2026-02-15 through 2026-05-06). The entry
  exists in `dim_category.csv`, meaning it was produced during a transform run, but the
  originating ZIP is not present in the current `data/raw/` directory. This may be from a
  pre-archive run or a ZIP that was replaced/removed.
- **Frequency:** Single occurrence; origin date unknown.
- **Recommended action:** Retain as-is. Code `102` is one above the valid maximum (101) and
  likely represents an off-by-one error from an unknown retailer.

### F3 — category_code `Категория`

- **category_key:** 372
- **Source retailer:** Валди (Ви Скай ЕООД) — file in 2026-04-22.zip and 2026-04-23.zip.
- **Frequency:** 2 consecutive days; not present in other ZIPs.
- **Root cause:** The literal word "Категория" (the Bulgarian column header for the category
  field) appeared as a data value in Валди's submission. This is a double-header row artifact —
  the header row was duplicated in the file body, likely caused by a BOM or encoding issue in
  Валди's export script. `transform.py` skips the first line (header), but subsequent header
  duplicates in the data body are read as data rows.
- **Recommended action:** Retain as-is. Two-day anomaly; Валди corrected the issue after
  2026-04-23.

---

## How to filter unknowns in analytics

To exclude all unknown categories from a query on the star schema:

```sql
SELECT * FROM fact_prices
JOIN dim_category ON fact_prices.category_key = dim_category.category_key
WHERE dim_category.category_name NOT LIKE '(unknown:%)'
```

Or, to include only officially-named categories:

```sql
WHERE CAST(dim_category.category_code AS INTEGER) BETWEEN 1 AND 101
```

---

## Traceability

| Group | Evidence location |
|---|---|
| A — empty | Any ZIP: `Кауфланд България_131129282.csv` row with empty column 4 |
| B — -1 | Any ZIP from 2026-03-28 onward: `АВАНТИ (АВАНТИ 777 ЕООД)_105568755.csv` |
| C — 1972047017 | Any ZIP from 2026-04-18 onward: `ТЪРГОВСКА ВЕРИГА ЖАНЕТ (ЖАНЕТ ООД)_102827804.csv` |
| D/E — 6-digit | `data/raw/2026-02-23.zip`, `2026-03-16.zip`, `2026-04-07.zip` — `ГРИЗЛИ (ДИЕЛ ЕООД)_823077024.csv` |
| F1 — 0 | `data/raw/2026-05-05.zip` — `T Market (Максима България ЕООД)_131324923.csv` |
| F2 — 102 | Not in current archive |
| F3 — Категория | `data/raw/2026-04-22.zip`, `2026-04-23.zip` — `Валди (Ви Скай ЕООД)_204454900.csv` |
