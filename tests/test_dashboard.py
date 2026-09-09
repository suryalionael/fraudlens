"""Tests for dashboard module."""

import pytest


class TestDashboard:
    def test_import(self):
        """Test that dashboard module can be imported."""
        from fraudlens.dashboard import create_dashboard
        assert create_dashboard is not None

    def test_create_dashboard_function(self):
        """Test that create_dashboard function exists."""
        from fraudlens.dashboard.app import create_dashboard
        assert callable(create_dashboard)
