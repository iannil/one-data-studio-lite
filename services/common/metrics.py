"""Prometheus 指标收集"""

from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app):
    """为 FastAPI 应用添加 Prometheus 指标

    在 /metrics 端点暴露 Prometheus 格式的指标，包括:
    - 请求计数
    - 请求延迟
    - 响应状态码分布
    - 请求大小
    """
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
