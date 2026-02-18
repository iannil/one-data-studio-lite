from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DBSession
from app.schemas.bi import (
    BISyncRequest,
    BISyncResponse,
    BIDatasetResponse,
    BIStatusResponse,
    BISyncStatusResponse,
    BatchSyncRequest,
    BatchSyncResponse,
    AssetSyncResponse,
)
from app.services import BIService, SupersetAPIError

router = APIRouter(prefix="/bi", tags=["BI"])


@router.get("/status", response_model=BIStatusResponse)
async def get_superset_status(
    db: DBSession,
    current_user: CurrentUser,
) -> BIStatusResponse:
    """Get Superset connection status."""
    bi_service = BIService(db)
    result = await bi_service.get_superset_status()
    return BIStatusResponse(**result)


@router.get("/datasets", response_model=list[BIDatasetResponse])
async def list_datasets(
    db: DBSession,
    current_user: CurrentUser,
) -> list[BIDatasetResponse]:
    """List all datasets synced to Superset."""
    bi_service = BIService(db)

    try:
        datasets = await bi_service.list_synced_datasets()
        return [BIDatasetResponse(**ds) for ds in datasets]
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e


@router.post("/sync/{table_name}", response_model=BISyncResponse)
async def sync_table(
    table_name: str,
    request: BISyncRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> BISyncResponse:
    """Sync a table to Superset as a dataset."""
    bi_service = BIService(db)

    try:
        result = await bi_service.sync_table_to_superset(
            table_name=table_name,
            schema=request.schema_name,
        )
        return BISyncResponse(**result)
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e


@router.get("/sync/{table_name}", response_model=BISyncStatusResponse)
async def get_sync_status(
    table_name: str,
    db: DBSession,
    current_user: CurrentUser,
    schema_name: str = "public",
) -> BISyncStatusResponse:
    """Get sync status for a specific table."""
    bi_service = BIService(db)

    try:
        result = await bi_service.get_sync_status(
            table_name=table_name,
            schema=schema_name,
        )
        return BISyncStatusResponse(**result)
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e


@router.delete("/sync/{table_name}")
async def unsync_table(
    table_name: str,
    db: DBSession,
    current_user: CurrentUser,
    schema_name: str = "public",
) -> dict[str, bool]:
    """Remove a table's dataset from Superset."""
    bi_service = BIService(db)

    try:
        success = await bi_service.delete_dataset(
            table_name=table_name,
            schema=schema_name,
        )
        return {"success": success}
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e


@router.post("/sync-batch", response_model=BatchSyncResponse)
async def batch_sync_tables(
    request: BatchSyncRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> BatchSyncResponse:
    """Batch sync multiple tables to Superset."""
    bi_service = BIService(db)

    try:
        result = await bi_service.batch_sync_tables(
            tables=request.tables,
            schema=request.schema_name,
        )
        return BatchSyncResponse(**result)
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e


@router.post("/sync-asset/{asset_id}", response_model=AssetSyncResponse)
async def sync_asset_to_bi(
    asset_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetSyncResponse:
    """Sync a DataAsset to Superset."""
    bi_service = BIService(db)

    try:
        result = await bi_service.sync_asset_to_superset(asset_id=str(asset_id))
        return AssetSyncResponse(**result)
    except SupersetAPIError as e:
        raise HTTPException(status_code=502, detail=f"Superset error: {e.message}") from e
