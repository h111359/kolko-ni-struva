# Prompt: aib-analyze

## 1. Objective

Generate `.aib_memory/analysis-<request_id>.md` for the resolved active request, and update `.aib_memory/plan-<request_id>.md` with implementation-relevant sections (`## Plan` and `## Decisions`).

`<request_id>` is the active request ID resolved in Preflight (e.g. `R-20260509-2313`).

> **Authoritative invariants for this prompt:**
> - MUST follow the section order and execution sequence defined below without reordering.
> - MUST NOT introduce behaviors not explicitly specified in this prompt.
> - MUST NOT skip or merge any numbered step.

---

## Execution Model Summary

This prompt operates as a deterministic multi-phase workflow. Each phase is strictly ordered and must complete before the next begins.

1. **Preflight** — Resolve register state, read inputs, apply any answered Q&A, apply amendments, and load context.
2. **Branch handling** — Auto-create request (when no Active request exists) OR proceed with existing Active request.
3. **Analysis generation** — Produce `analysis-<request_id>.md` with 5 mandatory sections.
4. **Request enrichment** — Update `plan-<request_id>.md` with Plan and Decisions.
5. **Q-block generation** (optional) — Write AI-generated questions to `input.md ## Questions` when genuine decision forks exist.
6. **Finalization** — Archive `input.md` (conditional on non-stub state) and reset to seed template via `finalize-input.py`.

---

## Global Constraints

These constraints apply throughout the entire prompt execution. Individual sections reference them by GC identifier rather than restating them.

- **GC-01 — No archive reads:** `inputs/input-archive-*.md` files in request folders MUST NOT be read or referenced during any phase of this prompt.
  
- **GC-02 — Single input reset:** `input.md` MUST be reset exactly once per run. The reset is performed either by the Auto-Request Creation Branch (section 4.7, step 6) or by the Standard Flow Final Step (section 8). Never both. **Exception:** (a) When Q-blocks are written to `input.md ## Questions` during this run, the Standard Flow Final Step (section 8) MUST NOT execute — the reset is deferred so the developer can read and answer the Q-blocks before the next run. (b) When the Answer Application Sub-flow (section 4.8) halts because any Q-block is unanswered, the Standard Flow Final Step (section 8) MUST NOT execute and `input.md` MUST remain unchanged.
  
- **GC-03 — Q-blocks in first cycle only:** Q-blocks are generated only when this is the first analysis run for the active request (i.e., no answered Q-blocks exist in `input.md`). On re-run after answers, no new Q-blocks are generated.

- **GC-04 — Halt on missing mandatory files:** If any mandatory file listed in section 2.1 (Inputs) cannot be read, execution MUST HALT with an explicit error message identifying the missing file.

- **GC-05 — No partial writes on halt:** When execution halts due to any error condition, MUST NOT write any output files. The workspace state must remain unchanged.
  
- **GC-06 — No closed-request reads:** Files inside `.aib_memory/requests/<folder>/` that belong to a Closed request MUST NOT be read or referenced during any phase of this prompt. This covers all artifact types (request, analysis, implementation, input archives, and any other file). A request folder belongs to a Closed request when its `state` in `requests_register.md` is `Closed`. If in doubt, treat the folder as Closed.
  
- **GC-07 — No implementation writes:** This prompt MUST NOT create, edit, or delete any file outside `.aib_memory/` except for the tool script invocations explicitly authorized in sections 4.7 (step 3 and step 5) and 8.2. Source code, test files, CI workflow files, scripts, and all non-AIB-memory artifacts are strictly out of bounds. Discovering that a fix is needed does NOT authorize applying it.

---

## Failure Handling

> **Trigger:** Any of the conditions below MUST cause an immediate execution HALT.
> **Rule:** On halt, output the specified literal error message and MUST NOT write any output files (See GC-05).

