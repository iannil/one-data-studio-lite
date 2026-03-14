"""
Feature Store Service

Provides offline and online feature storage, retrieval, and serving capabilities.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.feature_store import (
    FeatureGroup, Feature, Entity, FeatureView, FeatureService, FeatureSet,
)

logger = logging.getLogger(__name__)


class FeatureStoreType(str, Enum):
    """Feature store types"""
    OFFLINE = "offline"  # Batch storage (data warehouse, lakehouse)
    ONLINE = "online"    # Low-latency serving (Redis, DynamoDB)
    HYBRID = "hybrid"    # Both offline and online


class DataType(str, Enum):
    """Feature data types"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    ARRAY = "array"
    VECTOR = "vector"
    TIMESTAMP = "timestamp"


class FeatureType(str, Enum):
    """Feature semantic types"""
    CONTINUOUS = "continuous"
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"
    TEXT = "text"
    EMBEDDING = "embedding"


@dataclass
class FeatureValue:
    """A feature value with metadata"""
    feature_name: str
    value: Any
    timestamp: datetime
    is_null: bool = False


@dataclass
class FeatureRow:
    """A row of feature values for an entity"""
    entity_key: Dict[str, Any]
    features: Dict[str, FeatureValue]
    event_timestamp: Optional[datetime] = None


