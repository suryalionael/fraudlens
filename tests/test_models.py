"""Tests for model training and evaluation."""

import numpy as np
import pandas as pd
import pytest

from fraudlens.models.evaluator import ModelEvaluator
from fraudlens.models.trainer import ModelTrainer


def create_sample_data(
    n_samples: int = 1000, fraud_rate: float = 0.036
) -> pd.DataFrame:
    """Create sample transaction data for testing."""
    np.random.seed(42)

    n_fraud = int(n_samples * fraud_rate)
    n_legit = n_samples - n_fraud

    # Generate features
    data = {
        "transaction_id": [f"T{i:06d}" for i in range(n_samples)],
        "timestamp": pd.date_range("2023-01-01", periods=n_samples, freq="min"),
        "amount_ngn": np.concatenate(
            [
                np.random.lognormal(10, 1.5, n_legit),
                np.random.lognormal(11, 2, n_fraud),
            ]
        ),
        "customer_transaction_count_prior": np.random.poisson(10, n_samples),
        "customer_avg_amount_prior": np.random.lognormal(10, 1, n_samples),
        "customer_std_amount_prior": np.random.exponential(1000, n_samples),
        "customer_max_amount_prior": np.random.lognormal(11, 1.5, n_samples),
        "amount_ratio_to_avg": np.random.lognormal(0, 0.5, n_samples),
        "amount_zscore": np.random.normal(0, 1, n_samples),
        "merchant_transaction_count_prior": np.random.poisson(100, n_samples),
        "merchant_fraud_rate_prior": np.random.beta(1, 50, n_samples),
        "location_transaction_count_prior": np.random.poisson(500, n_samples),
        "location_fraud_rate_prior": np.random.beta(1, 30, n_samples),
        "device_transaction_count_prior": np.random.poisson(5, n_samples),
        "device_first_seen": np.random.choice([True, False], n_samples, p=[0.3, 0.7]),
        "is_fraud": np.concatenate(
            [
                np.zeros(n_legit, dtype=bool),
                np.ones(n_fraud, dtype=bool),
            ]
        ),
    }

    df = pd.DataFrame(data)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


class TestModelTrainer:
    def test_initialization(self):
        trainer = ModelTrainer()
        assert trainer.config is not None
        assert trainer.scaler is not None

    def test_prepare_features(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)

        assert X.shape[0] == len(df)
        assert y.shape[0] == len(df)
        assert "is_fraud" not in X.columns

    def test_train_test_split(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)
        X_train, X_test, y_train, _ = trainer.train_test_split(X, y)

        assert len(X_train) + len(X_test) == len(X)
        assert len(y_train) + len(_) == len(y)

    def test_train_logistic_regression(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)
        X_train, X_test, y_train, _ = trainer.train_test_split(X, y)

        scaler = trainer.scaler
        X_train_scaled = pd.DataFrame(
            scaler.fit_transform(X_train),
            columns=X_train.columns,
        )
        X_test_scaled = pd.DataFrame(
            scaler.transform(X_test),
            columns=X_test.columns,
        )

        model, y_prob = trainer.train_logistic_regression(
            X_train_scaled, y_train, X_test_scaled
        )

        assert model is not None
        assert len(y_prob) == len(X_test)
        assert all(0 <= p <= 1 for p in y_prob)

    def test_train_random_forest(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)
        X_train, X_test, y_train, _ = trainer.train_test_split(X, y)

        model, y_prob = trainer.train_random_forest(X_train, y_train, X_test)

        assert model is not None
        assert len(y_prob) == len(X_test)
        assert all(0 <= p <= 1 for p in y_prob)

    def test_train_xgboost(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)
        X_train, X_test, y_train, _ = trainer.train_test_split(X, y)

        try:
            model, y_prob = trainer.train_xgboost(X_train, y_train, X_test)
            assert model is not None
            assert len(y_prob) == len(X_test)
            assert all(0 <= p <= 1 for p in y_prob)
        except ImportError:
            pytest.skip("XGBoost not installed")

    def test_train_all(self):
        df = create_sample_data()
        trainer = ModelTrainer()
        results = trainer.train_all(df)

        assert len(results) == 3
        assert "logistic_regression" in results
        assert "random_forest" in results
        assert "xgboost" in results

    def test_save_model(self, tmp_path):
        df = create_sample_data()
        trainer = ModelTrainer()
        X, y = trainer.prepare_features(df)
        X_train, X_test, y_train, _ = trainer.train_test_split(X, y)

        model, _ = trainer.train_random_forest(X_train, y_train, X_test)
        path = trainer.save_model(model, "test_model", tmp_path)

        assert path.exists()


class TestModelEvaluator:
    def test_initialization(self):
        evaluator = ModelEvaluator()
        assert evaluator.results == {}

    def test_evaluate(self):
        np.random.seed(42)
        y_true = np.array([0] * 964 + [1] * 36)
        y_prob = np.random.beta(1, 50, 1000)
        # Make fraud cases have higher probabilities
        y_prob[y_true == 1] = np.random.beta(5, 1, 36)

        evaluator = ModelEvaluator()
        result = evaluator.evaluate(y_true, y_prob, "test_model")

        assert result.model_name == "test_model"
        assert 0 <= result.pr_auc <= 1
        assert 0 <= result.roc_auc <= 1
        assert 0 <= result.precision <= 1
        assert 0 <= result.recall <= 1
        assert 0 <= result.f1 <= 1
        assert 0 < result.optimal_threshold < 1

    def test_precision_at_k(self):
        np.random.seed(42)
        y_true = np.array([0] * 964 + [1] * 36)
        y_prob = np.random.beta(1, 50, 1000)
        y_prob[y_true == 1] = np.random.beta(5, 1, 36)

        evaluator = ModelEvaluator()
        result = evaluator.evaluate(y_true, y_prob, "test_model", k_values=[100, 500])

        assert 100 in result.precision_at_k
        assert 500 in result.precision_at_k
        assert 0 <= result.precision_at_k[100] <= 1
        assert 0 <= result.precision_at_k[500] <= 1

    def test_compare_models(self):
        np.random.seed(42)
        y_true = np.array([0] * 964 + [1] * 36)

        evaluator = ModelEvaluator()

        # Model 1
        y_prob1 = np.random.beta(1, 50, 1000)
        y_prob1[y_true == 1] = np.random.beta(5, 1, 36)
        evaluator.evaluate(y_true, y_prob1, "model_1")

        # Model 2
        y_prob2 = np.random.beta(1, 50, 1000)
        y_prob2[y_true == 1] = np.random.beta(3, 1, 36)
        evaluator.evaluate(y_true, y_prob2, "model_2")

        comparison = evaluator.compare_models()

        assert len(comparison) == 2
        assert "model" in comparison.columns
        assert "pr_auc" in comparison.columns

    def test_get_summary(self):
        np.random.seed(42)
        y_true = np.array([0] * 964 + [1] * 36)
        y_prob = np.random.beta(1, 50, 1000)
        y_prob[y_true == 1] = np.random.beta(5, 1, 36)

        evaluator = ModelEvaluator()
        evaluator.evaluate(y_true, y_prob, "test_model")
        summary = evaluator.get_summary()

        assert "Model Evaluation Summary" in summary
        assert "test_model" in summary
