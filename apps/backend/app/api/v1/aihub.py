"""
AIHub API Endpoints

REST API for the AI model marketplace, fine-tuning, and deployment.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.aihub import (
    list_models,
    get_model,
    get_categories,
    get_frameworks,
    get_model_stats,
    ModelCategory,
    ModelFramework,
    finetune_service,
    aihub_deployer,
    FinetuneMethod,
    FinetuneStatus,
    DeploymentStatus,
)

router = APIRouter(prefix="/aihub", tags=["aihub"])

# Request/Response Models


class ModelListItem(BaseModel):
    """Model item in list response"""

    id: str
    name: str
    category: str
    framework: str
    description: Optional[str]
    tags: Optional[List[str]]
    parameter_size: Optional[str]
    provider: Optional[str]
    capabilities: Optional[dict]


class ModelDetail(BaseModel):
    """Full model details"""

    id: str
    name: str
    category: str
    framework: str
    source: str
    license: str
    description: Optional[str]
    tags: Optional[List[str]]
    tasks: Optional[List[str]]
    languages: Optional[List[str]]
    parameter_size: Optional[str]
    gpu_memory_mb: Optional[int]
    cpu_cores: Optional[int]
    ram_mb: Optional[int]
    capabilities: Optional[dict]
    deploy_template: Optional[str]
    default_inference_image: Optional[str]
    provider: Optional[str]
    paper_url: Optional[str]
    demo_url: Optional[str]


class DeploymentCreateRequest(BaseModel):
    """Request to create deployment"""

    model_id: str = Field(..., description="AIHub model ID")
    name: str = Field(..., min_length=1, max_length=64, description="Deployment name")
    replicas: int = Field(1, ge=1, le=10, description="Number of replicas")
    gpu_enabled: bool = Field(True, description="Enable GPU")
    gpu_type: Optional[str] = Field(None, description="GPU type (e.g., A100, V100, T4)")
    gpu_count: int = Field(1, ge=1, le=8, description="Number of GPUs per replica")
    autoscaling_enabled: bool = Field(True, description="Enable autoscaling")
    autoscaling_min: int = Field(1, ge=1, description="Min replicas for autoscaling")
    autoscaling_max: int = Field(5, le=10, description="Max replicas for autoscaling")


class FinetuneCreateRequest(BaseModel):
    """Request to create fine-tuning job"""

    base_model: str = Field(..., description="AIHub model ID to fine-tune")
    dataset_id: str = Field(..., description="Training dataset ID")
    method: str = Field(FinetuneMethod.LORA, description="Fine-tuning method")
    epochs: int = Field(3, ge=1, le=100, description="Number of training epochs")
    batch_size: int = Field(16, ge=1, le=256, description="Training batch size")
    learning_rate: float = Field(2e-4, ge=0, le=0.01, description="Learning rate")
    use_template: bool = Field(True, description="Use recommended template config")
    custom_config: Optional[dict] = Field(None, description="Custom config overrides")


class FinetuneCostRequest(BaseModel):
    """Request for cost estimation"""

    model_id: str = Field(..., description="AIHub model ID")
    method: str = Field(FinetuneMethod.LORA, description="Fine-tuning method")
    epochs: int = Field(3, ge=1, le=100, description="Number of epochs")
    batch_size: int = Field(16, ge=1, le=256, description="Batch size")


# Model Market Endpoints


@router.get("/models", response_model=List[ModelListItem])
async def list_aihub_models(
    category: Optional[str] = Query(None, description="Filter by category"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    task: Optional[str] = Query(None, description="Filter by task"),
    search: Optional[str] = Query(None, description="Search in name/description/tags"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """
    List models in AIHub marketplace.

    Supports filtering by category, framework, task, and text search.
    """
    cat = ModelCategory(category) if category else None
    fw = ModelFramework(framework) if framework else None

    models = list_models(
        category=cat,
        framework=fw,
        task=task,
        search=search,
        limit=limit,
    )

    return [
        {
            "id": m.id,
            "name": m.name,
            "category": m.category.value,
            "framework": m.framework.value,
            "description": m.description,
            "tags": m.tags,
            "parameter_size": m.parameter_size,
            "provider": m.provider,
            "capabilities": {
                "cuda_supported": m.capabilities.cuda_supported if m.capabilities else False,
                "cpu_inference": m.capabilities.cpu_inference if m.capabilities else False,
                "quantization_available": m.capabilities.quantization_available if m.capabilities else False,
                "streaming": m.capabilities.streaming if m.capabilities else False,
            }
        }
        for m in models
    ]


@router.get("/models/{model_id}", response_model=ModelDetail)
async def get_aihub_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get detailed information about a specific model."""
    model = get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )

    return {
        "id": model.id,
        "name": model.name,
        "category": model.category.value,
        "framework": model.framework.value,
        "source": model.source,
        "license": model.license.value,
        "description": model.description,
        "tags": model.tags,
        "tasks": model.tasks,
        "languages": model.languages,
        "parameter_size": model.parameter_size,
        "gpu_memory_mb": model.gpu_memory_mb,
        "cpu_cores": model.cpu_cores,
        "ram_mb": model.ram_mb,
        "capabilities": {
            "cuda_supported": model.capabilities.cuda_supported if model.capabilities else False,
            "cpu_inference": model.capabilities.cpu_inference if model.capabilities else False,
            "quantization_available": model.capabilities.quantization_available if model.capabilities else False,
            "distributed_training": model.capabilities.distributed_training if model.capabilities else False,
            "streaming": model.capabilities.streaming if model.capabilities else False,
            "function_calling": model.capabilities.function_calling if model.capabilities else False,
            "vision": model.capabilities.vision if model.capabilities else False,
            "code": model.capabilities.code if model.capabilities else False,
        }
        if model.capabilities else None,
        "deploy_template": model.deploy_template,
        "default_inference_image": model.default_inference_image,
        "provider": model.provider,
        "paper_url": model.paper_url,
        "demo_url": model.demo_url,
    }


