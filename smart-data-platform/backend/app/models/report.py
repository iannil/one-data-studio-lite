"""Report builder models for saving and managing reports."""
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


class ReportStatus(str, enum.Enum):
    """Status of a report."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ChartType(str, enum.Enum):
    """Supported chart types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    TABLE = "table"
    STAT = "stat"
    GAUGE = "gauge"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Report(Base, TimestampMixin):
    """A saved report configuration with multiple charts."""
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    department: Mapped[Optional[str]] = mapped_column(String(255))

    # Status & visibility
    status: Mapped[ReportStatus] = mapped_column(
        SQLEnum(ReportStatus), default=ReportStatus.DRAFT
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Layout configuration (grid positions, sizes)
    layout_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Tags for organization
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Refresh settings
    auto_refresh: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_interval_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    charts: Mapped[list["ReportChart"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportChart.position"
    )


class ReportChart(Base, TimestampMixin):
    """A chart component within a report."""
    __tablename__ = "report_charts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        index=True
    )

    # Chart configuration
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    chart_type: Mapped[ChartType] = mapped_column(SQLEnum(ChartType))

    # Data source (NL query or direct SQL)
    query_type: Mapped[str] = mapped_column(String(50), default="nl_query")
    nl_query: Mapped[Optional[str]] = mapped_column(Text)
    sql_query: Mapped[Optional[str]] = mapped_column(Text)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Chart-specific options
    chart_options: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Visualization configuration
    x_field: Mapped[Optional[str]] = mapped_column(String(255))
    y_field: Mapped[Optional[str]] = mapped_column(String(255))
    group_by: Mapped[Optional[str]] = mapped_column(String(255))

    # Layout (position in grid)
    position: Mapped[int] = mapped_column(Integer, default=0)
    grid_x: Mapped[int] = mapped_column(Integer, default=0)
    grid_y: Mapped[int] = mapped_column(Integer, default=0)
    grid_width: Mapped[int] = mapped_column(Integer, default=6)
    grid_height: Mapped[int] = mapped_column(Integer, default=4)

    # Cached data
    cached_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    cache_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    report: Mapped["Report"] = relationship(back_populates="charts")
