## Purpose
Define the exact format, lifecycle, and editing rules for the request‑scoped `implementation.md` file so implementations can be recorded deterministically, audited reliably, and consumed by automation without ambiguity.

## Applicability
This convention applies to every request folder under `.aib_memory/requests/<request-folder>/` that contains a single `implementation.md` file. It is request‑scoped and append‑only.

## Canonical File Path
- Location: `.aib_memory/requests/<request-folder>/implementation.md`
- Exactly one `implementation.md` per request.
- The file MUST exist after the first successful `implement` action for the request.

## Relationship to AIB Actions (Normative)
- The `implement` action MUST write to this file (create if missing, append otherwise).
- The action MUST respect the append‑only rule and MUST NOT rewrite or delete previous entries.
- The action MAY synthesize entry content using analysis artifacts for the same request.

## Authoring Model
- Primary author: automation (AIB tools/prompts).
- Human edits are allowed only for typo fixes or to add clarifying notes in the designated field; structure MUST remain intact.

## File Structure (Top‑Level)
The file is a Markdown document composed of an ordered sequence of **Entries**. Each Entry documents one implementation increment for the request.

Top‑level layout:
1. Optional short introduction paragraph (plain text, no headings).
2. List of .aib_memory/ files taken into consideration
3. `## Implementation Log` (single section header).
4. A strictly chronological list of Entries. Newest entries are appended to the end.

### Entry Block Format (Strict)
Each Entry is a Markdown block with the following exact structure and headings in this exact order:

- `### Entry <YYYY-MM-DD HH:MM>`
- `#### Scope`
- `#### Changes`
- `#### Tests`
- `#### Outcome`
- `#### Evidence`
- `#### Notes (Optional)`

**Formatting rules:**
- Times are local project time in 24h format (`YYYY-MM-DD HH:MM`).
- Headings MUST be level‑3 for the entry title and level‑4 for all sub‑sections.
- Lists under `Changes`, `Tests`, and `Evidence` MUST be Markdown bullet lists (`- `).
- Code, commands, or logs in any section MUST be fenced with triple backticks and a language hint when applicable (e.g., ` ```bash `). Do NOT break the outer document fence.

### Field Semantics
- **Scope**: 1–5 sentences summarizing the goal of the change as implemented in this increment. Reference impacted areas/components.
- **Changes**: Bullet list of concrete modifications (files, modules, documents, data jobs, infra changes). Each bullet SHOULD start with a verb in past tense.
- **Tests**: Bullet list describing tests executed. Each bullet MUST state type (unit/integration/e2e/perf/security), the target, and pass/fail result. Include minimal evidence pointers if not in `Evidence`.
- **Outcome**: Short paragraph stating the result (success/partial/failed), residual risks, and follow‑ups.
- **Evidence**: Bullet list of artifact pointers (paths to screenshots/logs/reports in repo, or inline fenced snippets).
- **Notes (Optional)**: Free‑form clarifications. Human edits are allowed here.

## Determinism & Append‑Only Rules (Normative)
- Entries MUST be appended; existing entries MUST remain bit‑for‑bit unchanged (except authorized typo fixes in `Notes (Optional)`).
- If a previously appended entry needs correction beyond typos, a new Entry MUST be added describing the correction; do not alter history.
- Entry timestamps MUST be strictly increasing.
- Exactly one Entry per `implement` action invocation.
- If an `implement` action spans multiple commits or steps, consolidate into one Entry for that action and summarize under `Changes` and `Tests`.

## Cross‑Artifact Consistency
- When available, the Entry SHOULD cross‑reference sections from `analysis.md` using plain text (do not use links). Example: "Aligned with analysis section 4.5".

## Validation Rules (Automation MUST Enforce)
- File exists and is UTF‑8 encoded text.
- Starts with any optional prose, then contains exactly one `## Implementation Log` header.
- Every Entry title matches regex: `^### Entry \d{4}-\d{2}-\d{2} \d{2}:\d{2}$`
- Sub‑sections exist exactly once per Entry and in the mandated order.
- Timestamps strictly increase across Entries.
- No Markdown tables are used inside `Changes`, `Tests`, or `Evidence` (lists only).
- No external hyperlinks are present anywhere in the file (plain text references only).

## Editing Workflow
- **Automation (default)**: AIB appends a fully‑formed Entry when `implement` completes.
- **Human (exceptional)**: May refine `Notes (Optional)` or fix typos without changing structure, headings, or order. Any substantial change requires a new Entry.

## Example (Illustrative)
> The example below is illustrative; do not pre‑seed real files with it.

### Entry 2026-03-08 19:05
#### Scope
Implement initial seeding tool for `.aib_memory` and generate register files.

#### Changes
- Added `tools/initialize.py` to create memory folders and seed default docs.
- Created `.aib_memory/requests_register.md`.
- Updated CI job to run initialization check on clean workspaces.

#### Tests
- unit: `test_initialize_seeding` — pass
- integration: run on empty workspace — pass
- integration: re‑run idempotency — pass

#### Outcome
Successful initialization. Workspace now reproducible; re‑runs converge with no diffs.

#### Evidence
- Path: `.aib_memory/requests_register.md`
- Log snippet:
  ```text
  Seeding .aib_memory ... OK
  Created requests_register.md
  ```

#### Notes (Optional)
Next: add validation step for duplicate requirement IDs.

## Anti‑Patterns (Do Not)
- Do not reorder or delete Entries.
- Do not collapse multiple `implement` runs into one Entry retroactively.
- Do not paste screenshots as base64 blobs; store files and reference their repo paths.
- Do not include owners, authors, or approval metadata here; those belong elsewhere.

## Interaction with Product Documentation
- If implementation updates any documentation artifacts (e.g., items in `.aib_memory/docs/...`), list those under `Changes` and provide their relative paths under `Evidence`.

## Consumption by Tools
- Parsers can rely on:
  - A single `## Implementation Log` header.
  - Entry title regex and fixed sub‑section sequence.
  - Bullet list structures for `Changes`, `Tests`, `Evidence`.
- Tools SHOULD treat unknown additional headings as invalid.

## Performance & Size Guidance
- Keep Entries concise (aim ≤ 200 lines each). If evidence is verbose, store it externally in repo paths and reference under `Evidence`.

## Security & Compliance
- Do not include secrets, tokens, or full credential strings in any section or snippet.
- Redact sensitive values in logs with `****`.

