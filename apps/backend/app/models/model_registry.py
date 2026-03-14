"""
Model Registry Database Models

Defines database models for registered models, model versions,
model deployments, and related entities.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
    Boolean,
    Float,
    BigInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ModelLifecycleStage(str):
    """Model lifecycle stages"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class ModelFramework(str):
    """Model framework types"""
    SKLEARN = "sklearn"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    HUGGINGFACE = "huggingface"
    ONNX = "onnx"
    CUSTOM = "custom"


class RegisteredModel(Base):
    """
    Registered Model

    Represents a registered model with multiple versions.
    """

    __tablename__ = "registered_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(250), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)  # List of tag strings
    metadata = Column(JSON, nullable=True, default=dict)  # Additional metadata

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User", back_populates="registered_models")
    project = relationship("Project", back_populates="registered_models")
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    deployments = relationship("ModelDeployment", back_populates="model")

    def __repr__(self):
        return f"<RegisteredModel(id={self.id}, name='{self.name}')>"


class ModelVersion(Base):
    """
    Model Version

    Represents a specific version of a registered model.
    """

    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("registered_models.id"), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)

    # Run information
    run_id = Column(String(250), nullable=True, index=True)
    experiment_id = Column(String(250), nullable=True)

    # Model information
    framework = Column(String(50), nullable=False)  # sklearn, tensorflow, etc.
    model_type = Column(String(100), nullable=True)  # classifier, regressor, etc.

    # Artifact information
    artifact_uri = Column(Text, nullable=False)  # MLflow artifact URI
    model_path = Column(String(500), nullable=True)  # Path within artifacts

    # Stage information
    current_stage = Column(
        SQLEnum(
            "development",
            "staging",
            "production",
            "archived",
            name="model_lifecycle_stage"
        ),
        nullable=False,
        default="development",
        index=True,
    )
    description = Column(Text, nullable=True)

    # Model metrics and parameters
    metrics = Column(JSON, nullable=True, default=dict)
    parameters = Column(JSON, nullable=True, default=dict)

    # Size and performance
    model_size_mb = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="ready")  # ready, failed, pending

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    model = relationship("RegisteredModel", back_populates="versions")
    created_by = relationship("User")
    deployments = relationship("ModelDeployment", back_populates="model_version")
    evaluations = relationship("ModelEvaluation", back_populates="model_version")

    # Unique constraint on model_id + version
    __table_args__ = (
        {"name": "uq_model_version", "postgresql_where": "NOT deleted"},
    )

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, model_id={self.model_id}, version='{self.version}', stage='{self.current_stage}')>"


class ModelDeployment(Base):
    """
    Model Deployment

    Represents a deployed model serving instance.
    """

    __tablename__ = "model_deployments"

    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(String(250), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)

    # Model reference
    model_id = Column(Integer, ForeignKey("registered_models.id"), nullable=False, index=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True, index=True)

    # Deployment configuration
    platform = Column(String(50), nullable=False, default="kserve")  # kserve, seldon, custom
    predictor_type = Column(String(50), nullable=False)  # sklearn, tensorflow, pytorch, etc.
    runtime_version = Column(String(100), nullable=True)

    # Deployment mode
    deployment_mode = Column(
        SQLEnum(
            "raw",
            "ab_testing",
            "canary",
            "shadow",
            name="deployment_mode"
        ),
        nullable=False,
        default="raw",
    )

    # Resource configuration
    replicas = Column(Integer, nullable=False, default=1)
    min_replicas = Column(Integer, nullable=True)
    max_replicas = Column(Integer, nullable=True)
    cpu_request = Column(String(50), nullable=True)
    cpu_limit = Column(String(50), nullable=True)
    memory_request = Column(String(50), nullable=True)
    memory_limit = Column(String(50), nullable=True)
    gpu_type = Column(String(50), nullable=True)
    gpu_count = Column(Integer, nullable=True)

    # Service endpoints
    namespace = Column(String(250), nullable=False, default="default")
    endpoint = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=True)

    # Autoscaling
    autoscaling_enabled = Column(Boolean, nullable=False, default=False)
    target_requests_per_second = Column(Integer, nullable=True)
    scale_to_zero_enabled = Column(Boolean, nullable=False, default=False)

    # Status
    status = Column(
        SQLEnum(
            "pending",
            "deploying",
            "running",
            "updating",
            "failed",
            "stopped",
            "unknown",
            name="deployment_status"
        ),
        nullable=False,
        default="pending",
        index=True,
    )
    status_message = Column(Text, nullable=True)

    # Canary/AB testing configuration
    canary_config = Column(JSON, nullable=True)  # Canary deployment settings
    ab_test_config = Column(JSON, nullable=True)  # A/B test variants and traffic split

    # Traffic distribution (for AB testing/canary)
    traffic_distribution = Column(JSON, nullable=True)  # {"variant1": 50, "variant2": 50}

    # Monitoring
    enable_logging = Column(Boolean, nullable=False, default=True)
    log_url = Column(String(1000), nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    stopped_at = Column(DateTime, nullable=True)

    # Relationships
    model = relationship("RegisteredModel", back_populates="deployments")
    model_version = relationship("ModelVersion", back_populates="deployments")
    created_by = relationship("User")
    project = relationship("Project")

    def __repr__(self):
        return f"<ModelDeployment(id={self.id}, deployment_id='{self.deployment_id}', status='{self.status}')>"


class ModelEvaluation(Base):
    """
    Model Evaluation

    Represents an evaluation run for a model version.
    """

    __tablename__ = "model_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(String(250), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)

    # Model reference
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False, index=True)

    # Dataset information
    dataset_name = Column(String(500), nullable=True)
    dataset_uri = Column(Text, nullable=True)
    dataset_version = Column(String(100), nullable=True)
    data_split = Column(String(50), nullable=False, default="test")  # train, validation, test

    # Evaluation metrics
    metrics = Column(JSON, nullable=False, default=dict)  # All evaluation metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)
    confusion_matrix = Column(JSON, nullable=True)

    # Execution information
    status = Column(String(50), nullable=False, default="completed")  # pending, running, completed, failed
    error_message = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    model_version = relationship("ModelVersion", back_populates="evaluations")

    def __repr__(self):
        return f"<ModelEvaluation(id={self.id}, evaluation_id='{self.evaluation_id}', status='{self.status}')>"


