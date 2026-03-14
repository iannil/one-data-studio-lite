"""
Distributed Training Service

Provides base classes and interfaces for distributed ML training
across multiple GPUs and nodes using PyTorch DDP and TensorFlow.
"""

import logging
import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TrainingBackend(str, Enum):
    """Training framework backends"""

    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    KERAS = "keras"
    JAX = "jax"
    HUGGINGFACE = "huggingface"


class DistributedStrategy(str, Enum):
    """Distributed training strategies"""

    # PyTorch strategies
    DDP = "ddp"  # DistributedDataParallel
    FSDP = "fsdp"  # FullyShardedDataParallel
    DEEPSPEED = "deepspeed"  # DeepSpeed

    # TensorFlow strategies
    MIRRORED = "mirrored"  # MirroredStrategy
    MULTI_WORKER_MIRRORED = "multi_worker_mirrored"  # MultiWorkerMirroredStrategy
    TPUS = "tpu"  # TPUStrategy
    PARAMETER_SERVER = "parameter_server"  # ParameterServerStrategy

    # General
    SINGLE_NODE = "single_node"  # Single node multi-GPU
    MULTI_NODE = "multi_node"  # Multi-node multi-GPU


class TrainingStatus(str, Enum):
    """Training job status"""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ResourceConfig:
    """Compute resource configuration"""

    # CPU resources
    cpu_limit: Optional[int] = None
    cpu_request: Optional[int] = None

    # Memory resources
    memory_limit: Optional[str] = None  # e.g., "16Gi", "16GB"
    memory_request: Optional[str] = None

    # GPU resources
    gpu_count: int = 0
    gpu_type: Optional[str] = None  # e.g., "nvidia.com/gpu", "nvidia.com/a100-gh"
    gpu_memory: Optional[str] = None  # e.g., "40Gi"

    # Specialized hardware
    tpu_count: int = 0
    tpu_type: Optional[str] = None  # e.g., "v3-8", "v4-16"

    # Node selection
    node_selector: Dict[str, str] = field(default_factory=dict)
    tolerations: List[Dict[str, Any]] = field(default_factory=list)
    affinity: Dict[str, Any] = field(default_factory=dict)

    # Storage
    shared_memory: Optional[str] = None  # For shared memory between containers
    ephemeral_storage: Optional[str] = None

    def to_k8s_resources(self) -> Dict[str, Any]:
        """Convert to Kubernetes resource format"""
        resources = {}

        if self.cpu_request or self.cpu_limit or self.memory_request or self.memory_limit:
            resources["requests"] = {}
            resources["limits"] = {}

            if self.cpu_request:
                resources["requests"]["cpu"] = str(self.cpu_request)
            if self.cpu_limit:
                resources["limits"]["cpu"] = str(self.cpu_limit)
            if self.memory_request:
                resources["requests"]["memory"] = self.memory_request
            if self.memory_limit:
                resources["limits"]["memory"] = self.memory_limit

            if self.gpu_count > 0 and self.gpu_type:
                resources["limits"][self.gpu_type] = str(self.gpu_count)

        return resources

    def validate(self) -> List[str]:
        """Validate resource configuration"""
        errors = []

        if self.gpu_count > 0 and not self.gpu_type:
            errors.append("gpu_type must be specified when gpu_count > 0")

        if self.tpu_count > 0 and not self.tpu_type:
            errors.append("tpu_type must be specified when tpu_count > 0")

        return errors


@dataclass
class TrainingConfig:
    """Training job configuration"""

    # Basic info
    name: str
    experiment_id: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Training framework
    backend: TrainingBackend = TrainingBackend.PYTORCH
    strategy: DistributedStrategy = DistributedStrategy.DDP

    # Entry point
    entry_point: str = ""  # Python script or module path
    entry_point_args: List[str] = field(default_factory=list)
    working_dir: Optional[str] = None

    # Hyperparameters
    hyperparameters: Dict[str, Any] = field(default_factory=dict)

    # Data configuration
    data_config: Dict[str, Any] = field(default_factory=dict)

    # Model configuration
    model_config: Dict[str, Any] = field(default_factory=dict)

    # Distributed settings
    num_nodes: int = 1
    num_processes_per_node: int = 1  # Typically equals GPU count
    master_addr: str = "localhost"
    master_port: Optional[int] = None  # Auto-assign if None

    # Checkpointing
    checkpoint_path: Optional[str] = None
    resume_from_checkpoint: Optional[str] = None
    save_frequency: int = 1000  # Steps
    save_total_limit: int = 3

    # Logging
    log_level: str = "INFO"
    log_frequency: int = 100

    # Training duration
    max_steps: Optional[int] = None
    max_epochs: Optional[int] = None
    max_duration: Optional[str] = None  # e.g., "8h", "2d"

    # Early stopping
    early_stopping: bool = False
    early_stopping_patience: int = 10
    early_stopping_metric: str = "val_loss"

    # Resources
    resources: ResourceConfig = field(default_factory=ResourceConfig)

    # Environment
    environment: Dict[str, str] = field(default_factory=dict)
    pip_packages: List[str] = field(default_factory=list)

    # Docker image
    image: Optional[str] = None
    image_pull_policy: str = "IfNotPresent"

    # Namespace for Kubernetes resources
    namespace: str = "default"

    # Service account
    service_account: Optional[str] = None

    # Priority class
    priority_class_name: Optional[str] = None

    # TTL seconds after finished
    ttl_seconds_after_finished: Optional[int] = None

    def validate(self) -> List[str]:
        """Validate training configuration"""
        errors = []

        if not self.name:
            errors.append("name is required")

        if not self.entry_point:
            errors.append("entry_point is required")

        if self.num_nodes < 1:
            errors.append("num_nodes must be >= 1")

        if self.num_processes_per_node < 1:
            errors.append("num_processes_per_node must be >= 1")

        # Validate resources
        errors.extend(self.resources.validate())

        # Strategy validation
        if self.strategy == DistributedStrategy.DDP and self.num_nodes > 1:
            if not self.master_addr or self.master_addr == "localhost":
                errors.append("master_addr must be set for multi-node DDP training")

        return errors


