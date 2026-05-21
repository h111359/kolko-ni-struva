# Data Profile — R-20260419-0854

> Generated: 2026-04-19 by aib-analysis.md re-run.
> Source: `data/raw/` (63 ZIP archives, 2026-02-15 – 2026-04-18).
> All statistics are based on full scans of the first and last ZIP, deep scans of 5 sampled ZIPs, and filename-level scans of all 63 ZIPs.

---

## 1. ZIP Inventory

| Attribute | Value |
|---|---|
| Total ZIPs | 63 |
| Date range | 2026-02-15 → 2026-04-18 |
| CSV files per ZIP (min) | 182 |
| CSV files per ZIP (max) | 216 |
| CSV files per ZIP (mean) | 207.8 |
| CSV files per ZIP (stdev) | 4.9 |
| Total CSV files (all ZIPs) | 13,089 |

---

## 2. Company / UIC Profile

| Attribute | Value |
|---|---|
| Unique UICs across all ZIPs | 217 |
| Unique company names across all ZIPs | 217 |
| Companies present in ALL 63 ZIPs | 128 |
| Companies present in some ZIPs (2–62) | 89 |
| Companies present in exactly one ZIP | 0 |

- UIC and company name are 1:1 (no UIC re-uses a different name or vice-versa in the sampled data).
- 128 companies are "permanent participants"; 89 appear sporadically (joined or left during the period).

---

## 3. Row Count Profile

| Source | Valid rows (7-column) |
|---|---|
| 2026-02-15 (first ZIP) | 1,278,026 |
| 2026-03-02 (sample) | 1,119,243 |
| 2026-03-17 (sample) | 1,234,829 |
| 2026-04-01 (sample) | 1,536,746 |
| 2026-04-18 (last ZIP) | 1,337,288 |
| **Estimated total (all 63 ZIPs)** | **~82,000,000** |

- Average rows per ZIP across 5-sample: ~1,301,226.
- Estimated total fact rows: **~82 million**.

### ⚠️ Critical size implication

