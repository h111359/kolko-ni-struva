"""
test_load_supabase.py: Unit tests for src/load_supabase.py core functions.
Part of the kolko-ni-struva ETL pipeline (request R-20260425-2313).
Responsibilities: verify create_tables DDL execution, upsert SQL conflict
clause format, insert_lookback behaviour, and rolling 3-day remote retention
behavior added in request R-20260429-0825.  Updated in R-20260430-0825 to
remove tests for deleted functions (insert_fact_day, prune_fact_prices,
get_latest_remote_date) and update DDL/index assertions for
fact_prices_lookback.
All tests use mocked psycopg2 connections — no live database is required.
"""
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src/ to sys.path so the module resolves without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))



class FakeDatabaseError(Exception):
    """Replacement psycopg2.DatabaseError used by the mocked test module."""


class FakeOperationalError(Exception):
    """Replacement psycopg2.OperationalError used by the mocked test module."""

# Build mock psycopg2 objects BEFORE importing load_supabase so the module
# binds to our mocks rather than the real library.
_mock_psycopg2 = MagicMock()
_mock_psycopg2_extras = MagicMock()
_mock_dotenv = MagicMock()
# Ensure psycopg2.extras attribute resolves to our extras mock so that
# load_supabase.psycopg2.extras.execute_batch refers to the right object.
_mock_psycopg2.extras = _mock_psycopg2_extras
_mock_psycopg2.DatabaseError = FakeDatabaseError
_mock_psycopg2.OperationalError = FakeOperationalError

with patch.dict(
    "sys.modules",
    {
        "psycopg2": _mock_psycopg2,
        "psycopg2.extras": _mock_psycopg2_extras,
        "dotenv": _mock_dotenv,
    },
):
    from load_supabase import (  # noqa: E402
        SQL_AUDIT_TABLE,
        create_tables,
        execute_batch_with_audit,
        execute_sql,
        _CREATE_RPC_FUNCTIONS,
        get_retained_local_dates,
        get_date_keys_for_dates,
        prune_sql_audit_log,
        prune_dim_category,
        prune_dim_date,
        insert_lookback,
        upsert_dim,
        _CREATE_DDL,
        _CREATE_INDEXES,
    )

# Capture the extras mock as used by the imported module.  Any call to
# psycopg2.extras.execute_batch inside load_supabase resolves through this object.
_EXECUTE_BATCH = _mock_psycopg2_extras.execute_batch


def _make_mock_conn():
    """
    Build a mock psycopg2 connection and cursor pair.

    Returns:
        Tuple of (mock_conn, mock_cursor).
    """
    mock_conn = MagicMock()

    def _build_cursor():
        mock_cursor = MagicMock()
        # Support the context-manager protocol used in 'with conn.cursor() as cur:'.
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.mogrify = MagicMock(
            side_effect=lambda sql, params=None: (
                f"{sql} -- {params}" if params is not None else str(sql)
            ).encode("utf-8")
        )
        mock_cursor.connection = mock_conn
        return mock_cursor

    created_cursors = []

    def _cursor_factory():
        cursor = _build_cursor()
        created_cursors.append(cursor)
        return cursor

    primary_cursor = _cursor_factory()
    mock_conn.cursor.side_effect = [primary_cursor] + [
        _cursor_factory() for _ in range(64)
    ]
    mock_conn._cursor_mocks = created_cursors
    mock_conn.cursor.reset_mock()
    return mock_conn, primary_cursor


def _non_audit_sql_calls(mock_cursor):
    """Return execute() calls excluding INSERTs into the audit table itself."""
    return [
        str(call.args[0])
        for call in mock_cursor.execute.call_args_list
        if f"INSERT INTO {SQL_AUDIT_TABLE}" not in str(call.args[0])
    ]


def _audit_sql_calls(mock_conn):
    """Return audit INSERT execute() calls across all cursors for a connection."""
    return [
        call
        for cursor in mock_conn._cursor_mocks
        for call in cursor.execute.call_args_list
        if f"INSERT INTO {SQL_AUDIT_TABLE}" in str(call.args[0])
    ]


