"""Unit tests for telemetry module

Tests for services/common/telemetry.py
"""

from unittest.mock import MagicMock, patch

import pytest

# Check if opentelemetry is available
try:
    from services.common.telemetry import (
        SpanHelper,
        TraceContext,
        TracingMiddleware,
        get_trace_headers,
        get_trace_id,
        instrument_sqlalchemy,
        setup_fastapi_instrumentation,
        setup_telemetry,
        span_helper,
        timed,
        trace_context,
        traced,
    )
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    pytest.skip("OpenTelemetry not installed", allow_module_level=True)


class TestTraceContext:
    """测试TraceContext类"""

    def test_trace_context_init(self):
        """测试初始化"""
        ctx = TraceContext(trace_id="trace-123", span_id="span-456")
        assert ctx.trace_id == "trace-123"
        assert ctx.span_id == "span-456"
        assert ctx.parent_span_id is None

    def test_trace_context_with_parent(self):
        """测试带父span的上下文"""
        ctx = TraceContext(trace_id="trace-123", span_id="span-456", parent_span_id="parent-789")
        assert ctx.parent_span_id == "parent-789"


class TestSetupTelemetry:
    """测试setup_telemetry函数"""

    @patch("services.common.telemetry.trace")
    @patch("services.common.telemetry.metrics")
    @patch("services.common.telemetry.Resource")
    @patch("services.common.telemetry.TracerProvider")
    @patch("services.common.telemetry.MeterProvider")
    def test_setup_telemetry_with_endpoint(self, mock_meter_provider, mock_tracer_provider, mock_resource, mock_metrics, mock_trace):
        """测试带endpoint的配置"""
        mock_resource_instance = MagicMock()
        mock_resource.create.return_value = mock_resource_instance
        mock_tracer_inst = MagicMock()
        mock_tracer_provider.return_value = mock_tracer_inst
        mock_meter_inst = MagicMock()
        mock_meter_provider.return_value = mock_meter_inst

        tracer_provider, meter_provider = setup_telemetry(
            service_name="test-service",
            endpoint="http://jaeger:4317",
            environment="production"
        )

        assert tracer_provider is not None
        assert meter_provider is not None
        mock_tracer_provider.assert_called_once()
        mock_meter_provider.assert_called_once()

    @patch("services.common.telemetry.trace")
    @patch("services.common.telemetry.metrics")
    @patch("services.common.telemetry.Resource")
    @patch("services.common.telemetry.TracerProvider")
    @patch("services.common.telemetry.MeterProvider")
    @patch("services.common.telemetry.ConsoleSpanExporter")
    @patch("services.common.telemetry.SimpleSpanProcessor")
    def test_setup_telemetry_without_endpoint(self, mock_simple_proc, mock_console_exporter,
                                              mock_meter_provider, mock_tracer_provider,
                                              mock_resource, mock_metrics, mock_trace):
        """测试不带endpoint的配置（控制台导出）"""
        mock_resource_instance = MagicMock()
        mock_resource.create.return_value = mock_resource_instance
        mock_tracer_inst = MagicMock()
        mock_tracer_provider.return_value = mock_tracer_inst
        mock_meter_inst = MagicMock()
        mock_meter_provider.return_value = mock_meter_inst
        mock_span_exporter = MagicMock()
        mock_console_exporter.return_value = mock_span_exporter
        mock_processor = MagicMock()
        mock_simple_proc.return_value = mock_processor

        tracer_provider, meter_provider = setup_telemetry(
            service_name="test-service",
            endpoint=None,
            environment="development"
        )

        assert tracer_provider is not None
        assert meter_provider is not None


