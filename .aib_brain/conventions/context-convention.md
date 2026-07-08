# Convention: context-convention.md

## Purpose
Defines required structure, statement syntax, formatting rules, and quality gates for `.aib_memory/context.md`. Single structural authority for context.md. `aib-refresh-context.md` MUST reference this convention. Product-agnostic; MUST NOT assume domain taxonomy or folder structure.

## Applicability
Applies to every `.aib_memory/context.md` in every AIB workspace, any domain, industry, or stack.

## Normative Language
Keywords MUST, MUST NOT, SHALL, SHOULD, MAY, OPTIONAL per BCP 14 (RFC 2119 + RFC 8174).

## Document Title
- First line of `context.md` MUST be `# Product Context`.

## Valid Sections (7)
Exactly seven H2 section names are valid in `context.md`:

1. `Product`
2. `Concepts`
3. `Requirements`
4. `Solution`
5. `File Structure`
6. `References`
7. `Issues`

No other H2 headings are permitted in `context.md`.

## Statement Format Rules

### Product, Concepts, Solution
Each statement is a plain bullet line matching `- <text>`. No type-letter prefix, no modality prefix. No backtick or inline code formatting in statements.

Example:
```
- AIB is a minimal, model-agnostic framework for specification-driven development.
```

### Requirements
Each statement is a modality-prefixed bullet matching `- [MUST|MUST NOT|OPTIONAL]: <text>`. Any Requirements bullet not using one of these three modality prefixes is a format violation.

Example:
```
- MUST: Every change must be preceded by analysis and plan before code is written.
- MUST NOT: AI agents must not modify .aib_brain/ assets during implementation.
- OPTIONAL: Recordings directory may contain video tutorials.
```

### File Structure
Content is a human-readable indented directory tree. Bullet-statement format is NOT enforced in this section.

### References
Each entry is a `###` sub-heading followed by a `Location:` line and a `Summary:` line. Bullet-statement format is NOT enforced in this section.

An existing Reference entry MAY include an optional fourth line in the format `Update: false` (read-only extension) or `Update: true` (writable extension) after the `Summary:` line. Entries without an `Update:` line remain valid bibliographic references. The `Update:` flag line distinguishes extension registrations from plain references.

### Issues
Content is a plain bullet list where each entry matches `- <description>`. No sub-headings, status fields, or structured fields are permitted. Lifecycle rule: an Issues entry MUST be removed when the issue is resolved or no longer applicable.

Bullet-statement format IS enforced in this section: each line must match `- <text>`.

## Mandatory Sections
- `## Product` MUST be present and non-empty.
- `## Concepts` MUST be present.
- `## Requirements` MUST be present.
- `## Solution` MUST be present.
- `## File Structure` MUST be present.
- `## References` is optional; if absent, the file is still valid.
- `## Issues` is optional; if absent, the file is still valid.

Each section uses the atomic statement format defined in context-convention.md, with the exception of `## File Structure` (indented directory tree) and `## References` (sub-heading entries):

### Product`
plain-bullet statements describing AIB's purpose, stakeholders, and product boundaries. Format: `- <text>`. Each statement is a self-contained fact about what the product is, who uses it, and what its scope boundaries are.

### Concepts`
plain-bullet statements covering domain knowledge, key terms, and general facts about the problem space. Format: `- <text>`.

### Requirements`
modality-prefixed statements for product directives, constraints, and behavioral rules. Format: `- [MUST|MUST NOT|OPTIONAL]: <text>`. These are the normative rules the product follows.

### Solution`
Plain-bullet statements documenting architectural decisions and implementation approaches. Format: `- <text>`. These explain how the product works technically.

### Files Section
#### Format
Use indented tree, example:
```
.aib_memory/
  context.md - product context synthesis
.aib_brain/tools/
  verify-context.py - validates context.md format
scripts/
  release_bookkeeping.py - SemVer bump + log generation
```

### References Section
#### Format
Use `###` sub-heading for each reference, followed by `Location:` and `Summary:` lines. Example:
```
### Context Data Models
Location: /context/context-data-models.md
Summary: Defines the data model as extension for context.md, including section names, statement types, and file structure representation.
```


