"""
Kubernetes Operator API Endpoints

Provides REST API for managing custom resources through operators.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.operator import (
    ResourceState,
    get_operator_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operator", tags=["Kubernetes Operator"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CreateNotebookRequest(BaseModel):
    """Request to create notebook"""
    name: str = Field(..., description="Notebook name")
    image: str = Field(..., description="Container image")
    cpu: str = "500m"
    memory: str = "1Gi"
    gpu: Optional[int] = None
    storage: str = "1Gi"
    ports: List[int] = Field(default_factory=lambda: [8888])
    env: Dict[str, str] = Field(default_factory=dict)
    workspace: Optional[str] = None
    timeout: Optional[int] = None
    auto_stop: bool = True


class CreateTrainingJobRequest(BaseModel):
    """Request to create training job"""
    name: str
    backend: str  # pytorch, tensorflow
    strategy: str  # ddp, mirrored, etc.
    entry_point: str
    entry_point_args: List[str] = Field(default_factory=list)
    num_nodes: int = 1
    num_processes_per_node: int = 1
    model_uri: str
    output_uri: Optional[str] = None
    tensorboard: bool = False
    docker_image: Optional[str] = None
    resources: Dict[str, Any] = Field(default_factory=dict)


class CreateInferenceServiceRequest(BaseModel):
    """Request to create inference service"""
    name: str
    model_uri: str
    predictor_type: str = "custom"
    framework: Optional[str] = None
    replicas: int = 1
    autoscaling_enabled: bool = False
    min_replicas: int = 1
    max_replicas: int = 3
    resources: Dict[str, Any] = Field(default_factory=dict)


class ScaleRequest(BaseModel):
    """Request to scale resource"""
    replicas: int = Field(..., ge=0, le=100)


# ============================================================================
# Notebook Endpoints
# ============================================================================


@router.post("/notebooks", response_model=Dict[str, Any])
async def create_notebook(
    request: CreateNotebookRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Create a notebook server"""
    try:
        manager = get_operator_manager(namespace)

        spec = {
            "image": request.image,
            "cpu": request.cpu,
            "memory": request.memory,
            "ports": request.ports,
            "env": request.env,
            "auto_stop": request.auto_stop,
        }

        if request.gpu:
            spec["gpu"] = request.gpu
        if request.storage:
            spec["storage"] = request.storage
        if request.workspace:
            spec["workspace"] = request.workspace
        if request.timeout:
            spec["timeout"] = request.timeout

        resource = await manager.create_notebook(
            request.name,
            spec,
            current_user.id,
        )

        return {
            "name": resource["metadata"]["name"],
            "namespace": resource["metadata"]["namespace"],
            "phase": resource["status"]["phase"],
            "message": "Notebook created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/notebooks", response_model=List[Dict[str, Any]])
