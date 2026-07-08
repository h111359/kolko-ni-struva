#!/usr/bin/env python3
"""Interactive launcher for AIB tool scripts."""

from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import artifact_name, get_semver, get_setup_option, set_setup_option, parse_input_header, read_text, slugify

# Auto-refresh interval used by choose_action() when no key is pressed.
_REFRESH_TIMEOUT_S: float = 3.0

# Hard-coded list of developer-facing menu actions.  Only scripts that are
# genuinely useful to the developer from the menu surface are included here.
# close-request.py is conditionally injected by filter_visible_actions when
# an active request exists; it is NOT listed here.
_SCRIPT_ACTIONS: list[dict[str, Any]] = [
    {
        "id": "1",
        "title": "Create Clarify Context",
        "description": "Generate context compilation file for aib-clarify.md.",
        "script": "create-clarify-context.py",
        "destructive": False,
        "parameters": [],
    },
]

# Guidance messages for each detected workspace state.  Two-element lists
# produce a two-line guidance block; single-element lists produce one line.
_GUIDANCE_MESSAGES: dict[str, list[str]] = {
    "idle": [
        "No task in progress. Add your description to `.aib_memory/input.md`,"
        " then execute: Execute `.aib_brain/prompts/aib-analyze.md`",
        "Tip: Place supporting files in `.aib_memory/attachments/` to include extra context.",
    ],
    "input_ready": [
        "Input ready. Execute analysis to create a request:"
        " Execute `.aib_brain/prompts/aib-analyze.md`",
        "Or go straight to implement — analysis runs automatically:"
        " Execute `.aib_brain/prompts/aib-implement.md`",
    ],
    "request_incomplete": [
        "Request active — no analysis yet. Run:"
        " Execute `.aib_brain/prompts/aib-analyze.md`",
    ],
    "questions_pending": [
        "Questions pending in input.md. Answer them then re-run:"
        " Execute `.aib_brain/prompts/aib-analyze.md`",
        "Or run implement directly — recommended options will be applied automatically:"
        " Execute `.aib_brain/prompts/aib-implement.md`",
    ],
    "implementation_ready": [
        "Request analysed and ready. Run:"
        " Execute `.aib_brain/prompts/aib-implement.md`",
        "To amend: write changes to `.aib_memory/input.md` then re-run:"
        " Execute `.aib_brain/prompts/aib-analyze.md`",
        "Tip: Place supporting files in `.aib_memory/attachments/` to include extra context.",
    ],
    "amendment_pending": [
        "Amendments pending in input.md. Re-run analysis to incorporate changes:"
        " Execute `.aib_brain/prompts/aib-analyze.md`",
    ],
    "unknown": [
        "\u26a0 Workspace state could not be determined."
        " Check `.aib_memory/` for inconsistencies.",
    ],
}

# Conditional action for closing the active request; injected by
# filter_visible_actions only when state.has_active_request is True.
_CLOSE_REQUEST_ACTION: dict[str, Any] = {
    "id": "close",
    "title": "Close current request",
    "description": "Close the active request and mark it as Closed in the register.",
    "script": "close-request.py",
    "destructive": False,
    "parameters": [
        {"name": "workspace", "flag": "--workspace", "type": "path", "required": True, "default": ".", "prompt": "Workspace path", "hint": "Root folder containing .aib_brain"},
    ],
}



