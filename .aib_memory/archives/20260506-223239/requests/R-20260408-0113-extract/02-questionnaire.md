# Questionnaire — Iteration 02

Request: R-20260408-0113 — Extract

---

## 1. Business & Functional Questions

---

### QID-BF-001 — Anomaly Detection Threshold

**Intent:** Confirm the canonical anomaly-detection threshold value so the implementation uses the correct constant.

**Rationale:** The updated `request.md` contains a conflict: Goal item 5 states "more than 25% deviation" while the Constraints section retains the Iteration 01 draft value of "30% row-count deviation". The pipeline will encode one value as a named constant (`ANOMALY_THRESHOLD`). The wrong value produces either too many false-positive WARNING flags (stricter) or missed anomalies (looser). Clarification is required before coding starts.

**Impact Areas:** Requirements, Data, Observability

**Assumptions:**
- The 25% value in the Goal was intentional (not a typo); the 30% in Constraints is an Iteration 01 artefact that was not updated.
- Threshold applies equally to all three metrics: row count, unique product-code count, unique product-name count.

**Answer Type:** single-select

**Options:**
- [x] A) 25% — as stated in Goal item 5. (recommended)
- [ ] B) 30% — as stated in the Constraints section (Iteration 01 default).
- [ ] C) 20% — stricter; more false positives expected.
- [ ] D) 50% — more lenient; only severe anomalies flagged.
- [ ] Other — (describe below):

**Constraints & Guards:** The chosen value is encoded as a single float constant (e.g., `ANOMALY_THRESHOLD = 0.25`). Changing it later is a one-line edit with no architectural impact.

---

### QID-BF-002 — Documentation Deliverable Scope (Item 6)

**Intent:** Define what "product user guide and technical documentation" (Goal item 6) means as concrete deliverable files.

**Rationale:** Item 6 is intentionally broad. At minimum, two interpretations exist: (A) a `README.md` in the project root for operator/analyst users, plus populating the eight existing AIB product-doc stubs (DATA-01…OBS-01); (B) a richer standalone `docs/` folder with separate user guide and technical reference pages. The effort difference is significant: option A populates already-scaffolded files; option B requires creating a new docs folder with multiple additional files.

**Impact Areas:** Scope, Requirements, Timeline

**Assumptions:**
- The AIB product-doc stubs (DATA-01, DATA-02, DATA-03, DATA-04, DATA-07, CMP-01, KNW-01, OBS-01) are already the established technical documentation system for this project.
- No `README.md` or `docs/` folder currently exists in the workspace.

**Answer Type:** single-select

**Options:**
- [ ] A) README.md + AIB stubs — create `README.md` (user guide) and populate the eight stub AIB product-doc files with project-specific content. (recommended)
- [ ] B) README.md + AIB stubs + docs/ folder — option A plus a separate `docs/user-guide.md` and `docs/technical-reference.md` for a richer browseable documentation set.
- [x] C) README.md only — skip the AIB stubs; write only a thorough `README.md` covering both user and technical audiences.
- [ ] D) AIB stubs only — skip `README.md`; add content to each existing product-doc stub.
- [ ] Other — (describe below):

**Constraints & Guards:** If B) is selected, the `docs/` folder will also contain `docs/supabase-setup.md` (already required by item 7), so the folder already exists. Only the extra guide/reference files are additional scope.

---

### QID-BF-003 — Supabase Migration Script Invocation Model (Item 8)

**Intent:** Confirm whether `src/migrate_supabase.py` is a one-time initial load script or must support incremental daily updates.

**Rationale:** "Migration" typically implies a one-time transfer. If the pipeline runs daily and produces new fact files, the user may need Supabase data to stay current — which requires an incremental sync capability (watermark tracking, upsert-against-remote state). Adding incremental sync roughly doubles the migration script's scope.

**Impact Areas:** Scope, Architecture, Data, Timeline

**Assumptions:**
- One-time load is the default interpretation; no incremental sync infrastructure (scheduler, watermark store) currently exists.

**Answer Type:** single-select

**Options:**
- [ ] A) One-time initial load only — script is run once after local JSON data exists; Supabase is not updated again automatically. (recommended)
- [x] B) Incremental daily sync — script is also run daily alongside the pipeline; it pushes each new day's data to Supabase, removing data older than the retention window. Adds watermark + upsert logic.
- [ ] C) Manual on-demand — one-time design, but built so it can be safely re-run at any time to refresh the full Supabase dataset (full truncate + reload).
- [ ] Other — (describe below):

