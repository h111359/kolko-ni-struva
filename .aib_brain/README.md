# AIB Workspace Guide

Open [user_guide.html](.aib_brain/user_guide.html) in a browser for the full interactive user guide.

AI Builder (AIB) is a minimal but powerful framework for AI specification-driven development. AIB serves for software development, documentation creation, data processing and all other activities which can be achieved with AI.

## Objectives:

  - To analyze the user input and to generate analysis and plan markdown files
  
  - To generate questions to the user for those aspects which can lead to different implementation
  
  - to write a detailed plan for action which will be performed during implementation phase
  
  - to write implementation details when execution is performed

## Prerequisites

- Python 3.10+ in your terminal.
- Terminal open at the repository root.

## Quick Start

Launch the interactive menu:

```bat
.aib_brain\run.bat        # Windows
```
```sh
sh .aib_brain/run.sh      # Linux / macOS
```

The menu displays a state-aware guidance block with your next recommended action and, when an active request exists, a "Close current request" action.

## Daily Flow

1. Write your intent into the `## Input` section of `.aib_memory/input.md`.
2. Run analysis in AI chat: `Execute .aib_brain/prompts/aib-analyze.md` _(Optional but highly recommended)_ 
3. Run implement in AI chat: `Execute .aib_brain/prompts/aib-implement.md`
   — If no active request exists, the prompt auto-creates one from `input.md` and proceeds.
   — The request is closed automatically when implementation completes.

## Prompt Invocations

```
Execute .aib_brain/prompts/aib-analyze.md
```
```
Execute .aib_brain/prompts/aib-implement.md
```
```
Execute .aib_brain/prompts/aib-refresh-context.md
```

## Use Cases

**Full analysis → implement flow**
1. Write request into `input.md → ## Input`.
2. Run `aib-analyze.md` — auto-creates request, generates `analysis-<id>.md` and `plan-<id>.md`.
3. Review `plan-<id>.md`; adjust if needed.
4. Run `aib-implement.md` — executes scope and closes request automatically.

**Direct implement (no formal analysis)**
1. Write request into `input.md → ## Input`.
2. Run `aib-implement.md` — auto-creates request from input and implements.

**Refresh workspace context**
- Run `aib-refresh-context.md` at any time (no active request required) to refresh `.aib_memory/context.md`.

## Workspace Instructions (`instructions.md`)

`.aib_memory/instructions.md` is a persistent directives file read by every AIB prompt before it executes. Write any workspace-specific rules here — coding conventions, naming rules, always/never behaviors. If absent or empty, all prompts continue normally.

**Do not store secrets, credentials, or PII in this file.**

## Questions and Answers

When `aib-analyze.md` identifies decision points with multiple valid implementation choices where the preferred option has a materially different impact on the codebase, it generates a `## Questions` section in `input.md`.

**How it works:**

1. After analysis runs, open `.aib_memory/input.md`. If any questions were generated, a `## Questions` section will appear at the end of the file.
2. Each question includes:
   - The question text.
   - A `> **Why this matters:**` line explaining the implementation impact.
   - For multiple-choice: mutually exclusive options with checkboxes; the first option is marked `*(recommended)*` as the AI's preferred choice.
   - For free-text: a `- Answer: ___` field when no bounded options exist.
   - Format templates and rules for both Q-block types are defined in `.aib_brain/conventions/q-block-convention.md`.
3. Answer questions by checking `[x]` next to your chosen option (multiple-choice), or writing a free-text answer after `- Answer:`.
4. If you leave a question unanswered, the Answer Application Sub-flow halts with an error message and leaves `input.md` unchanged. All Q-blocks must be answered before re-running analysis.
5. Re-run `aib-analyze.md` — the prompt reads your answers, applies them to the relevant `plan.md` sections, and clears the `## Questions` section from `input.md`.

**Note:** The `## Questions` section is ephemeral — it is never part of the `input.md` seed template and is fully cleared after each Q&A cycle.

## Concepts

  - AIB shall be defined entirely in a folder called `.aib_brain/` with files and subfolders in it where are defined the prompts, templates, conventions and tools of the framework (generic, non-specific and replaceable part).
   
  - The artifacts in `.aib_brain/` shall be used to seed the folder `.aib_memory/` (if not existing) in the same folder where `.aib_brain/` is located. 
  
  - AIB work will be organized in a series of requests defined in files and file structure as per this document. In the requests are defined the context and specifications needed for AI to build or change the product accordingly the expectation of the human. 
  
  - The AI-produced output (the product) is driven by the functionalities defined in `.aib_brain/` and the information stored in `.aib_memory`. 
  
  - `.aib_brain/` installed in a project folder SHALL NOT be modified by AIB tool scripts. Humans may replace or update `.aib_brain/` explicitly when evolving the framework.

  - The request to AIB shall be defined in file `input.md` in  `.aib_memory/`. In addition, a record shall be added for it in a file `.aib_memory/requests_register.md`.

  - During a request, an analysis and plan for implementation will be created.
  
  -  `implementation.md` file must be generated during request implementation.

  - The artifacts of AIB shall be separated by their lifecycle. In `.aib_brain/` folder shall be stored reusable framework assets (prompts, conventions, tools). On upgrade this folder shall be replaceable entirely. In `.aib_memory/` shall be stored project specific artifacts - project-specific requests and iteration artifacts
  
  - All kind of formatting specifications, shared and common definitions, extended context or similar shall be located in `.aib_brain/conventions/` folder in markdown files.
  
  - Scripts to support AIB workflow shall be placed in `.aib_brain/tools/` folder. Python 3.10+ is the prime choice of programming language for the scripts.
  
  - A file `.aib_memory/requests_register.md` shall contain a list with the requests the user has generated. Each request record shall contain the request ID in format "R-<YYYYMMDD>-<HHmi>", request title, relative path to the request folder and states (Active, Closed). Many Closed requests could coexist. Only one Active request shall exist at a time. No new requests shall be created until the current Active one is closed.
  
  - The product knowledge for the workspace is consolidated in `.aib_memory/context.md`, updated by `aib-refresh-context.md` on each execution. 
  
  - Developers MAY use `.aib_memory/instructions.md` to flag any additional files that AIB prompts should read or treat with special care.

  - AIB shall be model and vendor agnostic. This means it shall be executable in all environments like VS Code with GitHub copilot, Claude Code, Cursor or similar and with different models like GPT 5.3 Codex, Claude Code 4.6 Opus, Gemini 3.1 or better.


### Folder structure

.aib_brain/
  - conventions/
  - prompts/
  - tools/
  - README.md
  - run.bat
  - run.sh
  - user_guide.html
  - vM.m.p (semver marker file)
.aib_memory/
  - attachments/
  - requests/
  - context.md
  - input.md
  - instructions.md
  - requests_register.md
logs/
  - next_version_changes.md
  - version_vX.Y.Z_log.md (per-version logs)
versions/
  - aib_brain_vX.Y.Z.zip (versioned archives)

## Request Folder Artifacts

| Artifact | Created by | Description |
| --- | --- | --- |
| `plan-<id>.md` | `aib-analyze.md` | Request plan and decisions. Active copy lives at `.aib_memory/plan-<id>.md`; moved to request subfolder after implementation. |
| `analysis-<id>.md` | `aib-analyze.md` | Reasoning artifact (not read by `implement`). |
| `implementation.md` | `aib-implement.md` | Append-only implementation log. |
| `inputs/input-archive-*.md` | `aib-analyze.md` | Archived `input.md` per analysis run. Never read by prompts after archiving. |