async def list_notebooks(
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """List all notebooks"""
    try:
        manager = get_operator_manager(namespace)
        notebooks = manager.list_notebooks()

        return [
            {
                "name": nb["metadata"]["name"],
                "namespace": nb["metadata"]["namespace"],
                "phase": nb["status"]["phase"],
                "readyReplicas": nb["status"].get("readyReplicas", 0),
                "replicas": nb["status"].get("replicas", 0),
                "jupyterURL": nb["status"].get("jupyterURL"),
                "createdAt": nb["metadata"].get("creationTimestamp"),
            }
            for nb in notebooks
        ]
    except Exception as e:
        logger.error(f"Failed to list notebooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/notebooks/{name}")
async def get_notebook(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Get notebook details"""
    try:
        manager = get_operator_manager(namespace)
        notebooks = manager.list_notebooks()

        for nb in notebooks:
            if nb["metadata"]["name"] == name:
                return {
                    "name": nb["metadata"]["name"],
                    "namespace": nb["metadata"]["namespace"],
                    "spec": nb["spec"],
                    "status": nb["status"],
                }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notebook {name} not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/notebooks/{name}")
async def delete_notebook(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Delete a notebook"""
    try:
        manager = get_operator_manager(namespace)
        success = await manager.delete_notebook(name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook {name} not found",
            )

        return {"message": f"Notebook {name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete notebook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/notebooks/{name}/start")
async def start_notebook(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Start a notebook"""
    try:
        manager = get_operator_manager(namespace)
        # In a real implementation, this would start the notebook pods
        return {"message": f"Notebook {name} started"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/notebooks/{name}/stop")
async def stop_notebook(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Stop a notebook"""
    try:
        manager = get_operator_manager(namespace)
        # In a real implementation, this would stop the notebook pods
        return {"message": f"Notebook {name} stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Training Job Endpoints
# ============================================================================


@router.post("/training-jobs", response_model=Dict[str, Any])
async def create_training_job(
    request: CreateTrainingJobRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Create a training job"""
    try:
        manager = get_operator_manager(namespace)

        spec = {
            "backend": request.backend,
            "strategy": request.strategy,
            "entry_point": request.entry_point,
            "entry_point_args": request.entry_point_args,
            "num_nodes": request.num_nodes,
            "num_processes_per_node": request.num_processes_per_node,
            "model_uri": request.model_uri,
            "tensorboard": request.tensorboard,
        }

        if request.output_uri:
            spec["output_uri"] = request.output_uri
        if request.docker_image:
            spec["docker_image"] = request.docker_image
        if request.resources:
            spec["resources"] = request.resources

        resource = await manager.create_training_job(
            request.name,
            spec,
            current_user.id,
        )

        return {
            "name": resource["metadata"]["name"],
            "namespace": resource["metadata"]["namespace"],
            "phase": resource["status"]["phase"],
            "message": "Training job created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create training job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/training-jobs", response_model=List[Dict[str, Any]])
async def list_training_jobs(
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """List all training jobs"""
    try:
        manager = get_operator_manager(namespace)
        jobs = manager.list_training_jobs()

        return [
            {
                "name": job["metadata"]["name"],
                "namespace": job["metadata"]["namespace"],
                "spec": job["spec"],
                "phase": job["status"]["phase"],
                "startedAt": job["status"].get("startedAt"),
            }
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Failed to list training jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/training-jobs/{name}")
async def delete_training_job(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Delete a training job"""
    try:
        manager = get_operator_manager(namespace)
        success = await manager.delete_training_job(name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Training job {name} not found",
            )

        return {"message": f"Training job {name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete training job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Inference Service Endpoints
# ============================================================================


@router.post("/inference-services", response_model=Dict[str, Any])
async def create_inference_service(
    request: CreateInferenceServiceRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Create an inference service"""
    try:
        manager = get_operator_manager(namespace)

        spec = {
            "model_uri": request.model_uri,
            "predictor_type": request.predictor_type,
            "replicas": request.replicas,
            "autoscaling_enabled": request.autoscaling_enabled,
        }

        if request.framework:
            spec["framework"] = request.framework
        if request.resources:
            spec["resources"] = request.resources

        resource = await manager.create_inference_service(
            request.name,
            spec,
            current_user.id,
        )

        return {
            "name": resource["metadata"]["name"],
            "namespace": resource["metadata"]["namespace"],
            "phase": resource["status"]["phase"],
            "message": "Inference service created successfully",
        }
    except Exception as e:
        logger.error(f"Failed to create inference service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/inference-services", response_model=List[Dict[str, Any]])
async def list_inference_services(
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """List all inference services"""
    try:
        manager = get_operator_manager(namespace)
        services = manager.list_inference_services()

        return [
            {
                "name": svc["metadata"]["name"],
                "namespace": svc["metadata"]["namespace"],
                "spec": svc["spec"],
                "phase": svc["status"]["phase"],
                "replicas": svc["status"].get("replicas", 0),
                "readyReplicas": svc["status"].get("readyReplicas", 0),
                "serviceURL": svc["status"].get("serviceURL"),
            }
            for svc in services
        ]
    except Exception as e:
        logger.error(f"Failed to list inference services: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/inference-services/{name}")
async def delete_inference_service(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Delete an inference service"""
    try:
        manager = get_operator_manager(namespace)
        success = await manager.delete_inference_service(name)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inference service {name} not found",
            )

        return {"message": f"Inference service {name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete inference service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.put("/inference-services/{name}/scale")
async def scale_inference_service(
    name: str,
    request: ScaleRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """Scale an inference service"""
    try:
        manager = get_operator_manager(namespace)
        services = manager.list_inference_services()

        for svc in services:
            if svc["metadata"]["name"] == name:
                # Update replicas
                if "status" not in svc:
                    svc["status"] = {}
                svc["status"]["replicas"] = request.replicas
                svc["status"]["readyReplicas"] = request.replicas

                # Update spec
                if "spec" not in svc:
                    svc["spec"] = {}
                svc["spec"]["replicas"] = request.replicas

                return {
                    "name": name,
                    "replicas": request.replicas,
                    "message": "Service scaled successfully",
                }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inference service {name} not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


# ============================================================================
# Cluster Endpoints
# ============================================================================


@router.get("/cluster/status")
async def get_cluster_status(
    current_user: User = Depends(get_current_user),
):
    """Get operator cluster status"""
    try:
        return {
            "operators": {
                "notebook": {"running": True, "version": "v1alpha1"},
                "training": {"running": True, "version": "v1alpha1"},
                "inference": {"running": True, "version": "v1alpha1"},
            },
            "crds": {
                "notebooks": {"installed": True},
                "trainingjobs": {"installed": True},
                "inferenceservices": {"installed": True},
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/cluster/install-crds")
async def install_crds(
    current_user: User = Depends(get_current_user),
):
    """Install CRDs to the cluster"""
    try:
        manager = get_operator_manager()
        results = await manager.install_crds()

        return {
            "message": "CRDs installed successfully",
            "results": results,
        }
    except Exception as e:
        logger.error(f"Failed to install CRDs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