def _non_audit_sql_calls_for_conn(mock_conn):
    """Return non-audit execute() SQL strings across all cursors for a connection."""
    return [
        str(call.args[0])
        for cursor in mock_conn._cursor_mocks
        for call in cursor.execute.call_args_list
        if f"INSERT INTO {SQL_AUDIT_TABLE}" not in str(call.args[0])
    ]


class TestCreateTables(unittest.TestCase):
    """Tests for create_tables(): DDL execution and commit."""

    def test_executes_ddl_with_dim_date(self) -> None:
        """create_tables calls cursor.execute with SQL containing CREATE TABLE IF NOT EXISTS dim_date."""
        mock_conn, mock_cursor = _make_mock_conn()
        create_tables(mock_conn)
        # Collect all SQL strings passed to execute across all calls.
        executed_sql = " ".join(_non_audit_sql_calls(mock_cursor))
        self.assertIn("CREATE TABLE IF NOT EXISTS dim_date", executed_sql)

    def test_commits_after_ddl(self) -> None:
        """create_tables calls conn.commit() after executing DDL."""
        mock_conn, _ = _make_mock_conn()
        create_tables(mock_conn)
        mock_conn.commit.assert_called_once()

    def test_executes_five_ddl_statements(self) -> None:
        """create_tables executes exactly five DDL blocks: main DDL, nullable DDL, migration DDL, RPC DDL, index DDL."""
        mock_conn, mock_cursor = _make_mock_conn()
        create_tables(mock_conn)
        self.assertEqual(len(_non_audit_sql_calls(mock_cursor)), 5)

    def test_create_ddl_does_not_contain_fact_prices_table(self) -> None:
        """_CREATE_DDL must not contain CREATE TABLE IF NOT EXISTS fact_prices (only lookback)."""
        # fact_prices (without _lookback) must not appear as a CREATE TABLE target.
        import re
        matches = re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', _CREATE_DDL)
        self.assertNotIn('fact_prices', matches)
        self.assertIn('fact_prices_lookback', matches)

    def test_create_ddl_contains_backend_sql_audit_table(self) -> None:
        """_CREATE_DDL provisions the backend SQL audit table."""
        self.assertIn(f"CREATE TABLE IF NOT EXISTS {SQL_AUDIT_TABLE}", _CREATE_DDL)

    def test_index_ddl_contains_lookback_date_key_index(self) -> None:
        """_CREATE_INDEXES contains CREATE INDEX IF NOT EXISTS for fact_prices_lookback(date_key)."""
        self.assertIn("idx_fact_prices_lookback_date_key", _CREATE_INDEXES)
        self.assertIn("CREATE INDEX IF NOT EXISTS", _CREATE_INDEXES)

    def test_index_ddl_contains_lookback_composite_date_store_index(self) -> None:
        """_CREATE_INDEXES contains a composite index on fact_prices_lookback(date_key, store_key)."""
        self.assertIn("idx_fact_prices_lookback_date_store", _CREATE_INDEXES)
        self.assertIn("date_key, store_key", _CREATE_INDEXES)

    def test_index_ddl_targets_fact_prices_lookback(self) -> None:
        """_CREATE_INDEXES creates indexes on fact_prices_lookback, not fact_prices."""
        self.assertIn("ON fact_prices_lookback", _CREATE_INDEXES)
        self.assertNotIn("ON fact_prices(", _CREATE_INDEXES)

    def test_index_ddl_contains_backend_sql_audit_index(self) -> None:
        """_CREATE_INDEXES provisions the audit-table executed_at index."""
        self.assertIn("idx_backend_sql_audit_log_executed_at", _CREATE_INDEXES)

    def test_index_ddl_contains_report_slice_index(self) -> None:
        """_CREATE_INDEXES provisions the report-oriented date/store/category index."""
        self.assertIn("idx_fpl_date_store_category", _CREATE_INDEXES)
        self.assertIn("date_key, store_key, category_key", _CREATE_INDEXES)

    def test_rpc_ddl_contains_report_functions(self) -> None:
        """_CREATE_RPC_FUNCTIONS provisions the report-oriented RPC helpers."""
        self.assertIn("get_report_1_category_prices", _CREATE_RPC_FUNCTIONS)
        self.assertIn("get_report_2_rows", _CREATE_RPC_FUNCTIONS)
        self.assertIn("get_report_3_rows", _CREATE_RPC_FUNCTIONS)

    def test_rpc_ddl_grants_anon_execute_for_report_functions(self) -> None:
        """Report RPC helpers grant EXECUTE to the Supabase anon role."""
        self.assertIn(
            "GRANT EXECUTE ON FUNCTION get_report_1_category_prices(bigint, bigint, text) TO anon;",
            _CREATE_RPC_FUNCTIONS,
        )
        self.assertIn(
            "GRANT EXECUTE ON FUNCTION get_report_2_rows(bigint, bigint, bigint, text) TO anon;",
            _CREATE_RPC_FUNCTIONS,
        )
        self.assertIn(
            "GRANT EXECUTE ON FUNCTION get_report_3_rows(bigint, bigint, text) TO anon;",
            _CREATE_RPC_FUNCTIONS,
        )


