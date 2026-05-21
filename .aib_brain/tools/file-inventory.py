#!/usr/bin/env python3
"""Emit a deterministic workspace file inventory.

This helper is intentionally model/tool agnostic: it does not generate documentation.
It exists to support context synthesis by producing a stable, sortable
inventory that can be chunked for large repositories.

Output format: JSON Lines (one JSON object per file), sorted by `path`.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable, List

from common import ValidationError, ensure_workspace


DEFAULT_EXCLUDE_DIRS = [
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AIB file-inventory helper: file inventory")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    parser.add_argument(
        "--output",
        default="",
        help="Output path for JSONL (default: stdout). Parent dirs are created.",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude (repeatable). Defaults include .git, node_modules, venv.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Maximum number of files to emit (0 means no limit).",
    )
    return parser.parse_args()


def _should_exclude(path: Path, excluded_dirnames: set[str], workspace: Path) -> bool:
    try:
        rel = path.relative_to(workspace)
    except ValueError:
        return True

    for part in rel.parts:
        if part in excluded_dirnames:
            return True
    return False


def iter_files(workspace: Path, excluded_dirnames: set[str]) -> Iterable[Path]:
    # Use os.walk for performance and easier dir-pruning.
    for root, dirs, files in os.walk(workspace):
        root_path = Path(root)

        # Prune excluded dirs.
        pruned: List[str] = []
        for d in list(dirs):
            candidate = root_path / d
            if _should_exclude(candidate, excluded_dirnames, workspace):
                pruned.append(d)
        for d in pruned:
            dirs.remove(d)

        for name in files:
            file_path = root_path / name
            if _should_exclude(file_path, excluded_dirnames, workspace):
                continue
            yield file_path


def main() -> None:
    args = parse_args()
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)
    except ValidationError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    excluded = set(DEFAULT_EXCLUDE_DIRS)
    excluded.update([d.strip() for d in args.exclude_dir if d.strip()])

    records = []
    for file_path in iter_files(workspace, excluded):
        try:
            stat = file_path.stat()
        except OSError:
            continue

        rel = file_path.relative_to(workspace).as_posix()
        ext = file_path.suffix.lower().lstrip(".")

        records.append(
            {
                "path": rel,
                "size_bytes": int(stat.st_size),
                "mtime_epoch": int(stat.st_mtime),
                "extension": ext,
            }
        )

    records.sort(key=lambda r: r["path"])

    if args.max_files and args.max_files > 0:
        records = records[: args.max_files]

    out_text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)

    if args.output:
        out_path = (workspace / args.output).resolve() if not Path(args.output).is_absolute() else Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_text, encoding="utf-8", newline="\n")
        print(f"Wrote {len(records)} records to {out_path}")
    else:
        print(out_text, end="")


if __name__ == "__main__":
    main()
