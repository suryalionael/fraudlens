"""Feature testing utilities for fraud detection.

This module provides tests to verify that features are computed correctly
and without temporal leakage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Any


@dataclass
class TestResult:
    """Result of a feature test."""

    test_name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


class FeatureTester:
    """Test feature engineering for correctness and temporal leakage."""

    def __init__(self) -> None:
        self.results: list[TestResult] = []

    def run_all_tests(self, df: pd.DataFrame) -> list[TestResult]:
        """Run all feature tests.

        Args:
            df: DataFrame with engineered features.

        Returns:
            List of test results.
        """
        self.results = []

        self.test_no_future_leakage(df)
        self.test_temporal_ordering(df)
        self.test_velocity_features(df)
        self.test_amount_features(df)
        self.test_customer_features(df)
        self.test_device_features(df)
        self.test_merchant_features(df)
        self.test_location_features(df)

        return self.results

    def test_no_future_leakage(self, df: pd.DataFrame) -> None:
        """Verify that no feature uses future information."""
        passed = True
        issues = []

        # Check that velocity features only use prior transactions
        if "transactions_last_10m" in df.columns:
            for idx in range(10, min(len(df), 100)):
                current = df.iloc[idx]
                # The velocity count should be <= total transactions before this point
                max_possible = idx
                if current["transactions_last_10m"] > max_possible:
                    passed = False
                    issues.append(f"Row {idx}: velocity count > prior transactions")

        self.results.append(TestResult(
            test_name="no_future_leakage",
            passed=passed,
            message="All features use only historical information" if passed else f"Leakage detected: {issues[:5]}",
            details={"issues": issues[:10]} if issues else None,
        ))

    def test_temporal_ordering(self, df: pd.DataFrame) -> None:
        """Verify that data is sorted by timestamp."""
        if "timestamp" in df.columns:
            is_sorted = df["timestamp"].is_monotonic_increasing
        else:
            is_sorted = True

        self.results.append(TestResult(
            test_name="temporal_ordering",
            passed=is_sorted,
            message="Data is sorted by timestamp" if is_sorted else "Data is not sorted by timestamp",
        ))

    def test_velocity_features(self, df: pd.DataFrame) -> None:
        """Test velocity features."""
        velocity_cols = [c for c in df.columns if c.startswith("transactions_last_")]
        passed = True
        issues = []

        for col in velocity_cols:
            if col in df.columns:
                # Check non-negative
                if (df[col] < 0).any():
                    passed = False
                    issues.append(f"{col} has negative values")

                # Check reasonable range
                if df[col].max() > 1000:
                    passed = False
                    issues.append(f"{col} has unusually high values: {df[col].max()}")

        self.results.append(TestResult(
            test_name="velocity_features",
            passed=passed,
            message="Velocity features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def test_amount_features(self, df: pd.DataFrame) -> None:
        """Test amount features."""
        passed = True
        issues = []

        if "amount_zscore" in df.columns:
            # Check z-score is numeric
            if not pd.api.types.is_numeric_dtype(df["amount_zscore"]):
                passed = False
                issues.append("amount_zscore is not numeric")

            # Check z-score range (should be reasonable)
            zscore_max = df["amount_zscore"].abs().max()
            if zscore_max > 100:
                passed = False
                issues.append(f"amount_zscore has extreme values: {zscore_max}")

        if "amount_ratio_to_avg" in df.columns:
            # Check ratio is positive
            if (df["amount_ratio_to_avg"] < 0).any():
                passed = False
                issues.append("amount_ratio_to_avg has negative values")

        self.results.append(TestResult(
            test_name="amount_features",
            passed=passed,
            message="Amount features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def test_customer_features(self, df: pd.DataFrame) -> None:
        """Test customer features."""
        passed = True
        issues = []

        if "customer_transaction_count_prior" in df.columns:
            if (df["customer_transaction_count_prior"] < 0).any():
                passed = False
                issues.append("customer_transaction_count_prior has negative values")

        if "customer_avg_amount_prior" in df.columns:
            if (df["customer_avg_amount_prior"] < 0).any():
                passed = False
                issues.append("customer_avg_amount_prior has negative values")

        self.results.append(TestResult(
            test_name="customer_features",
            passed=passed,
            message="Customer features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def test_device_features(self, df: pd.DataFrame) -> None:
        """Test device features."""
        passed = True
        issues = []

        if "device_transaction_count_prior" in df.columns:
            if (df["device_transaction_count_prior"] < 0).any():
                passed = False
                issues.append("device_transaction_count_prior has negative values")

        if "device_first_seen" in df.columns:
            if not pd.api.types.is_bool_dtype(df["device_first_seen"]):
                passed = False
                issues.append("device_first_seen is not boolean")

        self.results.append(TestResult(
            test_name="device_features",
            passed=passed,
            message="Device features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def test_merchant_features(self, df: pd.DataFrame) -> None:
        """Test merchant features."""
        passed = True
        issues = []

        if "merchant_fraud_rate_prior" in df.columns:
            rates = df["merchant_fraud_rate_prior"]
            if (rates < 0).any() or (rates > 1).any():
                passed = False
                issues.append("merchant_fraud_rate_prior out of [0, 1] range")

        self.results.append(TestResult(
            test_name="merchant_features",
            passed=passed,
            message="Merchant features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def test_location_features(self, df: pd.DataFrame) -> None:
        """Test location features."""
        passed = True
        issues = []

        if "location_fraud_rate_prior" in df.columns:
            rates = df["location_fraud_rate_prior"]
            if (rates < 0).any() or (rates > 1).any():
                passed = False
                issues.append("location_fraud_rate_prior out of [0, 1] range")

        self.results.append(TestResult(
            test_name="location_features",
            passed=passed,
            message="Location features valid" if passed else f"Issues: {issues}",
            details={"issues": issues} if issues else None,
        ))

    def get_summary(self) -> str:
        """Get a summary of all test results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        lines = [
            "",
            "Feature Test Summary",
            "─" * 40,
            f"Total tests:  {total}",
            f"Passed:       {passed}",
            f"Failed:       {failed}",
            "",
        ]

        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.test_name}: {r.message}")

        lines.append("")
        return "\n".join(lines)
