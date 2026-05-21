# Convention: requirements-analysis-convention.md

**Scope:** Normative
**Applies to:** Every new or updated request evaluated by the AI Automation Agent or a human reviewer before implementation begins.

---

## Purpose

This convention defines a structured, checklist-driven gate for evaluating whether a work request is sufficiently clear and complete from a business and user-requirements perspective before any technical analysis or implementation planning begins. It draws on established requirements-engineering frameworks — BABOK (Business Analysis Body of Knowledge), IEEE 29148 (Systems and Software Requirements Engineering), INVEST criteria for user stories, and SMART criteria for acceptance definitions — to provide a principled, extensible acceptance standard.

The convention is intended to be applied by the AI Automation Agent during the analysis phase and by human reviewers during request review. Items are expressed as Markdown checkboxes so they can be evaluated interactively against the content of `input.md` and `context.md`.

---

## Applicability

This convention applies to:

- Every request submitted via `input.md` before the analysis workflow begins.
- Any request whose scope, goal, or acceptance criteria are updated mid-lifecycle.

It does **not** apply to:

- Internal AIB framework maintenance tasks that have no user-facing product change (e.g., pure refactoring with no behavioral delta).
- Hotfix requests where the defect is unambiguous and the fix is a single, reversible change.

---

## Normative Language

The key words **MUST**, **MUST NOT**, **SHALL**, **SHOULD**, **MAY**, and **OPTIONAL** in this document are to be interpreted as described in BCP 14 (RFC 2119 and RFC 8174).

---

## Acceptance Gate Declaration

A request **passes** this gate when **all mandatory checklist items** (items not explicitly marked OPTIONAL) in every category below are checked (satisfied), and **no critical-severity gaps** have been identified that are not already resolved or deferred by explicit documented assumptions.

A request **fails** this gate — and MUST NOT proceed to implementation — if one or more mandatory items remain unchecked and cannot be resolved by a reasonable, documented assumption within the current iteration scope.

The **pass threshold** is: zero unchecked mandatory items AND zero undocumented critical gaps.

---

### 1. Goal Clarity

Goal clarity ensures the request communicates a single, unambiguous intent that can be implemented without guessing what "done" means.

- [ ] The goal is stated in one or two sentences that a new team member can understand without domain pre-knowledge.
  *Why it matters:* Vague goals lead to divergent implementations. "Satisfied" means the goal sentence stands alone and requires no external clarification. (BABOK: Unambiguous; IEEE 29148: Necessary)

- [ ] The goal expresses a single, atomic intent — it is not a bundle of two or more independent concerns.
  *Why it matters:* Bundled goals create scope ambiguity and make acceptance testing harder. "Satisfied" means a single outcome is described, even if multiple tasks are needed to reach it. (BABOK: Atomic; INVEST: Small, Independent)

- [ ] The goal is stated in outcome or behaviour terms, not in implementation or solution terms.
  *Why it matters:* Prescribing the solution constrains valid approaches and may embed incorrect assumptions. "Satisfied" means the goal describes what changes for whom, not how the change is made. (IEEE 29148: Implementation-free)

- [ ] The goal is traceable to a stated business need, user need, or product objective.
  *Why it matters:* Goals without business justification may represent gold-plating or low-value work. "Satisfied" means a motivating need is explicitly referenced or inferable from `context.md`. (BABOK: Traceable; IEEE 29148: Traceable)

---

### 2. Stakeholder and User Identification

Knowing who is affected by and who benefits from a change is necessary to define correct scope and acceptance criteria.

- [ ] At least one named stakeholder or user role is identified who will directly use or be affected by the change.
  *Why it matters:* Anonymous requirements cannot be validated against real needs. "Satisfied" means a role (e.g., "Developer", "AIB Automation Agent") is explicitly stated. (BABOK: Stakeholder alignment; IEEE 29148: Traceable)

- [ ] The stakeholder's need or pain point that motivates the request is explicitly stated.
  *Why it matters:* Without the motivating need, trade-off decisions during implementation lack a reference point. "Satisfied" means the request states what problem the stakeholder currently faces or what goal they cannot achieve. (BABOK: Unambiguous)

