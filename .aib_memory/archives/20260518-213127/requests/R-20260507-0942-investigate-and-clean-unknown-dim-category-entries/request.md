## Goal

Investigate the 271 unknown category entries in `data/schema/dim_category.csv` and either clean the entries that are genuinely invalid or document in a dedicated explanation file where each group of unknown codes came from, so operators understand the data lineage and can make informed decisions about retention or removal.

## Background

The `dim_category` table is a star-schema dimension that maps a surrogate `category_key` to a `category_code` and `category_name`. The Bulgarian government portal publishes a fixed set of 101 mandatory retail-price categories (IDs 1–101) defined in `data/nomenclatures/product-categories.json`. When `src/transform.py` encounters a category code in a raw retailer CSV that does not match any entry in that JSON, it records the entry as `(unknown:<code>)`.

As of the latest transform run, `dim_category.csv` contains 372 rows total, 271 of which are `(unknown:...)` entries. This is ~73% of the dimension — a significant proportion that erodes trust in category-level analytics. The user has listed 38 sample codes in the input and asks to either clean those that are not real or explain in a file where they came from.

Two sentinel entries also exist:
- category_key=102: empty category_code (`(unknown:)`)
- category_key=103: category_code=-1 (`(unknown:-1)`)

## Scope

- Analyse all 271 unknown category entries in `data/schema/dim_category.csv` to determine their origin.

- Investigate the raw ZIP archives in `data/raw/` (or `lab/`) to confirm which CSV files produce the non-standard category codes and what format those codes take in the raw data.

- Create `data/nomenclatures/unknown_categories_explanation.md` documenting:
  - Where the unknown codes come from (which retailer files, which raw-data column, which structural anomaly)
  - How many fact rows reference unknown category keys
  - What the operator should do (retain as-is, delete fact rows, patch nomenclature, or ignore)

- If any unknown codes are verifiably erroneous (e.g., the empty code and -1 code), document the recommended remediation.

- Update `src/transform.py` if a structural fix is feasible and clearly safe within this request (e.g., filtering or logging improvements for the empty/negative sentinel codes).

## Out of scope

- Bulk deletion of fact rows referencing unknown categories — no destructive data operations without explicit operator confirmation.

- Adding the unknown codes to `product-categories.json` as new official categories — that requires authoritative source confirmation from the government portal.

- Changes to the React app or Supabase sync.

- Modifying the no-rejection policy (architectural decision #4 in context.md).

## Constraints

- Python stdlib only for `src/transform.py` (architectural decision #5 in context.md).
- Atomic file writes required — all CSV modifications must use `.partial` → rename pattern.
- The `category_key` surrogate values in `dim_category.csv` are stable references from existing fact CSVs; removing rows would break FK integrity in the star schema.
- Do not create a Python virtual environment.
- Do not install additional libraries.

## Success criteria

1. `data/nomenclatures/unknown_categories_explanation.md` exists and explains the origin of the unknown category codes with at least: (a) source identification (which retailer/file type produces them), (b) frequency per group, (c) recommended operator action.

2. The explanation file is factually accurate — the stated origin can be traced back to evidence in the raw data (lab CSVs or raw ZIPs).

3. If a safe, clearly scoped fix is identified for the empty/sentinel codes (empty and -1), it is implemented in `src/transform.py` and documented.

4. All existing tests continue to pass after any changes.

5. The operator reading the explanation file can make an informed decision without needing further investigation.

## Assumptions

1. The 81 ZIP archives in `data/raw/` are a complete and unmodified copy of the government portal's published data for the covered date range (2026-02-15 through 2026-05-06).

2. The `dim_category.csv` surrogate keys are stable references in existing fact CSVs; removing rows would break FK integrity, so no rows are deleted.

3. A documentation-only deliverable fully satisfies the user's request. No code changes to `src/transform.py` are required to meet all success criteria.

4. ГРИЗЛИ (ДИЕЛ ЕООД) has since corrected the column-swap export bug (no swap present in any ZIP after 2026-04-07); therefore, no new 6-digit unknown category codes will be produced by future runs against existing ZIPs.

5. The origin of `category_code='102'` cannot be traced to a specific ZIP in the current archive; it is documented as "origin not identified in current archive."

6. The explanation file is a point-in-time snapshot as of 2026-05-07; it will require manual update if new unknown categories appear in future runs.

## Plan

### Phase 1 — Research (completed during analysis)
- T1.1 ✅ Analysed `dim_category.csv` (372 rows, 271 unknowns)
- T1.2 ✅ Scanned all 81 ZIPs to identify active non-standard category codes
- T1.3 ✅ Confirmed ГРИЗЛИ column-swap dates (2026-02-23, 2026-03-16, 2026-04-07) across all 81 ZIPs
- T1.4 ✅ Confirmed delimiter detection is correct for all ГРИЗЛИ files
- T1.5 ✅ Confirmed 6-digit codes overlap 100% with `dim_product.category_code`
- T1.6 ✅ Confirmed codes `Категория` (Валди) and `0` (T Market) origin ZIPs

### Phase 2 — Documentation deliverable
- T2.1 Create `data/nomenclatures/unknown_categories_explanation.md` with all six groups documented

### Phase 3 — Verification
- T3.1 Run `python -m pytest tests/` and confirm all tests pass (no code was changed, regression check is formal)

### Phase 4 — Closure
- T4.1 Update `.aib_memory/context.md` with R-20260507-0942 findings
- T4.2 Write `implementation.md` in the request folder
- T4.3 Run `move-request-artifacts.py` and `close-request.py`

## Documentation

- **New file:** `data/nomenclatures/unknown_categories_explanation.md` — primary deliverable; explains all six groups of unknown category codes with source attribution, frequency, and recommended operator action.

- **Updated:** `.aib_memory/context.md` — add entry for R-20260507-0942 findings (ГРИЗЛИ column-swap anomaly, known active sources Kaufland/АВАНТИ/ЖАНЕТ).

## Questions & Decisions

- **Q001 (Resolved — autonomous):** Should `src/transform.py` be modified to log or filter sentinel codes (empty, -1, large integers)?
  - **Decision:** No code change. The no-rejection policy is architecturally correct. The explanation file is sufficient for the stated goal. A future request can add warning logs if desired.

- **Q002 (Resolved — autonomous):** Should the orphan dim_category rows from ГРИЗЛИ swap dates be deleted?
  - **Decision:** No deletion. Removing surrogate keys would break FK integrity in existing fact CSVs. The explanation file documents the re-ingest path for operators who wish to correct the affected fact rows.

- **Q003 (Resolved — autonomous):** Is the origin of `category_code='102'` traceable?
  - **Decision:** Not traceable from current ZIP archive. Documented as "origin not in current archive; likely from a pre-archive or replaced ZIP." No further investigation needed.

## Code and Asset Scan for Impacted Components

- `src/transform.py` — read-only; no changes required.
- `data/schema/dim_category.csv` — read-only; no changes required.
- `data/nomenclatures/product-categories.json` — read-only; no changes required.
- `data/nomenclatures/unknown_categories_explanation.md` — new file; created by this request.
- `.aib_memory/context.md` — updated with request findings.

## Internal Review of Request and Product Docs

- Goal, Scope, Success Criteria, and Constraints sections verified against analysis findings — all consistent.
- No scope creep detected; the explanation file covers exactly the stated scope.
- Success criteria 1–5 are all achievable by the documentation-only deliverable.
- No contradictions identified between this request and architectural decisions in `context.md`.
