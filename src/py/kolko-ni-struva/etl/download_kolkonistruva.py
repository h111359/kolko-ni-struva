#!/usr/bin/env python3
"""
Kolko Ni Struva Downloader
Downloads data from kolkostruva.bg and saves CSVs in data/raw/.
"""

import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = "data/raw/"
BASE_URL = "https://kolkostruva.bg/opendata"
TRADE_CHAINS_FILE = "data/trade-chains-nomenclature.json"

class KolkoNiStruvaDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.trade_chains = self._load_trade_chains()

    def update_trade_chains_from_web(self, date):
        """
        Checks the trade chains from the web page for the given date and updates the local nomenclature file if new chains are found.
        """
        url = f"{BASE_URL}?date={date}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            # Find the select element for trade chains (correct name/id is 'account')
            select = soup.find('select', attrs={'name': 'account'})
            if not select:
                select = soup.find('select', attrs={'id': 'account'})
            if not select:
                logger.warning(f"No trade chain <select> found with name or id 'account' for {date}")
                return
            web_chains = {}
            for option in select.find_all('option'):
                chain_id = option.get('value')
                chain_name = option.text.strip()
                # Skip the first option (prompt)
                if not chain_id or chain_id == "":
                    continue
                if chain_id and chain_name:
                    web_chains[chain_id] = chain_name
            # Compare and add new chains
            updated = False
            for chain_id, chain_name in web_chains.items():
                if chain_id not in self.trade_chains:
                    logger.info(f"Adding new trade chain: {chain_id} - {chain_name}")
                    self.trade_chains[chain_id] = chain_name
                    updated = True
            if updated:
                # Sort trade chains by key before saving
                sorted_chains = dict(sorted(self.trade_chains.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]))
                try:
                    with open(TRADE_CHAINS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(sorted_chains, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated trade chains nomenclature saved to {TRADE_CHAINS_FILE}")
                except Exception as e:
                    logger.error(f"Failed to save updated trade chains nomenclature: {e}")
            else:
                logger.info("No new trade chains found.")
        except Exception as e:
            logger.error(f"Error updating trade chains from web: {e}")

    def _load_trade_chains(self):
        try:
            with open(TRADE_CHAINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"{TRADE_CHAINS_FILE} not found!")
            return {}

    def download_csv_for_account(self, date, account_id):
        import time
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                url = f"{BASE_URL}?date={date}&account={account_id}"
                logger.info(f"Fetching data for account {account_id} on {date} (attempt {attempt})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                csv_link = soup.find('a', href=re.compile(r'\.csv'))
                if not csv_link:
                    logger.warning(f"No CSV link found for account {account_id} on {date} (attempt {attempt})")
                    if attempt < attempts:
                        time.sleep(5)
                    continue
                csv_url = urljoin(BASE_URL, csv_link['href'])
                csv_response = self.session.get(csv_url, timeout=30)
                csv_response.raise_for_status()
                os.makedirs(DOWNLOADS_DIR, exist_ok=True)
                filename = f"kolko_struva_{date}_account_{account_id}.csv"
                filepath = os.path.join(DOWNLOADS_DIR, filename)
                try:
                    with open(filepath, 'wb') as f:
                        f.write(csv_response.content)
                    logger.info(f"Successfully downloaded: {filepath}")
                    return filepath
                except Exception as file_err:
                    logger.error(f"Failed to store file locally: {filepath} ({file_err}) (attempt {attempt})")
                    if attempt < attempts:
                        time.sleep(5)
                    continue
            except Exception as e:
                logger.warning(f"Error downloading CSV for account {account_id}: {e} (attempt {attempt})")
                if attempt < attempts:
                    time.sleep(5)
                continue
        # All attempts failed
        return None

    def download_all_for_date(self, date):
        logger.info(f"Starting download for {date}")
        # Update trade chains from web before downloading
        self.update_trade_chains_from_web(date)
        if not self.trade_chains:
            logger.error("No trade chains found. Cannot proceed with download.")
            return []
        downloaded_files = []
        failed_accounts = []
        for account_id in self.trade_chains.keys():
            filepath = self.download_csv_for_account(date, account_id)
            if filepath:
                downloaded_files.append(filepath)
            else:
                failed_accounts.append(account_id)
            import time
            time.sleep(0.3)
        if len(downloaded_files) == 0:
            logger.warning(f"No files were downloaded for {date}!")
        else:
            logger.info(f"Downloaded {len(downloaded_files)} files for {date}")
        if failed_accounts:
            logger.warning(f"Accounts with missing data for {date}: {', '.join(str(a) for a in failed_accounts)}")
        return downloaded_files

def main():
    parser = argparse.ArgumentParser(
        description='Download Kolko Ni Struva data for given dates.'
    )
    parser.add_argument(
        '--dates', nargs='+', required=True,
        help='Specific dates to download (YYYY-MM-DD)'
    )
    args = parser.parse_args()
    downloader = KolkoNiStruvaDownloader()
    for date in args.dates:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Invalid date format: {date}. Use YYYY-MM-DD format.")
            continue
        downloader.download_all_for_date(date)

if __name__ == "__main__":
    main()
