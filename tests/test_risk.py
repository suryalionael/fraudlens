"""Tests for risk engine and rules engine."""

import pytest

from fraudlens.risk.engine import RiskEngine, RiskConfig, RiskResult
from fraudlens.risk.rules import RuleEngine, RuleSignal


class TestRuleEngine:
    def test_initialization(self):
        engine = RuleEngine()
        assert engine.rules is not None
        assert len(engine.rules) > 0

    def test_evaluate_new_device(self):
        engine = RuleEngine()
        transaction = {"device_first_seen": True}
        signals = engine.evaluate(transaction)

        assert any(s.rule == "new_device" for s in signals)
        assert signals[0].severity == "high"
        assert signals[0].score_contribution == 20

    def test_evaluate_amount_anomaly(self):
        engine = RuleEngine()
        transaction = {"amount_zscore": 3.0}
        signals = engine.evaluate(transaction)

        assert any(s.rule == "amount_anomaly" for s in signals)

    def test_evaluate_no_rules_triggered(self):
        engine = RuleEngine()
        transaction = {
            "device_first_seen": False,
            "amount_zscore": 0.5,
            "amount_ratio_to_avg": 1.0,
            "transactions_last_1h": 2,
            "merchant_fraud_rate_prior": 0.01,
            "location_fraud_rate_prior": 0.01,
            "customer_transaction_count_prior": 50,
            "customer_transactions_per_day": 5,
        }
        signals = engine.evaluate(transaction)

        assert len(signals) == 0

    def test_get_total_rule_score(self):
        engine = RuleEngine()
        signals = [
            RuleSignal("rule1", True, "high", 20, "desc1"),
            RuleSignal("rule2", True, "medium", 15, "desc2"),
        ]
        total = engine.get_total_rule_score(signals)

        assert total == 35

    def test_get_total_rule_score_capped(self):
        engine = RuleEngine()
        signals = [
            RuleSignal("rule1", True, "critical", 50, "desc1"),
            RuleSignal("rule2", True, "critical", 50, "desc2"),
            RuleSignal("rule3", True, "critical", 50, "desc3"),
        ]
        total = engine.get_total_rule_score(signals)

        assert total == 100  # Capped at 100

    def test_get_rule_summary(self):
        engine = RuleEngine()
        signals = [
            RuleSignal("rule1", True, "high", 20, "desc1"),
        ]
        summary = engine.get_rule_summary(signals)

        assert summary["total_rules_triggered"] == 1
        assert summary["total_score_contribution"] == 20
        assert len(summary["rules"]) == 1


class TestRiskEngine:
    def test_initialization(self):
        engine = RiskEngine()
        assert engine.config is not None
        assert engine.rule_engine is not None

    def test_calculate_risk_score(self):
        engine = RiskEngine()
        score = engine.calculate_risk_score(0.8, 50)

        # 0.7 * 80 + 0.3 * 50 = 56 + 15 = 71
        assert 60 <= score <= 80

    def test_calculate_risk_score_capped(self):
        engine = RiskEngine()
        score = engine.calculate_risk_score(1.0, 100)

        assert score == 100

    def test_assign_risk_level(self):
        engine = RiskEngine()

        assert engine.assign_risk_level(10) == "low"
        assert engine.assign_risk_level(45) == "medium"
        assert engine.assign_risk_level(70) == "high"
        assert engine.assign_risk_level(90) == "critical"

    def test_assign_action(self):
        engine = RiskEngine()

        assert engine.assign_action(10) == "allow"
        assert engine.assign_action(45) == "monitor"
        assert engine.assign_action(70) == "review"
        assert engine.assign_action(90) == "urgent_review"

    def test_identify_risk_factors(self):
        engine = RiskEngine()
        transaction = {
            "amount_zscore": 3.0,
            "merchant_fraud_rate_prior": 0.15,
            "location_fraud_rate_prior": 0.02,
            "customer_transaction_count_prior": 1,
        }
        rule_signals = [
            RuleSignal("new_device", True, "high", 20, "Transaction from a new device"),
        ]

        factors = engine.identify_risk_factors(transaction, rule_signals)

        assert len(factors) > 0
        assert any("new device" in f.lower() for f in factors)

    def test_assess_transaction(self):
        engine = RiskEngine()
        transaction = {
            "transaction_id": "T001",
            "device_first_seen": True,
            "amount_zscore": 2.5,
            "amount_ratio_to_avg": 3.5,
            "transactions_last_1h": 12,
            "merchant_fraud_rate_prior": 0.12,
            "location_fraud_rate_prior": 0.02,
            "customer_transaction_count_prior": 5,
            "customer_transactions_per_day": 25,
        }

        result = engine.assess_transaction(transaction, 0.85)

        assert result.transaction_id == "T001"
        assert 0 <= result.risk_score <= 100
        assert result.risk_level in ["low", "medium", "high", "critical"]
        assert result.recommended_action in ["allow", "monitor", "review", "urgent_review"]
        assert len(result.risk_factors) > 0
        assert len(result.rule_signals) > 0

    def test_assess_batch(self):
        engine = RiskEngine()
        transactions = [
            {"transaction_id": "T001", "device_first_seen": True},
            {"transaction_id": "T002", "device_first_seen": False},
        ]
        probabilities = [0.9, 0.1]

        results = engine.assess_batch(transactions, probabilities)

        assert len(results) == 2
        assert results[0].risk_score > results[1].risk_score

    def test_assess_batch_mismatched_lengths(self):
        engine = RiskEngine()
        transactions = [{"transaction_id": "T001"}]
        probabilities = [0.9, 0.1]

        with pytest.raises(ValueError):
            engine.assess_batch(transactions, probabilities)

    def test_get_investigation_queue(self):
        engine = RiskEngine()
        results = [
            RiskResult("T001", 0.9, 85, "critical", 50, 90, ["factor1"], "urgent_review", []),
            RiskResult("T002", 0.1, 15, "low", 0, 10, [], "allow", []),
            RiskResult("T003", 0.7, 70, "high", 30, 70, ["factor2"], "review", []),
        ]

        queue = engine.get_investigation_queue(results, max_items=2)

        assert len(queue) == 2
        assert queue[0].risk_score >= queue[1].risk_score

    def test_get_summary_statistics(self):
        engine = RiskEngine()
        results = [
            RiskResult("T001", 0.9, 85, "critical", 50, 90, [], "urgent_review", []),
            RiskResult("T002", 0.1, 15, "low", 0, 10, [], "allow", []),
        ]

        stats = engine.get_summary_statistics(results)

        assert stats["total_transactions"] == 2
        assert stats["avg_risk_score"] == 50
        assert stats["risk_level_distribution"]["critical"] == 1
        assert stats["risk_level_distribution"]["low"] == 1
