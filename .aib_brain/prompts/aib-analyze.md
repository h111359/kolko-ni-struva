# Prompt: aib-analyze

## 1. Objective

Generate `.aib_memory/analysis-<request_id>.md` for the resolved active request, and update `.aib_memory/plan-<request_id>.md` with implementation-relevant sections (`## Plan` and `## Decisions`).

`<request_id>` is the active request ID resolved in Preflight (e.g. `R-20260509-2313`).

> **Authoritative invariants for this prompt:**
> - MUST follow the section order and execution sequence defined below without reordering.
> - MUST NOT introduce behaviors not explicitly specified in this prompt.
> - MUST NOT skip or merge any numbered step.

---

## 2. Execution Model Summary

This prompt operates as a deterministic 10-step linear workflow. Each step is strictly ordered and must complete before the next begins.

1. **Preflight + State Resolution** — Read workspace instructions, resolve register state, auto-create request if no Active request exists.
2. **Context check** — Verify `context.md` exists and is non-trivial; trigger `aib-refresh-context.md` if absent or empty.
3. **Read inputs** — Read `input.md` `## Input` section and attachments to detect user-provided instructions; read `## Options` to set [Questions-expected].
4. **Read Questions** — If `## Questions` section is present in `input.md` with unanswered Q-blocks, halt. If all answered, continue.
5. **Generate analysis** — Produce or overwrite `analysis-<request_id>.md` (full replace); identify all Decision Points; leave Requirements Gate Evaluation empty.
6. **Quality Check** — Evaluate every checklist item from `requirements-analysis-convention.md` against the analysis; record results under Requirements Gate Evaluation; tag unsatisfied items as `ask`.
7. **Archive Input and Reset** — Invoke `finalize-input.py` to archive `input.md`, move attachments, and reset `input.md` to the seed template.
8. **Q-block generation** — If Decision Points tagged `ask` exist, generate Q-blocks in `input.md ## Questions` and halt; otherwise continue.
9. **Plan generation** — Generate or recreate `plan-<request_id>.md` following `plan-convention.md` based on the completed analysis.
10. **Completion Confirmation** — Output the literal confirmation line `--- I am done with the analysis of <request_id> ---` as the final message.

The following internal variables are used for process control and are not persisted:

   * [Input-detected] — boolean; True when the user has provided input via the ## Input section in input.md and/or files in attachments. Indicates that change instructions from the user are present. Initially set to False.
  
   * [Questions-detected] - number; How many questions are found defined in  `input.md ## Questions` section. Initially set to 0

   * [Questions-answered] - number; How many questions have answer defined in  `input.md ## Questions` section. Initially set to 0
  
   * [Questions-expected] - number; How many questions need to be added in  `input.md ## Questions` section. Initially set to 0

---

## 3. Global Rules

### 3.1 Global Constraints

These constraints apply throughout the entire prompt execution. Individual sections reference them by GC identifier rather than restating them.

- **GC-01 — No archive reads:** `inputs/input-archive-*.md` files in request folders MUST NOT be read or referenced during any phase of this prompt.
  
- **GC-02 — Halt on missing mandatory files:** If any mandatory file listed in section 4.1 (Inputs) cannot be read, execution MUST HALT with an explicit error message identifying the missing file.

- **GC-03 — No partial writes on halt:** When execution halts due to any error condition, MUST NOT write any output files. The workspace state must remain unchanged.
  
- **GC-04 — No closed-request reads:** Files inside `.aib_memory/requests/<folder>/` that belong to a Closed request MUST NOT be read or referenced during any phase of this prompt. This covers all artifact types (request, analysis, implementation, input archives, and any other file). A request folder belongs to a Closed request when its `state` in `requests_register.md` is `Closed`. If in doubt, treat the folder as Closed.
  
- **GC-05 — No implementation writes:** This prompt MUST NOT create, edit, or delete any file outside `.aib_memory/` except for the tool script invocations explicitly authorized in **Appendix A — Auto-Request Creation Branch**. Source code, test files, CI workflow files, scripts, and all non-AIB-memory artifacts are strictly out of bounds. Discovering that a fix is needed does NOT authorize applying it.

### 3.2 Failure Handling

> **Trigger:** Any of the conditions below MUST cause an immediate execution HALT.
> **Rule:** On halt, output the specified literal error message and MUST NOT write any output files (See GC-03).

