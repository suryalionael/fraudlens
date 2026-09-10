"""Model evaluation for fraud detection.

This module implements evaluation metrics for fraud detection models including:
- PR-AUC (primary metric)
- Precision/Recall
- F1
- Precision@K
- Recall@K
- Confusion matrix
- Threshold analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_recall_curve,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    auc,
)


@dataclass
class EvaluationResult:
    """Result of model evaluation."""

    model_name: str
    pr_auc: float
    roc_auc: float
    precision: float
    recall: float
    f1: float
    precision_at_k: dict[int, float]
    recall_at_k: dict[int, float]
    confusion_matrix: dict[str, int]
    threshold_analysis: list[dict[str, Any]]
    optimal_threshold: float
    optimal_threshold_precision: float
    optimal_threshold_recall: float


class ModelEvaluator:
    """Evaluate fraud detection models."""

    def __init__(self) -> None:
        self.results: dict[str, EvaluationResult] = {}

    def evaluate(
        self,
        y_true: np.ndarray | pd.Series,
        y_prob: np.ndarray | pd.Series,
        model_name: str,
        k_values: list[int] | None = None,
    ) -> EvaluationResult:
        """Evaluate a model's predictions.

        Args:
            y_true: True labels.
            y_prob: Predicted probabilities.
            model_name: Name of the model.
            k_values: List of K values for Precision@K and Recall@K.

        Returns:
            EvaluationResult with all metrics.
        """
        if k_values is None:
            k_values = [100, 500, 1000, 5000]

        y_true = np.array(y_true)
        y_prob = np.array(y_prob)

        # PR-AUC
        precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
        pr_auc = auc(recall_curve, precision_curve)

        # ROC-AUC
        try:
            roc_auc = roc_auc_score(y_true, y_prob)
        except ValueError:
            roc_auc = 0.0

        # Find optimal threshold using F1
        thresholds = np.arange(0.1, 0.9, 0.01)
        best_f1 = 0
        best_threshold = 0.5
        for t in thresholds:
            y_pred = (y_prob >= t).astype(int)
            f1 = f1_score(y_true, y_pred, zero_division=0)
            if f1 > best_f1:
                best_f1 = f1
                best_threshold = t

        # Predictions at optimal threshold
        y_pred_optimal = (y_prob >= best_threshold).astype(int)
        precision_optimal = precision_score(y_true, y_pred_optimal, zero_division=0)
        recall_optimal = recall_score(y_true, y_pred_optimal, zero_division=0)
        f1_optimal = f1_score(y_true, y_pred_optimal, zero_division=0)

        # Confusion matrix at optimal threshold
        cm = confusion_matrix(y_true, y_pred_optimal)
        tn, fp, fn, tp = cm.ravel()

        # Precision@K and Recall@K
        precision_at_k = {}
        recall_at_k = {}
        for k in k_values:
            if k <= len(y_prob):
                # Get top K predictions
                top_k_indices = np.argsort(y_prob)[-k:]
                top_k_true = y_true[top_k_indices]

                precision_at_k[k] = top_k_true.sum() / k
                recall_at_k[k] = (
                    top_k_true.sum() / y_true.sum() if y_true.sum() > 0 else 0
                )

        # Threshold analysis
        threshold_analysis = []
        for t in np.arange(0.1, 0.9, 0.05):
            y_pred = (y_prob >= t).astype(int)
            p = precision_score(y_true, y_pred, zero_division=0)
            r = recall_score(y_true, y_pred, zero_division=0)
            f = f1_score(y_true, y_pred, zero_division=0)
            flagged = y_pred.sum()
            threshold_analysis.append(
                {
                    "threshold": round(t, 2),
                    "precision": round(p, 4),
                    "recall": round(r, 4),
                    "f1": round(f, 4),
                    "flagged_transactions": int(flagged),
                }
            )

        result = EvaluationResult(
            model_name=model_name,
            pr_auc=round(pr_auc, 4),
            roc_auc=round(roc_auc, 4),
            precision=round(precision_optimal, 4),
            recall=round(recall_optimal, 4),
            f1=round(f1_optimal, 4),
            precision_at_k={k: round(v, 4) for k, v in precision_at_k.items()},
            recall_at_k={k: round(v, 4) for k, v in recall_at_k.items()},
            confusion_matrix={
                "true_negatives": int(tn),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_positives": int(tp),
            },
            threshold_analysis=threshold_analysis,
            optimal_threshold=round(best_threshold, 3),
            optimal_threshold_precision=round(precision_optimal, 4),
            optimal_threshold_recall=round(recall_optimal, 4),
        )

        self.results[model_name] = result
        return result

    def compare_models(self) -> pd.DataFrame:
        """Compare all evaluated models.

        Returns:
            DataFrame with comparison metrics.
        """
        if not self.results:
            return pd.DataFrame()

        rows = []
        for name, result in self.results.items():
            rows.append(
                {
                    "model": name,
                    "pr_auc": result.pr_auc,
                    "roc_auc": result.roc_auc,
                    "precision": result.precision,
                    "recall": result.recall,
                    "f1": result.f1,
                    "optimal_threshold": result.optimal_threshold,
                }
            )

        df = pd.DataFrame(rows)
        return df.sort_values("pr_auc", ascending=False)

    def get_summary(self) -> str:
        """Get a summary of all evaluation results."""
        if not self.results:
            return "No models evaluated."

        lines = [
            "",
            "Model Evaluation Summary",
            "─" * 60,
            "",
        ]

        comparison = self.compare_models()
        lines.append(comparison.to_string(index=False))
        lines.append("")

        for name, result in self.results.items():
            lines.append(f"\n{name}:")
            lines.append(f"  PR-AUC: {result.pr_auc}")
            lines.append(f"  Optimal threshold: {result.optimal_threshold}")
            lines.append("  Precision@K:")
            for k, v in result.precision_at_k.items():
                lines.append(f"    Top {k}: {v:.4f}")
            lines.append("  Recall@K:")
            for k, v in result.recall_at_k.items():
                lines.append(f"    Top {k}: {v:.4f}")

        lines.append("")
        return "\n".join(lines)
