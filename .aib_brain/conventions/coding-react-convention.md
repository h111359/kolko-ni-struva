# Coding React Convention

**Scope:** Normative  
**Applies to:** All React component files (`.jsx`, `.tsx`), React-specific hook/context files, API service layers, state management modules, and build/deploy configuration created or edited by the AI Automation Agent during any `implement` workflow run.  
**Extends:** `coding-general-convention.md` and `coding-javascript-convention.md` — all rules defined in both MUST be applied in addition to the rules below.

---

## 1. Purpose

This convention defines framework- and tool-agnostic architectural rules for React codebases. It applies equally to greenfield and brownfield projects regardless of which specific state library, HTTP client, or build tool is in use.

The goals are:

- Components cleanly separated into logic and presentation.
- State managed predictably through a single, consistent approach per project.
- Network calls isolated from UI code.
- Backend data typed, mapped, and validated at the API boundary.
- Builds reproducible and deployable.

---

## 2. Adaptability Principle

- The agent MUST inspect the existing codebase to identify established patterns, libraries, and directory structures **before** generating new code.
- New code MUST conform to the conventions already present in the repository unless the task explicitly requests a migration or refactor.
- The agent MUST NOT introduce a new library, client, or tool that serves the same purpose as one already in use.
- All rules in this convention describe **what** must be achieved (the architectural constraint), not **which tool** achieves it. Specific tools are mentioned only as illustrative examples.

---

## 3. Scope & Normative Language

This convention applies to:

- All `.jsx` and `.tsx` files containing React components, custom hooks, or context definitions.
- State management modules (stores, slices, atoms, providers, etc.).
- API/service layer modules that encapsulate network requests.
- Data mapping, transformation, and validation modules at the API boundary.
- Build and bundler configuration files.
- Higher-order components and render-prop components.

Out of scope:

- Plain utility modules that are not React-specific — apply `coding-javascript-convention.md`.
- Stylesheets, test files — apply the relevant convention for those types.

Normative keywords **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, and **MAY** are interpreted per BCP 14 (RFC 2119 / RFC 8174).

---

## 4. File-Level Header

Every React component file MUST begin with a block comment header that:

- Names the component or hook defined in the file.
- Describes its UI responsibility and where it fits in the application.

Example:

```jsx
/**
 * ProductCard.jsx: Presentational card component for displaying a single product.
 * Rendered by ProductGrid in the catalog and search results views.
 */
```

---

## 5. Component Architecture — Logic / View Separation

### 5.1 Principle

Logic and rendering MUST be separated into two distinct concerns. The **custom hook is the unit of that separation** — not the file. A dedicated hook and its consuming component MAY co-exist in a single file when the feature is self-contained; they MUST be split into separate files when the hook is shared across multiple components or the combined file exceeds ~100 lines.

| Layer | Responsibility | Naming Convention |
|-------|---------------|-------------------|
| **Logic** | State, effects, event handlers, data-fetching orchestration | `use<Feature>Logic.ts` (own file when shared or complex) |
| **View** | Rendering; receives data and callbacks primarily via props | `<Feature>.tsx` or `<Feature>View.tsx` |

A separate container/glue file (`<Feature>Container.tsx`) SHOULD NOT be created solely to wire one hook to one view. The component itself serves that role.

### 5.2 Rules

- All stateful logic (state, effects, event handlers, data-fetching calls) MUST be encapsulated in a `use<Feature>Logic` hook, not scattered inline in the JSX return.
- View components MUST NOT call data-fetching hooks or trigger side effects directly. They MUST receive data and callbacks via props or via the feature's logic hook called in the same component.
- View components MAY call pure, non-stateful hooks for rendering concerns: `useRef` (DOM handles), `useMemo` / `useCallback` (stable references and memoized derivations), and context hooks scoped to theme or localization.
- Logic hooks MUST be independently testable without rendering a component.
- The logic hook's return value MUST be the sole source of data wired into the view's props when the two are in the same component.

### 5.3 Example Structures

**Single-file (co-located hook + component) — use for self-contained features up to ~100 lines:**

