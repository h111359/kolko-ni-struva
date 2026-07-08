#!/usr/bin/env python3
"""Shared helpers for AIB tool scripts."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import List, Sequence

ACTIVE = "Active"
CLOSED = "Closed"

REQ_ID_PATTERN = re.compile(r"^R-\d{8}-\d{4}$")

# Authoritative seed template for input.md using the nested YAML structure.
# Both finalize-input.py and initialize.py import this constant so the seed
# is defined in exactly one place.
_INPUT_SEED_TEMPLATE = (
    "---\n"
    "state:\n"
    "  request_id: ~\n"
    "  title: ~\n"
    "  status: idle\n"
    "  input_verification_result: null\n"
    "  context_verification_result: null\n"
    "options:\n"
    "  minimum_questions: 5\n"
    "  input_verification_enabled: true\n"
    "  context_verification_enabled: true\n"
    "---\n\n"
    "## Input\n\n"
)


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


def _parse_flat_yaml_value(content: str, key: str) -> "str | None":
    """Extract the scalar value for *key* from flat-structure YAML content.

    Handles plain and single/double-quoted values.  Ignores comment lines
    (starting with ``#``) and blank lines.  Does NOT support nested keys,
    multi-line values, or anchors — aib-setup.yaml uses flat top-level keys only.

    Args:
        content: Raw text content of a flat-key YAML file.
        key: The top-level key to look up.

    Returns:
        The string value associated with *key*, or ``None`` if not found.
    """
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Only match lines that start with the exact key at column 0 (top-level).
        if not line.startswith(key):
            continue
        remainder = line[len(key):]
        # Require colon immediately after the key name to avoid partial-name matches.
        if not remainder.startswith(":"):
            continue
        value = remainder[1:].strip()
        # Strip an optional inline comment.
        if " #" in value:
            value = value[: value.index(" #")].strip()
        # Strip surrounding single or double quotes.
        if len(value) >= 2 and value[0] in ("'", '"') and value[-1] == value[0]:
            value = value[1:-1]
        return value if value else None
    return None


def get_setup_option(directory: Path, option: str) -> "str | None":
    """Return the value of *option* from aib-setup.yaml in *directory*, or None.

    Reads ``aib-setup.yaml`` from *directory* and returns the string value for
    the named top-level key.  Returns ``None`` when the file does not exist,
    cannot be read, or the key is absent.

    Args:
        directory: Filesystem path of the directory containing ``aib-setup.yaml``.
        option: Top-level YAML key to retrieve (e.g. ``"memory_version"``).

    Returns:
        The string value for *option*, or ``None`` if not found.
    """
    setup_file = directory / "aib-setup.yaml"
    if not setup_file.is_file():
        return None
    try:
        content = setup_file.read_text(encoding="utf-8")
    except OSError:
        return None
    return _parse_flat_yaml_value(content, option)


def set_setup_option(directory: Path, option: str, value: str) -> None:
    """Set *option* to *value* in aib-setup.yaml in *directory*.

    Reads ``aib-setup.yaml``, replaces any existing line whose key matches
    *option* with ``option: value``, or appends a new line when the key is
    absent.  All other keys are preserved unchanged.
    """
    setup_file = directory / "aib-setup.yaml"
    if setup_file.is_file():
        lines = setup_file.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []
    found = False
    for i, line in enumerate(lines):
        key_part = line.split(":", 1)[0].rstrip()
        if key_part == option:
            lines[i] = f"{option}: {value}\n"
            found = True
            break
    if not found:
        lines.append(f"{option}: {value}\n")
    setup_file.write_text("".join(lines), encoding="utf-8", newline="\n")


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


def requests_root(workspace: Path) -> Path:
    return workspace / ".aib_memory" / "requests"


def _yaml_quote(value: str) -> str:
    """Return *value* single-quoted when it contains YAML special characters.

    Plain values (null marker ``~`` and values with no YAML-special characters)
    are returned as-is.  All other strings are wrapped in single quotes with
    embedded single-quote characters escaped as ``''`` (YAML 1.2 convention).

    Args:
        value: The string value to quote.

    Returns:
        The value unchanged or wrapped in single quotes.
    """
    if value == "~":
        return "~"
    _YAML_SPECIAL = set(":#{}[]|>&*!,'`\"")
    if any(c in value for c in _YAML_SPECIAL):
        return "'" + value.replace("'", "''") + "'"
    return value


def parse_input_header(content: str) -> "dict | None":
    """Parse YAML frontmatter block from *content* (input.md text).

    Supports the new AIB nested schema with two top-level group keys:
    - ``state:`` group: ``request_id``, ``title``, ``status`` (the workflow
      state; values ``idle|analysis_ready|questions_generated``),
      ``input_verification_result``, ``context_verification_result``.
    - ``options:`` group: ``minimum_questions``, ``input_verification_enabled``,
      ``context_verification_enabled``.

    Raises ``ValueError`` when a top-level ``request_id`` key is detected,
    indicating the old flat format. No auto-migration is performed; the workspace
    must be re-initialized.

    Args:
        content: Full text of input.md.

    Returns:
        Dict with two top-level keys ``state`` (nested dict) and ``options``
        (nested dict).  Returns ``None`` when no valid ``---`` frontmatter
        block is found.

    Raises:
        ValueError: When the old flat frontmatter format is detected
            (top-level ``request_id`` key present at the non-indented level).
    """
    import re as _re

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx == -1:
        return None

    # Detect old flat format: top-level request_id key (no leading whitespace).
    for line in lines[1:end_idx]:
        if _re.match(r"^request_id\s*:", line):
            raise ValueError(
                "Old flat frontmatter format detected (top-level 'request_id' key present). "
                "Re-initialize the workspace to migrate to the new nested format."
            )

    state_block: dict = {
        "request_id": "~",
        "title": "~",
        "status": "idle",
        "input_verification_result": None,
        "context_verification_result": None,
    }
    options_block: dict = {
        "minimum_questions": 0,
        "input_verification_enabled": True,
        "context_verification_enabled": True,
    }

    # Track the current top-level group being parsed.
    current_group: "str | None" = None
    for line in lines[1:end_idx]:
        # Detect top-level group keys (no leading whitespace, ends with colon only).
        top_key_match = _re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*$", line)
        if top_key_match:
            current_group = top_key_match.group(1)
            continue

        # Parse indented sub-keys within the current group.
        sub_key_match = _re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)", line)
        if sub_key_match and current_group is not None:
            key = sub_key_match.group(1)
            raw = sub_key_match.group(2).strip()
            # Strip surrounding single or double quotes.
            if len(raw) >= 2:
                if (raw[0] == "'" and raw[-1] == "'") or (raw[0] == '"' and raw[-1] == '"'):
                    raw = raw[1:-1].replace("''", "'")
            if current_group == "state":
                state_block[key] = raw
            elif current_group == "options":
                options_block[key] = raw

    # Convert minimum_questions to int.
    try:
        options_block["minimum_questions"] = int(options_block["minimum_questions"])
    except (ValueError, TypeError):
        options_block["minimum_questions"] = 0

    # Convert YAML boolean strings to Python bool for enabled flags.
    for bool_key in ("input_verification_enabled", "context_verification_enabled"):
        raw_val = options_block.get(bool_key)
        if raw_val == "true":
            options_block[bool_key] = True
        elif raw_val == "false":
            options_block[bool_key] = False
        # Already a bool (from defaults) — leave unchanged.

    # Convert YAML null string to Python None for result flags.
    for result_key in ("input_verification_result", "context_verification_result"):
        if state_block.get(result_key) == "null":
            state_block[result_key] = None

    return {"state": state_block, "options": options_block}


def _serialize_bool(value: object) -> str:
    """Serialize a Python bool (or bool-like string) to a YAML boolean literal.

    Args:
        value: Python ``True``/``False`` or the strings ``"true"``/``"false"``.

    Returns:
        ``"true"`` or ``"false"``.
    """
    if value is True or value == "true":
        return "true"
    return "false"


def _serialize_result_flag(value: object) -> str:
    """Serialize a verification result flag to its YAML representation.

    Args:
        value: Python ``None`` or the strings ``"valid"``/``"invalid"``.

    Returns:
        ``"null"``, ``"valid"``, or ``"invalid"``.
    """
    if value is None or value == "null":
        return "null"
    if value in ("valid", "invalid"):
        return str(value)
    return "null"


def write_input_header(content: str, header: dict) -> str:
    """Replace the YAML frontmatter block in *content* with *header* and return the result.

    The body of input.md (everything after the closing ``---`` delimiter) is
    preserved unchanged.  When no frontmatter block exists the new block is
    prepended to the existing content.

    Args:
        content: Current full text of input.md.
        header: Dict with two top-level keys:
            - ``state``: nested dict with ``request_id``, ``title``, ``status``,
              ``input_verification_result``, ``context_verification_result``.
            - ``options``: nested dict with ``minimum_questions``,
              ``input_verification_enabled``, ``context_verification_enabled``.

    Returns:
        Updated input.md text with the frontmatter block replaced.
    """
    lines = content.splitlines(keepends=True)
    body_start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                body_start = i + 1
                break
    body = "".join(lines[body_start:])

    state = header.get("state", {})
    opts = header.get("options", {})

    req_id = _yaml_quote(str(state.get("request_id", "~")))
    title = _yaml_quote(str(state.get("title", "~")))
    status = str(state.get("status", "idle"))
    input_ver_result = _serialize_result_flag(state.get("input_verification_result", None))
    ctx_ver_result = _serialize_result_flag(state.get("context_verification_result", None))

    min_q = int(opts.get("minimum_questions", 0))
    input_ver_enabled = _serialize_bool(opts.get("input_verification_enabled", True))
    ctx_ver_enabled = _serialize_bool(opts.get("context_verification_enabled", True))

    frontmatter = (
        "---\n"
        "state:\n"
        f"  request_id: {req_id}\n"
        f"  title: {title}\n"
        f"  status: {status}\n"
        f"  input_verification_result: {input_ver_result}\n"
        f"  context_verification_result: {ctx_ver_result}\n"
        "options:\n"
        f"  minimum_questions: {min_q}\n"
        f"  input_verification_enabled: {input_ver_enabled}\n"
        f"  context_verification_enabled: {ctx_ver_enabled}\n"
        "---\n"
    )
    return frontmatter + body


def read_input_header(workspace: Path) -> dict:
    """Read and parse the YAML frontmatter header from input.md in *workspace*.

    Args:
        workspace: Resolved absolute path to the workspace root.

    Returns:
        Parsed header dict (see ``parse_input_header``).

    Raises:
        ValidationError: When input.md is missing or has no valid YAML header.
    """
    input_path = workspace / ".aib_memory" / "input.md"
    if not input_path.exists():
        raise ValidationError("input.md not found; run initialize first")
    content = read_text(input_path)
    header = parse_input_header(content)
    if header is None:
        raise ValidationError("input.md does not contain a valid YAML frontmatter header")
    return header


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
