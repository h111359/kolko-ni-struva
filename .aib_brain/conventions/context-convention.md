# Convention: context.md

## Purpose

This convention defines the required structure, section content guidance, formatting rules, and quality gates for `.aib_memory/context.md`. It is the single authoritative source for the structure of `context.md` and MUST be referenced by the `aib-refresh-context.md` prompt.

This convention is product-agnostic and MUST NOT embed assumptions about any specific product's domain taxonomy or folder structure.

## Applicability

This convention applies to every `.aib_memory/context.md` file in every workspace that uses the AIB framework, regardless of product domain, industry, or technology stack.

## Normative Language

The key words MUST, MUST NOT, SHALL, SHOULD, MAY, and OPTIONAL in this document are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174).

## Document Identity

- **Canonical file path:** `.aib_memory/context.md`
- **Encoding:** UTF-8
- **Format:** Markdown only. No HTML tags, no images, no external hyperlinks.
- **Authoring model:** Generated or modified by the `aib-refresh-context.md` prompt. Human edits are not expected but possible; 
- **Replacement semantics:** Every execution MUST fully replace the file. No append-only semantics apply.

---

## Section Structure

The document MUST contain the following sections, in the following order, using the exact headings specified. Additional subsections within each section are permitted using H3 and H4 headings. No section may be omitted; a mandatory section with no available content MUST include a stub notice as defined in the Stub Notice Format section below.

### Mandatory Section Order and Headings

1. `## Product Identity`
2. `## Domain Knowledge`
3. `## Concepts`
4. `## Constraints & Assumptions`
5. `## Requirements`
6. `## Architecture & Decisions`
7. `## Technical Design`
8. `## Data Architecture`
9. `## Security & Compliance`
10. `## Operations`
11. `## Development Practices`
12. `## Workspace File Inventory`

---

## Section Content Guidance

### Section 1 — Product Identity

**Purpose:** Establish what the product is — its name, version, primary purpose, and intended audience.

**MUST include:**
- Product name and version (or version range if relevant).
- One-paragraph purpose statement that a new team member can read and immediately understand what the product does.
- Primary actors or users.
- Production or operational status (e.g., active, deprecated, experimental).

**SHOULD include:**
- Key business outcome the product enables.
- Scope boundaries — what the product is NOT responsible for.

**MUST NOT include:**
- Technical implementation details (those belong in section 7, Technical Design).
- Marketing copy or aspirational language without factual basis.

---

### Section 2 — Domain Knowledge

**Purpose:** Capture the business domain knowledge required to understand why the product exists, how it fits into the broader organization, and all domain-specific terminology.

**MUST include:**
- Business domain and sub-domain the product operates in.
- Key business processes the product supports or automates.
- Organizational units or teams that own, operate, or consume the product.
- Critical external dependencies: external systems, data providers, regulatory bodies.
- Domain-specific terminology and acronyms in a `### Glossary` sub-heading within this section; each entry MUST follow the format `**<Term>**: <Definition>` on a single line, sorted alphabetically (no standalone Glossary section at document level).

**SHOULD include:**
- Business events or triggers that drive product activity.
- Key stakeholder groups and their primary interests.

**MUST NOT include:**
- Marketing or sales material.
- Internal organizational politics or aspirational intent without factual grounding.

---

### Section 3 — Concepts

**Purpose:** Define the product's guiding philosophy, conceptual principles, and domain-level abstractions that inform all design and implementation decisions.

**MUST include:**
- Conceptual entries (product philosophy, spirit, guiding principles) in definition-list format: `**Concept name**: one-sentence definition`, sorted alphabetically.
- Only conceptual and definitional entries; constraints and assumptions belong in Section 4.

**MUST NOT include:**
- Operational constraints or assumptions (those belong in Section 4, Constraints & Assumptions).
- Glossary terms or domain terminology (those belong in Section 2, Domain Knowledge).

---

### Section 4 — Constraints & Assumptions

**Purpose:** Explicitly capture all constraints and assumptions that govern the product's design, operation, and evolution.

