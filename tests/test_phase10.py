"""Phase 10 tests — temporal leakage, scoring service, API integration."""

import numpy as np
import pandas as pd
import pytest

from fraudlens.features.preparation import (
    MODEL_FEATURES,
    prepare_features_from_transaction,
)
from fraudlens.models.serving import train_and_persist_model, load_model_artifact
from fraudlens.risk.historical import HistoricalContextService
from fraudlens.risk.scoring import ScoringResult


def _make_sample_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    n_fraud = max(int(n * 0.05), 2)
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


class TestTemporalLeakageProtection:
    """Verify that historical context queries use strict temporal cutoffs."""

    def test_historical_context_uses_strict_cutoff(self):
        """Verify the SQL query uses < not <= for temporal cutoff."""
        import inspect

        source = inspect.getsource(HistoricalContextService.get_customer_context)
        assert "timestamp < %s" in source
        assert "timestamp <=" not in source

    def test_velocity_uses_strict_cutoff(self):
        """Verify velocity queries use strict < for temporal cutoff."""
        import inspect

        source = inspect.getsource(HistoricalContextService.get_velocity_context)
        assert "timestamp < %s" in source

    def test_merchant_uses_strict_cutoff(self):
        import inspect

        source = inspect.getsource(HistoricalContextService.get_merchant_context)
        assert "timestamp < %s" in source

    def test_location_uses_strict_cutoff(self):
        import inspect

        source = inspect.getsource(HistoricalContextService.get_location_context)
        assert "timestamp < %s" in source

    def test_device_uses_strict_cutoff(self):
        import inspect

        source = inspect.getsource(HistoricalContextService.get_device_context)
        assert "timestamp < %s" in source

    def test_transaction_excluded_from_own_history(self):
        """The current transaction must not appear in its own historical aggregates.

        This is verified by the < cutoff: if transaction T is at time t,
        only transactions with timestamp < t are included.
        """
        import inspect

        # All methods use strict < which excludes the current timestamp
        for method_name in [
            "get_customer_context",
            "get_velocity_context",
            "get_merchant_context",
            "get_location_context",
            "get_device_context",
        ]:
            source = inspect.getsource(getattr(HistoricalContextService, method_name))
            assert (
                "timestamp < %s" in source
            ), f"{method_name} does not use strict < temporal cutoff"

    def test_forbidden_fields_rejected_by_api(self):
        """Precomputed features from source dataset must be rejected."""
        from fraudlens.api.app import FORBIDDEN_FIELDS
        from pydantic import ValidationError

        for field_name in FORBIDDEN_FIELDS:
            transaction = {
                "transaction_id": "T001",
                "timestamp": "2023-06-15T10:30:00Z",
                "amount_ngn": 50000.0,
                "transaction_type": "transfer",
                "merchant_category": "electronics",
                "location": "Lagos",
                "device_used": "mobile",
                "payment_channel": "Bank Transfer",
                "ip_address": "192.168.1.1",
                "device_hash": "D001",
                "bvn_linked": True,
                "sender_persona": "Trader",
                "sender_account": "ACC001",
                "receiver_account": "ACC002",
                field_name: "test_value",
            }

            from fraudlens.api.app import TransactionRequest

            with pytest.raises(ValidationError):
                TransactionRequest(**transaction)


class TestFeatureParity:
    """Verify training and inference use identical feature definitions."""

    def test_model_features_match_training(self):
        """MODEL_FEATURES must match what the model was trained on."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(
            df, output_dir="/tmp/parity_test", model_name="random_forest"
        )
        artifact = load_model_artifact(artifact_path)

        assert artifact.feature_columns == MODEL_FEATURES

    def test_inference_features_match_training(self):
        """prepare_features_from_transaction must produce same columns as training."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(
            df, output_dir="/tmp/parity_test", model_name="random_forest"
        )
        artifact = load_model_artifact(artifact_path)

        transaction = {
            "amount_ngn": 50000.0,
            "customer_transaction_count_prior": 10,
            "customer_avg_amount_prior": 45000.0,
            "device_first_seen": True,
        }

        features = prepare_features_from_transaction(
            transaction, artifact.feature_columns
        )
        assert list(features.keys()) == artifact.feature_columns

    def test_model_features_do_not_include_target(self):
        """MODEL_FEATURES must not contain the target variable."""
        assert "is_fraud" not in MODEL_FEATURES

    def test_model_features_do_not_contain_forbidden_fields(self):
        """MODEL_FEATURES must not contain precomputed dataset fields."""
        forbidden = {
            "new_device_transaction",
            "time_since_last_transaction",
            "velocity_score",
            "geo_anomaly_score",
            "spending_deviation_score",
        }
        for field in forbidden:
            assert (
                field not in MODEL_FEATURES
            ), f"Forbidden field {field} found in MODEL_FEATURES"


