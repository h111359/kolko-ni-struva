#!/usr/bin/env python3
"""
log-entry.py: Append UTC-timestamped audit log entries to request or general log files.
Part of the AIB core tooling layer.
Responsibilities: write a single timestamped log entry to .aib_memory/log_<request_id>.md
(normal mode) or .aib_memory/log_general.md (--general mode); print entry to stdout;
exit with code 1 when no active request is found in normal mode.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import ValidationError, ensure_workspace, parse_input_header, read_text

# Log entry timestamp format: YYYYMMDD-HHmmss (UTC 24-hour).
_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"

# Filename for the general (non-request-scoped) log.
_GENERAL_LOG_FILENAME = "log_general.md"


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed namespace with workspace, message, and general flag.
    """
    parser = argparse.ArgumentParser(
        description="Append a UTC-timestamped log entry to the active request or general log."
    )
    parser.add_argument(
        "--workspace", default=".", help="Workspace root path (default: current directory)."
    )
    parser.add_argument(
        "--message", required=True, help="Log message text to append."
    )
    parser.add_argument(
        "--general",
        action="store_true",
        default=False,
        help=(
            "Write to log_general.md instead of the active-request log. "
            "Bypasses the active-request check."
        ),
    )
    return parser.parse_args()


def _resolve_log_path(workspace: Path, general: bool) -> "tuple[Path, None] | tuple[None, str]":
    """Resolve the target log file path for the current invocation.

    In normal mode, reads the active request ID from input.md YAML header. In
    general mode, bypasses the active-request check and returns the path to
    log_general.md.

    Args:
        workspace: Resolved workspace root path.
        general: When True, use the general log regardless of active-request state.

    Returns:
        Tuple of (log_path, None) on success, or (None, error_message) on failure.
    """
    memory_dir = workspace / ".aib_memory"
    if general:
        return memory_dir / _GENERAL_LOG_FILENAME, None

    input_path = memory_dir / "input.md"
    if not input_path.exists():
        return None, "input.md not found; run initialize first."
    content = read_text(input_path)
    try:
        header = parse_input_header(content)
    except ValueError as exc:
        return None, f"Cannot parse input.md header: {exc}"
    if header is None:
        return None, "input.md does not contain a valid YAML frontmatter header."
    if header["state"]["status"] == "idle":
        return None, "No active request found. Cannot write log entry."
    request_id = header["state"]["request_id"]
    return memory_dir / f"log_{request_id}.md", None


def _format_entry(message: str) -> str:
    """Format a single log entry with a UTC timestamp prefix.

    Args:
        message: The log message text.

    Returns:
        Formatted entry string: ``YYYYMMDD-HHmmss: <message>\\n``.
    """
    timestamp = datetime.now(timezone.utc).strftime(_TIMESTAMP_FORMAT)
    return f"{timestamp}: {message}\n"


def main() -> int:
    """Entry point: resolve log path, write entry, print to stdout.

    Returns:
        0 on success; 1 when no active request is found in normal mode.
    """
    args = _parse_args()
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    log_path, error = _resolve_log_path(workspace, args.general)
    if error is not None:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    entry = _format_entry(args.message)

    # Append entry to log file; create the file if it does not exist.
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)

    # Print entry to stdout (without trailing newline to match expected output).
    print(entry, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
