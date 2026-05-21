## Goal

Inspect `logs/pipeline.log` and identify all problems present in the ETL pipeline's execution history, including data-quality issues, operational problems, and structural log concerns.

## Background

The Kolko Ni Struva ETL pipeline processes daily retail price ZIP archives from the Bulgarian government portal (kolkostruva.bg/opendata). It runs locally, sometimes multiple times per day, writing JSON fact and dimension files. The pipeline emits a log file at `logs/pipeline.log`. As of 2026-04-18, this log file contains 860,427 lines covering runs from 2026-04-09 to 2026-04-14, processing dates from 2026-02-15 to 2026-04-13.

The operator noticed potential problems and wants a structured analysis of what went wrong in the pipeline runs captured in the log.

## Scope

- Review and categorise all WARNING-level log messages in `logs/pipeline.log`.

- Identify all distinct warning and error types emitted during data parsing (row-level and file-level).

- Identify operational concerns in how the pipeline was invoked (run frequency, backfill mode, concurrent runs).

- Identify trends in anomaly detection results over the date range covered.

- Identify log verbosity / observability issues that make diagnosis difficult.

- Provide a structured summary of problems by category with counts and affected companies.

## Out of scope

- Implementing fixes to the pipeline code.

- Changes to the EKATTE nomenclature or product category seed files.

- Any Supabase migration or cloud sync concerns.

- Analysis of the `data/quality/` report JSON files (only the log is in scope).

## Constraints

- The log file is read-only; no modifications to `logs/pipeline.log` are made.

- Analysis is based solely on the single log file covering the period 2026-04-09 to 2026-04-14.

- Python version ≥ 3.9 (per project constraints) if scripting is needed.

## Success criteria

- All distinct warning/rejection types are identified and counted.

- A per-problem explanation is provided, including the likely root cause and the business impact.

- A warning-trend chart or table across days is documented.

- All concurrent-execution observations are noted with supporting evidence from the log timestamps.

- The analysis document is produced with a structured, actionable problem list.

## Assumptions

- A1: The decimal-comma format (`1,50` instead of `1.50`) is the primary cause of `Invalid retail_price` warnings for pharmacy chains and other EU-locale vendors.
  - Risk if false: Other causes (non-numeric text, empty fields) may require additional handling beyond a comma-to-dot substitution.

- A2: EKATTE codes 68134-01 through 68134-10 are Sofia sub-district codes from the NSI full registry and are absent from the current `data/nomenclatures/cities-ekatte-nomenclature.json` seed.
  - Risk if false: These codes might represent vendor-defined invented codes that do not map to any official administrative entity.

- A3: The four companies with "Wrong column count (1)" submit single-column CSVs persistently across all dates; this is a vendor-side structural issue, not a transient error.
  - Risk if false: The files might be correct but encoded in an incompatible format (e.g., semicolon-delimited incorrectly treated as single-column).

- A4: Runs 1–3 on 2026-04-09 were terminated without reaching a `Pipeline finished` log line, implying either explicit interruption or silent process termination.
  - Risk if false: The `Pipeline finished` message might simply not have been captured in the log rotation cycle, and runs did complete successfully.

- A5: The anomaly WARNING spike on 2026-04-09 through 2026-04-12 (49-56 per day vs. typical 7-15) may reflect corrupted 7-day rolling baselines caused by concurrent dimension writes from overlapping runs, or could reflect genuine data quality shifts from multiple vendors in early April.
  - Risk if false: If it is a genuine vendor data shift, fixing the concurrent execution issue alone will not reduce future spikes.

## Plan

### Task 1: Document all problem categories from log analysis
**Intent:** Produce a structured problem catalogue with counts, affected entities, and severity classification.
**Inputs:** `logs/pipeline.log` (860,427 lines); `src/pipeline.py` (parse logic)
**Outputs:** Problem table in `analysis.md` or a summary report
**External Interfaces:** `logs/pipeline.log`
**Environment & Configuration:** Local workspace; Python ≥ 3.9 for scripting if needed
**Procedure:**
1. Grep and count each warning category using awk (already done in analysis).
2. For each category, identify top offending companies/codes and counts.
3. Classify severity: Critical (data loss), High (operational risk), Medium (quality), Low (observability).
4. Record findings in analysis.md.
**Done Criteria:** All 8 problems are documented with counts, root causes, and severity.
**Dependencies:** None
**Risk Notes:** Log file is 860K lines; grep/awk required — direct file reading is impractical.