| Condition | Error message |
| --- | --- |
| A mandatory input file (section 2.1) cannot be read | `ERROR: Cannot read mandatory file <path>. Execution halted.` |
| A convention file (`.aib_brain/conventions/*.md`) cannot be read | `ERROR: Cannot read convention file <path>. Execution halted.` |
| A tool script (`.aib_brain/tools/*.py`) exits with a non-zero code | `ERROR: Tool script <script> failed with exit code <N>. Execution halted.` |
| Any write attempted to a file outside .aib_memory not covered by GC-07 exceptions | `ERROR: Unauthorized write to <path> blocked. aib-analyze.md is a reasoning-only prompt. Use aib-implement.md to apply changes.` |
| Answer Application Sub-flow detects one or more unanswered Q-blocks | `Note: <N> of <M> questions in input.md are unanswered. Answer all questions before re-running analysis. Execution halted.` |

---

## 2. Inputs & External Dependencies

### 2.1 Inputs

| Source | Description |
| --- | --- |
| `.aib_memory/plan-<request_id>.md` | Active plan (authoritative scope source) |
| `.aib_memory/context.md` | Workspace product context (optional; graceful when absent) |
| `.aib_memory/input.md` | Developer input; Q-blocks and options are read here |
| `.aib_memory/attachments/` | Supplementary input files (text read; binary acknowledged by name) |
| `.aib_memory/instructions.md` | Persistent workspace-level directives |
| Additional files listed in `instructions.md` | Developer-flagged context files |

### 2.2 External Dependencies

| Item | Location | Purpose |
| --- | --- | --- |
| `create-request.py` | `.aib_brain/tools/create-request.py` | Creates request folder and register entry (Auto-Request Branch only) |
| `finalize-input.py` | `.aib_brain/tools/finalize-input.py` | Archives `input.md`, moves attachments, resets `input.md` to seed template |
| `analysis-convention.md` | `.aib_brain/conventions/analysis-convention.md` | Mandatory structure for the analysis document |
| `plan-convention.md` | `.aib_brain/conventions/plan-convention.md` | Mandatory structure for `plan.md` |
| `requirements-analysis-convention.md` | `.aib_brain/conventions/requirements-analysis-convention.md` | Requirements gate checklist applied during analysis to verify request completeness before WBS generation |

### 2.3 Outputs

| Artifact | Location | Description |
| --- | --- | --- |
| `analysis-<request_id>.md` | `.aib_memory/` root (active phase) | Full analysis document; set of mandatory sections |
| `plan-<request_id>.md` (updated) | `.aib_memory/` root (active phase) | Updated with Plan and Decisions sections |
| `input.md` (updated) | `.aib_memory/input.md` | Q-blocks written to `## Questions` (when applicable); reset to seed template at end of run **only when no Q-blocks were generated** — reset is deferred when Q-blocks are present so the developer can answer them |

---

## 3. Workspace Instructions Pre-read (MUST)

Read `.aib_memory/instructions.md`. If the file exists and is non-empty, treat its content as persistent workspace-level instructions that MUST be observed throughout this prompt's execution. If the file is absent or empty, proceed normally.

---

## 4. Mandatory Preflight

> **MUST execute every step in the order shown.** Each step is numbered and must complete before the next begins. Two labeled sub-flows interrupt the linear sequence when their trigger conditions hold:
> - **Auto-Request Creation Branch** — triggered after step 1 when zero Active rows exist.
> - **Answer Application Sub-flow** — triggered inside step 5 when `input.md` contains a `## Questions` section with one or more Q-blocks.

### Phase 1 — State Resolution

_Covers steps 1–2 (sections 4.1–4.2): resolve the register state and identify the active request._

### 4.1 Step 1 — Resolve register state

1. Read `.aib_memory/requests_register.md` and count rows with `state = Active`.
2. Branch on the count:
   - **Exactly one Active row** → record the resolved request and continue to step 2 (standard analysis flow).
   - **Zero Active rows** → enter the **Auto-Request Creation Branch** (section 4.7) and do not proceed to steps 2–9 until the branch hands control back.
   - **More than one Active row** → output the literal message **"ERROR: Register inconsistency — multiple Active requests found. Execution halted. Fix requests_register.md before running analysis."** and HALT. MUST NOT proceed to any subsequent step. MUST NOT write any output files.

