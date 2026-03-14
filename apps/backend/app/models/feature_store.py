"""
Feature Store Models

Provides models for managing feature definitions, storage, and serving.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, JSON,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.core.database import Base


class FeatureGroup(Base):
    """
    Feature Group - A collection of related features

    Feature groups are logical groupings of features that are computed
    and stored together. They serve as the primary unit of organization
    in the feature store.
    """
    __tablename__ = "feature_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Feature group configuration
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)
    primary_keys = Column(JSONB, default=list)  # List of primary key column names

    # Storage configuration
    store_type = Column(String(50), default="offline")  # offline, online, hybrid
    offline_table_name = Column(String(255))  # For offline storage (e.g., Snowflake table)
    online_table_name = Column(String(255))  # For online storage (e.g., Redis)

    # Time travel / versioning
    enable_time_travel = Column(Boolean, default=True)
    time_travel_granularity = Column(String(50), default="day")  # hour, day, week

    # Data source
    source_type = Column(String(50))  # sql, dataframe, streaming, batch
    source_config = Column(JSONB)  # Connection info, query, etc.

    # Schedule
    schedule_cron = Column(String(100))  # For batch updates

    # Status
    status = Column(String(50), default="active")  # active, disabled, archived
    version = Column(Integer, default=1)

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_refresh_at = Column(DateTime)

    # Statistics
    feature_count = Column(Integer, default=0)
    row_count = Column(Integer, default=0)
    storage_size_bytes = Column(Float, default=0)

    __table_args__ = (
        Index("ix_feature_groups_owner", "owner_id"),
        Index("ix_feature_groups_project", "project_id"),
        Index("ix_feature_groups_status", "status"),
    )

    # Relationships
    features = relationship("Feature", back_populates="feature_group", cascade="all, delete-orphan")
    feature_views = relationship("FeatureView", back_populates="feature_group")


class Feature(Base):
    """
    Feature - Individual feature definition

    A feature represents a measurable property or attribute of an entity.
    Features are the basic building blocks of the feature store.
    """
    __tablename__ = "features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)

    # Grouping
    feature_group_id = Column(UUID(as_uuid=True), ForeignKey("feature_groups.id"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True)

    # Feature type
    data_type = Column(String(50), nullable=False)  # int, float, string, bool, array, vector
    feature_type = Column(String(50))  # continuous, categorical, ordinal, timestamp, text

    # Value constraints
    value_type = Column(String(50))  # numerical, categorical, embedding
    dimension = Column(Integer)  # For vectors/embeddings

    # Validation
    validation_config = Column(JSONB)  # Min, max, allowed values, etc.

    # Transformation
    transformation = Column(String(255))  # Name of transformation function
    transformation_config = Column(JSONB)

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Status
    status = Column(String(50), default="active")  # active, deprecated, archived
    version = Column(Integer, default=1)

    # Statistics
    null_count = Column(Integer, default=0)
    null_percentage = Column(Float, default=0)
    unique_count = Column(Integer)
    min_value = Column(Float)
    max_value = Column(Float)
    mean_value = Column(Float)
    std_value = Column(Float)
    histogram = Column(JSONB)  # Histogram data for visualization

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("feature_group_id", "name", "version", name="uq_feature_group_name_version"),
        Index("ix_features_feature_group", "feature_group_id"),
        Index("ix_features_entity", "entity_id"),
        Index("ix_features_status", "status"),
    )

    # Relationships
    feature_group = relationship("FeatureGroup", back_populates="features")


class Entity(Base):
    """
    Entity - A business entity that features describe

    Entities represent the core objects in the domain, such as users,
    products, transactions, etc. Features are always associated with an entity.
    """
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Entity type
    entity_type = Column(String(50))  # user, product, transaction, session, etc.

    # Join keys for this entity
    join_keys = Column(JSONB, default=list)  # List of key column names

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    feature_groups = relationship("FeatureGroup", foreign_keys=[FeatureGroup.entity_id])
    features = relationship("Feature", foreign_keys=[Feature.entity_id])


class FeatureView(Base):
    """
    Feature View - A logical view over one or more feature groups

    Feature views allow combining features from multiple feature groups
    and applying transformations before serving.
    """
    __tablename__ = "feature_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Feature group associations
    feature_group_id = Column(UUID(as_uuid=True), ForeignKey("feature_groups.id"), nullable=False)
    feature_ids = Column(JSONB, default=list)  # List of feature IDs to include

    # View configuration
    view_type = Column(String(50), default="selection")  # selection, transformation, join
    transformation_sql = Column(Text)
    transformation_config = Column(JSONB)

    # Serving configuration
    serving_mode = Column(String(50), default="online")  # online, offline, both
    ttl_seconds = Column(Integer, default=86400)  # Time to live for cached results

    # Status
    status = Column(String(50), default="active")  # active, disabled, archived
    version = Column(Integer, default=1)

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_feature_views_group", "feature_group_id"),
        Index("ix_feature_views_owner", "owner_id"),
        Index("ix_feature_views_status", "status"),
    )

    # Relationships
    feature_group = relationship("FeatureGroup", back_populates="feature_views")


class FeatureService(Base):
    """
    Feature Service - An API endpoint for serving features

    Feature services expose feature views through APIs for model inference
    and other serving scenarios.
    """
    __tablename__ = "feature_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Associated feature views
    feature_view_ids = Column(JSONB, default=list)  # List of feature view IDs

    # Serving configuration
    endpoint_path = Column(String(255))  # API endpoint path
    serving_type = Column(String(50), default="low_latency")  # low_latency, batch, streaming

    # Performance
    max_qps = Column(Integer, default=1000)
    target_p95_latency_ms = Column(Integer, default=50)

    # Caching
    enable_cache = Column(Boolean, default=True)
    cache_ttl_seconds = Column(Integer, default=300)

    # Monitoring
    enable_monitoring = Column(Boolean, default=True)
    alert_config = Column(JSONB)

    # Deployment
    deployment_status = Column(String(50), default="draft")  # draft, deployed, archived
    deployment_config = Column(JSONB)

    # Status
    status = Column(String(50), default="active")  # active, disabled

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deployed_at = Column(DateTime)

    # Statistics
    total_requests = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0)
    p95_latency_ms = Column(Float, default=0)
    p99_latency_ms = Column(Float, default=0)

    __table_args__ = (
        Index("ix_feature_services_owner", "owner_id"),
        Index("ix_feature_services_status", "status"),
        Index("ix_feature_services_deployment", "deployment_status"),
    )


class FeatureSet(Base):
    """
    Feature Set - A versioned collection of features for training

    Feature sets represent a specific snapshot of features for model training.
    They enable reproducibility by capturing exact feature values at a point in time.
    """
    __tablename__ = "feature_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255))
    description = Column(Text)

    # Associated feature views
    feature_view_ids = Column(JSONB, default=list)

    # Snapshot info
    snapshot_time = Column(DateTime, nullable=False)
    snapshot_id = Column(String(255), unique=True)

    # Training data
    training_data_path = Column(String(500))  # Path to training dataset
    row_count = Column(Integer, default=0)
    feature_count = Column(Integer, default=0)

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Status
    status = Column(String(50), default="active")  # active, archived

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("name", "snapshot_id", name="uq_feature_set_snapshot"),
        Index("ix_feature_sets_owner", "owner_id"),
        Index("ix_feature_sets_snapshot", "snapshot_time"),
    )
