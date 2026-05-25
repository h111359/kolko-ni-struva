"""
test_menu.py: Unit tests for menu.py actions and helper functions.
Part of the kolko-ni-struva ETL pipeline (request R-20260426-2150).
Responsibilities: verify action_local_preview() call order and credential
validation, stats helpers, read_state, main loop dispatch, and
publishable-key prefix format security check.
"""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path so the root module can be imported
# without an installation step.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import menu  # noqa: E402


# ---------------------------------------------------------------------------
# Credential validation tests (T1 — missing credentials cause early return)
# ---------------------------------------------------------------------------

class TestActionLocalPreviewCredentials(unittest.TestCase):
    """Tests for the VITE_ credential validation guard in action_local_preview()."""

    def test_missing_both_credentials_returns_early(self) -> None:
        """action_local_preview() prints an error and returns without running npm when both VITE_ vars are empty."""
        with patch.dict("os.environ", {"VITE_SUPABASE_URL": "", "VITE_SUPABASE_PUBLISHABLE_KEY": ""}):
            with patch("menu.load_dotenv"):
                with patch("menu.subprocess.run") as mock_run:
                    with patch("menu.subprocess.Popen") as mock_popen:
                        captured = io.StringIO()
                        with patch("sys.stdout", captured):
                            menu.action_local_preview()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()
        self.assertIn("ERROR", captured.getvalue())

    def test_missing_url_prints_variable_name(self) -> None:
        """Error output names VITE_SUPABASE_URL when only that variable is absent."""
        with patch.dict("os.environ", {"VITE_SUPABASE_URL": "", "VITE_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_testkey"}):
            with patch("menu.load_dotenv"):
                with patch("menu.subprocess.run"):
                    captured = io.StringIO()
                    with patch("sys.stdout", captured):
                        menu.action_local_preview()
        self.assertIn("VITE_SUPABASE_URL", captured.getvalue())

    def test_missing_key_prints_variable_name(self) -> None:
        """Error output names VITE_SUPABASE_PUBLISHABLE_KEY when only that variable is absent."""
        with patch.dict("os.environ", {"VITE_SUPABASE_URL": "https://x.supabase.co", "VITE_SUPABASE_PUBLISHABLE_KEY": ""}):
            with patch("menu.load_dotenv"):
                with patch("menu.subprocess.run"):
                    captured = io.StringIO()
                    with patch("sys.stdout", captured):
                        menu.action_local_preview()
        self.assertIn("VITE_SUPABASE_PUBLISHABLE_KEY", captured.getvalue())


# ---------------------------------------------------------------------------
# Call-order tests (T2 — build before preview; T3 — server start before browser)
# ---------------------------------------------------------------------------

