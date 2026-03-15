"""
Dataset Statistics Service

Computes and caches statistics for datasets.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dataset import Dataset, DatasetStatistics

logger = logging.getLogger(__name__)


class DatasetStatistics:
    """
    Dataset statistics calculator

    Computes and caches statistics for different dataset types.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize dataset statistics service

        Args:
            db: Database session
        """
        self.db = db

    async def compute_statistics(
        self,
        dataset_id: str,
        force: bool = False,
        sample_limit: Optional[int] = None,
    ) -> DatasetStatistics:
        """
        Compute statistics for a dataset

        Args:
            dataset_id: Dataset ID
            force: Force recompute even if cached
            sample_limit: Limit samples for computation

        Returns:
            Dataset statistics
        """
        # Check if statistics already exist
        if not force:
            result = await self.db.execute(
                select(DatasetStatistics).where(
                    DatasetStatistics.dataset_id == dataset_id
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Get dataset
        dataset_result = await self.db.execute(
            select(Dataset).where(Dataset.dataset_id == dataset_id)
        )
        dataset = dataset_result.scalar_one_or_none()

        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Compute statistics based on dataset type
        if dataset.dataset_type == "tabular":
            stats = await self._compute_tabular_stats(dataset, sample_limit)
        elif dataset.dataset_type == "image":
            stats = await self._compute_image_stats(dataset, sample_limit)
        elif dataset.dataset_type == "text":
            stats = await self._compute_text_stats(dataset, sample_limit)
        else:
            stats = await self._compute_generic_stats(dataset, sample_limit)

        # Save or update statistics
        result = await self.db.execute(
            select(DatasetStatistics).where(
                DatasetStatistics.dataset_id == dataset_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.total_samples = stats.get("total_samples", 0)
            existing.total_classes = stats.get("total_classes")
            existing.class_distribution = stats.get("class_distribution")
            existing.feature_statistics = stats.get("feature_statistics")
            existing.image_statistics = stats.get("image_statistics")
            existing.text_statistics = stats.get("text_statistics")
            existing.computed_at = datetime.utcnow()
        else:
            from uuid import uuid4
            existing = DatasetStatistics(
                id=str(uuid4()),
                dataset_id=dataset_id,
                total_samples=stats.get("total_samples", 0),
                total_classes=stats.get("total_classes"),
                class_distribution=stats.get("class_distribution"),
                feature_statistics=stats.get("feature_statistics"),
                image_statistics=stats.get("image_statistics"),
                text_statistics=stats.get("text_statistics"),
                computed_at=datetime.utcnow(),
            )
            self.db.add(existing)

        await self.db.commit()
        await self.db.refresh(existing)

        return existing

    async def _compute_tabular_stats(
        self,
        dataset: Dataset,
        sample_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute statistics for tabular data"""
        # TODO: Implement actual tabular statistics computation
        return {
            "total_samples": dataset.num_samples or 0,
            "total_classes": dataset.num_classes,
            "feature_statistics": {},
        }

    async def _compute_image_stats(
        self,
        dataset: Dataset,
        sample_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute statistics for image data"""
        # TODO: Implement actual image statistics computation
        return {
            "total_samples": dataset.num_samples or 0,
            "total_classes": dataset.num_classes,
            "class_distribution": dataset.class_distribution or {},
            "image_statistics": {
                "avg_width": 0,
                "avg_height": 0,
                "format_distribution": {},
            },
        }

    async def _compute_text_stats(
        self,
        dataset: Dataset,
        sample_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute statistics for text data"""
        # TODO: Implement actual text statistics computation
        return {
            "total_samples": dataset.num_samples or 0,
            "total_classes": dataset.num_classes,
            "text_statistics": {
                "avg_length": 0,
                "min_length": 0,
                "max_length": 0,
                "vocabulary_size": 0,
            },
        }

    async def _compute_generic_stats(
        self,
        dataset: Dataset,
        sample_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compute generic statistics"""
        return {
            "total_samples": dataset.num_samples or 0,
            "total_classes": dataset.num_classes,
            "class_distribution": dataset.class_distribution or {},
        }

    async def get_statistics(
        self,
        dataset_id: str,
    ) -> Optional[DatasetStatistics]:
        """
        Get cached statistics for a dataset

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset statistics or None
        """
        result = await self.db.execute(
            select(DatasetStatistics).where(
                DatasetStatistics.dataset_id == dataset_id
            )
        )
        return result.scalar_one_or_none()

    async def invalidate_statistics(
        self,
        dataset_id: str,
    ) -> bool:
        """
        Invalidate cached statistics for a dataset

        Args:
            dataset_id: Dataset ID

        Returns:
            True if successful
        """
        try:
            from sqlalchemy import delete
            await self.db.execute(
                delete(DatasetStatistics).where(
                    DatasetStatistics.dataset_id == dataset_id
                )
            )
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate statistics for {dataset_id}: {e}")
            await self.db.rollback()
            return False
