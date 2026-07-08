"""
verify-input.py: Validate .aib_memory/input.md against input-convention.md rules.
Part of the AIB tools suite.
Responsibilities: Run structural and format checks on input.md YAML header, body sections,
and Q-block format; write input_verification_result to input.md YAML header;
exit with code 0 if all pass or 1 if any fail.
"""

import argparse
import re
import sys
from pathlib import Path

from common import parse_input_header, read_text, write_input_header, write_text

# Required top-level YAML group keys (the two nested blocks).
REQUIRED_YAML_KEYS = (
    "state",
    "options",
)

# Valid values for the state field.
VALID_STATES = {"idle", "analysis_ready", "questions_generated"}

# Valid values for result flags (None maps to null in YAML).
VALID_RESULT_VALUES = {None, "valid", "invalid"}

# Allowed H2 section headings in the body.
ALLOWED_H2_SECTIONS = {"## Input", "## Options", "## Questions"}

# Pattern for a QID line: **Q001**: ...
QID_LINE_PATTERN = re.compile(r"^\*\*Q\d{3}\*\*:")

# Pattern for H2 headings.
H2_PATTERN = re.compile(r"^## ")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed namespace with workspace path.
    """
    parser = argparse.ArgumentParser(
        description="Validate .aib_memory/input.md against input-convention.md rules."
    )
    parser.add_argument(
        "--workspace", default=".", help="Workspace root path (default: current directory)"
    )
    return parser.parse_args()


def _read_input(workspace: Path) -> str:
    """Read input.md from the workspace.

    Args:
        workspace: Path to workspace root.

    Returns:
        Full text content of input.md.

    Raises:
        FileNotFoundError: If input.md does not exist.
    """
    input_path = workspace / ".aib_memory" / "input.md"
    if not input_path.exists():
        raise FileNotFoundError(f".aib_memory/input.md not found in {workspace}")
    return input_path.read_text(encoding="utf-8")


def _extract_raw_yaml_keys(content: str) -> set[str]:
    """Extract top-level YAML key names from the frontmatter block.

    Parses only top-level keys (no leading spaces) within the YAML
    frontmatter delimited by ``---``.

    Args:
        content: Full text of input.md.

    Returns:
        Set of top-level key names found in the frontmatter.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    keys: set[str] = set()
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            break
        # Only match top-level keys (no leading whitespace).
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):", line)
        if m:
            keys.add(m.group(1))
    return keys


def _extract_nested_keys(content: str, group_key: str) -> set[str]:
    """Extract sub-key names from a named nested YAML block within the frontmatter.

    Scans the frontmatter for a top-level ``group_key:`` line and collects
    all indented sub-key names beneath it until the next non-indented line or
    the closing ``---`` delimiter.

    Args:
        content: Full text of input.md.
        group_key: Top-level group name to look for (e.g. ``"state"``).

    Returns:
        Set of sub-key names found within the named group block.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()
    keys: set[str] = set()
    in_group = False
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            break
        # Detect the target top-level group key (no leading whitespace).
        if line.rstrip() == f"{group_key}:":
            in_group = True
            continue
        if in_group:
            # Exit the group when a non-indented line is encountered.
            if line and not line[0].isspace():
                in_group = False
                continue
            m = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):", line)
            if m:
                keys.add(m.group(1))
    return keys


def _get_body_lines(content: str) -> list[str]:
    """Return lines of input.md after the closing YAML frontmatter delimiter.

    Args:
        content: Full text of input.md.

    Returns:
        List of body lines (empty list when no closing delimiter is found).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return lines  # No frontmatter — entire content is body.
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[i + 1:]
    return []


def _extract_questions_section(body_lines: list[str]) -> list[str]:
    """Extract lines from the ## Questions section of the body.

    Args:
        body_lines: Body lines of input.md (after frontmatter).

    Returns:
        Lines within ## Questions, or empty list when section absent.
    """
    inside = False
    collected: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if stripped == "## Questions":
            inside = True
            continue
        if inside:
            if H2_PATTERN.match(stripped):
                break
            collected.append(line)
    return collected


def _split_qblocks(questions_lines: list[str]) -> list[list[str]]:
    """Split questions section lines into individual Q-block line groups.

    A new Q-block starts at any line matching the QID pattern ``**Q###**:``.

    Args:
        questions_lines: Lines inside ## Questions section.

    Returns:
        List of Q-block line groups, each being a list of lines.
    """
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in questions_lines:
        if QID_LINE_PATTERN.match(line.strip()):
            if current:
                blocks.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