class TestAuditHelpers(unittest.TestCase):
    """Tests for the backend SQL audit helper functions."""

    def setUp(self) -> None:
        """Reset the execute_batch mock call history before each test."""
        _EXECUTE_BATCH.reset_mock()

    def test_execute_sql_logs_origin_and_rendered_text(self) -> None:
        """execute_sql runs the statement and inserts an audit row for it."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_conn.cursor()
        mock_conn.cursor.reset_mock()
        execute_sql(
            mock_cursor,
            "SELECT date_key FROM dim_date WHERE date::text = ANY(%s)",
            (["2026-04-29"],),
            origin="get_date_keys_for_dates",
        )

        self.assertEqual(mock_cursor.execute.call_count, 1)
        audit_call = _audit_sql_calls(mock_conn)[0]
        self.assertIn(f"INSERT INTO {SQL_AUDIT_TABLE}", audit_call.args[0])
        self.assertEqual(audit_call.args[1][0], "get_date_keys_for_dates")
        self.assertEqual(audit_call.args[1][1], 1)
        self.assertIn("SELECT date_key FROM dim_date", audit_call.args[1][2])

    def test_execute_sql_uses_sibling_cursor_for_audit_insert(self) -> None:
        """execute_sql logs through a sibling cursor so the caller cursor keeps its result set."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_conn.cursor()
        mock_conn.cursor.reset_mock()

        execute_sql(
            mock_cursor,
            "SELECT category_key FROM dim_category",
            origin="test_select",
        )

        self.assertEqual(mock_conn.cursor.call_count, 1)
        self.assertEqual(mock_cursor.execute.call_count, 1)
        audit_calls = _audit_sql_calls(mock_conn)
        self.assertEqual(len(audit_calls), 1)

    def test_execute_batch_with_audit_logs_one_row_per_page(self) -> None:
        """execute_batch_with_audit preserves page batching and logs each rendered page."""
        mock_conn, mock_cursor = _make_mock_conn()
        rows = [(1, "A"), (2, "B"), (3, "C")]

        execute_batch_with_audit(
            mock_cursor,
            "INSERT INTO demo_table (id, name) VALUES (%s, %s)",
            rows,
            origin="demo_batch",
            page_size=2,
        )

        self.assertEqual(_EXECUTE_BATCH.call_count, 2)
        first_batch_rows = _EXECUTE_BATCH.call_args_list[0].args[2]
        second_batch_rows = _EXECUTE_BATCH.call_args_list[1].args[2]
        self.assertEqual(first_batch_rows, rows[:2])
        self.assertEqual(second_batch_rows, rows[2:])

        audit_calls = _audit_sql_calls(mock_conn)
        self.assertEqual(len(audit_calls), 2)
        self.assertEqual(audit_calls[0].args[1][0], "demo_batch")
        self.assertEqual(audit_calls[0].args[1][1], 2)
        self.assertIn("INSERT INTO demo_table", audit_calls[0].args[1][2])
        self.assertEqual(audit_calls[1].args[1][1], 1)


