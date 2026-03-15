"""
AIHub API Endpoints

Provides REST API for algorithm marketplace and model applications.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.aihub.algorithm_marketplace import (
    get_algorithm_marketplace,
    AlgorithmMarketplace,
    AlgorithmCategory,
    AlgorithmFramework,
    AlgorithmLicense,
    Algorithm,
    AlgorithmSubscription,
    AlgorithmDeploymentConfig,
)
from app.services.aihub.app_marketplace import (
    get_app_marketplace,
    AppMarketplace,
    AppCategory,
    AppTemplate,
    ModelApp,
    AppDeployment,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aihub", tags=["AIHub"])


# ============================================================================
# Request/Response Models
# ============================================================================


class AlgorithmResponse(BaseModel):
    """Algorithm response"""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    framework: str
    license: str
    author: Dict[str, Any]
    tags: List[str]
    latest_version: str
    is_public: bool
    is_verified: bool
    downloads: int
    rating: float
    created_at: datetime


class AlgorithmDetailResponse(AlgorithmResponse):
    """Algorithm detail response"""
    repository_url: Optional[str]
    documentation_url: Optional[str]
    paper_url: Optional[str]
    versions: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    hyperparameters: List[Dict[str, Any]]
    input_schema: Optional[Dict[str, Any]]
    output_schema: Optional[Dict[str, Any]]


class AlgorithmSubscribeRequest(BaseModel):
    """Subscribe to algorithm request"""
    algorithm_id: str
    version: Optional[str] = None
    auto_update: bool = True


class AlgorithmDeployRequest(BaseModel):
    """Deploy algorithm request"""
    algorithm_id: str
    version: str = "latest"
    instance_type: str = "cpu"
    replicas: int = 1
    resources: Dict[str, str] = {}
    environment_vars: Dict[str, str] = {}


class TemplateResponse(BaseModel):
    """App template response"""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    icon_url: Optional[str]
    author: str
    version: str
    model_id: Optional[str]
    tags: List[str]
    featured: bool
    verified: bool
    rating: float
    created_at: datetime


class TemplateDetailResponse(TemplateResponse):
    """App template detail response"""
    resources: List[Dict[str, Any]]
    ports: List[Dict[str, Any]]
    config_schema: Optional[Dict[str, Any]]
    default_config: Optional[Dict[str, Any]]


class AppCreateRequest(BaseModel):
    """Create app request"""
    template_id: str
    name: str
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AppResponse(BaseModel):
    """App response"""
    app_id: str
    template_id: str
    name: str
    description: Optional[str]
    user_id: str
    status: str
    replicas: int
    created_at: datetime
    updated_at: datetime


class AppDeployRequest(BaseModel):
    """Deploy app request"""
    name: Optional[str] = None
    namespace: str = "default"
    replicas: Optional[int] = None


class DeploymentResponse(BaseModel):
    """Deployment response"""
    deployment_id: str
    app_id: str
    name: str
    namespace: str
    status: str
    replicas: int
    endpoint: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]


# ============================================================================
# Algorithm Marketplace Endpoints
# ============================================================================


@router.get("/algorithms", response_model=List[AlgorithmResponse])
async def list_algorithms(
    category: Optional[AlgorithmCategory] = None,
    framework: Optional[AlgorithmFramework] = None,
    search: Optional[str] = None,
    verified_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List algorithms from marketplace"""
    marketplace = get_algorithm_marketplace(db)

    algorithms = await marketplace.list_algorithms(
        category=category,
        framework=framework,
        search=search,
        verified_only=verified_only,
        limit=limit,
    )

    return [
        AlgorithmResponse(
            id=algo.id,
            name=algo.name,
            display_name=algo.display_name,
            description=algo.description,
            category=algo.category.value,
            framework=algo.framework.value,
            license=algo.license.value,
            author={
                "name": algo.author.name,
                "organization": algo.author.organization,
                "website": algo.author.website,
            },
            tags=algo.tags,
            latest_version=algo.latest_version,
            is_public=algo.is_public,
            is_verified=algo.is_verified,
            downloads=algo.downloads,
            rating=algo.rating,
            created_at=algo.created_at,
        )
        for algo in algorithms
    ]


