"""
extract.py: Scrape kolkostruva.bg/opendata and download new daily retail-price ZIPs.
Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
Responsibilities: discover ZIP links, filter already-downloaded files, download
with retry logic, verify ZIP integrity, write last_downloaded_date to config.ini.
"""
import logging
import sys
import time
import zipfile as _zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config_utils import load_config, save_state


# BASE_DIR resolves to the project root regardless of where the script is called from.
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
CONFIG_PATH = BASE_DIR / "config.ini"


def setup_logging(level_name: str) -> None:
    """
    Configure root logger to write to stdout with a consistent timestamp format.

    Args:
        level_name: String log level (e.g. 'INFO', 'DEBUG').  Unknown names
            fall back to INFO.
    """
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s: %(message)s",
        stream=sys.stdout,
    )


def fetch_page(session: requests.Session, url: str, max_retries: int, retry_delay: int) -> str:
    """
    Fetch the HTML content of url, retrying up to max_retries times on failure.

    Args:
        session:     Active requests.Session to reuse connections.
        url:         URL to GET.
        max_retries: Maximum number of attempts before raising RuntimeError.
        retry_delay: Base delay in seconds between retries; scaled by attempt index.

    Returns:
        The decoded response body as a string.

    Raises:
        RuntimeError: When all retry attempts are exhausted.
    """
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            logging.warning("Fetch attempt %d/%d failed: %s", attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")


def parse_zip_links(html: str, base_url: str) -> list:
    """
    Extract all .zip hrefs from the page HTML, resolved against base_url.

    Args:
        html:     Raw HTML of the opendata page.
        base_url: Base URL used to resolve relative hrefs.

    Returns:
        Sorted list of absolute ZIP URLs, newest-first (descending string order).
    """
    soup = BeautifulSoup(html, "html.parser")
    links: set = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".zip"):
            links.add(urljoin(base_url, href))
    return sorted(links, reverse=True)


def existing_filenames(raw_dir: Path) -> set:
    """
    Return the set of filenames already present in raw_dir, creating it if absent.

    Args:
        raw_dir: Directory that holds downloaded ZIP files.

    Returns:
        Set of filename strings (basename only, no path prefix).
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    return {p.name for p in raw_dir.iterdir() if p.is_file()}


def verify_zip(path: Path) -> bool:
    """
    Return True when path is a structurally valid ZIP archive.

    Args:
        path: Filesystem path to the file to check.

    Returns:
        True if the file passes zipfile.is_zipfile(); False otherwise.
    """
    return _zipfile.is_zipfile(path)


def download_file(
    session: requests.Session,
    url: str,
    dest_path: Path,
    max_retries: int,
    retry_delay: int,
) -> bool:
    """
    Download url to dest_path, writing via a .partial temp file, with retry logic.

    After a successful download the ZIP is verified with verify_zip().  A
    failed integrity check deletes the file and triggers a re-download (counted
    as a separate attempt within max_retries).

    Args:
        session:     Active requests.Session.
        url:         Remote URL of the ZIP file.
        dest_path:   Final destination path.
        max_retries: Total attempts allowed (including integrity-failure retries).
        retry_delay: Base delay in seconds between retries.

    Returns:
        True when the file was downloaded and verified successfully; False
        when all attempts are exhausted.
    """
    tmp = dest_path.with_suffix(dest_path.suffix + ".partial")

    for attempt in range(1, max_retries + 1):
        try:
            with session.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

            # Atomic move: Path.replace() overwrites on all platforms.
            tmp.replace(dest_path)

            # Verify ZIP integrity using zipfile magic-number check.
            if not verify_zip(dest_path):
                logging.warning(
                    "ZIP integrity check failed for %s (attempt %d/%d); deleting and retrying",
                    dest_path.name, attempt, max_retries,
                )
                dest_path.unlink(missing_ok=True)
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)
                continue

            logging.info("Downloaded and verified %s", dest_path.name)
            return True

        except Exception as exc:
            logging.warning("Download %s attempt %d/%d failed: %s", url, attempt, max_retries, exc)
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            if attempt < max_retries:
                time.sleep(retry_delay * attempt)

    logging.error("Failed to download %s after %d attempts", url, max_retries)
    return False


def main() -> None:
    """
    Entry point: load config, scrape page, filter work list, download new ZIPs.

    Writes last_downloaded_date to config.ini [state] after at least one
    successful download.
    """
    cfg = load_config(CONFIG_PATH)

    log_level = cfg.get("settings", "log_level", fallback="INFO")
    setup_logging(log_level)

    opendata_url: str = cfg.get("settings", "opendata_url")
    max_retries: int = cfg.getint("settings", "max_retries", fallback=3)
    retry_delay: int = cfg.getint("settings", "retry_delay", fallback=10)
    # force_from: re-download ZIPs with date >= this value; empty means no forcing.
    force_from: str = cfg.get("state", "last_downloaded_date", fallback="")

    logging.info("Scraping %s for ZIP links", opendata_url)
    session = requests.Session()
    html = fetch_page(session, opendata_url, max_retries, retry_delay)
    links = parse_zip_links(html, opendata_url)

    if not links:
        logging.info("No ZIP links found on page.")
        return

    existing = existing_filenames(RAW_DIR)
    to_download: list = []
    for url in links:
        name = Path(urlparse(url).path).name
        date_str = name.replace(".zip", "")
        # Schedule if not yet downloaded, or if force re-download threshold is met.
        needs_download = name not in existing or (force_from and date_str >= force_from)
        if needs_download:
            to_download.append((url, RAW_DIR / name, date_str))

    if not to_download:
        logging.info("No new files to download.")
        return

    logging.info("Found %d file(s) to download", len(to_download))

    max_downloaded_date: str = ""
    for url, dest, date_str in to_download:
        logging.info("Downloading %s", url)
        ok = download_file(session, url, dest, max_retries, retry_delay)
        if ok and date_str > max_downloaded_date:
            max_downloaded_date = date_str

    if max_downloaded_date:
        save_state(CONFIG_PATH, last_downloaded_date=max_downloaded_date)
        logging.info("State: last_downloaded_date = %s", max_downloaded_date)


if __name__ == "__main__":
    main()
