Implementation record for request R-20260508-0743.

Files taken into consideration from .aib_memory/:
- .aib_memory/input.md
- .aib_memory/request.md
- .aib_memory/requests_register.md
- .aib_memory/context.md
- .aib_memory/instructions.md

## Implementation Log

### Entry 2026-05-09 11:44
#### Scope
Implemented the root-cause fix for duplicated settlement identities affecting Report 1 category coverage on the React analytics page. The change canonicalizes settlement EKATTE values during transform, adds a UI safeguard for duplicate settlement labels in Report 1, and documents the required local reprocess and Supabase resync path.

#### Changes
- Updated `src/transform.py` to canonicalize settlement codes before `dim_settlement` natural-key assignment so equivalent EKATTE variants collapse to one settlement identity.
- Added focused regression coverage in `tests/test_transform.py` for padded EKATTE normalization, 5-digit padding, and raion-suffix preservation.
- Updated `react-app/src/lib/dataService.js` so settlement options gain a `displayLabel` and duplicate visible names are disambiguated with EKATTE.
- Updated `react-app/src/components/Report1.jsx` to render the disambiguated settlement label in the dropdown.
- Added React regression tests in `react-app/src/lib/dataService.test.js` and `react-app/src/components/Report1.test.jsx` for duplicate-name settlement handling.
- Updated `README.md` and `.aib_memory/context.md` with the settlement-normalization behavior and the required transform-plus-sync operator workflow.

#### Tests
- unit: `venv/bin/python -m pytest tests/test_transform.py -q` — pass (27 passed).
- unit: `cd react-app && npm test -- --run src/lib/dataService.test.js src/components/Report1.test.jsx` — pass (30 passed).
- verification: local schema evidence check for Sofia duplicate settlements — pass (`68134` mapped to 103 categories and `068134` mapped to 2 categories before reprocessing).
- verification: raw ZIP sample over the latest 15 archives — pass (`68134` and `068134` both observed in source rows, with materially different category coverage).

#### Outcome
Successful implementation. New transform runs will stop creating analytically split settlement identities for padded EKATTE variants, and Report 1 now makes duplicate settlement labels explicit when stale remote data still contains duplicates. Existing local and remote derived data still require a transform rerun and Supabase resync to remove already-materialized duplicate settlement rows.

#### Evidence
- Files: `src/transform.py`, `tests/test_transform.py`, `react-app/src/lib/dataService.js`, `react-app/src/components/Report1.jsx`, `react-app/src/lib/dataService.test.js`, `react-app/src/components/Report1.test.jsx`, `README.md`, `.aib_memory/context.md`
- Local schema verification:
  ```text
  settlement_key=261 ekatte=068134 categories=2 stores=1
  settlement_key=7 ekatte=68134 categories=103 stores=1548
  ```
- Raw ZIP verification:
  ```text
  code=068134 rows=605 categories=2 sample_files=['2026-04-23.zip/ALEXFISH (ЕТ АЛЕКС-АЛЕКСАНДЪР ХРИСТОВ СПАСОВ)_831314284.csv', '2026-04-24.zip/ALEXFISH (ЕТ АЛЕКС-АЛЕКСАНДЪР ХРИСТОВ СПАСОВ)_831314284.csv', '2026-04-27.zip/ALEXFISH (ЕТ АЛЕКС-АЛЕКСАНДЪР ХРИСТОВ СПАСОВ)_831314284.csv']
  code=68134 rows=5988898 categories=104 sample_files=['2026-04-23.zip/AVON (Ейвън Козметикс България ЕООД)_121902485.csv', '2026-04-23.zip/DOUGLAS (ПАРФЮМЕРИ ДЪГЛАС БЪЛГАРИЯ ЕООД)_131507508.csv', '2026-04-23.zip/DS HOME (ДИ ЕС ХОУМ ООД)_124134610.csv']
  ```

#### Notes (Optional)
The current local schema still contains both Sofia settlement rows because the existing derived CSVs were produced before the canonicalization change. Re-run `python3 src/transform.py` and `python3 src/load_supabase.py` to materialize the corrected identity model end to end.