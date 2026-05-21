# Analysis - Iteration 02

## Executive Summary

- **Request ID:** R-20260408-0113

- **Request Title:** Extract

- **Iteration ID:** 02

- **High-level purpose:** Iteration 02 supplements the core ETL pipeline scope (established in Iteration 01) with three new deliverables: (6) product user guide and technical documentation; (7) Supabase cloud-database setup instructions; (8) a Supabase migration script that fits within the 500 MB free-tier limit. No implementation has started yet — `src/` does not exist, all product-doc files remain stubs, and `implementation.md` is an empty log.

- **Earlier iterations:** Iteration 01 (Completed 2026-04-08 22:11:26) produced the core ETL analysis and rewrite of the request. All Iteration 01 findings, decisions, and assumptions carry forward unless explicitly overridden here. Per AIB precedence rule, Iteration 02 overrides Iteration 01 on any conflicting item.

- **Critical inconsistency:** The anomaly-detection threshold appears twice in the updated request.md with different values: item 5 of the Goal states "more than 25% deviation", whereas the Constraints section retains the Iteration 01 draft value of "default 30% row-count deviation". Iteration 02 treats **25%** as the authoritative threshold (Goal is more specific than Constraints; Iteration 02 > Iteration 01). This is flagged for explicit user confirmation in the Open Questions section.

- **Anomaly metric expansion:** The current request.md extends anomaly detection from row-count only (Iteration 01 assumption A8) to **three metrics**: unique product-code count, total row count, and unique product-name count — all compared against the same company's 7-day rolling mean with the same threshold.

- **Key open items:** Documentation format/path, migration script invocation model (one-time vs incremental), and acceptable Supabase granularity for historical data are user-owned and require confirmation before planning.

---

## Scope Interpretation

- **In scope — explicit (items 1–5, carried from Iteration 01):**

  - Download daily ZIP files from https://kolkostruva.bg/opendata that are not yet in `data/raw/`.

  - Extract and parse each company's CSV file (UTF-8 BOM, double-quoted field handling).

  - Populate JSON-based star schema under `data/schema/` (five SCD Type 2 dimension files + date-partitioned daily fact files).

  - Maintain nomenclature dimensions automatically as SCD Type 2; add new companies, trade objects, and products as they appear.

  - Detect anomalous/malformed company files by comparing three metrics (product-code count, row count, product-name count) against 7-day rolling mean per company, threshold 25%; write per-day anomaly report to `data/quality/`.

- **In scope — explicit (new, Iteration 02):**

  - Item 6: Product user guide AND technical documentation as separate deliverables.

  - Item 7: Setup instructions for a Supabase database (PostgreSQL schema + step-by-step guide); Supabase account already exists.

  - Item 8: A standalone Python migration script that loads local JSON star-schema data into Supabase while staying within the 500 MB free-tier storage limit. Last-week data at maximum available granularity; older periods aggregated as needed.

- **In scope — implicit:**

  - Backfill all 52 existing ZIPs on first run (confirmed by SC1 in request.md). (implicit rule - AIB framework)

  - Single `src/pipeline.py` entry point (confirmed by SC1 in request.md). (implicit rule - AIB framework)

  - Logging to `logs/` using Python `logging`. (implicit rule - AIB framework)

  - Documentation updates: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01 (explicit in Scope section of request.md, implicit as AIB framework rule when code is touched). (implicit rule - AIB framework)

  - New dependency additions to `requirements.txt` for Supabase client/PostgreSQL driver. (implicit rule - AIB framework)

- **Out of scope — explicit:**

  - Web API, dashboarding, or front-end.

  - Real-time alerting or email notifications for anomalies.

  - Data archiving, deletion, or retention policy enforcement.

  - Containerisation or CI/CD pipeline.

  - Changes to `data/raw/` directory layout or format.

  - Modification of source nomenclature JSON files (`data/nomenclatures/`).

- **Out of scope — implicit:**

  - Supabase authentication, row-level security, or API key rotation (the free tier is used for internal/developer use only).

  - Production scheduling; the pipeline is run manually for now.

  - `extract.py` deprecation or deletion (kept as-is per Iteration 01 Decision Point D1 default).

---

## Domain Knowledge Essentials

*(Carries all definitions from Iteration 01 unchanged; supplements listed below.)*

- **kolkostruva.bg / "Колко ни струва":** Bulgarian consumer-price open-data portal publishing daily ZIP archives of retail prices legally mandated from Bulgarian retailers.

- **EKATTE (ЕКАТТЕ):** National statistical classification code for Bulgarian populated places (5-digit numeric). Used as the city natural key in source data.

- **EIK / UIC (ЕИК):** Bulgaria's unique company identifier. Natural key for the company dimension; the CSV filename suffix.

- **Търговски обект (Trade Object):** A physical retail location. One company (UIC) may operate multiple trade objects and submit separate price rows for each.

- **SCD Type 2 (Slowly Changing Dimension):** Tracks full history of dimension attribute changes using `valid_from`, `valid_to`, `is_current` flags. New version row inserted on attribute change; old row closed.

- **Star schema:** Central fact table surrounded by denormalized dimension tables. Here realized as JSON files (local) and PostgreSQL tables (Supabase).

- **Суперbase / Supabase:** An open-source cloud platform providing a managed PostgreSQL database, Auth, Storage, and REST/Realtime APIs. Free tier includes one project with **500 MB PostgreSQL storage**. The project owner has an existing Supabase account. Connection to Supabase PostgreSQL is available via standard `libpq`-compatible drivers (e.g., `psycopg2`) using the connection string shown in the Supabase dashboard.

- **Free-tier 500 MB storage limit:** Applies to total shared table storage (heap + indexes + TOAST). TOAST stores out-of-line values for fields > 2 KB (not applicable here). Exceeding the limit may cause write failures.

