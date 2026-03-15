"""
Storage Schemas

Pydantic schemas for unified storage management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, validator


# =============================================================================
# Storage Config Schemas
# =============================================================================

class StorageConfigBase(BaseModel):
    """Base storage config schema"""
    backend_type: str = Field(..., description="Backend type: s3, minio, oss, nfs, local")
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None

    # S3-compatible configuration
    endpoint: Optional[str] = Field(None, description="S3 endpoint URL")
    access_key: Optional[str] = Field(None, max_length=256)
    secret_key: Optional[str] = Field(None, max_length=256)
    bucket: Optional[str] = Field(None, max_length=256)
    region: Optional[str] = Field(None, max_length=100)

    # NFS/Local configuration
    mount_path: Optional[str] = Field(None, max_length=512)
    nfs_server: Optional[str] = Field(None, max_length=256)
    nfs_path: Optional[str] = Field(None, max_length=512)

    # OSS specific
    oss_endpoint: Optional[str] = Field(None, max_length=512)
    oss_bucket: Optional[str] = Field(None, max_length=256)

    # Additional configuration
    config: Optional[Dict[str, Any]] = None


class StorageConfigCreate(StorageConfigBase):
    """Schema for creating storage config"""
    is_default: bool = Field(default=False)
    tenant_id: Optional[str] = None


class StorageConfigUpdate(BaseModel):
    """Schema for updating storage config"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class StorageConfigResponse(StorageConfigBase):
    """Schema for storage config response"""
    id: str
    config_id: str
    is_default: bool
    enabled: bool
    status: str
    last_checked_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tenant_id: Optional[str] = None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @validator('secret_key', pre=True)
    def hide_secret_key(cls, v):
        """Hide secret key in responses"""
        if v and len(v) > 8:
            return "******"
        return v


class StorageConfigListResponse(BaseModel):
    """Schema for storage config list response"""
    total: int
    items: List[StorageConfigResponse]


# =============================================================================
# Storage File Schemas
# =============================================================================

class StorageFileBase(BaseModel):
    """Base storage file schema"""
    file_path: str = Field(..., max_length=1000)
    file_name: str = Field(..., max_length=512)
    content_type: Optional[str] = Field(None, max_length=256)
    metadata: Optional[Dict[str, Any]] = None
    is_public: bool = Field(default=False)


class StorageFileCreate(StorageFileBase):
    """Schema for creating storage file record"""
    storage_config_id: Optional[str] = None


class StorageFileResponse(StorageFileBase):
    """Schema for storage file response"""
    id: str
    file_id: str
    storage_config_id: Optional[str] = None
    backend_type: str
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    checksum_algorithm: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StorageFileListResponse(BaseModel):
    """Schema for file list response"""
    total: int
    items: List[StorageFileResponse]


# =============================================================================
# File Operation Schemas
# =============================================================================

class FileUploadRequest(BaseModel):
    """Schema for file upload request"""
    file_path: str = Field(..., max_length=1000, description="Destination path")
    content_type: Optional[str] = Field(None, max_length=256)
    metadata: Optional[Dict[str, Any]] = None
    overwrite: bool = Field(default=False)
    storage_config_id: Optional[str] = Field(None, description="Specific storage backend")


class FileUploadResponse(BaseModel):
    """Schema for file upload response"""
    file_id: str
    file_path: str
    file_size_bytes: int
    upload_url: Optional[str] = None
    checksum: Optional[str] = None


class FileDownloadRequest(BaseModel):
    """Schema for file download request"""
    file_path: str = Field(..., max_length=1000)
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)


class FileDownloadResponse(BaseModel):
    """Schema for file download response"""
    download_url: str
    expires_at: datetime
    file_size_bytes: Optional[int] = None


class FileDeleteRequest(BaseModel):
    """Schema for file delete request"""
    file_path: str = Field(..., max_length=1000)


class FileListRequest(BaseModel):
    """Schema for file list request"""
    prefix: str = Field(default="", description="Filter by path prefix")
    limit: int = Field(default=1000, ge=1, le=10000)
    continuation_token: Optional[str] = Field(None, description="Pagination token")


class FileListResponse(BaseModel):
    """Schema for file list response"""
    files: List[Dict[str, Any]]
    common_prefixes: List[str]
    continuation_token: Optional[str] = None
    is_truncated: bool


# =============================================================================
# Transfer Schemas
# =============================================================================

class StorageTransferBase(BaseModel):
    """Base storage transfer schema"""
    source_config_id: str
    dest_config_id: str
    source_path: str = Field(..., max_length=1000)
    dest_path: str = Field(..., max_length=1000)
    transfer_type: str = Field(default="copy", description="copy, move, sync")
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None


class StorageTransferCreate(StorageTransferBase):
    """Schema for creating transfer"""
    pass


class StorageTransferResponse(StorageTransferBase):
    """Schema for transfer response"""
    id: str
    transfer_id: str
    status: str
    progress: float
    total_files: int
    transferred_files: int
    total_bytes: int
    transferred_bytes: int
    error_message: Optional[str] = None
    failed_files: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str

    model_config = ConfigDict(from_attributes=True)


class StorageTransferListResponse(BaseModel):
    """Schema for transfer list response"""
    total: int
    items: List[StorageTransferResponse]


# =============================================================================
# Quota Schemas
# =============================================================================

class StorageQuotaResponse(BaseModel):
    """Schema for storage quota response"""
    scope_type: str
    scope_id: str
    quota_bytes: int
    used_bytes: int
    file_count: int
    usage_percentage: float
    alert_threshold: float
    alert_sent: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StorageQuotaUpdate(BaseModel):
    """Schema for updating quota"""
    quota_bytes: int = Field(..., gt=0)
    alert_threshold: float = Field(default=0.9, ge=0, le=1)


# =============================================================================
# Storage Statistics Schemas
# =============================================================================

class StorageStatsResponse(BaseModel):
    """Schema for storage statistics response"""
    total_files: int
    total_bytes: int
    total_quotas: int
    by_backend: Dict[str, Dict[str, Any]]
    by_scope: List[Dict[str, Any]]


class StorageHealthCheckResponse(BaseModel):
    """Schema for health check response"""
    config_id: str
    backend_type: str
    is_healthy: bool
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    checked_at: datetime
