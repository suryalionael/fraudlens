"""Tests for FraudLens API."""

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from fraudlens.api.app import create_app
from fraudlens.models.serving import train_and_persist_model


@pytest.fixture(scope="module")
def trained_model_path(tmp_path_factory):
    """Train a small model and return the artifact path."""
    tmp_dir = tmp_path_factory.mktemp("models")

    # Create a small deterministic dataset for testing
    np.random.seed(42)
    n = 500
    n_fraud = 25
    n_legit = n - n_fraud

    # Distribute fraud cases throughout the dataset
    fraud_indices = np.random.choice(n, size=n_fraud, replace=False)
    is_fraud = np.zeros(n, dtype=bool)
    is_fraud[fraud_indices] = True

    amounts = np.random.lognormal(10, 1, n)
    amounts[is_fraud] = np.random.lognormal(11, 2, n_fraud)

    data = {
        "transaction_id": [f"T{i:06d}" for i in range(n)],
        "timestamp": pd.date_range("2023-01-01", periods=n, freq="min"),
        "amount_ngn": amounts,
        "is_fraud": is_fraud,
        "customer_transaction_count_prior": np.random.poisson(10, n),
        "customer_avg_amount_prior": np.random.lognormal(10, 1, n),
        "customer_std_amount_prior": np.random.exponential(1000, n),
        "customer_max_amount_prior": np.random.lognormal(11, 1.5, n),
        "amount_ratio_to_avg": np.random.lognormal(0, 0.5, n),
        "amount_zscore": np.random.normal(0, 1, n),
        "merchant_transaction_count_prior": np.random.poisson(100, n),
        "merchant_fraud_rate_prior": np.random.beta(1, 50, n),
        "location_transaction_count_prior": np.random.poisson(500, n),
        "location_fraud_rate_prior": np.random.beta(1, 30, n),
        "device_transaction_count_prior": np.random.poisson(5, n),
        "device_first_seen": np.random.choice([True, False], n, p=[0.3, 0.7]),
        "transactions_last_10m": np.random.poisson(2, n),
        "transactions_last_60m": np.random.poisson(5, n),
        "transactions_last_1440m": np.random.poisson(20, n),
        "hour_of_day": np.random.randint(0, 24, n),
        "day_of_week": np.random.randint(0, 7, n),
        "is_weekend": np.random.choice([0, 1], n, p=[0.7, 0.3]),
    }

    df = pd.DataFrame(data)
    artifact_path = train_and_persist_model(df, output_dir=str(tmp_dir), model_name="random_forest")
    return artifact_path


@pytest.fixture
def client_with_model(trained_model_path):
    """Create a test client with a loaded model."""
    app = create_app(model_path=str(trained_model_path))
    return TestClient(app)


@pytest.fixture
def client_no_model(tmp_path):
    """Create a test client without a model."""
    app = create_app(model_path=str(tmp_path / "nonexistent.pkl"))
    return TestClient(app)


@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        "transaction_id": "T_TEST_001",
        "sender_account": "ACC001",
        "receiver_account": "ACC002",
        "transaction_type": "transfer",
        "merchant_category": "electronics",
        "location": "Lagos",
        "device_used": "mobile",
        "amount_ngn": 50000.00,
        "payment_channel": "Bank Transfer",
        "ip_address": "192.168.1.1",
        "device_hash": "D1234567",
        "sender_persona": "Trader",
    }


class TestHealthEndpoint:
    def test_health_check_with_model(self, client_with_model):
        response = client_with_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert "model_version" in data
        assert "version" in data
        assert "timestamp" in data

    def test_health_check_without_model(self, client_no_model):
        response = client_no_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["model_loaded"] is False


class TestScoreTransaction:
    def test_score_transaction_success(self, client_with_model, sample_transaction):
        response = client_with_model.post("/score-transaction", json=sample_transaction)

        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == "T_TEST_001"
        assert 0 <= data["fraud_probability"] <= 1
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_level"] in ["low", "medium", "high", "critical"]
        assert data["recommended_action"] in ["allow", "monitor", "review", "urgent_review"]
        assert isinstance(data["risk_factors"], list)
        assert "model_version" in data
        assert "risk_engine_version" in data
        assert "scored_at" in data
        # Verify model_version is real, not hardcoded
        assert data["model_version"].startswith("fraudlens-")

    def test_score_transaction_high_risk(self, client_with_model):
        """Test high-risk transaction."""
        transaction = {
            "transaction_id": "T_HIGH_RISK",
            "sender_account": "ACC001",
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "amount_ngn": 500000.00,
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D_NEW_DEVICE",
            "sender_persona": "Trader",
            "customer_avg_amount_prior": 10000.00,
            "amount_zscore": 3.5,
            "amount_ratio_to_avg": 50.0,
            "device_first_seen": True,
            "merchant_fraud_rate_prior": 0.15,
            "location_fraud_rate_prior": 0.12,
            "transactions_last_10m": 15,
            "transactions_last_60m": 30,
            "transactions_last_1440m": 50,
        }

        response = client_with_model.post("/score-transaction", json=transaction)

        assert response.status_code == 200
        data = response.json()
        # With real model, high-risk features should produce elevated risk
        assert data["fraud_probability"] > 0
        assert data["risk_score"] > 0
        assert len(data["risk_factors"]) > 0

    def test_score_transaction_low_risk(self, client_with_model):
        """Test low-risk transaction."""
        transaction = {
            "transaction_id": "T_LOW_RISK",
            "sender_account": "ACC001",
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "groceries",
            "location": "Lagos",
            "device_used": "mobile",
            "amount_ngn": 5000.00,
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D1234567",
            "sender_persona": "Trader",
            "customer_avg_amount_prior": 4500.00,
            "amount_zscore": 0.5,
            "amount_ratio_to_avg": 1.1,
            "device_first_seen": False,
            "merchant_fraud_rate_prior": 0.01,
            "location_fraud_rate_prior": 0.02,
            "transactions_last_10m": 1,
            "transactions_last_60m": 2,
            "transactions_last_1440m": 5,
        }

        response = client_with_model.post("/score-transaction", json=transaction)

        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["fraud_probability"] <= 1
        assert 0 <= data["risk_score"] <= 100

    def test_score_returns_503_without_model(self, client_no_model, sample_transaction):
        """Test that scoring returns 503 when model is not loaded."""
        response = client_no_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 503

    def test_score_transaction_missing_required_field(self, client_with_model):
        """Test missing required field."""
        transaction = {
            "transaction_id": "T_MISSING",
            # Missing sender_account
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "amount_ngn": 50000.00,
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D1234567",
            "sender_persona": "Trader",
        }

        response = client_with_model.post("/score-transaction", json=transaction)
        assert response.status_code == 422

    def test_score_transaction_invalid_amount(self, client_with_model, sample_transaction):
        """Test invalid amount (negative)."""
        sample_transaction["amount_ngn"] = -100
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_score_transaction_schema_valid(self, client_with_model):
        """Test response schema validation."""
        response = client_with_model.post("/score-transaction", json={
            "transaction_id": "T_SCHEMA",
            "sender_account": "ACC001",
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "amount_ngn": 50000.00,
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D1234567",
            "sender_persona": "Trader",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] in ["low", "medium", "high", "critical"]
        assert data["recommended_action"] in ["allow", "monitor", "review", "urgent_review"]


class TestAPIMetadata:
    def test_openapi_schema(self, client_with_model):
        """Test that OpenAPI schema is available."""
        response = client_with_model.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/score-transaction" in schema["paths"]
