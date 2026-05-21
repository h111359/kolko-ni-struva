# Coding Python Convention

**Scope:** Normative  
**Applies to:** All Python source files (`.py`) created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines Python-specific commenting, docstring, and code-quality rules that supplement the general coding convention. It ensures that AI-generated Python code is idiomatic, readable, and consistent with the Python community's established practices.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.py` files created or modified by the AI Automation Agent.
- Both application code and test code.

Out of scope:
- Python configuration files (e.g., `setup.py`, `pyproject.toml`) where comment style differs from application code.
- Jupyter notebook cells (`.ipynb`) — apply best-effort only.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every Python file MUST begin with a module-level docstring (not a `#` comment) as the very first statement after the optional shebang line.

The module docstring MUST:

- Be enclosed in triple double-quotes (`"""`).
- Describe the module's purpose in one to three sentences.
- Reference the owning component or AIB request if applicable.

Example:

```python
"""
menu.py: CLI menu rendering and user-input dispatch for the AIB interface.
Part of the AIB core interaction layer.
"""
```

---

## 4. Function and Method Docstrings

Every public function and method MUST have a docstring.

Docstrings MUST use triple double-quotes (`"""`).

The docstring MUST follow the baseline format (what it does, parameters, return value, side effects). Any format that captures this information is acceptable per the general convention; NumPy or Google style is RECOMMENDED but not required.

Baseline format example:

```python
def load_convention(path: str) -> str:
    """
    Load the content of a convention file from disk.

    Args:
        path: Workspace-relative path to the convention file.

    Returns:
        The full text content of the convention file.

    Raises:
        FileNotFoundError: If the specified path does not exist.
    """
```

Private functions (prefixed with a single underscore) SHOULD have a docstring unless the name and signature are fully self-explanatory.

---

## 5. Class Docstrings

Every class MUST have a class-level docstring that:

- Describes the concept or entity the class represents.
- States whether the class owns shared resources (e.g., database connections, file handles).
- Lists key public attributes or properties if they are not documented by type annotations alone.

---

## 6. Inline Comments

Inline comments MUST use the `#` prefix followed by a single space.

Inline comments MUST describe **why** the code behaves as it does, not **what** it does.

Type: ignore comments MUST include a brief explanation of why the type check is suppressed.

---

## 7. Type Annotations

All public function signatures MUST include type annotations for parameters and return values.

Type annotations SHOULD also be used for class attributes and local variables when the type is not obvious from the assignment.

---

## 8. Constants

Module-level constants MUST be in `UPPER_SNAKE_CASE` and placed near the top of the file, after imports and before class or function definitions.

Every constant SHOULD have a brief `#` inline comment explaining its meaning if not obvious from the name.

---

## 9. Imports

Import statements MUST be grouped in this order, separated by a blank line:

1. Standard library imports.
2. Third-party library imports.
3. Local application imports.

Each group MUST be sorted alphabetically.

Wildcard imports (`from module import *`) are PROHIBITED.

---

## 10. Code Quality Rules

- Functions MUST NOT exceed 50 lines of executable code. If they do, they SHOULD be decomposed into named helper functions with docstrings.
- Exception handling MUST be specific; bare `except:` clauses are PROHIBITED.
- `pass` statements in non-empty function bodies are PROHIBITED without a comment explaining why the block intentionally does nothing.
