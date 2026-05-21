# Analysis - Iteration 01

## Executive Summary

- **Request ID:** R-20260408-0113

- **Request Title:** Extract

- **Iteration ID:** 01

- **High-level purpose:** Build a Python data pipeline that (a) downloads daily ZIP price-data files from the Bulgarian open-data portal kolkostruva.bg/opendata, (b) extracts and validates each company's CSV file, (c) loads records into a JSON-based star-schema data store (dimensions + daily fact files), (d) maintains nomenclature dimensions as slowly-changing dimensions (SCD Type 2), and (e) flags anomalous or malformed company files by comparing them with the same company's historical data.

- **Context:** The project already has `extract.py` — a script that scrapes and downloads ZIP files into `data/raw/`. As of 2026-04-07, 52 daily ZIPs (2026-02-15 to 2026-04-07) are present. No database exists yet; all persistent state is in JSON files.

- **Earlier iterations:** None. This is the first iteration.

- **Key conflicts to resolve:** The request mentions a `src/` script that must download AND populate the schema, while `extract.py` already covers downloading. Scope of the new script must be clarified (replace vs. extend `extract.py`).

---

## Scope Interpretation

- **In scope — explicit:**

  - Download daily ZIP files from https://kolkostruva.bg/opendata that are not yet in `data/raw/`.

  - Explore and document format of files inside ZIPs.

  - Propose and implement a maximally normalized, space-efficient star-schema stored as JSON files.

  - Create a Python script in `src/` that downloads new ZIPs and populates the JSON schema.

  - Auto-maintain nomenclature dimensions (companies, cities, products, categories, trade objects) as slowly-changing dimensions; add new values automatically.

  - Implement anomaly / wrong-file detection by comparing a company's daily file with its historical submissions.

- **Out of scope — explicit:**

  - None stated in request.

- **Out of scope — implicit:**

  - Production deployment infrastructure (scheduling, containerisation, CI/CD).

  - A relational database backend (explicitly excluded: "I don't have a relational database yet").

  - Any UI/web API or dashboarding layer (no mention in request).

  - Historical backfill of ZIPs already present at `data/raw/` is ambiguous — assumed in scope so the first run is useful (see Assumption A3).

- **Implicitly in scope:**

  - Logging of download and ETL operations. (implicit rule - AIB framework)

  - Update of `CMP-01` (script catalog), `DATA-01` (source catalog), `DATA-02` (data models), `DATA-07` (data quality rules) product-doc stubs. (implicit rule - AIB framework)

---

## Domain Knowledge Essentials

- **kolkostruva.bg / "Колко ни струва":** Bulgarian consumer-price open-data portal. The site publishes daily ZIP archives of retail prices submitted (by law) by Bulgarian retailers. URL: https://kolkostruva.bg/opendata.

- **EKATTE (ЕКАТТЕ):** The Bulgarian national statistical classification code for populated places (Единен класификатор на административно-териториалните и териториалните единици). Each locality has a unique 5-digit numeric code. Used as the city key in the source data.

- **EIK / UIC (ЕИК — Единен идентификационен код):** Bulgaria's unique business identifier (analogous to company ID / tax number). Forms part of each CSV filename and uniquely identifies a legal entity. A legal entity may operate multiple trade objects.

- **Търговски обект (Trade Object):** A physical retail point-of-sale premise. One company (UIC) may submit prices for multiple trade objects in its CSV file.

- **Цена на дребно / Цена в промоция:** Retail (shelf) price and promotional price respectively. Promotional price is present only during active promotions; the column is empty otherwise.

- **Star schema:** A dimensional data model with a central fact table referencing multiple denormalized dimension tables. Chosen here because it simplifies analytical queries (aggregation by date/company/category) while minimizing duplication.

- **SCD Type 2 (Slowly Changing Dimension):** A dimension management technique that keeps full history: when a dimension attribute changes, a new row is added (along with `valid_from`, `valid_to`, `is_current` flags) and the old row is closed. This preserves historical context without losing prior states.

- **Data quality / "wrong file":** Files that are structurally malformed (wrong column count, encoding anomalies such as double-quoted values) or statistically anomalous (row count deviates significantly from historical baseline for the same company).

- **Price categories in data:** Categories 1–85 are food and non-food retail consumer goods; categories 86–101 are pharmaceutical/OTC medicinal products. All 101 categories are defined in `data/nomenclatures/product-categories.json`.

- **Affected personas:** Data analyst / researcher who queries prices; automated reporting tools that read JSON data files; developer who maintains the pipeline.

---

