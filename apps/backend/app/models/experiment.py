"""
Experiment Tracking Models

SQLAlchemy models for MLflow experiments, runs, metrics, and artifacts.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Experiment(Base):
    """
    MLflow Experiment model

    Experiments are the top-level organizational unit for ML runs.
    """
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    # MLflow experiment_id (string in MLflow, stored as string here too)
    experiment_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    artifact_location = Column(String(512), nullable=True)
    lifecycle_stage = Column(String(32), default="active")

    # Organization
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Tags stored as JSON
    tags = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    runs = relationship("Run", back_populates="experiment", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Experiment(id={self.id}, name={self.name})>"


class Run(Base):
    """
    MLflow Run model

    Runs represent a single execution of an ML model training or evaluation.
    """
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    # MLflow run_id (UUID)
    run_id = Column(String(64), unique=True, nullable=False, index=True)
    run_uuid = Column(String(64), unique=True, nullable=False)
    run_name = Column(String(256), nullable=True)

    # Foreign key to experiment
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)

    # Run status
    status = Column(String(32), default="running")  # running, completed, failed, killed, scheduled
    lifecycle_stage = Column(String(32), default="active")

    # Execution info
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Artifacts
    artifact_uri = Column(String(512), nullable=True)

    # Source info
    source_type = Column(String(64), nullable=True)  # NOTEBOOK, JOB, PROJECT, LOCAL
    source_name = Column(String(256), nullable=True)
    entry_point_name = Column(String(64), nullable=True)

    # Git info
    git_commit = Column(String(64), nullable=True)
    git_branch = Column(String(256), nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="runs")
    params = relationship("RunParam", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("RunMetric", back_populates="run", cascade="all, delete-orphan")
    tags = relationship("RunTag", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_runs_experiment_start", "experiment_id", "start_time"),
        Index("ix_runs_status", "status"),
    )

    def __repr__(self):
        return f"<Run(id={self.id}, run_id={self.run_id}, status={self.status})>"


class RunParam(Base):
    """
    Run parameters (hyperparameters, config, etc.)
    """
    __tablename__ = "run_params"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    key = Column(String(256), nullable=False)
    value = Column(String(500), nullable=True)

    # Relationships
    run = relationship("Run", back_populates="params")

    __table_args__ = (
        Index("ix_run_params_run_key", "run_id", "key"),
    )

    def __repr__(self):
        return f"<RunParam(id={self.id}, key={self.key}, value={self.value})>"


class RunMetric(Base):
    """
    Run metrics (loss, accuracy, etc.)
    """
    __tablename__ = "run_metrics"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    key = Column(String(256), nullable=False)
    value = Column(Float, nullable=True)
    step = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # For tracking history
    is_nan = Column(Integer, default=0)  # 1 if value is NaN

    # Relationships
    run = relationship("Run", back_populates="metrics")

    __table_args__ = (
        Index("ix_run_metrics_run_key_step", "run_id", "key", "step"),
        Index("ix_run_metrics_run_timestamp", "run_id", "timestamp"),
    )

    def __repr__(self):
        return f"<RunMetric(id={self.id}, key={self.key}, value={self.value}, step={self.step})>"


class RunTag(Base):
    """
    Run tags (metadata for organization and search)
    """
    __tablename__ = "run_tags"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    key = Column(String(256), nullable=False)
    value = Column(String(500), nullable=True)

    # Relationships
    run = relationship("Run", back_populates="tags")

    __table_args__ = (
        Index("ix_run_tags_run_key", "run_id", "key"),
    )

    def __repr__(self):
        return f"<RunTag(id={self.id}, key={self.key}, value={self.value})>"


class Artifact(Base):
    """
    Artifacts (models, plots, data files, etc.)
    """
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    path = Column(String(512), nullable=False)  # Path within artifact URI
    artifact_type = Column(String(64), nullable=True)  # model, plot, data, other

    # File info
    is_dir = Column(Integer, default=0)  # 1 if directory
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Metadata
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("Run", back_populates="artifacts")

    __table_args__ = (
        Index("ix_artifacts_run_path", "run_id", "path"),
        Index("ix_artifacts_type", "artifact_type"),
    )

    def __repr__(self):
        return f"<Artifact(id={self.id}, path={self.path}, type={self.artifact_type})>"


class ModelVersion(Base):
    """
    Registered model versions

    Tracks models registered from runs for deployment.
    """
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)  # Model name
    version = Column(Integer, nullable=False)  # Version number

    # Source run
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)
    artifact_path = Column(String(512), nullable=True)  # Path to model artifact

    # Model info
    description = Column(Text, nullable=True)
    model_type = Column(String(64), nullable=True)  # sklearn, pytorch, tensorflow, etc.
    framework_version = Column(String(64), nullable=True)

    # Deployment stage
    stage = Column(String(32), default="None")  # Staging, Production, Archived, None

    # Metadata
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Creator
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("ix_model_versions_name_version", "name", "version", unique=True),
        Index("ix_model_versions_stage", "stage"),
    )

    def __repr__(self):
        return f"<ModelVersion(id={self.id}, name={self.name}, version={self.version})>"


class RegisteredModel(Base):
    """
    Registered model metadata

    Top-level container for model versions.
    """
    __tablename__ = "registered_models"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Organization
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Tags stored as JSON
    tags = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    versions = relationship("ModelVersion", back_populates="registered_model")

    def __repr__(self):
        return f"<RegisteredModel(id={self.id}, name={self.name})>"


class ModelDeployment(Base):
    """
    Model deployment metadata

    Tracks deployed inference services (KServe, Seldon, etc.).
    """
    __tablename__ = "model_deployments"

    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)

    # Model reference
    model_name = Column(String(256), nullable=False)
    model_version = Column(String(64), nullable=False)
    model_uri = Column(String(512), nullable=True)

    # Deployment configuration
    framework = Column(String(64), nullable=True)  # sklearn, pytorch, tensorflow, xgboost, etc.
    predictor_type = Column(String(64), default="sklearn")  # sklearn, pytorch, tensorflow, custom
    runtime_version = Column(String(64), nullable=True)

    # Resource configuration
    replicas = Column(Integer, default=1)
    gpu_enabled = Column(Integer, default=0)  # 0 or 1
    gpu_type = Column(String(64), nullable=True)  # nvidia.com/gpu, nvidia.com/a100, etc.
    gpu_count = Column(Integer, default=0)

    # Resource limits/requests (stored as JSON)
    resources = Column(JSON, nullable=True)

    # Traffic configuration
    endpoint = Column(String(256), nullable=True)  # InferenceService name
    url = Column(String(512), nullable=True)  # Service URL
    traffic_percentage = Column(Integer, default=100)  # For A/B testing

    # Autoscaling
    autoscaling_enabled = Column(Integer, default=0)  # 0 or 1
    autoscaling_min = Column(Integer, default=1)
    autoscaling_max = Column(Integer, default=3)

    # Status
    status = Column(String(32), default="deploying")  # deploying, running, failed, stopped
    status_message = Column(Text, nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Ownership
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_model_deployments_endpoint", "endpoint"),
        Index("ix_model_deployments_status", "status"),
        Index("ix_model_deployments_model", "model_name"),
    )

    def __repr__(self):
        return f"<ModelDeployment(id={self.id}, name={self.name}, status={self.status})>"


class ModelStage(Base):
    """
    Model stage transition history

    Tracks all stage transitions for model versions.
    """
    __tablename__ = "model_stages"

    id = Column(Integer, primary_key=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False)

    # Stage transition
    stage = Column(String(32), nullable=False)  # Staging, Production, Archived, None
    previous_stage = Column(String(32), nullable=True)

    # Transition info
    transition_type = Column(String(32), default="manual")  # manual, auto, api
    transitioner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_model_stages_version_id", "model_version_id"),
        Index("ix_model_stages_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<ModelStage(id={self.id}, stage={self.stage}, created_at={self.created_at})>"


# Update ModelVersion to add the relationship
ModelVersion.registered_model = relationship("RegisteredModel", back_populates="versions")
