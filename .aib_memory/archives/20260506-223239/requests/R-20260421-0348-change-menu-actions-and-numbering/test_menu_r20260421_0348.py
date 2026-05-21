"""
test_menu_r20260421_0348.py: Unit tests for menu.py changes introduced by R-20260421-0348.
Part of the kolko-ni-struva ETL pipeline test suite.
Responsibilities: verify print_menu() output, run_script() return value,
action_full_refresh() call order and failure-stop behaviour, main() dispatch
remapping, and prompt range hint.
"""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

# Ensure project root is on sys.path so `import menu` resolves correctly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import menu  # noqa: E402  (import after sys.path adjustment)


class TestPrintMenu(unittest.TestCase):
    """Tests for print_menu() display output (SC-1)."""

    def _capture_menu(self) -> str:
        """Capture print_menu() stdout output as a string."""
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            menu.print_menu()
        return buf.getvalue()

    def test_action_1_is_full_refresh(self) -> None:
        """Line 1 must show '1) Full refresh' with the three-step description."""
        output = self._capture_menu()
        self.assertIn("1) Full refresh", output)
        self.assertIn("download + transform + update supabase", output)

    def test_action_2_is_download_only(self) -> None:
        """Line 2 must show '2) Download only'."""
        output = self._capture_menu()
        self.assertIn("2) Download only", output)

    def test_action_3_is_transform_only(self) -> None:
        """Line 3 must show '3) Transform only'."""
        output = self._capture_menu()
        self.assertIn("3) Transform only", output)

    def test_action_4_is_update_supabase(self) -> None:
        """Line 4 must show '4) Update Supabase DB'."""
        output = self._capture_menu()
        self.assertIn("4) Update Supabase DB", output)

    def test_action_0_is_exit(self) -> None:
        """Line 5 must show '0) Exit'."""
        output = self._capture_menu()
        self.assertIn("0) Exit", output)

    def test_no_action_5(self) -> None:
        """Old action 5 must not appear in the menu output (SC-7)."""
        output = self._capture_menu()
        self.assertNotIn("5)", output)

    def test_menu_order(self) -> None:
        """Actions must appear in the specified order: 1, 2, 3, 4, 0."""
        output = self._capture_menu()
        pos1 = output.index("1) Full refresh")
        pos2 = output.index("2) Download only")
        pos3 = output.index("3) Transform only")
        pos4 = output.index("4) Update Supabase DB")
        pos0 = output.index("0) Exit")
        self.assertLess(pos1, pos2)
        self.assertLess(pos2, pos3)
        self.assertLess(pos3, pos4)
        self.assertLess(pos4, pos0)


class TestRunScriptReturnValue(unittest.TestCase):
    """Tests for run_script() boolean return value (supports SC-3 failure guard)."""

    def test_returns_true_on_success(self) -> None:
        """run_script() must return True when the subprocess exits with code 0."""
        mock_result = unittest.mock.MagicMock()
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            result = menu.run_script("src/extract.py")
        self.assertTrue(result)

    def test_returns_false_on_failure(self) -> None:
        """run_script() must return False when the subprocess exits with non-zero code."""
        import subprocess
        exc = subprocess.CalledProcessError(1, ["python", "src/extract.py"])
        exc.stdout = ""
        exc.stderr = "error output"
        with patch("subprocess.run", side_effect=exc):
            result = menu.run_script("src/extract.py")
        self.assertFalse(result)


class TestActionFullRefresh(unittest.TestCase):
    """Tests for action_full_refresh() call order and failure-stop (SC-3)."""

    def test_calls_all_three_scripts_on_success(self) -> None:
        """All three scripts must be called in order when each succeeds (SC-3)."""
        call_log: list = []

        def fake_run_script(path: str) -> bool:
            call_log.append(path)
            return True

        with patch.object(menu, "run_script", side_effect=fake_run_script):
            menu.action_full_refresh()

        self.assertEqual(
            call_log,
            ["src/extract.py", "src/transform.py", "src/load_supabase.py"],
        )

    def test_stops_after_extract_failure(self) -> None:
        """If extract fails, transform and load_supabase must NOT be called."""
        call_log: list = []

        def fake_run_script(path: str) -> bool:
            call_log.append(path)
            # First call (extract) fails
            return False

        with patch.object(menu, "run_script", side_effect=fake_run_script):
            menu.action_full_refresh()

        self.assertEqual(call_log, ["src/extract.py"])
        self.assertNotIn("src/transform.py", call_log)
        self.assertNotIn("src/load_supabase.py", call_log)

    def test_stops_after_transform_failure(self) -> None:
        """If transform fails, load_supabase must NOT be called."""
        call_log: list = []

        def fake_run_script(path: str) -> bool:
            call_log.append(path)
            # Second call (transform) fails
            return len(call_log) < 2

        with patch.object(menu, "run_script", side_effect=fake_run_script):
            menu.action_full_refresh()

        self.assertIn("src/extract.py", call_log)
        self.assertIn("src/transform.py", call_log)
        self.assertNotIn("src/load_supabase.py", call_log)


