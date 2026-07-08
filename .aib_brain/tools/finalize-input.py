#!/usr/bin/env python3
"""
finalize-input.py: Archive input.md (with stub-equivalence guard), move attachment
files from .aib_memory/attachments/ to the request folder root, and reset
input.md to the seed template with the active request ID injected.
Part of the AIB core tooling layer.
Responsibilities: stub-equivalence check, conditional input.md archiving,
attachment relocation, seed-template reset with request ID injection.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from common import (
    ValidationError,
    _INPUT_SEED_TEMPLATE,
    ensure_workspace,
    parse_input_header,
    read_input_header,
    read_text,
    slugify,
    write_input_header,
    write_text,
)

# ---------------------------------------------------------------------------
# Seed template — imported from common to ensure a single authoritative source.
# ---------------------------------------------------------------------------


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


def _is_stub_equivalent(content: str) -> bool:
    """Return True when content is functionally identical to the seed template.

    For YAML-frontmatter format: strip the frontmatter block (between the two
    ``---`` delimiters) from both content and the seed template, then compare
    the bodies.  The frontmatter values (request_id, title, state) are
    intentionally ignored during comparison so that an already-reset input.md
    (which carries the real request ID and a state value) is treated the same
    as a freshly seeded input.md.

    Args:
        content: Current content of input.md.

    Returns:
        True when the non-frontmatter body matches the seed template body.
    """
    def _strip_frontmatter(text: str) -> str:
        """Strip the YAML frontmatter block and return the normalized body."""
        norm = text.replace("\r\n", "\n")
        lines = norm.splitlines()
        if lines and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    body = "\n".join(lines[i + 1:]).strip()
                    return body
        # No frontmatter — return stripped content.
        return norm.strip()

    return _strip_frontmatter(content) == _strip_frontmatter(_INPUT_SEED_TEMPLATE)


def main() -> None:
    """Entry point: archive input.md, move attachments, reset input.md.

    Steps performed in order:
    1. Validate workspace and resolve the target request from the register.
    2. Archive input.md to <request-folder>/input-archive-<timestamp>.md
       when input.md is not stub-equivalent; skip otherwise.
    3. Walk .aib_memory/attachments/ and move every non-.gitkeep file to
       <request-folder>/<relative-path>, preserving subdirectory structure.
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

        # Resolve target request from input.md YAML header.
        header = read_input_header(workspace)
        if header["state"]["status"] == "idle":
            raise ValidationError("No active request found in input.md YAML header; cannot finalize")

        # If explicit --request-id given, validate it matches.
        req_id_arg = (args.request_id or "").strip()
        if req_id_arg and req_id_arg != header["state"]["request_id"]:
            raise ValidationError(
                f"Explicit --request-id {req_id_arg!r} does not match active request {header['state']['request_id']!r}"
            )

        request_id = header["state"]["request_id"]
        title = header["state"]["title"]
        # Derive folder path from request_id and title using the same slugify
        # convention used by create-request.py.
        folder_name = f"{request_id}-{slugify(title)}"
        folder_rel = f".aib_memory/requests/{folder_name}"
        request_folder = workspace / folder_rel

        input_file = workspace / ".aib_memory" / "input.md"

        # ---- Step 1: Conditionally archive input.md --------------------------
        current_content = read_text(input_file)
        if not _is_stub_equivalent(current_content):
            # Non-stub: preserve the developer's content before overwriting.
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            archive_path = request_folder / f"input-archive-{timestamp}.md"
            write_text(archive_path, current_content)
            print(f"Archived input.md -> {archive_path.relative_to(workspace)}")
        else:
            # Stub-equivalent: nothing meaningful to preserve; skip archiving.
            print("input.md is stub-equivalent — archive step skipped.")

        # ---- Step 2: Move attachment files to request folder root ----------------
        attachments_dir = workspace / ".aib_memory" / "attachments"
        if attachments_dir.is_dir():
            for src in attachments_dir.rglob("*"):
                # Skip directories and .gitkeep placeholder files.
                if not src.is_file() or src.name == ".gitkeep":
                    continue
                # Compute the relative path under attachments/ so subdirectory
                # structure is preserved under the request folder root.
                rel = src.relative_to(attachments_dir)
                dest = request_folder / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Use shutil.move for cross-filesystem compatibility.
                shutil.move(str(src), str(dest))
                print(f"Moved attachment: {rel} -> {dest.relative_to(workspace)}")

        # ---- Step 3: Reset input.md to seed template -------------------------
        # Build new header preserving minimum_questions, injecting real request ID and title.
        # The seed template uses status: idle; we explicitly set analysis_ready for active requests.
        reset_header = parse_input_header(_INPUT_SEED_TEMPLATE) or {
            "state": {
                "request_id": "~", "title": "~", "status": "analysis_ready",
                "input_verification_result": None, "context_verification_result": None,
            },
            "options": {
                "minimum_questions": 5,
                "input_verification_enabled": True,
                "context_verification_enabled": True,
            },
        }
        reset_header["state"]["request_id"] = request_id
        reset_header["state"]["title"] = title
        # Keep the request in analysis_ready state after finalization.
        reset_header["state"]["status"] = "analysis_ready"
        reset_header["options"]["minimum_questions"] = header["options"]["minimum_questions"]
        reset_content = write_input_header(_INPUT_SEED_TEMPLATE, reset_header)
        write_text(input_file, reset_content)
        print(f"Reset input.md - active request: {request_id} - {title}")

    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
