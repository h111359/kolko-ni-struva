#!/usr/bin/env python3
"""
initialize.py: Initialize AIB memory structures and default artifacts.
Part of the AIB core tooling layer.
Responsibilities: seed .aib_memory/ from .aib_brain/ templates, create required
directories and files, seed semver marker, run upgrade procedure when --upgrade is given.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

from common import (
    ValidationError,
    ensure_workspace,
    get_semver,
    parse_markdown_table,
    print_error_and_exit,
    parse_args,
    write_text,
)


# Default `path` values that the legacy `references.md` seeded; rows whose
# normalised path matches one of these values are NOT reported during the
# upgrade-time legacy inspection.
_LEGACY_DEFAULT_REFERENCE_PATHS = frozenset(
    {".aib_memory/context.md"}
)


def _seed_memory(workspace: Path, brain_dir: Path, memory_root: Path, force: bool = False) -> None:
    """Seed the standard .aib_memory/ artifacts from .aib_brain/ templates.

    Creates required directories and seeds every default file. Existing files
    are skipped on idempotent re-runs.

    Args:
        workspace: Resolved workspace root path.
        brain_dir: Path to the .aib_brain/ directory.
        memory_root: Path to the .aib_memory/ directory to seed.
        force: Reserved for future per-file overwrite behaviour.
    """
    (memory_root / "requests").mkdir(parents=True, exist_ok=True)
    (memory_root / "logs").mkdir(parents=True, exist_ok=True)

    # Create the attachments staging folder used by aib-analyze.md as an
    # enriched input channel. A .gitkeep placeholder ensures the empty directory
    # is committed to VCS and available immediately after a fresh clone.
    attachments_dir = memory_root / "attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    gitkeep = attachments_dir / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
        print("Created attachments directory.")

    register_file = memory_root / "requests_register.md"
    if register_file.exists():
        print("requests_register.md already exists — skipping overwrite.")
    else:
        requests_register = (
            "# Requests Register\n\n"
            "| request_id | title | folder | state | created_at | closed_at |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
        )
        write_text(register_file, requests_register)

    context_file = memory_root / "context.md"
    if context_file.exists():
        print("context.md already exists — skipping overwrite.")
    else:
        write_text(context_file, "# Context\n\nThis file is managed by the `aib-refresh-context.md` prompt. Run it to populate workspace context.\n")

    input_file = memory_root / "input.md"
    if input_file.exists():
        print("input.md already exists — skipping overwrite.")
    else:
        input_seed = (
            "## Active request\n"
            "No active request\n\n"
            "## Options\n"
            "- Minimum questions: 0\n\n"
            "## Input\n\n"
        )
        write_text(input_file, input_seed)

    # Seed instructions.md as the workspace-level persistent instructions file.
    # Idempotent: does not overwrite a file that already exists.
    instructions_file = memory_root / "instructions.md"
    if instructions_file.exists():
        print("instructions.md already exists — skipping overwrite.")
    else:
        write_text(instructions_file, "")


def _seed_semver(brain_dir: Path, memory_root: Path, force: bool = False) -> str | None:
    """Seed a semver marker file in *memory_root* matching the brain version.

    Skips seeding when the marker already exists, unless *force* is True.
    Prints a warning and returns None when no brain semver can be found.

    Args:
        brain_dir: Path to the .aib_brain/ directory.
        memory_root: Path to the .aib_memory/ directory.
        force: When True, overwrite an existing semver marker.

    Returns:
        The seeded semver string (e.g. ``"v1.2.8"``), or None when skipped.
    """
    brain_semver = get_semver(brain_dir)
    if not brain_semver:
        print("WARNING: No semver marker found in .aib_brain/ — skipping semver seeding.")
        return None

    semver_file = memory_root / brain_semver
    if semver_file.exists() and not force:
        print(f"{brain_semver} already exists in .aib_memory/ — skipping overwrite.")
        return brain_semver

    # Remove any stale semver files before writing the new one.
    for old in memory_root.glob("v[0-9]*.[0-9]*.[0-9]*"):
        if old.is_file():
            old.unlink()

    semver_file.touch()
    return brain_semver


def _prompt_migrate_requests() -> bool:
    """Interactively ask whether old requests should be migrated into the new .aib_memory/.

    When stdin is not a TTY (e.g., during automated testing or CI), the function
    silently returns True (migrate), preserving backward-compatible behaviour.

    Returns:
        True when old requests should be restored (migrate); False when they
        should remain in the archive only.
    """
    if not sys.stdin.isatty():
        # Non-interactive environment: default to migrate for backward compatibility.
        return True
    choice = input(
        "Migrate old requests to new .aib_memory/? "
        "[Y=migrate / N=archive only] (Y): "
    ).strip().upper()
    return choice != "N"


def _warn_about_legacy_references(legacy_path: Path) -> None:
    """Inspect a legacy `references.md` from the upgrade archive and warn about
    rows whose `path` differs from the two known defaults.

    The warning is informational only. The function never raises: a missing
    file is silently ignored, and an unparseable file produces a single
    explicit warning line then returns.

    Args:
        legacy_path: Path to the archived legacy `references.md` file.
    """
    if not legacy_path.is_file():
        return

    try:
        content = legacy_path.read_text(encoding="utf-8")
        header, rows = parse_markdown_table(content)
    except Exception:  # noqa: BLE001 — informational helper, never blocks upgrade
        print("WARNING: legacy references.md is not parseable; skipping migration check.")
        return

    if not header or "path" not in header:
        print("WARNING: legacy references.md is not parseable; skipping migration check.")
        return

    path_idx = header.index("path")
    extras: list[str] = []
    for row in rows:
        if path_idx >= len(row):
            continue
        raw_path = row[path_idx].strip()
        if not raw_path:
            continue
        normalised = raw_path.replace("\\", "/")
        if normalised in _LEGACY_DEFAULT_REFERENCE_PATHS:
            continue
        extras.append(raw_path)

    if not extras:
        return

    print("WARNING: legacy references.md contains entries beyond the two defaults.")
    print("The following references will NOT be migrated automatically:")
    for entry in extras:
        print(f"  - {entry}")
    print("If you still need them, add them to .aib_memory/instructions.md.")


def _run_upgrade(workspace: Path, brain_dir: Path, memory_root: Path) -> None:
    """Execute the full .aib_memory/ upgrade procedure.

    Creates a timestamped archive of the current .aib_memory/ (excluding any
    existing archives/), deletes the non-archive content, re-seeds from brain
    templates, and restores the user-curated files from the archive.
    Prompts interactively whether old requests should be migrated or archived only.

    When the user chooses to migrate requests (Y), the requests/ directory is
    MOVED from the archive to active memory — it is NOT retained in the archive.
    After a successful migration the archive will NOT contain a requests/ subfolder;
    requests exist in exactly one location (active memory).

    When the user declines migration (N), requests/ remains exclusively in the
    archive and active memory receives only the freshly-seeded empty stub.

    Args:
        workspace: Resolved workspace root path.
        brain_dir: Path to the .aib_brain/ directory.
        memory_root: Path to the .aib_memory/ directory to upgrade.

    Raises:
        ValidationError: When no brain semver marker is found.
    """
    brain_semver = get_semver(brain_dir)
    if not brain_semver:
        raise ValidationError(
            "Cannot upgrade: no semver marker found in .aib_brain/. "
            "Ensure the brain directory contains a file named vMAJOR.MINOR.PATCH."
        )

    # Step 1 — Create timestamped archive directory.
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archives_dir = memory_root / "archives"
    archive_path = archives_dir / timestamp
    # Ensure uniqueness when two upgrades happen within the same second.
    counter = 1
    while archive_path.exists():
        archive_path = archives_dir / f"{timestamp}-{counter}"
        counter += 1
    archive_path.mkdir(parents=True, exist_ok=True)

    # Step 2 — Copy all .aib_memory/ content (excluding archives/) into the archive.
    # Prevents the archives/ directory from being nested inside itself.
    for item in memory_root.iterdir():
        if item.name == "archives":
            # Existing archives stay at their current level — never nest them.
            continue
        dest = archive_path / item.name
        if item.is_dir():
            shutil.copytree(str(item), str(dest))
        else:
            shutil.copy2(str(item), str(dest))

    print(f"Archive created: {archive_path}")

    # Step 2b — Inspect any legacy references.md captured in the archive and
    # warn the developer about user-added rows that will not be migrated
    # automatically. Informational only; never aborts the upgrade.
    _warn_about_legacy_references(archive_path / "references.md")

    # Step 3 — Delete all non-archive content from .aib_memory/.
    for item in memory_root.iterdir():
        if item.name == "archives":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    print("Cleared non-archive content from .aib_memory/")

    # Step 4 — Re-seed .aib_memory/ from brain templates.
    _seed_memory(workspace, brain_dir, memory_root, force=False)

    # Step 5 — Seed new semver marker.
    _seed_semver(brain_dir, memory_root, force=True)

    # Step 6 — Prompt whether old requests should be migrated or archived only.
    migrate_requests = _prompt_migrate_requests()

    # Step 7 — Restore user-curated files from the archive.
    # context.md and instructions.md are always restored; requests-related
    # files are restored only when the user chose to migrate old requests.
    restore_files = ["context.md", "instructions.md"]
    if migrate_requests:
        restore_files += ["requests_register.md"]
    restored: list[str] = []
    for filename in restore_files:
        src = archive_path / filename
        if src.exists():
            dest = memory_root / filename
            shutil.copy2(str(src), str(dest))
            restored.append(filename)

    # Step 8 — Conditionally restore requests/ directory from archive.
    # When migrating, copy requests/ to active memory then remove it from the
    # archive so requests exist in exactly one location (active memory only).
    if migrate_requests:
        requests_archive = archive_path / "requests"
        if requests_archive.exists():
            requests_dest = memory_root / "requests"
            if requests_dest.exists():
                shutil.rmtree(requests_dest)
            shutil.copytree(str(requests_archive), str(requests_dest))
            # Remove from the archive after a successful copy so requests/ is
            # never duplicated across active memory and the archive.
            shutil.rmtree(str(requests_archive))
            restored.append("requests/ (moved from archive)")

    requests_disposition = "moved to active memory (removed from archive)" if migrate_requests else "archived only"
    print("\nUpgrade summary:")
    print(f"  Brain version   : {brain_semver}")
    print(f"  Archive location: {archive_path}")
    print(f"  Restored files  : {', '.join(restored) if restored else 'none'}")
    print(f"  Requests        : {requests_disposition}")
    print("\n.aib_memory/ upgrade complete.")


def main() -> None:
    """Entry point for the initialize script.

    Parses arguments and either runs the upgrade procedure (--upgrade) or the
    standard idempotent seeding procedure. Exits with a non-zero code on error.
    """
    args = parse_args("Initialize AIB memory structure")
    workspace = Path(args.workspace).resolve()

    try:
        ensure_workspace(workspace)

        memory_root = workspace / ".aib_memory"
        brain_dir = workspace / ".aib_brain"

        if args.upgrade:
            # Upgrade path: back up, clean, re-seed, restore.
            memory_root.mkdir(parents=True, exist_ok=True)
            _run_upgrade(workspace, brain_dir, memory_root)
        else:
            # Standard idempotent initialization path.
            memory_root.mkdir(parents=True, exist_ok=True)
            _seed_memory(workspace, brain_dir, memory_root, force=args.force)
            _seed_semver(brain_dir, memory_root, force=args.force)
            print("Initialized .aib_memory structure successfully.")

    except ValidationError as exc:
        print_error_and_exit(str(exc))


if __name__ == "__main__":
    main()
