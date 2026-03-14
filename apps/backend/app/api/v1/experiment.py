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
from app.services.experiment.hyperopt import (
    HyperparameterService,
    get_hyperparameter_service,
    OptimizationDirection,
    SamplerType,
    PrunerType,
    SearchSpace,
    TrialStatus,
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


# =============================================================================
# Hyperparameter Optimization Endpoints
# =============================================================================

class StudyCreateRequest(BaseModel):
    """Request to create an optimization study"""
    name: str = Field(..., description="Study name")
    experiment_id: Optional[str] = Field(None, description="Associated experiment ID")
    project_id: Optional[int] = Field(None, description="Project ID")

    # Optimization settings
    metric: str = Field("accuracy", description="Metric to optimize")
    direction: OptimizationDirection = Field(OptimizationDirection.MAXIMIZE, description="Optimization direction")

    # Search configuration
    sampler: SamplerType = Field(SamplerType.TPE, description="Sampling algorithm")
    pruner: PrunerType = PrunerType.NONE

    # Trial settings
    n_trials: int = Field(100, ge=1, le=10000, description="Number of trials")
    timeout_hours: Optional[float] = Field(None, ge=0.1, description="Timeout in hours")
    n_jobs: int = Field(1, ge=1, le=100, description="Parallel jobs")

    # Early stopping
    n_warmup_steps: int = Field(10, ge=0, description="Warmup steps before pruning")
    early_stopping_rounds: int = Field(20, ge=0, description="Early stopping rounds")
    early_stopping_threshold: float = Field(0.0, description="Early stopping threshold")

    # Search space
    search_space: Optional[Dict[str, Any]] = Field(None, description="Search space definition")


class StudyResponse(BaseModel):
    """Optimization study response"""
    study_id: str
    name: str
    experiment_id: Optional[str]
    project_id: Optional[int]
    metric: str
    direction: str
    sampler: str
    pruner: str
    n_trials: int
    status: str
    progress: float
    best_value: Optional[float]
    best_params: Optional[Dict[str, Any]]
    completed_trials: int
    created_at: str
    start_time: Optional[str]
    end_time: Optional[str]


class TrialResponse(BaseModel):
    """Trial response"""
    trial_number: int
    trial_id: str
    params: Dict[str, Any]
    value: float
    status: str
    start_time: Optional[str]
    end_time: Optional[str]


class OptimizationHistoryResponse(BaseModel):
    """Optimization history response"""
    study_id: str
    name: str
    metric: str
    direction: str
    best_value: Optional[float]
    best_params: Optional[Dict[str, Any]]
    trials: List[TrialResponse]
    status: str
    progress: float
    created_at: str
    start_time: Optional[str]
    end_time: Optional[str]


@router.get("/hyperopt/studies")
async def list_studies(
    project_id: Optional[int] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
):
    """
    List hyperparameter optimization studies

    Returns all studies with optional filtering.
    """
    service = get_hyperparameter_service()
    studies = await service.list_studies(project_id=project_id, status=status)

    return [
        {
            "study_id": s.study_id,
            "name": s.name,
            "experiment_id": s.experiment_id,
            "project_id": s.project_id,
            "metric": s.metric,
            "direction": s.direction.value,
            "sampler": s.sampler.value,
            "pruner": s.pruner.value,
            "n_trials": s.n_trials,
            "status": s.status,
            "progress": s.progress,
            "best_value": s.best_value,
            "completed_trials": s.completed_trials,
            "created_at": s.created_at.isoformat(),
        }
        for s in studies
    ]


@router.post("/hyperopt/studies", status_code=status.HTTP_201_CREATED)
async def create_study(
    request: StudyCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a hyperparameter optimization study

    Creates a new study for hyperparameter search.
    """
    service = get_hyperparameter_service()

    # Build search space if provided
    search_space = None
    if request.search_space:
        search_space = SearchSpace(
            categorical=request.search_space.get("categorical", {}),
            float_uniform=request.search_space.get("float_uniform", {}),
            float_log_uniform=request.search_space.get("float_log_uniform", {}),
            float_discrete_uniform=request.search_space.get("float_discrete_uniform", {}),
            int_uniform=request.search_space.get("int_uniform", {}),
            int_log_uniform=request.search_space.get("int_log_uniform", {}),
        )

    study = await service.create_study(
        name=request.name,
        metric=request.metric,
        direction=request.direction,
        search_space=search_space,
        n_trials=request.n_trials,
        sampler=request.sampler,
        pruner=request.pruner,
        experiment_id=request.experiment_id,
        project_id=request.project_id,
        n_jobs=request.n_jobs,
        n_warmup_steps=request.n_warmup_steps,
        early_stopping_rounds=request.early_stopping_rounds,
        early_stopping_threshold=request.early_stopping_threshold,
        timeout_hours=request.timeout_hours,
        owner_id=current_user.id,
    )

    return {
        "study_id": study.study_id,
        "name": study.name,
        "experiment_id": study.experiment_id,
        "project_id": study.project_id,
        "metric": study.metric,
        "direction": study.direction.value,
        "sampler": study.sampler.value,
        "pruner": study.pruner.value,
        "n_trials": study.n_trials,
        "status": study.status,
        "created_at": study.created_at.isoformat(),
    }


@router.get("/hyperopt/studies/{study_id}")
async def get_study(
    study_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get study details

    Returns detailed information about an optimization study.
    """
    service = get_hyperparameter_service()
    study = await service.get_study(study_id)

    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study {study_id} not found",
        )

    return StudyResponse(
        study_id=study.study_id,
        name=study.name,
        experiment_id=study.experiment_id,
        project_id=study.project_id,
        metric=study.metric,
        direction=study.direction.value,
        sampler=study.sampler.value,
        pruner=study.pruner.value,
        n_trials=study.n_trials,
        status=study.status,
        progress=study.progress,
        best_value=study.best_value,
        best_params=study.best_trial.params if study.best_trial else None,
        completed_trials=study.completed_trials,
        created_at=study.created_at.isoformat(),
        start_time=study.start_time.isoformat() if study.start_time else None,
        end_time=study.end_time.isoformat() if study.end_time else None,
    )


@router.get("/hyperopt/studies/{study_id}/history")
async def get_study_history(
    study_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get optimization study history

    Returns complete trial history for visualization.
    """
    service = get_hyperparameter_service()

    try:
        history = await service.get_study_history(study_id)
        return history
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/hyperopt/studies/{study_id}/trials")
async def list_trials(
    study_id: str,
    status: Optional[TrialStatus] = Query(None, description="Filter by trial status"),
    current_user: User = Depends(get_current_user),
):
    """
    List trials for a study

    Returns all trials with optional filtering.
    """
    service = get_hyperparameter_service()
    study = await service.get_study(study_id)

    if not study:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study {study_id} not found",
        )

    trials = study.trials
    if status:
        trials = [t for t in trials if t.status == status]

    return [
        TrialResponse(
            trial_number=t.trial_number,
            trial_id=t.trial_id,
            params=t.params,
            value=t.value,
            status=t.status.value,
            start_time=t.start_time.isoformat() if t.start_time else None,
            end_time=t.end_time.isoformat() if t.end_time else None,
        )
        for t in trials
    ]


@router.delete("/hyperopt/studies/{study_id}")
async def delete_study(
    study_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a study

    Cancels running optimization and deletes the study.
    """
    service = get_hyperparameter_service()

    success = await service.delete_study(study_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study {study_id} not found",
        )

    return {"message": f"Study {study_id} deleted"}


@router.get("/hyperopt/samplers")
async def list_samplers(
    current_user: User = Depends(get_current_user),
):
    """
    List available samplers

    Returns information about supported sampling algorithms.
    """
    return [
        {
            "sampler": "random",
            "name": "Random Sampling",
            "description": "Random parameter sampling",
            "best_for": "Baseline comparison",
        },
        {
            "sampler": "tpe",
            "name": "Tree-structured Parzen Estimator",
            "description": "Bayesian optimization using TPE",
            "best_for": "Most hyperparameter optimization tasks",
        },
        {
            "sampler": "cmaes",
            "name": "CMA-ES",
            "description": "Covariance Matrix Adaptation Evolution Strategy",
            "best_for": "Continuous parameter spaces",
        },
        {
            "sampler": "grid",
            "name": "Grid Search",
            "description": "Exhaustive grid search",
            "best_for": "Small discrete parameter spaces",
        },
    ]


@router.get("/hyperopt/pruners")
async def list_pruners(
    current_user: User = Depends(get_current_user),
):
    """
    List available pruners

    Returns information about supported pruning algorithms.
    """
    return [
        {
            "pruner": "none",
            "name": "No Pruning",
            "description": "Run all trials to completion",
        },
        {
            "pruner": "median",
            "name": "Median Pruner",
            "description": "Prune trials worse than median",
            "best_for": "General purpose pruning",
        },
        {
            "pruner": "successive_halving",
            "name": "Successive Halving",
            "description": "Allocate more resources to promising trials",
            "best_for": "Early stopping with resource allocation",
        },
        {
            "pruner": "hyperband",
            "name": "Hyperband",
            "description": "Aggressive successive halving",
            "best_for": "Large hyperparameter spaces",
        },
    ]


@router.get("/hyperopt/templates")
async def list_optimization_templates(
    framework: Optional[str] = Query(None, description="Filter by framework"),
    current_user: User = Depends(get_current_user),
):
    """
    List hyperparameter optimization templates

    Returns predefined search spaces for common use cases.
    """
    templates = [
        {
            "id": "pytorch-image-classification",
            "name": "Image Classification (PyTorch)",
            "framework": "pytorch",
            "description": "Optimize hyperparameters for image classification",
            "metric": "accuracy",
            "direction": "maximize",
            "search_space": {
                "categorical": {
                    "model": ["resnet18", "resnet34", "resnet50", "efficientnet_b0"],
                    "optimizer": ["adam", "adamw", "sgd"],
                },
                "float_log_uniform": {
                    "lr": (1e-5, 1e-1),
                    "weight_decay": (1e-6, 1e-3),
                },
                "int_uniform": {
                    "batch_size": (16, 128),
                    "epochs": (10, 100),
                },
            },
        },
        {
            "id": "pytorch-llm-finetuning",
            "name": "LLM Fine-tuning (PyTorch)",
            "framework": "pytorch",
            "description": "Optimize hyperparameters for LLM fine-tuning",
            "metric": "eval_loss",
            "direction": "minimize",
            "search_space": {
                "categorical": {
                    "lora_r": [8, 16, 32, 64],
                    "lora_alpha": [16, 32, 64, 128],
                },
                "float_log_uniform": {
                    "learning_rate": (1e-6, 1e-3),
                    "warmup_ratio": (0.01, 0.2),
                },
                "int_uniform": {
                    "batch_size": (1, 8),
                    "gradient_accumulation_steps": (1, 8),
                },
            },
        },
        {
            "id": "xgboost-classification",
            "name": "XGBoost Classification",
            "framework": "xgboost",
            "description": "Optimize hyperparameters for XGBoost classifier",
            "metric": "accuracy",
            "direction": "maximize",
            "search_space": {
                "float_uniform": {
                    "eta": (0.01, 0.3),
                    "subsample": (0.5, 1.0),
                    "colsample_bytree": (0.5, 1.0),
                },
                "int_uniform": {
                    "max_depth": (3, 10),
                    "min_child_weight": (1, 10),
                },
                "float_discrete_uniform": {
                    "gamma": (0, 10, 0.5),
                },
            },
        },
    ]

    if framework:
        templates = [t for t in templates if t["framework"] == framework]

    return templates