- **Data aggregation for storage reduction:** Grouping and averaging fine-grained records into coarser temporal or dimensional buckets (e.g., daily product-level → weekly category-level) to meet a storage budget while preserving trend information.

- **User guide:** A document for non-developer end users (data analysts, researchers, journalists) explaining how to run the pipeline and interpret outputs. Typically a `README.md` or dedicated `docs/` file.

- **Technical documentation:** A document for developers explaining architecture, data model, configuration, and contribution. Typically a set of markdown files in `docs/` or the AIB product-doc infrastructure.

- **Affected personas:**
  - *Pipeline operator / developer:* runs `pipeline.py`, monitors logs and quality reports.
  - *Data analyst / researcher:* queries Supabase or local JSON files for price trends.
  - *Supabase admin:* creates the database schema, runs the migration script.

---

## Technical Knowledge & Terms

*(Carries all Iteration 01 technical terms unchanged; supplements listed below.)*

- **`psycopg2-binary`:** Python adapter for PostgreSQL using the `libpq` library. Supports `COPY` command for high-speed bulk insert. Not currently in `requirements.txt`; must be added for the migration script. The `-binary` variant bundles the native library (no external `libpq` installation required).

- **`supabase` (`supabase-py`):** Official Supabase Python client wrapping the REST/realtime API. Simpler setup than `psycopg2` but limited to ~1,000 rows per upsert call; not suitable for bulk loads of millions of rows.

- **`DATABASE_URL` / PostgreSQL connection string:** Provided by Supabase in dashboard → Settings → Database. Format: `postgresql://postgres:<password>@<host>:<port>/postgres`. Must be treated as a secret (not hardcoded in script).

- **Two-tier fact strategy (for 500 MB constraint):**
  - *Tier 1 — daily product-level* (last 7 days): One row per `(date, company_sk, product_sk, category_sk)`, storing `avg(retail_price)` and `min(promo_price)` aggregated across trade objects and cities. Eliminates `trade_object_sk` and `city_sk` from the Supabase fact table (these remain in the local JSON schema at full granularity).
  - *Tier 2 — weekly category-level* (all prior days): One row per `(week_start, company_sk, category_sk)`, storing `avg(retail_price)`, `avg(promo_price)`, `product_count`, `submission_count`.

- **Volume estimates (Tier 1 + Tier 2 + dimensions):**

  | Component | Rows | Est. size |
  |---|---|---|
  | fact_prices_daily (Tier 1, 7 days) | ~1.75M (≈250K/day) | ~160 MB incl. indexes |
  | fact_prices_weekly_hist (Tier 2, 45 days) | ~126K (6 wks × 208 × 101) | <10 MB |
  | dim_product | ~416K (SCD versions) | ~50 MB |
  | dim_company, dim_trade_object, dim_city, dim_category | ~6K total | <5 MB |
  | **Total estimate** | | **~225 MB** |

  This leaves ≈275 MB of headroom against the 500 MB limit and accommodates schema growth.

- **Anomaly-detection metrics (Iteration 02 expansion):** Three separate rolling-7-day per-company deviations are computed: (a) total row count, (b) count of unique product codes, (c) count of unique product names. A file is marked WARNING if any metric deviates > threshold (25%) AND the file is still parseable after normalization. REJECTED if the file cannot be parsed at all.

- **Surrogate key (SK):** Internal auto-increment integer assigned by the pipeline; used for FK references in the fact table. Stable across re-runs for the same natural key.

- **`requirements.txt` additions needed for Supabase migration:** `psycopg2-binary` (bulk load). Optionally `python-dotenv` for reading `DATABASE_URL` from a `.env` file (already an established Python pattern; not in current `requirements.txt`).

- **README.md vs AIB product docs:** The project already has an AIB product-doc infrastructure (`.aib_memory/docs/`). Item 6 likely means: (a) create a concise `README.md` in the project root for operator/analyst audience, AND (b) populate the currently-stub AIB product docs (DATA-01 through OBS-01) for the technical audience. Both are separate artifacts.

---

## Assumptions

*(Assumptions A1–A8 from Iteration 01 carry forward unchanged. New assumptions below.)*

- Assumption A1 (carried): `src/pipeline.py` is the single integrated download + ETL entry point; `extract.py` is kept but not the primary entry point.
  - (See Iteration 01 for full A1–A8 rationale; no change.)

- Assumption A9: The "product user guide" (item 6) is a `README.md` in the project root covering how to install, run, and interpret the pipeline; and "technical documentation" means populating the stub AIB product-doc files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01, OBS-01).
  - Rationale: The project has no `docs/` folder and no `README.md` file. The AIB docs infrastructure is the established technical-documentation system for this project. A single user-facing `README.md` is the standard entry point for any Python project.
  - Risk if false: If the user wants a richer separate `docs/` folder or a different documentation format, additional files must be created.
  - Falsification method: Ask user whether `README.md` + AIB docs is the expected deliverable for item 6.

- Assumption A10: The Supabase migration script (`src/migrate_supabase.py`) is intended as a **one-time initial load** (run after the pipeline has populated local JSON files). It is not a daily incremental sync.
  - Rationale: The word "migration" implies a one-time transfer of existing data. Incremental syncing is a materially more complex deliverable (requires change tracking, upsert logic against the Supabase state) and is not implied by the request.
  - Risk if false: If incremental sync is needed, the script architecture must include a watermark and upsert strategy, adding significant scope.
  - Falsification method: Ask user whether the script must support incremental daily runs.

- Assumption A11: "Last week" means the **7 most recent calendar days** for which fact data exists in `data/schema/facts/`.
  - Rationale: Iteration 01 established the 7-day rolling window for anomaly detection; using the same window for Supabase tiering is consistent and avoids introducing a new configurable parameter.
  - Risk if false: User may mean "current ISO calendar week" (Monday–Sunday). This would cause fewer days to be in Tier 1 early in the week.
  - Falsification method: Configurable constant `RECENT_DAYS = 7` in the migration script; no architectural impact.

