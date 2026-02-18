"""API endpoints for data service - standardized asset data access."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DBSession
from app.services.data_service import DataService, RateLimitExceeded

router = APIRouter(prefix="/data-service", tags=["data-service"])


class QueryFilter(BaseModel):
    """Filter condition for data queries."""
    column: str
    operator: str = Field(default="eq", pattern=r"^(eq|ne|gt|gte|lt|lte|in|contains)$")
    value: Any


class QueryParams(BaseModel):
    """Query parameters for data queries."""
    filters: list[QueryFilter] = Field(default_factory=list)
    sort_by: str | None = None
    sort_order: str = Field(default="asc", pattern=r"^(asc|desc)$")
    columns: list[str] | None = None


class DataQueryRequest(BaseModel):
    """Request schema for data queries."""
    asset_id: uuid.UUID
    query_params: QueryParams | None = None
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)


class DataQueryResponse(BaseModel):
    """Response schema for data queries."""
    asset_id: str
    asset_name: str
    data: list[dict[str, Any]]
    row_count: int
    columns: list[str]
    total_rows: int | None
    limit: int
    offset: int


class DataExportRequest(BaseModel):
    """Request schema for data export."""
    asset_id: uuid.UUID
    format: str = Field(default="csv", pattern=r"^(csv|json|parquet|excel)$")
    query_params: QueryParams | None = None
    limit: int | None = Field(default=None, ge=1)


class AccessStatisticsResponse(BaseModel):
    """Response schema for access statistics."""
    period_days: int
    total_accesses: int
    unique_users: int
    unique_assets: int
    access_by_type: dict[str, int]
    daily_trend: list[dict[str, Any]]
    avg_daily_accesses: float


class TopAssetResponse(BaseModel):
    """Response schema for top accessed asset."""
    asset_id: str
    name: str
    domain: str | None
    category: str | None
    access_count: int


@router.post("/query", response_model=DataQueryResponse)
async def query_data(
    request: DataQueryRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> DataQueryResponse:
    """Query data from a data asset.

    Supports filtering, sorting, and pagination.
    Automatically masks sensitive data (email, phone, ID card, etc.).
    """
    service = DataService(db)

    query_params_dict = None
    if request.query_params:
        query_params_dict = {
            "filters": [f.model_dump() for f in request.query_params.filters],
            "sort_by": request.query_params.sort_by,
            "sort_order": request.query_params.sort_order,
            "columns": request.query_params.columns,
        }

    try:
        result = await service.query_asset_data(
            asset_id=request.asset_id,
            user_id=current_user.id,
            query_params=query_params_dict,
            limit=request.limit,
            offset=request.offset,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DataQueryResponse(**result)


@router.get("/query/{asset_id}", response_model=DataQueryResponse)
async def query_data_simple(
    asset_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    sort_by: str | None = None,
    sort_order: str = Query(default="asc", pattern=r"^(asc|desc)$"),
) -> DataQueryResponse:
    """Simple data query endpoint for GET requests.

    Use POST /query for advanced filtering.
    Automatically masks sensitive data (email, phone, ID card, etc.).
    """
    service = DataService(db)

    query_params_dict = None
    if sort_by:
        query_params_dict = {
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

    try:
        result = await service.query_asset_data(
            asset_id=asset_id,
            user_id=current_user.id,
            query_params=query_params_dict,
            limit=limit,
            offset=offset,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return DataQueryResponse(**result)


@router.post("/export")
async def export_data(
    request: DataExportRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Export data from a data asset.

    Supports CSV, JSON, Parquet, and Excel formats.
    Automatically masks sensitive data before export.
    """
    service = DataService(db)

    query_params_dict = None
    if request.query_params:
        query_params_dict = {
            "filters": [f.model_dump() for f in request.query_params.filters],
            "sort_by": request.query_params.sort_by,
            "sort_order": request.query_params.sort_order,
            "columns": request.query_params.columns,
        }

    try:
        result = await service.export_asset_data(
            asset_id=request.asset_id,
            user_id=current_user.id,
            format=request.format,
            query_params=query_params_dict,
            limit=request.limit,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    content = result["content"]
    if isinstance(content, str):
        content = content.encode("utf-8")

    return StreamingResponse(
        iter([content]),
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "X-Row-Count": str(result["row_count"]),
        },
    )


@router.get("/export/{asset_id}")
async def export_data_simple(
    asset_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
    format: str = Query(default="csv", pattern=r"^(csv|json|parquet|excel)$"),
    limit: int | None = Query(default=None, ge=1),
) -> StreamingResponse:
    """Simple data export endpoint for GET requests.

    Use POST /export for advanced filtering.
    Automatically masks sensitive data before export.
    """
    service = DataService(db)

    try:
        result = await service.export_asset_data(
            asset_id=asset_id,
            user_id=current_user.id,
            format=format,
            limit=limit,
        )
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    content = result["content"]
    if isinstance(content, str):
        content = content.encode("utf-8")

    return StreamingResponse(
        iter([content]),
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            "X-Row-Count": str(result["row_count"]),
        },
    )


@router.get("/statistics", response_model=AccessStatisticsResponse)
async def get_access_statistics(
    db: DBSession,
    current_user: CurrentUser,
    asset_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    days: int = Query(default=30, ge=1, le=365),
) -> AccessStatisticsResponse:
    """Get access statistics for assets or users."""
    service = DataService(db)

    result = await service.get_access_statistics(
        asset_id=asset_id,
        user_id=user_id,
        days=days,
    )

    return AccessStatisticsResponse(**result)


@router.get("/top-assets", response_model=list[TopAssetResponse])
async def get_top_assets(
    db: DBSession,
    current_user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
) -> list[TopAssetResponse]:
    """Get top accessed assets."""
    service = DataService(db)

    result = await service.get_top_accessed_assets(
        limit=limit,
        days=days,
    )

    return [TopAssetResponse(**r) for r in result]
