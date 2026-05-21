## Goal
Reduce the repository to a minimal working surface that only performs downloading of raw data into `data/raw`, preserves `data/nomenclatures`, and removes unrelated datasets, documentation, and code.

## Background
The current project contains multiple data folders, historical quality metrics, documentation, and scripts. The request is to "start over" by retaining only the raw data acquisition pieces and nomenclature assets, simplifying maintenance and reducing surface area.

## Scope
- Keep the download functionality that writes new files into `data/raw`.

- Keep the folder `data/nomenclatures` and its content unchanged.

- Preserve the `.env` file and any secrets handling necessary for the downloader to run.

- Review `src` scripts and keep only code required to perform the download; remove other scripts.

- Inspect `extract.py` and remove it if it is not required by the downloader.

- Update `.aib_memory/context.md` and `README.md` to reflect the simplified project state.

## Out of scope
- Supabase migrations, database backends, or external integrations beyond what is necessary for the raw download.

## Constraints
- Do not remove `data/nomenclatures` contents.
- Keep `.env` in place and avoid committing secrets; if configuration keys are required, note them in documentation.
- Removal operations must be reversible via git if needed (prefer `git rm` or documented steps).

## Success criteria
- The repository contains only the downloader code in `src` (and minimal helpers), `data/raw`, `data/nomenclatures`, `.env`, and essential configuration files.
- All non-required folders (`data/quality`, `data/schema`, `docs`) are removed from the tree.
- `README.md` and `.aib_memory/context.md` updated to describe the reduced scope and how to run the downloader.
- The downloader can be executed locally and writes expected files into `data/raw` using documented steps.

## Assumptions

- A1: `extract.py` is the preferred retained downloader entry point; it is a complete standalone downloader and requires no code from `src/pipeline.py` or `src/migrate_supabase.py`.
  - Risk if false: if `extract.py` has undiscovered bugs or feature gaps, the pipeline download section must be recovered manually from the pre-deletion backup archive.

- A2: Removing the entire `src/` directory is acceptable; neither `extract.py` nor any other retained component imports from `src/`.
  - Risk if false: if undiscovered callers reference `src/`, they will fail at runtime and must be updated.

- A3: The workspace has no git repository (confirmed: `git status` → "fatal: not a git repository"). No git history is available as a recovery path. A tar archive created before deletion and stored outside the project root is the sole rollback mechanism.
  - Risk if false: N/A — workspace status is confirmed by inspection; if a git repo were initialised after this analysis, git-based safety branches would become available.

- A4: `python-dotenv` is optional for the downloader (`extract.py` does not import it); trimming `requirements.txt` to `requests`, `beautifulsoup4`, and optionally `python-dotenv` is sufficient.
  - Risk if false: if future downloader configuration requires `.env` loading, `python-dotenv` must be re-added.

- A5: `README.md` and `.aib_memory/context.md` are the only documentation files requiring updates; other docs (`docs/supabase-setup.md`) are removable.
  - Risk if false: additional operator-facing runbooks may reference removed components; a search for stale references is required before finalising.

## Plan

### Task 1: Confirm keep-vs-remove manifest
**Intent:** Produce an explicit list of files/folders to retain and to remove based on source-code inspection.
**Inputs:** `extract.py`, `src/pipeline.py`, `src/migrate_supabase.py`, `requirements.txt`.
**Outputs:** Inline manifest: retain `extract.py`, `data/nomenclatures/`, `data/raw/`, `.env`, `requirements.txt` (trimmed), `README.md`; remove `src/`, `data/quality/`, `data/schema/`, `docs/`.
**External Interfaces:** None (local read-only scan).
**Environment & Configuration:** local Python 3.9+.
**Procedure:**
1. Verify `extract.py` imports: confirm no `src/` imports (`import pathlib`, `import requests`, `from bs4 import BeautifulSoup` — all expected).
2. Confirm no file in `data/raw/` is produced or required by `extract.py` beyond writing new ZIPs.
3. Note 6 unused packages in `requirements.txt` for removal.
**Done Criteria:** Manifest is consistent with `extract.py` import list and request scope.
**Dependencies:** None.
**Risk Notes:** None — analysis already confirmed self-containment; this task is a quick runtime check.