**MUST include:**
- Technical constraints: platform, technology choices, API contracts, or integration requirements that cannot be changed.
- Organizational constraints: regulatory requirements, company policies, budget limits, audit requirements.
- Explicitly stated assumptions: what is assumed to be true at the time of documentation, with confidence level if known.
- Validity horizon: when key assumptions should be revisited.

**SHOULD include:**
- Dependencies that are outside the product team's control.
- Known risks attached to each constraint or assumption.

**MUST NOT include:**
- Speculative future constraints or assumptions that have no current evidence.
- Conceptual entries (those belong in Section 3, Concepts).

---

### Section 5 — Requirements

**Purpose:** List all functional and non-functional requirements so that a reader can understand what the product must do and how well it must do it.

**MUST include:**
- All functional and non-functional requirements verbatim with full detail — no summarization.
- Each requirement bullet MUST begin with a unique identifier — `FR-NNN` for functional requirements and `NFR-NNN` for non-functional requirements — followed by a colon and a space. Continuation content for the same requirement MUST be placed as a sub-bullet under its identified parent bullet rather than as a separate unlabelled top-level bullet.
- Known requirement priorities or MoSCoW classification for the top capabilities.

**SHOULD include:**
- Requirement IDs from the product's requirements document for traceability (plain text, no hyperlinks).
- Acceptance criteria for the most critical capabilities.
- Known requirement conflicts or open trade-offs.

**MUST NOT include:**
- Implementation details (those belong in section 7, Technical Design).

---

### Section 6 — Architecture & Decisions

**Purpose:** Capture the product's high-level structural design and all architectural decisions, including rationale and consequences.

**MUST include:**
- High-level component or system map (text-based; no diagrams). Each component named with its responsibility described in one sentence.
- Key integration points with external systems: names, protocols, direction of data flow.
- All architectural decisions in ADR style: decision taken, context and drivers, alternatives considered, rationale for choice, consequences and trade-offs.
- Technology stack summary: languages, frameworks, platforms, cloud providers, with rationale for major choices.

**SHOULD include:**
- Quality attributes prioritized by the architecture (e.g., availability over throughput over cost).
- Deployment topology summary: where components run and what hosts them.
- Known architectural risks or technical debt items.

**MUST NOT include:**
- Full ADR documents reproduced verbatim. Reference ADR IDs for traceability.
- Source code listings.

---

### Section 7 — Technical Design

**Purpose:** Provide enough technical detail that a developer unfamiliar with the codebase can understand how the product works internally.

**MUST include:**
- Module or component breakdown with brief responsibility descriptions.
- Key algorithms, formulas, or processing logic described at a conceptual level.
- Inter-component communication protocols and patterns (e.g., event-driven, REST, RPC, batch).
- Configuration and parameterization approach: where configuration lives and what is configurable.

**SHOULD include:**
- Notable design patterns applied and why.
- Performance-critical code paths or hotspots.
- Known technical constraints that affect implementation choices.

**MUST NOT include:**
- Full source code listings.
- Build, CI, or CD script content reproduced verbatim (summarize and reference paths instead).

---

### Section 8 — Data Architecture

**Purpose:** Capture the structure, lineage, quality standards, and access patterns for all data assets the product owns or consumes.

**MUST include:**
- Data sources: names, owners, ingestion method, refresh frequency.
- All data entities or models with key attributes and relationships.
- Data lineage summary: how data flows from source to output.
- Data storage locations and technologies.
- Data access patterns: who reads what data, in what form, and at what latency.

**SHOULD include:**
- Data quality rules and validation gates.
- Data retention and archiving policies.
- Sensitive data classifications (e.g., PII, confidential, restricted) with handling rules.
- Key metrics and KPIs derived from data.

**MUST NOT include:**
- Full schema DDL or raw query text reproduced verbatim (summarize and reference paths to schema files).

---

### Section 9 — Security & Compliance

**Purpose:** Capture the security posture and compliance obligations so that any developer or auditor can understand the product's security controls.

