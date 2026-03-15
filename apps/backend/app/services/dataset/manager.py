"""
Dataset Manager Service

Handles CRUD operations for datasets including creation,
listing, updating, and deletion.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from uuid import uuid4

from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import (
    Dataset,
    DatasetVersion,
    DatasetTag,
    DatasetSplit,
    DatasetPreview,
    DatasetAccessLog,
    DatasetStatistics,
)
from app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
)

logger = logging.getLogger(__name__)


class DatasetManager:
    """
    Dataset lifecycle manager

    Handles dataset creation, modification, deletion, and access tracking.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize dataset manager

        Args:
            db: Database session
        """
        self.db = db

    async def create_dataset(
        self,
        data: DatasetCreate,
        owner_id: str,
    ) -> Dataset:
        """
        Create a new dataset

        Args:
            data: Dataset creation data
            owner_id: User ID of the owner

        Returns:
            Created Dataset
        """
        dataset_id = f"ds-{uuid4().hex[:8]}"

        dataset = Dataset(
            dataset_id=dataset_id,
            owner_id=owner_id,
            tenant_id=data.tenant_id,
            project_id=data.project_id,
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            dataset_type=data.dataset_type,
            storage_type=data.storage_type,
            storage_path=data.storage_path,
            format=data.format,
            schema_=data.schema_,
            tags=data.tags,
            source_type=data.source_type,
            source_id=data.source_id,
            is_public=data.is_public,
            metadata=data.metadata,
            status="ready",
        )

        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(f"Created dataset {dataset_id} for user {owner_id}")

        # Create initial version
        from .version import DatasetVersionManager
        version_manager = DatasetVersionManager(self.db)
        await version_manager.create_version(
            dataset_id=dataset_id,
            storage_path=data.storage_path,
            description="Initial version",
            created_by=owner_id,
        )

        return dataset

    async def get_dataset_by_name(
        self,
        name: str,
        owner_id: str,
    ) -> Optional[Dataset]:
        """
        Get dataset by name and owner

        Args:
            name: Dataset name
            owner_id: Owner user ID

        Returns:
            Dataset or None
        """
        result = await self.db.execute(
            select(Dataset).where(
                and_(Dataset.name == name, Dataset.owner_id == owner_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """
        Get dataset by ID

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset or None
        """
        result = await self.db.execute(
            select(Dataset).where(Dataset.dataset_id == dataset_id)
        )
        return result.scalar_one_or_none()

    async def list_datasets(
        self,
        owner_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        tag: Optional[str] = None,
        is_public: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dataset], int]:
        """
        List datasets with filtering

        Args:
            owner_id: Filter by owner
            tenant_id: Filter by tenant
            project_id: Filter by project
            dataset_type: Filter by dataset type
            tag: Filter by tag
            is_public: Filter by public status
            status: Filter by status
            search: Search in name/description
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            Tuple of (list of datasets, total count)
        """
        conditions = []

        if owner_id:
            conditions.append(Dataset.owner_id == owner_id)
        if tenant_id:
            conditions.append(Dataset.tenant_id == tenant_id)
        if project_id:
            conditions.append(Dataset.project_id == project_id)
        if dataset_type:
            conditions.append(Dataset.dataset_type == dataset_type)
        if is_public is not None:
            conditions.append(Dataset.is_public == is_public)
        if status:
            conditions.append(Dataset.status == status)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                (Dataset.name.ilike(search_pattern)) |
                (Dataset.display_name.ilike(search_pattern)) |
                (Dataset.description.ilike(search_pattern))
            )

        # Get total count
        count_query = select(func.count(Dataset.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = select(Dataset)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Dataset.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        datasets = result.scalars().all()

        # Filter by tag if specified (post-filter)
        if tag:
            datasets = [d for d in datasets if d.tags and tag in d.tags]

        return list(datasets), total

    async def list_datasets_with_public(
        self,
        owner_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        tag: Optional[str] = None,
        is_public: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dataset], int]:
        """
        List datasets including public datasets from other users

        Similar to list_datasets but includes public datasets when filtering.
        """
        conditions = []

        # Include owner's datasets OR public datasets
        if owner_id:
            conditions.append(
                or_(Dataset.owner_id == owner_id, Dataset.is_public == True)
            )
        if tenant_id:
            conditions.append(Dataset.tenant_id == tenant_id)
        if project_id:
            conditions.append(Dataset.project_id == project_id)
        if dataset_type:
            conditions.append(Dataset.dataset_type == dataset_type)
        if is_public is not None:
            conditions.append(Dataset.is_public == is_public)
        if status:
            conditions.append(Dataset.status == status)
        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                (Dataset.name.ilike(search_pattern)) |
                (Dataset.display_name.ilike(search_pattern)) |
                (Dataset.description.ilike(search_pattern))
            )

        # Get total count
        count_query = select(func.count(Dataset.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = select(Dataset)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(Dataset.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        datasets = result.scalars().all()

        # Filter by tag if specified (post-filter)
        if tag:
            datasets = [d for d in datasets if d.tags and tag in d.tags]

        return list(datasets), total

    async def update_dataset(
        self,
        dataset: Dataset,
        data: DatasetUpdate,
    ) -> Dataset:
        """
        Update dataset

        Args:
            dataset: Dataset to update
            data: Update data

        Returns:
            Updated dataset
        """
        if data.display_name is not None:
            dataset.display_name = data.display_name
        if data.description is not None:
            dataset.description = data.description
        if data.tags is not None:
            dataset.tags = data.tags
        if data.is_public is not None:
            dataset.is_public = data.is_public
        if data.metadata is not None:
            dataset.metadata = data.metadata
        if data.status is not None:
            dataset.status = data.status

        dataset.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(dataset)

        return dataset

    async def delete_dataset(self, dataset: Dataset) -> bool:
        """
        Delete dataset and all associated data

        Args:
            dataset: Dataset to delete

        Returns:
            True if successful
        """
        try:
            dataset_id = dataset.dataset_id

            # Delete associated records
            await self.db.execute(
                delete(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
            )
            await self.db.execute(
                delete(DatasetTag).where(DatasetTag.dataset_id == dataset_id)
            )
            await self.db.execute(
                delete(DatasetSplit).where(DatasetSplit.dataset_id == dataset_id)
            )
            await self.db.execute(
                delete(DatasetPreview).where(DatasetPreview.dataset_id == dataset_id)
            )
            await self.db.execute(
                delete(DatasetAccessLog).where(DatasetAccessLog.dataset_id == dataset_id)
            )
            await self.db.execute(
                delete(DatasetStatistics).where(DatasetStatistics.dataset_id == dataset_id)
            )

            # Delete dataset
            await self.db.delete(dataset)
            await self.db.commit()

            logger.info(f"Deleted dataset {dataset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset.dataset_id}: {e}")
            await self.db.rollback()
            return False

    async def log_access(
        self,
        dataset_id: str,
        user_id: str,
        action: str,
        access_type: str = "api",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log dataset access

        Args:
            dataset_id: Dataset ID
            user_id: User ID
            action: Action performed
            access_type: Access type (api, ui, export)
            context: Additional context
        """
        log = DatasetAccessLog(
            dataset_id=dataset_id,
            user_id=user_id,
            action=action,
            access_type=access_type,
            context=context,
        )

        self.db.add(log)

        # Update last accessed timestamp
        await self.db.execute(
            update(Dataset)
            .where(Dataset.dataset_id == dataset_id)
            .values(last_accessed_at=datetime.utcnow())
        )

        await self.db.commit()

    async def add_tag(
        self,
        dataset_id: str,
        key: str,
        value: Optional[str] = None,
        tag_type: Optional[str] = None,
    ) -> DatasetTag:
        """
        Add a tag to a dataset

        Args:
            dataset_id: Dataset ID
            key: Tag key
            value: Tag value
            tag_type: Tag type

        Returns:
            Created tag
        """
        tag_id = f"tag-{uuid4().hex[:8]}"

        tag = DatasetTag(
            tag_id=tag_id,
            dataset_id=dataset_id,
            key=key,
            value=value,
            tag_type=tag_type,
        )

        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)

        return tag

    async def remove_tag(self, tag_id: str) -> bool:
        """
        Remove a tag from a dataset

        Args:
            tag_id: Tag ID

        Returns:
            True if successful
        """
        try:
            await self.db.execute(
                delete(DatasetTag).where(DatasetTag.tag_id == tag_id)
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to remove tag {tag_id}: {e}")
            await self.db.rollback()
            return False

    async def list_tags(
        self,
        dataset_id: str,
    ) -> List[DatasetTag]:
        """
        List all tags for a dataset

        Args:
            dataset_id: Dataset ID

        Returns:
            List of tags
        """
        result = await self.db.execute(
            select(DatasetTag).where(DatasetTag.dataset_id == dataset_id)
        )
        return list(result.scalars().all())

    async def get_access_history(
        self,
        dataset_id: str,
        limit: int = 100,
    ) -> List[DatasetAccessLog]:
        """
        Get access history for a dataset

        Args:
            dataset_id: Dataset ID
            limit: Maximum number of records

        Returns:
            List of access logs
        """
        result = await self.db.execute(
            select(DatasetAccessLog)
            .where(DatasetAccessLog.dataset_id == dataset_id)
            .order_by(DatasetAccessLog.accessed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def archive_dataset(self, dataset: Dataset) -> Dataset:
        """
        Archive a dataset

        Args:
            dataset: Dataset to archive

        Returns:
            Updated dataset
        """
        dataset.status = "archived"
        dataset.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(f"Archived dataset {dataset.dataset_id}")
        return dataset

    async def unarchive_dataset(self, dataset: Dataset) -> Dataset:
        """
        Unarchive a dataset

        Args:
            dataset: Dataset to unarchive

        Returns:
            Updated dataset
        """
        dataset.status = "ready"
        dataset.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(dataset)

        logger.info(f"Unarchived dataset {dataset.dataset_id}")
        return dataset

    async def duplicate_dataset(
        self,
        dataset: Dataset,
        new_name: str,
        owner_id: str,
    ) -> Dataset:
        """
        Duplicate a dataset

        Args:
            dataset: Dataset to duplicate
            new_name: Name for the duplicate
            owner_id: User ID of the owner

        Returns:
            New dataset
        """
        new_dataset_id = f"ds-{uuid4().hex[:8]}"

        new_dataset = Dataset(
            dataset_id=new_dataset_id,
            owner_id=owner_id,
            tenant_id=dataset.tenant_id,
            project_id=dataset.project_id,
            name=new_name,
            display_name=f"{dataset.display_name or dataset.name} (copy)",
            description=dataset.description,
            dataset_type=dataset.dataset_type,
            storage_type=dataset.storage_type,
            storage_path=dataset.storage_path,  # Same storage
            format=dataset.format,
            schema_=dataset.schema_,
            tags=dataset.tags,
            source_type="dataset",
            source_id=dataset.dataset_id,
            is_public=False,  # Duplicates are private by default
            metadata=dataset.metadata,
            status="ready",
        )

        self.db.add(new_dataset)
        await self.db.commit()
        await self.db.refresh(new_dataset)

        logger.info(f"Duplicated dataset {dataset.dataset_id} to {new_dataset_id}")

        return new_dataset
