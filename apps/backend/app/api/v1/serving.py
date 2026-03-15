"""
Model Serving API Endpoints

Provides REST API for:
- Inference service management
- A/B testing experiments
- Canary deployments
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.serving import (
    ServingPlatform,
    ServingStatus,
    PredictorType,
    DeploymentMode,
    InferenceService,
    ModelServingService,
    get_serving_service,
    TrafficSplitMethod,
    SuccessMetricType,
    ABTestExperiment,
    ABTestingService,
    get_ab_testing_service,
    CanaryPhase,
    CanaryStrategy,
    CanaryDeployment,
    CanaryService,
    get_canary_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/serving", tags=["Model Serving"])


# ============================================================================
# Request/Response Schemas
# ============================================================================


class PredictorConfigSchema(BaseModel):
    """Predictor configuration schema"""

    predictor_type: PredictorType
    model_uri: str
    runtime_version: Optional[str] = None
    protocol: str = "v1"
    storage_uri: Optional[str] = None
    framework: Optional[str] = None
    device: str = "cpu"
    replicas: int = 1
    resource_requirements: Dict[str, str] = {}
    batch_size: Optional[int] = None
    max_batch_size: Optional[int] = None
    timeout: int = 60
    custom_predictor_image: Optional[str] = None
    custom_predictor_args: List[str] = []
    env: Dict[str, str] = {}


class ABTestConfigSchema(BaseModel):
    """A/B testing configuration schema"""

    experiment_id: str
    model_variants: List[Dict[str, Any]]
    duration: Optional[str] = None
    sample_size: Optional[int] = None
    success_metric: str = "accuracy"
    success_mode: str = "max"
    min_sample_size: int = 100
    traffic_split_method: str = "fixed"


class CanaryConfigSchema(BaseModel):
    """Canary deployment configuration schema"""

    canary_model_uri: str
    canary_predictor_config: PredictorConfigSchema
    baseline_model_uri: str
    baseline_predictor_config: PredictorConfigSchema
    canary_traffic_percentage: int = 10
    auto_promote: bool = True
    promotion_threshold: float = 0.95
    monitoring_window: str = "1h"
    min_requests: int = 100
    auto_rollback: bool = True
    rollback_threshold: float = 0.90


class CreateInferenceServiceRequest(BaseModel):
    """Request to create inference service"""

    name: str = Field(..., description="Service name")
    namespace: str = "default"
    description: Optional[str] = None
    tags: List[str] = []
    platform: ServingPlatform = ServingPlatform.KSERVE
    mode: DeploymentMode = DeploymentMode.RAW
    predictor_config: Optional[PredictorConfigSchema] = None
    ab_test_config: Optional[ABTestConfigSchema] = None
    canary_config: Optional[CanaryConfigSchema] = None
    autoscaling_enabled: bool = False
    min_replicas: int = 1
    max_replicas: int = 3
    target_requests_per_second: int = 10
    enable_logging: bool = True
    log_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
    project_id: Optional[int] = None


class UpdateInferenceServiceRequest(BaseModel):
    """Request to update inference service"""

    description: Optional[str] = None
    tags: Optional[List[str]] = None
    predictor_config: Optional[PredictorConfigSchema] = None
    autoscaling_enabled: Optional[bool] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    target_requests_per_second: Optional[int] = None


class ScaleServiceRequest(BaseModel):
    """Request to scale service"""

    replicas: int = Field(..., ge=0, le=100)


class UpdateTrafficRequest(BaseModel):
    """Request to update traffic split"""

    traffic_distribution: Dict[str, int] = Field(
        ...,
        description="Traffic distribution mapping variant name to percentage",
    )


class CreateABTestRequest(BaseModel):
    """Request to create A/B test"""

    name: str
    description: Optional[str] = None
    variants: List[Dict[str, Any]]
    success_metric: SuccessMetricType = SuccessMetricType.ACCURACY
    split_method: TrafficSplitMethod = TrafficSplitMethod.FIXED
    duration_hours: Optional[int] = None
    min_sample_size: int = 100
    confidence_level: float = 0.95
    project_id: Optional[int] = None
    tags: List[str] = []


class CreateCanaryDeploymentRequest(BaseModel):
    """Request to create canary deployment"""

    service_name: str
    baseline_model_uri: str
    baseline_version: str = "current"
    canary_model_uri: str
    canary_version: str = "canary"
    strategy: CanaryStrategy = CanaryStrategy.LINEAR
    steps: Optional[int] = 5
    duration_minutes: int = 60
    auto_promote: bool = True
    auto_rollback: bool = True
    rollback_threshold: float = 0.10
    max_error_rate: Optional[float] = None
    max_latency_p95_ms: Optional[float] = None


# ============================================================================
# Inference Service Endpoints
# ============================================================================


@router.get("/services", response_model=List[Dict[str, Any]])
async def list_inference_services(
    status_filter: Optional[ServingStatus] = None,
    platform_filter: Optional[ServingPlatform] = None,
    project_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """
    List all inference services

    Requires authentication.
    """
    service = get_serving_service()

    services = []
    for svc in service._services.values():
        if status_filter and svc.status != status_filter:
            continue
        if platform_filter and svc.platform != platform_filter:
            continue
        if project_id and svc.project_id != project_id:
            continue

        services.append({
            "name": svc.name,
            "namespace": svc.namespace,
            "description": svc.description,
            "platform": svc.platform.value,
            "mode": svc.mode.value,
            "status": svc.status.value,
            "status_message": svc.status_message,
            "endpoint": svc.endpoint,
            "url": svc.url,
            "autoscaling_enabled": svc.autoscaling_enabled,
            "min_replicas": svc.min_replicas,
            "max_replicas": svc.max_replicas,
            "enable_logging": svc.enable_logging,
            "tags": svc.tags,
            "project_id": svc.project_id,
            "created_at": svc.created_at.isoformat(),
            "updated_at": svc.updated_at.isoformat(),
        })

    return services


@router.post("/services", response_model=Dict[str, Any])
async def create_inference_service(
    request: CreateInferenceServiceRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new inference service

    Requires authentication.
    """
    service = get_serving_service(platform=request.platform)

    # Convert predictor config
    predictor_config = None
    if request.predictor_config:
        predictor_config = PredictorConfig(
            predictor_type=request.predictor_config.predictor_type,
            model_uri=request.predictor_config.model_uri,
            runtime_version=request.predictor_config.runtime_version,
            protocol=request.predictor_config.protocol,
            storage_uri=request.predictor_config.storage_uri,
            framework=request.predictor_config.framework,
            device=request.predictor_config.device,
            replicas=request.predictor_config.replicas,
            resource_requirements=request.predictor_config.resource_requirements,
            batch_size=request.predictor_config.batch_size,
            max_batch_size=request.predictor_config.max_batch_size,
            timeout=request.predictor_config.timeout,
            custom_predictor_image=request.predictor_config.custom_predictor_image,
            custom_predictor_args=request.predictor_config.custom_predictor_args,
            env=request.predictor_config.env,
        )

    # Convert A/B test config
    ab_test_config = None
    if request.ab_test_config:
        from app.services.serving import ABTestConfig
        ab_test_config = ABTestConfig(
            experiment_id=request.ab_test_config.experiment_id,
            model_variants=request.ab_test_config.model_variants,
            duration=request.ab_test_config.duration,
            sample_size=request.ab_test_config.sample_size,
            success_metric=request.ab_test_config.success_metric,
            success_mode=request.ab_test_config.success_mode,
            min_sample_size=request.ab_test_config.min_sample_size,
            traffic_split_method=request.ab_test_config.traffic_split_method,
        )

    # Convert canary config
    canary_config = None
    if request.canary_config:
        from app.services.serving import CanaryConfig, PredictorConfig
        canary_predictor = PredictorConfig(
            **request.canary_config.canary_predictor_config.dict()
        )
        baseline_predictor = PredictorConfig(
            **request.canary_config.baseline_predictor_config.dict()
        )
        canary_config = CanaryConfig(
            canary_model_uri=request.canary_config.canary_model_uri,
            canary_predictor_config=canary_predictor,
            baseline_model_uri=request.canary_config.baseline_model_uri,
            baseline_predictor_config=baseline_predictor,
            canary_traffic_percentage=request.canary_config.canary_traffic_percentage,
            auto_promote=request.canary_config.auto_promote,
            promotion_threshold=request.canary_config.promotion_threshold,
            monitoring_window=request.canary_config.monitoring_window,
            min_requests=request.canary_config.min_requests,
            auto_rollback=request.canary_config.auto_rollback,
            rollback_threshold=request.canary_config.rollback_threshold,
        )

    inference_service = InferenceService(
        name=request.name,
        namespace=request.namespace,
        description=request.description,
        tags=request.tags,
        platform=request.platform,
        mode=request.mode,
        predictor_config=predictor_config,
        ab_test_config=ab_test_config,
        canary_config=canary_config,
        autoscaling_enabled=request.autoscaling_enabled,
        min_replicas=request.min_replicas,
        max_replicas=request.max_replicas,
        target_requests_per_second=request.target_requests_per_second,
        enable_logging=request.enable_logging,
        log_url=request.log_url,
        metadata=request.metadata,
        project_id=request.project_id,
        owner_id=current_user.id,
    )

    deployed = await service.deploy_service(inference_service)

    return {
        "name": deployed.name,
        "namespace": deployed.namespace,
        "status": deployed.status.value,
        "endpoint": deployed.endpoint,
        "message": "Inference service deployed successfully",
    }


