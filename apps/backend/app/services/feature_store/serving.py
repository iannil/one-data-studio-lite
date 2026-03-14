"""
Feature Store Serving Service

Provides online and offline feature retrieval capabilities.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy.orm import Session

from app.models.feature_store import (
    FeatureGroup, Feature, FeatureView, FeatureService,
)
from app.services.feature_store.feature_service import (
    FeatureValue, FeatureRow, FeatureSetResult,
    FeatureStoreService, get_feature_store_service,
)

logger = logging.getLogger(__name__)


class RetrievalMode(str, Enum):
    """Feature retrieval modes"""
    ONLINE = "online"        # Real-time low-latency retrieval
    OFFLINE = "offline"      # Batch retrieval from warehouse
    HYBRID = "hybrid"        # Combine online and offline


@dataclass
class ServingConfig:
    """Configuration for feature serving"""
    mode: RetrievalMode = RetrievalMode.ONLINE
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    max_batch_size: int = 1000
    timeout_seconds: int = 10


@dataclass
class FeatureRequest:
    """Request for feature retrieval"""
    entity_keys: List[Dict[str, Any]]  # List of entity key dicts
    feature_view_names: List[str]       # Feature views to retrieve
    point_in_time: Optional[datetime] = None  # For time travel


@dataclass
class FeatureResponse:
    """Response from feature retrieval"""
    request_id: str
    features: Dict[str, List[FeatureRow]]  # feature_view_name -> rows
    metadata: Dict[str, Any]
    latency_ms: float
    cached: bool = False


class OnlineFeatureServing:
    """
    Online Feature Serving

    Provides low-latency feature retrieval for model inference.
    """

    def __init__(self, db: Session):
        self.db = db
        self.feature_service = get_feature_store_service(db)

        # Simulated online store (in production, use Redis/DynamoDB)
        self._online_store: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, Tuple[datetime, Any]] = {}

    def get_features(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        feature_group_id: str,
    ) -> Dict[str, FeatureValue]:
        """
        Get feature values for a single entity

        Args:
            entity_key: Entity key values (e.g., {"user_id": 123})
            feature_names: List of feature names to retrieve
            feature_group_id: Feature group containing the features

        Returns:
            Dict mapping feature names to FeatureValue objects
        """
        # Generate cache key
        cache_key = self._generate_cache_key(entity_key, feature_names, feature_group_id)

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_value = self._cache[cache_key]
            if datetime.utcnow() - cached_time < timedelta(seconds=300):
                return cached_value

        # Fetch features (in production, query from online store like Redis)
        result = {}
        for feature_name in feature_names:
            # Mock retrieval - in production, query from online store
            key = f"{feature_group_id}:{self._dict_to_str(entity_key)}:{feature_name}"
            value = self._online_store.get(key)

            if value:
                result[feature_name] = FeatureValue(
                    feature_name=feature_name,
                    value=value["value"],
                    timestamp=value["timestamp"],
                    is_null=value.get("is_null", False),
                )
            else:
                # Return null for missing features
                result[feature_name] = FeatureValue(
                    feature_name=feature_name,
                    value=None,
                    timestamp=datetime.utcnow(),
                    is_null=True,
                )

        # Cache result
        self._cache[cache_key] = (datetime.utcnow(), result)

        return result

    def get_features_batch(
        self,
        entity_keys: List[Dict[str, Any]],
        feature_names: List[str],
        feature_group_id: str,
    ) -> List[Dict[str, FeatureValue]]:
        """
        Get feature values for multiple entities (batch)

        Args:
            entity_keys: List of entity key dicts
            feature_names: List of feature names to retrieve
            feature_group_id: Feature group containing the features

        Returns:
            List of dicts mapping feature names to FeatureValue objects
        """
        results = []
        for entity_key in entity_keys:
            features = self.get_features(entity_key, feature_names, feature_group_id)
            results.append(features)
        return results

    def write_features(
        self,
        entity_key: Dict[str, Any],
        features: Dict[str, Any],
        feature_group_id: str,
        timestamp: Optional[datetime] = None,
    ) -> bool:
        """
        Write feature values to online store

        Args:
            entity_key: Entity key values
            features: Dict mapping feature names to values
            feature_group_id: Feature group to write to
            timestamp: Feature timestamp (defaults to now)

        Returns:
            True if write successful
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        try:
            for feature_name, value in features.items():
                key = f"{feature_group_id}:{self._dict_to_str(entity_key)}:{feature_name}"
                self._online_store[key] = {
                    "value": value,
                    "timestamp": timestamp,
                    "is_null": value is None,
                }

            # Invalidate cache
            cache_key = self._generate_cache_key(entity_key, list(features.keys()), feature_group_id)
            self._cache.pop(cache_key, None)

            return True
        except Exception as e:
            logger.error(f"Failed to write features: {e}")
            return False

    def _generate_cache_key(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        feature_group_id: str,
    ) -> str:
        """Generate cache key for features"""
        entity_str = self._dict_to_str(entity_key)
        features_str = ",".join(sorted(feature_names))
        return f"{feature_group_id}:{entity_str}:{features_str}"

    def _dict_to_str(self, d: Dict[str, Any]) -> str:
        """Convert dict to sorted string representation"""
        return json.dumps(d, sort_keys=True)


