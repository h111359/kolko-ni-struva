# Tasks: Data File Refactor

**Feature Branch**: `003-data-file-refactor`  
**Input**: Design documents from `/specs/003-data-file-refactor/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are NOT explicitly requested in the specification, therefore NO test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project structure:
- Python source: `src/py/kolko-ni-struva/`
- Web source: `src/web/`
- Data: `data/`
- Build output: `build/web/`
- Tests: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for normalized data processing

- [X] T001 Create directory structure for normalized data: `data/processed/dims/`, `data/processed/facts/`, `logs/`
- [X] T002 [P] Create Python package structure: `src/py/kolko-ni-struva/etl/` with `__init__.py`
- [X] T003 [P] Create schemas package: `src/py/kolko-ni-struva/schemas/` with `__init__.py`
- [X] T004 [P] Create web JavaScript directory: `src/web/js/`
- [X] T005 [P] Create test fixtures directory: `tests/fixtures/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement ETLLogger class in `src/py/kolko-ni-struva/etl/logger.py` with JSON logging methods `log_error()` and `log_dimension_created()`
- [X] T007 [P] Implement DimensionManager class in `src/py/kolko-ni-struva/etl/dimension_manager.py` with methods: `load()`, `get_or_create()`, `get()`, `save()`, `check_size_warnings()`
- [X] T008 [P] Create dimension schema definitions in `src/py/kolko-ni-struva/schemas/dimensions.py` with dataclasses for all dimension types
- [X] T009 Create sample raw CSV fixture in `tests/fixtures/sample_raw.csv` with representative test data
- [X] T010 [P] Create sample dimension JSON fixtures in `tests/fixtures/sample_dimensions.json` for testing dimension operations
- [X] T011 Validate ETLLogger JSON output format matches spec requirements: verify error log structure (FR-007) includes timestamp, error_type, file, row_number, raw_data, error_message fields; verify audit log structure (FR-009) includes timestamp, event_type, dimension, id, value, attributes fields

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Fast Data Load (Priority: P1) 🎯 MVP

**Goal**: Reduce web page data file size by normalizing into fact + dimension files, achieving <2s page load time

**Independent Test**: 
1. Generate normalized files from raw data
2. Measure combined file sizes (should be 40-70% smaller than original)
3. Load web page and verify data displays correctly within 2 seconds on 3G connection

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement DataNormalizer class skeleton in `src/py/kolko-ni-struva/etl/normalize.py` with `__init__()` method accepting dimension managers
- [X] T013 [P] [US1] Implement dimension initialization for category in DataNormalizer: create category dimension manager with name-based lookup
- [X] T014 [P] [US1] Implement dimension initialization for city in DataNormalizer: create city dimension manager with ekatte_code-based lookup
- [X] T015 [P] [US1] Implement dimension initialization for trade_chain in DataNormalizer: create trade chain dimension manager with name-based lookup
- [X] T016 [P] [US1] Implement dimension initialization for trade_object in DataNormalizer: create trade object dimension manager with chain_id+address composite lookup
- [X] T017 [P] [US1] Implement dimension initialization for product in DataNormalizer: create product dimension manager with name+product_code composite lookup
- [X] T018 [US1] Implement `_normalize_row()` method in DataNormalizer to transform single CSV row: extract dimensions, call get_or_create on each manager, return fact dict with IDs
- [X] T019 [US1] Implement `_process_csv_file()` method in DataNormalizer to process single raw CSV file: read with DictReader, call _normalize_row for each, collect facts
- [X] T020 [US1] Implement `normalize()` method in DataNormalizer: find raw CSV files by date filter, process each file, write fact_prices.csv, save all dimensions, return statistics
- [X] T021 [US1] Implement error handling in DataNormalizer per FR-006 validation checklist: catch malformed rows (missing required fields, invalid data types, constraint violations, unresolvable dimension references), log via ETLLogger with full context, skip invalid row and continue processing valid data
- [X] T022 [US1] Add CLI command `normalize` in `src/py/kolko-ni-struva/cli.py` to run normalization with --dates options
- [ ] T023 [US1] Update CLI command `update` in `src/py/kolko-ni-struva/cli.py` to run normalize then copy files to build/web/
- [X] T024 [P] [US1] Create DimensionLoader JavaScript class in `src/web/js/dimension-loader.js` with parallel async loading of 5 dimension files
- [ ] T025 [P] [US1] Implement dimension lookup methods in DimensionLoader: `getCategory()`, `getCity()`, `getChain()`, `getTradeObject()`, `getProduct()`
- [ ] T026 [US1] Update `src/web/js/script.js`: add `loadFactData()` function to load and parse fact_prices.csv
- [ ] T027 [US1] Update `src/web/js/script.js`: add `joinFactsWithDimensions()` function to enrich facts with dimension data
- [ ] T028 [US1] Update `src/web/js/script.js`: modify main `loadData()` workflow to use DimensionLoader and joinFactsWithDimensions
- [ ] T029 [US1] Add loading indicator and error handling in `src/web/js/script.js` for async dimension loading
- [ ] T030 [US1] Update `scripts/refresh.sh` to call normalize command in ETL pipeline before deploying to build/web/, ensure /build/web folder creation, add writability checks per Constitution II, preserve error handling

