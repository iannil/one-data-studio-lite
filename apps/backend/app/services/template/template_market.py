"""
Template Market Service

Extends the base template service with marketplace features including:
- More template categories (training, data quality, ETL, monitoring, etc.)
- Template versioning
- Template ratings and reviews
- Template usage statistics
- Featured and trending templates
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from .template_service import (
    TemplateService,
    TemplateVariable,
    TemplateTask,
    WorkflowTemplate,
    get_template_service,
)

logger = logging.getLogger(__name__)


class TemplateCategory(str, Enum):
    """Template categories"""

    ETL = "etl"
    ML_TRAINING = "ml_training"
    DATA_QUALITY = "data_quality"
    MONITORING = "monitoring"
    BATCH_INFERENCE = "batch_inference"
    DATA_SYNC = "data_sync"
    REPORTING = "reporting"
    NOTIFICATION = "notification"
    BACKUP = "backup"
    DATA_PIPELINE = "data_pipeline"


class TemplateComplexity(str, Enum):
    """Template complexity levels"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class TemplateReview:
    """Template review/rating"""

    review_id: str
    template_id: str
    user_id: int
    user_name: str
    rating: int  # 1-5
    comment: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class TemplateVersion:
    """Template version information"""

    version: str
    changelog: str
    created_at: str
    author: str


@dataclass
class TemplateStats:
    """Template usage statistics"""

    usage_count: int = 0
    view_count: int = 0
    download_count: int = 0
    fork_count: int = 0
    avg_rating: float = 0.0
    rating_count: int = 0


@dataclass
class MarketTemplate:
    """Extended template for marketplace"""

    # Base template fields
    id: str
    name: str
    description: str
    category: TemplateCategory
    icon: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    tasks: List[TemplateTask] = field(default_factory=list)
    variables: List[TemplateVariable] = field(default_factory=list)
    thumbnail: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None

    # Market-specific fields
    complexity: TemplateComplexity = TemplateComplexity.INTERMEDIATE
    featured: bool = False
    verified: bool = False
    official: bool = False
    stats: TemplateStats = field(default_factory=TemplateStats)
    versions: List[TemplateVersion] = field(default_factory=list)
    current_version: str = "1.0.0"
    reviews: List[TemplateReview] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None
    repository_url: Optional[str] = None
    license: str = "MIT"
    requirements: List[str] = field(default_factory=list)