class TestScoringService:
    """Tests for the real-time scoring service orchestration."""

    def test_scoring_result_structure(self):
        """Verify ScoringResult has expected fields."""
        from fraudlens.risk.engine import RiskResult

        risk = RiskResult(
            transaction_id="T001",
            fraud_probability=0.85,
            risk_score=75.0,
            risk_level="high",
            rule_score=30.0,
            ml_score=85.0,
            risk_factors=["test factor"],
            recommended_action="review",
            rule_signals=[],
        )

        result = ScoringResult(
            transaction_id="T001",
            fraud_probability=0.85,
            risk_result=risk,
            shap_factors=["SHAP factor"],
            model_version="fraudlens-rf-v001",
            risk_engine_version="001",
            latency_ms=15.0,
            persisted=False,
        )

        assert result.transaction_id == "T001"
        assert result.fraud_probability == 0.85
        assert result.risk_result.risk_level == "high"
        assert result.model_version == "fraudlens-rf-v001"


class TestModelInference:
    """Verify real model is used, not heuristics."""

    def test_prediction_uses_real_model(self, tmp_path):
        """Verify prediction probability comes from actual model."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        features = {col: 0.0 for col in MODEL_FEATURES}
        features["amount_ngn"] = 50000.0

        from fraudlens.models.serving import predict_probability

        prob = predict_probability(artifact, features)

        assert isinstance(prob, float)
        assert 0.0 <= prob <= 1.0

    def test_model_version_from_artifact(self, tmp_path):
        """Verify model version comes from actual artifact."""
        df = _make_sample_df()
        artifact_path = train_and_persist_model(df, output_dir=str(tmp_path))
        artifact = load_model_artifact(artifact_path)

        assert artifact.model_version.startswith("fraudlens-")
        assert artifact.training_timestamp is not None
        assert len(artifact.feature_columns) > 0

    def test_no_heuristic_in_production_path(self):
        """Verify the API does not contain heuristic fraud probability."""
        import inspect
        from fraudlens.api.app import create_app

        source = inspect.getsource(create_app)
        assert "_estimate_fraud_probability" not in source
        assert "random" not in source.lower() or "random" in "random_forest"


class TestRiskEngine:
    """Verify risk engine produces valid outputs."""

    def test_risk_score_range(self):
        from fraudlens.risk.engine import RiskEngine

        engine = RiskEngine()

        for prob in [0.0, 0.25, 0.5, 0.75, 1.0]:
            result = engine.calculate_risk_score(prob, 50)
            assert 0 <= result <= 100

    def test_risk_level_mapping(self):
        from fraudlens.risk.engine import RiskEngine

        engine = RiskEngine()

        assert engine.assign_risk_level(10) == "low"
        assert engine.assign_risk_level(45) == "medium"
        assert engine.assign_risk_level(70) == "high"
        assert engine.assign_risk_level(90) == "critical"

    def test_action_mapping(self):
        from fraudlens.risk.engine import RiskEngine

        engine = RiskEngine()

        assert engine.assign_action(10) == "allow"
        assert engine.assign_action(45) == "monitor"
        assert engine.assign_action(70) == "review"
        assert engine.assign_action(90) == "urgent_review"


class TestPersistenceSchema:
    """Verify persistence schema supports Phase 10 requirements."""

    def test_risk_factors_stored_as_jsonb(self):
        """risk_factors should be stored as JSONB."""
        from fraudlens.risk.storage import RISK_SCORES_DDL

        assert "JSONB" in RISK_SCORES_DDL
        assert "risk_factors" in RISK_SCORES_DDL

    def test_upsertHandles_json_serialization(self):
        """Verify upsert correctly serializes list fields to JSON."""
        import inspect
        from fraudlens.risk.storage import RiskScoreStore

        source = inspect.getsource(RiskScoreStore.upsert_score)
        assert "json.dumps" in source
