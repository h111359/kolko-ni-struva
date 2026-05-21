## Executive Summary

- Request ID: R-20260418-2209

- Request title: Keep raw download and nomenclatures

- High-level purpose: Reduce the repository to a minimal surface that retains only `extract.py` as the sole downloader entry point, keeps `data/nomenclatures`, and removes the full ETL pipeline, migration script, historical data artifacts, and supplementary documentation.

- Source of truth: `request.md` in the same request folder defines the formal Goal, Background, Scope, Out of scope, Constraints, and Success criteria.

- Re-run note: This is the second analysis run, triggered by user feedback (input.md `## Input`) identifying that the workspace has no git repository while the previous plan contained git branch creation and `git rm`/`git commit` operations. All five AI-generated `request.md` sections are fully replaced.

- `request.md` sections fully replaced in this run: `## Assumptions`, `## Plan`, `## Testing`, `## Documentation`, `## Code and Asset Scan for Impacted Components`, `## Internal Review of Request and Product Docs`, `## Multi-Perspective Stakeholder Review`. `## Questions & Decisions` — no new questions raised; content unchanged.

- Key change from previous run: no git repository exists in the workspace (confirmed: `git status` → "fatal: not a git repository (or any of the parent directories): .git"). The `## Constraints` "or documented steps" fallback is applied: a pre-deletion tar archive stored outside the project root is the sole recovery mechanism. All four plan tasks that referenced `git checkout`, `git rm`, or `git commit` are replaced with filesystem operations.

- All other findings from the first analysis run remain valid: `extract.py` is fully self-contained, 6 dependencies are removable, removed directories are not consumed by `extract.py`.


## Domain Knowledge Essentials

- kolkostruva.bg/opendata: Bulgarian government retail-price transparency portal. Publishes one ZIP archive per day, each containing one CSV per reporting retail company (~208 companies/day). The open-data availability and format are outside the product team's control.

- EKATTE: Bulgarian administrative code registry for municipalities and settlements. Used to map location codes in raw company CSVs to human-readable city names. File `data/nomenclatures/cities-ekatte-nomenclature.json` holds this mapping; must be preserved.

- Product categories: static list mapping numeric category IDs to Bulgarian category names. File `data/nomenclatures/product-categories.json` holds this mapping; must be preserved.

- Actors: data operator/engineer who runs the downloader periodically to stage new raw ZIPs locally. No end-user UI; no automated scheduling configured.

- Business process retained by this request: daily HTTP download of government ZIP archives to `data/raw/`.

- Business processes removed by this request: CSV parsing, SCD Type 2 dimension management, fact file writing, anomaly detection, quality reporting, and Supabase cloud sync.

- Acceptance impact: stakeholders accept that all historical processed data (`data/quality`, `data/schema`) will be removed; raw ZIPs in `data/raw` remain; git history provides recovery of removed code and data artifacts.


## Technical Knowledge & Terms

- `extract.py` (workspace root): 110-line standalone download utility. Imports: `pathlib`, `time`, `logging`, `urllib.parse` (stdlib), `requests`, `bs4.BeautifulSoup`. Functions: `fetch_page`, `parse_zip_links`, `existing_filenames`, `download_file`, `main`. No imports from `src/` or any pipeline module. Confirmed self-contained.

- `src/pipeline.py`: ~760-line full ETL module. Contains a duplicated download subsystem — `_fetch_page`, `_parse_zip_links`, `_download_file`, `download_new_zips` — mirroring `extract.py` with minor parameter differences (chunk size 65 536 vs 8 192; download timeout 120 s vs 60 s). Post-download ETL logic (CSV parsing, `DimensionStore`, `build_facts`, anomaly detection) is tightly coupled and not isolatable without significant refactoring. Entire file is removable.

- `src/migrate_supabase.py`: Cloud sync module. Zero shared imports or functions with `extract.py`. Removable in full.

- `requirements.txt`: 9 pinned packages. Downloader-required packages: `requests==2.32.0`, `beautifulsoup4==4.12.0`. Optional for downloader: `python-dotenv` (not imported by `extract.py`; retained if operators use `.env` for future config). Removable packages: `fastapi==0.115.0`, `uvicorn[standard]==0.30.0`, `aiofiles==24.1.0`, `python-multipart==0.0.9`, `httpx==0.27.0`, `psycopg2-binary`.

