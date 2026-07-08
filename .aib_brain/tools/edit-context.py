"""
edit-context.py: CRUD operations for statements in .aib_memory/context.md.
Part of the AIB tools suite.
Responsibilities: Select, insert, and delete statements by section using
text-based line matching. Supports Product, Concepts, Requirements, Solution,
and Issues sections. Supports --planned flag for insert operations.
"""

import argparse
import re
import sys
from pathlib import Path

# Valid content section names for CRUD operations (must match context-convention.md)
VALID_AREAS = {
    "Product",
    "Concepts",
    "Requirements",
    "Solution",
    "Issues",
}

# Ordered area list for consistent section insertion order
AREA_ORDER = [
    "Product",
    "Concepts",
    "Requirements",
    "Solution",
    "Issues",
]

# Valid modality types for Requirements section inserts
MODALITY_TYPES = {"MUST", "MUST NOT", "OPTIONAL"}

# Pattern matching H2 headings
H2_PATTERN = re.compile(r"^## .+$")

# Pattern matching a Requirements modality-prefixed statement
MODALITY_STATEMENT_PATTERN = re.compile(r"^- (MUST NOT|MUST|OPTIONAL): (.+)$")


def _build_area_heading(area: str) -> str:
    """
    Return the H2 heading string for the given area name.

    Args:
        area: Area name (e.g. 'Product').

    Returns:
        The heading string (e.g. '## Product').
    """
    return f"## {area}"


def _find_area_range(lines: list[str], area: str) -> tuple[int, int]:
    """
    Find the start and end line indices for a given area section.

    Args:
        lines: All lines of context.md.
        area: The area name (e.g. 'Product').

    Returns:
        Tuple (start, end) where start is the heading line index and end is the
        line index of the next H2 or end of file. Returns (-1, -1) if not found.
    """
    target_heading = _build_area_heading(area)
    start = -1
    for i, line in enumerate(lines):
        if line.rstrip() == target_heading:
            start = i
            break

    if start == -1:
        return (-1, -1)

    # Find end: next H2 heading or end of file
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if H2_PATTERN.match(lines[i].rstrip()):
            end = i
            break

    return (start, end)


def _get_statement_text(line: str) -> str | None:
    """
    Extract the text portion from a statement line, stripping any prefix.

    For Requirements lines (e.g., '- MUST: text'), returns the text after the modality prefix.
    For plain lines (e.g., '- text'), returns the text after '- '.
    Returns None if the line is not a statement line.

    Args:
        line: A single line from context.md (stripped of trailing whitespace).

    Returns:
        The text portion, or None if the line is not a statement.
    """
    stripped = line.strip()
    if not stripped.startswith("- "):
        return None

    # Check for modality prefix first (longer match wins)
    modality_match = MODALITY_STATEMENT_PATTERN.match(stripped)
    if modality_match:
        return modality_match.group(2).strip()

    # Plain bullet: text is everything after "- "
    return stripped[2:].strip()


def _find_statement_by_text(lines: list[str], area: str, text_substring: str) -> int:
    """
    Find the line index of the first statement in the area section that contains
    the given text substring (case-insensitive, matched against text portion only).

    Args:
        lines: All lines of context.md.
        area: Area name.
        text_substring: Substring to search for in statement text portion.

    Returns:
        Line index of the matching statement, or -1 if not found.
    """
    start, end = _find_area_range(lines, area)
    if start == -1:
        return -1

    needle = text_substring.lower()
    matches = []
    for i in range(start + 1, end):
        text = _get_statement_text(lines[i].rstrip())
        if text is not None and needle in text.lower():
            matches.append(i)

    if len(matches) > 1:
        sys.stderr.write(
            f"Warning: Ambiguous match — {len(matches)} statements in '{area}' "
            f"contain '{text_substring}'. Using first match at line {matches[0] + 1}.\n"
        )

    return matches[0] if matches else -1