class TestSetupFastapiInstrumentation:
    """测试setup_fastapi_instrumentation函数"""

    @patch("services.common.telemetry.setup_telemetry")
    @patch("services.common.telemetry.FastAPIInstrumentor")
    @patch("services.common.telemetry.HTTPxClientInstrumentor")
    def test_setup_with_endpoint(self, mock_httpx_inst, mock_fastapi_inst, mock_setup):
        """测试带endpoint的FastAPI埋点"""
        mock_app = MagicMock()
        mock_tracer_provider = MagicMock()
        mock_meter_provider = MagicMock()
        mock_setup.return_value = (mock_tracer_provider, mock_meter_provider)
        mock_httpx_inst.return_value = MagicMock()

        setup_fastapi_instrumentation(
            app=mock_app,
            service_name="test-service",
            endpoint="http://jaeger:4317"
        )

        mock_setup.assert_called_once_with("test-service", "http://jaeger:4317")
        mock_fastapi_inst.instrument_app.assert_called_once_with(mock_app, tracer_provider=mock_tracer_provider)
        mock_httpx_inst.return_value.instrument.assert_called_once()

    @patch("services.common.telemetry.setup_telemetry")
    @patch("services.common.telemetry.FastAPIInstrumentor")
    def test_setup_without_endpoint(self, mock_fastapi_inst, mock_setup):
        """测试不带endpoint的FastAPI埋点"""
        mock_app = MagicMock()

        setup_fastapi_instrumentation(
            app=mock_app,
            service_name="test-service",
            endpoint=None
        )

        # Should not setup telemetry if no endpoint
        mock_setup.assert_not_called()
        mock_fastapi_inst.instrument_app.assert_not_called()


