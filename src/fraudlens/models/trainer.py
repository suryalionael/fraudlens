"""Model training for fraud detection.

This module implements training pipelines for fraud detection models including:
- Logistic Regression (baseline)
- Random Forest
- XGBoost

All models use class weighting to handle the imbalanced fraud dataset.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


@dataclass
class ModelConfig:
    """Configuration for model training."""

    # Feature columns to use
    feature_columns: list[str] | None = None

    # Target column
    target_column: str = "is_fraud"

    # Test size
    test_size: float = 0.2

    # Random state
    random_state: int = 42

    # Class weight strategy
    class_weight: str = "balanced"

    # Model-specific parameters
    logistic_regression_params: dict[str, Any] = field(
        default_factory=lambda: {
            "max_iter": 1000,
            "solver": "lbfgs",
            "C": 1.0,
        }
    )

    random_forest_params: dict[str, Any] = field(
        default_factory=lambda: {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
        }
    )

    xgboost_params: dict[str, Any] = field(
        default_factory=lambda: {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        }
    )


@dataclass
class TrainResult:
    """Result of model training."""

    model_name: str
    model_version: str
    training_timestamp: str
    hyperparameters: dict[str, Any]
    train_size: int
    test_size: int
    fraud_rate_train: float
    fraud_rate_test: float
    features_used: list[str]
    model_path: str | None = None


class ModelTrainer:
    """Train and evaluate fraud detection models."""

    def __init__(self, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()
        self.scaler = StandardScaler()
        self.models: dict[str, Any] = {}
        self.results: dict[str, TrainResult] = {}

    def prepare_features(
        self,
        df: pd.DataFrame,
        feature_columns: list[str] | None = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training.

        Args:
            df: DataFrame with features and target.
            feature_columns: List of feature column names. If None, uses config.

        Returns:
            Tuple of (features_df, target_series).
        """
        cols = feature_columns or self.config.feature_columns
        if cols is None:
            # Auto-detect numeric features
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cols = [c for c in numeric_cols if c != self.config.target_column]

        X = df[cols].copy()
        y = df[self.config.target_column].copy()

        # Handle missing values
        X = X.fillna(0)

        return X, y

    def train_test_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        temporal: bool = False,
        timestamps: pd.Series | None = None,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Split data into train and test sets.

        Args:
            X: Features DataFrame.
            y: Target Series.
            temporal: If True, use temporal split (no shuffle).
            timestamps: Series of timestamps for temporal splitting.

        Returns:
            Tuple of (X_train, X_test, y_train, y_test).
        """
        if temporal and timestamps is not None:
            # Temporal split: use most recent data for test
            split_idx = int(len(X) * (1 - self.config.test_size))
            X_train = X.iloc[:split_idx]
            X_test = X.iloc[split_idx:]
            y_train = y.iloc[:split_idx]
            y_test = y.iloc[split_idx:]
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
                stratify=y,
            )

        return X_train, X_test, y_train, y_test

    def train_logistic_regression(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
    ) -> tuple[Any, np.ndarray]:
        """Train Logistic Regression model.

        Returns:
            Tuple of (model, predicted_probabilities).
        """
        params = self.config.logistic_regression_params.copy()
        params["class_weight"] = self.config.class_weight
        params["random_state"] = self.config.random_state

        model = LogisticRegression(**params)
        model.fit(X_train, y_train)

        # Get probabilities
        y_prob = model.predict_proba(X_test)[:, 1]

        return model, y_prob

    def train_random_forest(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
    ) -> tuple[Any, np.ndarray]:
        """Train Random Forest model.

        Returns:
            Tuple of (model, predicted_probabilities).
        """
        params = self.config.random_forest_params.copy()
        params["class_weight"] = self.config.class_weight
        params["random_state"] = self.config.random_state

        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)

        # Get probabilities
        y_prob = model.predict_proba(X_test)[:, 1]

        return model, y_prob

    def train_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
    ) -> tuple[Any, np.ndarray]:
        """Train XGBoost model.

        Returns:
            Tuple of (model, predicted_probabilities).
        """
        try:
            from xgboost import XGBClassifier
        except ImportError:
            raise ImportError("XGBoost is required. Install with: pip install xgboost")

        # Calculate scale_pos_weight for imbalanced data
        n_negative = (y_train == 0).sum()
        n_positive = (y_train == 1).sum()
        scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1

        params = self.config.xgboost_params.copy()
        params["scale_pos_weight"] = scale_pos_weight
        params["random_state"] = self.config.random_state
        params["eval_metric"] = "aucpr"
        params["use_label_encoder"] = False

        model = XGBClassifier(**params)
        model.fit(X_train, y_train)

        # Get probabilities
        y_prob = model.predict_proba(X_test)[:, 1]

        return model, y_prob

    def train_all(
        self,
        df: pd.DataFrame,
        feature_columns: list[str] | None = None,
        temporal: bool = False,
    ) -> dict[str, tuple[Any, np.ndarray, TrainResult]]:
        """Train all models and return results.

        Args:
            df: DataFrame with features and target.
            feature_columns: List of feature column names.
            temporal: If True, use temporal split.

        Returns:
            Dict mapping model_name to (model, y_prob, TrainResult).
        """
        X, y = self.prepare_features(df, feature_columns)

        # Get timestamps for temporal split
        timestamps = df["timestamp"] if "timestamp" in df.columns and temporal else None

        X_train, X_test, y_train, y_test = self.train_test_split(
            X, y, temporal=temporal, timestamps=timestamps
        )

        # Scale features for logistic regression
        X_train_scaled = pd.DataFrame(
            self.scaler.fit_transform(X_train),
            columns=X_train.columns,
            index=X_train.index,
        )
        X_test_scaled = pd.DataFrame(
            self.scaler.transform(X_test),
            columns=X_test.columns,
            index=X_test.index,
        )

        results = {}

        # Train Logistic Regression
        lr_model, lr_prob = self.train_logistic_regression(
            X_train_scaled, y_train, X_test_scaled
        )
        self.models["logistic_regression"] = lr_model
        results["logistic_regression"] = (
            lr_model,
            lr_prob,
            TrainResult(
                model_name="logistic_regression",
                model_version="fraudlens-lr-v001",
                training_timestamp=datetime.now(tz=timezone.utc).isoformat(),
                hyperparameters=self.config.logistic_regression_params,
                train_size=len(X_train),
                test_size=len(X_test),
                fraud_rate_train=y_train.mean(),
                fraud_rate_test=y_test.mean(),
                features_used=list(X_train.columns),
            ),
        )

        # Train Random Forest
        rf_model, rf_prob = self.train_random_forest(X_train, y_train, X_test)
        self.models["random_forest"] = rf_model
        results["random_forest"] = (
            rf_model,
            rf_prob,
            TrainResult(
                model_name="random_forest",
                model_version="fraudlens-rf-v001",
                training_timestamp=datetime.now(tz=timezone.utc).isoformat(),
                hyperparameters=self.config.random_forest_params,
                train_size=len(X_train),
                test_size=len(X_test),
                fraud_rate_train=y_train.mean(),
                fraud_rate_test=y_test.mean(),
                features_used=list(X_train.columns),
            ),
        )

        # Train XGBoost
        xgb_model, xgb_prob = self.train_xgboost(X_train, y_train, X_test)
        self.models["xgboost"] = xgb_model
        results["xgboost"] = (
            xgb_model,
            xgb_prob,
            TrainResult(
                model_name="xgboost",
                model_version="fraudlens-xgb-v001",
                training_timestamp=datetime.now(tz=timezone.utc).isoformat(),
                hyperparameters=self.config.xgboost_params,
                train_size=len(X_train),
                test_size=len(X_test),
                fraud_rate_train=y_train.mean(),
                fraud_rate_test=y_test.mean(),
                features_used=list(X_train.columns),
            ),
        )

        self.results = {k: v[2] for k, v in results.items()}
        return results

    def save_model(
        self,
        model: Any,
        model_name: str,
        output_dir: str | Path = "models/",
    ) -> Path:
        """Save a trained model to disk.

        Args:
            model: Trained model object.
            model_name: Name of the model.
            output_dir: Directory to save model.

        Returns:
            Path to saved model.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        model_path = output_dir / f"{model_name}.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        return model_path

    def save_results(
        self,
        output_dir: str | Path = "models/",
    ) -> Path:
        """Save training results to JSON.

        Args:
            output_dir: Directory to save results.

        Returns:
            Path to results file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results_path = output_dir / "training_results.json"
        results_data = {}
        for name, result in self.results.items():
            results_data[name] = {
                "model_name": result.model_name,
                "model_version": result.model_version,
                "training_timestamp": result.training_timestamp,
                "hyperparameters": result.hyperparameters,
                "train_size": result.train_size,
                "test_size": result.test_size,
                "fraud_rate_train": result.fraud_rate_train,
                "fraud_rate_test": result.fraud_rate_test,
                "features_used": result.features_used,
            }

        with open(results_path, "w") as f:
            json.dump(results_data, f, indent=2)

        return results_path