```
src/features/product/
├── Product.tsx               // Logic hook defined and consumed here
├── product.types.ts          // Shared interfaces/types
└── index.ts                  // Public barrel export
```

**Split-file (separate hook) — use when the hook is shared or the file grows large:**

```
src/features/product/
├── useProductLogic.ts        // Logic hook: data fetching, local state
├── ProductView.tsx           // View: renders product UI from props
├── product.types.ts          // Shared interfaces/types
└── index.ts                  // Public barrel export
```

### 5.4 Decision Rule

| Condition | Structure to use |
|-----------|------------------|
| Hook used by a single component AND file ≤ ~100 lines | Co-locate hook and component in one file |
| Hook shared by two or more components | Extract hook to its own `use<Feature>Logic.ts` file |
| Component file exceeds ~100 lines | Split into `use<Feature>Logic.ts` + `<Feature>View.tsx` |
| Pure presentational leaf with no logic whatsoever | Single file, no hook needed |

---

## 6. Custom Hook Documentation & Design

Every custom hook (functions prefixed with `use`) MUST have a JSDoc block that describes:

- What stateful logic or side effect it encapsulates.
- Parameters it accepts.
- The shape of the return value.

Custom hooks MUST NOT return JSX. They MUST return data and callbacks only.

Logic hooks SHOULD be independently testable without rendering a component.

---

## 7. State Management

### 7.1 Guiding Principles

- The agent MUST use the state management approach already established in the project.
- If no state management exists yet, the agent MUST choose the simplest option that satisfies the requirements.
- State MUST live at the narrowest scope that still allows all consumers to access it.

### 7.2 State Categorization

| Category | Scope | Placement |
|----------|-------|-----------|
| **UI state** (toggles, modals) | Component-local | Local state hook inside the logic layer |
| **Feature state** (form data, wizard steps) | Feature-scoped | Scoped provider, local store slice, or feature-level atom |
| **Application state** (auth, user profile, theme) | Global | The project's global store or top-level provider |
| **Server/cache state** (fetched entities) | Global cache | The project's data-fetching/caching layer |

### 7.3 Structural Rules

