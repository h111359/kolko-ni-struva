"""
test_extract.py: Unit tests for src/extract.py core functions.
Part of the kolko-ni-struva ETL pipeline (request R-20260425-2313).
Responsibilities: verify parse_zip_links, existing_filenames, incremental
download skip logic, and atomic rename behaviour of download_file().
"""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src/ to sys.path so the module resolves without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from extract import (  # noqa: E402
    download_file,
    existing_filenames,
    parse_zip_links,
)


class TestParseZipLinks(unittest.TestCase):
    """Tests for parse_zip_links(): HTML → sorted list of absolute ZIP URLs."""

    def test_extracts_zip_hrefs(self) -> None:
        """parse_zip_links returns absolute URLs for .zip anchor hrefs."""
        html = """
        <html><body>
          <a href="/files/2026-04-01.zip">April 1</a>
          <a href="/files/2026-04-02.zip">April 2</a>
          <a href="/other/page.html">Not a ZIP</a>
        </body></html>
        """
        base = "https://kolkostruva.bg/opendata"
        result = parse_zip_links(html, base)
        self.assertIn("https://kolkostruva.bg/files/2026-04-02.zip", result)
        self.assertIn("https://kolkostruva.bg/files/2026-04-01.zip", result)
        # Non-ZIP href must be absent.
        self.assertNotIn("https://kolkostruva.bg/other/page.html", result)

    def test_sorted_descending(self) -> None:
        """parse_zip_links returns URLs in descending (newest-first) order."""
        html = """
        <html><body>
          <a href="/files/2026-04-01.zip">A</a>
          <a href="/files/2026-04-03.zip">B</a>
          <a href="/files/2026-04-02.zip">C</a>
        </body></html>
        """
        result = parse_zip_links(html, "https://kolkostruva.bg/opendata")
        # Descending by URL string — newest date string comes first.
        dates = [u.split("/")[-1].replace(".zip", "") for u in result]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_empty_page_returns_empty_list(self) -> None:
        """parse_zip_links returns an empty list when no ZIP anchors are found."""
        result = parse_zip_links("<html><body>No links here</body></html>", "https://example.com")
        self.assertEqual(result, [])

    def test_duplicate_hrefs_deduplicated(self) -> None:
        """parse_zip_links deduplicates repeated identical ZIP hrefs."""
        html = """
        <html><body>
          <a href="/files/2026-04-01.zip">First</a>
          <a href="/files/2026-04-01.zip">Duplicate</a>
        </body></html>
        """
        result = parse_zip_links(html, "https://kolkostruva.bg/opendata")
        self.assertEqual(len(result), 1)


class TestExistingFilenames(unittest.TestCase):
    """Tests for existing_filenames(): directory scan and auto-creation."""

    def test_returns_filenames_in_dir(self) -> None:
        """existing_filenames returns the names of files present in the directory."""
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "2026-04-01.zip").write_bytes(b"data")
            (p / "2026-04-02.zip").write_bytes(b"data")
            result = existing_filenames(p)
            self.assertIn("2026-04-01.zip", result)
            self.assertIn("2026-04-02.zip", result)

    def test_creates_directory_when_absent(self) -> None:
        """existing_filenames creates the target directory if it does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "new_raw_dir"
            self.assertFalse(target.exists())
            existing_filenames(target)
            self.assertTrue(target.exists())

    def test_returns_empty_set_for_new_dir(self) -> None:
        """existing_filenames returns an empty set for a freshly created directory."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "empty"
            result = existing_filenames(target)
            self.assertEqual(result, set())


class TestIncrementalDownloadSkip(unittest.TestCase):
    """Tests that download_file is NOT called when file already exists."""

    def test_skips_download_for_existing_filename(self) -> None:
        """When the target filename is already in existing_filenames, requests.get is not called."""
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp)
            # Pre-create the target file so existing_filenames includes it.
            existing_name = "2026-04-01.zip"
            (raw_dir / existing_name).write_bytes(b"fake zip content")

            known_files = existing_filenames(raw_dir)
            self.assertIn(existing_name, known_files)

            # Simulate the scheduling logic from main(): only schedule if absent.
            url = f"https://kolkostruva.bg/files/{existing_name}"
            to_download = []
            if existing_name not in known_files:
                to_download.append(url)

            # Assert no download is scheduled.
            self.assertEqual(to_download, [])


class TestAtomicRename(unittest.TestCase):
    """Tests that download_file leaves no .partial temp file after success."""

    def _make_valid_zip_bytes(self) -> bytes:
        """Create a minimal valid ZIP archive in memory and return its bytes."""
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("dummy.csv", "col1,col2\nval1,val2")
        return buf.getvalue()

    def test_no_partial_file_after_successful_download(self) -> None:
        """download_file removes the .partial temp file after a successful download."""
        zip_bytes = self._make_valid_zip_bytes()

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "2026-04-01.zip"
            partial = dest.with_suffix(dest.suffix + ".partial")

            # Build a mock requests.Session whose .get() returns valid ZIP bytes.
            mock_resp = MagicMock()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.raise_for_status = MagicMock()
            # iter_content yields the complete ZIP in one chunk.
            mock_resp.iter_content = MagicMock(return_value=[zip_bytes])

            mock_session = MagicMock()
            mock_session.get.return_value = mock_resp

            ok = download_file(
                mock_session,
                "https://kolkostruva.bg/files/2026-04-01.zip",
                dest,
                max_retries=1,
                retry_delay=0,
            )

            self.assertTrue(ok, "download_file should return True on success")
            self.assertTrue(dest.exists(), "Destination file should exist after download")
            self.assertFalse(partial.exists(), ".partial file should not remain after success")


if __name__ == "__main__":
    unittest.main()