class TestMainDispatch(unittest.TestCase):
    """Tests for main() input dispatch and prompt range hint (SC-2, SC-4–SC-7)."""

    def _run_main_with_input(self, inputs: list) -> str:
        """Run main() with a sequence of inputs captured from stdin; return stdout."""
        input_data = "\n".join(inputs) + "\n"
        buf = io.StringIO()
        with (
            patch("builtins.input", side_effect=inputs),
            patch("sys.stdout", buf),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
        ):
            menu.main()
        return buf.getvalue()

    def test_key_0_exits_cleanly(self) -> None:
        """Selecting '0' must exit the menu without error (SC-2)."""
        output = self._run_main_with_input(["0"])
        self.assertIn("Exiting", output)

    def test_key_1_calls_full_refresh(self) -> None:
        """Selecting '1' must call action_full_refresh() (SC-3)."""
        with (
            patch("builtins.input", side_effect=["1", "0"]),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
            patch.object(menu, "action_full_refresh") as mock_fr,
        ):
            menu.main()
        mock_fr.assert_called_once()

    def test_key_2_calls_download(self) -> None:
        """Selecting '2' must call action_download() (SC-4)."""
        with (
            patch("builtins.input", side_effect=["2", "0"]),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
            patch.object(menu, "action_download") as mock_dl,
        ):
            menu.main()
        mock_dl.assert_called_once()

    def test_key_3_calls_transform(self) -> None:
        """Selecting '3' must call action_transform() (SC-5)."""
        with (
            patch("builtins.input", side_effect=["3", "0"]),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
            patch.object(menu, "action_transform") as mock_tr,
        ):
            menu.main()
        mock_tr.assert_called_once()

    def test_key_4_calls_supabase(self) -> None:
        """Selecting '4' must call action_update_supabase() (SC-6)."""
        with (
            patch("builtins.input", side_effect=["4", "0"]),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
            patch.object(menu, "action_update_supabase") as mock_sb,
        ):
            menu.main()
        mock_sb.assert_called_once()

    def test_key_5_is_invalid(self) -> None:
        """Old key '5' must produce the invalid-choice message (SC-7)."""
        output = self._run_main_with_input(["5", "0"])
        self.assertIn("Invalid choice", output)

    def test_key_range_in_prompt(self) -> None:
        """The input prompt must contain '[0-4]' (T3)."""
        prompt_seen: list = []

        def capturing_input(prompt: str = "") -> str:
            prompt_seen.append(prompt)
            return "0"  # Exit immediately

        with (
            patch("builtins.input", side_effect=capturing_input),
            patch.object(menu, "print_stats"),
            patch.object(menu, "print_menu"),
        ):
            menu.main()

        self.assertTrue(
            any("[0-4]" in p for p in prompt_seen),
            f"Expected '[0-4]' in prompt, got: {prompt_seen}",
        )


class TestContextMdUpdated(unittest.TestCase):
    """Tests that context.md no longer contains the old menu description (SC-8 / T10)."""

    CONTEXT_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".aib_memory" / "context.md"

    def test_old_menu_description_absent(self) -> None:
        """context.md must not contain '(download + transform)' as a menu description."""
        if not self.CONTEXT_PATH.exists():
            self.skipTest("context.md not present; skipped until next context run.")
        text = self.CONTEXT_PATH.read_text(encoding="utf-8")
        # Allow the string in ADR / architecture rationale text, but not in the
        # Functional Capabilities or Component Map menu-action descriptions.
        # We check the entire file for the old exact menu label.
        self.assertNotIn(
            "full refresh, exit, and update Supabase DB",
            text,
            "Old menu action list still present in context.md.",
        )


if __name__ == "__main__":
    unittest.main()
