## Executive Summary
- Request ID: `R-20260508-0743`.

- Request title: Investigate category prices page calculation.

- High-level purpose: explain why the React page "Цени по категория" can show only 2 categories for София, verify the issue against raw inputs, and define the concrete implementation work required to fix the root cause.

- The controlling calculation path is `react-app/src/components/Report1.jsx` -> `react-app/src/lib/dataService.js::fetchReport1()`, with settlement identity inherited from ETL outputs in `data/schema/dim_settlement.csv` and `data/schema/dim_store.csv`.

- Local transformed data disproves the symptom as a raw-data limitation: the latest `fact_prices_lookback.csv` contains 103 categories for canonical София (`settlement_key=7`, `ekatte=68134`) and only 2 categories for a duplicate София row (`settlement_key=261`, `ekatte=068134`).

- Raw ZIP verification confirms the padded variant is present in source data, but only in a narrow slice: the latest ZIP contains 374,419 rows for `68134` across 62 files and 55 rows for `068134` in a single file, spanning just 2 categories.

- The root cause is not Report 1 aggregation truncation in the current workspace: `fetchReport1()` already paginates past the 1,000-row PostgREST limit. The defect path is that ETL settlement identity is keyed by raw EKATTE text, so `068134` and `68134` are treated as distinct settlements while both resolve to the same visible name "София".

- The most credible user-facing failure mode is ambiguous settlement selection: if the UI exposes two visually identical София options, choosing the padded duplicate routes Report 1 to the 2-category slice even though the canonical Sofia dataset contains 103 categories.

