"""Tests for dashboard data access layer.

Tests verify query construction, parameter handling, and transformation logic
without requiring a live database connection.
"""

from unittest.mock import MagicMock, patch

from fraudlens.dashboard.data.connection import query_scalar


class TestConnection:
    @patch("fraudlens.dashboard.data.connection.get_connection")
    def test_query_scalar_returns_value(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        result = query_scalar("SELECT COUNT(*) FROM raw.transactions")
        assert result == 42

    @patch("fraudlens.dashboard.data.connection.get_connection")
    def test_query_scalar_returns_none_on_empty(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        result = query_scalar("SELECT COUNT(*) FROM nonexistent")
        assert result is None


class TestExecutiveQueries:
    @patch("fraudlens.dashboard.data.executive.query_scalar")
    def test_get_kpi_summary_structure(self, mock_scalar):
        mock_scalar.side_effect = [1000, 36, 500000.0, 18000.0, 500.0]
        from fraudlens.dashboard.data.executive import get_kpi_summary

        result = get_kpi_summary()

        assert "total_transactions" in result
        assert "fraud_count" in result
        assert "fraud_rate" in result
        assert "total_value" in result
        assert "fraud_value" in result
        assert "avg_amount" in result
        assert result["total_transactions"] == 1000
        assert result["fraud_count"] == 36
        assert result["fraud_rate"] == 3.6

    @patch("fraudlens.dashboard.data.executive.query_scalar")
    def test_get_kpi_summary_zero_division(self, mock_scalar):
        mock_scalar.side_effect = [0, 0, 0, 0, 0]
        from fraudlens.dashboard.data.executive import get_kpi_summary

        result = get_kpi_summary()
        assert result["fraud_rate"] == 0


class TestRiskQueries:
    @patch("fraudlens.dashboard.data.risk.query_scalar")
    def test_get_risk_kpi_summary_structure(self, mock_scalar):
        mock_scalar.side_effect = [500, 50, 10, 45.5, 60]
        from fraudlens.dashboard.data.risk import get_risk_kpi_summary

        result = get_risk_kpi_summary()

        assert "total_scored" in result
        assert "high_risk" in result
        assert "critical_risk" in result
        assert "high_risk_pct" in result
        assert "avg_risk_score" in result
        assert "review_count" in result
        assert result["high_risk_pct"] == 10.0


class TestInvestigationQueries:
    @patch("fraudlens.dashboard.data.investigations.query_scalar")
    def test_get_investigation_stats_structure(self, mock_scalar):
        mock_scalar.side_effect = [1000, 100, 80]
        from fraudlens.dashboard.data.investigations import get_investigation_stats

        result = get_investigation_stats()

        assert "total_scored" in result
        assert "high_critical_count" in result
        assert "needs_review_count" in result


class TestParseJsonList:
    def test_parse_json_list_with_list(self):
        from fraudlens.dashboard.app import _parse_json_list

        result = _parse_json_list(["a", "b", "c"])
        assert result == ["a", "b", "c"]

    def test_parse_json_list_with_json_string(self):
        from fraudlens.dashboard.app import _parse_json_list

        result = _parse_json_list('["a", "b"]')
        assert result == ["a", "b"]

    def test_parse_json_list_with_plain_string(self):
        from fraudlens.dashboard.app import _parse_json_list

        result = _parse_json_list("hello")
        assert result == ["hello"]

    def test_parse_json_list_with_none(self):
        from fraudlens.dashboard.app import _parse_json_list

        result = _parse_json_list(None)
        assert result == []

    def test_parse_json_list_with_empty_string(self):
        from fraudlens.dashboard.app import _parse_json_list

        result = _parse_json_list("")
        assert result == []


class TestDashboardApp:
    def test_check_db_connection_returns_bool(self):
        """Test that _check_db_connection returns a boolean."""
        from fraudlens.dashboard.app import _check_db_connection

        result = _check_db_connection()
        assert isinstance(result, bool)

    def test_dashboard_importable(self):
        """Test that the dashboard module can be imported."""
        from fraudlens.dashboard import app

        assert hasattr(app, "create_dashboard")
        assert hasattr(app, "_render_executive_overview")
        assert hasattr(app, "_render_risk_monitoring")
        assert hasattr(app, "_render_investigation_queue")
        assert hasattr(app, "_render_fraud_analysis")
        assert hasattr(app, "_render_model_performance")
