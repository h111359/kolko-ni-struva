# Prompt: aib-refresh-context

## Goal:
Produce or modify `.aib_memory/context.md` — a unified, structured synthesis of all workspace-specific product knowledge, structured according to `.aib_brain/conventions/context-convention.md`. This prompt also serves the reverse-engineering use case: when no prior `context.md` content exists, the workspace scan in Phase 2 becomes the primary synthesis source.

## Workspace instructions pre-read (MUST):
- Read `.aib_memory/instructions.md`. If the file exists and is non-empty, treat its content as persistent workspace-level instructions that MUST be observed throughout this prompt's execution. If the file is absent or empty, proceed normally.

## Core requirements (normative):
- MUST be workspace/tool/model/vendor agnostic.
- MUST handle large repos (chunked inventory + selective deep reads).
- MUST produce full content replacement of `.aib_memory/context.md` on each execution (not append, prepend, or partially edit).
- Re-execution with unchanged sources MUST produce semantically equivalent output.

## Non-goals:
- Do not modify any existing file in the workspace other than `.aib_memory/context.md`.
- Do not explore or read `.aib_brain/` folder contents except `.aib_brain/conventions/context-convention.md` and tool script invocations listed in this prompt.
- Do not explore `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.git/`.
- Do not remove content in `.aib_memory\context.md` unless you find evidence it is incorrect.

---

## Phase 1 — Preflight

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 1 started" --general`.

1. Read `.aib_brain/conventions/context-convention.md`. This is the authoritative source for the required section structure, content guidance, formatting rules, and quality gates for `context.md`.
2. If `.aib_memory/instructions.md` lists additional file paths the developer wants AIB to treat as supplementary product-doc inputs, collect those paths into the supplementary read set. Otherwise the supplementary read set is empty.
3. If the supplementary read set is not empty, read every file in the supplementary read set.
4. **Format detection:** Read `.aib_memory/context.md` (if it exists). Determine whether the file is in the current format by checking for the presence of the section heading.
   - If the file has the current section format as per `.aib_brain/conventions/context-convention.md`; use existing statements as baseline and update based on workspace evidence.
   - If the file does not have the current section format as per `.aib_brain/conventions/context-convention.md`; generate fresh content in the format of the convention.
   - If the file does not exist: proceed with full generation in the format of the convention.
5. **Extension relevance check:** For each Reference entry in `## References` of the existing `context.md`, read the `Summary:` line and use AI semantic relevance judgement to determine whether the extension is relevant to the current refresh goal. If relevant, read the full extension file at the `Location:` path and treat its content as additional input context alongside `context.md`.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 1 complete" --general`.

---

## Phase 2 — Supplementary read (workspace sources)

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 2 started" --general`.

In addition to the supplementary read set, this phase is the **primary synthesis source** (reverse-engineering mode). Apply the traceability and evidence-collection rules from the Reverse-Engineering Evidence Collection section below.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 2 complete" --general`.

1. Build a deterministic file inventory of the workspace root.
   - Include all files and directories.
   - Exclude these directories and their contents:
     - `.aib_brain/`
     - `.aib_memory/`
     - `.venv/`
     - `venv/`
     - `node_modules/`
     - `__pycache__/`
     - `.pytest_cache/`
     - `.mypy_cache/`
     - `.git/`
   - For directories containing three or more items that share a repeating naming pattern, apply the grouping rule defined in `context-convention.md` Section 12: provide a single summary bullet for the directory rather than listing individual items.
   - Sort by workspace-relative path ascending.
2. Read `README.md` (if it exists at workspace root).
3. Read script and program code files (purpose, inputs, outputs per script).
4. Read test files (test coverage areas, key test targets).
5. Read root configuration files (e.g., `.gitignore`, `pyproject.toml`, `setup.cfg`, `requirements.txt`, `package.json`) if they exist.

---

## Reverse-Engineering Evidence Collection

Apply the following additional evidence-collection rules during Phase 2.

### A. Deterministic file inventory