- This analysis run added and populated implementation-relevant sections in `request.md`: `## Assumptions`, `## Plan`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs`. No unresolved user question met the threshold for a Q-block.

## Domain Knowledge Essentials
- EKATTE: Bulgaria's settlement identifier system. In this request, it is the source identifier used to map rows to settlements.

- Settlement: a населено място such as София. Report 1 groups price observations by category within the selected settlement.

- Category coverage: the number of distinct product categories with at least one price observation for a settlement on the selected date. This is the business-visible measure the user is questioning.

- Lookback fact row: one retained fact row in `fact_prices_lookback` for the current retained date `D`, optionally carrying `D-1` and `D-2` prices in side columns. Report 1 reads from this retained structure.

- Canonical code variant: the normalized EKATTE form expected to represent a settlement consistently, such as `68134` for София.

- Over-padded code variant: a source formatting variant with extra leading zeros, such as `068134`, that still refers to the same settlement semantically.

- Impacted personas: end users of the public React analytics app, data engineers who run ETL reprocessing and Supabase sync, and analysts who trust Report 1 as a summary of category-level price coverage.

- Business process touched: daily ingestion of public retail price files, transformation into dimensional analytics outputs, sync to Supabase, and end-user exploration via the React Report 1 page.

- KPI affected: category completeness for a settlement on a selected date. The expected business outcome is that София shows all categories present in the raw and transformed data, not a narrow duplicate subset.

- Acceptance impact: a business stakeholder should be able to select София and see category coverage consistent with source data; duplicate hidden data splits are a correctness failure even if the underlying rows exist somewhere else in the model.

## Technical Knowledge & Terms
- React Report 1: the page component in `react-app/src/components/Report1.jsx` that loads settlements for a selected date and then renders average effective price by category for the chosen settlement.

- `fetchReport1()`: the client-side aggregation function in `react-app/src/lib/dataService.js` that queries `fact_prices_lookback`, paginates over all matching rows, normalizes lookback prices when needed, and computes average price per category.

- `dim_settlement`: the settlement dimension in `data/schema/dim_settlement.csv`, keyed today by the raw EKATTE text captured during transformation.

- Natural key: the business/source key used to decide whether two rows represent the same logical entity. Here, the ETL currently uses raw `ekatte` text rather than a canonicalized form.

- PostgREST pagination: the Supabase/PostgREST behavior that limits result windows and requires explicit range-based pagination to retrieve the full set. Current `fetchReport1()` already implements this correctly.

- Data normalization: standardizing source identifiers before joining or deduplicating them. This request depends on applying that concept to settlement codes before dimension upserts.

- Reliability implication: if the ETL stores semantically equivalent settlement IDs as separate dimension rows, downstream analytics become sensitive to whichever duplicate visible label the user selects.

- Performance implication: the current Report 1 path is already paginated and therefore not at immediate risk of silent 1,000-row truncation for this symptom.

- Security implication: this request does not materially expand attack surface; it remains a correctness and data-governance issue.

- Operations implication: if settlement identity normalization changes the ETL natural key, local schema regeneration and Supabase resync are likely required for the fix to be visible in deployed analytics.

- Files Read:
  - `.aib_memory/input.md`
  - `.aib_memory/context.md`
  - `.aib_memory/instructions.md`
  - `.aib_memory/requests_register.md`
  - `.aib_brain/conventions/analysis-convention.md`
  - `.aib_brain/conventions/request-convention.md`
  - `README.md`
  - `react-app/src/components/Report1.jsx`
  - `react-app/src/lib/dataService.js`
  - `react-app/src/components/Report1.test.jsx`
  - `react-app/src/App.test.jsx`
  - `react-app/src/lib/dataService.test.js`
  - `src/transform.py`
  - `src/load_supabase.py`
  - `data/schema/dim_settlement.csv` (via targeted terminal verification)
  - `data/schema/dim_store.csv` (via targeted terminal verification)
  - `data/schema/fact_prices_lookback.csv` (via targeted terminal verification)
  - `data/raw/*.zip` latest and recent files (via targeted terminal verification)

- Evidence -> implication:
  - Evidence: `fetchReport1()` paginates using `.range(from, to)` until the final partial page. Implication: the current 2-category symptom is not explained by the known 1,000-row truncation bug that affected earlier code.
  - Evidence: `src/transform.py` upserts `dim_settlement` with natural key `(ekatte,)`, where `ekatte` is the raw CSV string. Implication: padded and canonical variants produce distinct settlement rows even when they resolve to the same displayed settlement name.
  - Evidence: local schema has `settlement_key=7, ekatte=68134, settlement_name=София` and `settlement_key=261, ekatte=068134, settlement_name=София`. Implication: duplicate visible settlement names can exist in the UI while pointing to different analytical slices.
  - Evidence: canonical Sofia maps to 1,548 stores and 103 categories; padded Sofia maps to 1 store and 2 categories. Implication: choosing the wrong duplicate settlement fully explains the reported undercount.
  - Evidence: recent raw ZIPs repeatedly include 55 rows with `068134` in one source file. Implication: this is a recurring source-formatting edge case and should be normalized upstream rather than treated as a one-off anomaly.

## Research Results
- Pattern scan against current workspace standards:
  - The workspace already corrected one major Report 1 defect class: `fetchReport1()` paginates all matching rows, explicitly addressing PostgREST window limits. That pattern is consistent with the product context statement that Report 1 should not silently truncate categories.
  - The ETL follows a different pattern for settlement identity: `resolve_settlement_name()` normalizes when mapping names, but `upsert_dim()` for settlements still keys by the unnormalized raw EKATTE string. The normalization rule is therefore applied to labels, not identities.
  - The data model allows duplicate display names whenever differently formatted source identifiers resolve to the same settlement name. Report 1 currently depends on `settlement_key` choice from the dropdown and does not include any additional disambiguation or merge behavior.

- Pattern findings from local evidence:
  - The issue is narrowly scoped to a recurring source-data formatting variant rather than a broad absence of Sofia data.
  - The affected padded code is present across multiple recent ZIPs but confined to one supplier file and two category codes in the latest archive, which is consistent with a source-specific formatting inconsistency.
  - The current request is therefore a combined ETL normalization and UI robustness issue. Fixing only the UI would leave duplicate settlement identities in the analytical model.

- Risks explicitly identified:
  - A code-only change in the React app will not correct already materialized duplicate settlement identities in local schema or Supabase.
  - A natural-key change in ETL can require regeneration of dependent dimensions and facts to keep store-to-settlement links consistent.
  - Duplicate visible labels in the dropdown create a user trust risk even when one option is technically correct.

## External Benchmarking
- Benchmark reference: PostgREST pagination guidance.
  - Key takeaway: clients must request ranges explicitly and should expect the server to return fewer rows than requested in the final page.
  - Applicability: this validates the current Report 1 pagination approach in `fetchReport1()` and helps rule out silent page truncation as the active root cause.
  - Adoption rationale: keep the existing full-pagination pattern because it is aligned with the underlying API model.
  - Rejection rationale: do not reopen pagination as the main defect hypothesis for this request because the local code already follows the relevant pattern.

- Benchmark reference: Nielsen Norman Group dropdown design guidance.
  - Key takeaway: interacting menus and visually ambiguous dropdown choices confuse users; unavailable or context-sensitive choices should remain understandable and distinguishable.
  - Applicability: if Report 1 shows two identical "София" options, users cannot reliably choose the analytically correct one.
  - Adoption rationale: the UI should make settlement choices unambiguous when duplicate labels can occur.
  - Adaptation rationale: the project likely needs a lightweight disambiguation or duplicate-avoidance approach rather than a broader control redesign.

- Benchmark scope note:
  - These external references support two separate conclusions: range-based pagination is already correctly handled, while ambiguous dropdown selection remains a valid UX and correctness concern.

## Minimal Spikes and Experiments
- **Spike: Report 1 pagination root-cause check**
  - Hypothesis: the София 2-category symptom is caused by a 1,000-row result truncation in the React data layer.
  - Approach: inspect `fetchReport1()` and verify whether it loops over multiple `.range()` pages.
  - Outcome: `fetchReport1()` paginates until a partial final page and aggregates over the full collected result set.
  - Conclusion: the active symptom is not explained by missing pagination in current workspace code.

- **Spike: Local transformed-data count for София**
  - Hypothesis: local schema already contains far more than 2 categories for Sofia, so the issue lies in how the page selects or interprets settlement identity.
  - Approach: count settlement rows in `dim_settlement.csv`, store links in `dim_store.csv`, and distinct categories in `fact_prices_lookback.csv` for Sofia-related settlement keys.
  - Outcome: local schema exposes two Sofia rows; canonical Sofia has 103 categories and padded Sofia has 2.
  - Conclusion: the analytical split is already present in transformed outputs and is sufficient to reproduce the symptom.

- **Spike: Raw ZIP verification of EKATTE variants**
  - Hypothesis: the padded Sofia code is a real recurring source-data variant, not a transform artifact invented locally.
  - Approach: scan recent ZIP archives using the exact column mapping from `src/transform.py` and count rows for `68134` and `068134`.
  - Outcome: recent ZIPs repeatedly contain 55 rows for `068134`; the latest ZIP has 374,419 rows for `68134` across 62 files and 55 rows for `068134` in one file.
  - Conclusion: upstream data contains the variant, so ETL normalization is the correct control point.

## AI Copilot Suggestions
- Finding: the current request is smaller than a broad "fix all issues in the page" interpretation but larger than a pure UI tweak.
  - Suggestion: keep the implementation centered on settlement identity normalization plus dropdown disambiguation, and avoid unrelated report refactors.

- Finding: the most important failure is a data-model split, not the visible chart rendering.
  - Suggestion: treat `src/transform.py` as the primary owning surface and use the React layer only to prevent ambiguous user selection if duplicate labels remain possible.

- Finding: the workspace already fixed the obvious pagination risk in `fetchReport1()`, so reworking that path would spend time without addressing the verified root cause.
  - Suggestion: preserve the current Report 1 pagination logic and focus regression coverage on duplicate settlement identity and selection behavior.

- Finding: any ETL natural-key change will be incomplete unless the resulting data regeneration and sync steps are explicit.
  - Suggestion: make the eventual implementation plan include reprocessing and documentation updates, otherwise the fix may appear to fail in environments using stale derived data.

- Finding: testability is good if the defect is modeled with a very small duplicate-settlement fixture.
  - Suggestion: add one ETL fixture for `68134` versus `068134` and one React fixture that proves two visible София options can no longer route to divergent category counts without clear distinction.

## Testing
- T1 — Active request artifacts exist: verify `.aib_memory/request.md`, `.aib_memory/analysis.md`, and the archived input under `.aib_memory/requests/R-20260508-0743-investigate-category-prices-page-calculation/inputs/` exist. Expected outcome: all files are present and readable.
- T2 — Request structure content check: verify `.aib_memory/request.md` contains all 12 required top-level sections in the correct order and that sections `Goal` through `Success criteria` are non-empty. Expected outcome: structure is complete and valid.
- T3 — Raw/source verification script: run a targeted script over recent `data/raw/*.zip` files and confirm the latest affected archive includes both `68134` and recurring `068134` rows, with the padded variant confined to a narrow slice. Expected outcome: raw verification reproduces the evidence used in this analysis.
- T4 — Local schema consistency check: run a targeted script over `data/schema/dim_settlement.csv`, `data/schema/dim_store.csv`, and `data/schema/fact_prices_lookback.csv` to confirm canonical Sofia resolves to 103 categories while the padded duplicate resolves to 2 before implementation, and collapses correctly after the fix. Expected outcome: pre-fix mismatch is reproducible and post-fix mismatch is eliminated.
- T5 — ETL normalization automated test: run the affected Python test slice covering `src/transform.py` settlement normalization. Expected outcome: padded and canonical EKATTE variants resolve to one logical settlement identity without breaking idempotent transform behavior.
- T6 — Report 1 regression automated test: run the affected Vitest slice covering `react-app/src/lib/dataService.js` and `react-app/src/components/Report1.jsx`. Expected outcome: Report 1 returns the full category set for the corrected Sofia selection path and does not regress pagination behavior.
- T7 — Tool/script execution check: if implementation changes the ETL natural key, execute the relevant transform/sync workflow for the touched slice and confirm it completes successfully with regenerated outputs. Expected outcome: the updated pipeline step exits 0 and produces consistent schema artifacts.
- T8 — Re-run idempotency check: re-run the affected transform/test commands without changing inputs. Expected outcome: no new duplicate settlement split is introduced and the same test suite still passes.
- T9 — Manual dropdown/UAT verification: validate the visible settlement selection behavior for София in the React UI and confirm it is no longer ambiguous or misleading. Expected outcome: user-visible behavior matches the corrected data model. See `UAT_scenarios.md` — UAT-01.

## Multi-Perspective Stakeholder Review
### Senior Solution Architect
The defect is technically feasible to fix with a contained change set, but only if the team treats settlement normalization as the owning abstraction. The current split between normalized display name and raw-key identity is architecturally inconsistent and allows downstream analytics to diverge from business meaning.

- The ETL is the architectural control point because it defines settlement identity for every downstream consumer.
- React-side disambiguation is still valuable as a guardrail because duplicate labels can confuse users even before full data cleanup is deployed.
- The risk is not query scale or pagination in current code; reopening that path would create churn without reducing the main defect.

### Product Owner
From a product perspective, the request has clear value because it addresses visible incorrect output on a flagship analytical page. Success is not just that "the page shows more rows" but that the user can trust settlement-level category completeness across the pipeline.

- The stated user problem is concrete and traceable to an observable business outcome.
- The acceptance criteria need end-to-end verification against raw data, not just a screenshot-level fix.
- The scope is appropriate if limited to the affected settlement-identity and selection path rather than a broad Report 1 redesign.

### User
The current behavior is confusing because a user selecting София expects the city's complete category picture, not two visually identical options with very different results. Even if the data technically exists, the UI currently puts too much burden on the user to discover the correct path.

- Duplicate visible settlement names make the control hard to trust.
- A 2-category result for Sofia looks like a broken report rather than a narrow source-specific edge case.
- Users benefit most from an outcome where settlement choice is either unique or clearly distinguishable.

### Security Officer
This request does not materially alter authentication or authorization, but it does touch public data integrity. Incorrect analytical slicing can undermine confidence in the published app even without exposing sensitive data.

- No new credentials, roles, or access patterns are required by the likely fix.
- The main security-adjacent concern is integrity of public-facing analytical output.
- If Supabase resync is required, deployment discipline still matters so stale remote data does not contradict the fixed local model.

### Data Governance Officer
This is a classic data-standardization issue: semantically identical identifiers are stored as distinct dimensional entities, which breaks lineage and analytical consistency. Governance quality improves when normalization rules are explicit and applied before identity assignment.

- `068134` versus `68134` should not create separate settlement entities if they refer to the same governed settlement.
- Lineage validation against raw files is necessary to justify canonicalization and avoid accidental over-merging.
- Documentation should explicitly state the normalization rule so future requests reason from the same data contract.