## Executive Summary

- Request ID: `R-20260429-0825`.

- Request title: `Trim Supabase facts to latest 3 days`.

- This analysis run was auto-created from `.aib_memory/input.md` because `.aib_memory/requests_register.md` had no Active request before execution.

- The current Supabase loader is append-only for `fact_prices`, fully reloads dimensions from local CSVs, and therefore does not enforce the requested 3-day remote retention window.

- The highest-impact implementation area is `src/load_supabase.py`; the main design risk is pruning remote data without violating foreign keys or leaving date metadata inconsistent with retained fact dates.

- `request.md` was generated and updated with the mandatory request sections plus AI-generated `## Assumptions`, `## Plan`, `## Documentation`, `## Questions & Decisions`, `## Code and Asset Scan for Impacted Components`, and `## Internal Review of Request and Product Docs` sections.

- One moderate-severity decision was identified and raised as Q001: whether remote date-related metadata pruning should include `dim_file` in addition to `dim_date`.

## Domain Knowledge Essentials

- **Supabase retention window**: The number of recent business days intentionally kept in the hosted serving database. In this request the target window is 3 days.

- **Fact table**: A table that stores granular observations. Here, `fact_prices` stores product-price observations by date, store, file, category, and product.

- **Date dimension**: A lookup table that gives business meaning to date keys. Here, `dim_date` maps `date_key` values to ISO dates and calendar parts.

- **Lookback snapshot**: A derived fact-style table that enriches the latest retained day with day-1 and day-2 prices. Here, `fact_prices_lookback` is regenerated each sync run.

- **Serving layer**: The copy of data optimized for application access rather than full historical storage. In this workspace, Supabase is the serving layer and local CSVs are the fuller historical source.

- Impacted roles:
  - **Operator / data engineer**: Runs `src/load_supabase.py` and needs predictable remote storage usage.
  - **Analyst / app consumer**: Sees only dates still present in Supabase; stale dates in dimensions would create misleading filters.
  - **Maintainer**: Needs retention logic that remains deterministic and testable.

- Business process touched:
  - Daily ETL sync from local star-schema files into Supabase.
  - Date-filtered analytics in the React app, which depend on consistent remote date availability.

- Relevant KPIs / constraints:
  - Remote storage cap: 500 MB.
  - Retained fact horizon: 3 latest days.
  - Idempotent sync behavior: a rerun must converge to the same retained remote dataset.

- Acceptance impact:
  - Business acceptance depends on two things together: remote storage stays bounded, and users do not see dates in Supabase-backed filters that no longer have retained fact rows.

## Technical Knowledge & Terms

- **`src/load_supabase.py`**: Python sync module that provisions Supabase tables, upserts all dimension CSVs, inserts the latest local fact day not yet present remotely, and refreshes `fact_prices_lookback`.

- **`DIM_TABLES`**: Ordered descriptors used to upsert local CSV-backed dimension tables into Supabase.

- **`date_key`**: Integer surrogate key representing a date; it links `fact_prices` to `dim_date`.

- **Foreign key (FK)**: A relational constraint that requires referenced dimension rows to exist before dependent fact rows can remain valid.

- **Idempotency**: Re-running the same sync with unchanged inputs should converge without duplicate inserts or inconsistent deletes.

- **Pruning SQL**: Targeted `DELETE` statements that remove remote rows outside the retained window.

- **Evidence -> implication**:
  - `src/load_supabase.py` inserts only the newest missing local fact day -> the current remote fact table can only grow unless explicit pruning is added.
  - `src/load_supabase.py` upserts all rows from `data/schema/dim_date.csv` -> remote `dim_date` will continue to include historical dates unless aligned explicitly after pruning.
  - `insert_lookback()` truncates and reloads `fact_prices_lookback` every run -> the lookback table already behaves as a rolling snapshot and is not the primary storage-growth driver.
  - `.aib_memory/context.md` states there is no automated retention policy -> this request changes documented product behavior, not just implementation detail.
  - `tests/test_load_supabase.py` currently covers DDL execution and basic helper behavior only -> retention logic will require new tests to keep regressions visible.

- Files Read:
  - `.aib_memory/requests_register.md`
  - `.aib_memory/input.md`
  - `.aib_memory/references.md`
  - `.aib_memory/context.md`
  - `.aib_brain/Concepts.md`
  - `.aib_brain/conventions/analysis-convention.md`
  - `.aib_brain/conventions/request-convention.md`
  - `src/load_supabase.py`
  - `tests/test_load_supabase.py`
  - `README.md`

## Research Results

