#!/usr/bin/env python3
"""
finalize-input.py: Archive input.md (with stub-equivalence guard), move attachment
files from .aib_memory/attachments/ to the request inputs folder, and reset
input.md to the seed template with the active request ID injected.
Part of the AIB core tooling layer.
Responsibilities: stub-equivalence check, conditional input.md archiving,
attachment relocation, seed-template reset with request ID injection.
"""

from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

from common import (
    ValidationError,
    ensure_workspace,
    parse_markdown_table,
    read_text,
    requests_register_path,
    resolve_active_request_or_explicit,
    write_text,
)

# ---------------------------------------------------------------------------
# Seed template (no toggle lines)
# ---------------------------------------------------------------------------
# This is the canonical reset state written to input.md after finalization.
# "No active request" is replaced with the real request ID + title at runtime.
_SEED_TEMPLATE = (
    "## Active request\n"
    "No active request\n\n"
    "## Options\n"
    "- Minimum questions: 0\n\n"
    "## Input\n\n"
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed namespace with ``workspace`` (str) and ``request_id`` (str | None).
    """
    parser = argparse.ArgumentParser(
        description=(
            "Archive input.md (stub-equivalence checked), move attachment files "
            "to the request inputs folder, and reset input.md to the seed template."
        )
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Workspace root path (must contain .aib_brain/ and .aib_memory/).",
    )
    parser.add_argument(
        "--request-id",
        default=None,
        help="Explicit request ID (e.g. R-20260511-2019); defaults to the single Active request.",
    )
    return parser.parse_args()


def _normalize(content: str) -> str:
    """Normalize line endings and trailing whitespace for stub-equivalence comparison.

    Converts CRLF to LF and strips trailing whitespace from every line so that
    a Windows-originated file with the same logical content compares equal to a
    Unix-style copy.

    Args:
        content: Raw file content string.

    Returns:
        Normalized string with CRLF -> LF and per-line trailing whitespace stripped.
    """
    # Normalize Windows line endings to Unix so cross-platform comparisons work.
    content = content.replace("\r\n", "\n")
    # Strip trailing whitespace per line to avoid false inequalities.
    lines = [line.rstrip() for line in content.split("\n")]
    return "\n".join(lines).strip()


def _is_stub_equivalent(content: str) -> bool:
    """Return True when content is functionally identical to the seed template.

    A stub-equivalent input.md contains no meaningful developer input — only the
    seed structure is present. The active request line value (request ID or
    "No active request") is intentionally ignored during comparison so that an
    already-reset input.md (which carries the request ID) is treated the same as
    a freshly seeded input.md (which carries "No active request").

    When True, the archive step is skipped because there is nothing worth preserving.

    Args:
        content: Current content of input.md.

    Returns:
        True when the content, after normalisation and active-request-line
        canonicalisation, matches the seed template.
    """
    # Regex to match "## Active request" heading followed by the value line.
    _active_req_re = re.compile(r"(## Active request\n)[^\n]*", re.MULTILINE)
    _placeholder = "## Active request\n_PLACEHOLDER_"

    def _canonicalise(text: str) -> str:
        """Normalise and replace the active-request value with a fixed placeholder."""
        normalised = _normalize(text)
        # Replace "## Active request\n<any value>" with a neutral placeholder so
        # the request ID value does not affect structural comparison.
        return _active_req_re.sub(_placeholder, normalised, count=1)

    return _canonicalise(content) == _canonicalise(_SEED_TEMPLATE)


def main() -> None:
    """Entry point: archive input.md, move attachments, reset input.md.

    Steps performed in order:
    1. Validate workspace and resolve the target request from the register.
    2. Archive input.md to <request-folder>/inputs/input-archive-<timestamp>.md
       when input.md is not stub-equivalent; skip otherwise.
    3. Walk .aib_memory/attachments/ and move every non-.gitkeep file to
       <request-folder>/inputs/<relative-path>, preserving subdirectory structure.
    4. Write the seed template to input.md, replacing "No active request" with
       the resolved request ID and title.

    Raises:
        SystemExit(1): On any ValidationError (missing workspace, missing register,
        no active request, etc.).
    """
    args = _parse_args()
    workspace = Path(args.workspace).resolve()
    try:
        # Validate workspace structure before performing any file I/O.
        ensure_workspace(workspace)

        # Resolve target request: explicit ID or the single Active row.
        row = resolve_active_request_or_explicit(workspace, args.request_id)

        # Parse column indices from the register header.
        register_content = read_text(requests_register_path(workspace))
        header, _rows = parse_markdown_table(register_content)
        col = {name: idx for idx, name in enumerate(header)}

        request_id = row[col["request_id"]]
        title = row[col["title"]]
        # folder is workspace-relative (e.g. ".aib_memory/requests/R-xxx-slug").
        folder_rel = row[col["folder"]]
        request_folder = workspace / folder_rel

        input_file = workspace / ".aib_memory" / "input.md"
        # inputs/ is the staging area for archived input.md and moved attachments.
        inputs_dir = request_folder / "inputs"

        # ---- Step 1: Conditionally archive input.md --------------------------
        current_content = read_text(input_file)
        if not _is_stub_equivalent(current_content):
            # Non-stub: preserve the developer's content before overwriting.
            inputs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_path = inputs_dir / f"input-archive-{timestamp}.md"
            write_text(archive_path, current_content)
            print(f"Archived input.md -> {archive_path.relative_to(workspace)}")
        else:
            # Stub-equivalent: nothing meaningful to preserve; skip archiving.
            print("input.md is stub-equivalent — archive step skipped.")

        # ---- Step 2: Move attachment files to request inputs/ ----------------
        attachments_dir = workspace / ".aib_memory" / "attachments"
        if attachments_dir.is_dir():
            for src in attachments_dir.rglob("*"):
                # Skip directories and .gitkeep placeholder files.
                if not src.is_file() or src.name == ".gitkeep":
                    continue
                # Compute the relative path under attachments/ so subdirectory
                # structure is preserved under inputs/.
                rel = src.relative_to(attachments_dir)
                dest = inputs_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Use shutil.move for cross-filesystem compatibility.
                shutil.move(str(src), str(dest))
                print(f"Moved attachment: {rel} -> {dest.relative_to(workspace)}")

        # ---- Step 3: Reset input.md to seed template -------------------------
        # Inject the real request ID + title, replacing the "No active request" stub.
        reset_content = _SEED_TEMPLATE.replace(
            "No active request", f"{request_id} \u2014 {title}"
        )
        write_text(input_file, reset_content)
        print(f"Reset input.md - active request: {request_id} - {title}")

    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
