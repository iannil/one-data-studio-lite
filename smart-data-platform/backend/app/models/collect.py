from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CollectTaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PAUSED = "paused"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CollectTask(Base, TimestampMixin):
    __tablename__ = "collect_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE")
    )
    source_table: Mapped[Optional[str]] = mapped_column(String(255))
    source_query: Mapped[Optional[str]] = mapped_column(Text)  # Custom query
    target_table: Mapped[str] = mapped_column(String(255))

    # Scheduling
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Incremental sync
    is_incremental: Mapped[bool] = mapped_column(Boolean, default=False)
    incremental_field: Mapped[Optional[str]] = mapped_column(String(255))
    last_sync_value: Mapped[Optional[str]] = mapped_column(String(255))

    # Status
    status: Mapped[CollectTaskStatus] = mapped_column(
        SQLEnum(CollectTaskStatus), default=CollectTaskStatus.PENDING
    )
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)

    # Mapping config
    column_mapping: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    source: Mapped["DataSource"] = relationship(back_populates="collect_tasks")
    executions: Mapped[list["CollectExecution"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class CollectExecution(Base, TimestampMixin):
    __tablename__ = "collect_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collect_tasks.id", ondelete="CASCADE")
    )
    status: Mapped[CollectTaskStatus] = mapped_column(SQLEnum(CollectTaskStatus))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    execution_log: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Relationships
    task: Mapped["CollectTask"] = relationship(back_populates="executions")


# Import for type hints (circular import workaround)
from app.models.metadata import DataSource  # noqa: E402
