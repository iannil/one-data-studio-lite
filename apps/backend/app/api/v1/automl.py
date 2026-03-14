"""
AutoML API Endpoints

Provides endpoints for automated machine learning experiments.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.automl import (
    get_automl_service,
    ProblemType,
    SearchAlgorithm,
    ModelType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automl", tags=["AutoML"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ExperimentCreate(BaseModel):
    """Request model for creating an AutoML experiment"""
    name: str = Field(..., description="Unique experiment name")
    display_name: Optional[str] = None
    description: Optional[str] = None
    problem_type: ProblemType
    target_column: str
    feature_columns: List[str]
    source_type: str = "dataframe"
    source_config: Dict[str, Any] = {}
    eval_metric: str = "accuracy"
    search_algorithm: SearchAlgorithm = SearchAlgorithm.RANDOM
    max_trials: int = Field(10, ge=1, le=100)
    max_time_minutes: int = Field(60, ge=1, le=480)
    model_types: List[ModelType] = [ModelType.XGBOOST, ModelType.LIGHTGBM]
    enable_auto_feature_engineering: bool = True
    enable_early_stopping: bool = True
    feature_config: Dict[str, Any] = {}
    tags: List[str] = []


class ExperimentResponse(BaseModel):
    """Response model for experiment"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    problem_type: str
    target_column: str
    eval_metric: str
    search_algorithm: str
    max_trials: int
    status: str
    progress: float
    best_score: Optional[float]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]


class TrialResponse(BaseModel):
    """Response model for trial"""
    id: str
    experiment_id: str
    trial_number: int
    model_type: str
    hyperparameters: Dict[str, Any]
    status: str
    train_score: Optional[float]
    val_score: Optional[float]
    test_score: Optional[float]
    metrics: Dict[str, float]
    duration_seconds: Optional[float]
    created_at: str


class TrainingRequest(BaseModel):
    """Request model for starting training"""
    experiment_id: str
    # Training data would typically be uploaded separately
    # For now, we reference it by path or table
    data_path: Optional[str] = None
    train_split: float = Field(0.8, ge=0.5, le=0.95)
    val_split: float = Field(0.1, ge=0.05, le=0.3)
    cv_folds: int = Field(5, ge=1, le=10)


class ModelResponse(BaseModel):
    """Response model for model"""
    id: str
    name: str
    version: int
    model_type: str
    problem_type: str
    metrics: Dict[str, float]
    deployment_status: str
    status: str
    created_at: str


# ============================================================================
# Experiment Endpoints
# ============================================================================


@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    data: ExperimentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new AutoML experiment"""
    service = get_automl_service(db)

    experiment = service.create_experiment(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        problem_type=data.problem_type,
        target_column=data.target_column,
        feature_columns=data.feature_columns,
        source_type=data.source_type,
        source_config=data.source_config,
        eval_metric=data.eval_metric,
        search_algorithm=data.search_algorithm,
        max_trials=data.max_trials,
        model_types=data.model_types,
        enable_auto_feature_engineering=data.enable_auto_feature_engineering,
        feature_config=data.feature_config,
        owner_id=str(current_user.id),
    )

    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        display_name=experiment.display_name,
        description=experiment.description,
        problem_type=experiment.problem_type,
        target_column=experiment.target_column,
        eval_metric=experiment.eval_metric,
        search_algorithm=experiment.search_algorithm,
        max_trials=experiment.max_trials,
        status=experiment.status,
        progress=experiment.progress,
        best_score=experiment.best_score,
        created_at=experiment.created_at.isoformat(),
        started_at=experiment.started_at.isoformat() if experiment.started_at else None,
        completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
    )


@router.get("/experiments", response_model=List[ExperimentResponse])
async def list_experiments(
    status: Optional[str] = Query(None),
    problem_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List AutoML experiments"""
    service = get_automl_service(db)

    experiments = service.list_experiments(
        owner_id=str(current_user.id),
        status=status,
        problem_type=problem_type,
        limit=limit,
        offset=offset,
    )

    return [
        ExperimentResponse(
            id=str(e.id),
            name=e.name,
            display_name=e.display_name,
            description=e.description,
            problem_type=e.problem_type,
            target_column=e.target_column,
            eval_metric=e.eval_metric,
            search_algorithm=e.search_algorithm,
            max_trials=e.max_trials,
            status=e.status,
            progress=e.progress,
            best_score=e.best_score,
            created_at=e.created_at.isoformat(),
            started_at=e.started_at.isoformat() if e.started_at else None,
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
        )
        for e in experiments
    ]


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get an experiment by ID"""
    service = get_automl_service(db)
    experiment = service.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )

    return ExperimentResponse(
        id=str(experiment.id),
        name=experiment.name,
        display_name=experiment.display_name,
        description=experiment.description,
        problem_type=experiment.problem_type,
        target_column=experiment.target_column,
        eval_metric=experiment.eval_metric,
        search_algorithm=experiment.search_algorithm,
        max_trials=experiment.max_trials,
        status=experiment.status,
        progress=experiment.progress,
        best_score=experiment.best_score,
        created_at=experiment.created_at.isoformat(),
        started_at=experiment.started_at.isoformat() if experiment.started_at else None,
        completed_at=experiment.completed_at.isoformat() if experiment.completed_at else None,
    )


@router.post("/experiments/{experiment_id}/start")
async def start_experiment(
    experiment_id: str,
    data: TrainingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start an AutoML experiment"""
    service = get_automl_service(db)
    experiment = service.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )

    # In a real implementation, this would:
    # 1. Load the data from source_config
    # 2. Preprocess the data
    # 3. Run the AutoML search
    # 4. Save the best model

    # For now, we'll update the status to indicate it's running
    experiment.status = "running"
    experiment.started_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "message": "Experiment started",
        "experiment_id": experiment_id,
    }


