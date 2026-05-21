"""
test_transform.py: Unit tests for src/transform.py core functions.
Part of the kolko-ni-struva ETL pipeline (request R-20260425-2313).
Responsibilities: verify delimiter auto-detection, dimension upsert (new and
existing code paths), atomic fact file write, and quality report generation.
"""
import csv
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

# Add src/ to sys.path so the module resolves without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transform import (  # noqa: E402
    detect_delimiter,
    load_dim,
    normalize_settlement_code,
    upsert_dim,
    write_dim,
    write_quality_report,
    load_settlement_names,
    resolve_settlement_name,
    patch_unknown_settlements,
    DIM_SETTLEMENT_HEADER,
    QUALITY_DIR,
)


class TestDetectDelimiter(unittest.TestCase):
    """Tests for detect_delimiter(): comma vs semicolon detection."""

    def test_returns_comma_for_comma_delimited_header(self) -> None:
        """detect_delimiter returns ',' when the header has more commas than semicolons."""
        header = "settlement,store,product_name,product_code,category,retail_price,promo_price"
        self.assertEqual(detect_delimiter(header), ",")

    def test_returns_semicolon_for_semicolon_delimited_header(self) -> None:
        """detect_delimiter returns ';' when the header has more semicolons than commas."""
        header = "settlement;store;product_name;product_code;category;retail_price;promo_price"
        self.assertEqual(detect_delimiter(header), ";")

    def test_defaults_to_comma_when_equal_counts(self) -> None:
        """detect_delimiter returns ',' as the default when comma and semicolon counts are equal."""
        # One comma, one semicolon — tie goes to comma.
        header = "a,b;c"
        self.assertEqual(detect_delimiter(header), ",")

    def test_semicolon_dominates_mixed_header(self) -> None:
        """detect_delimiter returns ';' when semicolons outnumber commas."""
        header = "a;b;c,d"  # 2 semicolons vs 1 comma
        self.assertEqual(detect_delimiter(header), ";")


class TestUpsertDim(unittest.TestCase):
    """Tests for upsert_dim(): SCD Type-1 dimension insert and lookup."""

    def test_new_code_gets_next_surrogate_key(self) -> None:
        """upsert_dim assigns surrogate key max_key + 1 for a previously unseen natural key."""
        lookup = {}
        # Counter starts at 5, simulating an existing dimension with 4 entries.
        counter = [5]
        sk = upsert_dim(
            lookup, counter, "settlement_key",
            ("12345",),
            {"ekatte": "12345", "settlement_name": "Sofia"},
        )
        self.assertEqual(sk, 5)
        # Counter must advance so the next new entry gets 6.
        self.assertEqual(counter[0], 6)

    def test_existing_code_returns_same_surrogate_key(self) -> None:
        """upsert_dim returns the already-assigned key for a known natural key."""
        lookup = {("12345",): {"settlement_key": "5", "ekatte": "12345", "settlement_name": "Sofia"}}
        counter = [6]
        sk = upsert_dim(
            lookup, counter, "settlement_key",
            ("12345",),
            {"ekatte": "12345", "settlement_name": "Sofia"},
        )
        self.assertEqual(sk, 5)
        # Counter must NOT advance for an existing entry.
        self.assertEqual(counter[0], 6)

    def test_row_stored_in_lookup(self) -> None:
        """upsert_dim adds the new row to the lookup dict after insertion."""
        lookup = {}
        counter = [1]
        upsert_dim(
            lookup, counter, "category_key",
            ("101",),
            {"category_code": "101", "category_name": "Мляко"},
        )
        self.assertIn(("101",), lookup)
        self.assertEqual(lookup[("101",)]["category_name"], "Мляко")


class TestLoadDim(unittest.TestCase):
    """Tests for load_dim(): CSV → lookup dict and next surrogate key calculation."""

    def test_returns_empty_lookup_for_absent_file(self) -> None:
        """load_dim returns ({}, 1) when the dimension CSV does not exist yet."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dim_missing.csv"
            lookup, next_key = load_dim(path, ["ekatte"])
            self.assertEqual(lookup, {})
            self.assertEqual(next_key, 1)

    def test_reads_existing_rows(self) -> None:
        """load_dim loads all rows from an existing dimension CSV into the lookup dict."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dim_settlement.csv"
            with open(path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["settlement_key", "ekatte", "settlement_name"])
                writer.writerow([1, "68134", "Sofia"])
                writer.writerow([2, "10135", "Plovdiv"])
            lookup, next_key = load_dim(path, ["ekatte"])
            self.assertIn(("68134",), lookup)
            self.assertIn(("10135",), lookup)
            # next surrogate key must be max_existing + 1 = 3.
            self.assertEqual(next_key, 3)


