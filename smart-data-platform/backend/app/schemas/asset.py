from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import AccessLevel, AssetType


class DataAssetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    asset_type: AssetType
    source_table: str | None = None
    source_schema: str | None = None
    source_database: str | None = None
    department: str | None = None
    access_level: AccessLevel = AccessLevel.INTERNAL
    tags: list[str] = []
    category: str | None = None
    domain: str | None = None


class DataAssetCreate(DataAssetBase):
    pass


class DataAssetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    department: str | None = None
    access_level: AccessLevel | None = None
    tags: list[str] | None = None
    category: str | None = None
    domain: str | None = None
    is_active: bool | None = None


class DataAssetResponse(DataAssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID | None
    ai_summary: str | None
    value_score: float | None
    usage_count: int
    last_accessed_at: datetime | None
    is_active: bool
    is_certified: bool
    certified_by: UUID | None
    certified_at: datetime | None
    created_at: datetime


class AssetLineageResponse(BaseModel):
    asset_id: UUID
    upstream: list[dict[str, Any]]
    downstream: list[dict[str, Any]]
    lineage_graph: dict[str, Any]


class AssetSearchRequest(BaseModel):
    query: str
    asset_types: list[AssetType] | None = None
    access_levels: list[AccessLevel] | None = None
    tags: list[str] | None = None
    limit: int = 20


class AssetSearchResponse(BaseModel):
    results: list[DataAssetResponse]
    total: int
    ai_summary: str | None = None


class AssetExportRequest(BaseModel):
    format: str = "csv"  # csv, json, parquet
    filters: dict[str, Any] | None = None
    columns: list[str] | None = None
    limit: int | None = None


class AssetExportResponse(BaseModel):
    download_url: str
    format: str
    row_count: int
    file_size_bytes: int


class AssetAutoRegisterRequest(BaseModel):
    """Request for auto-registering an asset from ETL output."""
    table_name: str = Field(..., description="Target table name")
    schema_name: str | None = Field(None, description="Target schema name")
    pipeline_name: str | None = Field(None, description="Source pipeline name")
    source_table: str | None = Field(None, description="Source table for lineage")


class AssetAutoRegisterResponse(BaseModel):
    """Response for auto-register operation."""
    action: str  # "created" or "updated"
    asset_id: str
    asset_name: str
    data_profile: dict[str, Any] | None = None
    ai_summary: str | None = None
    tags: list[str] = []
    value_score: float | None = None
    value_level: str | None = None


class AssetGenerateDescriptionRequest(BaseModel):
    """Request for AI-generated asset description."""
    include_columns: bool = True
    include_quality_metrics: bool = True


class AssetGenerateDescriptionResponse(BaseModel):
    """Response with AI-generated description."""
    asset_id: str
    name: str
    description: str
    summary: str
    suggested_tags: list[str] = []
    suggested_domain: str | None = None
    suggested_category: str | None = None


class AssetValueTrendResponse(BaseModel):
    """Response for value trend analysis."""
    asset_id: str
    current_score: float | None
    current_level: str | None
    trend: list[dict[str, Any]] = []
    change_percentage: float | None = None
    trend_direction: str | None = None  # "up", "down", "stable"


class AssetApiConfigBase(BaseModel):
    """Base schema for asset API configuration."""
    is_enabled: bool = True
    endpoint_slug: str | None = None
    rate_limit_requests: int = Field(default=100, ge=1, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    allow_query: bool = True
    allow_export: bool = True
    allowed_export_formats: list[str] = ["csv", "json"]
    exposed_columns: list[str] | None = None
    hidden_columns: list[str] = []
    default_limit: int = Field(default=100, ge=1, le=10000)
    max_limit: int = Field(default=10000, ge=1, le=100000)
    require_auth: bool = True
    allowed_roles: list[str] | None = None
    enable_desensitization: bool = True
    desensitization_rules: dict[str, Any] | None = None


class AssetApiConfigCreate(AssetApiConfigBase):
    """Schema for creating asset API configuration."""
    asset_id: UUID


class AssetApiConfigUpdate(BaseModel):
    """Schema for updating asset API configuration."""
    is_enabled: bool | None = None
    endpoint_slug: str | None = None
    rate_limit_requests: int | None = Field(default=None, ge=1, le=10000)
    rate_limit_window_seconds: int | None = Field(default=None, ge=1, le=3600)
    allow_query: bool | None = None
    allow_export: bool | None = None
    allowed_export_formats: list[str] | None = None
    exposed_columns: list[str] | None = None
    hidden_columns: list[str] | None = None
    default_limit: int | None = Field(default=None, ge=1, le=10000)
    max_limit: int | None = Field(default=None, ge=1, le=100000)
    require_auth: bool | None = None
    allowed_roles: list[str] | None = None
    enable_desensitization: bool | None = None
    desensitization_rules: dict[str, Any] | None = None


class AssetApiConfigResponse(AssetApiConfigBase):
    """Response schema for asset API configuration."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    created_at: datetime
    updated_at: datetime
    api_endpoint: str | None = None
    api_documentation: dict[str, Any] | None = None


class AssetApiDocsResponse(BaseModel):
    """Response schema for asset API documentation."""
    asset_id: str
    asset_name: str
    api_endpoint: str
    description: str | None = None
    is_enabled: bool
    require_auth: bool
    rate_limit: dict[str, int]
    available_operations: list[str]
    allowed_formats: list[str]
    limits: dict[str, int]
    request_examples: dict[str, Any]
    response_example: dict[str, Any]
