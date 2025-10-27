# 📁 Project File Structure (Shell & PowerShell Version + Documentation)

This document describes the organized structure of the project, designed for:
- Python-based ETL (Extract–Transform–Load)
- Star-schema data outputs (JSON dimensions + CSV facts)
- Static web reporting via Netlify
- Local development, testing, and scheduled cloud execution
- Automation using **plain shell and PowerShell scripts**
- Comprehensive documentation for requirements, specifications, and guides

---

## 🧩 Root Layout

```
```
repo-root/
├─ src/                       # Source code (Python + Web)
│  ├─ py/                     # Python ETL and utilities
│  │  └─ kolko-ni-struva/
│  │     ├─ etl/              # Extract, transform, load modules
│  │     ├─ schemas/          # Schema definitions, validation models
│  │     ├─ cli.py            # Command-line entry point
│  │     └─ __init__.py
│  └─ web/                    # Frontend source files
```
│     ├─ assets/              # Images, CSS, icons
│     ├─ js/                  # Data fetching and visualization scripts
│     ├─ index.html
│     └─ templates/           # Optional templating
│
├─ data/                      # Local ETL data (not committed)
│  ├─ raw/                    # Downloaded raw data
│  ├─ interim/                # Cleaned / intermediate data
│  └─ processed/              # Final star schema output
│     ├─ dims/                # Dimension tables (JSON)
│     └─ facts/               # Fact tables (CSV)
│
├─ build/                     # Generated deployment artifacts
│  └─ web/                    # Final static site for Netlify
│     ├─ data/
│     │  ├─ dims/
│     │  └─ facts/
│     ├─ assets/
│     ├─ js/
│     └─ index.html
│
├─ docs/                      # Full project documentation
│  ├─ requirements/            # Requirements documents
│  │  ├─ functional-requirements.md
│  │  ├─ technical-requirements.md
│  │  └─ data-requirements.md
│  ├─ specifications/          # Architecture and data flow
│  │  ├─ architecture-diagram.png
│  │  ├─ pipeline-flow.md
│  │  ├─ data-model.md
│  ├─ user-guides/             # End-user and analyst guides
│  │  ├─ getting-started.md
│  │  ├─ usage-examples.md
│  │  └─ troubleshooting.md
│  ├─ developer-guides/        # Developer setup and contribution
│  │  ├─ setup.md
│  │  ├─ contributing.md
│  │  ├─ coding-standards.md
│  │  └─ file-structure.md     # This document (project structure reference)
│  ├─ changelog.md
│  └─ index.md
│
├─ tests/                     # Automated tests
│  ├─ fixtures/               # Sample datasets for tests
│  │  └─ sample_data/
│  ├─ test_etl.py
│  ├─ test_schema_validation.py
│  └─ tmp/                    # Temporary outputs (ignored)
│
├─ configs/                   # Environment configuration files
│  ├─ local.env
│  ├─ cloud.env
│  └─ prod.env
│
├─ scripts/                   # Shell and PowerShell automation scripts
│  ├─ refresh.sh              # Unified data refresh (download + build) - RECOMMENDED
│  ├─ build.sh                # Linux/macOS build script (process existing data)
│  ├─ build.ps1               # Windows PowerShell build script
│  ├─ update.sh               # Legacy update script (deprecated - use refresh.sh)
│  ├─ test.sh                 # Linux/macOS test script
│  ├─ test.ps1                # Windows PowerShell test script
│  ├─ deploy.sh               # Linux/macOS deploy script
│  └─ deploy.ps1              # Windows PowerShell deploy script
│
├─ .github/workflows/         # CI/CD pipelines
│  ├─ ci.yml                  # Run tests and build
│  └─ deploy.yml              # Optional deployment
│
├─ .env.example               # Example environment variables
├─ .gitignore                 # Ignored files and folders
├─ netlify.toml               # Netlify configuration
├─ pyproject.toml             # Python dependencies and settings
└─ README.md                  # Main project documentation
```

---

## ⚙️ Key Principles

### 1. Source vs. Build Separation
- `src/` → editable code only  
- `build/` → generated artifacts (ignored by Git)  
- Netlify publishes from `build/web/`

### 2. Data Lifecycle
| Stage | Folder | Description |
|--------|---------|-------------|
| **Raw** | `data/raw/` | Direct downloads, unmodified |
| **Interim** | `data/interim/` | Cleaned/normalized data |
| **Processed** | `data/processed/` | Star schema: JSON dims + CSV facts |

### 3. Documentation
- All project documentation lives under `docs/`
- `developer-guides/` holds internal developer materials, including **file-structure.md**
- Keep diagrams and flowcharts in `docs/specifications/`
- Use `README.md` as a summary linking to detailed documentation

### 4. Testing
- All tests in `tests/`  
- Use `tmp_path` for temporary output (no overwrite of real data)  
- Run locally:  
  ```bash
  bash scripts/test.sh
  ```
  or on Windows:
  ```powershell
  .\scripts\test.ps1
  ```

