"""Report builder API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models import User
from app.models.report import Report, ReportChart, ReportStatus, ChartType
from app.schemas.report import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportListResponse,
    ReportChartCreate,
    ReportChartUpdate,
    ReportChartResponse,
    ReportRefreshResponse,
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List reports",
)
async def list_reports(
    status: str | None = None,
    is_public: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """List all reports accessible to the current user.

    Args:
        status: Filter by report status
        is_public: Filter by public/private
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of reports
    """
    query = select(Report).options(selectinload(Report.charts))

    if status:
        query = query.where(Report.status == ReportStatus(status))

    if is_public is not None:
        if is_public:
            query = query.where(Report.is_public.is_(True))
        else:
            query = query.where(
                (Report.owner_id == current_user.id) | (Report.is_public.is_(True))
            )
    else:
        query = query.where(
            (Report.owner_id == current_user.id) | (Report.is_public.is_(True))
        )

    query = query.order_by(Report.updated_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    reports = list(result.scalars().unique())

    return {
        "items": reports,
        "total": len(reports),
    }


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report by ID",
)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Get a report by ID.

    Args:
        report_id: The report ID

    Returns:
        The report with all charts
    """
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.charts))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if not report.is_public and report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this report",
        )

    return report


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
)
async def create_report(
    request: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Create a new report.

    Args:
        request: Report creation data

    Returns:
        The created report
    """
    report = Report(
        name=request.name,
        description=request.description,
        owner_id=current_user.id,
        department=request.department,
        status=ReportStatus.DRAFT,
        is_public=request.is_public,
        layout_config=request.layout_config,
        tags=request.tags,
        auto_refresh=request.auto_refresh,
        refresh_interval_seconds=request.refresh_interval_seconds,
    )

    db.add(report)
    await db.flush()

    for i, chart_data in enumerate(request.charts):
        chart = ReportChart(
            report_id=report.id,
            title=chart_data.title,
            description=chart_data.description,
            chart_type=ChartType(chart_data.chart_type),
            query_type=chart_data.query_type,
            nl_query=chart_data.nl_query,
            sql_query=chart_data.sql_query,
            asset_id=chart_data.asset_id,
            chart_options=chart_data.chart_options,
            x_field=chart_data.x_field,
            y_field=chart_data.y_field,
            group_by=chart_data.group_by,
            position=chart_data.position or i,
            grid_x=chart_data.grid_x,
            grid_y=chart_data.grid_y,
            grid_width=chart_data.grid_width,
            grid_height=chart_data.grid_height,
        )
        db.add(chart)

    await db.commit()
    await db.refresh(report)

    result = await db.execute(
        select(Report)
        .options(selectinload(Report.charts))
        .where(Report.id == report.id)
    )
    return result.scalar_one()


@router.patch(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Update report",
)
async def update_report(
    report_id: uuid.UUID,
    request: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Update a report.

    Args:
        report_id: The report ID
        request: Update data

    Returns:
        The updated report
    """
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.charts))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own reports",
        )

    update_data = request.model_dump(exclude_unset=True)

    if "status" in update_data:
        update_data["status"] = ReportStatus(update_data["status"])

    for field, value in update_data.items():
        setattr(report, field, value)

    await db.commit()
    await db.refresh(report)

    return report


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete report",
)
async def delete_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a report.

    Args:
        report_id: The report ID
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own reports",
        )

    await db.delete(report)
    await db.commit()


@router.post(
    "/{report_id}/charts",
    response_model=ReportChartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add chart to report",
)
async def add_chart(
    report_id: uuid.UUID,
    request: ReportChartCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportChart:
    """Add a chart to a report.

    Args:
        report_id: The report ID
        request: Chart creation data

    Returns:
        The created chart
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own reports",
        )

    chart = ReportChart(
        report_id=report_id,
        title=request.title,
        description=request.description,
        chart_type=ChartType(request.chart_type),
        query_type=request.query_type,
        nl_query=request.nl_query,
        sql_query=request.sql_query,
        asset_id=request.asset_id,
        chart_options=request.chart_options,
        x_field=request.x_field,
        y_field=request.y_field,
        group_by=request.group_by,
        position=request.position,
        grid_x=request.grid_x,
        grid_y=request.grid_y,
        grid_width=request.grid_width,
        grid_height=request.grid_height,
    )

    db.add(chart)
    await db.commit()
    await db.refresh(chart)

    return chart


@router.patch(
    "/{report_id}/charts/{chart_id}",
    response_model=ReportChartResponse,
    summary="Update chart",
)
async def update_chart(
    report_id: uuid.UUID,
    chart_id: uuid.UUID,
    request: ReportChartUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportChart:
    """Update a chart in a report.

    Args:
        report_id: The report ID
        chart_id: The chart ID
        request: Update data

    Returns:
        The updated chart
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own reports",
        )

    chart_result = await db.execute(
        select(ReportChart).where(
            ReportChart.id == chart_id,
            ReportChart.report_id == report_id,
        )
    )
    chart = chart_result.scalar_one_or_none()

    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found",
        )

    update_data = request.model_dump(exclude_unset=True)

    if "chart_type" in update_data:
        update_data["chart_type"] = ChartType(update_data["chart_type"])

    for field, value in update_data.items():
        setattr(chart, field, value)

    await db.commit()
    await db.refresh(chart)

    return chart


@router.delete(
    "/{report_id}/charts/{chart_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete chart",
)
async def delete_chart(
    report_id: uuid.UUID,
    chart_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chart from a report.

    Args:
        report_id: The report ID
        chart_id: The chart ID
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own reports",
        )

    chart_result = await db.execute(
        select(ReportChart).where(
            ReportChart.id == chart_id,
            ReportChart.report_id == report_id,
        )
    )
    chart = chart_result.scalar_one_or_none()

    if not chart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chart not found",
        )

    await db.delete(chart)
    await db.commit()


@router.post(
    "/{report_id}/refresh",
    response_model=ReportRefreshResponse,
    summary="Refresh report data",
)
async def refresh_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Refresh all charts in a report.

    Re-executes all NL queries and SQL queries to fetch fresh data.

    Args:
        report_id: The report ID

    Returns:
        Refresh summary
    """
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.charts))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if not report.is_public and report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this report",
        )

    refreshed = 0
    failed = 0
    errors = []

    ai_service = AIService(db)

    for chart in report.charts:
        try:
            if chart.query_type == "nl_query" and chart.nl_query:
                result_data = await ai_service.natural_language_to_sql(chart.nl_query)
                chart.cached_data = {
                    "sql": result_data.get("sql"),
                    "data": result_data.get("data"),
                    "columns": result_data.get("columns"),
                    "row_count": result_data.get("row_count"),
                }
                chart.cache_expires_at = datetime.now(timezone.utc)
                refreshed += 1
        except Exception as e:
            failed += 1
            errors.append({
                "chart_id": str(chart.id),
                "chart_title": chart.title,
                "error": str(e),
            })

    report.last_refreshed_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "report_id": report_id,
        "refreshed_charts": refreshed,
        "failed_charts": failed,
        "errors": errors,
        "refreshed_at": datetime.now(timezone.utc),
    }


@router.post(
    "/{report_id}/publish",
    response_model=ReportResponse,
    summary="Publish report",
)
async def publish_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Report:
    """Publish a report (change status to published).

    Args:
        report_id: The report ID

    Returns:
        The published report
    """
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.charts))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    if report.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only publish your own reports",
        )

    report.status = ReportStatus.PUBLISHED
    await db.commit()
    await db.refresh(report)

    return report