- Each domain/feature MUST own its state definition in a dedicated file, grouped by domain.
- Selectors or derived-state accessors MUST be co-located with the state definition they read from.
- State collections MUST be normalized (flat, keyed by ID) unless the data model is inherently hierarchical and small.
- Derived data MUST be computed on read (via selectors, computed properties, or memoization) — never stored redundantly.
- State mutations MUST be immutable (via the library's immutability mechanism or explicit copies).
- Async side effects (e.g., data fetching triggered by state changes) MUST use the library's prescribed async pattern, not raw imperative dispatch of resolved values.
- Middleware or plugin additions MUST be documented with a comment explaining their purpose.
- Store/provider configuration MUST reside in a single, clearly named entry point file.

### 7.4 Context as State

When React Context is used for state sharing:

- Each context MUST reside in its own file.
- The provider MUST be exported separately from the consumer hook.
- Context SHOULD NOT be the sole state mechanism when the state graph is complex (more than 5 independent values or high-frequency updates). A comment MUST justify the choice.

---

## 8. Network Calls & API Layer

### 8.1 Separation Principle

All network calls MUST be isolated from component and hook code into a dedicated service/API layer. Logic hooks orchestrate calls via this layer — they MUST NOT contain raw HTTP invocations inline.

### 8.2 Structural Rules

- A single, centrally configured HTTP client MUST be the foundation for all requests.
- Authentication credentials MUST be attached via a centralized mechanism (interceptor, middleware, link, etc.) — not per-request in calling code.
- Error responses MUST be normalized into a consistent shape at the client level.
- Retry, timeout, and cancellation policies MUST be configured centrally; per-endpoint overrides MUST be documented.
- Base URLs MUST be read from environment variables, never hardcoded.
- Endpoint definitions MUST be grouped by domain in dedicated files within the API layer directory.

### 8.3 When Using a Data-Fetching/Caching Library

- The library's definition layer (endpoints, query keys, operations) replaces manual service files.
- The centralized client configuration MUST still underpin the library's transport layer.
- Caching, polling, and refetch behavior MUST be configured per-endpoint with a documenting comment.
- Cache invalidation strategy MUST be documented.
- Optimistic updates MUST include rollback logic.
- New endpoints MUST be added to the existing definition files (not in standalone files) unless creating a new domain.

### 8.4 When Using No Data-Fetching Library

- Each endpoint function MUST return a typed Promise and handle response parsing.
- The calling logic hook MUST manage loading, error, and data states (or delegate to a reusable async helper if the project provides one).
- Cancellation MUST be implemented for requests that can be superseded by navigation or unmounting.

---

## 9. Backend Data Handling

- Every backend response MUST be typed. Untyped or `any`-typed responses are NOT permitted. Types MUST be generated from a published schema when one is available; otherwise defined explicitly in the API layer.
- Raw API response shapes (DTOs) MUST NOT be used directly in components or state. They MUST be mapped to a frontend model at the API boundary via a pure mapper function before reaching the store or view.
- Every piece of fetched data has four states — loading, success, error, and empty — and all four MUST be explicitly handled in the logic layer and reflected in the view.
- Unbounded collections MUST use pagination or virtual scrolling. The frontend MUST NOT simulate pagination by slicing a full response.
- Cache staleness windows MUST be configured explicitly. Data MUST be invalidated or refetched after a mutation that affects it. Optimistic updates MUST include rollback logic.
- Sensitive fields (PII, credentials) MUST NOT be persisted to browser storage without encryption and MUST be annotated in the type definition.

---

## 10. Component Documentation Comment

Every exported React component MUST have a JSDoc block immediately above its function definition that describes:

- The component's purpose.
- A `@param {Object} props` block listing each prop with type and description.
- Accessibility or layout constraints (if any).

Example:

```jsx
/**
 * Renders a product card with image, title, price, and an add-to-cart button.
 *
 * @param {Object} props
 * @param {string} props.name - Product display name.
 * @param {number} props.price - Price in USD.
 * @param {string} props.imageUrl - Product thumbnail URL.
 * @param {function} props.onAddToCart - Callback when add-to-cart is clicked.
 */
function ProductCard({ name, price, imageUrl, onAddToCart }) {
```

---

## 11. useEffect and Lifecycle Comments

Every `useEffect` call MUST be preceded by a comment that:

- States the effect's purpose.
- Explains the dependency array choices.

Example:

```jsx
// Fetch product details when productId changes.
// fetchProduct is stable via useCallback — safe to omit from deps.
useEffect(() => {
    fetchProduct(productId);
}, [productId]);
```

---

## 12. useState and useReducer Comments

Complex state shapes MUST have a preceding comment describing the structure of the state object and the meaning of each field.

---

## 13. Props Validation

- When PropTypes are used, every defined PropType MUST match the component's JSDoc block.
- When TypeScript is used, the props interface MUST have a JSDoc comment describing the contract.

---

## 14. Build, Transpile & Deploy

### 13.1 General Principle

The agent MUST identify and work within the project's existing build toolchain. The agent MUST NOT switch tools unless explicitly asked to migrate.

### 13.2 Configuration Rules

- Build config MUST be version-controlled.
- Secrets MUST NOT appear in client-side bundles.
- Source maps MUST be enabled in development and either disabled or privately uploaded in production.

### 13.3 Transpilation & Compatibility

- TypeScript MUST be transpiled using the project's existing transpiler. The agent MUST NOT change it without explicit instruction.
- Browser targets MUST be declared explicitly (via browserslist config, the build tool's target field, or equivalent).
- Polyfills MUST be added only for features outside the declared targets.


### 13.7 Deployment

The convention does not mandate a hosting platform. The agent MUST follow the project's existing deployment configuration

---

## 15. Code Quality Rules

- Side effects MUST be isolated in the logic layer or handled by the data-fetching library; they MUST NOT appear in view components.
- Prop drilling beyond two levels MUST be replaced with a sharing mechanism (context, store, etc.) with a documenting comment.
- Complex conditional rendering MUST be extracted into a named variable or helper function.
- Barrel files MUST only re-export the public API of a feature — internal files MUST NOT be exported.
