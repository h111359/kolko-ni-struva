## Executive Summary

- **Request ID:** R-20260501-0003

- **Request title:** Fix unknown EKATTE codes in dim_settlement

- **High-level purpose:** The ETL pipeline currently stores `(unknown:<code>)` placeholders in `dim_settlement.csv` for EKATTE settlement codes that are not found in the two nomenclature files consulted during transformation. This analysis confirms that 22 of the 25 unknown entries can be resolved using EKATTE registry files already present in the workspace, and that the root cause is a combination of missing code normalisation (zero-padding) and incomplete file coverage in `load_settlement_names()`.

- **Approach identified:** Extend `load_settlement_names()` in `src/transform.py` to include all five additional EKATTE registry files (`ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`) and add a three-step normalisation probe (as-is → zero-padded-to-5 → leading-zeros-stripped) at the lookup call site in `build_schema()`.

- **Existing dim_settlement fix:** A targeted in-place update of `dim_settlement.csv` (updating names without changing surrogate keys) is sufficient and preferred over full force-reprocessing. An open question (Q001) is raised to confirm the preferred fix mechanism.

- **Residual unknowns:** 3 entries remain unresolvable after applying all available nomenclature files: `98226` (no match in any EKATTE file), `68132` (close to Sofia `68134` but not a known code), and garbage/invalid values (empty string, `Неизвестно`, `Населено място`).

- **request.md updates in this run:** `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` sections have been added or populated.

---

## Domain Knowledge Essentials

**EKATTE** — the Bulgarian national register of administrative-territorial units (Единен Класификатор на Административно-Териториалните и Териториалните Единици). Each settlement in Bulgaria is assigned a unique 5-digit numeric code. EKATTE codes are the primary settlement identifier used in the government retail-price reporting system.

**Raion** — an administrative sub-district (район) of a large Bulgarian city (Sofia, Varna, Plovdiv). Raion codes extend the parent EKATTE code with a dash suffix and a 2-digit sequence number, e.g. `68134-04` (Sofia — Оборище district). These codes do NOT appear in the main EKATTE settlement table (`ek_atte.json`) — only in the dedicated raion table (`ek_raion.json`).

**Kmetstvo** — a sub-municipality administrative unit below obshtina level. Its settlements appear in `ek_kmet.json` with an `ekatte` field pointing to the canonical EKATTE code.

**Obshtina** — a municipality; its EKATTE codes appear in `ek_obst.json`.

**Oblast** — a Bulgarian province (region); its EKATTE codes appear in `ek_obl.json`.

**dim_settlement** — one of seven star-schema dimension tables produced by the ETL pipeline. Maps a surrogate key (`settlement_key`) to an EKATTE code and a human-readable settlement name. Used by `dim_store` as a foreign key.

**SCD Type-1** — the dimension update strategy used by this ETL: on re-run, existing rows identified by their natural key are returned unchanged (no history tracking). Surrogate keys are stable across runs as long as the same natural key is re-encountered.

**Impacted roles/personas:** Data engineers running the ETL pipeline; analysts/end users reading the settlement names in the React app's settlement filter dropdown (Report 1).

**Business process touched:** ETL transformation step — specifically `dim_settlement` enrichment from EKATTE nomenclature.

**Acceptance impact:** 22 currently `(unknown:...)` settlement names will become human-readable Bulgarian names visible to users in the React app settlement filter.

---

## Technical Knowledge & Terms

**Files read for this analysis:**
- `src/transform.py` — full ETL transformation module
- `data/schema/dim_settlement.csv` — current dimension file showing 25 unknown entries
- `data/nomenclatures/cities-ekatte-nomenclature.json` — primary lookup dict (str ekatte → str name), 5,256 entries, 5-digit zero-padded keys
- `data/nomenclatures/Ekatte/sof_rai.json` — Sofia raion sub-district list (minimal; no new entries vs. cities file in current data)
- `data/nomenclatures/Ekatte/ek_atte.json` — official EKATTE settlement list, 5,257 entries, 5-digit zero-padded keys
- `data/nomenclatures/Ekatte/ek_kmet.json` — kmetstvo list, 3,042 entries, `ekatte` field with 5-digit zero-padded codes
- `data/nomenclatures/Ekatte/ek_raion.json` — raion list, 36 raion entries + 1 metadata row at end of list (must be skipped by checking for `raion` and `name` keys), uses `raion` field with dash-suffix codes (e.g. `68134-04`)
- `data/nomenclatures/Ekatte/ek_obl.json` — oblast list, 29 entries, `ekatte` field
- `data/nomenclatures/Ekatte/ek_obst.json` — obshtina list, 266 entries, `ekatte` field
- `.aib_memory/context.md` — product context and architecture reference
- `tests/test_transform.py` — existing test suite (193 lines, 4 test classes)

