"""
transform.py: Transform raw ZIP archives into a star-schema data layer under data/schema/.
Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
Responsibilities: parse CSVs inside each daily ZIP, build seven dimension tables
(dim_date, dim_company, dim_settlement, dim_category, dim_product, dim_store,
dim_file), write date-partitioned fact CSVs under data/schema/facts/, produce a
quality report in data/quality/, and log progress to logs/.
"""
import csv
import json
import logging
import sys
import zipfile as _zipfile
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config_utils import load_config, save_state


# ---------------------------------------------------------------------------
# Path constants (all relative to project root, not to src/)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.ini"
RAW_DIR = BASE_DIR / "data" / "raw"
SCHEMA_DIR = BASE_DIR / "data" / "schema"
FACTS_DIR = SCHEMA_DIR / "facts"
QUALITY_DIR = BASE_DIR / "data" / "quality"
LOGS_DIR = BASE_DIR / "logs"

NOM_DIR = BASE_DIR / "data" / "nomenclatures"
CITIES_FILE = NOM_DIR / "cities-ekatte-nomenclature.json"
SOF_RAI_FILE = NOM_DIR / "Ekatte" / "sof_rai.json"
EKATTE_DIR = NOM_DIR / "Ekatte"
EK_ATTE_FILE = EKATTE_DIR / "ek_atte.json"
EK_KMET_FILE = EKATTE_DIR / "ek_kmet.json"
EK_RAION_FILE = EKATTE_DIR / "ek_raion.json"
EK_OBL_FILE = EKATTE_DIR / "ek_obl.json"
EK_OBST_FILE = EKATTE_DIR / "ek_obst.json"
CATEGORIES_FILE = NOM_DIR / "product-categories.json"

# ---------------------------------------------------------------------------
# CSV headers for all dimension and fact tables
# ---------------------------------------------------------------------------
DIM_DATE_HEADER = ["date_key", "date", "year", "month", "day", "weekday"]
DIM_COMPANY_HEADER = ["company_key", "uic", "company_name"]
DIM_SETTLEMENT_HEADER = ["settlement_key", "ekatte", "settlement_name"]
DIM_CATEGORY_HEADER = ["category_key", "category_code", "category_name"]
DIM_PRODUCT_HEADER = ["product_key", "product_code", "product_name"]
DIM_STORE_HEADER = ["store_key", "store_name", "settlement_key", "company_key"]
DIM_FILE_HEADER = ["file_key", "file_name", "zip_date"]

FACT_HEADER = [
    "date_key", "store_key", "file_key",
    "category_key", "product_key",
    "retail_price", "promo_price",
]

# Header for the derived lookback fact table produced by build_lookback_table.
# Extends FACT_HEADER with four day-over-day lookback price columns.
LOOKBACK_HEADER = [
    "date_key", "store_key", "file_key",
    "category_key", "product_key",
    "retail_price", "promo_price",
    "retail_price_day1", "promo_price_day1",
    "retail_price_day2", "promo_price_day2",
]

QUALITY_HEADER = [
    "zip_date", "total_rows", "null_prices",
    "unknown_settlements", "unknown_categories", "delimiter_anomalies",
]

# Minimum expected column count in raw CSVs (7 Bulgarian columns)
EXPECTED_COLUMNS = 7

# Column indices within raw CSV rows (0-based)
COL_SETTLEMENT = 0  # Населено място (EKATTE code)
COL_STORE = 1       # Търговски обект (store name)
COL_PRODUCT_NAME = 2  # Наименование на продукта
COL_PRODUCT_CODE = 3  # Код на продукта
COL_CATEGORY = 4    # Категория (category code)
COL_RETAIL_PRICE = 5  # Цена на дребно
COL_PROMO_PRICE = 6   # Цена в промоция


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

