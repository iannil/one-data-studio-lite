from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.metadata import DataSourceStatus, DataSourceType


class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: DataSourceType
    connection_config: dict[str, Any]


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    connection_config: dict[str, Any] | None = None
    status: DataSourceStatus | None = None


class DataSourceResponse(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DataSourceStatus
    last_connected_at: datetime | None
    created_at: datetime
    created_by: UUID | None


class DataSourceTest(BaseModel):
    success: bool
    message: str
    details: dict[str, Any] | None = None


# Metadata Column
class MetadataColumnBase(BaseModel):
    column_name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    default_value: str | None = None
    description: str | None = None


class MetadataColumnResponse(MetadataColumnBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    table_id: UUID
    ai_inferred_meaning: str | None
    ai_data_category: str | None
    tags: list[str]
    standard_mapping: str | None
    ordinal_position: int


# Metadata Table
class MetadataTableBase(BaseModel):
    schema_name: str | None = None
    table_name: str
    description: str | None = None


class MetadataTableResponse(MetadataTableBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    ai_description: str | None
    tags: list[str]
    row_count: int | None
    version: int
    created_at: datetime
    columns: list[MetadataColumnResponse] = []


class MetadataScanRequest(BaseModel):
    include_row_count: bool = False
    table_filter: str | None = None  # Regex pattern


class MetadataScanResponse(BaseModel):
    source_id: UUID
    tables_scanned: int
    columns_scanned: int
    duration_ms: int


class BatchTagsRequest(BaseModel):
    """Request for batch tag operations on tables or columns."""
    table_ids: list[UUID] = Field(default_factory=list)
    column_ids: list[UUID] = Field(default_factory=list)
    tags_to_add: list[str] = Field(default_factory=list)
    tags_to_remove: list[str] = Field(default_factory=list)


class BatchTagsResponse(BaseModel):
    """Response for batch tag operations."""
    tables_updated: int
    columns_updated: int
    tags_added: list[str]
    tags_removed: list[str]
