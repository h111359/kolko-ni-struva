#!/usr/bin/env python3
"""
Command-line interface for kolko-ni-struva ETL operations.
"""

import sys
import os
import shutil
import argparse
from pathlib import Path

# Import normalize components (always available)
from .etl.normalize import DataNormalizer
from .etl.dimension_manager import DimensionManager
from .etl.logger import ETLLogger

# Try to import optional download/update components
try:
    from .etl.download_kolkonistruva import main as download_main
    DOWNLOAD_AVAILABLE = True
except ImportError:
    DOWNLOAD_AVAILABLE = False

try:
    from .etl.update_kolko_ni_struva import main as update_main
    UPDATE_AVAILABLE = True
except ImportError:
    UPDATE_AVAILABLE = False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Kolko Ni Struva ETL Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download data for specific dates
  python -m kolko-ni-struva.cli download --dates 2025-10-24 2025-10-25
  
  # Update and merge data
  python -m kolko-ni-struva.cli update --dates 2025-10-24 2025-10-25
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download data from kolkostruva.bg')
    download_parser.add_argument('--dates', nargs='+', required=True,
                                help='Dates to download (YYYY-MM-DD)')
    
    # Update command
    update_parser = subparsers.add_parser('update', help='Update and merge downloaded data')
    update_parser.add_argument('--dates', nargs='+',
                              help='Dates to merge (YYYY-MM-DD). If not provided, uses last 2 available dates.')
    
    # Normalize command
    normalize_parser = subparsers.add_parser('normalize', help='Normalize raw data into star schema')
    normalize_parser.add_argument('--dates', nargs='+',
                                 help='Dates to normalize (YYYY-MM-DD). If not provided, processes all files.')
    normalize_parser.add_argument('--output-dir', default='data/processed',
                                 help='Output directory for normalized data (default: data/processed)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'download':
        if not DOWNLOAD_AVAILABLE:
            print("Error: Download functionality requires beautifulsoup4, lxml, and requests")
            print("Install with: pip install -r requirements.txt")
            sys.exit(1)
        sys.argv = ['download', '--dates'] + args.dates
        download_main()
    elif args.command == 'normalize':
        run_normalize(args.dates, args.output_dir)
    elif args.command == 'update':
        # Update command always available (uses normalization internally)
        run_update(args.dates)


def run_normalize(dates=None, output_dir='data/processed'):
    """
    Run data normalization process.
    
    Args:
        dates: List of dates to process (YYYY-MM-DD) or None for all
        output_dir: Output directory for normalized data
    """
    print("=" * 60)
    print("Kolko Ni Struva - Data Normalization")
    print("=" * 60)
    
    # Setup paths
    raw_data_dir = "data/raw"
    dims_dir = os.path.join(output_dir, "dims")
    facts_dir = os.path.join(output_dir, "facts")
    logs_dir = "logs"
    
    # Ensure directories exist
    Path(dims_dir).mkdir(parents=True, exist_ok=True)
    Path(facts_dir).mkdir(parents=True, exist_ok=True)
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize logger
    logger = ETLLogger(
        error_log_path=os.path.join(logs_dir, "etl_errors.json"),
        audit_log_path=os.path.join(logs_dir, "dimension_audit.json")
    )
    
    # Define lookup key functions
    def category_lookup_key(attrs):
        return attrs["name"]
    
    def city_lookup_key(attrs):
        return attrs["ekatte_code"]
    
    def trade_chain_lookup_key(attrs):
        return attrs["name"]
    
    def trade_object_lookup_key(attrs):
        return f"{attrs['chain_id']}|{attrs['address']}"
    
    def product_lookup_key(attrs):
        product_code = attrs.get("product_code") or ""
        return f"{attrs['name']}|{product_code}"
    
    # Initialize dimension managers
    print("\nInitializing dimension managers...")
    dimension_managers = {
        "category": DimensionManager(
            "category",
            os.path.join(dims_dir, "dim_category.json"),
            category_lookup_key,
            logger
        ),
        "city": DimensionManager(
            "city",
            os.path.join(dims_dir, "dim_city.json"),
            city_lookup_key,
            logger
        ),
        "trade_chain": DimensionManager(
            "trade_chain",
            os.path.join(dims_dir, "dim_trade_chain.json"),
            trade_chain_lookup_key,
            logger
        ),
        "trade_object": DimensionManager(
            "trade_object",
            os.path.join(dims_dir, "dim_trade_object.json"),
            trade_object_lookup_key,
            logger
        ),
        "product": DimensionManager(
            "product",
            os.path.join(dims_dir, "dim_product.json"),
            product_lookup_key,
            logger
        )
    }
    
    # Initialize normalizer
    normalizer = DataNormalizer(
        raw_data_dir=raw_data_dir,
        output_fact_file=os.path.join(facts_dir, "fact_prices.csv"),
        dimension_managers=dimension_managers,
        logger=logger
    )
    
    # Run normalization
    date_filter = dates if dates else None
    stats = normalizer.normalize(date_filter=date_filter)
    
    # Check for size warnings
    print("\nChecking dimension file sizes...")
    for name, manager in dimension_managers.items():
        manager.check_size_warnings()
    
    print("\n✅ Normalization complete!")
    return stats


def run_update(dates=None):
    """
    Run update process: normalize data and deploy to build/web.
    
    Args:
        dates: List of dates to process (YYYY-MM-DD) or None for default (last 2 dates)
    """
    print("=" * 60)
    print("Kolko Ni Struva - Update and Deploy")
    print("=" * 60)
    
    # Step 1: Normalize data
    print("\n📊 Step 1: Normalizing data...")
    run_normalize(dates=dates)
    
    # Step 2: Deploy normalized files to build/web
    print("\n📦 Step 2: Deploying to build/web...")
    deploy_dir = "build/web"
    Path(deploy_dir).mkdir(parents=True, exist_ok=True)
    
    # Copy dimension files
    dims_src = "data/processed/dims"
    for dim_file in os.listdir(dims_src):
        if dim_file.endswith('.json'):
            src = os.path.join(dims_src, dim_file)
            dst = os.path.join(deploy_dir, dim_file)
            shutil.copy2(src, dst)
            print(f"  ✓ Copied {dim_file}")
    
    # Copy fact file as data.csv
    fact_src = "data/processed/facts/fact_prices.csv"
    fact_dst = os.path.join(deploy_dir, "data.csv")
    shutil.copy2(fact_src, fact_dst)
    print(f"  ✓ Copied fact_prices.csv → data.csv")
    
    # Copy web assets
    print("\n📄 Step 3: Deploying web assets...")
    web_files = [
        ("src/web/index.html", "index.html"),
        ("src/web/js/script.js", "script.js"),
        ("src/web/js/dimension-loader.js", "dimension-loader.js"),
        ("src/web/assets/style.css", "style.css")
    ]
    
    for src_rel, dst_name in web_files:
        if os.path.exists(src_rel):
            dst = os.path.join(deploy_dir, dst_name)
            shutil.copy2(src_rel, dst)
            file_size = os.path.getsize(src_rel)
            print(f"  ✓ Copied {dst_name} ({file_size:,} bytes)")
        else:
            print(f"  ⚠ Warning: {src_rel} not found")
    
    print("\n" + "=" * 60)
    print("✅ Update and deployment complete!")
    print("=" * 60)
    print(f"Static site ready in: {deploy_dir}/")
    print("=" * 60)


if __name__ == '__main__':
    main()