- Assumption A12: For Supabase Tier 1 (last 7 days), the fact records will be **aggregated at the product level across trade objects and cities** (i.e., `trade_object_sk` and `city_sk` are dropped from the Supabase fact table). This reduces ~1.28M rows/day to ~250K rows/day while preserving product-level price intelligence.
  - Rationale: Storage estimate shows that even 7 days of full-granularity facts (~9M rows) exceeds 500 MB including indexes. Product-level aggregation gives ~1.75M rows for 7 days (~160 MB), well within budget.
  - Risk if false: If trade-object or city granularity is required in Supabase, Tier 1 must be restricted to fewer days (≤3 days at full granularity still risks the 500 MB cap).
  - Falsification method: Ask user whether per-store (trade-object level) price queries are required in Supabase.

- Assumption A13: The Supabase PostgreSQL connection string (`DATABASE_URL`) will be provided via an environment variable or `.env` file; it is **not** hardcoded in the migration script.
  - Rationale: Standard secret-management practice; prevents accidental credential exposure in source control.
  - Risk if false: None — this is a security requirement, not a preference.
  - Falsification method: N/A (enforced by implementation).

---

## Impact Assessment

### 6.1 Affected Components / Areas

*(Carries forward Iteration 01 list; new additions marked NEW.)*

- `src/pipeline.py` (new) — single entry point: download + ETL + quality checks.
- `src/migrate_supabase.py` (**NEW**) — one-time Supabase migration script.
- `README.md` (**NEW**) — project-root user guide and operational quickstart.
- `data/schema/` (new) — JSON star-schema dimensions and daily fact files.
- `data/quality/` (new) — anomaly reports per day.
- `data/nomenclatures/` — read-only seeding source for city and category dimensions.
- `data/raw/` — read-only ZIP landing zone.
- `requirements.txt` — must add `psycopg2-binary`; optionally `python-dotenv`.
- `logs/` — pipeline log output.
- `.aib_memory/docs/` stub files: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01 (**population of stubs NEW**).
- `.env` (**NEW**) — environment variable file; must be `.gitignore`d; contains `DATABASE_URL`.
- `.gitignore` — must include `.env` if not already present.

### 6.2 Change Type and Dependencies

| Component | Change Type | Dependencies | Sequencing |
|---|---|---|---|
| `src/pipeline.py` | Add | `data/raw/`, `data/nomenclatures/`, `data/schema/`, `data/quality/`, `logs/` | First to implement; prerequisite for migration |
| `src/migrate_supabase.py` | Add | `data/schema/` (output of pipeline), Supabase account, `psycopg2-binary` | After local schema is populated by pipeline |
| `README.md` | Add | Completed pipeline and documented schema | Can be drafted in parallel with implementation |
| AIB product-doc stubs | Modify (populate) | `src/pipeline.py` design finalized | After pipeline architecture is settled |
| `requirements.txt` | Modify | PyPI | Add `psycopg2-binary`; optionally `python-dotenv` |
| `.env` | Add | Supabase dashboard | Must be present before running migration script |
| `data/schema/` | Add | `data/raw/` | Created by pipeline |
| `data/quality/` | Add | `data/schema/` (dimension lookup) | Created by pipeline |

### 6.3 Domain Impacts

- DOMAIN (ARCH): New components `src/pipeline.py`, `src/migrate_supabase.py`, `data/schema/`, `data/quality/`, Supabase PostgreSQL instance must be documented in ARCH-01. ARCH-07 resource catalog must list all new directories and scripts.
  - Relevant: ARCH-01, ARCH-07

- DOMAIN (CMP): `src/pipeline.py` and `src/migrate_supabase.py` must be registered in CMP-01 script catalog.
  - Relevant: CMP-01

- DOMAIN (DATA): Core impact. DATA-01: kolkostruva.bg as source + Supabase as secondary store. DATA-02: star schema (local JSON) + Supabase two-tier physical model. DATA-03: lineage from ZIP to JSON to Supabase. DATA-04: JSON partitioned storage (local) + PostgreSQL tiered storage (Supabase). DATA-07: anomaly detection rules for three metrics.
  - Relevant: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07

- DOMAIN (KNW): KNW-01 must add "Supabase", "two-tier fact strategy", "data migration" to existing glossary entries.
  - Relevant: KNW-01

- DOMAIN (OBS): Logging strategy for both pipeline and migration script must be documented in OBS-01.
  - Relevant: OBS-01

- DOMAIN (SEC): `DATABASE_URL` is a credential and must be kept in `.env` (excluded from VCS). `.gitignore` must be reviewed. No other security impact (source data is public).
  - Relevant: SEC-03 (secrets management); no other SEC impact detected.

- DOMAIN (RQT): RQT-01 must include Supabase as a secondary data-access layer. RQT-02 must formalize Supabase schema and migration requirements.
  - Relevant: RQT-01, RQT-02

- DOMAIN (DEV): No impact detected.

- DOMAIN (DSR): No impact detected.

- DOMAIN (FNL): No impact detected.

- DOMAIN (OPR): No impact detected (no production automated scheduling required).

### 6.4 Constraints

*(Carries forward Iteration 01; additions below.)*

- Python 3 (≥3.9) only; no compiled native extensions except `psycopg2-binary` which bundles its own native library.
- All local persistence in JSON files; Supabase is an additional optional secondary store.
- Migration script must fit all migrated data within Supabase's **500 MB free-tier storage** limit.
- `DATABASE_URL` must not be hardcoded; must be read from environment or `.env` file.
- Migration script must be safe to run on a partially-populated or empty Supabase database (idempotent upsert strategy).
- Source site is public and unauthenticated; no credentials needed for download.
- Must process one ZIP at a time during ETL to bound memory.