def _insert_area_section(lines: list[str], area: str) -> list[str]:
    """
    Insert a new area section heading in the correct order within the document.

    Area sections are ordered according to AREA_ORDER. The new section is inserted
    after the last existing area section that precedes it in the order, or before
    the '## File Structure' section (or end of file) if no preceding area exists.

    Args:
        lines: All lines of context.md.
        area: The area name to insert.

    Returns:
        Modified lines with the new area heading inserted.
    """
    target_order = AREA_ORDER.index(area) if area in AREA_ORDER else len(AREA_ORDER)

    # Use '## File Structure' as the upper bound, or end of file
    insert_at = len(lines)
    file_structure_line = -1
    for i, line in enumerate(lines):
        if line.rstrip() == "## File Structure":
            file_structure_line = i
            break

    if file_structure_line != -1:
        insert_at = file_structure_line

    # Walk backwards from insert_at to find the last area section that should precede this one
    last_preceding_end = -1
    for idx, other_area in enumerate(AREA_ORDER):
        if idx >= target_order:
            break
        start, end = _find_area_range(lines, other_area)
        if start != -1:
            last_preceding_end = end

    if last_preceding_end != -1:
        insert_at = last_preceding_end

    # Build insertion with blank line separation
    new_section_lines = []
    if insert_at > 0 and lines[insert_at - 1].strip() != "":
        new_section_lines.append("\n")
    new_section_lines.append(f"{_build_area_heading(area)}\n")
    new_section_lines.append("\n")

    return lines[:insert_at] + new_section_lines + lines[insert_at:]


def _validate_uniqueness_in_area(lines: list[str], area: str, new_text: str) -> bool:
    """
    Check that no existing statement in the area section has identical text (case-insensitive).

    Comparison uses the text portion only (after stripping any modality prefix).

    Args:
        lines: All lines of context.md.
        area: Area name.
        new_text: The text of the statement being inserted (without prefix).

    Returns:
        True if the text is unique, False if a duplicate exists.
    """
    start, end = _find_area_range(lines, area)
    if start == -1:
        return True  # Section doesn't exist yet, no duplicates possible

    needle = new_text.strip().lower()
    for i in range(start + 1, end):
        text = _get_statement_text(lines[i].rstrip())
        if text is not None and text.lower() == needle:
            sys.stderr.write(
                f"Error: Duplicate statement text in '{area}': '{new_text}'\n"
            )
            return False

    return True


def operation_select(lines: list[str], area: str, text_substring: str) -> int:
    """
    Find and print the statement matching the given text substring in the area section.

    Args:
        lines: All lines of context.md.
        area: Area name.
        text_substring: Substring to search for in statement text.

    Returns:
        0 if found, 1 if not found.
    """
    line_idx = _find_statement_by_text(lines, area, text_substring)
    if line_idx == -1:
        sys.stderr.write(
            f"Error: No statement in '{area}' containing '{text_substring}'.\n"
        )
        return 1

    print(lines[line_idx].rstrip())
    return 0


def operation_insert(
    lines: list[str],
    area: str,
    modality: str | None,
    text: str,
    planned: bool = False,
) -> tuple[list[str], int]:
    """
    Insert a new statement in the appropriate area section.

    For Requirements sections, formats the line as '- MODALITY: text' or
    '- [PLANNED] MODALITY: text' when planned=True.
    For other sections, formats the line as '- text' or '- [PLANNED] text'
    when planned=True. Issues section uses plain '- text' format only
    (--planned is silently ignored for Issues).

    Args:
        lines: All lines of context.md.
        area: Area name.
        modality: Modality prefix (MUST/MUST NOT/OPTIONAL) for Requirements; None for others.
        text: Statement text content.
        planned: When True, prepend '[PLANNED] ' to the statement.

    Returns:
        Tuple of (modified lines, exit code). Exit code 0 on success, 1 on failure.
    """
    # Validate uniqueness before inserting
    if not _validate_uniqueness_in_area(lines, area, text):
        return (lines, 1)

    # Find or create the area section
    start, end = _find_area_range(lines, area)
    if start == -1:
        lines = _insert_area_section(lines, area)
        start, end = _find_area_range(lines, area)
        if start == -1:
            sys.stderr.write(f"Error: Failed to create section for area '{area}'.\n")
            return (lines, 1)

    # Build the statement line based on section type and planned flag
    if area == "Requirements" and modality:
        if planned:
            statement = f"- [PLANNED] {modality}: {text}\n"
        else:
            statement = f"- {modality}: {text}\n"
    elif planned and area != "Issues":
        # [PLANNED] prefix is meaningful only in Product, Concepts, Solution, Requirements
        statement = f"- [PLANNED] {text}\n"
    else:
        statement = f"- {text}\n"

    # Insert at the end of the section, before trailing blank lines
    insert_at = end
    while insert_at > start + 1 and lines[insert_at - 1].strip() == "":
        insert_at -= 1

    new_lines = lines[:insert_at]
    new_lines.append(statement)
    new_lines.extend(lines[insert_at:])

    return (new_lines, 0)