def _enable_ansi_windows() -> None:
    """Enable ANSI/VT escape sequence processing on Windows consoles.

    Uses the Windows Console API via ctypes to set ENABLE_VIRTUAL_TERMINAL_PROCESSING
    on the standard output handle. Must be called once at startup before any ANSI
    escape sequences are written to stdout. On non-Windows platforms this is a no-op.
    Failures (e.g., restricted ctypes access or legacy console) are silently ignored
    so the program continues with gracefully degraded terminal output.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        import ctypes.wintypes

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.wintypes.DWORD()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:  # noqa: BLE001
        # Graceful degradation: ANSI sequences may appear as literal text on
        # unsupported consoles; blink elimination goal is not met in that case.
        pass


def _sanitize_action_id(raw: str) -> str:
    """Return a filesystem-safe action identifier from *raw*."""
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in raw.lower()).strip("-")[:60]


def _stream_pipe(pipe, dest, prefix, lock):
    """Read *pipe* line-by-line, writing each line to *dest* for live terminal streaming."""
    try:
        for raw_line in iter(pipe.readline, ""):
            line = raw_line.rstrip("\n").rstrip("\r")
            with lock:
                dest.write(line + "\n")
                dest.flush()
    except Exception:  # noqa: BLE001 — swallow thread errors silently; live stream is best-effort
        pass
    finally:
        pipe.close()


def _run_and_tee(
    command: list[str],
    title: str,
    inherit_stdin: bool = False,
) -> int:
    """Run *command* while streaming stdout/stderr live to the terminal.

    Returns the subprocess exit code.
    """
    lock = threading.Lock()

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=None if inherit_stdin else subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout_thread = threading.Thread(
        target=_stream_pipe,
        args=(proc.stdout, sys.stdout, "[OUT]", lock),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_pipe,
        args=(proc.stderr, sys.stderr, "[ERR]", lock),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    proc.wait()
    stdout_thread.join()
    stderr_thread.join()

    return proc.returncode


def clear_screen() -> None:
    """Clear the terminal using ANSI escape sequences to avoid blank-screen blink.

    Writes cursor-home (ESC[H) followed by erase-to-end-of-screen (ESC[J) directly
    to stdout, avoiding subprocess spawning and the associated blank-window flash.
    The function name and signature are preserved for backward compatibility.
    """
    sys.stdout.write("\033[H\033[J")
    sys.stdout.flush()


def ascii_banner() -> str:
    return "\n".join(
        [
            r"   ___    ___    ____   _   _   ___   _      ____    _____   ____    ",
            r"  / _ \  |_ _|  | __ ) | | | | |_ _| | |    |  _ \  | ____| |  _ \   ",
            r" / /_\ \  | |   |  _ \ | |_| |  | |  | |__  | |_| | |  _|   | |_) |  ",
            r"/_/   \_\|___|  |____/  \___/  |___| |____| |____/  |_____| |_| \_\  ",
            "",
        ]
    )


@dataclass(frozen=True)
class MenuState:
    active_request_id: str | None
    active_request_folder: str | None
    active_request_title: str | None = None

    @property
    def has_active_request(self) -> bool:
        return bool(self.active_request_id)


def resolve_menu_state(workspace: Path) -> MenuState:
    """Resolve the active request state from the input.md YAML frontmatter header.

    Args:
        workspace: The workspace root path.

    Returns:
        MenuState populated from the YAML header, or a MenuState with all None
        fields if the header is absent or state is idle.
    """
    input_path = workspace / ".aib_memory" / "input.md"
    if not input_path.exists():
        return MenuState(None, None, None)

    header = parse_input_header(read_text(input_path))
    if header is None or header["state"]["status"] == "idle":
        return MenuState(None, None, None)

    request_id = header.get("state", {}).get("request_id", "").strip() or None
    title = header.get("state", {}).get("title", "").strip() or None
    if not request_id or request_id == "~":
        return MenuState(None, None, None)

    # Derive folder path using the same slugify convention as create-request.py.
    folder_rel = None
    if request_id and title and title != "~":
        folder_name = f"{request_id}-{slugify(title)}"
        folder_rel = f".aib_memory/requests/{folder_name}"

    return MenuState(request_id, folder_rel, title if title != "~" else None)


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AIB interactive command menu")
    parser.add_argument("--workspace", default=".", help="Workspace root path")
    return parser.parse_args()


def build_script_actions(tools_dir: Path) -> list[dict[str, Any]]:
    """Return the hard-coded list of developer-facing menu actions.

    The ``tools_dir`` parameter is accepted for API compatibility but is no
    longer used now that actions are fully enumerated by ``_SCRIPT_ACTIONS``
    rather than discovered dynamically from the filesystem.

    Args:
        tools_dir: Path to the tools directory (unused; kept for compatibility).

    Returns:
        A fresh copy of ``_SCRIPT_ACTIONS`` with sequentially renumbered IDs.
    """
    actions = [dict(a) for a in _SCRIPT_ACTIONS]
    for idx, action in enumerate(actions, start=1):
        action["id"] = str(idx)
    return actions


def filter_visible_actions(
    actions: list[dict[str, Any]],
    state: MenuState,
    workspace: Path | None = None,
) -> list[dict[str, Any]]:
    """Return visible actions, filtering by enabled flags and appending close-request when active.

    The close-request action is injected at the end of the visible list when
    ``state.has_active_request`` is ``True``.

    Args:
        actions: Full list of script actions (from build_script_actions).
        state: Current resolved menu state.
        workspace: Optional workspace root path; accepted for API compatibility.

    Returns:
        Filtered and optionally extended list of visible actions.
    """
    visible: list[dict[str, Any]] = list(actions)

    if state.has_active_request:
        # Append a copy so the module-level constant is not mutated.
        close_action = dict(_CLOSE_REQUEST_ACTION)
        close_action["id"] = str(len(visible) + 1)
        visible.append(close_action)
    return visible


def ensure_memory_initialized_if_missing(workspace: Path, python_exe: str, tools_dir: Path) -> None:
    memory_root = workspace / ".aib_memory"
    if memory_root.exists():
        return

    init_script = (tools_dir / "initialize.py").resolve()
    result = subprocess.run(
        [python_exe, str(init_script), "--workspace", str(workspace)],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        summary = (stderr or stdout).splitlines()[0] if (stderr or stdout) else "Initialization failed"
        raise SystemExit(f"ERROR: Auto-initialization failed: {summary}")


def get_key(timeout: float | None = None) -> str:
    """Read a single keypress from the terminal and return a normalised key name.

    Args:
        timeout: Maximum seconds to wait for a keypress. When ``None`` the
            function blocks until a key is pressed. When a float is supplied
            the function returns ``"TIMEOUT"`` if no key arrives within that
            many seconds.

    Returns:
        A normalised key name: ``"UP"``, ``"DOWN"``, ``"ENTER"``, ``"QUIT"``,
        ``"DIGIT:<n>"``, ``"TIMEOUT"`` (only when *timeout* is set and the
        deadline expires), or ``"OTHER"`` for any unrecognised key.
    """
    if os.name == "nt":
        import msvcrt

        if timeout is None:
            # Blocking: wait indefinitely for the next keypress.
            first = msvcrt.getwch()
        else:
            # Polling loop: check for available input every 50 ms until deadline.
            deadline = time.monotonic() + timeout
            while not msvcrt.kbhit():
                if time.monotonic() >= deadline:
                    return "TIMEOUT"
                time.sleep(0.05)
            first = msvcrt.getwch()

        if first in ("\x00", "\xe0"):
            second = msvcrt.getwch()
            if second == "H":
                return "UP"
            if second == "P":
                return "DOWN"
            return "OTHER"
        if first in ("\r", "\n"):
            return "ENTER"
        if first in ("q", "Q"):
            return "QUIT"
        if first.isdigit():
            return f"DIGIT:{first}"
        return "OTHER"

    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    if timeout is not None:
        # Check whether input is ready before entering raw mode; avoids blocking.
        import select

        readable, _, _ = select.select([sys.stdin], [], [], timeout)
        if not readable:
            return "TIMEOUT"

    try:
        tty.setraw(fd)
        ch1 = sys.stdin.read(1)
        if ch1 == "\x1b":
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            if ch2 == "[" and ch3 == "A":
                return "UP"
            if ch2 == "[" and ch3 == "B":
                return "DOWN"
            return "OTHER"
        if ch1 in ("\r", "\n"):
            return "ENTER"
        if ch1 in ("q", "Q"):
            return "QUIT"
        if ch1.isdigit():
            return f"DIGIT:{ch1}"
        return "OTHER"
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def prompt_yes_no(question: str, default_yes: bool = False) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    while True:
        answer = input(f"{question} {suffix}: ").strip().lower()
        if not answer:
            return default_yes
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please type y or n.")


def validate_param(raw_value: str, schema: dict[str, Any]) -> tuple[bool, str]:
    param_type = str(schema.get("type", "string")).lower()
    required = bool(schema.get("required", False))

    value = raw_value.strip()
    if required and not value:
        return False, "This field is required."

    if not value:
        return True, ""

    if param_type == "int":
        try:
            int(value)
        except ValueError:
            return False, "Expected an integer value."

    if param_type == "choice":
        choices = [str(c) for c in schema.get("choices", [])]
        if choices and value not in choices:
            return False, f"Expected one of: {', '.join(choices)}"

    return True, ""


def collect_parameters(action: dict[str, Any], workspace_default: str) -> dict[str, str]:
    print("\nParameter input")
    print("---------------")
    values: dict[str, str] = {}

    for param in action.get("parameters", []):
        name = str(param.get("name", "")).strip()
        if not name:
            continue

        prompt = str(param.get("prompt", name))
        hint = str(param.get("hint", "")).strip()
        required = bool(param.get("required", False))

        default_value = param.get("default")
        if name == "workspace" and (default_value is None or str(default_value).strip() == "."):
            default_value = workspace_default

        if name == "workspace":
            values[name] = str(default_value) if default_value not in (None, "") else workspace_default
            continue

        if name in {"request_id"} and not required:
            if default_value not in (None, ""):
                values[name] = str(default_value)
            continue

        while True:
            label = prompt
            if default_value not in (None, ""):
                label += f" [{default_value}]"
            label += ": "

            if hint:
                print(f"Hint: {hint}")
            raw = input(label).strip()
            value = raw if raw else ("" if default_value is None else str(default_value))

            ok, reason = validate_param(value, param)
            if not ok:
                print(f"Invalid value: {reason}")
                continue

            if value:
                values[name] = value
            elif required:
                print("Invalid value: This field is required.")
                continue
            break

    return values


def build_command(python_exe: str, tools_dir: Path, action: dict[str, Any], values: dict[str, str]) -> list[str]:
    script_name = str(action.get("script", "")).strip()
    command = [python_exe, str((tools_dir / script_name).resolve())]

    for param in action.get("parameters", []):
        name = str(param.get("name", "")).strip()
        flag = str(param.get("flag", "")).strip()
        if not name or not flag:
            continue

        if name not in values:
            continue

        command.extend([flag, values[name]])

    return command


def run_action(python_exe: str, tools_dir: Path, action: dict[str, Any], workspace_default: str) -> None:
    clear_screen()
    title = str(action.get("title", action.get("script", "Action")))
    print(ascii_banner())
    print(f"Selected: {title}")
    print(str(action.get("description", "")))

    values = collect_parameters(action, workspace_default)

    command = build_command(python_exe, tools_dir, action, values)

    print(f"\n\u25b6 Running {title}... (output appears below)\n")

    exit_code = _run_and_tee(command, title, inherit_stdin=False)

    if exit_code == 0:
        print(f"\nStatus: Success")
    else:
        print(f"\nStatus: Failed (exit code {exit_code})")
    input("Press Enter to return to menu...")


def _extract_section(text: str, section_title: str) -> str:
    """Extract the body of a Markdown section identified by its H2 heading.

    Searches for a line equal to ``## <section_title>`` and returns the text
    between that heading line and the next ``##``-level heading (or EOF),
    stripped of leading/trailing whitespace.

    Args:
        text: Full Markdown document text to search.
        section_title: Section title without the ``## `` prefix.

    Returns:
        The section body stripped of surrounding whitespace, or an empty
        string when the section heading is not found.
    """
    lines = text.splitlines()
    header = f"## {section_title}"
    inside = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == header:
            inside = True
            continue
        if inside:
            if line.startswith("## "):
                break
            collected.append(line)
    return "\n".join(collected).strip()


def _is_context_empty(workspace: Path) -> bool:
    """Return True when .aib_memory/context.md is absent or contains only whitespace.

    Args:
        workspace: Resolved workspace root path.

    Returns:
        True if context.md does not exist or is blank; False otherwise.
    """
    context_path = workspace / ".aib_memory" / "context.md"
    if not context_path.exists():
        return True
    return not context_path.read_text(encoding="utf-8").strip()


def _detect_guidance_state(state: MenuState, workspace: Path) -> str:
    """Detect the developer's next-action state from workspace artifacts.

    Evaluates states in the following priority order:

    1. No active request — inspect ``input.md ## Input``; empty → ``"idle"``;
       non-empty → ``"input_ready"``.
    2. Active request, ``input.md ## Questions`` non-empty → ``"questions_pending"``
       (highest-priority active-request check, evaluated before plan.md presence).
    3. Active request, ``plan-<ID>.md`` absent → ``"request_incomplete"``.
    4. Active request, ``plan-<ID>.md`` present, ``## Input`` non-empty →
       ``"amendment_pending"``.
    5. Otherwise → ``"implementation_ready"``.

    Any unhandled exception during detection returns ``"unknown"`` without
    propagating the exception.

    Args:
        state: Current MenuState describing whether an active request exists.
        workspace: Resolved workspace root path.

    Returns:
        One of: ``"idle"``, ``"input_ready"``, ``"request_incomplete"``,
        ``"questions_pending"``, ``"implementation_ready"``,
        ``"amendment_pending"``, or ``"unknown"``.
    """
    try:
        input_path = workspace / ".aib_memory" / "input.md"
        input_text = input_path.read_text(encoding="utf-8") if input_path.exists() else ""

        if not state.has_active_request:
            input_body = _extract_section(input_text, "Input")
            return "input_ready" if input_body else "idle"

        # Active-request branch — check questions first (priority over request-<ID>.md).
        questions_body = _extract_section(input_text, "Questions")
        if questions_body:
            return "questions_pending"

        # Look for the ID-suffixed active-phase request artifact.
        req_filename = artifact_name("plan", state.active_request_id)
        plan_md_path = workspace / ".aib_memory" / req_filename
        if not plan_md_path.exists():
            return "request_incomplete"

        input_body = _extract_section(input_text, "Input")
        return "amendment_pending" if input_body else "implementation_ready"

    except Exception:  # noqa: BLE001
        return "unknown"


def render_menu(
    state: MenuState,
    script_actions: list[dict[str, Any]],
    selected_index: int,
    workspace: Path,
) -> None:
    """Render the interactive menu with active-request status and state-aware guidance.

    Accumulates the entire menu string into an in-memory buffer and flushes it to
    stdout in a single write, minimising the blank-window between clear and redraw.
    No print() or clear_screen() calls are made inside this function.

    Args:
        state: Current resolved menu state (active request info).
        script_actions: Visible action list to render with numeric shortcuts.
        selected_index: Zero-based index of the currently highlighted action.
        workspace: Resolved workspace root path used for guidance-state detection.
    """
    buf = io.StringIO()

    # Move cursor to top-left and erase to end of screen (blink-free clear).
    buf.write("\033[H\033[J")

    buf.write(ascii_banner() + "\n")

    req_id = state.active_request_id or "No active request"
    req_title = state.active_request_title
    if state.active_request_id and req_title:
        req_text = f"{req_id} — {req_title}"
    else:
        req_text = req_id
    buf.write(f"Active request: {req_text}\n")

    # State-aware guidance block — displayed before the numbered options list
    # so the recommended next step is visible immediately after the status line.
    buf.write("\n")
    buf.write("  \u2500\u2500 Next Step \u2500\u2500\n")
    guidance_state = _detect_guidance_state(state, workspace)
    guidance_lines = _GUIDANCE_MESSAGES.get(guidance_state, _GUIDANCE_MESSAGES["unknown"])
    for line in guidance_lines:
        buf.write(f"  {line}\n")

    # Additional line when context.md is absent or empty (orthogonal to state).
    if _is_context_empty(workspace):
        buf.write(
            "  Context file is empty \u2014 context gathering will execute automatically before analysis."
            " Execute `.aib_brain/prompts/aib-analyze.md` to begin.\n"
        )

    # Blank separator between guidance block and numbered options.
    buf.write("\n")
    for idx, action in enumerate(script_actions, start=1):
        marker = ">" if idx - 1 == selected_index else " "
        number = str(idx)
        line = f"{marker} {number}) {action.get('title', 'Untitled action')}"
        description = str(action.get("description", "")).strip()
        if description:
            line += f" - {description}"
        buf.write(line + "\n")

    # Fixed quit footer — non-navigable; displayed below all numbered items.
    buf.write("  0) Quit\n")

    # Erase any stale content remaining below the rendered menu (handles menu shrinkage).
    buf.write("\033[J")

    sys.stdout.write(buf.getvalue())
    sys.stdout.flush()


def choose_action(tools_dir: Path, workspace: Path) -> dict[str, Any] | None:
    all_script_actions = build_script_actions(tools_dir)

    selected = 0

    while True:
        state = resolve_menu_state(workspace)
        script_actions = filter_visible_actions(all_script_actions, state, workspace)
        total_items = len(script_actions)
        render_menu(state, script_actions, selected, workspace)
        key = get_key(timeout=_REFRESH_TIMEOUT_S)

        if key == "TIMEOUT":
            # No keypress within the idle window; re-render to pick up state changes.
            continue
        if key == "QUIT":
            # q/Q pressed; signal the caller to exit the menu loop.
            return None
        if key == "DIGIT:0":
            # 0 pressed; same exit intent as q/Q.
            return None
        if key == "UP":
            if total_items > 0:
                selected = (selected - 1) % total_items
            continue
        if key == "DOWN":
            if total_items > 0:
                selected = (selected + 1) % total_items
            continue
        if key == "ENTER":
            if selected < len(script_actions):
                action = script_actions[selected]
                return action
        if key.startswith("DIGIT:"):
            digit = key.split(":", 1)[1]
            numeric = int(digit)
            if 1 <= numeric <= len(script_actions):
                action = script_actions[numeric - 1]
                return action


def check_version_compatibility(workspace: Path, python_exe: str, tools_dir: Path) -> bool:
    """Check whether .aib_brain/ and .aib_memory/ versions match.

    Reads the brain version from the ``vMAJOR.MINOR.PATCH`` marker file in
    ``.aib_brain/`` and the memory version from the ``memory_version`` key in
    ``.aib_memory/aib-setup.yaml``.  When a mismatch (or missing memory version)
    is detected, an upgrade prompt is shown. The user can choose to upgrade or
    skip. If the user upgrades, ``initialize.py --upgrade`` is invoked and this
    function returns True so the caller continues to the normal menu without
    requiring a relaunch.  When the upgrade fails, the function returns False so
    the caller exits.  When the user skips, or when versions are in sync, returns True.

    Args:
        workspace: Resolved workspace root path.
        python_exe: Path to the Python interpreter.
        tools_dir: Path to the .aib_brain/tools/ directory.

    Returns:
        True when the caller should continue to the normal menu; False when
        the caller should exit (upgrade failed or user chose to exit).
    """
    brain_dir = workspace / ".aib_brain"
    memory_dir = workspace / ".aib_memory"

    brain_semver = get_semver(brain_dir)
    # Read memory version from aib-setup.yaml rather than a v*.*.* empty marker file.
    memory_semver = get_setup_option(memory_dir, "memory_version")

    # Unknown brain version: cannot compare; warn but do not block.
    if brain_semver is None:
        print("WARNING: No semver marker found in .aib_brain/; version check skipped.")
        return True

    # Versions match — no prompt needed.
    if brain_semver == memory_semver:
        return True

    # Display a version mismatch banner.
    brain_label = brain_semver
    memory_label = memory_semver or "unknown (no marker)"
    print("\n" + "=" * 60)
    print("  AIB VERSION MISMATCH DETECTED")
    print(f"  .aib_brain/  version : {brain_label}")
    print(f"  .aib_memory/ version : {memory_label}")
    print("=" * 60)
    print(
        "\n  Your .aib_memory/ was created with a different AIB version.\n"
        "  Upgrading will archive the current .aib_memory/ and re-seed\n"
        "  it from the new brain assets while preserving your curated\n"
        "  files (context.md, instructions.md, and optionally requests/).\n"
    )

    # Present options and loop until a valid choice is made.
    while True:
        print("  [1] Upgrade .aib_memory/ now  (recommended)")
        print("  [2] Skip for this session")
        choice = input("\n  Enter choice [1/2]: ").strip()
        if choice == "1":
            init_script = (tools_dir / "initialize.py").resolve()
            result = subprocess.run(
                [python_exe, str(init_script), "--workspace", str(workspace), "--upgrade"],
                # Inherit stdin/stdout so the upgrade output is visible.
                stdin=None,
                text=True,
            )
            if result.returncode != 0:
                print("\nERROR: Upgrade failed. Re-launch menu to try again.")
                return False
            else:
                print("\nUpgrade complete. Continuing to menu...")
                return True
        if choice == "2":
            print("  Skipping upgrade for this session.\n")
            return True
        print("  Invalid choice — please enter 1 or 2.")


def _show_migration_completion_screen(workspace: Path) -> bool:
    """Display the migration-completion screen and block until the user confirms or exits.

    Returns True when the developer confirms migration is complete (sets
    memory_version_compatibility to compatible), False when they choose to exit.
    """
    memory_dir = workspace / ".aib_memory"
    clear_screen()
    sys.stdout.write(ascii_banner())
    sys.stdout.flush()
    print("  -- Migration Completion Required --")
    print()
    print("  The AIB memory upgrade is complete, but migration instructions still need to be executed. input.md is prepared with the instructions needed.")
    print("  Run `Execute .aib_brain/prompts/aib-modify.md` in chat it to reconstruct context.md from the archived legacy memory.")
    print("  Do not proceed until the migration prompt has completed successfully.")
    print()
    print("  [1] Confirm Completed  \u2014 migration prompt has been executed successfully")
    print("  [2] Exit")
    while True:
        choice = input("  Enter choice [1/2]: ").strip()
        if choice == "1":
            set_setup_option(memory_dir, "memory_version_compatibility", "compatible")
            print("  Migration confirmed. Continuing to menu...")
            return True
        if choice == "2":
            return False
        print("  Invalid choice \u2014 please enter 1 or 2.")


def main() -> None:
    """Main entry point: parse arguments, ensure memory is initialized, then run the menu.

    Performs a version-compatibility check before showing the interactive menu.
    When .aib_brain/ and .aib_memory/ semver markers differ, the user is
    offered an upgrade option before the menu is shown.
    """
    args = parse_cli_args()
    workspace = Path(args.workspace).resolve()

    tools_dir = Path(__file__).resolve().parent
    python_exe = sys.executable

    ensure_memory_initialized_if_missing(workspace, python_exe, tools_dir)

    # Version-compatibility check: prompt for upgrade if semver markers differ.
    should_continue = check_version_compatibility(workspace, python_exe, tools_dir)
    if not should_continue:
        # Upgrade failed; exit so the user can retry after resolving the issue.
        return

    compat_state = get_setup_option(workspace / ".aib_memory", "memory_version_compatibility")
    if compat_state == "initialized-not-populated":
        if not _show_migration_completion_screen(workspace):
            return

    # Enable ANSI VT processing on Windows once before the first render.
    _enable_ansi_windows()

    try:
        while True:
            action = choose_action(tools_dir, workspace)
            if action is None:
                # None signals a quit intent (q/Q/0); exit the menu loop cleanly.
                break
            run_action(python_exe, tools_dir, action, str(workspace))
    except KeyboardInterrupt:
        # Ctrl+C pressed during menu navigation or key polling; exit cleanly.
        sys.stdout.write("\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