# ---------------------------------------------------------------------------
# Check functions — each returns (passed: bool, message: str)
# ---------------------------------------------------------------------------

def check_frontmatter_present(content: str) -> tuple[bool, str]:
    """Verify the file starts with a YAML frontmatter block delimited by ---.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return False, (
            "input.md must start with '---' (YAML frontmatter delimiter). "
            "Ensure the file begins with a valid YAML frontmatter block."
        )
    # Also verify the closing delimiter exists.
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return True, ""
    return False, (
        "YAML frontmatter block is not closed. "
        "Add a closing '---' line after the YAML key-value pairs."
    )


def check_required_yaml_keys_present(content: str) -> tuple[bool, str]:
    """Verify the two required top-level YAML group keys and all their sub-keys are present.

    Checks that ``state:`` and ``options:`` top-level groups exist, then
    verifies each group contains its required sub-keys.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    present = _extract_raw_yaml_keys(content)
    # Check for the two required top-level group keys.
    missing_top = [k for k in REQUIRED_YAML_KEYS if k not in present]
    if missing_top:
        return False, (
            f"Missing required top-level YAML groups: {missing_top}. "
            f"Required top-level keys are: {list(REQUIRED_YAML_KEYS)}."
        )

    # Check sub-keys within the state: block.
    state_subkeys = _extract_nested_keys(content, "state")
    required_state_subkeys = (
        "request_id", "title", "status",
        "input_verification_result", "context_verification_result",
    )
    missing_state = [k for k in required_state_subkeys if k not in state_subkeys]
    if missing_state:
        return False, (
            f"Missing required sub-keys in state: block: {missing_state}. "
            f"Required state sub-keys are: {list(required_state_subkeys)}."
        )

    # Check sub-keys within the options: block.
    options_subkeys = _extract_nested_keys(content, "options")
    required_options_subkeys = (
        "minimum_questions", "input_verification_enabled", "context_verification_enabled",
    )
    missing_options = [k for k in required_options_subkeys if k not in options_subkeys]
    if missing_options:
        return False, (
            f"Missing required sub-keys in options: block: {missing_options}. "
            f"Required options sub-keys are: {list(required_options_subkeys)}."
        )

    return True, ""


def check_state_value_valid(content: str) -> tuple[bool, str]:
    """Verify the state.status sub-field contains one of the allowed values.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    try:
        header = parse_input_header(content)
    except ValueError as exc:
        return False, f"Cannot parse YAML header (old flat format detected): {exc}"
    if header is None:
        return False, "Cannot parse YAML header; run check_frontmatter_present first."
    # status is a sub-field within the state: nested block.
    status = header.get("state", {}).get("status", "")
    if status not in VALID_STATES:
        return False, (
            f"state.status value '{status}' is invalid. "
            f"state.status must be one of: {', '.join(sorted(VALID_STATES))}."
        )
    return True, ""


def check_minimum_questions_non_negative(content: str) -> tuple[bool, str]:
    """Verify options.minimum_questions is a non-negative integer.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    # Find the closing --- to limit scan to frontmatter only.
    end_idx = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
    if end_idx == -1:
        # No valid frontmatter; skip this check (will fail frontmatter check).
        return True, ""

    in_options = False
    for line in lines[1:end_idx]:
        if line.rstrip() == "options:":
            in_options = True
            continue
        if in_options:
            m = re.match(r"^\s+minimum_questions:\s*(\S+)", line)
            if m:
                raw = m.group(1)
                try:
                    val = int(raw)
                    if val < 0:
                        return False, (
                            f"options.minimum_questions must be a non-negative integer, got: {raw}."
                        )
                    return True, ""
                except ValueError:
                    return False, (
                        f"options.minimum_questions must be an integer, got: {raw!r}."
                    )
            # options block present but no minimum_questions key found.
            if not line.strip().startswith(" ") and not line.strip().startswith("\t"):
                break
    return True, ""


