"""
verify-context.py: Validate .aib_memory/context.md against context-convention.md rules.
Part of the AIB tools suite.
Responsibilities: Run structural and format checks on context.md, report pass/fail per check,
write context_verification_result to input.md YAML header, exit with code 0 if all pass or 1 if any fail.
"""

import argparse
import re
import sys
from pathlib import Path

from common import parse_input_header, read_text, write_input_header, write_text

# Valid section names (must match context-convention.md)
VALID_SECTIONS = {
    "Product",
    "Concepts",
    "Requirements",
    "Solution",
    "File Structure",
    "References",
    "Issues",
}

# Sections where bullet-statement format is NOT enforced
NON_STATEMENT_SECTIONS = {"File Structure", "References"}

# Pattern matching a plain bullet statement (Product, Concepts, Solution, Issues)
PLAIN_STATEMENT_PATTERN = re.compile(r"^- .+$")

# Pattern matching a [PLANNED]-prefixed plain bullet (Product, Concepts, Solution)
PLANNED_PLAIN_PATTERN = re.compile(r"^- \[PLANNED\] .+$")

# Pattern matching a modality-prefixed statement (Requirements)
MODALITY_STATEMENT_PATTERN = re.compile(r"^- (MUST NOT|MUST|OPTIONAL): .+$")

# Pattern matching a [PLANNED]-prefixed modality statement (Requirements)
PLANNED_MODALITY_PATTERN = re.compile(r"^- \[PLANNED\] (MUST NOT|MUST|OPTIONAL): .+$")

# Pattern matching H2 headings
H2_PATTERN = re.compile(r"^## .+$")

# Pattern matching H3 headings
H3_PATTERN = re.compile(r"^### .+$")

# Pattern detecting HTML tags
HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z/][^>]*>")

# Pattern detecting URLs
URL_PATTERN = re.compile(r"https?://")

# Pattern detecting Markdown table rows (lines starting with |)
TABLE_PATTERN = re.compile(r"^\|")

# Type-letter prefix pattern (e.g., "- N: text" or "- R: text")
TYPE_LETTER_PATTERN = re.compile(r"^- [A-Z]: ")


def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the verification script.

    Returns:
        Parsed namespace with workspace path.
    """
    parser = argparse.ArgumentParser(
        description="Validate .aib_memory/context.md against context-convention.md rules."
    )
    parser.add_argument(
        "--workspace", default=".", help="Workspace root path (default: current directory)"
    )
    return parser.parse_args()


def _read_context(workspace: Path) -> str:
    """
    Read the context.md file from the workspace.

    Args:
        workspace: Path to workspace root.

    Returns:
        Full text content of context.md.

    Raises:
        FileNotFoundError: If context.md does not exist.
    """
    context_path = workspace / ".aib_memory" / "context.md"
    return context_path.read_text(encoding="utf-8")


def _get_section_ranges(lines: list[str]) -> list[tuple[str, int, int]]:
    """
    Extract content section ranges from the document, excluding File Structure and References.

    Args:
        lines: All lines of context.md.

    Returns:
        List of (section_name, heading_line_index, end_line_index) tuples for
        Product, Concepts, Requirements, Solution, and Issues sections only.
        end_line_index is the index of the next H2 or end of file.
    """
    sections: list[tuple[str, int, int]] = []

    # Collect all H2 heading positions
    h2_positions: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if H2_PATTERN.match(stripped):
            heading_text = stripped[3:].strip()
            h2_positions.append((heading_text, i))

    for idx, (heading_text, pos) in enumerate(h2_positions):
        end = h2_positions[idx + 1][1] if idx + 1 < len(h2_positions) else len(lines)
        # Skip File Structure and References — no bullet-statement format enforcement
        if heading_text in NON_STATEMENT_SECTIONS:
            continue
        if heading_text in VALID_SECTIONS:
            sections.append((heading_text, pos, end))

    return sections


def check_document_title(content: str) -> tuple[bool, str]:
    """
    Verify document starts with '# Product Context'.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "# Product Context":
        return False, "Document does not start with '# Product Context'."
    return True, ""


