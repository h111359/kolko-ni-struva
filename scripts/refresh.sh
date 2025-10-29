#!/bin/bash
###############################################################################
# refresh.sh - Unified Data Refresh Script
# 
# Purpose: Download the last 3 days of data, process it, and generate a static
#          site with the last 2 days in /build/web
#
# Usage:
#   ./scripts/refresh.sh              # Download last 3 days, use last 2
#   ./scripts/refresh.sh --help       # Show usage information
#
# Features:
#   - Downloads data for the last 3 days
#   - Processes and generates site with only the last 2 days
#   - Implements retry logic for failed downloads
#   - Comprehensive error handling and logging
#   - Warns about skipped days due to missing/incomplete data
#   - Creates /build/web if it doesn't exist
#   - Validates folder permissions before proceeding
#
# Exit Codes:
#   0 - Success
#   1 - General error (missing venv, invalid dates, etc.)
#   2 - Folder permission error
#   3 - Download error (all retries failed)
#   4 - Processing error
#
# Examples:
#   # Standard refresh (download last 3 days, use last 2)
#   bash scripts/refresh.sh
#
#   # Run from project root
#   cd /path/to/kolko-ni-struva && bash scripts/refresh.sh
#
###############################################################################

set -o pipefail  # Capture errors in pipes

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MAX_RETRIES=3
RETRY_DELAY=5
LOG_FILE="logs/refresh_$(date +%Y%m%d_%H%M%S).log"

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT="$(pwd)"

###############################################################################
# Logging Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

###############################################################################
# Helper Functions
###############################################################################

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Unified data refresh script for Kolko Ni Struva project.
Downloads the last 3 days of data and generates a static site with the last 2 days.

OPTIONS:
    --help          Show this help message

FEATURES:
    ✓ Downloads data for the last 3 days
    ✓ Generates site with only the last 2 days
    ✓ Retry logic for failed downloads (up to $MAX_RETRIES attempts)
    ✓ Comprehensive error handling and logging
    ✓ Warnings for skipped days
    ✓ Creates /build/web if missing
    ✓ Validates folder permissions

EXIT CODES:
    0 - Success
    1 - General error
    2 - Folder permission error
    3 - Download error
    4 - Processing error

EXAMPLES:
    # Standard refresh
    $0

    # Show help
    $0 --help

LOGS:
    All operations are logged to: logs/refresh_YYYYMMDD_HHMMSS.log

EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        log_error "Virtual environment not found at .venv/"
        log_error "Please create a virtual environment first:"
        log_error "  python3 -m venv .venv"
        log_error "  source .venv/bin/activate"
        log_error "  pip install -r requirements.txt"
        return 1
    fi
    
    # Check if required Python scripts exist
    if [ ! -f "src/py/kolko-ni-struva/etl/download_kolkonistruva.py" ]; then
        log_error "Download script not found: src/py/kolko-ni-struva/etl/download_kolkonistruva.py"
        return 1
    fi
    
    if [ ! -f "src/py/kolko-ni-struva/etl/update_kolko_ni_struva.py" ]; then
        log_error "Update script not found: src/py/kolko-ni-struva/etl/update_kolko_ni_struva.py"
        return 1
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

check_folder_permissions() {
    log_info "Checking folder permissions..."
    
    # Create logs directory if it doesn't exist
    if [ ! -d "logs" ]; then
        mkdir -p "logs" || {
            log_error "Failed to create logs directory"
            return 2
        }
    fi
    
    # Create data/raw directory if it doesn't exist
    if [ ! -d "data/raw" ]; then
        mkdir -p "data/raw" || {
            log_error "Failed to create data/raw directory"
            return 2
        }
    fi
    
    # Create build/web directory if it doesn't exist
    if [ ! -d "build/web" ]; then
        log_info "Creating build/web directory..."
        mkdir -p "build/web" || {
            log_error "Failed to create build/web directory"
            log_error "Please check folder permissions"
            return 2
        }
        log_success "Created build/web directory"
    fi
    
    # Test write permissions for build/web
    if [ ! -w "build/web" ]; then
        log_error "build/web directory is not writable"
        log_error "Please check folder permissions"
        return 2
    fi
    
    log_success "Folder permissions check passed"
    return 0
}

activate_venv() {
    log_info "Activating virtual environment..."
    source .venv/bin/activate || {
        log_error "Failed to activate virtual environment"
        return 1
    }
    log_success "Virtual environment activated"
    return 0
}

get_dates() {
    # Calculate dates for the last 3 days
    TODAY=$(date +%Y-%m-%d)
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
    T2DAYS=$(date -d "2 days ago" +%Y-%m-%d)
    
    log_info "Target dates:"
    log_info "  - Today: $TODAY"
    log_info "  - Yesterday: $YESTERDAY"
    log_info "  - 2 days ago: $T2DAYS"
}

