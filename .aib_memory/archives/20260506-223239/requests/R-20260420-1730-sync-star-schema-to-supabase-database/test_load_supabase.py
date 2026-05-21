"""
test_load_supabase.py: Unit tests for src/load_supabase.py.
Part of the kolko-ni-struva ETL pipeline (request R-20260420-1730).
Responsibilities: verify get_latest_local_date, _coerce, and main() error
paths (missing DATABASE_URL, connection failure) without a live database.
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Ensure src/ is on the path so load_supabase resolves without installation.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "src"))

from load_supabase import _coerce, get_latest_local_date  # noqa: E402


class TestCoerce(unittest.TestCase):
    """Tests for the _coerce() helper."""

    def test_empty_string_returns_none(self) -> None:
        """Empty CSV cell must become None for nullable DB columns."""
        self.assertIsNone(_coerce(""))

    def test_whitespace_only_returns_none(self) -> None:
        """Whitespace-only cell must become None."""
        self.assertIsNone(_coerce("   "))

    def test_non_empty_string_preserved(self) -> None:
        """Non-empty strings must pass through unchanged."""
        self.assertEqual(_coerce("abc"), "abc")

    def test_numeric_string_preserved(self) -> None:
        """Numeric strings must pass through as strings."""
        self.assertEqual(_coerce("42"), "42")


class TestGetLatestLocalDate(unittest.TestCase):
    """Tests for get_latest_local_date()."""

    def test_returns_none_when_directory_absent(self) -> None:
        """Must return None for a non-existent facts directory."""
        result = get_latest_local_date(Path("/nonexistent/path"))
        self.assertIsNone(result)

    def test_returns_none_when_directory_empty(self) -> None:
        """Must return None when facts directory contains no CSVs."""
        with tempfile.TemporaryDirectory() as tmp:
            result = get_latest_local_date(Path(tmp))
            self.assertIsNone(result)

    def test_returns_latest_stem(self) -> None:
        """Must return the lexicographically largest .csv stem."""
        with tempfile.TemporaryDirectory() as tmp:
            for name in ["2026-02-15.csv", "2026-04-01.csv", "2026-03-10.csv"]:
                (Path(tmp) / name).write_text("header\n", encoding="utf-8")
            result = get_latest_local_date(Path(tmp))
            self.assertEqual(result, "2026-04-01")

    def test_ignores_non_csv_files(self) -> None:
        """Non-CSV files in facts directory must not affect the result."""
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "2026-02-15.csv").write_text("h\n", encoding="utf-8")
            (Path(tmp) / "README.txt").write_text("note", encoding="utf-8")
            result = get_latest_local_date(Path(tmp))
            self.assertEqual(result, "2026-02-15")


class TestMainMissingCredentials(unittest.TestCase):
    """Tests for main() when DATABASE_URL is absent or connection fails."""

    def test_exit_1_when_database_url_missing(self) -> None:
        """main() must exit with code 1 and print an error when DATABASE_URL unset."""
        # Patch load_dotenv to no-op and os.getenv to return None for DATABASE_URL.
        with mock.patch("load_supabase.load_dotenv"):
            with mock.patch("load_supabase.os.getenv", return_value=None):
                with self.assertRaises(SystemExit) as ctx:
                    import load_supabase
                    load_supabase.main()
        self.assertEqual(ctx.exception.code, 1)

    def test_exit_1_on_connection_error(self) -> None:
        """main() must exit with code 1 on psycopg2 OperationalError."""
        import psycopg2

        with mock.patch("load_supabase.load_dotenv"):
            with mock.patch(
                "load_supabase.os.getenv", return_value="postgresql://fake"
            ):
                with mock.patch(
                    "load_supabase.psycopg2.connect",
                    side_effect=psycopg2.OperationalError("refused"),
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        import load_supabase
                        load_supabase.main()
        self.assertEqual(ctx.exception.code, 1)


class TestUpsertDimFileNotFound(unittest.TestCase):
    """Tests for upsert_dim() when the CSV is missing."""

    def test_raises_file_not_found(self) -> None:
        """upsert_dim() must raise FileNotFoundError for absent CSVs."""
        from load_supabase import upsert_dim

        fake_conn = mock.MagicMock()
        with self.assertRaises(FileNotFoundError):
            upsert_dim(
                fake_conn,
                "dim_date",
                Path("/nonexistent/dim_date.csv"),
                "date_key",
                ["date_key", "date"],
            )


class TestInsertFactDayFileNotFound(unittest.TestCase):
    """Tests for insert_fact_day() when the CSV is missing."""

    def test_raises_file_not_found(self) -> None:
        """insert_fact_day() must raise FileNotFoundError for absent CSVs."""
        from load_supabase import insert_fact_day

        fake_conn = mock.MagicMock()
        with self.assertRaises(FileNotFoundError):
            insert_fact_day(
                fake_conn,
                "2026-02-15",
                Path("/nonexistent/2026-02-15.csv"),
            )


class TestUpsertDimWithData(unittest.TestCase):
    """Integration-style tests for upsert_dim() using a real temp CSV."""

    def _make_dim_csv(self, tmp_dir: str) -> Path:
        """Write a minimal dim_date CSV and return its path."""
        path = Path(tmp_dir) / "dim_date.csv"
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["date_key", "date", "year", "month", "day", "weekday"])
            writer.writerow(["1", "2026-02-15", "2026", "2", "15", "6"])
        return path

    def test_calls_execute_batch_with_rows(self) -> None:
        """upsert_dim() must call execute_batch and commit for valid CSV."""
        from load_supabase import upsert_dim

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = self._make_dim_csv(tmp)
            mock_conn = mock.MagicMock()
            mock_cursor = mock.MagicMock()
            mock_conn.cursor.return_value.__enter__ = mock.Mock(
                return_value=mock_cursor
            )
            mock_conn.cursor.return_value.__exit__ = mock.Mock(return_value=False)

            with mock.patch(
                "load_supabase.psycopg2.extras.execute_batch"
            ) as mock_batch:
                count = upsert_dim(
                    mock_conn,
                    "dim_date",
                    csv_path,
                    "date_key",
                    ["date_key", "date", "year", "month", "day", "weekday"],
                )
                mock_batch.assert_called_once()
                mock_conn.commit.assert_called_once()
                self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