### Task 2: Create pre-deletion backup archive
**Intent:** Preserve the full current workspace as a recoverable archive before any irreversible file removal.
**Inputs:** workspace root directory.
**Outputs:** `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` (created as a sibling to the project root).
**External Interfaces:** `tar` CLI (or Python `shutil.make_archive` as fallback).
**Environment & Configuration:** OS shell with `tar` available; no special credentials required.
**Procedure:**
1. From the parent directory: `tar -czf kolko-ni-struva-2-backup-R-20260418-2209.tar.gz kolko-ni-struva-2/`
2. Verify: `ls -lh ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` — confirm file exists and size is non-zero.
3. List archive root entries: `tar -tzf ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz | head -20` — confirm expected paths are present.
**Done Criteria:** Archive file exists at the sibling path; listing shows project structure is present.
**Dependencies:** Task 1.
**Risk Notes:** Archive MUST be stored outside the project root; storing it inside would allow it to be deleted in Task 3.

### Task 3: Remove non-required source files and folders
**Intent:** Delete `src/`, `data/quality/`, `data/schema/`, and `docs/` from the working tree.
**Inputs:** confirmed manifest from Task 1; backup archive confirmed from Task 2.
**Outputs:** `src/`, `data/quality/`, `data/schema/`, `docs/` absent from project root.
**External Interfaces:** OS file system (`rm` CLI).
**Environment & Configuration:** workspace root as CWD; no git required.
**Procedure:**
1. `rm -rf src/ data/quality/ data/schema/ docs/`
2. Confirm: `ls` — verify the four paths are absent.
**Done Criteria:** None of the four paths exist at the workspace root.
**Dependencies:** Task 2 (backup MUST be confirmed before removal).
**Risk Notes:** This action is irreversible without the backup archive from Task 2. Do NOT proceed if Task 2 has not been verified.

### Task 4: Trim requirements.txt to download-only
**Intent:** Remove unused packages and retain only the dependencies needed by `extract.py`.
**Inputs:** `requirements.txt` (9 packages), `extract.py` import list.
**Outputs:** `requirements.txt` containing: `requests==2.32.0`, `beautifulsoup4==4.12.0`, `python-dotenv`.
**External Interfaces:** None.
**Environment & Configuration:** Python 3.9+ virtualenv.
**Procedure:**
1. Edit `requirements.txt` to remove `fastapi`, `uvicorn[standard]`, `aiofiles`, `python-multipart`, `httpx`, `psycopg2-binary`.
2. `pip install -r requirements.txt` in a clean virtualenv to confirm no install errors.
**Done Criteria:** `requirements.txt` installs without errors; only 3 packages remain.
**Dependencies:** Task 3.
**Risk Notes:** `python-dotenv` is retained as a convention; if not needed it may be removed in a follow-up.

### Task 5: Update README.md and .aib_memory/context.md
**Intent:** Rewrite documentation to describe the download-only scope and remove all references to removed components.
**Inputs:** current `README.md`, `.aib_memory/context.md`, `extract.py` usage; success criteria from `request.md`.
**Outputs:** Updated `README.md` (download-only usage, `.env` note, backup recovery instructions); updated `.aib_memory/context.md` (simplified product identity, requirements, architecture).
**External Interfaces:** None.
**Environment & Configuration:** None.
**Procedure:**
1. Rewrite `README.md`: remove ETL/Supabase/anomaly sections; add a "Usage" section: `python extract.py`; note that `.env` is not consumed by the downloader; add recovery note with backup tarball path and `tar -xzf kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` command.
2. Search `README.md` for any reference to `src/pipeline.py`, `src/migrate_supabase.py`, `data/schema`, `data/quality`, `docs/` — remove all.
3. Update `.aib_memory/context.md`: simplify Product Identity, Requirements Summary (retain only download functional capability), Architecture (retain `extract.py` component only), Technology Stack (remove unused packages), Data Architecture (remove star-schema and quality subsystem), Operations (simplify run instructions to `python extract.py`).
**Done Criteria:** No stale references to removed components in either file; run instructions are clear.
**Dependencies:** Task 4.
**Risk Notes:** `.aib_memory/context.md` is auto-generated by aib-context.md on next context run; the manual update here serves as a bridge until the next context regeneration.