class TestActionLocalPreviewCallOrder(unittest.TestCase):
    """Tests asserting the correct sequential ordering of operations in action_local_preview()."""

    # Valid VITE_ credentials used for all call-order tests.
    _VALID_ENV = {
        "VITE_SUPABASE_URL": "https://x.supabase.co",
        "VITE_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_testkey",
    }

    def _run_and_collect_order(
        self,
        run_side_effect=None,
        wait_server_result: bool = True,
    ) -> list:
        """
        Execute action_local_preview() with mocked subprocess and browser calls,
        collecting events in the order they occur.

        Args:
            run_side_effect: Optional side_effect for subprocess.run (the build step).
            wait_server_result: Return value for the mocked _wait_for_server helper.

        Returns:
            Ordered list of event tuples: ('run', cmd), ('popen', cmd), ('browser', url).
        """
        call_log: list = []

        def tracking_run(*args, **kwargs):
            # Record the build step; args[0] is the command list.
            call_log.append(("run", list(args[0]) if args else []))
            if run_side_effect is not None:
                raise run_side_effect
            return MagicMock()

        mock_proc = MagicMock()
        mock_proc.wait.return_value = None

        def tracking_popen(*args, **kwargs):
            call_log.append(("popen", list(args[0]) if args else []))
            return mock_proc

        def tracking_browser(url: str) -> None:
            call_log.append(("browser", url))

        with patch.dict("os.environ", self._VALID_ENV):
            with patch("menu.load_dotenv"):
                with patch("menu.subprocess.run", side_effect=tracking_run):
                    with patch("menu.subprocess.Popen", side_effect=tracking_popen):
                        with patch("menu._wait_for_server", return_value=wait_server_result):
                            with patch("menu.webbrowser.open", side_effect=tracking_browser):
                                with patch("sys.stdout", io.StringIO()):
                                    menu.action_local_preview()
        return call_log

    def test_build_called_before_preview_server_starts(self) -> None:
        """subprocess.run (npm build) event precedes subprocess.Popen (preview server) event."""
        call_log = self._run_and_collect_order()
        event_types = [e[0] for e in call_log]
        self.assertIn("run", event_types, "Expected a subprocess.run call (build step)")
        self.assertIn("popen", event_types, "Expected a subprocess.Popen call (preview server)")
        # Build must appear before the server start.
        self.assertLess(
            event_types.index("run"),
            event_types.index("popen"),
            "npm run build must be invoked before npm run preview",
        )

    def test_browser_opened_after_preview_server_starts(self) -> None:
        """webbrowser.open() event follows subprocess.Popen (server start) — not before."""
        call_log = self._run_and_collect_order(wait_server_result=True)
        event_types = [e[0] for e in call_log]
        self.assertIn("popen", event_types)
        self.assertIn("browser", event_types)
        # Browser MUST open only after the server process has been started.
        self.assertLess(
            event_types.index("popen"),
            event_types.index("browser"),
            "webbrowser.open() must be called after the preview server Popen, not before",
        )

    def test_browser_not_opened_when_server_does_not_become_ready(self) -> None:
        """webbrowser.open() is NOT called when _wait_for_server returns False (timeout)."""
        call_log = self._run_and_collect_order(wait_server_result=False)
        event_types = [e[0] for e in call_log]
        self.assertNotIn("browser", event_types)

    def test_build_failure_prevents_preview_server_start(self) -> None:
        """subprocess.Popen is not called when npm run build exits non-zero."""
        import subprocess as _sp

        call_log = self._run_and_collect_order(
            run_side_effect=_sp.CalledProcessError(1, ["npm", "run", "build"])
        )
        event_types = [e[0] for e in call_log]
        self.assertNotIn("popen", event_types)

    def test_npm_not_found_prevents_preview_server_start(self) -> None:
        """subprocess.Popen is not called when npm is not found during the build step."""
        call_log = self._run_and_collect_order(run_side_effect=FileNotFoundError())
        event_types = [e[0] for e in call_log]
        self.assertNotIn("popen", event_types)

    def test_npm_not_found_prints_error_message(self) -> None:
        """An actionable error message mentioning npm is printed when npm is absent."""
        with patch.dict("os.environ", self._VALID_ENV):
            with patch("menu.load_dotenv"):
                with patch("menu.subprocess.run", side_effect=FileNotFoundError()):
                    captured = io.StringIO()
                    with patch("sys.stdout", captured):
                        menu.action_local_preview()
        self.assertIn("npm", captured.getvalue())


# ---------------------------------------------------------------------------
# Stats helper tests (T6)
# ---------------------------------------------------------------------------

class TestCountZips(unittest.TestCase):
    """Tests for count_zips() — counting ZIP archives in the raw data directory."""

    def test_returns_zero_for_nonexistent_directory(self) -> None:
        """count_zips returns 0 when the directory does not exist."""
        self.assertEqual(menu.count_zips(Path("/nonexistent_path_xyz")), 0)

    def test_returns_zero_for_empty_directory(self) -> None:
        """count_zips returns 0 for a directory that contains no ZIP files."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(menu.count_zips(Path(tmp)), 0)

    def test_counts_only_zip_files(self) -> None:
        """count_zips counts only .zip files and ignores files with other extensions."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "2026-04-01.zip").write_bytes(b"")
            (p / "2026-04-02.zip").write_bytes(b"")
            (p / "readme.txt").write_bytes(b"")
            self.assertEqual(menu.count_zips(p), 2)


