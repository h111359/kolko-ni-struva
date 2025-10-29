"""
Validation script for ETLLogger JSON output format.

This script tests that ETLLogger produces correctly structured JSON logs
matching the specification requirements.
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / 'src' / 'py'
sys.path.insert(0, str(src_path))

# Now we can import with the correct module name
sys.path.insert(0, str(src_path / 'kolko-ni-struva'))

from etl.logger import ETLLogger


def validate_error_log_structure(log_path: str) -> bool:
    """
    Validate error log structure matches FR-007 requirements.
    
    Required fields:
    - timestamp (string, ISO format)
    - error_type (string)
    - file (string)
    - row_number (integer)
    - raw_data (string)
    - error_message (string)
    """
    if not os.path.exists(log_path):
        print(f"❌ Error log file not found: {log_path}")
        return False
    
    with open(log_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    if not isinstance(entries, list):
        print(f"❌ Error log must be a JSON array")
        return False
    
    for i, entry in enumerate(entries):
        required_fields = ['timestamp', 'error_type', 'file', 'row_number', 'raw_data', 'error_message']
        for field in required_fields:
            if field not in entry:
                print(f"❌ Error log entry {i} missing required field: {field}")
                return False
        
        # Type checks
        if not isinstance(entry['timestamp'], str):
            print(f"❌ Error log entry {i}: timestamp must be string")
            return False
        if not isinstance(entry['error_type'], str):
            print(f"❌ Error log entry {i}: error_type must be string")
            return False
        if not isinstance(entry['file'], str):
            print(f"❌ Error log entry {i}: file must be string")
            return False
        if not isinstance(entry['row_number'], int):
            print(f"❌ Error log entry {i}: row_number must be integer")
            return False
        if not isinstance(entry['raw_data'], str):
            print(f"❌ Error log entry {i}: raw_data must be string")
            return False
        if not isinstance(entry['error_message'], str):
            print(f"❌ Error log entry {i}: error_message must be string")
            return False
    
    print(f"✅ Error log structure valid ({len(entries)} entries)")
    return True


def validate_audit_log_structure(log_path: str) -> bool:
    """
    Validate audit log structure matches FR-009 requirements.
    
    Required fields:
    - timestamp (string, ISO format)
    - event_type (string)
    - dimension (string)
    - id (integer)
    - value (string)
    - attributes (object)
    """
    if not os.path.exists(log_path):
        print(f"❌ Audit log file not found: {log_path}")
        return False
    
    with open(log_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    
    if not isinstance(entries, list):
        print(f"❌ Audit log must be a JSON array")
        return False
    
    for i, entry in enumerate(entries):
        required_fields = ['timestamp', 'event_type', 'dimension', 'id', 'value', 'attributes']
        for field in required_fields:
            if field not in entry:
                print(f"❌ Audit log entry {i} missing required field: {field}")
                return False
        
        # Type checks
        if not isinstance(entry['timestamp'], str):
            print(f"❌ Audit log entry {i}: timestamp must be string")
            return False
        if not isinstance(entry['event_type'], str):
            print(f"❌ Audit log entry {i}: event_type must be string")
            return False
        if not isinstance(entry['dimension'], str):
            print(f"❌ Audit log entry {i}: dimension must be string")
            return False
        if not isinstance(entry['id'], int):
            print(f"❌ Audit log entry {i}: id must be integer")
            return False
        if not isinstance(entry['value'], str):
            print(f"❌ Audit log entry {i}: value must be string")
            return False
        if not isinstance(entry['attributes'], dict):
            print(f"❌ Audit log entry {i}: attributes must be object")
            return False
    
    print(f"✅ Audit log structure valid ({len(entries)} entries)")
    return True


def main():
    """Run validation tests."""
    print("=" * 60)
    print("ETLLogger Output Format Validation")
    print("=" * 60)
    
    # Create test logger
    test_error_log = "tests/tmp/test_errors.json"
    test_audit_log = "tests/tmp/test_audit.json"
    
    # Ensure tmp directory exists
    Path("tests/tmp").mkdir(parents=True, exist_ok=True)
    
    # Clean up old test files
    for log_file in [test_error_log, test_audit_log]:
        if os.path.exists(log_file):
            os.remove(log_file)
    
    logger = ETLLogger(test_error_log, test_audit_log)
    
    # Test error logging
    print("\n1. Testing error log format...")
    logger.log_error(
        error_type="malformed_row",
        file="data/raw/test.csv",
        row_number=42,
        raw_data="incomplete,row,data",
        error_message="Missing required field: Цена на дребно"
    )
    
    error_valid = validate_error_log_structure(test_error_log)
    
    # Test audit logging
    print("\n2. Testing audit log format...")
    logger.log_dimension_created(
        dimension="product",
        dimension_id=523,
        value="Ябълки Грени Смит",
        attributes={"name": "Ябълки Грени Смит", "category_id": 50, "product_code": ""}
    )
    
    audit_valid = validate_audit_log_structure(test_audit_log)
    
    # Summary
    print("\n" + "=" * 60)
    if error_valid and audit_valid:
        print("✅ ALL VALIDATIONS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ VALIDATION FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
