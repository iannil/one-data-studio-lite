"""
Training Database Models

Defines database models for distributed training jobs, checkpoints,
and related training entities.
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
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class TrainingBackend(str):
    """Training framework backends"""
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    KERAS = "keras"
    JAX = "jax"
    HUGGINGFACE = "huggingface"
    SKLEARN = "sklearn"
    CUSTOM = "custom"


class DistributedStrategy(str):
    """Distributed training strategies"""
    # PyTorch strategies
    DDP = "ddp"  # DistributedDataParallel
    FSDP = "fsdp"  # FullyShardedDataParallel
    DEEPSPEED = "deepspeed"
    # TensorFlow strategies
    MIRRORED = "mirrored"
    MULTI_WORKER_MIRRORED = "multi_worker_mirrored"
    PARAMETER_SERVER = "parameter_server"
    # General
    SINGLE_NODE = "single_node"
    MULTI_NODE = "multi_node"


class TrainingJobStatus(str):
    """Training job status"""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    STOPPING = "stopping"


class TrainingJob(Base):
    """
    Training Job

    Represents a distributed training job.
    """

    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(250), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Experiment linkage
    experiment_id = Column(String(250), ForeignKey("experiments.id"), nullable=True, index=True)
    mlflow_run_id = Column(String(250), nullable=True, index=True)

    # Training configuration
    backend = Column(String(50), nullable=False, default="pytorch")
    strategy = Column(String(50), nullable=False, default="ddp")

    # Entry point
    entry_point = Column(String(500), nullable=False)
    entry_point_args = Column(JSON, nullable=True, default=list)
    working_dir = Column(String(500), nullable=True)

    # Hyperparameters
    hyperparameters = Column(JSON, nullable=False, default=dict)

    # Data configuration
    dataset_uri = Column(Text, nullable=True)
    dataset_version = Column(String(100), nullable=True)

    # Model configuration
    model_config = Column(JSON, nullable=True, default=dict)

    # Distributed settings
    num_nodes = Column(Integer, nullable=False, default=1)
    num_processes_per_node = Column(Integer, nullable=False, default=1)
    master_addr = Column(String(250), nullable=True)
    master_port = Column(Integer, nullable=True)

    # Checkpointing
    checkpoint_path = Column(Text, nullable=True)
    resume_from_checkpoint = Column(String(500), nullable=True)
    save_frequency = Column(Integer, nullable=False, default=1000)

    # Training duration
    max_steps = Column(BigInteger, nullable=True)
    max_epochs = Column(Integer, nullable=True)
    max_duration = Column(String(100), nullable=True)  # e.g., "8h", "2d"

    # Early stopping
    early_stopping_enabled = Column(Boolean, nullable=False, default=False)
    early_stopping_patience = Column(Integer, nullable=False, default=10)
    early_stopping_metric = Column(String(100), nullable=False, default="val_loss")

    # Resource configuration
    cpu_limit = Column(Integer, nullable=True)
    cpu_request = Column(Integer, nullable=True)
    memory_limit = Column(String(50), nullable=True)
    memory_request = Column(String(50), nullable=True)
    gpu_count = Column(Integer, nullable=False, default=0)
    gpu_type = Column(String(50), nullable=True)  # e.g., "nvidia.com/gpu", "nvidia.com/a100-gh"
    gpu_memory = Column(String(50), nullable=True)

    # Node selection
    node_selector = Column(JSON, nullable=True, default=dict)
    affinity = Column(JSON, nullable=True, default=dict)

    # Docker configuration
    image = Column(String(500), nullable=True)
    image_pull_policy = Column(String(50), nullable=False, default="IfNotPresent")
    pip_packages = Column(JSON, nullable=True, default=list)

    # Environment variables
    environment = Column(JSON, nullable=True, default=dict)

    # Namespace for Kubernetes resources
    namespace = Column(String(250), nullable=False, default="default")
    service_account = Column(String(250), nullable=True)

    # Priority
    priority_class_name = Column(String(250), nullable=True)

    # TTL after finished
    ttl_seconds_after_finished = Column(Integer, nullable=True)

    # Status
    status = Column(
        SQLEnum(
            "pending",
            "starting",
            "running",
            "completed",
            "failed",
            "cancelled",
            "paused",
            "stopping",
            name="training_job_status"
        ),
        nullable=False,
        default="pending",
        index=True,
    )
    status_message = Column(Text, nullable=True)

    # Timing
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    # Results
    exit_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics (final metrics)
    final_metrics = Column(JSON, nullable=True, default=dict)

    # Pod/Container info
    pod_names = Column(JSON, nullable=True, default=list)
    pod_status = Column(JSON, nullable=True, default=dict)  # Pod name -> status
    service_name = Column(String(250), nullable=True)

    # Checkpoint info
    latest_checkpoint = Column(String(500), nullable=True)

    # GPU utilization
    gpu_utilization = Column(JSON, nullable=True, default=dict)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    # Ownership
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Relationships
    created_by = relationship("User")
    project = relationship("Project")
    experiment = relationship("Experiment")
    checkpoints = relationship("TrainingCheckpoint", back_populates="training_job", cascade="all, delete-orphan")
    logs = relationship("TrainingLog", back_populates="training_job", cascade="all, delete-orphan")

    @property
    def duration(self) -> Optional[float]:
        """Get training duration in seconds"""
        if not self.started_at:
            return None
        end = self.finished_at or datetime.utcnow()
        return (end - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status in ("starting", "running")

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state"""
        return self.status in ("completed", "failed", "cancelled")

    def __repr__(self):
        return f"<TrainingJob(id={self.id}, job_id='{self.job_id}', status='{self.status}')>"