### Task 2: Verify and enumerate unknown EKATTE codes in workspace data
**Intent:** Confirm which missing EKATTE codes can be resolved from existing workspace nomenclature files.
**Inputs:** `data/nomenclatures/Ekatte/` (raw NSI EKATTE data); `data/nomenclatures/cities-ekatte-nomenclature.json` (current seed)
**Outputs:** List of unresolvable vs. resolvable unknown EKATTE codes; candidate patch entries
**External Interfaces:** Workspace-local nomenclature files only
**Environment & Configuration:** Local; Python ≥ 3.9
**Procedure:**
1. Load all codes from `cities-ekatte-nomenclature.json`.
2. Extract unknown EKATTE codes from the log (top 20 by count).
3. Search for each code in the raw Ekatte XLS/CSV files under `data/nomenclatures/Ekatte/`.
4. Record which codes are found in the raw source and which are truly absent.
**Done Criteria:** A table mapping each top unknown EKATTE code to either "Found in NSI data" or "Not in NSI data".
**Dependencies:** Task 1

### Task 3: Confirm decimal-comma hypothesis for Invalid retail_price
**Intent:** Verify that comma-decimal format is the actual cause of price parse failures.
**Inputs:** `data/raw/<date>/` ZIP or CSV files from top-offending companies (e.g., Lilly Drogerie)
**Outputs:** Confirmation finding: "comma-decimal confirmed" or "other format found"
**External Interfaces:** `data/raw/` directory
**Environment & Configuration:** Local; Python
**Procedure:**
1. Extract one CSV from a recently downloaded ZIP for Lilly Drogerie (UIC from log).
2. Inspect the price field for rows that would trigger `Invalid retail_price`.
3. Attempt `float(val.replace(',', '.'))` on the failing value.
4. Record result.
**Done Criteria:** Root cause of `Invalid retail_price` confirmed with example.
**Dependencies:** Task 1

### Task 4: Confirm concurrent execution interleaving evidence
**Intent:** Solidify evidence that multiple pipeline runs operated simultaneously using timestamp analysis.
**Inputs:** `logs/pipeline.log`
**Outputs:** Timestamp table showing interleaved events from multiple processes
**External Interfaces:** `logs/pipeline.log`
**Environment & Configuration:** Local; grep/awk
**Procedure:**
1. Extract all `Pipeline starting`, `SKIP`, and `Completed` lines with timestamps.
2. Identify cross-run interleaving: events from different logical runs sharing the same time window.
3. Document the specific overlapping events in the analysis.
**Done Criteria:** Concrete timestamp evidence of concurrent execution is documented (already captured in analysis.md Spike 2).
**Dependencies:** None

## Testing

- T1 — All warning categories counted: Run `awk` summary against `logs/pipeline.log` and confirm total WARNING lines matches sum of all category counts (385,259 + 470,653 + 4,072 + 227 = 860,211). Expected outcome: sum equals total WARNING count.

- T2 — EKATTE 68134-01 in workspace data: Load top unknown EKATTE codes; search `data/nomenclatures/Ekatte/` subdirectory for code `68134-01`. Expected outcome: code is found in raw NSI files, confirming it is a resolvable gap.

- T3 — Decimal-comma root cause: Open a raw CSV from Lilly Drogerie. Expected outcome: price field rows with `Invalid retail_price` contain comma-decimal notation (e.g., `1,50`).

- T4 — Concurrent run evidence: Extract interleaved log lines; verify timestamp gap between "SKIP 2026-02-28" (08:24:09) and "Completed 2026-02-28" (08:24:10) spans two process contexts. Expected outcome: 1-second gap confirms concurrent writes.

- T5 — Analysis.md created: Verify `.aib_memory/requests/R-20260418-0120-check-pipeline-log-and-find-problems/analysis.md` exists and contains all 6 required sections per `analysis-convention.md`. Expected outcome: file present with correct section structure.

- T6 — request.md has all 14 sections: Verify `request.md` contains headings `## Goal` through `## Multi-Perspective Stakeholder Review` in correct order. Expected outcome: all 14 headings present.

## Documentation

- `docs/supabase-setup.md` (ref_id: N/A) — No update needed for this analysis-only request.

## Questions & Decisions

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
|---|---|---|
| `logs/pipeline.log` | Read-only dependency | Primary evidence artifact; read for analysis only |
| `src/pipeline.py` | Read-only dependency | Code inspected to understand warning conditions and REJECTED/WARNING logic |
| `.aib_memory/requests/R-20260418-0120-check-pipeline-log-and-find-problems/request.md` | Created | Request definition created during auto-request creation flow |
| `.aib_memory/requests/R-20260418-0120-check-pipeline-log-and-find-problems/analysis.md` | Created | Analysis output artifact |
| `.aib_memory/requests/R-20260418-0120-check-pipeline-log-and-find-problems/inputs/input-archive-2026-04-18_01-26-18.md` | Created | Archived input.md content per auto-request-creation branch |
| `.aib_memory/requests_register.md` | Modified | New Active request row added by create-request.py |
| `.aib_memory/input.md` | Modified | Reset to seed template with active request ID after analysis completion |
| `data/nomenclatures/cities-ekatte-nomenclature.json` | Read-only dependency | Used to understand scope of unknown EKATTE codes |
| `data/nomenclatures/Ekatte/` | Read-only dependency | Referenced as potential source for EKATTE gap resolution |