## Technical Knowledge & Terms

- **Python 3 / pathlib / zipfile / csv:** Core libraries used in `extract.py`; will be used in the new `src/` script.

- **UTF-8 BOM (utf-8-sig):** Encoding observed in all source CSV files. Must be handled explicitly during parsing; Python's `csv.reader` with `utf-8-sig` decoding strips the BOM automatically.

- **Double-quoted CSV anomaly:** A CSV formatting defect present in at least one company's files (e.g., `ОГАФАРМ (ЕВАРОС ЕООД)`). The entire field value is wrapped in a second layer of quotes, causing the raw token to appear as `"" "86""` instead of `"86"`. After stripping outer whitespace and extra quotes, the underlying value is still valid. This affects CSV parsing but not data integrity once handled.

- **Star schema — JSON implementation:** Without a SQL engine, the schema is realized as:
  - Dimension JSON files (one per dimension entity) containing arrays of records with surrogate keys.
  - Fact JSON files partitioned by date (`data/schema/facts/YYYY-MM-DD.json`) to bound memory use and support incremental loads.

- **SCD Type 2 implementation in JSON:** Each dimension record carries `valid_from` (ISO date string), `valid_to` (ISO date string or `null` for current), and `is_current` (boolean). On upsert: if the natural key is new, insert; if the natural key exists but a tracked attribute changed, close the old record and insert a new one.

- **Surrogate key (SK):** An internal integer key assigned by the pipeline, independent of the source keys (EKATTE code, UIC, product code). Ensures dimension stability even if source keys are corrected.

- **`requests` + `BeautifulSoup4`:** Already in `requirements.txt`. Used by `extract.py` for scraping and downloading.

- **Anomaly detection strategy:** Statistical z-score or percentage-deviation on row count per company per day vs. rolling N-day baseline (N = 7 or 14). Also rule-based: wrong column count, unparseable numeric price field, city/category ID not resolvable to a known dimension value.

- **Data volume (observed):** ~208 companies/day, ~1.28M rows/day per ZIP, ZIP size ~20 MB. Projected total across 52 days: ~66M rows, ~1 GB raw data. Daily fact JSON files will be smaller than the ZIPs due to integer surrogate keys replacing long strings.

- **`data/raw/` layout:** ZIPs land as `YYYY-MM-DD.zip`. Two dates (2026-02-15, 2026-02-16) are also extracted into same-named subfolders. The new script must handle both ZIP-only and pre-extracted formats.

- **`logs/` directory:** Present; must be used for pipeline logging per observability convention.

---

## Assumptions

- Assumption A1: The new `src/` script supersedes and replaces the functionality of `extract.py` (i.e., it both downloads ZIPs and populates the star schema in one command). `extract.py` may be kept as-is but will not be the primary entry point after delivery.
  - Rationale: The request says "create a Python script in `src/` which downloads the data files...and then populates the new schema", implying an integrated script.
  - Risk if false: If the user wants the download step separated from ETL, architecture must be split; increases complexity.
  - Falsification method: Ask user whether a single integrated script is acceptable.

- Assumption A2: Historical ZIPs already in `data/raw/` should be processed (backfill) on the first run, not skipped.
  - Rationale: 52 ZIPs already downloaded; skipping them would leave the schema empty and anomaly detection without a baseline.
  - Risk if false: Backfilling 52 ZIPs takes significant runtime (~66M rows); user may not want it on first run.
  - Falsification method: Ask user whether backfilling is in scope.

- Assumption A3: SCD Type 2 is required only for the company dimension and product dimension; city and category dimensions are stable enough for SCD Type 1 (overwrite) unless the request states otherwise.
  - Rationale: EKATTE city codes are official government codes and do not change. Category IDs and names are defined by law; additions are infrequent.
  - Risk if false: City/category renames would be lost historically if Type 1 is used.
  - Falsification method: Verify with user whether historical tracking of city or category name changes matters.

- Assumption A4: A "product" dimension is scoped to (company_uic, product_code) — i.e., product codes are company-specific, not global.
  - Rationale: The request states "Код на продукта — company specific product code". Two companies can use the same code for different products.
  - Risk if false: If product codes are global, dimension design changes.
  - Falsification method: Inspect whether the same product_code + product_name appear identically across multiple companies in the data. Already confirmed in data sample that codes are company-specific.

- Assumption A5: Anomaly detection need only produce a machine-readable report file per day (e.g., `data/quality/YYYY-MM-DD-anomalies.json`). No real-time alerts or email notifications are required.
  - Rationale: The project operates in a single-user Python script context; no messaging infrastructure exists.
  - Risk if false: User expects actionable notifications; adds integration work.
  - Falsification method: Ask user what "mechanism to detect wrong files" means in terms of output.

