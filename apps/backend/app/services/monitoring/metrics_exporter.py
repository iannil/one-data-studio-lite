"""
Monitoring and Metrics Service

Provides Prometheus metrics export and monitoring capabilities.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    Info,
    Enum,
    CollectorRegistry,
    generate_latest,
    REGISTRY,
    exposition,
)

from fastapi import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from sqlalchemy.orm import Session
from app.core.database import get_db

logger = logging.getLogger(__name__)

# ============================================================================
# Metrics Definitions
# ============================================================================

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=(.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)

# Database metrics
db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=(.001, .005, .01, .025, .05, .1, .25, .5, 1.0, 2.5, 5.0, 10.0),
)

db_connections_total = Gauge(
    "db_connections_total",
    "Total database connections",
    ["state"],  # idle, in_use
)

db_connections_max = Gauge(
    "db_connections_max",
    "Maximum database connections",
)

# Business metrics
notebook_total = Gauge(
    "notebook_total",
    "Total notebooks",
    ["state"],  # running, stopped, error
)

training_job_total = Gauge(
    "training_job_total",
    "Total training jobs",
    ["state"],
)

inference_service_total = Gauge(
    "inference_service_total",
    "Total inference services",
    ["state"],
)

workflow_run_total = Gauge(
    "workflow_run_total",
    "Total workflow runs",
    ["state"],
)

user_total = Gauge(
    "user_total",
    "Total users",
    ["status"],  # active, inactive
)

tenant_total = Gauge(
    "tenant_total",
    "Total tenants",
    ["status", "tier"],
)

# Resource usage metrics
cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "CPU usage percentage",
    ["service", "instance"],
)

memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "Memory usage in bytes",
    ["service", "instance"],
)

gpu_usage_percent = Gauge(
    "gpu_usage_percent",
    "GPU usage percentage",
    ["gpu_id"],
)

gpu_memory_usage_percent = Gauge(
    "gpu_memory_usage_percent",
    "GPU memory usage percentage",
    ["gpu_id"],
)

gpu_temperature_celsius = Gauge(
    "gpu_temperature_celsius",
    "GPU temperature in Celsius",
    ["gpu_id"],
)

# Queue metrics
etl_queue_size = Gauge(
    "etl_queue_size",
    "ETL queue size",
    ["queue_name"],
)

etl_jobs_processed_total = Counter(
    "etl_jobs_processed_total",
    "Total ETL jobs processed",
    ["queue_name", "status"],
)

# Celery task metrics
celery_task_total = Counter(
    "celery_task_total",
    "Total Celery tasks",
    ["task_name", "status"],
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration",
    ["task_name"],
    buckets=(.1, .5, 1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600),
)

celery_queue_length = Gauge(
    "celery_queue_length",
    "Celery queue length",
    ["queue_name"],
)

# API key usage
api_key_requests_total = Counter(
    "api_key_requests_total",
    "Total API key requests",
    ["key_id", "status"],
)

# Quota metrics
quota_usage_percent = Gauge(
    "quota_usage_percent",
    "Quota usage percentage",
    ["tenant_id", "resource_type"],
)

quota_limit = Gauge(
    "quota_limit",
    "Quota limit",
    ["tenant_id", "resource_type"],
)

# System metrics
system_info = Info(
    "system_info",
    "System information",
)

# ============================================================================
# Metrics Collection Context
# ============================================================================


@dataclass
class MetricLabel:
    """Prometheus metric labels"""
    method: str = ""
    endpoint: str = ""
    status: str = ""
    operation: str = ""
    table: str = ""
    state: str = ""
    queue_name: str = ""
    task_name: str = ""
    service: str = ""
    instance: str = ""
    gpu_id: str = ""
    tenant_id: str = ""
    resource_type: str = ""
    key_id: str = ""


class MetricsContext:
    """Context manager for tracking metrics"""

    def __init__(self, labels: Dict[str, str]):
        self.labels = labels
        self.start_time = time.time()

    def record_http_request(self, status: int, labels: Optional[Dict[str, str]] = None):
        """Record HTTP request metrics"""
        combined_labels = {**self.labels, **(labels or {})}
        http_requests_total.labels(
            method=combined_labels.get("method", ""),
            endpoint=combined_labels.get("endpoint", ""),
            status=str(status),
        ).inc()
        http_request_duration_seconds.labels(
            method=combined_labels.get("method", ""),
            endpoint=combined_labels.get("endpoint", ""),
        ).observe(time.time() - self.start_time)

    def record_db_query(self, operation: str, table: str, labels: Optional[Dict[str, str]] = None):
        """Record database query metrics"""
        combined_labels = {**self.labels, **(labels or {})}
        duration = time.time() - self.start_time
        db_query_duration_seconds.labels(
            operation=operation,
            table=table,
        ).observe(duration)

        logger.debug(f"DB Query: {operation} on {table} took {duration:.3f}s")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# ============================================================================
# Metrics Middleware
# ============================================================================


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for Prometheus metrics collection.
    """

    async def dispatch(self, request: Request, call_next):
        # Get method and path
        method = request.method
        path = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Start timer
        start_time = time.time()

        try:
            response = await call_next(request)

            # Record metrics
            status = response.status_code
            duration = time.time() - start_time

            http_requests_total.labels(method=method, endpoint=path, status=str(status)).inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

            return response

        except Exception as e:
            # Record error
            duration = time.time() - start_time
            http_requests_total.labels(method=method, endpoint=path, status="500").inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)
            raise

        finally:
            http_requests_in_progress.labels(method=method, endpoint=path).dec()


