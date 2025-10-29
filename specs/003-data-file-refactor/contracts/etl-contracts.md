# ETL Process Contracts

**Feature**: Data File Refactor  
**Date**: 2025-10-27

This document defines the contracts (interfaces) for the ETL process components that implement data normalization.

---

## 1. Dimension Manager Interface

**Module**: `src/py/kolko-ni-struva/etl/dimension_manager.py`

### Purpose
Manages dimension file lifecycle: loading, ID assignment, lookups, and persistence.

### Class: `DimensionManager`

```python
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DimensionEntry:
    """Single dimension entry with metadata."""
    id: int
    attributes: Dict[str, Any]

class DimensionManager:
    """
    Manages a single dimension file (category, city, product, or trade chain).
    
    Responsibilities:
    - Load dimension file from disk
    - Assign new IDs to unseen values
    - Perform lookups (value -> ID)
    - Save dimension file back to disk
    - Log new entries to audit log
    """
    
    def __init__(self, dimension_name: str, dimension_file_path: str, lookup_key_fn: Callable[[Dict], str]):
        """
        Initialize dimension manager.
        
        Args:
            dimension_name: Name of dimension (e.g., "category", "city", "product")
            dimension_file_path: Path to JSON dimension file
            lookup_key_fn: Function to generate lookup key from attributes dict
        """
        pass
    
    def load(self) -> None:
        """
        Load dimension from JSON file.
        
        Creates new dimension file with initial structure if not exists.
        Raises IOError if file exists but is malformed.
        """
        pass
    
    def get_or_create(self, attributes: Dict[str, Any]) -> int:
        """
        Get existing dimension ID or create new entry.
        
        Args:
            attributes: Dimension attributes (e.g., {"name": "София", "ekatte_code": "68134"})
        
        Returns:
            Integer ID for the dimension entry
        
        Side Effects:
            - If new entry created, logs to audit file
            - Updates internal next_id counter
        """
        pass
    
    def get(self, dimension_id: int) -> Optional[DimensionEntry]:
        """
        Get dimension entry by ID.
        
        Args:
            dimension_id: Integer ID to lookup
        
        Returns:
            DimensionEntry if found, None otherwise
        """
        pass
    
    def save(self) -> None:
        """
        Persist dimension to JSON file.
        
        File structure:
        {
            "version": "1.0",
            "generated": "2025-10-27T14:30:00Z",
            "dimensions": {"1": {...}, "2": {...}},
            "next_id": 3,
            "lookup_index": {"key1": 1, "key2": 2}
        }
        
        Raises:
            IOError: If unable to write file
        """
        pass
    
    def check_size_warnings(self) -> None:
        """
        Check dimension file size and log warning if exceeds thresholds.
        
        Thresholds:
            - File size: 10 MB
            - Entry count: 100,000 rows
        
        Side Effects:
            Logs warning message if threshold exceeded
        """
        pass
```

### Usage Example

```python
# Initialize manager for city dimension
def city_lookup_key(attrs: Dict) -> str:
    return attrs["ekatte_code"]

city_dim = DimensionManager(
    dimension_name="city",
    dimension_file_path="data/processed/dims/dim_city.json",
    lookup_key_fn=city_lookup_key
)

# Load existing dimension
city_dim.load()

# Get or create city ID
city_id = city_dim.get_or_create({
    "ekatte_code": "68134",
    "name": "София"
})

# Save updates
city_dim.save()
```

---

## 2. Normalizer Interface

**Module**: `src/py/kolko-ni-struva/etl/normalize.py`

### Purpose
Transforms raw denormalized CSV files into normalized fact table with dimension references.

### Class: `DataNormalizer`

