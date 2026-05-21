#!/usr/bin/env python3
"""
move-request-artifacts.py: Move active-request artifacts from .aib_memory/ root
to the active request's subfolder.
Part of the AIB tool scripts. Invoked by aib-implement.md (pre-close) and
close-request.py (safety net).
Responsibilities: locate the active request folder, move plan-<ID>.md and
analysis-<ID>.md from .aib_memory/ to the request subfolder; idempotent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from common import (
    ACTIVE,
    ValidationError,
    artifact_name,
    ensure_workspace,
    parse_args,
    parse_markdown_table,
    read_text,
    requests_register_path,
)

# Artifact types that live at .aib_memory/ root while a request is active.
# The actual filenames are constructed dynamically using artifact_name() so
# that each file carries the request ID, preventing merge conflicts across branches.
_ARTIFACT_TYPES = ("plan", "analysis")


def move_artifacts(workspace: Path) -> None:
    """Move active-request artifacts from .aib_memory/ root to the active request subfolder.

    Reads requests_register.md to resolve the active request folder and request ID.
    For each artifact type (plan, analysis):
      - Constructs the ID-suffixed source filename (e.g. ``plan-R-20260509-2313.md``).
            - If the source exists at ``.aib_memory/<filename>``, moves it to the request
                subfolder keeping its ID-suffixed name (e.g. ``plan-R-20260509-2313.md``).
      - If the source does not exist, skips silently (idempotent).
    Calling this function a second time is safe: no sources remain at root after
    the first successful move, so the second call is a no-op.

    Args:
        workspace: Resolved absolute path to the workspace root.

    Raises:
        ValidationError: If the workspace is invalid, the register is missing,
                         or no active request is found.
    """
    ensure_workspace(workspace)

    register = requests_register_path(workspace)
    if not register.exists():
        raise ValidationError("Missing requests_register.md; run initialize first")

    header, rows = parse_markdown_table(read_text(register))
    if not header:
        raise ValidationError("requests_register.md has no valid table")

    col = {name: idx for idx, name in enumerate(header)}
    active = [r for r in rows if r[col["state"]] == ACTIVE]
    if len(active) == 0:
        raise ValidationError("No active request found; cannot move artifacts")
    if len(active) > 1:
        raise ValidationError("Multiple active requests found; resolve register inconsistency")

    folder_rel = active[0][col["folder"]]
    dest_folder = workspace / folder_rel
    dest_folder.mkdir(parents=True, exist_ok=True)

    request_id = active[0][col["request_id"]].strip()
    aib_memory = workspace / ".aib_memory"

    for artifact_type in _ARTIFACT_TYPES:
        # Construct the ID-suffixed filename (e.g. "plan-R-20260509-2313.md").
        filename = artifact_name(artifact_type, request_id)
        source = aib_memory / filename
        # Archived artifacts keep their ID-suffixed names inside the subfolder.
        dest = dest_folder / filename
        if source.exists():
            # shutil.move handles cross-filesystem moves unlike os.rename
            shutil.move(str(source), str(dest))
            print(f"Moved: {source.relative_to(workspace)} -> {dest.relative_to(workspace)}")
        else:
            print(f"Skipped (not found): .aib_memory/{filename}")


def main() -> None:
    """Entry point: resolve workspace, run move_artifacts, exit cleanly."""
    args = parse_args("Move active-request artifacts to request subfolder")
    workspace = Path(args.workspace).resolve()

    try:
        move_artifacts(workspace)
    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
