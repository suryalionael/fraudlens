"""Tests for the ingestion pipeline."""

from pathlib import Path

import pytest

from fraudlens.ingestion.pipeline import IngestionPipeline, IngestionReport
from fraudlens.ingestion.postgres_loader import DBConfig

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES / "sample_transactions.csv"


def _get_test_db_config() -> DBConfig | None:
    try:
        import psycopg2

        config = DBConfig.from_env()
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            dbname=config.dbname,
            user=config.user,
            password=config.password,
        )
        conn.close()
        return config
    except (ImportError, OSError):
        return None


class TestIngestionReport:
    def test_format_output(self):
        report = IngestionReport(
            source_file="test.csv",
            rows_read=1000,
            rows_loaded=1000,
            fraud_count=35,
            fraud_rate=3.5,
            status="SUCCESS",
        )
        output = report.format()
        assert "1,000" in output
        assert "SUCCESS" in output
        assert "3.5000%" in output


class TestIngestionPipeline:
    @pytest.fixture(autouse=True)
    def _skip_if_no_db(self):
        config = _get_test_db_config()
        if config is None:
            pytest.skip("PostgreSQL not available")
        self.config = config

    def test_pipeline_loads_sample(self):
        pipeline = IngestionPipeline(db_config=self.config, chunk_size=10)
        report = pipeline.run(SAMPLE_CSV, replace=True)
        assert report.status == "SUCCESS"
        assert report.rows_read == 5
        assert report.rows_loaded == 5
        assert report.fraud_count == 1

    def test_pipeline_idempotent_with_replace(self):
        pipeline = IngestionPipeline(db_config=self.config, chunk_size=10)
        r1 = pipeline.run(SAMPLE_CSV, replace=True)
        r2 = pipeline.run(SAMPLE_CSV, replace=True)
        assert r1.status == "SUCCESS"
        assert r2.status == "SUCCESS"
        assert r2.rows_loaded == 5

    def test_pipeline_rejects_when_no_replace(self):
        pipeline = IngestionPipeline(db_config=self.config, chunk_size=10)
        pipeline.run(SAMPLE_CSV, replace=True)  # seed data
        report = pipeline.run(SAMPLE_CSV, replace=False)
        assert report.status == "FAILED_IDEMPOTENCY"

    def test_missing_file_fails(self):
        pipeline = IngestionPipeline(db_config=self.config)
        report = pipeline.run(Path("nonexistent.csv"))
        assert report.status == "FAILED_SCHEMA"

    def test_report_sha256(self):
        pipeline = IngestionPipeline(db_config=self.config, chunk_size=10)
        report = pipeline.run(SAMPLE_CSV, replace=True)
        assert len(report.source_sha256) == 64

    def test_report_has_required_fields(self):
        pipeline = IngestionPipeline(db_config=self.config, chunk_size=10)
        report = pipeline.run(SAMPLE_CSV, replace=True)
        assert report.source_file
        assert report.rows_read == 5
        assert report.rows_loaded == 5
        assert report.fraud_count == 1
        assert report.status == "SUCCESS"