### 6.5 Required Documentation Updates

| Ref ID | Document | Required update? | Reason |
|---|---|---|---|
| REF-0001 | ARCH-01 - High-level architecture | YES | New pipeline, migration script, and Supabase layer |
| REF-0006 | ARCH-07 - Resource catalog | YES | New directories, scripts, and Supabase resource |
| REF-0007 | CMP-01 - Notebook/script catalog | YES | `src/pipeline.py` and `src/migrate_supabase.py` |
| REF-0009 | DATA-01 - Source data catalog | YES | kolkostruva.bg source + Supabase destination |
| REF-0010 | DATA-02 - Data models | YES | Local JSON star schema + Supabase two-tier model |
| REF-0011 | DATA-03 - Data lineage | YES | ZIP → JSON → Supabase lineage added |
| REF-0012 | DATA-04 - Data storage strategy | YES | JSON + Supabase tiered storage pattern |
| REF-0015 | DATA-07 - Data quality rules | YES | Three-metric anomaly detection at 25% threshold |
| REF-0018 | KNW-01 - Domain glossary | YES | Supabase, two-tier strategy, migration script |
| REF-0021 | OBS-01 - Logging | YES | Logging for pipeline and migration script |
| REF-0022 | RQT-01 - Product charter | YES | Supabase added as secondary store component |
| REF-0023 | RQT-02 - Requirements document | YES | Supabase schema + migration requirements formalized |
| REF-0025 | SEC-02 - Infrastructure data protection | YES | `.env` / `DATABASE_URL` secret hygiene |
| REF-0026 | SEC-03 - Secrets management & rotation | YES | `DATABASE_URL` lifecycle documented |

### 6.6 Decision Points

*(Carries forward Iter 01 Decision Points D1–D4 as resolved; new below.)*

**Decision Point D5: Supabase bulk-load library choice**

- Option A: `psycopg2-binary` with direct `COPY` or `executemany` for bulk load.
  - Reason to choose: Fastest bulk insert (millions of rows in minutes), full PostgreSQL feature access, no row-count limitations per call.
  - Trade-off: Additional dependency; requires connection-string handling.
  - Recommended: YES for migration script.

- Option B: `supabase-py` REST client.
  - Reason to choose: Official SDK; simpler auth via API key (not direct DB connection).
  - Trade-off: ~1,000 row/request limit; loading 1.75M fact rows would require ~1,750 API calls: slow and rate-limited.
  - Recommended: NO for bulk migration; acceptable for small utility calls.

**Decision Point D6: Anomaly threshold value (inconsistency resolution)**

- The Goal (item 5) says "more than 25% deviation"; the Constraints section says "default 30%".
- Option A: Use 25% as the threshold (Goal overrides Constraints; Iter 02 overrides Iter 01).
  - Recommended: YES.
- Option B: Use 30% and treat Goal's "25%" as a typo.
  - Recommended: No basis to assume typo; Goal is more authoritative than Constraints.
- DECISION: Use 25% as the default threshold. Constraints section to be updated in the request rewrite.

**Decision Point D7: Migration script invocation model**

- Option A: One-time initial load only (run once after first pipeline run).
  - Implication: Simpler; no incremental logic. Must be documented to be re-run after data rebuild.
- Option B: Incremental daily sync (run alongside pipeline).
  - Implication: More complex; needs watermark or comparison against Supabase state.
- Default recommendation: Option A (one-time). Confirm with user.

---

## Research Plan and Findings

**Methodology:**

1. Internal-first: read `request.md` (active), `iterations.md` (02 active), `01-analysis.md`, `01-questionnaire.md`, `implementation.md`, `references.md`, all 27 product-doc refs, both AIB conventions.
2. Code scan: read `extract.py`, `requirements.txt`.
3. Workspace scan: confirmed no `src/` directory exists; no `README.md` exists; `implementation.md` is empty (no implementation yet).
4. Data volume analysis: estimated Supabase storage requirements using known data statistics (1.28M rows/day, 208 companies, 52 days).
5. Technology research: Supabase free-tier limits, `psycopg2-binary` vs `supabase-py` for bulk loads, two-tier aggregation strategy design.

**Evidence summary:**

| Evidence | Implication |
|---|---|
| All product-doc files are stubs | Item 6 (technical documentation) requires populating all eight stub files from scratch |
| No `src/` directory or `README.md` exists | Implementation has not started; both pipeline and migration are fully greenfield |
| `implementation.md` is empty | No code was written in Iteration 01; Iteration 02 is still pre-implementation |
| `requirements.txt` includes `fastapi`, `uvicorn`, `httpx`, `aiofiles` | A web API is likely planned in a future request; these deps are out of scope for this request |
| `requirements.txt` does NOT include `psycopg2-binary` or `supabase` | Both must be added as part of item 8 scope |
| No `.env` or `.gitignore` file in workspace | Both must be created; `.env` for `DATABASE_URL`; `.gitignore` to protect it |
| Supabase free tier = 500 MB storage | Full 52-day raw facts (~6.6 GB) cannot be stored; two-tier aggregation required |
| 7 days × 1.28M rows = 8.96M rows at full granularity | Even 7 days at full detail exceeds 500 MB including indexes; product-level aggregation (×0.2) reduces to ~1.75M rows for 7 days ≈ 160 MB |
| anomaly threshold: 25% in Goal, 30% in Constraints | Inconsistency; treated as 25% per Decision Point D6 |
| 01-questionnaire.md: all options unchecked | User answered questions by updating request.md directly rather than checking questionnaire boxes; this is valid; answers are inferred from request content |
| QID-BF-001 answer (inferred from request.md item 5): structural + volumetric, 3 metrics | Scope of anomaly detection confirmed |
| QID-BF-002 answer (inferred from SC1): YES backfill all 52 ZIPs | Backfill confirmed |
| QID-AT-001 answer (inferred from SC1): single `src/pipeline.py` | Architecture confirmed |
| QID-AT-002 answer (inferred from request.md Goal item 5): 25% | Threshold confirmed (see inconsistency note) |

