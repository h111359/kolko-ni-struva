#!/usr/bin/env python3
"""
read-setup.py: Read a single named option from .aib_memory/aib-setup.yaml.
Part of the AIB core tooling layer.
Responsibilities: retrieve a flat top-level key value, print it to stdout,
exit with code 1 on missing file or missing key.
"""

import argparse
import sys
from pathlib import Path

from common import _parse_flat_yaml_value


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for read-setup.py.

    Returns:
        Parsed argument namespace with ``workspace`` and ``option`` attributes.
    """
    parser = argparse.ArgumentParser(
        description="Read a single option from .aib_memory/aib-setup.yaml."
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root directory (default: current directory).",
    )
    parser.add_argument(
        "--option",
        required=True,
        help="Top-level YAML key to retrieve from aib-setup.yaml.",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: read *option* from aib-setup.yaml and print its bare value.

    Exits with code 1 when the file is missing, unparseable, or the key is absent.
    """
    args = _parse_args()
    workspace = Path(args.workspace).resolve()
    setup_path = workspace / ".aib_memory" / "aib-setup.yaml"

    if not setup_path.is_file():
        print(f"ERROR: aib-setup.yaml not found at {setup_path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        content = setup_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: Cannot read aib-setup.yaml: {exc}", file=sys.stderr)
        raise SystemExit(1)

    # Validate that content parses as a non-empty flat YAML document.
    # A completely empty or whitespace-only file has no parseable keys.
    if not content.strip():
        print("ERROR: aib-setup.yaml is empty or contains only whitespace.", file=sys.stderr)
        raise SystemExit(1)

    # Attempt to detect clearly non-YAML content by checking for a colon in
    # any non-comment line.  A file with no colon at all cannot contain any key.
    has_any_key = any(
        ":" in line and not line.strip().startswith("#")
        for line in content.splitlines()
        if line.strip()
    )
    if not has_any_key:
        print("ERROR: aib-setup.yaml does not contain any parseable key-value pairs.", file=sys.stderr)
        raise SystemExit(1)

    value = _parse_flat_yaml_value(content, args.option)
    if value is None:
        print(
            f"ERROR: option '{args.option}' not found in aib-setup.yaml",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print(value)


if __name__ == "__main__":
    main()
