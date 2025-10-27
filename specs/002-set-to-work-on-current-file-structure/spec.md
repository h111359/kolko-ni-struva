
# Feature Specification: Set to Work on Current File Structure

**Feature Branch**: `002-set-to-work-on-current-file-structure`  
**Created**: October 27, 2025  
**Status**: Draft  
**Input**: User description: "The process of download and refresh of the data to work on the new file structure. To continue with regular refreshes and to continue with further enhancements. Acceptance Criteria: From the scripts /scripts/update.sh and /scripts/build.sh to be created a single refresh.sh script which do all at once - from data download to creation of new deployable in Netlify version. No need to deal with the upload to Netlify now - it will be created later. The refresh.sh script download the last 3 days and prepare the site with the last 2 days. The web site should be generated in folder /build/web. No more references to folder /web-deploy should exist in the code."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->


### User Story 1 - Unified Data Refresh (Priority: P1)

A maintainer runs a single script to download the latest data, process it, and generate a new version of the website in the correct folder structure.

**Why this priority**: Enables regular refreshes and future enhancements by simplifying the workflow.

**Independent Test**: Can be fully tested by running the new script and verifying the site is updated with the latest data in /build/web.

**Acceptance Scenarios**:

1. **Given** the maintainer has access to the repository, **When** they run refresh.sh, **Then** the last 3 days of data are downloaded and the site is prepared with the last 2 days in /build/web.
2. **Given** the codebase, **When** refresh.sh is run, **Then** no references to /web-deploy exist in the code or output.

---

### User Story 2 - Data Preparation Accuracy (Priority: P2)

The system prepares the site using only the last 2 days of data, regardless of how many days are downloaded.

**Why this priority**: Ensures the site always reflects the most recent and relevant data.

**Independent Test**: Can be tested by inspecting the generated site and confirming only the last 2 days are present.

**Acceptance Scenarios**:

1. **Given** 3 days of data are downloaded, **When** the site is generated, **Then** only the last 2 days are included in /build/web.

---

### User Story 3 - Elimination of Deprecated References (Priority: P3)

All code and scripts are updated to remove any references to /web-deploy.

**Why this priority**: Prevents confusion and ensures the new file structure is used exclusively.

**Independent Test**: Can be tested by searching the codebase for /web-deploy and confirming no matches.

**Acceptance Scenarios**:

1. **Given** the updated codebase, **When** a search for /web-deploy is performed, **Then** no references are found.

---

### Edge Cases

- What happens if data for the last 3 days is incomplete or missing?
- How does the system handle errors during download or site generation?
- What if the /build/web folder does not exist or is not writable?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->


### Functional Requirements

- **FR-001**: System MUST provide a single script (refresh.sh) that performs data download, processing, and site generation in one step.
- **FR-002**: System MUST download data for the last 3 days.
- **FR-003**: System MUST generate the website using only the last 2 days of data.
- **FR-004**: System MUST output the generated site to /build/web.
- **FR-005**: System MUST remove all references to /web-deploy from the codebase and ensure all output and references use /build/web only.
- **FR-006**: System MUST handle missing or incomplete data gracefully. If some of the last 3 days are missing, the script MUST skip missing days, proceed with available data, and warn the user.
 - **FR-007**: System MUST create /build/web if it does not exist. If the folder cannot be created or is not writable, the script MUST fail with a clear error message.
 - **FR-008**: System MUST ensure that the folder structure in /build/web is followed and all relevant paths in the code and scripts are adapted accordingly.
 - **FR-009**: All automation scripts (including refresh.sh) MUST implement error handling, retry logic for failed downloads, and comprehensive logging of all operations and failures, as mandated by the constitution.
### Key Entities

- **Data File**: Represents downloaded data for a specific day; attributes include date, source, completeness.
- Q: What is the fallback if some days are missing? → A: Skip missing days, warn user
- **Site Build**: Represents the generated website; attributes include included dates, output folder, status.

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->


### Measurable Outcomes
- **SC-004**: Errors and edge cases (missing data, unwritable folder) are reported clearly to the maintainer.

### /build/web Folder Structure

The /build/web folder MUST have the following structure (see docs/developer-guides/file-structure.md):

- /build/web/
  - data/
    - dims/ (dimension tables as JSON)
    - facts/ (fact tables as CSV)
  - assets/ (images, CSS, icons)
  - js/ (JavaScript for data fetching and visualization)
  - index.html

## Clarifications
### Session 2025-10-27
- Q: What is the fallback if some days are missing? → A: Skip missing days, warn user
- Q: Should the script create the /build/web folder or fail if it does not exist? → A: Create /build/web if missing, fail if not writable

- **SC-001**: Maintainers can refresh the site with a single command in under 5 minutes.
- **SC-002**: The generated site always contains only the last 2 days of data.
- **SC-003**: No references to /web-deploy exist in the codebase after implementation.
- **SC-004**: Errors and edge cases (missing data, unwritable folder) are reported clearly to the maintainer.
