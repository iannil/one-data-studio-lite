"""Unit tests for metrics module

Tests for services/common/metrics.py
"""

from unittest.mock import MagicMock, patch

import pytest

from services.common.metrics import (
    PROMETHEUS_AVAILABLE,
    setup_metrics,
)


class TestPrometheusAvailable:
    """测试Prometheus可用性标志"""

    def test_prometheus_available_is_bool(self):
        """测试PROMETHEUS_AVAILABLE是布尔值"""
        assert isinstance(PROMETHEUS_AVAILABLE, bool)


class TestSetupMetrics:
    """测试setup_metrics函数"""

    def test_setup_metrics_with_prometheus_available(self):
        """测试Prometheus可用时设置指标"""
        mock_app = MagicMock()

        # Mock Instrumentator
        mock_instrumentator = MagicMock()
        mock_instrumentator.instrument.return_value = mock_instrumentator
        mock_instrumentator.expose.return_value = mock_instrumentator

        with patch('services.common.metrics.PROMETHEUS_AVAILABLE', True):
            with patch('services.common.metrics.Instrumentator', return_value=mock_instrumentator):
                setup_metrics(mock_app)

                # Should instrument and expose the app
                mock_instrumentator.instrument.assert_called_once_with(mock_app)
                mock_instrumentator.expose.assert_called_once_with(mock_app, endpoint="/metrics")

    def test_setup_metrics_without_prometheus(self):
        """测试Prometheus不可用时的行为"""
        mock_app = MagicMock()

        with patch('services.common.metrics.PROMETHEUS_AVAILABLE', False):
            # Should log warning but not crash
            setup_metrics(mock_app)

            # App should not have been modified
            assert not mock_app.add_route.called

    def test_setup_metrics_import_error(self):
        """测试导入错误时的行为"""
        mock_app = MagicMock()

        with patch('services.common.metrics.PROMETHEUS_AVAILABLE', False):
            # Should handle gracefully
            setup_metrics(mock_app)

            # Should not raise exception
            assert True  # If we get here, no exception was raised
