#!/bin/bash
# Wrapper script to run update-kolko-ni-struva.py with virtual environment activated

cd "$(dirname "$0")/.."
source scraper_venv/bin/activate

# Get last two days in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

# Download data for last two days
python src/download-kolkonistruva.py --dates "$YESTERDAY" "$TODAY"

# Merge and update for the same dates
python src/update-kolko-ni-struva.py --dates "$YESTERDAY" "$TODAY" "$@"
