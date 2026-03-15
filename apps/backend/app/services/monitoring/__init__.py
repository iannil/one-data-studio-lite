"""
Monitoring and Alerting Service Package

Provides Prometheus metrics export and alert rule management.
"""

from .metrics_exporter import (
    PrometheusMiddleware,
    MetricsExporter,
    MetricsContext,
    get_metrics_exporter,
    track_time,
    track_db_query,
    # Metrics
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    db_query_duration_seconds,
    db_connections_total,
    db_connections_max,
    notebook_total,
    training_job_total,
    inference_service_total,
    workflow_run_total,
    user_total,
    tenant_total,
    cpu_usage_percent,
    memory_usage_bytes,
    gpu_usage_percent,
    gpu_memory_usage_percent,
    gpu_temperature_celsius,
    etl_queue_size,
    etl_jobs_processed_total,
    celery_task_total,
    celery_task_duration_seconds,
    celery_queue_length,
    api_key_requests_total,
    quota_usage_percent,
    quota_limit,
    system_info,
)

from .alert_rule import (
    AlertSeverity,
    AlertState,
    MetricOperator,
    NotificationChannel,
    AlertCondition,
    AlertRule,
    Alert,
    AlertRuleEngine,
    get_alert_engine,
)

from .efk import LogAggregator, get_log_aggregator
from .jaeger import TraceExporter, get_trace_exporter

__all__ = [
    # Metrics Exporter
    "PrometheusMiddleware",
    "MetricsExporter",
    "MetricsContext",
    "get_metrics_exporter",
    "track_time",
    "track_db_query",
    # Metrics
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    "db_query_duration_seconds",
    "db_connections_total",
    "db_connections_max",
    "notebook_total",
    "training_job_total",
    "inference_service_total",
    "workflow_run_total",
    "user_total",
    "tenant_total",
    "cpu_usage_percent",
    "memory_usage_bytes",
    "gpu_usage_percent",
    "gpu_memory_usage_percent",
    "gpu_temperature_celsius",
    "etl_queue_size",
    "etl_jobs_processed_total",
    "celery_task_total",
    "celery_task_duration_seconds",
    "celery_queue_length",
    "api_key_requests_total",
    "quota_usage_percent",
    "quota_limit",
    "system_info",
    # Alert Rule
    "AlertSeverity",
    "AlertState",
    "MetricOperator",
    "NotificationChannel",
    "AlertCondition",
    "AlertRule",
    "Alert",
    "AlertRuleEngine",
    "get_alert_engine",
    # EFK
    "LogAggregator",
    "get_log_aggregator",
    # Jaeger
    "TraceExporter",
    "get_trace_exporter",
]