def check_enabled_flags_are_boolean(content: str) -> tuple[bool, str]:
    """Verify input_verification_enabled and context_verification_enabled are booleans.

    Scans within the ``options:`` nested block for these flags.
    Acceptable YAML boolean values: ``true`` or ``false``.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    end_idx = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
    if end_idx == -1:
        return True, ""

    bool_keys = {"input_verification_enabled", "context_verification_enabled"}
    invalid: list[str] = []
    # Scan only within the options: nested block.
    in_options_block = False
    for line in lines[1:end_idx]:
        if line.rstrip() == "options:":
            in_options_block = True
            continue
        if in_options_block:
            # Exit the options block when a non-indented line is encountered.
            if line and not line[0].isspace():
                in_options_block = False
                continue
            m = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):\s*(\S*)", line)
            if m and m.group(1) in bool_keys:
                val = m.group(2).strip()
                if val not in ("true", "false"):
                    invalid.append(f"{m.group(1)}: got '{val}', expected 'true' or 'false'")
    if invalid:
        return False, (
            f"Enabled flags must be boolean (true/false): {invalid}."
        )
    return True, ""


def check_result_flags_valid(content: str) -> tuple[bool, str]:
    """Verify input_verification_result and context_verification_result have valid values.

    Scans within the ``state:`` nested block for these flags.
    Acceptable values: ``null``, ``valid``, or ``invalid``.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    lines = content.splitlines()
    end_idx = -1
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
    if end_idx == -1:
        return True, ""

    result_keys = {"input_verification_result", "context_verification_result"}
    valid_values = {"null", "valid", "invalid"}
    invalid: list[str] = []
    # Scan only within the state: nested block.
    in_state_block = False
    for line in lines[1:end_idx]:
        if line.rstrip() == "state:":
            in_state_block = True
            continue
        if in_state_block:
            # Exit the state block when a non-indented line is encountered.
            if line and not line[0].isspace():
                in_state_block = False
                continue
            m = re.match(r"^\s+([a-zA-Z_][a-zA-Z0-9_]*):\s*(\S*)", line)
            if m and m.group(1) in result_keys:
                val = m.group(2).strip()
                if val not in valid_values:
                    invalid.append(
                        f"{m.group(1)}: got '{val}', expected one of: {', '.join(sorted(valid_values))}"
                    )
    if invalid:
        return False, (
            f"Result flags must be null/valid/invalid: {invalid}."
        )
    return True, ""


def check_allowed_h2_sections_only(content: str) -> tuple[bool, str]:
    """Verify only allowed H2 sections appear in the body.

    Allowed sections: ``## Input``, ``## Options``, ``## Questions``.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    body_lines = _get_body_lines(content)
    disallowed: list[str] = []
    for line in body_lines:
        stripped = line.strip()
        if H2_PATTERN.match(stripped) and stripped not in ALLOWED_H2_SECTIONS:
            disallowed.append(stripped)
    if disallowed:
        return False, (
            f"Disallowed H2 sections found: {disallowed}. "
            f"Only these sections are permitted: {sorted(ALLOWED_H2_SECTIONS)}."
        )
    return True, ""


def check_input_section_present(content: str) -> tuple[bool, str]:
    """Verify ## Input section is present in the body.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    body_lines = _get_body_lines(content)
    if any(line.strip() == "## Input" for line in body_lines):
        return True, ""
    return False, (
        "'## Input' section is missing from input.md body. "
        "Add a '## Input' section heading to the file body."
    )