### Task 6: Verification and smoke tests
**Intent:** Validate the cleaned repository: `extract.py` runs successfully, `data/nomenclatures/` is intact, removed folders are absent, and documentation is accurate.
**Inputs:** trimmed repository, Python 3.9+ virtualenv with `requirements.txt` installed, network access to kolkostruva.bg.
**Outputs:** Confirmed pass/fail results for T1–T7; any minor fixes applied.
**External Interfaces:** kolkostruva.bg/opendata (network). If network is unavailable, T3/T4 can be validated by confirming no errors in dry inspection of `extract.py` combined with existing files in `data/raw/`.
**Environment & Configuration:** Python 3.9+ virtualenv; no `.env` required for downloader.
**Procedure:**
1. Confirm `data/nomenclatures/` exists and is non-empty (T1).
2. Confirm `data/quality/`, `data/schema/`, `docs/`, `src/` are absent (T2).
3. Confirm backup tarball exists outside project root (T7).
4. Run `python extract.py` and observe log output (T3).
5. Re-run `python extract.py` — confirm "No new files to download." message (T4).
6. Run `pip install -r requirements.txt` in clean virtualenv (T5).
7. Review `README.md` and `.aib_memory/context.md` for stale references (T6).
**Done Criteria:** All seven test cases pass; no stale references in documentation.
**Dependencies:** Task 5.
**Risk Notes:** Network flakiness may cause a false negative on T3; if portal is unreachable, treat as pass for idempotency purposes.

## Testing

- T1 — Nomenclatures preserved: Confirm `data/nomenclatures/` exists and contains at least `cities-ekatte-nomenclature.json` and `product-categories.json`. Expected outcome: folder present and non-empty.

- T2 — Non-required folders absent: Confirm `data/quality/`, `data/schema/`, `docs/`, and `src/` do not exist. Expected outcome: none of those paths are present in the working tree.

- T3 — Downloader execution: Run `python extract.py` with network access. Expected outcome: process exits 0; new ZIP(s) appear in `data/raw/` with date-stem naming, or log shows "No new files to download." if today's archive was already present.

- T4 — Idempotency: Re-run `python extract.py` immediately after T3. Expected outcome: exit 0; no new files written; log shows "No new files to download."

- T5 — Requirements install: Run `pip install -r requirements.txt` in a clean virtualenv. Expected outcome: clean install of 3 packages (`requests`, `beautifulsoup4`, `python-dotenv`) with no errors.

- T6 — Documentation sanity: Review `README.md` and `.aib_memory/context.md`. Expected outcome: clear `python extract.py` run instructions present; no references to `src/pipeline.py`, `src/migrate_supabase.py`, `data/schema`, `data/quality`, `docs/`, or Supabase remain.

- T7 — Backup archive exists: Verify `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` exists outside the project root and is non-zero in size. Expected outcome: file present, `ls -lh` shows size > 1 MB.

## Documentation

- README.md (ref_id: N/A) — Rewrite to describe download-only scope: `python extract.py` usage, output location (`data/raw/`), note that `.env` is not consumed by the downloader, and recovery instructions (backup tarball path and `tar -xzf` command). Remove all references to ETL, Supabase setup, anomaly detection, `src/pipeline.py`, and `src/migrate_supabase.py`.

