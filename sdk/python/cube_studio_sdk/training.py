"""
Training module for SDK

Provides TrainingJob class for managing model training.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .client import CubeStudioClient

logger = logging.getLogger(__name__)


class TrainingStatus(str, Enum):
    """Training job status"""
    PENDING = "pending"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrainingMetrics:
    """Training metrics"""
    epoch: int
    loss: float
    accuracy: Optional[float] = None
    learning_rate: Optional[float] = None
    timestamp: datetime = None


@dataclass
class TrainingConfig:
    """Training configuration"""
    # Model
    model_type: str
    model_params: Dict[str, Any] = None
    
    # Data
    dataset_id: str = None
    validation_split: float = 0.2
    batch_size: int = 32
    
    # Training
    epochs: int = 10
    learning_rate: float = 0.001
    optimizer: str = "adam"
    loss_function: str = None
    
    # Resources
    gpu_count: int = 1
    gpu_type: str = "T4"
    cpu_count: int = 4
    memory_gb: int = 16
    
    # Hyperparameters
    hyperparameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.model_params is None:
            self.model_params = {}
        if self.hyperparameters is None:
            self.hyperparameters = {}


class TrainingJob:
    """
    Training job for managing model training
    
    Example:
        ```python
        async with CubeStudioClient() as client:
            job = TrainingJob(
                client=client,
                name="my-model-training",
                config=TrainingConfig(
                    model_type="resnet50",
                    dataset_id="dataset-123",
                    epochs=50,
                    batch_size=64,
                )
            )
            
            # Submit job
            await job.submit()
            
            # Wait for completion
            await job.wait_for_completion()
            
            # Get metrics
            metrics = await job.get_metrics()
        ```
    """

    def __init__(
        self,
        client: CubeStudioClient,
        name: str,
        config: TrainingConfig,
        job_id: Optional[str] = None,
        status: TrainingStatus = TrainingStatus.PENDING,
        created_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        error: Optional[str] = None,
    ):
        self.client = client
        self.name = name
        self.config = config
        self.job_id = job_id
        self.status = status
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.error = error

    async def submit(self) -> "TrainingJob":
        """Submit the training job"""
        response = await self.client._client.post(
            "/api/v1/training/jobs",
            json={
                "name": self.name,
                "model_type": self.config.model_type,
                "dataset_id": self.config.dataset_id,
                "config": {
                    "model_params": self.config.model_params,
                    "validation_split": self.config.validation_split,
                    "batch_size": self.config.batch_size,
                    "epochs": self.config.epochs,
                    "learning_rate": self.config.learning_rate,
                    "optimizer": self.config.optimizer,
                    "loss_function": self.config.loss_function,
                    "hyperparameters": self.config.hyperparameters,
                },
                "resources": {
                    "gpu_count": self.config.gpu_count,
                    "gpu_type": self.config.gpu_type,
                    "cpu_count": self.config.cpu_count,
                    "memory_gb": self.config.memory_gb,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        
        self.job_id = data["job_id"]
        self.status = TrainingStatus(data.get("status", "pending"))
        self.created_at = datetime.now()
        
        return self

    async def refresh(self) -> "TrainingJob":
        """Refresh job status from server"""
        if not self.job_id:
            raise ValueError("Job not submitted yet")
            
        data = await self.client.get_training_job(self.job_id)
        
        self.status = TrainingStatus(data.get("status", self.status))
        self.started_at = datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
        self.completed_at = datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        self.error = data.get("error")
        
        return self

    async def stop(self) -> bool:
        """Stop the training job"""
        if not self.job_id:
            raise ValueError("Job not submitted yet")
            
        response = await self.client._client.post(f"/api/v1/training/jobs/{self.job_id}/stop")
        response.raise_for_status()
        
        self.status = TrainingStatus.STOPPING
        return True

    async def wait_for_completion(
        self,
        poll_interval: float = 10.0,
        timeout: Optional[float] = None,
    ) -> "TrainingJob":
        """Wait for training to complete"""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            await self.refresh()
            
            if self.status == TrainingStatus.COMPLETED:
                return self
            elif self.status in (TrainingStatus.FAILED, TrainingStatus.STOPPED):
                if self.error:
                    raise RuntimeError(f"Training failed: {self.error}")
                return self
            
            # Check timeout
            if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
                raise TimeoutError(f"Training job {self.job_id} timed out")
            
            await asyncio.sleep(poll_interval)

    async def get_metrics(self) -> List[TrainingMetrics]:
        """Get training metrics"""
        if not self.job_id:
            raise ValueError("Job not submitted yet")
            
        response = await self.client._client.get(
            f"/api/v1/training/jobs/{self.job_id}/metrics"
        )
        response.raise_for_status()
        
        metrics_data = response.json()
        return [
            TrainingMetrics(
                epoch=m["epoch"],
                loss=m["loss"],
                accuracy=m.get("accuracy"),
                learning_rate=m.get("learning_rate"),
                timestamp=datetime.fromisoformat(m["timestamp"]) if m.get("timestamp") else None,
            )
            for m in metrics_data
        ]

    async def get_logs(self, tail_lines: int = 100) -> str:
        """Get training logs"""
        if not self.job_id:
            raise ValueError("Job not submitted yet")
            
        response = await self.client._client.get(
            f"/api/v1/training/jobs/{self.job_id}/logs",
            params={"tail": tail_lines},
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("logs", "")

    async def save_model(
        self,
        model_name: str,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Save the trained model"""
        if self.status != TrainingStatus.COMPLETED:
            raise ValueError("Training must be completed before saving model")
            
        response = await self.client._client.post(
            "/api/v1/models/register",
            json={
                "name": model_name,
                "version": version,
                "training_job_id": self.job_id,
                "metadata": metadata or {},
            },
        )
        response.raise_for_status()
        
        return response.json()

    def __repr__(self) -> str:
        return f"TrainingJob(job_id={self.job_id}, name={self.name}, status={self.status})"