At ~45–60 bytes per CSV row, a single `fact_prices.csv` is estimated at **~3.4–4.9 GB**.
This conflicts with the "minimal space" and "human readable" constraints as a single flat file.
See [Section 9 — Design Implications](#9-design-implications) for recommended partitioning strategy.

---

## 4. Row-Level Data Quality

### 4.1 Column Count / Delimiter Issues

Three to four CSV files per ZIP (consistently the same companies across all 63 ZIPs) use **semicolons** as the field delimiter instead of commas. The ZIP header row is standard but data rows are single-column with semicolon-separated values.

| Date | Semicolon-delimited files |
|---|---|
| 2026-02-15 | 3 |
| 2026-02-16 | 4 |
| 2026-02-17 | 4 |
| 2026-02-18 | 4 |
| … | 2–4 (all ZIPs) |

**Confirmed offenders (2026-02-15):**
- `Бакалия (Бакалия 2014 ООД)_202935695.csv` — semicolons, BOM (`\ufeff`) in header
- `ГРИЗЛИ (ДИЕЛ ЕООД)_823077024.csv` — semicolons
- `Маркет Диана (ДИАНА 77 ООД)_128614343.csv` — semicolons

**Impact:** ~2,000–3,600 column-count errors per ZIP (roughly consistent with these companies' row counts). These rows are silently skipped with comma-based `csv.reader`. The transformation script MUST detect and re-parse files that produce single-column rows by falling back to a semicolon delimiter (`csv.reader(..., delimiter=';')`).

### 4.2 Category Code Anomalies

The category "unknown" rows (0.01% of total) are caused by:
- Empty category field: 69 rows
- Category values with leading spaces and stray quote characters (e.g., `' "86'`, `' "87'`): 9 × 3 rows = 27 rows — likely a CSV quoting edge-case in one specific company's file.

**Impact:** Negligible. ~100 rows out of 1.28M in one ZIP — well under 0.01%.

### 4.3 Price Anomalies

| Price condition | Count (2026-02-15 full ZIP) |
|---|---|
| Price = 0.00 | 383 |
| Price < 0 | 0 |
| Price > 100 | 0 |
| Max observed price | 277.00 BGN |
| Parse failures (non-numeric) | 105 |

- 383 zero-price rows likely represent items that are "free" or have a data entry error; they should be retained without filtering as-is.
- No negative prices found (good).
- No prices above 277 BGN in the sampled ZIP.

---

## 5. Price Statistics (2026-02-15 full ZIP)

| Statistic | Value (BGN) |
|---|---|
| Minimum | 0.00 |
| Maximum | 277.00 |
| Median | 3.27 |
| Mean | 4.98 |
| Total priced rows | 1,277,921 |
| Promo price filled | 448,046 (35.1%) |
| Promo price empty | 829,980 (64.9%) |

### Price distribution (sample of 20 companies):

| Price range (BGN) | Row count |
|---|---|
| 0 | 0 |
| < 1.00 | 12,769 |
| 1.00 – 4.99 | 53,810 |
| 5.00 – 9.99 | 19,753 |
| 10.00 – 49.99 | 14,401 |
| 50.00 – 99.99 | 164 |
| ≥ 100 | 0 |

- The bulk of prices are in the 1–5 BGN range (everyday grocery staples).
- ~35% of rows carry a promotional price — significant enough to model `promo_price` as a first-class column.

---

## 6. EKATTE Coverage

| Attribute | Value |
|---|---|
| Unique EKATTE codes in `cities-ekatte-nomenclature.json` | 5,256 |
| Unique EKATTE codes found in data (2026-02-15) | 256 |
| Codes matched in nomenclature | 238 (93.0%) |
| Codes NOT in nomenclature | 18 (7.0% of codes, 0.55% of rows) |

### Unknown EKATTE codes (top 10 by row count):

| Code | Row count | Pattern |
|---|---|---|
| `68134-01` | 1,600 | Sofia sub-district (raion) code |
| `7079` | 784 | Short numeric code (not in ek_atte.json) |
| `68134-04` | 773 | Sofia sub-district |
| `68134-10` | 465 | Sofia sub-district |
| `702` | 345 | Short numeric code |
| `98226` | 335 | Unknown |
| `68134-09` | 321 | Sofia sub-district |
| `68134-02` | 321 | Sofia sub-district |
| `4279` | 312 | Short numeric code |
| `7702` | 296 | Short numeric code |

**Finding:** The `68134-XX` pattern are **Sofia district (raion) codes**. `sof_rai.json` contains the authoritative list of these sub-district codes (38 entries, e.g., `68134-21`, `68134-24`). The transformation script can map all `68134-XX` codes to "София" (EKATTE 68134) or, better, to the district name if `sof_rai.json` is consulted. The short numeric codes (702, 2508, 4501, etc.) suggest retailer-side data entry errors.

**Impact:** 0.55% of rows use unknown EKATTE codes. These should be labelled `(unknown)` in `dim_settlement` unless enriched via `sof_rai.json`.

---

## 7. Category Coverage

| Attribute | Value |
|---|---|
| Unique category codes in nomenclature | 101 |
| Unique category codes found in data | 118 (as of 2026-02-15) |
| Expected category id range | 1 – 101 |
| Codes matched in nomenclature | 101 (found) |
| Codes NOT matched | 17 edge-case values |

- 0.01% of rows use unresolvable category codes; these should be labelled `(unknown)` in `dim_category`.

---

## 8. Product Code Diversity

| Attribute | Value |
|---|---|
| Unique product codes in 2026-02-15 ZIP | 83,404 |
| Top product code occurrence | 326 rows per code (typical for ~200-store chain) |

- Product codes appear to be **retailer-local** — the same numeric code can appear for different products across different companies.
- `dim_product` grain must be `(product_code, product_name)` pair, not product_code alone.
- Expected `dim_product` size: tens of thousands to low hundreds of thousands of rows across all ZIPs.

---

## 9. Design Implications

### 9.1 Fact Table Partitioning (Critical)

A single `fact_prices.csv` would be **~3.4–4.9 GB** — not consistent with "minimal space, human readable". Recommended resolution:

**Option A (recommended):** Partition the fact table by date into `data/schema/facts/YYYY-MM-DD.csv`. Each file is ~54–78 MB. The folder remains browsable; any single file is "human readable" in a text editor or spreadsheet.

**Option B:** Write a single `fact_prices.csv.gz` (gzip-compressed). Size reduces to ~400–700 MB. Readable via `zcat` or `gzip -d` but adds a decompression step.

**Option C:** Accept the 3.4 GB flat file as-is and document the size constraint. Analytical tools (pandas, Excel, DuckDB) can handle this but text editors cannot.

The implementation plan should be updated to reflect the chosen option (default recommendation: Option A — date-partitioned facts).

### 9.2 Semicolon Delimiter Handling (Required)

The transformation script must implement **auto-delimiter detection**: attempt comma-delimited parsing; if the first data row produces 1 column and contains semicolons, re-read using semicolons. Also strip BOM (`\ufeff`) from headers.

### 9.3 Sofia District Enrichment (Optional but recommended)

Supplement `cities-ekatte-nomenclature.json` with `sof_rai.json` data to resolve `68134-XX` codes to district names rather than labelling them `(unknown)`.

### 9.4 Product Code Grain

`dim_product` keyed on `(product_code, product_name)` pair to avoid inter-company product code collisions. First-seen canonical name per pair.

---

## 10. Nomenclature Summary

| File | Records | Used for |
|---|---|---|
| `cities-ekatte-nomenclature.json` | 5,256 | EKATTE → settlement name |
| `product-categories.json` | 101 | category id → category name |
| `Ekatte/ek_atte.json` | 5,257 | Full EKATTE registry with oblast/obshtina |
| `Ekatte/sof_rai.json` | 38 | Sofia sub-district (raion) codes |
| `Ekatte/ek_raion.json` | 36 | Varna district codes |
