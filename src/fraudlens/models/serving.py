"""Model serving for FraudLens.

This module handles model training, persistence, and loading for inference.
It ensures the trained model is available to the API at runtime.
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from fraudlens.features.preparation import (
    prepare_features_from_dataframe,
)

logger = logging.getLogger(__name__)


@dataclass
class ModelArtifact:
    """Container for a trained model and its metadata."""

    model: Any
    scaler: StandardScaler | None
    model_name: str
    model_version: str
    feature_columns: list[str]
    training_timestamp: str
    hyperparameters: dict[str, Any]
    evaluation: dict[str, Any]
    train_size: int
    test_size: int


def train_and_persist_model(
    df: pd.DataFrame,
    output_dir: str | Path = "models/",
    model_name: str = "random_forest",
) -> Path:
    """Train a model and save the artifact to disk.

    Args:
        df: DataFrame with features and is_fraud target.
        output_dir: Directory to save model artifacts.
        model_name: Which model to train ("logistic_regression", "random_forest", "xgboost").

    Returns:
        Path to saved model artifact.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare features using shared preparation
    X, feature_columns = prepare_features_from_dataframe(df)
    y = df["is_fraud"].astype(int)

    # Temporal train/test split (80/20, no shuffle — respects time ordering)
    split_idx = int(len(X) * 0.8)
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]

    # Train model
    scaler = None
    if model_name == "logistic_regression":
        scaler = StandardScaler()
        X_train_input = pd.DataFrame(
            scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index
        )
        X_test_input = pd.DataFrame(
            scaler.transform(X_test), columns=X_test.columns, index=X_test.index
        )
        model = LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            C=1.0,
            class_weight="balanced",
            random_state=42,
        )
        model.fit(X_train_input, y_train)
        y_prob = model.predict_proba(X_test_input)[:, 1]
    elif model_name == "random_forest":
        X_train_input = X_train
        X_test_input = X_test
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train_input, y_train)
        y_prob = model.predict_proba(X_test_input)[:, 1]
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    # Evaluate
    from sklearn.metrics import (
        average_precision_score,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    y_pred = (y_prob >= 0.5).astype(int)
    evaluation = {
        "pr_auc": round(float(average_precision_score(y_test, y_prob)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "test_size": len(y_test),
        "train_size": len(y_train),
        "fraud_rate_train": round(float(y_train.mean()), 4),
        "fraud_rate_test": round(float(y_test.mean()), 4),
    }

    # Build artifact
    prefix_map = {"logistic_regression": "lr", "random_forest": "rf", "xgboost": "xgb"}
    prefix = prefix_map.get(model_name, model_name[:3])
    model_version = f"fraudlens-{prefix}-v001"
    artifact = ModelArtifact(
        model=model,
        scaler=scaler,
        model_name=model_name,
        model_version=model_version,
        feature_columns=feature_columns,
        training_timestamp=datetime.now(tz=timezone.utc).isoformat(),
        hyperparameters=get_hyperparameters(model_name),
        evaluation=evaluation,
        train_size=len(y_train),
        test_size=len(y_test),
    )

    # Save artifact
    artifact_path = output_dir / f"{model_name}.artifact.pkl"
    with open(artifact_path, "wb") as f:
        pickle.dump(artifact, f)

    # Save metadata as JSON for easy inspection
    metadata = {
        "model_name": model_name,
        "model_version": model_version,
        "training_timestamp": artifact.training_timestamp,
        "feature_columns": feature_columns,
        "hyperparameters": artifact.hyperparameters,
        "evaluation": evaluation,
        "train_size": artifact.train_size,
        "test_size": artifact.test_size,
    }
    metadata_path = output_dir / f"{model_name}.metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(
        "Model trained and saved: %s (PR-AUC=%.4f, F1=%.4f)",
        model_version,
        evaluation["pr_auc"],
        evaluation["f1"],
    )

    return artifact_path


def load_model_artifact(artifact_path: str | Path) -> ModelArtifact:
    """Load a trained model artifact from disk.

    Supports both local paths and S3 URIs (s3://bucket/key).

    Args:
        artifact_path: Path to the .artifact.pkl file or S3 URI.

    Returns:
        ModelArtifact with model, scaler, and metadata.
    """
    path_str = str(artifact_path)

    # S3 loading
    if path_str.startswith("s3://"):
        return _load_from_s3(path_str)

    # Local loading
    artifact_path = Path(artifact_path)
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"Model artifact not found: {artifact_path}. Run model training first."
        )

    with open(artifact_path, "rb") as f:
        artifact = pickle.load(f)

    if not isinstance(artifact, ModelArtifact):
        raise TypeError(f"Invalid artifact format in {artifact_path}")

    return artifact


def _load_from_s3(s3_uri: str) -> ModelArtifact:
    """Load a model artifact from S3.

    Args:
        s3_uri: S3 URI in format s3://bucket/key.

    Returns:
        ModelArtifact with model, scaler, and metadata.
    """
    import tempfile

    import boto3

    # Parse s3://bucket/key
    parts = s3_uri.replace("s3://", "").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI: {s3_uri}")

    bucket, key = parts

    logger.info("Loading model from S3: s3://%s/%s", bucket, key)

    s3 = boto3.client("s3")

    with tempfile.NamedTemporaryFile(suffix=".pkl") as tmp:
        s3.download_file(bucket, key, tmp.name)

        with open(tmp.name, "rb") as f:
            artifact = pickle.load(f)

    if not isinstance(artifact, ModelArtifact):
        raise TypeError(f"Invalid artifact format in S3 object {s3_uri}")

    logger.info("Loaded model from S3: %s", artifact.model_version)
    return artifact


def predict_probability(
    artifact: ModelArtifact,
    features: dict[str, float],
) -> float:
    """Predict fraud probability for a single transaction.

    Args:
        artifact: Loaded model artifact.
        features: Feature dictionary (from prepare_features_from_transaction).

    Returns:
        Fraud probability (0.0 - 1.0).
    """
    # Build feature vector in correct order
    X = pd.DataFrame([features], columns=artifact.feature_columns)

    # Apply scaler if needed (logistic regression)
    if artifact.scaler is not None:
        X = pd.DataFrame(
            artifact.scaler.transform(X),
            columns=artifact.feature_columns,
        )

    prob = artifact.model.predict_proba(X)[:, 1][0]
    return float(prob)


def get_hyperparameters(model_name: str) -> dict[str, Any]:
    """Return default hyperparameters for a model."""
    if model_name == "logistic_regression":
        return {
            "max_iter": 1000,
            "solver": "lbfgs",
            "C": 1.0,
            "class_weight": "balanced",
        }
    elif model_name == "random_forest":
        return {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 5,
            "min_samples_leaf": 2,
            "class_weight": "balanced",
        }
    return {}
