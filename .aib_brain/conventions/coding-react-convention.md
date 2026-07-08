# Coding React Convention
Scope: Normative | Applies to: .jsx/.tsx, hook/context files, API layers, state mgmt modules, build/deploy config; created/edited by agent during implement workflow
Extends: coding-general-convention.md + coding-javascript-convention.md — all rules apply
$Logic = use<Feature>Logic hook | $View = <Feature>.tsx | $API = dedicated API/service layer
Keywords MUST/MUST NOT/SHALL/SHOULD/MAY per BCP 14
## Purpose
Goals: logic/presentation separated; state via single consistent approach; network calls isolated from UI; backend data typed+mapped+validated at API boundary; builds reproducible
## Adaptability
Inspect existing codebase -> identify patterns/libs/dirs BEFORE generating code
New code MUST conform to existing conventions unless task requests migration/refactor
NO: introduce new lib/client/tool serving same purpose as existing; rules describe WHAT not which tool
## Scope
Applies: .jsx/.tsx components/hooks/context; state mgmt modules; $API layer; data mapping/validation at API boundary; build config; HOCs/render-prop components
OUT: plain utils -> coding-javascript-convention.md; stylesheets/tests -> relevant convention
## File Header
Every component file MUST start with block comment: component/hook name + UI responsibility + app placement
## Component Architecture: Logic/View Separation
Separation unit = custom hook, not file
[self-contained + <=100 lines] -> single file OK | [hook shared || file >100 lines] -> split files
Layer structure:
 Logic: state/effects/handlers/fetch -> use<Feature>Logic.ts [own file if shared/complex]
 View: rendering via props -> <Feature>.tsx or <Feature>View.tsx
NO: <Feature>Container.tsx solely to wire one hook to one view
Rules:
- All stateful logic MUST be in $Logic hook; NO: inline JSX
- View MUST NOT call data-fetch hooks or trigger side effects directly; receive via props or $Logic
- View MAY call: useRef, useMemo, useCallback, context hooks [theme/l10n only]
- $Logic MUST be independently testable without rendering
- $Logic return value MUST be sole data source for view props [same component]
Decision:
 [single hook + <=100 lines] -> co-locate
 [hook shared 2+ components] -> extract to use<Feature>Logic.ts
 [file >100 lines] -> split use<Feature>Logic.ts + <Feature>View.tsx
 [pure presentational, no logic] -> single file, no hook
src/features/product/ [single]: Product.tsx | product.types.ts | index.ts
src/features/product/ [split]: useProductLogic.ts | ProductView.tsx | product.types.ts | index.ts
## Custom Hook Docs
Every use* fn MUST have JSDoc: encapsulated logic/side-effect; params; return shape
NO: return JSX from hooks; return data+callbacks only | SHOULD be independently testable
## State Management
Use existing state mgmt approach; [none exists] -> choose simplest satisfying reqs
State MUST live at narrowest scope with access for all consumers
Categories:
 UI state (toggles/modals) -> local state in $Logic
 Feature state (forms/wizard) -> scoped provider/slice/atom
 App state (auth/profile/theme) -> global store/provider
 Server/cache state -> data-fetching/caching layer
Rules:
- Each domain/feature owns state in dedicated file grouped by domain
- Selectors co-located with state definition
- Collections MUST be normalized [keyed by ID] unless inherently hierarchical+small
- Derived data computed on read; never stored redundantly
- Mutations MUST be immutable
- Async side effects MUST use library's prescribed async pattern; NO: raw imperative dispatch
- Middleware/plugins MUST have comment explaining purpose
- Store/provider config in single clearly named entry file
[React Context]: each context own file; provider exported separately from consumer hook
Context SHOULD NOT be sole mechanism [>5 independent values || high-freq updates]; comment MUST justify
## Network Calls & API Layer
All network calls isolated into $API; $Logic orchestrates via $API; NO: raw HTTP inline in $Logic
Rules:
- Single centrally configured HTTP client for all requests
- Auth credentials via centralized mechanism [interceptor/middleware]; NO: per-request auth
- Error responses normalized at client level
- Retry/timeout/cancellation configured centrally; per-endpoint overrides MUST be documented
- Base URLs from env vars; NO: hardcoded URLs
- Endpoint defs grouped by domain in $API dir
[data-fetch/caching lib]:
- lib's definition layer replaces manual service files
- centralized client MUST still underpin transport layer
- caching/polling/refetch configured per-endpoint with comment
- cache invalidation strategy MUST be documented
- optimistic updates MUST include rollback
- new endpoints -> existing domain files; [new domain] -> new file
[no data-fetch lib]:
- each endpoint fn MUST return typed Promise + handle response parsing
- $Logic MUST manage loading/error/data states
- cancellation MUST be implemented [navigation/unmounting supersedes]
## Backend Data Handling
- Every backend response MUST be typed; NO: any-typed responses
- Types generated from schema [if available]; else defined explicitly in $API
- DTOs MUST NOT be used directly in components/state; map to frontend model at API boundary via pure mapper
- Every fetch has 4 states [loading/success/error/empty]; all MUST be handled in $Logic + reflected in view
- Unbounded collections MUST use pagination or virtual scroll; NO: simulate pagination by slicing full response
- Cache staleness MUST be configured explicitly; invalidate/refetch after mutation; optimistic updates MUST include rollback
- PII/credentials MUST NOT persist to browser storage unencrypted; MUST be annotated in type def
## Component JSDoc
Every exported component MUST have JSDoc above fn def: purpose; @param props [each prop: type+desc]; a11y/layout constraints
## useEffect Comments
Every useEffect MUST be preceded by comment: effect purpose + dependency array rationale
## useState/useReducer Comments
Complex state shapes MUST have preceding comment: state structure + meaning of each field
## Props Validation
[PropTypes]: every PropType MUST match JSDoc | [TypeScript]: props interface MUST have JSDoc describing contract
## Build, Transpile & Deploy
Identify + work within existing build toolchain; NO: switch tools without explicit instruction
Config: build config version-controlled; NO: secrets in client bundles; source maps [dev: on, prod: off or privately uploaded]
Transpilation: use existing transpiler; NO: change without explicit instruction; browser targets MUST be declared; polyfills only for out-of-target features
Deployment: follow existing deployment config; no platform mandated
## Code Quality
- Side effects in $Logic or data-fetch lib; NO: in view components
- Prop drilling >2 levels -> sharing mechanism [context/store] with comment
- Complex conditional rendering -> named var or helper fn
- Barrel files: only re-export public API; NO: export internal files