- [ ] All parties who will be impacted by the change (beyond the primary requester) are identified or confirmed to be none.
  *Why it matters:* Hidden impacted parties create integration surprises. "Satisfied" means impacted parties are listed or a statement confirms the change is self-contained. (IEEE 29148: Traceable)

---

### 3. Business Value and Justification

Every request consumes effort; the value delivered must justify the cost and opportunity trade-off.

- [ ] The business value, user benefit, or product improvement delivered by this request is stated.
  *Why it matters:* Without stated value, it is impossible to prioritise competing requests or justify accepting technical debt. "Satisfied" means at least one concrete benefit is articulated. (INVEST: Valuable; BABOK: Feasible, Prioritized)

- [ ] The request is prioritised, or a reason why it warrants immediate attention is provided.
  *Why it matters:* Unprioritised work competes equally with all other backlog items. "Satisfied" means priority, urgency, or dependency is stated. (INVEST: Estimable)

- [ ] No equivalent existing feature or solution already satisfies the goal without modification.
  *Why it matters:* Duplicate implementations create maintenance overhead. "Satisfied" means the request addresses a known gap or explicitly explains why existing solutions are insufficient. (BABOK: Feasible)

---

### 4. Scope Definition

Clear scope prevents both under-delivery (missing required outputs) and scope creep (delivering unrequested work).

- [ ] The scope is explicitly listed as a set of bounded, named deliverables or changes.
  *Why it matters:* Implicit scope leads to disagreement at acceptance time. "Satisfied" means the request names every file, component, or behaviour it intends to change or create. (BABOK: Complete; IEEE 29148: Singular)

- [ ] The scope is deliverable within a reasonable iteration without decomposition into sub-requests.
  *Why it matters:* Oversized scope causes estimation failure and incomplete delivery. "Satisfied" means the request could plausibly be completed in a single implementation run. (INVEST: Small)

- [ ] Scope items do not contradict each other (no two items require mutually exclusive behaviour).
  *Why it matters:* Contradictory scope results in implementation choices that satisfy one item at the expense of another. "Satisfied" means all scope items are consistent when read together. (BABOK: Consistent; IEEE 29148: Singular)

- [ ] Scope items describe required outcomes or deliverables, not the internal implementation approach.
  *Why it matters:* Implementation-prescriptive scope items block valid alternative solutions. "Satisfied" means scope items state what is to exist or behave, not how the code achieves it. (IEEE 29148: Implementation-free; INVEST: Negotiable)

---

### 5. Out of Scope

Explicit out-of-scope statements prevent scope expansion during implementation and align reviewer expectations.

- [ ] At least one explicit out-of-scope exclusion is stated.
  *Why it matters:* Without exclusions, implementors may reasonably include adjacent work. "Satisfied" means at least one topic, component, or concern is named as excluded. (BABOK: Concise)

- [ ] Each exclusion is unambiguous — it names a specific concern, not a vague category.
  *Why it matters:* Vague exclusions ("nothing else") are unenforceable. "Satisfied" means each exclusion identifies a specific feature, file type, workflow, or concern that is out of bounds. (BABOK: Unambiguous; IEEE 29148: Unambiguous)

---

### 6. Constraints and Assumptions

Constraints and assumptions bound the solution space; undocumented ones become hidden blockers.

- [ ] All known technical constraints that restrict the implementation approach are stated.
  *Why it matters:* Unrecorded technical constraints lead to solutions that fail in the target environment. "Satisfied" means constraints such as framework version, file format, or tool availability are listed. (IEEE 29148: Consistent; INVEST: Negotiable)

- [ ] All known business or organisational constraints (e.g., naming conventions, mandatory compliance rules) are stated.
  *Why it matters:* Organisational constraints that are invisible to the implementor result in non-compliant deliverables. "Satisfied" means policy, convention, and process constraints are surfaced. (IEEE 29148: Consistent)

- [ ] Assumptions that could affect the scope, approach, or acceptance criteria are documented with a risk note if false.
  *Why it matters:* Unrecorded assumptions become undetected risks. "Satisfied" means each load-bearing assumption is listed with a brief description of the impact if it proves incorrect. (INVEST: Negotiable; BABOK: Traceable)