**Gaps and unknowns:**

1. Documentation format for item 6: `README.md` + AIB docs assumed but not confirmed.
2. Migration invocation model: one-time or incremental? Assumed one-time.
3. Supabase granularity requirement: trade-object/city level needed or product-level aggregation acceptable?
4. Anomaly threshold canonical value: 25% or 30%? Pending user confirmation.

**Files read:**

- `.aib_brain/prompts/aib-analysis.md` — execution trigger; defines output rules.
- `.aib_memory/requests/R-20260408-0113-extract/request.md` — active request; current Iteration 02 content.
- `.aib_memory/requests/R-20260408-0113-extract/iterations.md` — Iteration 01 Completed; Iteration 02 Active.
- `.aib_memory/requests/R-20260408-0113-extract/01-analysis.md` — full Iteration 01 analysis; all findings carried forward.
- `.aib_memory/requests/R-20260408-0113-extract/01-questionnaire.md` — all options unchecked; answers inferred from request.md updates.
- `.aib_memory/requests/R-20260408-0113-extract/implementation.md` — empty; no implementation yet.
- `.aib_memory/references.md` — 27 product-doc refs; all type=product-doc.
- `.aib_brain/conventions/analysis-convention.md` — mandatory structure.
- `.aib_brain/conventions/request-convention.md` — rewrite format rules.
- `.aib_brain/Concepts.md` — AIB framework action contract.
- `.aib_memory/docs/04 Technology/Architecture/ARCH-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Inventory/ARCH-07.md` — stub only.
- `.aib_memory/docs/04 Technology/Compute/CMP-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Sources/DATA-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Models/DATA-02.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Workspace/DATA-03.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Workspace/DATA-04.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Workspace/DATA-07.md` — stub only.
- `.aib_memory/docs/02 Domain/Terms and Concepts/KNW-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Observability/OBS-01.md` — stub only.
- `.aib_memory/docs/01 Product Management/Product Charter/RQT-01.md` — stub only.
- `.aib_memory/docs/03 Requirements/RQT-02.md` — stub only.
- `.aib_memory/docs/04 Technology/Access and Security/SEC-02.md` [SKIPPED — domain out of scope for current iteration focus; stub confirmed]
- `.aib_memory/docs/04 Technology/Access and Security/SEC-03.md` [SKIPPED — domain out of scope for current iteration focus; stub confirmed]
- `extract.py` — download script; unchanged from Iteration 01 review.
- `requirements.txt` — confirmed: `fastapi/uvicorn/requests/beautifulsoup4/aiofiles/httpx`; no Supabase or psycopg2.

---

## Rewrite Proposal of the Request

*(Full rewrite resolving the 25%/30% inconsistency, adding precision to items 6–8, and adding success criteria SC7–SC9 for the new deliverables.)*

### Goal

Build a Python 3 ETL pipeline (`src/pipeline.py`) that:

1. Downloads daily ZIP price files from `https://kolkostruva.bg/opendata` that are not yet present in `data/raw/`.

2. Extracts and parses each company's CSV file from each unprocessed ZIP (handling UTF-8 BOM encoding and double-quoted CSV anomalies).

3. Populates a JSON-based star schema (`data/schema/`) with five SCD Type 2 dimension files and date-partitioned daily fact files.

4. Maintains nomenclature dimensions automatically, adding new companies, trade objects, and products as slowly-changing dimensions (SCD Type 2).

5. Detects anomalous or malformed company files by comparing each file against the same company's historical submissions and checks for significant (more than **25%**) deviation in unique product-code count, total row count, and unique product-name count against the 7-day rolling mean; writes a per-day anomaly report to `data/quality/`.

6. Creates a `README.md` project user guide (installation, usage, output description) and populates the stub AIB technical documentation files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) with project-specific content.

7. Creates `docs/supabase-setup.md` — a step-by-step instruction document for setting up the Supabase PostgreSQL database from the local JSON star-schema, including the full SQL DDL to create all tables, indexes, and foreign keys.

8. Creates `src/migrate_supabase.py` — a standalone Python script that reads local JSON star-schema data and loads it into the Supabase PostgreSQL database using a two-tier strategy: (a) Tier 1: last 7 days of data at daily product-level aggregation (`avg_retail_price`, `min_promo_price` across trade objects and cities); (b) Tier 2: all older data aggregated at weekly category-level (`avg_retail_price`, `avg_promo_price`, `product_count`, `submission_count`). Total migrated data must remain within **500 MB** of Supabase storage including indexes.

### Background

The project collects daily retail prices from the Bulgarian government's open-data portal (kolkostruva.bg). An existing script `extract.py` scrapes and downloads daily ZIP archives into `data/raw/`. As of 2026-04-07, 52 daily ZIP files (2026-02-15 to 2026-04-07) are present. No analytical data store exists yet; all nomenclature data is in JSON files under `data/nomenclatures/`.

Key source data characteristics (verified from `data/raw/`):
- ZIP naming: `YYYY-MM-DD.zip`; ~208 company CSV files per ZIP; ~1.28M rows per ZIP; ~20 MB per ZIP.
- CSV filename format: `CompanyName (LegalName)_UIC.csv` (UIC = Единен идентификационен код / EIK).
- CSV columns (7, UTF-8 BOM encoded): "Населено място" (EKATTE city code), "Търговски обект" (trade object name), "Наименование на продукта" (product name), "Код на продукта" (company-specific product code), "Категория" (category ID 1–101), "Цена на дребно" (retail price), "Цена в промоция" (promo price, may be empty).
- Nomenclatures: `cities-ekatte-nomenclature.json` (EKATTE to city name), `product-categories.json` (101 category IDs and names including 86–101 for pharmaceutical products).
- Known data quality issue: some files (e.g., pharmacy chains) have double-quoted CSV field values that require normalization during parsing.

