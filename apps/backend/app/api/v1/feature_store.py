"""
Feature Store API Endpoints

Provides endpoints for managing features, feature groups, feature views, and feature services.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.feature_store import (
    get_feature_store_service,
    get_feature_serving_service,
    DataType,
    FeatureStoreType,
    FeatureType,
    RetrievalMode,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-store", tags=["Feature Store"])


# ============================================================================
# Request/Response Models
# ============================================================================


class EntityCreate(BaseModel):
    """Request model for creating an entity"""
    name: str = Field(..., description="Unique entity name")
    display_name: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    join_keys: List[str] = []
    tags: List[str] = []


class EntityResponse(BaseModel):
    """Response model for entity"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    entity_type: Optional[str]
    join_keys: List[str]
    tags: List[str]
    created_at: str


class FeatureGroupCreate(BaseModel):
    """Request model for creating a feature group"""
    name: str = Field(..., description="Unique feature group name")
    display_name: Optional[str] = None
    description: Optional[str] = None
    entity_id: Optional[str] = None
    primary_keys: List[str] = []
    store_type: FeatureStoreType = FeatureStoreType.OFFLINE
    source_type: Optional[str] = None
    source_config: Dict[str, Any] = {}
    schedule_cron: Optional[str] = None
    tags: List[str] = []


class FeatureGroupResponse(BaseModel):
    """Response model for feature group"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    entity_id: Optional[str]
    primary_keys: List[str]
    store_type: str
    source_type: Optional[str]
    status: str
    feature_count: int
    row_count: int
    created_at: str
    updated_at: str


class FeatureCreate(BaseModel):
    """Request model for creating a feature"""
    name: str
    data_type: DataType
    display_name: Optional[str] = None
    description: Optional[str] = None
    entity_id: Optional[str] = None
    feature_type: Optional[FeatureType] = None
    dimension: Optional[int] = None
    validation_config: Dict[str, Any] = {}
    transformation: Optional[str] = None
    transformation_config: Dict[str, Any] = {}
    tags: List[str] = []


class FeatureResponse(BaseModel):
    """Response model for feature"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    feature_group_id: str
    data_type: str
    feature_type: Optional[str]
    dimension: Optional[int]
    null_percentage: float
    mean_value: Optional[float]
    created_at: str


class FeatureViewCreate(BaseModel):
    """Request model for creating a feature view"""
    name: str
    feature_group_id: str
    feature_ids: List[str]
    display_name: Optional[str] = None
    description: Optional[str] = None
    view_type: str = "selection"
    transformation_sql: Optional[str] = None
    transformation_config: Dict[str, Any] = {}
    serving_mode: str = "online"
    ttl_seconds: int = 86400
    tags: List[str] = []


class FeatureViewResponse(BaseModel):
    """Response model for feature view"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    feature_group_id: str
    feature_ids: List[str]
    view_type: str
    serving_mode: str
    ttl_seconds: int
    status: str
    created_at: str


class FeatureServiceCreate(BaseModel):
    """Request model for creating a feature service"""
    name: str
    feature_view_ids: List[str]
    display_name: Optional[str] = None
    description: Optional[str] = None
    serving_type: str = "low_latency"
    max_qps: int = 1000
    target_p95_latency_ms: int = 50
    enable_cache: bool = True
    cache_ttl_seconds: int = 300
    tags: List[str] = []


class FeatureServiceResponse(BaseModel):
    """Response model for feature service"""
    id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    feature_view_ids: List[str]
    serving_type: str
    endpoint_path: Optional[str]
    deployment_status: str
    status: str
    total_requests: int
    avg_latency_ms: float
    created_at: str
    deployed_at: Optional[str]


class FeatureRetrievalRequest(BaseModel):
    """Request model for feature retrieval"""
    entity_keys: List[Dict[str, Any]]
    feature_view_names: List[str]
    point_in_time: Optional[str] = None
    mode: RetrievalMode = RetrievalMode.ONLINE


class FeatureSetCreate(BaseModel):
    """Request model for creating a feature set"""
    name: str
    feature_view_ids: List[str]
    snapshot_time: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []


# ============================================================================
# Entity Endpoints
# ============================================================================


@router.post("/entities", response_model=EntityResponse)
async def create_entity(
    data: EntityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new entity"""
    service = get_feature_store_service(db)

    entity = service.create_entity(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        entity_type=data.entity_type,
        join_keys=data.join_keys,
        tags=data.tags,
    )

    return EntityResponse(
        id=str(entity.id),
        name=entity.name,
        display_name=entity.display_name,
        description=entity.description,
        entity_type=entity.entity_type,
        join_keys=entity.join_keys or [],
        tags=entity.tags or [],
        created_at=entity.created_at.isoformat(),
    )


