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
    ValidationError,
    artifact_name,
    ensure_workspace,
    parse_args,
    read_input_header,
    slugify,
)

# Artifact types that live at .aib_memory/ root while a request is active.
# The actual filenames are constructed dynamically using artifact_name() so
# that each file carries the request ID, preventing merge conflicts across branches.
_ARTIFACT_TYPES = ("plan", "analysis")


def move_artifacts(workspace: Path) -> None:
    """Move active-request artifacts from .aib_memory/ root to the active request subfolder.

    Reads the input.md YAML header to resolve the active request folder and request ID.
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
        ValidationError: If the workspace is invalid, the input.md header is missing,
                         or no active request is found.
    """
    ensure_workspace(workspace)

    # Read active request state from input.md YAML header.
    header = read_input_header(workspace)
    if header["state"]["status"] == "idle":
        raise ValidationError("No active request found; cannot move artifacts")

    request_id = header["state"]["request_id"].strip()
    title = header["state"]["title"]
    # Derive folder path using the same slugify convention as create-request.py.
    folder_name = f"{request_id}-{slugify(title)}"
    folder_rel = f".aib_memory/requests/{folder_name}"
    dest_folder = workspace / folder_rel
    dest_folder.mkdir(parents=True, exist_ok=True)
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

    # Handle the log file separately — its naming pattern uses an underscore,
    # which is incompatible with the artifact_name() helper (hyphen convention).
    log_filename = f"log_{request_id}.md"
    log_source = aib_memory / log_filename
    log_dest = dest_folder / log_filename
    if log_source.exists():
        shutil.move(str(log_source), str(log_dest))
        print(f"Moved: {log_source.relative_to(workspace)} -> {log_dest.relative_to(workspace)}")
    else:
        print(f"Skipped (not found): .aib_memory/{log_filename}")


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