class TestUpsertDimSQL(unittest.TestCase):
    """Tests that upsert_dim generates SQL containing ON CONFLICT … DO UPDATE."""

    def setUp(self) -> None:
        """Reset the execute_batch mock call history before each test."""
        _EXECUTE_BATCH.reset_mock()

    def test_upsert_sql_contains_on_conflict_clause(self) -> None:
        """upsert_dim generates SQL with ON CONFLICT (pk_col) DO UPDATE SET."""
        mock_conn, mock_cursor = _make_mock_conn()

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "dim_settlement.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["settlement_key", "ekatte", "settlement_name"])
                writer.writerow([1, "68134", "Sofia"])

            upsert_dim(
                mock_conn,
                "dim_settlement",
                csv_path,
                "settlement_key",
                ["settlement_key", "ekatte", "settlement_name"],
            )

            # Verify execute_batch was called with the correct SQL.
            self.assertTrue(_EXECUTE_BATCH.called, "execute_batch should have been called")
            captured_sql = _EXECUTE_BATCH.call_args.args[1]
            self.assertIn("ON CONFLICT", captured_sql)
            self.assertIn("DO UPDATE SET", captured_sql)

    def test_upsert_rows_match_csv_content(self) -> None:
        """upsert_dim passes the exact CSV rows to execute_batch."""
        mock_conn, mock_cursor = _make_mock_conn()

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "dim_company.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["company_key", "uic", "company_name"])
                writer.writerow([1, "123456789", "Test Company"])

            count = upsert_dim(
                mock_conn,
                "dim_company",
                csv_path,
                "company_key",
                ["company_key", "uic", "company_name"],
            )
            self.assertEqual(count, 1)
            rows_passed = _EXECUTE_BATCH.call_args.args[2]
            # First (and only) row: ('1', '123456789', 'Test Company').
            self.assertEqual(rows_passed[0], ("1", "123456789", "Test Company"))


