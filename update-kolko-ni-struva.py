#!/usr/bin/env python3
"""
Unified Kolko Ni Struva Updater
Downloads data from kolkostruva.bg and merges it into data.csv
If called without parameters, downloads today and yesterday data
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
OUTPUT_FILE = "data.csv"
BASE_URL = "https://kolkostruva.bg/opendata"
CONFIG_FILE = "trade_chains_config.json"
DEPLOY_DIR = "kolko-ni-struva"
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
        self.session = requests.Session()
        self.trade_chains = self._load_trade_chains()
        
    def _load_trade_chains(self):
        """Load trade chains from trade-chains-nomenclature.json"""
        try:
            with open('trade-chains-nomenclature.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error("trade-chains-nomenclature.json not found!")
            return {}
    
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
    
    def download_csv_for_account(self, date, account_id):
        """Download CSV file for a specific date and account ID"""
        try:
            url = f"{BASE_URL}?date={date}&account={account_id}"
            logger.info(f"Fetching data for account {account_id} on {date}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find CSV download link
            csv_link = soup.find('a', href=re.compile(r'\.csv'))
            if not csv_link:
                logger.debug(f"No CSV link found for account {account_id} on {date}")
                return None
            
            csv_url = urljoin(BASE_URL, csv_link['href'])
            
            # Download the CSV file
            csv_response = self.session.get(csv_url, timeout=30)
            csv_response.raise_for_status()
            
            # Create output directory if it doesn't exist
            os.makedirs(DOWNLOADS_DIR, exist_ok=True)
            
            # Generate filename
            filename = f"kolko_struva_{date}_account_{account_id}.csv"
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            
            # Save the file
            with open(filepath, 'wb') as f:
                f.write(csv_response.content)
            
            logger.info(f"Successfully downloaded: {filepath}")
            return filepath
            
        except Exception as e:
            logger.warning(f"Error downloading CSV for account {account_id}: {e}")
            return None
    
    def download_all_for_date(self, date):
        """Download CSV files for all available trade chains for a given date"""
        logger.info(f"Starting download for {date}")
        
        if not self.trade_chains:
            logger.error("No trade chains found. Cannot proceed with download.")
            return []
        
        downloaded_files = []
        
        for account_id in self.trade_chains.keys():
            filepath = self.download_csv_for_account(date, account_id)
            if filepath:
                downloaded_files.append(filepath)
            
            # Small delay to be respectful to the server
            import time
            time.sleep(0.3)
        
        logger.info(f"Downloaded {len(downloaded_files)} files for {date}")
        return downloaded_files
    
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
    
    def update(self, dates=None, keep_only_latest_two=True):
        """
        Update data by downloading specified dates and merging
        
        Args:
            dates: List of dates to download (format: YYYY-MM-DD)
                   If None, downloads today and yesterday
            keep_only_latest_two: If True, only keep the latest 2 days in data.csv
        """
        if dates is None:
            # Default: download today and yesterday
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            dates = [today.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d')]
        
        logger.info(f"Updating data for dates: {', '.join(dates)}")
        
        # Download data for specified dates
        for date in dates:
            self.download_all_for_date(date)
        
        # Merge data
        if keep_only_latest_two:
            # Get all available dates including newly downloaded
            all_dates = self.get_available_dates_in_data()
            
            # Add the dates we just downloaded
            for date in dates:
                if date not in all_dates:
                    all_dates.append(date)
            
            # Sort and keep only the latest 2
            all_dates = sorted(all_dates, reverse=True)[:2]
            logger.info(f"Keeping only latest 2 days: {', '.join(all_dates)}")
            
            self.merge_data(keep_only_dates=set(all_dates))
        else:
            self.merge_data()
        
        logger.info("Update complete!")
        return all_dates if keep_only_latest_two else dates
    
    def deploy_to_folder(self):
        """
        Deploy website files to kolko-ni-struva folder
        Clears the folder first, then copies all necessary files
        """
        logger.info(f"Deploying files to {DEPLOY_DIR} folder...")
        
        try:
            # Create deploy directory if it doesn't exist, or clear it if it does
            if os.path.exists(DEPLOY_DIR):
                logger.info(f"Clearing existing {DEPLOY_DIR} folder...")
                shutil.rmtree(DEPLOY_DIR)
            
            os.makedirs(DEPLOY_DIR, exist_ok=True)
            logger.info(f"Created {DEPLOY_DIR} folder")
            
            # Copy each file
            copied_files = []
            for filename in FILES_TO_DEPLOY:
                src = filename
                dst = os.path.join(DEPLOY_DIR, filename)
                
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                    file_size = os.path.getsize(src)
                    logger.info(f"Copied {filename} ({file_size:,} bytes)")
                    copied_files.append(filename)
                else:
                    logger.warning(f"File {filename} not found, skipping...")
            
            logger.info(f"Deployment complete! Copied {len(copied_files)} files to {DEPLOY_DIR}/")
            return copied_files
            
        except Exception as e:
            logger.error(f"Error during deployment: {e}")
            return []
    
    def deploy_to_netlify(self):
        """
        Deploy the kolko-ni-struva folder to Netlify using REST API
        Requires NETLIFY_AUTH_TOKEN environment variable to be set
        No npm or CLI required - uses pure Python!
        """
        logger.info(f"Deploying to Netlify (site: {NETLIFY_SITE_ID})...")
        
        # Check if netlify token is set
        netlify_token = os.environ.get(NETLIFY_TOKEN_ENV)
        if not netlify_token:
            logger.error(f"Netlify token not found! Set {NETLIFY_TOKEN_ENV} environment variable.")
            logger.info(f"Example: export {NETLIFY_TOKEN_ENV}='your-netlify-token-here'")
            return False
        
        # Check if deploy directory exists
        if not os.path.exists(DEPLOY_DIR):
            logger.error(f"Deploy directory {DEPLOY_DIR} not found! Run deployment first.")
            return False
        
        try:
            import hashlib
            import base64
            from pathlib import Path
            
            # Netlify API endpoint
            api_base = "https://api.netlify.com/api/v1"
            headers = {
                "Authorization": f"Bearer {netlify_token}",
                "Content-Type": "application/json"
            }
            
            logger.info("Step 1/3: Preparing files for upload...")
            
            # Collect all files and calculate their SHA1 hashes
            files_to_upload = {}
            file_hashes = {}
            
            for root, dirs, files in os.walk(DEPLOY_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, DEPLOY_DIR)
                    
                    # Normalize path separators for Netlify
                    relative_path = relative_path.replace(os.sep, '/')
                    
                    # Calculate SHA1 hash
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        sha1_hash = hashlib.sha1(content).hexdigest()
                        file_hashes[relative_path] = sha1_hash
                        files_to_upload[relative_path] = content
            
            logger.info(f"Found {len(files_to_upload)} files to upload")
            
            # Step 2: Create a new deploy
            logger.info("Step 2/3: Creating deployment...")
            deploy_payload = {
                "files": file_hashes
            }
            
            response = self.session.post(
                f"{api_base}/sites/{NETLIFY_SITE_ID}/deploys",
                headers=headers,
                json=deploy_payload,
                timeout=60
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create deploy: {response.status_code} - {response.text}")
                return False
            
            deploy_data = response.json()
            deploy_id = deploy_data['id']
            required_files = deploy_data.get('required', [])
            
            logger.info(f"Deploy created: {deploy_id}")
            logger.info(f"Need to upload {len(required_files)} files")
            
            # Step 3: Upload required files
            logger.info("Step 3/3: Uploading files...")
            
            for file_path in required_files:
                if file_path not in files_to_upload:
                    logger.warning(f"Required file not found: {file_path}")
                    continue
                
                content = files_to_upload[file_path]
                
                # Upload file
                upload_response = self.session.put(
                    f"{api_base}/deploys/{deploy_id}/files/{file_path}",
                    headers={
                        "Authorization": f"Bearer {netlify_token}",
                        "Content-Type": "application/octet-stream"
                    },
                    data=content,
                    timeout=120
                )
                
                if upload_response.status_code == 200:
                    logger.info(f"  ✓ Uploaded: {file_path}")
                else:
                    logger.warning(f"  ✗ Failed to upload {file_path}: {upload_response.status_code}")
            
            # Wait a moment for Netlify to process
            import time
            time.sleep(2)
            
            # Get deploy status
            status_response = self.session.get(
                f"{api_base}/deploys/{deploy_id}",
                headers=headers,
                timeout=30
            )
            
            if status_response.status_code == 200:
                deploy_info = status_response.json()
                site_url = deploy_info.get('ssl_url') or deploy_info.get('url')
                deploy_state = deploy_info.get('state')
                
                logger.info("✅ Successfully deployed to Netlify!")
                logger.info(f"Deploy ID: {deploy_id}")
                logger.info(f"Deploy State: {deploy_state}")
                if site_url:
                    logger.info(f"Website URL: {site_url}")
                
                return True
            else:
                logger.warning("Deploy uploaded but couldn't get status")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during Netlify deployment: {e}")
            return False
        except Exception as e:
            logger.error(f"Error deploying to Netlify: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Update kolko ni struva data - downloads and merges price data'
    )
    parser.add_argument(
        '--dates',
        nargs='+',
        help='Specific dates to download (YYYY-MM-DD). Default: today and yesterday'
    )
    parser.add_argument(
        '--keep-all',
        action='store_true',
        help='Keep all historical data instead of only latest 2 days'
    )
    parser.add_argument(
        '--no-deploy',
        action='store_true',
        help='Skip deploying files to kolko-ni-struva folder'
    )
    parser.add_argument(
        '--netlify',
        action='store_true',
        help='Deploy to Netlify after local deployment'
    )
    
    args = parser.parse_args()
    
    # Validate date formats if provided
    dates = None
    if args.dates:
        dates = []
        for date_str in args.dates:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(date_str)
            except ValueError:
                logger.error(f"Invalid date format: {date_str}. Use YYYY-MM-DD format.")
                return
    
    # Run the update
    updater = KolkoNiStruvaUpdater()
    updated_dates = updater.update(dates=dates, keep_only_latest_two=not args.keep_all)
    
    # Deploy files to kolko-ni-struva folder
    deployed_files = []
    if not args.no_deploy:
        deployed_files = updater.deploy_to_folder()
    
    # Deploy to Netlify if requested
    netlify_deployed = False
    if args.netlify and deployed_files:
        netlify_deployed = updater.deploy_to_netlify()
    
    print("\n" + "="*60)
    print("✅ Update Complete!")
    print("="*60)
    print(f"Data available for dates: {', '.join(updated_dates)}")
    print(f"Output file: {OUTPUT_FILE}")
    if deployed_files:
        print(f"Deployed {len(deployed_files)} files to {DEPLOY_DIR}/")
    if netlify_deployed:
        print(f"✅ Deployed to Netlify (site: {NETLIFY_SITE_ID})")
    elif args.netlify:
        print(f"⚠️  Netlify deployment skipped or failed")
    print("="*60)

if __name__ == "__main__":
    main()
