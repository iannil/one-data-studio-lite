"""
Dataset Schemas

Pydantic schemas for dataset management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator


# =============================================================================
# Dataset Base Schemas
# =============================================================================

class DatasetBase(BaseModel):
    """Base dataset schema"""
    name: str = Field(..., min_length=1, max_length=256, description="Dataset unique name")
    display_name: Optional[str] = Field(None, max_length=256, description="Display name")
    description: Optional[str] = Field(None, description="Dataset description")
    dataset_type: str = Field(..., description="Dataset type: image, text, audio, video, tabular, multimodal, time_series")

    # Storage
    storage_type: str = Field(default="minio", description="Storage type: minio, s3, oss, nfs, local")
    storage_path: str = Field(..., description="Storage path")

    # Format
    format: Optional[str] = Field(None, description="Data format: coco, yolo, csv, json, parquet, etc.")
    schema_: Optional[Dict[str, Any]] = Field(None, description="Data schema", alias="schema")

    # Tags
    tags: Optional[List[str]] = Field(default=None, description="List of tags")

    # Source
    source_type: Optional[str] = Field(None, description="Source type: upload, annotation, export, synthesis")
    source_id: Optional[str] = Field(None, description="Source ID reference")

    # Visibility
    is_public: bool = Field(default=False, description="Is dataset public")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    @validator('schema_', pre=True)
    def validate_schema(cls, v):
        """Handle schema field name"""
        if isinstance(v, dict) or v is None:
            return v
        return {}

    class Config:
        populate_by_name = True


class DatasetCreate(DatasetBase):
    """Schema for creating a dataset"""
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    project_id: Optional[str] = Field(None, description="Project ID")


class DatasetUpdate(BaseModel):
    """Schema for updating a dataset"""
    display_name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, description="Dataset status")


# =============================================================================
# Dataset Response Schemas
# =============================================================================

class DatasetResponse(DatasetBase):
    """Schema for dataset response"""
    id: str
    dataset_id: str
    total_size_bytes: Optional[int] = None
    num_samples: Optional[int] = None
    num_classes: Optional[int] = None
    class_distribution: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_accessed_at: Optional[datetime] = None
    owner_id: str
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DatasetListResponse(BaseModel):
    """Schema for dataset list response"""
    total: int
    items: List[DatasetResponse]


# =============================================================================
# Dataset Version Schemas
# =============================================================================

class DatasetVersionBase(BaseModel):
    """Base dataset version schema"""
    version_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    storage_path: str = Field(..., description="Storage path for this version")
    change_description: Optional[str] = None
    checksum: Optional[str] = None
    checksum_algorithm: Optional[str] = None
    is_major: bool = Field(default=False, description="Is this a major version?")
    tags: Optional[List[str]] = Field(default=None, description="Version tags (e.g., latest, production)")
    metadata: Optional[Dict[str, Any]] = None


class DatasetVersionCreate(DatasetVersionBase):
    """Schema for creating a dataset version"""
    parent_version_id: Optional[str] = Field(None, description="Parent version ID")


class DatasetVersionResponse(DatasetVersionBase):
    """Schema for dataset version response"""
    id: str
    version_id: str
    dataset_id: str
    version_number: int
    total_size_bytes: Optional[int] = None
    added_samples: Optional[int] = None
    removed_samples: Optional[int] = None
    modified_samples: Optional[int] = None
    created_at: datetime
    created_by: str

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Dataset Tag Schemas
# =============================================================================

class DatasetTagBase(BaseModel):
    """Base dataset tag schema"""
    key: str = Field(..., max_length=100)
    value: Optional[str] = Field(None, max_length=500)
    tag_type: Optional[str] = Field(None, max_length=50)


class DatasetTagCreate(DatasetTagBase):
    """Schema for creating a dataset tag"""
    pass


class DatasetTagResponse(DatasetTagBase):
    """Schema for dataset tag response"""
    id: str
    tag_id: str
    dataset_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Dataset Split Schemas
# =============================================================================

class DatasetSplitBase(BaseModel):
    """Base dataset split schema"""
    name: str = Field(..., max_length=50, description="Split name: train, validation, test")
    split_type: str = Field(..., description="Split type: train, validation, test, custom")
    ratio: Optional[float] = Field(None, ge=0, le=1, description="Split ratio")
    num_samples: int = Field(..., ge=0, description="Number of samples")
    storage_path: str = Field(..., description="Storage path for split data")
    stratified: bool = Field(default=False, description="Is stratified split?")
    stratify_column: Optional[str] = Field(None, max_length=100, description="Column to stratify by")
    metadata: Optional[Dict[str, Any]] = None


class DatasetSplitCreate(DatasetSplitBase):
    """Schema for creating a dataset split"""
    version_id: Optional[str] = Field(None, description="Dataset version ID")


class DatasetSplitResponse(DatasetSplitBase):
    """Schema for dataset split response"""
    id: str
    split_id: str
    dataset_id: str
    version_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Dataset Preview Schemas
# =============================================================================

class DatasetPreviewResponse(BaseModel):
    """Schema for dataset preview response"""
    dataset_id: str
    version_id: Optional[str] = None
    preview_data: Dict[str, Any]
    num_preview_samples: int
    columns: Optional[List[Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Dataset Statistics Schemas
# =============================================================================

class DatasetStatisticsResponse(BaseModel):
    """Schema for dataset statistics response"""
    dataset_id: str
    total_samples: int
    total_classes: Optional[int] = None
    class_distribution: Optional[Dict[str, Any]] = None
    feature_statistics: Optional[Dict[str, Any]] = None
    image_statistics: Optional[Dict[str, Any]] = None
    text_statistics: Optional[Dict[str, Any]] = None
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Dataset Import/Export Schemas
# =============================================================================

class DatasetImportRequest(BaseModel):
    """Schema for dataset import request"""
    name: str = Field(..., min_length=1, max_length=256)
    display_name: Optional[str] = Field(None, max_length=256)
    description: Optional[str] = None
    dataset_type: str = Field(..., description="Dataset type")
    format: str = Field(..., description="Data format")
    source_url: str = Field(..., description="Source URL or file path")
    import_options: Optional[Dict[str, Any]] = Field(None, description="Import options")
    tags: Optional[List[str]] = None
    is_public: bool = Field(default=False)


class DatasetImportResponse(BaseModel):
    """Schema for dataset import response"""
    dataset_id: str
    status: str
    message: str
    import_job_id: Optional[str] = None


class DatasetExportRequest(BaseModel):
    """Schema for dataset export request"""
    format: str = Field(..., description="Export format: csv, json, coco, yolo, etc.")
    export_options: Optional[Dict[str, Any]] = Field(None, description="Export options")
    include_splits: bool = Field(default=True, description="Include data splits")
    version_id: Optional[str] = Field(None, description="Export specific version")


class DatasetExportResponse(BaseModel):
    """Schema for dataset export response"""
    export_url: str
    expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None


# =============================================================================
# Dataset Action Schemas
# =============================================================================

class DatasetActionRequest(BaseModel):
    """Schema for dataset action request"""
    action: str = Field(..., description="Action: split, shuffle, validate, compute_stats, archive")


class DatasetSplitConfig(BaseModel):
    """Schema for dataset split configuration"""
    train_ratio: float = Field(default=0.8, ge=0, le=1)
    validation_ratio: float = Field(default=0.1, ge=0, le=1)
    test_ratio: float = Field(default=0.1, ge=0, le=1)
    stratified: bool = Field(default=False)
    stratify_column: Optional[str] = Field(None)
    random_seed: Optional[int] = Field(None)


class DatasetComputeStatsRequest(BaseModel):
    """Schema for compute statistics request"""
    force: bool = Field(default=False, description="Force recompute")
    sample_limit: Optional[int] = Field(None, description="Limit samples for computation")