def check_all_h2_headings_valid(content: str) -> tuple[bool, str]:
    """
    Verify every H2 heading is one of the 6 valid section names.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    invalid_headings = []

    for line in lines:
        stripped = line.strip()
        if H2_PATTERN.match(stripped):
            heading_text = stripped[3:].strip()
            if heading_text not in VALID_SECTIONS:
                invalid_headings.append(stripped)

    if invalid_headings:
        return False, f"Invalid H2 headings found: {invalid_headings[:5]}."
    return True, ""


def check_product_section_present_and_non_empty(content: str) -> tuple[bool, str]:
    """
    Verify '## Product' section is present and has at least one non-blank line.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()

    product_start = None
    product_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## Product":
            product_start = i
        elif product_start is not None and H2_PATTERN.match(stripped):
            product_end = i
            break

    if product_start is None:
        return False, "Section '## Product' not found."

    if product_end is None:
        product_end = len(lines)

    # Check for at least one non-blank line after the heading
    for i in range(product_start + 1, product_end):
        if lines[i].strip():
            return True, ""

    return False, "Section '## Product' is present but empty."


def check_requirements_section_present(content: str) -> tuple[bool, str]:
    """
    Verify '## Requirements' section heading is present in the document.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    if any(line.strip() == "## Requirements" for line in lines):
        return True, ""
    return False, "Section '## Requirements' not found."


def check_solution_section_present(content: str) -> tuple[bool, str]:
    """
    Verify '## Solution' section heading is present in the document.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    if any(line.strip() == "## Solution" for line in lines):
        return True, ""
    return False, "Section '## Solution' not found."


def check_file_structure_section_present(content: str) -> tuple[bool, str]:
    """
    Verify '## File Structure' section heading is present in the document.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    if any(line.strip() == "## File Structure" for line in lines):
        return True, ""
    return False, "Section '## File Structure' not found."


def check_product_concepts_solution_format(content: str) -> tuple[bool, str]:
    """
    Verify every bullet line in Product, Concepts, and Solution sections uses plain format.

    Plain format: '- <text>' or '- [PLANNED] <text>' with no type-letter prefix
    and no plain modality prefix.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    sections = _get_section_ranges(lines)

    invalid_lines = []
    for section_name, start, end in sections:
        if section_name not in ("Product", "Concepts", "Solution"):
            continue
        for i in range(start + 1, end):
            stripped = lines[i].strip()
            if not stripped or H3_PATTERN.match(stripped):
                continue
            if stripped.startswith("- "):
                # Allow [PLANNED]-prefixed plain bullets
                if PLANNED_PLAIN_PATTERN.match(stripped):
                    continue
                # Fail if it has a type-letter prefix (e.g., "- N: text")
                if TYPE_LETTER_PATTERN.match(stripped):
                    invalid_lines.append(f"Line {i + 1}: type-letter prefix not allowed in '{section_name}': {stripped[:80]}")
                # Fail if it has a modality prefix (e.g., "- MUST: text")
                elif MODALITY_STATEMENT_PATTERN.match(stripped):
                    invalid_lines.append(f"Line {i + 1}: modality prefix not allowed in '{section_name}': {stripped[:80]}")

    if invalid_lines:
        report = invalid_lines[:5]
        suffix = f" (and {len(invalid_lines) - 5} more)" if len(invalid_lines) > 5 else ""
        return False, f"Invalid statement lines: {report}{suffix}."
    return True, ""