- Assumption A6: The script should process ZIPs in ascending date order to ensure the SCD dimension timeline is physically correct.
  - Rationale: SCD Type 2 requires `valid_from` dates to be monotonically assigned; processing out of order would corrupt the timeline.
  - Risk if false: No impact if all ZIPs are processed in a single run from scratch, but idempotency requires consistent ordering.
  - Falsification method: Technical constraint — no user input needed.

- Assumption A7: All price values are in Bulgarian Lev (BGN). No currency conversion is required.
  - Rationale: The source site is Bulgarian; no multi-currency evidence in data.
  - Risk if false: Negligible for this use case.
  - Falsification method: Inspect site documentation (already confirmed from data — prices are decimal numbers, not currency-coded).

- Assumption A8: The anomaly detection threshold for row-count deviation is 30% relative change vs. 7-day rolling mean for the same company. This is a configurable default.
  - Rationale: The two days sampled showed identical row counts for the three checked companies; a 30% threshold balances sensitivity and false-positive rate.
  - Risk if false: Too strict = too many false positives; too lenient = real errors missed.
  - Falsification method: Configurable parameter in script; user can tune.

---

## Impact Assessment

### 6.1 Affected Components / Areas

- `extract.py` — existing download script; may be integrated or superseded.

- `data/raw/` — source landing zone for ZIPs; read-only by the new pipeline.

- `data/schema/` (new) — persisted star schema JSON files (dimensions + daily facts).

- `data/quality/` (new) — anomaly/quality reports per day.

- `data/nomenclatures/` — read by dimension seeding; `cities-ekatte-nomenclature.json`, `product-categories.json`.

- `src/` (new) — main pipeline script.

- `requirements.txt` — may need additional entries (e.g., `pandas` for z-score if chosen; otherwise pure stdlib suffices).

- `logs/` — pipeline log output.

### 6.2 Change Type and Dependencies

| Component | Change Type | Dependencies |
|---|---|---|
| `src/` pipeline script | Add | `data/raw/`, `data/nomenclatures/`, `data/schema/`, `data/quality/` |
| `data/schema/` directory | Add | None |
| `data/quality/` directory | Add | `data/schema/` (dimension lookup needed for quality reports) |
| `extract.py` | Modify or supersede (TBD) | None |
| `requirements.txt` | Modify if pandas added | PyPI |
| `data/nomenclatures/` files | Read-only (seeding source) | None |

### 6.3 Domain Impacts

- DOMAIN (ARCH): New components `src/` pipeline, `data/schema/`, `data/quality/` must be documented in ARCH-01 and ARCH-07.
  - Relevant: ARCH-01, ARCH-07

- DOMAIN (CMP): New script `src/pipeline.py` (or similar) must be registered in CMP-01 script catalog.
  - Relevant: CMP-01

- DOMAIN (DATA): Core impact. DATA-01 must document kolkostruva.bg as data source. DATA-02 must define the star schema (logical and physical model). DATA-03 must define lineage from raw ZIP to fact JSON. DATA-04 must document JSON partitioned storage pattern. DATA-07 must document quality rules and anomaly thresholds.
  - Relevant: DATA-01, DATA-02, DATA-03, DATA-04, DATA-07

- DOMAIN (KNW): KNW-01 domain glossary must define EKATTE, EIK/UIC, SCD Type 2, trade object, star schema for domain users.
  - Relevant: KNW-01

- DOMAIN (OBS): Logging must be added to the pipeline per OBS-01. No alert infrastructure exists yet.
  - Relevant: OBS-01

- DOMAIN (SEC): No impact on access control, secrets, or authentication. The data source is public open data. No credentials required.
  - Relevant: SEC-01 (No impact detected)

- DOMAIN (RQT): RQT-01 product charter must be updated to include the price data pipeline as a core product component. RQT-02 requirements document must include the ETL and schema requirements.
  - Relevant: RQT-01, RQT-02

- DOMAIN (DEV): No impact detected (no separate development environment conventions defined yet).

- DOMAIN (DSR): No impact detected.

- DOMAIN (FNL): No impact detected.

- DOMAIN (OPR): No impact detected (no production operations environment exists).

### 6.4 Constraints

- No relational database: all persistent storage must be JSON files.

- Python only: the runtime language is Python 3.

- Dependencies limited to what is installable via pip; no compiled C extensions are required.

