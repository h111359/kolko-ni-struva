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
  "Satisfied" means the goal sentence stands alone and requires no external clarification.

- [ ] The goal expresses a single, atomic intent — it is not a bundle of two or more independent concerns.
  "Satisfied" means a single outcome is described, even if multiple tasks are needed to reach it. 

- [ ] The goal is stated in outcome or behaviour terms, not in implementation or solution terms.
  "Satisfied" means the goal describes what changes for whom, not how the change is made. 

- [ ] The goal is traceable to a stated business need, user need, or product objective.
  "Satisfied" means a motivating need is explicitly referenced or inferable from `context.md`.

---

### 2. Stakeholder and User Identification

Knowing who is affected by and who benefits from a change is necessary to define correct scope and acceptance criteria.

- [ ] At least one named stakeholder or user role is identified who will directly use or be affected by the change.
 "Satisfied" means a role (e.g., "Developer", "AIB Automation Agent") is explicitly stated.

- [ ] The stakeholder's need or pain point that motivates the request is explicitly stated.
  "Satisfied" means the request states what problem the stakeholder currently faces or what goal they cannot achieve.

- [ ] All parties who will be impacted by the change (beyond the primary requester) are identified or confirmed to be none.
  "Satisfied" means impacted parties are listed or a statement confirms the change is self-contained.

---

### 3. Business Value and Justification

Every request consumes effort; the value delivered must justify the cost and opportunity trade-off.

- [ ] The business value, user benefit, or product improvement delivered by this request is stated.
  "Satisfied" means at least one concrete benefit is articulated.

- [ ] The request is prioritised, or a reason why it warrants immediate attention is provided.
  "Satisfied" means priority, urgency, or dependency is stated.

- [ ] No equivalent existing feature or solution already satisfies the goal without modification.
  "Satisfied" means the request addresses a known gap or explicitly explains why existing solutions are insufficient. 

---

### 4. Scope Definition

Clear scope prevents both under-delivery (missing required outputs) and scope creep (delivering unrequested work).

- [ ] The scope is explicitly listed as a set of bounded, named deliverables or changes.
  "Satisfied" means the request names every file, component, or behaviour it intends to change or create.

- [ ] The scope is deliverable within a reasonable iteration without decomposition into sub-requests.
  "Satisfied" means the request could plausibly be completed in a single implementation run.

- [ ] Scope items do not contradict each other (no two items require mutually exclusive behaviour).
  "Satisfied" means all scope items are consistent when read together.

- [ ] Scope items describe required outcomes or deliverables, not the internal implementation approach.
  "Satisfied" means scope items state what is to exist or behave, not how the code achieves it.

---

### 5. Out of Scope

Explicit out-of-scope statements prevent scope expansion during implementation and align reviewer expectations.

- [ ] At least one explicit out-of-scope exclusion is stated.
  "Satisfied" means at least one topic, component, or concern is named as excluded.

- [ ] Each exclusion is unambiguous — it names a specific concern, not a vague category.
 "Satisfied" means each exclusion identifies a specific feature, file type, workflow, or concern that is out of bounds.

---

### 6. Constraints and Assumptions

Constraints and assumptions bound the solution space; undocumented ones become hidden blockers.

- [ ] All known technical constraints that restrict the implementation approach are stated.
  "Satisfied" means constraints such as framework version, file format, or tool availability are listed.

- [ ] All known business or organisational constraints (e.g., naming conventions, mandatory compliance rules) are stated.
  "Satisfied" means policy, convention, and process constraints are surfaced.

- [ ] Assumptions that could affect the scope, approach, or acceptance criteria are documented with a risk note if false.
 "Satisfied" means each load-bearing assumption is listed with a brief description of the impact if it proves incorrect.

- [ ] Constraints are separated from functional scope items — they are not embedded inside deliverable descriptions.
  "Satisfied" means constraints appear in a dedicated constraints section, not inside scope bullets.

---

### 7. Success Criteria and Acceptance

Success criteria translate business intent into verifiable statements that confirm when implementation is complete.

- [ ] At least one success criterion is defined for the request.
  "Satisfied" means at least one criterion exists.

- [ ] Each success criterion is measurable — it has a concrete pass/fail test that can be performed without subjective judgement.
 "Satisfied" means each criterion names a file, behaviour, count, or observable state that can be checked deterministically.

- [ ] Each success criterion is achievable within the stated scope and constraints.
  "Satisfied" means every criterion can be satisfied by delivering only the items listed in scope.

- [ ] Each success criterion is specific — it does not use vague qualifiers such as "better", "cleaner", or "improved" without a measurable definition.
  "Satisfied" means every qualifier has an associated measurable threshold or behavioural description.

- [ ] The set of success criteria collectively covers all items listed in scope (no scope item lacks a corresponding criterion).
  "Satisfied" means each scope deliverable maps to at least one criterion.

---

### 8. Context Adequacy

`context.md` is the shared product memory; requests that ignore or contradict it produce implementations misaligned with the product.

- [ ] The product domain, key actors, and product boundaries described in `context.md` are reflected in the request framing.
  "Satisfied" means the request uses terminology and actor names consistent with `context.md`.

- [ ] Relevant prior decisions, conventions, or constraints documented in `context.md` are acknowledged in the request's Constraints or Assumptions sections.
  "Satisfied" means any context entry that bears on the request scope is either cited or explicitly acknowledged as not applicable.

- [ ] No conflict exists between the request scope or success criteria and constraints documented in `context.md`.
  "Satisfied" means the request has been cross-checked against `context.md` and any conflict is either resolved or escalated as a documented blocker.

---

## Extension Guide

To add new checklist items to an existing category, append the new `- [ ]` item and its annotation at the end of that category's section, before the horizontal rule or the next `##` heading. Do not renumber existing items.

To add a new category, append a new `### N.` section after `### 8. Context Adequacy` and before `## Extension Guide`, incrementing the category number. Each new category MUST follow the same structure: a brief category-level paragraph explaining its purpose, followed by one or more annotated `- [ ]` items.

Existing items and categories MUST NOT be restructured, renumbered, or removed in a way that invalidates references made in external documents or prior implementation records.


## References

 BABOK 
 IEEE 29148
 INVEST
 SMART