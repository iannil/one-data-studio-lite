"""
Storage Abstraction Models

Models for unified storage management across different backends
(S3, MinIO, OSS, NFS, Local).
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, BigInteger, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StorageConfig(Base):
    """Storage configuration for different backends"""
    __tablename__ = "storage_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    config_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Backend information
    backend_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # s3, minio, oss, nfs, local
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Connection configuration
    endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # For S3-compatible
    access_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    secret_key: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # Encrypted
    bucket: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # NFS/Local configuration
    mount_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    nfs_server: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    nfs_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # OSS specific
    oss_endpoint: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    oss_bucket: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Additional configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Is this the default storage?
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Status
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, error, disconnected

    # Last connection check
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Ownership
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<StorageConfig {self.config_id}:{self.backend_type}>"


class StorageFile(Base):
    """File metadata record"""
    __tablename__ = "storage_files"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    file_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Storage information
    storage_config_id: Mapped[Optional[str]] = mapped_column(
        String(100), ForeignKey("storage_configs.config_id"), nullable=True, index=True
    )
    backend_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # File information
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # MIME type and metadata
    content_type: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    file_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="metadata")

    # Checksum for integrity
    checksum: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    checksum_algorithm: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # md5, sha256, etag

    # Access control
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Signed URL information
    signed_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signed_url_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<StorageFile {self.file_id}:{self.file_name}>"


class StorageSignedUrl(Base):
    """Signed URL tracking for access control"""
    __tablename__ = "storage_signed_urls"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    url_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # File reference
    file_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("storage_files.file_id"), nullable=False, index=True
    )

    # URL information
    url_token: Mapped[str] = mapped_column(String(256), unique=True, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)

    # Access control
    created_for: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # User ID
    access_type: Mapped[str] = mapped_column(String(20), default="read")  # read, write, delete

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    max_access_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<StorageSignedUrl {self.url_id}>"


class StorageTransfer(Base):
    """Storage transfer job for moving data between backends"""
    __tablename__ = "storage_transfers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    transfer_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Source and destination
    source_config_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("storage_configs.config_id"), nullable=False
    )
    dest_config_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("storage_configs.config_id"), nullable=False
    )
    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    dest_path: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Transfer configuration
    transfer_type: Mapped[str] = mapped_column(String(50), default="copy")  # copy, move, sync
    include_pattern: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    exclude_pattern: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)

    # Statistics
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    transferred_files: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    transferred_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failed_files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Owner
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<StorageTransfer {self.transfer_id}:{self.status}>"


class StorageQuota(Base):
    """Storage quota tracking"""
    __tablename__ = "storage_quotas"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Scope (tenant, user, or project)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)  # tenant, user, project
    scope_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Quota configuration
    quota_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Total quota
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)  # Used space
    file_count: Mapped[int] = mapped_column(Integer, default=0)  # Number of files

    # Alerts
    alert_threshold: Mapped[float] = mapped_column(Float, default=0.9)  # Alert at 90%
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<StorageQuota {self.scope_type}:{self.scope_id}>"