- Source data is public and unauthenticated; no credential management is needed for download.

- The system must handle ~1.28M rows per day efficiently without loading all data into memory at once (streaming / incremental load required to avoid OOM on large backfills).

- The `data/raw/` directory layout must remain unchanged (backward compatible with existing `extract.py`).

### 6.5 Required Documentation Updates

| Ref ID | Document | Required update? | Reason |
|---|---|---|---|
| REF-0001 | ARCH-01 - High-level architecture | YES | New pipeline component and storage layer introduced |
| REF-0006 | ARCH-07 - Resource catalog | YES | New directories and script resources |
| REF-0007 | CMP-01 - Notebook/script catalog | YES | New `src/pipeline.py` (or equivalent) must be catalogued |
| REF-0009 | DATA-01 - Source data catalog | YES | kolkostruva.bg ZIP source must be described |
| REF-0010 | DATA-02 - Data models | YES | Star schema logical and physical model |
| REF-0011 | DATA-03 - Data lineage | YES | ZIP → CSV → dimension/fact lineage |
| REF-0012 | DATA-04 - Data storage strategy | YES | JSON partitioned fact storage pattern |
| REF-0015 | DATA-07 - Data quality rules | YES | Anomaly detection rules and thresholds |
| REF-0018 | KNW-01 - Domain glossary | YES | EKATTE, EIK/UIC, SCD, star schema |
| REF-0022 | RQT-01 - Product charter | YES | Pipeline added as core component |
| REF-0023 | RQT-02 - Requirements document | YES | ETL and schema requirements formalized |
| REF-0021 | OBS-01 - Logging | YES | Pipeline logging strategy |

### 6.6 Decision Points

**Decision Point D1: Integration vs. separation of download and ETL**

- Option 1: Single `src/pipeline.py` that downloads new ZIPs AND processes them (Assumption A1).
  - Implication: Simpler single entry point; `extract.py` becomes redundant.
  - Recommended: YES — reduces cognitive overhead.

- Option 2: Keep `extract.py` for download, create separate `src/etl.py` for processing.
  - Implication: More modular; allows independent scheduling; `extract.py` continues to work standalone.
  - Recommended: Alternative if user prefers separation.

**Decision Point D2: Backfill of existing ZIPs on first run**

- Option A: Process all ZIPs in `data/raw/` on first run (backfill).
  - Implication: Builds full historical schema (~66M rows, significant first-run time).

- Option B: Process only ZIPs downloaded after the script is deployed (forward-only).
  - Implication: Schema starts empty; anomaly detection has no baseline initially.

- Recommendation: Option A (backfill) with optional `--no-backfill` flag.

**Decision Point D3: SCD scope for city and category dimensions**

- Option A: SCD Type 1 (overwrite) for cities and categories.
  - Implication: Name changes in official nomenclature are not historically tracked.

- Option B: SCD Type 2 for all dimensions uniformly.
  - Implication: Adds complexity but ensures full historical correctness.

- Recommendation: SCD Type 2 for all dimensions for maximum correctness.

**Decision Point D4: Fact file partitioning**

- Option A: One JSON fact file per day (`data/schema/facts/YYYY-MM-DD.json`).
  - Implication: Simple incremental append; bounded file size (~1GB total for 52 days at current volume).

- Option B: Single JSONL file (`data/schema/facts.jsonl`) appended per run.
  - Implication: Simpler write; harder to reprocess a single day if needed.

- Recommendation: Option A (per-day files) — supports idempotent per-day reprocessing and avoids single-file growth issues.

---

## Research Plan and Findings

**Methodology:**

1. Internal-first: read `request.md`, `iterations.md`, all product-doc stubs, `references.md`, analysis and request conventions.

2. Code scan: read `extract.py`, `requirements.txt`.

3. Data scan: inspected ZIP file structure, CSV internal format, encoding, column schemas, nomenclature JSON files.

4. Volume and quality analysis: counted rows per ZIP (~1.28M), companies per ZIP (~208), total ZIPs (52), identified double-quoting anomaly in ОГАФАРМ file, confirmed all city codes and category IDs resolve correctly after normalization.

5. Cross-day comparison: compared company file presence and row counts between 2026-02-15 and 2026-02-16. Row counts are stable (3 sampled companies: 0 diff). 2 companies missing from day1, 8 companies new in day2.

**Evidence summary:**