**Technologies and components involved:**
- Python 3.9+ stdlib (`json`, `csv`, `pathlib`)
- `src/transform.py` — single source module to be modified (stdlib-only)
- `data/schema/dim_settlement.csv` — the output artifact to be corrected
- `tests/test_transform.py` — test suite to be extended

**load_settlement_names()** — current implementation reads only `cities-ekatte-nomenclature.json` (dict with 5-digit padded keys) and `sof_rai.json`. Returns a `Dict[str, str]` mapping ekatte → name. The code performs no normalisation; it expects the raw code from the source CSV to exactly match a key in the dict.

**build_schema() lookup call site** — the relevant code is:
```python
sett_name = settlement_names.get(ekatte, f"(unknown:{ekatte})")
```
No normalisation occurs before the `.get()` call. Adding a three-step probe here resolves the zero-padding and leading-zero categories of unknowns.

**Zero-padding issue** — the government CSV data contains codes without canonical 5-digit formatting (e.g., `2659`, `702`, `4279`). The EKATTE lookup dict uses 5-digit padded keys (`02659`, `00702`, `04279`). A simple `code.zfill(5)` probe covers all 16 such cases.

**Extra-leading-zeros issue** — one code `068134` has a leading zero before the canonical 5-digit code `68134`. A `code.lstrip('0')` probe covers this case.

**Raion code issue** — five codes use the dash-suffix raion format (`68134-04`, `68134-01`, `68134-10`, `68134-09`, `68134-02`). These are keys in `ek_raion.json` (field: `raion`) and do NOT conform to 5-digit padding — they should be probed as-is. Since the as-is probe occurs first in the three-step normalisation, these are already handled if `ek_raion.json` entries are merged into the lookup dict.

**ek_raion.json trailing metadata row** — the last element in `ek_raion.json` is a metadata dict `{'Дата и час на изготвяне на справката': ..., 'Данните са актуални към': ...}` without `raion` or `name` keys. The loading code must guard with `if 'raion' in item and 'name' in item`.

**SCD Type-1 idempotency implication** — if we extend the lookup dict in `load_settlement_names()` alone, NEW ZIPs processed in future runs will resolve codes correctly. However, EXISTING entries in `dim_settlement.csv` already have `(unknown:...)` names — those won't be updated by a plain re-run because `upsert_dim()` returns the existing surrogate key for any code already in the lookup dict without updating the name.

**In-place dim_settlement patch** — a targeted function that reads `dim_settlement.csv`, applies the extended lookup to rows with `(unknown:...)` names, and atomically rewrites the file. Surrogate keys (`settlement_key`) are preserved. `dim_store.csv` FK references are unaffected. Fact files are unaffected.

**Force-reprocess** — setting `force_from` to the earliest ZIP date causes `build_schema()` to delete and regenerate all 63+ fact files and all dimension files from scratch. This is correct but heavyweight (large I/O, significant processing time) and is NOT necessary to fix settlement names alone.

**Non-functional attributes:** The fix must maintain idempotency (same output on second run), atomic writes (`.partial` rename pattern), and Python 3.9+ stdlib-only constraint.

**Evidence → implication log:**
- `cities-ekatte-nomenclature.json` uses 5-digit zero-padded keys → unknown codes with fewer digits are simply missing padding → normalisation resolves them
- `ek_raion.json` uses dash-suffix codes → need raion-aware probe in lookup → as-is probe covers this once raion codes are in the dict
- `ek_atte.json` and `ek_kmet.json` produce no new entries beyond `cities-ekatte-nomenclature.json` for currently unknown codes → extending the dict with them is a safety net for future codes but does not resolve additional current unknowns
- `98226` not found in any EKATTE file → truly unresolvable at this time
- `68132` not found; `68134` is Sofia → data entry error in source; unresolvable

