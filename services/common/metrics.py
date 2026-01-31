"""Prometheus 指标收集"""

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


def setup_metrics(app):
    """为 FastAPI 应用添加 Prometheus 指标

    在 /metrics 端点暴露 Prometheus 格式的指标，包括:
    - 请求计数
    - 请求延迟
    - 响应状态码分布
    - 请求大小
    """
    if PROMETHEUS_AVAILABLE:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    else:
        # 如果 Prometheus 不可用，记录警告但继续运行
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("prometheus_fastapi_instrumentator not installed, metrics disabled")