**Constraints & Guards:** If B) is selected, implementation effort for the migration script increases by ~1–2 days. Option C is a middle ground: idempotent full-reload with no incremental complexity.

---

## 2. Architecture & Technical Questions

---

### QID-AT-001 — Supabase Tier 1 Granularity (Item 8)

**Intent:** Decide whether the "last 7 days" data in Supabase (`fact_prices_daily`) must preserve per-store (trade-object) level prices or may be aggregated to the product level across all stores of a company.

**Rationale:** At full granularity (date × company × trade-object × product × city), 7 days of facts = ~9M rows ≈ >500 MB in PostgreSQL. At product level (date × company × product, aggregating away trade-object and city), 7 days ≈ 1.75M rows ≈ 160 MB — comfortably within budget. The trade-off: product-level aggregation enables "what does company X charge for product Y on date D?" queries but loses "which specific store charges what price?" queries. If per-store queries are needed, the period of full-granularity data in Supabase must be reduced to ~3 days.

**Impact Areas:** Architecture, Data, Requirements

**Assumptions:**
- Supabase is intended for analytical price queries (trends, comparisons), not operational store-level reporting.
- The full per-store granularity is always available in the local `data/schema/facts/` files.

**Answer Type:** single-select

**Options:**
- [ ] A) Product-level aggregation — Tier 1: (date, company, product, category, avg_retail_price, min_promo_price); trade-object and city dimensions omitted from Supabase. Last 7 days fits ~160 MB. (recommended)
- [x] B) Trade-object level — Tier 1 keeps (date, company, trade_object, product, category, retail_price, promo_price) for full per-store detail; period limited to last 3 days to fit within 500 MB.
- [ ] C) Company-level aggregation — Tier 1: (date, company, category, avg_retail_price, avg_promo_price, product_count); most compact; loses product identity entirely.
- [ ] Other — (describe below):

**Constraints & Guards:** If B) is selected, the Tier 1 `RECENT_DAYS` constant must be set to 3, not 7. Success criterion SC9 must be updated accordingly.

---

### QID-AT-002 — Python Library Approval for Supabase Migration (Item 8)

**Intent:** Approve the addition of `psycopg2-binary` to `requirements.txt` for the migration script, or confirm a preferred alternative.

**Rationale:** The migration script must load up to ~1.75M rows into Supabase. Direct PostgreSQL access via `psycopg2-binary` (using `COPY` or `execute_values`) is orders of magnitude faster than the `supabase-py` REST client (which is limited to ~1,000 rows per API call and is subject to rate limits). However, `psycopg2-binary` requires the Supabase project's direct database connection string (port 5432 or 6543 via the connection pooler), which must be configured in `.env`. The Iteration 01 constraint said "no compiled native extensions"; `psycopg2-binary` bundles its own `libpq` but is still a binary extension.

**Impact Areas:** Architecture, Data, Security

**Assumptions:**
- Supabase port 5432 (or 6543 via pooler) is accessible from the user's development machine.
- `DATABASE_URL` (PostgreSQL connection string) will be read from the `.env` file and never hardcoded.

**Answer Type:** single-select

**Options:**
- [x] A) psycopg2-binary — direct PostgreSQL connection; fastest bulk load; add to `requirements.txt`. Requires `DATABASE_URL` in `.env`. (recommended)
- [ ] B) supabase-py (REST client) — uses Supabase API key + project URL; no direct DB connection; slower (~minutes for full load); requires `SUPABASE_URL` + `SUPABASE_KEY` in `.env` instead of `DATABASE_URL`.
- [ ] C) psycopg2-binary + python-dotenv — option A plus `python-dotenv` for `.env` file loading; removes need to manually export `DATABASE_URL` before running the script.
- [ ] Other — (describe below):

**Constraints & Guards:** If the user's network blocks port 5432/6543 to Supabase, option A will fail. If in doubt, test with `psql $DATABASE_URL` before committing. Adding `python-dotenv` (option C) is a small convenience; if already present in the environment, it is redundant.

---

## 3. Appendix — Answer Encoding Rules

- Unchecked option: `- [ ]`
- Checked option: `- [x]`
- Exactly one `- [x]` is required for `single-select` questions; any number for `multi-select`.
- If `Other` is checked, write the free-text answer on the line immediately following the `Other` option.
- A question is "answered" when at least one option is `- [x]` and (if `Other` is selected) the free-text is non-empty.
- These answers are the canonical input for plan generation (`02-plan.md`).