```python
from typing import List, Dict
import csv

class DataNormalizer:
    """
    Normalizes raw price data into star schema format.
    
    Responsibilities:
    - Read raw CSV files
    - Extract and deduplicate dimension values
    - Replace dimension values with IDs in fact table
    - Handle malformed data (log and skip)
    - Generate fact_prices.csv
    """
    
    def __init__(self, 
                 raw_data_dir: str,
                 output_fact_file: str,
                 dimension_managers: Dict[str, DimensionManager]):
        """
        Initialize normalizer.
        
        Args:
            raw_data_dir: Path to data/raw/ directory
            output_fact_file: Path to output fact CSV file
            dimension_managers: Dict of dimension name -> DimensionManager instance
        """
        pass
    
    def normalize(self, date_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute normalization process.
        
        Args:
            date_filter: Optional list of dates (YYYY-MM-DD) to process
        
        Returns:
            Statistics dictionary:
            {
                "total_rows_processed": 10000,
                "rows_written": 9950,
                "rows_skipped": 50,
                "dimensions_created": {
                    "category": 5,
                    "city": 12,
                    "product": 234,
                    "trade_chain": 0,
                    "trade_object": 45
                },
                "files_processed": 150
            }
        
        Side Effects:
            - Writes fact_prices.csv
            - Updates all dimension files via managers
            - Logs errors to logs/etl_errors.json
            - Logs new dimensions to logs/dimension_audit.json
        """
        pass
    
    def _process_csv_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Process single raw CSV file.
        
        Args:
            filepath: Path to raw CSV file
        
        Returns:
            List of normalized fact dictionaries
        
        Raises:
            ValueError: If file format is unrecognized
        """
        pass
    
    def _normalize_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Normalize single CSV row.
        
        Args:
            row: Raw CSV row as dictionary
        
        Returns:
            Normalized fact dictionary with dimension IDs, or None if row is invalid
        
        Example:
            Input:
            {
                "date": "2025-10-27",
                "chain_id": "5",
                "Населено място": "68134",
                "Търговски обект": "бул. Витоша 123, София",
                "Наименование на продукта": "Хляб бял",
                "Категория": "Хляб бял",
                "Цена на дребно": "3.45",
                "Цена в промоция": ""
            }
            
            Output:
            {
                "date": "2025-10-27",
                "trade_chain_id": 5,
                "trade_object_id": 142,
                "city_id": 89,
                "product_id": 523,
                "category_id": 1,
                "retail_price": 3.45,
                "promo_price": None
            }
        """
        pass
    
    def _log_error(self, error_type: str, context: Dict[str, Any]) -> None:
        """
        Log processing error to JSON error log.
        
        Args:
            error_type: Type of error (e.g., "malformed_row", "missing_field")
            context: Error context (file, row number, raw data, message)
        """
        pass
```

### Usage Example

```python
# Setup dimension managers
managers = {
    "category": DimensionManager("category", "data/processed/dims/dim_category.json", ...),
    "city": DimensionManager("city", "data/processed/dims/dim_city.json", ...),
    "product": DimensionManager("product", "data/processed/dims/dim_product.json", ...),
    "trade_chain": DimensionManager("trade_chain", "data/processed/dims/dim_trade_chain.json", ...),
    "trade_object": DimensionManager("trade_object", "data/processed/dims/dim_trade_object.json", ...)
}

# Initialize normalizer
normalizer = DataNormalizer(
    raw_data_dir="data/raw",
    output_fact_file="data/processed/facts/fact_prices.csv",
    dimension_managers=managers
)

# Run normalization
stats = normalizer.normalize(date_filter=["2025-10-26", "2025-10-27"])

print(f"Processed {stats['total_rows_processed']} rows")
print(f"Created {stats['dimensions_created']['product']} new products")
```

---

## 3. Logger Interface

**Module**: `src/py/kolko-ni-struva/etl/logger.py`

### Purpose
Structured JSON logging for ETL errors and audit events.

### Class: `ETLLogger`

```python
from typing import Dict, Any
from datetime import datetime
import json

class ETLLogger:
    """
    Manages JSON-formatted logging for ETL process.
    
    Responsibilities:
    - Log errors (malformed rows, missing data)
    - Log audit events (new dimensions created)
    - Append to JSON log files
    - Rotate log files if needed
    """
    
    def __init__(self, error_log_path: str, audit_log_path: str):
        """
        Initialize logger.
        
        Args:
            error_log_path: Path to error log JSON file (logs/etl_errors.json)
            audit_log_path: Path to audit log JSON file (logs/dimension_audit.json)
        """
        pass
    
    def log_error(self, 
                  error_type: str,
                  file: str,
                  row_number: int,
                  raw_data: str,
                  error_message: str) -> None:
        """
        Log ETL error.
        
        Args:
            error_type: Error classification (malformed_row, missing_field, invalid_value)
            file: Source file path
            row_number: Row number in source file (1-indexed)
            raw_data: Raw row data as string
            error_message: Human-readable error description
        
        Example log entry:
        {
            "timestamp": "2025-10-27T14:30:45Z",
            "error_type": "malformed_row",
            "file": "data/raw/kolko_struva_2025-10-27_account_5.csv",
            "row_number": 142,
            "raw_data": "incomplete,row,data",
            "error_message": "Missing required field: Цена на дребно"
        }
        """
        pass
    
    def log_dimension_created(self,
                             dimension: str,
                             dimension_id: int,
                             value: str,
                             attributes: Dict[str, Any]) -> None:
        """
        Log new dimension entry creation.
        
        Args:
            dimension: Dimension name (category, city, product, trade_chain)
            dimension_id: Assigned integer ID
            value: Primary value (name or code)
            attributes: All dimension attributes
        
        Example log entry:
        {
            "timestamp": "2025-10-27T14:30:50Z",
            "event_type": "new_dimension_entry",
            "dimension": "product",
            "id": 523,
            "value": "Ябълки Грени Смит",
            "attributes": {"name": "Ябълки Грени Смит", "category_id": 50, "product_code": ""}
        }
        """
        pass
    
    def _append_to_log(self, log_path: str, entry: Dict[str, Any]) -> None:
        """
        Append entry to JSON log file.
        
        Args:
            log_path: Path to log file
            entry: Log entry dictionary
        
        Creates log file with JSON array structure if not exists.
        Appends to existing array if file exists.
        """
        pass
```

