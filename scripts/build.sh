#!/bin/bash
# Build script - Downloads data, processes it, and generates the static site

set -e  # Exit on error

echo "🚀 Starting build process..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found. Using system Python."
fi

# Get dates for last 2 days
TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "📥 Downloading data for $YESTERDAY and $TODAY..."
python src/py/kolko-ni-struva/etl/download_kolkonistruva.py --dates "$YESTERDAY" "$TODAY"

echo "🔄 Processing and merging data..."
python src/py/kolko-ni-struva/etl/update_kolko_ni_struva.py --dates "$YESTERDAY" "$TODAY"

echo "✅ Build complete!"
echo "📦 Static site is ready in build/web/"
