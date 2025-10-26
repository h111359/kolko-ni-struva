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
repo-root/
├─ src/                       # Source code (Python + Web)
│  ├─ py/                     # Python ETL and utilities
│  │  └─ your_project/
│  │     ├─ etl/              # Extract, transform, load modules
│  │     ├─ schemas/          # Schema definitions, validation models
│  │     ├─ cli.py            # Command-line entry point
│  │     └─ __init__.py
│  └─ web/                    # Frontend source files
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
│  │  └─ api-spec.md
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
│  ├─ build.sh                # Linux/macOS build script
│  ├─ build.ps1               # Windows PowerShell build script
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
| **Download & transform data, build web site** | `bash scripts/build.sh` | `.\scriptsuild.ps1` |
| **Run tests** | `bash scripts/test.sh` | `.\scripts	est.ps1` |
| **Deploy to Netlify** | `bash scripts/deploy.sh` | `.\scripts\deploy.ps1` |

Each script runs a full sequence of steps — download, transform, generate, copy assets, and prepare `build/web/` for deployment.

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