| Condition | Error message |
| --- | --- |
| A mandatory input file (section 4.1) cannot be read | `ERROR: Cannot read mandatory file <path>. Execution halted.` |
| A convention file (`.aib_brain/conventions/*.md`) cannot be read | `ERROR: Cannot read convention file <path>. Execution halted.` |
| A tool script (`.aib_brain/tools/*.py`) exits with a non-zero code | `ERROR: Tool script <script> failed with exit code <N>. Execution halted.` |
| Any write attempted to a file outside .aib_memory not covered by GD-05 exceptions | `ERROR: Unauthorized write to <path> blocked. aib-analyze.md is a reasoning-only prompt. Use aib-implement.md to apply changes.` |
| Answer Application Sub-flow detects one or more unanswered Q-blocks | `Note: <N> of <M> questions in input.md are unanswered. Answer all questions before re-running analysis. Execution halted.` |

---

## 4. Inputs, Outputs & Dependencies

### 4.1 Inputs

| Source | Description |
| --- | --- |
| `.aib_memory/context.md` | Workspace product context (optional; graceful when absent) |
| `.aib_memory/input.md` | Developer input; Q-blocks and options are read here |
| `.aib_memory/attachments/` | Supplementary input files (text read; binary acknowledged by name) |
| `.aib_memory/instructions.md` | Persistent workspace-level directives |
| Additional files listed in `instructions.md` | Developer-flagged context files |

### 4.2 External Dependencies

| Item | Location | Purpose |
| --- | --- | --- |
| `create-request.py` | `.aib_brain/tools/create-request.py` | Creates request folder and register entry (Auto-Request Branch only) |
| `finalize-input.py` | `.aib_brain/tools/finalize-input.py` | Archives `input.md`, moves attachments, resets `input.md` to seed template |
| `analysis-convention.md` | `.aib_brain/conventions/analysis-convention.md` | Mandatory structure for the analysis document |
| `plan-convention.md` | `.aib_brain/conventions/plan-convention.md` | Mandatory structure for `plan.md` |
| `requirements-analysis-convention.md` | `.aib_brain/conventions/requirements-analysis-convention.md` | Requirements gate checklist applied during analysis to verify request completeness before WBS generation |

### 4.3 Outputs

| Artifact | Location | Description |
| --- | --- | --- |
| `analysis-<request_id>.md` | `.aib_memory/` root (active phase) | Full analysis document; set of mandatory sections |
| `plan-<request_id>.md` (updated) | `.aib_memory/` root (active phase) | Updated with Plan and Decisions sections |
| `input.md` (updated) | `.aib_memory/input.md` | Q-blocks written to `## Questions` (when applicable); reset to seed template at end of run **only when no Q-blocks were generated** — reset is deferred when Q-blocks are present so the developer can answer them |

---

## 5. Execution Procedure

> **MUST execute every step in the order shown.** Each step is numbered and must complete before the next begins.

### S01. Step 1 — Preflight + State Resolution

S01.1. Read `.aib_memory/instructions.md`. If the file exists and is non-empty, treat its content as persistent workspace-level instructions that MUST be executed and observed throughout this prompt's execution. If the file is absent or empty, proceed normally.

S01.2. Read `.aib_memory/requests_register.md` and count rows with `state = Active`.

S01.3. Branch on the count:
   
   - **Exactly one Active row** → record the resolved request and continue to step 2.
  
   - **Zero Active rows** → execute **Appendix A — Auto-Request Creation Branch**, then resume at Step 2. 
  
   - **More than one Active row** → output the literal message **"ERROR: Register inconsistency — multiple Active requests found. Execution halted. Fix requests_register.md before running analysis."** and HALT. MUST NOT proceed to any subsequent step. MUST NOT write any output files.

S01.4. Use the single Active row as the resolved request. The resolved `<request_id>` MUST be used everywhere in this run.

S01.5. Output a short step-completion note in format: `[S01 done] Workspace instructions read and active request resolved.`


### S02. Step 2 — Context Check

S02.1. Check whether `.aib_memory/context.md` is absent or empty (contains only whitespace after trimming) or has less than 50 words.

S02.2. If **absent or empty**: execute `.aib_brain/prompts/aib-refresh-context.md` to populate `context.md`. After execution completes, continue to step S03.

