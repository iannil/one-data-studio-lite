# Quality API endpoints

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.models import DataAsset
from app.schemas import (
    QualityScoreRequest,
    QualityScoreResponse,
    QualityIssuesResponse,
    QualityReportRequest,
    QualityReportResponse,
    QualityTrendRequest,
    QualityTrendResponse,
)
from app.services import DataQualityService

router = APIRouter(prefix="/quality", tags=["Quality"])


@router.post("/score", response_model=QualityScoreResponse)
async def calculate_quality_score(
    request: QualityScoreRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityScoreResponse:
    """Calculate quality score for a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.calculate_quality_score(
        request.source_id,
        request.table_name,
    )
    return QualityScoreResponse(**result)


@router.post("/issues", response_model=QualityIssuesResponse)
async def detect_quality_issues(
    request: QualityScoreRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityIssuesResponse:
    """Detect data quality issues in a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.detect_quality_issues(
        request.source_id,
        request.table_name,
    )
    return QualityIssuesResponse(**result)


@router.post("/report", response_model=QualityReportResponse)
async def generate_quality_report(
    request: QualityReportRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityReportResponse:
    """Generate comprehensive quality report for a table."""
    quality_service = DataQualityService(db)
    result = await quality_service.generate_quality_report(
        request.source_id,
        request.table_name,
    )
    return QualityReportResponse(**result)


@router.post("/trend", response_model=QualityTrendResponse)
async def get_quality_trend(
    request: QualityTrendRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityTrendResponse:
    """Get quality trend over time."""
    quality_service = DataQualityService(db)

    # Map source_id + table_name to asset_id for historical data
    asset_id = await _find_asset_by_source(db, request.source_id, request.table_name)

    result = await quality_service.track_quality_trend(
        asset_id=asset_id,
        days=request.days,
    )
    return QualityTrendResponse(**result)


async def _find_asset_by_source(
    db: DBSession,
    source_id: str,
    table_name: str,
) -> Optional[uuid.UUID]:
    """Find an asset by source reference.

    Attempts to match a DataAsset by source_table and optionally source_schema.
    This enables quality trend tracking for assets that have been cataloged.

    Args:
        db: Database session.
        source_id: Data source ID (can be used for additional filtering).
        table_name: Table name to search for in source_table field.

    Returns:
        Asset ID if found, None otherwise.
    """
    # Parse table_name to extract schema if provided (format: "schema.table")
    schema_name = None
    if "." in table_name:
        parts = table_name.split(".", 1)
        schema_name = parts[0]
        table_name = parts[1]

    # Build query - match by source_table first
    query = select(DataAsset).where(
        DataAsset.is_active.is_(True),
        DataAsset.source_table == table_name,
    )

    # If schema was provided, also match by source_schema
    if schema_name:
        query = query.where(DataAsset.source_schema == schema_name)

    result = await db.execute(query.limit(1))
    asset = result.scalar_one_or_none()

    return asset.id if asset else None
