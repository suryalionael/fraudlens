"""Shared test fixtures for FraudLens tests.

Provides session-scoped database initialization that creates the required
schemas (raw.*, risk.*) and seeds minimal deterministic transaction data
for integration tests.
"""

from __future__ import annotations

import psycopg2
import pytest

from fraudlens.ingestion.postgres_loader import DBConfig, PostgresLoader
from fraudlens.risk.storage import RiskScoreStore


def _get_test_db_config() -> DBConfig | None:
    """Return DBConfig if PostgreSQL is available."""
    try:
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
    except (ImportError, OSError, psycopg2.OperationalError):
        return None


@pytest.fixture(scope="session")
def db_config():
    """Session-scoped fixture: returns DBConfig if PostgreSQL is available."""
    config = _get_test_db_config()
    if config is None:
        pytest.skip("PostgreSQL not available")
    return config


@pytest.fixture(scope="session")
def _db_initialized(db_config):
    """Session-scoped fixture: creates schemas and seeds minimal test data.

    This runs once per test session and ensures that raw.* and risk.*
    schemas exist with deterministic seed data for integration tests.
    """
    # Create raw schema + tables
    loader = PostgresLoader(db_config)
    loader.create_schema_and_tables()

    # Create risk schema + tables
    risk_store = RiskScoreStore(db_config)
    risk_store.create_schema()

    # Seed minimal deterministic historical transactions
    # Timestamps are before the API test transactions (2023-06-15T10:30:00Z)
    seed_rows = [
        [
            "T_SEED_001",
            "2023-06-10 08:00:00",
            "ACC001",
            "ACCReceiver1",
            "transfer",
            "electronics",
            "Lagos",
            "mobile",
            "False",
            "",
            "",
            "",
            "",
            "",
            "Bank Transfer",
            "10.0.0.1",
            "D1234567",
            "25000.00",
            "True",
            "False",
            "Trader",
        ],
        [
            "T_SEED_002",
            "2023-06-12 14:30:00",
            "ACC001",
            "ACCReceiver2",
            "deposit",
            "banking",
            "Abuja",
            "atm",
            "False",
            "",
            "",
            "",
            "",
            "",
            "ATM",
            "10.0.0.2",
            "D7654321",
            "15000.00",
            "True",
            "False",
            "Trader",
        ],
        [
            "T_SEED_003",
            "2023-06-14 09:15:00",
            "ACC001",
            "ACCReceiver3",
            "transfer",
            "groceries",
            "Lagos",
            "pos",
            "False",
            "",
            "",
            "",
            "",
            "",
            "POS",
            "10.0.0.3",
            "D9998887",
            "8000.00",
            "True",
            "False",
            "Trader",
        ],
    ]

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

    loader.truncate_transactions()
    loader.bulk_insert(header, seed_rows)

    yield

    # Cleanup
    try:
        loader.truncate_transactions()
    except (OSError, psycopg2.Error):
        pass
    loader.close()
    risk_store.close()