**MUST include:**
- Authentication and authorization model (e.g., OAuth2, RBAC, ABAC) with scope.
- Data protection measures: encryption at rest, encryption in transit, key management approach.
- Regulatory or compliance requirements the product must meet (e.g., GDPR, SOC2, HIPAA) with specific obligations described.
- Secrets management approach: where secrets are stored and the rotation policy.

**SHOULD include:**
- Network security controls: ingress and egress rules, VPN, private endpoints.
- Known security risks or open vulnerabilities with mitigations.
- Incident response responsibilities (role or team names, no personal contact details).

**MUST NOT include:**
- Actual secrets, credentials, keys, or tokens.
- Specific CVE identifiers or exploit details that could aid attackers.

---

### Section 10 — Operations

**Purpose:** Capture what is needed to operate, monitor, and support the product in production.

**MUST include:**
- Operational runbook or SOP summary: reference paths for detailed procedures; do NOT reproduce full runbooks verbatim.
- Observability setup: logging approach, key log sources, monitoring dashboards, alerting thresholds.
- SLO or SLA targets if defined.
- On-call responsibilities and escalation path using team or role names (no personal contact details).

**SHOULD include:**
- Deployment procedure summary: steps, tools, required approvals.
- Rollback procedure.
- Known operational risks or failure modes with mitigations.

**MUST NOT include:**
- Personal contact details or phone numbers.
- Credentials or access keys.

---

### Section 11 — Development Practices

**Purpose:** Capture the norms, tooling, and process standards that govern how contributors work on the product.

**MUST include:**
- Repository structure overview: key folders and their purpose.
- Developer setup steps at a high level; tool versions if significant.
- Branching strategy and PR or merge conventions.
- Testing strategy: test types used, coverage targets, test execution commands.
- CI/CD pipeline summary: what triggers it and what gates must pass before deploy.

**SHOULD include:**
- Code review standards: required approvals and automated checks.
- Linting, formatting, and type checking tools with configuration file references.
- Known developer experience pain points or unreliable test areas.

**MUST NOT include:**
- Full script or configuration file content reproduced verbatim.
- Personal development environment preferences.

---

### Section 12 — Workspace File Inventory

**Purpose:** Provide a quick structural reference of all non-excluded workspace files so that agents and developers can navigate the codebase without prior knowledge.

**MUST include:**
- All workspace-relative file paths discovered during supplementary read, sorted ascending.
- An entry for every directory and subdirectory present in the workspace (using a trailing slash, e.g., `scripts/`), sorted ascending alongside file entries.
- Exclusions applied: `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.git/`.
- When a directory contains three or more items that share a repeating naming pattern (e.g., per-request subfolders under `.aib_memory/requests/`, versioned log files under `logs/`, versioned archive files under `versions/`), do NOT list individual items as separate bullets. Instead, provide a single summary bullet for the directory in the format: `- \`path/\` — Contains <N> <type> items following the pattern \`<pattern>\`; individual items are not listed.`

**Format:**
- Present each entry as a Markdown bullet list item: `- \`path\` — description.`
- File entries: `- \`path/to/file.ext\` — One-sentence description of the file's content or purpose.`
- Directory entries: `- \`path/to/dir/\` — One-sentence description of the folder's role in the workspace.`
- All entries (files and directories together) MUST be sorted ascending by path.

**Description quality requirements:**
- Each description MUST be one sentence, representative of the file's content or purpose.
- Descriptions MUST NOT contain secrets, credentials, or PII.
- For repetitive request artifact files (`request.md`, `implementation.md`, `analysis.md` in per-request folders), a formulaic description derived from the request folder slug is acceptable.

**MUST NOT include:**
- Entries for excluded directories or their contents.

---

## Formatting Rules

1. The document MUST be UTF-8 encoded Markdown.
2. The document MUST NOT contain HTML tags.
3. The document MUST NOT contain images.
4. The document MUST NOT contain external hyperlinks. References to external sources MUST be plain text (author, title, year) only. URLs MUST NOT appear in the file.
5. Heading levels MUST follow this hierarchy:
   - `# Product Context` — document title (H1, exactly one, in the preamble).
   - `## <Section Name>` — mandatory and optional top-level sections (H2).
   - `### <Subsection Name>` — subsections within a section (H3).
   - `#### <Sub-subsection Name>` — deeper nesting if needed (H4; avoid when possible).
