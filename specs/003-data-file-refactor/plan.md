# Implementation Plan: Data File Refactor

**Branch**: `003-data-file-refactor` | **Date**: 2025-10-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-data-file-refactor/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Redesign `build/web/data.csv` to remove all repeating data by normalizing it into dimension files. The main fact file will reference dimensions using integer IDs instead of duplicating values. ETL scripts will automatically maintain dimension files, creating new entries when encountering new values. This refactor will reduce file size for faster web page loads while ensuring data integrity and automatic nomenclature maintenance.

## Technical Context

**Language/Version**: Python 3.9+  
**Primary Dependencies**: requests, beautifulsoup4, lxml, csv (stdlib), json (stdlib)  
**Storage**: CSV files for fact data, JSON for dimension nomenclatures, file-based data storage  
**Testing**: Manual testing for ETL workflow, pytest for unit tests (encouraged)  
**Target Platform**: Linux server (primary), cross-platform Python scripts
**Project Type**: Single project - Python ETL + static web frontend  
**Performance Goals**: Web page load time <2 seconds for standard dataset, ETL processing within 1 hour daily  
**Constraints**: <200KB for data.csv file size, JSON dimensions <10MB/100K rows each, minimize external dependencies  
**Scale/Scope**: ~100 trade chains, ~5K cities, ~100 categories, 2 days of price data in production (current ~50K-100K rows)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Before Phase 0)

All principles passed initial check. See below for details.

### Post-Design Check (After Phase 1) ✅

**Status**: ALL GATES PASS - Design approved for implementation

### I. Data Integrity First ✅
- **Status**: PASS (Confirmed after design)
- **Initial Analysis**: Refactor preserves all source data accuracy. Normalization improves traceability by eliminating duplication. ETL will validate dimension references and log all data operations. Missing/incomplete data handling remains unchanged (skip, warn, continue).
- **Post-Design Verification**: 
  - ✅ Star schema design preserves all source data with referential integrity
  - ✅ Dimension lookup failures create UNKNOWN placeholders (no silent data loss)
  - ✅ Structured JSON logging tracks all errors and dimension creations
  - ✅ ETL continues on error, logs to `etl_errors.json` for manual review
  - ✅ All data validation rules defined in data-model.md

### II. Daily Automation ✅
- **Status**: PASS (Confirmed after design)
- **Initial Analysis**: Existing `refresh.sh` script will be enhanced to handle dimension file updates automatically. No change to daily automation workflow or error handling. The refactor improves automation by reducing file sizes and processing time.
- **Post-Design Verification**:
  - ✅ Normalization integrated into existing CLI workflow
  - ✅ `python -m kolko-ni-struva.cli update` handles full pipeline
  - ✅ Dimension files auto-maintained (no manual intervention)
  - ✅ Error handling preserves "fail gracefully" pattern
  - ✅ Comprehensive logging enables post-run diagnostics

### III. Multi-Device Accessibility ✅
- **Status**: PASS (Confirmed after design)
- **Initial Analysis**: Smaller data.csv file directly improves load times on 3G connections. Web interface unchanged - JavaScript will join dimension data client-side. Performance improvement supports mobile use case.
- **Post-Design Verification**:
  - ✅ Target load time <2s on 3G (fact file reduced to 400-800KB)
  - ✅ Parallel dimension loading minimizes latency
  - ✅ Browser caching strategy optimizes repeat visits
  - ✅ Progressive enhancement ensures core functionality always works
  - ✅ Performance contracts defined in web-contracts.md

### IV. Historical Analytics Capability ✅
- **Status**: PASS (Confirmed after design)
- **Initial Analysis**: All historical data retained. Dimension files provide better structure for analytics queries. Time-series analysis improved by normalized schema. No data loss or degradation.
- **Post-Design Verification**:
  - ✅ Star schema is industry standard for analytics/BI
  - ✅ Dimension stability (IDs never reassigned) enables time-series joins
  - ✅ All historical data preserved (dimensions only grow, never delete)
  - ✅ Foreign key relationships support complex queries
  - ✅ Future-proofs for potential migration to analytical database (Supabase)

