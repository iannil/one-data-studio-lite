"""Pydantic schemas for report builder."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChartOptionsBase(BaseModel):
    """Base configuration for chart rendering."""
    x_field: str | None = None
    y_field: str | None = None
    group_by: str | None = None
    color_field: str | None = None
    sort_field: str | None = None
    sort_order: str | None = Field(default="asc", pattern=r"^(asc|desc)$")
    limit: int | None = Field(default=100, ge=1, le=10000)


class ReportChartBase(BaseModel):
    """Base schema for report charts."""
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    chart_type: str = Field(..., pattern=r"^(bar|line|pie|scatter|area|table|stat|gauge)$")


class ReportChartCreate(ReportChartBase):
    """Schema for creating a report chart."""
    query_type: str = Field(default="nl_query", pattern=r"^(nl_query|sql_query|asset)$")
    nl_query: str | None = None
    sql_query: str | None = None
    asset_id: uuid.UUID | None = None
    chart_options: dict[str, Any] | None = None
    x_field: str | None = None
    y_field: str | None = None
    group_by: str | None = None
    position: int = 0
    grid_x: int = 0
    grid_y: int = 0
    grid_width: int = 6
    grid_height: int = 4


class ReportChartUpdate(BaseModel):
    """Schema for updating a report chart."""
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    chart_type: str | None = Field(None, pattern=r"^(bar|line|pie|scatter|area|table|stat|gauge)$")
    query_type: str | None = Field(None, pattern=r"^(nl_query|sql_query|asset)$")
    nl_query: str | None = None
    sql_query: str | None = None
    asset_id: uuid.UUID | None = None
    chart_options: dict[str, Any] | None = None
    x_field: str | None = None
    y_field: str | None = None
    group_by: str | None = None
    position: int | None = None
    grid_x: int | None = None
    grid_y: int | None = None
    grid_width: int | None = None
    grid_height: int | None = None


class ReportChartResponse(ReportChartBase):
    """Response schema for report charts."""
    id: uuid.UUID
    report_id: uuid.UUID
    query_type: str
    nl_query: str | None
    sql_query: str | None
    asset_id: uuid.UUID | None
    chart_options: dict[str, Any] | None
    x_field: str | None
    y_field: str | None
    group_by: str | None
    position: int
    grid_x: int
    grid_y: int
    grid_width: int
    grid_height: int
    cached_data: dict[str, Any] | None = None
    cache_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    """Base schema for reports."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ReportCreate(ReportBase):
    """Schema for creating a report."""
    department: str | None = None
    is_public: bool = False
    layout_config: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)
    auto_refresh: bool = False
    refresh_interval_seconds: int | None = None
    charts: list[ReportChartCreate] = Field(default_factory=list)


class ReportUpdate(BaseModel):
    """Schema for updating a report."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    department: str | None = None
    status: str | None = Field(None, pattern=r"^(draft|published|archived)$")
    is_public: bool | None = None
    layout_config: dict[str, Any] | None = None
    tags: list[str] | None = None
    auto_refresh: bool | None = None
    refresh_interval_seconds: int | None = None


class ReportResponse(ReportBase):
    """Response schema for reports."""
    id: uuid.UUID
    owner_id: uuid.UUID
    department: str | None
    status: str
    is_public: bool
    layout_config: dict[str, Any] | None
    tags: list[str]
    auto_refresh: bool
    refresh_interval_seconds: int | None
    last_refreshed_at: datetime | None
    charts: list[ReportChartResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Response schema for listing reports."""
    items: list[ReportResponse]
    total: int


class ReportRefreshResponse(BaseModel):
    """Response schema for report refresh."""
    report_id: uuid.UUID
    refreshed_charts: int
    failed_charts: int
    errors: list[dict[str, Any]]
    refreshed_at: datetime
