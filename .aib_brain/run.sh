#!/usr/bin/env sh
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
WORKSPACE_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
python3 "$SCRIPT_DIR/tools/menu.py" --workspace "$WORKSPACE_DIR"
