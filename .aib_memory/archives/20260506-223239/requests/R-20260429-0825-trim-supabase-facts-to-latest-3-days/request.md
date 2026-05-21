## Goal

During the Supabase load process, keep the remote fact data limited to the latest 3 available days so the hosted database stays within the 500 MB storage limit. The remote date dimension must stay aligned with the retained fact dates so the database and the React app expose only dates that still have retained fact data.

## Background

The current `src/load_supabase.py` flow provisions tables, upserts every dimension CSV from `data/schema/`, inserts only the newest local fact CSV that is not already present in Supabase, and fully refreshes `fact_prices_lookback`. It does not remove old rows from remote `fact_prices`, and `dim_date` is reloaded from the full local CSV on every run.

Workspace context documents that Supabase currently has no automated retention policy. The input for this request explicitly states that Supabase storage is limited to 500 MB and that only the latest 3 days should remain in the facts. Without retention pruning, the current append-only remote fact table will continue to grow even though the local schema keeps full history.

## Scope

- Update `src/load_supabase.py` so a Supabase sync run prunes remote `fact_prices` to the latest 3 available dates instead of keeping all historically loaded days.

- Define the retention window from the latest available local fact CSV dates in `data/schema/facts/`, because the loader is driven by local schema artifacts.

- Keep remote `dim_date` aligned to the retained remote fact dates so only retained dates remain available in the date dimension.

- Preserve the current responsibilities of `load_supabase.py`: table provisioning, dimension upserts, latest fact sync, and lookback refresh.

- Add or update automated tests for the retention behavior, including re-run idempotency.

- Update operator-facing documentation that currently describes the Supabase sync as append-only.

## Out of scope

- Deleting local raw ZIPs, local fact CSVs, or local dimension CSV history under `data/`.

- Repartitioning or redesigning Supabase tables.

- Changing the React app unless a server-side retention change exposes a documented mismatch that requires a follow-up request.

- Broad pruning of every non-date dimension unless it is required to preserve referential correctness or explicitly resolved through `## Questions & Decisions`.

- Changing `.aib_brain/` framework assets.

## Constraints

- Supabase storage is limited to 500 MB; retention must materially constrain remote fact growth.

- The sync must remain idempotent: re-running `src/load_supabase.py` with the same local inputs must complete without duplicating retained fact days or failing on already-pruned data.

- The retention rule applies during Supabase load only; the local star-schema files remain the authoritative historical source.

- The implementation must preserve referential integrity between retained fact rows and any dimension rows that remain in Supabase.

- No new third-party Python dependencies may be introduced.

- Existing DDL provisioning, RPC provisioning, and lookback refresh behavior in `src/load_supabase.py` must continue to work.

## Success criteria

- SC-1: After a successful `src/load_supabase.py` run, remote `fact_prices` contains rows for no more than the latest 3 available local fact dates.

- SC-2: After the same run, remote `dim_date` contains only the dates retained in remote `fact_prices`.

- SC-3: Running `src/load_supabase.py` again with unchanged local inputs completes without error and leaves the same retained remote date set.

- SC-4: Automated tests cover the retention behavior, including the retained-date calculation and re-run safety, and pass successfully.

- SC-5: Documentation reflects that Supabase load now enforces a rolling 3-day remote retention window rather than unbounded accumulation.

## Assumptions

- A1: The latest 3 days are determined from the newest local fact CSV filenames in `data/schema/facts/`, not from what currently exists remotely.
  - Risk if false: The implementation could prune the wrong remote days when local history and remote history diverge.

- A2: The local schema directory remains the source of full historical truth; remote Supabase is an intentionally trimmed serving layer.
  - Risk if false: Pruning remote data could destroy the only accessible history for operators or app consumers.

- A3: `fact_prices_lookback` should continue to represent the latest retained day snapshot and does not need a separate multi-day retention rule because it is already fully replaced on each sync.
  - Risk if false: Lookback data could become inconsistent with the retained fact window and require additional pruning logic.

- A4: The project virtual environment and `.env` already provide a working `DATABASE_URL`, as confirmed by a successful dry run of `venv/bin/python src/load_supabase.py` during analysis.
  - Risk if false: Implementation validation against the live Supabase database will be blocked.

