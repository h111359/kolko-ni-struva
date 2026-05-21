"""
test_fixes.py: Unit tests for request R-20260420-2008 — Fix db update failures.
Part of the kolko-ni-struva ETL pipeline (request R-20260420-2008).
Responsibilities: verify that create_tables() executes both DDL blocks in the
correct order, that _ENSURE_NULLABLE_DDL targets the three expected columns,
and that refresh.sh contains the venv detection guard.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# Ensure the project src/ is importable regardless of working directory.
# test_fixes.py is at <proj>/.aib_memory/requests/<request-folder>/test_fixes.py
# Four .parent() calls navigate from test_fixes.py up to the project root.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestCreateTablesExecutesTwoDDLCalls(unittest.TestCase):
    """Verify create_tables() issues exactly two cur.execute() calls in order."""

    def test_create_tables_calls_execute_twice(self) -> None:
        """
        Confirm that create_tables() calls cur.execute with _CREATE_DDL first
        and _ENSURE_NULLABLE_DDL second, then commits the transaction.
        """
        import load_supabase as ls

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        ls.create_tables(mock_conn)

        # The cursor must have been called with both DDL strings in order.
        self.assertEqual(mock_cursor.execute.call_count, 2)
        calls = mock_cursor.execute.call_args_list
        self.assertEqual(calls[0], call(ls._CREATE_DDL))
        self.assertEqual(calls[1], call(ls._ENSURE_NULLABLE_DDL))

        # The connection must be committed once after both executes.
        mock_conn.commit.assert_called_once()


class TestEnsureNullableDdlContent(unittest.TestCase):
    """Verify _ENSURE_NULLABLE_DDL targets the three expected columns."""

    def _get_ddl(self) -> str:
        import load_supabase as ls
        return ls._ENSURE_NULLABLE_DDL

    def test_ddl_contains_dim_store_settlement_key(self) -> None:
        """_ENSURE_NULLABLE_DDL must reference dim_store and settlement_key."""
        ddl = self._get_ddl()
        self.assertIn("dim_store", ddl)
        self.assertIn("settlement_key", ddl)

    def test_ddl_contains_dim_store_company_key(self) -> None:
        """_ENSURE_NULLABLE_DDL must reference dim_store and company_key."""
        ddl = self._get_ddl()
        self.assertIn("dim_store", ddl)
        self.assertIn("company_key", ddl)

    def test_ddl_contains_dim_file_zip_date(self) -> None:
        """_ENSURE_NULLABLE_DDL must reference dim_file and zip_date."""
        ddl = self._get_ddl()
        self.assertIn("dim_file", ddl)
        self.assertIn("zip_date", ddl)

    def test_ddl_contains_drop_not_null(self) -> None:
        """_ENSURE_NULLABLE_DDL must use DROP NOT NULL phrasing."""
        ddl = self._get_ddl().upper()
        self.assertIn("DROP NOT NULL", ddl)


class TestRefreshShVenvDetection(unittest.TestCase):
    """Verify refresh.sh contains the venv detection guard."""

    def _read_refresh_sh(self) -> str:
        refresh_path = BASE_DIR / "refresh.sh"
        return refresh_path.read_text(encoding="utf-8")

    def test_refresh_sh_contains_venv_bin_python(self) -> None:
        """refresh.sh must contain a reference to venv/bin/python."""
        content = self._read_refresh_sh()
        self.assertIn("venv/bin/python", content)

    def test_refresh_sh_contains_python_variable(self) -> None:
        """refresh.sh must use a $PYTHON variable to invoke scripts."""
        content = self._read_refresh_sh()
        self.assertIn("$PYTHON", content)

    def test_refresh_sh_has_fallback_to_python3(self) -> None:
        """refresh.sh must include a fallback to python3."""
        content = self._read_refresh_sh()
        self.assertIn("python3", content)


if __name__ == "__main__":
    unittest.main()
