"""
AutoML Models

Provides models for automated machine learning experiments.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class AutoMLExperiment(Base):
    """
    AutoML Experiment - Container for automated ML runs
    """
    __tablename__ = "automl_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255))
    description = Column(Text)

    # Problem definition
    problem_type = Column(String(50), nullable=False)  # classification, regression, clustering, timeseries
    target_column = Column(String(255), nullable=False)
    feature_columns = Column(JSONB, default=list)

    # Data source
    source_type = Column(String(50))  # file, table, query, feature_view
    source_config = Column(JSONB)

    # Evaluation
    eval_metric = Column(String(50))  # accuracy, f1, auc, mse, mae, r2
    cv_folds = Column(Integer, default=5)
    test_split = Column(Float, default=0.2)
    random_seed = Column(Integer, default=42)

    # Search configuration
    search_algorithm = Column(String(50), default="random")  # random, bayesian, genetic, grid
    max_trials = Column(Integer, default=10)
    max_time_minutes = Column(Integer, default=60)

    # Model candidates
    model_types = Column(JSONB, default=list)  # xgboost, lightgbm, random_forest, linear, etc.

    # Feature engineering
    enable_auto_feature_engineering = Column(Boolean, default=True)
    feature_engineering_config = Column(JSONB)

    # Early stopping
    enable_early_stopping = Column(Boolean, default=True)
    early_stopping_patience = Column(Integer, default=10)
    early_stopping_min_delta = Column(Float, default=0.001)

    # Status
    status = Column(String(50), default="draft")  # draft, running, completed, failed, cancelled
    progress = Column(Float, default=0)

    # Results
    best_model_id = Column(UUID(as_uuid=True), ForeignKey("automl_models.id"), nullable=True)
    best_score = Column(Float)
    best_trial_number = Column(Integer)

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    __table_args__ = (
        Index("ix_automl_experiments_owner", "owner_id"),
        Index("ix_automl_experiments_status", "status"),
        Index("ix_automl_experiments_problem", "problem_type"),
    )

    # Relationships
    trials = relationship("AutoMLTrial", back_populates="experiment", cascade="all, delete-orphan")
    best_model_obj = relationship("AutoMLModel", foreign_keys=[best_model_id])


class AutoMLTrial(Base):
    """
    AutoML Trial - Single training run in an experiment
    """
    __tablename__ = "automl_trials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("automl_experiments.id"), nullable=False)
    trial_number = Column(Integer, nullable=False)

    # Model configuration
    model_type = Column(String(100), nullable=False)  # xgboost.XGBClassifier, etc.
    model_config = Column(JSONB, nullable=False)

    # Hyperparameters
    hyperparameters = Column(JSONB, nullable=False)

    # Feature engineering
    feature_pipeline = Column(JSONB)  # Steps applied to features
    selected_features = Column(JSONB, default=list)

    # Training results
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Float)

    # Metrics
    train_score = Column(Float)
    val_score = Column(Float)
    test_score = Column(Float)

    # Additional metrics
    metrics = Column(JSONB, default=dict)

    # Artifacts
    model_path = Column(String(500))
    feature_importance = Column(JSONB)

    # Error info
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_automl_trials_experiment", "experiment_id"),
        Index("ix_automl_trials_status", "status"),
        Index("ix_automl_trials_score", "val_score"),
    )

    # Relationships
    experiment = relationship("AutoMLExperiment", back_populates="trials")


class AutoMLModel(Base):
    """
    AutoML Model - Trained model from AutoML
    """
    __tablename__ = "automl_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(Integer, default=1)

    # Source
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("automl_experiments.id"), nullable=True)
    trial_id = Column(UUID(as_uuid=True), ForeignKey("automl_trials.id"), nullable=True)

    # Model info
    model_type = Column(String(100), nullable=False)
    problem_type = Column(String(50), nullable=False)
    target_column = Column(String(255), nullable=False)

    # Model artifacts
    model_path = Column(String(500), nullable=False)
    model_format = Column(String(50))  # pickle, joblib, onnx, mlflow

    # Feature info
    feature_names = Column(JSONB, nullable=False)
    feature_importance = Column(JSONB)

    # Performance
    metrics = Column(JSONB, default=dict)

    # Deployment
    deployment_status = Column(String(50), default="none")  # none, staging, production
    deployment_endpoint = Column(String(500))

    # Status
    status = Column(String(50), default="trained")  # training, trained, deployed, archived

    # Metadata
    tags = Column(JSONB, default=list)
    properties = Column(JSONB, default=dict)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_automl_models_experiment", "experiment_id"),
        Index("ix_automl_models_owner", "owner_id"),
        Index("ix_automl_models_status", "status"),
        Index("ix_automl_models_deployment", "deployment_status"),
    )


class FeatureConfig(Base):
    """
    Feature Configuration - Auto feature engineering settings
    """
    __tablename__ = "feature_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Feature types to generate
    enable_polynomial = Column(Boolean, default=False)
    enable_interactions = Column(Boolean, default=False)
    polynomial_degree = Column(Integer, default=2)
    max_interactions = Column(Integer, default=3)

    # Scaling and encoding
    scaling_method = Column(String(50))  # standard, minmax, robust, none
    encoding_method = Column(String(50))  # onehot, label, target, none

    # Feature selection
    selection_method = Column(String(50))  # variance, kbest, rfe, none
    max_features = Column(Integer)

    # Dimensionality reduction
    enable_pca = Column(Boolean, default=False)
    pca_variance_ratio = Column(Float, default=0.95)

    # Time series specific
    enable_lag_features = Column(Boolean, default=False)
    lag_steps = Column(JSONB, default=list)
    enable_rolling_features = Column(Boolean, default=False)
    rolling_windows = Column(JSONB, default=list)

    # Text features
    enable_tfidf = Column(Boolean, default=False)
    max_features_tfidf = Column(Integer, default=1000)
    ngram_range = Column(JSONB, default=[1, 1])

    # Status
    status = Column(String(50), default="active")

    # Metadata
    tags = Column(JSONB, default=list)

    # Ownership
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_feature_configs_owner", "owner_id"),
    )


class HyperparameterSearch(Base):
    """
    Hyperparameter Search Space Definition
    """
    __tablename__ = "hyperparameter_search"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    model_type = Column(String(100), nullable=False)

    # Search space
    search_space = Column(JSONB, nullable=False)  # JSON structure defining hyperparameter ranges

    # Constraints
    constraints = Column(JSONB, default=dict)

    # Metadata
    description = Column(Text)
    tags = Column(JSONB, default=list)

    # Status
    status = Column(String(50), default="active")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_hyperparameter_search_model", "model_type"),
    )