### 4.2 Step 2 — Resolve active request

Use the single Active row identified in step 1 as the resolved request. The resolved `<request_id>` MUST be used everywhere in this run.

### Phase 2 — Input Acquisition

_Covers steps 3–5 (sections 4.3–4.5): read the active request file, attachments, and input options. The Answer Application Sub-flow (Phase 3, section 4.8) is triggered from within this phase at step 5 when Q-blocks are detected._

### 4.3 Step 3 — Read active request file

Read the active `plan-<request_id>.md` from `.aib_memory/plan-<request_id>.md`. If the file is absent, check `.aib_memory/input.md` for the presence of a `## Questions` section. If a `## Questions` section exists, set a **deferred-creation** flag and continue without reading `plan.md` (it will be created by the Answer Application Sub-flow, section 4.8). If `plan.md` is absent and no `## Questions` section exists in `input.md`, halt with the GC-04 error message.

### 4.4 Step 4 — Read attachments (MUST execute before toggle detection)

1. Recursively walk all files in `.aib_memory/attachments/` (including files in subdirectories at any depth).
2. For each file found (excluding `.gitkeep`):
   - If the file is text-readable: read its full content and treat it as additional input context alongside `input.md`.
   - If the file is binary (not text-readable): note the filename and acknowledge its presence without reading content.
3. Files in `attachments/` are considered part of the input even if not referenced in `input.md`.
4. If the folder is absent or empty, continue normally with no error.

### 4.5 Step 5 — Read input options and Q&A re-run check (MUST execute before any further steps)

1. Read the `## Options` section of `input.md` (`.aib_memory/input.md`).
2. **Q&A re-run check:** Check if `input.md` contains a `## Questions` section with one or more Q-blocks.
   - If **yes**, enter the **Answer Application Sub-flow** (section 4.8) before proceeding with steps 6–9.
   - If **no**, continue directly to step 6.

### Phase 3 — State Mutation (Q&A and Amendments)

_Executes in two contexts: (a) triggered from Phase 2 step 5 via the Answer Application Sub-flow (section 4.8) when Q-blocks are present, and (b) as step 9 below (amendment detection after context enrichment)._

### Phase 4 — Context Enrichment

_Opens with a brownfield context check; then covers steps 6–9 (within section 4.6): context read, additional developer-flagged file reads, convention reads, and amendments._

**Brownfield context check (executes at the start of this phase):**

 1. Check whether `.aib_memory/context.md` is absent or empty (contains only whitespace after trimming) or has less than 50 words.
 2. If **absent or empty**: execute `.aib_brain/prompts/aib-refresh-context.md` to populate `context.md`. After execution completes, continue to step 6.
 3. If **present and non-empty**: continue directly to step 6.

 **Non-recursion guarantee:** `aib-refresh-context.md` does NOT invoke `aib-analyze.md`. No recursive execution loop can occur.

### 4.6 Steps 6–9 — Context, additional reads, conventions, amendments

6. Read `.aib_memory/context.md`. If the file is absent or empty, continue normally with no error; otherwise treat its content as the unified workspace product context for this analysis run.
7. If `.aib_memory/instructions.md` lists additional file paths the developer has flagged for AIB to read, read each of those files before drafting analysis. Otherwise skip this step.
8. Read all three convention files: `.aib_brain/conventions/analysis-convention.md`, `.aib_brain/conventions/plan-convention.md`, and `.aib_brain/conventions/requirements-analysis-convention.md`.
9. Detect `## Amend Request` section in `plan.md`. If present and non-empty:
   a. Apply its free-text instructions to the relevant mandatory sections (`## Goal`, `## Constraints`, `## Success criteria`) of `plan.md`.
   b. Clear the content of `## Amend Request` from `plan.md` after applying.

---

### 4.7 Auto-Request Creation Branch

