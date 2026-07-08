# Prompt: aib-create-request

## Goal

Encapsulate the auto-request-creation logic as a standalone, reusable prompt.
Called by `aib-analyze.md` (Appendix A) and `aib-modify.md` (idle-state branch)
when no active request exists and `input.md ## Input` is non-empty.

## Process

Step 1 — Skip. Continue to step 2.

Step 2 — State guard: Run `python .aib_brain/tools/input-header.py --workspace . --operation read` and parse `request_id` and `state`.

- If `state != idle`, halt immediately with the literal error:
  `ERROR: Active request <request_id> already exists. aib-create-request.md must only be called when state is idle.`

Step 3 — Check input: Read `.aib_memory/input.md` `## Input` section.

- If the section is absent or contains only whitespace, halt with the literal error:
  `ERROR: No active request and input.md is empty. Add content to ## Input before running analysis.`

Step 4 — Derive title: Extract the first meaningful sentence or noun phrase from `## Input`, truncated to ≤ 60 characters, as the request title.

Step 5 — Create request: Invoke `python .aib_brain/tools/create-request.py --workspace . --title "<derived-title>"`.

Step 6 — Resolve new request_id: Run `python .aib_brain/tools/input-header.py --workspace . --operation read` and capture the newly created `request_id` from the output.

Step 7 — Log completion:

Run `python .aib_brain/tools/log-entry.py --workspace . --message "aib-create-request: complete <request_id>"`.

Step 8 — Output the resolved `request_id` to the conversation.
