"""
Edge Computing Models

Models for edge computing functionality:
- Edge nodes management
- Model deployment to edge
- Edge jobs and monitoring
- Device and sensor management
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, Enum as SQLEnum, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NodeStatus(str):
    """Edge node status"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class DeploymentStatus(str):
    """Model deployment status"""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UPDATING = "updating"
    ROLLING_BACK = "rolling_back"


class JobStatus(str):
    """Edge job status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class DeviceType(str):
    """Edge device types"""
    GATEWAY = "gateway"  # Edge gateway
    CAMERA = "camera"  # Camera/Video
    SENSOR = "sensor"  # IoT sensor
    CONTROLLER = "controller"  # PLC/Controller
    DRONE = "drone"  # UAV/Drone
    VEHICLE = "vehicle"  # Autonomous vehicle
    ROBOT = "robot"  # Robot
    CUSTOM = "custom"


class EdgeNode(Base):
    """Edge computing node"""
    __tablename__ = "edge_nodes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    node_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Location
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    geo_fence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Hardware specs
    hardware_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    storage_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # GPU/Accelerator
    gpu_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gpu_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    npu_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # For NPU

    # Network
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mac_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    network_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # wifi, ethernet, 4g, 5g

    # Software
    os_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    runtime_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=NodeStatus.OFFLINE)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Capabilities
    capabilities: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Example: ["gpu_inference", "video_decode", "mqtt", "modbus"]

    # Configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Group/Label
    group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    labels: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Statistics
    deployment_count: Mapped[int] = mapped_column(Integer, default=0)
    job_count: Mapped[int] = mapped_column(Integer, default=0)
    total_inference_count: Mapped[int] = mapped_column(BigInteger, default=0)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeNode {self.node_id}:{self.name}>"


class EdgeModel(Base):
    """Model deployed to edge"""
    __tablename__ = "edge_models"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    model_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Model info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Model type
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # classification, detection, segmentation, etc.
    framework: Mapped[str] = mapped_column(String(50), nullable=False)  # tensorflow, pytorch, onnx, trt, etc.

    # Model files
    model_path: Mapped[str] = mapped_column(String(512), nullable=False)
    model_size_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    config_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Input/Output
    input_shape: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [batch, height, width, channels]
    input_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # image, video, audio, text
    output_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Performance
    inference_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    throughput_fps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Hardware requirements
    min_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_gpu: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source
    source_model_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Reference to AIHub model

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Statistics
    deployment_count: Mapped[int] = mapped_column(Integer, default=0)
    total_inference_count: Mapped[int] = mapped_column(BigInteger, default=0)

    # Tags
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeModel {self.model_id}:{self.name}>"


class EdgeDeployment(Base):
    """Model deployment to edge nodes"""
    __tablename__ = "edge_deployments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    deployment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # References
    model_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Deployment info
    name: Mapped[str] = mapped_column(String(256), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=DeploymentStatus.PENDING)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Example: {"batch_size": 1, "precision": "fp16", "num_workers": 2}

    # Resource allocation
    allocated_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    allocated_gpu_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Update strategy
    update_strategy: Mapped[str] = mapped_column(String(50), default="manual")  # manual, rolling, blue_green
    rollback_on_failure: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timing
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Statistics
    inference_count: Mapped[int] = mapped_column(BigInteger, default=0)
    total_latency_ms: Mapped[int] = mapped_column(BigInteger, default=0)
    error_count: Mapped[int] = mapped_column(BigInteger, default=0)

    # Health
    health_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_health_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeDeployment {self.deployment_id}>"


class EdgeJob(Base):
    """Job running on edge nodes"""
    __tablename__ = "edge_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    job_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Job info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)  # inference, training, data_collection

    # Target
    node_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    deployment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default=JobStatus.PENDING)

    # Configuration
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {"input_source": "rtsp://...", "output_sink": "...", "parameters": {...}}

    # Schedule
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Execution
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Progress
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    current_step: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Results
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeJob {self.job_id}:{self.name}>"


class EdgeDevice(Base):
    """Device connected to edge node"""
    __tablename__ = "edge_devices"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    device_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Node reference
    node_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Device info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    device_type: Mapped[str] = mapped_column(String(50), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Connection
    connection_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # usb, serial, network, bluetooth
    connection_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Configuration
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="offline")
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Data collection
    data_stream_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    data_stream_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Location
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    position: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {x, y, z}

    # Calibration
    calibration_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    last_calibration: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Maintenance
    install_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_maintenance: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_maintenance: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EdgeDevice {self.device_id}:{self.name}>"


class EdgeMetrics(Base):
    """Metrics collected from edge nodes"""
    __tablename__ = "edge_metrics"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Node reference
    node_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Deployment reference (optional)
    deployment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # System metrics
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    memory_used_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # GPU metrics
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_temperature: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_power_draw_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Network metrics
    network_rx_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    network_tx_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Inference metrics
    inference_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inference_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inference_error_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Custom metrics
    custom_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<EdgeMetrics {self.id}>"


class EdgeInferenceResult(Base):
    """Inference result from edge"""
    __tablename__ = "edge_inference_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # References
    deployment_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Input
    input_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output
    output: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {"predictions": [...], "confidence": 0.95}

    # Performance
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    pre_processing_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    inference_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    post_processing_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Resource usage
    memory_used_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_utilization: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<EdgeInferenceResult {self.id}>"