### V. Python-First Development ✅
- **Status**: PASS (Confirmed after design)
- **Initial Analysis**: All changes in Python with type hints and docstrings. Using stdlib csv and json modules (no new dependencies). Modular design with clear separation: download → normalize → generate. Follows PEP 8 compliance.
- **Post-Design Verification**:
  - ✅ All ETL contracts include type hints and comprehensive docstrings
  - ✅ Zero new external dependencies (csv, json from stdlib)
  - ✅ Single-responsibility classes (DimensionManager, DataNormalizer, ETLLogger)
  - ✅ Testable interfaces with clear boundaries
  - ✅ Code examples in contracts demonstrate proper usage patterns

## Project Structure

### Documentation (this feature)

```text
specs/003-data-file-refactor/
├── spec.md              # Feature specification (already exists)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── py/
│   └── kolko-ni-struva/
│       ├── etl/
│       │   ├── __init__.py
│       │   ├── download_kolkonistruva.py      # Existing - downloads raw CSVs
│       │   ├── update_kolko_ni_struva.py      # Existing - merges data
│       │   ├── normalize.py                   # NEW - dimension extraction
│       │   └── dimension_manager.py           # NEW - dimension CRUD operations
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── dimensions.py                  # NEW - dimension schemas
│       └── cli.py                             # Existing - CLI interface (update)
└── web/
    ├── js/
    │   ├── script.js                          # Existing - update to load dimensions
    │   └── dimension-loader.js                # NEW - dimension data loading
    ├── assets/
    │   └── style.css                          # Existing - no changes
    └── index.html                             # Existing - no changes

data/
├── category-nomenclature.json                 # Existing - will be regenerated with IDs
├── cities-ekatte-nomenclature.json            # Existing - will be regenerated with IDs
├── trade-chains-nomenclature.json             # Existing - already has IDs
├── product-nomenclature.json                  # NEW - product dimension
├── raw/                                       # Existing - raw CSV downloads
├── interim/                                   # Existing - normalized data staging
└── processed/
    ├── dims/                                  # NEW - dimension files
    │   ├── dim_category.json
    │   ├── dim_city.json
    │   ├── dim_trade_chain.json
    │   ├── dim_trade_object.json
    │   └── dim_product.json
    └── facts/
        └── fact_prices.csv                    # NEW - normalized fact table

build/web/
├── data.csv                                   # Existing - will be replaced by fact_prices.csv
├── dim_category.json                          # NEW - copied from processed/dims/
├── dim_city.json                              # NEW - copied from processed/dims/
├── dim_trade_chain.json                       # NEW - copied from processed/dims/
├── dim_trade_object.json                      # NEW - copied from processed/dims/
├── dim_product.json                           # NEW - copied from processed/dims/
├── index.html                                 # Existing - copied from src/web/
├── script.js                                  # Existing - copied from src/web/js/
└── style.css                                  # Existing - copied from src/web/assets/

tests/
├── fixtures/
│   ├── sample_raw.csv                         # NEW - test data
│   └── sample_dimensions.json                 # NEW - test dimensions
├── test_normalize.py                          # NEW - test normalization
├── test_dimension_manager.py                  # NEW - test dimension CRUD
└── tmp/                                       # Existing - temporary test outputs

logs/
├── etl_errors.json                            # NEW - malformed row logs
└── dimension_audit.json                       # NEW - new dimension entry logs
```

**Structure Decision**: Single project structure selected as this is a Python ETL pipeline with a static web frontend. All Python code lives under `src/py/kolko-ni-struva/`, web assets under `src/web/`. Data flows from `data/raw/` → `data/interim/` → `data/processed/` → `build/web/`. This maintains the existing project structure while adding normalized data layers.

## Complexity Tracking

> **No Constitution violations identified. This section is not applicable.**
