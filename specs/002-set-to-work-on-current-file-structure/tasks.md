# Tasks: Set to Work on Current File Structure

## Phase 1: Setup
- [X] T002 [P] Update scripts/build.sh and scripts/update.sh to support new file structure (scripts/build.sh, scripts/update.sh)

## Phase 2: Foundational
- [X] T003 Remove all references to /web-deploy from codebase and ensure all output and references use /build/web only (src/, scripts/, tests/)
- [X] T004 [P] Update documentation to reflect new file structure (docs/developer-guides/file-structure.md)

## Phase 3: [US1] Unified Data Refresh (P1)
 - [X] T005 [P] [US1] Create refresh.sh script to download last 3 days, process, and generate site (scripts/refresh.sh)
 - [X] T006 [US1] Implement error handling for missing/incomplete data (scripts/refresh.sh)
 - [X] T007 [US1] Implement warning for skipped days (scripts/refresh.sh)
 - [X] T008 [US1] Ensure output is in /build/web (scripts/refresh.sh)
 - [X] T015 [US1] Implement retry logic and comprehensive logging for all operations and failures in refresh.sh (scripts/refresh.sh)

## Phase 4: [US2] Data Preparation Accuracy (P2)
- [X] T009 [P] [US2] Ensure only last 2 days of data are used for site generation (scripts/refresh.sh)
- [X] T010 [US2] Validate generated site contains only last 2 days (build/web/data/)

## Phase 5: [US3] Elimination of Deprecated References (P3)
- [X] T011 [P] [US3] Search and remove /web-deploy references in all scripts and code, and ensure all output and references use /build/web only (src/, scripts/, tests/)
- [X] T012 [US3] Validate no /web-deploy references remain (repo-wide)

## Final Phase: Polish & Cross-Cutting Concerns
- [X] T013 [P] Add usage instructions and examples to refresh.sh (scripts/refresh.sh)
- [X] T014 [P] Update README and developer guides for new workflow (README.md, docs/developer-guides/file-structure.md)

## Dependencies
- US1 → US2 → US3
- Setup and Foundational tasks must be completed before user stories

## Parallel Execution Examples
- T002, T004, T005, T009, T011, T013, T014 can be executed in parallel (different files, no dependencies)

## Implementation Strategy
- MVP: Complete all tasks for US1 (Unified Data Refresh)
- Incremental delivery: Complete US2 and US3 after MVP

## Task Summary
- Total tasks: 14
- US1: 4 tasks
- US2: 2 tasks
- US3: 2 tasks
- Parallel opportunities: 7 tasks
- Independent test criteria: Each user story phase is independently testable
- MVP scope: US1 (T005-T008)
- Format validation: All tasks follow strict checklist format (checkbox, ID, labels, file paths)