class OfflineFeatureServing:
    """
    Offline Feature Serving

    Provides batch feature retrieval from data warehouse.
    """

    def __init__(self, db: Session):
        self.db = db
        self.feature_service = get_feature_store_service(db)

    def get_training_dataset(
        self,
        feature_view_id: str,
        entity_keys: Optional[List[Dict[str, Any]]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> FeatureSetResult:
        """
        Get training dataset from feature store

        Args:
            feature_view_id: Feature view to retrieve
            entity_keys: Optional list of entity keys to filter
            start_time: Start time for time range
            end_time: End time for time range

        Returns:
            FeatureSetResult with rows and metadata
        """
        feature_view = self.feature_service.get_feature_view(feature_view_id)
        if not feature_view:
            raise ValueError(f"Feature view not found: {feature_view_id}")

        # In production, this would query the data warehouse
        # For now, return mock result
        rows = []
        if entity_keys:
            for i, entity_key in enumerate(entity_keys):
                # Mock row
                features = {}
                for feature_id in feature_view.feature_ids[:5]:  # Limit for demo
                    features[f"feature_{feature_id[:8]}"] = FeatureValue(
                        feature_name=f"feature_{feature_id[:8]}",
                        value=i * 1.5,  # Mock value
                        timestamp=datetime.utcnow(),
                        is_null=False,
                    )
                rows.append(FeatureRow(
                    entity_key=entity_key,
                    features=features,
                    event_timestamp=datetime.utcnow(),
                ))

        return FeatureSetResult(
            feature_set_id=feature_view_id,
            rows=rows,
            metadata={
                "feature_view_name": feature_view.name,
                "row_count": len(rows),
                "feature_count": len(feature_view.feature_ids),
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
            },
        )

    def get_historical_features(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        feature_group_id: str,
        timestamp: datetime,
    ) -> Dict[str, FeatureValue]:
        """
        Get historical feature values (time travel)

        Args:
            entity_key: Entity key values
            feature_names: List of feature names
            feature_group_id: Feature group to query
            timestamp: Point in time for feature values

        Returns:
            Dict mapping feature names to FeatureValue objects
        """
        # In production, query warehouse with time travel
        # For now, return mock values
        result = {}
        for feature_name in feature_names:
            result[feature_name] = FeatureValue(
                feature_name=feature_name,
                value=None,  # Would be actual historical value
                timestamp=timestamp,
                is_null=True,  # Mock null
            )
        return result

    def point_in_time_join(
        self,
        entity_keys: List[Dict[str, Any]],
        feature_group_ids: List[str],
        event_timestamps: List[datetime],
    ) -> List[FeatureRow]:
        """
        Perform point-in-time join for multiple feature groups

        This is a critical operation for creating training data that
        avoids data leakage by using feature values as they were
        at each event timestamp.

        Args:
            entity_keys: List of entity keys
            feature_group_ids: Feature groups to join
            event_timestamps: Event timestamp for each entity

        Returns:
            List of FeatureRows with point-in-time correct features
        """
        results = []

        for i, (entity_key, event_time) in enumerate(zip(entity_keys, event_timestamps)):
            features = {}

            # Get features from each group as of event_time
            for group_id in feature_group_ids:
                # Mock: get feature names for group
                group = self.feature_service.get_feature_group(group_id)
                if group:
                    group_features = self.feature_service.list_features(
                        feature_group_id=group_id,
                        limit=10,
                    )
                    for feature in group_features:
                        features[feature.name] = FeatureValue(
                            feature_name=feature.name,
                            value=i * 1.0,  # Mock value
                            timestamp=event_time,
                            is_null=False,
                        )

            results.append(FeatureRow(
                entity_key=entity_key,
                features=features,
                event_timestamp=event_time,
            ))

        return results


class FeatureServingService:
    """
    Unified Feature Serving Service

    Combines online and offline serving capabilities.
    """

    def __init__(self, db: Session):
        self.db = db
        self.online = OnlineFeatureServing(db)
        self.offline = OfflineFeatureServing(db)

    def serve_features(
        self,
        request: FeatureRequest,
        config: Optional[ServingConfig] = None,
    ) -> FeatureResponse:
        """
        Serve features based on request configuration

        Args:
            request: Feature request with entity keys and feature views
            config: Optional serving configuration

        Returns:
            FeatureResponse with requested features
        """
        start_time = datetime.utcnow()
        request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        config = config or ServingConfig()

        # Determine serving mode
        mode = config.mode

        results = {}
        cached = False

        if mode in (RetrievalMode.ONLINE, RetrievalMode.HYBRID):
            # Try online first
            for view_name in request.feature_view_names:
                view = self.db.query(FeatureView).filter(
                    FeatureView.name == view_name
                ).first()

                if view:
                    # Get features for each entity
                    rows = []
                    for entity_key in request.entity_keys:
                        # Get feature IDs from view
                        features = self.online.get_features(
                            entity_key=entity_key,
                            feature_names=view.feature_ids[:10],  # Limit for demo
                            feature_group_id=str(view.feature_group_id),
                        )

                        # Convert to FeatureRow format
                        feature_dict = {}
                        for fname, fval in features.items():
                            feature_dict[fname] = fval

                        rows.append(FeatureRow(
                            entity_key=entity_key,
                            features=feature_dict,
                        ))

                    results[view_name] = rows

        if mode == RetrievalMode.OFFLINE or (mode == RetrievalMode.HYBRID and not results):
            # Fall back to offline
            for view_name in request.feature_view_names:
                view = self.db.query(FeatureView).filter(
                    FeatureView.name == view_name
                ).first()

                if view:
                    dataset = self.offline.get_training_dataset(
                        feature_view_id=str(view.id),
                        entity_keys=request.entity_keys,
                    )
                    results[view_name] = dataset.rows

        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        return FeatureResponse(
            request_id=request_id,
            features=results,
            metadata={
                "mode": mode.value,
                "entity_count": len(request.entity_keys),
                "feature_view_count": len(request.feature_view_names),
            },
            latency_ms=latency_ms,
            cached=cached,
        )

    def get_feature_service_endpoint(
        self,
        service_name: str,
    ) -> Optional[str]:
        """Get the endpoint URL for a feature service"""
        service = self.db.query(FeatureService).filter(
            FeatureService.name == service_name
        ).first()

        if service:
            return service.endpoint_path
        return None


def get_feature_serving_service(db: Session) -> FeatureServingService:
    """Get the feature serving service instance"""
    return FeatureServingService(db)
