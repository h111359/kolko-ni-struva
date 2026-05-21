# Coding CSS Convention

**Scope:** Normative  
**Applies to:** All CSS and SCSS/Sass files (`.css`, `.scss`, `.sass`, `.less`) created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines CSS-specific commenting and code-quality rules to ensure that AI-generated stylesheets are organized, understandable, and maintainable by front-end developers without additional context from the original author.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.css`, `.scss`, `.sass`, and `.less` files created or modified by the AI Automation Agent.
- Inline `<style>` blocks within HTML files when the block exceeds 10 lines.

Out of scope:
- Minified or generated CSS output files.
- CSS-in-JS (e.g., styled-components) — apply `coding-javascript-convention.md` for those files.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every CSS file MUST begin with a block comment header.

The header MUST contain:

- The file name and a one-sentence description of the stylesheet's scope or purpose.
- A brief list of the main sections or components styled within the file.

Example:

```css
/*
 * dashboard.css: Styles for the main application dashboard layout.
 * Sections: Layout Grid, Navigation Bar, Summary Cards, Data Table, Footer.
 */
```

---

## 4. Section Delimiter Comments

Every logically distinct section of a CSS file MUST be preceded by a section delimiter comment.

A section corresponds to a distinct UI component, layout region, or state group (e.g., base styles, typography, form elements, responsive breakpoints).

Example:

```css
/* ============================================================
   Navigation Bar
   ============================================================ */
```

---

## 5. Rule-Level Comments

A CSS rule set MUST be accompanied by a preceding comment when:

- The selector is non-obvious or relies on specificity tricks.
- The property values include magic numbers (e.g., `z-index: 9999`, `margin-top: -7px`).
- The rule implements a browser-specific workaround or hack.

The comment MUST explain the reason for the non-obvious choice.

Example:

```css
/* Compensate for the fixed header height (60px) to avoid content overlap */
.main-content {
    margin-top: 60px;
}
```

---

## 6. Magic Numbers in CSS

Numeric values for `z-index`, negative margins, percentage-based widths derived from calculations, and pixel-perfect offsets MUST be accompanied by a comment explaining the value's origin or business rule.

SCSS/Sass SHOULD use named variables for repeated magic values.

---

## 7. SCSS/Sass Variables and Mixins

Every SCSS variable defined at the top of a file or in a variables partial SHOULD have an inline `//` comment describing its purpose and semantic meaning (e.g., "Primary brand color used for buttons and links").

Every mixin MUST have a preceding comment block that describes:

- The mixin's purpose.
- Each parameter's name, type, and default value.

---

## 8. Responsive Breakpoints

Every `@media` query MUST be preceded by a comment declaring the target device type or screen size range and the layout change it implements.

Example:

```css
/* Tablet portrait and below (max 768px): collapse two-column grid to single column */
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
    }
}
```

---

## 9. Code Quality Rules

- `!important` is PROHIBITED unless accompanied by a comment explaining why specificity cannot be resolved by selector restructuring.
- Duplicate property declarations within the same rule set (without a comment explaining the intentional fallback) are PROHIBITED.
- Vendor-prefixed properties (`-webkit-`, `-moz-`, etc.) MUST be accompanied by a comment stating the targeted browser and minimum version.
- Color values MUST use named variables or design tokens in SCSS; raw hex or RGB literals in `.css` files MUST be commented with the semantic color name (e.g., `/* Primary brand blue */`).
