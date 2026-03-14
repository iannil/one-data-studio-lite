"""Data standard models for field format specifications and encoding rules."""
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


class StandardType(str, enum.Enum):
    """Types of data standards."""
    FIELD_FORMAT = "field_format"
    ENCODING_RULE = "encoding_rule"
    NAMING_CONVENTION = "naming_convention"
    VALUE_DOMAIN = "value_domain"
    DATA_QUALITY = "data_quality"


class StandardStatus(str, enum.Enum):
    """Standard lifecycle status."""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class DataStandard(Base):
    """Data standard definition model.

    Defines field format specifications, encoding rules, naming conventions,
    and value domain constraints.
    """
    __tablename__ = "data_standards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    standard_type: Mapped[StandardType] = mapped_column(SQLEnum(StandardType))
    status: Mapped[StandardStatus] = mapped_column(
        SQLEnum(StandardStatus), default=StandardStatus.DRAFT
    )

    # Standard rules specification
    rules: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    """
    Rules structure varies by standard_type:

    FIELD_FORMAT:
    {
        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
        "format": "date",
        "min_length": 10,
        "max_length": 10,
        "example": "2024-01-15"
    }

    ENCODING_RULE:
    {
        "encoding": "UTF-8",
        "allowed_characters": "alphanumeric",
        "case_sensitivity": "lower"
    }

    NAMING_CONVENTION:
    {
        "pattern": "^[a-z][a-z0-9_]*$",
        "prefix": "tbl_",
        "max_length": 64
    }

    VALUE_DOMAIN:
    {
        "allowed_values": ["M", "F", "U"],
        "range": {"min": 0, "max": 100},
        "reference_table": "gender_codes"
    }

    DATA_QUALITY:
    {
        "completeness": 0.95,
        "uniqueness": true,
        "not_null": true,
        "precision": 2
    }
    """

    # Applicability
    applicable_domains: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    applicable_data_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Ownership
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    department: Mapped[Optional[str]] = mapped_column(String(255))

    # AI-generated suggestions
    ai_suggested: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column()

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    previous_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    applications: Mapped[list["StandardApplication"]] = relationship(
        back_populates="standard", cascade="all, delete-orphan"
    )
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(
        back_populates="standard", cascade="all, delete-orphan"
    )


class StandardApplication(Base):
    """Records where a data standard is applied.

    Links standards to specific tables, columns, or assets.
    """
    __tablename__ = "standard_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_standards.id", ondelete="CASCADE")
    )

    # Target specification
    target_type: Mapped[str] = mapped_column(String(50))  # table, column, asset
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    table_name: Mapped[Optional[str]] = mapped_column(String(255))
    column_name: Mapped[Optional[str]] = mapped_column(String(255))
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Application status
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    applied_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    standard: Mapped["DataStandard"] = relationship(back_populates="applications")


class ComplianceResult(Base):
    """Compliance check results for a standard against data.

    Records whether data complies with the applied standard.
    """
    __tablename__ = "compliance_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_standards.id", ondelete="CASCADE")
    )
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("standard_applications.id", ondelete="SET NULL")
    )

    # Check scope
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    table_name: Mapped[Optional[str]] = mapped_column(String(255))
    column_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Results
    is_compliant: Mapped[bool] = mapped_column(Boolean)
    compliance_score: Mapped[float] = mapped_column()  # 0.0 to 1.0
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    compliant_records: Mapped[int] = mapped_column(Integer, default=0)
    violation_records: Mapped[int] = mapped_column(Integer, default=0)

    # Violation details
    violations: Mapped[dict[str, Any]] = mapped_column(JSONB, default={})
    """
    {
        "sample_violations": [
            {"value": "invalid_value", "reason": "Pattern mismatch", "row_index": 42}
        ],
        "violation_types": {
            "pattern_mismatch": 15,
            "length_exceeded": 3
        }
    }
    """

    # Check metadata
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    checked_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    check_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    standard: Mapped["DataStandard"] = relationship(back_populates="compliance_results")
