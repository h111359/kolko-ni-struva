"""
test_config_utils.py: Unit tests for the config_utils module.
Part of the kolko-ni-struva ETL pipeline (request R-20260419-0854).
Responsibilities: verify bootstrap, re-read-before-write, and atomic-rename
behaviour of load_config() and save_state().
"""
import configparser
import sys
import tempfile
import unittest
from pathlib import Path

# Add src/ to path so the module resolves without installing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from config_utils import load_config, save_state  # noqa: E402


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config() bootstrap and idempotency."""

    def test_creates_config_when_absent(self) -> None:
        """load_config writes a new file with both sections when none exists."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            self.assertFalse(path.exists())
            cfg = load_config(path)
            self.assertTrue(path.exists())
            self.assertTrue(cfg.has_section("settings"))
            self.assertTrue(cfg.has_section("state"))

    def test_defaults_present(self) -> None:
        """Bootstrapped config contains expected default keys."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            cfg = load_config(path)
            self.assertIn("opendata_url", cfg["settings"])
            self.assertIn("max_retries", cfg["settings"])
            self.assertIn("last_downloaded_date", cfg["state"])
            self.assertIn("last_processed_date", cfg["state"])

    def test_idempotent_when_file_exists(self) -> None:
        """load_config does not overwrite existing values on re-reads."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            cfg1 = load_config(path)
            cfg1.set("state", "last_downloaded_date", "2026-04-18")
            from config_utils import _write_atomic
            _write_atomic(cfg1, path)
            cfg2 = load_config(path)
            self.assertEqual(cfg2.get("state", "last_downloaded_date"), "2026-04-18")

    def test_adds_missing_section(self) -> None:
        """load_config adds [state] if the file only has [settings]."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            existing = configparser.ConfigParser()
            existing.add_section("settings")
            existing.set("settings", "log_level", "DEBUG")
            with open(path, "w", encoding="utf-8") as fh:
                existing.write(fh)
            cfg = load_config(path)
            self.assertTrue(cfg.has_section("state"))
            # Existing key must be preserved.
            self.assertEqual(cfg.get("settings", "log_level"), "DEBUG")


class TestSaveState(unittest.TestCase):
    """Tests for save_state() re-read-before-write and atomic rename."""

    def test_writes_key(self) -> None:
        """save_state persists a single key to disk."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            load_config(path)
            save_state(path, last_processed_date="2026-04-18")
            cfg = configparser.ConfigParser()
            cfg.read(path, encoding="utf-8")
            self.assertEqual(cfg.get("state", "last_processed_date"), "2026-04-18")

    def test_preserves_sibling_keys(self) -> None:
        """save_state does not overwrite keys written by another script."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            load_config(path)
            # Simulate extract.py writing last_downloaded_date.
            save_state(path, last_downloaded_date="2026-04-18")
            # Simulate transform.py writing last_processed_date.
            save_state(path, last_processed_date="2026-04-17")
            cfg = configparser.ConfigParser()
            cfg.read(path, encoding="utf-8")
            # Both keys must coexist.
            self.assertEqual(cfg.get("state", "last_downloaded_date"), "2026-04-18")
            self.assertEqual(cfg.get("state", "last_processed_date"), "2026-04-17")

    def test_no_partial_file_left(self) -> None:
        """save_state leaves no .partial file after a successful write."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            load_config(path)
            save_state(path, last_downloaded_date="2026-04-18")
            partial = path.with_suffix(path.suffix + ".partial")
            self.assertFalse(partial.exists())

    def test_uses_replace_not_rename(self) -> None:
        """Atomic write uses Path.replace() semantics (overwrites destination)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.ini"
            load_config(path)
            # Write once, then write again — Path.rename() would raise on
            # Windows if the destination exists; Path.replace() must not raise.
            save_state(path, last_downloaded_date="2026-04-17")
            save_state(path, last_downloaded_date="2026-04-18")
            cfg = configparser.ConfigParser()
            cfg.read(path, encoding="utf-8")
            self.assertEqual(cfg.get("state", "last_downloaded_date"), "2026-04-18")


if __name__ == "__main__":
    unittest.main()