@router.get("/services/{service_name}", response_model=Dict[str, Any])
async def get_inference_service(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get inference service details"""
    serving_service = get_serving_service()
    service = serving_service._services.get(service_name)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found",
        )

    return {
        "name": service.name,
        "namespace": service.namespace,
        "description": service.description,
        "platform": service.platform.value,
        "mode": service.mode.value,
        "status": service.status.value,
        "status_message": service.status_message,
        "endpoint": service.endpoint,
        "url": service.url,
        "autoscaling_enabled": service.autoscaling_enabled,
        "min_replicas": service.min_replicas,
        "max_replicas": service.max_replicas,
        "target_requests_per_second": service.target_requests_per_second,
        "enable_logging": service.enable_logging,
        "log_url": service.log_url,
        "tags": service.tags,
        "traffic_distribution": service.get_traffic_distribution(),
        "project_id": service.project_id,
        "owner_id": service.owner_id,
        "created_at": service.created_at.isoformat(),
        "updated_at": service.updated_at.isoformat(),
    }


@router.put("/services/{service_name}", response_model=Dict[str, Any])
async def update_inference_service(
    service_name: str,
    request: UpdateInferenceServiceRequest,
    current_user: User = Depends(get_current_user),
):
    """Update inference service configuration"""
    serving_service = get_serving_service()

    existing = serving_service._services.get(service_name)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found",
        )

    # Update fields
    if request.description is not None:
        existing.description = request.description
    if request.tags is not None:
        existing.tags = request.tags
    if request.autoscaling_enabled is not None:
        existing.autoscaling_enabled = request.autoscaling_enabled
    if request.min_replicas is not None:
        existing.min_replicas = request.min_replicas
    if request.max_replicas is not None:
        existing.max_replicas = request.max_replicas
    if request.target_requests_per_second is not None:
        existing.target_requests_per_second = request.target_requests_per_second

    existing.updated_at = datetime.utcnow()

    return {
        "name": existing.name,
        "status": existing.status.value,
        "message": "Service updated successfully",
    }


@router.delete("/services/{service_name}")
async def delete_inference_service(
    service_name: str,
    namespace: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Delete (undeploy) inference service"""
    serving_service = get_serving_service()

    success = await serving_service.undeploy_service(service_name, namespace)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found",
        )

    return {"message": f"Service {service_name} deleted successfully"}


