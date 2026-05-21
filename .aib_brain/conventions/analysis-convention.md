# Analysis Document Convention

**Scope:** Normative  
**Applies to:** All files named `analysis-<request_id>.md` generated under `.aib_memory/` (active phase) and archived to `.aib_memory/requests/<request-folder>/` (archived phase).

## 1. Purpose

The **Analysis document** is a **reasoning and knowledge-capture artifact** only. It records the AI's structured thinking about the user request - research findings, scope interpretation, domain and technical context, impact awareness, and risk identification.

**The analysis document is NOT an implementation driver.**

- `implement` MUST NOT read the analysis document.
- All implementation-relevant content (assumptions, plan, testing, documentation touchpoints, open questions) is written into `plan-<request_id>.md` by the `aib-analyze.md` prompt.
- Human stakeholders read the analysis for auditability and context; they do not use it as an execution specification.

***

## 2. Scope & Normative Language

This convention applies only to analysis artifacts for a single request:

*   Target files: `analysis.md`
*   Location: `.aib_memory/requests/<request-folder>/`
*   Out of scope: plan, questionnaire, and implementation records (defined by their own conventions or removed)

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

***

## 3. File Naming, Location & Write Behavior (Normative)

*   File name **must** follow the pattern: `analysis-<request_id>.md`
    where `<request_id>` is the active request ID (e.g. `analysis-R-20260509-2313.md`).

*   **Two-phase placement rule:**
    1.  **Active phase** — while the request is open, `analysis-<request_id>.md` resides at `.aib_memory/analysis-<request_id>.md` (workspace root of `.aib_memory/`, NOT inside the request subfolder).
    2.  **Archived phase** — upon successful implementation completion, `analysis-<request_id>.md` is moved by `move-request-artifacts.py` to `.aib_memory/requests/<request-folder>/analysis-<request_id>.md` (ID suffix preserved) before `close-request.py` marks the request Closed.

*   Exactly one analysis file per request **MAY** exist at a time.

*   Re-runs of `aib-analyze.md` **must** fully replace (overwrite) the active copy at `.aib_memory/analysis-<request_id>.md`. Appending to, prepending to, or partially editing the existing file is PROHIBITED. The prior file content is discarded entirely; the output is always written from scratch as a complete, self-contained document.

*   Version metadata (for example: version/author/status headers) **must not** be embedded in the analysis file. Versioning is handled by VCS.

***

## 4. Mandatory Structure

Each analysis file **must** contain the following sections in the exact order:

1. **Overview** **[REQ]**
2. **Files Read During This Analysis Run** **[REQ]**
3. **Input Interpretation** **[REQ]**
4. **Research Results** **[REQ]**
5. **Implementation Alternatives** **[REQ]**

***

### 4.1 Overview

This section is for human review and auditability only; `implement` MUST NOT read or act on it. Fully replace on every re-run.

**Mandatory content:**

- Request ID

- Request title

- `### Background` — Context explaining why the change is needed, sourced from the developer's `## Input` content.

- `### Scope` — Clear definition of what is included in the change, listing impacted functional areas, components, domains, or documents.

- `### Out of scope` — Items intentionally excluded from the request.

**Rules:**

- Each sub-section (`### Background`, `### Scope`, `### Out of scope`) MUST contain at least one sentence.

- On every re-run, fully replace this section.

***

### 4.2 Files Read During This Analysis Run **[REQ]**

List every workspace file read during this analysis run.

- Each entry MUST be a workspace-relative file path.

- Include all files read for preflight, convention loading, and analysis drafting.

- This section MUST NOT be empty.

***

### 4.3 Input Interpretation **[REQ]**

This section contains an AI-generated, specification-grade interpretation of the developer's original `## Input` content. It rewrites the developer's intent using correct product terminology (from `context.md`) and relevant external domain knowledge. It is written in third-person specification prose. Its primary purpose is to serve as the authoritative source material for the Answer Application Sub-flow when creating `request-<request_id>.md` on re-run without access to the archived `input.md` (GC-01 compliance).

