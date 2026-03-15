"""
Fine-tuning Pipeline Models

Models for managing LLM fine-tuning pipelines including
data preparation, training, evaluation, registration, and deployment.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinetunePipeline(Base):
    """Fine-tuning pipeline main table"""
    __tablename__ = "finetune_pipelines"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic information
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Base model configuration
    base_model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # From AIHub
    base_model_name: Mapped[str] = mapped_column(String(256), nullable=False)
    base_model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # llama, qwen, baichuan, etc.

    # Fine-tuning method
    finetune_method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # full, lora, qlora, p-tuning, prefix-tuning
    lora_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For LoRA
    lora_alpha: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lora_dropout: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Data configuration
    dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Training dataset
    eval_dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    test_dataset_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Training hyperparameters
    learning_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    num_epochs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warmup_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_decay: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gradient_accumulation_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Resource configuration
    gpu_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gpu_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distributed_backend: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ddsp, deepspeed

    # Output configuration
    output_dir: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    save_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    save_total_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Evaluation configuration
    eval_steps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    eval_strategy: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # steps, epoch, no

    # Pipeline stages
    current_stage: Mapped[str] = mapped_column(
        String(50), default="data_prep", index=True
    )  # data_prep, training, evaluation, registration, deployment, completed, failed

    # Stage statuses
    data_prep_status: Mapped[str] = mapped_column(String(20), default="pending")
    training_status: Mapped[str] = mapped_column(String(20), default="pending")
    evaluation_status: Mapped[str] = mapped_column(String(20), default="pending")
    registration_status: Mapped[str] = mapped_column(String(20), default="pending")
    deployment_status: Mapped[str] = mapped_column(String(20), default="pending")

    # Training job reference
    training_job_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Registered model reference
    registered_model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Deployment reference
    deployment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metrics
    train_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eval_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eval_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Tags and labels
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<FinetunePipeline {self.pipeline_id}:{self.name}>"


class FinetuneStage(Base):
    """Fine-tuning pipeline stage execution record"""
    __tablename__ = "finetune_stages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    stage_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    pipeline_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("finetune_pipelines.pipeline_id"), nullable=False, index=True
    )

    # Stage information
    stage_type: Mapped[str] = mapped_column(String(50), nullable=False)  # data_prep, training, evaluation, registration, deployment
    stage_name: Mapped[str] = mapped_column(String(256), nullable=False)

    # Stage configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed, cancelled

    # Results
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Artifacts
    output_artifacts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Retry information
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Dependencies
    depends_on: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # List of stage IDs

    def __repr__(self) -> str:
        return f"<FinetuneStage {self.stage_id}:{self.stage_type}>"


class FinetuneCheckpoint(Base):
    """Fine-tuning checkpoint record"""
    __tablename__ = "finetune_checkpoints"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    checkpoint_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    pipeline_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("finetune_pipelines.pipeline_id"), nullable=False, index=True
    )

    # Checkpoint information
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    epoch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metrics at checkpoint
    train_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eval_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Storage
    checkpoint_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Classification
    is_best: Mapped[bool] = mapped_column(Boolean, default=False)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FinetuneCheckpoint {self.checkpoint_id}:step{self.step}>"


class FinetuneMetric(Base):
    """Fine-tuning metric history"""
    __tablename__ = "finetune_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pipeline_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("finetune_pipelines.pipeline_id"), nullable=False, index=True
    )

    # Metric information
    step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    epoch: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metrics
    train_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    learning_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eval_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timing
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<FinetuneMetric {self.pipeline_id}:step{self.step}>"


class FinetuneTemplate(Base):
    """Fine-tuning pipeline template"""
    __tablename__ = "finetune_templates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    template_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Template information
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Template type
    template_type: Mapped[str] = mapped_column(String(50), nullable=False)  # instruction, sft, rlhf, pretrain

    # Supported model types
    supported_models: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Default configuration
    default_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Template schema (for validation)
    schema_: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, name="schema")

    # Visibility
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Ownership
    owner_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FinetuneTemplate {self.template_id}:{self.name}>"
