# Quality API endpoints

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Query
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


@router.post("/assessment", response_model=QualityScoreResponse)
async def run_quality_assessment(
    request: QualityScoreRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> QualityScoreResponse:
    """Run quality assessment for a table (alias for /score endpoint)."""
    quality_service = DataQualityService(db)
    result = await quality_service.calculate_quality_score(
        request.source_id,
        request.table_name,
    )
    return QualityScoreResponse(**result)


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


# GET versions for frontend compatibility


@router.get("/issues", response_model=QualityIssuesResponse)
async def get_quality_issues_get(
    source_id: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> QualityIssuesResponse:
    """Get quality issues for a table (GET version for frontend compatibility)."""
    if not source_id or not table_name:
        return QualityIssuesResponse(
            issues={"critical": [], "warning": [], "info": []},
            total_issues=0,
            critical_count=0,
            warning_count=0,
            info_count=0,
        )

    quality_service = DataQualityService(db)
    result = await quality_service.detect_quality_issues(
        uuid.UUID(source_id),
        table_name,
    )
    return QualityIssuesResponse(**result)


@router.get("/trend/{asset_id}", response_model=QualityTrendResponse)
async def get_quality_trend_get(
    asset_id: str,
    days: int = Query(30),
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> QualityTrendResponse:
    """Get quality trend for an asset (GET version for frontend compatibility)."""
    quality_service = DataQualityService(db)

    # Parse asset_id - it might be "source_id:table_name" format or a real asset UUID
    if ":" in asset_id:
        source_id, table_name = asset_id.split(":", 1)
        mapped_asset_id = await _find_asset_by_source(db, source_id, table_name)
    else:
        try:
            mapped_asset_id = uuid.UUID(asset_id)
        except ValueError:
            mapped_asset_id = None

    result = await quality_service.track_quality_trend(
        asset_id=mapped_asset_id,
        days=days,
    )
    return QualityTrendResponse(**result)


@router.get("/report/{asset_id}", response_model=QualityReportResponse)
async def get_quality_report_get(
    asset_id: str,
    db: DBSession = None,
    current_user: CurrentUser = None,
) -> QualityReportResponse:
    """Get quality report for an asset (GET version for frontend compatibility)."""
    # Parse asset_id - it might be "source_id:table_name" format or a real asset UUID
    source_id: Optional[uuid.UUID] = None
    table_name: str = ""

    if ":" in asset_id:
        source_id_str, table_name = asset_id.split(":", 1)
        try:
            source_id = uuid.UUID(source_id_str)
        except ValueError:
            pass
        mapped_asset_id = await _find_asset_by_source(db, source_id_str, table_name) if source_id else None
    else:
        try:
            mapped_asset_id = uuid.UUID(asset_id)
        except ValueError:
            mapped_asset_id = None

    if not source_id or not table_name:
        # Return empty report if we can't parse the asset_id
        return QualityReportResponse(
            table_name=table_name or "unknown",
            generated_at="",
            summary={
                "overall_score": 0,
                "completeness_score": 0,
                "uniqueness_score": 0,
                "validity_score": 0,
                "consistency_score": 0,
                "timeliness_score": 0,
                "row_count": 0,
                "column_count": 0,
                "assessment": "Unknown",
                "total_issues": 0,
                "critical_issues": 0,
                "warning_issues": 0,
            },
            issues={"critical": [], "warning": [], "info": []},
            trend={
                "asset_id": asset_id,
                "period_days": 30,
                "trend": [],
                "average_score": 0,
                "trend_direction": "unknown",
            },
            recommendations=[],
        )

    quality_service = DataQualityService(db)
    result = await quality_service.generate_quality_report(
        source_id,
        table_name,
        asset_id=mapped_asset_id,
        save_assessment=False,  # Don't save on GET requests
    )
    return QualityReportResponse(**result)
