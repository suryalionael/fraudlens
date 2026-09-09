"""Shared feature preparation for training and inference.

This module ensures that the same feature transformation logic is used
during both training and inference, preventing feature parity bugs.

The feature list is the single source of truth for which features
the model expects.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


# Canonical feature list used by the model.
# Training and inference MUST use exactly this set.
MODEL_FEATURES: list[str] = [
    "amount_ngn",
    "customer_transaction_count_prior",
    "customer_avg_amount_prior",
    "customer_std_amount_prior",
    "customer_max_amount_prior",
    "amount_ratio_to_avg",
    "amount_zscore",
    "merchant_transaction_count_prior",
    "merchant_fraud_rate_prior",
    "location_transaction_count_prior",
    "location_fraud_rate_prior",
    "device_transaction_count_prior",
    "device_first_seen_int",
    "transactions_last_10m",
    "transactions_last_60m",
    "transactions_last_1440m",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
]


def prepare_features_from_dataframe(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Prepare features from a DataFrame for training.

    Args:
        df: DataFrame with raw + engineered features.
        feature_columns: Override feature list. If None, uses MODEL_FEATURES.

    Returns:
        Tuple of (features DataFrame, feature column names).
    """
    cols = feature_columns or MODEL_FEATURES
    df = df.copy()

    # Handle boolean → int conversion before selecting columns
    if "device_first_seen" in df.columns and "device_first_seen_int" not in df.columns:
        df["device_first_seen_int"] = df["device_first_seen"].astype(int)
    if "device_first_seen_int" in df.columns and "device_first_seen" in cols:
        # device_first_seen_int is the numeric version used by the model
        pass

    # Fill missing values
    df = df.fillna(0)

    # Ensure all expected columns exist (default to 0)
    for col in cols:
        if col not in df.columns:
            df[col] = 0

    X = df[cols].copy()
    return X, cols


def prepare_features_from_transaction(
    transaction: dict[str, Any],
    feature_columns: list[str] | None = None,
) -> dict[str, float]:
    """Prepare features from a single transaction dict for inference.

    This function mirrors prepare_features_from_dataframe but operates
    on a single transaction dictionary as received by the API.

    Args:
        transaction: Transaction dictionary with raw + computed features.
        feature_columns: Override feature list. If None, uses MODEL_FEATURES.

    Returns:
        Dictionary mapping feature names to float values.
    """
    cols = feature_columns or MODEL_FEATURES
    features: dict[str, float] = {}

    for col in cols:
        if col == "device_first_seen_int":
            val = transaction.get("device_first_seen", transaction.get("device_first_seen_int", 0))
            features[col] = float(int(val)) if val is not None else 0.0
        else:
            val = transaction.get(col, 0)
            if val is None:
                features[col] = 0.0
            else:
                try:
                    features[col] = float(val)
                except (TypeError, ValueError):
                    features[col] = 0.0

    return features


def get_model_features() -> list[str]:
    """Return the canonical model feature list."""
    return MODEL_FEATURES.copy()
