"""
Monitoring Models

Models for monitoring integration including Prometheus, EFK, and Jaeger.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PrometheusMetric(Base):
    """Prometheus metric definition"""
    __tablename__ = "prometheus_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    metric_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Metric information
    name: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    metric_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # counter, gauge, histogram, summary
    help_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Labels
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    default_labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Value (for gauges)
    current_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Bucket configuration (for histograms)
    buckets: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Object reference
    object_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # job, pipeline, model, etc.
    object_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PrometheusMetric {self.name}>"


class PrometheusRule(Base):
    """Prometheus alerting rule"""
    __tablename__ = "prometheus_rules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    rule_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Rule information
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str] = mapped_column(String(50), default="1m")  # Evaluation duration

    # Severity
    severity: Mapped[str] = mapped_column(String(20), default="warning")  # info, warning, critical

    # Annotations and labels
    annotations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Alert configuration
    alert_type: Mapped[str] = mapped_column(String(50), default="prometheus")  # prometheus, custom
    notification_channels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PrometheusRule {self.name}>"


class LogIndex(Base):
    """Log index for EFK (Elasticsearch, Fluentd, Kibana)"""
    __tablename__ = "log_indices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    index_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Index information
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    index_pattern: Mapped[str] = mapped_column(String(256), nullable=False)  # e.g., "logs-*"

    # Index configuration
    retention_days: Mapped[int] = mapped_column(Integer, default=30)
    shard_count: Mapped[int] = mapped_column(Integer, default=1)
    replica_count: Mapped[int] = mapped_column(Integer, default=1)

    # Field mappings
    field_mappings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Object filtering
    object_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    object_filter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<LogIndex {self.name}>"


class TraceConfig(Base):
    """Jaeger distributed tracing configuration"""
    __tablename__ = "trace_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    trace_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Trace information
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    service_name: Mapped[str] = mapped_column(String(256), nullable=False)

    # Sampling
    sample_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_traces_per_second: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Jaeger endpoint
    jaeger_endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    jaeger_user: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    jaeger_password: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Tags
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    default_tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Batching
    batch_size: Mapped[int] = mapped_column(Integer, default=100)
    batch_timeout: Mapped[int] = mapped_column(Integer, default=5000)  # milliseconds

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TraceConfig {self.name}>"


class Dashboard(Base):
    """Monitoring dashboard configuration"""
    __tablename__ = "dashboards"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    dashboard_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Dashboard information
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dashboard type
    dashboard_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # grafana, kibana, custom

    # Configuration
    panel_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    layout: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Data sources
    data_sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Refresh settings
    refresh_interval: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 10s, 1m, 5m, etc.

    # Filters
    default_filters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Tags
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Dashboard {self.dashboard_id}:{self.title}>"