- MUST produce (internally, for reasoning) a deterministic inventory of workspace files:
- Sort by workspace-relative path ascending.

Notes for large repos:
- Prefer a two-pass approach:
  1. Fast inventory from metadata only.
  2. Deep reads only for a small set of relevant files per section.
- If context is limited, summarize and defer deep reads; never invent content.

- Use `.aib_brain/tools/file-inventory.py` to emit a JSONL inventory and compare with the existing list in `.aib_memory/context.md`

### B. Traceability requirement

For each mandatory section of `.aib_memory/context.md` synthesized from workspace sources:
- Provide explicit traceability references (source path and brief note of what was found).
- Mark claims that cannot be directly supported from workspace evidence as assumptions with a confidence level.
- Prefer leaving a stub notice over guessing.

### C. Evidence-backed synthesis rules

- Keep content consistent with workspace evidence.
- Prefer concise, deterministic wording.
- Do NOT reproduce verbatim content from source files. Summarize and synthesize.
- If a section has no workspace evidence, write the stub notice exactly as specified in `context-convention.md`.

---

## Phase 3 — Cross-Reference

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 3 started" --general`.

1. Read files under `tests/` to identify test coverage areas and key test targets that should inform context.md content.
2. Read any script files under `scripts/` that were not covered in Phase 2.
3. Note any additional architectural facts, constraints, or decisions discovered in this phase that are relevant to the 6 sections of context.md.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 3 complete" --general`.

---

## Phase 4 — Synthesis

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 4 started" --general`.

Produce or modify the content of `.aib_memory/context.md` as follows.

Apply the formatting rules defined in the `## Formatting Rules` section of `.aib_brain/conventions/context-convention.md`.

Use atomic statement format for each bullet line as specified in context-convention.md.

### Content currency rule

All content MUST reflect the current state of the product only.
MUST NOT include version history annotations such as "introduced in vX.Y.Z", "added in vX", "deprecated as of vX", "removed as of", or "(Deprecated)" labels.
Describe what currently exists and is active; historical change information belongs in changelogs and version logs, not in context.md.

### Non-repeating information rule

CLI argument names and function signatures MUST NOT be included in `context.md` because they are derivable by reading the tool scripts directly. High-level tool purpose, behaviour, and architectural facts are retained. All other facts may still be included.

### 4.1 Context Convention Reference

Refer to the valid sections definition in `context-convention.md` for the required section structure, content guidance, formatting rules, and quality gates.

### 4.2 Six-Section Synthesis

Write the content of `.aib_memory/context.md` following the convention defined in `context-convention.md`.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 4 complete" --general`.

---

## Phase 5 — Enrichment Verification Passes

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 5 started" --general`.

After synthesis, execute the following enrichment passes to ensure completeness:

### Pass 1 — Analysis decisions verification

Read `.aib_memory/analysis-<request_id>.md` for the active request (if one is active). Verify all decisions from the Decision Register section are reflected as statements in the appropriate section of the current 7-section `context.md` format (Product, Concepts, Requirements, Solution, File Structure, References, or Issues). Add missing statements.

### Pass 2 — Plan results verification

Read `.aib_memory/plan-<request_id>.md` for the active request (if it exists). Verify all completed task outcomes and architectural decisions from the plan are reflected in context statements. Add missing statements.

### Pass 3 — Modified files verification

Compare workspace file state against context statements. Verify that any new files, removed files, or renamed files since the last context generation are reflected in `## File Structure`. Verify that significant functional changes to existing files are reflected as updated or new statements in the appropriate sections.

### Pass 4 — [PLANNED] entry re-evaluation

For each `[PLANNED]` entry currently present in `context.md` (across all sections: Product, Concepts, Requirements, Solution), evaluate whether the feature described by that entry is now present in the current workspace via workspace scan:
- If the feature is confirmed realized (workspace evidence shows the feature is implemented), remove the `[PLANNED]` prefix from the statement — the entry transitions to a plain untagged statement.
- If the feature cannot be confirmed as realized, preserve the `[PLANNED]` entry verbatim in the refreshed `context.md`.

