# Coding React Convention

**Scope:** Normative  
**Applies to:** All React component files (`.jsx`, `.tsx`) and React-specific hook or context files created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` and `coding-javascript-convention.md` — all rules defined in both MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines React-specific commenting and code-quality rules for AI-generated React components, hooks, and context providers. It ensures that component purpose, props, state, and side effects are clearly documented.

---

## 2. Scope & Normative Language

This convention applies to:

- All `.jsx` and `.tsx` files containing React components, custom hooks, or context definitions.
- Higher-order components and render-prop components.

Out of scope:
- Plain JavaScript modules used by React apps that are not themselves components or hooks — apply `coding-javascript-convention.md`.
- CSS Modules, styled-components files, or test files — apply the relevant convention for those types.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 3. File-Level Header

Every React component file MUST begin with a block comment header that:

- Names the component or hook defined in the file.
- Describes the component's UI responsibility and where it fits in the application.

Example:

```jsx
/**
 * ProductCard.jsx: Reusable card component for displaying a single product.
 * Rendered by ProductGrid in the catalog and search results views.
 */
```

---

## 4. Component Documentation Comment

Every exported React component MUST have a JSDoc block immediately above its function definition that describes:

- The component's purpose (what it renders and for what use case).
- A `@param {Object} props` block listing each prop with its expected type and description.
- Any important accessibility or layout constraints.

Example:

```jsx
/**
 * Renders a product card with image, title, price, and an add-to-cart button.
 *
 * @param {Object} props
 * @param {string} props.name - The product display name.
 * @param {number} props.price - The product price in USD.
 * @param {string} props.imageUrl - URL for the product thumbnail image.
 * @param {function} props.onAddToCart - Callback invoked when the add-to-cart button is clicked.
 */
function ProductCard({ name, price, imageUrl, onAddToCart }) {
```

---

## 5. Custom Hook Documentation

Every custom hook (functions prefixed with `use`) MUST have a JSDoc block that describes:

- What stateful logic or side effect the hook encapsulates.
- Parameters the hook accepts.
- The shape of the return value.

---

## 6. useEffect and Lifecycle Comments

Every `useEffect` call MUST be preceded by a `//` comment that:

- States the effect's purpose (what side effect it produces).
- Explains the dependency array choices, especially why specific dependencies are included or excluded using `eslint-disable` comments.

Example:

```jsx
// Fetch product details when the productId changes.
// Re-runs only on productId change; fetchProduct is stable (useCallback).
useEffect(() => {
    fetchProduct(productId);
}, [productId]);
```

---

## 7. useState and useReducer Comments

Complex `useState` or `useReducer` state shapes MUST have a preceding comment describing the structure of the state object and the meaning of each field.

---

## 8. Props Validation

If PropTypes are used, every defined PropType MUST match the props described in the component's JSDoc block.

If TypeScript is used, the corresponding interface or type alias MUST have a JSDoc comment describing the component's props contract.

---

## 9. Code Quality Rules

- Components MUST NOT exceed 150 lines of code. Components that exceed this limit SHOULD be decomposed into smaller sub-components with their own documentation comments.
- Side effects (network calls, DOM mutations, subscriptions) MUST be isolated inside `useEffect` or custom hooks; they MUST NOT be triggered directly in render logic.
- Prop drilling beyond two component levels SHOULD be replaced with context or a state management solution, with a comment explaining the architectural decision.
- Conditional rendering with complex ternary expressions MUST be extracted into a named variable or helper function with a comment.
