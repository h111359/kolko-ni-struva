Files considered during this implementation run:
- `.aib_memory/requests_register.md`
- `.aib_memory/requests/R-20260418-2209-keep-raw-download-and-nomenclatures/request.md`
- `.aib_memory/references.md`
- `.aib_memory/context.md`
- `.aib_brain/Concepts.md`
- `.aib_brain/conventions/context-convention.md`
- `.aib_brain/conventions/implementation-convention.md`
- `.aib_brain/conventions/coding-general-convention.md`

## Implementation Log

### Entry 2026-04-19 01:18

#### Scope
Execute request R-20260418-2209: reduce the repository to a download-only surface. Remove `src/`, `data/quality/`, `data/schema/`, and `docs/`; trim `requirements.txt` to three packages; rewrite `README.md` and simplify `.aib_memory/context.md` to reflect the new download-only scope. Pre-deletion backup archive created outside the project root as the sole rollback mechanism.

#### Changes

- Created backup archive `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` (1.4 GB) at the sibling path before any deletion.
- Deleted `src/` directory (contained `pipeline.py` and `migrate_supabase.py`).
- Deleted `data/quality/` directory (60 anomaly report and metrics files).
- Deleted `data/schema/` directory (dimension JSON files, fact files, watermark).
- Deleted `docs/` directory (contained `supabase-setup.md`).
- Edited `requirements.txt`: removed `fastapi==0.115.0`, `uvicorn[standard]==0.30.0`, `aiofiles==24.1.0`, `python-multipart==0.0.9`, `httpx==0.27.0`, `psycopg2-binary`; retained `beautifulsoup4==4.12.0`, `python-dotenv`; updated `requests==2.32.0` to `requests==2.32.5` (security fix — 2.32.0 yanked due to CVE-2024-35195).
- Rewrote `README.md`: removed ETL, Supabase, anomaly detection, and star-schema sections; added Usage (`python extract.py`), Output, and Recovery sections.
- Replaced `.aib_memory/context.md` with simplified content: download-only Product Identity, single functional capability in Requirements, `extract.py`-only Architecture, trimmed Technology Stack, simplified Data Architecture and Operations sections; added recovery instructions.

#### Tests

- T1 — integration: `data/nomenclatures/` exists and contains `cities-ekatte-nomenclature.json` and `product-categories.json` — pass
- T2 — integration: `data/quality/`, `data/schema/`, `docs/`, `src/` absent from project root — pass (all four absent)
- T3 — integration: `python extract.py` — pass; downloaded 5 new ZIPs (`2026-04-14.zip` through `2026-04-18.zip`) to `data/raw/`
- T4 — integration: re-run `python extract.py` — pass; logged "No new files to download."
- T5 — integration: `pip install -r requirements.txt` in existing venv — pass; clean install of `requests==2.32.5`, `beautifulsoup4==4.12.0`, `python-dotenv`; no errors or warnings
- T6 — manual: `README.md` and `.aib_memory/context.md` reviewed — pass; no references to `src/pipeline.py`, `src/migrate_supabase.py`, `data/schema`, `data/quality`, `docs/`, or Supabase remain
- T7 — integration: `../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` exists — pass; size 1.4 GB; archive listing confirmed project structure present

#### Outcome

Successful. Repository is now a download-only surface: `extract.py`, `data/nomenclatures/`, `data/raw/`, `requirements.txt`, `README.md`, `.env`, and AIB framework memory are the only retained components. `python extract.py` runs and downloads ZIPs as expected. One security fix applied: `requests` pin upgraded from 2.32.0 (yanked, CVE-2024-35195) to 2.32.5. No unresolved failures or blockers.

#### Evidence

- `ls data/` output: `nomenclatures  raw`
- T1 output: `cities-ekatte-nomenclature.json  EkatteXLS  Ekatte.zip  Ekatte  EkatteXLS.zip  product-categories.json`
- T2 output: all four folders confirmed absent
- T3 log snippet:
```
2026-04-19 01:16:46,280 INFO: Scraping https://kolkostruva.bg/opendata for ZIP links
2026-04-19 01:16:47,106 INFO: Found 5 new files
2026-04-19 01:16:52,197 INFO: Downloaded 2026-04-18.zip
2026-04-19 01:16:55,618 INFO: Downloaded 2026-04-17.zip
2026-04-19 01:17:00,822 INFO: Downloaded 2026-04-16.zip
2026-04-19 01:17:04,159 INFO: Downloaded 2026-04-15.zip
2026-04-19 01:17:08,720 INFO: Downloaded 2026-04-14.zip
```
- T4 log snippet:
```
2026-04-19 01:17:13,633 INFO: Scraping https://kolkostruva.bg/opendata for ZIP links
2026-04-19 01:17:13,812 INFO: No new files to download.
```
- T7: `ls -lh ../kolko-ni-struva-2-backup-R-20260418-2209.tar.gz` → `-rw-rw-r-- 1 hromar hromar 1.4G Apr 19 01:08`
- Path: `.aib_memory/requests/R-20260418-2209-keep-raw-download-and-nomenclatures/implementation.md`
