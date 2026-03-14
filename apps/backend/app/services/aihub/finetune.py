"""
AIHub Model Fine-tuning Service

Handles fine-tuning of pre-trained models from AIHub.
Supports various fine-tuning methods:
- Full fine-tuning
- LoRA (Low-Rank Adaptation)
- QLoRA (Quantized LoRA)
- Adapter-based fine-tuning
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from app.services.aihub.registry import AIHubModel, ModelCategory, get_model
from app.services.experiment.mlflow_client import MLflowClient
from app.core.config import settings


class FinetuneMethod(str, Enum):
    """Fine-tuning methods"""

    FULL = "full"  # Full parameter fine-tuning
    LORA = "lora"  # Low-Rank Adaptation
    QLORA = "qlora"  # Quantized LoRA
    ADAPTER = "adapter"  # Adapter-based
    PROMPT_TUNING = "prompt_tuning"  # Prompt tuning
    PREFIX_TUNING = "prefix_tuning"  # Prefix tuning


class FinetuneStatus(str, Enum):
    """Fine-tuning job status"""

    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    EVALUATING = "evaluating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FinetuneConfig:
    """Fine-tuning configuration templates"""

    # LLM fine-tuning configs
    LLM_LORA_CONFIG = {
        "method": FinetuneMethod.LORA,
        "r": 16,  # LoRA rank
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
        "bias": "none",
        "task_type": "CAUSAL_LM",
    }

    LLM_QLORA_CONFIG = {
        "method": FinetuneMethod.QLORA,
        "r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "target_modules": ["q_proj", "v_proj", "k_proj", "o_proj"],
        "bias": "none",
        "task_type": "CAUSAL_LM",
        "load_in_4bit": True,
        "bnb_4bit_use_double_quant": True,
        "bnb_4bit_quant_type": "nf4",
    }

    # Vision model fine-tuning configs
    VISION_FULL_CONFIG = {
        "method": FinetuneMethod.FULL,
        "learning_rate": 1e-5,
        "weight_decay": 0.01,
        "warmup_steps": 1000,
    }

    VISION_LORA_CONFIG = {
        "method": FinetuneMethod.LORA,
        "r": 8,
        "lora_alpha": 16,
        "target_modules": ["q_proj", "v_proj"],
    }

    # Embedding model fine-tuning
    EMBEDDING_ADAPTER_CONFIG = {
        "method": FinetuneMethod.ADAPTER,
        "adapter_size": 64,
        "learning_rate": 1e-4,
    }


class FinetuneJob:
    """Fine-tuning job representation"""

    def __init__(
        self,
        job_id: str,
        base_model: str,
        dataset_id: str,
        config: Dict[str, Any],
        user_id: int,
    ):
        self.job_id = job_id
        self.base_model = base_model
        self.dataset_id = dataset_id
        self.config = config
        self.user_id = user_id
        self.status = FinetuneStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.metrics: Dict[str, float] = {}
        self.output_model_uri: Optional[str] = None
        self.mlflow_run_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "job_id": self.job_id,
            "base_model": self.base_model,
            "dataset_id": self.dataset_id,
            "config": self.config,
            "user_id": self.user_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metrics": self.metrics,
            "output_model_uri": self.output_model_uri,
            "mlflow_run_id": self.mlflow_run_id,
        }


class FinetuneService:
    """
    Service for managing model fine-tuning jobs.
    """

    def __init__(self):
        self.jobs: Dict[str, FinetuneJob] = {}
        self.mlflow_client = MLflowClient()

    async def create_finetune_job(
        self,
        base_model: str,
        dataset_id: str,
        config: Dict[str, Any],
        user_id: int,
        project_id: Optional[int] = None,
    ) -> FinetuneJob:
        """
        Create a new fine-tuning job.

        Args:
            base_model: AIHub model ID to fine-tune
            dataset_id: Training dataset ID
            config: Fine-tuning configuration
            user_id: User creating the job
            project_id: MLflow project ID

        Returns:
            Created fine-tuning job
        """
        # Validate base model exists
        model = get_model(base_model)
        if not model:
            raise ValueError(f"Model {base_model} not found in AIHub")

        # Generate job ID
        job_id = f"ft_{base_model}_{int(datetime.utcnow().timestamp())}"

        # Create job
        job = FinetuneJob(
            job_id=job_id,
            base_model=base_model,
            dataset_id=dataset_id,
            config=config,
            user_id=user_id,
        )

        # Validate config
        self._validate_finetune_config(model, config)

        # Store job
        self.jobs[job_id] = job

        # Create MLflow experiment if provided
        if project_id:
            experiment_name = f"finetune_{base_model}"
            mlflow_exp = await self.mlflow_client.get_or_create_experiment(
                experiment_name, project_id
            )
            job.mlflow_run_id = mlflow_exp.id

        return job

    def _validate_finetune_config(
        self, model: AIHubModel, config: Dict[str, Any]
    ) -> None:
        """Validate fine-tuning configuration for the model"""
        method = config.get("method", FinetuneMethod.FULL)

        # Check if method is supported for this model category
        if model.category in [ModelCategory.LLM, ModelCategory.EMBEDDING]:
            supported_methods = [
                FinetuneMethod.FULL,
                FinetuneMethod.LORA,
                FinetuneMethod.QLORA,
            ]
        elif model.category in [
            ModelCategory.IMAGE_CLASSIFICATION,
            ModelCategory.OBJECT_DETECTION,
            ModelCategory.SEGMENTATION,
        ]:
            supported_methods = [FinetuneMethod.FULL, FinetuneMethod.LORA]
        else:
            supported_methods = [FinetuneMethod.FULL]

        if method not in supported_methods:
            raise ValueError(
                f"Method {method} not supported for {model.category}. "
                f"Supported: {supported_methods}"
            )

        # Validate hyperparameters
        if "epochs" in config and config["epochs"] > 100:
            raise ValueError("Epochs cannot exceed 100")
        if "batch_size" in config and config["batch_size"] > 256:
            raise ValueError("Batch size cannot exceed 256")
        if "learning_rate" in config and config["learning_rate"] > 1e-2:
            raise ValueError("Learning rate too high (max: 0.01)")

    async def start_finetune_job(self, job_id: str) -> FinetuneJob:
        """
        Start a fine-tuning job.

        Args:
            job_id: Job ID to start

        Returns:
            Updated job
        """
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status != FinetuneStatus.PENDING:
            raise ValueError(f"Job {job_id} is not in PENDING status")

        job.status = FinetuneStatus.PREPARING
        job.started_at = datetime.utcnow()

        # Start training in background
        asyncio.create_task(self._run_finetune_job(job))

        return job

    async def _run_finetune_job(self, job: FinetuneJob) -> None:
        """
        Run the fine-tuning job (background task).

        In production, this would:
        1. Submit training job to Kubernetes (using PyTorchJob)
        2. Monitor training progress
        3. Update job status and metrics
        4. Save final model to MLflow
        """
        try:
            job.status = FinetuneStatus.TRAINING

            # Simulate training progress
            # In production, this would poll the training pod
            await asyncio.sleep(2)

            job.metrics = {
                "train_loss": 0.234,
                "train_accuracy": 0.891,
                "val_loss": 0.312,
                "val_accuracy": 0.856,
                "epoch": 3,
            }

            job.status = FinetuneStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.output_model_uri = f"s3://models/finetuned/{job.job_id}"

            # Log to MLflow
            if job.mlflow_run_id:
                await self.mlflow_client.log_metrics(
                    job.mlflow_run_id, job.metrics
                )
                await self.mlflow_client.log_model(
                    job.mlflow_run_id,
                    model_uri=job.output_model_uri,
                    model_name=f"finetuned_{job.base_model}",
                )

        except Exception as e:
            job.status = FinetuneStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error = str(e)

    async def get_finetune_job(self, job_id: str) -> Optional[FinetuneJob]:
        """Get fine-tuning job by ID"""
        return self.jobs.get(job_id)

    async def list_finetune_jobs(
        self,
        user_id: Optional[int] = None,
        base_model: Optional[str] = None,
        status: Optional[FinetuneStatus] = None,
    ) -> List[FinetuneJob]:
        """List fine-tuning jobs with filters"""
        jobs = list(self.jobs.values())

        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]
        if base_model:
            jobs = [j for j in jobs if j.base_model == base_model]
        if status:
            jobs = [j for j in jobs if j.status == status]

        return jobs

    async def cancel_finetune_job(self, job_id: str) -> bool:
        """Cancel a fine-tuning job"""
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.status in [FinetuneStatus.PENDING, FinetuneStatus.PREPARING]:
            job.status = FinetuneStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            return True

        # In production, would send cancellation signal to training pod
        if job.status == FinetuneStatus.TRAINING:
            job.status = FinetuneStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            return True

        return False

    async def delete_finetune_job(self, job_id: str, user_id: int) -> bool:
        """Delete a fine-tuning job"""
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.user_id != user_id:
            raise PermissionError("Not authorized to delete this job")

        del self.jobs[job_id]
        return True

    def get_finetune_templates(self, model_id: str) -> List[Dict[str, Any]]:
        """
        Get recommended fine-tuning templates for a model.

        Args:
            model_id: AIHub model ID

        Returns:
            List of template configurations
        """
        model = get_model(model_id)
        if not model:
            return []

        templates = []

        if model.category == ModelCategory.LLM:
            templates.append(
                {
                    "name": "LoRA Fine-tuning",
                    "description": "Low-Rank Adaptation for efficient fine-tuning",
                    "config": FinetuneConfig.LLM_LORA_CONFIG,
                    "estimated_time": "2-4 hours",
                    "estimated_cost": "$5-10",
                }
            )
            templates.append(
                {
                    "name": "QLoRA Fine-tuning",
                    "description": "Quantized LoRA for lower memory usage",
                    "config": FinetuneConfig.LLM_QLORA_CONFIG,
                    "estimated_time": "3-6 hours",
                    "estimated_cost": "$3-7",
                }
            )

        elif model.category in [
            ModelCategory.IMAGE_CLASSIFICATION,
            ModelCategory.OBJECT_DETECTION,
            ModelCategory.SEGMENTATION,
        ]:
            templates.append(
                {
                    "name": "Full Fine-tuning",
                    "description": "Full parameter fine-tuning for best results",
                    "config": FinetuneConfig.VISION_FULL_CONFIG,
                    "estimated_time": "4-8 hours",
                    "estimated_cost": "$10-20",
                }
            )
            templates.append(
                {
                    "name": "LoRA Fine-tuning",
                    "description": "Low-Rank Adaptation for efficient fine-tuning",
                    "config": FinetuneConfig.VISION_LORA_CONFIG,
                    "estimated_time": "2-4 hours",
                    "estimated_cost": "$5-10",
                }
            )

        elif model.category == ModelCategory.EMBEDDING:
            templates.append(
                {
                    "name": "Adapter Fine-tuning",
                    "description": "Adapter-based fine-tuning",
                    "config": FinetuneConfig.EMBEDDING_ADAPTER_CONFIG,
                    "estimated_time": "1-2 hours",
                    "estimated_cost": "$2-5",
                }
            )

        return templates

    async def estimate_finetune_cost(
        self, model_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Estimate cost and time for fine-tuning.

        Args:
            model_id: AIHub model ID
            config: Fine-tuning configuration

        Returns:
            Cost and time estimates
        """
        model = get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Estimate based on model size and config
        epochs = config.get("epochs", 3)
        batch_size = config.get("batch_size", 16)

        # GPU hours estimate (simplified)
        if model.parameter_size:
            params_billions = float(model.parameter_size.replace("B", ""))
            base_hours = params_billions * epochs / 2
            if config.get("method") == FinetuneMethod.QLORA:
                base_hours *= 0.7
            elif config.get("method") == FinetuneMethod.LORA:
                base_hours *= 0.8

            gpu_hours = base_hours * (100 / batch_size)
        else:
            gpu_hours = 5.0

        # Cost estimate (using $1/GPU-hour)
        gpu_cost = gpu_hours * 1.0

        return {
            "estimated_gpu_hours": round(gpu_hours, 2),
            "estimated_cost_usd": round(gpu_cost, 2),
            "estimated_time_hours": round(gpu_hours * 0.8, 2),  # Assuming parallel training
            "recommended_gpu_type": self._get_recommended_gpu(model),
        }

    def _get_recommended_gpu(self, model: AIHubModel) -> str:
        """Get recommended GPU type for model"""
        if model.parameter_size:
            size = float(model.parameter_size.replace("B", ""))
            if size >= 30:
                return "A100 (80GB)"
            elif size >= 10:
                return "A100 (40GB)"
            elif size >= 7:
                return "V100 (32GB)"
            else:
                return "T4 (16GB)"
        return "T4 (16GB)"


# Global service instance
finetune_service = FinetuneService()