@dataclass
class TrainingJob:
    """Training job instance"""

    # Job info
    job_id: str
    config: TrainingConfig
    status: TrainingStatus = TrainingStatus.PENDING

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    # Results
    exit_code: Optional[int] = None
    error_message: Optional[str] = None

    # Metrics
    metrics: Dict[str, Any] = field(default_factory=dict)

    # Pod/Container info
    pod_names: List[str] = field(default_factory=list)
    service_name: Optional[str] = None

    # Checkpoint info
    latest_checkpoint: Optional[str] = None

    # Owner
    owner_id: Optional[int] = None

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
        return self.status in (TrainingStatus.STARTING, TrainingStatus.RUNNING)

    @property
    def is_terminal(self) -> bool:
        """Check if job is in a terminal state"""
        return self.status in (
            TrainingStatus.COMPLETED,
            TrainingStatus.FAILED,
            TrainingStatus.CANCELLED,
        )


class BaseDistributedTrainer(ABC):
    """
    Base class for distributed training runners

    Defines the interface for training job submission and management.
    """

    def __init__(self, config: TrainingConfig):
        """
        Initialize trainer

        Args:
            config: Training configuration
        """
        self.config = config
        self.job_id = f"training-{uuid.uuid4().hex[:8]}"
        self._status = TrainingStatus.PENDING
        self._pods: List[str] = []

    @abstractmethod
    async def submit(self) -> TrainingJob:
        """
        Submit training job to cluster

        Returns:
            TrainingJob with job_id
        """
        pass

    @abstractmethod
    async def get_status(self, job_id: str) -> TrainingStatus:
        """
        Get current training status

        Args:
            job_id: Training job ID

        Returns:
            Current training status
        """
        pass

    @abstractmethod
    async def get_logs(
        self,
        job_id: str,
        follow: bool = False,
        tail_lines: Optional[int] = None,
    ) -> str:
        """
        Get training logs

        Args:
            job_id: Training job ID
            follow: Whether to follow logs
            tail_lines: Number of lines to tail

        Returns:
            Log output
        """
        pass

    @abstractmethod
    async def cancel(self, job_id: str) -> bool:
        """
        Cancel training job

        Args:
            job_id: Training job ID

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def get_metrics(self, job_id: str) -> Dict[str, Any]:
        """
        Get training metrics

        Args:
            job_id: Training job ID

        Returns:
            Training metrics
        """
        pass

    def build_launch_command(self) -> List[str]:
        """
        Build the launch command for distributed training

        Returns:
            Command as list of strings
        """
        raise NotImplementedError("Subclasses must implement build_launch_command")

    def get_environment_variables(self, rank: int = 0, world_size: int = 1) -> Dict[str, str]:
        """
        Get environment variables for training process

        Args:
            rank: Process rank
            world_size: Total number of processes

        Returns:
            Environment variables dictionary
        """
        env = {
            **self.config.environment,
            "RANK": str(rank),
            "WORLD_SIZE": str(world_size),
            "JOB_ID": self.job_id,
        }

        if self.config.experiment_id:
            env["EXPERIMENT_ID"] = self.config.experiment_id

        # Training backend specific
        if self.config.backend == TrainingBackend.PYTORCH:
            env.update(self._get_pytorch_env(rank, world_size))
        elif self.config.backend == TrainingBackend.TENSORFLOW:
            env.update(self._get_tensorflow_env())

        return env

    def _get_pytorch_env(self, rank: int, world_size: int) -> Dict[str, str]:
        """Get PyTorch-specific environment variables"""
        env = {}

        if self.config.strategy == DistributedStrategy.DDP:
            env.update({
                "MASTER_ADDR": str(self.config.master_addr),
                "MASTER_PORT": str(self.config.master_port or 29500),
                "NCCL_DEBUG": "INFO",
                "NCCL_SOCKET_IFNAME": "eth0",
            })

        # CUDA settings
        if self.config.resources.gpu_count > 0:
            local_rank = rank % self.config.resources.gpu_count
            env.update({
                "LOCAL_RANK": str(local_rank),
                "CUDA_VISIBLE_DEVICES": ",".join(
                    str(i) for i in range(self.config.resources.gpu_count)
                ),
            })

        return env

    def _get_tensorflow_env(self) -> Dict[str, str]:
        """Get TensorFlow-specific environment variables"""
        env = {}

        if self.config.strategy == DistributedStrategy.MIRRORED:
            env["TF_CONFIG"] = json.dumps({
                "cluster": {
                    "worker": [f"{self.config.master_addr}:{self.config.master_port or 2222}"]
                },
                "task": {"type": "worker", "index": 0},
            })

        return env


class TrainingOrchestrator:
    """
    Orchestrates distributed training jobs

    Manages the lifecycle of training jobs including submission,
    monitoring, and cleanup.
    """

    def __init__(self):
        self._jobs: Dict[str, TrainingJob] = {}
        self._trainers: Dict[str, BaseDistributedTrainer] = {}

    async def submit_training(
        self,
        config: TrainingConfig,
        owner_id: Optional[int] = None,
    ) -> TrainingJob:
        """
        Submit a new training job

        Args:
            config: Training configuration
            owner_id: User ID who submitted the job

        Returns:
            TrainingJob instance
        """
        # Validate configuration
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")

        # Create trainer based on backend and strategy
        trainer = self._create_trainer(config)

        # Submit job
        job = await trainer.submit()
        job.owner_id = owner_id

        # Track job
        self._jobs[job.job_id] = job
        self._trainers[job.job_id] = trainer

        logger.info(f"Submitted training job {job.job_id}")
        return job

    async def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        """
        Get training job status

        Args:
            job_id: Training job ID

        Returns:
            TrainingJob or None if not found
        """
        job = self._jobs.get(job_id)
        if not job:
            return None

        trainer = self._trainers.get(job_id)
        if trainer:
            job.status = await trainer.get_status(job_id)

        return job

    async def list_jobs(
        self,
        owner_id: Optional[int] = None,
        status: Optional[TrainingStatus] = None,
    ) -> List[TrainingJob]:
        """
        List training jobs

        Args:
            owner_id: Filter by owner
            status: Filter by status

        Returns:
            List of training jobs
        """
        jobs = list(self._jobs.values())

        if owner_id:
            jobs = [j for j in jobs if j.owner_id == owner_id]

        if status:
            jobs = [j for j in jobs if j.status == status]

        return jobs

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a training job

        Args:
            job_id: Training job ID

        Returns:
            True if cancelled successfully
        """
        trainer = self._trainers.get(job_id)
        if not trainer:
            return False

        result = await trainer.cancel(job_id)
        if result and job_id in self._jobs:
            self._jobs[job_id].status = TrainingStatus.CANCELLED
            self._jobs[job_id].finished_at = datetime.utcnow()

        return result

    async def get_job_logs(
        self,
        job_id: str,
        follow: bool = False,
        tail_lines: Optional[int] = None,
    ) -> Optional[str]:
        """
        Get training job logs

        Args:
            job_id: Training job ID
            follow: Whether to follow logs
            tail_lines: Number of lines to tail

        Returns:
            Log output or None if job not found
        """
        trainer = self._trainers.get(job_id)
        if not trainer:
            return None

        return await trainer.get_logs(job_id, follow, tail_lines)

    async def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get training job metrics

        Args:
            job_id: Training job ID

        Returns:
            Metrics or None if job not found
        """
        trainer = self._trainers.get(job_id)
        if not trainer:
            return None

        return await trainer.get_metrics(job_id)

    def _create_trainer(self, config: TrainingConfig) -> BaseDistributedTrainer:
        """Create appropriate trainer based on backend and strategy"""
        from .torch_runner import PyTorchDDPTrainer
        from .tf_runner import TensorFlowTrainer

        if config.backend == TrainingBackend.PYTORCH:
            if config.strategy == DistributedStrategy.DDP:
                return PyTorchDDPTrainer(config)
            # Add other PyTorch strategies here
            raise NotImplementedError(f"PyTorch strategy {config.strategy} not implemented")

        elif config.backend == TrainingBackend.TENSORFLOW:
            return TensorFlowTrainer(config)

        raise NotImplementedError(f"Backend {config.backend} not implemented")


# Singleton instance
_orchestrator: Optional[TrainingOrchestrator] = None


def get_training_orchestrator() -> TrainingOrchestrator:
    """Get the training orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TrainingOrchestrator()
    return _orchestrator
