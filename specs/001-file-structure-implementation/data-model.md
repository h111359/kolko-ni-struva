# data-model.md

## Entities Extracted from Feature Spec

### File
- **Attributes:**
  - name: string
  - location: string (absolute path)
  - purpose: string (code, documentation, config, automation)

### Folder
- **Attributes:**
  - name: string
  - contents: list of File or Folder
  - hierarchy: string (parent/child relationships)

### Script
- **Attributes:**
  - name: string
  - location: string
  - compatibility: boolean (runs after structure change)
  - correct_path_usage: boolean

## Validation Rules
- All required files and folders must exist after implementation
- Scripts must reference correct paths and run successfully
- No loss of functionality or breakage permitted
- Minimal README.md for empty folders

## State Transitions
- File/folder moved: update location, preserve history
- Script updated: only path references changed unless logic change strictly required for compatibility
