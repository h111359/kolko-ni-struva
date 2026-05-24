#!/usr/bin/env python3
"""
close-request.py: Close an active request and reset input.md to the seed template.
Part of the AIB tool scripts.
Responsibilities: invoke move-request-artifacts before marking Closed (safety net),
mark the active request as Closed in requests_register.md,
auto-close any open iterations, and reset input.md to 'No active request'.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from common import (
    ACTIVE,
    CLOSED,
    ValidationError,
    ensure_workspace,
    format_markdown_table,
    now_iso,
    parse_args,
    parse_markdown_table,
    read_text,
    requests_register_path,
    update_requests_register,
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
    args = parse_args("Close request")
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)

        register = requests_register_path(workspace)
        if not register.exists():
            raise ValidationError("Missing requests_register.md; run initialize first")

        header, rows = parse_markdown_table(read_text(register))
        col = {name: idx for idx, name in enumerate(header)}

        req_id = (args.request_id or "").strip()
        if req_id:
            matches = [r for r in rows if r[col["request_id"]] == req_id]
            if not matches:
                raise ValidationError(f"Request not found: {req_id}")
            target = matches[0]
        else:
            active = [r for r in rows if r[col["state"]] == ACTIVE]
            if len(active) == 0:
                raise ValidationError("No active request found; provide --request-id")
            if len(active) > 1:
                raise ValidationError("Multiple active requests found")
            target = active[0]

        if target[col["state"]] == CLOSED:
            raise ValidationError("Request already closed")

        folder_rel = target[col["folder"]]

        # Move active-request artifacts from .aib_memory/ root to the request
        # subfolder before marking Closed. This is a safety-net call; if
        # aib-implement.md already ran the move, this is a no-op. A move
        # failure must not block the close operation.
        try:
            move_artifacts = _load_move_artifacts()
            move_artifacts(workspace)
        except Exception as exc:  # noqa: BLE001
            print(f"WARNING: move-request-artifacts encountered an error and was skipped: {exc}")

        target[col["state"]] = CLOSED
        target[col["closed_at"]] = now_iso()

        update_requests_register(workspace, rows)

        # Safety-net: warn (non-blocking) when attachments/ is non-empty at
        # close time. Files should have been moved to the request folder during
        # the analysis archiving step; their presence here indicates a missed
        # archiving step that the developer should investigate.
        attachments_dir = workspace / ".aib_memory" / "attachments"
        if attachments_dir.exists() and any(
            f for f in attachments_dir.iterdir() if f.name != ".gitkeep"
        ):
            print(
                "WARNING: .aib_memory/attachments/ is non-empty. "
                "Files were not archived — consider running aib-analyze.md before closing."
            )

        # Reset input.md to the seed template so the Status section reads
        # "No active request" and State: idle after the request is closed. Skip silently if the
        # file does not exist (e.g. workspace not yet initialized).
        input_file = workspace / ".aib_memory" / "input.md"
        if input_file.exists():
            input_seed = (
                "## Status\n"
                "No active request\n"
                "State: idle\n\n"
                "## Options\n"
                "- Minimum questions: 0\n\n"
                "## Input\n\n"
            )
            write_text(input_file, input_seed)

        print(f"Closed request: {target[col['request_id']]}")

    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