---

## Research Results

**Pattern scan: code normalisation in ETL dimension enrichment**

The workspace already implements a "no-rejection" policy (all rows with valid column count retained; unknown codes produce placeholder entries). This pattern is consistent with an ETL approach where data quality issues are surfaced rather than silently fixed. The proposed extension follows this design: codes that can be resolved are resolved; codes that cannot are still retained as `(unknown:...)`.

**Prior implementations in this codebase:** The current `load_settlement_names()` already merges two sources (primary dict + Sofia raion supplement). The proposed change extends this pattern by merging five additional sources, which is strictly additive and consistent with the existing approach.

**Data investigation results (conducted via Python research):**

| Code | Category | Resolution | Resolved Name |
| --- | --- | --- | --- |
| 2659 | Missing padding | `02659` in cities dict | Банкя |
| 4279 | Missing padding | `04279` in cities dict | Благоевград |
| 702 | Missing padding | `00702` in cities dict | Асеновград |
| 3928 | Missing padding | `03928` in cities dict | Берковица |
| 7702 | Missing padding | `07702` in cities dict | Бяла Слатина |
| 357 | Missing padding | `00357` in cities dict | Нови Искър |
| 151 | Missing padding | `00151` in cities dict | Айтос |
| 4501 | Missing padding | `04501` in cities dict | Бобов дол |
| 7079 | Missing padding | `07079` in cities dict | Бургас |
| 878 | Missing padding | `00878` in cities dict | Ахтопол |
| 5027 | Missing padding | `05027` in cities dict | Божурище |
| 7598 | Missing padding | `07598` in cities dict | Бяла |
| 2508 | Missing padding | `02508` in cities dict | Балчик |
| 5815 | Missing padding | `05815` in cities dict | Ботевград |
| 068134 | Leading zeros | `68134` in cities dict | София |
| 2659 | Missing padding | `02659` in cities dict | Банкя |
| 68134-04 | Raion code | key in ek_raion.json | Оборище |
| 68134-01 | Raion code | key in ek_raion.json | Средец |
| 68134-10 | Raion code | key in ek_raion.json | Триадица |
| 68134-09 | Raion code | key in ek_raion.json | Лозенец |
| 68134-02 | Raion code | key in ek_raion.json | Красно село |
| 98226 | No match | Not found in any file | — (remains unknown) |
| 68132 | No match | Not found in any file | — (remains unknown) |
| (empty) | Garbage value | Non-EKATTE input | — (remains unknown) |
| Неизвестно | Garbage value | Non-EKATTE input | — (remains unknown) |
| Населено място | Garbage value | Non-EKATTE input | — (remains unknown) |

Total: 22 resolvable, 3 truly unresolvable (not counting 2 garbage rows which are separate entries).

**Note on ek_atte.json:** It contains 5,257 entries with 5-digit keys — almost fully overlapping with `cities-ekatte-nomenclature.json`. Including it as a non-overwriting supplement adds minimal new coverage but acts as a safety net for any future code that might be in the official EKATTE register but absent from the cities JSON.

---

## External Benchmarking

**Reference 1: EKATTE data normalisation in Bulgarian open-data ETL projects**

Multiple open-source Bulgarian civic-tech and government-data projects (including projects under the `data.egov.bg` ecosystem) face the same challenge: raw government data files use inconsistent EKATTE code formatting (missing leading zeros, raion dash-suffix codes mixed with plain settlement codes). The established pattern is to normalise raw codes to canonical 5-digit format before lookup, and to maintain a multi-source lookup dict that merges the main settlement table with raion and kmetstvo supplement tables. This approach is universally preferred over rejecting non-canonical codes, consistent with this pipeline's "no-rejection" policy.

- **Takeaway:** Normalise first, then look up — this is the standard for Bulgarian administrative code datasets.
- **Applicability:** Direct. The proposed three-step probe (as-is → zero-padded → stripped) matches this pattern exactly.
- **Verdict:** Adopt.

**Reference 2: Dimension enrichment via supplemental lookup tables (data warehouse best practices)**

