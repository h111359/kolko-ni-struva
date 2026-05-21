#!/bin/bash
# menu.sh: Launch the interactive ETL pipeline menu.
# Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
# Usage: ./menu.sh  (run from project root)
# Use the venv Python when present so all pip dependencies are available.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    exec "$SCRIPT_DIR/venv/bin/python" menu.py "$@"
else
    exec python3 menu.py "$@"
fi