def setup_logging(level_name: str, run_ts: str) -> None:
    """
    Configure console and file logging for the transform run.

    Args:
        level_name: String log level from config (e.g. 'INFO').
        run_ts:     Timestamp string (YYYY-MM-DD_HHMMSS) used for the log
                    file name.

    Side effects:
        Creates LOGS_DIR if absent.  Adds StreamHandler (stdout) and
        FileHandler (logs/transform_<run_ts>.log) to the root logger.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    level = getattr(logging, level_name.upper(), logging.INFO)
    log_file = LOGS_DIR / f"transform_{run_ts}.log"

    root = logging.getLogger()
    root.setLevel(level)

    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Nomenclature loaders
# ---------------------------------------------------------------------------

def load_settlement_names() -> Dict[str, str]:
    """
    Build a combined EKATTE→name lookup from all available nomenclature files.

    Reads cities-ekatte-nomenclature.json (primary), sof_rai.json (Sofia
    sub-districts), and the five extended EKATTE registry files (ek_atte,
    ek_kmet, ek_raion, ek_obl, ek_obst).  Each supplementary file adds
    entries only when the code is not already present in the lookup, so the
    primary cities file always takes precedence.

    For ek_raion.json the key field is 'raion' (e.g. '68134-04'); for all
    other EKATTE files the key field is 'ekatte'.  Trailing metadata rows in
    ek_raion.json (which lack the required keys) are skipped silently.

    All file reads are guarded with an existence check so that absent files
    do not raise errors — the function degrades gracefully to fewer entries.

    Returns:
        Dict mapping EKATTE code string (or raion code string) to settlement
        name string.  Includes padded canonical codes from the primary file,
        raion codes from ek_raion, and any codes unique to the extended files.
    """
    names: Dict[str, str] = {}

    if CITIES_FILE.exists():
        with open(CITIES_FILE, encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, dict):
            names.update(raw)
        elif isinstance(raw, list):
            for item in raw:
                names[str(item.get("ekatte", ""))] = item.get("name", "")

    if SOF_RAI_FILE.exists():
        with open(SOF_RAI_FILE, encoding="utf-8") as fh:
            sof_list = json.load(fh)
        for item in sof_list:
            ekatte = str(item.get("ekatte", ""))
            name = item.get("name", "")
            if ekatte and ekatte not in names:
                names[ekatte] = name

    # Extended EKATTE files — supplement without overwriting existing entries.
    _ekatte_files = [
        (EK_ATTE_FILE, "ekatte"),
        (EK_KMET_FILE, "ekatte"),
        (EK_OBL_FILE, "ekatte"),
        (EK_OBST_FILE, "ekatte"),
    ]
    for file_path, key_field in _ekatte_files:
        if file_path.exists():
            with open(file_path, encoding="utf-8") as fh:
                items = json.load(fh)
            for item in items:
                if key_field in item and "name" in item:
                    code = str(item[key_field])
                    if code and code not in names:
                        names[code] = item["name"]

    # ek_raion.json uses the 'raion' field (e.g. '68134-04') as the key.
    if EK_RAION_FILE.exists():
        with open(EK_RAION_FILE, encoding="utf-8") as fh:
            raion_items = json.load(fh)
        for item in raion_items:
            # Guard against the trailing metadata row that lacks 'raion'/'name'.
            if "raion" in item and "name" in item:
                code = str(item["raion"])
                if code and code not in names:
                    names[code] = item["name"]

    return names


def resolve_settlement_name(code: str, lookup: Dict[str, str]) -> str:
    """
    Resolve an EKATTE code to a settlement name using three-step normalisation.

    Tries the code exactly as provided, then zero-padded to 5 digits, then
    with leading zeros stripped.  Returns the first match found.  If none of
    the three probes matches, returns '(unknown:<code>)'.

    The three-step probe handles common source-data formatting variants:
    - Non-canonical codes shorter than 5 digits (e.g. '2659' → '02659').
    - Codes with extra leading zeros (e.g. '068134' → '68134').
    - Raion codes with dash suffixes (e.g. '68134-04') are matched as-is in
      the first probe since they are stored verbatim in the lookup.

    Args:
        code:   Raw EKATTE code string as read from the source data.
        lookup: Settlement name lookup dict from load_settlement_names().

    Returns:
        Settlement name string, or '(unknown:<code>)' if unresolvable.
    """
    # Probe 1: exact code as-is (handles canonical codes and raion codes).
    name = lookup.get(code)
    if name is not None:
        return name

    # Probe 2: zero-pad to 5 digits (handles short numeric codes like '2659').
    name = lookup.get(code.zfill(5))
    if name is not None:
        return name

    # Probe 3: strip leading zeros (handles over-padded codes like '068134').
    stripped = code.lstrip("0") or code  # preserve '0' if the code is all zeros
    name = lookup.get(stripped)
    if name is not None:
        return name

    return f"(unknown:{code})"


def normalize_settlement_code(code: str) -> str:
    """
    Canonicalise a settlement code so equivalent EKATTE variants collapse.

    Args:
        code: Raw settlement code string as read from the source data.

    Returns:
        Canonical settlement code string. Numeric codes are normalised by
        stripping redundant leading zeros, then padding to 5 digits when the
        significant part is shorter than the EKATTE canonical width. Raion
        suffixes such as '-04' are preserved while their numeric prefix is
        canonicalised.
    """
    cleaned = code.strip()
    if not cleaned:
        return cleaned

    if "-" in cleaned:
        prefix, suffix = cleaned.split("-", 1)
        normalised_prefix = normalize_settlement_code(prefix)
        return f"{normalised_prefix}-{suffix}"

    if not cleaned.isdigit():
        return cleaned

    significant = cleaned.lstrip("0")
    if not significant:
        return "00000"
    if len(significant) < 5:
        return significant.zfill(5)
    return significant


def patch_unknown_settlements(dim_path: Path, lookup: Dict[str, str]) -> int:
    """
    Correct existing (unknown:...) entries in dim_settlement.csv in place.

    Reads the current dim_settlement CSV, applies resolve_settlement_name()
    to each row whose settlement_name starts with '(unknown:', and atomically
    rewrites the file via write_dim() when at least one correction is made.
    Surrogate key (settlement_key) values are preserved unchanged.

    Args:
        dim_path: Path to data/schema/dim_settlement.csv.  If the file does
                  not exist, the function returns 0 immediately.
        lookup:   Settlement name lookup dict from load_settlement_names().

    Returns:
        Number of rows whose settlement_name was updated from a placeholder
        to a real name.  Returns 0 when no corrections are made.
    """
    if not dim_path.exists():
        return 0

    sett_lkp, _ = load_dim(dim_path, ["ekatte"])
    updated = 0

    for row in sett_lkp.values():
        if row["settlement_name"].startswith("(unknown:"):
            resolved = resolve_settlement_name(row["ekatte"], lookup)
            if not resolved.startswith("(unknown:"):
                row["settlement_name"] = resolved
                updated += 1

    if updated:
        write_dim(dim_path, DIM_SETTLEMENT_HEADER, sett_lkp)
        logging.info(
            "patch_unknown_settlements: resolved %d previously unknown entries",
            updated,
        )

    return updated


def load_category_names() -> Dict[str, str]:
    """
    Build a category_code→name lookup from product-categories.json.

    Returns:
        Dict mapping numeric category code (as string) to category name string.
    """
    names: Dict[str, str] = {}
    if not CATEGORIES_FILE.exists():
        return names
    with open(CATEGORIES_FILE, encoding="utf-8") as fh:
        items = json.load(fh)
    for item in items:
        names[str(item["id"])] = item.get("name", "")
    return names


# ---------------------------------------------------------------------------
# Dimension persistence (load existing CSVs for SCD Type-1 idempotency)
# ---------------------------------------------------------------------------

def load_dim(path: Path, key_fields: List[str]) -> Tuple[Dict, int]:
    """
    Load an existing dimension CSV into a dict keyed by the natural key tuple.

    Args:
        path:       Path to the dimension CSV (may not exist yet).
        key_fields: List of column names that form the natural key.

    Returns:
        Tuple of (lookup_dict, next_surrogate_key) where lookup_dict maps the
        natural key tuple to the full row dict, and next_surrogate_key is the
        next integer to assign for new entries.
    """
    lookup: Dict = {}
    max_key = 0

    if not path.exists():
        return lookup, 1

    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Determine surrogate key column (always first column per convention)
            sk_col = reader.fieldnames[0] if reader.fieldnames else None
            if sk_col:
                try:
                    sk = int(row[sk_col])
                    if sk > max_key:
                        max_key = sk
                except (ValueError, KeyError):
                    pass
            nat_key = tuple(row[f] for f in key_fields)
            lookup[nat_key] = row

    return lookup, max_key + 1


def upsert_dim(
    lookup: Dict,
    counter: List[int],
    sk_col: str,
    nat_key: tuple,
    extra_fields: Dict[str, str],
) -> int:
    """
    Insert a new dimension row or return the existing surrogate key (SCD Type 1).

    Args:
        lookup:      Existing dim lookup dict (mutated in place on insert).
        counter:     Single-element list holding the next surrogate key integer
                     (mutated in place on insert).
        sk_col:      Name of the surrogate key column.
        nat_key:     Tuple of natural-key field values.
        extra_fields: Dict of additional column names → values for the row.

    Returns:
        Integer surrogate key for the dimension entry.
    """
    if nat_key in lookup:
        return int(lookup[nat_key][sk_col])
    sk = counter[0]
    row = {sk_col: str(sk)}
    # Natural key is a tuple; extra_fields carries header→value for each position.
    row.update(extra_fields)
    lookup[nat_key] = row
    counter[0] += 1
    return sk


def write_dim(path: Path, header: List[str], lookup: Dict) -> None:
    """
    Write a dimension lookup dict to a CSV atomically using Path.replace().

    Args:
        path:   Final destination path for the CSV.
        header: Ordered list of column names.
        lookup: Dict of natural-key-tuple → row dict from upsert_dim.

    Side effects:
        Writes path.partial then renames to path.  Output encoding is UTF-8
        without BOM.
    """
    partial = path.with_suffix(path.suffix + ".partial")
    rows = sorted(lookup.values(), key=lambda r: int(r[header[0]]))
    with open(partial, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    partial.replace(path)


# ---------------------------------------------------------------------------
# CSV parsing helpers
# ---------------------------------------------------------------------------

def detect_delimiter(first_line: str) -> str:
    """
    Return the delimiter character for a CSV line — comma or semicolon.

    Args:
        first_line: The header line of the CSV.

    Returns:
        ',' or ';'.  Defaults to ',' when neither dominates.
    """
    if first_line.count(";") > first_line.count(","):
        return ";"
    return ","


def parse_price(raw: str) -> Optional[str]:
    """
    Normalise a raw price string to a decimal string or None.

    Args:
        raw: Price string as read from the CSV (may be quoted, empty, or
             contain commas as decimal separators).

    Returns:
        Normalised decimal string (e.g. '3.17'), or empty string for missing /
        non-parseable values (treated as NULL in the fact table).
    """
    cleaned = raw.strip().strip('"').replace(",", ".")
    if not cleaned:
        return ""
    try:
        float(cleaned)
        return cleaned
    except ValueError:
        return ""


# ---------------------------------------------------------------------------
# Main ETL loop
# ---------------------------------------------------------------------------

def build_schema(force_from: str) -> None:
    """
    Read all ZIPs in data/raw/, populate all 7 dimensions, write fact CSVs.

    Args:
        force_from: ISO date string (YYYY-MM-DD).  Fact files for dates >=
                    force_from are deleted and re-created even when they
                    already exist.  Empty string disables forcing.

    Side effects:
        Creates SCHEMA_DIR/facts/, writes dimension CSVs and fact CSVs,
        writes a quality report to data/quality/, saves last_processed_date
        to config.ini.
    """
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    FACTS_DIR.mkdir(parents=True, exist_ok=True)
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Load nomenclatures
    # ------------------------------------------------------------------
    settlement_names = load_settlement_names()
    category_names = load_category_names()

    # ------------------------------------------------------------------
    # Load existing dimensions (SCD Type 1: natural key → row)
    # ------------------------------------------------------------------
    dim_paths = {
        "date":       SCHEMA_DIR / "dim_date.csv",
        "company":    SCHEMA_DIR / "dim_company.csv",
        "settlement": SCHEMA_DIR / "dim_settlement.csv",
        "category":   SCHEMA_DIR / "dim_category.csv",
        "product":    SCHEMA_DIR / "dim_product.csv",
        "store":      SCHEMA_DIR / "dim_store.csv",
        "file":       SCHEMA_DIR / "dim_file.csv",
    }

    date_lkp, date_ctr_val = load_dim(dim_paths["date"], ["date"])
    comp_lkp, comp_ctr_val = load_dim(dim_paths["company"], ["uic"])
    sett_lkp, sett_ctr_val = load_dim(dim_paths["settlement"], ["ekatte"])
    cat_lkp, cat_ctr_val = load_dim(dim_paths["category"], ["category_code"])
    prod_lkp, prod_ctr_val = load_dim(dim_paths["product"], ["product_code", "product_name"])
    store_lkp, store_ctr_val = load_dim(dim_paths["store"], ["store_name", "settlement_key", "company_key"])
    file_lkp, file_ctr_val = load_dim(dim_paths["file"], ["file_name", "zip_date"])

    # Counters as single-element lists so upsert_dim can mutate them.
    date_ctr = [date_ctr_val]
    comp_ctr = [comp_ctr_val]
    sett_ctr = [sett_ctr_val]
    cat_ctr = [cat_ctr_val]
    prod_ctr = [prod_ctr_val]
    store_ctr = [store_ctr_val]
    file_ctr = [file_ctr_val]

    # ------------------------------------------------------------------
    # Enumerate ZIPs
    # ------------------------------------------------------------------
    zips = sorted(p for p in RAW_DIR.iterdir() if p.suffix == ".zip")
    total_zips = len(zips)
    quality_rows: List[Dict] = []
    max_processed_date = ""

    for zip_idx, zip_path in enumerate(zips, start=1):
        date_str = zip_path.stem  # e.g. "2026-02-15"

        # Check skip condition: fact file already exists and no forcing needed.
        fact_path = FACTS_DIR / f"{date_str}.csv"
        should_skip = fact_path.exists() and (not force_from or date_str < force_from)
        if should_skip:
            logging.debug("Skipping already-processed ZIP %s", date_str)
            continue

        # If force re-process: delete existing fact file.
        if fact_path.exists():
            fact_path.unlink()

        # ------------------------------------------------------------------
        # Parse ZIP
        # ------------------------------------------------------------------
        if not _zipfile.is_zipfile(zip_path):
            logging.warning("Skipping non-ZIP or corrupt file: %s", zip_path.name)
            continue

        q_total = 0
        q_null_prices = 0
        q_unknown_settlements = 0
        q_unknown_categories = 0
        q_delimiter_anomalies = 0

        fact_rows: List[List] = []

        try:
            with _zipfile.ZipFile(zip_path, "r") as zf:
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]

                for csv_name in csv_names:
                    # --------------------------------------------------
                    # Parse company name and UIC from filename
                    # --------------------------------------------------
                    stem = csv_name
                    if stem.endswith(".csv"):
                        stem = stem[:-4]
                    parts = stem.rsplit("_", 1)
                    company_name = parts[0] if len(parts) == 2 else stem
                    uic = parts[1] if len(parts) == 2 else ""

                    comp_key = upsert_dim(
                        comp_lkp, comp_ctr, "company_key",
                        (uic,),
                        {"uic": uic, "company_name": company_name},
                    )

                    # --------------------------------------------------
                    # Upsert dim_file
                    # --------------------------------------------------
                    file_key = upsert_dim(
                        file_lkp, file_ctr, "file_key",
                        (csv_name, date_str),
                        {"file_name": csv_name, "zip_date": date_str},
                    )

                    # --------------------------------------------------
                    # Read CSV content
                    # --------------------------------------------------
                    raw_bytes = zf.read(csv_name)
                    text = raw_bytes.decode("utf-8-sig")
                    lines = text.splitlines()
                    if not lines:
                        continue

                    delimiter = detect_delimiter(lines[0])
                    if delimiter == ";":
                        q_delimiter_anomalies += 1

                    reader = csv.reader(lines, delimiter=delimiter)
                    # Skip header row
                    header_row = next(reader, None)
                    if header_row is None:
                        continue

                    for raw_row in reader:
                        # Validate column count; skip malformed rows silently.
                        if len(raw_row) < EXPECTED_COLUMNS:
                            continue

                        ekatte = normalize_settlement_code(
                            raw_row[COL_SETTLEMENT].strip().strip('"')
                        )
                        store_name = raw_row[COL_STORE].strip().strip('"')
                        product_name = raw_row[COL_PRODUCT_NAME].strip().strip('"')
                        product_code = raw_row[COL_PRODUCT_CODE].strip().strip('"')
                        category_code = raw_row[COL_CATEGORY].strip().strip('"')
                        retail_price_str = parse_price(raw_row[COL_RETAIL_PRICE])
                        promo_price_str = parse_price(raw_row[COL_PROMO_PRICE])

                        q_total += 1
                        if not retail_price_str:
                            q_null_prices += 1

                        # --------------------------------------------------
                        # Upsert dim_date
                        # --------------------------------------------------
                        d_key = upsert_dim(
                            date_lkp, date_ctr, "date_key",
                            (date_str,),
                            _date_extra(date_str),
                        )

                        # --------------------------------------------------
                        # Upsert dim_settlement
                        # --------------------------------------------------
                        sett_name = resolve_settlement_name(ekatte, settlement_names)
                        if sett_name.startswith("(unknown:"):
                            q_unknown_settlements += 1
                        sett_key = upsert_dim(
                            sett_lkp, sett_ctr, "settlement_key",
                            (ekatte,),
                            {"ekatte": ekatte, "settlement_name": sett_name},
                        )

                        # --------------------------------------------------
                        # Upsert dim_category
                        # --------------------------------------------------
                        cat_name = category_names.get(category_code, f"(unknown:{category_code})")
                        if cat_name.startswith("(unknown:"):
                            q_unknown_categories += 1
                        cat_key = upsert_dim(
                            cat_lkp, cat_ctr, "category_key",
                            (category_code,),
                            {"category_code": category_code, "category_name": cat_name},
                        )

                        # --------------------------------------------------
                        # Upsert dim_product
                        # --------------------------------------------------
                        prod_key = upsert_dim(
                            prod_lkp, prod_ctr, "product_key",
                            (product_code, product_name),
                            {"product_code": product_code, "product_name": product_name},
                        )

                        # --------------------------------------------------
                        # Upsert dim_store (snowflake bridge to settlement/company)
                        # --------------------------------------------------
                        store_key = upsert_dim(
                            store_lkp, store_ctr, "store_key",
                            (store_name, str(sett_key), str(comp_key)),
                            {
                                "store_name": store_name,
                                "settlement_key": str(sett_key),
                                "company_key": str(comp_key),
                            },
                        )

                        fact_rows.append([
                            d_key, store_key, file_key,
                            cat_key, prod_key,
                            retail_price_str, promo_price_str,
                        ])

        except _zipfile.BadZipFile as exc:
            logging.error("Corrupt ZIP %s: %s — skipping", zip_path.name, exc)
            continue

        # ------------------------------------------------------------------
        # Write fact file atomically
        # ------------------------------------------------------------------
        fact_partial = fact_path.with_suffix(fact_path.suffix + ".partial")
        with open(fact_partial, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(FACT_HEADER)
            writer.writerows(fact_rows)
        fact_partial.replace(fact_path)

        # ------------------------------------------------------------------
        # Write all 7 dimension CSVs atomically after each ZIP (crash safety)
        # ------------------------------------------------------------------
        write_dim(dim_paths["date"], DIM_DATE_HEADER, date_lkp)
        write_dim(dim_paths["company"], DIM_COMPANY_HEADER, comp_lkp)
        write_dim(dim_paths["settlement"], DIM_SETTLEMENT_HEADER, sett_lkp)
        write_dim(dim_paths["category"], DIM_CATEGORY_HEADER, cat_lkp)
        write_dim(dim_paths["product"], DIM_PRODUCT_HEADER, prod_lkp)
        write_dim(dim_paths["store"], DIM_STORE_HEADER, store_lkp)
        write_dim(dim_paths["file"], DIM_FILE_HEADER, file_lkp)

        if date_str > max_processed_date:
            max_processed_date = date_str

        quality_rows.append({
            "zip_date": date_str,
            "total_rows": q_total,
            "null_prices": q_null_prices,
            "unknown_settlements": q_unknown_settlements,
            "unknown_categories": q_unknown_categories,
            "delimiter_anomalies": q_delimiter_anomalies,
        })

        logging.info(
            "Processed ZIP %d/%d (%s) — %d rows",
            zip_idx, total_zips, date_str, q_total,
        )

    return max_processed_date, quality_rows


def _date_extra(date_str: str) -> Dict[str, str]:
    """
    Build the non-key dimension fields for a dim_date row from an ISO date string.

    Args:
        date_str: ISO-format date string 'YYYY-MM-DD'.

    Returns:
        Dict with keys year, month, day, weekday (weekday: Monday=0, Sunday=6).
    """
    d = date.fromisoformat(date_str)
    return {
        "date": date_str,
        "year": str(d.year),
        "month": str(d.month),
        "day": str(d.day),
        "weekday": str(d.weekday()),
    }


def load_fact_dict(fact_path: Path) -> Dict[Tuple, Tuple[str, str]]:
    """
    Load a fact CSV into an in-memory lookup dict keyed by composite price key.

    The composite key is (store_key, category_key, product_key) — the join
    predicate used by build_lookback_table for day-over-day lookback.

    Args:
        fact_path: Path to a date-partitioned fact CSV (7-column FACT_HEADER
                   format).  If the file does not exist, an empty dict is
                   returned; no error is raised.

    Returns:
        Dict mapping (store_key, category_key, product_key) string tuples to
        a (retail_price, promo_price) string pair.  Where a key appears more
        than once (see Assumption A1 in request.md), the last row wins.
    """
    lookup: Dict[Tuple, Tuple[str, str]] = {}
    if not fact_path.exists():
        return lookup
    with open(fact_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            composite_key = (
                row["store_key"],
                row["category_key"],
                row["product_key"],
            )
            lookup[composite_key] = (row["retail_price"], row["promo_price"])
    return lookup


def build_lookback_table(facts_dir: Path, output_path: Path) -> None:
    """
    Build the derived lookback fact table from the three most recent fact CSVs.

    Identifies D (latest fact date), D-1, and D-2 from facts_dir.  For each
    row in D, produces an 11-column output row consisting of D's 7 original
    columns plus retail_price_day1, promo_price_day1 (from the D-1 dict) and
    retail_price_day2, promo_price_day2 (from the D-2 dict).  Missing
    lookback values are stored as empty string (NULL equivalent in CSV),
    consistent with the existing promo_price nullability convention.

    The output file is written atomically via a .partial → rename pattern.
    It is always fully replaced on each call (no incremental append).

    Args:
        facts_dir:   Directory containing date-partitioned fact CSV files
                     named YYYY-MM-DD.csv.
        output_path: Destination path for the lookback CSV
                     (data/schema/fact_prices_lookback.csv).

    Side effects:
        Creates output_path (via output_path + '.partial' → rename).
        Logs a warning and returns without writing when no fact files exist.
    """
    # Collect and sort fact CSVs lexicographically; ISO date stems sort
    # correctly as strings (YYYY-MM-DD ascending).
    fact_files = sorted(
        p for p in facts_dir.iterdir() if p.suffix == ".csv"
    ) if facts_dir.exists() else []

    if not fact_files:
        logging.warning(
            "build_lookback_table: no fact files found in %s — skipping.",
            facts_dir,
        )
        return

    # Identify D, D-1, D-2 (at most) from the sorted list.
    fact_d = fact_files[-1]
    fact_d1 = fact_files[-2] if len(fact_files) >= 2 else None
    fact_d2 = fact_files[-3] if len(fact_files) >= 3 else None

    # Load prior-day dicts; load_fact_dict returns {} when path is None
    # or absent, so missing prior days produce all-empty lookback columns.
    d1_lookup = load_fact_dict(fact_d1) if fact_d1 is not None else {}
    d2_lookup = load_fact_dict(fact_d2) if fact_d2 is not None else {}

    partial_path = output_path.with_suffix(output_path.suffix + ".partial")
    with open(fact_d, encoding="utf-8", newline="") as in_fh, \
         open(partial_path, "w", encoding="utf-8", newline="") as out_fh:
        reader = csv.DictReader(in_fh)
        writer = csv.writer(out_fh)
        writer.writerow(LOOKBACK_HEADER)

        for row in reader:
            composite_key = (
                row["store_key"],
                row["category_key"],
                row["product_key"],
            )
            d1_retail, d1_promo = d1_lookup.get(composite_key, ("", ""))
            d2_retail, d2_promo = d2_lookup.get(composite_key, ("", ""))

            writer.writerow([
                row["date_key"],
                row["store_key"],
                row["file_key"],
                row["category_key"],
                row["product_key"],
                row["retail_price"],
                row["promo_price"],
                d1_retail,
                d1_promo,
                d2_retail,
                d2_promo,
            ])

    partial_path.replace(output_path)
    logging.info("Lookback table written to %s", output_path)


def write_quality_report(quality_rows: List[Dict], run_ts: str) -> None:
    """
    Write the per-ZIP quality report CSV to data/quality/.

    Args:
        quality_rows: List of quality counter dicts (one per processed ZIP).
        run_ts:       Run timestamp string for the filename.

    Side effects:
        Creates QUALITY_DIR if absent.  Writes UTF-8 no-BOM CSV.
    """
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    report_path = QUALITY_DIR / f"report_{run_ts}.csv"
    with open(report_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=QUALITY_HEADER)
        writer.writeheader()
        writer.writerows(quality_rows)
    logging.info("Quality report written to %s", report_path)


def main() -> None:
    """
    Entry point: load config, run schema build loop, write quality report,
    update last_processed_date in config.ini.
    """
    run_ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    cfg = load_config(CONFIG_PATH)
    log_level = cfg.get("settings", "log_level", fallback="INFO")
    setup_logging(log_level, run_ts)

    force_from: str = cfg.get("state", "last_processed_date", fallback="")
    logging.info("Starting transform run %s (force_from=%r)", run_ts, force_from)

    max_date, quality_rows = build_schema(force_from)

    if quality_rows:
        write_quality_report(quality_rows, run_ts)

    if max_date:
        save_state(CONFIG_PATH, last_processed_date=max_date)
        logging.info("State: last_processed_date = %s", max_date)
    else:
        logging.info("No new ZIPs processed.")

    # Patch any pre-existing (unknown:...) entries in dim_settlement that were
    # recorded before extended EKATTE lookup and normalisation were introduced.
    settlement_names = load_settlement_names()
    patched = patch_unknown_settlements(
        SCHEMA_DIR / "dim_settlement.csv", settlement_names
    )
    if patched:
        logging.info("Patched %d unknown settlement entries in dim_settlement.csv", patched)
    else:
        logging.info("No unknown settlement entries required patching.")

    # Always regenerate the lookback table so it reflects the current state of
    # data/schema/facts/ after this run (see request R-20260420-2055, Task 2).
    build_lookback_table(FACTS_DIR, SCHEMA_DIR / "fact_prices_lookback.csv")

    logging.info("Transform run complete.")


if __name__ == "__main__":
    main()