| Evidence | Implication |
|---|---|
| CSV encoding = utf-8-sig | Must use `utf-8-sig` when decoding; BOM stripping is automatic |
| 7 fixed columns per CSV, always quoted | Standard `csv.reader` works; handle double-quote anomaly |
| Double-quoting anomaly in ОГАФАРМ file (pharmacy chain) | Anomaly detection rule needed: detect and log malformed rows but still extract data after normalization |
| All 101 category IDs from `product-categories.json` cover all observed IDs in data | Nomenclature is complete; no new categories need to be seeded on first run beyond known 101 |
| City EKATTE codes in data all match `cities-ekatte-nomenclature.json` | City dimension can be directly seeded from nomenclature file |
| Categories 86–101 are pharmaceutical categories | Pharmacy companies (АПТЕКА, АПТЕКИ) use these; trade-object dimension must be company-scoped |
| 52 ZIPs, ~20 MB each → ~1 GB raw | Requires streaming/chunked processing to avoid OOM during backfill |
| 2 companies absent on day1, 8 new on day2 | Company dimension may grow over time; SCD correctly handles new companies |
| Row counts stable across days for 3 sampled companies | Stable baseline exists; 30% threshold anomaly detection is feasible |
| `requirements.txt` includes `fastapi`, `uvicorn` | A web API may be planned; pipeline script should remain independently runnable without starting a server |

**Gaps and unknowns:**

1. The definition of "wrong file" from the user's perspective — is it structural (CSV format), volumetric (row count), or semantic (price outlier)?

2. Anomaly thresholds — 30% row-count deviation is assumed; actual business tolerance unknown.

3. Whether backfill of all 52 existing ZIPs is expected on first run.

4. Whether `extract.py` should be preserved alongside the new `src/` script or deprecated.

5. No explicit schema for the `data/schema/` output is validated by the user yet.

**Files read:**

- `.aib_brain/prompts/aib-analysis.md` — execution trigger; defines output rules.
- `.aib_memory/requests/R-20260408-0113-extract/request.md` — active request content.
- `.aib_memory/requests/R-20260408-0113-extract/iterations.md` — active iteration = 01.
- `.aib_memory/references.md` — full list of 27 product-doc refs.
- `.aib_brain/conventions/analysis-convention.md` — mandatory output structure.
- `.aib_brain/conventions/request-convention.md` — format for rewritten request.
- `.aib_brain/Concepts.md` — AIB framework concepts and action contract.
- `.aib_memory/requests_register.md` — request state = Active.
- `.aib_memory/docs/04 Technology/Architecture/ARCH-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Architecture/ARCH-07.md` [SKIPPED — domain out of scope for stub content]
- `.aib_memory/docs/04 Technology/Compute/CMP-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Sources/DATA-01.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Models/DATA-02.md` — stub only.
- `.aib_memory/docs/04 Technology/Data Workspace/DATA-04.md` — stub only.
- `.aib_memory/docs/02 Domain/Terms and Concepts/KNW-01.md` — stub only.
- `.aib_memory/docs/01 Product Management/Product Charter/RQT-01.md` — stub only.
- `.aib_memory/docs/03 Requirements/RQT-02.md` [SKIPPED — assumed stub only]
- `extract.py` — download script; read in full.
- `requirements.txt` — dependencies; read in full.
- `data/nomenclatures/product-categories.json` — 101 categories confirmed; all IDs 1–101 present.
- `data/nomenclatures/cities-ekatte-nomenclature.json` — EKATTE code → city name map; confirmed all observed city codes resolve.
- `data/raw/2026-02-15/ABC MARKET (ЦБА-ДОБРИЧ ООД)_124634359.csv` — sample CSV; confirmed columns, encoding, quote handling.
- `data/raw/` directory listing — 52 ZIPs + 2 extracted folders confirmed.

---

## Rewrite Proposal of the Request

### Goal

Build a Python 3 ETL pipeline (located in `src/`) for the "Колко ни струва" Bulgarian open-data price portal. The pipeline must:

1. Download daily ZIP files from `https://kolkostruva.bg/opendata` that are not yet present in `data/raw/`, storing them as `YYYY-MM-DD.zip`.

2. Extract and parse each company's CSV file from each unprocessed ZIP. Handle UTF-8 BOM encoding and double-quoted CSV field anomalies.