- Pattern scan against the current workspace shows the Supabase loader follows an **append newest partition only** pattern for facts and an **upsert full dimension state** pattern for dimensions.

- This pattern was sufficient when the remote database was treated as an accumulating replica, but it conflicts directly with the new serving-layer constraint of a 500 MB storage ceiling.

- The most local control point is the orchestration in `main()` of `src/load_supabase.py`, because that function already decides when to insert facts, when to upsert dimensions, and when to refresh lookback data.

- The main technical fork is not whether pruning is needed; that is explicit in the input. The only unresolved fork is the scope of date-related metadata pruning beyond `dim_date`, specifically whether `dim_file` should be trimmed together with out-of-window facts.

- Existing tests are mock-driven and isolated from a live database, which is a good fit for verifying delete-order intent, retained-date calculation, and idempotent convergence semantics.

- README and product context both currently describe the loader in a way that implies remote history can accumulate without bound. That wording becomes incorrect once this request is implemented.

## External Benchmarking

- **Benchmark 1: PostgreSQL `DELETE` command guidance**
  - Takeaway: PostgreSQL supports targeted `DELETE ... WHERE ...` and `DELETE ... USING ...` patterns, plus `RETURNING` when row counts or audit visibility are useful.
  - Applicability: This fits the current schema because the request is about pruning selected historical rows from ordinary tables, not replacing entire tables.
  - Adoption rationale: Adopt targeted delete-based retention because the current Supabase schema is a regular table layout and the requested retention horizon is very small.
  - Rejection rationale for alternatives: Do not switch this request to blanket `TRUNCATE` because the requirement is to keep the latest 3 days, not clear the whole table.

- **Benchmark 2: PostgreSQL partitioning guidance for old-data removal**
  - Takeaway: Native partitioning is the fastest long-term pattern for dropping whole old partitions, but it is most beneficial when designed in from the start and carries structural migration cost.
  - Applicability: The current `fact_prices` table in Supabase is not partitioned; local CSV partitioning does not automatically confer remote partition maintenance benefits.
  - Adoption rationale: Adopt only the conceptual lesson that retention should be date-window-driven; do not adopt table repartitioning in this request.
  - Rejection rationale for alternatives: Repartitioning Supabase would be a larger architectural migration than needed to satisfy the immediate storage-cap goal.

- **Benchmark 3: Supabase RLS and exposed-schema operations guidance**
  - Takeaway: Data changes in exposed schemas need to respect table privileges and RLS posture; backend administrative work should stay on the trusted server-side connection path.
  - Applicability: `src/load_supabase.py` already uses `DATABASE_URL` server-side, making it the correct place for retention deletes.
  - Adoption rationale: Keep retention logic in the Python loader rather than the React client or ad hoc browser-exposed SQL.
  - Rejection rationale for alternatives: Reject any client-side cleanup approach because it would be operationally brittle and security-inappropriate.

## Minimal Spikes and Experiments

- **Spike: Current loader runtime behavior**
  - Hypothesis: The current loader completes successfully and is already “up to date,” but it does not prune older remote facts.
  - Approach: Ran `venv/bin/python src/load_supabase.py 2>&1 | head -40` from the workspace root.
  - Outcome: The loader connected successfully, provisioned schema objects, upserted dimensions, reported `Latest local fact date  : 2026-04-28`, `Latest remote fact date : 2026-04-28`, and exited with `already up to date`.
  - Conclusion: The live path works today, and the request is a behavior change to retention policy rather than a repair of a failing loader.

- **Spike: Documentation alignment check**
  - Hypothesis: Operator-facing docs still describe `load_supabase.py` as append-only for facts.
  - Approach: Searched `README.md` for the current Supabase sync description.
  - Outcome: README states the loader “upserts all seven dimension CSVs, then inserts the latest local fact day not yet present in Supabase,” with no mention of retention.
  - Conclusion: Documentation updates are required as part of this request, not optional follow-up work.

## AI Copilot Suggestions

- Finding: The functional goal is small, but the hidden complexity is relational cleanup order.
  - Suggestion: Keep the implementation centered in one orchestration path inside `src/load_supabase.py` rather than scattering delete logic across helper layers.

- Finding: The request is storage-driven, not analytics-driven.
  - Suggestion: Treat Supabase as an intentionally trimmed serving layer and document that explicitly so future changes do not reintroduce full-history assumptions.

- Finding: The current wording “Ensure dimensions contain only the dates available” is narrower than the full referential-cleanup problem.
  - Suggestion: Resolve the metadata boundary explicitly before implementation, especially for `dim_file`, because otherwise the code will encode an unstated product decision.