def check_requirements_format(content: str) -> tuple[bool, str]:
    """
    Verify every bullet line in the Requirements section uses modality prefix format.

    Expected formats:
    - '- [MUST|MUST NOT|OPTIONAL]: <text>'
    - '- [PLANNED] [MUST|MUST NOT|OPTIONAL]: <text>'

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    sections = _get_section_ranges(lines)

    invalid_lines = []
    for section_name, start, end in sections:
        if section_name != "Requirements":
            continue
        for i in range(start + 1, end):
            stripped = lines[i].strip()
            if not stripped or H3_PATTERN.match(stripped):
                continue
            if stripped.startswith("- "):
                # Allow [PLANNED]-prefixed modality bullets
                if PLANNED_MODALITY_PATTERN.match(stripped):
                    continue
                if not MODALITY_STATEMENT_PATTERN.match(stripped):
                    invalid_lines.append(f"Line {i + 1}: missing modality prefix (MUST/MUST NOT/OPTIONAL): {stripped[:80]}")

    if invalid_lines:
        report = invalid_lines[:5]
        suffix = f" (and {len(invalid_lines) - 5} more)" if len(invalid_lines) > 5 else ""
        return False, f"Invalid Requirements lines: {report}{suffix}."
    return True, ""


def check_references_format(content: str) -> tuple[bool, str]:
    """
    Verify References section entries have required sub-structure, if the section exists.

    Each entry must have a '###' sub-heading followed within 5 lines by 'Location:' and 'Summary:'.
    If '## References' is absent, this check passes automatically.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()

    ref_start = None
    ref_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## References":
            ref_start = i
        elif ref_start is not None and H2_PATTERN.match(stripped):
            ref_end = i
            break

    # References section absent — check passes automatically
    if ref_start is None:
        return True, ""

    if ref_end is None:
        ref_end = len(lines)

    # Find all ### sub-headings in References section
    invalid_entries = []
    i = ref_start + 1
    while i < ref_end:
        stripped = lines[i].strip()
        if H3_PATTERN.match(stripped):
            # Check that Location: and Summary: appear within 5 lines
            window_end = min(i + 6, ref_end)
            window = [lines[j].strip() for j in range(i + 1, window_end)]
            has_location = any("Location:" in w for w in window)
            has_summary = any("Summary:" in w for w in window)
            if not has_location or not has_summary:
                invalid_entries.append(f"Line {i + 1}: References entry '{stripped}' missing Location: or Summary:.")
        i += 1

    if invalid_entries:
        return False, f"Malformed References entries: {invalid_entries[:3]}."
    return True, ""


def check_no_html_tables_urls(content: str) -> tuple[bool, str]:
    """
    Verify no line contains an HTML tag, a Markdown table row, or a bare URL.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    inline_code_pattern = re.compile(r"`[^`]+`")
    offending = []
    lines = content.splitlines()

    for i, line in enumerate(lines):
        cleaned = inline_code_pattern.sub("", line)
        if HTML_TAG_PATTERN.search(cleaned):
            offending.append(f"Line {i + 1}: HTML tag detected.")
        elif TABLE_PATTERN.match(line.strip()):
            offending.append(f"Line {i + 1}: Markdown table row detected.")
        elif URL_PATTERN.search(line):
            offending.append(f"Line {i + 1}: Bare URL detected.")

    if offending:
        return False, f"Formatting violations: {offending[:5]}."
    return True, ""


def check_issues_format(content: str) -> tuple[bool, str]:
    """
    Verify all entries in the Issues section are plain bullets, if the section exists.

    Each entry must match '- <description>' where description is non-empty.
    If '## Issues' is absent, this check passes automatically.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()

    issues_start = None
    issues_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## Issues":
            issues_start = i
        elif issues_start is not None and H2_PATTERN.match(stripped):
            issues_end = i
            break

    # Issues section absent — check passes automatically
    if issues_start is None:
        return True, ""

    if issues_end is None:
        issues_end = len(lines)

    invalid_lines = []
    for i in range(issues_start + 1, issues_end):
        stripped = lines[i].strip()
        if not stripped:
            continue
        if not PLAIN_STATEMENT_PATTERN.match(stripped):
            invalid_lines.append(f"Line {i + 1}: Issues entry not a plain bullet: {stripped[:80]}")

    if invalid_lines:
        return False, f"Malformed Issues entries: {invalid_lines[:5]}."
    return True, ""


