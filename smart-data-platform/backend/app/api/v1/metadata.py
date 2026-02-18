from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.connectors import get_connector
from app.models import DataSource, DataSourceStatus, MetadataTable
from app.schemas import (
    DataSourceCreate,
    DataSourceResponse,
    DataSourceTest,
    DataSourceUpdate,
    MetadataScanRequest,
    MetadataScanResponse,
    MetadataTableResponse,
)
from app.services import MetadataEngine

router = APIRouter(prefix="/sources", tags=["Data Sources"])


@router.post("", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    request: DataSourceCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> DataSource:
    """Create a new data source."""
    source = DataSource(
        name=request.name,
        description=request.description,
        type=request.type,
        connection_config=request.connection_config,
        status=DataSourceStatus.INACTIVE,
        created_by=current_user.id,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)

    return source


@router.get("", response_model=list[DataSourceResponse])
async def list_sources(
    db: DBSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[DataSource]:
    """List all data sources."""
    result = await db.execute(select(DataSource).offset(skip).limit(limit))
    return list(result.scalars())


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_source(
    source_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> DataSource:
    """Get a specific data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    return source


@router.patch("/{source_id}", response_model=DataSourceResponse)
async def update_source(
    source_id: UUID,
    request: DataSourceUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> DataSource:
    """Update a data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)

    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_source(
    source_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/test", response_model=DataSourceTest)
async def test_source(
    source_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> DataSourceTest:
    """Test connection to a data source."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    try:
        connector = get_connector(source.type, source.connection_config)
        success, message = await connector.test_connection()

        if success:
            source.status = DataSourceStatus.ACTIVE
            source.last_connected_at = datetime.now(timezone.utc)
        else:
            source.status = DataSourceStatus.ERROR

        await db.commit()

        return DataSourceTest(success=success, message=message)
    except Exception as e:
        source.status = DataSourceStatus.ERROR
        await db.commit()
        return DataSourceTest(success=False, message=str(e))


@router.post("/{source_id}/scan", response_model=MetadataScanResponse)
async def scan_source(
    source_id: UUID,
    request: MetadataScanRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> MetadataScanResponse:
    """Scan data source and extract metadata."""
    result = await db.execute(select(DataSource).where(DataSource.id == source_id))
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="Data source not found")

    engine = MetadataEngine(db)
    scan_result = await engine.scan_source(
        source,
        include_row_count=request.include_row_count,
        table_filter=request.table_filter,
    )

    return MetadataScanResponse(**scan_result)


# Metadata endpoints
metadata_router = APIRouter(prefix="/metadata", tags=["Metadata"])


@metadata_router.get("/tables", response_model=list[MetadataTableResponse])
async def list_tables(
    db: DBSession,
    current_user: CurrentUser,
    source_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[MetadataTable]:
    """List metadata tables."""
    query = select(MetadataTable).options(selectinload(MetadataTable.columns))

    if source_id:
        query = query.where(MetadataTable.source_id == source_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars())


@metadata_router.get("/tables/{table_id}", response_model=MetadataTableResponse)
async def get_table(
    table_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> MetadataTable:
    """Get metadata for a specific table."""
    result = await db.execute(
        select(MetadataTable)
        .options(selectinload(MetadataTable.columns))
        .where(MetadataTable.id == table_id)
    )
    table = result.scalar_one_or_none()

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return table


@metadata_router.post("/ai-analyze")
async def ai_analyze_metadata(
    source_id: UUID,
    table_name: str,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Use AI to analyze and enrich metadata."""
    from app.services import AIService

    ai_service = AIService(db)
    return await ai_service.analyze_field_meanings(source_id, table_name)
