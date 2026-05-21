# Questionnaire — R-20260413-2055-bugfixing / Iteration 01

---

## 1. Business & Functional Questions

---

### QID-BF-001 — Old JSON fact files: automatic cleanup after CSV conversion?

**Intent:**  
Decide whether `pipeline.py` should automatically delete the legacy `YYYY-MM-DD.json` fact file when it writes the new `YYYY-MM-DD.csv` for the same date.

**Rationale:**  
After the code change, 58 existing `.json` fact files (~12 GB) will become orphaned — the pipeline will no longer read or write them, but they remain on disk. Automatic cleanup avoids permanent disk waste; manual cleanup gives the operator a chance to verify the CSV output before discarding the originals. The answer affects whether `write_fact_file()` needs an extra `os.unlink()` call and whether any cleanup guard is needed.

**Impact Areas:** Scope, Operations, Data

**Assumptions:**
- Existing JSON files are for local use only and are not consumed by any external system.
- The operator has verified (or will verify) CSV correctness before committing to irreversible deletion.

**Answer Type:** single-select

**Options:**

- [ ] A) Do nothing — leave old `.json` files in place. Operator deletes manually. *(recommended)*
- [ ] B) Auto-delete the `.json` file after writing the `.csv`, but only when `--force` is used.
- [ ] C) Auto-delete the `.json` file every time a `.csv` is written (including first-run re-processing).
- [ ] D) Add a new `--cleanup-json` CLI flag that deletes orphaned `.json` fact files without re-processing.
- [ ] Other — (describe below)

```
Answer Box (fill in if Other is selected or to add context):

```

---

### QID-BF-002 — Placeholder record naming for unknown EKATTE / category_id values

**Intent:**  
Decide the display name format for auto-inserted placeholder city and category dimension records.

**Rationale:**  
When a raw CSV row contains an EKATTE code or `category_id` not found in the nomenclature files, the pipeline will create a placeholder `dim_city` or `dim_category` record. The `city_name` / `category_name` value in that record will appear in Supabase queries and any analytics tooling. A structured, searchable format helps operators quickly identify which codes need resolution; a plain "UNKNOWN" is simpler but loses the key identity in the name field.

**Impact Areas:** Data, Operations, User Experience

**Assumptions:**
- Placeholder records are distinguishable from real records by the `is_unresolved: true` flag (local JSON only) and may also be identified by querying `dim_city` / `dim_category` in Supabase by `city_name` / `category_name` pattern.

**Answer Type:** single-select

**Options:**

- [ ] A) `[UNKNOWN EKATTE:{code}]` / `[UNKNOWN ID:{id}]` — structured prefix with natural key embedded. *(recommended)*
- [ ] B) `UNKNOWN` — simple uniform value; natural key available in the `ekatte` / `category_id` field.
- [ ] C) `PLACEHOLDER:{code}` / `PLACEHOLDER:{id}` — alternative structured prefix.
- [ ] D) Leave the name empty (`""`) — natural key fields (`ekatte`, `category_id`) carry the identity.
- [ ] Other — (describe below)

```
Answer Box (fill in if Other is selected or to add context):

```

---

## 2. Architecture & Technical Questions

*No architecture or technical questions require user input — all relevant technical decisions were resolved during source-code analysis (see `01-analysis.md`, Sections 7 and 9).*

---

## 3. Appendix — Answer Encoding Rules

- Mark a selected option by replacing `[ ]` with `[x]`.
- For **single-select** questions: mark exactly one option `[x]`.
- For **Other**: mark `[x]` on the Other line **and** provide non-empty text in the Answer Box.
- Answers are consumed by the plan-generation step (`create-plan`) and must be completed before planning begins.

**Example — single-select answered:**
```
- [ ] A) Option text
- [x] B) Selected option text
- [ ] C) Option text
- [ ] Other — (describe below)
```
