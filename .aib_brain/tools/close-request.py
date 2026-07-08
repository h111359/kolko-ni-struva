#!/usr/bin/env python3
"""
close-request.py: Close the active request and reset input.md YAML header to idle.
Part of the AIB tool scripts.
Responsibilities: invoke move-request-artifacts before resetting (safety net),
verify the target request is active, reset input.md YAML header to idle state.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from common import (
    ValidationError,
    ensure_workspace,
    parse_args,
    parse_input_header,
    read_text,
    slugify,
    write_input_header,
    write_text,
)


def _load_move_artifacts():
    """Dynamically load move_artifacts from move-request-artifacts.py.

    Returns:
        The move_artifacts callable from the move script.

    Raises:
        ImportError: If the script cannot be found or loaded.
    """
    # The script uses a hyphenated filename which is not directly importable
    # as a Python module identifier; use importlib to load it by file path.
    script_path = Path(__file__).parent / "move-request-artifacts.py"
    spec = importlib.util.spec_from_file_location("move_request_artifacts", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.move_artifacts


def main() -> None:
    """Entry point: resolve active request from YAML header, run cleanup, reset header to idle."""
    args = parse_args("Close request")
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)

        input_path = workspace / ".aib_memory" / "input.md"
        if not input_path.exists():
            raise ValidationError("input.md not found; run initialize first")

        content = read_text(input_path)
        header = parse_input_header(content)
        if header is None:
            raise ValidationError("input.md does not contain a valid YAML frontmatter header")

        if header["state"]["status"] == "idle":
            raise ValidationError("No active request found; nothing to close")

        # If explicit --request-id given, verify it matches the active request.
        req_id_arg = (args.request_id or "").strip()
        if req_id_arg and req_id_arg != header["state"]["request_id"]:
            raise ValidationError(
                f"Explicit request ID {req_id_arg!r} does not match active request {header['state']['request_id']!r}"
            )

        active_request_id = header["state"]["request_id"]
        active_title = header["state"]["title"]

        # Move active-request artifacts from .aib_memory/ root to the request subfolder.
        # Safety-net call; if aib-implement.md already ran the move, this is a no-op.
        try:
            move_artifacts = _load_move_artifacts()
            move_artifacts(workspace)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: move-request-artifacts encountered an error and was skipped: {exc}")

        # Safety-net: warn (non-blocking) when attachments/ is non-empty at close time.
        attachments_dir = workspace / ".aib_memory" / "attachments"
        if attachments_dir.exists() and any(
            f for f in attachments_dir.iterdir() if f.name != ".gitkeep"
        ):
            print(
                "WARNING: .aib_memory/attachments/ is non-empty. "
                "Files were not archived — consider running aib-analyze.md before closing."
            )

        # Reset input.md YAML header to idle state, preserving options.
        idle_header = {
            "state": {
                "request_id": "~",
                "title": "~",
                "status": "idle",
                "input_verification_result": None,
                "context_verification_result": None,
            },
            "options": {
                "minimum_questions": header["options"]["minimum_questions"],
                "input_verification_enabled": header["options"].get("input_verification_enabled", True),
                "context_verification_enabled": header["options"].get("context_verification_enabled", True),
            },
        }
        write_text(input_path, write_input_header(content, idle_header))

        print(f"Closed request: {active_request_id}")

    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
