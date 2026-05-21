#!/bin/bash
# refresh.sh: Run the complete ETL pipeline (download + transform) in sequence.
# Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
# Updated by request R-20260420-2008 to use the project venv Python when available.
# Usage: ./refresh.sh  (run from project root)
set -e

# Use the venv Python when present so all pip dependencies (requests, beautifulsoup4,
# psycopg2-binary, python-dotenv) are available; fall back to system python3 otherwise.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$SCRIPT_DIR/venv/bin/python" ]; then
    PYTHON="$SCRIPT_DIR/venv/bin/python"
else
    PYTHON="python3"
fi

echo "=== Kolko Ni Struva — ETL Refresh ==="
echo ""

echo "[1/2] Downloading new ZIPs..."
"$PYTHON" src/extract.py

echo ""
echo "[2/2] Transforming raw ZIPs into schema..."
"$PYTHON" src/transform.py

echo ""
echo "=== Refresh complete ==="
