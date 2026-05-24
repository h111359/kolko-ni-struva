# Prompt: implement

## Goal:
Execute active request scope, update the documentation and create request-scoped `implementation.md` from scratch.

## Process

Step 1:  Read `.aib_memory/instructions.md`. If the file exists and is non-empty, treat its content as persistent workspace-level instructions that MUST be observed throughout this prompt's execution. If the file is absent or empty, proceed normally.

Step 2: Read `.aib_memory/requests_register.md` and check for exactly one row with `state = Active`.
  - If zero Active rows are found: output the message **"ERROR: No active request is found. Execution halted."** and HALT.
  - If more than one Active row is found: output the message **"ERROR: Register inconsistency — multiple Active requests found. Execution halted. Fix requests_register.md before running implement."** Do NOT proceed to any subsequent step. Do NOT write any output files.
  - If exactly one Active row is found: continue with input resolution below.

Step 3:  Resolve active request from `.aib_memory/requests_register.md` unless explicit ID is provided.

Step 4: Read `.aib_memory/context.md`. If the file is absent or empty, continue normally with no error; otherwise treat its content as the unified workspace product context for this implementation run.

Step 5: Read `.aib_memory/plan-<request_id>.md` (the active location while the request is open, where `<request_id>` is the active request ID resolved from the register). 

Step 6: Follow strictly the plan and implement it. Implement the tasks in the same order. After each task implented - output a quick summary.


Step 7: Apply code/documentation changes required by request scope.

Step 8: Create/update tests where applicable.

Step 9: Run validation/tests and capture results.

Step 10: Resolve any test failures

Step 11: Continue until done criteria are met or blockers are explicitly recorded.

Step 11: Execute `.aib_brain\prompts\aib-refresh-context.md`

Step 12: Move the active-request artifacts to the request subfolder and then auto-close the request by invoking (in this exact order):
  ```
  python .aib_brain/tools/move-request-artifacts.py --workspace .
  python .aib_brain/tools/close-request.py --workspace .
  ```
> Rules:
>  The move step MUST be executed before `close-request.py`. 
>  MUST: Only invoke these scripts after the implementation is confirmed successful (no unresolved test failures or blockers).

Step 13. Generate `implementation.md` from scratch in the active request folder if it does not exist; append a new Entry if it already exists. Follow the exact Entry Block Format defined in `.aib_brain/conventions/implementation-convention.md`. 

Step 14. MUST confirm at the very end of the conversation with the text "--- I am done with the implementation  of `<request_id>` ---" that all your activities are finished

> Rules:
> Do not add additional text after "--- I am done with the implementation of `<request_id>` ---" line. MUST: If needed to be written somenting in the output chat - do it before this line.

## Rules

### Execution requirements:

- Must not read the Analysis
- MUST NOT read `inputs/input-archive-*.md` files from any request folder.
- MUST NOT read or reference any file inside `.aib_memory/requests/<folder>/` that belongs to a Closed request. This covers all artifact types (request, analysis, implementation, input archives, and any other file). A request folder is Closed when its `state` in `requests_register.md` is `Closed`. If in doubt, treat the folder as Closed.


### Documentation reading requirements:

- Read `.aib_brain/conventions/context-convention.md` (authoritative convention for `.aib_memory/context.md`) before editing `.aib_memory/context.md` or any other documentation file. If the convention file cannot be read, DO NOT edit `.aib_memory/context.md`; record the blocker and required remediation in `implementation.md`.

### Coding convention requirements:

- UNCONDITIONALLY read `.aib_brain/conventions/coding-general-convention.md` before generating or editing any source-code file.
- CONDITIONALLY read the language-specific convention file based on the file extensions being created or edited, according to the table below. Read the convention file before generating code for that language.

| File extension(s)            | Convention file to read                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `.py` (non-framework)        | `.aib_brain/conventions/coding-python-convention.md`          |
| `.py` (Flask app)            | `.aib_brain/conventions/coding-python-convention.md` AND `.aib_brain/conventions/coding-flask-convention.md` |
| `.py` (Django app)           | `.aib_brain/conventions/coding-python-convention.md` AND `.aib_brain/conventions/coding-django-convention.md` |
| `.dax`                       | `.aib_brain/conventions/coding-dax-convention.md`             |
| `.sql`                       | `.aib_brain/conventions/coding-sql-convention.md`             |
| `.html`, `.htm`              | `.aib_brain/conventions/coding-html-convention.md`            |
| `.js`, `.mjs`, `.cjs`        | `.aib_brain/conventions/coding-javascript-convention.md`      |
| `.jsx`                       | `.aib_brain/conventions/coding-javascript-convention.md` AND `.aib_brain/conventions/coding-react-convention.md` |
| `.tsx`                       | `.aib_brain/conventions/coding-javascript-convention.md` AND `.aib_brain/conventions/coding-react-convention.md` |
| `.css`, `.scss`, `.sass`, `.less` | `.aib_brain/conventions/coding-css-convention.md`        |
| `.cs`                        | `.aib_brain/conventions/coding-csharp-convention.md`          |
| `.scala`                     | `.aib_brain/conventions/coding-scala-convention.md`           |
| UI/UX design files (`.html`, `.css`, `.jsx`, `.tsx` with design intent) | `.aib_brain/conventions/coding-uiux-convention.md` (in addition to the language convention) |

- Apply all rules from the loaded convention file(s) to every file created or edited in the current implement run.


### Safety requirements:
- Do not modify `.aib_brain/` assets during implementation work.
- Do not add files under `.aib_brain/`
- If nothing else specified, add tests in the folder of the request
- Do not create Python virtual environment unless explicitely specified in the request or in plan or in the documentation
- Do not install any additional libraries or third party software  unless explicitely specified in the request or in plan or in the documentation



