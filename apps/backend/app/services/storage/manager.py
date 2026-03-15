"""
Storage Manager Service

High-level storage management service that handles
backend selection, file operations, and quota management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage import (
    StorageConfig,
    StorageFile,
    StorageSignedUrl,
    StorageTransfer,
    StorageQuota,
)
from app.schemas.storage import (
    StorageConfigCreate,
    StorageConfigUpdate,
)

from .backends import get_storage_backend

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Storage lifecycle manager

    Handles storage configuration, file operations, and
    provides unified interface across different backends.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize storage manager

        Args:
            db: Database session
        """
        self.db = db
        self._backends: Dict[str, Any] = {}

    def _get_backend(self, config: StorageConfig) -> Any:
        """
        Get backend instance for config

        Args:
            config: Storage configuration

        Returns:
            Storage backend instance
        """
        if config.config_id not in self._backends:
            backend_config = {
                "backend_type": config.backend_type,
                "endpoint": config.endpoint,
                "access_key": config.access_key,
                "secret_key": config.secret_key,
                "bucket": config.bucket,
                "region": config.region,
                "mount_path": config.mount_path,
                "nfs_server": config.nfs_server,
                "nfs_path": config.nfs_path,
                "oss_endpoint": config.oss_endpoint,
                "oss_bucket": config.oss_bucket,
                **(config.config or {}),
            }
            self._backends[config.config_id] = get_storage_backend(backend_config)

        return self._backends[config.config_id]

    async def get_default_backend(self) -> Optional[Any]:
        """Get default storage backend"""
        result = await self.db.execute(
            select(StorageConfig).where(
                and_(StorageConfig.is_default == True, StorageConfig.enabled == True)
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            # Try to get any enabled backend
            result = await self.db.execute(
                select(StorageConfig).where(StorageConfig.enabled == True).limit(1)
            )
            config = result.scalar_one_or_none()

        if not config:
            return None

        return self._get_backend(config)

    async def get_backend_by_id(self, config_id: str) -> Optional[Any]:
        """Get backend by config ID"""
        result = await self.db.execute(
            select(StorageConfig).where(StorageConfig.config_id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            return None

        return self._get_backend(config)

    async def create_storage_config(
        self,
        data: StorageConfigCreate,
        owner_id: Optional[str] = None,
    ) -> StorageConfig:
        """
        Create a new storage configuration

        Args:
            data: Storage configuration data
            owner_id: Owner user ID

        Returns:
            Created configuration
        """
        config_id = f"storage-{uuid4().hex[:8]}"

        # If this is set as default, unset other defaults
        if data.is_default:
            await self.db.execute(
                update(StorageConfig)
                .where(StorageConfig.is_default == True)
                .values(is_default=False)
            )

        config = StorageConfig(
            config_id=config_id,
            backend_type=data.backend_type,
            name=data.name,
            description=data.description,
            endpoint=data.endpoint,
            access_key=data.access_key,
            secret_key=data.secret_key,
            bucket=data.bucket,
            region=data.region,
            mount_path=data.mount_path,
            nfs_server=data.nfs_server,
            nfs_path=data.nfs_path,
            oss_endpoint=data.oss_endpoint,
            oss_bucket=data.oss_bucket,
            config=data.config,
            is_default=data.is_default,
            tenant_id=data.tenant_id,
        )

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        # Test connection
        backend = self._get_backend(config)
        health = await backend.health_check()
        config.status = "active" if health["is_healthy"] else "error"
        config.error_message = health.get("error")
        config.last_checked_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Created storage config {config_id}")

        return config

    async def list_storage_configs(
        self,
        tenant_id: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[StorageConfig]:
        """List storage configurations"""
        conditions = []

        if tenant_id:
            conditions.append(StorageConfig.tenant_id == tenant_id)
        if enabled_only:
            conditions.append(StorageConfig.enabled == True)

        query = select(StorageConfig)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(StorageConfig.is_default.desc(), StorageConfig.created_at)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_storage_config(self, config_id: str) -> Optional[StorageConfig]:
        """Get storage configuration by ID"""
        result = await self.db.execute(
            select(StorageConfig).where(StorageConfig.config_id == config_id)
        )
        return result.scalar_one_or_none()

    async def update_storage_config(
        self,
        config: StorageConfig,
        data: StorageConfigUpdate,
    ) -> StorageConfig:
        """Update storage configuration"""
        if data.name is not None:
            config.name = data.name
        if data.description is not None:
            config.description = data.description
        if data.enabled is not None:
            config.enabled = data.enabled
        if data.config is not None:
            config.config = data.config

        # Clear backend cache
        if config.config_id in self._backends:
            del self._backends[config.config_id]

        config.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def delete_storage_config(self, config: StorageConfig) -> bool:
        """Delete storage configuration"""
        if config.is_system:
            raise ValueError("Cannot delete system storage configuration")

        # Clear backend cache
        if config.config_id in self._backends:
            del self._backends[config.config_id]

        await self.db.delete(config)
        await self.db.commit()

        return True

    async def upload_file(
        self,
        file_path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        storage_config_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> StorageFile:
        """
        Upload a file

        Args:
            file_path: Destination file path
            data: File data
            content_type: MIME type
            metadata: Additional metadata
            storage_config_id: Specific storage backend
            owner_id: Owner user ID

        Returns:
            Storage file record
        """
        # Get backend
        if storage_config_id:
            backend = await self.get_backend_by_id(storage_config_id)
            if not backend:
                raise ValueError(f"Storage config {storage_config_id} not found")
        else:
            backend = await self.get_default_backend()
            if not backend:
                raise RuntimeError("No storage backend available")

        # Upload to backend
        result = await backend.upload(file_path, data, content_type, metadata)

        # Create file record
        file_id = f"file-{uuid4().hex[:8]}"
        file_record = StorageFile(
            file_id=file_id,
            storage_config_id=storage_config_id,
            backend_type=backend.backend_type,
            file_path=file_path,
            file_name=file_path.split("/")[-1],
            file_size_bytes=result.get("file_size"),
            content_type=content_type,
            metadata=metadata,
            checksum=result.get("checksum"),
            checksum_algorithm=result.get("checksum_algorithm"),
            owner_id=owner_id,
        )

        self.db.add(file_record)
        await self.db.commit()
        await self.db.refresh(file_record)

        # Update quota
        await self._update_quota_usage(
            scope_type="tenant" if owner_id else "system",
            scope_id=owner_id or "default",
            file_size=result.get("file_size", 0),
            increment=True,
        )

        return file_record

    async def download_file(self, file_path: str) -> bytes:
        """Download a file"""
        backend = await self.get_default_backend()
        if not backend:
            raise RuntimeError("No storage backend available")

        return await backend.download(file_path)

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        backend = await self.get_default_backend()
        if not backend:
            raise RuntimeError("No storage backend available")

        # Get file info first for quota update
        file_info = await backend.get_file_info(file_path)

        result = await backend.delete(file_path)

        if result and file_info:
            # Update quota
            await self._update_quota_usage(
                scope_type="system",
                scope_id="default",
                file_size=file_info.get("file_size", 0),
                increment=False,
            )

        return result

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 1000,
        continuation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List files"""
        backend = await self.get_default_backend()
        if not backend:
            return {"files": [], "common_prefixes": [], "is_truncated": False}

        return await backend.list_files(prefix, limit, continuation_token)

    async def get_signed_url(
        self,
        file_path: str,
        user_id: str,
        ttl_seconds: int = 3600,
        operation: str = "read",
        storage_config_id: Optional[str] = None,
    ) -> StorageSignedUrl:
        """
        Generate a signed URL for file access

        Args:
            file_path: File path
            user_id: User requesting access
            ttl_seconds: URL time-to-live
            operation: Operation type
            storage_config_id: Specific storage backend

        Returns:
            Signed URL record
        """
        # Get backend
        if storage_config_id:
            backend = await self.get_backend_by_id(storage_config_id)
        else:
            backend = await self.get_default_backend()

        if not backend:
            raise RuntimeError("No storage backend available")

        # Generate signed URL
        url = await backend.get_signed_url(file_path, ttl_seconds, operation)

        # Create signed URL record
        url_id = f"url-{uuid4().hex[:8]}"
        token = uuid4().hex

        url_record = StorageSignedUrl(
            url_id=url_id,
            file_id=file_path,  # Using file_path as temporary file_id
            url_token=token,
            url=url,
            created_for=user_id,
            access_type=operation,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        )

        self.db.add(url_record)
        await self.db.commit()
        await self.db.refresh(url_record)

        return url_record

    async def check_storage_health(
        self,
        config_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check storage backend health

        Args:
            config_id: Specific config to check, or check all

        Returns:
            Health check results
        """
        if config_id:
            config = await self.get_storage_config(config_id)
            if not config:
                return {"error": f"Storage config {config_id} not found"}

            backend = self._get_backend(config)
            health = await backend.health_check()

            # Update status
            config.status = "active" if health["is_healthy"] else "error"
            config.error_message = health.get("error")
            config.last_checked_at = datetime.utcnow()
            await self.db.commit()

            return {
                "config_id": config_id,
                "backend_type": config.backend_type,
                **health,
                "checked_at": datetime.utcnow(),
            }

        # Check all enabled configs
        results = []
        configs = await self.list_storage_configs(enabled_only=True)

        for config in configs:
            try:
                backend = self._get_backend(config)
                health = await backend.health_check()

                # Update status
                config.status = "active" if health["is_healthy"] else "error"
                config.error_message = health.get("error")
                config.last_checked_at = datetime.utcnow()

                results.append({
                    "config_id": config.config_id,
                    "backend_type": config.backend_type,
                    **health,
                })
            except Exception as e:
                results.append({
                    "config_id": config.config_id,
                    "backend_type": config.backend_type,
                    "is_healthy": False,
                    "error": str(e),
                })

        await self.db.commit()

        return {"results": results}

    async def _update_quota_usage(
        self,
        scope_type: str,
        scope_id: str,
        file_size: int,
        increment: bool = True,
    ) -> None:
        """Update quota usage"""
        result = await self.db.execute(
            select(StorageQuota).where(
                and_(
                    StorageQuota.scope_type == scope_type,
                    StorageQuota.scope_id == scope_id,
                )
            )
        )
        quota = result.scalar_one_or_none()

        if quota:
            if increment:
                quota.used_bytes += file_size
                quota.file_count += 1
            else:
                quota.used_bytes = max(0, quota.used_bytes - file_size)
                quota.file_count = max(0, quota.file_count - 1)
            quota.updated_at = datetime.utcnow()

    async def get_quota(
        self,
        scope_type: str,
        scope_id: str,
    ) -> Optional[StorageQuota]:
        """Get quota for scope"""
        result = await self.db.execute(
            select(StorageQuota).where(
                and_(
                    StorageQuota.scope_type == scope_type,
                    StorageQuota.scope_id == scope_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get overall storage statistics"""
        # Count files by backend
        result = await self.db.execute(
            select(
                StorageFile.backend_type,
                func.count(StorageFile.id).label("count"),
                func.sum(StorageFile.file_size_bytes).label("total_bytes"),
            )
            .group_by(StorageFile.backend_type)
        )
        by_backend = {r.backend_type: {"count": r.count, "total_bytes": r.total_bytes or 0}
                      for r in result.scalars()}

        # Get quota info
        quota_result = await self.db.execute(
            select(func.count(StorageQuota.id))
        )
        total_quotas = quota_result.scalar()

        # Total files
        files_result = await self.db.execute(
            select(func.count(StorageFile.id))
        )
        total_files = files_result.scalar()

        # Total bytes
        bytes_result = await self.db.execute(
            select(func.sum(StorageFile.file_size_bytes))
        )
        total_bytes = bytes_result.scalar() or 0

        return {
            "total_files": total_files,
            "total_bytes": total_bytes,
            "total_quotas": total_quotas,
            "by_backend": by_backend,
        }