class Experiment(Base):
    """
    Experiment

    Represents an ML experiment for tracking training runs.
    """

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String(250), nullable=False)  # MLflow experiment ID
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Artifact location
    artifact_location = Column(String(1000), nullable=True)

    # Lifecycle
    lifecycle_stage = Column(String(50), nullable=False, default="active")  # active, deleted

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User")
    project = relationship("Project")

    def __repr__(self):
        return f"<Experiment(id={self.id}, experiment_id='{self.experiment_id}', name='{self.name}')>"


class Run(Base):
    """
    Run

    Represents a single training/evaluation run within an experiment.
    """

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(250), unique=True, nullable=False, index=True)
    run_name = Column(String(500), nullable=False)

    # Experiment reference
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    mlflow_run_id = Column(String(250), nullable=True, index=True)  # MLflow run ID

    # Status
    status = Column(String(50), nullable=False, index=True)  # running, completed, failed, scheduled
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Artifact information
    artifact_uri = Column(Text, nullable=True)

    # Hyperparameters
    params = Column(JSON, nullable=False, default=dict)

    # Metrics
    metrics = Column(JSON, nullable=True, default=dict)

    # Tags
    tags = Column(JSON, nullable=True, default=list)

    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)

    # Source
    source_type = Column(String(50), nullable=True)  # training, pipeline, manual
    source_run_id = Column(String(250), nullable=True)  # Triggered by another run

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    experiment = relationship("Experiment")
    created_by = relationship("User")

    def __repr__(self):
        return f"<Run(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"


class HyperparameterSearch(Base):
    """
    Hyperparameter Search

    Represents a hyperparameter optimization run.
    """

    __tablename__ = "hyperparameter_searches"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(String(250), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)

    # Experiment/Model reference
    base_experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("registered_models.id"), nullable=True)

    # Search configuration
    algorithm = Column(String(50), nullable=False, default="optuna")  # optuna, hyperopt, random, grid
    search_space = Column(JSON, nullable=False, default=dict)
    optimization_metric = Column(String(100), nullable=False, default="accuracy")  # Metric to optimize
    optimization_mode = Column(String(20), nullable=False, default="max")  # max or min

    # Search settings
    n_trials = Column(Integer, nullable=False, default=10)
    timeout_minutes = Column(Integer, nullable=True)
    early_stopping_trials = Column(Integer, nullable=True)

    # Execution
    status = Column(String(50, nullable=False, default="created")  # created, running, completed, failed, cancelled
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Best result
    best_trial_id = Column(Integer, nullable=True)
    best_metric_value = Column(Float, nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    base_experiment = relationship("Experiment")
    model = relationship("RegisteredModel")

    def __repr__(self):
        return f"<HyperparameterSearch(id={self.id}, search_id='{self.search_id}', algorithm='{self.algorithm}')>"


class HyperparameterTrial(Base):
    """
    Hyperparameter Trial

    Represents a single trial in a hyperparameter search.
    """

    __tablename__ = "hyperparameter_trials"

    id = Column(Integer, primary_key=True, index=True)
    trial_id = Column(String(250), nullable=False, index=True)
    trial_number = Column(Integer, nullable=False)

    # Search reference
    search_id = Column(Integer, ForeignKey("hyperparameter_searches.id"), nullable=False, index=True)

    # Hyperparameters
    params = Column(JSON, nullable=False, default=dict)

    # Metrics
    metrics = Column(JSON, nullable=True, default=dict)
    objective_value = Column(Float, nullable=False)

    # Status
    status = Column(String(50, nullable=False, default="running")  # running, completed, failed, pruned
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Artifacts
    run_id = Column(String(250), nullable=True)  # Associated training run
    artifact_uri = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    search = relationship("HyperparameterSearch")

    def __repr__(self):
        return f"<HyperparameterTrial(id={self.id}, trial_id='{self.trial_id}', status='{self.status}')>"