S02.3. If **present and non-empty**: continue directly to step S03.

S02.4. Output a short step-completion note in format: `[S02 done] Context check complete; context.md is available.`


### S03. Step 3 — Read Inputs

S03.1. Read the section `## Input` in `input.md` file. This is what the user has requested. If non-empty - set [Input-detected] to True.

S03.2. Recursively walk all files in `.aib_memory/attachments/` (including files in subdirectories at any depth). Files in `attachments/` are considered part of the input even if not referenced in `input.md`. 
  - If the folder is absent or empty, continue normally. 
  - If instructions for actions found - set [Input-detected] to True. 
  
S03.3. For each file found (excluding `.gitkeep`): 
  - if text-readable, read its full content as additional input context; 
  - if binary, note the filename and acknowledge its presence. 

S03.4. Read the `## Options ` section of `.aib_memory/input.md` and determine the value of the `Minimum questions:` and write the value in [Questions-expected].

S03.5. Output a short step-completion note in format: `[S03 done] Inputs read; [Input-detected] and [Questions-expected] values set.`

### S04. Step 4 — Read Questions

1. Check if `input.md` contains a `## Questions` section with one or more Q-blocks.

2. If **no `## Questions` section exists**: continue directly to the next step.

3. If **`## Questions` section exists**: 
   
   - Count the total number of Q-blocks in `input.md ## Questions` and set the number in [Questions-detected]. 
  
   - Count the number of answered Q-blocks and write in [Questions-answered] the result. A Q-block is answered when at least one checkbox is marked `[x]` OR `Other:`  line has non-empty text after the colon OR the `- Answer:` line has non-empty text after the colon. 
  
   - If [Questions-answered] < [Questions-detected]: output `Note: <[Questions-answered]> of <[Questions-detected]> questions in input.md are unanswered. Answer all questions before re-running analysis. Execution halted.` and HALT. MUST NOT write any output files.

S04.4. Output a short step-completion note in format: `[S04 done] Questions section checked; all Q-blocks answered or no questions present.`


### S05. Step 5 — Generate Analysis

> **Rules:**
> - MUST follow required headings and sections structure exactly as defined in `.aib_brain/conventions/analysis-convention.md`.
> - MUST keep statements concrete and traceable to request scope.
> - MAY NOT ask the user for information you can collect yourself from the workspace — review files and search for answers first.
> - MUST seek for information you can find on the Internet or via available tools or MCP — research yourself before raising user-facing questions.
> - MUST explicitly list issues and risks found and write them in the analysis file.
> - If information is insufficient, MUST ask the user wia Q-block question.
> - The analysis document is a reasoning artifact only; it is NOT an implementation driver.


S05.1. If both [Input-detected] is False and [Questions-detected] is 0: output `Note: No new instructions found. Execution halted.` and HALT. MUST NOT write any output files.

S05.2. Based on the information in `.aib_memory/input.md` (Input or Questions sections), files in `.aib_memory/attachments`, `analysis-<request_id>.md` if exists and project memory in `.aib_memory/context.md` generate or update `analysis-<request_id>.md` as a full content replacement (overwrite) at `.aib_memory/analysis-<request_id>.md`. Leave the **Requirements Gate Evaluation** sub-heading empty - it will be populated in the next steps.

S05.3. A solution is built from instructions that have exactly one valid implementation path and from others that permit multiple approaches — requiring a deliberate choice. Each such choice point is called a "Decision Point." Ensure that ALL Decision Points are identified in the ### Decision Points section within ## Decision Register of the analysis document.

S05.4. Output a short step-completion note in format: `[S05 done] Analysis document generated; all Decision Points identified.`
   
### S06 Step 6 — Quality Check

S06.1 Evaluate the generated analysis. Evaluate every checklist item from `requirements-analysis-convention.md` against the active request `analysis-<request_id>.md` — item-by-item.

S06.2 Record the evaluation result for all items in the `## Research Results` section of the analysis document under a **Requirements Gate Evaluation** sub-heading. 

S06.3 If any mandatory item cannot be satisfied by a reasonable documented assumption, ad a new decision point in the analysis and tag it with `ask` in the Decision Points section.

S06.4. Output a short step-completion note in format: `[S06 done] Quality check complete; Requirements Gate Evaluation recorded in analysis.`

