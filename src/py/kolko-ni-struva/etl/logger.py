"""
ETL Logger for structured JSON logging of errors and audit events.

This module provides the ETLLogger class for recording ETL process events
in structured JSON format for easy parsing and monitoring.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path


class ETLLogger:
    """
    Manages JSON-formatted logging for ETL process.
    
    Responsibilities:
    - Log errors (malformed rows, missing data)
    - Log audit events (new dimensions created)
    - Append to JSON log files
    - Create log files if they don't exist
    
    Attributes:
        error_log_path (str): Path to error log JSON file
        audit_log_path (str): Path to audit log JSON file
    """
    
    def __init__(self, error_log_path: str, audit_log_path: str):
        """
        Initialize logger.
        
        Args:
            error_log_path: Path to error log JSON file (e.g., logs/etl_errors.json)
            audit_log_path: Path to audit log JSON file (e.g., logs/dimension_audit.json)
        """
        self.error_log_path = error_log_path
        self.audit_log_path = audit_log_path
        
        # Buffered audit entries for batch writing
        self._audit_buffer: List[Dict[str, Any]] = []
        self._audit_buffer_size = 5000  # Write every 5000 entries (reduced I/O)
        
        # Buffered error entries for batch writing
        self._error_buffer: List[Dict[str, Any]] = []
        self._error_buffer_size = 1000  # Write every 1000 errors
        
        # Ensure log directories exist
        Path(error_log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(audit_log_path).parent.mkdir(parents=True, exist_ok=True)
    
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
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": error_type,
            "file": file,
            "row_number": row_number,
            "raw_data": raw_data,
            "error_message": error_message
        }
        
        # Buffer the entry
        self._error_buffer.append(entry)
        
        # Flush buffer if it reaches threshold
        if len(self._error_buffer) >= self._error_buffer_size:
            self.flush_error_buffer()
    
    def flush_error_buffer(self) -> None:
        """
        Flush buffered error entries to file.
        Should be called at end of ETL process to ensure all entries are written.
        """
        if not self._error_buffer:
            return
        
        # Load existing log entries or start with empty list
        if os.path.exists(self.error_log_path):
            try:
                with open(self.error_log_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or empty, start fresh
                entries = []
        else:
            entries = []
        
        # Append buffered entries
        entries.extend(self._error_buffer)
        
        # Write back to file with pretty formatting
        with open(self.error_log_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        # Clear buffer
        self._error_buffer.clear()
    
    def log_dimension_created(self,
                             dimension: str,
                             dimension_id: int,
                             value: str,
                             attributes: Dict[str, Any]) -> None:
        """
        Log new dimension entry creation.
        
        Args:
            dimension: Dimension name (category, city, product, trade_chain, trade_object)
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
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "event_type": "new_dimension_entry",
            "dimension": dimension,
            "id": dimension_id,
            "value": value,
            "attributes": attributes
        }
        
        # Buffer the entry
        self._audit_buffer.append(entry)
        
        # Flush buffer if it reaches threshold
        if len(self._audit_buffer) >= self._audit_buffer_size:
            self.flush_audit_buffer()
    
    def flush_audit_buffer(self) -> None:
        """
        Flush buffered audit entries to file.
        Should be called at end of ETL process to ensure all entries are written.
        """
        if not self._audit_buffer:
            return
        
        # Load existing log entries or start with empty list
        if os.path.exists(self.audit_log_path):
            try:
                with open(self.audit_log_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or empty, start fresh
                entries = []
        else:
            entries = []
        
        # Append buffered entries
        entries.extend(self._audit_buffer)
        
        # Write back to file with pretty formatting
        with open(self.audit_log_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        
        # Clear buffer
        self._audit_buffer.clear()
    
    def _append_to_log(self, log_path: str, entry: Dict[str, Any]) -> None:
        """
        Append entry to JSON log file.
        
        Args:
            log_path: Path to log file
            entry: Log entry dictionary
        
        Creates log file with JSON array structure if not exists.
        Appends to existing array if file exists.
        """
        # Load existing log entries or start with empty list
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
                    if not isinstance(entries, list):
                        entries = []
            except (json.JSONDecodeError, IOError):
                # If file is corrupted or empty, start fresh
                entries = []
        else:
            entries = []
        
        # Append new entry
        entries.append(entry)
        
        # Write back to file with pretty formatting
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