def check_references_update_flag(content: str) -> tuple[bool, str]:
    """
    Verify all Update: lines in References entries have valid values (true or false).

    If no Reference entry contains an Update: line, this check passes automatically.

    Args:
        content: Full text of context.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()

    ref_start = None
    ref_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "## References":
            ref_start = i
        elif ref_start is not None and H2_PATTERN.match(stripped):
            ref_end = i
            break

    # References section absent — check passes automatically
    if ref_start is None:
        return True, ""

    if ref_end is None:
        ref_end = len(lines)

    invalid_flags = []
    for i in range(ref_start + 1, ref_end):
        stripped = lines[i].strip()
        if stripped.startswith("Update:"):
            value = stripped[len("Update:"):].strip()
            if value not in ("true", "false"):
                invalid_flags.append(f"Line {i + 1}: invalid Update: value '{value}' (must be 'true' or 'false').")

    if invalid_flags:
        return False, f"Invalid References Update: flags: {invalid_flags[:5]}."
    return True, ""


# All checks in execution order (12 checks total)
ALL_CHECKS = [
    ("check_document_title", check_document_title),
    ("check_all_h2_headings_valid", check_all_h2_headings_valid),
    ("check_product_section_present_and_non_empty", check_product_section_present_and_non_empty),
    ("check_requirements_section_present", check_requirements_section_present),
    ("check_solution_section_present", check_solution_section_present),
    ("check_file_structure_section_present", check_file_structure_section_present),
    ("check_product_concepts_solution_format", check_product_concepts_solution_format),
    ("check_requirements_format", check_requirements_format),
    ("check_references_format", check_references_format),
    ("check_no_html_tables_urls", check_no_html_tables_urls),
    ("check_issues_format", check_issues_format),
    ("check_references_update_flag", check_references_update_flag),
]


def main() -> int:
    """
    Entry point for the context.md verification tool.

    Runs all checks sequentially, prints structured results, writes
    context_verification_result to input.md YAML header, and returns
    exit code 0 if all pass or 1 if any fail. Runs 12 checks total.

    Returns:
        0 on all checks passing, 1 on any failure.
    """
    args = _parse_args()
    workspace = Path(args.workspace)

    try:
        content = _read_context(workspace)
    except FileNotFoundError:
        print("[FAIL] file_exists: .aib_memory/context.md not found.")
        print("Results: 0/1 checks passed.")
        return 1

    passed = 0
    failed = 0

    for name, check_fn in ALL_CHECKS:
        ok, message = check_fn(content)
        if ok:
            print(f"[OK] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}: {message}")
            failed += 1

    total = passed + failed
    print(f"Results: {passed}/{total} checks passed.")

    result_value = "valid" if failed == 0 else "invalid"
    _write_verification_result(workspace, "context_verification_result", result_value)

    return 0 if failed == 0 else 1


def _write_verification_result(workspace: Path, flag_key: str, result_value: str) -> None:
    """Write a verification result flag to the input.md YAML header.

    Reads the current input.md, updates the specified flag key, and writes
    the file back.  Silently skips if input.md is absent or has no valid header.

    Args:
        workspace: Workspace root path containing .aib_memory/input.md.
        flag_key: The YAML header key to set (e.g. ``"context_verification_result"``).
        result_value: The value to write; one of ``"valid"`` or ``"invalid"``.
    """
    input_path = workspace / ".aib_memory" / "input.md"
    print(f"Writing verification result '{result_value}' to {input_path} under key '{flag_key}'...")
    if not input_path.exists():
        print(f"Warning: {input_path} not found; skipping verification result write.")
        return
    content = read_text(input_path)
    header = parse_input_header(content)
    print(f"header: {header}")
    if header is None:
        print(f"Warning: {input_path} has no valid YAML header; skipping verification result write.")
        return
    header["state"][flag_key] = result_value
    write_text(input_path, write_input_header(content, header))


if __name__ == "__main__":
    sys.exit(main())
