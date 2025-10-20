# File and Folder Structure

> This document describes the folder structure for the "Kolko Ni Struva" (How Much Does It Cost) web application project - a data processing and visualization tool for price tracking.

## Project Root Structure

```
kolko-ni-struva/
├── .github/                    # GitHub-specific configuration
├── .rdd-docs/                  # Project documentation
├── .vscode/                    # VS Code workspace settings
├── README.md                   # Project overview and setup instructions
├── archive/                    # Archived/legacy files
├── build/                      # Built application files (production-ready)
├── data/                       # Processed data files and nomenclatures
├── downloads/                  # Raw downloaded CSV data files
├── helper-scripts/             # Utility and helper scripts
├── kolko-ni-struva/           # Additional source code directory
├── scraper_venv/              # Python virtual environment
├── src/                       # Main source code directory
└── workin-update.py           # Working update script
```

## Directory Descriptions

### Core Configuration
- **`.github/`**: GitHub-specific files including workflows, issue templates, instructions, prompts, and scripts
- **`.rdd-docs/`**: All project documentation following RDD (Requirements-Driven Development) methodology
- **`.vscode/`**: Specific setup and configuration for Visual Studio Code workspace

### Source Code & Build
- **`src/`**: Main source code directory containing:
  - Python scripts for data processing and scraping
  - HTML, CSS, and JavaScript files for the web interface
  - Deployment documentation and requirements
- **`build/`**: Production-ready built files including:
  - Compiled web assets (HTML, CSS, JS)
  - JSON nomenclature files for categories, cities, and trade chains
- **`kolko-ni-struva/`**: Secondary source code directory (may contain alternative implementations)

### Data Management
- **`data/`**: Processed and cleaned data files including:
  - Master data CSV file (`data.csv`)
  - JSON nomenclature files for categories, cities, and trade chains
- **`downloads/`**: Raw CSV files downloaded from external sources:
  - Individual account CSV files from the source system
  - Download summary logs

### Development & Utilities
- **`helper-scripts/`**: Utility scripts for various development and maintenance tasks
- **`scraper_venv/`**: Python virtual environment containing all required dependencies
- **`archive/`**: Legacy and archived files including old versions of scripts and HTML files

## .rdd-docs/ Structure
Project documentation and planning following RDD methodology:
- **`requirements.md`**: Requirements specification file representing the current state of the product
- **`technical-specification.md`**: Technical information including architecture, design, and setup
- **`folder-structure.md`**: This document describing the files and folders organization
- **`change-requests/`**: Folder with individual change requests documentation (*.cr.md files)
- **`templates/`**: Documentation templates for requirements, technical specification, CRs, etc.

For every change request (CR), a dedicated log file (`cr-<cr id>-<cr-name>-log.md`) is created in the same folder as the CR file to record all rdd-copilot.* prompts and replies related to that CR.

## .github/ Structure
GitHub configuration and automation:
- **`instructions/`**: Copilot instructions for different file types and technologies
- **`prompts/`**: Reusable prompt templates for various development tasks
- **`scripts/`**: Automation scripts for project maintenance
- **`chatmodes/`**: Chat mode configurations
- **`copilot-instructions.md`**: Main Copilot configuration file
- **`user-prompts-log.md`**: Log of user prompts and interactions

## Best Practices & Guidelines

### File Organization
- Keep source files in `src/` for development
- Use `build/` for production-ready compiled assets
- Store raw data in `downloads/`, processed data in `data/`
- Archive old files in `archive/` rather than deleting them

### Data Flow
1. Raw data downloaded to `downloads/`
2. Processed and cleaned in `data/`
3. Source code in `src/` processes the data
4. Built application in `build/` serves the final product

### Development Workflow
- Use the virtual environment in `scraper_venv/` for Python development
- Utility scripts go in `helper-scripts/`
- Follow RDD methodology for documentation in `.rdd-docs/`
- Use GitHub workflows and scripts in `.github/` for automation

## Customization Notes
- This structure is optimized for a data processing web application with scraping capabilities
- Maintain clear separation between raw data, processed data, source code, and built assets
- The dual source directories (`src/` and `kolko-ni-struva/`) may indicate different development approaches or versions
- Consider consolidating source code directories if they serve similar purposes
