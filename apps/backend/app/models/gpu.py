"""
GPU and Resource Pool models
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GPURecord(Base):
    """GPU inventory record"""
    __tablename__ = "gpu_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    gpu_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    gpu_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vendor: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    uuid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bus_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    node_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Memory
    total_memory_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    # Compute capability
    compute_capability: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Features
    supports_mig: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mig_device: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_gpu_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    health_status: Mapped[str] = mapped_column(String(20), default="healthy")  # healthy, warning, error

    # Labels
    labels: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<GPURecord {self.gpu_id}:{self.gpu_type}>"


class GPUAllocationRecord(Base):
    """GPU allocation record"""
    __tablename__ = "gpu_allocation_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    allocation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    gpu_ids: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    gpu_type: Mapped[str] = mapped_column(String(50), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Who allocated
    allocated_to: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # task_id or user_id
    allocated_by: Mapped[str] = mapped_column(String(100), nullable=False)  # user_id

    # Timing
    allocated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, expired, returned

    # Metadata
    metadata: Mapped[dict] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<GPUAllocationRecord {self.allocation_id}:{self.status}>"


class ResourcePoolRecord(Base):
    """Resource pool record"""
    __tablename__ = "resource_pool_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pool_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nodes
    node_names: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    # Allocation policy
    allocation_policy: Mapped[str] = mapped_column(String(50), default="best_fit")

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Labels
    labels: Mapped[dict] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ResourcePoolRecord {self.pool_id}>"


class ResourceQuotaRecord(Base):
    """Resource quota record"""
    __tablename__ = "resource_quota_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pool_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("resource_pool_records.pool_id"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quota_type: Mapped[str] = mapped_column(String(20), default="hard")  # hard, soft, burst
    limit: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    burst_limit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    burst_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ResourceQuotaRecord {self.pool_id}:{self.resource_type}>"


class PoolAllocationRecord(Base):
    """Pool allocation record"""
    __tablename__ = "pool_allocation_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    allocation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    pool_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("resource_pool_records.pool_id"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Resources allocated
    resources: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Timing
    allocated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PoolAllocationRecord {self.allocation_id}:{self.status}>"


class GPUMetricsRecord(Base):
    """GPU metrics record for historical data"""
    __tablename__ = "gpu_metrics_records"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    gpu_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Metrics
    utilization_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_used_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_free_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    power_usage_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Additional metrics as JSON
    additional_metrics: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Timestamp
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<GPUMetricsRecord {self.gpu_id}@{self.recorded_at}>"