**Triggered when:** zero Active rows found in Preflight step 1.

> **Constraint:** This branch is the only place where `create-request.py` is invoked from `aib-analyze.md`. After completing the branch, control returns to step 6 of the standard flow (NOT step 1).

**Procedure:**

1. Read `.aib_memory/input.md`.
   - If `## Input` section is empty or contains only whitespace: output the literal message **"ERROR: No active request and input.md is empty. Add content to ## Input before running analysis."** and HALT. Do NOT proceed.
2. Derive a request title from the `## Input` content (first meaningful sentence or noun phrase, ≤ 60 characters).
3. Invoke `.aib_brain/tools/create-request.py`:
   ```
   python .aib_brain/tools/create-request.py --workspace . --title "<derived-title>"
   ```
4. Read `.aib_memory/requests_register.md` to resolve the newly created request folder and `<request_id>`.
5. Archive the current `input.md` content and move attachments by invoking `finalize-input.py`:
   ```
   python .aib_brain/tools/finalize-input.py --workspace . --request-id <request_id>
   ```
   where `<request_id>` is the newly created request ID resolved in step 4. The script:
   - archives `input.md`,
   - moves all non-`.gitkeep` attachment files from `.aib_memory/attachments/` to `<request-folder>/inputs/`,
   - resets `input.md` to the seed template with the request ID injected.

   After the script completes, `.aib_memory/attachments/` MUST contain only `.gitkeep`.
6. Resume the standard analysis flow at Preflight step 6 (Context read).
   - After resuming, if the analysis generates Q-blocks, `plan-<request_id>.md` MUST NOT be written in this pass — it remains absent. If the analysis generates no Q-blocks, `plan-<request_id>.md` is written as part of Part 2 updates (sections 7.1–7.2) during this same pass. All 4 mandatory sections MUST be present when the file is first written, whether in the no-Q-blocks first pass or in the Answer Application Sub-flow re-run.
   - **MUST NOT** reset `input.md` again during this triggered standard flow — the reset was already performed by `finalize-input.py` in step 5.
   - **MUST NOT** execute the Standard Flow Final Step's `finalize-input.py` invocation (section 8) for this triggered run.

### 4.8 Answer Application Sub-flow

**Triggered when:** `## Questions` section is present in `input.md` (detected in Preflight step 5).

**Procedure:**

0. **All-answered pre-check:** Count the total number of Q-blocks in `input.md ## Questions` (M). Count the number of answered Q-blocks (N) — a Q-block is answered when at least one checkbox is marked `[x]` OR the `> Answer:` line has non-empty text after the colon. If N < M: output `Note: <N> of <M> questions in input.md are unanswered. Answer all questions before re-running analysis. Execution halted.` and HALT. MUST NOT modify `input.md`, `plan.md`, or any other file. MUST NOT continue to any subsequent step of this sub-flow or to the standard analysis flow.

1. Before applying Q-block answers to `plan.md` sections, check whether `.aib_memory/plan-<request_id>.md` exists. If the file is absent (deferred-creation state), create it from scratch using the following sources: (1) the `## Input Interpretation` section from the existing `.aib_memory/analysis-<request_id>.md`; (2) the Q&A answers from the `## Questions` section of `input.md`; (3) the request title from `requests_register.md`. All 4 mandatory sections MUST be present in the newly created file. Sections 3–4 (`## Success criteria`, `## Plan`) MAY be empty here — they are populated during the standard analysis output generation (Part 2, sections 7.1–7.2) that follows the Answer Application Sub-flow.

2. For each Q-block in `## Questions`: apply the chosen option (the checked `[x]` option or the non-empty `> Answer:` text) to the relevant `plan.md` section (`## Goal`, `## Constraints`, etc.) based on what the answer addresses. If the target section is ambiguous, apply to `## Goal`. Append a resolved entry to `plan.md` `## Decisions` in the format `**Q<nnn>:** <question text> → **Chosen:** <chosen option text>`.
3. After all Q-blocks are processed, remove the entire `## Questions` section from `input.md`.
4. Continue with the normal analysis flow (steps 6–9 of Preflight, then output generation including the full WBS plan). The Plan deferral rule (section 7.2) does NOT apply on this re-run — Q-blocks have been resolved and the full plan MUST be generated. No new Q-blocks are generated when re-running after answers — all ambiguities were resolved in the prior run.