**Checkpoint**: At this point, User Story 1 should be fully functional - normalized files generated, web page loads fast with joined data

---

## Phase 4: User Story 2 - Accurate Data Reference (Priority: P2)

**Goal**: Ensure fact table references dimension files correctly with no data duplication, enabling easy maintenance

**Independent Test**:
1. Run normalization on raw data
2. Inspect fact_prices.csv - verify all values are integer IDs (no repeated text)
3. Inspect dimension files - verify each unique value appears exactly once
4. Cross-reference fact IDs with dimension files - verify all references are valid

### Implementation for User Story 2

- [ ] T031 [P] [US2] Add data validation to DimensionManager: validate all IDs exist before saving dimension file
- [ ] T032 [P] [US2] Add referential integrity check in DataNormalizer: verify all fact foreign keys exist in dimensions before writing
- [ ] T033 [US2] Implement dimension uniqueness validation in DimensionManager: check lookup_index for duplicates before creating new entries
- [ ] T034 [US2] Add CSV output validation in DataNormalizer: ensure fact_prices.csv contains only numeric IDs and no duplicated dimension text
- [ ] T035 [US2] Add dimension file integrity check in normalize command: verify JSON structure, next_id consistency, and lookup_index accuracy
- [ ] T036 [US2] Add post-normalization report to CLI: display statistics on dimension counts, new entries created, data reduction percentage
- [ ] T037 [US2] Update DimensionManager to log warning if duplicate dimension detected (same lookup key but different attributes)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - data loads fast AND references are accurate

---

## Phase 5: User Story 3 - Automated Dimension Maintenance (Priority: P3)

**Goal**: ETL scripts automatically create new dimension entries when encountering new values, with full audit trail

**Independent Test**:
1. Run normalization with existing dimensions
2. Add new raw CSV file with previously unseen products/cities/categories
3. Re-run normalization
4. Verify new dimension entries auto-created in dimension files
5. Check logs/dimension_audit.json - verify all new entries logged with timestamps and attributes

### Implementation for User Story 3

- [ ] T038 [P] [US3] Enhance DimensionManager `get_or_create()` to log audit event via ETLLogger when creating new dimension entry
- [ ] T039 [P] [US3] Implement dimension audit log structure in ETLLogger: include timestamp, dimension name, ID, value, and full attributes
- [ ] T040 [US3] Add dimension growth monitoring to DimensionManager `check_size_warnings()`: check file size against 10MB threshold and entry count against 100K threshold
- [ ] T041 [US3] Update normalize command to call `check_size_warnings()` on all dimensions after save
- [ ] T042 [US3] Add dimension summary report to normalize command output: show count of new entries per dimension type
- [ ] T043 [US3] Create audit log viewer utility in CLI: `python -m kolko-ni-struva.cli audit --dimension <name> --date <YYYY-MM-DD>` to filter and display audit events
- [ ] T044 [US3] Document dimension maintenance workflow in `docs/user-guides/etl-operations.md`: explain auto-creation, audit logs, and size monitoring