### 5. Compute Environment (Cloud)
- The **same codebase** runs locally and in the cloud.  
- CI/CD services use shell or PowerShell scripts to build and deploy automatically.

### 6. Deployment
- **Static site:** deployed to Netlify from `build/web/`
- **ETL jobs:** scheduled in cloud (GitHub Actions, Azure Functions)
- **Configuration:** environment variables in `.env` or platform secrets

### 7. .gitignore Essentials
```gitignore
# Python
__pycache__/
*.pyc
.venv/
.env

# Data
data/raw/
data/interim/
data/processed/
!data/processed/README.md

# Build artifacts
build/
dist/

# Tests
tests/tmp/

# Node
node_modules/

# OS/editor
.DS_Store
```

---

## 🧠 Typical Commands (Shell/PowerShell)

| Purpose | Linux/macOS Command | Windows Command |
|----------|--------------------|----------------|
| **Unified refresh (download + build)** | `bash scripts/refresh.sh` | *PowerShell version coming soon* |
| **Download & transform data, build web site** | `bash scripts/build.sh` | `.\scripts\build.ps1` |
| **Run tests** | `bash scripts/test.sh` | `.\scripts\test.ps1` |
| **Deploy to Netlify** | `bash scripts/deploy.sh` | `.\scripts\deploy.ps1` |

### Recommended Workflow

**For regular data refreshes**, use the unified `refresh.sh` script:
```bash
bash scripts/refresh.sh
```

This script:
- ✅ Downloads data for the last 3 days
- ✅ Processes and generates site with only the last 2 days
- ✅ Implements retry logic for failed downloads
- ✅ Handles missing/incomplete data gracefully
- ✅ Creates `/build/web` if it doesn't exist
- ✅ Provides comprehensive logging
- ✅ Warns about skipped days

Each script runs a full sequence of steps — download, transform, generate, copy assets, and prepare `build/web/` for deployment.

---

## 📝 Adding New Files to the Project

When adding new files, follow this decision tree to place them in the correct location:

### Python Code
- **ETL modules** (data extraction, transformation, loading): `src/py/kolko-ni-struva/etl/`
- **Schema definitions** (validation models, data structures): `src/py/kolko-ni-struva/schemas/`
- **CLI commands**: Add to or extend `src/py/kolko-ni-struva/cli.py`
- **Utilities and helpers**: Create a `src/py/kolko-ni-struva/lib/` or `src/py/kolko-ni-struva/utils/` folder

### Web Files
- **HTML pages**: `src/web/` (e.g., `index.html`, `about.html`)
- **JavaScript**: `src/web/js/` (e.g., `script.js`, `chart.js`)
- **CSS, images, icons**: `src/web/assets/` (e.g., `style.css`, `logo.png`)
- **Templates** (if using templating): `src/web/templates/`

### Automation Scripts
- **Shell scripts** (`.sh`): `scripts/` (e.g., `build.sh`, `deploy.sh`)
- **PowerShell scripts** (`.ps1`): `scripts/` (e.g., `build.ps1`, `deploy.ps1`)
- Name scripts descriptively based on their function

### Tests
- **Test files**: `tests/` (e.g., `test_etl.py`, `test_schema_validation.py`)
- **Test fixtures** (sample data): `tests/fixtures/`
- **Temporary test outputs**: `tests/tmp/` (auto-ignored by Git)

### Documentation
- **User guides** (how to use the system): `docs/user-guides/`
- **Developer guides** (setup, contribution, coding standards): `docs/developer-guides/`
- **Requirements** (functional, technical, data): `docs/requirements/`
- **Specifications** (architecture, API, data models): `docs/specifications/`

### Configuration
- **Environment files**: Root (e.g., `.env`, `.env.example`)
- **Application configs**: `configs/` (e.g., `local.env`, `cloud.env`, `prod.env`)

### Data Files
- **Nomenclatures and reference data**: `data/` (e.g., `category-nomenclature.json`)
- **Raw downloaded data**: `data/raw/` (not committed to Git)
- **Interim/processed data**: `data/interim/`, `data/processed/` (not committed to Git)

### Checklist for Adding Files
1. ✅ Determine the file's purpose (code, web, script, test, docs, config, data)
2. ✅ Place in the appropriate folder based on the guidelines above
3. ✅ If creating a new Python module, add `__init__.py` if needed
4. ✅ Update `.gitignore` if the file should not be committed (e.g., secrets, generated data)
5. ✅ Update documentation if the file introduces new functionality or changes workflow

---

## ✅ Summary

- **Source of truth:** `src/`  
- **Generated artifacts:** `data/processed/`, `build/web/`  
- **Automation:** via shell and PowerShell scripts in `scripts/`  
- **Documentation:** organized in `docs/` for users, developers, and specifications  
- **This document:** `docs/developer-guides/file-structure.md` (developer reference)  
- **Tests:** isolated and automated (no data overwrite)  
- **Cloud compute:** uses same scripts for CI/CD  
- **Deployment:** Netlify hosts static reports built with one command  

This structure is complete, reproducible, and maintainable — ready for both local and cloud-based workflows, and fully documented.
