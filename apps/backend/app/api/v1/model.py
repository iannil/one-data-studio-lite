"""
Model Management API endpoints

REST API for MLflow model registry and model serving.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.model import (
    ModelRegistryService,
    ModelServingService,
    get_model_registry_service,
    get_model_serving_service,
)

router = APIRouter(prefix="/models", tags=["models"])


# Request/Response Schemas
class ModelRegisterRequest(BaseModel):
    """Request to register a model"""
    name: str = Field(..., description="Model name")
    run_id: str = Field(..., description="Run ID that produced the model")
    artifact_path: str = Field(..., description="Path to model artifact")
    model_type: str = Field("sklearn", description="Model framework type")
    description: Optional[str] = Field(None, description="Model description")
    tags: Optional[Dict[str, str]] = Field(None, description="Model tags")


class ModelUpdateRequest(BaseModel):
    """Request to update a model"""
    description: Optional[str] = Field(None, description="New description")


class ModelStageTransitionRequest(BaseModel):
    """Request to transition model stage"""
    stage: str = Field(..., description="Target stage: Staging, Production, Archived, None")
    archive_existing_versions: bool = Field(False, description="Archive existing versions in stage")


class DeploymentCreateRequest(BaseModel):
    """Request to create a deployment"""
    name: str = Field(..., description="Deployment name")
    model_name: str = Field(..., description="Registered model name")
    model_version: str = Field(..., description="Model version")
    replicas: int = Field(1, ge=1, le=10, description="Number of replicas")
    gpu_enabled: bool = Field(False, description="Enable GPU")
    gpu_type: Optional[str] = Field(None, description="GPU type (e.g., nvidia.com/gpu)")
    gpu_count: int = Field(1, ge=0, le=8, description="Number of GPUs")
    cpu: str = Field("1", description="CPU request per replica")
    memory: str = Field("2Gi", description="Memory request per replica")
    endpoint: Optional[str] = Field(None, description="Custom endpoint name")
    traffic_percentage: int = Field(100, ge=0, le=100, description="Traffic percentage")
    framework: str = Field("sklearn", description="Model framework")
    autoscaling_enabled: bool = Field(False, description="Enable HPA")
    autoscaling_min: int = Field(1, ge=1, description="Min replicas for HPA")
    autoscaling_max: int = Field(3, ge=1, description="Max replicas for HPA")
    description: Optional[str] = Field(None, description="Deployment description")
    tags: Optional[Dict[str, str]] = Field(None, description="Deployment tags")


class DeploymentUpdateRequest(BaseModel):
    """Request to update a deployment"""
    replicas: Optional[int] = Field(None, ge=1, le=10)
    traffic_percentage: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None


class CanaryDeploymentRequest(BaseModel):
    """Request to create a canary deployment"""
    name: str = Field(..., description="Deployment name")
    model_name: str = Field(..., description="Model name")
    current_version: str = Field(..., description="Current stable version")
    new_version: str = Field(..., description="New canary version")
    canary_traffic_percentage: int = Field(10, ge=1, le=50, description="Traffic for canary")


# Helper
async def get_services() -> tuple:
    """Get service instances"""
    return (
        get_model_registry_service(),
        get_model_serving_service(),
    )


# Model Registry Endpoints

@router.get("/registered")
async def list_registered_models(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List all registered models

    Returns all registered models with latest version info.
    """
    registry_service, _ = await get_services()
    return await registry_service.list_models(search=search)


@router.post("/registered", status_code=status.HTTP_201_CREATED)
async def create_registered_model(
    name: str = Query(..., description="Model name"),
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new registered model

    Creates a new model in the registry (without version).
    """
    registry_service, _ = await get_services()

    try:
        model = await registry_service.create_registered_model(
            name=name,
            description=description,
            tags=tags,
        )
        return model
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create model: {str(e)}",
        )


@router.get("/registered/{name}")
async def get_registered_model(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get registered model details

    Returns model metadata with all versions.
    """
    registry_service, _ = await get_services()

    try:
        model = await registry_service.get_model(name)
        return model
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {name}",
        )


