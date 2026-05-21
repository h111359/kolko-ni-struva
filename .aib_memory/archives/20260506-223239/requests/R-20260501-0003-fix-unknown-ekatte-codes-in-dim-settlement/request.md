## Goal

Expand the EKATTE settlement-name resolution in `src/transform.py` to consult all available nomenclature files under `data/nomenclatures/` (including `Ekatte/ek_atte.json`, `Ekatte/ek_kmet.json`, `Ekatte/ek_raion.json`, `Ekatte/ek_obl.json`, and `Ekatte/ek_obst.json`) and to apply code normalisation (zero-padding to 5 digits; leading-zero stripping; raion-code pass-through) so that as many `(unknown:<code>)` placeholder entries as possible are replaced with real settlement names in `data/schema/dim_settlement.csv`.

## Background

The ETL pipeline populates `dim_settlement` by looking up each raw EKATTE code in a combined dictionary built from `data/nomenclatures/cities-ekatte-nomenclature.json` and `data/nomenclatures/Ekatte/sof_rai.json`. When a code is not found, the pipeline stores a placeholder string `(unknown:<code>)`.

A quality review revealed 25 unknown entries in the current `dim_settlement.csv`. Investigation of the full EKATTE registry files shows that:

- 5 entries use raion codes with a dash suffix (e.g. `68134-04`, `68134-01`) present in `ek_raion.json` but not in the current lookup.
- 16 entries use codes without the canonical 5-digit zero-padding (e.g. `2659` instead of `02659`) that exist in `cities-ekatte-nomenclature.json` under their padded form.
- 1 entry uses a code with extra leading zeros (`068134` instead of `68134`).
- 3 entries are truly unresolvable: `98226` (not present in any EKATTE file), `68132` (close to Sofia `68134` but not a known code), and degenerate values (empty string, `Неизвестно`, `Населено място`).

The existing `load_settlement_names()` function in `src/transform.py` only reads two nomenclature files and performs no normalisation. Expanding it to read all available EKATTE files and apply normalisation will resolve 22 of the 25 unknowns without requiring any manual data entry.

## Scope

- Update `load_settlement_names()` in `src/transform.py` to additionally read the following files and merge their codes into the name lookup: `data/nomenclatures/Ekatte/ek_atte.json` (field `ekatte` → `name`), `data/nomenclatures/Ekatte/ek_kmet.json` (field `ekatte` → `name`), `data/nomenclatures/Ekatte/ek_raion.json` (field `raion` → `name`), `data/nomenclatures/Ekatte/ek_obl.json` (field `ekatte` → `name`), `data/nomenclatures/Ekatte/ek_obst.json` (field `ekatte` → `name`).

- Update the EKATTE lookup call site in `build_schema()` to normalise incoming codes before lookup: first try the code as-is, then try it zero-padded to 5 characters, then try it with leading zeros stripped; use the first match found.

- Update path constant(s) in `src/transform.py` to reference the new nomenclature files.

- Ensure all 5 new file reads are guarded with `if <file>.exists():` checks to prevent hard failures when files are absent.

- Re-generate `dim_settlement.csv` by force-reprocessing the existing ZIPs so that the 22 now-resolvable codes are replaced with real names. The remaining 3 unresolvable codes (`98226`, `68132`, and garbage values) retain their `(unknown:...)` placeholder.

- Update the automated test suite (`tests/test_transform.py`) to cover the new normalisation and extended lookup behaviour.

## Out of scope

- Manual research or external API lookup to resolve the 3 truly unresolvable EKATTE codes (`98226`, `68132`, empty/garbage values).

- Changes to the React app, Supabase sync, or any other ETL module outside `src/transform.py`.

- Removal of the `(unknown:...)` placeholder mechanism — it must be retained for any code that genuinely cannot be resolved.

- Adding new EKATTE nomenclature files beyond those already present in `data/nomenclatures/Ekatte/`.

## Constraints

- `src/transform.py` uses Python stdlib only — no new third-party imports allowed.

- All new file reads must be non-breaking: if a nomenclature file is absent, the function must continue without error (existing logic is preserved).

- The SCD Type-1 idempotency rule for `dim_settlement` must be preserved — previously resolved codes must not change their surrogate key on re-run.