class TemplateMarketService:
    """
    Service for managing the template marketplace

    Provides additional functionality beyond basic template management:
    - Template discovery and search
    - Ratings and reviews
    - Usage statistics
    - Template verification
    """

    def __init__(self, template_service: Optional[TemplateService] = None):
        """
        Initialize template market service

        Args:
            template_service: Base template service instance
        """
        self.template_service = template_service or get_template_service()
        self._market_templates: Dict[str, MarketTemplate] = {}
        self._reviews: Dict[str, List[TemplateReview]] = {}
        self._stats: Dict[str, TemplateStats] = {}

        # Load extended templates
        self._load_market_templates()

    def _load_market_templates(self):
        """Load marketplace templates"""
        # Import built-in templates from base service
        builtin = self.template_service._builtin_templates
        for template_id, template in builtin.items():
            self._market_templates[template_id] = MarketTemplate(
                id=template.id,
                name=template.name,
                description=template.description,
                category=TemplateCategory(template.category),
                icon=template.icon,
                tags=template.tags or [],
                tasks=template.tasks or [],
                variables=template.variables or [],
                thumbnail=template.thumbnail,
                author=template.author,
                created_at=template.created_at,
                complexity=self._get_complexity_for_template(template_id),
                official=True,
                verified=True,
                current_version="1.0.0",
                versions=[
                    TemplateVersion(
                        version="1.0.0",
                        changelog="Initial release",
                        created_at=template.created_at or "2024-01-01T00:00:00Z",
                        author=template.author or "System",
                    )
                ],
            )
            self._stats[template_id] = TemplateStats(
                usage_count=0,
                view_count=0,
                download_count=0,
                fork_count=0,
                avg_rating=4.5,
                rating_count=10,
            )

    def _get_complexity_for_template(self, template_id: str) -> TemplateComplexity:
        """Determine complexity level for a template"""
        template = self._market_templates.get(template_id)
        if not template:
            return TemplateComplexity.INTERMEDIATE

        task_count = len(template.tasks)
        variable_count = len(template.variables)

        if task_count <= 3 and variable_count <= 3:
            return TemplateComplexity.BEGINNER
        elif task_count <= 6:
            return TemplateComplexity.INTERMEDIATE
        else:
            return TemplateComplexity.ADVANCED

    async def list_market_templates(
        self,
        category: Optional[TemplateCategory] = None,
        complexity: Optional[TemplateComplexity] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "popular",  # popular, newest, rating, verified
        featured_only: bool = False,
        verified_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List marketplace templates with filters

        Args:
            category: Filter by category
            complexity: Filter by complexity
            search: Search in name/description
            tags: Filter by tags
            sort_by: Sort order
            featured_only: Only featured templates
            verified_only: Only verified templates

        Returns:
            List of template summaries with market info
        """
        templates = []

        for template_id, template in self._market_templates.items():
            # Apply filters
            if category and template.category != category:
                continue
            if complexity and template.complexity != complexity:
                continue
            if featured_only and not template.featured:
                continue
            if verified_only and not template.verified:
                continue
            if tags:
                if not any(tag in template.tags for tag in tags):
                    continue
            if search:
                search_lower = search.lower()
                if (
                    search_lower not in template.name.lower()
                    and search_lower not in template.description.lower()
                ):
                    continue

            # Get stats
            stats = self._stats.get(template_id, TemplateStats())

            templates.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "icon": template.icon,
                "tags": template.tags,
                "complexity": template.complexity.value,
                "author": template.author,
                "created_at": template.created_at,
                "thumbnail": template.thumbnail,
                "official": template.official,
                "verified": template.verified,
                "featured": template.featured,
                "task_count": len(template.tasks),
                "variable_count": len(template.variables),
                "current_version": template.current_version,
                "stats": {
                    "usage_count": stats.usage_count,
                    "view_count": stats.view_count,
                    "download_count": stats.download_count,
                    "avg_rating": stats.avg_rating,
                    "rating_count": stats.rating_count,
                },
            })

        # Sort results
        if sort_by == "popular":
            templates.sort(key=lambda t: t["stats"]["usage_count"], reverse=True)
        elif sort_by == "newest":
            templates.sort(key=lambda t: t["created_at"], reverse=True)
        elif sort_by == "rating":
            templates.sort(key=lambda t: t["stats"]["avg_rating"], reverse=True)
        elif sort_by == "verified":
            templates.sort(key=lambda t: t["verified"], reverse=True)

        return templates

    async def get_market_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed template info

        Args:
            template_id: Template identifier

        Returns:
            Full template details with market info
        """
        template = self._market_templates.get(template_id)
        if not template:
            # Try to get from base service
            base_template = await self.template_service.get_template(template_id)
            if not base_template:
                return None

            # Convert to market template
            template = MarketTemplate(
                id=base_template["id"],
                name=base_template["name"],
                description=base_template["description"],
                category=TemplateCategory(base_template.get("category", "data_pipeline")),
                icon=base_template.get("icon"),
                tags=base_template.get("tags", []),
                thumbnail=base_template.get("thumbnail"),
                author=base_template.get("author"),
                created_at=base_template.get("created_at"),
            )

        # Increment view count
        if template_id in self._stats:
            self._stats[template_id].view_count += 1

        # Get reviews
        reviews = self._reviews.get(template_id, [])

        return {
            **template.__dict__,
            "stats": self._stats.get(template_id, TemplateStats()).__dict__,
            "reviews": [r.__dict__ for r in reviews],
        }

    async def get_template_categories(self) -> List[Dict[str, Any]]:
        """Get all template categories with counts"""
        category_counts: Dict[str, int] = {}
        for template in self._market_templates.values():
            cat = template.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        categories = []
        for category in TemplateCategory:
            categories.append({
                "value": category.value,
                "label": category.value.replace("_", " ").title(),
                "count": category_counts.get(category.value, 0),
                "icon": self._get_category_icon(category),
            })

        return categories

    def _get_category_icon(self, category: TemplateCategory) -> str:
        """Get icon for category"""
        icons = {
            TemplateCategory.ETL: "🔄",
            TemplateCategory.ML_TRAINING: "🧠",
            TemplateCategory.DATA_QUALITY: "📊",
            TemplateCategory.MONITORING: "📈",
            TemplateCategory.BATCH_INFERENCE: "🔮",
            TemplateCategory.DATA_SYNC: "🔄",
            TemplateCategory.REPORTING: "📄",
            TemplateCategory.NOTIFICATION: "🔔",
            TemplateCategory.BACKUP: "💾",
            TemplateCategory.DATA_PIPELINE: "⚙️",
        }
        return icons.get(category, "📦")

    async def get_featured_templates(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get featured templates"""
        featured = [t for t in self._market_templates.values() if t.featured]
        if not featured:
            # Return top rated if no featured
            featured = sorted(
                self._market_templates.values(),
                key=lambda t: self._stats.get(t.id, TemplateStats()).avg_rating,
                reverse=True,
            )[:limit]

        result = []
        for template in featured[:limit]:
            stats = self._stats.get(template.id, TemplateStats())
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "icon": template.icon,
                "tags": template.tags,
                "complexity": template.complexity.value,
                "author": template.author,
                "thumbnail": template.thumbnail,
                "verified": template.verified,
                "stats": {
                    "avg_rating": stats.avg_rating,
                    "rating_count": stats.rating_count,
                    "usage_count": stats.usage_count,
                },
            })

        return result

    async def get_trending_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending templates (most used recently)"""
        trending = sorted(
            self._market_templates.values(),
            key=lambda t: self._stats.get(t.id, TemplateStats()).usage_count,
            reverse=True,
        )[:limit]

        result = []
        for template in trending:
            stats = self._stats.get(template.id, TemplateStats())
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "icon": template.icon,
                "tags": template.tags,
                "stats": {
                    "usage_count": stats.usage_count,
                    "avg_rating": stats.avg_rating,
                },
            })

        return result

    async def add_review(
        self,
        template_id: str,
        user_id: int,
        user_name: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> TemplateReview:
        """
        Add a review to a template

        Args:
            template_id: Template identifier
            user_id: User ID
            user_name: User name
            rating: Rating (1-5)
            comment: Optional comment

        Returns:
            Created review
        """
        if template_id not in self._market_templates:
            raise ValueError(f"Template {template_id} not found")

        review = TemplateReview(
            review_id=str(uuid.uuid4()),
            template_id=template_id,
            user_id=user_id,
            user_name=user_name,
            rating=max(1, min(5, rating)),
            comment=comment,
        )

        if template_id not in self._reviews:
            self._reviews[template_id] = []
        self._reviews[template_id].append(review)

        # Update stats
        if template_id not in self._stats:
            self._stats[template_id] = TemplateStats()

        stats = self._stats[template_id]
        total_rating = sum(r.rating for r in self._reviews[template_id])
        stats.avg_rating = total_rating / len(self._reviews[template_id])
        stats.rating_count = len(self._reviews[template_id])

        logger.info(f"Added review for template {template_id}: {rating}/5")
        return review

    async def get_reviews(self, template_id: str) -> List[TemplateReview]:
        """Get all reviews for a template"""
        return self._reviews.get(template_id, [])

    async def record_usage(self, template_id: str):
        """Record template usage"""
        if template_id not in self._stats:
            self._stats[template_id] = TemplateStats()
        self._stats[template_id].usage_count += 1

    async def record_download(self, template_id: str):
        """Record template download"""
        if template_id not in self._stats:
            self._stats[template_id] = TemplateStats()
        self._stats[template_id].download_count += 1

    async def get_recommended_templates(
        self,
        user_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recommended templates for a user

        Args:
            user_id: User ID
            limit: Max recommendations

        Returns:
            List of recommended templates
        """
        # For now, return top rated templates
        # In production, this would use collaborative filtering
        top_rated = sorted(
            self._market_templates.values(),
            key=lambda t: self._stats.get(t.id, TemplateStats()).avg_rating,
            reverse=True,
        )[:limit]

        result = []
        for template in top_rated:
            stats = self._stats.get(template.id, TemplateStats())
            result.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "icon": template.icon,
                "tags": template.tags,
                "complexity": template.complexity.value,
                "stats": {
                    "avg_rating": stats.avg_rating,
                    "rating_count": stats.rating_count,
                },
            })

        return result


# Singleton instance
_market_service: Optional[TemplateMarketService] = None


def get_market_service() -> TemplateMarketService:
    """Get the template market service singleton"""
    global _market_service
    if _market_service is None:
        _market_service = TemplateMarketService()
    return _market_service