---

## 5. Analysis Requirements

> **Invariants:**
> - MUST follow required headings exactly as defined in `analysis-convention.md`.
> - MUST keep statements concrete and traceable to request scope.
> - MUST NOT ask the user for information you can collect yourself from the workspace — review files and search for answers first.
> - MUST NOT ask the user for information you can find on the Internet or via available tools or MCP — research yourself before raising user-facing questions.
> - MUST explicitly list risks in the analysis.
> - If information is insufficient, MUST make a research-based assumption and record it in the relevant Plan task's Risk Notes in `plan.md`.
> - The analysis document is a reasoning artifact only; it is NOT an implementation driver.
> - `inputs/input-archive-*.md` files in request folders MUST NOT be read or referenced by this prompt beyond archiving.
> - After reading `requirements-analysis-convention.md` (step 8), evaluate every mandatory checklist item against the active request (`plan-<request_id>.md`) and `input.md`. Surface the gate evaluation — item-by-item status, any unmet mandatory items, and any identified gaps — in the `## Research Results` section of the analysis document under a **Requirements Gate Evaluation** sub-heading. If any mandatory item cannot be satisfied by a reasonable documented assumption, tag the gap `ask` in the Decision Points section and generate a corresponding Q-block.

---

## 6. Output Contract — Part 1: Analysis Document

### 6.1 File placement and replacement

