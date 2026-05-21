# Questionnaire — Iteration 01

Request: R-20260408-0113 — Extract

---

## 1. Business & Functional Questions

---

### QID-BF-001

**Intent:** Define what constitutes a "wrong" company file so the anomaly-detection rules implement the user's intent.

**Rationale:** The request states "some files are wrong" and asks for detection mechanisms, but does not specify what "wrong" means. The definition directly controls which detection rules are implemented and whether a file is loaded (WARNING) or rejected (REJECTED). Three distinct failure modes exist in the data; the user must confirm which are in scope.

**Impact Areas:** Scope, Requirements, Data, Observability

**Assumptions:**
- A structural failure (wrong column count, encoding error) is always "wrong".
- A volumetric anomaly (row count deviation) may be "wrong" or just informational.
- A semantic anomaly (price outlier vs. historical values) has not been observed in the data yet.

**Answer Type:** multi-select

**Options:**
- [ ] A) Structural only — wrong column count, unparseable price, unresolvable city/category ID after normalization. (recommended)
- [ ] B) Structural + Volumetric — above, plus row count deviates >threshold% from same company's historical mean.
- [ ] C) Structural + Volumetric + Semantic — above, plus price values that are statistical outliers vs. same product/company history.
- [ ] D) Any file where the same company submitted identical data on two consecutive days (exact duplicate detection).
- [ ] Other — (describe below):

**Constraints & Guards:** Multi-select allowed. If C) is selected, price-outlier baseline computation adds significant implementation complexity and is deferred to a second iteration.

---

### QID-BF-002

**Intent:** Confirm whether the pipeline must process (backfill) all 52 existing ZIPs on the first run or only forward-going downloads.

**Rationale:** 52 ZIPs (2026-02-15 to 2026-04-07) are already present in `data/raw/`. Without backfill the schema is empty and anomaly detection has no 7-day historical baseline for later runs. If backfill is required it adds significant first-run time (~66M rows); if not, the schema starts empty.

**Impact Areas:** Scope, Requirements, Data, Timeline

**Assumptions:**
- Backfill is assumed required (Assumption A2 in analysis).
- First-run processing time is estimated at several minutes on a modern machine (streaming, one ZIP at a time).

**Answer Type:** single-select

**Options:**
- [ ] A) YES — process all existing 52 ZIPs on first run; provide `--no-backfill` flag to skip. (recommended)
- [ ] B) NO — only process ZIPs downloaded after the script is deployed; schema starts empty.
- [ ] C) PARTIAL — process only the most recent N days (e.g. 14) to populate a baseline; configurable via `--backfill-days N`.
- [ ] Other — (describe below):

**Constraints & Guards:** If B) is selected, anomaly detection will have no baseline for the first 7 days and will produce no volumetric anomaly flags.

---

## 2. Architecture & Technical Questions

---

### QID-AT-001

**Intent:** Decide whether the new pipeline is a single integrated script or separate download + ETL modules.

**Rationale:** The existing `extract.py` already handles ZIP download. The request asks for a script in `src/` that "downloads...and then populates the schema". Two architectures are viable: (A) one combined `src/pipeline.py` that supersedes `extract.py`, or (B) separate `src/download.py` + `src/etl.py` keeping `extract.py` intact. The choice impacts repo structure, scheduling, and whether `extract.py` is deprecated.

**Impact Areas:** Architecture, Scope, Operations

**Assumptions:**
- A single entry point is simpler to schedule and document.
- Separation enables independent execution (e.g., download on one schedule, ETL on another).

**Answer Type:** single-select

**Options:**
- [ ] A) Single `src/pipeline.py` — integrates download + ETL + quality check; `extract.py` is kept but superseded. (recommended)
- [ ] B) Separate scripts — `src/etl.py` handles ETL only; `extract.py` (or a copy in `src/download.py`) handles download.
- [ ] C) Single `src/pipeline.py` replacing `extract.py` — `extract.py` is deleted.
- [ ] Other — (describe below):

**Constraints & Guards:** If C) is selected, `extract.py` must be deleted; confirm destructive action before implementation.

---

### QID-AT-002

**Intent:** Set the default anomaly detection threshold for row-count deviation before the pipeline flags a company file as WARNING.

**Rationale:** The analysis proposes a 30% row-count deviation from a 7-day rolling mean as the default threshold. This parameter is configurable but the default affects which files are flagged on every run. Too strict = excess false positives; too lenient = real errors missed. The user is closest to the domain and can best judge the tolerance.

**Impact Areas:** Data, Observability, Requirements

**Assumptions:**
- Row counts for the same company are generally stable day-to-day (confirmed: 0 diff observed across 3 companies on 2 sampled days).
- Legitimate reasons for large deviations include new store openings, store closures, seasonal promotions (expanded catalogue).

**Answer Type:** single-select

**Options:**
- [ ] A) 30% deviation from 7-day rolling mean. (recommended)
- [ ] B) 20% deviation from 7-day rolling mean (stricter).
- [ ] C) 50% deviation from 7-day rolling mean (more lenient).
- [ ] D) No volumetric threshold — flag only structural errors; row-count deviation is informational only.
- [ ] Other — (describe below):

**Constraints & Guards:** The threshold must be expressed as a float constant (0.0–1.0) in the script; selected value will be documented in DATA-07. If D) selected, see also QID-BF-001 options.

---

## 3. Appendix — Answer Encoding Rules

- Unchecked option: `- [ ]`
- Checked option: `- [x]`
- Exactly one `- [x]` is required for `single-select` questions; any number for `multi-select`.
- If `Other` is checked, write the free-text answer on the line immediately following the `Other` option.
- A question is "answered" when at least one option is `- [x]` and (if `Other` is selected) the free-text is non-empty.
- These answers will be used as canonical input for plan generation (`01-plan.md`).
