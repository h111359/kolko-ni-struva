#!/bin/bash
# Wrapper script to run update_kolko_ni_struva.py with virtual environment activated

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Get last two days in YYYY-MM-DD format
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
T2DAYS=$(date -d "2 days ago" +%Y-%m-%d)

# Download data for last two days
python src/py/kolko-ni-struva/etl/download_kolkonistruva.py --dates "$T2DAYS" "$YESTERDAY" "$TODAY"

# Merge and update for the same dates
python src/py/kolko-ni-struva/etl/update_kolko_ni_struva.py --dates "$YESTERDAY" "$TODAY" "$@"
