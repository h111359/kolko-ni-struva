## Goal
Investigate the React analytics page "Цени по категория" and correct the calculation and selection behavior so settlements such as София show the full category coverage supported by the raw and transformed data. Verify all identified issues against the raw ZIP inputs, add targeted automated tests, and define the implementation work needed to fix the root causes rather than masking the symptom.

## Background
The active input reports that the "Цени по категория" page shows only 2 categories for София. Workspace context states that Report 1 should include all categories with at least one price observation and should not silently truncate the result set. Local verification against `data/schema/fact_prices_lookback.csv` shows that София should expose 103 categories in the latest local data, while a second duplicate settlement row named София with EKATTE `068134` is linked to only 2 categories. The current ETL uses the raw EKATTE string as the natural key for `dim_settlement`, so canonical code `68134` and over-padded code `068134` are treated as different settlements even though name resolution maps both to София.

## Scope
- Trace the Report 1 data path across the React app, transformed schema outputs, and relevant raw ZIP inputs to explain why the page can resolve София to a 2-category slice.

- Identify all calculation, data-normalization, and UX-selection issues that materially affect the correctness of the "Цени по категория" page for duplicated settlement names.

- Define implementation work to normalize settlement identifiers at the ETL/data-model level, prevent ambiguous settlement selection in the React UI, and verify the fixed behavior against raw source rows.

- Add automated coverage for the ETL normalization and React Report 1 behavior, plus any required manual UAT for user-visible dropdown behavior.

- Update product context and user-facing documentation to reflect the corrected settlement-handling behavior and any required reprocessing or Supabase resync steps.

## Out of scope
- Redesigning unrelated reports or replacing the Report 1 visualization.

- Broad refactoring of the ETL pipeline beyond changes needed to normalize settlement identity and preserve correct Report 1 behavior.

- Changes to the legacy web app unless the same defect is confirmed there and must be documented for parity.

## Constraints
The request must be resolved using the current workspace codebase, local schema outputs, and raw ZIP archives without relying on unverifiable assumptions about production-only state. The fix must remain consistent with the existing architecture: ETL outputs feed Supabase, and the React app reads settlement and category data from the retained 3-day lookback model. Validation must explicitly compare the affected Report 1 behavior with raw source records and local transformed outputs. Any remediation must preserve idempotent ETL behavior and avoid introducing stale or duplicate settlement dimension rows.

## Success criteria
- Report 1 no longer resolves София or any equivalent duplicate settlement-name case to an incomplete 2-category slice when local/raw data supports a larger category set.

- Settlement identity is normalized or otherwise handled so semantically identical EKATTE variants do not create incorrect analytical splits between the ETL output and the React UI.

- Verification demonstrates that the fixed behavior matches the raw ZIP inputs and the transformed local schema for the affected settlement.

- Automated tests cover the discovered root cause and guard against regression in both data normalization and Report 1 result construction.

- Documentation and workspace context are updated to record the corrected behavior, affected components, and any reprocessing/resync implications.

## Assumptions
- A1: The reported page is the active React Report 1 implementation in `react-app/`, not the legacy `build-legacy/web/` page.
  - Risk if false: Analysis and planned fixes could target the wrong UI surface.

- A2: The duplicate София entries in `data/schema/dim_settlement.csv` are representative of the defect path that can also propagate to Supabase after a normal sync.
  - Risk if false: A local-only artifact could mislead the implementation and miss a separate remote/UI issue.

- A3: Canonicalizing semantically identical EKATTE variants such as `068134` and `68134` is acceptable because the request explicitly asks for raw-data verification and root-cause correction.
  - Risk if false: A business rule might require preserving the padded variant as a distinct settlement identity.

- A4: Reprocessing local schema outputs and re-syncing Supabase are acceptable parts of the eventual fix if the ETL natural key changes.
  - Risk if false: Code-only changes would leave existing derived data and the deployed UI inconsistent.

