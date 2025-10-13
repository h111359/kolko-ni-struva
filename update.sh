#!/bin/bash
# Wrapper script to run update-kolko-ni-struva.py with virtual environment activated

cd "$(dirname "$0")"
source scraper_venv/bin/activate
python update-kolko-ni-struva.py "$@"
