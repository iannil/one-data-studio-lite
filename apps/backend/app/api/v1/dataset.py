"""
Dataset API Endpoints

REST API for managing ML datasets.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user,
    get_db,
)
from app.models.user import User
from app.models.dataset import Dataset, DatasetTag, DatasetAccessLog
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetListResponse,
    DatasetTagCreate,
    DatasetTagResponse,
    DatasetActionRequest,
    DatasetSplitConfig,
    DatasetComputeStatsRequest,
    DatasetPreviewResponse,
    DatasetStatisticsResponse,
    DatasetImportRequest,
    DatasetImportResponse,
    DatasetExportRequest,
    DatasetExportResponse,
)
from app.services.dataset import DatasetManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    data: DatasetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new dataset

    Creates a new ML dataset with version tracking.
    """
    manager = DatasetManager(db)

    # Check if dataset name already exists for this user
    existing = await manager.get_dataset_by_name(data.name, str(current_user.id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset with name '{data.name}' already exists",
        )

    # Create dataset
    dataset = await manager.create_dataset(data, str(current_user.id))

    # Log access
    await manager.log_access(
        dataset.dataset_id,
        str(current_user.id),
        "create",
    )

    return DatasetResponse.model_validate(dataset)


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    dataset_type: Optional[str] = Query(None, description="Filter by dataset type"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Result offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List datasets

    Returns a paginated list of datasets accessible to the user.
    """
    manager = DatasetManager(db)

    # Non-admin users can only see their own datasets or public ones
    owner_id = str(current_user.id) if not current_user.is_superuser else None
    if not current_user.is_superuser:
        # If filtering by public, don't filter by owner
        if is_public is True:
            owner_id = None
        else:
            # Include both own and public datasets
            datasets, total = await manager.list_datasets_with_public(
                owner_id=str(current_user.id),
                tenant_id=current_user.tenant_id if hasattr(current_user, 'tenant_id') else None,
                project_id=project_id,
                dataset_type=dataset_type,
                tag=tag,
                is_public=is_public,
                status=status,
                search=search,
                limit=limit,
                offset=offset,
            )
            return DatasetListResponse(
                total=total,
                items=[DatasetResponse.model_validate(d) for d in datasets],
            )

    datasets, total = await manager.list_datasets(
        owner_id=owner_id,
        tenant_id=current_user.tenant_id if hasattr(current_user, 'tenant_id') else None,
        project_id=project_id,
        dataset_type=dataset_type,
        tag=tag,
        is_public=is_public,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )

    return DatasetListResponse(
        total=total,
        items=[DatasetResponse.model_validate(d) for d in datasets],
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dataset details

    Returns detailed information about a specific dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access permission
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this dataset",
        )

    # Log access
    await manager.log_access(
        dataset_id,
        str(current_user.id),
        "view",
    )

    return DatasetResponse.model_validate(dataset)


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    data: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update dataset

    Updates dataset information.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this dataset",
        )

    # Update dataset
    updated_dataset = await manager.update_dataset(dataset, data)

    # Log access
    await manager.log_access(
        dataset_id,
        str(current_user.id),
        "edit",
    )

    return DatasetResponse.model_validate(updated_dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete dataset

    Permanently deletes a dataset and all its versions.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this dataset",
        )

    # Delete dataset
    success = await manager.delete_dataset(dataset)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dataset",
        )


@router.post("/{dataset_id}/action")
async def dataset_action(
    dataset_id: str,
    action: DatasetActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform action on dataset

    Actions: split, shuffle, validate, compute_stats, archive
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform actions on this dataset",
        )

    if action.action == "archive":
        await manager.archive_dataset(dataset)
        return {"success": True, "message": "Dataset archived"}
    elif action.action == "unarchive":
        await manager.unarchive_dataset(dataset)
        return {"success": True, "message": "Dataset unarchived"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {action.action}",
        )


@router.post("/{dataset_id}/split")
async def create_dataset_split(
    dataset_id: str,
    config: DatasetSplitConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create dataset splits

    Splits the dataset into train, validation, and test sets.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to split this dataset",
        )

    # TODO: Implement actual splitting logic
    # For now, return a placeholder response
    return {
        "success": True,
        "message": "Dataset splits created",
        "splits": {
            "train": {"ratio": config.train_ratio, "samples": 0},
            "validation": {"ratio": config.validation_ratio, "samples": 0},
            "test": {"ratio": config.test_ratio, "samples": 0},
        }
    }


@router.post("/{dataset_id}/statistics", response_model=DatasetStatisticsResponse)
async def compute_statistics(
    dataset_id: str,
    config: DatasetComputeStatsRequest = DatasetComputeStatsRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute dataset statistics

    Computes and caches statistics for the dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this dataset",
        )

    # TODO: Implement actual statistics computation
    from app.services.dataset import DatasetStatistics
    stats_service = DatasetStatistics(db)
    stats = await stats_service.compute_statistics(dataset_id, force=config.force)

    return DatasetStatisticsResponse.model_validate(stats)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def get_dataset_preview(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of samples to preview"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dataset preview

    Returns a preview of the dataset data.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this dataset",
        )

    # TODO: Implement actual preview generation
    return DatasetPreviewResponse(
        dataset_id=dataset_id,
        preview_data={"samples": []},
        num_preview_samples=0,
        created_at=datetime.utcnow(),
    )


@router.post("/{dataset_id}/tags", response_model=DatasetTagResponse)
async def add_dataset_tag(
    dataset_id: str,
    data: DatasetTagCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a tag to a dataset

    Adds a custom tag to the dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to tag this dataset",
        )

    tag = await manager.add_tag(
        dataset_id=dataset_id,
        key=data.key,
        value=data.value,
        tag_type=data.tag_type,
    )

    return DatasetTagResponse.model_validate(tag)


@router.get("/{dataset_id}/tags", response_model=list[DatasetTagResponse])
async def list_dataset_tags(
    dataset_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List dataset tags

    Returns all tags for a dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this dataset",
        )

    tags = await manager.list_tags(dataset_id)

    return [DatasetTagResponse.model_validate(t) for t in tags]


@router.delete("/tags/{tag_id}")
async def delete_dataset_tag(
    tag_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a dataset tag

    Removes a tag from a dataset.
    """
    manager = DatasetManager(db)

    # TODO: Verify ownership
    success = await manager.remove_tag(tag_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag {tag_id} not found",
        )

    return {"success": True, "message": "Tag deleted"}


@router.get("/{dataset_id}/history")
async def get_dataset_history(
    dataset_id: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dataset access history

    Returns access log for the dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check ownership
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this dataset's history",
        )

    logs = await manager.get_access_history(dataset_id, limit)

    return {
        "dataset_id": dataset_id,
        "access_logs": [
            {
                "user_id": log.user_id,
                "action": log.action,
                "access_type": log.access_type,
                "accessed_at": log.accessed_at,
            }
            for log in logs
        ],
    }


@router.post("/{dataset_id}/duplicate", response_model=DatasetResponse)
async def duplicate_dataset(
    dataset_id: str,
    new_name: str = Query(..., min_length=1, max_length=256, description="Name for the duplicate"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate a dataset

    Creates a copy of the dataset.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to duplicate this dataset",
        )

    # Check if new name already exists
    existing = await manager.get_dataset_by_name(new_name, str(current_user.id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset with name '{new_name}' already exists",
        )

    # Duplicate dataset
    new_dataset = await manager.duplicate_dataset(dataset, new_name, str(current_user.id))

    # Log access
    await manager.log_access(
        new_dataset.dataset_id,
        str(current_user.id),
        "create",
        context={"source_dataset_id": dataset_id},
    )

    return DatasetResponse.model_validate(new_dataset)


@router.post("/import", response_model=DatasetImportResponse)
async def import_dataset(
    data: DatasetImportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Import a dataset

    Imports a dataset from an external source.
    """
    manager = DatasetManager(db)

    # Check if name already exists
    existing = await manager.get_dataset_by_name(data.name, str(current_user.id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Dataset with name '{data.name}' already exists",
        )

    # TODO: Implement actual import logic
    import_job_id = f"import-{uuid4().hex[:8]}"

    return DatasetImportResponse(
        dataset_id="",
        status="pending",
        message="Import job started",
        import_job_id=import_job_id,
    )


@router.post("/{dataset_id}/export", response_model=DatasetExportResponse)
async def export_dataset(
    dataset_id: str,
    data: DatasetExportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a dataset

    Exports a dataset in the specified format.
    """
    manager = DatasetManager(db)
    dataset = await manager.get_dataset(dataset_id)

    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found",
        )

    # Check access
    if not current_user.is_superuser and dataset.owner_id != str(current_user.id) and not dataset.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export this dataset",
        )

    # Log access
    await manager.log_access(
        dataset_id,
        str(current_user.id),
        "export",
        context={"format": data.format},
    )

    # TODO: Implement actual export logic
    return DatasetExportResponse(
        export_url=f"/exports/{dataset_id}.{data.format}",
        expires_at=datetime.utcnow(),
    )