## Plan
### Task 1: Reproduce and Bound the Defect
**Intent:** Confirm the exact failure mode for Report 1 and isolate whether it comes from the UI, transformed schema, or raw source data.
**Inputs:** `.aib_memory/input.md`, `.aib_memory/context.md`, `react-app/src/components/Report1.jsx`, `react-app/src/lib/dataService.js`, `data/schema/dim_settlement.csv`, `data/schema/dim_store.csv`, `data/schema/fact_prices_lookback.csv`, latest ZIPs in `data/raw/`.
**Outputs:** Verified defect statement tied to specific settlement keys, category counts, and raw source rows.
**External Interfaces:** Local filesystem only.
**Environment & Configuration:** No special configuration beyond local workspace access.
**Procedure:** 1. Trace the Report 1 query path. 2. Count categories for the affected settlement in local schema outputs. 3. Compare duplicate settlement rows and their store coverage. 4. Verify the corresponding raw ZIP rows and category codes. 5. Record the controlling root cause.
**Done Criteria:** A single evidence-backed explanation exists for why София can appear as a 2-category result.
**Dependencies:** None.
**Risk Notes:** Misreading the raw CSV column layout would produce a false negative during source verification.

### Task 2: Normalize Settlement Identity in ETL
**Intent:** Remove or prevent analytical splits caused by raw EKATTE formatting variants that refer to the same settlement.
**Inputs:** `src/transform.py`, `data/nomenclatures/`, existing dimension natural-key behavior, raw ZIP examples containing `068134` and `68134`.
**Outputs:** Updated ETL normalization logic and, if needed, migration-safe handling for existing `dim_settlement` and dependent dimensions/facts.
**External Interfaces:** Local filesystem; downstream Supabase sync expectations.
**Environment & Configuration:** Must preserve Python 3.9+ compatibility and idempotent transform behavior.
**Procedure:** 1. Identify the earliest point where settlement codes can be canonicalized. 2. Update natural-key handling so padded and canonical equivalents collapse to the same settlement identity. 3. Ensure dependent store/fact relationships remain consistent after reprocessing. 4. Rebuild affected local schema artifacts as needed. 5. Verify the duplicate София split is removed.
**Done Criteria:** Local transformed outputs no longer contain analytically duplicated settlement identities for the affected case.
**Dependencies:** Task 1.
**Risk Notes:** Changing settlement natural keys can require controlled regeneration of downstream schema files and Supabase data.

### Task 3: Harden Report 1 Settlement Selection
**Intent:** Ensure the React page cannot mislead users when multiple settlement options have the same visible label or stale duplicate identities remain.
**Inputs:** `react-app/src/components/Report1.jsx`, `react-app/src/lib/dataService.js`, dimension-loading behavior, settlement dropdown rendering.
**Outputs:** Updated settlement selection behavior for Report 1 and any shared helper logic needed to disambiguate options.
**External Interfaces:** Supabase/PostgREST data reads through the existing client abstractions.
**Environment & Configuration:** Must preserve current React/Vite architecture and Bulgarian UI copy.
**Procedure:** 1. Determine how duplicate visible settlement names are surfaced today. 2. Add the smallest safe UI/data-service change that prevents ambiguous selection. 3. Confirm the selected settlement maps to the intended aggregated dataset. 4. Keep existing lookback-date routing intact.
**Done Criteria:** Report 1 settlement selection is unambiguous and returns the correct category aggregation for the affected case.
**Dependencies:** Task 1.
**Risk Notes:** A UI-only mitigation without ETL normalization would leave downstream data quality issues unresolved.

### Task 4: Validate Raw-to-UI Consistency
**Intent:** Prove that the corrected behavior matches both raw ZIP content and transformed analytical outputs.
**Inputs:** Latest affected ZIPs in `data/raw/`, regenerated schema outputs in `data/schema/`, Report 1 logic in `react-app/src/lib/dataService.js`.
**Outputs:** Verification evidence covering raw rows, transformed dimensions/facts, and final Report 1 category counts.
**External Interfaces:** Local filesystem; optional Supabase resync if implementation updates remote state.
**Environment & Configuration:** If Supabase is included, requires the existing `.env` configuration for database access.
**Procedure:** 1. Recompute the affected settlement/category counts from raw data. 2. Compare them with regenerated local schema outputs. 3. Validate the Report 1 aggregation against the corrected settlement identity. 4. Record any remaining mismatches. 5. Confirm no new duplicate-split cases were introduced.
**Done Criteria:** Observable counts match across raw data, local schema, and Report 1 for the corrected path.
**Dependencies:** Tasks 2 and 3.
**Risk Notes:** If remote Supabase data is stale, local validation alone may not guarantee deployed behavior until a sync is performed.