- A5: The existing React app date selector behavior remains correct if `dim_date` is pruned to the same retained dates because it already filters by fact-present dates.
  - Risk if false: The app may depend on broader `dim_date` history and require a follow-up client adjustment.

- A6: The unresolved metadata-retention decision in Q001 is the only material scope ambiguity discovered in product docs and code inspection.
  - Risk if false: Additional hidden retention expectations could surface during implementation and force rework.

## Plan

### Task 1: Define retained remote date window
**Intent:** Establish the exact remote retention boundary that `load_supabase.py` must enforce on every run.
**Inputs:** `src/load_supabase.py`, local fact file names under `data/schema/facts/`, Q001 decision if answered.
**Outputs:** A deterministic retained-date selection rule expressed in code and tests.
**External Interfaces:** Local filesystem under `data/schema/facts/`.
**Environment & Configuration:** Project workspace; no new config keys.
**Procedure:**
1. Inspect the current latest-local-date logic and extend it to derive the newest 3 local dates.
2. Apply the Q001 outcome for whether date-related metadata retention includes `dim_file` in addition to `dim_date`.
3. Record the retention rule in code-level helper logic and in documentation updates.
**Done Criteria:** The implementation has one unambiguous definition of the retained remote date set for each run.
**Dependencies:** Q001 if answered; otherwise proceed with the recommended option documented there.
**Risk Notes:** Misdefining the retained window would either over-delete recent data or fail to contain storage growth.

### Task 2: Add remote pruning to `src/load_supabase.py`
**Intent:** Enforce rolling retention in Supabase while preserving current schema-provisioning and sync responsibilities.
**Inputs:** `src/load_supabase.py`, remote tables `fact_prices`, `dim_date`, and any date-related metadata table resolved in Task 1.
**Outputs:** Updated `src/load_supabase.py` with retention-aware helper functions and orchestration flow.
**External Interfaces:** Supabase PostgreSQL via `DATABASE_URL`.
**Environment & Configuration:** `.env` at project root; Python 3.9+; existing `psycopg2` connection flow.
**Procedure:**
1. Add helper logic to compute retained dates from local files and the corresponding retained `date_key` values.
2. Add SQL pruning for remote rows outside the retained window in the appropriate order to preserve foreign keys.
3. Keep the existing dimension upsert, latest fact-day insert, and lookback refresh behavior compatible with the new retention flow.
4. Ensure all SQL paths remain safe on re-run when the remote database is already trimmed.
**Done Criteria:** A sync run can converge the remote database to the latest 3 retained days without foreign-key failures.
**Dependencies:** Task 1.
**Risk Notes:** Incorrect delete ordering could violate FK constraints or retain orphaned metadata.

### Task 3: Extend automated test coverage for retention
**Intent:** Prove the new retention logic and delete orchestration are correct without relying on manual database inspection.
**Inputs:** `tests/test_load_supabase.py`, updated helpers in `src/load_supabase.py`.
**Outputs:** New or updated unit tests covering retained-date calculation, delete SQL intent, and re-run safety.
**External Interfaces:** Mocked psycopg2 connection objects only.
**Environment & Configuration:** Existing Python test environment.
**Procedure:**
1. Add tests for computing the latest 3 local dates from partitioned fact filenames.
2. Add tests asserting the loader executes pruning SQL for out-of-window rows.
3. Add tests that cover `dim_date` alignment to the retained date set.
4. Preserve existing test isolation with mocks and temporary files only.
**Done Criteria:** Tests fail if retention logic, delete order, or retained-date computation regresses.
**Dependencies:** Task 2.
**Risk Notes:** Over-mocking can miss integration defects, so test assertions must target observable SQL behavior clearly.

