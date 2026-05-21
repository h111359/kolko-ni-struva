# Coding General Convention

**Scope:** Normative  
**Applies to:** Every source-code file created or edited by the AI Automation Agent during any `implement` workflow run, regardless of programming language or technology.

---

## 1. Purpose

This convention establishes the minimum baseline commenting requirements and code-quality hygiene rules that MUST be applied to **all** code files produced or modified by the AI Automation Agent. Language-specific conventions extend these rules; they do not replace them.

The goal is to ensure that every piece of AI-generated code is self-documenting, reviewable, and maintainable without requiring the reviewer to reverse-engineer intent from logic alone.

---

## 2. Scope & Normative Language

This convention applies to:

- All source-code files created or edited by the AI Automation Agent as part of any `implement` action.
- All programming languages and technology stacks (Python, SQL, DAX, JavaScript, TypeScript, CSS, HTML, C#, Scala, and framework variants thereof).

Out of scope:
- Existing code files that are not touched during the current `implement` run.
- Documentation-only files (e.g., `.md`, `.txt`, `.json` config files) — commenting rules do not apply to those file types.
- Automated test-generated artefacts (e.g., coverage reports, build outputs).

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header Comment

Every source-code file MUST begin with a file-level header comment placed before any import statements, `use` directives, or non-comment code.

The header MUST contain at minimum:

- A one-sentence description of the file's purpose.
- The primary owner or context reference (e.g., module name, component name, or AIB request ID if applicable).

The header SHOULD also include:

- A brief list of the file's main responsibilities or public surface.

The header MUST NOT contain:

- Author names, email addresses, or personal identifiers.
- Auto-generated timestamps or version numbers that are not maintained by VCS.

Example (language-agnostic representation):

```
<comment-syntax>
  <filename>: <one-sentence purpose description>.
  Part of <module/component/context>.
  Responsibilities: <comma-separated list of responsibilities>.
</comment-syntax>
```

---

## 4. Function, Method, and Class Docstrings

Every **public** function, method, and class MUST have a docstring or equivalent doc-comment explaining:

- What it does (not how it does it).
- The meaning of each parameter (name and what it represents).
- The return value (what it is, not just its type).
- Any side effects or raised exceptions that a caller must know about.

Every **private or internal** function or method SHOULD have a docstring if its purpose is not immediately obvious from its name and parameters alone.

A docstring is considered "immediately obvious" only if the function name is a verb-noun pair that fully describes the operation and the parameters have self-explanatory names.

Class docstrings MUST describe:

- The concept or entity the class represents.
- Key invariants or ownership rules (e.g., "owns its database connection").

---

## 5. Inline Comments for Non-Obvious Logic

Inline comments MUST be added to any code block that:

- Implements a non-trivial algorithm or a workaround for a known limitation.
- Contains a magic value that is not immediately explained by context (see Section 7).
- Produces a side effect that is not reflected in the function or variable name.
- Has a performance trade-off that justifies an unusual pattern.

Inline comments SHOULD explain **why** the code does what it does, not **what** it does when the what is already clear from reading the code.

Inline comments MUST NOT simply restate the code in natural language:

```
# WRONG: Increment counter by one
counter += 1

# RIGHT: Compensate for the off-by-one error in the upstream API response index
counter += 1
```

---

## 6. TODO and FIXME Markers

TODO and FIXME markers MUST include a brief description of the outstanding task or issue.

A marker MUST NOT be left with an empty description or only a name/date.

Examples:

```
# TODO: Replace with batch query to avoid N+1 problem once pagination is implemented
# FIXME: This throws on empty input; guarded upstream but add defensive check here
```

---

## 7. No Magic Numbers or Magic Strings

Literal numeric or string values whose meaning is not obvious from immediate context MUST be assigned to a named constant defined adjacent to its first use, at the module level, or in a dedicated constants file.

The constant name MUST convey the meaning of the value:

```
# WRONG: if status == 3:
# RIGHT: PENDING_REVIEW_STATUS = 3; if status == PENDING_REVIEW_STATUS:
```

---

## 8. No Dead Code

The AI Automation Agent MUST NOT generate files that contain:

- Commented-out code blocks left in place (unless the comment explicitly states why they are retained and references a tracking item).
- Unused imports, variables, functions, or classes.
- Unreachable code paths.

If code is temporarily disabled for a specific, documented reason, a TODO or FIXME marker (see Section 6) MUST accompany it.

---

## 9. Consistent Formatting

Generated code MUST follow consistent indentation within any given file:

- MUST NOT mix tabs and spaces within a file.
- MUST NOT leave trailing whitespace on lines.
- Functions and classes MUST be separated by consistent blank-line spacing per the applicable language convention.

---

## 10. Language-Specific Convention Loading

When the AI Automation Agent creates or edits files of a specific language, it MUST also read the corresponding language-specific convention file listed in `aib-implement.md` and apply its rules in addition to the rules in this document.

Language-specific rules take precedence over general rules only when they explicitly address the same topic with a more precise requirement.

---

## 11. Code Quality Rules

The AI Automation Agent MUST ensure:

- Each function or method has a single, clearly defined responsibility (single-responsibility principle).
- Deeply nested logic (more than three levels of indentation) SHOULD be refactored into named helper functions with explanatory docstrings.
- Error handling MUST be explicit; silent exception catching (bare `except`, `catch (Exception e)`) is PROHIBITED unless the rationale is documented in a comment.
- Variable and function names MUST be descriptive and unambiguous. Single-letter names are permitted only as loop counters in well-understood idiomatic patterns.
