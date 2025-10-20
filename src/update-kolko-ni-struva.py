#!/usr/bin/env python3
"""
Kolko Ni Struva Data Merger
Merges downloaded CSV files from downloads/ into data/data.csv.
Keeps only the last two available dates by default.
"""

import os
import csv
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
import argparse
import logging
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DOWNLOADS_DIR = "downloads"
OUTPUT_FILE = "web-deploy/data.csv"
BASE_URL = "https://kolkostruva.bg/opendata"
CONFIG_FILE = "web-deploy/trade-chains-nomenclature.json"
DEPLOY_DIR = "web-deploy"
NETLIFY_SITE_ID = "b2c0c6b5-58f2-4620-892b-0f5a4d9513f2"
NETLIFY_TOKEN_ENV = "NETLIFY_AUTH_TOKEN"  # Environment variable name
FILES_TO_DEPLOY = [
    "index.html",
    "script.js",
    "style.css",
    "data.csv",
    "category-nomenclature.json",
    "cities-ekatte-nomenclature.json",
    "trade-chains-nomenclature.json"
]

class KolkoNiStruvaUpdater:
    def __init__(self):
        pass
        
    # Download logic removed. See src/download-kolkonistruva.py
    
    def normalize_city_code(self, code):
        """
        Normalize city codes (EKATTE codes) to 5-digit format:
        - Remove everything after first 5 digits (e.g., "68134-01" -> "68134")
        - Left-pad with zeros to 5 digits (e.g., "702" -> "00702")
        - Return empty string if code is empty or invalid
        """
        if not code or not isinstance(code, str):
            return ""
        
        # Strip whitespace
        code = code.strip()
        
        # Extract first 5 digits (remove anything after hyphen or non-digit)
        digits_only = ""
        for char in code:
            if char.isdigit():
                digits_only += char
                if len(digits_only) == 5:
                    break
            elif digits_only:  # Stop at first non-digit after digits started
                break
        
        # Left-pad to 5 digits
        if digits_only:
            return digits_only.zfill(5)
        
        return ""
    
    # Download logic removed. See src/download-kolkonistruva.py
    
    # Download logic removed. See src/download-kolkonistruva.py
    
    def extract_date_chain_from_filename(self, filename):
        """Extract date and chain ID from filename"""
        match = re.match(r"kolko_struva_(\d{4}-\d{2}-\d{2})_account_(\d+)\.csv", filename)
        if match:
            return match.group(1), match.group(2)
        return None, None
    
    def merge_data(self, keep_only_dates=None):
        """
        Merge all CSV files from downloads folder into data.csv
        If keep_only_dates is provided, only keep data for those dates
        """
        logger.info("Starting data merge...")
        
        # Define the standard header order for output
        STANDARD_HEADER = [
            "Населено място",
            "Търговски обект", 
            "Наименование на продукта",
            "Код на продукта",
            "Категория",
            "Цена на дребно",
            "Цена в промоция"
        ]
        
        # Collect all new rows and their (date, chain) keys
        new_rows = []
        new_keys = set()

        for fname in sorted(os.listdir(DOWNLOADS_DIR)):
            if fname.endswith(".csv"):
                date, chain = self.extract_date_chain_from_filename(fname)
                if not date or not chain:
                    continue
                    
                # Skip if we're filtering by dates and this date is not in the list
                if keep_only_dates and date not in keep_only_dates:
                    continue
                
                file_path = os.path.join(DOWNLOADS_DIR, fname)
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    # Detect delimiter by reading first line
                    first_line = f.readline()
                    f.seek(0)
                    
                    # Check if file uses semicolon or comma as delimiter
                    if ';' in first_line and first_line.count(';') > first_line.count(','):
                        delimiter = ';'
                        quoting = csv.QUOTE_MINIMAL
                    else:
                        delimiter = ','
                        quoting = csv.QUOTE_ALL
                    
                    reader = csv.reader(f, delimiter=delimiter, quotechar='"', quoting=quoting)
                    file_header = next(reader, None)
                    
                    for row in reader:
                        # Create row dict with date and chain_id
                        row_dict = {"date": date, "chain_id": chain}
                        
                        # Map file columns to standard header
                        if file_header:
                            for i, h in enumerate(file_header):
                                if i < len(row):
                                    value = row[i]
                                    # Normalize city code if this is the "Населено място" column
                                    if h == "Населено място":
                                        value = self.normalize_city_code(value)
                                    row_dict[h] = value
                                else:
                                    row_dict[h] = ""
                        
                        new_rows.append(row_dict)
                        new_keys.add((date, chain))

        # Load existing rows and filter
        filtered_existing = []
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row_dict in reader:
                    row_date = row_dict.get("date")
                    row_chain = row_dict.get("chain_id")
                    
                    # Keep existing row if:
                    # - It's not being replaced by new data (not in new_keys)
                    # - AND if we're filtering by dates, it's in the allowed dates
                    if (row_date, row_chain) not in new_keys:
                        if keep_only_dates is None or row_date in keep_only_dates:
                            filtered_existing.append(row_dict)

        # Write merged data as CSV
        merged_rows = filtered_existing + new_rows
        if merged_rows:
            # Define explicit header order: date, chain_id, then standard columns
            headers = ['date', 'chain_id'] + STANDARD_HEADER
            
            with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=headers,
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                for row in merged_rows:
                    # Ensure all header keys are present in each row
                    row_out = {h: row.get(h, "") for h in headers}
                    writer.writerow(row_out)
            
            logger.info(f"Merged {len(merged_rows)} rows into {OUTPUT_FILE}")
        else:
            # If no rows, write only header
            with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow(['date', 'chain_id'] + STANDARD_HEADER)
            
            logger.info(f"Created empty {OUTPUT_FILE} with header")
    
    def get_available_dates_in_data(self):
        """Get all unique dates from the current data.csv file"""
        dates = set()
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date = row.get('date')
                    if date:
                        dates.add(date)
        return sorted(dates)
    
    def update(self, dates=None):
        """
        Merge data for the specified dates (if provided) or the last two available dates in downloads/ into data/data.csv.
        On first run (if build/data.csv does not exist or is empty), scan downloads/ for available dates.
        """
        all_dates = self.get_available_dates_in_data()
        # If no dates found in data.csv, scan downloads/ for available dates
        if not all_dates:
            logger.warning("No data.csv found or no dates in data.csv. Scanning downloads/ for available dates...")
            found_dates = set()
            for fname in os.listdir(DOWNLOADS_DIR):
                if fname.endswith(".csv"):
                    date, chain = self.extract_date_chain_from_filename(fname)
                    if date:
                        found_dates.add(date)
            all_dates = sorted(found_dates)
            if not all_dates:
                logger.error("No data files found in downloads/.")
                return []
        if dates:
            # Only keep dates that are available
            merge_dates = [d for d in dates if d in all_dates]
            if not merge_dates:
                logger.error(f"None of the specified dates found in downloads/: {dates}")
                return []
            logger.info(f"Merging data for specified dates: {', '.join(merge_dates)}")
        else:
            # Default: last two dates
            merge_dates = sorted(all_dates, reverse=True)[:2]
            logger.info(f"Merging data for latest 2 days: {', '.join(merge_dates)}")
        self.merge_data(keep_only_dates=set(merge_dates))
        logger.info("Update complete!")
        return merge_dates
    
    def deploy_to_folder(self):
        """
        Deploy website files to kolko-ni-struva folder
        Clears the folder first, then copies all necessary files from web-deploy/.
        Also copies index.html, script.js, and style.css from src/ to web-deploy/ after clearing.
        """
        logger.info(f"Deploying files to {DEPLOY_DIR} folder...")
        try:
            # Create deploy directory if it doesn't exist, or clear it if it does
            if os.path.exists(DEPLOY_DIR):
                logger.info(f"Clearing existing {DEPLOY_DIR} folder...")
                shutil.rmtree(DEPLOY_DIR)
            os.makedirs(DEPLOY_DIR, exist_ok=True)
            logger.info(f"Created {DEPLOY_DIR} folder")

            # Copy index.html, script.js, and style.css from src/ to web-deploy/
            static_files = ["index.html", "script.js", "style.css"]
            for fname in static_files:
                src_path = os.path.join("src", fname)
                dst_path = os.path.join(DEPLOY_DIR, fname)
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    file_size = os.path.getsize(src_path)
                    logger.info(f"Copied {fname} from src/ to web-deploy/ ({file_size:,} bytes)")
                else:
                    logger.warning(f"File {fname} not found in src/, skipping...")

            # Copy nomenclature files from data/ to web-deploy/
            nomenclature_files = [
                "category-nomenclature.json",
                "cities-ekatte-nomenclature.json",
                "trade-chains-nomenclature.json"
            ]
            for fname in nomenclature_files:
                src_path = os.path.join("data", fname)
                dst_path = os.path.join(DEPLOY_DIR, fname)
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
                    file_size = os.path.getsize(src_path)
                    logger.info(f"Copied {fname} from data/ to web-deploy/ ({file_size:,} bytes)")
                else:
                    logger.warning(f"File {fname} not found in data/, skipping...")

        except Exception as e:
            logger.error(f"Error during deployment: {e}")
            return []
    

def main():
    parser = argparse.ArgumentParser(
        description='Merge Kolko Ni Struva data from downloads/ into data/data.csv (last 2 dates by default)'
    )
    parser.add_argument(
        '--dates', nargs='+',
        help='Specific dates to merge (YYYY-MM-DD). If not provided, merges the last 2 available dates.'
    )
    args = parser.parse_args()

    updater = KolkoNiStruvaUpdater()
    updated_dates = updater.update(dates=args.dates)

    print("\n" + "="*60)
    print("✅ Data Merge Complete!")
    print("="*60)
    print(f"Data available for dates: {', '.join(updated_dates)}")
    print(f"Output file: {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()
