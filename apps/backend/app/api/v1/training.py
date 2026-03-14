"""
Training API endpoints

REST API for managing distributed training jobs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator

from app.api.deps import get_current_user, require_permission
from app.models.user import User
from app.services.training import (
    TrainingBackend,
    TrainingStatus,
    DistributedStrategy,
    TrainingConfig,
    ResourceConfig,
    TrainingOrchestrator,
    get_training_orchestrator,
)

router = APIRouter(prefix="/training", tags=["training"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ResourceConfigRequest(BaseModel):
    """Resource configuration request"""

    cpu_limit: Optional[int] = None
    cpu_request: Optional[int] = None
    memory_limit: Optional[str] = None
    memory_request: Optional[str] = None
    gpu_count: int = 0
    gpu_type: Optional[str] = None
    gpu_memory: Optional[str] = None
    tpu_count: int = 0
    tpu_type: Optional[str] = None
    shared_memory: Optional[str] = None

    class Config:
        extra = "allow"


class TrainingJobCreateRequest(BaseModel):
    """Request to create a training job"""

    name: str = Field(..., description="Training job name")
    description: Optional[str] = Field(None, description="Job description")
    experiment_id: Optional[str] = Field(None, description="Associated experiment ID")
    tags: List[str] = Field(default_factory=list, description="Job tags")

    # Training framework
    backend: TrainingBackend = Field(TrainingBackend.PYTORCH, description="Training backend")
    strategy: DistributedStrategy = Field(DistributedStrategy.DDP, description="Distributed strategy")

    # Entry point
    entry_point: str = Field(..., description="Training script path")
    entry_point_args: List[str] = Field(default_factory=list, description="Script arguments")

    # Working directory
    working_dir: Optional[str] = Field(None, description="Working directory")

    # Hyperparameters
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Training hyperparameters")

    # Data configuration
    data_config: Dict[str, Any] = Field(default_factory=dict, description="Data configuration")

    # Model configuration
    model_config: Dict[str, Any] = Field(default_factory=dict, description="Model configuration")

    # Distributed settings
    num_nodes: int = Field(1, ge=1, le=100, description="Number of training nodes")
    num_processes_per_node: int = Field(1, ge=1, le=8, description="Processes per node (typically GPUs)")
    master_addr: str = Field("localhost", description="Master node address for multi-node")
    master_port: Optional[int] = Field(None, ge=1, le=65535, description="Master port")

    # Checkpointing
    checkpoint_path: Optional[str] = Field(None, description="Checkpoint save path")
    resume_from_checkpoint: Optional[str] = Field(None, description="Resume from checkpoint")
    save_frequency: int = Field(1000, ge=1, description="Save frequency (steps)")
    save_total_limit: int = Field(3, ge=1, le=100, description="Max checkpoints to keep")

    # Training duration
    max_steps: Optional[int] = Field(None, ge=1, description="Maximum training steps")
    max_epochs: Optional[int] = Field(None, ge=1, description="Maximum training epochs")
    max_duration: Optional[str] = Field(None, description="Maximum duration (e.g., '8h', '2d')")

    # Resources
    resources: ResourceConfigRequest = Field(default_factory=ResourceConfigRequest, description="Resource configuration")

    # Environment
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    pip_packages: List[str] = Field(default_factory=list, description="Additional pip packages")

    # Docker
    image: Optional[str] = Field(None, description="Docker image")
    namespace: str = Field("default", description="Kubernetes namespace")

    # Logging
    log_level: str = Field("INFO", description="Log level")

    @validator("backend")
    def validate_backend_for_strategy(cls, v, values):
        strategy = values.get("strategy")
        if strategy == DistributedStrategy.TPUS and v != TrainingBackend.TENSORFLOW:
            raise ValueError("TPU strategy requires TensorFlow backend")
        return v


class TrainingJobResponse(BaseModel):
    """Training job response"""

    id: int
    job_id: str
    name: str
    description: Optional[str]
    backend: str
    strategy: str
    status: str
    num_nodes: int
    num_processes_per_node: str
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration: Optional[float]
    metrics: Dict[str, Any]
    tags: List[str]
    owner_id: Optional[int]


class TrainingJobListResponse(BaseModel):
    """Training job list response"""

    id: int
    job_id: str
    name: str
    status: str
    backend: str
    num_nodes: int
    created_at: str


class TrainingJobUpdateRequest(BaseModel):
    """Request to update a training job"""

    description: Optional[str] = None
    tags: Optional[List[str]] = None
    # Currently only supports metadata updates


class TrainingLogsResponse(BaseModel):
    """Training logs response"""

    job_id: str
    logs: str
    follow_url: Optional[str]


class JobMetricsResponse(BaseModel):
    """Job metrics response"""

    job_id: str
    metrics: Dict[str, Any]
    timestamp: str


class NodeStatusResponse(BaseModel):
    """Training node status response"""

    id: int
    node_rank: int
    node_name: Optional[str]
    pod_name: Optional[str]
    status: str
    hostname: Optional[str]
    ip_address: Optional[str]
    gpu_ids: Optional[List[int]]
    started_at: Optional[str]
    finished_at: Optional[str]


# =============================================================================
# Helper Functions
# =============================================================================

async def get_orchestrator() -> TrainingOrchestrator:
    """Get training orchestrator instance"""
    return get_training_orchestrator()


def config_from_request(request: TrainingJobCreateRequest) -> TrainingConfig:
    """Convert request to TrainingConfig"""
    return TrainingConfig(
        name=request.name,
        description=request.description,
        tags=request.tags,
        backend=request.backend,
        strategy=request.strategy,
        entry_point=request.entry_point,
        entry_point_args=request.entry_point_args,
        working_dir=request.working_dir,
        hyperparameters=request.hyperparameters,
        data_config=request.data_config,
        model_config=request.model_config,
        num_nodes=request.num_nodes,
        num_processes_per_node=request.num_processes_per_node,
        master_addr=request.master_addr,
        master_port=request.master_port,
        checkpoint_path=request.checkpoint_path,
        resume_from_checkpoint=request.resume_from_checkpoint,
        save_frequency=request.save_frequency,
        save_total_limit=request.save_total_limit,
        max_steps=request.max_steps,
        max_epochs=request.max_epochs,
        max_duration=request.max_duration,
        resources=ResourceConfig(
            cpu_limit=request.resources.cpu_limit,
            cpu_request=request.resources.cpu_request,
            memory_limit=request.resources.memory_limit,
            memory_request=request.resources.memory_request,
            gpu_count=request.resources.gpu_count,
            gpu_type=request.resources.gpu_type,
            gpu_memory=request.resources.gpu_memory,
            tpu_count=request.resources.tpu_count,
            tpu_type=request.resources.tpu_type,
            shared_memory=request.resources.shared_memory,
        ),
        environment=request.environment,
        pip_packages=request.pip_packages,
        image=request.image,
        namespace=request.namespace,
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/jobs", response_model=List[TrainingJobListResponse])
async def list_training_jobs(
    status: Optional[TrainingStatus] = Query(None, description="Filter by status"),
    backend: Optional[TrainingBackend] = Query(None, description="Filter by backend"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    current_user: User = Depends(get_current_user),
):
    """
    List training jobs

    Returns all training jobs with optional filtering.
    """
    orchestrator = await get_orchestrator()

    jobs = await orchestrator.list_jobs(
        owner_id=current_user.id if not current_user.is_admin else None,
        status=status,
    )

    # Filter by backend
    if backend:
        jobs = [j for j in jobs if j.config.backend == backend]

    # Apply limit
    jobs = jobs[:limit]

    return [
        TrainingJobListResponse(
            id=id(job),  # Placeholder
            job_id=job.job_id,
            name=job.config.name,
            status=job.status.value,
            backend=job.config.backend.value,
            num_nodes=job.config.num_nodes,
            created_at=job.created_at.isoformat(),
        )
        for job in jobs
    ]


@router.post("/jobs", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    request: TrainingJobCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new training job

    Submits a new distributed training job to the cluster.
    """
    orchestrator = await get_orchestrator()

    config = config_from_request(request)

    try:
        job = await orchestrator.submit_training(config, owner_id=current_user.id)
        return TrainingJobResponse(
            id=0,  # Will be filled by DB
            job_id=job.job_id,
            name=job.config.name,
            description=job.config.description,
            backend=job.config.backend.value,
            strategy=job.config.strategy.value,
            status=job.status.value,
            num_nodes=job.config.num_nodes,
            num_processes_per_node=job.config.num_processes_per_node,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            duration=job.duration,
            metrics=job.metrics,
            tags=job.config.tags,
            owner_id=job.owner_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get training job details

    Returns detailed information about a training job.
    """
    orchestrator = await get_orchestrator()

    job = await orchestrator.get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    return TrainingJobResponse(
        id=0,
        job_id=job.job_id,
        name=job.config.name,
        description=job.config.description,
        backend=job.config.backend.value,
        strategy=job.config.strategy.value,
        status=job.status.value,
        num_nodes=job.config.num_nodes,
        num_processes_per_node=job.config.num_processes_per_node,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        duration=job.duration,
        metrics=job.metrics,
        tags=job.config.tags,
        owner_id=job.owner_id,
    )


@router.delete("/jobs/{job_id}")
async def cancel_training_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a training job

    Stops and removes the training job from the cluster.
    """
    orchestrator = await get_orchestrator()

    job = await orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    if not job.is_running:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not running (status: {job.status.value})",
        )

    result = await orchestrator.cancel_job(job_id)

    if result:
        return {"message": f"Training job {job_id} cancelled successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job {job_id}",
        )