3. Load all records into a JSON-based star schema stored under `data/schema/`, consisting of:
   - Five dimension files with SCD Type 2 (surrogate key, natural key, tracked attributes, `valid_from`, `valid_to`, `is_current`):
     - `data/schema/dim_company.json` — keyed on UIC; tracks company name and legal name.
     - `data/schema/dim_trade_object.json` — keyed on (UIC, trade-object-name); tracks store name.
     - `data/schema/dim_product.json` — keyed on (UIC, product-code); tracks product name.
     - `data/schema/dim_city.json` — keyed on EKATTE code; seeded from `data/nomenclatures/cities-ekatte-nomenclature.json`.
     - `data/schema/dim_category.json` — keyed on category ID; seeded from `data/nomenclatures/product-categories.json`.
   - Date-partitioned daily fact files:
     - `data/schema/facts/YYYY-MM-DD.json` — one file per date; each record contains (date, company_sk, trade_object_sk, product_sk, city_sk, category_sk, retail_price, promo_price).

4. Execute a daily anomaly-detection check per company file before loading and produce a report at `data/quality/YYYY-MM-DD-report.json`. Anomaly rules:
   - Structural: wrong column count (≠ 7), unparseable retail price, unresolvable city/category ID after normalization.
   - Volumetric: row count deviates by more than 30% (configurable) from the 7-day rolling mean for the same company.
   - Mark files as `OK`, `WARNING` (loaded despite anomaly), or `REJECTED` (not loaded) with reason.

5. Log all actions (downloads, loads, anomalies) to `logs/` using the Python `logging` module.

### Background

The project collects daily retail prices from the Bulgarian government's open-data portal (kolkostruva.bg). An existing `extract.py` scrapes and downloads the ZIP files. No further processing exists. The goal is to build the analytical data store that enables price trend analysis.

### Scope

- `src/pipeline.py` (or similar) — single-script entry point integrating download + ETL + quality checks.
- `data/schema/` — output directory for star-schema JSON files.
- `data/quality/` — output directory for anomaly reports.
- `data/nomenclatures/` — read-only input; used to seed city and category dimensions.
- `data/raw/` — read-only input; ZIPs are read from here after download.
- `requirements.txt` — may be extended if additional packages are needed.
- Documentation updates: `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-07`, `CMP-01`, `KNW-01`.

### Out of scope

- Relational database backend.
- Web API / dashboarding / front-end.
- Real-time alerting or email notifications.
- Data deletion, archiving, or retention policy.
- Containerisation or CI/CD pipeline.
- Changes to the `data/raw/` directory layout.

### Constraints

- Python 3 only; no compiled native extensions.
- No relational DB; all persistence in JSON files.
- Must process one ZIP at a time to bound memory usage.
- Source is public, unauthenticated; no credential management needed.
- Must be idempotent: running twice on the same ZIP must produce the same result in `data/schema/`.

### Success criteria

- SC1: Running `python src/pipeline.py` with all 52 existing ZIPs processes without crash; all 52 daily fact files created under `data/schema/facts/`.
- SC2: Dimension files contain correct SCD Type 2 records for all companies, trade objects, products, cities, and categories observed in raw data; no referential gaps in fact files.
- SC3: For each ZIP processed, a report file exists at `data/quality/YYYY-MM-DD-report.json`; the ОГАФАРМ file from 2026-02-15 is flagged as `WARNING` with reason "double-quoted CSV fields".
- SC4: Running the script a second time produces no new fact or dimension records when no new ZIPs exist (idempotency).
- SC5: A new ZIP downloaded from the site is processed within the same `pipeline.py` run that downloads it; its fact file appears in `data/schema/facts/` after the run.
- SC6: Documented anomaly threshold (30% row count deviation) is configurable via a constant or CLI argument.

---

## Solution Options

**Option A: Single integrated `src/pipeline.py` with streaming per-ZIP processing**

- Overview: One Python script; three sequential phases: (1) scrape + download new ZIPs, (2) for each unprocessed ZIP, stream-parse CSVs and upsert dimensions, write daily fact JSON file, (3) write anomaly report. Dimensions loaded from JSON at start; flushed back to JSON on success. Uses only stdlib + `requests` + `beautifulsoup4`.

- Benefits: Single entry point; no additional dependencies; simple to schedule (cron); consistent with existing `extract.py` style.