- Finding: The easiest regression is silent re-expansion of `dim_date` during future dimension upserts.
  - Suggestion: Add tests that assert both retained fact dates and retained dimension dates after the sync path completes, not just that delete SQL ran.

- Scope note: The scope appears slightly smaller than a full “remote warehouse retention” feature and should stay that way. Expanding this request to broad orphan cleanup for every dimension or to remote repartitioning would be disproportionate to the stated 500 MB goal.

## Testing

- T1 — Request artifact creation: Verify `.aib_memory/requests/R-20260429-0825-trim-supabase-facts-to-latest-3-days/request.md` and `analysis.md` exist and contain all required top-level sections. Expected outcome: both files exist; required headings are present exactly once.

- T2 — Retained-date calculation: Run unit tests for the helper that derives the newest 3 local fact dates from `data/schema/facts/`. Expected outcome: the helper returns exactly the latest 3 available local dates in descending or otherwise documented deterministic order.

- T3 — Fact retention SQL behavior: Run unit tests asserting the loader issues pruning SQL for `fact_prices` rows outside the retained date window. Expected outcome: test doubles observe targeted delete behavior before final convergence; no delete touches retained dates.

- T4 — Date-dimension alignment: Run unit tests asserting the loader leaves remote `dim_date` aligned to the retained fact dates only. Expected outcome: after the sync flow, the retained remote `date_key` set in `dim_date` matches the retained `fact_prices` dates exactly.

- T5 — Script execution against live path: Run `venv/bin/python src/load_supabase.py` with the configured `.env`. Expected outcome: the script exits 0 and reports a successful convergence path with no retention-related errors.

- T6 — Re-run idempotency: Run `venv/bin/python src/load_supabase.py` a second time with unchanged local inputs. Expected outcome: the script exits 0 again and leaves the same retained remote date set without duplicate inserts or delete failures.

- T7 — Regression test suite: Run the narrow Python test slice covering `tests/test_load_supabase.py`. Expected outcome: the full touched test slice exits 0.

- T8 — Documentation content checks: Verify `.aib_memory/context.md` and `README.md` describe the Supabase loader as a rolling 3-day remote retention process after implementation. Expected outcome: both docs no longer imply unbounded remote fact accumulation.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The request is technically feasible with a contained change surface because the loader already centralizes Supabase write orchestration. The main architecture risk is not code size; it is encoding the wrong retention boundary and creating inconsistencies between facts and supporting date metadata.

- The narrowest correct control point is `src/load_supabase.py`, not the React app or ETL transform stage.
- FK-aware delete ordering is the critical integrity concern.
- Repartitioning Supabase would be architecture overreach for this request.

### Product Owner

The request has clear business value because the storage cap is explicit and the desired operating outcome is easy to explain: keep only the latest 3 days remotely. The acceptance criteria are mostly clear, with one notable scope ambiguity around whether date-related metadata retention includes only `dim_date` or also `dim_file`.

- The core value statement is concrete: stay under 500 MB while preserving recent analytics.
- Success criteria can be measured through retained-date counts and idempotent reruns.
- Q001 is the only meaningful product-decision gap identified during analysis.

### User

For the end user, the change should reduce confusion rather than add it, provided dates in the app never outlive the retained fact data. If dimensions are not kept consistent with the retained dates, users could still see stale filter choices and interpret that as broken data.

- Users care about available recent dates, not historical completeness in Supabase.
- Consistent date filters are more important than preserving hidden historical metadata remotely.
- The user-facing experience should remain stable if date retention and date dimensions stay synchronized.

### Security Officer

The request has low direct security risk because it changes server-side retention behavior on a trusted database connection and does not expand browser access. The main security-relevant concern is ensuring cleanup remains in the privileged backend path rather than leaking into client-side operations.

- Retention deletes belong in `src/load_supabase.py`, not in browser-exposed code.
- No new secrets, roles, or exposed endpoints are required.
- If additional SQL is added, it should continue using the existing trusted `DATABASE_URL` connection path.

### Data Governance Officer

This request materially changes remote data lifecycle policy, so it needs documentation clarity even though the data itself is public. The central governance question is whether Supabase is a historical system of record or a bounded serving copy; current analysis supports the latter.

- Local `data/schema/` remains the broader historical source; Supabase becomes a trimmed serving layer.
- Retention policy must be documented so downstream consumers do not assume indefinite remote history.
- Aligning `dim_date` with retained facts is necessary to avoid misleading lineage signals about available dates.