**Rules:** MUST be present in every analysis run (first pass and re-run). MUST faithfully represent developer intent — enrichment, not replacement. MUST NOT be empty.

***

### 4.4 Research Results **[REQ]**

This section is the primary AI reasoning artifact for the request. It documents the AI's full analytical thinking — workspace findings, relevant industry knowledge, feasibility assessment, and observations.

**Mandatory content:**

- Workspace pattern-scan findings: impacted components, cross-reference issues, relevant prior solutions found in the workspace.

- Industry knowledge: best practices and external benchmarking relevant to the request topic. At minimum 3 findings from established frameworks, open-source communities, or industry literature, each with an applicability assessment.

- AI Agent critique: a bullet-list review of all issues found in the request itself and in every workspace file read during this analysis run. Not limited to the current request scope. Each issue is listed as a bullet regardless of whether it relates to the request. Issue types include: misalignment, inconsistencies, logical errors, redundancies, misplaced content, unclear wording, broken cross-references, format drift, and other quality concerns.

**Rules:**

- Summarize findings and implications; do not embed external links.

- MUST NOT be empty or contain only stub notices.

- `implement` MUST NOT read or act on this section.


***

### 4.5 Implementation Alternatives **[REQ]**

This section is the primary driver for Q-block generation. It MUST be completed before any Q-block is written.

**Mandatory content:**

For each implementation decision fork identified in the request scope, define a named decision block containing:

  - Identification of the specific task or step where this decision applies, plus an explanation of why the alternatives exist.

  - Two or more named alternative approaches, each with:
    - A one-sentence description.
    - Key trade-offs (benefits and drawbacks).
    - Expected codebase impact.

  - The resolution: tag and rationale per the classification rules in `aib-analyze.md` section 7.3.2.
    - Tag `ask` — a Q-block MUST be raised for developer input. The AI MUST NOT express a preference or steer the developer toward any option. Present choices neutrally.
    - Tag `resolve-autonomously` — ONLY when the developer's own `input.md ## Input` text OR a named, specific section of a workspace convention file explicitly and unambiguously resolves the fork. The rationale MUST quote or cite the exact source text and file path. External benchmarking, industry best practices, and AI judgment are NOT valid justifications for this tag.

- A `### Decision Points` section using a heading/sub-heading list — one `#### Fork: <name>` level-4 heading per fork, each containing bullet list items for Tag and Rationale/Resolution.

- If no decision forks are identified, include a single entry documenting that fact.

**Rules:**

- At least one named alternative MUST be documented per decision fork.

- When in doubt whether to tag `ask` or `resolve-autonomously`, always tag `ask`.

- MUST NOT be empty.

- Fully replaced on every analysis re-run.

***

## 5. Maintenance Rules (Normative)

*   Idempotence: same memory state and same request should converge to same analysis intent.
*   Change drivers: update analysis when scope changes, new evidence appears, or risk state changes.
*   Closure: once a request is closed in `requests_register.md`, analysis remains unchanged except factual corrections.

***

## 6. Formatting Requirements

*   All headings must use `##` or `###` consistent with this convention.
*   Bullet lists must use `- `.
*   Make a list of sub-bullets if the bullet text is split by symbols like `;`
*   In case of enumerated parts in a single list item - position them in a sublist
*   Tables must use standard GitHub Markdown table syntax.
*   No HTML is allowed.
*   No images, diagrams, embeds, or external hyperlinks.
*   The document must be deterministic (same inputs -> same output intent).
*   Separate chapters, bullets with empty lines for readability

***

## 7. Determinism Rules (Normative)

*   Given the same memory state and request input, analysis output intent must be identical.
*   AI must not guess beyond request scope.
*   If request ambiguity exists that cannot be resolved internally, create a `Q<nnn>` question block in `plan-<request_id>.md` -> `## Decisions` instead of making assumptions.

***

## 8. Prohibited Content

*   Secrets, private keys, credentials, tokens, or sensitive PII.
*   External hyperlinks.
*   Embedded images or diagrams.
*   In-file version/author/status metadata headers.

***


