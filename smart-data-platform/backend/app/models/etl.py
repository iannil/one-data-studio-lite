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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ETLStepType(str, enum.Enum):
    FILTER = "filter"
    DEDUPLICATE = "deduplicate"
    MAP_VALUES = "map_values"
    JOIN = "join"
    CALCULATE = "calculate"
    FILL_MISSING = "fill_missing"
    MASK = "mask"
    RENAME = "rename"
    TYPE_CAST = "type_cast"
    AGGREGATE = "aggregate"
    SORT = "sort"
    DROP_COLUMNS = "drop_columns"
    SELECT_COLUMNS = "select_columns"
    CUSTOM_PYTHON = "custom_python"


class PipelineStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ExecutionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ETLPipeline(Base, TimestampMixin):
    __tablename__ = "etl_pipelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[PipelineStatus] = mapped_column(
        SQLEnum(PipelineStatus), default=PipelineStatus.DRAFT
    )

    # Source configuration
    source_type: Mapped[str] = mapped_column(String(50))  # table, query, file
    source_config: Mapped[dict[str, Any]] = mapped_column(JSONB)

    # Target configuration
    target_type: Mapped[str] = mapped_column(String(50))  # table, file
    target_config: Mapped[dict[str, Any]] = mapped_column(JSONB)

    # Scheduling
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100))
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Metadata
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    steps: Mapped[list["ETLStep"]] = relationship(
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="ETLStep.order"
    )
    executions: Mapped[list["ETLExecution"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )


class ETLStep(Base, TimestampMixin):
    __tablename__ = "etl_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("etl_pipelines.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(255))
    step_type: Mapped[ETLStepType] = mapped_column(SQLEnum(ETLStepType))
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    order: Mapped[int] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    pipeline: Mapped["ETLPipeline"] = relationship(back_populates="steps")


class ETLExecution(Base, TimestampMixin):
    __tablename__ = "etl_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("etl_pipelines.id", ondelete="CASCADE")
    )
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Metrics
    rows_input: Mapped[int] = mapped_column(Integer, default=0)
    rows_output: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    failed_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Execution details
    execution_log: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    step_metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    pipeline: Mapped["ETLPipeline"] = relationship(back_populates="executions")
