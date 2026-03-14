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


# =============================================================================
# Distributed Training Models
# =============================================================================

class TrainingJob(Base):
    """
    Distributed Training Job model

    Tracks distributed training jobs submitted to the cluster.
    """

    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # Training configuration
    backend = Column(String(32), nullable=False)  # pytorch, tensorflow, jax
    strategy = Column(String(64), nullable=False)  # ddp, fsdp, mirrored, etc.

    # Entry point
    entry_point = Column(String(512), nullable=False)
    entry_point_args = Column(JSON, nullable=True)

    # Distributed settings
    num_nodes = Column(Integer, nullable=False, default=1)
    num_processes_per_node = Column(Integer, nullable=False, default=1)
    master_addr = Column(String(256), nullable=True)
    master_port = Column(Integer, nullable=True)

    # Hyperparameters
    hyperparameters = Column(JSON, nullable=True)

    # Data and model config
    data_config = Column(JSON, nullable=True)
    model_config = Column(JSON, nullable=True)

    # Resource configuration
    resources = Column(JSON, nullable=True)

    # Training settings
    max_steps = Column(Integer, nullable=True)
    max_epochs = Column(Integer, nullable=True)
    max_duration = Column(String(64), nullable=True)

    # Checkpointing
    checkpoint_path = Column(String(512), nullable=True)
    resume_from_checkpoint = Column(String(512), nullable=True)

    # Docker image
    image = Column(String(256), nullable=True)

    # Status
    status = Column(
        SQLEnum("pending", "starting", "running", "completed", "failed", "cancelled", "paused",
               name="training_job_status"),
        nullable=False,
        default="pending",
        index=True,
    )

    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Results
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics (latest values)
    metrics = Column(JSON, nullable=True)

    # Kubernetes resources
    namespace = Column(String(64), nullable=True)
    pod_names = Column(JSON, nullable=True)
    service_name = Column(String(256), nullable=True)

    # Ownership
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Tags
    tags = Column(JSON, nullable=True)

    # Relationships
    experiment = relationship("Experiment", backref="training_jobs")

    __table_args__ = (
        Index("ix_training_jobs_status", "status"),
        Index("ix_training_jobs_experiment", "experiment_id"),
        Index("ix_training_jobs_owner", "owner_id"),
    )

    def __repr__(self):
        return f"<TrainingJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


class TrainingNode(Base):
    """
    Training Node model

    Tracks individual nodes participating in distributed training.
    """

    __tablename__ = "training_nodes"

    id = Column(Integer, primary_key=True, index=True)
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=False, index=True)

    # Node identification
    node_rank = Column(Integer, nullable=False)
    node_name = Column(String(256), nullable=True)
    pod_name = Column(String(256), nullable=True)

    # Node status
    status = Column(
        SQLEnum("pending", "running", "succeeded", "failed", "unknown",
               name="training_node_status"),
        nullable=False,
        default="pending",
    )

    # Host info
    hostname = Column(String(256), nullable=True)
    ip_address = Column(String(64), nullable=True)

    # GPU assignment
    gpu_ids = Column(JSON, nullable=True)  # List of GPU IDs assigned to this node

    # Timing
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Logs
    log_url = Column(String(512), nullable=True)

    # Metrics (node-specific)
    metrics = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    training_job = relationship("TrainingJob", backref="nodes")

    def __repr__(self):
        return f"<TrainingNode(id={self.id}, node_rank={self.node_rank}, status='{self.status}')>"


class TrainingCheckpoint(Base):
    """
    Training Checkpoint model

    Tracks model checkpoints saved during training.
    """

    __tablename__ = "training_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=False, index=True)

    # Checkpoint info
    checkpoint_path = Column(String(512), nullable=False)
    step = Column(Integer, nullable=False)
    epoch = Column(Integer, nullable=True)

    # Metrics at checkpoint
    metrics = Column(JSON, nullable=True)

    # File info
    file_size = Column(Integer, nullable=True)  # Size in bytes

    # Classification
    is_best = Column(Integer, default=0)  # 1 if this is the best checkpoint
    is_latest = Column(Integer, default=0)  # 1 if this is the latest checkpoint

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    training_job = relationship("TrainingJob", backref="checkpoints")

    __table_args__ = (
        Index("ix_training_checkpoints_job_step", "training_job_id", "step"),
        Index("ix_training_checkpoints_best", "training_job_id", "is_best"),
    )

    def __repr__(self):
        return f"<TrainingCheckpoint(id={self.id}, step={self.step}, is_best={bool(self.is_best)})>"


class HyperparameterTune(Base):
    """
    Hyperparameter Tuning Job model

    Tracks automated hyperparameter tuning experiments.
    """

    __tablename__ = "hyperparameter_tunes"

    id = Column(Integer, primary_key=True, index=True)
    tune_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)

    # Tuning configuration
    tuning_strategy = Column(String(64), nullable=False)  # bayesian, random, grid, hyperband
    optimization_metric = Column(String(64), nullable=False)  # Metric to optimize
    optimization_mode = Column(String(8), nullable=False)  # min, max

    # Search space
    search_space = Column(JSON, nullable=True)  # Parameter search space

    # Tuning settings
    max_trials = Column(Integer, nullable=False, default=10)
    parallel_trials = Column(Integer, nullable=False, default=1)
    max_duration = Column(String(64), nullable=True)

    # Base training config
    base_config = Column(JSON, nullable=True)

    # Status
    status = Column(
        SQLEnum("pending", "running", "completed", "failed", "cancelled",
               name="tune_status"),
        nullable=False,
        default="pending",
    )

    # Results
    best_trial_id = Column(Integer, nullable=True)
    best_value = Column(Float, nullable=True)

    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Ownership
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Tags
    tags = Column(JSON, nullable=True)

    # Relationships
    experiment = relationship("Experiment", backref="hyperparameter_tunes")
    trials = relationship("HyperparameterTrial", back_populates="tune", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<HyperparameterTune(id={self.id}, tune_id='{self.tune_id}', status='{self.status}')>"


class HyperparameterTrial(Base):
    """
    Hyperparameter Trial model

    Individual trial in a hyperparameter tuning experiment.
    """

    __tablename__ = "hyperparameter_trials"

    id = Column(Integer, primary_key=True, index=True)
    tune_id = Column(Integer, ForeignKey("hyperparameter_tunes.id"), nullable=False, index=True)

    # Trial number
    trial_number = Column(Integer, nullable=False)

    # Hyperparameters used
    hyperparameters = Column(JSON, nullable=False)

    # Results
    metrics = Column(JSON, nullable=True)

    # Training job reference (if launched)
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=True)

    # Status
    status = Column(
        SQLEnum("pending", "running", "completed", "failed", "cancelled",
               name="trial_status"),
        nullable=False,
        default="pending",
    )

    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Relationships
    tune = relationship("HyperparameterTune", back_populates="trials")
    training_job = relationship("TrainingJob", backref="hyperparameter_trial")

    __table_args__ = (
        Index("ix_hyperparameter_trials_tune_number", "tune_id", "trial_number"),
    )

    def __repr__(self):
        return f"<HyperparameterTrial(id={self.id}, trial_number={self.trial_number}, status='{self.status}')>"