6. Bold text (`**text**`) MUST be used only for term definitions (in the Glossary) and critical callouts.
7. Lists MUST use Markdown bullet syntax (`- `) or numbered syntax (`1. `).
8. File paths and code identifiers MUST be wrapped in backticks.
9. Traceability references (e.g., `per ARCH-01`, `per RQT-02 FR-003`) MUST be plain text, not hyperlinks.
10. The document MUST begin with the preamble defined below.
11. Markdown tables MUST NOT appear anywhere in the document. Use nested bullet lists to represent structured multi-attribute data (for example, component maps, data entity tables, and comparison grids).
12. One blank line MUST appear between each top-level list item in every section. Consecutive list items with no blank line between them are prohibited.
13. Heading nesting MUST NOT exceed H3 (`###`) in any section. H4 (`####`) headings MUST NOT be introduced; use a sub-bullet or prose break instead.
14. Each bullet item MUST be a grammatically complete sentence and MUST end with a period. Incomplete sentence fragments as list items are prohibited.
15. Every section body MUST begin with at least one prose sentence before introducing a bullet list. A section body MUST NOT start directly with a bullet item without an introductory context sentence.
16. Each bullet or list item MUST NOT exceed two sentences. If the content of an entry requires more than two sentences to express, it MUST be split into two or more separate bullet items rather than combined into a single long entry.

---

## Preamble Format (Normative)

The document MUST begin with the following block, with the timestamp placeholder replaced by the actual generation timestamp in local project time:

```
# Product Context

> **Auto-generated** by `aib-refresh-context.md` on <YYYY-MM-DD HH:MM timezone>.
> Framework definition assets (`.aib_brain/`) are excluded by design — see `.aib_brain/` for AIB framework internals.
> This document is a synthesis of product documentation and workspace sources. It is fully replaced on each execution.
```

---

## Stub Notice Format (Normative)

When a mandatory section has no available source content, the section body MUST contain exactly the following line and nothing else:

```
*Not yet documented.*
```

A stub section MUST NOT be omitted from the document.

---

## Quality Gates

A generated `context.md` passes quality review if and only if all of the following are true:

1. **Structure completeness:** All 12 mandatory sections are present with the exact headings specified in this convention.
2. **Non-empty populated sections:** Every section for which source content exists has substantive content (not only a stub notice).
3. **Stub sections present:** Every mandatory section with no available source content contains the stub notice and is not omitted.
4. **Traceability:** Populated sections cite source document IDs (e.g., `per ARCH-01`) where applicable.
5. **Rebuildability:** A competent developer reading only `context.md` can understand: what the product does, why key decisions were made, what the data flows are, what security controls are in place, and how to develop and operate it.
6. **No verbatim reproduction:** Section content MUST summarize and synthesize source material; it MUST NOT reproduce full source documents.
7. **Determinism:** Re-executing the generating prompt with the same workspace state produces semantically equivalent content.
8. **No external hyperlinks:** The file contains no Markdown-formatted or plain-text URLs (no `http://` or `https://` strings).
9. **No `.aib_brain/` content:** The file MUST NOT contain content derived from `.aib_brain/` framework internals.
10. **Workspace inventory present:** Section 12 lists all non-excluded workspace files in the required format.
11. **No structural definitions in prompt:** The generating prompt contains no hardcoded section names, domain mapping tables, or scope summary tables; it references this convention instead.

---

## Relationship to Other Conventions

- This convention governs ONLY `.aib_memory/context.md`.
- It does NOT govern product-doc files under `.aib_memory/docs/` (governed by their respective per-document conventions).
- It does NOT govern any `.aib_brain/` framework files.
- The `aib-refresh-context.md` prompt MUST reference this convention as the sole structural authority for `context.md`.