# ============================================================================
# Metrics Exporter
# ============================================================================


class MetricsExporter:
    """
    Metrics Exporter Service

    Collects and exposes metrics for Prometheus scraping.
    """

    def __init__(self):
        self.start_time = time.time()
        self._collectors: List[Callable] = []

    def register_collector(self, collector: Callable) -> None:
        """Register a custom collector function"""
        self._collectors.append(collector)

    async def update_db_metrics(self, db: Session) -> None:
        """Update database connection metrics"""
        try:
            # Get connection pool info
            engine = db.get_bind()
            pool = engine.pool

            if hasattr(pool, 'size'):
                db_connections_max.set(pool.size())

            if hasattr(pool, 'checkedout'):
                db_connections_total.labels(state="in_use").set(pool.checkedout())
                db_connections_total.labels(state="idle").set(pool.size() - pool.checkedout())

        except Exception as e:
            logger.warning(f"Failed to update DB metrics: {e}")

    async def update_notebook_metrics(self) -> None:
        """Update notebook metrics"""
        try:
            from app.api.v1.operator import get_operator_manager

            manager = get_operator_manager()
            notebooks = manager.list_notebooks()

            # Count by state
            states = {}
            for nb in notebooks:
                state = nb.get("status", {}).get("phase", "unknown")
                states[state] = states.get(state, 0) + 1

            # Update gauges
            for state, count in states.items():
                notebook_total.labels(state=state).set(count)

        except Exception as e:
            logger.warning(f"Failed to update notebook metrics: {e}")

    async def update_training_job_metrics(self) -> None:
        """Update training job metrics"""
        try:
            from app.api.v1.operator import get_operator_manager

            manager = get_operator_manager()
            jobs = manager.list_training_jobs()

            # Count by state
            states = {}
            for job in jobs:
                state = job.get("status", {}).get("phase", "unknown")
                states[state] = states.get(state, 0) + 1

            # Update gauges
            for state, count in states.items():
                training_job_total.labels(state=state).set(count)

        except Exception as e:
            logger.warning(f"Failed to update training job metrics: {e}")

    async def update_inference_service_metrics(self) -> None:
        """Update inference service metrics"""
        try:
            from app.api.v1.operator import get_operator_manager

            manager = get_operator_manager()
            services = manager.list_inference_services()

            # Count by state
            states = {}
            for svc in services:
                state = svc.get("status", {}).get("phase", "unknown")
                states[state] = states.get(state, 0) + 1

            # Update gauges
            for state, count in states.items():
                inference_service_total.labels(state=state).set(count)

        except Exception as e:
            logger.warning(f"Failed to update inference service metrics: {e}")

    async def update_workflow_metrics(self) -> None:
        """Update workflow run metrics"""
        try:
            from app.models.workflow import DAGRun

            # Query database
            async with get_db() as db:
                runs = db.query(DAGRun).all()

                # Count by state
                states = {}
                for run in runs:
                    state = run.state or "unknown"
                    states[state] = states.get(state, 0) + 1

                # Update gauges
                for state, count in states.items():
                    workflow_run_total.labels(state=state).set(count)

        except Exception as e:
            logger.warning(f"Failed to update workflow metrics: {e}")

    async def update_user_metrics(self) -> None:
        """Update user metrics"""
        try:
            from app.models.user import User

            async with get_db() as db:
                active = db.query(User).filter(User.is_active == True).count()
                inactive = db.query(User).filter(User.is_active == False).count()

                user_total.labels(status="active").set(active)
                user_total.labels(status="inactive").set(inactive)

        except Exception as e:
            logger.warning(f"Failed to update user metrics: {e}")

    async def update_tenant_metrics(self) -> None:
        """Update tenant metrics"""
        try:
            from app.models.tenant import Tenant, TenantTier

            async with get_db() as db:
                tenants = db.query(Tenant).all()

                # Count by status and tier
                status_counts = {}
                tier_counts = {}

                for tenant in tenants:
                    status = tenant.status or "unknown"
                    tier = tenant.tier or "unknown"
                    status_counts[status] = status_counts.get(status, 0) + 1
                    tier_counts[tier] = tier_counts.get(tier, 0) + 1

                # Update gauges
                for status, count in status_counts.items():
                    tenant_total.labels(status=status, tier="all").set(count)

                for tier, count in tier_counts.items():
                    tenant_total.labels(status="all", tier=tier).set(count)

        except Exception as e:
            logger.warning(f"Failed to update tenant metrics: {e}")

    async def update_gpu_metrics(self) -> None:
        """Update GPU metrics"""
        try:
            from app.services.gpu import get_gpu_pool_manager

            manager = get_gpu_pool_manager()
            pool_status = manager.get_pool_status()

            # Update GPU metrics
            for gpu in pool_status.get("gpus", []):
                gpu_id = gpu["gpu_id"]
                cpu_util = gpu.get("utilization_percent", 0)
                temp = gpu.get("temperature_celsius", 0)

                gpu_usage_percent.labels(gpu_id=gpu_id).set(cpu_util)
                gpu_temperature_celsius.labels(gpu_id=gpu_id).set(temp)

                # Memory usage if available
                if "memory_used_mb" in gpu and "total_memory_mb" in gpu:
                    used = gpu["memory_used_mb"]
                    total = gpu["total_memory_mb"]
                    mem_percent = (used / total * 100) if total > 0 else 0
                    gpu_memory_usage_percent.labels(gpu_id=gpu_id).set(mem_percent)

        except Exception as e:
            logger.warning(f"Failed to update GPU metrics: {e}")

    async def update_quota_metrics(self) -> None:
        """Update quota usage metrics"""
        try:
            from app.models.tenant import Tenant
            from app.services.tenant import QuotaService

            async with get_db() as db:
                tenants = db.query(Tenant).filter(Tenant.status == "active").all()

                for tenant in tenants:
                    quota_service = QuotaService(db)
                    summary = quota_service.get_quota_summary(tenant.id)

                    # Update usage for each resource type
                    for attr_name, value in vars(summary).items():
                        if hasattr(value, "current") and hasattr(value, "limit"):
                            usage = value.current
                            limit = value.limit
                            if limit > 0:
                                percent = (usage / limit * 100) if usage else 0
                                quota_usage_percent.labels(
                                    tenant_id=str(tenant.id),
                                    resource_type=attr_name,
                                ).set(percent)
                                quota_limit.labels(
                                    tenant_id=str(tenant.id),
                                    resource_type=attr_name,
                                ).set(limit)

        except Exception as e:
            logger.warning(f"Failed to update quota metrics: {e}")

    async def update_all_metrics(self) -> None:
        """Update all metrics"""
        try:
            async with get_db() as db:
                await self.update_db_metrics(db)

            await self.update_notebook_metrics()
            await self.update_training_job_metrics()
            await self.update_inference_service_metrics()
            await self.update_workflow_metrics()
            await self.update_user_metrics()
            await self.update_tenant_metrics()
            await self.update_gpu_metrics()
            await self.update_quota_metrics()

            # Call custom collectors
            for collector in self._collectors:
                try:
                    await collector()
                except Exception as e:
                    logger.error(f"Custom collector failed: {e}")

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(REGISTRY).decode("utf-8")


# Global metrics exporter instance
_metrics_exporter: Optional[MetricsExporter] = None


def get_metrics_exporter() -> MetricsExporter:
    """Get the global metrics exporter instance"""
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = MetricsExporter()
    return _metrics_exporter


# ============================================================================
# Metrics Decorators
# ============================================================================


def track_time(operation: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track operation time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                logger.debug(f"{operation} took {duration:.3f}s")

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                logger.debug(f"{operation} took {duration:.3f}s")

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_db_query(operation: str, table: str):
    """Decorator to track database query time"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
