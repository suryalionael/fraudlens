"""Tests for the chunked CSV reader."""

from pathlib import Path

import pytest

from fraudlens.ingestion.csv_reader import compute_sha256, iter_chunks, read_csv

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES / "sample_transactions.csv"


class TestIterChunks:
    def test_yields_header_and_rows(self):
        chunks = list(iter_chunks(SAMPLE_CSV, chunk_size=10))
        assert len(chunks) >= 1
        header, rows = chunks[0]
        assert header[0] == "transaction_id"
        assert len(rows) > 0

    def test_chunk_size_limits_rows(self):
        chunks = list(iter_chunks(SAMPLE_CSV, chunk_size=2))
        # 5 rows, chunk_size=2 → 3 chunks (2+2+1)
        assert len(chunks) == 3
        _, first_chunk = chunks[0]
        assert len(first_chunk) == 2


class TestReadCsv:
    def test_reads_all_rows(self):
        total = 0
        for result, rows in read_csv(SAMPLE_CSV, chunk_size=2):
            total += len(rows)
        # The final chunk is empty (sentinel)
        assert total == 5

    def test_fraud_count(self):
        last_result = None
        for result, rows in read_csv(SAMPLE_CSV, chunk_size=10):
            last_result = result
        assert last_result is not None
        assert last_result.fraud_count == 1

    def test_sha256_computed(self):
        last_result = None
        for result, rows in read_csv(SAMPLE_CSV, chunk_size=10):
            last_result = result
        assert last_result is not None
        assert len(last_result.sha256) == 64

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            list(read_csv(Path("nonexistent.csv")))


class TestComputeSha256:
    def test_deterministic(self):
        h1 = compute_sha256(SAMPLE_CSV)
        h2 = compute_sha256(SAMPLE_CSV)
        assert h1 == h2

    def test_is_hex(self):
        h = compute_sha256(SAMPLE_CSV)
        assert all(c in "0123456789abcdef" for c in h)