### Task 4: Run automated validation and idempotency checks
**Intent:** Confirm the implementation works in both the mocked test suite and the live loader execution path.
**Inputs:** Updated code, `tests/test_load_supabase.py`, working `.env`.
**Outputs:** Passing automated tests and successful loader re-run evidence.
**External Interfaces:** Supabase PostgreSQL for the live sync command.
**Environment & Configuration:** Project venv; `.env` with `DATABASE_URL`.
**Procedure:**
1. Run the narrow Python test slice for `test_load_supabase.py`.
2. Run `venv/bin/python src/load_supabase.py` and confirm it completes successfully.
3. Re-run the same command to verify idempotent convergence of the retained date window.
**Done Criteria:** Tests exit 0 and both live script runs exit 0 without retention-related errors.
**Dependencies:** Task 3.
**Risk Notes:** Live validation depends on the current remote database role having delete privileges on the affected tables.

### Task 5: Update context and operator documentation
**Intent:** Keep workspace documentation aligned with the new remote retention behavior.
**Inputs:** `.aib_memory/context.md`, `README.md`, updated request outcomes.
**Outputs:** Documentation updates that describe the rolling 3-day Supabase retention window and any retained metadata rule.
**External Interfaces:** None.
**Environment & Configuration:** Workspace documentation only.
**Procedure:**
1. Update `.aib_memory/context.md` to replace the current “no automated retention policy” statement for Supabase facts.
2. Update `README.md` so the `src/load_supabase.py` description reflects remote pruning and aligned date dimensions.
3. Note any documentation discrepancies discovered during implementation.
**Done Criteria:** Editable product docs and operator docs no longer describe the Supabase load as unbounded retention.
**Dependencies:** Tasks 1–4.
**Risk Notes:** Stale docs would cause operators to misunderstand what historical data remains remotely available.

## Documentation

- `.aib_memory/context.md` (ref_id: REF-0001) — Update the product context to reflect that Supabase fact retention is now enforced during load and that remote date availability is intentionally limited.
- `README.md` (ref_id: N/A) — Update the `src/load_supabase.py` description so operators understand that the remote Supabase dataset is trimmed to the latest 3 days.

## Questions & Decisions

**Q001**: When trimming Supabase data to the latest 3 days, should date-related metadata retention apply only to `dim_date`, or also to `dim_file` rows whose `zip_date` is outside the retained fact window?
- [ ] Option A: Prune only `fact_prices` and `dim_date`; keep full `dim_file` history remotely.
- [ ] Option B: Prune `fact_prices`, `dim_date`, and out-of-window `dim_file` rows so remote metadata matches the retained fact window. *(recommended)*
- [ ] Other: ___
> Answer: 

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `src/load_supabase.py` | Modified | Add retention-aware date-window calculation and remote pruning logic. |
| `tests/test_load_supabase.py` | Modified | Cover retained-date calculation, pruning SQL intent, and idempotency safeguards. |
| `.aib_memory/context.md` | Modified | Document the new remote retention policy and remove the outdated “no automated retention” statement for Supabase facts. |
| `README.md` | Modified | Update operator-facing description of the Supabase sync behavior. |
| `data/schema/facts/*.csv` | Read-only dependency | Determine the newest local 3-day retention window from existing partition files. |
| `data/schema/dim_date.csv` | Read-only dependency | Map retained remote fact dates to the authoritative local date dimension. |
| `data/schema/dim_file.csv` | Read-only dependency | Evaluate whether remote `dim_file` rows should be pruned alongside retained date metadata. |

## Internal Review of Request and Product Docs

- OK: `input.md` — The request intent is concrete about keeping only the latest 3 days in Supabase and aligning dimensions to available dates.
- OK: `.aib_memory/context.md` — Confirms there is currently no automated retention policy and that `load_supabase.py` is append-only for fact data.
- OK: `README.md` — Confirms current documentation describes the loader as provisioning tables, upserting dimensions, and inserting the latest local fact day only.
- Missing info: `input.md` / request scope — The request does not specify whether date-related metadata pruning should include `dim_file` in addition to `dim_date`.
- Ambiguity: `input.md` / request scope — “Ensure dimensions contain only the dates available” clearly applies to `dim_date`, but the treatment of other date-bearing metadata is materially underspecified; raised as Q001.
- Cross-ref issue: `.aib_memory/context.md` — The current statement “No automated retention policy” will become outdated once this request is implemented and must be revised.
- OK: `references.md` — `.aib_memory/context.md` is the only editable product document in the required-read set; `README.md` is additional operator documentation outside that set but still affected by this request.