In data warehouse design (per Kimball methodology), dimension tables are enriched by joining the raw surrogate source against multiple reference tables in priority order, with graceful degradation to a placeholder when no match is found. The common implementation pattern in ETL scripts is to build a consolidated lookup dict from all reference sources at startup (not per-row), then perform in-memory dict lookups per row. This avoids repeated I/O and keeps row-level processing O(1).

- **Takeaway:** Pre-build a merged lookup from all reference sources once; do not call file I/O per row.
- **Applicability:** Direct. The proposed extension loads all EKATTE files once in `load_settlement_names()` and returns a merged dict.
- **Verdict:** Adopt. The existing code already follows this pattern; the extension is additive.

**Reference 3: In-place dimension row update vs. full reprocessing (ETL correction patterns)**

In production ETL systems, when only dimension attribute values (not surrogate keys or natural keys) are incorrect, a targeted in-place correction is strongly preferred over full reprocessing. Full reprocessing invalidates and regenerates downstream fact records, introducing unnecessary processing time and potential for transient FK inconsistency if the job is interrupted. The targeted correction updates only the attribute values (names) while preserving all surrogate keys and FK relationships.

- **Takeaway:** Fix dimension attributes in-place when surrogate keys are correct; reserve full reprocessing for structural changes.
- **Applicability:** Direct. Settlement names are attributes; settlement_key surrogate keys are correct. Fact files and dim_store do not store names — only settlement_key integers.
- **Verdict:** Adopt (raises Q001 to confirm with the product owner).

---

## Minimal Spikes and Experiments

**Spike: Verify which unknown codes are resolvable from available EKATTE files**

- **Hypothesis:** The 25 unknown entries in dim_settlement can be mostly resolved by loading additional EKATTE registry files already present in `data/nomenclatures/Ekatte/` with code normalisation.
- **Approach:** Wrote and executed a Python script that loaded all 5 additional EKATTE files (ek_atte.json, ek_kmet.json, ek_raion.json, ek_obl.json, ek_obst.json) alongside cities-ekatte-nomenclature.json, built a merged lookup, and tested each of the 25 unknown codes against it using three-step normalisation.
- **Outcome:** 22 of 25 codes resolved. Codes `98226` and `68132` not found in any file. Three entries (`""`, `Неизвестно`, `Населено място`) are non-EKATTE garbage values.
- **Conclusion:** The approach is viable and the exact set of resolvable codes is known. Implementation can proceed with confidence.

**Spike: Confirm ek_raion.json trailing metadata row**

- **Hypothesis:** ek_raion.json may have a non-standard trailing entry that would cause a `KeyError` during loading.
- **Approach:** Printed all entries of ek_raion.json; inspected the final element.
- **Outcome:** The final element is `{'Дата и час на изготвяне на справката': '15/04/2026 03:00', 'Данните са актуални към': '24/01/2005'}` — no `raion` or `name` keys.
- **Conclusion:** All five EKATTE files must be loaded with guards `if 'raion' in item and 'name' in item` (or the equivalent field guard per file). This is a known implementation requirement.

**Spike: Confirm SCD Type-1 behaviour prevents in-place name update on plain re-run**

- **Hypothesis:** Simply extending `load_settlement_names()` and re-running without force-reprocess will NOT update existing `(unknown:...)` entries in dim_settlement.csv.
- **Approach:** Code-level analysis of `upsert_dim()`: `if nat_key in lookup: return int(lookup[nat_key][sk_col])` — the lookup is populated from the existing CSV at start; existing entries are returned unchanged.
- **Outcome:** Confirmed. Running transform without force-reprocess will not modify existing dim_settlement rows.
- **Conclusion:** To fix existing entries, either an in-place patch function or a full force-reprocess is required. In-place patch is preferred (Q001).

---

## AI Copilot Suggestions

**Observation 1 — Normalisation should live in `load_settlement_names()`, not in the call site**

The proposed design places the three-step normalisation probe in `build_schema()` at the `settlement_names.get(ekatte, ...)` call. While functional, this leaks normalisation logic into the main ETL loop, making the function harder to test and maintain. A cleaner approach is to either pre-build the lookup dict with all normalised variants as keys (i.e., store entries under both `02659` and `2659`, both `68134-04` and the raion name), or to encapsulate the normalisation in a helper function `resolve_settlement_name(code, lookup) -> str` that is unit-testable in isolation.