@router.get("/jobs/{job_id}/logs", response_model=TrainingLogsResponse)
async def get_job_logs(
    job_id: str,
    follow: bool = Query(False, description="Follow logs"),
    tail_lines: Optional[int] = Query(None, ge=1, description="Number of lines to tail"),
    current_user: User = Depends(get_current_user),
):
    """
    Get training job logs

    Returns logs from the training job.
    """
    orchestrator = await get_orchestrator()

    job = await orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    logs = await orchestrator.get_job_logs(job_id, follow, tail_lines)

    return TrainingLogsResponse(
        job_id=job_id,
        logs=logs or "",
        follow_url=f"/training/jobs/{job_id}/logs/stream" if follow else None,
    )


@router.get("/jobs/{job_id}/metrics", response_model=JobMetricsResponse)
async def get_job_metrics(
    job_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get training job metrics

    Returns current metrics from the training job.
    """
    orchestrator = await get_orchestrator()

    job = await orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    metrics = await orchestrator.get_job_metrics(job_id)

    return JobMetricsResponse(
        job_id=job_id,
        metrics=metrics or {},
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/backends")
async def list_training_backends(
    current_user: User = Depends(get_current_user),
):
    """
    List available training backends

    Returns supported training frameworks and their features.
    """
    return [
        {
            "backend": "pytorch",
            "name": "PyTorch",
            "strategies": [
                {"strategy": "ddp", "name": "DistributedDataParallel", "description": "Synchronous data parallelism"},
                {"strategy": "fsdp", "name": "FullyShardedDataParallel", "description": "Sharded data parallelism"},
                {"strategy": "deepspeed", "name": "DeepSpeed", "description": "ZeRO optimizer + memory optimizations"},
            ],
            "features": ["amp", "gradient_checkpointing", "model_parallelism"],
            "available": True,
        },
        {
            "backend": "tensorflow",
            "name": "TensorFlow",
            "strategies": [
                {"strategy": "mirrored", "name": "MirroredStrategy", "description": "Synchronous multi-GPU"},
                {"strategy": "multi_worker_mirrored", "name": "MultiWorkerMirroredStrategy", "description": "Multi-node synchronous"},
                {"strategy": "tpu", "name": "TPUStrategy", "description": "TPU training"},
                {"strategy": "parameter_server", "name": "ParameterServerStrategy", "description": "Parameter server training"},
            ],
            "features": ["amp", "tpu", "model_parallelism"],
            "available": True,
        },
        {
            "backend": "jax",
            "name": "JAX",
            "strategies": [
                {"strategy": "pmap", "name": "pmap", "description": "Single program multiple data"},
                {"strategy": "pjit", "name": "pjit", "description": "Parallel JIT compilation"},
            ],
            "features": ["tpu", "auto_parallelism"],
            "available": False,
        },
    ]


@router.get("/strategies")
async def list_training_strategies(
    current_user: User = Depends(get_current_user),
):
    """
    List available distributed training strategies

    Returns information about each strategy.
    """
    return [
        {
            "strategy": "ddp",
            "name": "DistributedDataParallel",
            "backend": "pytorch",
            "description": "PyTorch synchronous data parallelism using NCCL",
            "multi_node": True,
            "requires_master": True,
            "scaling": "linear",
        },
        {
            "strategy": "fsdp",
            "name": "FullyShardedDataParallel",
            "backend": "pytorch",
            "description": "PyTorch sharded training with ZeRO-3",
            "multi_node": True,
            "requires_master": True,
            "scaling": "near_linear",
        },
        {
            "strategy": "mirrored",
            "name": "MirroredStrategy",
            "backend": "tensorflow",
            "description": "TensorFlow synchronous multi-GPU",
            "multi_node": False,
            "requires_master": False,
            "scaling": "linear",
        },
        {
            "strategy": "multi_worker_mirrored",
            "name": "MultiWorkerMirroredStrategy",
            "backend": "tensorflow",
            "description": "TensorFlow multi-node synchronous",
            "multi_node": True,
            "requires_master": True,
            "scaling": "linear",
        },
        {
            "strategy": "tpu",
            "name": "TPUStrategy",
            "backend": "tensorflow",
            "description": "Google TPU training",
            "multi_node": False,
            "requires_master": False,
            "scaling": "near_linear",
        },
    ]


@router.post("/validate")
async def validate_training_config(
    request: TrainingJobCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Validate training job configuration

    Validates the configuration without submitting the job.
    """
    config = config_from_request(request)

    errors = config.validate()

    # Backend-specific validation
    if config.backend == TrainingBackend.PYTORCH:
        from app.services.training.torch_runner import validate_ddp_configuration
        errors.extend(validate_ddp_configuration(config))
    elif config.backend == TrainingBackend.TENSORFLOW:
        from app.services.training.tf_runner import validate_tf_configuration
        errors.extend(validate_tf_configuration(config))

    if errors:
        return {
            "valid": False,
            "errors": errors,
        }
    else:
        return {
            "valid": True,
            "warnings": [],
            "estimated_cost": _estimate_training_cost(config),
        }


def _estimate_training_cost(config: TrainingConfig) -> Optional[Dict[str, Any]]:
    """Estimate training cost based on resources and duration"""
    if not config.max_duration and not config.max_steps and not config.max_epochs:
        return None

    # Simple estimation (would need pricing data for real costs)
    total_gpus = config.num_nodes * config.resources.gpu_count
    estimated_hours = 1.0  # Placeholder

    return {
        "currency": "USD",
        "estimated_cost": total_gpus * estimated_hours * 0.50,  # Placeholder rate
        "gpu_hours": total_gpus * estimated_hours,
    }


@router.get("/templates")
async def list_training_templates(
    framework: Optional[TrainingBackend] = Query(None, description="Filter by framework"),
    current_user: User = Depends(get_current_user),
):
    """
    List training job templates

    Returns predefined training configurations for common use cases.
    """
    templates = [
        {
            "id": "pytorch-image-classification",
            "name": "Image Classification (PyTorch)",
            "framework": "pytorch",
            "strategy": "ddp",
            "description": "Train an image classifier using PyTorch DDP",
            "entry_point": "train.py",
            "hyperparameters": {
                "model": "resnet50",
                "batch_size": 32,
                "epochs": 100,
                "lr": 0.1,
                "momentum": 0.9,
                "weight_decay": 0.0001,
            },
            "requirements": ["torch", "torchvision", "tensorboard"],
        },
        {
            "id": "pytorch-llm-finetuning",
            "name": "LLM Fine-tuning (PyTorch)",
            "framework": "pytorch",
            "strategy": "deepspeed",
            "description": "Fine-tune a large language model with DeepSpeed",
            "entry_point": "finetune.py",
            "hyperparameters": {
                "model": "meta-llama/Llama-2-7b-hf",
                "batch_size": 4,
                "max_steps": 10000,
                "lr": 1e-5,
                "warmup_steps": 1000,
            },
            "requirements": ["torch", "transformers", "deepspeed"],
        },
        {
            "id": "tf-image-classification",
            "name": "Image Classification (TensorFlow)",
            "framework": "tensorflow",
            "strategy": "mirrored",
            "description": "Train an image classifier using TensorFlow",
            "entry_point": "train.py",
            "hyperparameters": {
                "model": "resnet50",
                "batch_size": 32,
                "epochs": 100,
                "lr": 0.001,
            },
            "requirements": ["tensorflow", "tensorboard"],
        },
        {
            "id": "tf-transformer",
            "name": "Transformer Training (TensorFlow)",
            "framework": "tensorflow",
            "strategy": "tpu",
            "description": "Train a transformer model on TPUs",
            "entry_point": "train.py",
            "hyperparameters": {
                "model": "bert-base",
                "batch_size": 32,
                "max_steps": 100000,
                "lr": 1e-4,
            },
            "requirements": ["tensorflow", "tensorflow-text"],
        },
    ]

    if framework:
        templates = [t for t in templates if t["framework"] == framework.value]

    return templates
