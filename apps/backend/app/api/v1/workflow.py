"""
Workflow API endpoints for One Data Studio Lite

Provides REST API for managing workflow DAGs.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, require_permission
from app.models.user import User
from app.services.workflow import WorkflowScheduler
from app.services.workflow.dag_engine import DAGConfig
from app.services.workflow.task_types import TaskType, TaskRegistry

router = APIRouter(prefix="/workflows", tags=["workflows"])


# Request/Response Schemas
class DAGCreateRequest(BaseModel):
    """Request to create a DAG"""

    dag_id: str = Field(..., description="Unique DAG identifier")
    name: str = Field(..., description="DAG display name")
    description: Optional[str] = Field(None, description="DAG description")
    schedule_interval: Optional[str] = Field(None, description="Cron expression or None")
    tags: List[str] = Field(default_factory=list, description="DAG tags")
    tasks: List[Dict[str, Any]] = Field(..., description="List of task configurations")


class DAGUpdateRequest(BaseModel):
    """Request to update a DAG"""

    name: Optional[str] = None
    description: Optional[str] = None
    schedule_interval: Optional[str] = None
    tags: Optional[List[str]] = None
    tasks: Optional[List[Dict[str, Any]] = None


class TaskConfigSchema(BaseModel):
    """Task configuration schema"""

    task_id: str
    task_type: str
    name: str
    description: Optional[str] = None
    depends_on: Optional[List[str]] = None
    retry_count: int = 0
    retry_delay_seconds: int = 300
    timeout_seconds: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class DAGResponse(BaseModel):
    """DAG response"""

    id: int
    dag_id: str
    name: str
    description: Optional[str]
    schedule_interval: Optional[str]
    is_active: bool
    is_paused: bool
    tags: List[str]
    owner_id: Optional[int]
    created_at: str
    updated_at: str


class DAGRunResponse(BaseModel):
    """DAG run response"""

    id: int
    dag_id: int
    run_id: str
    execution_date: str
    state: str
    start_date: Optional[str]
    end_date: Optional[str]
    run_type: str


class TaskTypeResponse(BaseModel):
    """Task type response"""

    type: str
    name: str
    category: str


# Helper function
async def get_workflow_service() -> WorkflowScheduler:
    """Get workflow service instance"""
    # Create or get singleton instance
    return WorkflowScheduler()


@router.get("/dags", response_model=List[DAGResponse])
async def list_dags(
    current_user: User = Depends(get_current_user),
):
    """
    List all DAGs

    Returns a list of all DAGs the user has access to.
    """
    service = await get_workflow_service()
    return await service.list_dags()


@router.post("/dags", response_model=DAGResponse, status_code=status.HTTP_201_CREATED)
async def create_dag(
    request: DAGCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new DAG

    Creates a new workflow DAG from the provided configuration.
    """
    service = await get_workflow_service()

    # Build task configs
    from app.services.workflow.task_types import TaskConfig

    task_configs = []
    for task_data in request.tasks:
        task_config = TaskConfig(
            task_id=task_data["task_id"],
            task_type=TaskType(task_data["task_type"]),
            name=task_data["name"],
            description=task_data.get("description"),
            depends_on=task_data.get("depends_on"),
            retry_count=task_data.get("retry_count", 0),
            retry_delay_seconds=task_data.get("retry_delay_seconds", 300),
            timeout_seconds=task_data.get("timeout_seconds"),
            parameters=task_data.get("parameters", {}),
        )
        task_configs.append(task_config)

    # Build DAG config
    dag_config = DAGConfig(
        dag_id=request.dag_id,
        name=request.name,
        description=request.description,
        schedule_interval=request.schedule_interval,
        tags=request.tags,
        owner=current_user.username,
        tasks=task_configs,
    )

    try:
        result = await service.create_dag(dag_config)
        return DAGResponse(
            id=0,  # Will be filled by actual creation
            dag_id=result["dag_id"],
            name=request.name,
            description=request.description,
            schedule_interval=request.schedule_interval,
            is_active=True,
            is_paused=False,
            tags=request.tags,
            owner_id=current_user.id,
            created_at=result["created_at"],
            updated_at=result["created_at"],
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/dags/{dag_id}", response_model=DAGResponse)
async def get_dag(
    dag_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific DAG

    Returns detailed information about a DAG.
    """
    service = await get_workflow_service()

    # This would query the database for the DAG
    # For now, return a mock response
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not yet implemented",
    )


@router.put("/dags/{dag_id}", response_model=DAGResponse)
async def update_dag(
    dag_id: str,
    request: DAGUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update a DAG

    Updates an existing DAG configuration.
    """
    service = await get_workflow_service()

    # This would update the DAG in the database and regenerate the file
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not yet implemented",
    )


@router.delete("/dags/{dag_id}")
async def delete_dag(
    dag_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a DAG

    Deletes a DAG and all its runs.
    """
    service = await get_workflow_service()

    result = await service.delete_dag(dag_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DAG {dag_id} not found",
        )

    return {"message": f"DAG {dag_id} deleted successfully"}


@router.post("/dags/{dag_id}/run", response_model=DAGRunResponse)
async def trigger_dag_run(
    dag_id: str,
    conf: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Trigger a manual DAG run

    Executes a DAG immediately regardless of its schedule.
    """
    service = await get_workflow_service()

    try:
        result = await service.trigger_dag_run(dag_id, conf)
        return DAGRunResponse(
            id=0,
            dag_id=0,
            run_id=result["dag_run_id"],
            execution_date=result["start_date"],
            state=result["state"],
            start_date=result["start_date"],
            end_date=None,
            run_type="manual",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to trigger DAG: {str(e)}",
        )


@router.get("/dags/{dag_id}/runs", response_model=List[DAGRunResponse])
async def get_dag_runs(
    dag_id: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
):
    """
    Get DAG runs

    Returns execution history for a DAG.
    """
    service = await get_workflow_service()

    try:
        runs = await service.get_dag_runs(dag_id, limit)
        return [
            DAGRunResponse(
                id=run.get("id", 0),
                dag_id=run.get("dag_id", 0),
                run_id=run.get("run_id", ""),
                execution_date=run.get("execution_date", ""),
                state=run.get("state", "unknown"),
                start_date=run.get("start_date"),
                end_date=run.get("end_date"),
                run_type=run.get("run_type", "manual"),
            )
            for run in runs
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DAG runs: {str(e)}",
        )


@router.get("/runs/{run_id}/tasks")
async def get_run_tasks(
    run_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get task instances for a DAG run

    Returns all task instances for a specific DAG run.
    """
    service = await get_workflow_service()

    try:
        tasks = await service.get_task_instances(run_id.split("_")[1])
        return {"tasks": tasks}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task instances: {str(e)}",
        )


@router.post("/dags/{dag_id}/pause")
async def pause_dag(
    dag_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Pause a DAG

    Prevents scheduled runs from executing.
    """
    service = await get_workflow_service()

    result = await service.pause_dag(dag_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DAG {dag_id} not found",
        )

    return {"message": f"DAG {dag_id} paused successfully"}


@router.post("/dags/{dag_id}/unpause")
async def unpause_dag(
    dag_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Unpause a DAG

    Allows scheduled runs to execute again.
    """
    service = await get_workflow_service()

    result = await service.unpause_dag(dag_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DAG {dag_id} not found",
        )

    return {"message": f"DAG {dag_id} unpaused successfully"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a running DAG run

    Stops execution of a DAG run.
    """
    service = await get_workflow_service()

    result = await service.cancel_run(run_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return {"message": f"Run {run_id} cancelled successfully"}


@router.get("/task-types", response_model=List[TaskTypeResponse])
async def list_task_types(
    current_user: User = Depends(get_current_user),
):
    """
    List available task types

    Returns all available task types for workflow DAGs.
    """
    task_types = TaskRegistry.list_task_types()
    return [
        TaskTypeResponse(
            type=tt["type"],
            name=tt["name"],
            category=tt["category"],
        )
        for tt in task_types
    ]


@router.get("/dags/{dag_id}/export")
async def export_dag(
    dag_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Export a DAG

    Exports a DAG configuration as JSON for backup or sharing.
    """
    service = await get_workflow_service()

    try:
        # Get DAG info
        dag_info = await service.get_dag_status(dag_id)

        # Build exportable format
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "dag": {
                "dag_id": dag_info.get("dag_id", dag_id),
                "name": dag_info.get("name", ""),
                "description": dag_info.get("description"),
                "schedule_interval": dag_info.get("schedule_interval"),
                "tags": dag_info.get("tags", []),
                "tasks": dag_info.get("tasks", []),
            },
        }

        return export_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export DAG: {str(e)}",
        )


@router.post("/dags/import")
async def import_dag(
    import_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """
    Import a DAG

    Imports a DAG configuration from JSON export.
    """
    from datetime import datetime

    service = await get_workflow_service()

    # Validate import data
    if "dag" not in import_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid import data: missing 'dag' field",
        )

    dag_data = import_data["dag"]

    # Check if DAG already exists
    existing_dags = await service.list_dags()
    dag_id = dag_data.get("dag_id")
    if any(d.get("dag_id") == dag_id for d in existing_dags):
        # Generate new ID if conflict
        dag_data["dag_id"] = f"{dag_id}_imported_{int(datetime.utcnow().timestamp())}"

    # Build task configs
    from app.services.workflow.task_types import TaskConfig

    task_configs = []
    for task_data in dag_data.get("tasks", []):
        try:
            task_config = TaskConfig(
                task_id=task_data["task_id"],
                task_type=TaskType(task_data["task_type"]),
                name=task_data["name"],
                description=task_data.get("description"),
                depends_on=task_data.get("depends_on"),
                retry_count=task_data.get("retry_count", 0),
                retry_delay_seconds=task_data.get("retry_delay_seconds", 300),
                timeout_seconds=task_data.get("timeout_seconds"),
                parameters=task_data.get("parameters", {}),
            )
            task_configs.append(task_config)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task configuration: {str(e)}",
            )

    # Build DAG config
    dag_config = DAGConfig(
        dag_id=dag_data["dag_id"],
        name=dag_data.get("name", "Imported DAG"),
        description=dag_data.get("description"),
        schedule_interval=dag_data.get("schedule_interval"),
        tags=dag_data.get("tags", []),
        owner=current_user.username,
        tasks=task_configs,
    )

    try:
        result = await service.create_dag(dag_config)
        return {
            "message": "DAG imported successfully",
            "dag_id": result["dag_id"],
            "name": dag_data.get("name"),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/dags/{dag_id}/clone")
async def clone_dag(
    dag_id: str,
    new_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Clone a DAG

    Creates a copy of an existing DAG with a new ID.
    """
    service = await get_workflow_service()

    try:
        # Get original DAG
        dag_info = await service.get_dag_status(dag_id)

        # Generate new ID
        timestamp = int(datetime.utcnow().timestamp())
        new_dag_id = f"{dag_id}_clone_{timestamp}"

        # Build task configs
        from app.services.workflow.task_types import TaskConfig

        task_configs = []
        for task_data in dag_info.get("tasks", []):
            task_config = TaskConfig(
                task_id=task_data["task_id"],
                task_type=TaskType(task_data["task_type"]),
                name=task_data["name"],
                description=task_data.get("description"),
                depends_on=task_data.get("depends_on"),
                retry_count=task_data.get("retry_count", 0),
                retry_delay_seconds=task_data.get("retry_delay_seconds", 300),
                timeout_seconds=task_data.get("timeout_seconds"),
                parameters=task_data.get("parameters", {}),
            )
            task_configs.append(task_config)

        # Build DAG config
        dag_config = DAGConfig(
            dag_id=new_dag_id,
            name=new_name or f"{dag_info.get('name', dag_id)} (Copy)",
            description=dag_info.get("description"),
            schedule_interval=dag_info.get("schedule_interval"),
            tags=dag_info.get("tags", []),
            owner=current_user.username,
            tasks=task_configs,
        )

        result = await service.create_dag(dag_config)
        return {
            "message": "DAG cloned successfully",
            "dag_id": result["dag_id"],
            "name": new_name or f"{dag_info.get('name', dag_id)} (Copy)",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clone DAG: {str(e)}",
        )


@router.get("/templates")
async def list_dag_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List DAG templates

    Returns predefined DAG templates for common workflows.
    """
    # This would return templates from the database or a templates directory
    templates = [
        {
            "id": "etl_daily",
            "name": "Daily ETL Pipeline",
            "description": "Daily data extraction, transformation, and loading",
            "category": "etl",
            "tasks": [
                {
                    "task_id": "extract",
                    "task_type": "sql",
                    "name": "Extract Data",
                    "parameters": {"sql": "SELECT * FROM source_table"},
                },
                {
                    "task_id": "transform",
                    "task_type": "etl",
                    "name": "Transform Data",
                    "depends_on": ["extract"],
                    "parameters": {"pipeline_id": "{{pipeline_id}}"},
                },
                {
                    "task_id": "load",
                    "task_type": "sql",
                    "name": "Load Data",
                    "depends_on": ["transform"],
                    "parameters": {"sql": "INSERT INTO target_table SELECT * FROM temp_table"},
                },
            ],
        },
        {
            "id": "ml_training",
            "name": "ML Training Pipeline",
            "description": "Machine learning model training workflow",
            "category": "ml",
            "tasks": [
                {
                    "task_id": "prepare_data",
                    "task_type": "python",
                    "name": "Prepare Data",
                    "parameters": {"code": "# Data preparation code"},
                },
                {
                    "task_id": "train_model",
                    "task_type": "training",
                    "name": "Train Model",
                    "depends_on": ["prepare_data"],
                    "parameters": {"experiment_id": "{{experiment_id}}"},
                },
                {
                    "task_id": "evaluate_model",
                    "task_type": "evaluation",
                    "name": "Evaluate Model",
                    "depends_on": ["train_model"],
                },
                {
                    "task_id": "register_model",
                    "task_type": "model_register",
                    "name": "Register Model",
                    "depends_on": ["evaluate_model"],
                },
            ],
        },
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    return templates


@router.get("/etl-pipelines")
async def list_etl_pipelines(
    current_user: User = Depends(get_current_user),
):
    """
    List available ETL pipelines for use in workflow DAGs

    Returns all ETL pipelines that can be used as ETL task nodes.
    """
    from sqlalchemy import select
    from app.core.database import get_async_session
    from app.models import ETLPipeline

    async for db in get_async_session():
        result = await db.execute(
            select(ETLPipeline).where(ETLPipeline.is_active == True)
        )
        pipelines = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "source_type": p.source_type,
                "target_type": p.target_type,
                "step_count": len([s for s in p.steps if s.is_enabled]),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in pipelines
        ]
