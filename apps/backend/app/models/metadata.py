from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

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

if TYPE_CHECKING:
    from app.models.collect import CollectTask


class DataSourceType(str, enum.Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    SQLITE = "sqlite"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    API = "api"


class DataSourceStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    type: Mapped[DataSourceType] = mapped_column(SQLEnum(DataSourceType))
    connection_config: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[DataSourceStatus] = mapped_column(
        SQLEnum(DataSourceStatus), default=DataSourceStatus.INACTIVE
    )
    last_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    # Relationships
    tables: Mapped[list["MetadataTable"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    collect_tasks: Mapped[list["CollectTask"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class MetadataTable(Base, TimestampMixin):
    __tablename__ = "metadata_tables"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE")
    )
    schema_name: Mapped[Optional[str]] = mapped_column(String(255))
    table_name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    ai_description: Mapped[Optional[str]] = mapped_column(Text)  # AI-generated
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    row_count: Mapped[Optional[int]] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Relationships
    source: Mapped["DataSource"] = relationship(back_populates="tables")
    columns: Mapped[list["MetadataColumn"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )
    versions: Mapped[list["MetadataVersion"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )


class MetadataColumn(Base, TimestampMixin):
    __tablename__ = "metadata_columns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("metadata_tables.id", ondelete="CASCADE")
    )
    column_name: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str] = mapped_column(String(100))
    nullable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False)
    default_value: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    ai_inferred_meaning: Mapped[Optional[str]] = mapped_column(Text)  # AI-inferred
    ai_data_category: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., PII, Financial
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=[])
    standard_mapping: Mapped[Optional[str]] = mapped_column(String(255))  # Standard field mapping
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    table: Mapped["MetadataTable"] = relationship(back_populates="columns")


class MetadataVersion(Base, TimestampMixin):
    __tablename__ = "metadata_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("metadata_tables.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    change_description: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    table: Mapped["MetadataTable"] = relationship(back_populates="versions")