### Task 5: Add Automated Regression Coverage
**Intent:** Cover all testable success criteria with focused automated tests for ETL normalization and Report 1 behavior.
**Inputs:** Existing Python tests under `tests/`, existing React tests under `react-app/src/**/*.test.*`, implementation changes from Tasks 2 and 3.
**Outputs:** New or updated unit/integration tests plus runnable commands for the affected slices.
**External Interfaces:** Python test runner; React/Vitest test runner.
**Environment & Configuration:** Use existing project test tooling; no live network access in tests.
**Procedure:** 1. Add ETL tests for canonical settlement-code handling. 2. Add React/data-service tests for duplicate-name settlement handling and correct category counts. 3. Run the narrow affected test suites. 4. Fix any local regressions uncovered by those suites. 5. Record expected rerun/idempotency checks.
**Done Criteria:** Every testable success criterion has at least one automated regression check and the affected suites pass.
**Dependencies:** Tasks 2 and 3.
**Risk Notes:** Test fixtures must be small enough to keep the suite fast while still modeling the duplicate-settlement edge case.

### Task 6: Update Context and Documentation
**Intent:** Capture the corrected behavior, data implications, and operator steps after the implementation lands.
**Inputs:** `.aib_memory/context.md`, `README.md`, implementation outcomes from Tasks 2 through 5.
**Outputs:** Updated workspace context and any user/operator documentation affected by the fix.
**External Interfaces:** Documentation files in the repository.
**Environment & Configuration:** None beyond repository write access.
**Procedure:** 1. Update `.aib_memory/context.md` with the corrected settlement-normalization behavior. 2. Update `README.md` if operator-facing behavior or rerun steps change. 3. Document any required reprocess/resync step. 4. Reconcile documentation with the final implementation.
**Done Criteria:** Documentation reflects the delivered behavior and any discovered discrepancies are resolved or explicitly noted.
**Dependencies:** Tasks 2 through 5.
**Risk Notes:** Leaving context stale would make future AIB analyses reason from outdated product behavior.

## Documentation
- .aib_memory/context.md — record the corrected settlement-normalization behavior, the Report 1 impact, and any required reprocess/resync implications.
- README.md — document any operator-visible rerun or data-refresh steps required after normalizing settlement identifiers.

## Questions & Decisions

## Code and Asset Scan for Impacted Components
| File/Asset | Change Type | Reason |
| --- | --- | --- |
| src/transform.py | Modified | Current ETL settlement natural key uses raw EKATTE text, which permits duplicate settlement identities for padded variants. |
| data/schema/dim_settlement.csv | Read-only dependency | Confirms duplicate София rows (`68134` and `068134`) in current local outputs. |
| data/schema/dim_store.csv | Read-only dependency | Shows the duplicate Sofia settlement rows map to different store populations. |
| data/schema/fact_prices_lookback.csv | Read-only dependency | Confirms 103 categories for canonical Sofia versus 2 for the padded duplicate slice. |
| data/raw/*.zip | Read-only dependency | Raw-source verification for canonical and padded EKATTE values in the affected settlement data. |
| react-app/src/lib/dataService.js | Modified | Contains Report 1 aggregation and settlement-driven query behavior. |
| react-app/src/components/Report1.jsx | Modified | Renders the settlement selector that can expose ambiguous duplicate visible names. |
| react-app/src/lib/dataService.test.js | Modified | Best-fit location for React data-service regression tests covering the defect path. |
| react-app/src/components/Report1.test.jsx | Modified | Best-fit location for UI regression tests around settlement selection behavior. |
| tests/test_transform.py | Modified | Best-fit location for ETL normalization regression coverage. |
| .aib_memory/context.md | Modified | Must reflect the corrected product behavior after implementation. |
| README.md | Modified | May need operator guidance if regeneration/resync becomes required. |

## Internal Review of Request and Product Docs
- OK: `.aib_memory/input.md` — the user intent is clear that this is a root-cause investigation and fix request, not a UI-only workaround.
- OK: `.aib_memory/context.md` — product context already states that Report 1 should include all categories with at least one price observation and must not silently truncate the chart.
- Missing info: `.aib_memory/input.md` — the request does not explicitly say whether the required fix must include local schema regeneration and Supabase resync, though the wording strongly implies end-to-end correction.
- Ambiguity: `.aib_memory/input.md` — the exact user path that selects the wrong София option is not described, so implementation should verify whether duplicate visible labels are currently exposed in the settlement dropdown.
- Cross-ref issue: `README.md` — the root README still describes `load_supabase.py` using `get_available_dates` and `get_settlements_for_date` only, while current workspace context also relies on category/settlement cross-filter RPC functions and newer retention behavior.