class TestInsertLookback(unittest.TestCase):
    """Tests for insert_lookback(): TRUNCATE + reinsert of fact_prices_lookback."""

    def setUp(self) -> None:
        """Reset the execute_batch mock before each test."""
        _EXECUTE_BATCH.reset_mock()

    def test_truncates_and_inserts_rows(self) -> None:
        """insert_lookback truncates fact_prices_lookback then inserts rows from CSV."""
        mock_conn, mock_cursor = _make_mock_conn()

        columns = [
            "date_key", "store_key", "file_key", "category_key", "product_key",
            "retail_price", "promo_price", "retail_price_day1", "promo_price_day1",
            "retail_price_day2", "promo_price_day2",
        ]

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fact_prices_lookback.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(columns)
                writer.writerow([20260429, 1, 1, 1, 1, "3.17", None, "3.20", None, "3.10", None])

            result = insert_lookback(mock_conn, csv_path)

        self.assertEqual(result, 1)
        # Verify TRUNCATE was called.
        executed_statements = [str(c.args[0]) for c in mock_cursor.execute.call_args_list]
        self.assertTrue(
            any("TRUNCATE" in s for s in executed_statements),
            "TRUNCATE TABLE fact_prices_lookback must be called",
        )
        # Verify execute_batch was called with INSERT.
        self.assertTrue(_EXECUTE_BATCH.called, "execute_batch should have been called for insert")
        captured_sql = _EXECUTE_BATCH.call_args.args[1]
        self.assertIn("INSERT INTO fact_prices_lookback", captured_sql)
        mock_conn.commit.assert_called_once()

    def test_truncates_only_when_csv_empty(self) -> None:
        """insert_lookback truncates and returns 0 when CSV is absent."""
        mock_conn, mock_cursor = _make_mock_conn()

        # Pass a path that does not exist.
        result = insert_lookback(mock_conn, Path("/nonexistent/fact_prices_lookback.csv"))

        self.assertEqual(result, 0)
        executed_statements = [str(c.args[0]) for c in mock_cursor.execute.call_args_list]
        self.assertTrue(
            any("TRUNCATE" in s for s in executed_statements),
            "TRUNCATE must still be executed even when CSV is absent",
        )
        # execute_batch must NOT be called when there are no rows to insert.
        _EXECUTE_BATCH.assert_not_called()
        mock_conn.commit.assert_called_once()

    def test_rollback_on_db_error(self) -> None:
        """insert_lookback rolls back and re-raises on a database error."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.execute.side_effect = FakeDatabaseError("simulated")

        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "fact_prices_lookback.csv"
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    "date_key", "store_key", "file_key", "category_key", "product_key",
                    "retail_price", "promo_price", "retail_price_day1", "promo_price_day1",
                    "retail_price_day2", "promo_price_day2",
                ])

            with self.assertRaises(FakeDatabaseError):
                insert_lookback(mock_conn, csv_path)

        mock_conn.rollback.assert_called_once()


class TestGetRetainedLocalDates(unittest.TestCase):
    """Tests for get_retained_local_dates(): rolling retention window calculation."""

    def test_returns_latest_three_from_many(self) -> None:
        """get_retained_local_dates returns the 3 newest dates when more exist."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            for d in ["2026-04-25", "2026-04-26", "2026-04-27", "2026-04-28", "2026-04-29"]:
                (facts_dir / f"{d}.csv").write_text("header\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir)
        self.assertEqual(result, ["2026-04-27", "2026-04-28", "2026-04-29"])

    def test_returns_all_when_fewer_than_three(self) -> None:
        """get_retained_local_dates returns all dates when only 2 CSVs exist."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            for d in ["2026-04-28", "2026-04-29"]:
                (facts_dir / f"{d}.csv").write_text("header\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir)
        self.assertEqual(result, ["2026-04-28", "2026-04-29"])

    def test_returns_single_date_when_one_csv(self) -> None:
        """get_retained_local_dates returns a single-element list for one fact file."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            (facts_dir / "2026-04-29.csv").write_text("header\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir)
        self.assertEqual(result, ["2026-04-29"])

    def test_returns_empty_list_for_absent_directory(self) -> None:
        """get_retained_local_dates returns [] when the facts directory does not exist."""
        result = get_retained_local_dates(Path("/nonexistent/path/facts"))
        self.assertEqual(result, [])

    def test_returns_empty_list_for_empty_directory(self) -> None:
        """get_retained_local_dates returns [] for a directory with no CSV files."""
        with tempfile.TemporaryDirectory() as tmp:
            result = get_retained_local_dates(Path(tmp))
        self.assertEqual(result, [])

    def test_ignores_non_csv_files(self) -> None:
        """get_retained_local_dates ignores files without a .csv extension."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            (facts_dir / "2026-04-29.csv").write_text("header\n", encoding="utf-8")
            (facts_dir / "README.txt").write_text("notes\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir)
        self.assertEqual(result, ["2026-04-29"])

    def test_custom_n_parameter(self) -> None:
        """get_retained_local_dates respects a custom n value."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            for d in ["2026-04-27", "2026-04-28", "2026-04-29"]:
                (facts_dir / f"{d}.csv").write_text("header\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir, n=2)
        self.assertEqual(result, ["2026-04-28", "2026-04-29"])

    def test_result_contains_latest_local_date(self) -> None:
        """The last element of get_retained_local_dates is always the newest date."""
        with tempfile.TemporaryDirectory() as tmp:
            facts_dir = Path(tmp)
            for d in ["2026-04-25", "2026-04-26", "2026-04-27", "2026-04-28", "2026-04-29"]:
                (facts_dir / f"{d}.csv").write_text("header\n", encoding="utf-8")
            result = get_retained_local_dates(facts_dir)
        self.assertEqual(result[-1], "2026-04-29")


class TestGetDateKeysForDates(unittest.TestCase):
    """Tests for get_date_keys_for_dates(): remote date_key resolution."""

    def test_returns_date_keys_from_cursor(self) -> None:
        """get_date_keys_for_dates parses cursor rows and returns integer date_keys."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.fetchall.return_value = [(20260427,), (20260428,), (20260429,)]
        result = get_date_keys_for_dates(mock_conn, ["2026-04-27", "2026-04-28", "2026-04-29"])
        self.assertEqual(result, [20260427, 20260428, 20260429])

    def test_returns_empty_list_for_empty_input(self) -> None:
        """get_date_keys_for_dates returns [] immediately without querying the DB."""
        mock_conn, mock_cursor = _make_mock_conn()
        result = get_date_keys_for_dates(mock_conn, [])
        self.assertEqual(result, [])
        # The cursor must not be opened when the input list is empty.
        mock_conn.cursor.assert_not_called()

    def test_passes_date_list_to_query(self) -> None:
        """get_date_keys_for_dates calls cursor.execute with the date list as a parameter."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.fetchall.return_value = []
        get_date_keys_for_dates(mock_conn, ["2026-04-29"])
        self.assertTrue(mock_cursor.execute.called)
        exec_args, _ = mock_cursor.execute.call_args_list[0]
        params = exec_args[1]  # second positional arg to cursor.execute
        # The date list must be passed as a query parameter (not interpolated).
        self.assertIn("2026-04-29", params[0])

    def test_preserves_fetchable_rows_after_audited_select(self) -> None:
        """get_date_keys_for_dates keeps SELECT rows fetchable after audit logging."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.fetchall.return_value = [(20260429,)]

        result = get_date_keys_for_dates(mock_conn, ["2026-04-29"])

        self.assertEqual(result, [20260429])
        mock_cursor.fetchall.assert_called_once_with()
        self.assertEqual(mock_conn.cursor.call_count, 2)
        self.assertEqual(len(_audit_sql_calls(mock_conn)), 1)


class TestPruneDimDate(unittest.TestCase):
    """Tests for prune_dim_date(): deletion of out-of-window dim_date rows."""

    def test_executes_delete_with_not_in_clause(self) -> None:
        """prune_dim_date issues a DELETE … NOT IN SQL statement against dim_date."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.rowcount = 60
        prune_dim_date(mock_conn, [20260427, 20260428, 20260429])
        executed_sql = _non_audit_sql_calls(mock_cursor)[0]
        self.assertIn("DELETE FROM dim_date", executed_sql)
        self.assertIn("NOT IN", executed_sql)

    def test_commits_after_delete(self) -> None:
        """prune_dim_date commits the transaction on success."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.rowcount = 0
        prune_dim_date(mock_conn, [20260429])
        mock_conn.commit.assert_called()

    def test_returns_rowcount(self) -> None:
        """prune_dim_date returns the number of deleted rows."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.rowcount = 60
        result = prune_dim_date(mock_conn, [20260427, 20260428, 20260429])
        self.assertEqual(result, 60)

    def test_skips_delete_when_retained_keys_empty(self) -> None:
        """prune_dim_date skips the DELETE and returns 0 for an empty retention set."""
        mock_conn, mock_cursor = _make_mock_conn()
        result = prune_dim_date(mock_conn, [])
        self.assertEqual(result, 0)
        mock_cursor.execute.assert_not_called()

    def test_rollback_on_db_error(self) -> None:
        """prune_dim_date rolls back and re-raises on a database error."""
        mock_conn, mock_cursor = _make_mock_conn()
        # Use the real exception class so the except clause in production code fires.
        mock_cursor.execute.side_effect = FakeDatabaseError("simulated")
        with self.assertRaises(FakeDatabaseError):
            prune_dim_date(mock_conn, [20260429])
        mock_conn.rollback.assert_called_once()

    def test_idempotent_when_already_pruned(self) -> None:
        """prune_dim_date returns 0 rows deleted when DB is already aligned."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.rowcount = 0
        result = prune_dim_date(mock_conn, [20260427, 20260428, 20260429])
        self.assertEqual(result, 0)


class TestPruneDimCategory(unittest.TestCase):
    """Tests for prune_dim_category(): deletion of unreferenced dim_category rows."""

    def test_prune_removes_unreferenced_rows(self) -> None:
        """prune_dim_category deletes dim_category rows not in fact_prices_lookback."""
        mock_conn, mock_cursor = _make_mock_conn()
        delete_cursor = mock_conn._cursor_mocks[2]
        # The SELECT returns 3 referenced category keys.
        mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]
        # The DELETE removes 2 unreferenced rows.
        delete_cursor.rowcount = 2
        result = prune_dim_category(mock_conn)
        self.assertEqual(result, 2)
        # Verify a DELETE … NOT IN statement was issued against dim_category.
        executed_sqls = _non_audit_sql_calls_for_conn(mock_conn)
        self.assertTrue(
            any("DELETE FROM dim_category" in s for s in executed_sqls),
            "Expected DELETE FROM dim_category in executed SQL",
        )
        self.assertTrue(
            any("NOT IN" in s for s in executed_sqls),
            "Expected NOT IN clause in DELETE statement",
        )
        mock_conn.commit.assert_called_once()

    def test_safety_guard_on_empty_fact_table(self) -> None:
        """prune_dim_category skips DELETE and returns 0 when fact_prices_lookback is empty."""
        mock_conn, mock_cursor = _make_mock_conn()
        # Empty fetchall simulates an empty fact_prices_lookback table.
        mock_cursor.fetchall.return_value = []
        result = prune_dim_category(mock_conn)
        self.assertEqual(result, 0)
        # Only the SELECT should have been executed; no DELETE should follow.
        executed_sqls = [str(c.args[0]) for c in mock_cursor.execute.call_args_list]
        self.assertFalse(
            any("DELETE" in s for s in executed_sqls),
            "DELETE must not be issued when fact_prices_lookback is empty",
        )

    def test_rollback_on_db_error(self) -> None:
        """prune_dim_category rolls back and re-raises on a database error."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.execute.side_effect = FakeDatabaseError("simulated")
        with self.assertRaises(FakeDatabaseError):
            prune_dim_category(mock_conn)
        mock_conn.rollback.assert_called_once()

    def test_no_op_when_all_categories_referenced(self) -> None:
        """prune_dim_category returns 0 when all dim_category rows are referenced."""
        mock_conn, mock_cursor = _make_mock_conn()
        delete_cursor = mock_conn._cursor_mocks[2]
        # All existing category keys appear in fact_prices_lookback.
        mock_cursor.fetchall.return_value = [(1,), (2,), (3,)]
        # DELETE matches nothing because all categories are retained.
        delete_cursor.rowcount = 0
        result = prune_dim_category(mock_conn)
        self.assertEqual(result, 0)
        mock_conn.commit.assert_called_once()


class TestPruneSqlAuditLog(unittest.TestCase):
    """Tests for prune_sql_audit_log(): rolling audit retention cleanup."""

    def test_executes_retention_delete_and_commits(self) -> None:
        """prune_sql_audit_log deletes old audit rows and commits on success."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.rowcount = 4

        result = prune_sql_audit_log(mock_conn, retention_days=7)

        self.assertEqual(result, 4)
        executed_sql = _non_audit_sql_calls(mock_cursor)[0]
        self.assertIn(f"DELETE FROM {SQL_AUDIT_TABLE}", executed_sql)
        self.assertIn("INTERVAL '7 days'", executed_sql)
        mock_conn.commit.assert_called_once()

    def test_rolls_back_on_database_error(self) -> None:
        """prune_sql_audit_log rolls back and re-raises on a database error."""
        mock_conn, mock_cursor = _make_mock_conn()
        mock_cursor.execute.side_effect = FakeDatabaseError("simulated")

        with self.assertRaises(FakeDatabaseError):
            prune_sql_audit_log(mock_conn)

        mock_conn.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
