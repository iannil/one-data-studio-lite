"""
TensorBoard Integration Models

Models for managing TensorBoard instances linked to training experiments.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TensorBoardInstance(Base):
    """TensorBoard instance record"""
    __tablename__ = "tensorboard_instances"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    instance_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Associated experiment/run
    experiment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    training_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Log directory configuration
    log_dir: Mapped[str] = mapped_column(String(500), nullable=False)
    log_source: Mapped[str] = mapped_column(String(50), default="minio")  # minio, nfs, s3, oss

    # Service configuration
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Container configuration
    image: Mapped[str] = mapped_column(String(256), default="tensorflow/tensorboard:latest")
    port: Mapped[int] = mapped_column(Integer, default=6006)

    # Resource limits
    cpu_limit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "500m"
    cpu_request: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    memory_limit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # e.g., "2Gi"
    memory_request: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Service type
    service_type: Mapped[str] = mapped_column(String(50), default="ClusterIP")  # ClusterIP, NodePort, LoadBalancer

    # Kubernetes resources
    namespace: Mapped[str] = mapped_column(String(100), default="default")
    pod_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    ingress_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Access URLs
    internal_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Additional TensorBoard arguments
    tensorboard_args: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # e.g., ["--logdir", "--host", "0.0.0.0"]

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True
    )  # pending, starting, running, stopped, failed, error
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Auto-stop configuration
    auto_stop: Mapped[bool] = mapped_column(Boolean, default=True)
    idle_timeout_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=3600)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_access_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Labels and annotations
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    annotations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<TensorBoardInstance {self.instance_id}:{self.status}>"


class TensorBoardAccessLog(Base):
    """TensorBoard access log for tracking usage"""
    __tablename__ = "tensorboard_access_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    instance_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("tensorboard_instances.instance_id"), nullable=False, index=True
    )

    # Access info
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_type: Mapped[str] = mapped_column(String(20), default="web")  # web, api
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Session info
    session_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamp
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<TensorBoardAccessLog {self.instance_id}@{self.accessed_at}>"


class TensorBoardConfig(Base):
    """Global TensorBoard configuration"""
    __tablename__ = "tensorboard_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TensorBoardConfig {self.key}>"
