"""Risk engine for fraud detection.

This module combines ML predictions with rule-based signals to produce
actionable risk assessments including:
- Risk score (0-100)
- Risk level (Low, Medium, High, Critical)
- Risk factors
- Recommended action
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from fraudlens.risk.rules import RuleEngine, RuleSignal


@dataclass
class RiskConfig:
    """Configuration for risk scoring."""

    # ML model weight (0-1)
    ml_weight: float = 0.7

    # Rule engine weight (0-1)
    rule_weight: float = 0.3

    # Risk level thresholds
    risk_level_thresholds: dict[str, tuple[int, int]] = field(
        default_factory=lambda: {
            "low": (0, 29),
            "medium": (30, 59),
            "high": (60, 79),
            "critical": (80, 100),
        }
    )

    # Action thresholds
    action_thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "allow": 0,
            "monitor": 30,
            "review": 60,
            "urgent_review": 80,
        }
    )


@dataclass
class RiskResult:
    """Result of risk assessment."""

    transaction_id: str
    fraud_probability: float
    risk_score: float
    risk_level: str
    rule_score: float
    ml_score: float
    risk_factors: list[str]
    recommended_action: str
    rule_signals: list[dict[str, Any]]


class RiskEngine:
    """Combine ML predictions with rule-based signals for risk assessment."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self.rule_engine = RuleEngine()

    def calculate_risk_score(
        self,
        fraud_probability: float,
        rule_score: float,
    ) -> float:
        """Calculate combined risk score from ML and rules.

        Args:
            fraud_probability: ML model's fraud probability (0-1).
            rule_score: Rule engine's score contribution (0-100).

        Returns:
            Risk score (0-100).
        """
        # Normalize ML probability to 0-100
        ml_score = fraud_probability * 100

        # Combine scores
        combined = (self.config.ml_weight * ml_score) + (
            self.config.rule_weight * rule_score
        )

        # Cap at 100
        return min(max(combined, 0), 100)

    def assign_risk_level(self, risk_score: float) -> str:
        """Assign risk level based on score.

        Args:
            risk_score: Risk score (0-100).

        Returns:
            Risk level string.
        """
        for level, (low, high) in self.config.risk_level_thresholds.items():
            if low <= risk_score <= high:
                return level
        return "unknown"

    def assign_action(self, risk_score: float) -> str:
        """Assign recommended action based on score.

        Args:
            risk_score: Risk score (0-100).

        Returns:
            Recommended action string.
        """
        action = "allow"
        for threshold_action, threshold_value in self.config.action_thresholds.items():
            if risk_score >= threshold_value:
                action = threshold_action
        return action

    def identify_risk_factors(
        self,
        transaction: dict[str, Any],
        rule_signals: list[RuleSignal],
    ) -> list[str]:
        """Identify key risk factors for explainability.

        Args:
            transaction: Transaction features.
            rule_signals: Triggered rule signals.

        Returns:
            List of risk factor descriptions.
        """
        factors = []

        # Add rule-based factors
        for signal in rule_signals:
            factors.append(signal.description)

        # Add ML-based factors
        if transaction.get("amount_zscore", 0) > 2:
            factors.append("Transaction amount significantly exceeds sender's average")
        elif transaction.get("amount_zscore", 0) < -2:
            factors.append("Transaction amount significantly below sender's average")

        if transaction.get("merchant_fraud_rate_prior", 0) > 0.05:
            factors.append("Merchant has elevated historical fraud rate")

        if transaction.get("location_fraud_rate_prior", 0) > 0.05:
            factors.append("Location has elevated historical fraud rate")

        if transaction.get("customer_transaction_count_prior", 0) < 3:
            factors.append("Sender has limited transaction history")

        return factors

    def assess_transaction(
        self,
        transaction: dict[str, Any],
        fraud_probability: float,
    ) -> RiskResult:
        """Perform full risk assessment on a transaction.

        Args:
            transaction: Dictionary with transaction features.
            fraud_probability: ML model's fraud probability (0-1).

        Returns:
            RiskResult with complete risk assessment.
        """
        # Evaluate rules
        rule_signals = self.rule_engine.evaluate(transaction)
        rule_score = self.rule_engine.get_total_rule_score(rule_signals)

        # Calculate combined risk score
        risk_score = self.calculate_risk_score(fraud_probability, rule_score)

        # Assign risk level and action
        risk_level = self.assign_risk_level(risk_score)
        recommended_action = self.assign_action(risk_score)

        # Identify risk factors
        risk_factors = self.identify_risk_factors(transaction, rule_signals)

        # ML score (normalized to 0-100)
        ml_score = fraud_probability * 100

        return RiskResult(
            transaction_id=transaction.get("transaction_id", "unknown"),
            fraud_probability=fraud_probability,
            risk_score=round(risk_score, 2),
            risk_level=risk_level,
            rule_score=round(rule_score, 2),
            ml_score=round(ml_score, 2),
            risk_factors=risk_factors,
            recommended_action=recommended_action,
            rule_signals=[
                {
                    "rule": s.rule,
                    "triggered": s.triggered,
                    "severity": s.severity,
                    "score_contribution": s.score_contribution,
                    "description": s.description,
                }
                for s in rule_signals
            ],
        )

    def assess_batch(
        self,
        transactions: list[dict[str, Any]],
        fraud_probabilities: list[float],
    ) -> list[RiskResult]:
        """Assess a batch of transactions.

        Args:
            transactions: List of transaction feature dictionaries.
            fraud_probabilities: List of ML fraud probabilities.

        Returns:
            List of RiskResult objects.
        """
        if len(transactions) != len(fraud_probabilities):
            raise ValueError(
                "Number of transactions must match number of probabilities"
            )

        results = []
        for transaction, prob in zip(transactions, fraud_probabilities):
            result = self.assess_transaction(transaction, prob)
            results.append(result)

        return results

    def get_investigation_queue(
        self,
        results: list[RiskResult],
        max_items: int = 100,
    ) -> list[RiskResult]:
        """Get prioritized investigation queue.

        Args:
            results: List of risk assessment results.
            max_items: Maximum number of items in queue.

        Returns:
            Sorted list of RiskResult objects (highest risk first).
        """
        # Sort by risk score descending
        sorted_results = sorted(results, key=lambda r: r.risk_score, reverse=True)

        # Return top N
        return sorted_results[:max_items]

    def get_summary_statistics(self, results: list[RiskResult]) -> dict[str, Any]:
        """Get summary statistics for a batch of assessments.

        Args:
            results: List of risk assessment results.

        Returns:
            Dictionary with summary statistics.
        """
        if not results:
            return {}

        scores = [r.risk_score for r in results]
        levels = [r.risk_level for r in results]
        actions = [r.recommended_action for r in results]

        return {
            "total_transactions": len(results),
            "avg_risk_score": round(np.mean(scores), 2),
            "max_risk_score": round(max(scores), 2),
            "min_risk_score": round(min(scores), 2),
            "risk_level_distribution": {
                level: levels.count(level)
                for level in ["low", "medium", "high", "critical"]
            },
            "action_distribution": {
                action: actions.count(action)
                for action in ["allow", "monitor", "review", "urgent_review"]
            },
            "high_risk_count": sum(
                1 for level in levels if level in ["high", "critical"]
            ),
            "urgent_review_count": actions.count("urgent_review"),
        }
