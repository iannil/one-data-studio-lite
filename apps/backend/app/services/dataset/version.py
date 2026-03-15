"""
Dataset Version Management Service

Handles versioning for datasets including creation,
comparison, and rollback.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset, DatasetVersion

logger = logging.getLogger(__name__)


class DatasetVersionManager:
    """
    Dataset version lifecycle manager

    Handles version creation, listing, comparison, and rollback.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize version manager

        Args:
            db: Database session
        """
        self.db = db

    async def create_version(
        self,
        dataset_id: str,
        storage_path: str,
        description: Optional[str] = None,
        created_by: str = "",
        parent_version_id: Optional[str] = None,
        checksum: Optional[str] = None,
        is_major: bool = False,
    ) -> DatasetVersion:
        """
        Create a new dataset version

        Args:
            dataset_id: Dataset ID
            storage_path: Storage path for this version
            description: Version description
            created_by: User ID who created the version
            parent_version_id: Parent version ID
            checksum: Data checksum
            is_major: Is this a major version?

        Returns:
            Created version
        """
        # Get the next version number
        result = await self.db.execute(
            select(func.max(DatasetVersion.version_number))
            .where(DatasetVersion.dataset_id == dataset_id)
        )
        max_version = result.scalar()
        next_version = (max_version or 0) + 1

        version_id = f"ver-{uuid4().hex[:8]}"

        version = DatasetVersion(
            version_id=version_id,
            dataset_id=dataset_id,
            version_number=next_version,
            description=description,
            storage_path=storage_path,
            parent_version_id=parent_version_id,
            checksum=checksum,
            is_major=is_major,
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        logger.info(f"Created version {next_version} for dataset {dataset_id}")

        return version

    async def get_version(self, version_id: str) -> Optional[DatasetVersion]:
        """
        Get version by ID

        Args:
            version_id: Version ID

        Returns:
            DatasetVersion or None
        """
        result = await self.db.execute(
            select(DatasetVersion).where(DatasetVersion.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self,
        dataset_id: str,
        limit: int = 100,
    ) -> List[DatasetVersion]:
        """
        List all versions of a dataset

        Args:
            dataset_id: Dataset ID
            limit: Maximum number of results

        Returns:
            List of versions
        """
        result = await self.db.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_version(
        self,
        dataset_id: str,
    ) -> Optional[DatasetVersion]:
        """
        Get the latest version of a dataset

        Args:
            dataset_id: Dataset ID

        Returns:
            Latest version or None
        """
        result = await self.db.execute(
            select(DatasetVersion)
            .where(DatasetVersion.dataset_id == dataset_id)
            .order_by(DatasetVersion.version_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def compare_versions(
        self,
        version_id_1: str,
        version_id_2: str,
    ) -> Dict[str, Any]:
        """
        Compare two dataset versions

        Args:
            version_id_1: First version ID
            version_id_2: Second version ID

        Returns:
            Comparison result
        """
        version_1 = await self.get_version(version_id_1)
        version_2 = await self.get_version(version_id_2)

        if not version_1 or not version_2:
            raise ValueError("One or both versions not found")

        # TODO: Implement actual comparison logic
        return {
            "version_1": {
                "version_id": version_1.version_id,
                "version_number": version_1.version_number,
            },
            "version_2": {
                "version_id": version_2.version_id,
                "version_number": version_2.version_number,
            },
            "differences": [],
        }

    async def add_tag_to_version(
        self,
        version_id: str,
        tag: str,
    ) -> bool:
        """
        Add a tag to a version

        Args:
            version_id: Version ID
            tag: Tag to add (e.g., "latest", "production")

        Returns:
            True if successful
        """
        version = await self.get_version(version_id)
        if not version:
            return False

        if version.tags is None:
            version.tags = []

        if tag not in version.tags:
            version.tags.append(tag)
            await self.db.commit()

        return True

    async def remove_tag_from_version(
        self,
        version_id: str,
        tag: str,
    ) -> bool:
        """
        Remove a tag from a version

        Args:
            version_id: Version ID
            tag: Tag to remove

        Returns:
            True if successful
        """
        version = await self.get_version(version_id)
        if not version or not version.tags:
            return False

        if tag in version.tags:
            version.tags.remove(tag)
            await self.db.commit()

        return True

    async def get_version_by_tag(
        self,
        dataset_id: str,
        tag: str,
    ) -> Optional[DatasetVersion]:
        """
        Get a version by tag

        Args:
            dataset_id: Dataset ID
            tag: Tag to search for

        Returns:
            DatasetVersion or None
        """
        result = await self.db.execute(
            select(DatasetVersion).where(
                and_(
                    DatasetVersion.dataset_id == dataset_id,
                    DatasetVersion.tags.contains([tag]),
                )
            )
        )
        return result.scalar_one_or_none()

    async def delete_version(
        self,
        version_id: str,
    ) -> bool:
        """
        Delete a dataset version

        Args:
            version_id: Version ID

        Returns:
            True if successful
        """
        try:
            version = await self.get_version(version_id)
            if not version:
                return False

            await self.db.delete(version)
            await self.db.commit()

            logger.info(f"Deleted version {version_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete version {version_id}: {e}")
            await self.db.rollback()
            return False

    async def restore_version(
        self,
        dataset_id: str,
        version_id: str,
        restored_by: str,
    ) -> Optional[DatasetVersion]:
        """
        Restore a dataset to a previous version

        Args:
            dataset_id: Dataset ID
            version_id: Version ID to restore
            restored_by: User ID performing the restore

        Returns:
            New version created from restore
        """
        version = await self.get_version(version_id)
        if not version or version.dataset_id != dataset_id:
            return None

        # Create a new version from the restored version
        new_version = await self.create_version(
            dataset_id=dataset_id,
            storage_path=version.storage_path,
            description=f"Restored from version {version.version_number}",
            created_by=restored_by,
            parent_version_id=version_id,
        )

        return new_version

    async def get_version_chain(
        self,
        version_id: str,
    ) -> List[DatasetVersion]:
        """
        Get the version chain (all ancestors) for a version

        Args:
            version_id: Version ID

        Returns:
            List of versions in order (oldest first)
        """
        chain = []
        current = await self.get_version(version_id)

        while current:
            chain.insert(0, current)
            if current.parent_version_id:
                current = await self.get_version(current.parent_version_id)
            else:
                break

        return chain