class TrainingCheckpoint(Base):
    """
    Training Checkpoint

    Represents a model checkpoint saved during training.
    """

    __tablename__ = "training_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    checkpoint_id = Column(String(250), unique=True, nullable=False, index=True)

    # Training job reference
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=False, index=True)
    training_job = relationship("TrainingJob", back_populates="checkpoints")

    # Checkpoint info
    step = Column(BigInteger, nullable=False)
    epoch = Column(Integer, nullable=True)
    checkpoint_path = Column(Text, nullable=False)

    # Metrics at checkpoint
    metrics = Column(JSON, nullable=True, default=dict)

    # File info
    file_size_bytes = Column(BigInteger, nullable=True)

    # Checkpoint type
    checkpoint_type = Column(String(50), nullable=False, default="epoch")  # epoch, step, best

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    metadata = Column(JSON, nullable=True, default=dict)

    def __repr__(self):
        return f"<TrainingCheckpoint(id={self.id}, checkpoint_id='{self.checkpoint_id}', step={self.step})>"


class TrainingLog(Base):
    """
    Training Log

    Stores log entries from training jobs.
    """

    __tablename__ = "training_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Training job reference
    training_job_id = Column(Integer, ForeignKey("training_jobs.id"), nullable=False, index=True)
    training_job = relationship("TrainingJob", back_populates="logs")

    # Log entry
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    level = Column(String(20), nullable=False, default="INFO")  # DEBUG, INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)  # e.g., "rank-0", "master"

    # Structured data (for parsing)
    structured_data = Column(JSON, nullable=True, default=dict)

    def __repr__(self):
        return f"<TrainingLog(id={self.id}, training_job_id={self.training_job_id}, timestamp={self.timestamp})>"


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
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("registered_models.id"), nullable=True)

    # Search configuration
    algorithm = Column(String(50), nullable=False, default="optuna")
    search_space = Column(JSON, nullable=False, default=dict)
    optimization_metric = Column(String(100), nullable=False, default="accuracy")
    optimization_mode = Column(String(20), nullable=False, default="max")  # max or min

    # Search settings
    n_trials = Column(Integer, nullable=False, default=10)
    timeout_minutes = Column(Integer, nullable=True)
    early_stopping_trials = Column(Integer, nullable=True)

    # Execution
    status = Column(String(50), nullable=False, default="created")
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
    experiment = relationship("Experiment")
    model = relationship("RegisteredModel")
    trials = relationship("HyperparameterTrial", back_populates="search")

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
    search = relationship("HyperparameterTrial", back_populates="trials")

    # Hyperparameters
    params = Column(JSON, nullable=False, default=dict)

    # Metrics
    metrics = Column(JSON, nullable=True, default=dict)
    objective_value = Column(Float, nullable=False)

    # Status
    status = Column(String(50), nullable=False, default="running")
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    # Artifacts
    run_id = Column(String(250), nullable=True)  # Associated training run
    artifact_uri = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<HyperparameterTrial(id={self.id}, trial_id='{self.trial_id}', status='{self.status}')>"
