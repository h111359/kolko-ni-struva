"""
Data Normalizer for transforming raw CSV into star schema format.

This module provides the DataNormalizer class that reads raw price data
and generates normalized fact tables with dimension references.
"""

import csv
import os
import glob
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from .dimension_manager import DimensionManager
from .logger import ETLLogger


class DataNormalizer:
    """
    Normalizes raw price data into star schema format.
    
    Responsibilities:
    - Read raw CSV files
    - Extract and deduplicate dimension values
    - Replace dimension values with IDs in fact table
    - Handle malformed data (log and skip)
    - Generate fact_prices.csv
    
    Attributes:
        raw_data_dir (str): Path to data/raw/ directory
        output_fact_file (str): Path to output fact CSV file
        dimension_managers (Dict[str, DimensionManager]): Dimension managers by name
        logger (ETLLogger): Logger for errors and audit events
    """
    
    def __init__(self, 
                 raw_data_dir: str,
                 output_fact_file: str,
                 dimension_managers: Dict[str, DimensionManager],
                 logger: ETLLogger):
        """
        Initialize normalizer.
        
        Args:
            raw_data_dir: Path to data/raw/ directory
            output_fact_file: Path to output fact CSV file
            dimension_managers: Dict of dimension name -> DimensionManager instance
            logger: ETLLogger instance for logging
        """
        self.raw_data_dir = raw_data_dir
        self.output_fact_file = output_fact_file
        self.dimension_managers = dimension_managers
        self.logger = logger
        
        # Load nomenclatures for human-readable names
        self.city_nomenclature = self._load_city_nomenclature()
        self.category_nomenclature = self._load_category_nomenclature()
        
        # Statistics tracking
        self.stats = {
            "total_rows_processed": 0,
            "rows_written": 0,
            "rows_skipped": 0,
            "dimensions_created": {name: 0 for name in dimension_managers.keys()},
            "files_processed": 0
        }
    
    def _load_city_nomenclature(self) -> Dict[str, str]:
        """
        Load city nomenclature from JSON file to get human-readable city names.
        
        Returns:
            Dictionary mapping EKATTE code to city name
        """
        nomenclature_path = "data/cities-ekatte-nomenclature.json"
        try:
            with open(nomenclature_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.log_error({
                "error": f"City nomenclature file not found: {nomenclature_path}",
                "severity": "WARNING",
                "fallback": "Will use EKATTE codes as city names"
            })
            return {}
        except json.JSONDecodeError as e:
            self.logger.log_error({
                "error": f"Invalid JSON in city nomenclature file: {e}",
                "severity": "WARNING",
                "fallback": "Will use EKATTE codes as city names"
            })
            return {}
    
    def _load_category_nomenclature(self) -> Dict[str, str]:
        """
        Load category nomenclature from JSON file to get human-readable category names.
        
        Returns:
            Dictionary mapping category code to category name
        """
        nomenclature_path = "data/category-nomenclature.json"
        try:
            with open(nomenclature_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.log_error({
                "error": f"Category nomenclature file not found: {nomenclature_path}",
                "severity": "WARNING",
                "fallback": "Will use category codes as names"
            })
            return {}
        except json.JSONDecodeError as e:
            self.logger.log_error({
                "error": f"Invalid JSON in category nomenclature file: {e}",
                "severity": "WARNING",
                "fallback": "Will use category codes as names"
            })
            return {}
    
    def normalize(self, date_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute normalization process.
        
        Args:
            date_filter: Optional list of dates (YYYY-MM-DD) to process
        
        Returns:
            Statistics dictionary with processing results
        
        Side Effects:
            - Writes fact_prices.csv
            - Updates all dimension files via managers
            - Logs errors to logs/etl_errors.json
            - Logs new dimensions to logs/dimension_audit.json
        """
        print("=" * 60)
        print("Starting Data Normalization")
        print("=" * 60)
        
        # Load all dimension managers
        print("\n1. Loading dimension files...")
        for name, manager in self.dimension_managers.items():
            manager.load()
            print(f"   ✓ Loaded {name}: {len(manager.dimensions)} entries")
        
        # Track initial dimension counts
        initial_counts = {name: len(mgr.dimensions) for name, mgr in self.dimension_managers.items()}
        
        # Find raw CSV files
        print(f"\n2. Finding raw CSV files in {self.raw_data_dir}...")
        csv_files = self._find_csv_files(date_filter)
        print(f"   ✓ Found {len(csv_files)} files")
        
        # Process all CSV files and write incrementally
        print("\n3. Processing CSV files and writing fact table...")
        print(f"   Output: {self.output_fact_file}")
        
        # Initialize fact table file (write header)
        self._initialize_fact_table()
        
        for i, csv_file in enumerate(csv_files, 1):
            try:
                facts = self._process_csv_file(csv_file)
                self._append_facts(facts)
                self.stats["files_processed"] += 1
                
                # Progress update every 5 files
                if i % 5 == 0 or i == len(csv_files):
                    print(f"   Progress: {i}/{len(csv_files)} files ({self.stats['rows_written']:,} rows written)")
            except Exception as e:
                print(f"   ✗ Failed to process {os.path.basename(csv_file)}: {str(e)}")
                self.logger.log_error(
                    error_type="file_processing_error",
                    file=csv_file,
                    row_number=0,
                    raw_data="",
                    error_message=str(e)
                )
        
        print(f"   ✓ Completed: {self.stats['files_processed']} files, {self.stats['rows_written']:,} rows written")
        
        # Save all dimension files
        print("\n4. Saving dimension files...")
        for name, manager in self.dimension_managers.items():
            manager.save()
            new_count = len(manager.dimensions) - initial_counts[name]
            self.stats["dimensions_created"][name] = new_count
            print(f"   ✓ Saved {name}: {new_count} new entries")
        
        # Flush any remaining audit log entries
        print("\n5. Flushing audit logs...")
        self.logger.flush_audit_buffer()
        self.logger.flush_error_buffer()
        print("   ✓ Audit and error logs saved")
        
        # Final statistics
        print("\n" + "=" * 60)
        print("Normalization Complete")
        print("=" * 60)
        print(f"Total rows processed: {self.stats['total_rows_processed']:,}")
        print(f"Rows written: {self.stats['rows_written']:,}")
        print(f"Rows skipped: {self.stats['rows_skipped']:,}")
        print(f"Files processed: {self.stats['files_processed']}")
        print("\nNew dimensions created:")
        for name, count in self.stats["dimensions_created"].items():
            print(f"  - {name}: {count}")
        print("=" * 60)
        
        return self.stats
    
    def _find_csv_files(self, date_filter: Optional[List[str]] = None) -> List[str]:
        """
        Find raw CSV files to process.
        
        Args:
            date_filter: Optional list of dates to filter by
        
        Returns:
            List of CSV file paths
        """
        if date_filter:
            # Filter by specific dates
            files = []
            for date in date_filter:
                pattern = os.path.join(self.raw_data_dir, f"kolko_struva_{date}_account_*.csv")
                files.extend(glob.glob(pattern))
            return sorted(files)
        else:
            # Get all CSV files
            pattern = os.path.join(self.raw_data_dir, "kolko_struva_*.csv")
            return sorted(glob.glob(pattern))
    
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
        # Extract date and chain_id from filename
        # Format: kolko_struva_YYYY-MM-DD_account_N.csv
        filename = os.path.basename(filepath)
        parts = filename.replace('.csv', '').split('_')
        
        try:
            # Extract date (YYYY-MM-DD format - parts[2])
            date = parts[2]
            # Extract chain_id (account number - parts[4])
            chain_id = int(parts[4])
        except (IndexError, ValueError) as e:
            raise ValueError(f"Unable to extract date/chain_id from filename: {filename}")
        
        facts = []
        
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                self.stats["total_rows_processed"] += 1
                
                # Normalize row with extracted metadata
                fact = self._normalize_row(row, filepath, row_num, date, chain_id)
                
                if fact:
                    facts.append(fact)
                    self.stats["rows_written"] += 1
                else:
                    self.stats["rows_skipped"] += 1
        
        return facts
    
    def _normalize_row(self, row: Dict[str, str], filepath: str, row_number: int, date: str, chain_id: int) -> Optional[Dict[str, Any]]:
        """
        Normalize single CSV row.
        
        Args:
            row: Raw CSV row as dictionary
            filepath: Source file path (for error logging)
            row_number: Row number (for error logging)
            date: Date from filename (YYYY-MM-DD)
            chain_id: Chain ID from filename
        
        Returns:
            Normalized fact dictionary with dimension IDs, or None if row is invalid
        """
        try:
            # Extract required fields from CSV
            city_ekatte = row.get('Населено място', '').strip()
            trade_object_address = row.get('Търговски обект', '').strip()
            product_name = row.get('Наименование на продукта', '').strip()
            product_code = row.get('Код на продукта', '').strip()
            category_name = row.get('Категория', '').strip()
            retail_price_str = row.get('Цена на дребно', '').strip()
            promo_price_str = row.get('Цена в промоция', '').strip()
            
            # Validate required fields
            if not city_ekatte:
                raise ValueError("Missing required field: Населено място")
            if not trade_object_address:
                raise ValueError("Missing required field: Търговски обект")
            if not product_name:
                raise ValueError("Missing required field: Наименование на продукта")
            if not category_name:
                raise ValueError("Missing required field: Категория")
            
            # Normalize EKATTE code (ensure 5 digits, left-pad with zeros)
            city_ekatte = city_ekatte.split('-')[0]  # Remove suffix if present
            city_ekatte = city_ekatte.zfill(5)
            
            # Get or create dimension IDs
            # Get human-readable category name from nomenclature, fallback to code
            category_display_name = self.category_nomenclature.get(category_name, category_name)
            category_id = self.dimension_managers['category'].get_or_create({
                'name': category_display_name
            })
            
            # Get human-readable city name from nomenclature, fallback to EKATTE
            city_name = self.city_nomenclature.get(city_ekatte, city_ekatte)
            city_id = self.dimension_managers['city'].get_or_create({
                'ekatte_code': city_ekatte,
                'name': city_name
            })
            
            # Trade chain - just validate it exists (IDs come from source)
            trade_chain_id = chain_id
            
            # Trade object - composite key (chain_id + address)
            trade_object_id = self.dimension_managers['trade_object'].get_or_create({
                'chain_id': chain_id,
                'address': trade_object_address
            })
            
            # Product - composite key (name + product_code)
            product_id = self.dimension_managers['product'].get_or_create({
                'name': product_name,
                'product_code': product_code if product_code else None,
                'category_id': category_id
            })
            
            # Parse prices
            retail_price = float(retail_price_str) if retail_price_str else None
            promo_price = float(promo_price_str) if promo_price_str else None
            
            # Validate at least one price is present
            if retail_price is None and promo_price is None:
                raise ValueError("At least one price (retail or promo) must be present")
            
            # Create normalized fact
            return {
                'date': date,
                'trade_chain_id': trade_chain_id,
                'trade_object_id': trade_object_id,
                'city_id': city_id,
                'product_id': product_id,
                'category_id': category_id,
                'retail_price': retail_price,
                'promo_price': promo_price
            }
            
        except Exception as e:
            # Log error and return None
            self.logger.log_error(
                error_type="malformed_row",
                file=filepath,
                row_number=row_number,
                raw_data=str(row),
                error_message=str(e)
            )
            return None
    
    def _initialize_fact_table(self) -> None:
        """
        Initialize fact table CSV file with header.
        """
        # Ensure output directory exists
        Path(self.output_fact_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV header
        fieldnames = [
            'date', 'trade_chain_id', 'trade_object_id', 'city_id', 
            'product_id', 'category_id', 'retail_price', 'promo_price'
        ]
        
        with open(self.output_fact_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
    
    def _append_facts(self, facts: List[Dict[str, Any]]) -> None:
        """
        Append normalized facts to CSV file.
        
        Args:
            facts: List of normalized fact dictionaries
        """
        if not facts:
            return
        
        # Define CSV header
        fieldnames = [
            'date', 'trade_chain_id', 'trade_object_id', 'city_id', 
            'product_id', 'category_id', 'retail_price', 'promo_price'
        ]
        
        with open(self.output_fact_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            
            for fact in facts:
                # Convert None to empty string for CSV
                row = {k: (v if v is not None else '') for k, v in fact.items()}
                writer.writerow(row)
    
    def _write_fact_table(self, facts: List[Dict[str, Any]]) -> None:
        """
        Write normalized facts to CSV file.
        
        Args:
            facts: List of normalized fact dictionaries
            
        Note: This method is deprecated in favor of incremental writing.
              Kept for backward compatibility.
        """
        # Ensure output directory exists
        Path(self.output_fact_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV header
        fieldnames = [
            'date', 'trade_chain_id', 'trade_object_id', 'city_id', 
            'product_id', 'category_id', 'retail_price', 'promo_price'
        ]
        
        with open(self.output_fact_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            
            for fact in facts:
                # Convert None to empty string for CSV
                row = {k: (v if v is not None else '') for k, v in fact.items()}
                writer.writerow(row)
