# Prompt: aib-modify

## Goal

Direct-execution prompt: reads `input.md ## Input` and applies changes immediately
without a prior analysis/plan cycle. Uses `context.md` for product awareness and
`instructions.md` for workspace directives. Archives `input.md` on completion but
does NOT close the request (no `move-request-artifacts.py` or `close-request.py`).

## Process

Step 1 — Read instructions: Read `.aib_memory/instructions.md`. If present and non-empty,
treat its content as persistent workspace-level instructions to be observed throughout
the entire execution.

Log: `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-modify: Step 1 Read instructions"`.

Step 2 — State check: Run `python .aib_brain/tools/input-header.py --workspace . --operation read`
and parse `state` and `request_id`. Apply the following branch logic:

- If `state == questions_generated`: halt immediately with the literal error:
  `ERROR: Active request <request_id> has unanswered Q-blocks (state: questions_generated). Answer all questions or reset state before running aib-modify.md.`

- If `state == idle`: execute `.aib_brain/prompts/aib-create-request.md`; after it completes,
  re-run `python .aib_brain/tools/input-header.py --workspace . --operation read` to resolve
  the new `request_id` and continue.

- If `state == analysis_ready`: continue.

Step 3 — Log preflight complete (uses resolved `request_id`) and run verifications:

`python .aib_brain/tools/log-entry.py --workspace . --message "aib-modify: preflight complete <request_id>"`

Read `input_verification_enabled` and `context_verification_enabled` from `input.md` YAML header by running `python .aib_brain/tools/input-header.py --workspace . --operation read` and parsing its output.

If `input_verification_enabled` is `true`: invoke `python .aib_brain/tools/verify-input.py --workspace .`. If the script exits with code 1, halt execution immediately. Output the literal message: `ERROR: input.md verification failed. Fix the following issues before re-running analysis:` followed by each failing check name and its corrective suggestion as returned by the script. MUST NOT write any output files.

If `context_verification_enabled` is `true`: invoke `python .aib_brain/tools/verify-context.py --workspace .`. If the script exits with code 1, halt execution immediately. Output the literal message: `ERROR: context.md verification failed. Fix the following issues before re-running analysis:` followed by each failing check name and its corrective suggestion as returned by the script. MUST NOT write any output files.

Step 4 — Read input: Read `.aib_memory/input.md` `## Input` section.

- If the section is absent or contains only whitespace, halt with:
  `ERROR: input.md ## Input is empty. Add implementation instructions before running aib-modify.md.`

Step 5 — Read context: Read `.aib_memory/context.md` for product-context awareness.
Do NOT update `context.md` during this execution.

Step 5.5 — Extension relevance check: For each Reference entry in `## References` of `context.md`, read the `Summary:` for that entry and use AI semantic relevance judgement to determine whether the extension is relevant to the active request. If relevant, read the full extension file at the `Location:` path and treat its content as additional input context alongside `context.md`.

Step 6 — Read coding conventions: Unconditionally read `.aib_brain/conventions/coding-general-convention.md`.
Additionally read the language-specific convention file that corresponds to the file extensions
being created or edited, using the same extension-to-convention mapping table as `aib-implement.md`:

| File extension(s)                                                  | Convention file to read                                                                                               |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `.py` (non-framework)                                              | `.aib_brain/conventions/coding-python-convention.md`                                                                 |
| `.py` (Flask app)                                                  | `.aib_brain/conventions/coding-python-convention.md` AND `.aib_brain/conventions/coding-flask-convention.md`         |
| `.py` (Django app)                                                 | `.aib_brain/conventions/coding-python-convention.md` AND `.aib_brain/conventions/coding-django-convention.md`        |
| `.dax`                                                             | `.aib_brain/conventions/coding-dax-convention.md`                                                                    |
| `.sql`                                                             | `.aib_brain/conventions/coding-sql-convention.md`                                                                    |
| `.html`, `.htm`                                                    | `.aib_brain/conventions/coding-html-convention.md`                                                                   |
| `.js`, `.mjs`, `.cjs`                                              | `.aib_brain/conventions/coding-javascript-convention.md`                                                             |
| `.jsx`                                                             | `.aib_brain/conventions/coding-javascript-convention.md` AND `.aib_brain/conventions/coding-react-convention.md`     |
| `.tsx`                                                             | `.aib_brain/conventions/coding-javascript-convention.md` AND `.aib_brain/conventions/coding-react-convention.md`     |
| `.css`, `.scss`, `.sass`, `.less`                                  | `.aib_brain/conventions/coding-css-convention.md`                                                                    |
| `.cs`                                                              | `.aib_brain/conventions/coding-csharp-convention.md`                                                                 |
| `.scala`                                                           | `.aib_brain/conventions/coding-scala-convention.md`                                                                  |
| UI/UX design files (`.html`, `.css`, `.jsx`, `.tsx` with design intent) | `.aib_brain/conventions/coding-uiux-convention.md` (in addition to the language convention)                    |

Apply all rules from the loaded convention file(s) to every file created or edited.

Step 7 — Implement: Apply the implementation directive from `input.md ## Input`, observing
`instructions.md` directives and the loaded coding conventions.

Rules:
- MUST NOT modify any file under `.aib_brain/`.
- MUST NOT update `context.md`.

After completing, log: `python .aib_brain/tools/log-entry.py --workspace . --message "aib-modify: implementation complete"`.

Step 8 — Archive input.md, move active-request artifacts to the request subfolder, and auto-close the request by invoking (in this exact order):

Run `python .aib_brain/tools/log-entry.py --workspace . --message "Step 9 Request close initiated: <request_id>"`.

Run the following commands in the workspace root:
  ```
  python .aib_brain/tools/finalize-input.py --workspace .
  python .aib_brain/tools/move-request-artifacts.py --workspace .
  python .aib_brain/tools/close-request.py --workspace .
  ```

Log: `python .aib_brain/tools/log-entry.py --workspace . --message "aib-modify: input archived"`.



Step 10 — Completion confirmation: Output the literal text below as the very last message.
Do not add any text after this line.

`--- I am done with the modification of <request_id> ---`

## Rules

### Safety requirements

- MUST NOT modify `.aib_brain/` assets during implementation work.
- MUST NOT add files under `.aib_brain/`.
- MUST NOT update `context.md`.
- Do not create Python virtual environment unless explicitly specified in the request.
- Do not install any additional libraries or third-party software unless explicitly specified.

### Modifier flags

- This prompt has no modifier flags; it operates in a single execution mode.