### Scope

- `src/pipeline.py` — single entry point integrating download, ETL, and quality checks.
- `src/migrate_supabase.py` — standalone Supabase migration script.
- `README.md` — project user guide (installation, configuration, usage, outputs).
- `docs/supabase-setup.md` — Supabase database setup instructions with full SQL DDL.
- `.env` — environment variable file (contains `DATABASE_URL`; must be added to `.gitignore`).
- `data/schema/dim_company.json` — SCD Type 2; natural key = UIC.
- `data/schema/dim_trade_object.json` — SCD Type 2; natural key = (UIC, trade-object-name).
- `data/schema/dim_product.json` — SCD Type 2; natural key = (UIC, product-code).
- `data/schema/dim_city.json` — SCD Type 2; natural key = EKATTE code; seeded from nomenclature.
- `data/schema/dim_category.json` — SCD Type 2; natural key = category ID; seeded from nomenclature.
- `data/schema/facts/YYYY-MM-DD.json` — one full-granularity fact file per day locally.
- `data/quality/YYYY-MM-DD-report.json` — per-day anomaly report; per-company status: OK / WARNING / REJECTED.
- Backfill: process all 52 existing ZIPs on first run.
- Logging: write to `logs/` using Python `logging`.
- Documentation updates: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01.

### Out of scope

- Web API, dashboarding, or front-end.
- Real-time alerting or email notifications for anomalies.
- Data archiving, deletion, or retention policy.
- Containerisation or CI/CD pipeline.
- Changes to the `data/raw/` directory layout or format.
- Modification of source nomenclature JSON files (`data/nomenclatures/`).
- Supabase incremental daily sync (migration script is one-time initial load only).
- Supabase row-level security, authentication policies, or API key rotation.

### Constraints

- Python 3 (≥3.9) only; `psycopg2-binary` permitted as an exception to the native-extension rule (it is self-contained and standard).
- Must process one ZIP at a time to bound memory to one day's data.
- Source site is public and unauthenticated; no credential management required for download.
- Must be idempotent: re-running the pipeline against a ZIP that has already been processed must produce no duplicate records.
- Anomaly detection threshold (default **25%** deviation from 7-day rolling mean) must be configurable via a script-level constant or `--threshold` CLI argument.
- `DATABASE_URL` for Supabase must be read from the `DATABASE_URL` environment variable (or `.env` file); never hardcoded.
- Total Supabase storage after migration must not exceed **500 MB** (including table heap and indexes).

### Success criteria

- SC1: `python src/pipeline.py` processes all 52 existing ZIPs without crash; 52 daily fact files exist under `data/schema/facts/`.
- SC2: Dimension files contain correct SCD Type 2 records (with `valid_from`, `valid_to`, `is_current`) for all companies, trade objects, products, cities, and categories from raw data; no missing surrogate key in fact files.
- SC3: A quality report exists at `data/quality/YYYY-MM-DD-report.json` for each processed day; a pharmacy-chain file with double-quoted CSV fields from 2026-02-15 is flagged with status `WARNING` and reason citing double-quoted CSV fields.
- SC4: Re-running the script a second time when no new ZIPs are available produces no new fact or dimension records (idempotency verified).
- SC5: A newly downloaded ZIP is processed within the same pipeline run that downloads it; its fact file appears in `data/schema/facts/` after the run completes.
- SC6: The anomaly threshold constant is configurable via a script-level constant or `--threshold` CLI argument.
- SC7: `README.md` exists in the project root; it covers installation, running the pipeline, and interpreting quality reports. All eight AIB product-doc stub files (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) are populated with project-specific content (no longer contain only `_This file is seeded by AIB initialize._`).
- SC8: `docs/supabase-setup.md` exists; it contains valid PostgreSQL DDL (CREATE TABLE statements for all dimension and fact tables) and a step-by-step guide for applying it in Supabase.
- SC9: `python src/migrate_supabase.py` loads all local JSON data into Supabase without error when `DATABASE_URL` is set. After migration, total Supabase storage usage is ≤500 MB. Tier 1 table (`fact_prices_daily`) contains rows only for the 7 most recent days; Tier 2 table (`fact_prices_weekly_hist`) contains weekly aggregates for all older days.

---

## Solution Options

**Option A: psycopg2-binary for migration, stdlib for pipeline**