- `data/quality/` (~80 files): per-day anomaly report and metrics JSON files produced exclusively by the ETL transform stage. Not consumed by `extract.py`. Removable.

- `data/schema/`: SCD Type 2 dimension JSON files and date-partitioned fact JSON files. Produced exclusively by the ETL transform stage. Includes `.migrate_watermark.json`. Removable.

- `docs/supabase-setup.md`: Supabase DDL and setup guide. Out of scope for download-only. Removable.

- SCD Type 2: slowly-changing dimension versioning pattern (attributes versioned with `valid_from`/`valid_to`/`is_current`). Relevant only to the removed `DimensionStore` in `src/pipeline.py`.

- Atomic write pattern: temp-file-then-`os.replace()`. Used by `src/pipeline.py` and `src/migrate_supabase.py`; `extract.py` uses the equivalent `.partial`-suffix-then-`Path.rename()` for download files.

- `.env`: holds only `DATABASE_URL` (Supabase connection string). `extract.py` does not load `.env`; must remain in place (not committed) per constraint.

- Files Read (evidence → implication):

  - `.aib_memory/requests_register.md` → one Active request (R-20260418-2209) confirmed; standard flow.

  - `.aib_memory/input.md` → both toggles unchecked; `## Input` contains user feedback ("The folder is not a git repo and you still have a task for branching and git operations. Why? Revise"); standard analysis re-run with plan revision.

  - `git status` (runtime check) → "fatal: not a git repository (or any of the parent directories): .git"; workspace has no VCS; git-based plan tasks are invalid and replaced.

  - `.aib_memory/references.md` → one product-doc REF-0001 (`.aib_memory/context.md`) required.

  - `.aib_memory/context.md` → authoritative product context; confirms component map, data lineage, and module responsibilities.

  - `extract.py` (full file) → confirmed completely standalone; no `src/` imports; sufficient as sole retained downloader.

  - `src/pipeline.py` lines 555–695 (download subsystem + main) → download duplication confirmed; ETL code not isolatable; entire file removable.

  - `requirements.txt` → 6 of 9 packages unused by `extract.py`; confirmed removable.

  - `.aib_brain/Concepts.md` → AIB framework reference; no impact on product scope.

  - `.aib_brain/conventions/analysis-convention.md` → structure for this document.

  - `.aib_brain/conventions/request-convention.md` → `request.md` editing rules.


## Research Results

- **No-git discovery:** Workspace contains no `.git` directory (confirmed: `git status` → "fatal: not a git repository"). All plan tasks from the previous run that referenced `git checkout -b`, `git rm -r`, and `git commit` are inapplicable. The "documented steps" fallback in `## Constraints` ("prefer `git rm` or documented steps") is the applicable path. A pre-deletion tarball archived outside the project root satisfies the reversibility constraint.

- `extract.py` satisfies the full downloader requirement without modification. Its docstring explicitly describes it as a "Simple extractor: scrape kolkostruva opendata page and download new ZIPs." It is shorter, simpler, and purpose-focused compared to the functionally equivalent but coupled download subsystem buried in `src/pipeline.py`.

- The download subsystem in `src/pipeline.py` is a functional duplication of `extract.py` with no architectural advantages for the retained use case. The slight parameter differences (larger chunk size, longer timeout) are inconsequential for the intended scope.

- `src/migrate_supabase.py` shares no code with `extract.py` and has no transitive imports from `extract.py` or vice versa. Removing it poses zero risk to downloader functionality.

- No `src/` module is referenced by `extract.py`. The `import` list in `extract.py` contains only stdlib and two third-party packages (`requests`, `bs4`). Removing `src/` does not break `extract.py`.

- `requirements.txt` trimming: 6 packages (`fastapi`, `uvicorn[standard]`, `aiofiles`, `python-multipart`, `httpx`, `psycopg2-binary`) are not imported by any code path reachable from `extract.py`. Removing them reduces installation time and dependency attack surface without any downloader impact.

- `data/raw/` contains both ZIPs and extracted directories (e.g., `data/raw/2026-02-15/`) for early dates. `extract.py` uses only `data/raw/` as its write target and checks for existing filenames via `existing_filenames(RAW_DIR)` — it iterates files but does not interact with subdirectories. Both ZIPs and subdirectories in `data/raw/` are preserved by the cleanup scope; no conflict exists.


