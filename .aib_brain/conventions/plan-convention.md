Purpose
Authoritative spec for plan artifact naming+placement+structure+constraints+validation+editing. Goal: deterministic parsing by AIB tools; consistent cross-request format; unambiguous impl directives.
Scope
IN: single per-request plan artifact, structure rules, heading rules, content limits, ID resolution, lifecycle/edit rules. OUT: analysis/questionnaire/implementation artifact conventions.
$RID=request_id|$PLAN=plan-$RID.md|$REQF=R-<YYYYMMDD>-<HHmi>-<request_title>|$ACTIVE=.aib_memory/$PLAN|$ARCH=.aib_memory/requests/<request-folder>/$PLAN
File Location+Naming (normative)
- Name MUST match $PLAN (ex: plan-R-20260509-2313.md).
- Placement 2-phase:
  1. Active(open req): store at $ACTIVE (root of .aib_memory, !inside req subfolder); written by aib-analyze.md; read by aib-implement.md.
  2. Archived(post successful impl): move via move-request-artifacts.py -> $ARCH (ID suffix preserved) before close-request.py marks Closed.
- Re-run aib-analyze.md: fully replace $ACTIVE; no merge.
- Request folder name MUST match $REQF; timestamp tool-generated, !human-generated.
- Archived phase: max one $PLAN per request folder.
Document Structure (normative)
- Top-level sections required exactly once, exact order, all present even if empty: 1) ## Goal 2) ## Constraints 3) ## Success criteria 4) ## Plan.
- Required headings level: section headings MUST be ##.
- ## Goal MUST include: target outcome + why/background + impacted components.
- ## Constraints MUST include assumptions/limits/boundaries; SHOULD include business+technical+timing constraints; if none -> None.
- ## Success criteria MUST be measurable; SHOULD map to testability/user acceptance.
- ## Plan = AI-generated WBS for active iteration.
- Task schema in ## Plan:
  ### Task <N>: <Task Name>
  #### Intent
  <single-sentence goal and artifacts changed/produced>
  #### Procedure
  <step 1>
  <blank line>
  <step 2>
  <blank line>
  <...>

- Procedure-step rules:
  - Each step MUST cite exact target file path.
  - Non-file step (ex terminal cmd) MUST include exact cmd + expected output location.
  - Each step MUST describe exact per-file change detail executable without ambiguity.
  - MUST NOT include programming code snippets; MUST describe changes in natural language with exact text to be added/deleted embedded.
- Analysis re-run fully replaces plan content.
- Mandatory extra tasks in every plan:
  - Automated tests task covering all testable Success criteria.
  - Documentation update task for .aib_memory/context.md + any affected docs.
  - Doc task Procedure step MUST include: target file path; exact edit-context.py command with literal --operation/--area/--type/--text for each atomic insert/delete; acceptance test.
Formatting Rules (normative)
- Required sections use ## only.
- Inside sections: ### allowed; task sub-fields MUST use #### for Intent/Outputs/Procedure/Done criteria/Dependencies.
- NO: [metadata header(Title/Version/Owner/etc), hyperlinks requiring external resolution, references requiring external resolution, footnotes requiring external resolution, markdown tables in plan.md].
- List marker consistency required: use - or 1. consistently.
- Spacing rules: 1 blank line between each ### Task block; 1 blank line between each #### sub-field heading and content; 1 blank line between Procedure steps.
Content Rules (normative)
- plan MUST contain execution directives only; rationale belongs in analysis-$RID.md.
- plan MUST avoid iteration-specific content beyond active-iteration WBS structure.
- plan MUST !instruct lifecycle violations (ex multiple active requests).
Lifecycle+Editing Rules (normative)
- System allows exactly one Active request.
- On close-request => Closed:
  - plan.md read-only except human archival comments.
  - tools MUST NOT modify plan.
- Human edits allowed only while Active; MUST preserve section order+headings; SHOULD avoid full unpredictable rewrites breaking iteration continuity.
- Tools MUST NOT auto-rewrite content except explicitly allowed (ex minor formatting normalization); MUST reject plan if mandatory sections missing.
Validation Rules (normative)
Valid plan.md requires all:
- Document Structure declares sections 1-4 as the mandatory top-level schema.
- 4 mandatory sections exist exactly once in order Goal->Constraints->Success criteria->Plan.
- Mandatory-section content non-empty unless explicitly allowed empty.
- File path matches request folder.
- Folder name matches convention; $RID parseable.
- ## Amends section MUST NOT exist in plan.md; use input.md for amendments.
Operational Workflow (normative)
- aib-analyze.md generates plan from input.md + Q&A answers.
- implement MUST treat plan as authoritative; MUST NOT alter plan; MUST NOT read .aib_memory/context.md; all execution context MUST be in plan.
Change Control (normative)
- Update this convention before generating new plan files.
- Existing plans SHOULD NOT be auto-rewritten when convention changes.
- New plans MUST follow latest convention.