@router.post("/services/{service_name}/scale", response_model=Dict[str, Any])
async def scale_service(
    service_name: str,
    request: ScaleServiceRequest,
    current_user: User = Depends(get_current_user),
):
    """Scale service replicas"""
    serving_service = get_serving_service()

    success = await serving_service.scale_service(service_name, request.replicas)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found",
        )

    return {
        "name": service_name,
        "replicas": request.replicas,
        "message": "Service scaled successfully",
    }


@router.get("/services/{service_name}/traffic", response_model=Dict[str, int])
async def get_traffic_distribution(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get current traffic distribution"""
    serving_service = get_serving_service()

    try:
        distribution = serving_service.get_traffic_distribution(service_name)
        return distribution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/services/{service_name}/traffic")
async def update_traffic_distribution(
    service_name: str,
    request: UpdateTrafficRequest,
    current_user: User = Depends(get_current_user),
):
    """Update traffic distribution for A/B testing or canary"""
    serving_service = get_serving_service()

    try:
        await serving_service.update_traffic_split(service_name, request.traffic_distribution)
        return {
            "message": "Traffic distribution updated successfully",
            "traffic_distribution": request.traffic_distribution,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/services/{service_name}/metrics")
async def get_service_metrics(
    service_name: str,
    duration: str = "1h",
    current_user: User = Depends(get_current_user),
):
    """Get service metrics"""
    serving_service = get_serving_service()

    metrics = await serving_service.get_service_metrics(service_name, duration)

    return {
        "service_name": service_name,
        "duration": duration,
        "metrics": metrics,
    }


@router.get("/services/{service_name}/status")
async def get_service_status(
    service_name: str,
    current_user: User = Depends(get_current_user),
):
    """Get service status"""
    serving_service = get_serving_service()

    status = await serving_service.get_service_status(service_name)

    if status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found",
        )

    return {
        "service_name": service_name,
        "status": status.value,
    }


# ============================================================================
# A/B Testing Endpoints
# ============================================================================


@router.get("/ab-tests", response_model=List[Dict[str, Any]])
async def list_ab_tests(
    project_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    """List A/B testing experiments"""
    ab_service = get_ab_testing_service()

    experiments = await ab_service.list_experiments(
        project_id=project_id,
        is_active=is_active,
    )

    return [
        {
            "experiment_id": exp.experiment_id,
            "name": exp.name,
            "description": exp.description,
            "is_active": exp.is_active,
            "is_running": exp.is_running(),
            "success_metric": exp.success_metric.value,
            "split_method": exp.split_method.value,
            "variant_count": len(exp.variants),
            "has_minimum_samples": exp.has_minimum_samples(),
            "winner_variant_id": exp.winner_variant_id,
            "project_id": exp.project_id,
            "created_at": exp.created_at.isoformat(),
            "updated_at": exp.updated_at.isoformat(),
        }
        for exp in experiments
    ]


@router.post("/ab-tests", response_model=Dict[str, Any])
async def create_ab_test(
    request: CreateABTestRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new A/B testing experiment"""
    ab_service = get_ab_testing_service()

    experiment = await ab_service.create_experiment(
        name=request.name,
        variants=request.variants,
        success_metric=request.success_metric,
        split_method=request.split_method,
        duration_hours=request.duration_hours,
        min_sample_size=request.min_sample_size,
        confidence_level=request.confidence_level,
        description=request.description,
        project_id=request.project_id,
        tags=request.tags,
        owner_id=current_user.id,
    )

    return {
        "experiment_id": experiment.experiment_id,
        "name": experiment.name,
        "variants": [
            {
                "variant_id": v.variant_id,
                "name": v.name,
                "traffic_percentage": v.traffic_percentage,
            }
            for v in experiment.variants
        ],
        "message": "A/B test created successfully",
    }


@router.get("/ab-tests/{experiment_id}", response_model=Dict[str, Any])
async def get_ab_test(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get A/B test details"""
    ab_service = get_ab_testing_service()

    experiment = await ab_service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    results = await ab_service.get_experiment_results(experiment_id)

    return results


@router.post("/ab-tests/{experiment_id}/traffic")
async def update_ab_test_traffic(
    experiment_id: str,
    request: UpdateTrafficRequest,
    current_user: User = Depends(get_current_user),
):
    """Update traffic split for A/B test"""
    ab_service = get_ab_testing_service()

    try:
        await ab_service.update_traffic_split(experiment_id, request.traffic_distribution)
        return {
            "message": "Traffic split updated successfully",
            "traffic_distribution": request.traffic_distribution,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/ab-tests/{experiment_id}/significance")
async def run_significance_test(
    experiment_id: str,
    treatment_variant_id: str,
    current_user: User = Depends(get_current_user),
):
    """Run statistical significance test"""
    ab_service = get_ab_testing_service()

    try:
        result = await ab_service.run_significance_test(experiment_id, treatment_variant_id)
        return {
            "is_significant": result.is_significant,
            "p_value": result.p_value,
            "confidence_interval": result.confidence_interval,
            "effect_size": result.effect_size,
            "control_metric": result.control_metric,
            "treatment_metric": result.treatment_metric,
            "relative_improvement": result.relative_improvement,
            "should_promote": result.should_promote,
            "recommendation": result.recommendation,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/ab-tests/{experiment_id}/winner")
async def select_winner(
    experiment_id: str,
    winner_variant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """Select winner variant and end experiment"""
    ab_service = get_ab_testing_service()

    try:
        experiment = await ab_service.select_winner(experiment_id, winner_variant_id)
        return {
            "experiment_id": experiment.experiment_id,
            "winner_variant_id": experiment.winner_variant_id,
            "message": "Winner selected successfully",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/ab-tests/{experiment_id}/pause")
async def pause_ab_test(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Pause A/B test"""
    ab_service = get_ab_testing_service()
    success = await ab_service.pause_experiment(experiment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return {"message": "Experiment paused successfully"}


@router.post("/ab-tests/{experiment_id}/resume")
async def resume_ab_test(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resume paused A/B test"""
    ab_service = get_ab_testing_service()
    success = await ab_service.resume_experiment(experiment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return {"message": "Experiment resumed successfully"}


@router.delete("/ab-tests/{experiment_id}")
async def delete_ab_test(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete A/B test"""
    ab_service = get_ab_testing_service()
    success = await ab_service.delete_experiment(experiment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )

    return {"message": "Experiment deleted successfully"}


# ============================================================================
# Canary Deployment Endpoints
# ============================================================================


@router.get("/canaries", response_model=List[Dict[str, Any]])
async def list_canary_deployments(
    service_name: Optional[str] = None,
    phase: Optional[CanaryPhase] = None,
    current_user: User = Depends(get_current_user),
):
    """List canary deployments"""
    canary_service = get_canary_service()

    deployments = await canary_service.list_deployments(
        service_name=service_name,
        phase=phase,
    )

    return [
        {
            "deployment_id": d.deployment_id,
            "name": d.name,
            "service_name": d.service_name,
            "phase": d.phase.value,
            "is_running": d.is_running,
            "is_complete": d.is_complete,
            "current_step": d.current_step_index + 1,
            "total_steps": len(d.steps),
            "current_traffic_percentage": d.current_traffic_percentage,
            "progress_percentage": d.progress_percentage,
            "baseline_model": d.baseline_model_uri,
            "canary_model": d.canary_model_uri,
            "created_at": d.created_at.isoformat(),
            "started_at": d.started_at.isoformat() if d.started_at else None,
            "completed_at": d.completed_at.isoformat() if d.completed_at else None,
        }
        for d in deployments
    ]


@router.post("/canaries", response_model=Dict[str, Any])
async def create_canary_deployment(
    request: CreateCanaryDeploymentRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new canary deployment"""
    canary_service = get_canary_service()

    deployment = await canary_service.create_canary_deployment(
        service_name=request.service_name,
        baseline_model_uri=request.baseline_model_uri,
        baseline_version=request.baseline_version,
        canary_model_uri=request.canary_model_uri,
        canary_version=request.canary_version,
        strategy=request.strategy,
        steps=request.steps,
        duration_minutes=request.duration_minutes,
        auto_promote=request.auto_promote,
        auto_rollback=request.auto_rollback,
        rollback_threshold=request.rollback_threshold,
        max_error_rate=request.max_error_rate,
        max_latency_p95_ms=request.max_latency_p95_ms,
        owner_id=current_user.id,
    )

    return {
        "deployment_id": deployment.deployment_id,
        "name": deployment.name,
        "service_name": deployment.service_name,
        "steps": len(deployment.steps),
        "strategy": deployment.strategy.value,
        "message": "Canary deployment created successfully",
    }


@router.get("/canaries/{deployment_id}")
async def get_canary_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get canary deployment status"""
    canary_service = get_canary_service()

    status = await canary_service.get_deployment_status(deployment_id)

    return status


@router.post("/canaries/{deployment_id}/start")
async def start_canary_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Start canary deployment"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.start_deployment(deployment_id)
        return {
            "deployment_id": deployment.deployment_id,
            "phase": deployment.phase.value,
            "message": "Canary deployment started",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/canaries/{deployment_id}/promote")
async def promote_canary(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Promote canary to 100% traffic"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.promote_canary(deployment_id)
        return {
            "deployment_id": deployment.deployment_id,
            "phase": deployment.phase.value,
            "message": "Canary promoted successfully",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/canaries/{deployment_id}/rollback")
async def rollback_canary_deployment(
    deployment_id: str,
    reason: Optional[str] = "Manual rollback",
    current_user: User = Depends(get_current_user),
):
    """Rollback canary deployment"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.rollback_deployment(deployment_id, reason)
        return {
            "deployment_id": deployment.deployment_id,
            "phase": deployment.phase.value,
            "message": f"Canary rolled back: {reason}",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/canaries/{deployment_id}/pause")
async def pause_canary_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Pause canary deployment"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.pause_deployment(deployment_id)
        return {
            "deployment_id": deployment.deployment_id,
            "phase": deployment.phase.value,
            "message": "Canary deployment paused",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/canaries/{deployment_id}/resume")
async def resume_canary_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Resume paused canary deployment"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.resume_deployment(deployment_id)
        return {
            "deployment_id": deployment.deployment_id,
            "phase": deployment.phase.value,
            "message": "Canary deployment resumed",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/canaries/{deployment_id}/traffic")
async def set_canary_traffic(
    deployment_id: str,
    traffic_percentage: int = Query(..., ge=0, le=100),
    current_user: User = Depends(get_current_user),
):
    """Manually set canary traffic percentage"""
    canary_service = get_canary_service()

    try:
        deployment = await canary_service.set_traffic_percentage(
            deployment_id,
            traffic_percentage,
        )
        return {
            "deployment_id": deployment.deployment_id,
            "current_traffic_percentage": deployment.current_traffic_percentage,
            "message": f"Traffic set to {traffic_percentage}%",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/canaries/{deployment_id}")
async def delete_canary_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete canary deployment"""
    canary_service = get_canary_service()
    success = await canary_service.delete_deployment(deployment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found",
        )

    return {"message": "Canary deployment deleted successfully"}