def check_questions_section_present_when_required(content: str) -> tuple[bool, str]:
    """Verify ## Questions section is present when state.status is questions_generated.

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    try:
        header = parse_input_header(content)
    except ValueError:
        return True, ""  # Skip; frontmatter/state check will report the issue.
    if header is None:
        return True, ""  # Skip; frontmatter check will report the issue.
    if header.get("state", {}).get("status") != "questions_generated":
        return True, ""
    body_lines = _get_body_lines(content)
    if any(line.strip() == "## Questions" for line in body_lines):
        return True, ""
    return False, (
        "state is 'questions_generated' but '## Questions' section is missing. "
        "Add a '## Questions' section containing the generated Q-blocks."
    )


def check_qblock_format(content: str) -> tuple[bool, str]:
    """Verify each Q-block in ## Questions conforms to the q-block-convention format.

    Each Q-block must have:
    - A QID line matching ``**Q###**:``
    - A ``> **Why this matters:**`` line
    - At least one checkbox line ``- [ ]`` or ``- [x]``, OR a ``- Answer:`` line
    - A ``- [ ] Other:`` line (for multiple-choice) or ``- Answer:`` line (for free-text)

    Args:
        content: Full text of input.md.

    Returns:
        Tuple of (passed, message).
    """
    body_lines = _get_body_lines(content)
    questions_lines = _extract_questions_section(body_lines)
    if not questions_lines:
        return True, ""  # No questions section or empty section — skip.

    blocks = _split_qblocks(questions_lines)
    if not blocks:
        return True, ""

    violations: list[str] = []
    for block in blocks:
        # Identify the QID for error messages.
        qid_line = block[0].strip() if block else "(unknown)"
        qid_match = QID_LINE_PATTERN.match(qid_line)
        qid_label = qid_match.group(0).rstrip(":") if qid_match else qid_line[:20]

        block_text = "\n".join(line.strip() for line in block)

        # Check for Why-this-matters line.
        if "> **Why this matters:**" not in block_text:
            violations.append(
                f"{qid_label}: missing '> **Why this matters:**' line. "
                "Expected format: '> **Why this matters:** <one-sentence impact>'"
            )

        has_checkbox = any(
            line.strip().startswith("- [ ]") or line.strip().startswith("- [x]")
            for line in block
        )
        has_answer_line = any(line.strip().startswith("- Answer:") for line in block)

        if not has_checkbox and not has_answer_line:
            violations.append(
                f"{qid_label}: missing answer options. "
                "Multiple-choice Q-blocks need '- [ ] Option:' lines; "
                "free-text Q-blocks need a '- Answer: ___' line."
            )

        # For multiple-choice blocks, verify Other: option is present.
        if has_checkbox:
            has_other = any("Other:" in line for line in block)
            if not has_other:
                violations.append(
                    f"{qid_label}: multiple-choice Q-block is missing the '- [ ] Other: ___' option."
                )

    if violations:
        report = violations[:5]
        suffix = f" (and {len(violations) - 5} more)" if len(violations) > 5 else ""
        return False, f"Q-block format violations: {report}{suffix}."
    return True, ""


# All checks in execution order.
ALL_CHECKS = [
    ("check_frontmatter_present", check_frontmatter_present),
    ("check_required_yaml_keys_present", check_required_yaml_keys_present),
    ("check_state_value_valid", check_state_value_valid),
    ("check_minimum_questions_non_negative", check_minimum_questions_non_negative),
    ("check_enabled_flags_are_boolean", check_enabled_flags_are_boolean),
    ("check_result_flags_valid", check_result_flags_valid),
    ("check_allowed_h2_sections_only", check_allowed_h2_sections_only),
    ("check_input_section_present", check_input_section_present),
    ("check_questions_section_present_when_required", check_questions_section_present_when_required),
    ("check_qblock_format", check_qblock_format),
]


def main() -> int:
    """Entry point for the input.md verification tool.

    Runs all checks sequentially, prints structured results, writes
    input_verification_result to input.md YAML header, and returns
    exit code 0 if all pass or 1 if any fail.

    Returns:
        0 on all checks passing, 1 on any failure.
    """
    args = _parse_args()
    workspace = Path(args.workspace)

    try:
        content = _read_input(workspace)
    except FileNotFoundError as exc:
        print(f"[FAIL] file_exists: {exc}")
        print("Results: 0/1 checks passed.")
        return 1

    passed = 0
    failed = 0

    for name, check_fn in ALL_CHECKS:
        ok, message = check_fn(content)
        if ok:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name} — {message}")
            failed += 1

    total = passed + failed
    print(f"Results: {passed}/{total} checks passed.")

    result_value = "valid" if failed == 0 else "invalid"
    _write_verification_result(workspace, result_value)

    return 0 if failed == 0 else 1


def _write_verification_result(workspace: Path, result_value: str) -> None:
    """Write input_verification_result to the input.md YAML header.

    Reads the current input.md, updates ``state.input_verification_result``,
    and writes the file back.  Silently skips if input.md is absent, has no
    valid YAML header, or uses the old flat format.

    Args:
        workspace: Workspace root path containing .aib_memory/input.md.
        result_value: ``"valid"`` or ``"invalid"``.
    """
    input_path = workspace / ".aib_memory" / "input.md"
    if not input_path.exists():
        print(f"Warning: {input_path} not found; cannot write input_verification_result.")
        return
    content = read_text(input_path)
    try:
        header = parse_input_header(content)
    except ValueError:
        print(f"Warning: {input_path} has no valid YAML header; cannot write input_verification_result.")
        return
    if header is None:
        print(f"Warning: {input_path} has no valid YAML header; cannot write input_verification_result.")
        return
    header["state"]["input_verification_result"] = result_value
    write_text(input_path, write_input_header(content, header))


if __name__ == "__main__":
    sys.exit(main())