@router.get("/entities", response_model=List[EntityResponse])
async def list_entities(
    entity_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all entities"""
    service = get_feature_store_service(db)

    entities = service.list_entities(
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )

    return [
        EntityResponse(
            id=str(e.id),
            name=e.name,
            display_name=e.display_name,
            description=e.description,
            entity_type=e.entity_type,
            join_keys=e.join_keys or [],
            tags=e.tags or [],
            created_at=e.created_at.isoformat(),
        )
        for e in entities
    ]


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get an entity by ID"""
    service = get_feature_store_service(db)
    entity = service.get_entity(entity_id)

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found"
        )

    return EntityResponse(
        id=str(entity.id),
        name=entity.name,
        display_name=entity.display_name,
        description=entity.description,
        entity_type=entity.entity_type,
        join_keys=entity.join_keys or [],
        tags=entity.tags or [],
        created_at=entity.created_at.isoformat(),
    )


# ============================================================================
# Feature Group Endpoints
# ============================================================================


@router.post("/feature-groups", response_model=FeatureGroupResponse)
async def create_feature_group(
    data: FeatureGroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new feature group"""
    service = get_feature_store_service(db)

    group = service.create_feature_group(
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        entity_id=data.entity_id,
        primary_keys=data.primary_keys,
        store_type=data.store_type,
        source_type=data.source_type,
        source_config=data.source_config,
        owner_id=str(current_user.id),
        tags=data.tags,
    )

    return FeatureGroupResponse(
        id=str(group.id),
        name=group.name,
        display_name=group.display_name,
        description=group.description,
        entity_id=str(group.entity_id) if group.entity_id else None,
        primary_keys=group.primary_keys or [],
        store_type=group.store_type,
        source_type=group.source_type,
        status=group.status,
        feature_count=group.feature_count,
        row_count=group.row_count,
        created_at=group.created_at.isoformat(),
        updated_at=group.updated_at.isoformat(),
    )


@router.get("/feature-groups", response_model=List[FeatureGroupResponse])
async def list_feature_groups(
    entity_id: Optional[str] = Query(None),
    store_type: Optional[FeatureStoreType] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List feature groups"""
    service = get_feature_store_service(db)

    groups = service.list_feature_groups(
        entity_id=entity_id,
        store_type=store_type,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        FeatureGroupResponse(
            id=str(g.id),
            name=g.name,
            display_name=g.display_name,
            description=g.description,
            entity_id=str(g.entity_id) if g.entity_id else None,
            primary_keys=g.primary_keys or [],
            store_type=g.store_type,
            source_type=g.source_type,
            status=g.status,
            feature_count=g.feature_count,
            row_count=g.row_count,
            created_at=g.created_at.isoformat(),
            updated_at=g.updated_at.isoformat(),
        )
        for g in groups
    ]


@router.get("/feature-groups/{group_id}", response_model=FeatureGroupResponse)
async def get_feature_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a feature group by ID"""
    service = get_feature_store_service(db)
    group = service.get_feature_group(group_id)

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature group not found"
        )

    return FeatureGroupResponse(
        id=str(group.id),
        name=group.name,
        display_name=group.display_name,
        description=group.description,
        entity_id=str(group.entity_id) if group.entity_id else None,
        primary_keys=group.primary_keys or [],
        store_type=group.store_type,
        source_type=group.source_type,
        status=group.status,
        feature_count=group.feature_count,
        row_count=group.row_count,
        created_at=group.created_at.isoformat(),
        updated_at=group.updated_at.isoformat(),
    )


@router.put("/feature-groups/{group_id}")
async def update_feature_group(
    group_id: str,
    display_name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    source_config: Optional[Dict[str, Any]] = Body(None),
    schedule_cron: Optional[str] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a feature group"""
    service = get_feature_store_service(db)
    group = service.update_feature_group(
        group_id,
        display_name=display_name,
        description=description,
        source_config=source_config,
        schedule_cron=schedule_cron,
        tags=tags,
    )

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature group not found"
        )

    return {"success": True, "message": "Feature group updated"}


