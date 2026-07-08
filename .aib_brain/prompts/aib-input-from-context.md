# Prompt: aib-input-from-context

## Objective

Read all `[PLANNED]` entries and Issues from `context.md` and append structured goal bullets to `input.md ## Input`. Fails with an error if an active request already exists.

---

## Variables

- `[PlannedEntries]` — list; statements prefixed with `[PLANNED]` found in Product, Concepts, Solution, and Requirements sections of `context.md`.
- `[IssueEntries]` — list; plain bullet entries found in the `## Issues` section of `context.md`.
- `[GoalBullets]` — list; formatted goal bullets to append to `input.md ## Input`.

---

## Global Rules

- **GC-01 — Active request guard:** If an active request exists (`status != idle`), halt immediately with an error. This prompt is intentionally designed for use only when no active request is open.
- **GC-02 — No write on halt:** When execution halts due to any error condition, MUST NOT write any output files.
- **GC-03 — Append only:** MUST append to `## Input`; must not overwrite or truncate any existing content in that section.

---

## Inputs

| Source | Description |
| --- | --- |
| `.aib_memory/input.md` | Active-request state check; target for appended goal bullets |
| `.aib_memory/context.md` | Source of `[PLANNED]` entries and `## Issues` bullets |
| `.aib_memory/instructions.md` | Persistent workspace-level directives (optional) |

## Outputs

| Artifact | Location | Description |
| --- | --- | --- |
| `input.md` (updated) | `.aib_memory/input.md` | Goal bullets appended to `## Input` section |

---

## Execution Procedure

### Step 1 — Preflight

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 1 started"`.

1. Read `.aib_memory/instructions.md`. If present and non-empty, observe its content as persistent workspace-level instructions throughout execution.

2. Run `python .aib_brain/tools/input-header.py --workspace . --operation read`. Parse `status` and `request_id` from the output.

3. If `status != idle`, halt with:
   `ERROR: Active request <request_id> already exists (status: <status>). Close the current request before running aib-input-from-context.md.`

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 1 complete"`.

---

### Step 2 — Read Context and Extensions

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 2 started"`.

1. Read `.aib_memory/context.md`. If absent, halt with:
   `ERROR: context.md not found. Run aib-refresh-context.md first. Execution halted.`

2. **Extension relevance check:** For each Reference entry in `## References` of `context.md`, read the `Summary:` and use AI semantic relevance judgement to determine whether the extension is relevant to the goal-collection task. If relevant, read the full extension file at the `Location:` path and treat its content as supplementary context.

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 2 complete"`.

---

### Step 3 — Collect [PLANNED] Entries

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 3 started"`.

1. Scan all five content sections of `context.md` (Product, Concepts, Requirements, Solution, and Issues) for statements beginning with `- [PLANNED]`.
2. For each matching statement, strip the `[PLANNED] ` prefix and record the remaining text in `[PlannedEntries]`.

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 3 complete"`.

---

### Step 4 — Collect Issues Entries

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 4 started"`.

1. Scan the `## Issues` section of `context.md` for all plain bullet entries.
2. For each entry, record the description text (after stripping the `- ` prefix) in `[IssueEntries]`.

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 4 complete"`.

---

### Step 5 — Generate Goal Bullets

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 5 started"`.

1. For each entry in `[PlannedEntries]`, format as:
   `- Implement: <statement text>`

2. For each entry in `[IssueEntries]`, format as:
   `- Resolve issue: <description>`

3. Collect all formatted lines into `[GoalBullets]`.

4. If `[GoalBullets]` is empty, output:
   `Note: No [PLANNED] entries or Issues found in context.md. Nothing to append.`
   Exit without modifying `input.md`.

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 5 complete"`.

---

### Step 6 — Append to Input

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 6 started"`.

1. Read the current content of `.aib_memory/input.md`.
2. Locate the `## Input` section.
3. Append all lines from `[GoalBullets]` after any existing content in `## Input`. Preserve existing content.
4. Write the updated content back to `.aib_memory/input.md`.

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 6 complete"`.

---

### Step 7 — Confirmation

Run `python .aib_brain/tools/log-entry.py --workspace . --general --message "aib-input-from-context Step 7 complete"`.

Output a confirmation message:
`Appended <N> goal bullets to input.md ## Input (<P> [PLANNED] entries, <I> Issues entries).`

Where `<N>` is the total count, `<P>` is the count from `[PlannedEntries]`, and `<I>` is the count from `[IssueEntries]`.

---

## Safety

- The only permitted write target is `.aib_memory/input.md`.
- MUST NOT modify `context.md` or any file under `.aib_brain/`.
- MUST NOT create files outside `.aib_memory/`.
- MUST append to existing `## Input` content; never overwrite.
