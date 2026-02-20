"""Data quality tracking models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QualityIssueSeverity(str, enum.Enum):
    """Severity level for quality issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DataQualityIssue(Base, TimestampMixin):
    """Record of a detected data quality issue."""
    __tablename__ = "data_quality_issues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Associated assets
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        index=True
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        index=True
    )

    # Issue location
    table_name: Mapped[str] = mapped_column(String(255), index=True)
    column_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Issue details
    severity: Mapped[QualityIssueSeverity] = mapped_column(
        SQLEnum(QualityIssueSeverity), default=QualityIssueSeverity.INFO, index=True
    )
    issue_type: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text)

    # Additional context
    context: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # When the issue was detected
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class QualityAssessmentHistory(Base):
    """Historical record of quality assessments for trend tracking."""
    __tablename__ = "quality_assessment_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Associated asset
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        index=True
    )

    # Overall score (weighted average)
    overall_score: Mapped[float] = mapped_column(Float, index=True)

    # Individual dimension scores
    completeness_score: Mapped[float] = mapped_column(Float)
    uniqueness_score: Mapped[float] = mapped_column(Float)
    validity_score: Mapped[float] = mapped_column(Float)
    consistency_score: Mapped[float] = mapped_column(Float)
    timeliness_score: Mapped[float] = mapped_column(Float)

    # Assessment metadata
    row_count: Mapped[Optional[int]] = mapped_column(Float)  # Float for compatibility
    column_count: Mapped[Optional[int]] = mapped_column(Float)

    # Additional metrics
    metrics: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # When the assessment was performed
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