@router.delete("/feature-groups/{group_id}")
async def delete_feature_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a feature group"""
    service = get_feature_store_service(db)
    success = service.delete_feature_group(group_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature group not found"
        )

    return {"success": True, "message": "Feature group deleted"}


# ============================================================================
# Feature Endpoints
# ============================================================================


@router.post("/features", response_model=FeatureResponse)
async def create_feature(
    feature_group_id: str,
    data: FeatureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new feature"""
    service = get_feature_store_service(db)

    # Verify feature group exists
    group = service.get_feature_group(feature_group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature group not found"
        )

    feature = service.create_feature(
        feature_group_id=feature_group_id,
        name=data.name,
        data_type=data.data_type,
        display_name=data.display_name,
        description=data.description,
        entity_id=data.entity_id,
        feature_type=data.feature_type,
        dimension=data.dimension,
        validation_config=data.validation_config,
        transformation=data.transformation,
        transformation_config=data.transformation_config,
        tags=data.tags,
    )

    return FeatureResponse(
        id=str(feature.id),
        name=feature.name,
        display_name=feature.display_name,
        description=feature.description,
        feature_group_id=str(feature.feature_group_id),
        data_type=feature.data_type,
        feature_type=feature.feature_type,
        dimension=feature.dimension,
        null_percentage=feature.null_percentage,
        mean_value=feature.mean_value,
        created_at=feature.created_at.isoformat(),
    )