@router.get("/algorithms/{algorithm_id}", response_model=AlgorithmDetailResponse)
async def get_algorithm(
    algorithm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get algorithm details"""
    marketplace = get_algorithm_marketplace(db)

    algorithm = await marketplace.get_algorithm(algorithm_id)
    if not algorithm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Algorithm not found"
        )

    return AlgorithmDetailResponse(
        id=algorithm.id,
        name=algorithm.name,
        display_name=algorithm.display_name,
        description=algorithm.description,
        category=algorithm.category.value,
        framework=algorithm.framework.value,
        license=algorithm.license.value,
        author={
            "name": algorithm.author.name,
            "organization": algorithm.author.organization,
            "website": algorithm.author.website,
        },
        tags=algorithm.tags,
        latest_version=algorithm.latest_version,
        is_public=algorithm.is_public,
        is_verified=algorithm.is_verified,
        downloads=algorithm.downloads,
        rating=algorithm.rating,
        repository_url=algorithm.repository_url,
        documentation_url=algorithm.documentation_url,
        paper_url=algorithm.paper_url,
        versions=[
            {
                "version": v.version,
                "created_at": v.created_at,
                "changelog": v.changelog,
                "is_deprecated": v.is_deprecated,
                "tags": v.tags,
            }
            for v in algorithm.versions
        ],
        metrics=[
            {
                "name": m.name,
                "value": m.value,
                "dataset": m.dataset,
                "unit": m.unit,
            }
            for m in algorithm.metrics
        ],
        hyperparameters=[
            {
                "name": hp.name,
                "type": hp.type,
                "default_value": hp.default_value,
                "min_value": hp.min_value,
                "max_value": hp.max_value,
                "choices": hp.choices,
                "description": hp.description,
            }
            for hp in algorithm.hyperparameters
        ],
        input_schema=algorithm.input_schema,
        output_schema=algorithm.output_schema,
        created_at=algorithm.created_at,
    )


@router.post("/algorithms/subscribe")
async def subscribe_algorithm(
    request: AlgorithmSubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Subscribe to an algorithm"""
    marketplace = get_algorithm_marketplace(db)

    subscription = await marketplace.subscribe_algorithm(
        algorithm_id=request.algorithm_id,
        user_id=str(current_user.id),
        version=request.version,
        auto_update=request.auto_update,
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Algorithm not found"
        )

    return {
        "subscription_id": subscription.subscription_id,
        "algorithm_id": subscription.algorithm_id,
        "subscribed_at": subscription.subscribed_at,
        "version": subscription.version,
    }


@router.get("/algorithms/subscriptions")
async def list_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's algorithm subscriptions"""
    marketplace = get_algorithm_marketplace(db)

    subscriptions = await marketplace.list_subscriptions(str(current_user.id))

    return {
        "subscriptions": [
            {
                "subscription_id": s.subscription_id,
                "algorithm_id": s.algorithm_id,
                "version": s.version,
                "subscribed_at": s.subscribed_at,
                "auto_update": s.auto_update,
            }
            for s in subscriptions
        ]
    }


@router.delete("/algorithms/subscriptions/{subscription_id}")
async def unsubscribe_algorithm(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unsubscribe from an algorithm"""
    marketplace = get_algorithm_marketplace(db)

    success = await marketplace.unsubscribe_algorithm(subscription_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )

    return {"success": True, "message": "Unsubscribed"}


@router.post("/algorithms/deploy")
async def deploy_algorithm(
    request: AlgorithmDeployRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deploy an algorithm"""
    marketplace = get_algorithm_marketplace(db)

    config = AlgorithmDeploymentConfig(
        algorithm_id=request.algorithm_id,
        version=request.version,
        instance_type=request.instance_type,
        replicas=request.replicas,
        resources=request.resources,
        environment_vars=request.environment_vars,
    )

    deployment = await marketplace.deploy_algorithm(
        algorithm_id=request.algorithm_id,
        user_id=str(current_user.id),
        config=config,
    )

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Algorithm not found"
        )

    return {
        "deployment_id": deployment.deployment_id,
        "algorithm_id": deployment.algorithm_id,
        "status": deployment.status,
        "created_at": deployment.created_at,
    }


@router.get("/algorithms/deployments")
async def list_algorithm_deployments(
    algorithm_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List algorithm deployments"""
    marketplace = get_algorithm_marketplace(db)

    deployments = await marketplace.list_deployments(
        user_id=str(current_user.id),
        algorithm_id=algorithm_id,
        status=status,
    )

    return {
        "deployments": [
            {
                "deployment_id": d.deployment_id,
                "algorithm_id": d.algorithm_id,
                "status": d.status,
                "created_at": d.created_at,
                "endpoint": d.endpoint,
            }
            for d in deployments
        ]
    }


@router.get("/algorithms/categories")
async def get_algorithm_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get algorithm categories"""
    marketplace = get_algorithm_marketplace(db)

    categories = await marketplace.get_categories()

    return {"categories": categories}


@router.get("/algorithms/search")
async def search_algorithms(
    query: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search algorithms by use case"""
    marketplace = get_algorithm_marketplace(db)

    algorithms = await marketplace.search_by_use_case(query, limit=limit)

    return {
        "query": query,
        "results": [
            {
                "id": algo.id,
                "name": algo.name,
                "display_name": algo.display_name,
                "description": algo.description,
                "category": algo.category.value,
                "framework": algo.framework.value,
            }
            for algo in algorithms
        ]
    }


# ============================================================================
# App Marketplace Endpoints
# ============================================================================


@router.get("/templates", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[AppCategory] = None,
    search: Optional[str] = None,
    featured_only: bool = Query(False),
    verified_only: bool = Query(True),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List app templates"""
    marketplace = get_app_marketplace(db)

    templates = await marketplace.list_templates(
        category=category,
        search=search,
        featured_only=featured_only,
        verified_only=verified_only,
        limit=limit,
    )

    return [
        TemplateResponse(
            id=t.id,
            name=t.name,
            display_name=t.display_name,
            description=t.description,
            category=t.category.value,
            icon_url=t.icon_url,
            author=t.author,
            version=t.version,
            model_id=t.model_id,
            tags=t.tags,
            featured=t.featured,
            verified=t.verified,
            rating=t.rating,
            created_at=t.created_at,
        )
        for t in templates
    ]


@router.get("/templates/featured")
async def get_featured_templates(
    limit: int = Query(6, ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get featured app templates"""
    marketplace = get_app_marketplace(db)

    templates = await marketplace.get_featured_templates(limit=limit)

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "category": t.category.value,
                "icon_url": t.icon_url,
                "rating": t.rating,
                "downloads": t.downloads,
            }
            for t in templates
        ]
    }


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get template details"""
    marketplace = get_app_marketplace(db)

    template = await marketplace.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        display_name=template.display_name,
        description=template.description,
        category=template.category.value,
        icon_url=template.icon_url,
        author=template.author,
        version=template.version,
        model_id=template.model_id,
        tags=template.tags,
        featured=template.featured,
        verified=template.verified,
        rating=template.rating,
        created_at=template.created_at,
        resources=[
            {
                "type": r.resource_type,
                "request": r.request,
                "limit": r.limit,
            }
            for r in template.resources
        ],
        ports=[
            {
                "port": p.port,
                "protocol": p.protocol,
                "service": p.service,
            }
            for p in template.ports
        ],
        config_schema=template.config_schema,
        default_config=template.default_config,
    )


@router.post("/apps", response_model=AppResponse)
async def create_app(
    request: AppCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create app from template"""
    marketplace = get_app_marketplace(db)

    app = await marketplace.create_app(
        template_id=request.template_id,
        name=request.name,
        user_id=str(current_user.id),
        config=request.config,
        description=request.description,
    )

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )

    return AppResponse(
        app_id=app.app_id,
        template_id=app.template_id,
        name=app.name,
        description=app.description,
        user_id=app.user_id,
        status=app.status.value,
        replicas=app.replicas,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.get("/apps", response_model=List[AppResponse])
async def list_apps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List user's apps"""
    marketplace = get_app_marketplace(db)

    apps = await marketplace.list_apps(user_id=str(current_user.id))

    return [
        AppResponse(
            app_id=a.app_id,
            template_id=a.template_id,
            name=a.name,
            description=a.description,
            user_id=a.user_id,
            status=a.status.value,
            replicas=a.replicas,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in apps
    ]


@router.get("/apps/{app_id}", response_model=AppResponse)
async def get_app(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get app details"""
    marketplace = get_app_marketplace(db)

    app = await marketplace.get_app(app_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return AppResponse(
        app_id=app.app_id,
        template_id=app.template_id,
        name=app.name,
        description=app.description,
        user_id=app.user_id,
        status=app.status.value,
        replicas=app.replicas,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


@router.put("/apps/{app_id}")
async def update_app(
    app_id: str,
    config: Optional[Dict[str, Any]] = Body(None),
    replicas: Optional[int] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update app configuration"""
    marketplace = get_app_marketplace(db)

    app = await marketplace.update_app(
        app_id=app_id,
        config=config,
        replicas=replicas,
    )

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return {"success": True, "message": "App updated"}


@router.delete("/apps/{app_id}")
async def delete_app(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an app"""
    marketplace = get_app_marketplace(db)

    success = await marketplace.delete_app(app_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return {"success": True, "message": "App deleted"}


@router.post("/apps/{app_id}/deploy", response_model=DeploymentResponse)
async def deploy_app(
    app_id: str,
    request: AppDeployRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deploy an app"""
    marketplace = get_app_marketplace(db)

    deployment = await marketplace.deploy_app(
        app_id=app_id,
        name=request.name,
        namespace=request.namespace,
        replicas=request.replicas,
    )

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="App not found"
        )

    return DeploymentResponse(
        deployment_id=deployment.deployment_id,
        app_id=deployment.app_id,
        name=deployment.name,
        namespace=deployment.namespace,
        status=deployment.status.value,
        replicas=deployment.replicas,
        endpoint=deployment.endpoint,
        created_at=deployment.created_at,
        started_at=deployment.started_at,
    )


@router.get("/apps/{app_id}/deployments")
async def list_app_deployments(
    app_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List app deployments"""
    marketplace = get_app_marketplace(db)

    deployments = await marketplace.list_deployments(app_id=app_id)

    return {
        "deployments": [
            {
                "deployment_id": d.deployment_id,
                "app_id": d.app_id,
                "name": d.name,
                "namespace": d.namespace,
                "status": d.status.value,
                "replicas": d.replicas,
                "endpoint": d.endpoint,
                "created_at": d.created_at,
                "started_at": d.started_at,
            }
            for d in deployments
        ]
    }


@router.post("/deployments/{deployment_id}/stop")
async def stop_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stop a deployment"""
    marketplace = get_app_marketplace(db)

    success = await marketplace.stop_deployment(deployment_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    return {"success": True, "message": "Deployment stopped"}


@router.post("/deployments/{deployment_id}/scale")
async def scale_deployment(
    deployment_id: str,
    replicas: int = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scale a deployment"""
    marketplace = get_app_marketplace(db)

    success = await marketplace.scale_deployment(deployment_id, replicas)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )

    return {"success": True, "message": f"Scaled to {replicas} replicas"}


@router.get("/deployments/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    tail_lines: int = Query(100, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get deployment logs"""
    marketplace = get_app_marketplace(db)

    logs = await marketplace.get_deployment_logs(deployment_id, tail_lines)

    return {
        "deployment_id": deployment_id,
        "logs": logs,
    }


@router.get("/categories")
async def get_app_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get app categories"""
    marketplace = get_app_marketplace(db)

    categories = await marketplace.get_categories()

    return {"categories": categories}