@router.get("/categories")
async def list_model_categories(
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """Get all model categories."""
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in get_categories()]


@router.get("/frameworks")
async def list_model_frameworks(
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Get all model frameworks."""
    return [f.value for f in get_frameworks()]


@router.get("/stats")
async def get_marketplace_stats(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get AIHub marketplace statistics."""
    return get_model_stats()


@router.get("/models/{model_id}/template")
async def get_deployment_template(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get recommended deployment template for a model."""
    template = aihub_deployer.get_deployment_template(model_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found"
        )
    return template


# Deployment Endpoints


@router.post("/deployments")
async def create_model_deployment(
    request: DeploymentCreateRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new model deployment.

    Deploys the specified model with the given configuration.
    """
    config = {
        "replicas": request.replicas,
        "gpu_enabled": request.gpu_enabled,
        "gpu_type": request.gpu_type,
        "gpu_count": request.gpu_count,
        "autoscaling": {
            "enabled": request.autoscaling_enabled,
            "min_replicas": request.autoscaling_min,
            "max_replicas": request.autoscaling_max,
        }
    }

    deployment = await aihub_deployer.create_deployment(
        model_id=request.model_id,
        name=request.name,
        config=config,
        user_id=current_user.id,
    )

    return deployment.to_dict()


@router.get("/deployments")
async def list_deployments(
    model_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List deployments for the current user."""
    deployments = await aihub_deployer.list_deployments(
        user_id=current_user.id,
        model_id=model_id,
        status=DeploymentStatus(status) if status else None,
    )
    return [d.to_dict() for d in deployments]


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get deployment details."""
    deployment = await aihub_deployer.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    return deployment.to_dict()


@router.post("/deployments/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Stop a running deployment."""
    success = await aihub_deployer.stop_deployment(deployment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop deployment {deployment_id}"
        )
    return {"stopped": True, "deployment_id": deployment_id}


@router.post("/deployments/{deployment_id}/start")
async def start_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start a stopped deployment."""
    success = await aihub_deployer.start_deployment(deployment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start deployment {deployment_id}"
        )
    return {"started": True, "deployment_id": deployment_id}


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a deployment."""
    success = await aihub_deployer.delete_deployment(deployment_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete deployment {deployment_id}"
        )
    return {"deleted": True, "deployment_id": deployment_id}


@router.post("/deployments/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: str,
    replicas: int = Query(..., ge=1, le=10),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Scale a deployment to specified replica count."""
    deployment = await aihub_deployer.scale_deployment(deployment_id, replicas)
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    return deployment.to_dict()


@router.get("/deployments/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    lines: int = Query(100, ge=10, le=1000),
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """Get deployment logs."""
    return await aihub_deployer.get_deployment_logs(deployment_id, lines)


@router.get("/deployments/{deployment_id}/metrics")
async def get_deployment_metrics(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get deployment metrics."""
    return await aihub_deployer.get_deployment_metrics(deployment_id)


@router.post("/deployments/{deployment_id}/predict")
async def predict(
    deployment_id: str,
    inputs: dict,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Make a prediction using a deployed model."""
    return await aihub_deployer.predict(deployment_id, inputs)


# Fine-tuning Endpoints


@router.get("/models/{model_id}/finetune-templates")
async def get_finetune_templates(
    model_id: str,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """Get recommended fine-tuning templates for a model."""
    templates = finetune_service.get_finetune_templates(model_id)
    if not templates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No templates found for model {model_id}"
        )
    return templates


@router.post("/finetune/cost-estimate")
async def estimate_finetune_cost(
    request: FinetuneCostRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Estimate cost and time for fine-tuning."""
    config = {
        "method": request.method,
        "epochs": request.epochs,
        "batch_size": request.batch_size,
    }
    return await finetune_service.estimate_finetune_cost(request.model_id, config)


@router.post("/finetune/jobs")
async def create_finetune_job(
    request: FinetuneCreateRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new fine-tuning job."""
    # Build config
    config = {
        "method": request.method,
        "epochs": request.epochs,
        "batch_size": request.batch_size,
        "learning_rate": request.learning_rate,
    }

    # Use template if requested
    if request.use_template:
        templates = finetune_service.get_finetune_templates(request.base_model)
        if templates:
            template_config = templates[0].get("config", {})
            config.update(template_config)

    # Apply custom overrides
    if request.custom_config:
        config.update(request.custom_config)

    job = await finetune_service.create_finetune_job(
        base_model=request.base_model,
        dataset_id=request.dataset_id,
        config=config,
        user_id=current_user.id,
    )

    return job.to_dict()


@router.get("/finetune/jobs")
async def list_finetune_jobs(
    base_model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List fine-tuning jobs for the current user."""
    jobs = await finetune_service.list_finetune_jobs(
        user_id=current_user.id,
        base_model=base_model,
        status=FinetuneStatus(status) if status else None,
    )
    return [j.to_dict() for j in jobs]


@router.get("/finetune/jobs/{job_id}")
async def get_finetune_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get fine-tuning job details."""
    job = await finetune_service.get_finetune_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job.to_dict()


@router.post("/finetune/jobs/{job_id}/start")
async def start_finetune_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Start a fine-tuning job."""
    job = await finetune_service.start_finetune_job(job_id)
    return job.to_dict()


@router.post("/finetune/jobs/{job_id}/cancel")
async def cancel_finetune_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a fine-tuning job."""
    success = await finetune_service.cancel_finetune_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel job {job_id}"
        )
    return {"cancelled": True, "job_id": job_id}


@router.delete("/finetune/jobs/{job_id}")
async def delete_finetune_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a fine-tuning job."""
    success = await finetune_service.delete_finetune_job(job_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete job {job_id}"
        )
    return {"deleted": True, "job_id": job_id}