**Checkpoint**: All user stories should now be independently functional - fast load + accurate references + automated maintenance

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [ ] T045 [P] Add comprehensive docstrings to all classes and methods in `src/py/kolko-ni-struva/etl/` following Google style guide
- [ ] T046 [P] Add type hints to all function signatures in ETL modules for better IDE support and type checking
- [ ] T047 [P] Add JSDoc comments to all JavaScript functions in `src/web/js/` for better documentation
- [ ] T048 Update README.md with normalized data structure documentation and quickstart instructions
- [ ] T049 [P] Add error recovery documentation to `docs/user-guides/troubleshooting.md` for common ETL errors
- [ ] T050 Optimize CSV writing in DataNormalizer: use csv.QUOTE_MINIMAL instead of QUOTE_ALL for smaller file size
- [ ] T051 [P] Add browser caching headers documentation in `docs/developer-guides/deployment.md` for dimension files
- [ ] T052 Run full quickstart.md validation: execute all commands, verify outputs, measure page load time
- [ ] T053 Create migration documentation in `docs/developer-guides/migration-guide.md` explaining transition from old to new schema
- [ ] T054 [P] Add performance benchmarking script in `scripts/benchmark.sh` to measure file sizes and load times before/after normalization
- [ ] T055 Code review and refactoring: ensure PEP 8 compliance, remove dead code, consolidate duplicate logic

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3, 4, 5)**: All depend on Foundational phase completion
  - User Story 1 (P1) can start immediately after Phase 2
  - User Story 2 (P2) builds on US1 but can be developed in parallel if different files
  - User Story 3 (P3) builds on US1 but can be developed in parallel if different files
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories. This is the MVP.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Enhances US1 with validation but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Enhances US1 with automation but independently testable

### Within Each User Story

**User Story 1 (P1)**:
1. T011-T016 (dimension managers) can run in parallel [P]
2. T017 (normalize_row) depends on T011-T016
3. T018 (process_csv_file) depends on T017
4. T019 (normalize method) depends on T018
5. T020 (error handling) can be added to T019
6. T021-T022 (CLI) depend on T019
7. T023-T024 (web dimension loader) can run in parallel [P] with T011-T022
8. T025-T027 (web data loading) depend on T023-T024
9. T028 (error handling) can be added to T027
10. T029 (refresh script) depends on T021-T022

**User Story 2 (P2)**:
1. T030-T031 (validation) can run in parallel [P]
2. T032-T036 (integrity checks) can run in parallel after T030-T031

**User Story 3 (P3)**:
1. T037-T038 (audit logging) can run in parallel [P]
2. T039-T041 (monitoring) can run in parallel with T037-T038
3. T042-T043 (documentation) depend on T037-T041

### Parallel Opportunities

- **Phase 1 Setup**: T002, T003, T004, T005 can all run in parallel
- **Phase 2 Foundational**: T007, T008, T010 can run in parallel after T006
- **User Story 1**: 
  - T012-T016 (dimension managers) in parallel
  - T023-T024 (web loader) in parallel with backend work
- **User Story 2**: T030-T031 in parallel, then T032-T036 in parallel
- **User Story 3**: T037-T038 in parallel, T039-T041 in parallel
- **Phase 6 Polish**: T044, T045, T046, T048, T050, T053 can all run in parallel
- **Multiple user stories can be worked on in parallel by different team members after Phase 2 completes**

---

## Parallel Example: User Story 1

