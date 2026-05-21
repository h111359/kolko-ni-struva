# Coding JavaScript Convention

**Scope:** Normative  
**Applies to:** All JavaScript files (`.js`, `.jsx`, `.mjs`, `.cjs`) created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines JavaScript-specific commenting, documentation, and code-quality rules to ensure that AI-generated JavaScript code is readable, maintainable, and self-documenting in both browser and Node.js environments.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.js`, `.jsx`, `.mjs`, and `.cjs` files created or modified by the AI Automation Agent.
- Vanilla JavaScript, Node.js, and framework-agnostic JavaScript modules.

Out of scope:
- TypeScript files (`.ts`, `.tsx`) — apply the same rules with TypeScript-specific type annotations added.
- React component files — additionally apply `coding-react-convention.md`.
- Minified or bundled output files.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every JavaScript file MUST begin with a block comment header using `/** ... */` syntax.

The header MUST contain:

- The file name and a one-sentence description of the module's purpose.
- The primary responsibility or exported surface of the module.

Example:

```js
/**
 * apiClient.js: HTTP client wrapper for the AIB REST API.
 * Provides authenticated request helpers for GET, POST, PUT, and DELETE operations.
 */
```

---

## 4. Function and Method Documentation

Every exported or public function MUST have a JSDoc comment block immediately preceding its definition.

The JSDoc block MUST include:

- A brief description of what the function does.
- `@param` tags for every parameter, each with a name and a description.
- `@returns` tag describing what the function returns (or `@returns {void}` if nothing).
- `@throws` tag for any explicitly thrown errors the caller must handle.

Example:

```js
/**
 * Fetches a paginated list of requests from the API.
 *
 * @param {string} baseUrl - The base URL of the AIB API endpoint.
 * @param {number} page - The 1-based page number to retrieve.
 * @param {number} pageSize - The number of items per page.
 * @returns {Promise<Object[]>} A promise that resolves to an array of request objects.
 * @throws {Error} If the HTTP request fails or returns a non-2xx status code.
 */
async function fetchRequests(baseUrl, page, pageSize) {
```

Private helper functions SHOULD have a short `//` comment describing their purpose if not self-evident from the name.

---

## 5. Inline Comments

Inline `//` comments MUST be used for:

- Non-obvious control flow decisions (e.g., why a specific fallback or guard is needed).
- Complex regular expressions — every non-trivial regex MUST be preceded by a comment describing what it matches.
- Asynchronous patterns where the order of operations affects correctness.

---

## 6. Constants and Configuration

Module-level constants MUST be declared with `const` and named in `UPPER_SNAKE_CASE`.

Every constant SHOULD have an inline `//` comment explaining its purpose and acceptable value range if not clear from the name.

---

## 7. Error Handling

Every `catch` block MUST contain at minimum a comment or a meaningful error-handling action.

Silent `catch` blocks (those that catch an error and do nothing — no log, no rethrow, no fallback) are PROHIBITED.

---

## 8. Code Quality Rules

- `var` declarations are PROHIBITED; use `const` or `let`.
- Implicit global variable creation (assigning without declaration) is PROHIBITED.
- Functions exceeding 40 lines of executable code SHOULD be decomposed into named helper functions with JSDoc.
- Arrow functions used as callbacks SHOULD have a name or be assigned to a named constant when their purpose is non-trivial.
- Template literals MUST be used instead of string concatenation when constructing strings with more than one variable insertion.
