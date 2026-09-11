"""Tests for FraudLens API — Phase 10 real-time scoring."""

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
    np.random.seed(42)
    n = 500
    n_fraud = 25

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
    artifact_path = train_and_persist_model(
        df, output_dir=str(tmp_dir), model_name="random_forest"
    )
    return artifact_path


@pytest.fixture
def client_with_model(trained_model_path, _db_initialized):
    """Create a test client with a loaded model (database initialized)."""
    app = create_app(model_path=str(trained_model_path))
    return TestClient(app)


@pytest.fixture
def client_no_model(tmp_path):
    """Create a test client without a model."""
    app = create_app(model_path=str(tmp_path / "nonexistent.pkl"))
    return TestClient(app)


@pytest.fixture
def sample_transaction():
    """Sample raw transaction (Phase 10 schema — no precomputed features)."""
    return {
        "transaction_id": "T_TEST_001",
        "timestamp": "2023-06-15T10:30:00Z",
        "amount_ngn": 50000.00,
        "transaction_type": "transfer",
        "merchant_category": "electronics",
        "location": "Lagos",
        "device_used": "mobile",
        "payment_channel": "Bank Transfer",
        "ip_address": "192.168.1.1",
        "device_hash": "D1234567",
        "bvn_linked": True,
        "sender_persona": "Trader",
        "sender_account": "ACC001",
        "receiver_account": "ACC002",
    }


class TestHealthEndpoint:
    def test_health_check_with_model(self, client_with_model):
        response = client_with_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert "model_version" in data

    def test_health_check_without_model(self, client_no_model):
        response = client_no_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["model_loaded"] is False

    def test_readiness_without_model(self, client_no_model):
        response = client_no_model.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is False


class TestRequestValidation:
    def test_missing_required_field(self, client_with_model):
        transaction = {
            "transaction_id": "T_MISSING",
            "timestamp": "2023-06-15T10:30:00Z",
            "amount_ngn": 50000.00,
            # Missing sender_account
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D1234567",
            "bvn_linked": True,
            "sender_persona": "Trader",
        }
        response = client_with_model.post("/score-transaction", json=transaction)
        assert response.status_code == 422

    def test_invalid_amount_negative(self, client_with_model, sample_transaction):
        sample_transaction["amount_ngn"] = -100
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_invalid_amount_zero(self, client_with_model, sample_transaction):
        sample_transaction["amount_ngn"] = 0
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_invalid_timestamp(self, client_with_model, sample_transaction):
        sample_transaction["timestamp"] = "not-a-date"
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_future_timestamp_rejected(self, client_with_model, sample_transaction):
        sample_transaction["timestamp"] = "2099-01-01T00:00:00Z"
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 400

    def test_unknown_field_rejected(self, client_with_model, sample_transaction):
        sample_transaction["unknown_field"] = "value"
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_forbidden_precomputed_field(self, client_with_model, sample_transaction):
        """Precomputed features from source dataset must be rejected."""
        sample_transaction["velocity_score"] = 10
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_empty_transaction_id(self, client_with_model, sample_transaction):
        sample_transaction["transaction_id"] = ""
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_whitespace_transaction_id(self, client_with_model, sample_transaction):
        sample_transaction["transaction_id"] = "   "
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422

    def test_empty_string_field(self, client_with_model, sample_transaction):
        sample_transaction["sender_account"] = ""
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 422


class TestScoreTransaction:
    def test_score_transaction_success(self, client_with_model, sample_transaction):
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 200
        data = response.json()
        assert data["transaction_id"] == "T_TEST_001"
        assert 0 <= data["fraud_probability"] <= 1
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_level"] in ["low", "medium", "high", "critical"]
        assert data["recommended_action"] in [
            "allow",
            "monitor",
            "review",
            "urgent_review",
        ]
        assert isinstance(data["risk_factors"], list)
        assert "model_version" in data
        assert "risk_engine_version" in data
        assert "scored_at" in data
        assert data["model_version"].startswith("fraudlens-")

    def test_score_returns_503_without_model(self, client_no_model, sample_transaction):
        response = client_no_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 503

    def test_score_response_schema(self, client_with_model, sample_transaction):
        response = client_with_model.post("/score-transaction", json=sample_transaction)
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] in ["low", "medium", "high", "critical"]
        assert data["recommended_action"] in [
            "allow",
            "monitor",
            "review",
            "urgent_review",
        ]

    def test_score_with_minimal_transaction(self, client_with_model):
        """Test scoring with only required fields."""
        transaction = {
            "transaction_id": "T_MINIMAL",
            "timestamp": "2023-06-15T10:30:00Z",
            "amount_ngn": 5000.00,
            "transaction_type": "deposit",
            "merchant_category": "banking",
            "location": "Abuja",
            "device_used": "atm",
            "payment_channel": "ATM",
            "ip_address": "10.0.0.1",
            "device_hash": "D_MINIMAL",
            "bvn_linked": False,
            "sender_persona": "individual",
            "sender_account": "ACC_MIN",
            "receiver_account": "ACC_MIN_R",
        }
        response = client_with_model.post("/score-transaction", json=transaction)
        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["fraud_probability"] <= 1


class TestIdempotency:
    def test_same_transaction_returns_same_result(
        self, client_with_model, sample_transaction
    ):
        """Duplicate requests should return the same result."""
        r1 = client_with_model.post("/score-transaction", json=sample_transaction)
        assert r1.status_code == 200

        r2 = client_with_model.post("/score-transaction", json=sample_transaction)
        assert r2.status_code == 200

        d1 = r1.json()
        d2 = r2.json()
        assert d1["transaction_id"] == d2["transaction_id"]
        assert d1["fraud_probability"] == d2["fraud_probability"]
        assert d1["risk_score"] == d2["risk_score"]


class TestAPIMetadata:
    def test_openapi_schema(self, client_with_model):
        response = client_with_model.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/ready" in schema["paths"]
        assert "/score-transaction" in schema["paths"]