Do NOT remove `[PLANNED]` entries automatically; only transition those entries where workspace evidence confirms the described feature is present.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 5 complete" --general`.

---

## Phase 6 — Write output

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 6 started" --general`.

1. **Statement uniqueness verification pass (MUST complete before writing):** Scan all generated atomic statements in Section 2. For each statement, extract the index (area+type+hash). If any duplicate index is found, resolve by adjusting the statement text (which changes the hash) or removing the duplicate. Only after zero uniqueness violations remain may you proceed to write the file.
2. Write the complete synthesized content to `.aib_memory/context.md`, replacing any existing content entirely.
3. Do NOT append — full replacement on every execution.
4. Do NOT modify any other file.
5. Confirm at the very end of the conversation with the text "--- I am done with the context update ---" that all your activities are finished

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 6 complete" --general`.

---

## Phase 7 — Post-write Validation

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 7 started" --general`.

1. Re-read `.aib_memory/context.md` as written.
2. Extract all level-2 headings from the document in order.
3. Compare the extracted list against the mandatory section list from `.aib_brain/conventions/context-convention.md` (required headings: `## Product`, `## Concepts`, `## Requirements`, `## Solution`, `## File Structure` — in that order; `## References` is optional).
4. If any heading is non-compliant — wrong name, wrong order, or missing — identify each correction needed.
5. For each non-compliant section, rewrite it (heading and content) to match the convention; do not alter compliant sections.
6. Verify all statements in Product, Concepts, and Solution sections use plain-bullet format, and all statements in Requirements use modality-prefixed format.
7. After all corrections are applied, confirm the written file is compliant.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 7 complete" --general`.

---

## Phase 8 — Format Verification

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 8 started" --general`.

1. Invoke `python .aib_brain/tools/verify-context.py --workspace .` to run automated format checks against the written `context.md`.
2. If the script exits with code 0 (all checks pass), proceed to completion.
3. If the script exits with code 1 (one or more checks fail), review the reported failures and correct the deviations in `context.md`. Re-run the verification script until all checks pass.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 8 complete" --general`.

---

## Phase 9 — Update Writable Extensions

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 9 started" --general`.

After `context.md` is written and verified, for every Reference entry in `## References` that contains `Update: true`:
1. Read the extension file at the registered `Location:` path.
2. Update its content to reflect the current workspace scan findings relevant to the topics covered by that extension's `Summary:`.
3. Write the updated extension file back to the same path.
4. Log each updated extension via `log-entry.py --workspace . --message "Extension updated: <location>"`.

If no Reference entries have `Update: true`, skip this phase.

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-refresh-context Phase 9 complete" --general`.

---

## Safety

- The only permitted write target is `.aib_memory/context.md`.
- Do NOT edit any existing workspace file.
- Do NOT create files other than `.aib_memory/context.md`.
- Do NOT explore or read `.aib_brain/` contents except `.aib_brain/conventions/context-convention.md`.
- Do NOT install packages, create virtual environments, or run tools.
- MAY read `.aib_memory/analysis-<request_id>.md` and `.aib_memory/plan-<request_id>.md` for the active request only (needed for enrichment passes in Phase 5 enrichment verification passes).
- MUST NOT read analysis or plan files for Closed requests.

---

## Done criteria

- `.aib_memory/context.md` exists and is valid Markdown.
- It contains the preamble as defined in `context-convention.md`, including the auto-generation notice and timestamp.
- It contains the 5 mandatory sections in the order specified by `context-convention.md` (`## Product`, `## Concepts`, `## Requirements`, `## Solution`, `## File Structure`), using the exact headings.
- All sections contain appropriate atomic statements in the format required by context-convention.md.
- `## File Structure` lists all non-excluded workspace files in the required indented-tree format.
- No content is derived from excluded directories.
- No files other than `.aib_memory/context.md` were modified.
