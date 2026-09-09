"""Tests for FraudLens API."""

import pytest
from fastapi.testclient import TestClient

from fraudlens.api.app import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
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
    def test_health_check(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "timestamp" in data


class TestScoreTransaction:
    def test_score_transaction_success(self, client, sample_transaction):
        response = client.post("/score-transaction", json=sample_transaction)

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

    def test_score_transaction_high_risk(self, client):
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
            "transactions_last_1h": 15,
        }

        response = client.post("/score-transaction", json=transaction)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] > 60
        assert data["risk_level"] in ["high", "critical"]
        assert len(data["risk_factors"]) > 0

    def test_score_transaction_low_risk(self, client):
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
            "transactions_last_1h": 1,
        }

        response = client.post("/score-transaction", json=transaction)

        assert response.status_code == 200
        data = response.json()
        assert data["risk_score"] < 40
        assert data["risk_level"] in ["low", "medium"]

    def test_score_transaction_missing_required_field(self, client):
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

        response = client.post("/score-transaction", json=transaction)

        assert response.status_code == 422

    def test_score_transaction_invalid_amount(self, client, sample_transaction):
        """Test invalid amount (negative)."""
        sample_transaction["amount_ngn"] = -100

        response = client.post("/score-transaction", json=sample_transaction)

        assert response.status_code == 422

    def test_score_transaction_invalid_risk_level(self, client):
        """Test response schema validation."""
        response = client.post("/score-transaction", json={
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
        # Verify risk_level is valid
        assert data["risk_level"] in ["low", "medium", "high", "critical"]


class TestAPIMetadata:
    def test_openapi_schema(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/health" in schema["paths"]
        assert "/score-transaction" in schema["paths"]