### S07. Step 7 — Archive Input and Reset

S07.1. Invoke `finalize-input.py` to handle the archive + move + reset sequence atomically. The script will:
   - Archive the pre-reset `input.md` content to `<request-folder>/inputs/input-archive-<YYYY-MM-DD_HH-MI-SS>.md` before resetting.
   - Move any remaining non-`.gitkeep` files from `.aib_memory/attachments/` to `<request-folder>/inputs/`.
   - Reset `input.md` to the seed template with the active request ID injected.
   ```
   python .aib_brain/tools/finalize-input.py --workspace . --request-id <request_id>
   ```
   where `<request_id>` is the active request ID.

S07.2. Output a short step-completion note in format: `[S07 done] Input archived, attachments moved, and input.md reset to seed template.`


### S08. Step 8 — Q-block Generation

> **Rules:**
> - Multiple-choice is preferred when bounded options exist.
> - Use free-text only when the answer space is unbounded (e.g., naming, external URLs, configuration values).

S08.1. If [Questions-expected] is more than the decision points marked as `ask` - change the tag of the most critical decision points marked as `resolve-autonomously` to `ask`. If still the [Questions-expected] number is not reached - write nottice to the user `Note: The minimum questions number can not be reached.`.  

S08.2. For every Decision Point tagged `ask`, generate one Q-block following the instructions in `.aib_brain/conventions/q-block-convention.md`. Q-blocks MUST reference the alternative by name from the Decision Register section when applicable. Write Q-blocks to a `## Questions` section appended to `input.md`.

S08.3. Edit `.aib_memory/input.md` to replace the line `State: analysis_ready` with `State: questions_generated`. Output `Note: New questions generated.` and HALT.

S08.4. If no Decision Point tagged `ask` are found, do NOT write a `## Questions` section. Continue with the next step.

S08.5. Output a short step-completion note in format: `[S08 done] Q-block generation complete; questions written or skipped based on Decision Points.`

### S09. Step 9 — Plan Generation

S09.1. Generate or recreate `.aib_memory/plan-<request_id>.md` based on `.aib_memory/analysis-<request_id>.md` and project memory in `.aib_memory/context.md`. Follow strictly the format and structure defined in `.aib_brain/conventions/plan-convention.md`

S09.2. Output a short step-completion note in format: `[S09 done] Plan document generated or recreated from completed analysis.`


### S10. Step 10 - Completion Confirmation

S10.1. Confirm at the very end of the conversation (this should be the very last message to the user after all other generated response) with the text "--- I am done with the analysis of `<request_id>` ---".

S10.2. Do not add additional text after "--- I am done with the analysis of `<request_id>` ---" line. MUST: If needed to be written somenting in the output chat - do it before this line.

---

## Appendix A — Auto-Request Creation Branch

> **Trigger:** Entered from Step 1 (§5.1) when zero Active rows are found in `requests_register.md` and `input.md ## Input` is non-empty.

**A.1.** Read `.aib_memory/input.md`.
   - If `## Input` section is empty or contains only whitespace: output the literal message **"ERROR: No active request and input.md is empty. Add content to ## Input before running analysis."** and HALT. Do NOT proceed.

**A.2.** Derive a request title from the `## Input` content (first meaningful sentence or noun phrase, ≤ 60 characters).

**A.3.** Invoke `.aib_brain/tools/create-request.py`:
   ```
   python .aib_brain/tools/create-request.py --workspace . --title "<derived-title>"
   ```

**A.4.** Read `.aib_memory/requests_register.md` to resolve the newly created request folder and `<request_id>`.

## Appendix B —  Decision Point Classification

**B.1.** A decision point MUST be tagged `resolve-autonomously` ONLY when ALL of the following hold:

1. The developer's own `input.md ## Input` text OR a named, specific section of a workspace convention file explicitly and unambiguously resolves it.
2. The cited source uses clear, explicit language — not inference, implication, or "spirit of" interpretation.
3. The rationale in the Decision Points section quotes or cites the exact source text and file path.

**B.2.** A decision point MUST be tagged `ask` in every other case, including:

- When the answer seems "obvious" or follows "industry best practice" without a named workspace source explicitly stating so.
- When external literature, benchmarking findings, or AI judgment provide the only justification.
- When the answer is "strongly implied" but not explicitly stated.
- When in doubt.