## External Benchmarking

- **Single-concern raw-data fetcher pattern (data engineering industry practice):** Modern data platform architectures (e.g., Medallion architecture, Lambda architecture) rigorously separate the ingestion/staging layer from the transformation layer. The fetch stage's only concern is to write raw, unmodified source data to a landing zone (equivalent to a Bronze layer). `extract.py` already embodies this pattern.

  - Takeaway: adopt `extract.py` as-is; no structural refactoring of the downloader is required.

  - Applicability: high — directly matches request intent.

- **Dependency surface minimization (DevSecOps and supply-chain security practice):** Projects should include only libraries directly consumed by the code in use (SBOM hygiene, CIS Software Supply Chain controls). Each extra package is an attack vector and a maintenance burden. The 6 removable packages in `requirements.txt` include a full ASGI web framework stack (`fastapi`, `uvicorn`) and a PostgreSQL driver (`psycopg2-binary`), none of which are needed for HTTP downloading.

  - Takeaway: remove the 6 unused packages; pin `requests` and `beautifulsoup4`; retain `python-dotenv` only if `.env` loading is desired.

  - Applicability: adopt during implementation.

- **Pre-deletion tarball backup (operational safety best practice):** In the absence of a VCS, creating a compressed archive of the full project root before any destructive change is the standard safe-cleanup pattern. The archive is stored as a sibling to the project directory to ensure it is not accidentally deleted as part of the cleanup. Recovery procedure: `tar -xzf <backup>.tar.gz -C <parent>` and locate the needed file by path.

  - Takeaway: create `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` as the first irreversible-operation gate in the plan; document the recovery command in `README.md`.

  - Applicability: adopt; replaces the "git safety branch" approach from the previous analysis run.


## Minimal Spikes and Experiments

- **Spike: `extract.py` self-containment verification**

  - Hypothesis: `extract.py` requires no imports from `src/` and no runtime dependency on any ETL or migration module; it can run independently after `src/` is deleted.

  - Approach: Read `extract.py` in full; inspect all `import` statements; confirm no path references `src/` or pipeline modules.

  - Outcome: `extract.py` imports `pathlib`, `time`, `logging`, `urllib.parse` (all stdlib), `requests`, and `bs4.BeautifulSoup`. No `src/` imports. No references to `SCHEMA_DIR`, `QUALITY_DIR`, `FACTS_DIR`, or any pipeline constant.

  - Conclusion: `extract.py` is fully self-contained and will function correctly after `src/` is removed. No code modifications are needed for the downloader.


## Risks (explicit)

- Risk 1: File deletion is irreversible without the backup tarball. If Task 2 is skipped or the archive is stored inside the project root and then deleted, all removed files are unrecoverable — there is no git history. Mitigation: verify the archive exists at the sibling path and its size is non-zero before executing Task 3 (`rm -rf`).

- Risk 2: `data/raw/` contains both ZIPs and extracted subdirectories for early dates (e.g., `2026-02-15/` directory). These are in scope to keep and will not be removed. However, `existing_filenames()` in `extract.py` iterates files (not directories); if the portal later re-publishes a ZIP whose name matches an extracted subdirectory, `extract.py` will download it again (the directory check is a ZIP duplicate check, not a directory check). Mitigation: Low-risk for the current use case; note in documentation.

- Risk 3: Removing `src/migrate_supabase.py` removes all Supabase sync capability. If the operator later needs to resume cloud sync, they must recover the file from the backup tarball (`tar -xzf ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz kolko-ni-struva-2/src/migrate_supabase.py`) and re-add `psycopg2-binary` to `requirements.txt`. Mitigation: confirm stakeholder acceptance; note recovery path in documentation.

- Risk 4: `requirements.txt` trimming removes `python-dotenv`. `extract.py` does not load `.env`, so `DATABASE_URL` is not consumed by the downloader. If an operator tries to run with `.env` present, it will have no effect unless `python-dotenv` is loaded explicitly. Mitigation: clarify in `README.md` that `.env` is not used by the downloader and is kept as a placeholder.

- Risk 5: `README.md` currently documents the full ETL, CLI flags (`--no-backfill`, `--force`, `--threshold`), and Supabase setup. Leaving stale references to removed functionality is a high operator-confusion risk. Mitigation: fully rewrite `README.md` as part of this request.


--- I am done with the analysis ---
