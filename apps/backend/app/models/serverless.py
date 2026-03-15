"""
Serverless Models

Models for serverless function computation:
- Functions with multiple runtime support
- Triggers (HTTP, Timer, Event, Queue)
- Executions and logs
- Runtimes and deployment
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, Enum as SQLEnum, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FunctionStatus(str):
    """Function deployment status"""
    BUILDING = "building"
    READY = "ready"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    DELETING = "deleting"


class ExecutionStatus(str):
    """Function execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TriggerType(str):
    """Trigger types"""
    HTTP = "http"  # HTTP endpoint
    TIMER = "timer"  # Cron/schedule
    EVENT = "event"  # Event bridge
    QUEUE = "queue"  # Message queue
    KAFKA = "kafka"  # Kafka topic
    MQTT = "mqtt"  # MQTT broker
    WEBHOOK = "webhook"  # Webhook


class RuntimeType(str):
    """Runtime types"""
    PYTHON = "python"
    NODEJS = "nodejs"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CUSTOM = "custom"


class ServerlessFunction(Base):
    """Serverless function definition"""
    __tablename__ = "serverless_functions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    function_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Runtime
    runtime: Mapped[str] = mapped_column(String(50), nullable=False)  # python3.9, nodejs18, etc.
    runtime_type: Mapped[str] = mapped_column(String(50), default=RuntimeType.PYTHON)
    handler: Mapped[str] = mapped_column(String(256), nullable=False)  # module.handler

    # Function code
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For small functions
    code_s3_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # For larger functions
    code_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Dependencies
    requirements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Python requirements
    package_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Node.js dependencies

    # Configuration
    timeout: Mapped[int] = mapped_column(Integer, default=300)  # seconds
    memory_mb: Mapped[int] = mapped_column(Integer, default=256)
    ephemeral_storage_mb: Mapped[int] = mapped_column(Integer, default=512)

    # Environment variables
    environment: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Resource limits
    max_concurrent: Mapped[int] = mapped_column(Integer, default=100)
    reserved_concurrent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Deployment
    image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)  # Container image
    status: Mapped[str] = mapped_column(String(50), default=FunctionStatus.BUILDING)
    deployment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Metrics
    invocation_count: Mapped[int] = mapped_column(BigInteger, default=0)
    error_count: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_duration_ms: Mapped[int] = mapped_column(BigInteger, default=0)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Tags
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_invoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<ServerlessFunction {self.function_id}:{self.name}>"


class FunctionTrigger(Base):
    """Trigger configuration for serverless functions"""
    __tablename__ = "function_triggers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    trigger_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Function reference
    function_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Trigger info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Trigger configuration
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # HTTP: {"path": "/api/func", "method": "POST", "auth": true}
    # TIMER: {"cron": "0 * * * *", "timezone": "UTC"}
    # QUEUE: {"queue_name": "tasks", "batch_size": 10}
    # KAFKA: {"topic": "events", "group_id": "func-consumers"}

    # Filter (for event triggers)
    filter: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Statistics
    trigger_count: Mapped[int] = mapped_column(BigInteger, default=0)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FunctionTrigger {self.trigger_id}:{self.type}>"


class FunctionExecution(Base):
    """Execution instance of a serverless function"""
    __tablename__ = "function_executions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    execution_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Function reference
    function_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Trigger reference
    trigger_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Execution info
    status: Mapped[str] = mapped_column(String(50), default=ExecutionStatus.PENDING)

    # Input
    event: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Resource usage
    memory_used_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cpu_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Output
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    return_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Retry
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_execution_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Request metadata
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invocation_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FunctionExecution {self.execution_id}>"


class FunctionLog(Base):
    """Log entry for function execution"""
    __tablename__ = "function_logs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Execution reference
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Log info
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # DEBUG, INFO, WARNING, ERROR
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<FunctionLog {self.id}>"


class Runtime(Base):
    """Available runtime for serverless functions"""
    __tablename__ = "serverless_runtimes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    runtime_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Runtime info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Runtime configuration
    image: Mapped[str] = mapped_column(String(512), nullable=False)
    entrypoint: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    build_command: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Capabilities
    supported_handlers: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Example: ["python:module.handler", "nodejs:index.handler"]

    # Resource requirements
    min_memory_mb: Mapped[int] = mapped_column(Integer, default=128)
    max_memory_mb: Mapped[int] = mapped_column(Integer, default=10240)
    min_timeout: Mapped[int] = mapped_column(Integer, default=1)
    max_timeout: Mapped[int] = mapped_column(Integer, default=900)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage
    function_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Runtime {self.runtime_id}:{self.name}>"


class FunctionLayer(Base):
    """Reusable layer for dependencies"""
    __tablename__ = "function_layers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    layer_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Layer info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Runtime compatibility
    compatible_runtimes: Mapped[list] = mapped_column(ARRAY(String), nullable=False)
    # Example: ["python3.9", "python3.10", "python3.11"]

    # Layer content
    s3_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    image: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    build_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Dependencies
    requirements: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Version
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Usage
    function_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FunctionLayer {self.layer_id}:{self.name}>"


class FunctionAlias(Base):
    """Alias for function versions (like staging, prod)"""
    __tablename__ = "function_aliases"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Alias info
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # staging, prod, v1, etc.
    function_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<FunctionAlias {self.name}->{self.function_id}>"


class APIEndpoint(Base):
    """API Gateway endpoint for HTTP triggers"""
    __tablename__ = "api_endpoints"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    endpoint_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Function reference
    function_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Endpoint info
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.

    # Configuration
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    auth_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # jwt, api_key, none
    rate_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # requests per minute

    # CORS
    cors_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cors_origins: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Request/response handling
    request_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_template: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Validation
    request_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Statistics
    invocation_count: Mapped[int] = mapped_column(BigInteger, default=0)
    error_count: Mapped[int] = mapped_column(BigInteger, default=0)
    avg_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<APIEndpoint {self.method}:{self.path}>"
