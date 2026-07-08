#!/usr/bin/env python3
"""input-header.py: CRUD operations on the YAML frontmatter header of .aib_memory/input.md.

Operations:
  read    Print all header fields as key=value lines to stdout.
  write   Update one or more header fields. Unspecified fields are preserved.
  reset   Reset header to idle state (request_id: ~, title: ~, state: idle, minimum_questions: 5).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import (
    ValidationError,
    ensure_workspace,
    parse_input_header,
    read_input_header,
    read_text,
    write_input_header,
    write_text,
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed namespace with workspace, operation, and optional field overrides.
    """
    parser = argparse.ArgumentParser(
        description="CRUD operations on the YAML frontmatter header of .aib_memory/input.md."
    )
    parser.add_argument(
        "--workspace", required=True, help="Workspace root path."
    )
    parser.add_argument(
        "--operation",
        required=True,
        choices=["read", "write", "reset"],
        help="Operation: read (print fields), write (update fields), reset (set to idle).",
    )
    parser.add_argument("--request-id", default=None, help="Set request_id field (write only).")
    parser.add_argument("--title", default=None, help="Set title field (write only).")
    parser.add_argument(
        "--state",
        default=None,
        choices=["idle", "analysis_ready", "questions_generated"],
        help="Set state field (write only).",
    )
    parser.add_argument(
        "--minimum-questions",
        type=int,
        default=None,
        help="Set options.minimum_questions field (write only).",
    )
    parser.add_argument(
        "--input-verification-enabled",
        default=None,
        choices=["true", "false"],
        help="Set input_verification_enabled flag (write only).",
    )
    parser.add_argument(
        "--input-verification-result",
        default=None,
        choices=["null", "valid", "invalid"],
        help="Set input_verification_result flag (write only).",
    )
    parser.add_argument(
        "--context-verification-enabled",
        default=None,
        choices=["true", "false"],
        help="Set context_verification_enabled flag (write only).",
    )
    parser.add_argument(
        "--context-verification-result",
        default=None,
        choices=["null", "valid", "invalid"],
        help="Set context_verification_result flag (write only).",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: perform the requested CRUD operation on the input.md YAML header."""
    args = _parse_args()
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)
        input_path = workspace / ".aib_memory" / "input.md"
        if not input_path.exists():
            raise ValidationError("input.md not found; run initialize first")

        content = read_text(input_path)

        if args.operation == "read":
            header = parse_input_header(content)
            if header is None:
                raise ValidationError("input.md does not contain a valid YAML frontmatter header")
            state = header["state"]
            opts = header["options"]
            print(f"request_id={state['request_id']}")
            print(f"title={state['title']}")
            # Print workflow status as "state=" for backward compatibility with prompt scripts.
            print(f"state={state['status']}")
            print(f"minimum_questions={opts['minimum_questions']}")
            # Convert Python booleans to lowercase string for consistent output.
            input_ver_enabled = opts.get("input_verification_enabled", True)
            input_ver_result = state.get("input_verification_result", None)
            ctx_ver_enabled = opts.get("context_verification_enabled", True)
            ctx_ver_result = state.get("context_verification_result", None)
            print(f"input_verification_enabled={str(input_ver_enabled).lower()}")
            print(f"input_verification_result={input_ver_result if input_ver_result is not None else 'null'}")
            print(f"context_verification_enabled={str(ctx_ver_enabled).lower()}")
            print(f"context_verification_result={ctx_ver_result if ctx_ver_result is not None else 'null'}")

        elif args.operation == "write":
            header = parse_input_header(content)
            if header is None:
                raise ValidationError("input.md does not contain a valid YAML frontmatter header")
            if args.request_id is not None:
                header["state"]["request_id"] = args.request_id
            if args.title is not None:
                header["state"]["title"] = args.title
            if args.state is not None:
                # The CLI flag --state maps to state.status in the nested structure.
                header["state"]["status"] = args.state
            if args.minimum_questions is not None:
                header["options"]["minimum_questions"] = args.minimum_questions
            if args.input_verification_enabled is not None:
                header["options"]["input_verification_enabled"] = args.input_verification_enabled == "true"
            if args.input_verification_result is not None:
                # Store None for "null", otherwise store the string value.
                header["state"]["input_verification_result"] = (
                    None if args.input_verification_result == "null" else args.input_verification_result
                )
            if args.context_verification_enabled is not None:
                header["options"]["context_verification_enabled"] = args.context_verification_enabled == "true"
            if args.context_verification_result is not None:
                header["state"]["context_verification_result"] = (
                    None if args.context_verification_result == "null" else args.context_verification_result
                )
            write_text(input_path, write_input_header(content, header))
            print(f"Updated input.md header: state={header['state']['status']}")

        elif args.operation == "reset":
            idle_header = {
                "state": {
                    "request_id": "~",
                    "title": "~",
                    "status": "idle",
                    "input_verification_result": None,
                    "context_verification_result": None,
                },
                "options": {
                    "minimum_questions": 0,
                    "input_verification_enabled": True,
                    "context_verification_enabled": True,
                },
            }
            write_text(input_path, write_input_header(content, idle_header))
            print("Reset input.md header to idle state.")

    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
