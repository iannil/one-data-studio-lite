"""
Experiment API endpoints

REST API for MLflow experiment tracking.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.experiment import (
    ExperimentService,
    RunService,
    MetricService,
    get_experiment_service,
    get_run_service,
    get_metric_service,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


# Request/Response Schemas
class ExperimentCreateRequest(BaseModel):
    """Request to create an experiment"""
    name: str = Field(..., description="Experiment name", max_length=256)
    description: Optional[str] = Field(None, description="Experiment description")
    tags: Optional[Dict[str, str]] = Field(None, description="Experiment tags")
    project_id: Optional[int] = Field(None, description="Project ID")


class ExperimentUpdateRequest(BaseModel):
    """Request to update an experiment"""
    name: Optional[str] = Field(None, description="New experiment name")
    description: Optional[str] = Field(None, description="New description")
    tags: Optional[Dict[str, str]] = Field(None, description="Tags to replace")


class RunCreateRequest(BaseModel):
    """Request to create a run"""
    experiment_id: str = Field(..., description="Experiment ID")
    run_name: Optional[str] = Field(None, description="Run name")
    tags: Optional[Dict[str, str]] = Field(None, description="Run tags")


class LogParamsRequest(BaseModel):
    """Request to log parameters"""
    params: Dict[str, Any] = Field(..., description="Parameters to log")


class LogMetricsRequest(BaseModel):
    """Request to log metrics"""
    metrics: Dict[str, float] = Field(..., description="Metrics to log")
    step: int = Field(0, description="Training step")


class LogBatchRequest(BaseModel):
    """Request to log batch of params and metrics"""
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None
    tags: Optional[Dict[str, str]] = None


class MetricHistoryRequest(BaseModel):
    """Request to get metric history"""
    run_ids: List[str] = Field(..., description="Run IDs to compare")
    metric_keys: Optional[List[str]] = Field(None, description="Specific metrics to include")


# Helper
async def get_services() -> tuple:
    """Get service instances"""
    return (
        get_experiment_service(),
        get_run_service(),
        get_metric_service(),
    )


# Experiment Endpoints

@router.get("")
async def list_experiments(
    project_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List all experiments

    Returns a list of all experiments with run counts and best runs.
    """
    exp_service, _, _ = await get_services()
    return await exp_service.list_experiments(project_id=project_id, search=search)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_experiment(
    request: ExperimentCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new experiment

    Creates a new MLflow experiment.
    """
    exp_service, _, _ = await get_services()

    try:
        experiment = await exp_service.create_experiment(
            name=request.name,
            description=request.description,
            tags=request.tags,
            project_id=request.project_id,
        )
        return experiment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create experiment: {str(e)}",
        )


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get experiment details

    Returns experiment metadata with stats.
    """
    exp_service, _, _ = await get_services()

    experiment = await exp_service.get_experiment(experiment_id)
    if not experiment or experiment.get("lifecycle_stage") == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return experiment


@router.put("/{experiment_id}")
async def update_experiment(
    experiment_id: str,
    request: ExperimentUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update experiment

    Updates experiment name, description, or tags.
    """
    exp_service, _, _ = await get_services()

    success = await exp_service.update_experiment(
        experiment_id=experiment_id,
        name=request.name,
        description=request.description,
        tags=request.tags,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update experiment",
        )

    return await exp_service.get_experiment(experiment_id)


@router.delete("/{experiment_id}")
async def delete_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete experiment (soft delete)

    Marks the experiment as deleted.
    """
    exp_service, _, _ = await get_services()

    success = await exp_service.delete_experiment(experiment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete experiment",
        )

    return {"message": f"Experiment {experiment_id} deleted"}


@router.post("/{experiment_id}/restore")
async def restore_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Restore deleted experiment

    Restores a previously deleted experiment.
    """
    exp_service, _, _ = await get_services()

    success = await exp_service.restore_experiment(experiment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to restore experiment",
        )

    return {"message": f"Experiment {experiment_id} restored"}


# Run Endpoints

@router.get("/{experiment_id}/runs")
async def list_experiment_runs(
    experiment_id: str,
    max_results: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List runs for an experiment

    Returns all runs for the specified experiment.
    """
    exp_service, run_service, _ = await get_services()

    # Verify experiment exists
    experiment = await exp_service.get_experiment(experiment_id)
    if not experiment or experiment.get("lifecycle_stage") == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return await run_service.list_runs(
        experiment_id=experiment_id,
        max_results=max_results,
        status=status,
    )


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(
    request: RunCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new run

    Creates a new run in the specified experiment.
    """
    _, run_service, _ = await get_services()

    try:
        run = await run_service.create_run(
            experiment_id=request.experiment_id,
            run_name=request.run_name,
            tags=request.tags,
        )
        return run
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create run: {str(e)}",
        )


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get run details

    Returns run metadata with params, metrics, tags, and artifacts.
    """
    _, run_service, _ = await get_services()

    run = await run_service.get_run(run_id)
    if not run or run.get("lifecycle_stage") == "deleted":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return run


@router.delete("/runs/{run_id}")
async def delete_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a run

    Marks the run as deleted.
    """
    _, run_service, _ = await get_services()

    success = await run_service.delete_run(run_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete run",
        )

    return {"message": f"Run {run_id} deleted"}


@router.post("/runs/{run_id}/params")
async def log_params(
    run_id: str,
    request: LogParamsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Log parameters to a run

    Logs hyperparameters or config to the run.
    """
    _, run_service, _ = await get_services()

    success = await run_service.log_params(run_id, request.params)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to log parameters",
        )

    return {"message": "Parameters logged successfully"}


@router.post("/runs/{run_id}/metrics")
async def log_metrics(
    run_id: str,
    request: LogMetricsRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Log metrics to a run

    Logs training metrics to the run.
    """
    _, run_service, _ = await get_services()

    success = await run_service.log_metrics(
        run_id=run_id,
        metrics=request.metrics,
        step=request.step,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to log metrics",
        )

    return {"message": "Metrics logged successfully"}


@router.post("/runs/{run_id}/batch")
async def log_batch(
    run_id: str,
    request: LogBatchRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Log batch of params, metrics, and tags

    Logs multiple items in a single call.
    """
    _, run_service, _ = await get_services()

    # Log each type
    if request.params:
        await run_service.log_params(run_id, request.params)
    if request.metrics:
        await run_service.log_metrics(run_id, request.metrics)
    if request.tags:
        from app.services.experiment.mlflow_client import get_mlflow_client
        mlflow = get_mlflow_client()
        mlflow.set_tags(run_id, request.tags)

    return {"message": "Batch logged successfully"}


@router.post("/runs/{run_id}/status")
async def set_run_status(
    run_id: str,
    run_status: str = Query(..., description="Status: FINISHED, FAILED, KILLED"),
    current_user: User = Depends(get_current_user),
):
    """
    Set run status (terminate run)

    Terminates the run with the specified status.
    """
    _, run_service, _ = await get_services()

    success = await run_service.set_run_status(run_id, run_status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to set run status",
        )

    return {"message": f"Run status set to {run_status}"}


# Metric Endpoints

@router.get("/runs/{run_id}/metrics/history")
async def get_metric_history(
    run_id: str,
    metric_key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get metric history for a run

    Returns all values for a specific metric over time.
    """
    _, run_service, _ = await get_services()

    history = await run_service.get_metric_history(run_id, metric_key)
    return {
        "run_id": run_id,
        "metric_key": metric_key,
        "history": history,
    }


@router.post("/metrics/compare")
async def compare_metrics(
    request: MetricHistoryRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Compare metrics across multiple runs

    Returns comparison data with statistics.
    """
    _, _, metric_service = await get_services()

    return await metric_service.compare_metrics(
        run_ids=request.run_ids,
        metric_keys=request.metric_keys,
    )


@router.get("/{experiment_id}/metrics/summary")
async def get_metric_summary(
    experiment_id: str,
    metric_key: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get metric summary for an experiment

    Returns best/worst runs and statistics for a metric.
    """
    _, _, metric_service = await get_services()

    return await metric_service.get_experiment_metric_summary(
        experiment_id=experiment_id,
        metric_key=metric_key,
    )


@router.get("/{experiment_id}/metrics/correlation")
async def get_metric_correlation(
    experiment_id: str,
    metric_key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get parameter-metric correlations

    Analyzes which parameters most influence a metric.
    """
    _, _, metric_service = await get_services()

    return await metric_service.get_metric_correlation(
        experiment_id=experiment_id,
        metric_key=metric_key,
    )


@router.post("/runs/compare")
async def compare_runs(
    run_ids: List[str],
    current_user: User = Depends(get_current_user),
):
    """
    Compare multiple runs side by side

    Returns params and metrics for all specified runs.
    """
    _, run_service, _ = await get_services()

    return await run_service.get_run_comparison(run_ids)


# Artifact Endpoints

@router.get("/runs/{run_id}/artifacts")
async def list_artifacts(
    run_id: str,
    path: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List artifacts for a run

    Returns all artifacts in the specified path.
    """
    _, run_service, _ = await get_services()

    artifacts = await run_service.get_run_artifacts(run_id, path)
    return {
        "run_id": run_id,
        "path": path or "",
        "artifacts": artifacts,
    }