---

## 4. CLI Contract Updates

**Module**: `src/py/kolko-ni-struva/cli.py`

### New Command: `normalize`

```python
@cli.command()
@click.option('--dates', multiple=True, help='Dates to normalize (YYYY-MM-DD)')
@click.option('--output-dir', default='data/processed', help='Output directory for normalized data')
def normalize(dates, output_dir):
    """
    Normalize raw CSV data into star schema format.
    
    Steps:
    1. Load dimension managers
    2. Process raw CSV files
    3. Generate fact_prices.csv
    4. Save updated dimension files
    5. Copy to build/web/
    
    Example:
        python -m kolko-ni-struva.cli normalize --dates 2025-10-26 --dates 2025-10-27
    """
    pass
```

### Updated Command: `update`

```python
@cli.command()
@click.option('--dates', multiple=True, help='Dates to update (YYYY-MM-DD)')
def update(dates):
    """
    Full ETL pipeline: normalize data and deploy to build/web.
    
    Steps:
    1. Run normalize command
    2. Copy dimension files to build/web
    3. Copy fact_prices.csv to build/web
    4. Copy web assets
    
    This replaces the old merge logic with normalization.
    
    Example:
        python -m kolko-ni-struva.cli update --dates 2025-10-26 --dates 2025-10-27
    """
    pass
```

---

## 5. File Format Contracts

### Fact CSV Format

**File**: `build/web/data.csv` (or `fact_prices.csv`)

**Delimiter**: Comma (`,`)  
**Quoting**: All fields quoted  
**Encoding**: UTF-8  
**Line Endings**: Unix (`\n`)

**Header**:
```
date,trade_chain_id,trade_object_id,city_id,product_id,category_id,retail_price,promo_price
```

**Data Types**:
- `date`: ISO 8601 date string (YYYY-MM-DD)
- `*_id`: Integer (no quotes in output)
- `*_price`: Decimal with max 2 places, or empty string for null

---

### Dimension JSON Format

**Files**: `build/web/dim_*.json`

**Encoding**: UTF-8  
**Indentation**: 2 spaces  
**Key Order**: Sorted

**Structure**:
```json
{
  "version": "1.0",
  "generated": "2025-10-27T14:30:00Z",
  "dimensions": {
    "1": { "attribute": "value" },
    "2": { "attribute": "value" }
  },
  "next_id": 3,
  "lookup_index": {
    "lookup_key": 1
  }
}
```

**Required Fields**:
- `version`: Schema version (semantic versioning)
- `generated`: ISO 8601 timestamp
- `dimensions`: Map of ID (string key) to attribute dict
- `next_id`: Next available ID (integer)
- `lookup_index`: Reverse lookup map (key -> ID)

---

## 6. Error Handling Contracts

### Error Categories

1. **Critical Errors** (fail fast):
   - Dimension file not found and cannot be created
   - Dimension file malformed (invalid JSON)
   - Output directory not writable
   - Insufficient disk space

2. **Data Errors** (log and continue):
   - Malformed CSV row (missing fields)
   - Invalid data type (non-numeric price)
   - Missing dimension value (create UNKNOWN placeholder)
   - Duplicate primary key (skip duplicate)

### Recovery Strategies

| Error Type | Strategy | User Action Required |
|------------|----------|---------------------|
| Critical file I/O | Fail with clear message | Fix permissions, create directory |
| Malformed row | Log to errors.json, skip row | Review errors.json, fix source data |
| Missing dimension | Create UNKNOWN entry, log | Review audit.json, validate data |
| Size threshold | Log warning, continue | Plan archival strategy |

---

## Summary

This contract specification defines 6 key interfaces:

1. ✅ **DimensionManager**: Dimension file lifecycle
2. ✅ **DataNormalizer**: Raw data → normalized schema transformation
3. ✅ **ETLLogger**: Structured error and audit logging
4. ✅ **CLI Commands**: User-facing ETL operations
5. ✅ **File Formats**: CSV and JSON schema contracts
6. ✅ **Error Handling**: Error categories and recovery patterns

All interfaces include type hints, docstrings, and example usage patterns consistent with the Python-First Development principle from the Constitution.
