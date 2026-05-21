#!/usr/bin/env python3
"""Shared helpers for AIB tool scripts."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

ACTIVE = "Active"
CLOSED = "Closed"

REQ_ID_PATTERN = re.compile(r"^R-\d{8}-\d{4}$")


class ValidationError(RuntimeError):
    """Raised on deterministic validation failures."""


def parse_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument("--request-id", default=None, help="Explicit request ID")
    parser.add_argument("--title", default=None, help="Request title (create-request only)")
    parser.add_argument("--summary", default="", help="Short summary text")
    parser.add_argument("--force", action="store_true", default=False, help="Force overwrite of existing files (initialize only)")
    parser.add_argument("--upgrade", action="store_true", default=False, help="Upgrade .aib_memory/ structure from .aib_brain/ templates (initialize only)")
    return parser.parse_args()


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def now_compact_request_id(now: dt.datetime | None = None) -> str:
    value = now or now_local()
    return f"R-{value.strftime('%Y%m%d-%H%M')}"


def now_iso(now: dt.datetime | None = None) -> str:
    value = now or now_local()
    return value.strftime("%Y-%m-%d %H:%M:%S %z")


def slugify(text: str, max_length: int = 64) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    lowered = lowered[:max_length].rstrip("-")
    return lowered or "request"


def get_semver(directory: Path) -> "str | None":
    """Return the semver marker file name found in *directory*, or None.

    Scans *directory* for files matching the ``vMAJOR.MINOR.PATCH`` pattern.
    Returns the file name (e.g. ``"v1.2.8"``) when exactly one match is found.
    Returns ``None`` when zero or multiple matches are found (fail-safe).

    Args:
        directory: Filesystem path of the directory to scan.

    Returns:
        The semver marker file name, or None if not found or ambiguous.
    """
    if not directory.is_dir():
        return None
    matches = list(directory.glob("v[0-9]*.[0-9]*.[0-9]*"))
    # Only consider plain files, not subdirectories; require exactly one match.
    file_matches = [m for m in matches if m.is_file()]
    if len(file_matches) == 1:
        return file_matches[0].name
    return None


def ensure_workspace(workspace: Path) -> None:
    if not workspace.exists() or not workspace.is_dir():
        raise ValidationError(f"Workspace does not exist: {workspace}")
    if not (workspace / ".aib_brain").exists():
        raise ValidationError("Missing .aib_brain/ folder in workspace")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def parse_markdown_table(content: str) -> Tuple[List[str], List[List[str]]]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 2:
        return [], []

    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: List[List[str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        rows.append(cells[: len(header)])
    return header, rows


def format_markdown_table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    sep = ["---"] * len(header)
    out = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in rows:
        vals = [str(v).replace("\n", " ").strip() for v in row]
        if len(vals) < len(header):
            vals += [""] * (len(header) - len(vals))
        out.append("| " + " | ".join(vals[: len(header)]) + " |")
    return "\n".join(out) + "\n"


def requests_register_path(workspace: Path) -> Path:
    return workspace / ".aib_memory" / "requests_register.md"


def requests_root(workspace: Path) -> Path:
    return workspace / ".aib_memory" / "requests"


def resolve_active_request_or_explicit(workspace: Path, request_id: str | None) -> List[str]:
    register = requests_register_path(workspace)
    if not register.exists():
        raise ValidationError("Missing .aib_memory/requests_register.md; run initialize first")

    header, rows = parse_markdown_table(read_text(register))
    if not header:
        raise ValidationError("requests_register.md has no valid table")

    col = {name: idx for idx, name in enumerate(header)}
    for required in ["request_id", "title", "folder", "state", "created_at", "closed_at"]:
        if required not in col:
            raise ValidationError(f"requests_register.md missing column: {required}")

    if request_id:
        matches = [r for r in rows if r[col["request_id"]] == request_id]
        if not matches:
            raise ValidationError(f"Request ID not found: {request_id}")
        return matches[0]

    active = [r for r in rows if r[col["state"]] == ACTIVE]
    if len(active) == 0:
        raise ValidationError("No active request found; provide --request-id explicitly")
    if len(active) > 1:
        raise ValidationError("Multiple active requests found; resolve register inconsistency")
    return active[0]


def update_requests_register(workspace: Path, rows: Sequence[Sequence[str]]) -> None:
    header = ["request_id", "title", "folder", "state", "created_at", "closed_at"]
    text = "# Requests Register\n\n" + format_markdown_table(header, rows)
    write_text(requests_register_path(workspace), text)


REQUIRED_PLAN_SECTIONS = [
    "## Goal",
    "## Constraints",
    "## Success criteria",
    "## Plan",
]


def validate_plan_md(path: Path) -> None:
    """Raise ValidationError if ``plan.md`` is missing any required section."""
    content = read_text(path)
    if not content:
        raise ValidationError(f"plan.md is empty or missing: {path}")
    for heading in REQUIRED_PLAN_SECTIONS:
        # Match heading at the start of a line, case-insensitive
        if not re.search(r"^" + re.escape(heading), content, re.IGNORECASE | re.MULTILINE):
            raise ValidationError(
                f"plan.md missing required section '{heading}': {path}"
            )


def artifact_name(artifact_type: str, request_id: str) -> str:
    """Construct the active-phase artifact filename for a given artifact type and request ID.

    Active-phase artifacts reside at ``.aib_memory/<artifact_type>-<request_id>.md``
    while the request is open. This helper centralises filename construction to avoid
    scattered string literals across tool scripts and prompts.

    Args:
        artifact_type: Artifact category; one of ``"plan"``, ``"analysis"``,
            or ``"UAT_scenarios"``.
        request_id: The request identifier, which must match the pattern
            ``R-YYYYMMDD-HHmi`` (e.g. ``"R-20260509-2313"``).

    Returns:
        The filename string, e.g. ``"plan-R-20260509-2313.md"``.

    Raises:
        ValueError: If ``request_id`` does not match the expected pattern, to
            prevent path traversal via malformed identifiers.
    """
    if not REQ_ID_PATTERN.match(request_id):
        raise ValueError(
            f"Invalid request_id '{request_id}'; expected pattern R-YYYYMMDD-HHmi"
        )
    return f"{artifact_type}-{request_id}.md"


def print_error_and_exit(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)