- **Suggestion:** Create a `resolve_settlement_name(code: str, lookup: Dict[str, str]) -> str` helper that encapsulates the three-step probe and the `(unknown:...)` fallback. Move the lookup call in `build_schema()` to call this helper. Add unit tests for this helper specifically.

**Observation 2 — The in-place patch function introduces a new code path with no established test pattern**

If the in-place patch approach (Q001) is chosen, it introduces a new one-time migration function (e.g., `patch_unknown_settlements(dim_path, lookup)`) that reads, modifies, and atomically rewrites a dimension CSV. This is different from the existing write path (`write_dim`) because it reads back the CSV first. If this function has a bug, it could corrupt `dim_settlement.csv`. The existing `write_dim` is well-tested but `patch_unknown_settlements` would need its own test coverage.

- **Suggestion:** Design the patch function to call the existing `write_dim()` for the write step, reusing the atomic `.partial` rename. Add an explicit test case for the patch function covering a mixed CSV (some resolved, some still unknown, none changed if already named).

**Observation 3 — Scope is appropriately minimal but the 3 residual unknowns should be documented**

The scope correctly excludes attempts to resolve `98226`, `68132`, and garbage entries. However, there is currently no mechanism to track which codes are permanently unresolvable versus which were unresolvable due to missing nomenclature files. If new EKATTE releases are published in the future, the 3 residual unknowns might become resolvable. The quality report already tracks `unknown_settlements` counts per ZIP date — but the specific codes are not surfaced.

- **Suggestion:** Add a `logging.warning()` in `load_settlement_names()` or in the patching step listing all codes that remain `(unknown:...)` after the extended lookup is applied. This creates a lightweight audit trail without adding new output artifacts.

**Scope note:** The scope is appropriately sized for the stated goal. The five EKATTE files are small (a few hundred to a few thousand entries each), the normalisation logic is trivial, and the patch function is a thin wrapper around existing infrastructure. There is no risk of scope creep here. The only scope enlargement risk is if the chosen fix mechanism (Q001) is force-reprocess, which would significantly expand the I/O footprint and time cost.

---

## Testing

- T1 — `load_settlement_names` includes raion codes: After the update, call `load_settlement_names()` in a test that uses real or mock file fixtures containing `ek_raion.json`; assert that `68134-04` maps to `Оборище`. Expected outcome: assertion passes.

- T2 — `load_settlement_names` handles ek_raion metadata row: Confirm that loading `ek_raion.json` with the trailing metadata row does not raise a `KeyError`. Expected outcome: function returns without exception; metadata row is silently skipped.

- T3 — `load_settlement_names` resolves missing-padding code via returned dict: Assert that the returned dict contains key `02659` → `Банкя` (from the primary cities dict, confirming it is present for normalisation to use). Expected outcome: assertion passes.

- T4 — Zero-padding normalisation resolves `2659` to `Банкя`: In a test that mocks the settlement lookup dict with only the padded key `02659`, call `resolve_settlement_name('2659', lookup)` (or test the equivalent call site) and assert the returned name is `Банкя`. Expected outcome: assertion passes.

- T5 — Leading-zero stripping resolves `068134` to `София`: Same approach as T4 but input code `068134`, expected name `София` (via key `68134`). Expected outcome: assertion passes.

- T6 — Truly unresolvable code retains `(unknown:...)` form: Call `resolve_settlement_name('98226', lookup)` with a lookup that does not contain `98226`, `09822_6_` or any normalised variant. Assert the result is `(unknown:98226)`. Expected outcome: assertion passes.

- T7 — `patch_unknown_settlements` updates only `(unknown:...)` rows: Create a temp `dim_settlement.csv` with 3 rows (1 named, 1 `(unknown:02659)`, 1 `(unknown:98226)`), run the patch function with a lookup containing `02659 → Банкя`, then read the result. Assert row with key `02659` now shows `Банкя`, row with `98226` still shows `(unknown:98226)`, and the named row is unchanged. Expected outcome: all three assertions pass.

- T8 — Patch function preserves surrogate keys: After running the patch function on a temp dim_settlement.csv, assert that no `settlement_key` integer value has changed. Expected outcome: all surrogate keys are identical to the input.

