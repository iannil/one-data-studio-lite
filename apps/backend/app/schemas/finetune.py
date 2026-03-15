"""
Fine-tuning Schemas

Pydantic schemas for LLM fine-tuning pipeline management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Fine-tuning Pipeline Base Schemas
# =============================================================================

class FinetunePipelineBase(BaseModel):
    """Base fine-tuning pipeline schema"""
    name: str = Field(..., min_length=1, max_length=256, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")

    # Base model
    base_model_id: str = Field(..., description="Base model ID from AIHub")
    base_model_name: str = Field(..., description="Base model name")
    base_model_type: str = Field(..., description="Base model type")

    # Fine-tuning method
    finetune_method: str = Field(default="lora", description="Fine-tuning method: full, lora, qlora, p-tuning, prefix-tuning")
    lora_rank: Optional[int] = Field(None, ge=1, le=512, description="LoRA rank")
    lora_alpha: Optional[int] = Field(None, ge=1, description="LoRA alpha")
    lora_dropout: Optional[float] = Field(None, ge=0, le=1, description="LoRA dropout")

    # Data
    dataset_id: Optional[str] = Field(None, description="Training dataset ID")
    eval_dataset_id: Optional[str] = Field(None, description="Evaluation dataset ID")
    test_dataset_id: Optional[str] = Field(None, description="Test dataset ID")

    # Training hyperparameters
    learning_rate: Optional[float] = Field(None, gt=0, description="Learning rate")
    batch_size: Optional[int] = Field(None, gt=0, description="Batch size")
    num_epochs: Optional[int] = Field(None, gt=0, description="Number of epochs")
    max_steps: Optional[int] = Field(None, gt=0, description="Maximum training steps")
    warmup_steps: Optional[int] = Field(None, ge=0, description="Warmup steps")
    weight_decay: Optional[float] = Field(None, ge=0, description="Weight decay")
    gradient_accumulation_steps: Optional[int] = Field(None, ge=1, description="Gradient accumulation steps")

    # Resources
    gpu_type: Optional[str] = Field(None, description="GPU type")
    gpu_count: Optional[int] = Field(None, ge=1, description="GPU count")
    distributed_backend: Optional[str] = Field(None, description="Distributed backend: ddsp, deepspeed")

    # Output
    output_dir: Optional[str] = Field(None, description="Output directory")
    save_steps: Optional[int] = Field(None, gt=0, description="Save checkpoint every N steps")
    save_total_limit: Optional[int] = Field(None, ge=0, description="Total checkpoint limit")

    # Evaluation
    eval_steps: Optional[int] = Field(None, gt=0, description="Evaluation steps")
    eval_strategy: Optional[str] = Field(None, description="Evaluation strategy: steps, epoch, no")

    # Tags
    tags: Optional[List[str]] = Field(None, description="Pipeline tags")
    labels: Optional[Dict[str, str]] = Field(None, description="Pipeline labels")


class FinetunePipelineCreate(FinetunePipelineBase):
    """Schema for creating a fine-tuning pipeline"""
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    project_id: Optional[str] = Field(None, description="Project ID")


class FinetunePipelineUpdate(BaseModel):
    """Schema for updating a fine-tuning pipeline"""
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None


# =============================================================================
# Pipeline Response Schemas
# =============================================================================

class FinetunePipelineResponse(FinetunePipelineBase):
    """Schema for fine-tuning pipeline response"""
    id: str
    pipeline_id: str
    current_stage: str
    data_prep_status: str
    training_status: str
    evaluation_status: str
    registration_status: str
    deployment_status: str

    training_job_id: Optional[str] = None
    registered_model_id: Optional[str] = None
    model_version: Optional[str] = None
    deployment_id: Optional[str] = None

    train_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    eval_metrics: Optional[Dict[str, Any]] = None

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    owner_id: str
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class FinetunePipelineListResponse(BaseModel):
    """Schema for pipeline list response"""
    total: int
    items: List[FinetunePipelineResponse]


# =============================================================================
# Stage Schemas
# =============================================================================

class FinetuneStageBase(BaseModel):
    """Base pipeline stage schema"""
    stage_type: str = Field(..., description="Stage type")
    stage_name: str = Field(..., description="Stage name")
    config: Optional[Dict[str, Any]] = None
    max_retries: int = Field(default=3, ge=0, description="Maximum retries")


class FinetuneStageResponse(FinetuneStageBase):
    """Schema for stage response"""
    id: str
    stage_id: str
    pipeline_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    output_artifacts: Optional[List[Any]] = None
    output_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    retry_count: int
    depends_on: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Checkpoint Schemas
# =============================================================================

class FinetuneCheckpointResponse(BaseModel):
    """Schema for checkpoint response"""
    id: str
    checkpoint_id: str
    pipeline_id: str
    step: int
    epoch: Optional[int] = None
    train_loss: Optional[float] = None
    eval_loss: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None
    checkpoint_path: str
    file_size_bytes: Optional[int] = None
    is_best: bool
    is_latest: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Template Schemas
# =============================================================================

class FinetuneTemplateBase(BaseModel):
    """Base fine-tuning template schema"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    template_type: str = Field(..., description="Template type: instruction, sft, rlhf, pretrain")
    supported_models: Optional[List[str]] = None
    default_config: Dict[str, Any] = Field(..., description="Default configuration")
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema", description="Template schema")


class FinetuneTemplateCreate(FinetuneTemplateBase):
    """Schema for creating a template"""
    is_public: bool = Field(default=False, description="Is template public")


class FinetuneTemplateUpdate(BaseModel):
    """Schema for updating a template"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    default_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None


class FinetuneTemplateResponse(FinetuneTemplateBase):
    """Schema for template response"""
    id: str
    template_id: str
    is_public: bool
    is_system: bool
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Action Schemas
# =============================================================================

class FinetuneActionRequest(BaseModel):
    """Schema for pipeline action request"""
    action: str = Field(..., description="Action: start, stop, retry, approve, reject")


class FinetuneActionResponse(BaseModel):
    """Schema for action response"""
    pipeline_id: str
    action: str
    status: str
    message: str


# =============================================================================
# Execution Schemas
# =============================================================================

class FinetuneExecuteRequest(BaseModel):
    """Schema for pipeline execution request"""
    pipeline_id: str
    stage: Optional[str] = Field(None, description="Start from specific stage")
    auto_advance: bool = Field(default=True, description="Automatically advance through stages")
    notify_on_complete: bool = Field(default=False, description="Notify on completion")


class FinetuneExecuteResponse(BaseModel):
    """Schema for execution response"""
    execution_id: str
    pipeline_id: str
    status: str
    current_stage: str
    message: str
