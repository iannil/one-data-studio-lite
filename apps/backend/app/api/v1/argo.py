"""
Argo Workflow API Endpoints

Provides REST API for Argo Workflow integration.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.models.user import User
from app.services.argo import (
    WorkflowPhase,
    Workflow,
    WorkflowStatus,
    DAGDefinition,
    ArgoClient,
    get_argo_client,
    get_dag_converter,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/argo", tags=["Argo Workflows"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class SubmitWorkflowRequest(BaseModel):
    """Request to submit workflow"""

    dag_id: str = Field(..., description="Unique DAG identifier")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = None
    namespace: str = "default"
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    service_account: Optional[str] = None
    ttl_seconds_after_finished: Optional[int] = None
    parallelism: Optional[int] = None

    # Artifact repository
    s3_bucket: Optional[str] = None
    s3_endpoint: Optional[str] = None


class RetryWorkflowRequest(BaseModel):
    """Request to retry workflow"""

    restart_successful: bool = False
    node_field_selector: Optional[str] = None


class StopWorkflowRequest(BaseModel):
    """Request to stop workflow"""

    message: Optional[str] = "Stopped by user"


class LogOptionsRequest(BaseModel):
    """Request for workflow logs"""

    node_id: Optional[str] = None
    tail: Optional[int] = None
    grep: Optional[str] = None
    container: Optional[str] = None
    since_time: Optional[str] = None


# ============================================================================
# Workflow Endpoints
# ============================================================================


@router.post("/workflows/submit", response_model=Dict[str, Any])
async def submit_workflow(
    request: SubmitWorkflowRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Submit a workflow to Argo

    Requires authentication.
    """
    try:
        # Build DAG definition
        dag = DAGDefinition(
            dag_id=request.dag_id,
            name=request.name,
            description=request.description,
            tags=request.tags,
            namespace=request.namespace,
            service_account=request.service_account,
            ttl_seconds_after_finished=request.ttl_seconds_after_finished,
            parallelism=request.parallelism,
            s3_bucket=request.s3_bucket,
            s3_endpoint=request.s3_endpoint,
        )

        # Convert nodes and edges from request
        from app.services.argo import DAGNode
        for node_data in request.nodes:
            dag.nodes.append(DAGNode(**node_data))

        from app.services.argo import DAGEdge
        for edge_data in request.edges:
            dag.edges.append(DAGEdge(**edge_data))

        # Convert to Argo workflow
        converter = get_dag_converter(request.namespace, request.service_account)
        workflow = await converter.convert(dag, request.variables)

        # Submit to Argo
        client = get_argo_client(namespace=request.namespace)
        result = await client.submit_workflow(workflow)

        return {
            "workflow_name": result["metadata"]["name"],
            "namespace": result["metadata"]["namespace"],
            "uid": result["metadata"]["uid"],
            "created_at": result["metadata"]["creationTimestamp"],
            "phase": result["status"]["phase"],
            "message": "Workflow submitted successfully",
        }
    except Exception as e:
        logger.error(f"Failed to submit workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows", response_model=List[Dict[str, Any]])
async def list_workflows(
    namespace: str = "default",
    phases: Optional[List[str]] = Query(None),
    labels: Optional[List[str]] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    List Argo workflows

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)

        # Convert phase strings to enums
        phase_filters = None
        if phases:
            phase_filters = [WorkflowPhase(p) for p in phases]

        workflows = await client.list_workflows(
            namespace=namespace,
            phases=phase_filters,
            labels=labels,
            limit=limit,
            offset=offset,
        )

        return workflows
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{name}", response_model=Dict[str, Any])
async def get_workflow(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """
    Get workflow details

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        workflow = await client.get_workflow(name, namespace)

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {name} not found",
            )

        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.delete("/workflows/{name}")
async def delete_workflow(
    name: str,
    namespace: str = "default",
    force: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a workflow

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        success = await client.delete_workflow(name, namespace, force)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {name} not found",
            )

        return {"message": f"Workflow {name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/workflows/{name}/retry")
async def retry_workflow(
    name: str,
    request: RetryWorkflowRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """
    Retry a failed workflow

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        result = await client.retry_workflow(
            name,
            namespace,
            request.restart_successful,
        )

        return {
            "workflow_name": result["name"],
            "namespace": result["namespace"],
            "message": "Workflow retry initiated",
        }
    except Exception as e:
        logger.error(f"Failed to retry workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/workflows/{name}/stop")
async def stop_workflow(
    name: str,
    request: StopWorkflowRequest,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """
    Stop a running workflow

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        success = await client.stop_workflow(name, namespace)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {name} not found",
            )

        return {
            "message": f"Workflow {name} stopped",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{name}/logs")
async def get_workflow_logs(
    name: str,
    namespace: str = "default",
    node_id: Optional[str] = Query(None),
    tail: Optional[int] = Query(None),
    grep: Optional[str] = Query(None),
    container: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Get workflow logs

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)

        log_options = {}
        if tail:
            log_options["tail"] = tail
        if grep:
            log_options["grep"] = grep
        if container:
            log_options["container"] = container

        logs = await client.get_workflow_logs(
            name,
            namespace,
            node_id,
            log_options if log_options else None,
        )

        return {
            "workflow_name": name,
            "namespace": namespace,
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{name}/artifacts")
async def get_workflow_artifacts(
    name: str,
    namespace: str = "default",
    node_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Get workflow artifacts

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        artifacts = await client.get_workflow_artifacts(name, namespace, node_id)

        return {
            "workflow_name": name,
            "namespace": namespace,
            "artifacts": artifacts,
        }
    except Exception as e:
        logger.error(f"Failed to get artifacts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/workflows/{name}/nodes")
async def get_workflow_nodes(
    name: str,
    namespace: str = "default",
    current_user: User = Depends(get_current_user),
):
    """
    Get workflow nodes status

    Requires authentication.
    """
    try:
        client = get_argo_client(namespace=namespace)
        workflow = await client.get_workflow(name, namespace)

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {name} not found",
            )

        nodes = workflow.get("status", {}).get("nodes", {})

        node_list = []
        for node_id, node_data in nodes.items():
            node_list.append({
                "id": node_id,
                "name": node_data.get("name", node_id),
                "phase": node_data.get("phase"),
                "started_at": node_data.get("startedAt"),
                "finished_at": node_data.get("finishedAt"),
                "message": node_data.get("message"),
                "inputs": node_data.get("inputs"),
                "outputs": node_data.get("outputs"),
                "children": node_data.get("children", []),
            })

        return {
            "workflow_name": name,
            "nodes": node_list,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/cluster/info")
async def get_cluster_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get Argo cluster information

    Requires authentication.
    """
    try:
        # Mock cluster info
        return {
            "version": "v3.4.8",
            "namespace": "default",
            "capabilities": {
                "workflows": True,
                "workflow_templates": True,
                "cron_workflows": True,
                "cluster_workflow_templates": True,
            },
            "config": {
                "container_runtime_executor": "docker",
                "artifact_repository": {
                    "s3": {
                        "bucket": "my-bucket",
                        "endpoint": "s3.amazonaws.com",
                    }
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get cluster info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
