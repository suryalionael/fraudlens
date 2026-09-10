"""Tests for model serving, SHAP explainer, feature preparation, and end-to-end integration."""

import json
import numpy as np
import pandas as pd
import pytest

from fraudlens.features.preparation import (
    MODEL_FEATURES,
    prepare_features_from_dataframe,
    prepare_features_from_transaction,
    get_model_features,
)
from fraudlens.models.serving import (
    ModelArtifact,
    train_and_persist_model,
    load_model_artifact,
    predict_probability,
)
from fraudlens.models.explainer import (
    explain_prediction,
    format_explanation_for_api,
)


@pytest.fixture(scope="module")
def trained_model_path(tmp_path_factory):
    """Train a small model and return the artifact path."""
    tmp_dir = tmp_path_factory.mktemp("models")
    df = _make_sample_df(n=300)
    artifact_path = train_and_persist_model(
        df, output_dir=str(tmp_dir), model_name="random_forest"
    )
    return artifact_path


def _make_sample_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    """Create a small deterministic DataFrame for testing."""
    np.random.seed(seed)
    n_fraud = max(int(n * 0.05), 2)

    # Distribute fraud cases throughout the dataset (not all at the end)
    fraud_indices = np.random.choice(n, size=n_fraud, replace=False)
    is_fraud = np.zeros(n, dtype=bool)
    is_fraud[fraud_indices] = True

    amounts = np.random.lognormal(10, 1, n)
    amounts[is_fraud] = np.random.lognormal(11, 2, n_fraud)

    return pd.DataFrame(
        {
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
    )


class TestFeaturePreparation:
    def test_model_features_defined(self):
        """Verify MODEL_FEATURES is a well-defined list."""
        assert isinstance(MODEL_FEATURES, list)
        assert len(MODEL_FEATURES) > 0
        assert "amount_ngn" in MODEL_FEATURES
        assert "is_fraud" not in MODEL_FEATURES

    def test_get_model_features_returns_copy(self):
        """Verify get_model_features returns a copy."""
        f1 = get_model_features()
        f2 = get_model_features()
        assert f1 == f2
        assert f1 is not f2

    def test_prepare_features_from_dataframe(self):
        """Test DataFrame feature preparation."""
        df = _make_sample_df()
        X, cols = prepare_features_from_dataframe(df)

        assert list(cols) == MODEL_FEATURES
        assert X.shape[0] == len(df)
        assert X.shape[1] == len(MODEL_FEATURES)
        assert not X.isna().any().any()

    def test_prepare_features_from_transaction(self):
        """Test single transaction feature preparation."""
        transaction = {
            "transaction_id": "T001",
            "amount_ngn": 50000.0,
            "customer_transaction_count_prior": 10,
            "customer_avg_amount_prior": 45000.0,
            "device_first_seen": True,
            "amount_zscore": 2.5,
            "merchant_fraud_rate_prior": 0.05,
        }

        features = prepare_features_from_transaction(transaction)

        assert isinstance(features, dict)
        assert set(features.keys()) == set(MODEL_FEATURES)
        assert all(isinstance(v, float) for v in features.values())
        assert features["amount_ngn"] == 50000.0
        assert features["device_first_seen_int"] == 1.0
        assert features["customer_transaction_count_prior"] == 10.0

    def test_prepare_features_handles_missing_fields(self):
        """Test that missing fields default to 0."""
        transaction = {"transaction_id": "T001", "amount_ngn": 1000.0}
        features = prepare_features_from_transaction(transaction)

        assert all(
            v == 0.0
            for k, v in features.items()
            if k not in ("amount_ngn", "amount_ratio_to_avg")
        )

    def test_feature_parity_between_dataframe_and_transaction(self):
        """Verify that DataFrame and transaction preparation produce the same features."""
        df = _make_sample_df(n=10)
        X_df, _ = prepare_features_from_dataframe(df)

        for i in range(min(3, len(df))):
            row_dict = df.iloc[i].to_dict()
            row_features = prepare_features_from_transaction(row_dict)
            for col in MODEL_FEATURES:
                assert abs(X_df.iloc[i][col] - row_features[col]) < 1e-6, (
                    f"Feature mismatch for {col} at row {i}: "
                    f"DataFrame={X_df.iloc[i][col]}, Transaction={row_features[col]}"
                )


class TestModelServing:
    def test_train_and_persist(self, tmp_path):
        """Test model training and persistence."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(
            df, output_dir=str(tmp_path), model_name="random_forest"
        )

        assert artifact_path.exists()
        assert artifact_path.name == "random_forest.artifact.pkl"

        # Metadata JSON should also exist
        metadata_path = tmp_path / "random_forest.metadata.json"
        assert metadata_path.exists()

        with open(metadata_path) as f:
            metadata = json.load(f)
        assert "evaluation" in metadata
        assert "pr_auc" in metadata["evaluation"]
        assert "feature_columns" in metadata

    def test_load_artifact(self, tmp_path):
        """Test loading a saved artifact."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))

        artifact = load_model_artifact(artifact_path)

        assert isinstance(artifact, ModelArtifact)
        assert artifact.model is not None
        assert artifact.scaler is None  # Random Forest doesn't use scaler
        assert artifact.model_version.startswith("fraudlens-")
        assert len(artifact.feature_columns) == len(MODEL_FEATURES)

    def test_load_nonexistent_raises(self, tmp_path):
        """Test that loading a nonexistent artifact raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_model_artifact(tmp_path / "nonexistent.pkl")

    def test_predict_probability(self, tmp_path):
        """Test probability prediction."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        features = {col: 0.0 for col in MODEL_FEATURES}
        features["amount_ngn"] = 50000.0
        prob = predict_probability(artifact, features)

        assert 0.0 <= prob <= 1.0

    def test_train_logistic_regression(self, tmp_path):
        """Test logistic regression training."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(
            df, output_dir=str(tmp_path), model_name="logistic_regression"
        )

        artifact = load_model_artifact(artifact_path)
        assert artifact.scaler is not None
        assert artifact.model_version.startswith("fraudlens-lr-")


class TestSHAPExplainer:
    def test_explain_prediction_tree_model(self, tmp_path):
        """Test SHAP explanation for tree-based model."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        features = {col: 0.0 for col in MODEL_FEATURES}
        features["amount_ngn"] = 100000.0
        features["amount_zscore"] = 3.0

        import pandas as pd

        X = pd.DataFrame([features], columns=artifact.feature_columns)
        explanations = explain_prediction(
            artifact.model, artifact.feature_columns, X, top_k=5
        )

        assert isinstance(explanations, list)
        assert len(explanations) <= 5
        for exp in explanations:
            assert "feature" in exp
            assert "shap_value" in exp
            assert "direction" in exp
            assert exp["direction"] in ("increases_risk", "decreases_risk")

    def test_format_explanation_for_api(self):
        """Test API formatting of explanations."""
        explanations = [
            {
                "feature": "amount_zscore",
                "shap_value": 0.5,
                "direction": "increases_risk",
                "magnitude": 0.5,
            },
            {
                "feature": "device_first_seen_int",
                "shap_value": 0.3,
                "direction": "increases_risk",
                "magnitude": 0.3,
            },
        ]

        factors = format_explanation_for_api(explanations)

        assert len(factors) == 2
        assert "amount_zscore" in factors[0]
        assert "increases" in factors[0]

    def test_explain_deterministic(self, tmp_path):
        """Test that explanations are deterministic for same input."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        features = {col: 1.0 for col in MODEL_FEATURES}
        import pandas as pd

        X = pd.DataFrame([features], columns=artifact.feature_columns)

        exp1 = explain_prediction(artifact.model, artifact.feature_columns, X, top_k=3)
        exp2 = explain_prediction(artifact.model, artifact.feature_columns, X, top_k=3)

        assert exp1 == exp2


class TestEndToEndScoring:
    """End-to-end integration test: transaction → features → model → explanation → risk → API response."""

    def test_end_to_end_scoring(self, tmp_path):
        """Test the complete scoring pipeline."""
        # 1. Train model
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        # 2. Prepare transaction
        transaction = {
            "transaction_id": "T_E2E_001",
            "sender_account": "ACC001",
            "receiver_account": "ACC002",
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "amount_ngn": 100000.0,
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D_NEW",
            "sender_persona": "Trader",
            "customer_transaction_count_prior": 2,
            "customer_avg_amount_prior": 50000.0,
            "customer_std_amount_prior": 10000.0,
            "customer_max_amount_prior": 80000.0,
            "amount_ratio_to_avg": 2.0,
            "amount_zscore": 3.0,
            "merchant_transaction_count_prior": 50,
            "merchant_fraud_rate_prior": 0.12,
            "location_transaction_count_prior": 200,
            "location_fraud_rate_prior": 0.08,
            "device_transaction_count_prior": 0,
            "device_first_seen": True,
            "transactions_last_10m": 12,
            "transactions_last_60m": 20,
            "transactions_last_1440m": 40,
            "hour_of_day": 2,
            "day_of_week": 5,
            "is_weekend": 1,
        }

        # 3. Prepare features
        features = prepare_features_from_transaction(
            transaction, artifact.feature_columns
        )

        # 4. Model prediction
        fraud_prob = predict_probability(artifact, features)
        assert 0.0 <= fraud_prob <= 1.0

        # 5. SHAP explanation
        import pandas as pd

        X = pd.DataFrame([features], columns=artifact.feature_columns)
        explanations = explain_prediction(
            artifact.model, artifact.feature_columns, X, top_k=5
        )
        assert len(explanations) > 0

        # 6. Risk engine
        from fraudlens.risk.engine import RiskEngine

        engine = RiskEngine()
        risk_result = engine.assess_transaction(transaction, fraud_prob)

        assert risk_result.transaction_id == "T_E2E_001"
        assert 0 <= risk_result.risk_score <= 100
        assert risk_result.risk_level in ["low", "medium", "high", "critical"]

        # 7. Combine factors
        shap_factors = format_explanation_for_api(explanations)
        all_factors = risk_result.risk_factors + shap_factors
        assert len(all_factors) > 0

    def test_end_to_end_via_api(self, trained_model_path):
        """Test complete scoring through the FastAPI endpoint."""
        from fastapi.testclient import TestClient
        from fraudlens.api.app import create_app

        app = create_app(model_path=str(trained_model_path))
        client = TestClient(app)

        transaction = {
            "transaction_id": "T_API_E2E",
            "timestamp": "2023-06-15T10:30:00Z",
            "amount_ngn": 75000.0,
            "transaction_type": "transfer",
            "merchant_category": "electronics",
            "location": "Lagos",
            "device_used": "mobile",
            "payment_channel": "Bank Transfer",
            "ip_address": "192.168.1.1",
            "device_hash": "D_API",
            "bvn_linked": True,
            "sender_persona": "Trader",
            "sender_account": "ACC001",
            "receiver_account": "ACC002",
        }

        response = client.post("/score-transaction", json=transaction)

        assert response.status_code == 200
        data = response.json()

        # Verify complete response structure
        assert data["transaction_id"] == "T_API_E2E"
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
        assert data["model_version"].startswith("fraudlens-")
        assert data["risk_engine_version"] == "001"
        assert "scored_at" in data