class TestWriteDim(unittest.TestCase):
    """Tests for write_dim(): atomic CSV write via .partial rename."""

    def test_writes_header_and_rows(self) -> None:
        """write_dim produces a CSV with the correct header and all lookup rows."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dim_settlement.csv"
            lookup = {
                ("68134",): {"settlement_key": "1", "ekatte": "68134", "settlement_name": "Sofia"},
                ("10135",): {"settlement_key": "2", "ekatte": "10135", "settlement_name": "Plovdiv"},
            }
            header = ["settlement_key", "ekatte", "settlement_name"]
            write_dim(path, header, lookup)
            self.assertTrue(path.exists())
            with open(path, encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            self.assertEqual(len(rows), 2)
            self.assertIn("Sofia", {r["settlement_name"] for r in rows})

    def test_no_partial_file_after_write(self) -> None:
        """write_dim leaves no .partial file after a successful write."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dim_category.csv"
            lookup = {
                ("101",): {"category_key": "1", "category_code": "101", "category_name": "Dairy"},
            }
            header = ["category_key", "category_code", "category_name"]
            write_dim(path, header, lookup)
            partial = path.with_suffix(path.suffix + ".partial")
            self.assertFalse(partial.exists(), ".partial file must not remain after write")


class TestWriteQualityReport(unittest.TestCase):
    """Tests for write_quality_report(): CSV output to data/quality/."""

    def test_writes_quality_csv(self) -> None:
        """write_quality_report creates a CSV with the expected columns and row data."""
        rows = [
            {
                "zip_date": "2026-04-01",
                "total_rows": 100,
                "null_prices": 2,
                "unknown_settlements": 1,
                "unknown_categories": 0,
                "delimiter_anomalies": 0,
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            # Temporarily redirect QUALITY_DIR to a temp location so tests don't
            # pollute the real data/quality/ folder.
            import transform as tr
            original_quality_dir = tr.QUALITY_DIR
            tr.QUALITY_DIR = Path(tmp)
            try:
                write_quality_report(rows, "2026-04-01_120000")
                report_files = list(Path(tmp).glob("report_*.csv"))
                self.assertEqual(len(report_files), 1)
                with open(report_files[0], encoding="utf-8", newline="") as fh:
                    reader = csv.DictReader(fh)
                    data = list(reader)
                self.assertEqual(len(data), 1)
                self.assertEqual(data[0]["zip_date"], "2026-04-01")
                self.assertEqual(data[0]["total_rows"], "100")
            finally:
                # Restore the original module-level constant.
                tr.QUALITY_DIR = original_quality_dir


class TestLoadSettlementNames(unittest.TestCase):
    """Tests for load_settlement_names(): extended EKATTE file loading."""

    def test_loads_raion_code_from_ek_raion(self) -> None:
        """load_settlement_names returns a raion code resolved from ek_raion.json."""
        # T1: raion code resolution — '68134-04' must map to a name
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            import transform as tr
            # Write minimal ek_raion.json fixture in temp dir.
            raion_file = tmp_path / "ek_raion.json"
            raion_file.write_text(
                '[{"raion":"68134-04","name":"Оборище","name_en":"Oborishte","document":21}]',
                encoding="utf-8",
            )
            # Patch the module-level constant and temporarily disable other files.
            orig_raion = tr.EK_RAION_FILE
            orig_cities = tr.CITIES_FILE
            orig_sof = tr.SOF_RAI_FILE
            orig_atte = tr.EK_ATTE_FILE
            orig_kmet = tr.EK_KMET_FILE
            orig_obl = tr.EK_OBL_FILE
            orig_obst = tr.EK_OBST_FILE
            tr.EK_RAION_FILE = raion_file
            tr.CITIES_FILE = tmp_path / "missing_cities.json"
            tr.SOF_RAI_FILE = tmp_path / "missing_sof.json"
            tr.EK_ATTE_FILE = tmp_path / "missing_atte.json"
            tr.EK_KMET_FILE = tmp_path / "missing_kmet.json"
            tr.EK_OBL_FILE = tmp_path / "missing_obl.json"
            tr.EK_OBST_FILE = tmp_path / "missing_obst.json"
            try:
                names = tr.load_settlement_names()
                self.assertIn("68134-04", names)
                self.assertEqual(names["68134-04"], "Оборище")
            finally:
                tr.EK_RAION_FILE = orig_raion
                tr.CITIES_FILE = orig_cities
                tr.SOF_RAI_FILE = orig_sof
                tr.EK_ATTE_FILE = orig_atte
                tr.EK_KMET_FILE = orig_kmet
                tr.EK_OBL_FILE = orig_obl
                tr.EK_OBST_FILE = orig_obst

    def test_skips_metadata_row_in_ek_raion(self) -> None:
        """load_settlement_names does not fail when ek_raion.json has a trailing metadata row."""
        # T2: metadata row in ek_raion.json is skipped without error
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            import transform as tr
            raion_file = tmp_path / "ek_raion.json"
            raion_file.write_text(
                '[{"raion":"68134-01","name":"Средец","document":21},'
                '{"Дата и час":"15/04/2026","Данните са актуални към":"24/04/2026"}]',
                encoding="utf-8",
            )
            orig_raion = tr.EK_RAION_FILE
            orig_cities, orig_sof = tr.CITIES_FILE, tr.SOF_RAI_FILE
            orig_atte, orig_kmet = tr.EK_ATTE_FILE, tr.EK_KMET_FILE
            orig_obl, orig_obst = tr.EK_OBL_FILE, tr.EK_OBST_FILE
            tr.EK_RAION_FILE = raion_file
            tr.CITIES_FILE = tmp_path / "missing.json"
            tr.SOF_RAI_FILE = tmp_path / "missing.json"
            tr.EK_ATTE_FILE = tmp_path / "missing.json"
            tr.EK_KMET_FILE = tmp_path / "missing.json"
            tr.EK_OBL_FILE = tmp_path / "missing.json"
            tr.EK_OBST_FILE = tmp_path / "missing.json"
            try:
                names = tr.load_settlement_names()
                # Valid entry present; metadata row silently skipped.
                self.assertIn("68134-01", names)
                self.assertEqual(names["68134-01"], "Средец")
            finally:
                tr.EK_RAION_FILE = orig_raion
                tr.CITIES_FILE = orig_cities
                tr.SOF_RAI_FILE = orig_sof
                tr.EK_ATTE_FILE = orig_atte
                tr.EK_KMET_FILE = orig_kmet
                tr.EK_OBL_FILE = orig_obl
                tr.EK_OBST_FILE = orig_obst

    def test_gracefully_handles_absent_ekatte_files(self) -> None:
        """load_settlement_names returns without error when all 5 EKATTE files are absent."""
        # T11: absent-file handling — function must not raise
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            import transform as tr
            orig_raion = tr.EK_RAION_FILE
            orig_cities, orig_sof = tr.CITIES_FILE, tr.SOF_RAI_FILE
            orig_atte, orig_kmet = tr.EK_ATTE_FILE, tr.EK_KMET_FILE
            orig_obl, orig_obst = tr.EK_OBL_FILE, tr.EK_OBST_FILE
            # Point all paths at non-existent files.
            tr.EK_RAION_FILE = tmp_path / "missing.json"
            tr.CITIES_FILE = tmp_path / "missing.json"
            tr.SOF_RAI_FILE = tmp_path / "missing.json"
            tr.EK_ATTE_FILE = tmp_path / "missing.json"
            tr.EK_KMET_FILE = tmp_path / "missing.json"
            tr.EK_OBL_FILE = tmp_path / "missing.json"
            tr.EK_OBST_FILE = tmp_path / "missing.json"
            try:
                names = tr.load_settlement_names()
                # Must return an empty dict without raising.
                self.assertIsInstance(names, dict)
            finally:
                tr.EK_RAION_FILE = orig_raion
                tr.CITIES_FILE = orig_cities
                tr.SOF_RAI_FILE = orig_sof
                tr.EK_ATTE_FILE = orig_atte
                tr.EK_KMET_FILE = orig_kmet
                tr.EK_OBL_FILE = orig_obl
                tr.EK_OBST_FILE = orig_obst


class TestResolveSettlementName(unittest.TestCase):
    """Tests for resolve_settlement_name(): three-step EKATTE normalisation."""

    def test_zero_padded_code_resolves(self) -> None:
        """resolve_settlement_name resolves a short code by zero-padding to 5 digits."""
        # T4: zero-padding — '2659' must resolve via '02659'
        lookup = {"02659": "Банкя"}
        result = resolve_settlement_name("2659", lookup)
        self.assertEqual(result, "Банкя")

    def test_leading_zero_stripped_code_resolves(self) -> None:
        """resolve_settlement_name resolves an over-padded code by stripping leading zeros."""
        # T5: leading-zero stripping — '068134' must resolve via '68134'
        lookup = {"68134": "София"}
        result = resolve_settlement_name("068134", lookup)
        self.assertEqual(result, "София")


class TestNormalizeSettlementCode(unittest.TestCase):
    """Tests for normalize_settlement_code(): canonical ETL settlement keys."""

    def test_strips_redundant_leading_zeroes_for_long_numeric_codes(self) -> None:
        """normalize_settlement_code collapses over-padded numeric EKATTE values."""
        self.assertEqual(normalize_settlement_code("068134"), "68134")

    def test_zero_pads_short_numeric_codes_to_five_digits(self) -> None:
        """normalize_settlement_code pads short numeric EKATTE values to canonical width."""
        self.assertEqual(normalize_settlement_code("2659"), "02659")

    def test_preserves_raion_suffix_while_normalising_numeric_prefix(self) -> None:
        """normalize_settlement_code keeps raion suffixes attached to the canonical prefix."""
        self.assertEqual(normalize_settlement_code("068134-04"), "68134-04")

    def test_truly_unresolvable_code_returns_placeholder(self) -> None:
        """resolve_settlement_name returns (unknown:<code>) when no probe matches."""
        # T6: unresolvable code — '98226' must return placeholder
        result = resolve_settlement_name("98226", {})
        self.assertEqual(result, "(unknown:98226)")

    def test_exact_code_takes_precedence(self) -> None:
        """resolve_settlement_name returns the as-is match before attempting normalisation."""
        # Exact match should be used when the code is already in the lookup.
        lookup = {"68134-04": "Оборище", "0681304": "Other"}
        result = resolve_settlement_name("68134-04", lookup)
        self.assertEqual(result, "Оборище")

    def test_empty_string_code_returns_placeholder(self) -> None:
        """resolve_settlement_name returns (unknown:) for an empty string code."""
        result = resolve_settlement_name("", {})
        self.assertEqual(result, "(unknown:)")


class TestPatchUnknownSettlements(unittest.TestCase):
    """Tests for patch_unknown_settlements(): targeted in-place correction."""

    def test_patches_unknown_entry_with_resolved_name(self) -> None:
        """patch_unknown_settlements replaces (unknown:...) with a real name."""
        # T7: targeted update — one unknown entry should be corrected
        with tempfile.TemporaryDirectory() as tmp:
            dim_path = Path(tmp) / "dim_settlement.csv"
            with open(dim_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["settlement_key", "ekatte", "settlement_name"])
                writer.writerow([1, "68134", "София"])
                writer.writerow([2, "2659", "(unknown:2659)"])
            lookup = {"02659": "Банкя"}
            count = patch_unknown_settlements(dim_path, lookup)
            self.assertEqual(count, 1)
            with open(dim_path, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            patched_row = next(r for r in rows if r["ekatte"] == "2659")
            self.assertEqual(patched_row["settlement_name"], "Банкя")

    def test_preserves_surrogate_keys(self) -> None:
        """patch_unknown_settlements does not change settlement_key values."""
        # T8: surrogate key preservation
        with tempfile.TemporaryDirectory() as tmp:
            dim_path = Path(tmp) / "dim_settlement.csv"
            with open(dim_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["settlement_key", "ekatte", "settlement_name"])
                writer.writerow([5, "2659", "(unknown:2659)"])
                writer.writerow([7, "68134", "София"])
            lookup = {"02659": "Банкя"}
            patch_unknown_settlements(dim_path, lookup)
            with open(dim_path, encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))
            key_map = {r["ekatte"]: r["settlement_key"] for r in rows}
            # Keys must remain at their original values.
            self.assertEqual(key_map["2659"], "5")
            self.assertEqual(key_map["68134"], "7")

    def test_idempotent_on_second_run(self) -> None:
        """patch_unknown_settlements returns 0 and makes no changes on a second run."""
        # T9: idempotency
        with tempfile.TemporaryDirectory() as tmp:
            dim_path = Path(tmp) / "dim_settlement.csv"
            with open(dim_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["settlement_key", "ekatte", "settlement_name"])
                writer.writerow([1, "2659", "(unknown:2659)"])
            lookup = {"02659": "Банкя"}
            # First run corrects the entry.
            count1 = patch_unknown_settlements(dim_path, lookup)
            self.assertEqual(count1, 1)
            # Second run finds nothing to patch.
            count2 = patch_unknown_settlements(dim_path, lookup)
            self.assertEqual(count2, 0)

    def test_returns_zero_when_file_absent(self) -> None:
        """patch_unknown_settlements returns 0 immediately when dim file does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "dim_settlement.csv"
            count = patch_unknown_settlements(missing, {"02659": "Банкя"})
            self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
