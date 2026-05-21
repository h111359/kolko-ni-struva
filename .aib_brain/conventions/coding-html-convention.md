# Coding HTML Convention

**Scope:** Normative  
**Applies to:** All HTML files (`.html`, `.htm`) created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` — all rules defined there MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines HTML-specific commenting and code-quality rules to ensure that AI-generated HTML markup is accessible, readable, and maintainable for front-end developers and designers.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.html` and `.htm` files created or modified by the AI Automation Agent.
- HTML embedded in template files (e.g., Jinja2, Django templates, Blade) when the template contains meaningful structural HTML.

Out of scope:
- Auto-generated HTML output (e.g., compiled output from React or Angular build tools).
- Email HTML (where comment strategies differ significantly from web HTML).

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every HTML file MUST begin with an HTML comment header block immediately after the `<!DOCTYPE html>` declaration.

The header MUST contain:

- The file name and a brief description of the page or component's purpose.
- The primary component or page name.

Example:

```html
<!DOCTYPE html>
<!--
  dashboard.html: Main application dashboard layout.
  Component: Dashboard Page — displays summary metrics and navigation.
-->
<html lang="en">
```

---

## 4. Section Delimiter Comments

Every major structural section of the HTML MUST be preceded by a comment identifying the section.

Major structural sections include: header, navigation, main content, sidebar, footer, and any distinct functional block.

Example:

```html
<!-- ============================================================
     Navigation — Primary site navigation bar
     ============================================================ -->
<nav class="primary-nav">
```

---

## 5. Component and Template Comments

Reusable HTML components or template partials MUST include a comment at the top explaining:

- The component's name and purpose.
- Expected template variables or data attributes (for template files).

Example:

```html
<!--
  Component: product-card
  Purpose:   Displays a single product with image, title, price, and CTA button.
  Variables: product.name, product.price, product.image_url, product.detail_url
-->
```

---

## 6. Accessibility Comments

Every non-decorative `<img>` element MUST have a meaningful `alt` attribute; if the `alt` value is derived from logic, a comment MUST explain the derivation.

ARIA attributes (`aria-label`, `aria-describedby`, `role`) MUST be accompanied by an inline comment explaining why they are present when the reason is not immediately obvious from context.

---

## 7. Closing Tag Labels

For long HTML blocks, the closing tag of a major structural element SHOULD be followed by a comment identifying what it closes, when the opening tag is more than 30 lines away.

Example:

```html
</div> <!-- end .dashboard-grid -->
```

---

## 8. Code Quality Rules

- Inline styles (`style="..."`) are PROHIBITED except for dynamically computed values; use CSS classes.
- `<script>` and `<style>` blocks embedded directly in HTML MUST be commented with their purpose.
- All form inputs MUST have associated `<label>` elements; unlabelled inputs MUST have a comment explaining how they are accessible.
- Deprecated HTML elements (`<font>`, `<center>`, `<marquee>`, etc.) are PROHIBITED.
- The `lang` attribute on the `<html>` element MUST be set and its value MUST match the page's primary language.
