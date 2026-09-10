"""FraudLens machine learning module."""

from fraudlens.models.evaluator import ModelEvaluator
from fraudlens.models.explainer import (
    explain_prediction,
    format_explanation_for_api,
)
from fraudlens.models.serving import (
    ModelArtifact,
    load_model_artifact,
    predict_probability,
    train_and_persist_model,
)
from fraudlens.models.trainer import ModelTrainer

__all__ = [
    "ModelArtifact",
    "ModelEvaluator",
    "ModelTrainer",
    "explain_prediction",
    "format_explanation_for_api",
    "load_model_artifact",
    "predict_probability",
    "train_and_persist_model",
]
