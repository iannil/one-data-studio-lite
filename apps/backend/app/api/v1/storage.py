"""
Storage API Endpoints

REST API for unified storage management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user,
    get_db,
)
from app.models.user import User
from app.models.storage import StorageConfig, StorageQuota
from app.schemas.storage import (
    StorageConfigCreate,
    StorageConfigUpdate,
    StorageConfigResponse,
    StorageConfigListResponse,
    FileUploadRequest,
    FileUploadResponse,
    FileDownloadRequest,
    FileDownloadResponse,
    FileListRequest,
    FileListResponse,
    StorageQuotaResponse,
    StorageQuotaUpdate,
    StorageStatsResponse,
    StorageHealthCheckResponse,
)
from app.services.storage import StorageManager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/configs", response_model=StorageConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_config(
    data: StorageConfigCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new storage configuration"""
    # Only admins can create storage configs
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create storage configurations",
        )

    manager = StorageManager(db)
    config = await manager.create_storage_config(data, str(current_user.id))

    return StorageConfigResponse.model_validate(config)


@router.get("/configs", response_model=StorageConfigListResponse)
async def list_storage_configs(
    enabled_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List storage configurations"""
    manager = StorageManager(db)

    tenant_id = current_user.tenant_id if hasattr(current_user, 'tenant_id') else None
    configs = await manager.list_storage_configs(tenant_id=tenant_id, enabled_only=enabled_only)

    return StorageConfigListResponse(
        total=len(configs),
        items=[StorageConfigResponse.model_validate(c) for c in configs],
    )


@router.get("/configs/{config_id}", response_model=StorageConfigResponse)
async def get_storage_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get storage configuration details"""
    manager = StorageManager(db)
    config = await manager.get_storage_config(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage config {config_id} not found",
        )

    return StorageConfigResponse.model_validate(config)


@router.put("/configs/{config_id}", response_model=StorageConfigResponse)
async def update_storage_config(
    config_id: str,
    data: StorageConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update storage configuration"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update storage configurations",
        )

    manager = StorageManager(db)
    config = await manager.get_storage_config(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage config {config_id} not found",
        )

    updated_config = await manager.update_storage_config(config, data)

    return StorageConfigResponse.model_validate(updated_config)


@router.delete("/configs/{config_id}")
async def delete_storage_config(
    config_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete storage configuration"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete storage configurations",
        )

    manager = StorageManager(db)
    config = await manager.get_storage_config(config_id)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Storage config {config_id} not found",
        )

    await manager.delete_storage_config(config)

    return {"success": True, "message": "Storage configuration deleted"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    file_path: str = Query(..., description="Destination file path"),
    metadata: Optional[str] = Query(None, description="Additional metadata (JSON)"),
    storage_config_id: Optional[str] = Query(None, description="Specific storage backend"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to storage"""
    import json

    manager = StorageManager(db)

    # Read file data
    data = await file.read()

    # Parse metadata if provided
    metadata_dict = None
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except:
            pass

    # Upload file
    file_record = await manager.upload_file(
        file_path=file_path,
        data=data,
        content_type=file.content_type,
        metadata=metadata_dict,
        storage_config_id=storage_config_id,
        owner_id=str(current_user.id),
    )

    return FileUploadResponse(
        file_id=file_record.file_id,
        file_path=file_path,
        file_size_bytes=file_record.file_size_bytes or 0,
        checksum=file_record.checksum,
    )


@router.get("/download")
async def download_file(
    file_path: str = Query(..., description="File path to download"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a file from storage"""
    manager = StorageManager(db)

    try:
        data = await manager.download_file(file_path)
        return Response(content=data, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found or error downloading: {str(e)}",
        )


@router.delete("/files")
async def delete_file(
    file_path: str = Query(..., description="File path to delete"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file from storage"""
    manager = StorageManager(db)

    success = await manager.delete_file(file_path)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )

    return {"success": True, "message": "File deleted"}


@router.get("/files", response_model=FileListResponse)
async def list_files(
    prefix: str = Query("", description="Path prefix to filter"),
    limit: int = Query(1000, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List files in storage"""
    manager = StorageManager(db)

    result = await manager.list_files(prefix=prefix, limit=limit)

    return FileListResponse(
        files=result.get("files", []),
        common_prefixes=[p.get("Prefix") for p in result.get("common_prefixes", [])],
        is_truncated=result.get("is_truncated", False),
    )


@router.get("/signed-url")
async def get_signed_url(
    file_path: str = Query(..., description="File path"),
    ttl_seconds: int = Query(3600, ge=60, le=86400),
    operation: str = Query("read", description="Operation type: read, write"),
    storage_config_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a signed URL for file access"""
    manager = StorageManager(db)

    url_record = await manager.get_signed_url(
        file_path=file_path,
        user_id=str(current_user.id),
        ttl_seconds=ttl_seconds,
        operation=operation,
        storage_config_id=storage_config_id,
    )

    return {
        "url": url_record.url,
        "url_token": url_record.url_token,
        "expires_at": url_record.expires_at,
    }


@router.get("/health", response_model=list[StorageHealthCheckResponse])
async def check_storage_health(
    config_id: Optional[str] = Query(None, description="Specific config to check"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check storage backend health"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can check storage health",
        )

    manager = StorageManager(db)
    result = await manager.check_storage_health(config_id)

    if config_id:
        return [StorageHealthCheckResponse(**result)]

    return [StorageHealthCheckResponse(**r) for r in result.get("results", [])]


@router.get("/quota", response_model=StorageQuotaResponse)
async def get_storage_quota(
    scope_type: str = Query("tenant", description="Scope type: tenant, user, project"),
    scope_id: Optional[str] = Query(None, description="Scope ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get storage quota information"""
    manager = StorageManager(db)

    # If not specified, use current user's tenant
    if not scope_id:
        scope_id = getattr(current_user, 'tenant_id', str(current_user.id))

    quota = await manager.get_quota(scope_type, scope_id)

    if not quota:
        # Create default quota if none exists
        from app.models.storage import StorageQuota
        quota = StorageQuota(
            id=f"quota-{scope_type}-{scope_id}",
            scope_type=scope_type,
            scope_id=scope_id,
            quota_bytes=100 * 1024 * 1024 * 1024,  # 100GB default
            used_bytes=0,
            file_count=0,
        )
        db.add(quota)
        await db.commit()
        await db.refresh(quota)

    usage_percentage = (quota.used_bytes / quota.quota_bytes) if quota.quota_bytes > 0 else 0

    return StorageQuotaResponse(
        scope_type=quota.scope_type,
        scope_id=quota.scope_id,
        quota_bytes=quota.quota_bytes,
        used_bytes=quota.used_bytes,
        file_count=quota.file_count,
        usage_percentage=usage_percentage,
        alert_threshold=quota.alert_threshold,
        alert_sent=quota.alert_sent,
        created_at=quota.created_at,
        updated_at=quota.updated_at,
    )


@router.put("/quota", response_model=StorageQuotaResponse)
async def update_storage_quota(
    data: StorageQuotaUpdate,
    scope_type: str = Query("tenant"),
    scope_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update storage quota"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update quota",
        )

    manager = StorageManager(db)
    quota = await manager.get_quota(scope_type, scope_id or "default")

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota not found",
        )

    quota.quota_bytes = data.quota_bytes
    quota.alert_threshold = data.alert_threshold
    await db.commit()
    await db.refresh(quota)

    usage_percentage = (quota.used_bytes / quota.quota_bytes) if quota.quota_bytes > 0 else 0

    return StorageQuotaResponse(
        scope_type=quota.scope_type,
        scope_id=quota.scope_id,
        quota_bytes=quota.quota_bytes,
        used_bytes=quota.used_bytes,
        file_count=quota.file_count,
        usage_percentage=usage_percentage,
        alert_threshold=quota.alert_threshold,
        alert_sent=quota.alert_sent,
        created_at=quota.created_at,
        updated_at=quota.updated_at,
    )


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get overall storage statistics"""
    manager = StorageManager(db)
    stats = await manager.get_storage_stats()

    return StorageStatsResponse(**stats)