download_data() {
    local dates=("$@")
    log_info "📥 Starting data download for ${#dates[@]} days..."
    
    local attempt=1
    local success=false
    
    while [ $attempt -le $MAX_RETRIES ] && [ "$success" = false ]; do
        log_info "Download attempt $attempt of $MAX_RETRIES..."
        
        if python src/py/kolko-ni-struva/etl/download_kolkonistruva.py --dates "${dates[@]}" 2>&1 | tee -a "$LOG_FILE"; then
            success=true
            log_success "Data download completed successfully"
        else
            log_warning "Download attempt $attempt failed"
            
            if [ $attempt -lt $MAX_RETRIES ]; then
                log_info "Waiting ${RETRY_DELAY}s before retry..."
                sleep $RETRY_DELAY
            fi
            
            ((attempt++))
        fi
    done
    
    if [ "$success" = false ]; then
        log_error "All download attempts failed after $MAX_RETRIES retries"
        return 3
    fi
    
    return 0
}

check_downloaded_data() {
    local dates=("$@")
    log_info "Checking downloaded data..."
    
    local missing_dates=()
    local found_count=0
    
    for date in "${dates[@]}"; do
        # Check if any file exists for this date
        local file_count=$(find data/raw -name "kolko_struva_${date}_account_*.csv" 2>/dev/null | wc -l)
        
        if [ "$file_count" -eq 0 ]; then
            missing_dates+=("$date")
            log_warning "No data files found for date: $date"
        else
            ((found_count++))
            log_info "Found $file_count files for date: $date"
        fi
    done
    
    if [ ${#missing_dates[@]} -gt 0 ]; then
        log_warning "⚠️  WARNING: Some days have missing or incomplete data:"
        for missing_date in "${missing_dates[@]}"; do
            log_warning "   - $missing_date"
        done
        log_warning "These days will be skipped in the final site generation"
    fi
    
    if [ $found_count -eq 0 ]; then
        log_error "No data files were downloaded successfully"
        return 3
    fi
    
    log_success "Downloaded data for $found_count out of ${#dates[@]} days"
    return 0
}

process_data() {
    local dates=("$@")
    log_info "🔄 Starting data normalization and processing for last 2 days..."
    log_info "Processing dates: ${dates[*]}"
    
    # Step 1: Normalize data into star schema
    log_info "Step 1: Normalizing raw data into star schema..."
    if PYTHONPATH="${PROJECT_ROOT}/src/py" python3 -m kolko-ni-struva.cli normalize --dates "${dates[@]}" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Data normalization completed successfully"
    else
        log_error "Data normalization failed"
        return 4
    fi
    
    # Step 2: Deploy normalized files to build/web
    log_info "Step 2: Deploying normalized data to build/web..."
    if PYTHONPATH="${PROJECT_ROOT}/src/py" python3 -m kolko-ni-struva.cli update --dates "${dates[@]}" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Data deployment completed successfully"
        return 0
    else
        log_error "Data deployment failed"
        return 4
    fi
}

verify_output() {
    log_info "Verifying output..."
    
    if [ ! -f "build/web/data.csv" ]; then
        log_warning "Output file not found: build/web/data.csv"
        return 4
    fi
    
    local file_size=$(stat -f%z "build/web/data.csv" 2>/dev/null || stat -c%s "build/web/data.csv" 2>/dev/null)
    log_success "Generated build/web/data.csv (${file_size} bytes)"
    
    # Check for essential web files
    local missing_files=()
    for file in "index.html" "script.js" "style.css"; do
        if [ ! -f "build/web/$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        log_warning "Some web files are missing in build/web/:"
        for file in "${missing_files[@]}"; do
            log_warning "   - $file"
        done
    else
        log_success "All essential web files are present in build/web/"
    fi
    
    return 0
}

###############################################################################
# Main Execution
###############################################################################

main() {
    # Parse arguments
    if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
        show_usage
        exit 0
    fi
    
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║       Kolko Ni Struva - Unified Data Refresh Script           ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    log_info "Starting refresh process at $(date)"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Log file: $LOG_FILE"
    echo ""
    
    # Step 1: Check prerequisites
    check_prerequisites || exit 1
    
    # Step 2: Check folder permissions
    check_folder_permissions || exit 2
    
    # Step 3: Activate virtual environment
    activate_venv || exit 1
    
    # Step 4: Get target dates
    get_dates
    
    # Step 5: Download data for last 3 days
    download_data "$T2DAYS" "$YESTERDAY" "$TODAY" || exit 3
    
    # Step 6: Check downloaded data and warn about missing days
    check_downloaded_data "$T2DAYS" "$YESTERDAY" "$TODAY" || exit 3
    
    # Step 7: Process data for last 2 days only
    process_data "$YESTERDAY" "$TODAY" || exit 4
    
    # Step 8: Verify output
    verify_output || exit 4
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║                   ✅ REFRESH COMPLETE                          ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    log_success "Refresh process completed successfully at $(date)"
    log_info "Static site is ready in: build/web/"
    log_info "Log file saved to: $LOG_FILE"
    echo ""
    
    exit 0
}

# Execute main function
main "$@"
