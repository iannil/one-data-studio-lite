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
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccessLevel(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class AssetType(str, enum.Enum):
    TABLE = "table"
    VIEW = "view"
    REPORT = "report"
    DASHBOARD = "dashboard"
    API = "api"
    FILE = "file"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DataAsset(Base, TimestampMixin):
    __tablename__ = "data_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    asset_type: Mapped[AssetType] = mapped_column(SQLEnum(AssetType))

    # Source reference
    source_table: Mapped[Optional[str]] = mapped_column(String(255))
    source_schema: Mapped[Optional[str]] = mapped_column(String(255))
    source_database: Mapped[Optional[str]] = mapped_column(String(255))

    # Ownership & access
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    department: Mapped[Optional[str]] = mapped_column(String(255))
    access_level: Mapped[AccessLevel] = mapped_column(
        SQLEnum(AccessLevel), default=AccessLevel.INTERNAL
    )

    # Classification
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    category: Mapped[Optional[str]] = mapped_column(String(255))
    domain: Mapped[Optional[str]] = mapped_column(String(255))

    # AI-generated
    ai_summary: Mapped[Optional[str]] = mapped_column(Text)
    value_score: Mapped[Optional[float]] = mapped_column(Float)  # AI-evaluated 0-100

    # Lineage
    lineage_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    upstream_assets: Mapped[list[str]] = mapped_column(ARRAY(UUID), default=[])
    downstream_assets: Mapped[list[str]] = mapped_column(ARRAY(UUID), default=[])

    # Usage metrics
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    certified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    certified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    accesses: Mapped[list["AssetAccess"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    api_config: Mapped["AssetApiConfig | None"] = relationship(
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )


class AssetAccess(Base, TimestampMixin):
    __tablename__ = "asset_accesses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_assets.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    access_type: Mapped[str] = mapped_column(String(50))  # read, write, export, api
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    access_details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Relationships
    asset: Mapped["DataAsset"] = relationship(back_populates="accesses")


class AssetApiConfig(Base, TimestampMixin):
    """Configuration for asset API endpoint access."""

    __tablename__ = "asset_api_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_assets.id", ondelete="CASCADE"),
        unique=True,
    )

    # API toggle
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    endpoint_slug: Mapped[Optional[str]] = mapped_column(String(255))

    # Rate limiting
    rate_limit_requests: Mapped[int] = mapped_column(Integer, default=100)
    rate_limit_window_seconds: Mapped[int] = mapped_column(Integer, default=60)

    # Operation permissions
    allow_query: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_export: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_export_formats: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=["csv", "json"]
    )

    # Column control
    exposed_columns: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    hidden_columns: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])

    # Row limits
    default_limit: Mapped[int] = mapped_column(Integer, default=100)
    max_limit: Mapped[int] = mapped_column(Integer, default=10000)

    # Authentication & authorization
    require_auth: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_roles: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))

    # Data desensitization
    enable_desensitization: Mapped[bool] = mapped_column(Boolean, default=True)
    desensitization_rules: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    # Relationships
    asset: Mapped["DataAsset"] = relationship(back_populates="api_config")
