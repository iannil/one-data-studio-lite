"""
Dataset Management Models

Models for managing ML datasets including versioning, tags, and splits.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Dataset(Base):
    """Dataset main table"""
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic information
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Dataset type
    dataset_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # image, text, audio, video, tabular, multimodal, time_series

    # Storage location
    storage_type: Mapped[str] = mapped_column(String(50), default="minio")  # minio, s3, oss, nfs, local
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    total_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Format information
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # coco, yolo, csv, json, parquet, etc.
    schema_: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="schema")

    # Statistics
    num_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    num_classes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    class_distribution: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    dataset_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="metadata")
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Source information
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # upload, annotation, export, synthesis
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Reference to source

    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="ready", index=True
    )  # ready, processing, error, archived

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Dataset {self.dataset_id}:{self.name}>"


class DatasetVersion(Base):
    """Dataset version table"""
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    version_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )

    # Version information
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Storage location for this version
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    total_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Changes from previous version
    change_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    added_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    removed_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    modified_samples: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)

    # Checksum for integrity verification
    checksum: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    checksum_algorithm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # md5, sha256, etc.

    # Parent version (for version chain)
    parent_version_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Is this a major version?
    is_major: Mapped[bool] = mapped_column(Boolean, default=False)

    # Tags
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)  # e.g., ["latest", "production"]

    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    dataset_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="metadata")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Created by
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<DatasetVersion {self.version_id}:v{self.version_number}>"


class DatasetTag(Base):
    """Dataset tag table for flexible tagging"""
    __tablename__ = "dataset_tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    tag_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )

    # Tag information
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Tag type for categorization
    tag_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # label, domain, quality, custom

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DatasetTag {self.key}:{self.value}>"


class DatasetSplit(Base):
    """Dataset split (train/validation/test)"""
    __tablename__ = "dataset_splits"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    split_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )
    version_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Split information
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # train, validation, test
    split_type: Mapped[str] = mapped_column(String(50), nullable=False)  # train, validation, test, custom

    # Split configuration
    ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # e.g., 0.8 for train
    num_samples: Mapped[int] = mapped_column(Integer, nullable=False)

    # Storage location
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Stratification information
    stratified: Mapped[bool] = mapped_column(Boolean, default=False)
    stratify_column: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metadata (renamed from 'metadata' to avoid SQLAlchemy reserved word)
    dataset_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="metadata")

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DatasetSplit {self.split_id}:{self.name}>"


class DatasetPreview(Base):
    """Dataset preview cache for quick UI rendering"""
    __tablename__ = "dataset_previews"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )
    version_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Preview data (limited number of samples)
    preview_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Preview metadata
    num_preview_samples: Mapped[int] = mapped_column(Integer, default=10)
    columns: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DatasetPreview {self.dataset_id}>"


class DatasetAccessLog(Base):
    """Dataset access log for tracking usage"""
    __tablename__ = "dataset_access_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )

    # Access information
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # view, download, edit, delete
    access_type: Mapped[str] = mapped_column(String(20), default="api")  # api, ui, export

    # Context
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamp
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<DatasetAccessLog {self.dataset_id}:{self.action}>"


class DatasetStatistics(Base):
    """Dataset statistics cache for quick access"""
    __tablename__ = "dataset_statistics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("datasets.dataset_id"), nullable=False, index=True, unique=True
    )

    # Basic statistics
    total_samples: Mapped[int] = mapped_column(Integer, default=0)
    total_classes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Class distribution
    class_distribution: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Feature statistics (for tabular data)
    feature_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Image statistics (for image data)
    image_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # avg dimensions, format distribution

    # Text statistics (for text data)
    text_statistics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # avg length, vocabulary size

    # Timestamp
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DatasetStatistics {self.dataset_id}>"
