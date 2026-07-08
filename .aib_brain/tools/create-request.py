#!/usr/bin/env python3
"""Create and register a new active request in input.md YAML header."""

from __future__ import annotations

import re
from pathlib import Path

from common import (
    ValidationError,
    ensure_workspace,
    now_compact_request_id,
    now_iso,
    parse_args,
    parse_input_header,
    read_input_header,
    read_text,
    requests_root,
    slugify,
    write_input_header,
    write_text,
)


def main() -> None:
    """Entry point: validate the workspace, check for an idle state, create request folder and YAML header."""
    args = parse_args("Create a new AIB request")
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)

        title = (args.title or "").strip()
        if not title:
            raise ValidationError("--title is required")
        if not re.search(r"[a-zA-Z]", title):
            raise ValidationError("Title must contain at least one letter to generate a meaningful slug.")

        # Read current header to check for an existing active request.
        header = read_input_header(workspace)
        if header["state"]["status"] != "idle":
            raise ValidationError(
                f"Cannot create request while another request is active: {header['state']['request_id']}"
            )

        req_id = args.request_id.strip() if args.request_id else now_compact_request_id()
        folder_name = f"{req_id}-{slugify(title)}"
        folder_rel = f".aib_memory/requests/{folder_name}"
        request_folder = workspace / folder_rel

        if request_folder.exists():
            raise ValidationError(f"Request folder already exists: {folder_rel}")

        request_folder.mkdir(parents=True, exist_ok=False)

        # Write active request to input.md YAML header.
        input_path = workspace / ".aib_memory" / "input.md"
        content = read_text(input_path)
        new_header = {
            "state": {
                "request_id": req_id,
                "title": title,
                "status": "analysis_ready",
                "input_verification_result": None,
                "context_verification_result": None,
            },
            "options": {
                "minimum_questions": header["options"]["minimum_questions"],
                "input_verification_enabled": header["options"].get("input_verification_enabled", True),
                "context_verification_enabled": header["options"].get("context_verification_enabled", True),
            },
        }
        write_text(input_path, write_input_header(content, new_header))

        print(f"Created request: {req_id}")
        print(f"Folder: {folder_rel}")

    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
