#!/bin/bash
# Run a local web server for the build directory, executable from any folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m http.server 8080 --directory "$SCRIPT_DIR/../build/web"