### Inclusion Rules
Include only directories + core architectural files. Ignore tests/config/assets/minor utilities unless they carry critical business logic.
Pattern compression: directory with >=3 similarly named items -> one summary line, example: logs/ - Contains N files matching version_vX.Y.Z_log.md.

## Uniqueness Invariant
Within each section, statement text MUST be unique (case-insensitive). Duplicate text in the same section is PROHIBITED. `edit-context.py` enforces uniqueness on insert.

## Telegraphic Language
Use concise telegraphic phrasing; drop unnecessary articles and helper verbs. Use standard abbreviations: req, res, auth, db, env, config, err, msg, btn.

## [PLANNED] Tag Specification

`[PLANNED]` is a permitted optional prefix on statement bullets in the `Product`, `Concepts`, `Solution`, and `Requirements` sections. It marks a statement as representing a future-intent feature not yet implemented.

Syntax:
- Product, Concepts, Solution: `- [PLANNED] <statement text>`
- Requirements: `- [PLANNED] MUST: <text>`, `- [PLANNED] MUST NOT: <text>`, or `- [PLANNED] OPTIONAL: <text>` (tag precedes modality prefix)

### [PLANNED] Lifecycle Rule

When the feature described by a `[PLANNED]` entry is implemented, the entry MUST be replaced with a plain untagged statement via a plan-driven `edit-context.py delete` + `edit-context.py insert` pair in the plan context update task. The `[PLANNED]` tag MUST NOT be removed by automated scanning; only plan-driven removal is authoritative.

## Pruning Rules
Aggressively remove historical context, old iterations, resolved questions, and deprecated features. `context.md` reflects CURRENT product state only.

**Carve-out:** `[PLANNED]` tagged entries are exempted from the "current state only" pruning rule. They are forward-looking markers with an explicit removal lifecycle, not stale historical content.

## Formatting Rules
1. UTF-8 Markdown only.
2. NO HTML tags.
3. NO images.
4. External refs as plain text only; no hyperlinks (no `https?://` URLs).
5. Heading hierarchy: `# Product Context` exactly once (H1); H2 limited to the 7 valid section names; H3 permitted inside `## References` only; H4+ forbidden (heading depth MUST NOT exceed H3).
6. Statements in `## Product`, `## Concepts`, `## Solution`, `## Requirements` MUST NOT use bold, italic, or backticks (inline code); plain text only.
7. Requirements statements MUST use modality prefix `MUST`, `MUST NOT`, or `OPTIONAL`.
8. No Markdown tables.
9. Each statement occupies exactly one line; no wraps or continuations.

## Quality Gates
`verify-context.py` MUST implement the following 12 checks. The file passes iff all 12 checks pass:

1. Document starts with `# Product Context`.
2. All H2 headings are one of the 7 valid section names.
3. `## Product` section is present and non-empty (at least one non-blank line after the heading).
4. `## Requirements` section is present.
5. `## Solution` section is present.
6. `## File Structure` section is present.
7. Every bullet line in `## Product`, `## Concepts`, and `## Solution` matches `- <text>` or `- [PLANNED] <text>` and does NOT contain a type-letter prefix or plain modality prefix. Every bullet line in `## Requirements` matches `- [MUST|MUST NOT|OPTIONAL]: <text>` or `- [PLANNED] [MUST|MUST NOT|OPTIONAL]: <text>`.
8. Every bullet line in `## Requirements` matches `- [MUST|MUST NOT|OPTIONAL]: <text>` or `- [PLANNED] [MUST|MUST NOT|OPTIONAL]: <text>`.
9. `## References` entries, if any, each have a `###` sub-heading followed by `Location:` and `Summary:` lines within 5 lines.
10. No line in the document contains an HTML tag, a Markdown table row (line starting with `|`), or a bare URL (`https?://`).
11. If a `## Issues` section is present, all entries in it are plain bullets matching `- <description>` where `<description>` is non-empty.
12. Every `Update:` line in a `## References` entry (if any) must have value exactly `false` or `true` (i.e., `Update: false` or `Update: true`).

## Relationship to Other Conventions
Governs only `.aib_memory/context.md`. Does NOT govern `.aib_brain` framework files. `aib-refresh-context.md` MUST reference this convention as sole structural authority for context.md.
