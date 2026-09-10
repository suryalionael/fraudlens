"""Feature engineering for fraud detection.

This module implements behavioral features that capture deviations from normal
transaction behavior. All features are computed using only historical information
to prevent temporal leakage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""

    velocity_windows: list[int] | None = None  # minutes
    amount_windows: list[int] | None = None  # number of transactions
    customer_history_window: int | None = None  # number of transactions

    def __post_init__(self) -> None:
        if self.velocity_windows is None:
            self.velocity_windows = [10, 60, 1440]
        if self.amount_windows is None:
            self.amount_windows = [5, 10, 20]
        if self.customer_history_window is None:
            self.customer_history_window = 100


class FeatureEngineer:
    """Compute behavioral features for fraud detection.

    Features are computed using only historical information to prevent
    temporal leakage. For each transaction, features are calculated from
    transactions that occurred BEFORE the current transaction.
    """

    def __init__(self, config: FeatureConfig | None = None) -> None:
        self.config = config or FeatureConfig()

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all behavioral features for a transaction dataset."""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        df = self._add_temporal_features(df)
        df = self._add_velocity_features(df)
        df = self._add_amount_features(df)
        df = self._add_customer_features(df)
        df = self._add_device_features(df)
        df = self._add_merchant_features(df)
        df = self._add_location_features(df)

        return df

    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        df["hour_of_day"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["month"] = df["timestamp"].dt.month
        df["day_of_month"] = df["timestamp"].dt.day
        return df

    def _add_velocity_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add transaction velocity features using groupby shift."""
        for window_minutes in self.config.velocity_windows:
            col_name = f"transactions_last_{window_minutes}m"
            df[col_name] = 0

            for sender in df["sender_account"].unique():
                sender_mask = df["sender_account"] == sender
                sender_idx = df.index[sender_mask]

                for i, idx in enumerate(sender_idx):
                    if i == 0:
                        continue
                    current_time = df.at[idx, "timestamp"]
                    window_start = current_time - pd.Timedelta(minutes=window_minutes)
                    prior_indices = sender_idx[:i]
                    prior_timestamps = df.loc[prior_indices, "timestamp"]
                    count = (
                        (prior_timestamps >= window_start)
                        & (prior_timestamps < current_time)
                    ).sum()
                    df.at[idx, col_name] = count

        return df

    def _add_amount_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add amount-based features."""
        df["customer_avg_amount_prior"] = 0.0
        df["customer_std_amount_prior"] = 0.0
        df["customer_max_amount_prior"] = 0.0

        for sender in df["sender_account"].unique():
            sender_mask = df["sender_account"] == sender
            sender_idx = df.index[sender_mask]

            for i, idx in enumerate(sender_idx):
                if i == 0:
                    continue
                prior_indices = sender_idx[:i]
                prior_amounts = df.loc[prior_indices, "amount_ngn"]
                if len(prior_amounts) > 0:
                    df.at[idx, "customer_avg_amount_prior"] = prior_amounts.mean()
                    df.at[idx, "customer_std_amount_prior"] = (
                        prior_amounts.std() if len(prior_amounts) >= 2 else 0
                    )
                    df.at[idx, "customer_max_amount_prior"] = prior_amounts.max()

        # Amount ratio to average
        avg_col = df["customer_avg_amount_prior"].replace(0, np.nan)
        df["amount_ratio_to_avg"] = df["amount_ngn"] / avg_col
        df["amount_ratio_to_avg"] = df["amount_ratio_to_avg"].fillna(1.0)

        # Amount z-score
        df["amount_zscore"] = 0.0
        for sender in df["sender_account"].unique():
            sender_mask = df["sender_account"] == sender
            sender_idx = df.index[sender_mask]

            for i, idx in enumerate(sender_idx):
                if i < 2:
                    continue
                prior_indices = sender_idx[:i]
                prior_amounts = df.loc[prior_indices, "amount_ngn"]
                mean = prior_amounts.mean()
                std = prior_amounts.std()
                if std > 0:
                    df.at[idx, "amount_zscore"] = (
                        df.at[idx, "amount_ngn"] - mean
                    ) / std

        return df

    def _add_customer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add customer-level behavioral features."""
        df["customer_transaction_count_prior"] = 0
        df["customer_days_active"] = 0
        df["customer_transactions_per_day"] = 0.0

        for sender in df["sender_account"].unique():
            sender_mask = df["sender_account"] == sender
            sender_idx = df.index[sender_mask]

            for i, idx in enumerate(sender_idx):
                if i == 0:
                    continue
                prior_indices = sender_idx[:i]
                prior_txns = df.loc[prior_indices]
                current_time = df.at[idx, "timestamp"]

                df.at[idx, "customer_transaction_count_prior"] = len(prior_txns)
                days_active = (current_time - prior_txns["timestamp"].min()).days + 1
                df.at[idx, "customer_days_active"] = days_active
                df.at[idx, "customer_transactions_per_day"] = len(prior_txns) / max(
                    days_active, 1
                )

        return df

    def _add_device_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add device-related features."""
        df["device_transaction_count_prior"] = 0
        df["device_first_seen"] = True

        for device in df["device_hash"].unique():
            device_mask = df["device_hash"] == device
            device_idx = df.index[device_mask]

            for i, idx in enumerate(device_idx):
                if i == 0:
                    continue
                prior_indices = device_idx[:i]
                df.at[idx, "device_transaction_count_prior"] = len(prior_indices)

        for idx in df.index:
            current_device = df.at[idx, "device_hash"]
            current_sender = df.at[idx, "sender_account"]
            current_time = df.at[idx, "timestamp"]
            prior_mask = (df["device_hash"] == current_device) & (
                df["timestamp"] < current_time
            )
            prior_sender_mask = prior_mask & (df["sender_account"] == current_sender)
            df.at[idx, "device_first_seen"] = not prior_sender_mask.any()

        return df

    def _add_merchant_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add merchant-level features."""
        df["merchant_transaction_count_prior"] = 0
        df["merchant_fraud_rate_prior"] = 0.0

        for merchant in df["merchant_category"].unique():
            merchant_mask = df["merchant_category"] == merchant
            merchant_idx = df.index[merchant_mask]

            for i, idx in enumerate(merchant_idx):
                if i == 0:
                    continue
                prior_indices = merchant_idx[:i]
                prior_txns = df.loc[prior_indices]
                df.at[idx, "merchant_transaction_count_prior"] = len(prior_txns)
                df.at[idx, "merchant_fraud_rate_prior"] = prior_txns[
                    "is_fraud"
                ].sum() / len(prior_txns)

        return df

    def _add_location_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add location-related features."""
        df["location_transaction_count_prior"] = 0
        df["location_fraud_rate_prior"] = 0.0

        for location in df["location"].unique():
            location_mask = df["location"] == location
            location_idx = df.index[location_mask]

            for i, idx in enumerate(location_idx):
                if i == 0:
                    continue
                prior_indices = location_idx[:i]
                prior_txns = df.loc[prior_indices]
                df.at[idx, "location_transaction_count_prior"] = len(prior_txns)
                df.at[idx, "location_fraud_rate_prior"] = prior_txns[
                    "is_fraud"
                ].sum() / len(prior_txns)

        return df