class TestZipDateRange(unittest.TestCase):
    """Tests for zip_date_range() — extracting the earliest and latest ZIP date stems."""

    def test_returns_dash_dash_for_empty_directory(self) -> None:
        """zip_date_range returns ('—', '—') when no ZIP files are present."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(menu.zip_date_range(Path(tmp)), ("\u2014", "\u2014"))

    def test_returns_correct_min_max_stems(self) -> None:
        """zip_date_range returns (earliest, latest) date stems from ZIP filenames."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "2026-04-01.zip").write_bytes(b"")
            (p / "2026-04-05.zip").write_bytes(b"")
            (p / "2026-04-03.zip").write_bytes(b"")
            self.assertEqual(menu.zip_date_range(p), ("2026-04-01", "2026-04-05"))


class TestCountFactFiles(unittest.TestCase):
    """Tests for count_fact_files() — counting processed fact CSV files."""

    def test_returns_zero_for_nonexistent_directory(self) -> None:
        """count_fact_files returns 0 when the directory does not exist."""
        self.assertEqual(menu.count_fact_files(Path("/nonexistent_xyz")), 0)

    def test_counts_csv_files(self) -> None:
        """count_fact_files returns the number of .csv files in the directory."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "2026-04-01.csv").write_bytes(b"")
            (p / "2026-04-02.csv").write_bytes(b"")
            self.assertEqual(menu.count_fact_files(p), 2)


class TestSchemaFreshness(unittest.TestCase):
    """Tests for schema_freshness() — identifying the newest fact CSV date."""

    def test_returns_not_built_for_empty_directory(self) -> None:
        """schema_freshness returns 'not built' when no CSV files exist."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(menu.schema_freshness(Path(tmp)), "not built")

    def test_returns_latest_date_stem(self) -> None:
        """schema_freshness returns the stem of the chronologically newest CSV."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "2026-04-01.csv").write_bytes(b"")
            (p / "2026-04-10.csv").write_bytes(b"")
            (p / "2026-04-05.csv").write_bytes(b"")
            self.assertEqual(menu.schema_freshness(p), "2026-04-10")


# ---------------------------------------------------------------------------
# read_state tests (T7)
# ---------------------------------------------------------------------------

class TestReadState(unittest.TestCase):
    """Tests for read_state() — reading ETL checkpoint dates from config.ini."""

    def test_returns_empty_strings_when_file_missing(self) -> None:
        """read_state returns ('', '') when the config file does not exist."""
        self.assertEqual(
            menu.read_state(Path("/nonexistent_config.ini")), ("", "")
        )

    def test_reads_both_state_keys(self) -> None:
        """read_state returns both last_downloaded_date and last_processed_date from [state]."""
        content = (
            "[state]\n"
            "last_downloaded_date = 2026-04-25\n"
            "last_processed_date = 2026-04-24\n"
        )
        with tempfile.NamedTemporaryFile(
            suffix=".ini", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            tmp_path = Path(fh.name)
        try:
            result = menu.read_state(tmp_path)
        finally:
            tmp_path.unlink()
        self.assertEqual(result, ("2026-04-25", "2026-04-24"))

    def test_returns_empty_when_state_section_absent(self) -> None:
        """read_state returns ('', '') when the [state] section is not present in the file."""
        content = "[settings]\nopendata_url = https://example.com\n"
        with tempfile.NamedTemporaryFile(
            suffix=".ini", mode="w", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(content)
            tmp_path = Path(fh.name)
        try:
            result = menu.read_state(tmp_path)
        finally:
            tmp_path.unlink()
        self.assertEqual(result, ("", ""))


# ---------------------------------------------------------------------------
# Main loop dispatch tests (T8)
# ---------------------------------------------------------------------------

class TestMainLoopDispatch(unittest.TestCase):
    """Tests for the main() input loop — verifies that each choice dispatches correctly."""

    def test_all_choices_dispatched_then_exit(self) -> None:
        """main() dispatches choices 1–6 to their action functions, then exits cleanly on 0."""
        inputs = iter(["1", "2", "3", "4", "5", "6", "0"])
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", io.StringIO()):
                with patch.object(menu, "print_stats"):
                    with patch.object(menu, "print_menu"):
                        with patch.object(menu, "action_full_refresh") as m1:
                            with patch.object(menu, "action_download") as m2:
                                with patch.object(menu, "action_transform") as m3:
                                    with patch.object(menu, "action_update_supabase") as m4:
                                        with patch.object(menu, "action_deploy_netlify") as m5:
                                            with patch.object(menu, "action_local_preview") as m6:
                                                menu.main()
        m1.assert_called_once()
        m2.assert_called_once()
        m3.assert_called_once()
        m4.assert_called_once()
        m5.assert_called_once()
        m6.assert_called_once()

    def test_invalid_choice_prints_error(self) -> None:
        """An invalid choice prints an error message containing the valid range."""
        inputs = iter(["9", "0"])
        captured = io.StringIO()
        with patch("builtins.input", side_effect=inputs):
            with patch("sys.stdout", captured):
                with patch.object(menu, "print_stats"):
                    with patch.object(menu, "print_menu"):
                        menu.main()
        # The error message must reference the allowed range (includes 6).
        self.assertIn("6", captured.getvalue())


# ---------------------------------------------------------------------------
# Security check: VITE_SUPABASE_PUBLISHABLE_KEY must use sb_publishable_ prefix (T12)
# ---------------------------------------------------------------------------

class TestVitePublishableKeyFormat(unittest.TestCase):
    """
    Security configuration check: VITE_SUPABASE_PUBLISHABLE_KEY must use the
    sb_publishable_... prefix.

    A secret key (sb_secret_...) in the React bundle bypasses all Supabase
    Row Level Security policies, exposing the entire database to unrestricted
    public access.
    """

    def test_vite_publishable_key_has_correct_prefix(self) -> None:
        """
        VITE_SUPABASE_PUBLISHABLE_KEY must start with 'sb_publishable_'.

        Skips when .env is absent or the key is not set under the new name.
        Fails with a security message when the key starts with 'sb_secret_'.
        """
        env_path = _PROJECT_ROOT / ".env"
        if not env_path.exists():
            self.skipTest(".env file not found; skipping publishable key validation")

        key: str | None = None
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("VITE_SUPABASE_PUBLISHABLE_KEY="):
                    key = stripped.split("=", 1)[1].strip()
                    break

        if not key:
            self.skipTest(
                "VITE_SUPABASE_PUBLISHABLE_KEY is not set in root .env; "
                "skipping publishable key validation"
            )

        # A secret key in the browser bundle bypasses all RLS — hard fail.
        if key.startswith("sb_secret_"):
            self.fail(
                "SECURITY: VITE_SUPABASE_PUBLISHABLE_KEY is a secret key "
                "(sb_secret_...). Replace with an sb_publishable_... key from "
                "the Supabase dashboard (Settings -> API -> Publishable key)."
            )

        if key.startswith("sb_publishable_"):
            # Correct format — test passes.
            return

        # Unrecognised format: skip gracefully during migration.
        self.skipTest(
            f"VITE_SUPABASE_PUBLISHABLE_KEY has unrecognised format "
            f"'{key[:20]}...'; skipping prefix validation during migration"
        )


if __name__ == "__main__":
    unittest.main()
