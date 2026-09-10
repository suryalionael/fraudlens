"""Tests for PostgreSQL loader and ingestion pipeline.

These tests require a running PostgreSQL instance.  They use a dedicated
test schema to avoid interfering with other databases.
"""

from pathlib import Path

import pytest

from fraudlens.ingestion.postgres_loader import DBConfig, PostgresLoader

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES / "sample_transactions.csv"


def _get_test_db_config() -> DBConfig | None:
    """Return a DBConfig if PostgreSQL is available, else None."""
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
    except Exception:
        return None


@pytest.fixture(scope="module")
def db_available():
    """Skip tests if PostgreSQL is not available."""
    config = _get_test_db_config()
    if config is None:
        pytest.skip("PostgreSQL not available")
    return config


@pytest.fixture(scope="module")
def loader(db_available):
    """Create a PostgresLoader connected to the test database."""
    ldr = PostgresLoader(db_available)
    ldr.create_schema_and_tables()
    yield ldr
    # Cleanup: truncate test data
    try:
        ldr.truncate_transactions()
    except Exception:
        pass
    ldr.close()


class TestPostgresLoader:
    def test_connect(self, loader):
        conn = loader.connect()
        assert conn is not None
        assert not conn.closed

    def test_create_schema_and_tables(self, loader):
        # Should not raise on second call (idempotent)
        loader.create_schema_and_tables()

    def test_truncate_transactions(self, loader):
        loader.truncate_transactions()
        assert loader.count_transactions() == 0

    def test_bulk_insert(self, loader):
        header = [
            "transaction_id",
            "timestamp",
            "sender_account",
            "receiver_account",
            "transaction_type",
            "merchant_category",
            "location",
            "device_used",
            "is_fraud",
            "fraud_type",
            "time_since_last_transaction",
            "spending_deviation_score",
            "velocity_score",
            "geo_anomaly_score",
            "payment_channel",
            "ip_address",
            "device_hash",
            "amount_ngn",
            "bvn_linked",
            "new_device_transaction",
            "sender_persona",
        ]
        rows = [
            [
                "T_TEST_1",
                "2023-01-01 12:00:00",
                "1111111111",
                "2222222222",
                "deposit",
                "ATM Withdrawal",
                "Lagos",
                "atm",
                "False",
                "",
                "5.0",
                "0.1",
                "3",
                "0.5",
                "Bank Transfer",
                "102.89.1.1",
                "D1234567",
                "10000.00",
                "True",
                "False",
                "Trader",
            ],
        ]
        loader.truncate_transactions()
        count = loader.bulk_insert(header, rows)
        assert count == 1
        assert loader.count_transactions() == 1

    def test_ingestion_run_lifecycle(self, loader):
        run_id = loader.insert_ingestion_run(
            source_name="test",
            source_version="V1",
            source_file="test.csv",
            source_sha256="abc123",
        )
        assert run_id > 0

        loader.update_ingestion_run(
            run_id,
            rows_read=100,
            rows_loaded=100,
            status="SUCCESS",
        )

        runs = loader.get_ingestion_runs()
        matching = [r for r in runs if r["ingestion_run_id"] == run_id]
        assert len(matching) == 1
        assert matching[0]["status"] == "SUCCESS"
        assert matching[0]["rows_read"] == 100
