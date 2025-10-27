<!--
SYNC IMPACT REPORT - Constitution v1.1.0
========================================
Version Change: 1.0.0 → 1.1.0
Modified Principles: 
- Data Integrity First (clarified missing/incomplete data handling)
- Daily Automation (unified script, folder creation logic)
Added Sections: None
Removed Sections: None
Templates Status:
- ✅ spec-template.md (validated - matches new requirements)
- ✅ plan-template.md (validated - matches new requirements)
- ✅ tasks-template.md (validated - matches new requirements)
Follow-up TODOs: None
-->

# Kolko Ni Struva Constitution

## Core Principles

### I. Data Integrity First
All data operations MUST preserve accuracy and traceability. Source data from kolkostruva.bg MUST be downloaded in original format with timestamps. If data for any of the last 3 days is missing or incomplete, the system MUST skip missing days, proceed with available data, and warn the maintainer clearly. All processed data MUST be validated for completeness before site generation.

**Rationale**: Consumer price data directly impacts financial decisions of price-sensitive users including retired people and low-income families. Data corruption, loss, or silent omission could lead to incorrect purchasing decisions.

### II. Daily Automation (NON-NEGOTIABLE)
Data collection MUST run automatically according to a configurable schedule from https://kolkostruva.bg/opendata. All data refresh operations MUST be unified in a single script (`refresh.sh`) that downloads the last 3 days, processes, and generates the site. The script MUST create the `/build/web` folder if missing, fail with a clear error if not writable, and remove all deprecated references to `/web-deploy`. Failed downloads MUST trigger alerts and manual intervention procedures. All automation scripts MUST include error handling, retry logic, and comprehensive logging.

**Rationale**: Stale price data renders the platform useless. Daily automation and a unified workflow ensure consumers have current pricing information and maintainers can reliably refresh the site.

### III. Multi-Device Accessibility
All user interfaces MUST work on mobile phones, tablets, and desktop computers. Web interfaces MUST be responsive and load within 3 seconds on 3G connections. Features MUST be usable in store environments (bright lighting, one-handed operation).

**Rationale**: Price-conscious consumers need access while shopping in stores, comparing prices on-the-go, and planning purchases at home.

### IV. Historical Analytics Capability
All price data MUST be retained indefinitely for trend analysis. Database schema MUST support time-series queries efficiently. Analytics features MUST provide insights into price trends, seasonal variations, and store chain comparisons.

**Rationale**: Historical data enables consumers to make informed decisions about timing purchases and identifying genuine sales versus price manipulation.

### V. Python-First Development
All data processing MUST use Python with clear type hints, docstrings, and PEP 8 compliance. External dependencies MUST be minimal and well-justified. Code MUST be modular with single-responsibility functions that can be tested independently.

**Rationale**: Python provides excellent data processing libraries while maintaining readability for future maintainers. Type safety prevents data corruption bugs.

## Technical Requirements

**Technology Stack**: Python 3.9+, HTML/CSS/JavaScript for web interface, JSON for data exchange, csv for big fact data
**Data Storage**: CSV files for raw data, JSON for nomenclatures, consider Supabase for analytics queries
**External Dependencies**: requests, beautifulsoup4, lxml (current); minimize additional dependencies
**Performance Standards**: Web pages load <3s on 3G, data processing completes within 1 hour daily
**Accessibility**: WCAG 2.1 AA compliance for web interfaces
**Browser Support**: Modern browsers (Chrome, Firefox, Safari, Edge) released within last 2 years
**Output Folder**: All generated site artifacts MUST be placed in `/build/web`. 

## Development Workflow

**Code Quality**: All Python code MUST include type hints, docstrings, and comprehensive error handling
**Testing**: Manual testing required for user-facing features; automated testing encouraged for data processing
**Documentation**: All scripts MUST include usage instructions and examples. When file structure changes, documentation and code references MUST be updated to match the new structure.
**Deployment**: Static file deployment preferred; avoid complex server requirements
**Security**: Input validation required for all external data; no sensitive data storage

## Governance

This constitution supersedes all other development practices. All feature implementations MUST verify compliance with these principles before completion. Complexity that violates principles MUST be explicitly justified with business rationale and documented alternatives.

All code reviews MUST check for data integrity preservation, automation reliability, and accessibility compliance. Performance requirements are mandatory gates for production deployment.

**Version**: 1.1.0 | **Ratified**: 2025-10-25 | **Last Amended**: 2025-10-27