class TestTracingMiddleware:
    """测试TracingMiddleware类"""

    def test_init(self):
        """测试初始化"""
        middleware = TracingMiddleware("test-app")
        assert middleware.app_name == "test-app"
        assert middleware.tracer is not None

    def test_generate_trace_id(self):
        """测试生成trace_id"""
        middleware = TracingMiddleware("test-app")
        trace_id = middleware._generate_trace_id()
        assert isinstance(trace_id, str)
        assert len(trace_id) > 0

    def test_generate_span_id(self):
        """测试生成span_id"""
        middleware = TracingMiddleware("test-app")
        span_id = middleware._generate_span_id()
        assert isinstance(span_id, str)
        assert len(span_id) == 32  # 16 bytes = 32 hex chars

    @pytest.mark.asyncio
    async def test_call_with_trace_id_header(self):
        """测试带X-Trace-ID的请求"""
        middleware = TracingMiddleware("test-app")

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "existing-trace-123"
        mock_request.state = MagicMock()
        mock_request.method.name = "GET"
        mock_request.url.path = "/test"
        mock_request.url.scheme = "http"
        mock_request.url.hostname = "localhost"
        mock_request.headers.get.side_effect = lambda k, default="": {
            "X-Trace-ID": "existing-trace-123",
            "user-agent": "test-agent"
        }.get(k, default)

        async def mock_call_next(req):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {}
            return mock_response

        with patch.object(middleware, "tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_tracer.start_as_current_span.return_value = mock_span

            response = await middleware(mock_request, mock_call_next)

            assert response.status_code == 200
            assert response.headers.get("X-Trace-ID") == "existing-trace-123"


class TestSpanHelper:
    """测试SpanHelper类"""

    def test_init(self):
        """测试初始化"""
        helper = SpanHelper("test-tracer")
        assert helper.tracer is not None

    def test_init_default_name(self):
        """测试默认名称"""
        helper = SpanHelper()
        assert helper.tracer is not None

    def test_start_span(self):
        """测试开始span"""
        helper = SpanHelper()

        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=False)

        with patch.object(helper.tracer, "start_as_current_span", return_value=mock_span):
            result = helper.start_span("test-operation", {"key": "value"})
            assert result is not None

    def test_add_event(self):
        """测试添加事件"""
        helper = SpanHelper()
        mock_span = MagicMock()

        with patch("services.common.telemetry.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            helper.add_event("test-event", {"attr": "value"})
            mock_span.add_event.assert_called_once()

    def test_set_attribute(self):
        """测试设置属性"""
        helper = SpanHelper()
        mock_span = MagicMock()

        with patch("services.common.telemetry.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            helper.set_attribute("key", "value")
            mock_span.set_attribute.assert_called_once_with("key", "value")

    def test_set_error(self):
        """测试设置错误"""
        helper = SpanHelper()
        mock_span = MagicMock()

        with patch("services.common.telemetry.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            mock_trace.Status = MagicMock()
            mock_trace.StatusCode.ERROR = "ERROR"

            error = ValueError("test error")
            helper.set_error(error)
            mock_span.set_status.assert_called_once()


class TestGetTraceId:
    """测试get_trace_id函数"""

    def test_get_trace_id_with_context(self):
        """测试有上下文时获取trace_id"""
        ctx = TraceContext(trace_id="trace-123", span_id="span-456")
        token = trace_context.set(ctx)

        try:
            result = get_trace_id()
            assert result == "trace-123"
        finally:
            trace_context.reset(token)

    def test_get_trace_id_without_context(self):
        """测试无上下文时获取trace_id"""
        result = get_trace_id()
        assert result is None


class TestInstrumentSqlalchemy:
    """测试instrument_sqlalchemy函数"""

    @patch("services.common.telemetry.SQLAlchemyInstrumentor")
    def test_instrument_sqlalchemy(self, mock_inst):
        """测试SQLAlchemy埋点"""
        mock_engine = MagicMock()
        mock_inst_instance = MagicMock()
        mock_inst.return_value = mock_inst_instance

        instrument_sqlalchemy(mock_engine)

        mock_inst.assert_called_once()
        mock_inst_instance.instrument.assert_called_once_with(mock_engine)


class TestGetTraceHeaders:
    """测试get_trace_headers函数"""

    def test_get_trace_headers_with_context(self):
        """测试有上下文时获取headers"""
        ctx = TraceContext(trace_id="trace-123", span_id="span-456")
        token = trace_context.set(ctx)

        try:
            headers = get_trace_headers()
            assert headers["X-Trace-ID"] == "trace-123"
        finally:
            trace_context.reset(token)

    def test_get_trace_headers_without_context(self):
        """测试无上下文时获取headers"""
        headers = get_trace_headers()
        assert headers == {}


class TestTracedDecorator:
    """测试traced装饰器"""

    @pytest.mark.asyncio
    async def test_traced_decorator_default_name(self):
        """测试默认函数名"""
        @traced()
        async def test_function():
            return "result"

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            result = await test_function()

            assert result == "result"
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_traced_decorator_custom_name(self):
        """测试自定义操作名"""
        @traced("custom.operation")
        async def test_function():
            return "result"

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            result = await test_function()

            assert result == "result"
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_traced_decorator_with_error(self):
        """测试异常处理"""
        @traced("test.operation")
        async def test_function():
            raise ValueError("test error")

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            with patch.object(span_helper, "set_error") as mock_set_error:
                with pytest.raises(ValueError):
                    await test_function()

                mock_set_error.assert_called_once()


class TestTimedDecorator:
    """测试timed装饰器"""

    @pytest.mark.asyncio
    async def test_timed_decorator(self):
        """测试计时装饰器"""
        @timed("test.operation")
        async def test_function():
            return "result"

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            result = await test_function()

            assert result == "result"
            mock_span.set_attribute.assert_called_once()

    @pytest.mark.asyncio
    async def test_timed_decorator_default_name(self):
        """测试默认函数名"""
        @timed()
        async def test_function():
            return "result"

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            result = await test_function()

            assert result == "result"

    @pytest.mark.asyncio
    async def test_timed_decorator_with_error(self):
        """测试异常处理"""
        @timed("test.operation")
        async def test_function():
            raise ValueError("test error")

        with patch.object(span_helper.tracer, "start_as_current_span") as mock_start:
            mock_span = MagicMock()
            mock_span.__enter__ = MagicMock(return_value=mock_span)
            mock_span.__exit__ = MagicMock(return_value=False)
            mock_start.return_value = mock_span

            with patch.object(span_helper, "set_error") as mock_set_error:
                with pytest.raises(ValueError):
                    await test_function()

                mock_set_error.assert_called_once()
