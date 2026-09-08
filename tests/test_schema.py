"""Tests for source schema validation."""

from pathlib import Path

import pytest

from fraudlens.ingestion.schema import EXPECTED_COLUMNS, validate_source_schema

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES / "sample_transactions.csv"


class TestValidateSourceSchema:
    def test_valid_schema_passes(self):
        is_valid, errors = validate_source_schema(SAMPLE_CSV)
        assert is_valid is True
        assert errors == []

    def test_missing_file_fails(self):
        is_valid, errors = validate_source_schema(Path("nonexistent.csv"))
        assert is_valid is False
        assert any("not found" in e.lower() for e in errors)

    def test_missing_column_detected(self, tmp_path: Path):
        bad_csv = tmp_path / "bad.csv"
        cols = [c for c in EXPECTED_COLUMNS if c != "amount_ngn"]
        header = ",".join(cols)
        bad_csv.write_text(f"{header}\nrow1\n")
        is_valid, errors = validate_source_schema(bad_csv)
        assert is_valid is False
        assert any("amount_ngn" in e for e in errors)

    def test_extra_column_detected(self, tmp_path: Path):
        bad_csv = tmp_path / "extra.csv"
        cols = EXPECTED_COLUMNS + ["suspicious_col"]
        header = ",".join(cols)
        bad_csv.write_text(f"{header}\nrow1\n")
        is_valid, errors = validate_source_schema(bad_csv)
        assert is_valid is False
        assert any("suspicious_col" in e for e in errors)

    def test_expected_columns_count(self):
        assert len(EXPECTED_COLUMNS) == 21