## Internal Review of Request and Product Docs

- OK: `request.md` — Goal, Background, Scope, and Success Criteria are consistent with each other and with findings from `logs/pipeline.log`.

- OK: `.aib_memory/context.md` — Accurately describes the log location, pipeline behaviour, and anomaly detection mechanism. Consistent with pipeline.py source code.

- Missing info: `request.md` — Does not specify whether the operator wants actionable fix recommendations or a read-only audit. Assumed: read-only audit (findings only, no code changes in scope).

- Missing info: `.aib_memory/references.md` — `logs/pipeline.log` and `src/pipeline.py` are not listed as references. They are operational artifacts, not product docs, but their role as primary evidence sources is not captured in the registry.

- OK: `analysis-convention.md` — All 6 mandatory sections present in `analysis.md`. Files Read bullet is populated.

- Cross-ref issue: `context.md` states "58 days processed as of the generation timestamp" but the log covers only dates 2026-02-15 to 2026-04-13 — this aligns correctly. No contradiction.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect

The most architecturally significant problem is the absence of a concurrency lock. The pipeline uses atomic temp-file-then-rename for individual file writes, which protects against partial file corruption from a single process, but does NOT protect against two processes performing SCD Type 2 dimension lookups and upserts concurrently. Both processes will load the same dimension state, make their respective upserts, and the last-write-wins — discarding the other's valid updates. This is a silent data integrity hazard.

- The lock could be added with 5 lines of code (`fcntl.flock`) and zero architectural changes.
- The log verbosity issue (860K lines per multi-run day) must be addressed before the pipeline can be monitored effectively by any toolchain.
- The missing EKATTE sub-district codes represent a fixable nomenclature gap, not a pipeline code issue.
- The decimal-comma price format issue is a low-risk, one-line fix.

### Product Owner

The pipeline is dropping a significant volume of data silently:
- ~385K invalid price rows from 9 major retailers (including Lilly Drogerie, Кауфланд, pharmacy chains).
- ~470K rows from locations with unresolved EKATTE codes (principally Sofia sub-districts).
- 4 companies are entirely excluded on every day due to "Wrong column count".

This translates to incomplete price coverage for consumers and analysts. Resolving the decimal-comma handling and extending the EKATTE nomenclature would recover the large majority of currently dropped rows. The success criteria (structured problem list with counts) is met by this analysis.

### User

From a pipeline operator's perspective, the key daily-operations problem is the 860K-line log that makes it impossible to answer "did today's run succeed?" without grep tooling. The `Pipeline finished` summary line at the very end is helpful but only present in the last run. Three runs terminated without a finish line, hiding whether they succeeded or failed. A persistent log-rotation setup and per-company summary warnings instead of per-row warnings would make the log operationally useful at first glance.

- The concurrent run problem creates scheduling confusion: the operator had to restart the pipeline 3 times in one morning, with unclear results.
- No alerting or notification mechanism is documented for WARNING/REJECTED status companies.

### Security Officer

This analysis involves read-only log audit and no changes to authentication, authorisation, or data exposure controls. However, the log file `logs/pipeline.log` contains company names, UIC numbers, and file counts — this is non-sensitive business data. No credentials or personal data appear in the log.

- The concurrent execution issue could in theory be exploited to inject corrupt dimension data if an attacker could trigger multiple pipeline runs, but the attack surface requires local filesystem access, which is outside the threat model for a local batch pipeline.
- Risk level: Low for security concerns. The primary risks are data integrity and operational, not security.

### Data Governance Officer

The pipeline is producing a star schema where the completeness of dimension records and fact rows is materially impacted by the identified problems:
- 470,653 rows with unknown EKATTE codes never reach the `dim_city` dimension or fact table. These trade objects are not classified geographically.
- 385,259 rows with invalid prices are excluded from the fact table entirely. Price data for affected companies is underreported.
- 4 companies (Wrong column count) contribute zero records to any fact table across all 58 days.
- Data lineage is not formally documented; the `data/quality/` report JSONs are the only lineage artifact. They do not capture the row-level skip counts (only company-level REJECTED status).
- Recommendation: the per-company skip counts (invalid_price_rows, skipped_ekatte_rows) should be added to `data/quality/YYYY-MM-DD-metrics.json` for auditability.