@dataclass
class FeatureSetResult:
    """Result from a feature set retrieval"""
    feature_set_id: str
    rows: List[FeatureRow]
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureStoreService:
    """
    Feature Store Service

    Manages feature storage, retrieval, and serving.
    """

    def __init__(self, db: Session):
        self.db = db

    # ============================================================================
    # Feature Group Management
    # ============================================================================

    def create_feature_group(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        entity_id: Optional[str] = None,
        primary_keys: Optional[List[str]] = None,
        store_type: FeatureStoreType = FeatureStoreType.OFFLINE,
        source_type: Optional[str] = None,
        source_config: Optional[Dict[str, Any]] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> FeatureGroup:
        """Create a new feature group"""
        feature_group = FeatureGroup(
            name=name,
            display_name=display_name or name,
            description=description,
            entity_id=entity_id,
            primary_keys=primary_keys or [],
            store_type=store_type.value,
            source_type=source_type,
            source_config=source_config or {},
            owner_id=owner_id,
            tags=tags or [],
            properties=properties or {},
        )

        self.db.add(feature_group)
        self.db.commit()
        self.db.refresh(feature_group)

        logger.info(f"Created feature group: {feature_group.id}")
        return feature_group

    def get_feature_group(self, feature_group_id: str) -> Optional[FeatureGroup]:
        """Get a feature group by ID"""
        return self.db.query(FeatureGroup).filter(
            FeatureGroup.id == feature_group_id
        ).first()

    def get_feature_group_by_name(self, name: str) -> Optional[FeatureGroup]:
        """Get a feature group by name"""
        return self.db.query(FeatureGroup).filter(
            FeatureGroup.name == name
        ).first()

    def list_feature_groups(
        self,
        entity_id: Optional[str] = None,
        store_type: Optional[FeatureStoreType] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FeatureGroup]:
        """List feature groups with optional filters"""
        query = self.db.query(FeatureGroup)

        if entity_id:
            query = query.filter(FeatureGroup.entity_id == entity_id)

        if store_type:
            query = query.filter(FeatureGroup.store_type == store_type.value)

        if status:
            query = query.filter(FeatureGroup.status == status)

        if owner_id:
            query = query.filter(FeatureGroup.owner_id == owner_id)

        if tags:
            query = query.filter(FeatureGroup.tags.contains(tags))

        query = query.order_by(FeatureGroup.created_at.desc())
        query = query.offset(offset).limit(limit)

        return query.all()

    def update_feature_group(
        self,
        feature_group_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        source_config: Optional[Dict[str, Any]] = None,
        schedule_cron: Optional[str] = None,
        tags: Optional[List[str]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[FeatureGroup]:
        """Update a feature group"""
        feature_group = self.get_feature_group(feature_group_id)
        if not feature_group:
            return None

        if display_name:
            feature_group.display_name = display_name
        if description is not None:
            feature_group.description = description
        if source_config:
            feature_group.source_config = source_config
        if schedule_cron:
            feature_group.schedule_cron = schedule_cron
        if tags:
            feature_group.tags = tags
        if properties:
            feature_group.properties = properties

        feature_group.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(feature_group)

        return feature_group

    def delete_feature_group(self, feature_group_id: str) -> bool:
        """Delete a feature group"""
        feature_group = self.get_feature_group(feature_group_id)
        if not feature_group:
            return False

        self.db.delete(feature_group)
        self.db.commit()

        logger.info(f"Deleted feature group: {feature_group_id}")
        return True

    # ============================================================================
    # Feature Management
    # ============================================================================

    def create_feature(
        self,
        feature_group_id: str,
        name: str,
        data_type: DataType,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        entity_id: Optional[str] = None,
        feature_type: Optional[FeatureType] = None,
        dimension: Optional[int] = None,
        validation_config: Optional[Dict[str, Any]] = None,
        transformation: Optional[str] = None,
        transformation_config: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Feature:
        """Create a new feature"""
        feature = Feature(
            name=name,
            display_name=display_name or name,
            description=description,
            feature_group_id=feature_group_id,
            entity_id=entity_id,
            data_type=data_type.value,
            feature_type=feature_type.value if feature_type else None,
            dimension=dimension,
            validation_config=validation_config or {},
            transformation=transformation,
            transformation_config=transformation_config or {},
            tags=tags or [],
        )

        self.db.add(feature)

        # Update feature group feature count
        feature_group = self.get_feature_group(feature_group_id)
        if feature_group:
            feature_group.feature_count += 1

        self.db.commit()
        self.db.refresh(feature)

        logger.info(f"Created feature: {feature.id}")
        return feature

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        """Get a feature by ID"""
        return self.db.query(Feature).filter(Feature.id == feature_id).first()

    def list_features(
        self,
        feature_group_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        data_type: Optional[DataType] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Feature]:
        """List features with optional filters"""
        query = self.db.query(Feature)

        if feature_group_id:
            query = query.filter(Feature.feature_group_id == feature_group_id)

        if entity_id:
            query = query.filter(Feature.entity_id == entity_id)

        if data_type:
            query = query.filter(Feature.data_type == data_type.value)

        if status:
            query = query.filter(Feature.status == status)

        query = query.order_by(Feature.name)
        query = query.offset(offset).limit(limit)

        return query.all()

    def update_feature_statistics(
        self,
        feature_id: str,
        null_count: int,
        null_percentage: float,
        unique_count: Optional[int] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        mean_value: Optional[float] = None,
        std_value: Optional[float] = None,
        histogram: Optional[Dict[str, Any]] = None,
    ) -> Optional[Feature]:
        """Update feature statistics"""
        feature = self.get_feature(feature_id)
        if not feature:
            return None

        feature.null_count = null_count
        feature.null_percentage = null_percentage
        feature.unique_count = unique_count
        feature.min_value = min_value
        feature.max_value = max_value
        feature.mean_value = mean_value
        feature.std_value = std_value
        feature.histogram = histogram

        self.db.commit()
        self.db.refresh(feature)

        return feature

    # ============================================================================
    # Entity Management
    # ============================================================================

    def create_entity(
        self,
        name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        join_keys: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Entity:
        """Create a new entity"""
        entity = Entity(
            name=name,
            display_name=display_name or name,
            description=description,
            entity_type=entity_type,
            join_keys=join_keys or [],
            tags=tags or [],
        )

        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)

        logger.info(f"Created entity: {entity.id}")
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID"""
        return self.db.query(Entity).filter(Entity.id == entity_id).first()

    def get_entity_by_name(self, name: str) -> Optional[Entity]:
        """Get an entity by name"""
        return self.db.query(Entity).filter(Entity.name == name).first()

    def list_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Entity]:
        """List entities with optional filters"""
        query = self.db.query(Entity)

        if entity_type:
            query = query.filter(Entity.entity_type == entity_type)

        query = query.order_by(Entity.name)
        query = query.offset(offset).limit(limit)

        return query.all()

    # ============================================================================
    # Feature View Management
    # ============================================================================

    def create_feature_view(
        self,
        name: str,
        feature_group_id: str,
        feature_ids: List[str],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        view_type: str = "selection",
        transformation_sql: Optional[str] = None,
        transformation_config: Optional[Dict[str, Any]] = None,
        serving_mode: str = "online",
        ttl_seconds: int = 86400,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> FeatureView:
        """Create a new feature view"""
        feature_view = FeatureView(
            name=name,
            display_name=display_name or name,
            description=description,
            feature_group_id=feature_group_id,
            feature_ids=feature_ids,
            view_type=view_type,
            transformation_sql=transformation_sql,
            transformation_config=transformation_config or {},
            serving_mode=serving_mode,
            ttl_seconds=ttl_seconds,
            owner_id=owner_id,
            tags=tags or [],
        )

        self.db.add(feature_view)
        self.db.commit()
        self.db.refresh(feature_view)

        logger.info(f"Created feature view: {feature_view.id}")
        return feature_view

    def get_feature_view(self, feature_view_id: str) -> Optional[FeatureView]:
        """Get a feature view by ID"""
        return self.db.query(FeatureView).filter(
            FeatureView.id == feature_view_id
        ).first()

    def list_feature_views(
        self,
        feature_group_id: Optional[str] = None,
        serving_mode: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FeatureView]:
        """List feature views with optional filters"""
        query = self.db.query(FeatureView)

        if feature_group_id:
            query = query.filter(FeatureView.feature_group_id == feature_group_id)

        if serving_mode:
            query = query.filter(FeatureView.serving_mode == serving_mode)

        if status:
            query = query.filter(FeatureView.status == status)

        query = query.order_by(FeatureView.created_at.desc())
        query = query.offset(offset).limit(limit)

        return query.all()

    # ============================================================================
    # Feature Service Management
    # ============================================================================

    def create_feature_service(
        self,
        name: str,
        feature_view_ids: List[str],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        serving_type: str = "low_latency",
        max_qps: int = 1000,
        target_p95_latency_ms: int = 50,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 300,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> FeatureService:
        """Create a new feature service"""
        feature_service = FeatureService(
            name=name,
            display_name=display_name or name,
            description=description,
            feature_view_ids=feature_view_ids,
            serving_type=serving_type,
            max_qps=max_qps,
            target_p95_latency_ms=target_p95_latency_ms,
            enable_cache=enable_cache,
            cache_ttl_seconds=cache_ttl_seconds,
            owner_id=owner_id,
            tags=tags or [],
            endpoint_path=f"/api/v1/feature-services/{name}",
        )

        self.db.add(feature_service)
        self.db.commit()
        self.db.refresh(feature_service)

        logger.info(f"Created feature service: {feature_service.id}")
        return feature_service

    def get_feature_service(self, service_id: str) -> Optional[FeatureService]:
        """Get a feature service by ID"""
        return self.db.query(FeatureService).filter(
            FeatureService.id == service_id
        ).first()

    def list_feature_services(
        self,
        deployment_status: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FeatureService]:
        """List feature services with optional filters"""
        query = self.db.query(FeatureService)

        if deployment_status:
            query = query.filter(FeatureService.deployment_status == deployment_status)

        if status:
            query = query.filter(FeatureService.status == status)

        if owner_id:
            query = query.filter(FeatureService.owner_id == owner_id)

        query = query.order_by(FeatureService.created_at.desc())
        query = query.offset(offset).limit(limit)

        return query.all()

    def deploy_feature_service(self, service_id: str) -> Optional[FeatureService]:
        """Deploy a feature service"""
        service = self.get_feature_service(service_id)
        if not service:
            return None

        service.deployment_status = "deployed"
        service.deployed_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(service)

        logger.info(f"Deployed feature service: {service_id}")
        return service

    # ============================================================================
    # Feature Set Management
    # ============================================================================

    def create_feature_set(
        self,
        name: str,
        feature_view_ids: List[str],
        snapshot_time: datetime,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        training_data_path: Optional[str] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> FeatureSet:
        """Create a new feature set (training snapshot)"""
        snapshot_id = f"{name}_{snapshot_time.strftime('%Y%m%d_%H%M%S')}"

        feature_set = FeatureSet(
            name=name,
            display_name=display_name or name,
            description=description,
            feature_view_ids=feature_view_ids,
            snapshot_time=snapshot_time,
            snapshot_id=snapshot_id,
            training_data_path=training_data_path,
            owner_id=owner_id,
            tags=tags or [],
        )

        self.db.add(feature_set)
        self.db.commit()
        self.db.refresh(feature_set)

        logger.info(f"Created feature set: {feature_set.id}")
        return feature_set

    def get_feature_set(self, feature_set_id: str) -> Optional[FeatureSet]:
        """Get a feature set by ID"""
        return self.db.query(FeatureSet).filter(
            FeatureSet.id == feature_set_id
        ).first()

    def list_feature_sets(
        self,
        owner_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FeatureSet]:
        """List feature sets with optional filters"""
        query = self.db.query(FeatureSet)

        if owner_id:
            query = query.filter(FeatureSet.owner_id == owner_id)

        if status:
            query = query.filter(FeatureSet.status == status)

        query = query.order_by(FeatureSet.snapshot_time.desc())
        query = query.offset(offset).limit(limit)

        return query.all()


def get_feature_store_service(db: Session) -> FeatureStoreService:
    """Get the feature store service instance"""
    return FeatureStoreService(db)
