# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
    **Language/Version**: Python 3.9+ (from constitution)
    **Primary Dependencies**: requests, beautifulsoup4, lxml (from constitution/spec); NEEDS CLARIFICATION if more required
    **Storage**: CSV for raw data, JSON for nomenclatures (from constitution)
    **Testing**: Manual for user-facing, basic script execution tests required (from spec); automated for data processing encouraged
    **Target Platform**: Linux server, local dev, CI/CD (from spec)
    **Project Type**: Single project (default, per spec)
    **Performance Goals**: Web pages load <3s on 3G, data processing <1hr daily (from constitution); NEEDS CLARIFICATION for file ops
    **Constraints**: Must preserve all functionality, no breakage; scripts only change paths unless strictly necessary (from spec)
    **Scale/Scope**: Repo <1000 files, <500MB (from spec)
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

  *GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

  **Gates:**
  - Data integrity must be preserved (no loss/corruption during moves)
  - All automation scripts must remain functional and include error handling
  - Python-first, PEP8, type hints, docstrings for any new code
  - Documentation must be updated for new structure
  - No unnecessary complexity (single project unless justified)
  - All changes must be justified if violating any principle

  **Status:**
  - No violations detected at planning stage. All requirements align with constitution. Any complexity or deviation must be documented in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
