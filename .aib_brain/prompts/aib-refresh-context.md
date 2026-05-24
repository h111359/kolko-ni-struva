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

1. Read `.aib_brain/conventions/context-convention.md`. This is the authoritative source for the required section structure, content guidance, formatting rules, and quality gates for `context.md`.
2. If `.aib_memory/instructions.md` lists additional file paths the developer wants AIB to treat as supplementary product-doc inputs, collect those paths into the supplementary read set. Otherwise the supplementary read set is empty.
3. If the supplementary read set is not empty, read every file in the supplementary read set.

---

## Phase 2 — Supplementary read (workspace sources)

In addition to the supplementary read set, this phase is the **primary synthesis source** (reverse-engineering mode). Apply the traceability and evidence-collection rules from the Reverse-Engineering Evidence Collection section below.

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
3. Read files under `scripts/` (purpose, inputs, outputs per script).
4. Read files under `tests/` (test coverage areas, key test targets).
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

## Phase 4 — Synthesis

Produce or modify the content of `.aib_memory/context.md` as follows.

Apply the formatting rules defined in the `## Formatting Rules` section of `.aib_brain/conventions/context-convention.md`.

### Content currency rule

All content MUST reflect the current state of the product only.
MUST NOT include version history annotations such as "introduced in vX.Y.Z", "added in vX", "deprecated as of vX", "removed as of", or "(Deprecated)" labels.
Glossary entries for deprecated or removed concepts MUST NOT be included; only currently active concepts and terms belong in the glossary.
Describe what currently exists and is active; historical change information belongs in changelogs and version logs, not in context.md.

### 4.1 Preamble

Write the preamble exactly as specified in the `context-convention.md` Preamble Format section. Replace the timestamp placeholder with the actual generation timestamp in local project time.

### 4.2 Mandatory sections

Write all mandatory sections in the exact order and with the exact headings defined in `context-convention.md`. For each section:

- Synthesize relevant content from all populated supplementary files (if any) and workspace sources.
- Apply the content guidance defined for the section in `context-convention.md`.
- Include traceability references (e.g., `per ARCH-01`) where applicable — plain text only, no hyperlinks.
- If no source content is available for a section, write the stub notice exactly as specified in `context-convention.md`.
- Do NOT reproduce verbatim content from source files. Summarize and synthesize.

When mapping documentation to sections:
- Use all populated supplementary content as source material. Map each document's content into the most relevant mandatory section(s) as defined in `context-convention.md`.
- A single supplementary document may contribute to multiple sections.
- A single mandatory section may draw from multiple supplementary documents and workspace sources.

### 4.3 Workspace file inventory

Write the final mandatory section (`## Workspace File Inventory`) listing all non-excluded files and directories discovered in Phase 2. Follow the format defined in `context-convention.md` Section 12.

For each entry:

- **File entries:** Write `- \`path\` — description.` where description is one sentence derived from knowledge synthesized in earlier sections (Sections 1–11) or from direct file content read in Phase 2.

- **Directory entries:** Write `- \`dir/\` — description.` for every directory and subdirectory present in the workspace (using a trailing slash). Derive the description from the folder's evident role (e.g., contents and purpose inferred from earlier synthesis). Add a directory entry for every folder and subfolder; do not omit any directory that contains listed files.

- **Repetitive request artifact files** (`request.md`, `implementation.md`, `analysis.md` within `.aib_memory/requests/<request-folder>/`): use a formulaic description based on the request folder slug (e.g., "Request definition for <human-readable-slug>.", "Implementation log for <human-readable-slug>.", "Analysis artifact for <human-readable-slug>.").
- Sort all entries (files and directories together) ascending by path.

---

## Phase 5 — Write output

1. **Rule 16 verification pass (MUST complete before writing):** Scan every generated bullet item in the full synthesized content. For each bullet item, count the terminal sentence-ending marks (`.`, `!`, `?`). If any bullet item contains more than two terminal sentences, split it at sentence boundaries into two or more new bullet items, each beginning with `- ` and separated from adjacent bullets by one blank line (Rule 12). Repeat the scan until zero Rule 16 violations remain. Only after zero violations are confirmed in the complete synthesized content may you proceed to write the file.
2. Write the complete synthesized content to `.aib_memory/context.md`, replacing any existing content entirely.
3. Do NOT append — full replacement on every execution.
4. Do NOT modify any other file.
5. Confirm at the very end of the conversation with the text "--- I am done with the context update ---" that all your activities are finished

---

## Phase 6 — Post-write Validation

1. Re-read `.aib_memory/context.md` as written.
2. Extract all level-2 headings from the document in order.
3. Compare the extracted list against the mandatory section list from `.aib_brain/conventions/context-convention.md` (exact heading text and order).
4. If any heading is non-compliant — wrong name, wrong order, or missing — identify each correction needed.
5. For each non-compliant section, rewrite it (heading and content) to match the convention; do not alter compliant sections.
6. After all corrections are applied, confirm the written file is compliant.

---

## Safety

- The only permitted write target is `.aib_memory/context.md`.
- Do NOT edit any existing workspace file.
- Do NOT create files other than `.aib_memory/context.md`.
- Do NOT explore or read `.aib_brain/` contents except `.aib_brain/conventions/context-convention.md`.
- Do NOT install packages, create virtual environments, or run tools.

---

## Done criteria

- `.aib_memory/context.md` exists and is valid Markdown.
- It contains the preamble as defined in `context-convention.md`, including the auto-generation notice and timestamp.
- It contains all mandatory sections in the order specified by `context-convention.md`, using the exact headings.
- Populated sections have concise, non-empty key-fact summaries sourced from workspace content.
- Sections with no available source content contain the stub notice as defined in `context-convention.md`.
- Workspace source artifacts (`scripts/`, `tests/`) are synthesized under the applicable mandatory sections.
- No content is derived from excluded directories.
- No files other than `.aib_memory/context.md` were modified.
