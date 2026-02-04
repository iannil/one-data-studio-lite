"""Tests for Prometheus metrics utilities

Tests metrics setup including:
- Prometheus availability check
- Metrics endpoint setup
- Graceful handling when Prometheus is unavailable
"""


from services.common.metrics import PROMETHEUS_AVAILABLE, setup_metrics


class TestPrometheusAvailable:
    """Tests for PROMETHEUS_AVAILABLE flag"""

    def test_prometheus_available_is_boolean(self):
        """Should be a boolean value"""
        assert isinstance(PROMETHEUS_AVAILABLE, bool)


class TestSetupMetrics:
    """Tests for setup_metrics function"""

    def test_setup_metrics_is_callable(self):
        """Should be a callable function"""
        assert callable(setup_metrics)

    def test_setup_metrics_accepts_app(self):
        """Should accept an app parameter without throwing error"""
        mock_app = object()  # Just a mock object
        # Should not raise error
        setup_metrics(mock_app)

    def test_setup_metrics_with_mock_app(self):
        """Should handle mock app objects"""
        class MockApp:
            pass

        mock_app = MockApp()
        # Should not raise error
        setup_metrics(mock_app)


class TestMetricsIntegration:
    """Integration tests for metrics setup"""

    def test_setup_metrics_exists(self):
        """Should have setup_metrics function available"""
        from services.common import metrics
        assert hasattr(metrics, 'setup_metrics')

    def test_prometheus_available_constant_exists(self):
        """Should have PROMETHEUS_AVAILABLE constant"""
        from services.common import metrics
        assert hasattr(metrics, 'PROMETHEUS_AVAILABLE')

    def test_can_import_metrics_module(self):
        """Should be able to import metrics module"""
        from services.common import metrics
        assert metrics is not None