@router.post("/experiments/{experiment_id}/stop")
async def stop_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stop a running AutoML experiment"""
    service = get_automl_service(db)
    experiment = service.get_experiment(experiment_id)

    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experiment not found"
        )

    if experiment.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Experiment is not running"
        )

    experiment.status = "cancelled"
    experiment.completed_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Experiment stopped"}


@router.get("/experiments/{experiment_id}/trials", response_model=List[TrialResponse])
async def get_trials(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all trials for an experiment"""
    service = get_automl_service(db)
    trials = service.get_trials(experiment_id)

    return [
        TrialResponse(
            id=str(t.id),
            experiment_id=str(t.experiment_id),
            trial_number=t.trial_number,
            model_type=t.model_type,
            hyperparameters=t.hyperparameters or {},
            status=t.status,
            train_score=t.train_score,
            val_score=t.val_score,
            test_score=t.test_score,
            metrics=t.metrics or {},
            duration_seconds=t.duration_seconds,
            created_at=t.created_at.isoformat(),
        )
        for t in trials
    ]


@router.get("/models", response_model=List[ModelResponse])
async def list_models(
    deployment_status: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List AutoML models"""
    from app.models.automl import AutoMLModel

    query = db.query(AutoMLModel)

    if deployment_status:
        query = query.filter(AutoMLModel.deployment_status == deployment_status)

    if status:
        query = query.filter(AutoMLModel.status == status)

    query = query.order_by(AutoMLModel.created_at.desc())
    query = query.offset(offset).limit(limit)

    models = query.all()

    return [
        ModelResponse(
            id=str(m.id),
            name=m.name,
            version=m.version,
            model_type=m.model_type,
            problem_type=m.problem_type,
            metrics=m.metrics or {},
            deployment_status=m.deployment_status,
            status=m.status,
            created_at=m.created_at.isoformat(),
        )
        for m in models
    ]


# ============================================================================
# Hyperparameter Search Endpoints
# ============================================================================


@router.get("/search-spaces")
async def list_search_spaces(
    model_type: Optional[ModelType] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Get hyperparameter search spaces for model types"""
    from app.services.automl.automl_service import HyperparameterTuner

    tuner = HyperparameterTuner()

    if model_type:
        spaces = {model_type.value: tuner.get_search_space(model_type)}
    else:
        spaces = {}
        for mt in [ModelType.XGBOOST, ModelType.LIGHTGBM, ModelType.RANDOM_FOREST, ModelType.LINEAR]:
            spaces[mt.value] = tuner.get_search_space(mt)

    return {
        "search_spaces": {
            model: [
                {
                    "name": space.name,
                    "type": space.type,
                    "low": space.low,
                    "high": space.high,
                    "choices": space.choices,
                    "log": space.log,
                }
                for space in search_space_list
            ]
            for model, search_space_list in spaces.items()
        }
    }


# ============================================================================
# Model Management Endpoints
# ============================================================================


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a model by ID"""
    from app.models.automl import AutoMLModel

    model = db.query(AutoMLModel).filter(AutoMLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    return ModelResponse(
        id=str(model.id),
        name=model.name,
        version=model.version,
        model_type=model.model_type,
        problem_type=model.problem_type,
        metrics=model.metrics or {},
        deployment_status=model.deployment_status,
        status=model.status,
        created_at=model.created_at.isoformat(),
    )


@router.post("/models/{model_id}/deploy")
async def deploy_model(
    model_id: str,
    deployment_status: str = "staging",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deploy an AutoML model"""
    from app.models.automl import AutoMLModel

    model = db.query(AutoMLModel).filter(AutoMLModel.id == model_id).first()

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found"
        )

    model.deployment_status = deployment_status
    model.deployment_endpoint = f"/api/v1/models/{model_id}/predict"
    model.status = "deployed"
    db.commit()

    return {"success": True, "message": f"Model deployed to {deployment_status}"}


# ============================================================================
# System Endpoints
# ============================================================================


@router.get("/health")
async def health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AutoML system health status"""
    from app.models.automl import AutoMLExperiment, AutoMLTrial, AutoMLModel

    # Get counts
    total_experiments = db.query(AutoMLExperiment).count()
    running_experiments = db.query(AutoMLExperiment).filter(
        AutoMLExperiment.status == "running"
    ).count()
    completed_experiments = db.query(AutoMLExperiment).filter(
        AutoMLExperiment.status == "completed"
    ).count()

    total_trials = db.query(AutoMLTrial).count()
    total_models = db.query(AutoMLModel).count()

    # Get problem type distribution
    problem_dist = db.query(AutoMLExperiment.problem_type).all()
    problem_counts = {}
    for p in problem_dist:
        problem_counts[p] = problem_counts.get(p, 0) + 1

    return {
        "status": "healthy",
        "experiments": {
            "total": total_experiments,
            "running": running_experiments,
            "completed": completed_experiments,
        },
        "trials": {
            "total": total_trials,
        },
        "models": {
            "total": total_models,
        },
        "problem_distribution": problem_counts,
    }
