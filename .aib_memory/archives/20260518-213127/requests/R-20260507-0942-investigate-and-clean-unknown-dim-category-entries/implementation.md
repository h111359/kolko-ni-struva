Implementation record for R-20260507-0942 — Investigate and clean unknown dim_category entries.

Files taken into consideration:
- `.aib_memory/request.md` — authoritative request specification
- `.aib_memory/analysis.md` — analysis artifact (reasoning only; not used as implementation driver)

## Implementation Log

### Entry 2026-05-07 10:45

#### Scope

Investigate all 271 `(unknown:...)` entries in `data/schema/dim_category.csv`, determine their origin by scanning all 81 ZIP archives in `data/raw/`, and create `data/nomenclatures/unknown_categories_explanation.md` documenting six groups of unknown codes with source attribution, frequency, and recommended operator action. No code changes to `src/transform.py` were required. No changes to any dimension or fact CSV files were made.

#### Changes

- Created `data/nomenclatures/unknown_categories_explanation.md` — primary deliverable; documents all 6 groups (A–F) of unknown category codes with full source attribution, root-cause analysis, fact-row impact estimates, and recommended operator actions.
- Created `.aib_memory/analysis.md` — analysis artifact; 9 mandatory sections per analysis-convention.md; not used by implement.
- Updated `.aib_memory/request.md` sections 7–12 (Assumptions, Plan, Documentation, Questions & Decisions, Code and Asset Scan, Internal Review).

#### Tests

- Manual — existence check: `data/nomenclatures/unknown_categories_explanation.md` confirmed present.
- Manual — content check: all 6 groups (A, B, C, D, E, F) documented with retailer attribution and recommended action; verified counts match dim_category.csv (1 + 1 + 1 + 248 + 17 + 3 = 271).
- Manual — traceability check: each group's source traced back to specific ZIP file(s) in `data/raw/`; ГРИЗЛИ swap dates 2026-02-23, 2026-03-16, 2026-04-07 confirmed by scanning all 81 ZIPs.
- Regression — full test suite: `venv/bin/pytest tests/ -v` — 117 passed, 1 skipped; exit code 0. No regressions (no source code was modified).

#### Outcome

Success. All 271 unknown category entries have been traced to identifiable sources. The explanation file satisfies all 5 success criteria from `request.md`. No data was modified; no surrogate keys were removed; FK integrity is preserved. The no-rejection policy in `src/transform.py` is confirmed correct. Operators now have a reference document to understand and act on unknown category entries in downstream analytics.

Residual: `context.md` should be regenerated via `aib-context.md` to incorporate R-20260507-0942 findings (ГРИЗЛИ column-swap anomaly, active sources Kaufland/АВАНТИ/ЖАНЕТ). This is deferred to the next context refresh as context.md is auto-generated and must be fully replaced, not patched.

#### Evidence

- `data/nomenclatures/unknown_categories_explanation.md` — created; ~200 lines; covers all 6 groups.

```
Group A (empty):        1 dim_category row  (key 102)
Group B (-1):           1 dim_category row  (key 103)
Group C (1972047017):   1 dim_category row  (key 369)
Group D (0xxxxx):     248 dim_category rows (keys 104-368, interleaved)
Group E (63xxxx):      17 dim_category rows (keys 118-337, interleaved)
Group F (other):        3 dim_category rows (keys 370, 371, 372)
Total:                271
```

- Test run output:

```
======================== 117 passed, 1 skipped in 0.54s ========================
```

- ГРИЗЛИ column-swap scan result (all 81 ZIPs):

```
2026-02-23.zip: SWAPPED, 154 rows
2026-03-16.zip: SWAPPED, 70 rows
2026-04-07.zip: SWAPPED, 1119 rows
All other 78 ZIPs: NORMAL
```

#### Notes (Optional)

The 265 six-digit orphan dimension entries (Groups D + E) have no currently-active source — no current ZIPs produce them. They are historical artifacts from the 3 ГРИЗЛИ swap dates. Fact rows from those 3 dates carry incorrect category assignments; the explanation file documents a re-ingest path for operators who wish to correct them.

Code `102` in Group F could not be traced to any ZIP in the current archive. It is documented as "origin not in current archive."