```bash
# After Foundational phase complete, launch dimension managers in parallel:
Task T012: "Implement dimension initialization for category in DataNormalizer"
Task T013: "Implement dimension initialization for city in DataNormalizer"
Task T014: "Implement dimension initialization for trade_chain in DataNormalizer"
Task T015: "Implement dimension initialization for trade_object in DataNormalizer"
Task T016: "Implement dimension initialization for product in DataNormalizer"

# While backend team works on T017-T022, frontend team can start in parallel:
Task T023: "Create DimensionLoader JavaScript class in src/web/js/dimension-loader.js"
Task T024: "Implement dimension lookup methods in DimensionLoader"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

This is the recommended approach for fastest time to value:

1. **Complete Phase 1: Setup** (T001-T005) - ~30 minutes
2. **Complete Phase 2: Foundational** (T006-T010) - ~4-6 hours
   - **CRITICAL GATE**: Must complete before any user story work
3. **Complete Phase 3: User Story 1** (T011-T029) - ~2-3 days
   - Core normalization logic (T011-T020)
   - CLI integration (T021-T022)
   - Web interface updates (T023-T028)
   - Deployment automation (T029)
4. **STOP and VALIDATE**: 
   - Run normalization on real data
   - Verify file size reduction (40-70%)
   - Test web page load time (<2 seconds on 3G)
   - Verify data displays correctly
5. **Deploy MVP** - You now have a working system with faster page loads!

### Incremental Delivery (All User Stories)

1. **Complete Setup + Foundational** → Foundation ready (~6-8 hours)
2. **Add User Story 1** → Test independently → Deploy/Demo (~2-3 days)
   - **MVP ACHIEVED**: Faster page loads with normalized data
3. **Add User Story 2** → Test independently → Deploy/Demo (~1 day)
   - **Value Add**: Data integrity validation and duplication prevention
4. **Add User Story 3** → Test independently → Deploy/Demo (~1 day)
   - **Value Add**: Full automation with audit trail
5. **Polish Phase** → Production hardening → Final Deploy (~1-2 days)
   - Documentation, optimization, code cleanup

**Total Estimated Time**: 5-7 days for full feature with all 3 user stories

### Parallel Team Strategy

With 2-3 developers, optimal parallelization:

**Week 1**:
- **Day 1**: All team - Setup + Foundational (pair programming recommended)
- **Day 2-3**: 
  - **Dev A**: US1 backend (T011-T022)
  - **Dev B**: US1 frontend (T023-T028)
  - **Dev C**: US2 validation (T030-T036)
- **Day 4**:
  - **Dev A**: US3 automation (T037-T043)
  - **Dev B**: Integration testing US1
  - **Dev C**: Integration testing US2
- **Day 5**: All team - Polish, documentation, final testing

---

## Notes

- **[P] marker**: These tasks work on different files with no dependencies, safe to parallelize
- **[Story] marker**: Maps task to user story for traceability and independent testing
- **File paths**: All paths are absolute from repository root
- **Constitution compliance**: 
  - All tasks preserve data integrity (Principle I)
  - Automation maintained through CLI and scripts (Principle II)
  - File size optimization for 3G access (Principle III)
  - Historical data preserved in normalized schema (Principle IV)
  - Pure Python ETL with type hints and docstrings (Principle V)
- **Checkpoint strategy**: Stop after each phase to validate independently
- **Error handling**: Fail gracefully, log errors, continue processing valid data
- **Testing approach**: Manual testing via quickstart.md, no unit tests requested in spec
- **Commit strategy**: Commit after each task or logical group of parallel tasks
- **Migration**: New schema is incompatible with old, requires atomic deployment

---

## Summary

**Total Tasks**: 55 tasks organized into 6 phases

**Task Breakdown by Phase**:
- Phase 1 (Setup): 5 tasks
- Phase 2 (Foundational): 6 tasks (CRITICAL - blocks all user stories)
- Phase 3 (User Story 1 - Fast Data Load): 19 tasks
- Phase 4 (User Story 2 - Accurate References): 7 tasks
- Phase 5 (User Story 3 - Automated Maintenance): 7 tasks
- Phase 6 (Polish): 11 tasks

**Parallel Opportunities**: 23 tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1 only) = 30 tasks (~3-4 days)

**Independent Test Criteria**:
- **US1**: Measure file sizes, test page load time, verify data display
- **US2**: Inspect files for duplicates, verify referential integrity
- **US3**: Add new data, verify auto-creation, check audit logs

**Suggested Delivery Approach**: MVP-first (US1 only), then incremental addition of US2 and US3

All tasks follow the strict checklist format with task ID, parallelization marker, story label, and exact file paths. Ready for immediate execution! 🚀
