"""OpenTelemetry 分布式追踪配置

提供统一的追踪服务，支持自动埋点和手动埋点。
"""

import contextvars
import logging

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPxClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricReader, PeriodicMetricsReader
from opentelemetry.sdk.metrics.view import ConsoleMetricExporter
from opentelemetry.sdk.resources import SERVICE_NAME, TELEMETRY_SDK_LANGUAGE
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.resources import Resource

logger = logging.getLogger(__name__)

# 全局追踪上下文变量
trace_context = contextvars.ContextVar("trace_context", default=None)


class TraceContext:
    """追踪上下文

    用于在异步调用间传递追踪信息。
    """

    def __init__(self, trace_id: str, span_id: str, parent_span_id: str | None = None):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id


def setup_telemetry(
    service_name: str,
    endpoint: str | None = None,
    environment: str = "development",
) -> tuple[TracerProvider, MeterProvider]:
    """设置 OpenTelemetry 追踪和指标

    Args:
        service_name: 服务名称
        endpoint: OTLP endpoint (如 http://jaeger:4317)
        environment: 环境标识

    Returns:
        (TracerProvider, MeterProvider)
    """
    # 资源标识
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            TELEMETRY_SDK_LANGUAGE: "python",
            "deployment.environment": environment,
        }
    )

    # ============================================================
    # 追踪配置
    # ============================================================

    if endpoint:
        # 导出到 Jaeger
        span_exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            insecure=True if environment == "development" else False,
        )
        span_processor = BatchSpanProcessor(span_exporter)
    else:
        # 开发环境使用控制台导出
        span_exporter = ConsoleSpanExporter()
        span_processor = SimpleSpanProcessor(span_exporter)

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)

    # 设置全局追踪器
    trace.set_tracer_provider(tracer_provider)

    # ============================================================
    # 指标配置
    # ============================================================

    if endpoint:
        # 导出到 OTLP
        metric_exporter = OTLPMetricExporter(
            endpoint=f"{endpoint}/v1/metrics",
            insecure=True if environment == "development" else False,
        )
        metric_reader = PeriodicMetricsReader(metric_exporter, export_interval_millis=60000)
    else:
        # 开发环境使用控制台导出
        metric_exporter = ConsoleMetricExporter()
        metric_reader = ConsoleMetricReader(metric_exporter)

    meter_provider = MeterProvider(resource=resource)
    meter_provider.add_metrics_reader(metric_reader)

    # 设置全局指标器
    metrics.set_meter_provider(meter_provider)

    logger.info(f"OpenTelemetry 已配置: service={service_name}, endpoint={endpoint or 'console'}")

    return tracer_provider, meter_provider


def setup_fastapi_instrumentation(
    app,
    service_name: str,
    endpoint: str | None = None,
):
    """为 FastAPI 应用添加自动埋点

    Args:
        app: FastAPI 应用实例
        service_name: 服务名称
        endpoint: OTLP endpoint
    """
    # 如果配置了 Jaeger 端点，启用自动埋点
    if endpoint:
        tracer_provider, meter_provider = setup_telemetry(service_name, endpoint)

        # FastAPI 自动埋点
        FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

        # HTTPX 客户端自动埋点
        HTTPxClientInstrumentor().instrument()

        logger.info(f"FastAPI 自动埋点已启用: {service_name}")


