"""Unit tests for telemetry utilities

Tests for services/common/telemetry.py

Note: OpenTelemetry is an optional dependency. Tests will be skipped if not installed.
"""

import sys

import pytest

# Skip all tests if opentelemetry is not installed
pytest.importorskip("opentelemetry", reason="opentelemetry not installed")

from unittest.mock import AsyncMock, MagicMock, patch

from services.common.telemetry import (
    TraceContext,
    setup_telemetry,
    setup_fastapi_instrumentation,
    TracingMiddleware,
    SpanHelper,
    get_trace_id,
    get_trace_headers,
    traced,
    timed,
)


class TestTraceContext:
    """测试追踪上下文"""

    def test_init_basic(self):
        """测试基本初始化"""
        ctx = TraceContext("trace-123", "span-456")

        assert ctx.trace_id == "trace-123"
        assert ctx.span_id == "span-456"
        assert ctx.parent_span_id is None

    def test_init_with_parent(self):
        """测试带父 span 初始化"""
        ctx = TraceContext("trace-123", "span-456", "parent-789")

        assert ctx.trace_id == "trace-123"
        assert ctx.span_id == "span-456"
        assert ctx.parent_span_id == "parent-789"


class TestSpanHelper:
    """测试 Span 辅助类"""

    def test_init_default(self):
        """测试默认初始化"""
        helper = SpanHelper()

        assert helper.tracer is not None

    def test_init_custom_name(self):
        """测试自定义名称初始化"""
        helper = SpanHelper("custom.tracer")

        assert helper.tracer is not None

    def test_add_event(self):
        """测试添加事件"""
        helper = SpanHelper()

        # Should not raise exception
        helper.add_event("test_event", {"key": "value"})

    def test_set_attribute(self):
        """测试设置属性"""
        helper = SpanHelper()

        # Should not raise exception
        helper.set_attribute("test_key", "test_value")

    def test_set_error(self):
        """测试设置错误"""
        helper = SpanHelper()

        # Should not raise exception
        helper.set_error(ValueError("Test error"))


class TestGetTraceId:
    """测试获取追踪 ID"""

    def test_get_trace_id_no_context(self):
        """测试无上下文时返回 None"""
        with patch('services.common.telemetry.trace_context') as mock_ctx:
            mock_ctx.get.return_value = None

            result = get_trace_id()

            assert result is None

    def test_get_trace_id_with_context(self):
        """测试有上下文时返回 trace_id"""
        with patch('services.common.telemetry.trace_context') as mock_ctx:
            mock_ctx.get.return_value = TraceContext("trace-123", "span-456")

            result = get_trace_id()

            assert result == "trace-123"


class TestGetTraceHeaders:
    """测试获取追踪请求头"""

    def test_get_trace_headers_no_context(self):
        """测试无上下文时返回空字典"""
        with patch('services.common.telemetry.get_trace_id', return_value=None):
            result = get_trace_headers()

            assert result == {}

    def test_get_trace_headers_with_context(self):
        """测试有上下文时返回请求头"""
        with patch('services.common.telemetry.get_trace_id', return_value="trace-123"):
            result = get_trace_headers()

            assert result == {"X-Trace-ID": "trace-123"}


class TestTracingMiddleware:
    """测试追踪中间件"""

    def test_init(self):
        """测试初始化"""
        app = MagicMock()
        middleware = TracingMiddleware(app_name="test-app")

        assert middleware.app_name == "test-app"
        assert middleware.tracer is not None

    def test_generate_trace_id(self):
        """测试生成追踪 ID"""
        app = MagicMock()
        middleware = TracingMiddleware(app_name="test-app")

        trace_id = middleware._generate_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 36  # UUID format

    def test_generate_span_id(self):
        """测试生成 Span ID"""
        app = MagicMock()
        middleware = TracingMiddleware(app_name="test-app")

        span_id = middleware._generate_span_id()

        assert isinstance(span_id, str)
        assert len(span_id) == 32  # 16 bytes = 32 hex chars


class TestDecorators:
    """测试装饰器"""

    @pytest.mark.asyncio
    async def test_traced_decorator(self):
        """测试追踪装饰器"""
        @traced("test.operation")
        async def test_function():
            return "result"

        result = await test_function()

        assert result == "result"

    @pytest.mark.asyncio
    async def test_timed_decorator(self):
        """测试计时装饰器"""
        @timed("test.operation")
        async def test_function():
            return "result"

        result = await test_function()

        assert result == "result"

    @pytest.mark.asyncio
    async def test_traced_decorator_default_name(self):
        """测试追踪装饰器默认名称"""
        @traced()
        async def test_function():
            return "result"

        result = await test_function()

        assert result == "result"


class TestSetupTelemetry:
    """测试遥测设置"""

    @patch('services.common.telemetry.TracerProvider')
    @patch('services.common.telemetry.MeterProvider')
    @patch('services.common.telemetry.trace')
    @patch('services.common.telemetry.metrics')
    def test_setup_telemetry_no_endpoint(self, mock_metrics, mock_trace, mock_meter_provider, mock_tracer_provider):
        """测试无端点时设置遥测"""
        with patch('services.common.telemetry.ConsoleSpanExporter'):
            with patch('services.common.telemetry.SimpleSpanProcessor'):
                with patch('services.common.telemetry.ConsoleMetricExporter'):
                    with patch('services.common.telemetry.ConsoleMetricReader'):
                        tracer_provider, meter_provider = setup_telemetry("test-service")

                        assert tracer_provider is not None
                        assert meter_provider is not None

    @patch('services.common.telemetry.TracerProvider')
    @patch('services.common.telemetry.MeterProvider')
    @patch('services.common.telemetry.trace')
    @patch('services.common.telemetry.metrics')
    def test_setup_telemetry_with_endpoint(self, mock_metrics, mock_trace, mock_meter_provider, mock_tracer_provider):
        """测试有端点时设置遥测"""
        with patch('services.common.telemetry.OTLPSpanExporter'):
            with patch('services.common.telemetry.BatchSpanProcessor'):
                with patch('services.common.telemetry.OTLPMetricExporter'):
                    with patch('services.common.telemetry.PeriodicMetricsReader'):
                        tracer_provider, meter_provider = setup_telemetry(
                            "test-service",
                            endpoint="http://jaeger:4317"
                        )

                        assert tracer_provider is not None
                        assert meter_provider is not None


class TestSetupFastAPIInstrumentation:
    """测试 FastAPI 自动埋点"""

    def test_setup_fastapi_instrumentation_no_endpoint(self):
        """测试无端点时设置 FastAPI 埋点"""
        app = MagicMock()

        # Should not raise exception
        setup_fastapi_instrumentation(app, "test-service", endpoint=None)

    @patch('services.common.telemetry.setup_telemetry')
    @patch('services.common.telemetry.FastAPIInstrumentor')
    @patch('services.common.telemetry.HTTPxClientInstrumentor')
    def test_setup_fastapi_instrumentation_with_endpoint(
        self, mock_httpx, mock_fastapi, mock_setup
    ):
        """测试有端点时设置 FastAPI 埋点"""
        app = MagicMock()

        setup_fastapi_instrumentation(app, "test-service", endpoint="http://jaeger:4317")

        # Verify setup was called
        mock_setup.assert_called_once()