- Trade-offs: In-memory dimension dictionaries required during processing (~tens of thousands of records; manageable); fact file for one day written as a list then dumped at end of day (peak memory = one day's facts ≈ 100–200 MB dict before JSON serialization).

- Constraints: Must stay within available RAM on the user's machine for one-day processing window.

- Risks: Large JSON fact files (~1M records) may be slow to load/query later; fact files will be 100–300 MB each uncompressed.

- Expected effort: Medium (2–3 implementation steps).

- Acceptance test ideas: Process 2026-02-15.zip; verify fact file row count matches CSV total; verify ОГАФАРМ appears in quality report.

**Option B: Separated modules with `pandas` for ETL**

- Overview: `src/download.py` (wraps `extract.py` logic) + `src/etl.py` (uses `pandas` DataFrames). Pandas enables vectorized CSV parsing, group-by aggregations for anomaly detection, and efficient join operations for dimension lookups.

- Benefits: Faster development; pandas' `read_csv` handles encoding and quoting edge cases robustly; `groupby` simplifies row-count baseline computation.

- Trade-offs: Adds `pandas` dependency (~10 MB install); loading a full day's CSVs into a DataFrame peaks at ~500 MB RAM; pandas is already an indirect dependency via many data toolchains but adds weight.

- Constraints: `pandas` not currently in `requirements.txt`; must be added.

- Risks: Dependency creep; pandas version compatibility; higher memory footprint.

- Expected effort: Medium-Low (pandas reduces boilerplate for CSV handling and anomaly stats).

- Acceptance test ideas: Same as Option A plus: confirm `read_csv` correctly handles ОГАФАРМ double-quoting after parser configuration.

**Recommendation:** Option A — stdlib + requests + beautifulsoup4 only. The existing `requirements.txt` already has `requests` and `beautifulsoup4`; no new runtime dependency is introduced. The memory profile is acceptable (one day at a time). Option B becomes relevant if query performance on the JSON facts becomes a bottleneck, at which point migration to SQLite or DuckDB is preferable.

---

## Affected Documentation

| ref_id | document_title | path | reason_for_inclusion |
|---|---|---|---|
| REF-0001 | ARCH-01 - High-level architecture | .aib_memory/docs/04 Technology/Architecture/ARCH-01.md | New pipeline + storage layer changes system architecture |
| REF-0006 | ARCH-07 - Resource catalog | .aib_memory/docs/04 Technology/Inventory/ARCH-07.md | New `src/`, `data/schema/`, `data/quality/` resources |
| REF-0007 | CMP-01 - Notebook/script catalog | .aib_memory/docs/04 Technology/Compute/CMP-01.md | `src/pipeline.py` must be registered |
| REF-0009 | DATA-01 - Source data catalog | .aib_memory/docs/04 Technology/Data Sources/DATA-01.md | kolkostruva.bg ZIP source description |
| REF-0010 | DATA-02 - Data models | .aib_memory/docs/04 Technology/Data Models/DATA-02.md | Star schema logical and physical model |
| REF-0011 | DATA-03 - Data lineage | .aib_memory/docs/04 Technology/Data Workspace/DATA-03.md | ZIP → CSV → dimension + fact lineage |
| REF-0012 | DATA-04 - Data storage strategy | .aib_memory/docs/04 Technology/Data Workspace/DATA-04.md | JSON partitioned storage pattern |
| REF-0015 | DATA-07 - Data quality rules | .aib_memory/docs/04 Technology/Data Workspace/DATA-07.md | Anomaly detection rules and thresholds |
| REF-0018 | KNW-01 - Domain glossary | .aib_memory/docs/02 Domain/Terms and Concepts/KNW-01.md | EKATTE, EIK/UIC, SCD, star schema, trade object |
| REF-0021 | OBS-01 - Logging | .aib_memory/docs/04 Technology/Observability/OBS-01.md | Pipeline logging strategy |
| REF-0022 | RQT-01 - Product charter | .aib_memory/docs/01 Product Management/Product Charter/RQT-01.md | Pipeline as core product component |
| REF-0023 | RQT-02 - Requirements document | .aib_memory/docs/03 Requirements/RQT-02.md | ETL and schema requirements |

---

## Operational & Documentation Implications

- A new daily run of `python src/pipeline.py` must be scheduled (manually or via cron) to keep data current.

- Logs must be written to `logs/pipeline-YYYY-MM-DD.log` or appended to a rolling log file in `logs/`.

- Anomaly reports at `data/quality/YYYY-MM-DD-report.json` are the primary observability mechanism; no other monitoring infrastructure is required at this stage.

- If a future relational DB is introduced, the star-schema JSON files provide a direct migration path: dimension JSON → dimension tables; fact JSON files → fact table bulk inserts.

- Product documentation stubs `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-07`, `CMP-01`, `KNW-01` must be populated as part of the implementation.

- The `OBS-01` logging document must be updated to reflect the pipeline's logging strategy.

---

## Risks

- Risk R1: Large single-day fact JSON files (~200–300 MB uncompressed) make later analytical queries slow.
  - Probability: Medium
  - Impact: Medium
  - Mitigation: Partition fact files by date (already proposed). If query performance is unacceptable, migrate to SQLite or DuckDB as a second iteration.
  - Owner (role): Developer

- Risk R2: Backfill of 52 existing ZIPs crashes due to OOM or takes unacceptably long.
  - Probability: Low–Medium (depends on machine RAM; ~200 MB peak per day is expected)
  - Impact: High
  - Mitigation: Stream-process one ZIP at a time and flush dimension/fact files to disk before processing the next. Provide `--date` argument to process a single day.
  - Owner (role): Developer
  - Contingency: If OOM occurs, reduce fact file buffering by streaming fact records directly to a JSONL file and converting to JSON array on close.

- Risk R3: kolkostruva.bg website structure changes, breaking scraping.
  - Probability: Medium (external dependency)
  - Impact: High (no new data ingested until fixed)
  - Mitigation: Anomaly detection can flag missing daily ZIPs. Scraping logic is isolated in the download phase; easy to update.
  - Owner (role): Developer

- Risk R4: SCD Type 2 implementation produces duplicate or incorrect dimension records when the same device runs the pipeline twice due to a bug.
  - Probability: Low
  - Impact: High (corrupt dimension breaks all fact joins)
  - Mitigation: Idempotency test is required (SC4). Implement a lock on `is_current = True` uniqueness per natural key before writing.
  - Owner (role): Developer
  - Contingency: Provide a `--rebuild-dimensions` flag that truncates and re-seeds dimensions from scratch using all available source data.

- Risk R5: Some source CSV files have encoding other than UTF-8 BOM that is not yet detected (e.g., Windows-1251).
  - Probability: Low (all sampled files are utf-8-sig)
  - Impact: Medium (corrupt text data if wrong encoding used)
  - Mitigation: Add a fallback encoding chain: try `utf-8-sig` → `windows-1251` → `latin-1`; log a warning if fallback was required.
  - Owner (role): Developer

---

## Disambiguation Questionnaire

This section answers canonical disambiguation questions based on available evidence.

- Question: What is the primary deployment target (OS / Python runtime / constraints)?
  - Chosen Answer / Value: Linux, Python 3 (version assumed ≥ 3.9 based on pathlib/zipfile usage in `extract.py`); no containerisation specified.
  - Rationale: User workspace is Linux; `extract.py` uses pathlib idioms consistent with Python 3.9+.
  - Evidence / Reference: workspace OS metadata; `extract.py` code review.
  - Impact if changed: Minimal — stdlib choices remain the same across Python 3.8+.

- Question: Should the new script replace or coexist with `extract.py`?
  - Chosen Answer / Value: Assumed coexist initially; `extract.py` kept, new `src/pipeline.py` supersedes it functionally (see Assumption A1, Decision Point D1).
  - Rationale: Safest backwards-compatible approach.
  - Evidence / Reference: Assumption A1.
  - Impact if changed: If user wants `extract.py` deleted, no functional impact, only file cleanup.

- Question: Is the 30% anomaly threshold acceptable?
  - Chosen Answer / Value: Assumed acceptable as a configurable default.
  - Rationale: Assumption A8; no user input yet.
  - Evidence / Reference: Assumption A8; data observation.
  - Impact if changed: Configurable constant; no architectural impact.

- Question: Is backfill of all existing ZIPs required?
  - Chosen Answer / Value: Assumed YES (Assumption A2).
  - Rationale: Without backfill the schema is empty and anomaly detection has no baseline.
  - Evidence / Reference: Assumption A2.
  - Impact if changed: If NO, the first run returns an empty schema; anomaly detection baseline is unavailable for ~7 days.

---

## Open Questions & Next Actions

1. **Q1 — "Wrong file" definition**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm: is a "wrong file" (a) structurally malformed only, (b) volumetrically anomalous only, (c) both, or (d) also semantically wrong (e.g., price outlier vs. historical values)?

2. **Q2 — Backfill confirmation**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm whether the pipeline should process all 52 existing ZIPs on first run or only forward-going downloads.

3. **Q3 — Download vs. ETL coupling**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm whether a single `src/pipeline.py` (download + ETL) is acceptable, or whether separate scripts are preferred.

4. **Q4 — Anomaly threshold**
   - Owner: User
   - Due: Before plan creation
   - Resolution path: User to confirm 30% row-count deviation as the default threshold, or provide a preferred value.

5. **Q5 — Fact file format: pure JSON array vs. JSONL**
   - Owner: Developer (internal)
   - Due: During plan creation
   - Resolution path: Default to one JSON array file per day. Switch to JSONL if fact file size exceeds 100 MB during implementation.

