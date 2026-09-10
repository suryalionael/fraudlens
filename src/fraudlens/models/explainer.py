"""SHAP-based model explainability for FraudLens.

This module provides feature-level explanations for individual predictions
using SHAP (SHapley Additive exPlanations).

All explanations describe features CONTRIBUTING to the model prediction,
not causal evidence of fraud.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def explain_prediction(
    model: Any,
    feature_names: list[str],
    X_explain: pd.DataFrame | np.ndarray,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Generate SHAP-based feature explanations for a prediction.

    Args:
        model: Trained sklearn-compatible model.
        feature_names: List of feature column names.
        X_explain: Feature matrix (single row or batch).
        top_k: Number of top features to return.

    Returns:
        List of dicts with feature_name, shap_value, direction, magnitude.
    """
    try:
        import shap
    except ImportError:
        logger.warning("SHAP not installed. Using feature importances as fallback.")
        return _fallback_explanation(model, feature_names, X_explain, top_k)

    try:
        # Use TreeExplainer for tree-based models, KernelExplainer as fallback
        if hasattr(model, "estimators_") or type(model).__name__ in (
            "RandomForestClassifier",
            "XGBClassifier",
            "GradientBoostingClassifier",
        ):
            explainer = shap.TreeExplainer(model)
        else:
            # For linear models, use a simple coefficient-based approach
            return _linear_explanation(model, feature_names, X_explain, top_k)

        # Compute SHAP values
        shap_values = explainer.shap_values(X_explain)

        # For binary classification, shap_values may be a list [class_0, class_1]
        if isinstance(shap_values, list):
            shap_vals = shap_values[1]  # fraud class
        else:
            shap_vals = shap_values

        # Take first row if single prediction
        if len(shap_vals.shape) > 1:
            shap_vals = shap_vals[0]

        return _format_shap_values(feature_names, shap_vals, top_k)

    except Exception as e:
        logger.warning("SHAP explanation failed: %s. Using fallback.", e)
        return _fallback_explanation(model, feature_names, X_explain, top_k)


def _linear_explanation(
    model: Any,
    feature_names: list[str],
    X_explain: pd.DataFrame | np.ndarray,
    top_k: int,
) -> list[dict[str, Any]]:
    """Generate explanations for linear models using coefficients."""
    if not hasattr(model, "coef_"):
        return []

    coef = model.coef_[0]
    if isinstance(X_explain, pd.DataFrame):
        x_vals = X_explain.values[0]
    else:
        x_vals = X_explain[0]

    contributions = coef * x_vals
    return _format_shap_values(feature_names, contributions, top_k)


def _fallback_explanation(
    model: Any,
    feature_names: list[str],
    X_explain: pd.DataFrame | np.ndarray,
    top_k: int,
) -> list[dict[str, Any]]:
    """Fallback explanation using feature importances and values."""
    if not hasattr(model, "feature_importances_"):
        return []

    importances = model.feature_importances_
    if isinstance(X_explain, pd.DataFrame):
        x_vals = X_explain.values[0]
    else:
        x_vals = X_explain[0]

    # Simple heuristic: importance * feature_value direction
    contributions = importances * np.abs(x_vals)
    return _format_shap_values(feature_names, contributions, top_k)


def _format_shap_values(
    feature_names: list[str],
    values: np.ndarray,
    top_k: int,
) -> list[dict[str, Any]]:
    """Format SHAP values into a sorted list of explanations."""
    if len(values) != len(feature_names):
        return []

    # Create list of (feature, value) pairs
    pairs = list(zip(feature_names, values))

    # Sort by absolute value descending
    pairs.sort(key=lambda x: abs(x[1]), reverse=True)

    # Take top_k
    explanations = []
    for name, val in pairs[:top_k]:
        explanations.append(
            {
                "feature": name,
                "shap_value": round(float(val), 6),
                "direction": "increases_risk" if val > 0 else "decreases_risk",
                "magnitude": round(float(abs(val)), 6),
            }
        )

    return explanations


def format_explanation_for_api(
    explanations: list[dict[str, Any]],
) -> list[str]:
    """Format explanations into human-readable strings for API response.

    Args:
        explanations: List of explanation dicts from explain_prediction.

    Returns:
        List of human-readable risk factor strings.
    """
    factors = []
    for exp in explanations:
        direction = "increases" if exp["direction"] == "increases_risk" else "decreases"
        factors.append(
            f"Feature '{exp['feature']}' {direction} risk "
            f"(contribution: {exp['shap_value']:.4f})"
        )
    return factors