@router.get("/features", response_model=List[FeatureResponse])
async def list_features(
    feature_group_id: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    data_type: Optional[DataType] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List features"""
    service = get_feature_store_service(db)

    features = service.list_features(
        feature_group_id=feature_group_id,
        entity_id=entity_id,
        data_type=data_type,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        FeatureResponse(
            id=str(f.id),
            name=f.name,
            display_name=f.display_name,
            description=f.description,
            feature_group_id=str(f.feature_group_id),
            data_type=f.data_type,
            feature_type=f.feature_type,
            dimension=f.dimension,
            null_percentage=f.null_percentage,
            mean_value=f.mean_value,
            created_at=f.created_at.isoformat(),
        )
        for f in features
    ]


# ============================================================================
# Feature View Endpoints
# ============================================================================


@router.post("/feature-views", response_model=FeatureViewResponse)
async def create_feature_view(
    data: FeatureViewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new feature view"""
    service = get_feature_store_service(db)

    view = service.create_feature_view(
        name=data.name,
        feature_group_id=data.feature_group_id,
        feature_ids=data.feature_ids,
        display_name=data.display_name,
        description=data.description,
        view_type=data.view_type,
        transformation_sql=data.transformation_sql,
        transformation_config=data.transformation_config,
        serving_mode=data.serving_mode,
        ttl_seconds=data.ttl_seconds,
        owner_id=str(current_user.id),
        tags=data.tags,
    )

    return FeatureViewResponse(
        id=str(view.id),
        name=view.name,
        display_name=view.display_name,
        description=view.description,
        feature_group_id=str(view.feature_group_id),
        feature_ids=view.feature_ids or [],
        view_type=view.view_type,
        serving_mode=view.serving_mode,
        ttl_seconds=view.ttl_seconds,
        status=view.status,
        created_at=view.created_at.isoformat(),
    )


@router.get("/feature-views", response_model=List[FeatureViewResponse])
async def list_feature_views(
    feature_group_id: Optional[str] = Query(None),
    serving_mode: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List feature views"""
    service = get_feature_store_service(db)

    views = service.list_feature_views(
        feature_group_id=feature_group_id,
        serving_mode=serving_mode,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        FeatureViewResponse(
            id=str(v.id),
            name=v.name,
            display_name=v.display_name,
            description=v.description,
            feature_group_id=str(v.feature_group_id),
            feature_ids=v.feature_ids or [],
            view_type=v.view_type,
            serving_mode=v.serving_mode,
            ttl_seconds=v.ttl_seconds,
            status=v.status,
            created_at=v.created_at.isoformat(),
        )
        for v in views
    ]


# ============================================================================
# Feature Service Endpoints
# ============================================================================


@router.post("/feature-services", response_model=FeatureServiceResponse)
async def create_feature_service(
    data: FeatureServiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new feature service"""
    service = get_feature_store_service(db)

    fs = service.create_feature_service(
        name=data.name,
        feature_view_ids=data.feature_view_ids,
        display_name=data.display_name,
        description=data.description,
        serving_type=data.serving_type,
        max_qps=data.max_qps,
        target_p95_latency_ms=data.target_p95_latency_ms,
        enable_cache=data.enable_cache,
        cache_ttl_seconds=data.cache_ttl_seconds,
        owner_id=str(current_user.id),
        tags=data.tags,
    )

    return FeatureServiceResponse(
        id=str(fs.id),
        name=fs.name,
        display_name=fs.display_name,
        description=fs.description,
        feature_view_ids=fs.feature_view_ids or [],
        serving_type=fs.serving_type,
        endpoint_path=fs.endpoint_path,
        deployment_status=fs.deployment_status,
        status=fs.status,
        total_requests=fs.total_requests,
        avg_latency_ms=fs.avg_latency_ms,
        created_at=fs.created_at.isoformat(),
        deployed_at=fs.deployed_at.isoformat() if fs.deployed_at else None,
    )


@router.get("/feature-services", response_model=List[FeatureServiceResponse])
async def list_feature_services(
    deployment_status: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List feature services"""
    service = get_feature_store_service(db)

    services = service.list_feature_services(
        deployment_status=deployment_status,
        status=status,
        limit=limit,
        offset=offset,
    )

    return [
        FeatureServiceResponse(
            id=str(s.id),
            name=s.name,
            display_name=s.display_name,
            description=s.description,
            feature_view_ids=s.feature_view_ids or [],
            serving_type=s.serving_type,
            endpoint_path=s.endpoint_path,
            deployment_status=s.deployment_status,
            status=s.status,
            total_requests=s.total_requests,
            avg_latency_ms=s.avg_latency_ms,
            created_at=s.created_at.isoformat(),
            deployed_at=s.deployed_at.isoformat() if s.deployed_at else None,
        )
        for s in services
    ]


@router.post("/feature-services/{service_id}/deploy")
async def deploy_feature_service(
    service_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deploy a feature service"""
    service = get_feature_store_service(db)
    fs = service.deploy_feature_service(service_id)

    if not fs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature service not found"
        )

    return {"success": True, "message": "Feature service deployed"}


# ============================================================================
# Feature Serving Endpoints
# ============================================================================


@router.post("/features/retrieve")
async def retrieve_features(
    request: FeatureRetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve features for inference"""
    from app.services.feature_store import FeatureRequest, ServingConfig

    serving_service = get_feature_serving_service(db)

    # Convert request
    feature_request = FeatureRequest(
        entity_keys=request.entity_keys,
        feature_view_names=request.feature_view_names,
        point_in_time=datetime.fromisoformat(request.point_in_time) if request.point_in_time else None,
    )

    config = ServingConfig(mode=request.mode)

    response = serving_service.serve_features(feature_request, config)

    return {
        "request_id": response.request_id,
        "features": {
            view_name: [
                {
                    "entity_key": row.entity_key,
                    "features": {
                        fname: {
                            "value": fval.value,
                            "timestamp": fval.timestamp.isoformat(),
                            "is_null": fval.is_null,
                        }
                        for fname, fval in row.features.items()
                    },
                    "event_timestamp": row.event_timestamp.isoformat() if row.event_timestamp else None,
                }
                for row in rows
            ]
            for view_name, rows in response.features.items()
        },
        "metadata": response.metadata,
        "latency_ms": response.latency_ms,
        "cached": response.cached,
    }


@router.get("/health")
async def feature_store_health(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get feature store health status"""
    service = get_feature_store_service(db)

    # Get counts
    entity_count = len(service.list_entities(limit=1000))
    group_count = len(service.list_feature_groups(limit=1000))
    feature_count = len(service.list_features(limit=1000))
    view_count = len(service.list_feature_views(limit=1000))
    service_count = len(service.list_feature_services(limit=1000))

    return {
        "status": "healthy",
        "entities": {
            "total": entity_count,
        },
        "feature_groups": {
            "total": group_count,
            "by_store_type": {
                "offline": len(service.list_feature_groups(store_type=FeatureStoreType.OFFLINE, limit=1000)),
                "online": len(service.list_feature_groups(store_type=FeatureStoreType.ONLINE, limit=1000)),
                "hybrid": len(service.list_feature_groups(store_type=FeatureStoreType.HYBRID, limit=1000)),
            },
        },
        "features": {
            "total": feature_count,
        },
        "feature_views": {
            "total": view_count,
        },
        "feature_services": {
            "total": service_count,
            "deployed": len(service.list_feature_services(deployment_status="deployed", limit=1000)),
        },
    }


# ============================================================================
# Online/Offline Computation Endpoints
# ============================================================================


class OnlineFeatureRequest(BaseModel):
    """Request model for online feature retrieval"""
    entity_keys: Dict[str, Any] = Field(..., description="Entity key-value pairs")
    feature_names: List[str] = Field(..., description="Feature names to retrieve")
    feature_view_name: Optional[str] = None
    request_timestamp: Optional[str] = None


class OnlineFeatureResponse(BaseModel):
    """Response model for online feature retrieval"""
    features: Dict[str, Any]
    metadata: Dict[str, Any] = {}
    errors: List[str] = []
    served_from: str = "unknown"
    response_time_ms: float = 0.0


class BatchFeatureRequest(BaseModel):
    """Request model for batch feature retrieval"""
    entity_keys: List[Dict[str, Any]] = Field(..., description="Multiple entity key-value pairs")
    feature_names: List[str] = Field(..., description="Feature names to retrieve")
    feature_view_name: Optional[str] = None
    request_timestamp: Optional[str] = None


class BatchFeatureResponse(BaseModel):
    """Response model for batch feature retrieval"""
    rows: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}
    errors: List[str] = []
    served_from: str = "unknown"
    response_time_ms: float = 0.0


class FeatureWriteRequest(BaseModel):
    """Request model for writing features"""
    entity_keys: Dict[str, Any]
    features: Dict[str, Any]
    feature_group_id: str
    event_timestamp: Optional[str] = None
    online_ttl: Optional[int] = None


class TimeTravelRequest(BaseModel):
    """Request model for time travel queries"""
    entity_keys: Dict[str, Any]
    feature_names: List[str]
    point_in_time: str  # ISO format timestamp


class FeatureTransformationRequest(BaseModel):
    """Request model for feature transformation"""
    transformation_type: str  # sql, python
    expression: Optional[str] = None
    column: Optional[str] = None
    config: Dict[str, Any] = {}
    input_features: List[str] = []
    output_feature: Optional[str] = None


@router.post("/features/online", response_model=OnlineFeatureResponse)
async def get_online_features(
    request: OnlineFeatureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get features from online store (low-latency)"""
    from app.services.feature_store.computation_service import (
        get_feature_computation_service,
        FeatureRequest,
        TimeTravelMode,
    )

    computation_service = get_feature_computation_service(db)

    feature_request = FeatureRequest(
        entity_keys=request.entity_keys,
        feature_names=request.feature_names,
        feature_view_name=request.feature_view_name,
        request_timestamp=datetime.fromisoformat(request.request_timestamp) if request.request_timestamp else datetime.utcnow(),
        time_travel_mode=TimeTravelMode.CURRENT,
    )

    response = computation_service.get_online_features(feature_request)

    return OnlineFeatureResponse(
        features=response.features,
        metadata=response.metadata,
        errors=response.errors,
        served_from=response.served_from,
        response_time_ms=response.response_time_ms,
    )


@router.post("/features/batch", response_model=BatchFeatureResponse)
async def get_batch_features(
    request: BatchFeatureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get features for multiple entities (batch)"""
    from app.services.feature_store.computation_service import (
        get_feature_computation_service,
        BatchFeatureRequest as BatchReq,
        TimeTravelMode,
    )

    computation_service = get_feature_computation_service(db)

    batch_request = BatchReq(
        entity_keys=request.entity_keys,
        feature_names=request.feature_names,
        feature_view_name=request.feature_view_name,
        request_timestamp=datetime.fromisoformat(request.request_timestamp) if request.request_timestamp else datetime.utcnow(),
        time_travel_mode=TimeTravelMode.CURRENT,
    )

    response = computation_service.get_batch_features(batch_request)

    return BatchFeatureResponse(
        rows=response.rows,
        metadata=response.metadata,
        errors=response.errors,
        served_from=response.served_from,
        response_time_ms=response.response_time_ms,
    )


@router.post("/features/write")
async def write_features(
    request: FeatureWriteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Write features to both online and offline stores"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    event_timestamp = None
    if request.event_timestamp:
        event_timestamp = datetime.fromisoformat(request.event_timestamp)

    success = computation_service.write_features(
        entity_key=request.entity_keys,
        features=request.features,
        feature_group_id=request.feature_group_id,
        event_timestamp=event_timestamp,
        online_ttl=request.online_ttl,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write features"
        )

    return {
        "success": True,
        "message": f"Wrote {len(request.features)} features",
    }


@router.post("/features/time-travel", response_model=OnlineFeatureResponse)
async def get_features_point_in_time(
    request: TimeTravelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get feature values as of a specific point in time (time travel)"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    point_in_time = datetime.fromisoformat(request.point_in_time)

    features = computation_service.get_features_point_in_time(
        entity_key=request.entity_keys,
        feature_names=request.feature_names,
        point_in_time=point_in_time,
    )

    return OnlineFeatureResponse(
        features=features,
        served_from="offline_store",
        metadata={
            "point_in_time": point_in_time.isoformat(),
        },
    )


@router.post("/features/compute")
async def compute_transformed_features(
    feature_view_id: str,
    entity_keys: List[Dict[str, Any]],
    transformations: List[FeatureTransformationRequest],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute features with transformations"""
    from app.services.feature_store.computation_service import (
        get_feature_computation_service,
        FeatureTransformation,
    )

    computation_service = get_feature_computation_service(db)

    # Convert transformation requests
    transform_list = []
    for t in transformations:
        transform_list.append(
            FeatureTransformation(
                name=f"{t.transformation_type}_transform",
                transformation_type=t.transformation_type,
                definition={
                    "expression": t.expression,
                    "column": t.column,
                    **t.config,
                },
                input_features=t.input_features,
                output_features=[t.output_feature] if t.output_feature else [],
            )
        )

    df = computation_service.compute_transformed_features(
        feature_view_id=feature_view_id,
        entity_keys=entity_keys,
        transformations=transform_list,
    )

    if df.empty:
        return {
            "rows": [],
            "metadata": {"message": "No computed features returned"},
        }

    return {
        "rows": df.to_dict(orient="records"),
        "metadata": {
            "row_count": len(df),
            "columns": list(df.columns),
        },
    }


# ============================================================================
# Cache Management Endpoints
# ============================================================================


@router.post("/features/cache/invalidate")
async def invalidate_feature_cache(
    entity_keys: Dict[str, Any],
    feature_names: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Invalidate cached features for an entity"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    success = computation_service.invalidate_cache(
        entity_key=entity_keys,
        feature_names=feature_names,
    )

    return {
        "success": success,
        "message": "Cache invalidated" if success else "Failed to invalidate cache",
    }


@router.post("/features/cache/warm")
async def warm_feature_cache(
    entity_keys: List[Dict[str, Any]],
    feature_names: List[str],
    feature_view_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Warm the online store cache with pre-computed features"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    count = computation_service.warm_cache(
        entity_keys=entity_keys,
        feature_names=feature_names,
        feature_view_id=feature_view_id,
    )

    return {
        "success": True,
        "cached_count": count,
        "message": f"Warmed cache for {count} entities",
    }


# ============================================================================
# Snapshot Endpoints
# ============================================================================


@router.post("/snapshots")
async def create_feature_snapshot(
    feature_view_id: str,
    snapshot_time: str,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a feature snapshot at a specific time"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    timestamp = datetime.fromisoformat(snapshot_time)
    snapshot_id = computation_service.create_snapshot(
        feature_view_id=feature_view_id,
        snapshot_time=timestamp,
        description=description,
    )

    return {
        "success": True,
        "snapshot_id": snapshot_id,
        "message": f"Created snapshot {snapshot_id}",
    }


@router.get("/snapshots")
async def list_feature_snapshots(
    feature_view_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List available snapshots for a feature view"""
    from app.services.feature_store.computation_service import get_feature_computation_service

    computation_service = get_feature_computation_service(db)

    start = datetime.fromisoformat(start_time) if start_time else None
    end = datetime.fromisoformat(end_time) if end_time else None

    snapshots = computation_service.list_snapshots(
        feature_view_id=feature_view_id,
        start_time=start,
        end_time=end,
    )

    return {
        "snapshots": snapshots,
        "count": len(snapshots),
    }