class TracingMiddleware:
    """追踪中间件

    为请求添加追踪 ID，并记录请求耗时。
    """

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.tracer = trace.get_tracer(__name__)

    async def __call__(self, request, call_next):
        """处理请求并添加追踪"""
        import time

        # 生成或获取 trace_id
        trace_id = request.headers.get("X-Trace-ID") or self._generate_trace_id()

        # 设置上下文
        ctx = TraceContext(trace_id, self._generate_span_id())
        token = trace_context.set(ctx)

        # 注入 trace_id 到请求头（传递给下游服务）
        request.state.trace_id = trace_id

        start_time = time.time()

        try:
            # 创建 Span
            with self.tracer.start_as_current_span(
                f"{request.method.name} {request.url.path}",
                attributes={
                    "http.method": request.method.name,
                    "http.url": str(request.url),
                    "http.scheme": request.url.scheme,
                    "http.host": request.url.hostname,
                    "http.target": request.url.path,
                    "http.user_agent": request.headers.get("user-agent", ""),
                    "http.trace_id": trace_id,
                    "app.name": self.app_name,
                },
            ) as span:
                # 记录请求开始
                span.add_event("request_started", {"timestamp": start_time})

                # 处理请求
                try:
                    response = await call_next(request)
                    duration = time.time() - start_time

                    # 记录成功
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_attribute("http.response_duration_ms", duration * 1000)
                    span.add_event(
                        "request_completed",
                        {"timestamp": time.time(), "duration_ms": duration * 1000}
                    )

                    # 添加响应头
                    response.headers["X-Trace-ID"] = trace_id

                    return response

                except Exception as e:
                    duration = time.time() - start_time

                    # 记录错误
                    span.set_attribute("error", str(e))
                    span.set_status(
                        trace.Status(
                            code=trace.StatusCode.ERROR,
                            description=str(e)
                        )
                    )
                    span.add_event(
                        "request_failed",
                        {"timestamp": time.time(), "error": str(e), "duration_ms": duration * 1000}
                    )

                    raise

        finally:
            # 恢复上下文
            trace_context.reset(token)

    def _generate_trace_id(self) -> str:
        """生成追踪 ID"""
        import uuid
        return str(uuid.uuid4())

    def _generate_span_id(self) -> str:
        """生成 Span ID"""
        import secrets
        return secrets.token_hex(16)


class SpanHelper:
    """手动埋点辅助类

    用于在代码中手动创建和管理 Span。
    """

    def __init__(self, tracer_name: str = __name__):
        self.tracer = trace.get_tracer(tracer_name)

    def start_span(
        self,
        name: str,
        attributes: dict | None = None,
    ):
        """开始一个 Span

        Args:
            name: Span 名称
            attributes: Span 属性

        Returns:
            Span 对象
        """
        return self.tracer.start_as_current_span(
            name,
            attributes=attributes or {},
        )

    def add_event(self, name: str, attributes: dict | None = None):
        """添加事件到当前 Span

        Args:
            name: 事件名称
            attributes: 事件属性
        """
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(name, attributes or {})

    def set_attribute(self, key: str, value: str):
        """设置当前 Span 的属性

        Args:
            key: 属性键
            value: 属性值
        """
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)

    def set_error(self, error: Exception):
        """标记当前 Span 为错误状态

        Args:
            error: 异常对象
        """
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_status(
                trace.Status(
                    code=trace.StatusCode.ERROR,
                    description=str(error)
                )
            )
            current_span.set_attribute("error.type", type(error).__name__)


# 全局 Span 辅助实例
span_helper = SpanHelper()


def get_trace_id() -> str | None:
    """获取当前追踪 ID

    Returns:
        trace_id 或 None
    """
    ctx = trace_context.get()
    if ctx:
        return ctx.trace_id
    return None


def instrument_sqlalchemy(engine):
    """为 SQLAlchemy 引擎添加自动埋点

    Args:
        engine: SQLAlchemy 引擎
    """
    SQLAlchemyInstrumentor().instrument(engine)
    logger.info("SQLAlchemy 自动埋点已启用")


def get_trace_headers() -> dict:
    """获取追踪请求头

    用于在调用其他服务时传递追踪信息。

    Returns:
        包含追踪信息的请求头字典
    """
    headers = {}
    trace_id = get_trace_id()
    if trace_id:
        headers["X-Trace-ID"] = trace_id
    return headers


# ============================================================
# 便捷装饰器
# ============================================================

def traced(operation_name: str = None):
    """函数追踪装饰器

    自动创建 Span 并记录函数执行时间。

    Args:
        operation_name: 操作名称，默认使用函数名

    Usage:
        @traced("database.query")
        async def query_users():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__

            with span_helper.tracer.start_as_current_span(name) as span:
                span.add_event("function_started", {"function": name})
                try:
                    result = await func(*args, **kwargs)
                    span.add_event("function_completed", {"function": name})
                    return result
                except Exception as e:
                    span_helper.set_error(e)
                    raise

        return wrapper
    return decorator


def timed(operation_name: str = None):
    """计时装饰器

    记录函数执行时间。

    Args:
        operation_name: 操作名称
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            name = operation_name or func.__name__
            start = time.time()

            with span_helper.tracer.start_as_current_span(name) as span:
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start
                    span_helper.set_attribute("duration_ms", duration * 1000)
                    return result
                except Exception as e:
                    span_helper.set_error(e)
                    raise

        return wrapper
    return decorator
