"""Tests for feature engineering module."""

from pathlib import Path

import pandas as pd

from fraudlens.features.engineering import FeatureEngineer
from fraudlens.features.tester import FeatureTester

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_CSV = FIXTURES / "sample_transactions.csv"


def load_sample_data() -> pd.DataFrame:
    """Load sample transaction data."""
    df = pd.read_csv(SAMPLE_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["is_fraud"] = df["is_fraud"].map(
        {"True": True, "False": False, "true": True, "false": False}
    )
    return df


class TestFeatureEngineer:
    def test_initialization(self):
        engineer = FeatureEngineer()
        assert engineer.config is not None

    def test_compute_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Check that new columns are added
        assert "hour_of_day" in result.columns
        assert "day_of_week" in result.columns
        assert "is_weekend" in result.columns
        assert "transactions_last_10m" in result.columns
        assert "transactions_last_60m" in result.columns
        assert "transactions_last_1440m" in result.columns
        assert "customer_transaction_count_prior" in result.columns
        assert "device_first_seen" in result.columns
        assert "merchant_fraud_rate_prior" in result.columns
        assert "location_fraud_rate_prior" in result.columns

    def test_temporal_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Check temporal features are valid
        assert result["hour_of_day"].between(0, 23).all()
        assert result["day_of_week"].between(0, 6).all()
        assert result["is_weekend"].isin([0, 1]).all()

    def test_velocity_features_non_negative(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Velocity features should be non-negative
        velocity_cols = [
            c for c in result.columns if c.startswith("transactions_last_")
        ]
        for col in velocity_cols:
            assert (result[col] >= 0).all(), f"{col} has negative values"

    def test_amount_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Amount ratio should be positive
        assert (result["amount_ratio_to_avg"] >= 0).all()

        # Z-score should be numeric
        assert pd.api.types.is_numeric_dtype(result["amount_zscore"])

    def test_customer_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Transaction count should be non-negative
        assert (result["customer_transaction_count_prior"] >= 0).all()

        # Average amount should be non-negative
        assert (result["customer_avg_amount_prior"] >= 0).all()

    def test_device_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Device transaction count should be non-negative
        assert (result["device_transaction_count_prior"] >= 0).all()

        # First seen should be boolean
        assert result["device_first_seen"].dtype == bool

    def test_merchant_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Fraud rate should be in [0, 1]
        assert (result["merchant_fraud_rate_prior"] >= 0).all()
        assert (result["merchant_fraud_rate_prior"] <= 1).all()

    def test_location_features(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        # Fraud rate should be in [0, 1]
        assert (result["location_fraud_rate_prior"] >= 0).all()
        assert (result["location_fraud_rate_prior"] <= 1).all()


class TestFeatureTester:
    def test_run_all_tests(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        tester = FeatureTester()
        results = tester.run_all_tests(result)

        # All tests should pass
        assert all(r.passed for r in results), tester.get_summary()

    def test_no_future_leakage(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        tester = FeatureTester()
        tester.test_no_future_leakage(result)

        leakage_test = [
            r for r in tester.results if r.test_name == "no_future_leakage"
        ][0]
        assert leakage_test.passed, leakage_test.message

    def test_temporal_ordering(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        tester = FeatureTester()
        tester.test_temporal_ordering(result)

        ordering_test = [
            r for r in tester.results if r.test_name == "temporal_ordering"
        ][0]
        assert ordering_test.passed, ordering_test.message

    def test_get_summary(self):
        df = load_sample_data()
        engineer = FeatureEngineer()
        result = engineer.compute_features(df)

        tester = FeatureTester()
        tester.run_all_tests(result)
        summary = tester.get_summary()

        assert "Feature Test Summary" in summary
        assert "Total tests:" in summary