@router.delete("/registered/{name}")
async def delete_registered_model(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a registered model

    Deletes the model and all its versions.
    """
    registry_service, _ = await get_services()

    success = await registry_service.delete_model(name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete model",
        )

    return {"message": f"Model {name} deleted"}


@router.put("/registered/{name}/rename")
async def rename_registered_model(
    name: str,
    new_name: str = Query(..., description="New model name"),
    current_user: User = Depends(get_current_user),
):
    """
    Rename a registered model
    """
    registry_service, _ = await get_services()

    success = await registry_service.rename_model(name, new_name)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to rename model",
        )

    return {"message": f"Model renamed from {name} to {new_name}"}


@router.post("/versions", status_code=status.HTTP_201_CREATED)
async def register_model_version(
    request: ModelRegisterRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Register a model version

    Registers a model from a run as a new version.
    """
    registry_service, _ = await get_services()

    try:
        model_version = await registry_service.register_model(
            name=request.name,
            run_id=request.run_id,
            artifact_path=request.artifact_path,
            model_type=request.model_type,
            description=request.description,
            tags=request.tags,
        )
        return model_version
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register model: {str(e)}",
        )


@router.get("/versions/{name}/{version}")
async def get_model_version(
    name: str,
    version: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get model version details

    Returns version metadata with run info and artifacts.
    """
    registry_service, _ = await get_services()

    try:
        model_version = await registry_service.get_model_version(name, version)
        return model_version
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model version not found: {name}:{version}",
        )


@router.put("/versions/{name}/{version}")
async def update_model_version(
    name: str,
    version: str,
    request: ModelUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update model version

    Updates model version description.
    """
    registry_service, _ = await get_services()

    success = await registry_service.update_model_version(
        name=name,
        version=version,
        description=request.description,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update model version",
        )

    return await registry_service.get_model_version(name, version)


@router.delete("/versions/{name}/{version}")
async def delete_model_version(
    name: str,
    version: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a model version

    Deletes a specific model version.
    """
    registry_service, _ = await get_services()

    success = await registry_service.delete_model_version(name, version)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete model version",
        )

    return {"message": f"Model version {name}:{version} deleted"}


@router.post("/versions/{name}/{version}/stage")
async def transition_model_stage(
    name: str,
    version: str,
    request: ModelStageTransitionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Transition model version to a new stage

    Moves a model version to Staging, Production, or Archived.
    """
    registry_service, _ = await get_services()

    success = await registry_service.transition_model_stage(
        name=name,
        version=version,
        stage=request.stage,
        archive_existing_versions=request.archive_existing_versions,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to transition model stage",
        )

    return {"message": f"Model {name}:{version} transitioned to {request.stage}"}


@router.get("/versions/{name}/{version}/history")
async def get_model_stage_history(
    name: str,
    version: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get model stage transition history

    Returns the history of stage transitions for a model version.
    """
    registry_service, _ = await get_services()

    history = await registry_service.get_model_stage_history(name, version)
    return {
        "name": name,
        "version": version,
        "history": history,
    }


@router.get("/search")
async def search_models(
    filter_string: Optional[str] = None,
    max_results: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """
    Search registered models

    Returns models matching the search criteria.
    """
    registry_service, _ = await get_services()

    return await registry_service.search_models(
        filter_string=filter_string,
        max_results=max_results,
    )


# Deployment Endpoints

@router.get("/deployments")
async def list_deployments(
    model_name: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List all model deployments

    Returns all inference service deployments.
    """
    _, serving_service = await get_services()

    return await serving_service.list_deployments(
        model_name=model_name,
        status=status,
    )


@router.post("/deployments", status_code=status.HTTP_201_CREATED)
async def create_deployment(
    request: DeploymentCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new model deployment

    Deploys a model version as an inference service.
    """
    _, serving_service = await get_services()

    try:
        deployment = await serving_service.create_deployment(
            name=request.name,
            model_name=request.model_name,
            model_version=request.model_version,
            replicas=request.replicas,
            gpu_enabled=request.gpu_enabled,
            gpu_type=request.gpu_type,
            gpu_count=request.gpu_count,
            cpu=request.cpu,
            memory=request.memory,
            endpoint=request.endpoint,
            traffic_percentage=request.traffic_percentage,
            framework=request.framework,
            autoscaling_enabled=request.autoscaling_enabled,
            autoscaling_min=request.autoscaling_min,
            autoscaling_max=request.autoscaling_max,
            description=request.description,
            tags=request.tags,
            owner_id=current_user.id,
        )
        return deployment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create deployment: {str(e)}",
        )


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get deployment details

    Returns deployment metadata with model details.
    """
    _, serving_service = await get_services()

    try:
        deployment = await serving_service.get_deployment(deployment_id)
        return deployment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment not found: {deployment_id}",
        )


@router.put("/deployments/{deployment_id}")
async def update_deployment(
    deployment_id: str,
    request: DeploymentUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update deployment

    Updates deployment configuration.
    """
    _, serving_service = await get_services()

    try:
        deployment = await serving_service.update_deployment(
            deployment_id=deployment_id,
            replicas=request.replicas,
            traffic_percentage=request.traffic_percentage,
            description=request.description,
        )
        return deployment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update deployment: {str(e)}",
        )


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a deployment

    Removes the inference service deployment.
    """
    _, serving_service = await get_services()

    success = await serving_service.delete_deployment(deployment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete deployment",
        )

    return {"message": f"Deployment {deployment_id} deleted"}


@router.post("/deployments/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: str,
    replicas: int = Query(..., ge=1, le=10),
    current_user: User = Depends(get_current_user),
):
    """
    Scale a deployment

    Changes the number of replicas for a deployment.
    """
    _, serving_service = await get_services()

    try:
        success = await serving_service.scale_deployment(deployment_id, replicas)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to scale deployment",
            )
        return {"message": f"Deployment scaled to {replicas} replicas"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to scale deployment: {str(e)}",
        )


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(
    deployment_id: str,
    target_version: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Rollback a deployment

    Rolls back to a previous model version.
    """
    _, serving_service = await get_services()

    try:
        deployment = await serving_service.rollback_deployment(
            deployment_id=deployment_id,
            target_version=target_version,
        )
        return deployment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to rollback deployment: {str(e)}",
        )


@router.get("/deployments/{deployment_id}/metrics")
async def get_deployment_metrics(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get deployment metrics

    Returns metrics like requests, latency, error rate, resource usage.
    """
    _, serving_service = await get_services()

    try:
        return await serving_service.get_deployment_metrics(deployment_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get deployment metrics: {str(e)}",
        )


@router.post("/deployments/canary", status_code=status.HTTP_201_CREATED)
async def create_canary_deployment(
    request: CanaryDeploymentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a canary deployment with traffic splitting

    Creates a deployment with gradual rollout of a new model version.
    """
    _, serving_service = await get_services()

    try:
        canary = await serving_service.create_canary_deployment(
            name=request.name,
            model_name=request.model_name,
            current_version=request.current_version,
            new_version=request.new_version,
            canary_traffic_percentage=request.canary_traffic_percentage,
        )
        return canary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create canary deployment: {str(e)}",
        )


@router.post("/deployments/canary/{deployment_id}/promote")
async def promote_canary(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Promote canary deployment to primary

    Completes the canary rollout by making the canary version the primary.
    """
    _, serving_service = await get_services()

    try:
        deployment = await serving_service.promote_canary(deployment_id)
        return deployment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to promote canary: {str(e)}",
        )
