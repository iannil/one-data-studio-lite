"""API endpoints for data standard management."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.connectors import get_connector
from app.models import DataSource
from app.models.standard import DataStandard, StandardStatus, StandardType
from app.schemas.standard import (
    ApplyStandardRequest,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceHistoryResponse,
    CreateVersionRequest,
    StandardApplicationResponse,
    StandardCreate,
    StandardListResponse,
    StandardResponse,
    StandardSuggestionRequest,
    StandardSuggestionResponse,
    StandardUpdate,
)
from app.services.standard_service import StandardService

router = APIRouter(prefix="/standards", tags=["data-standards"])


@router.get("", response_model=StandardListResponse)
async def list_standards(
    db: DBSession,
    current_user: CurrentUser,
    standard_type: str | None = None,
    status: str | None = None,
) -> StandardListResponse:
    """List all data standards with optional filtering."""
    service = StandardService(db)

    type_filter = None
    if standard_type:
        try:
            type_filter = StandardType(standard_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid standard type: {standard_type}",
            )

    status_filter = None
    if status:
        try:
            status_filter = StandardStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}",
            )

    standards = await service.get_standards_by_type(
        standard_type=type_filter,
        status=status_filter,
    )

    return StandardListResponse(
        items=[StandardResponse.model_validate(s) for s in standards],
        total=len(standards),
    )


@router.post("", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
async def create_standard(
    data: StandardCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Create a new data standard."""
    existing = await db.execute(
        select(DataStandard).where(DataStandard.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Standard with code '{data.code}' already exists",
        )

    standard = DataStandard(
        name=data.name,
        code=data.code,
        description=data.description,
        standard_type=StandardType(data.standard_type),
        rules=data.rules,
        applicable_domains=data.applicable_domains,
        applicable_data_types=data.applicable_data_types,
        tags=data.tags,
        department=data.department,
        owner_id=current_user.id,
    )

    db.add(standard)
    await db.commit()
    await db.refresh(standard)

    return StandardResponse.model_validate(standard)


@router.get("/{standard_id}", response_model=StandardResponse)
async def get_standard(
    standard_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Get a specific data standard by ID."""
    result = await db.execute(
        select(DataStandard).where(DataStandard.id == standard_id)
    )
    standard = result.scalar_one_or_none()

    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Standard not found: {standard_id}",
        )

    return StandardResponse.model_validate(standard)


@router.patch("/{standard_id}", response_model=StandardResponse)
async def update_standard(
    standard_id: uuid.UUID,
    data: StandardUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Update a data standard."""
    result = await db.execute(
        select(DataStandard).where(DataStandard.id == standard_id)
    )
    standard = result.scalar_one_or_none()

    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Standard not found: {standard_id}",
        )

    if standard.status == StandardStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify an approved standard. Create a new version instead.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(standard, field, value)

    await db.commit()
    await db.refresh(standard)

    return StandardResponse.model_validate(standard)


@router.delete("/{standard_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_standard(
    standard_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete a data standard (only draft standards can be deleted)."""
    result = await db.execute(
        select(DataStandard).where(DataStandard.id == standard_id)
    )
    standard = result.scalar_one_or_none()

    if not standard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Standard not found: {standard_id}",
        )

    if standard.status != StandardStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft standards can be deleted",
        )

    await db.delete(standard)
    await db.commit()


@router.post("/suggest", response_model=StandardSuggestionResponse)
async def suggest_standards(
    data: StandardSuggestionRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardSuggestionResponse:
    """Use AI to suggest data standards for a table."""
    source_result = await db.execute(
        select(DataSource).where(DataSource.id == data.source_id)
    )
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {data.source_id}",
        )

    connector = get_connector(source.type, source.connection_config)

    # Try to read sample data from the table
    try:
        sample_data = await connector.read_data(table_name=data.table_name, limit=1000)
    except RuntimeError as e:
        # Check if it's a table not found error
        error_msg = str(e)
        if "does not exist" in error_msg or "UndefinedTable" in error_msg or "relation" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{data.table_name}' does not exist in data source '{source.name}'. "
                      f"Please scan the data source to update metadata or verify the table name.",
            )
        # Re-raise other runtime errors with a cleaner message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read data from table: {error_msg}",
        ) from e

    service = StandardService(db)
    result = await service.suggest_standards(
        source_id=data.source_id,
        table_name=data.table_name,
        sample_data=sample_data,
    )

    return StandardSuggestionResponse(**result)


@router.post("/suggest/create", response_model=StandardResponse)
async def create_from_suggestion(
    suggestion: dict[str, Any],
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Create a data standard from an AI suggestion."""
    service = StandardService(db)
    standard = await service.create_standard_from_suggestion(
        suggestion=suggestion,
        owner_id=current_user.id,
    )

    return StandardResponse.model_validate(standard)


@router.post("/{standard_id}/approve", response_model=StandardResponse)
async def approve_standard(
    standard_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Approve a data standard."""
    service = StandardService(db)

    try:
        standard = await service.approve_standard(
            standard_id=standard_id,
            approved_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return StandardResponse.model_validate(standard)


@router.post("/{standard_id}/version", response_model=StandardResponse)
async def create_new_version(
    standard_id: uuid.UUID,
    data: CreateVersionRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardResponse:
    """Create a new version of a data standard."""
    service = StandardService(db)

    try:
        standard = await service.create_new_version(
            standard_id=standard_id,
            updated_rules=data.updated_rules,
            owner_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return StandardResponse.model_validate(standard)


@router.post("/apply", response_model=StandardApplicationResponse)
async def apply_standard(
    data: ApplyStandardRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> StandardApplicationResponse:
    """Apply a standard to a target (table, column, or asset)."""
    service = StandardService(db)

    try:
        application = await service.apply_standard(
            standard_id=data.standard_id,
            target_type=data.target_type,
            table_name=data.table_name,
            column_name=data.column_name,
            source_id=data.source_id,
            asset_id=data.asset_id,
            is_mandatory=data.is_mandatory,
            applied_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return StandardApplicationResponse.model_validate(application)


@router.post("/compliance/check", response_model=ComplianceCheckResponse)
async def check_compliance(
    data: ComplianceCheckRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ComplianceCheckResponse:
    """Check data compliance against a standard."""
    if not data.source_id or not data.table_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_id and table_name are required for compliance check",
        )

    source_result = await db.execute(
        select(DataSource).where(DataSource.id == data.source_id)
    )
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Data source not found: {data.source_id}",
        )

    connector = get_connector(source.type, source.connection_config)

    # Try to read sample data from the table
    try:
        sample_data = await connector.read_data(table_name=data.table_name, limit=10000)
    except RuntimeError as e:
        # Check if it's a table not found error
        error_msg = str(e)
        if "does not exist" in error_msg or "UndefinedTable" in error_msg or "relation" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table '{data.table_name}' does not exist in data source '{source.name}'. "
                      f"Please scan the data source to update metadata or verify the table name.",
            )
        # Re-raise other runtime errors with a cleaner message
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read data from table: {error_msg}",
        ) from e

    service = StandardService(db)

    try:
        result = await service.check_compliance(
            standard_id=data.standard_id,
            data=sample_data,
            column_name=data.column_name,
            source_id=data.source_id,
            table_name=data.table_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return ComplianceCheckResponse.model_validate(result)


@router.get("/compliance/history", response_model=ComplianceHistoryResponse)
async def get_compliance_history(
    db: DBSession,
    current_user: CurrentUser,
    standard_id: uuid.UUID | None = None,
    table_name: str | None = None,
    column_name: str | None = None,
    limit: int = 100,
) -> ComplianceHistoryResponse:
    """Get compliance check history."""
    service = StandardService(db)

    results = await service.get_compliance_history(
        standard_id=standard_id,
        table_name=table_name,
        column_name=column_name,
        limit=limit,
    )

    return ComplianceHistoryResponse(
        items=[ComplianceCheckResponse.model_validate(r) for r in results],
        total=len(results),
    )
