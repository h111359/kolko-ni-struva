Purpose
Define the authoritative format, naming, semantics, and operational rules for the file `plan-<request_id>.md` (the per-request precision execution specification). This convention ensures deterministic parsing by AIB tools, consistent structure across all requests, and unambiguous interpretation of implementation directives by the AI Automation Agent.

Scope
- Applies only to the single plan artifact per active request, named `plan-<request_id>.md`.
- Covers: file structure, required headings, allowed content, ID resolution, constraints, and editing rules.
- Excludes: rules for analysis, questionnaire, and implementation artifacts (defined by their own conventions).

File Location & Naming (normative)
- MUST be named following the pattern `plan-<request_id>.md` during the active phase (e.g. `plan-R-20260509-2313.md`).
- **Two-phase placement rule:**
  1. **Active phase** — while the request is open, `plan-<request_id>.md` resides at `.aib_memory/plan-<request_id>.md` (workspace root of `.aib_memory/`, NOT inside the request subfolder). It is written here by `aib-analyze.md` and read from here by `aib-implement.md`.
  2. **Archived phase** — upon successful implementation completion, `plan-<request_id>.md` is moved by `move-request-artifacts.py` to `.aib_memory/requests/<request-folder>/plan-<request_id>.md` (ID suffix preserved) before `close-request.py` marks the request Closed.
- Re-runs of `aib-analyze.md` fully replace the active copy at `.aib_memory/plan-<request_id>.md` without merging.
- Request folder name MUST follow:
  `R-<YYYYMMDD>-<HHmi>-<request_title>`
  where the timestamp is created by tooling, not the human.
- Only one `plan-<request_id>.md` may exist per request folder (archived phase).

Document Structure (normative)
The file MUST contain the following top-level sections in the exact order shown below.
All headings MUST be level-2 (`##`).
All sections (1–4) are mandatory and MUST be present, even if empty.

1. `## Goal`
   - A concise, execution-oriented description of what the implementation must achieve.
   - MUST be concise; typically a few sentences.

2. `## Constraints`
   - All assumptions, limitations, or boundary conditions the implementation must respect.
   - SHOULD include business constraints, technical constraints, and timing restrictions.
   - MUST avoid ambiguity; if undefined, specify "None".

3. `## Success criteria`
   - MUST define measurable outcomes that indicate completion.
   - SHOULD link criteria to testability or user acceptance conditions.

4. `## Plan`
   - AI-generated Work Breakdown Structure (WBS) for the active iteration.
   - Each task uses the following schema:
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
   - Every Procedure step MUST reference the exact file path it operates on. Steps that do not operate on a specific file (e.g., running a terminal command) MUST name the command and its expected output location.
   - Pre-flight findings (cross-reference issues, missing information, factual inconsistencies, impacted files) MUST be redistributed into the relevant task's `Risk Notes` or raised as Q-blocks; they MUST NOT appear as separate top-level sections.
   - Fully replaced on every analysis re-run.
   - Every plan MUST include: (a) a task defining automated test steps for the request scope (covering all testable Success Criteria); (b) a task to update `.aib_memory/context.md` and any other documentation files affected by the request, reflecting changes made and any discovered discrepancies. The documentation task MUST specify for each step: (1) the target file path, (2) what to change, and (3) an acceptance test.

Formatting Rules (normative)
- Only level-2 headings (`##`) are allowed for the required sections.
- Level-3 headings MAY be used inside sections.
- Level-4 headings (`####`) MUST be used for plan task sub-fields (Intent, Outputs, Procedure, Done criteria, Dependencies, Risk notes).
- No metadata header (Title/Version/Owner/etc.) is allowed.
- No hyperlinks, references, or footnotes that require external resolution.
- Markdown lists MUST use `-` or `1.` consistently.
- One blank line MUST separate each `### Task N` block from the next `### Task N` block.
- One blank line MUST separate each `####` sub-field heading from its content.
- Procedure steps within a plan task MUST each be separated from the next by one blank line.
- Markdown tables MUST NOT appear anywhere in `plan.md`.

Content Rules (normative)
- The plan MUST contain only execution-oriented directives; human narrative and rationale belong in `analysis-<request_id>.md`.
- The plan MUST avoid specifying iteration-specific content (iterations are separate entities).
- The plan MUST NOT instruct the tools to violate lifecycle rules (e.g., creating multiple active requests).

Lifecycle & Editing Rules (normative)
- Only one request in the system MAY be `Active` at a time.
- A request becomes `Closed` via `close-request`; after that:
  - `plan.md` becomes read-only except for human archival comments.
  - Tools MUST NOT modify the plan after closure.
- Human edits:
  - Allowed only while request is `Active`.
  - MUST maintain section order and headings.
  - SHOULD avoid unpredictable changes (rewriting the whole file breaks iteration continuity).
- Tools:
  - MUST NOT auto-rewrite the content except where explicitly allowed (e.g., minor formatting normalization).
  - MUST reject the plan if mandatory sections are missing.

Validation Rules (normative)
A valid `plan.md` MUST satisfy:
- The four mandatory sections (Goal, Constraints, Success criteria, Plan) exist exactly once and in order 1–4.
- Content in each mandatory section is non-empty except where explicitly allowed.
- File path matches the request folder.
- Folder name matches naming convention and `request_id` is parseable.
- `## Amends` section MUST NOT appear in any `plan.md`; use `input.md` for amendments.

Operational Workflow (normative)
- `plan-<request_id>.md` is generated by `aib-analyze.md` from `input.md` content and Q&A answers.
- `implement` MUST rely on `plan-<request_id>.md` as its authoritative source; it MUST NOT alter `plan-<request_id>.md`.

Change Control (normative)
- Any updates to this convention MUST be made before generating new `plan-<request_id>.md` files.
- When the convention is updated, existing plans SHOULD NOT be rewritten automatically.
- New plans MUST always follow the latest convention.
