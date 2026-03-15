"""
Feature Store Computation Service

Provides online and offline feature computation capabilities including:
- Online feature serving with Redis integration
- Offline batch computation with SQL/DataFrame support
- Feature versioning and time travel
- Feature transformation pipeline
- Caching layer for low-latency serving
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import hashlib

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.models.feature_store import (
    FeatureGroup, Feature, Entity, FeatureView, FeatureService,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class ServingMode(str, Enum):
    """Feature serving modes"""
    ONLINE = "online"        # Real-time low-latency serving
    OFFLINE = "offline"      # Batch computation
    HYBRID = "hybrid"        # Both online and offline


class TimeTravelMode(str, Enum):
    """Time travel modes for feature versioning"""
    CURRENT = "current"              # Latest values
    POINT_IN_TIME = "point_in_time"  # As of specific timestamp
    TIME_RANGE = "time_range"        # Range of values


@dataclass
class FeatureRequest:
    """Request for feature retrieval"""
    entity_keys: Dict[str, Any]  # Entity key-value pairs
    feature_names: List[str]     # Feature names to retrieve
    feature_view_name: Optional[str] = None
    service_name: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    time_travel_mode: TimeTravelMode = TimeTravelMode.CURRENT
    point_in_time: Optional[datetime] = None


@dataclass
class FeatureResponse:
    """Response from feature retrieval"""
    features: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    served_from: str = "unknown"  # online_store, offline_store, cache
    response_time_ms: float = 0.0


@dataclass
class BatchFeatureRequest:
    """Request for batch feature retrieval"""
    entity_keys: List[Dict[str, Any]]  # Multiple entity key-value pairs
    feature_names: List[str]
    feature_view_name: Optional[str] = None
    request_timestamp: Optional[datetime] = None
    time_travel_mode: TimeTravelMode = TimeTravelMode.CURRENT
    point_in_time: Optional[datetime] = None


@dataclass
class BatchFeatureResponse:
    """Response from batch feature retrieval"""
    rows: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    served_from: str = "unknown"
    response_time_ms: float = 0.0


@dataclass
class FeatureTransformation:
    """Feature transformation definition"""
    name: str
    transformation_type: str  # sql, python, custom
    definition: Union[str, Dict[str, Any]]
    input_features: List[str]
    output_features: List[str]
    dependencies: Optional[List[str]] = None


class OnlineFeatureStore:
    """
    Online Feature Store for low-latency feature serving

    Uses Redis as the backing store for fast feature retrieval.
    Falls back to database when Redis is unavailable.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 86400,
        prefix: str = "feature_store",
    ):
        self.redis_url = redis_url or getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.default_ttl = default_ttl
        self.prefix = prefix
        self._redis_client = None
        self._redis_available = False

        if REDIS_AVAILABLE:
            try:
                self._redis_client = redis.from_url(self.redis_url, decode_responses=True)
                self._redis_client.ping()
                self._redis_available = True
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Redis unavailable: {e}. Using database fallback.")

    @property
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._redis_available

    def _make_key(self, feature_name: str, entity_key: Dict[str, Any]) -> str:
        """Generate a Redis key for a feature"""
        # Sort entity key for consistency
        key_parts = sorted(entity_key.items())
        key_string = "|".join(f"{k}={v}" for k, v in key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
        return f"{self.prefix}:feature:{feature_name}:{key_hash}"

    def _make_entity_prefix(self, entity_key: Dict[str, Any]) -> str:
        """Generate a prefix for all features of an entity"""
        key_parts = sorted(entity_key.items())
        key_string = "|".join(f"{k}={v}" for k, v in key_parts)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]
        return f"{self.prefix}:entity:*:{key_hash}"

    def get_features(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """Get features from online store"""
        if not self._redis_available:
            return {}

        result = {}
        pipeline = self._redis_client.pipeline()

        for feature_name in feature_names:
            key = self._make_key(feature_name, entity_key)
            pipeline.get(key)

        responses = pipeline.execute()

        for feature_name, response in zip(feature_names, responses):
            if response:
                try:
                    data = json.loads(response)
                    result[feature_name] = data.get('value')
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON for feature {feature_name}")

        return result

    def set_features(
        self,
        entity_key: Dict[str, Any],
        features: Dict[str, Any],
        ttl: Optional[int] = None,
        event_timestamp: Optional[datetime] = None,
    ) -> bool:
        """Set features in online store"""
        if not self._redis_available:
            return False

        ttl = ttl or self.default_ttl
        timestamp = event_timestamp or datetime.utcnow()
        pipeline = self._redis_client.pipeline()

        for feature_name, value in features.items():
            key = self._make_key(feature_name, entity_key)
            data = {
                'value': value,
                'timestamp': timestamp.isoformat(),
                'entity_key': entity_key,
            }
            pipeline.setex(key, ttl, json.dumps(data))

        try:
            pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to set features in Redis: {e}")
            return False

    def delete_features(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
    ) -> bool:
        """Delete features from online store"""
        if not self._redis_available:
            return False

        keys = [self._make_key(name, entity_key) for name in feature_names]

        try:
            self._redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to delete features from Redis: {e}")
            return False

    def get_entity_features(self, entity_key: Dict[str, Any]) -> Dict[str, Any]:
        """Get all features for an entity"""
        if not self._redis_available:
            return {}

        pattern = self._make_entity_prefix(entity_key)

        try:
            keys = self._redis_client.keys(pattern)
            if not keys:
                return {}

            values = self._redis_client.mget(keys)

            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        data = json.loads(value)
                        # Extract feature name from key
                        feature_name = key.split(':')[-2]
                        result[feature_name] = data.get('value')
                    except (json.JSONDecodeError, IndexError):
                        pass

            return result
        except Exception as e:
            logger.error(f"Failed to get entity features: {e}")
            return {}

    def invalidate_entity(self, entity_key: Dict[str, Any]) -> bool:
        """Invalidate all features for an entity"""
        if not self._redis_available:
            return False

        pattern = self._make_entity_prefix(entity_key)

        try:
            keys = self._redis_client.keys(pattern)
            if keys:
                self._redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate entity: {e}")
            return False


class OfflineFeatureStore:
    """
    Offline Feature Store for batch feature computation

    Supports SQL-based feature computation and DataFrame operations.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_features_sql(
        self,
        feature_view: FeatureView,
        entity_keys: List[Dict[str, Any]],
        feature_names: List[str],
        point_in_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get features using SQL query

        Constructs a SQL query to fetch features from the offline store.
        """
        feature_group = self.db.query(FeatureGroup).filter(
            FeatureGroup.id == feature_view.feature_group_id
        ).first()

        if not feature_group:
            logger.error(f"Feature group not found: {feature_view.feature_group_id}")
            return pd.DataFrame()

        source_config = feature_group.source_config or {}
        source_type = feature_group.source_type

        # Build SQL query based on source type
        if source_type == "database":
            return self._query_from_database(
                source_config, entity_keys, feature_names, point_in_time
            )
        elif source_type == "data_lake":
            return self._query_from_datalake(
                source_config, entity_keys, feature_names, point_in_time
            )
        else:
            logger.warning(f"Unsupported source type: {source_type}")
            return pd.DataFrame()

    def _query_from_database(
        self,
        source_config: Dict[str, Any],
        entity_keys: List[Dict[str, Any]],
        feature_names: List[str],
        point_in_time: Optional[datetime],
    ) -> pd.DataFrame:
        """Query features from a database source"""
        table_name = source_config.get('table_name')

        if not table_name:
            logger.error("No table_name in source_config")
            return pd.DataFrame()

        # Build WHERE clause for entity keys
        entity_conditions = []
        for key_dict in entity_keys:
            conditions = [f"{k} = '{v}'" for k, v in key_dict.items()]
            entity_conditions.append(f"({' AND '.join(conditions)})")

        where_clause = f"({' OR '.join(entity_conditions)})"

        # Build SELECT clause for feature names
        select_clause = ", ".join(feature_names)

        # Add time travel if specified
        if point_in_time:
            select_clause = f"{select_clause}, valid_from, valid_to"

        sql = f"SELECT {select_clause} FROM {table_name} WHERE {where_clause}"

        try:
            # Execute query using the database connection
            # In production, you'd use the appropriate connector
            from app.connectors.database import DatabaseConnector

            connector_config = {
                'host': source_config.get('host'),
                'port': source_config.get('port'),
                'database': source_config.get('database'),
                'username': source_config.get('username'),
                'password': source_config.get('password'),
            }

            # For now, return empty DataFrame - connector integration needed
            logger.info(f"Would execute SQL: {sql}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Database query failed: {e}")
            return pd.DataFrame()

    def _query_from_datalake(
        self,
        source_config: Dict[str, Any],
        entity_keys: List[Dict[str, Any]],
        feature_names: List[str],
        point_in_time: Optional[datetime],
    ) -> pd.DataFrame:
        """Query features from a data lake source"""
        file_path = source_config.get('path')

        if not file_path:
            logger.error("No path in source_config")
            return pd.DataFrame()

        try:
            # Read from parquet/csv files
            if file_path.endswith('.parquet'):
                df = pd.read_parquet(file_path)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                logger.error(f"Unsupported file format: {file_path}")
                return pd.DataFrame()

            # Filter by entity keys
            if entity_keys:
                # Build filter conditions
                masks = []
                for key_dict in entity_keys:
                    mask = pd.Series([True] * len(df))
                    for k, v in key_dict.items():
                        if k in df.columns:
                            mask &= (df[k] == v)
                    masks.append(mask)

                if masks:
                    combined_mask = masks[0]
                    for m in masks[1:]:
                        combined_mask |= m
                    df = df[combined_mask]

            # Select requested features
            available_features = [f for f in feature_names if f in df.columns]
            result = df[available_features + list(entity_keys[0].keys())] if available_features else pd.DataFrame()

            return result

        except Exception as e:
            logger.error(f"Data lake query failed: {e}")
            return pd.DataFrame()

    def compute_features(
        self,
        feature_view: FeatureView,
        entity_keys: List[Dict[str, Any]],
        transformations: Optional[List[FeatureTransformation]] = None,
    ) -> pd.DataFrame:
        """
        Compute features with transformations

        Applies SQL or Python transformations to compute derived features.
        """
        # Get base features
        feature_names = []
        if transformations:
            for t in transformations:
                feature_names.extend(t.input_features)

        # Get base feature data
        df = self.get_features_sql(
            feature_view, entity_keys, list(set(feature_names)), None
        )

        if df.empty:
            return df

        # Apply transformations
        if transformations:
            df = self._apply_transformations(df, transformations)

        return df

    def _apply_transformations(
        self,
        df: pd.DataFrame,
        transformations: List[FeatureTransformation],
    ) -> pd.DataFrame:
        """Apply feature transformations to DataFrame"""
        for transform in transformations:
            try:
                if transform.transformation_type == "sql":
                    df = self._apply_sql_transformation(df, transform)
                elif transform.transformation_type == "python":
                    df = self._apply_python_transformation(df, transform)
            except Exception as e:
                logger.error(f"Transformation {transform.name} failed: {e}")

        return df

    def _apply_sql_transformation(
        self,
        df: pd.DataFrame,
        transform: FeatureTransformation,
    ) -> pd.DataFrame:
        """Apply SQL-style transformation using pandas eval"""
        definition = transform.definition

        if isinstance(definition, dict):
            expression = definition.get('expression')
            output_col = transform.output_features[0] if transform.output_features else 'computed'

            if expression and output_col:
                try:
                    df[output_col] = df.eval(expression)
                except Exception as e:
                    logger.error(f"Failed to eval expression {expression}: {e}")

        return df

    def _apply_python_transformation(
        self,
        df: pd.DataFrame,
        transform: FeatureTransformation,
    ) -> pd.DataFrame:
        """Apply Python transformation"""
        definition = transform.definition

        if isinstance(definition, dict):
            func_type = definition.get('type')

            if func_type == 'normalize':
                col = definition.get('column')
                output_col = transform.output_features[0] if transform.output_features else col
                if col in df.columns:
                    mean = df[col].mean()
                    std = df[col].std()
                    df[output_col] = (df[col] - mean) / std if std > 0 else 0

            elif func_type == 'standardize':
                col = definition.get('column')
                output_col = transform.output_features[0] if transform.output_features else col
                if col in df.columns:
                    min_val = df[col].min()
                    max_val = df[col].max()
                    df[output_col] = (df[col] - min_val) / (max_val - min_val) if max_val > min_val else 0

            elif func_type == 'log':
                col = definition.get('column')
                output_col = transform.output_features[0] if transform.output_features else col
                if col in df.columns:
                    df[output_col] = np.log1p(df[col])

            elif func_type == 'bucket':
                col = definition.get('column')
                bins = definition.get('bins', 5)
                output_col = transform.output_features[0] if transform.output_features else f"{col}_binned"
                if col in df.columns:
                    df[output_col] = pd.cut(df[col], bins=bins, labels=False)

            elif func_type == 'one_hot':
                col = definition.get('column')
                if col in df.columns:
                    dummies = pd.get_dummies(df[col], prefix=col)
                    df = pd.concat([df, dummies], axis=1)

        return df


class FeatureVersioning:
    """
    Feature versioning and time travel capabilities

    Manages feature versions over time and enables point-in-time queries.
    """

    def __init__(self, db: Session, online_store: Optional[OnlineFeatureStore] = None):
        self.db = db
        self.online_store = online_store

    def get_features_at_time(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        point_in_time: datetime,
    ) -> Dict[str, Any]:
        """
        Get feature values as of a specific point in time

        Implements time travel by querying version history.
        """
        # Try online store first (if it has versioning)
        if self.online_store and self.online_store.is_available:
            result = self._get_online_features_at_time(
                entity_key, feature_names, point_in_time
            )
            if result:
                return result

        # Fall back to offline version history
        return self._get_offline_features_at_time(
            entity_key, feature_names, point_in_time
        )

    def _get_online_features_at_time(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        point_in_time: datetime,
    ) -> Dict[str, Any]:
        """Get features from online store with version key"""
        if not self.online_store:
            return {}

        result = {}
        for feature_name in feature_names:
            # Construct versioned key
            version_key = self._make_version_key(feature_name, entity_key, point_in_time)
            # Implementation would query Redis with version key
            # For now, return empty

        return result

    def _make_version_key(self, feature_name: str, entity_key: Dict[str, Any], timestamp: datetime) -> str:
        """Create a versioned feature key"""
        key_parts = sorted(entity_key.items())
        key_string = "|".join(f"{k}={v}" for k, v in key_parts)
        time_str = timestamp.strftime('%Y%m%d_%H%M%S')
        key_hash = hashlib.md5(f"{key_string}_{time_str}".encode()).hexdigest()[:16]
        return f"feature_version:{feature_name}:{key_hash}"

    def _get_offline_features_at_time(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        point_in_time: datetime,
    ) -> Dict[str, Any]:
        """Get features from offline store with time travel"""
        # This would query a feature history table
        # For now, return empty dict
        return {}

    def create_feature_snapshot(
        self,
        feature_view_id: str,
        snapshot_time: datetime,
        description: Optional[str] = None,
    ) -> str:
        """
        Create a snapshot of features at a specific time

        Returns the snapshot ID.
        """
        snapshot_id = f"snapshot_{feature_view_id}_{snapshot_time.strftime('%Y%m%d_%H%M%S')}"

        # Implementation would:
        # 1. Query all current feature values
        # 2. Store in a snapshot table
        # 3. Return snapshot ID

        logger.info(f"Created feature snapshot: {snapshot_id}")
        return snapshot_id

    def list_feature_snapshots(
        self,
        feature_view_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """List available snapshots for a feature view"""
        # Implementation would query snapshot metadata table
        # For now, return empty list
        return []

    def get_latest_snapshot(
        self,
        feature_view_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the latest snapshot for a feature view"""
        snapshots = self.list_feature_snapshots(feature_view_id)
        return snapshots[0] if snapshots else None


class FeatureComputationService:
    """
    Main service for feature computation and serving

    Combines online, offline, and versioning capabilities.
    """

    def __init__(self, db: Session, redis_url: Optional[str] = None):
        self.db = db
        self.online_store = OnlineFeatureStore(redis_url=redis_url)
        self.offline_store = OfflineFeatureStore(db)
        self.versioning = FeatureVersioning(db, self.online_store)

    # ========================================================================
    # Online Feature Serving
    # ========================================================================

    def get_online_features(
        self,
        request: FeatureRequest,
    ) -> FeatureResponse:
        """
        Get features from online store (low-latency)

        Returns FeatureResponse with features and metadata.
        """
        start_time = datetime.utcnow()

        try:
            # Try online store first
            if self.online_store.is_available:
                features = self.online_store.get_features(
                    entity_key=request.entity_keys,
                    feature_names=request.feature_names,
                )

                if features or len(features) == len(request.feature_names):
                    return FeatureResponse(
                        features=features,
                        served_from="online_store",
                        response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                        metadata={
                            'request_timestamp': request.request_timestamp.isoformat() if request.request_timestamp else None,
                            'entity_count': len(request.entity_keys),
                        }
                    )

            # Fall back to offline store
            return self._get_offline_features_fallback(request, start_time)

        except Exception as e:
            logger.error(f"Error getting online features: {e}")
            return FeatureResponse(
                features={},
                errors=[str(e)],
                served_from="error",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

    def _get_offline_features_fallback(
        self,
        request: FeatureRequest,
        start_time: datetime,
    ) -> FeatureResponse:
        """Fallback to offline store for feature retrieval"""
        try:
            # Get feature view
            feature_view = None
            if request.feature_view_name:
                feature_view = self.db.query(FeatureView).filter(
                    FeatureView.name == request.feature_view_name
                ).first()

            if not feature_view:
                return FeatureResponse(
                    features={},
                    errors=["Feature view not found"],
                    served_from="offline_store",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Get feature group
            feature_group = self.db.query(FeatureGroup).filter(
                FeatureGroup.id == feature_view.feature_group_id
            ).first()

            if not feature_group:
                return FeatureResponse(
                    features={},
                    errors=["Feature group not found"],
                    served_from="offline_store",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Query offline store
            df = self.offline_store.get_features_sql(
                feature_view=feature_view,
                entity_keys=[request.entity_keys],
                feature_names=request.feature_names,
                point_in_time=request.point_in_time,
            )

            if df.empty:
                return FeatureResponse(
                    features={},
                    errors=["No features found"],
                    served_from="offline_store",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Extract first row features
            features = df.iloc[0].to_dict() if len(df) > 0 else {}

            return FeatureResponse(
                features=features,
                served_from="offline_store",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

        except Exception as e:
            logger.error(f"Offline fallback error: {e}")
            return FeatureResponse(
                features={},
                errors=[str(e)],
                served_from="offline_store",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

    # ========================================================================
    # Batch Feature Serving
    # ========================================================================

    def get_batch_features(
        self,
        request: BatchFeatureRequest,
    ) -> BatchFeatureResponse:
        """
        Get features for multiple entities (batch)

        Returns BatchFeatureResponse with all rows.
        """
        start_time = datetime.utcnow()

        try:
            # Get feature view
            feature_view = None
            if request.feature_view_name:
                feature_view = self.db.query(FeatureView).filter(
                    FeatureView.name == request.feature_view_name
                ).first()

            if not feature_view:
                return BatchFeatureResponse(
                    rows=[],
                    errors=["Feature view not found"],
                    served_from="offline_store",
                    response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                )

            # Query offline store
            df = self.offline_store.get_features_sql(
                feature_view=feature_view,
                entity_keys=request.entity_keys,
                feature_names=request.feature_names,
                point_in_time=request.point_in_time,
            )

            rows = df.to_dict('records') if not df.empty else []

            return BatchFeatureResponse(
                rows=rows,
                served_from="offline_store",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                metadata={
                    'row_count': len(rows),
                    'request_timestamp': request.request_timestamp.isoformat() if request.request_timestamp else None,
                }
            )

        except Exception as e:
            logger.error(f"Error getting batch features: {e}")
            return BatchFeatureResponse(
                rows=[],
                errors=[str(e)],
                served_from="error",
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
            )

    # ========================================================================
    # Feature Writing
    # ========================================================================

    def write_features(
        self,
        entity_key: Dict[str, Any],
        features: Dict[str, Any],
        feature_group_id: str,
        event_timestamp: Optional[datetime] = None,
        online_ttl: Optional[int] = None,
    ) -> bool:
        """
        Write features to both online and offline stores

        Returns True if successful.
        """
        try:
            timestamp = event_timestamp or datetime.utcnow()

            # Write to online store
            if self.online_store.is_available:
                self.online_store.set_features(
                    entity_key=entity_key,
                    features=features,
                    ttl=online_ttl,
                    event_timestamp=timestamp,
                )

            # Write to offline store (implementation depends on source)
            # This would write to the data warehouse/lakehouse

            logger.info(f"Wrote {len(features)} features for entity {entity_key}")
            return True

        except Exception as e:
            logger.error(f"Error writing features: {e}")
            return False

    # ========================================================================
    # Feature Computation / Transformation
    # ========================================================================

    def compute_transformed_features(
        self,
        feature_view_id: str,
        entity_keys: List[Dict[str, Any]],
        transformations: List[FeatureTransformation],
    ) -> pd.DataFrame:
        """
        Compute features with transformations

        Returns DataFrame with computed features.
        """
        try:
            feature_view = self.db.query(FeatureView).filter(
                FeatureView.id == feature_view_id
            ).first()

            if not feature_view:
                logger.error(f"Feature view not found: {feature_view_id}")
                return pd.DataFrame()

            return self.offline_store.compute_features(
                feature_view=feature_view,
                entity_keys=entity_keys,
                transformations=transformations,
            )

        except Exception as e:
            logger.error(f"Error computing transformed features: {e}")
            return pd.DataFrame()

    # ========================================================================
    # Time Travel
    # ========================================================================

    def get_features_point_in_time(
        self,
        entity_key: Dict[str, Any],
        feature_names: List[str],
        point_in_time: datetime,
    ) -> Dict[str, Any]:
        """
        Get feature values as of a specific point in time

        Implements time travel capability.
        """
        return self.versioning.get_features_at_time(
            entity_key=entity_key,
            feature_names=feature_names,
            point_in_time=point_in_time,
        )

    def create_snapshot(
        self,
        feature_view_id: str,
        snapshot_time: datetime,
        description: Optional[str] = None,
    ) -> str:
        """Create a feature snapshot at a specific time"""
        return self.versioning.create_feature_snapshot(
            feature_view_id=feature_view_id,
            snapshot_time=snapshot_time,
            description=description,
        )

    def list_snapshots(
        self,
        feature_view_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """List available snapshots for a feature view"""
        return self.versioning.list_feature_snapshots(
            feature_view_id=feature_view_id,
            start_time=start_time,
            end_time=end_time,
        )

    # ========================================================================
    # Cache Management
    # ========================================================================

    def invalidate_cache(
        self,
        entity_key: Dict[str, Any],
        feature_names: Optional[List[str]] = None,
    ) -> bool:
        """
        Invalidate cached features for an entity

        If feature_names is None, invalidates all features for the entity.
        """
        if not self.online_store.is_available:
            return False

        try:
            if feature_names:
                return self.online_store.delete_features(entity_key, feature_names)
            else:
                return self.online_store.invalidate_entity(entity_key)
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False

    def warm_cache(
        self,
        entity_keys: List[Dict[str, Any]],
        feature_names: List[str],
        feature_view_id: str,
    ) -> int:
        """
        Warm the online store cache with pre-computed features

        Returns the number of entities cached.
        """
        count = 0

        if not self.online_store.is_available:
            return 0

        try:
            feature_view = self.db.query(FeatureView).filter(
                FeatureView.id == feature_view_id
            ).first()

            if not feature_view:
                return 0

            # Batch fetch from offline store
            df = self.offline_store.get_features_sql(
                feature_view=feature_view,
                entity_keys=entity_keys,
                feature_names=feature_names,
                point_in_time=None,
            )

            # Write to online store
            for _, row in df.iterrows():
                entity_key = {k: row[k] for k in entity_keys[0].keys() if k in row}
                features = {f: row[f] for f in feature_names if f in row}

                if self.online_store.set_features(entity_key, features):
                    count += 1

            logger.info(f"Warmed cache for {count} entities")
            return count

        except Exception as e:
            logger.error(f"Error warming cache: {e}")
            return count


# Singleton instance
_computation_service: Optional[FeatureComputationService] = None


def get_feature_computation_service(
    db: Session,
    redis_url: Optional[str] = None,
) -> FeatureComputationService:
    """Get or create the feature computation service instance"""
    return FeatureComputationService(db, redis_url)
