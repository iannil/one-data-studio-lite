"""
TensorBoard Schemas

Pydantic schemas for TensorBoard instance management.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, validator


# =============================================================================
# Base Schemas
# =============================================================================

class TensorBoardBase(BaseModel):
    """Base TensorBoard schema"""
    name: str = Field(..., min_length=1, max_length=256, description="Instance name")
    description: Optional[str] = Field(None, description="Instance description")
    log_dir: str = Field(..., min_length=1, max_length=500, description="Log directory path")
    log_source: str = Field(default="minio", description="Log storage source")

    # Associated resources
    experiment_id: Optional[str] = Field(None, description="Associated experiment ID")
    run_id: Optional[str] = Field(None, description="Associated run ID")
    training_job_id: Optional[str] = Field(None, description="Associated training job ID")

    # Container configuration
    image: str = Field(default="tensorflow/tensorboard:latest", description="TensorBoard Docker image")
    port: int = Field(default=6006, ge=1024, le=65535, description="Service port")

    # Resource configuration
    cpu_limit: Optional[str] = Field(None, description="CPU limit (e.g., '500m')")
    cpu_request: Optional[str] = Field(None, description="CPU request")
    memory_limit: Optional[str] = Field(None, description="Memory limit (e.g., '2Gi')")
    memory_request: Optional[str] = Field(None, description="Memory request")

    # Service configuration
    service_type: str = Field(default="ClusterIP", description="Kubernetes service type")
    namespace: str = Field(default="default", description="Kubernetes namespace")

    # Auto-stop configuration
    auto_stop: bool = Field(default=True, description="Auto-stop when idle")
    idle_timeout_seconds: Optional[int] = Field(default=3600, ge=60, description="Idle timeout in seconds")

    # Labels and annotations
    labels: Optional[Dict[str, str]] = Field(default=None, description="Kubernetes labels")
    annotations: Optional[Dict[str, str]] = Field(default=None, description="Kubernetes annotations")


class TensorBoardCreate(TensorBoardBase):
    """Schema for creating a TensorBoard instance"""
    tenant_id: Optional[str] = Field(None, description="Tenant ID (if multi-tenant)")
    project_id: Optional[str] = Field(None, description="Project ID")


class TensorBoardUpdate(BaseModel):
    """Schema for updating a TensorBoard instance"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    auto_stop: Optional[bool] = None
    idle_timeout_seconds: Optional[int] = Field(None, ge=60)
    labels: Optional[Dict[str, str]] = None
    annotations: Optional[Dict[str, str]] = None


# =============================================================================
# Response Schemas
# =============================================================================

class TensorBoardResponse(TensorBoardBase):
    """Schema for TensorBoard instance response"""
    id: str
    instance_id: str
    status: str
    status_message: Optional[str] = None

    # Kubernetes resources
    pod_name: Optional[str] = None
    service_name: Optional[str] = None
    ingress_name: Optional[str] = None

    # Access URLs
    internal_url: Optional[str] = None
    external_url: Optional[str] = None

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    last_access_at: Optional[datetime] = None

    # Ownership
    owner_id: str
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TensorBoardListResponse(BaseModel):
    """Schema for TensorBoard list response"""
    total: int
    items: List[TensorBoardResponse]


class TensorBoardAccessLogResponse(BaseModel):
    """Schema for TensorBoard access log response"""
    id: str
    instance_id: str
    user_id: Optional[str] = None
    access_type: str
    ip_address: Optional[str] = None
    session_duration_seconds: Optional[int] = None
    accessed_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Action Schemas
# =============================================================================

class TensorBoardActionRequest(BaseModel):
    """Schema for TensorBoard action requests"""
    action: str = Field(..., description="Action to perform: start, stop, restart")


class TensorBoardActionResponse(BaseModel):
    """Schema for TensorBoard action response"""
    instance_id: str
    action: str
    status: str
    message: str


# =============================================================================
# Config Schemas
# =============================================================================

class TensorBoardConfigBase(BaseModel):
    """Base TensorBoard config schema"""
    key: str = Field(..., min_length=1, max_length=100)
    value: Dict[str, Any] = Field(..., description="Configuration value")
    description: Optional[str] = None


class TensorBoardConfigCreate(TensorBoardConfigBase):
    """Schema for creating TensorBoard config"""
    pass


class TensorBoardConfigUpdate(BaseModel):
    """Schema for updating TensorBoard config"""
    value: Dict[str, Any]
    description: Optional[str] = None


class TensorBoardConfigResponse(TensorBoardConfigBase):
    """Schema for TensorBoard config response"""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Statistics Schemas
# =============================================================================

class TensorBoardStatsResponse(BaseModel):
    """Schema for TensorBoard statistics response"""
    total_instances: int
    running_instances: int
    stopped_instances: int
    failed_instances: int
    total_usage_hours: float
    avg_session_duration_minutes: float


# =============================================================================
# URL Proxy Schemas
# =============================================================================

class TensorBoardProxyRequest(BaseModel):
    """Schema for TensorBoard proxy request"""
    instance_id: str


class TensorBoardUrlResponse(BaseModel):
    """Schema for TensorBoard URL response"""
    instance_id: str
    url: str
    expires_at: Optional[datetime] = None
    access_token: Optional[str] = None
