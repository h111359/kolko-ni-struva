# Coding UI/UX Convention

**Scope:** Normative  
**Applies to:** All design-related source files — including HTML layout files, CSS stylesheets, and front-end JavaScript/TypeScript files — that are created or edited by the AI Automation Agent during any `implement` workflow run with an explicit UI/UX design intent.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below. When files are also `.html`, `.css`, or `.js`/`.jsx` files, their respective language conventions MUST also be applied.

---

## 1. Purpose

This convention defines UI/UX-specific commenting and design-quality rules for AI-generated interface code. It ensures that design intent, accessibility rationale, interaction patterns, and visual constants are documented within the code so that developers and designers can understand, maintain, and extend the interface without external design specifications.

---

## 2. Scope & Normative Language

This convention applies to:

- HTML layout and template files with significant structural or layout responsibility.
- CSS and SCSS files implementing visual design systems (spacing, typography, color, motion).
- JavaScript and TypeScript files implementing user interaction logic (event handlers, animation, form validation feedback, modal/drawer behaviour).
- React component files whose primary purpose is detailed visual presentation or interaction.

Out of scope:
- Back-end logic files that happen to produce HTML output (e.g., server-side template rendering logic) — apply only the relevant server-side language convention.
- Design specification documents (e.g., Figma export notes, design tokens JSON files) — no comment rules apply to those artefacts.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. Design Intent Comments

Every major layout section, component, or visual region MUST have a preceding comment that states:

- The design intent: what experience or information hierarchy the element is meant to communicate.
- The target viewport or device context if the layout is device-specific.

Example:

```html
<!--
  Hero Section
  Design intent: Full-width banner communicating the primary value proposition.
  Target: Desktop (1024px+). Mobile variant collapses to text-only stack layout.
-->
<section class="hero">
```

---

## 4. Accessibility Documentation

Every interactive element (button, link, input, toggle, dialog, tab panel) MUST be accompanied by a comment in the markup or JavaScript that confirms:

- The element's accessible role.
- The keyboard interaction pattern it supports (e.g., Enter to activate, Escape to close, Arrow keys to navigate).
- Any ARIA attribute used and what it communicates to assistive technology.

Example:

```html
<!-- Dialog: traps focus when open; Escape key closes; aria-modal=true signals modal to screen readers -->
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
```

---

## 5. Design Token and Visual Constant Comments

CSS custom properties (CSS variables) and SCSS variables used for design tokens (colors, spacing, typography) MUST be documented with:

- The semantic name and its visual role (e.g., "Primary action color — used for all interactive affordances").
- The relationship to the design system (e.g., "maps to Primary/600 in the Figma token set").

Example:

```css
:root {
    /* Primary action color — all buttons, links, and focus rings. Maps to brand/primary-600. */
    --color-action-primary: #0057d8;

    /* Base spacing unit — all layout spacings are multiples of this value. */
    --spacing-base: 8px;
}
```

---

## 6. Interaction and Animation Comments

Every CSS transition, animation, or JavaScript-driven animation MUST have a comment explaining:

- The interaction it supports (e.g., "slide-in on menu open").
- The timing choice and why it reflects the intended user experience (e.g., "200ms — fast enough not to feel sluggish; stays under 300ms perceivable delay threshold").

Motion that is disabled via a `prefers-reduced-motion` media query MUST have a comment confirming accessibility compliance.

---

## 7. Component Variant and State Comments

Every CSS rule that targets a component state (`:hover`, `:focus`, `:active`, `:disabled`, `.is-loading`, `.has-error`) MUST be preceded by a comment describing the visual and interactive change the state represents.

Example:

```css
/* Disabled state: muted appearance and cursor change signal non-interactivity to users */
.btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
```

---

## 8. Responsive Layout Comments

Every responsive layout decision (breakpoint-specific override, grid change, hiding/showing elements) MUST be accompanied by a comment stating:

- The device type or screen size being targeted.
- The UX reason for the layout change (e.g., "Below 768px, sidebar moves below main content to preserve reading flow on mobile").

---

## 9. Code Quality Rules

- Hardcoded color values, font sizes, and spacing values MUST be replaced with design tokens or named CSS variables; any exception to this rule MUST be commented with the justification.
- `z-index` values MUST be commented with the stacking layer they represent (e.g., "above content (1), modals (100), tooltips (200), notifications (300)").
- Inline styles on interactive elements that affect user perception of affordance (color, opacity, cursor) are PROHIBITED; use CSS classes.
- Every form validation error message displayed to users MUST have a comment explaining the validation rule it communicates and its accessibility delivery method (e.g., via `aria-live` region, `aria-describedby`, or visible error label).