- Full content replacement (overwrite) of `.aib_memory/analysis-<request_id>.md` (NOT inside the request subfolder — the active analysis lives at `.aib_memory/` root while the request is active, using the ID-suffixed filename). On every run — first pass or re-run — the file is written from scratch and ALL prior content is discarded. MUST NOT append to, prepend to, or partially edit the existing file. The fact that the prior analysis file was read during this run (e.g., to source ## Input Interpretation for the Answer Application Sub-flow) does NOT authorize retaining any of its content in the output.
- Must follow the section structure defined in `analysis-convention.md`.
- Always generated unless triggered from `aib-implement.md` (see Standard Flow Final Step note in section 8).

### 6.2 Generation Instructions for Mandatory Sections

**`## Overview`** — Produce this section with the following content: Request ID, Request title, and three level-3 sub-sections: `### Background` (sourced from the developer's `## Input` content, explaining why the change is needed), `### Scope` (listing impacted functional areas, components, domains, or documents), and `### Out of scope` (items intentionally excluded from the request). This section is for human review and auditability only; `implement` MUST NOT read or act on it. Fully replace on every re-run. Each sub-section MUST contain at least one sentence.

**`## Files Read During This Analysis Run`** — List every workspace file read during this analysis run as a bullet list of workspace-relative paths. Include files read during preflight (e.g., `requests_register.md`, `input.md`), convention files, and any files inspected during research. MUST NOT be empty.

**`## Input Interpretation`** — Always generated — present in every analysis run (first pass and re-run). Rewrite the developer's `## Input` content (as read from `input.md` during Preflight, or as understood from the active session context on re-run) in specification-grade prose using correct product terminology (roles, artifact names, workflow names as defined in `context.md`). Enrich with relevant external domain knowledge where it adds clarity. Write in third-person specification style. The section MUST be faithful to developer intent — it enriches but does not replace or reinterpret the developer's stated goal. The primary purpose of this section is to provide the Answer Application Sub-flow on re-run with a reliable, GC-01-compliant source for populating sections 1–2 of `plan-<request_id>.md` without requiring access to the archived `input.md`.

**`## Research Results`** — This is the primary AI reasoning artifact. Write it as a cohesive analytical document covering all of the following dimensions:

- **Workspace findings:** pattern-scan results — impacted components, cross-reference issues, relevant prior solutions found in the workspace.

- **Industry knowledge:** best practices and external benchmarking relevant to the request topic. At minimum three findings from established frameworks, open-source communities, or industry literature. For each finding: the practice, its source context, and an applicability assessment for this request.

- **AI Agent critique:** A holistic bullet-list review of all issues found in the request itself and in every workspace file read during this analysis run. This sub-section is NOT limited to the current request scope. Every issue encountered — regardless of whether it relates to the current request — MUST be listed as a bullet. Issue types to identify include but are not limited to: misalignment between files, logical inconsistencies, redundancies, misplaced content, unclear wording, broken cross-references, format drift, stale names, and other quality concerns. The goal is to function as an expert reviewer who reports every issue found, not just those relevant to the change being analyzed.

Do NOT embed external links. This section is for human review and auditability only — `implement` MUST NOT read or act on it.

**`## Implementation Alternatives`** — This section is the primary driver for Q-block generation. MUST be completed before any Q-block is written.

For each implementation decision fork identified in the request scope, write a named decision block. Each block must contain:

1. Identification of the specific task or step where the decision applies, plus an explanation of why the alternatives exist.

2. Two or more named alternative approaches, each with: a one-sentence description, key trade-offs, and expected codebase impact.

3. Tag and resolution per section 7.3.2 rules:
   - Tag `ask` — a Q-block MUST be raised. The AI MUST NOT express a preference or steer the developer — present options neutrally.
   - Tag `resolve-autonomously` — ONLY when the developer's own `input.md ## Input` text OR a named, specific section of a workspace convention file explicitly and unambiguously resolves the fork. The rationale MUST quote or cite the exact source text and file path. External benchmarking, industry best practices, and AI judgment are NOT valid justifications. When in doubt, tag `ask`.

Produce a **`### Decision Points`** section using heading/sub-heading list format — one `#### Fork: <name>` level-4 heading per fork, with bullet list items for Tag and Rationale/Resolution.

If no decision forks are identified, include a single entry documenting that fact.

### 6.3 (Reserved)

Section 6.3 is reserved; `## Request Context` has been merged into `## Overview` (section 6.2).

---

## 7. Output Contract — Part 2: `plan.md` Updates

After generating the analysis, update `.aib_memory/plan-<request_id>.md` by appending or replacing the following optional sections.

> **Invariant:** Add a section only when it has content; never add an empty shell section.

### 7.1 Section: `## Plan`

> **Plan deferral rule (Option A):** If Q-blocks are written to `input.md ## Questions` during this run, `## Plan` MUST be set to the following stub and MUST NOT contain a WBS:
> ```
> *Plan deferred — pending Q&A. Re-run analysis after answering questions in `input.md`.*
> ```
> The full WBS is generated only on the re-run when the Answer Application Sub-flow (section 4.8) has processed all answers — i.e., when no `## Questions` section is present in `input.md` at Preflight step 5. The 4-section plan structure (Goal, Constraints, Success criteria, Plan) MUST always be fully present when the file is written.

- Generate a Work Breakdown Structure with numbered tasks for this iteration.
- Each task MUST use this schema:
  ```
  ### Task <N>: <Task Name>

  #### Intent
  <single-sentence goal>

  #### Outputs
  <artifacts produced or changed; file paths or product components>

  #### Procedure
  <step 1>

  <step 2>

  <...each step on its own paragraph, separated by one blank line; each step MUST cite the exact file path it operates on>

  #### Done criteria
  <objective pass/fail checks>

  #### Dependencies
  <Task IDs or external>

  #### Risk notes
  <if any>
  ```

**Plan-level invariants:**

- Keep tasks vertically sliceable; each must produce at least one verifiable output.
- Target ≤ 12 tasks per iteration; keep each procedure to ≤ 6 steps unless strictly necessary.
- Every Procedure step MUST reference the exact file path it operates on. Steps that do not operate on a specific file (e.g., running a terminal command) MUST name the command and its expected output location.
- Every plan MUST include:
  - (a) a task defining automated test steps for the request scope (covering all testable Success Criteria defined in `plan.md`);
  - (b) a task to update `.aib_memory/context.md` and any other documentation files affected by the request, reflecting changes made and any discovered discrepancies. The documentation task MUST be planned using the same Procedure explicitness standard as code tasks: each documentation step MUST specify (1) the target file path, (2) what to change, and (3) an acceptance test.
- Pre-flight findings (cross-reference issues, missing information, factual inconsistencies, impacted files) MUST be redistributed into the relevant Plan task's `Risk Notes` field or raised as Q-blocks in `## Decisions` when user input is needed. Do NOT create separate top-level sections for these findings.
- Fully replace this section on every re-run (AI-generated; no user data).

### 7.2 Section: `## Decisions`

> **Note:** Q-blocks are NOT written to `plan.md ## Decisions`. They are written to `input.md ## Questions` instead (see Q-block Generation Rules in section 7.3).

- `## Decisions` records resolved Q&A entries — one entry per question that was asked to the developer and answered.
- Each entry uses the format: `**Q<nnn>:** <question text> → **Chosen:** <chosen option text>`.
- Entries are appended by `aib-analyze.md` when applying answered Q-blocks (Answer Application Sub-flow, section 4.8); they are never removed after being written.
- **Re-run rule:** append-only; never modify or remove existing entries.

### 7.3 Q-block Generation Rules

#### 7.3.1 Decision Identification

**Step 1 — Decision Fork Enumeration (MUST execute before any Q-block generation):**
Enumerate ALL implementation decision forks identified in the request scope. Record the complete enumeration in the **`### Decision Points`** section within `## Implementation Alternatives` of the analysis document. Tag each fork as `ask` or `resolve-autonomously` using the rules in section 7.3.2. Q-blocks are then generated only for `ask`-tagged forks.

#### 7.3.2 Decision Classification (strictly enforced)

**Step 2 — Classification rules:**

A fork MUST be tagged `resolve-autonomously` ONLY when ALL of the following hold:

1. The developer's own `input.md ## Input` text OR a named, specific section of a workspace convention file explicitly and unambiguously resolves it.
2. The cited source uses clear, explicit language — not inference, implication, or "spirit of" interpretation.
3. The rationale in the Decision Points section quotes or cites the exact source text and file path.

A fork MUST be tagged `ask` in every other case, including:

- When the answer seems "obvious" or follows "industry best practice" without a named workspace source explicitly stating so.
- When external literature, benchmarking findings, or AI judgment provide the only justification.
- When the answer is "strongly implied" but not explicitly stated.
- When in doubt.

The AI MUST NOT express a preference or steer the developer toward any option when tagging a fork `ask`.

#### 7.3.3 Q-block Generation

**Step 3 — Q-block generation for `ask`-tagged forks:**
For every fork tagged `ask` in the Decision Points section, generate one Q-block. Q-blocks MUST reference the alternative by name from the Implementation Alternatives section when applicable.

For `resolve-autonomously` forks: document the chosen resolution inline in the relevant `plan.md` section and record the rationale in the Decision Points section.

Do NOT raise Q-blocks for decisions with no meaningful implementation impact.

**Soft limit:** 9 Q-blocks per run. Alternatives-derived Q-blocks MUST NOT be suppressed to meet the soft limit.

**Minimum-questions handling:** If the developer has set a `Minimum questions:` value greater than 0 in `input.md ## Options`, generate at least that many Q-blocks. If fewer genuine decision points exist than the minimum, document the shortfall in the analysis but do NOT generate low-value filler questions.

**Q-block generation target — `input.md ## Questions`:**

- Q-blocks are written to a `## Questions` section appended to `input.md` (`.aib_memory/input.md`).
- If no Q-blocks are generated (no genuine multi-choice forks), do NOT write a `## Questions` section to `input.md`.
- One cycle of Q&A is assumed: after all questions in `input.md` are answered, the Answer Application Sub-flow (Preflight step 5 / section 4.8) resolves them and no new Q-blocks are generated on re-run.

**Q-block format:**

- Each question block:
  ```
  **Q<nnn>**: <question text>
  > **Why this matters:** <one-sentence explanation of impact on implementation>
  - [ ] Option A: <text> *(recommended)*
  - [ ] Option B: <text>
  - [ ] Other: ___
  > Answer: 
  ```
- Use stable QIDs starting from Q001 (or the next available number if questions already exist).
- MUST include the `> **Why this matters:**` line immediately after the question text.
- MUST mark exactly one option per Q-block as `*(recommended)*`. The recommended option MUST be placed first in the list. All other options MUST NOT carry the marker.

---

## 8. Standard Flow Final Step

> **Trigger guard:** This section MUST execute when `aib-analyze.md` is invoked directly **AND no Q-blocks were written to `input.md ## Questions` during this run**. It MUST NOT execute when `aib-analyze.md` is triggered from `aib-implement.md`. It MUST NOT execute when Q-blocks were generated in this run — those Q-blocks must remain in `input.md` for the developer to answer before the next run. The Auto-Request Creation Branch (section 4.7) also suppresses this step (its step 6 already handled archive + move + reset).

### 8.1 Eligibility Check

1. After all Part 1 (analysis document) and Part 2 (`plan.md` updates) outputs are fully written and confirmed, evaluate whether `.aib_memory/input.md` is in a non-stub state.
   - **Definition of "non-stub":** the file content is not exactly equivalent to the seed template state after normalization of line endings and trailing whitespace. The seed template state is:
     ```
     ## Active request
     No active request

     ## Options
     - Minimum questions: 0

     ## Input

     ```
     (literal seed: `## Active request\nNo active request\n\n## Options\n- Minimum questions: 0\n\n## Input\n\n`)

### 8.2 Finalize Script Invocation

2. Invoke `finalize-input.py` to handle the archive + move + reset sequence atomically. The script will:
   - If non-stub: archive the pre-reset `input.md` content to `<request-folder>/inputs/input-archive-<YYYY-MM-DD_HH-MI-SS>.md` before resetting.
   - If stub-equivalent: skip archive creation for this standard-flow reset.
   - Move any remaining non-`.gitkeep` files from `.aib_memory/attachments/` to `<request-folder>/inputs/`.
   - Reset `input.md` to the seed template with the active request ID injected.
   ```
   python .aib_brain/tools/finalize-input.py --workspace . --request-id <request_id>
   ```
   where `<request_id>` is the active request ID. This MUST be the last action of the run.

### 8.3 Post-conditions

- The reset inherently clears any `## Questions` section that was present in `input.md`.
- No further file writes are permitted after this step.

---

## 9. Re-run Behaviour Summary (Navigational Reference)

> **Note:** This section is a navigational summary derived from sections 4–8. The authoritative rules live in those sections; this summary MUST NOT be read as authoritative if it conflicts with the body of the prompt.

- `## Plan` (in `plan.md`): stubbed when Q-blocks are generated on first run; fully generated on re-run after Q&A answers are applied (see section 7.1).
- `## Decisions` (in `plan.md`): append-only; entries are added by the Answer Application Sub-flow and never removed (see section 7.2).
- `## Questions` (in `input.md`): answered/unanswered Q-blocks are processed and the section is cleared by the Answer Application Sub-flow (Preflight step 5 / section 4.8) on re-run.
- Sections with no content: do not add (never create an empty shell section).

---

## 10. Context-Window Management

- If the aggregate size of required-read files exceeds 80% of available context, prioritize files by relevance to request scope, summarize the rest, and note which files were summarized in the output artifact.

---

## 11. Completion Confirmation

Confirm at the very end of the conversation (this should be the very last message to the user after all other generated response) with the text "--- I am done with the analysis ---" that all your activities are finished.