def operation_delete(lines: list[str], area: str, text_substring: str) -> tuple[list[str], int]:
    """
    Remove the statement matching the text substring in the area section.

    Args:
        lines: All lines of context.md.
        area: Area name.
        text_substring: Substring to search for in statement text.

    Returns:
        Tuple of (modified lines, exit code). Exit code 0 on success, 1 if not found.
    """
    line_idx = _find_statement_by_text(lines, area, text_substring)
    if line_idx == -1:
        sys.stderr.write(
            f"Error: No statement in '{area}' containing '{text_substring}'. Nothing deleted.\n"
        )
        return (lines, 1)

    new_lines = [line for i, line in enumerate(lines) if i != line_idx]
    return (new_lines, 0)


def main() -> int:
    """
    Entry point for the edit-context tool.

    Parses arguments and dispatches to the appropriate CRUD operation on
    statements in .aib_memory/context.md.

    Returns:
        0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        description="CRUD operations for statements in .aib_memory/context.md."
    )
    parser.add_argument(
        "--operation",
        required=True,
        choices=["select", "insert", "delete"],
        help="Operation to perform: select, insert, or delete.",
    )
    parser.add_argument(
        "--area",
        required=True,
        help="Section name (Product, Concepts, Requirements, Solution).",
    )
    parser.add_argument(
        "--type",
        default=None,
        dest="modality",
        help="Statement modality prefix; required for Requirements inserts (MUST, MUST NOT, OPTIONAL); not used for other sections.",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Statement text (required for insert and as search substring for select/delete).",
    )
    parser.add_argument(
        "--planned",
        action="store_true",
        default=False,
        help="When set on insert, prepend '[PLANNED] ' to the statement. Ignored for Issues area.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace root path (default: current directory).",
    )

    args = parser.parse_args()

    # Validate area name
    if args.area not in VALID_AREAS:
        sys.stderr.write(
            f"Error: Invalid area name '{args.area}'. "
            f"Valid names: {', '.join(sorted(VALID_AREAS))}.\n"
        )
        return 1

    # Validate text is provided (required for all operations)
    if not args.text:
        sys.stderr.write("Error: --text is required for all operations.\n")
        return 1

    # Validate modality for insert
    if args.operation == "insert":
        if args.area == "Requirements":
            if not args.modality:
                sys.stderr.write("Error: --type is required for Requirements insert.\n")
                return 1
            if args.modality not in MODALITY_TYPES:
                sys.stderr.write(
                    f"Error: Invalid modality '{args.modality}'. "
                    f"Valid values: {', '.join(sorted(MODALITY_TYPES))}.\n"
                )
                return 1
        elif args.area != "Issues":
            if args.modality:
                sys.stderr.write(
                    f"Error: --type is only valid for Requirements inserts; "
                    f"'{args.area}' does not use modality prefixes.\n"
                )
                return 1
        else:
            # Issues area: modality is not applicable
            if args.modality:
                sys.stderr.write(
                    "Error: --type is not valid for Issues inserts.\n"
                )
                return 1

    # Locate context.md
    context_path = Path(args.workspace) / ".aib_memory" / "context.md"
    if not context_path.exists():
        sys.stderr.write(f"Error: context.md not found at '{context_path}'.\n")
        return 1

    # Read context.md
    lines = context_path.read_text(encoding="utf-8").splitlines(keepends=True)

    if args.operation == "select":
        return operation_select(lines, args.area, args.text)

    elif args.operation == "insert":
        new_lines, exit_code = operation_insert(
            lines, args.area, args.modality, args.text, planned=args.planned
        )
        if exit_code == 0:
            context_path.write_text("".join(new_lines), encoding="utf-8")
        return exit_code

    elif args.operation == "delete":
        new_lines, exit_code = operation_delete(lines, args.area, args.text)
        if exit_code == 0:
            context_path.write_text("".join(new_lines), encoding="utf-8")
        return exit_code

    return 1


if __name__ == "__main__":
    sys.exit(main())