- [ ] Constraints are separated from functional scope items — they are not embedded inside deliverable descriptions.
  *Why it matters:* Mixed constraint/scope statements create ambiguity about what is a requirement and what is a restriction. "Satisfied" means constraints appear in a dedicated constraints section, not inside scope bullets. (IEEE 29148: Singular; INVEST: Independent)

---

### 7. Success Criteria and Acceptance

Success criteria translate business intent into verifiable statements that confirm when implementation is complete.

- [ ] At least one success criterion is defined for the request.
  *Why it matters:* Without success criteria, "done" is subjective. "Satisfied" means at least one criterion exists. (BABOK: Testable; SMART: Specific)

- [ ] Each success criterion is measurable — it has a concrete pass/fail test that can be performed without subjective judgement.
  *Why it matters:* Unmeasurable criteria cannot confirm completion. "Satisfied" means each criterion names a file, behaviour, count, or observable state that can be checked deterministically. (SMART: Measurable; IEEE 29148: Verifiable)

- [ ] Each success criterion is achievable within the stated scope and constraints.
  *Why it matters:* Criteria that require work outside the stated scope will never pass. "Satisfied" means every criterion can be satisfied by delivering only the items listed in scope. (SMART: Achievable; INVEST: Estimable)

- [ ] Each success criterion is specific — it does not use vague qualifiers such as "better", "cleaner", or "improved" without a measurable definition.
  *Why it matters:* Vague qualifiers leave acceptance open to interpretation. "Satisfied" means every qualifier has an associated measurable threshold or behavioural description. (SMART: Specific; IEEE 29148: Unambiguous)

- [ ] The set of success criteria collectively covers all items listed in scope (no scope item lacks a corresponding criterion).
  *Why it matters:* Uncovered scope items can be delivered in any form. "Satisfied" means each scope deliverable maps to at least one criterion. (BABOK: Complete; SMART: Relevant)

---

### 8. Context Adequacy

`context.md` is the shared product memory; requests that ignore or contradict it produce implementations misaligned with the product.

- [ ] `.aib_memory/context.md` has been read and is non-empty before evaluating this request.
  *Why it matters:* An empty or unread context means the implementation is performed without product memory, increasing the risk of inconsistent decisions. "Satisfied" means the context file exists, is non-empty, and has been loaded by the evaluating agent or reviewer. (BABOK: Traceable)

- [ ] The product domain, key actors, and product boundaries described in `context.md` are reflected in the request framing.
  *Why it matters:* Requests that re-define product actors or boundaries without acknowledging the existing context create divergence. "Satisfied" means the request uses terminology and actor names consistent with `context.md`. (IEEE 29148: Consistent)

- [ ] Relevant prior decisions, conventions, or constraints documented in `context.md` are acknowledged in the request's Constraints or Assumptions sections.
  *Why it matters:* Ignoring prior decisions leads to contradictory implementations. "Satisfied" means any context entry that bears on the request scope is either cited or explicitly acknowledged as not applicable. (BABOK: Traceable; IEEE 29148: Traceable)

- [ ] No conflict exists between the request scope or success criteria and constraints documented in `context.md`.
  *Why it matters:* Conflicting requirements cannot be simultaneously satisfied. "Satisfied" means the request has been cross-checked against `context.md` and any conflict is either resolved or escalated as a documented blocker. (BABOK: Consistent; IEEE 29148: Consistent)

---

## Extension Guide

To add new checklist items to an existing category, append the new `- [ ]` item and its annotation at the end of that category's section, before the horizontal rule or the next `##` heading. Do not renumber existing items.

To add a new category, append a new `### N.` section after `### 8. Context Adequacy` and before `## Extension Guide`, incrementing the category number. Each new category MUST follow the same structure: a brief category-level paragraph explaining its purpose, followed by one or more annotated `- [ ]` items.

Existing items and categories MUST NOT be restructured, renumbered, or removed in a way that invalidates references made in external documents or prior implementation records.
