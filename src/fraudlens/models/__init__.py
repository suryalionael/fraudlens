"""FraudLens machine learning module."""

from fraudlens.models.trainer import ModelTrainer
from fraudlens.models.evaluator import ModelEvaluator
from fraudlens.models.serving import (
    ModelArtifact,
    train_and_persist_model,
    load_model_artifact,
    predict_probability,
)
from fraudlens.models.explainer import (
    explain_prediction,
    format_explanation_for_api,
)

__all__ = [
    "ModelTrainer",
    "ModelEvaluator",
    "ModelArtifact",
    "train_and_persist_model",
    "load_model_artifact",
    "predict_probability",
    "explain_prediction",
    "format_explanation_for_api",
]
