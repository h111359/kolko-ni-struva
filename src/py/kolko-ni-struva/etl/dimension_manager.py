"""
Dimension Manager for managing dimension files lifecycle.

This module provides the DimensionManager class for loading, creating,
and persisting dimension entries with automatic ID assignment.
"""

import json
import os
from typing import Dict, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    from .logger import ETLLogger


@dataclass
class DimensionEntry:
    """Single dimension entry with metadata."""
    id: int
    attributes: Dict[str, Any]


class DimensionManager:
    """
    Manages a single dimension file (category, city, product, trade_chain, or trade_object).
    
    Responsibilities:
    - Load dimension file from disk
    - Assign new IDs to unseen values
    - Perform lookups (value -> ID)
    - Save dimension file back to disk
    - Monitor file size warnings
    
    Attributes:
        dimension_name (str): Name of the dimension
        dimension_file_path (str): Path to JSON dimension file
        lookup_key_fn (Callable): Function to generate lookup key from attributes
        dimensions (Dict[int, Dict]): Map of ID to attributes
        lookup_index (Dict[str, int]): Map of lookup key to ID
        next_id (int): Next available ID
    """
    
    def __init__(self, 
                 dimension_name: str, 
                 dimension_file_path: str, 
                 lookup_key_fn: Callable[[Dict], str],
                 logger: Optional['ETLLogger'] = None):
        """
        Initialize dimension manager.
        
        Args:
            dimension_name: Name of dimension (e.g., "category", "city", "product")
            dimension_file_path: Path to JSON dimension file
            lookup_key_fn: Function to generate lookup key from attributes dict
            logger: Optional ETLLogger instance for audit logging
        """
        self.dimension_name = dimension_name
        self.dimension_file_path = dimension_file_path
        self.lookup_key_fn = lookup_key_fn
        self.logger = logger
        
        # Internal state
        self.dimensions: Dict[int, Dict[str, Any]] = {}
        self.lookup_index: Dict[str, int] = {}
        self.next_id: int = 1
        self.version: str = "1.0"
        
        # Track new entries for audit
        self._new_entries: list = []
    
    def load(self) -> None:
        """
        Load dimension from JSON file.
        
        Creates new dimension file with initial structure if not exists.
        Raises IOError if file exists but is malformed.
        """
        if not os.path.exists(self.dimension_file_path):
            # Initialize new dimension file
            self.dimensions = {}
            self.lookup_index = {}
            self.next_id = 1
            self.version = "1.0"
            
            # Ensure directory exists
            Path(self.dimension_file_path).parent.mkdir(parents=True, exist_ok=True)
            return
        
        try:
            with open(self.dimension_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict):
                raise IOError(f"Dimension file {self.dimension_file_path} has invalid structure")
            
            # Load dimensions (convert string keys to int)
            dimensions_data = data.get("dimensions", {})
            self.dimensions = {int(k): v for k, v in dimensions_data.items()}
            
            # Load metadata
            self.lookup_index = data.get("lookup_index", {})
            self.next_id = data.get("next_id", 1)
            self.version = data.get("version", "1.0")
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise IOError(f"Failed to load dimension file {self.dimension_file_path}: {str(e)}")
    
    def get_or_create(self, attributes: Dict[str, Any]) -> int:
        """
        Get existing dimension ID or create new entry.
        
        Args:
            attributes: Dimension attributes (e.g., {"name": "София", "ekatte_code": "68134"})
        
        Returns:
            Integer ID for the dimension entry
        
        Side Effects:
            - If new entry created, logs to audit file (if logger provided)
            - Updates internal next_id counter
        """
        # Generate lookup key
        lookup_key = self.lookup_key_fn(attributes)
        
        # Check if entry already exists
        if lookup_key in self.lookup_index:
            return self.lookup_index[lookup_key]
        
        # Create new entry
        new_id = self.next_id
        self.dimensions[new_id] = attributes
        self.lookup_index[lookup_key] = new_id
        self.next_id += 1
        
        # Log to audit (if logger provided)
        if self.logger:
            # Determine primary value for audit log
            primary_value = attributes.get("name") or attributes.get("ekatte_code") or lookup_key
            self.logger.log_dimension_created(
                dimension=self.dimension_name,
                dimension_id=new_id,
                value=str(primary_value),
                attributes=attributes
            )
        
        return new_id
    
    def get(self, dimension_id: int) -> Optional[DimensionEntry]:
        """
        Get dimension entry by ID.
        
        Args:
            dimension_id: Integer ID to lookup
        
        Returns:
            DimensionEntry if found, None otherwise
        """
        if dimension_id not in self.dimensions:
            return None
        
        return DimensionEntry(
            id=dimension_id,
            attributes=self.dimensions[dimension_id]
        )
    
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
        # Ensure directory exists
        Path(self.dimension_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Prepare data structure (convert int keys to strings for JSON)
        data = {
            "version": self.version,
            "generated": datetime.utcnow().isoformat() + "Z",
            "dimensions": {str(k): v for k, v in sorted(self.dimensions.items())},
            "next_id": self.next_id,
            "lookup_index": dict(sorted(self.lookup_index.items()))
        }
        
        try:
            with open(self.dimension_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            raise IOError(f"Failed to save dimension file {self.dimension_file_path}: {str(e)}")
    
    def check_size_warnings(self) -> None:
        """
        Check dimension file size and log warning if exceeds thresholds.
        
        Thresholds:
            - File size: 10 MB
            - Entry count: 100,000 rows
        
        Side Effects:
            Prints warning message to console if threshold exceeded
        """
        # Check entry count
        entry_count = len(self.dimensions)
        if entry_count > 100000:
            print(f"⚠️  WARNING: Dimension '{self.dimension_name}' has {entry_count:,} entries (threshold: 100,000)")
            print(f"   File: {self.dimension_file_path}")
            print(f"   Consider archival strategy for old entries.")
        
        # Check file size
        if os.path.exists(self.dimension_file_path):
            file_size_mb = os.path.getsize(self.dimension_file_path) / (1024 * 1024)
            if file_size_mb > 10:
                print(f"⚠️  WARNING: Dimension '{self.dimension_name}' file is {file_size_mb:.2f} MB (threshold: 10 MB)")
                print(f"   File: {self.dimension_file_path}")
                print(f"   Consider archival strategy or compression.")
