# AIB Context Migration

## Goal

This prompt is executed during a migration from a previous version of AIB to a newer with
different convention for context.md formatting and content.

Reconstruct `.aib_memory/context.md` from a legacy `context.md` created by an earlier AIB memory version.

The migration is a **lossless semantic transformation**, not a summarization.

The output MUST conform exactly to:

- `.aib_brain/conventions/context-convention.md`

The archived context is the sole source of truth.

---

## Source

Identify the legacy context file as per the prompt.

No other files are migration sources.

Do NOT use:

- archived input.md
- archived aib-setup.yaml
- archived requests
- any previous migration artifacts

Use the current workspace only to understand the current product when resolving obvious inconsistencies.

---

## Definitions

### Atomic Semantic Fact

An atomic semantic fact is the smallest independently meaningful statement in the legacy context.

Examples:

- downloads with retry
- verifies ZIP integrity
- promotes temporary file
- skips already-downloaded archives

are FOUR different semantic facts.

Replacing them by

"downloads archives safely"

is NOT lossless.

---

## Migration Rules

### Minimal changes

If a part of the legacy context.md is already formatted accordingly the convention - copy it in the new context.md without change. Changes CAN be made while transfering to the new context.md only on those parts, which are deviating from the convention.

### Perform a semantic migration.

Semantic migration means information may be:

- reorganized
- reworded
- normalized
- merged when semantically identical

### Information MUST NOT be summarized merely to reduce document size.

Every unique semantic fact in the legacy context MUST be represented exactly once in the new context unless it is:

- obsolete
- duplicated
- contradictory to the current workspace
- prohibited by the current context convention

### The migration MUST NOT replace implementation details by higher-level abstractions.

Examples:

BAD
--------
Downloads archives safely.

GOOD
--------
Downloads with retry.
Verifies archive integrity.
Promotes temporary file atomically.

### Merge only statements that are literally equivalent.

Do not merge statements that differ in:

- behavior
- rationale
- conditions
- edge cases
- implementation details
- algorithms


### Relationships between facts are semantic facts.

If the legacy context describes

component A calls component B

or

A produces B consumed by C

that relationship MUST remain represented.

Do not flatten process descriptions into unrelated bullets.

### Design rationale is first-class information.

Whenever the legacy context explains WHY something exists,
that rationale MUST be preserved.

Never preserve only the conclusion.

### Modality-preserving section mapping

Map information according to both meaning and original modality.

- Normative product directives → Requirements.
- Descriptive architectural constraints → Product or Solution.
- Current implementation state → Solution.
- Assumptions, confidence, and validity conditions → Concepts or Solution.
- Product boundaries → Product unless the legacy explicitly expresses them as normative prohibitions.
- Negative normative rules → Requirements using MUST NOT.

MUST NOT convert:
- descriptive fact into MUST or MUST NOT;
- assumption into requirement;
- observed absence into prohibition;
- implementation choice into permanent product directive.

Preserve the original semantic modality even when section structure changes.

### Preserve edge cases

Edge cases, failure handling,
recovery behavior,
retry behavior,
validation,
atomicity,
ordering,
fallbacks,
and assumptions

are independent semantic facts.

They MUST NOT be omitted.

### Perform a semantically isomorphic migration.

The resulting document shall contain the same information content as the legacy context.

The organization may change.

The wording may change.

The information content must remain equivalent.

### The migration MUST NOT reduce information density.

If a paragraph contains ten independent facts,
the output must still contain ten independent facts.

Concise wording is encouraged.

Fewer facts are prohibited.

### Do not introduce synthesized architectural conclusions.

If the legacy context does not explicitly state something,
do not infer it solely because it appears reasonable.

The migration is archival, not analytical.

### Workspace

The current workspace MAY be consulted only to verify whether a legacy fact is demonstrably obsolete or contradictory. Workspace information MUST NOT be added to the migrated context unless already represented in the legacy context.

### ### Negative knowledge

Statements describing absence are independent semantic facts.

Examples include:

- no formal requirements register exists;
- no regulatory framework is documented;
- no runbook directory exists;
- no SLO, SLA, or on-call rotation is documented;
- no CI/CD configuration is present.

Do not replace an absence statement only with an inference derived from it.

For example:

"No SLO is documented; operations appear manually supervised"

contains TWO facts, and both MUST be preserved.

### Assumption decomposition

An assumption statement may contain several independent facts:

1. assumption conclusion;
2. confidence level;
3. evidence or rationale;
4. validity horizon;
5. invalidating conditions.

Each fact MUST receive an explicit destination.

Preserving only the assumption conclusion is semantic loss.

Exact Identifier Preservation

### Preserve verbatim unless demonstrably obsolete:

- product names;
- environment-variable names;
- table and column names;
- RPC names;
- file and directory paths;
- filename patterns;
- numeric counts;
- date-window sizes;
- confidence levels;
- proper nouns.

---

## Section Mapping

Map legacy information into the current context sections according to its meaning.

The mapping is semantic rather than structural.

INFORMATION PRESERVATION INVARIANT

Every atomic semantic fact from the legacy context
must satisfy exactly one of the following:

1. migrated unchanged
2. migrated after rewording
3. migrated into another section
4. removed because obsolete
5. removed because duplicate
6. removed because prohibited by context-convention

No other outcome is permitted.

---

## Preservation Requirements

Preserve all unique information including:

- product purpose
- scope boundaries
- concepts
- glossary items
- assumptions
- constraints
- requirements
- architectural decisions
- implementation details
- data architecture
- communication patterns
- integration points
- storage locations
- access patterns
- security model
- operational guidance
- operational risks
- deployment information
- developer guidance
- file structure

Telegraphic language may simplify grammar but MUST NOT remove semantic information.

The current context convention governs output structure and syntax only. It MUST NOT be used as justification for deleting a semantic fact unless a specific convention rule makes representation impossible.

---

## File Structure

Construct the File Structure section according to the context convention.

Pattern compression is permitted only for repetitive files.

Architecturally significant files and directories MUST remain represented.

---

## Quality Checks

Before producing the final document verify that:

1. Every legacy section has been examined.
2. Every unique semantic fact has been migrated or intentionally removed.
3. Every intentional removal satisfies one of the permitted removal rules.
4. The output conforms exactly to `context-convention.md`.
5. The output represents the current product without semantic loss.

If a conflict exists between preserving legacy structure and following the current context convention, preserve the information while adapting the structure to satisfy the convention.


Before producing the document, internally perform this audit:

For every paragraph of the legacy context:

identify every atomic semantic fact

verify each fact has exactly one destination
in the new document.

Do not emit the audit.

### Bidirectional equivalence check

After constructing the output, perform both checks:

1. Forward coverage:
   Every atomic legacy fact is entailed by exactly one output statement or has an approved removal record.

2. Reverse coverage:
   Every output statement is entailed by one or more legacy facts and introduces no new semantic assertion.

Formatting changes do not count as semantic equivalence when they alter:
- modality;
- scope;
- conditions;
- confidence;
- rationale;
- relationship;
- temporal meaning;
- negative meaning.