- Overview: `src/pipeline.py` uses only `requests`, `beautifulsoup4`, and Python stdlib (CSV, JSON, zipfile, pathlib, logging). `src/migrate_supabase.py` uses `psycopg2-binary` with `execute_values()` for batch inserts (1,000 rows per batch) or server-side `COPY` via `copy_expert()` for the highest throughput.
- Benefits: No API rate limits; fastest bulk insert (COPY can load millions of rows in seconds); full PostgreSQL DDL support; minimal additional dependencies.
- Trade-offs: Direct PostgreSQL connection requires port 5432 to be open (Supabase's session pooler port is 5432 by default; available on free tier). Requires `psycopg2-binary` in `requirements.txt`.
- Constraints: Connection string from Supabase dashboard → Settings → Database → Connection string (URI mode).
- Risks: Supabase free tier may enforce connection limits (10 direct connections); script should use a single connection and close it promptly.
- Expected effort: Low-Medium. Dimension upsert logic is the most complex part (ON CONFLICT DO UPDATE).
- Acceptance test: Load dim_company + one day of Tier 1 facts; query from Supabase UI; verify row counts match local JSON.

**Option B: supabase-py REST client for migration**

- Overview: Both scripts use `supabase-py`. Migration loads data by calling `table.upsert(rows)` in batches of 500–1,000 rows.
- Benefits: Official Supabase SDK; uses API key (no direct DB connection needed). Easier to establish from environments where port 5432 is blocked.
- Trade-offs: Rate-limited REST calls; loading 1.75M Tier 1 rows requires ~3,500 API calls (~minutes). No COPY support. `supabase-py` needs `SUPABASE_URL` + `SUPABASE_KEY` (two env vars instead of one `DATABASE_URL`).
- Constraints: Supabase free tier has default API rate limits; large upsert batches may throttle.
- Risks: Significantly slower for initial migration; potential for partial loads if rate limit is hit mid-migration.
- Expected effort: Medium (retry logic needed per batch).
- Acceptance test: Same as Option A but monitor for rate-limit HTTP 429 responses during load.

**Recommendation:** Option A (`psycopg2-binary` direct connection). Direct PostgreSQL is faster, more reliable for bulk loads, and is the standard approach for data migrations. The `COPY` command loads the 1.75M Tier 1 rows orders of magnitude faster than REST batches. Option B is acceptable if Supabase port 5432 is not accessible from the user's environment.

---

## Affected Documentation

| ref_id | document_title | path | reason_for_inclusion |
|---|---|---|---|
| REF-0001 | ARCH-01 - High-level architecture | .aib_memory/docs/04 Technology/Architecture/ARCH-01.md | New pipeline, migration script, Supabase layer |
| REF-0006 | ARCH-07 - Resource catalog | .aib_memory/docs/04 Technology/Inventory/ARCH-07.md | New directories, scripts, Supabase resource |
| REF-0007 | CMP-01 - Notebook/script catalog | .aib_memory/docs/04 Technology/Compute/CMP-01.md | `src/pipeline.py` and `src/migrate_supabase.py` |
| REF-0009 | DATA-01 - Source data catalog | .aib_memory/docs/04 Technology/Data Sources/DATA-01.md | kolkostruva.bg source + Supabase destination |
| REF-0010 | DATA-02 - Data models | .aib_memory/docs/04 Technology/Data Models/DATA-02.md | Local JSON star schema + Supabase two-tier model |
| REF-0011 | DATA-03 - Data lineage | .aib_memory/docs/04 Technology/Data Workspace/DATA-03.md | ZIP → JSON → Supabase lineage |
| REF-0012 | DATA-04 - Data storage strategy | .aib_memory/docs/04 Technology/Data Workspace/DATA-04.md | JSON + Supabase dual-storage pattern |
| REF-0015 | DATA-07 - Data quality rules | .aib_memory/docs/04 Technology/Data Workspace/DATA-07.md | Three-metric anomaly detection at 25% |
| REF-0018 | KNW-01 - Domain glossary | .aib_memory/docs/02 Domain/Terms and Concepts/KNW-01.md | Supabase, two-tier, migration, 25% threshold |
| REF-0021 | OBS-01 - Logging | .aib_memory/docs/04 Technology/Observability/OBS-01.md | Pipeline + migration script logging strategy |
| REF-0022 | RQT-01 - Product charter | .aib_memory/docs/01 Product Management/Product Charter/RQT-01.md | Supabase included as secondary store |
| REF-0023 | RQT-02 - Requirements document | .aib_memory/docs/03 Requirements/RQT-02.md | Supabase schema and migration requirements |
| REF-0025 | SEC-02 - Infrastructure data protection | .aib_memory/docs/04 Technology/Access and Security/SEC-02.md | `.env` and `DATABASE_URL` secret hygiene |
| REF-0026 | SEC-03 - Secrets management & rotation | .aib_memory/docs/04 Technology/Access and Security/SEC-03.md | `DATABASE_URL` secret lifecycle |

---

## Operational & Documentation Implications

- **Pipeline operation:** A new daily run of `python src/pipeline.py` must be scheduled (manually or via cron) to keep data current. Logs written to `logs/pipeline-YYYY-MM-DD.log` (rolling or per-run).

- **Migration operation:** `src/migrate_supabase.py` is a one-time command run after the pipeline has fully populated `data/schema/`. Expected runtime: ~5–15 minutes for the initial Tier 1 + Tier 2 load depending on network speed. After a run, local `data/schema/` remains the authoritative store; Supabase is a secondary, queryable copy.

- **Secret management:** `DATABASE_URL` stored in `.env` file (not committed to VCS). `.gitignore` must include `.env`. Documentation must instruct users to create `.env` before running the migration script.

- **Supabase schema management:** `docs/supabase-setup.md` includes the full DDL. Any schema change (e.g., adding an index) requires manual re-application in the Supabase SQL editor.

- **Anomaly report observability:** `data/quality/YYYY-MM-DD-report.json` is the primary quality monitoring artifact. No automated alerting; the operator must inspect reports manually after each run.

- **Documentation delivery:** `README.md` and the eight AIB product-doc stubs are part of the implementation scope. They should be written or updated concurrent with or after `src/pipeline.py` implementation is stable.

- **Storage monitoring:** After initial migration, the Supabase dashboard → Settings → Database shows current storage usage. If it approaches 500 MB over time (as new daily data is processed and re-migrated), the `RECENT_DAYS` constant in the migration script should be reduced, or Tier 2 aggregation period should be shortened.

---

## Risks

- Risk R1: Supabase free-tier storage is exceeded by the migration despite the two-tier strategy.
  - Probability: Low (estimated ~225 MB vs 500 MB limit; headroom ~275 MB).
  - Impact: High (migration fails; data not accessible in Supabase).
  - Mitigation: Storage estimate is conservative. If estimates are wrong, reduce `RECENT_DAYS` from 7 to 5 in the migration script to shed ~70 MB from Tier 1. Add a pre-flight storage check via Supabase `pg_database_size()` query before bulk load.
  - Owner (role): Developer.

- Risk R2: Using `psycopg2-binary` cannot connect to Supabase (port 5432 blocked by ISP or firewall).
  - Probability: Low–Medium (depends on user network environment).
  - Impact: Medium (migration script fails; fallback to `supabase-py` Option B needed).
  - Mitigation: Detect connection failure with a clear error message and instructions to switch to Supabase's connection pooler (port 6543) or use `supabase-py` Option B.
  - Owner (role): Developer.

- Risk R3: Large single-day fact JSON files (~100–300 MB uncompressed per day) cause slow reads during migration and during ETL.
  - Probability: Medium.
  - Impact: Low–Medium (slows throughput but does not break correctness).
  - Mitigation: Stream JSON fact files using `ijson` incremental parser instead of loading entire file into memory. If `ijson` is not in `requirements.txt`, standard `json.load()` is acceptable for files up to ~300 MB on a modern machine.
  - Owner (role): Developer.

- Risk R4: Anomaly threshold inconsistency (25% vs 30%) is not resolved before implementation, resulting in the wrong value being hardcoded.
  - Probability: High (if no explicit user confirmation is obtained).
  - Impact: Low (threshold is a configurable constant; easy to change; no data corruption).
  - Mitigation: Flag in questionnaire (OQ-001 below); default to 25% per Decision Point D6; make it a clearly named constant `ANOMALY_THRESHOLD = 0.25`.
  - Owner (role): Developer.
  - Contingency: If user confirms 30%, update the constant and re-run quality checks in <5 minutes.

- Risk R5: "Product user guide and technical documentation" scope is misunderstood — user expects a richer deliverable than `README.md` + populated AIB stubs.
  - Probability: Medium.
  - Impact: Medium (additional documentation artifacts must be created; rework of already-written docs).
  - Mitigation: Clarify scope in questionnaire (OQ-002 below) before documentation work begins.
  - Owner (role): Developer / User.

- Risk R6: Supabase free-tier project is paused due to inactivity (free projects auto-pause after 1 week of no queries).
  - Probability: Medium (Supabase policy for free tier).
  - Impact: Low (easily reactivated via dashboard; no data loss).
  - Mitigation: Document in `docs/supabase-setup.md` that free projects must be periodically queried or upgraded to Pro to avoid auto-pause.
  - Owner (role): Operator.

---

## Disambiguation Questionnaire

- **Question:** What is the authoritative anomaly detection threshold — 25% (stated in Goal item 5) or 30% (stated in Constraints section)?
  - **Chosen Answer / Value:** 25% (analysis default per Decision Point D6; Goal overrides Constraints).
  - **Rationale:** Goal is more specific and was updated in Iteration 02; Constraints section retains an Iteration 01 draft value.
  - **Evidence / Reference:** `request.md` Goal item 5 vs. Constraints section; `01-analysis.md` Assumption A8.
  - **Impact if changed:** Trivial — update one constant `ANOMALY_THRESHOLD` in `pipeline.py`.

- **Question:** What is the expected deliverable for item 6 "product user guide and technical documentation"?
  - **Chosen Answer / Value:** (a) `README.md` in project root (user guide) + (b) populate eight AIB product-doc stubs (technical documentation).
  - **Rationale:** No `README.md` or `docs/` folder exists; AIB docs infrastructure is the established technical-doc system.
  - **Evidence / Reference:** Workspace scan (no README, no docs/); `references.md` listing of product-doc files.
  - **Impact if changed:** If richer separate `docs/` is required, additional files must be created; higher effort.

- **Question:** Should `src/migrate_supabase.py` support incremental daily runs or is it a one-time initial load?
  - **Chosen Answer / Value:** One-time initial load (Assumption A10 default).
  - **Rationale:** "Migration" implies one-time transfer; incremental sync adds significant complexity.
  - **Evidence / Reference:** Assumption A10; request text "Create separate script for migration".
  - **Impact if changed:** Incremental sync requires watermark tracking and upsert-against-remote state; +1–2 implementation days.

- **Question:** For Supabase Tier 1 (last 7 days): is product-level daily aggregation (aggregated across trade objects and cities) acceptable, or must per-store (trade-object level) prices be preserved for Supabase queries?
  - **Chosen Answer / Value:** Product-level aggregation assumed acceptable (Assumption A12 default).
  - **Rationale:** Storage estimate shows full-granularity 7-day facts exceed 500 MB; product-level facts (~1.75M rows, ~160 MB) fit comfortably.
  - **Evidence / Reference:** Assumption A12; Technical Knowledge & Terms volume table.
  - **Impact if changed:** Must reduce Tier 1 to ≤3 days to fit within 500 MB, significantly limiting recent-price history in Supabase.

---

## Open Questions & Next Actions

1. **OQ-001 — Anomaly threshold canonical value**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm whether the anomaly threshold is 25% (per Goal item 5) or 30% (per Constraints section). Analysis defaults to 25%.

2. **OQ-002 — Documentation deliverable format for item 6**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm: is "product user guide and technical documentation" satisfied by (a) `README.md` in project root + populated AIB product-doc stubs (recommended default), or (b) a separate richer `docs/` folder, or (c) something else?

3. **OQ-003 — Migration script invocation model**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm: should `src/migrate_supabase.py` be a one-time initial load script only, or must it support incremental daily updates to Supabase? Default assumption: one-time.

4. **OQ-004 — Supabase granularity requirement for last-week data**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm: for Tier 1 (last 7 days) in Supabase, is product-level daily aggregation acceptable (prices averaged across trade objects/cities per product per day), or must per-store (trade-object level) prices be preserved? Default assumption: product-level aggregation is acceptable.

5. **OQ-005 — New dependencies approval (psycopg2-binary)**
   - Owner: User
   - Due: Before implementation
   - Resolution path: User to confirm that adding `psycopg2-binary` (and optionally `python-dotenv`) to `requirements.txt` is approved. If `supabase-py` is preferred instead, confirm that trade-offs (slower migration, API rate limits) are acceptable.