- T9 — Idempotency: Run the patch function twice on the same file. Assert the file content is identical after the second run. Expected outcome: content hash or row-by-row comparison is equal.

- T10 — Existing test suite passes: Run `python -m pytest tests/test_transform.py` and confirm exit code 0. Expected outcome: all existing tests pass without modification.

- T11 — `load_settlement_names` is non-breaking when ek_atte.json is absent: In a test environment with `ek_atte.json` deleted/missing, call `load_settlement_names()` and assert no exception is raised and the function returns a non-empty dict (from the primary cities file). Expected outcome: no exception; dict length > 0.

---

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is technically well-scoped and architecturally coherent. Extending `load_settlement_names()` to merge additional EKATTE files is strictly additive to an already established multi-source loading pattern — no new design patterns are introduced. The normalisation logic is straightforward and carries low risk of introducing regressions. The key architectural risk is the choice of fix mechanism for existing data (Q001): the in-place patch approach is architecturally correct and consistent with dimension SCD Type-1 semantics, while force-reprocess would be architecturally wasteful and disproportionate to the change.

- The three-step normalisation probe is simple but should be encapsulated in a helper function rather than inlined in the main ETL loop.
- The ek_raion.json trailing metadata row is a known data quality issue that requires a guard; this is a minor but non-negotiable implementation requirement.
- Adding `ek_atte.json` and `ek_kmet.json` overlap with `cities-ekatte-nomenclature.json` but add defensive depth at negligible cost.
- No new external dependencies are introduced; stdlib-only constraint is maintained.

### Product Owner

The change delivers clear, visible business value: 22 settlement names currently shown as `(unknown:NNNNN)` in the React app's Report 1 settlement filter will become human-readable Bulgarian city/district names. This directly improves the usability of the analytics product for end users. The scope is narrow and well-bounded, and the success criteria are measurable (exact list of codes that should and should not be resolved is known). The only scope risk is if the accepted approach (Q001) results in full force-reprocess, which has no user-facing benefit over the in-place patch but significantly increases delivery time.

- Success criteria are appropriately precise and fully testable.
- No new features or user-visible UI changes are required.
- The residual 3 unknowns are correctly excluded from scope.
- No changes to the React app or Supabase schema are required.

### User

For end users of the React app, this change makes the Report 1 settlement filter significantly more usable. City names like `Асеновград`, `Берковица`, `Бяла Слатина`, and `Оборище` (а Sofia district) will now appear instead of `(unknown:702)`, `(unknown:3928)`, `(unknown:7702)`, and `(unknown:68134-04)`. The improvement is immediately visible and requires no user action. The 3 remaining unknowns are a minor residual and unlikely to be questioned, since the codes are either data-entry errors or absent from the official registry.

- No change to app behaviour, loading times, or UI structure.
- Filter list becomes more readable; stores previously listed under `(unknown:...)` are now identifiable by city name.
- No friction introduced for existing users.

### Security Officer

This change is purely additive — it reads additional JSON files from the local filesystem at ETL runtime and populates an in-memory dict. No external network calls, no new credentials, no new user input surfaces, no changes to the Supabase schema, and no changes to the React app. The EKATTE files are static government reference data bundled with the workspace.

- No new attack surface introduced.
- No data exposure risk: EKATTE codes and settlement names are public government data.
- No authentication or authorisation impact.
- The only risk is path traversal if `NOM_DIR` were user-controlled — but it is a hardcoded constant relative to `__file__`.

### Data Governance Officer

The change improves data quality in `dim_settlement` by replacing placeholder values with accurate, government-sourced names. Data lineage is maintained: the new sources (`ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`) are official EKATTE registry files provided by the Bulgarian government and already bundled in the workspace. No new external data sources are introduced.

- Data lineage: settlement names will now be traceable to official EKATTE registry files (already in workspace).
- Retention: `dim_settlement.csv` is a workspace artifact; retention policy is unchanged.
- Classification: EKATTE codes and settlement names are public government data; no PII involved.
- Compliance: no compliance implications; the change improves data accuracy without introducing new data categories.
- The 3 residual unknowns (`98226`, `68132`, garbage values) should be documented in a known-issues register if one exists; currently only the quality report tracks `unknown_settlements` counts.