- Normalisation must not silently produce wrong resolutions: if zero-padding or stripping produces a code that maps to a different name than expected, it should still be accepted (the source data code is non-canonical, and any real match is better than `(unknown:...)`).

- Force re-process must use the existing `force_from` mechanism in `build_schema()` — no new CLI flags or code paths required.

## Success criteria

- `load_settlement_names()` returns a dict that includes entries from all 5 new EKATTE files.

- After a force re-process, `data/schema/dim_settlement.csv` contains no `(unknown:...)` entries for the 22 now-resolvable EKATTE codes listed in the Background section.

- After a force re-process, the 3 truly unresolvable codes (`98226`, `68132`, and garbage values) still appear as `(unknown:...)` — no silent data loss.

- `tests/test_transform.py` includes at least one test covering extended EKATTE file loading and at least one test covering code normalisation (zero-padding and raion-code lookup).

- All existing tests continue to pass.

- Running `build_schema()` twice with the same inputs produces identical `dim_settlement.csv` output (idempotency).

## Assumptions

- A1: All five additional EKATTE files (`ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, `ek_obst.json`) are and will remain present in `data/nomenclatures/Ekatte/`. If absent, the code gracefully degrades to the existing behaviour.
  - Risk if false: Any of the 22 newly resolvable codes would fall back to `(unknown:...)` if the corresponding file is missing at runtime.

- A2: The three-step normalisation probe (as-is → zero-padded to 5 digits → leading-zeros stripped) is sufficient to cover all current and future code formatting variants from the source data.
  - Risk if false: Edge cases with non-numeric codes or unusual formatting would remain unresolved; the placeholder mechanism would handle them gracefully.

- A3: The `ek_raion.json` trailing metadata row (`{'Дата и час на изготвяне на справката': ..., ...}`) is a stable data quality characteristic of this file and must always be guarded by checking for required keys.
  - Risk if false: If a future version of the file omits the metadata row or adds differently structured entries, the guard is a no-op and does not cause harm.

- A4: Surrogate keys in `dim_settlement.csv` are stable and referenced by `dim_store.csv` and indirectly by all fact files via `store_key`. The in-place patch must preserve all `settlement_key` values.
  - Risk if false: If surrogate keys were regenerated, all FK references in `dim_store` and downstream fact files would need to be regenerated as well — significantly expanding scope.

- A5: The `cities-ekatte-nomenclature.json` already contains all canonical 5-digit padded codes for the resolvable unknowns. No new nomenclature file needs to be created or downloaded.
  - Risk if false: If the cities file is missing specific codes, `ek_atte.json` acts as a fallback safety net (since it overlaps with the cities file).

## Plan

### Task 1: Extend `load_settlement_names()` with all EKATTE files
**Intent:** Add loading of `ek_atte.json`, `ek_kmet.json`, `ek_raion.json`, `ek_obl.json`, and `ek_obst.json` to the settlement name lookup dict.
**Inputs:** `src/transform.py`, `data/nomenclatures/Ekatte/` (five JSON files)
**Outputs:** Modified `src/transform.py` — updated `load_settlement_names()` function and updated path constants
**External Interfaces:** Local filesystem reads of five JSON files
**Environment & Configuration:** No new config keys; all paths relative to `NOM_DIR` constant
**Procedure:**
1. Add five new `Path` constants in `src/transform.py` for the new EKATTE files (parallel to existing `SOF_RAI_FILE`).
2. In `load_settlement_names()`, add five `if <file>.exists():` guarded loading blocks after the existing `sof_rai` block, each merging entries into `names` without overwriting existing entries.
3. For `ek_raion.json`, use the `raion` field as key; for all others, use the `ekatte` field. Guard each item with `if '<field>' in item and 'name' in item`.
**Done Criteria:** `load_settlement_names()` returns a dict that includes `68134-04 → Оборище` and `02659 → Банкя` (or equivalent padded form as present in the source files).
**Dependencies:** None
**Risk Notes:** ek_raion.json trailing metadata row — handled by key-presence guard.

### Task 2: Add `resolve_settlement_name()` helper and update call site
**Intent:** Encapsulate three-step EKATTE code normalisation (as-is → zero-padded → leading-zeros-stripped) in a testable helper and update `build_schema()` to use it.
**Inputs:** `src/transform.py`
**Outputs:** Modified `src/transform.py` — new `resolve_settlement_name()` function; updated call site in `build_schema()`
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Define `resolve_settlement_name(code: str, lookup: Dict[str, str]) -> str` that tries `lookup.get(code)`, then `lookup.get(code.zfill(5))`, then `lookup.get(code.lstrip('0') or code)`, returning the first non-None result or `f"(unknown:{code})"`.
2. Replace the single `.get(ekatte, f"(unknown:{ekatte})")` call in `build_schema()` with a call to `resolve_settlement_name(ekatte, settlement_names)`.
3. Update the `q_unknown_settlements += 1` guard to check if the result starts with `(unknown:`.
**Done Criteria:** `resolve_settlement_name('2659', {'02659': 'Банкя'})` returns `Банкя`; `resolve_settlement_name('068134', {'68134': 'София'})` returns `София`; `resolve_settlement_name('98226', {})` returns `(unknown:98226)`.
**Dependencies:** Task 1
**Risk Notes:** None.

### Task 3: Add in-place `patch_unknown_settlements()` function (if Q001 resolved as in-place patch)
**Intent:** Correct existing `(unknown:...)` entries in `dim_settlement.csv` without force-reprocessing fact files.
**Inputs:** `data/schema/dim_settlement.csv`, extended settlement lookup dict from `load_settlement_names()`
**Outputs:** Updated `data/schema/dim_settlement.csv` (names corrected; surrogate keys unchanged)
**External Interfaces:** Local filesystem read/write of `dim_settlement.csv`
**Environment & Configuration:** No new config keys
**Procedure:**
1. Define `patch_unknown_settlements(dim_path: Path, lookup: Dict[str, str]) -> int` that reads the CSV, applies `resolve_settlement_name()` to each row whose `settlement_name` starts with `(unknown:`, and rewrites the file atomically using `write_dim()`.
2. Return the count of rows updated.
3. Call this function from `build_schema()` after the main ZIP processing loop, or from a standalone invocation in `main()`.
**Done Criteria:** Running `patch_unknown_settlements()` on the current `dim_settlement.csv` reduces the `(unknown:...)` count from 25 to 3; all `settlement_key` values are unchanged.
**Dependencies:** Task 1, Task 2
**Risk Notes:** Surrogate key preservation is critical; verified by the atomic rewrite through `write_dim()`.

### Task 4: Extend `tests/test_transform.py` with new test cases
**Intent:** Provide automated coverage for all new behaviour introduced in Tasks 1–3.
**Inputs:** `tests/test_transform.py`, fixture JSON files (minimal inline or temp-dir based)
**Outputs:** Updated `tests/test_transform.py`
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Add `TestLoadSettlementNames` class covering: raion code resolution (T1), metadata row skipping (T2), graceful absent-file handling (T11).
2. Add `TestResolveSettlementName` class covering: zero-padding (T4), leading-zero stripping (T5), truly unresolvable code (T6).
3. Add `TestPatchUnknownSettlements` class covering: targeted update (T7), surrogate key preservation (T8), idempotency (T9).
**Done Criteria:** `python -m pytest tests/test_transform.py` exits 0; new tests cover all test IDs T1–T9.
**Dependencies:** Tasks 1–3
**Risk Notes:** Temp-dir fixtures must be fully isolated; no writes to real `data/` directories in tests.

### Task 5: Verify fix and run full test suite
**Intent:** Confirm that the changes produce the expected output in `dim_settlement.csv` and that no regressions are introduced.
**Inputs:** Modified `src/transform.py`, existing `data/schema/dim_settlement.csv`, real EKATTE files
**Outputs:** Updated `data/schema/dim_settlement.csv`; test run output
**External Interfaces:** Local filesystem
**Environment & Configuration:** Python venv activated; no new env vars required
**Procedure:**
1. Run `python -m pytest tests/test_transform.py -v` — confirm all tests pass.
2. Run `python -m pytest tests/ -v` — confirm no regressions in other test modules.
3. Invoke the patch function (or run transform with appropriate trigger) and inspect `dim_settlement.csv` for reduced `(unknown:...)` count.
4. Confirm exactly 3 (or fewer if garbage entries are also treated differently) `(unknown:...)` entries remain.
**Done Criteria:** Test suite exits 0; `dim_settlement.csv` contains ≤ 3 `(unknown:...)` entries; the 22 previously unknown codes now show real names.
**Dependencies:** Tasks 1–4
**Risk Notes:** None.

### Task 6: Update context.md and documentation
**Intent:** Reflect the extended EKATTE loading and normalisation in the product context and any affected documentation.
**Inputs:** `.aib_memory/context.md`, `README.md` (if it documents EKATTE handling)
**Outputs:** Updated `.aib_memory/context.md`
**External Interfaces:** None
**Environment & Configuration:** None
**Procedure:**
1. Update the `load_settlement_names()` description in `context.md` (Technical Design → Module Breakdown → `src/transform.py`) to note the five additional EKATTE files and normalisation.
2. Update the `## Architecture & Key Decisions` section entry for "Dimension from facts (no pre-load)" to note that unknown codes are now resolved via extended EKATTE lookup and normalisation before falling back to `(unknown:...)`.
3. Check README.md for any mention of unknown settlements; update if present.
**Done Criteria:** `context.md` accurately reflects the updated `load_settlement_names()` and normalisation logic.
**Dependencies:** Tasks 1–5
**Risk Notes:** None.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — update `src/transform.py` module description to reflect extended EKATTE file loading and `resolve_settlement_name()` normalisation helper.

## Questions & Decisions

**Q001**: How should existing `(unknown:...)` entries in `dim_settlement.csv` be fixed?
- [x] Option A: Add an in-place `patch_unknown_settlements()` function that reads `dim_settlement.csv`, updates only the name column for resolvable codes, and atomically rewrites the file — no force-reprocess of fact files needed. *(recommended)*
- [ ] Option B: Force-reprocess all ZIPs from the earliest date (`force_from = "2026-02-15"`) to rebuild `dim_settlement.csv` and all 63+ fact files from scratch.
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/transform.py` | Modified | Add new EKATTE file path constants; extend `load_settlement_names()`; add `resolve_settlement_name()` helper; add `patch_unknown_settlements()` function; update call site in `build_schema()` |
| `data/schema/dim_settlement.csv` | Modified | 22 `(unknown:...)` entries corrected to real settlement names |
| `tests/test_transform.py` | Modified | New test classes for `load_settlement_names`, `resolve_settlement_name`, and `patch_unknown_settlements` |
| `.aib_memory/context.md` | Modified | Updated module description for `src/transform.py` |
| `data/nomenclatures/Ekatte/ek_atte.json` | Read-only dependency | New EKATTE source file read by `load_settlement_names()` |
| `data/nomenclatures/Ekatte/ek_kmet.json` | Read-only dependency | New EKATTE source file read by `load_settlement_names()` |
| `data/nomenclatures/Ekatte/ek_raion.json` | Read-only dependency | New EKATTE source file read by `load_settlement_names()` (raion codes) |
| `data/nomenclatures/Ekatte/ek_obl.json` | Read-only dependency | New EKATTE source file read by `load_settlement_names()` |
| `data/nomenclatures/Ekatte/ek_obst.json` | Read-only dependency | New EKATTE source file read by `load_settlement_names()` |
| `data/nomenclatures/cities-ekatte-nomenclature.json` | Read-only dependency | Existing primary EKATTE source (unchanged) |
| `data/nomenclatures/Ekatte/sof_rai.json` | Read-only dependency | Existing Sofia raion source (unchanged) |

## Internal Review of Request and Product Docs

- OK: `request.md` — all 6 mandatory sections are present and non-empty; scope is sufficiently specific for implementation.
- Ambiguity: `request.md § Scope` — the phrase "Re-generate dim_settlement.csv by force-reprocessing the existing ZIPs" in the original draft may conflict with the preferred in-place patch approach identified during analysis; resolved via Q001.
- Missing info: `request.md § Constraints` — no mention of whether `build_schema()` should invoke the patch automatically or whether it should be a separate explicit step; left for Q001 answer to resolve.
- OK: `.aib_memory/context.md` (REF-0001) — accurately describes the current `load_settlement_names()` with two sources; will need update after implementation.
- Cross-ref issue: `context.md § Key Architectural Decisions` item 2 states "Unknown codes receive `(unknown:<code>)` entries" — this will remain partially true after the fix (for the 3 unresolvable codes) but the statement should be updated to note the extended resolution.
- OK: All EKATTE nomenclature files referenced in this analysis are present in `data/nomenclatures/Ekatte/`.