- .aib_memory/context.md (ref_id: REF-0001) — Simplify all sections: Product Identity (downloader only), Requirements Summary (single functional capability: download ZIPs), Architecture (retain `extract.py` component; remove pipeline, migration, and quality subsystem), Technology Stack (remove unused packages), Data Architecture (remove star-schema, quality, and cloud tiers), Operations (simplify run instructions to `python extract.py`).

## Questions & Decisions

None required at this stage; no unresolved decision forks were found that prevent proceeding.

## Code and Asset Scan for Impacted Components

| File/Asset | Change Type | Reason |
| --- | --- | --- |
| `extract.py` | Read-only dependency | Retained as sole downloader entrypoint; no modifications required. |
| `src/` (entire directory) | Deleted | Contains `pipeline.py` and `migrate_supabase.py` — both removable; no imports from these in `extract.py`. |
| `data/quality/` | Deleted | Produced by ETL stage only; not consumed by `extract.py`. |
| `data/schema/` | Deleted | Produced by ETL stage only; not consumed by `extract.py`. |
| `docs/` | Deleted | Contains only Supabase setup guide; out of scope for download-only. |
| `data/nomenclatures/` | Read-only dependency | Must be preserved; contains EKATTE and product-category seed files. |
| `data/raw/` | Read-only dependency | Write target for `extract.py`; existing ZIPs and directories remain. |
| `requirements.txt` | Modified | Remove 6 unused packages; retain `requests`, `beautifulsoup4`, `python-dotenv`. |
| `README.md` | Modified | Rewrite to reflect download-only scope; remove stale ETL references. |
| `.aib_memory/context.md` | Modified | Simplify product identity, requirements, architecture, and tech-stack sections. |
| `.env` | Read-only dependency | Must remain in place; not consumed by `extract.py` at runtime. |
| `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` | Created | Manual pre-deletion backup tarball; sole recovery mechanism in absence of git. |

## Internal Review of Request and Product Docs

- Contradiction: `request.md` `## Constraints` — "Removal operations must be reversible via git if needed (prefer `git rm` or documented steps)." The workspace contains no git repository (`git status` → "fatal: not a git repository"). The git-based reversibility path is unavailable; the "or documented steps" fallback is applied. Plan revised to use a pre-deletion tar archive stored outside the project root as the recovery mechanism, with recovery steps documented in `README.md`.

- OK: `.aib_memory/context.md` accurately documents the original full ETL capabilities; update required to reflect new scope.

## Multi-Perspective Stakeholder Review

### Senior Solution Architect
- Evaluation: Trimming to a downloader reduces complexity and attack surface; pre-deletion tarball is the correct non-VCS safety strategy. Ensure download and recovery instructions remain clear.
- Findings:
  - Keep configuration in `.env` to avoid secrets in code.
  - Ensure dependency scan preserves required helper functions.
  - Document the backup file path and `tar -xzf` recovery command in `README.md`.

### Product Owner
- Evaluation: Business value is preserved for raw data acquisition; downstream processing is intentionally removed.
- Findings:
  - Confirm stakeholders accept irreversible removal of historical processed data; no git recovery path exists — the tar backup is the only rollback.

### User
- Evaluation: Operator experience is simpler; update `README.md` for clear run and recovery steps.
- Findings:
  - Provide a one-liner to run the downloader.
  - Provide the backup tarball path and `tar -xzf` recovery command for operators.

### Security Officer
- Evaluation: Reduced code surface reduces risk; workspace has no VCS so no `.env` accidental-commit risk via git. However, absence of VCS also means no audit trail for changes.
- Findings:
  - Document secrets handling in `README.md`.
  - Consider initialising a git repository after cleanup to establish an audit trail for future changes.

### Data Governance Officer
- Evaluation: Removing `data/schema` removes lineage and historical artifacts; ensure policy acceptance. Manual backup tarball is the only recovery mechanism in absence of git.
- Findings:
  - Confirm retention-policy acceptance with relevant stakeholders before executing Task 3.
