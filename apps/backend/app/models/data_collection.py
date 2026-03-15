"""
Data Collection Models

Models for online data collection and回流 (flowback) to data lake:
- Collection tasks and executions
- Data source connectors
- Quality validation results
- Collection statistics
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Boolean, JSON, Float, Enum as SQLEnum, BigInteger
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CollectionType(str):
    """Collection task types"""
    BATCH = "batch"  # One-time batch collection
    SCHEDULED = "scheduled"  # Scheduled recurring collection
    STREAMING = "streaming"  # Real-time streaming
    EVENT_DRIVEN = "event_driven"  # Triggered by events
    MANUAL = "manual"  # Manual trigger


class SourceType(str):
    """Data source types"""
    DATABASE = "database"  # Database query
    API = "api"  # REST API
    KAFKA = "kafka"  # Kafka topic
    MQTT = "mqtt"  # MQTT broker
    WEBSOCKET = "websocket"  # WebSocket
    FILE = "file"  # File system
    S3 = "s3"  # S3-compatible storage
    FTP = "ftp"  # FTP server
    WEBHOOK = "webhook"  # Webhook endpoint
    CUSTOM = "custom"  # Custom connector


class CollectionStatus(str):
    """Execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class QualityLevel(str):
    """Data quality levels"""
    EXCELLENT = "excellent"  # > 95% valid
    GOOD = "good"  # 80-95% valid
    FAIR = "fair"  # 60-80% valid
    POOR = "poor"  # < 60% valid


class CollectionTask(Base):
    """Data collection task configuration"""
    __tablename__ = "collection_tasks"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    task_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Collection type and source
    collection_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Source configuration
    source_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example for database: {"connection_id": "xxx", "query": "SELECT * FROM ..."}
    # Example for API: {"url": "...", "method": "GET", "headers": {...}}

    # Destination (data lake)
    destination_type: Mapped[str] = mapped_column(String(50), default="s3")  # s3, minio, local
    destination_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {"bucket": "datalake", "prefix": "raw/source1/"}

    # Schedule (for scheduled tasks)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    schedule_interval: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # seconds

    # Data processing
    preprocessing_pipeline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    postprocessing_pipeline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Batch configuration
    batch_size: Mapped[int] = mapped_column(Integer, default=1000)
    batch_timeout: Mapped[int] = mapped_column(Integer, default=300)  # seconds

    # Quality validation
    quality_rules: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    quality_threshold: Mapped[float] = mapped_column(Float, default=0.8)  # minimum quality score
    stop_on_error: Mapped[bool] = mapped_column(Boolean, default=False)

    # Retry configuration
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[int] = mapped_column(Integer, default=60)  # seconds

    # Notifications
    notification_channels: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    notify_on_success: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Tags
    tags: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)

    # Statistics
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    successful_runs: Mapped[int] = mapped_column(Integer, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_records_collected: Mapped[int] = mapped_column(BigInteger, default=0)
    total_bytes_collected: Mapped[int] = mapped_column(BigInteger, default=0)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CollectionTask {self.task_id}:{self.name}>"


class CollectionExecution(Base):
    """Execution instance of a collection task"""
    __tablename__ = "collection_executions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    execution_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Task reference
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Execution info
    status: Mapped[str] = mapped_column(String(50), default=CollectionStatus.PENDING)

    # Trigger
    trigger_type: Mapped[str] = mapped_column(String(50), default="manual")  # manual, schedule, event, api
    trigger_source: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # Execution parameters
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Statistics
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    records_collected: Mapped[int] = mapped_column(BigInteger, default=0)
    records_failed: Mapped[int] = mapped_column(BigInteger, default=0)
    bytes_collected: Mapped[int] = mapped_column(BigInteger, default=0)

    # Batches
    batches_total: Mapped[int] = mapped_column(Integer, default=0)
    batches_completed: Mapped[int] = mapped_column(Integer, default=0)

    # Output
    output_files: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    output_location: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Quality
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Resource usage
    peak_memory_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cpu_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<CollectionExecution {self.execution_id}>"


class DataSourceConnector(Base):
    """Reusable data source connector configuration"""
    __tablename__ = "data_source_connectors"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    connector_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Connector type
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Connection configuration
    connection_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Different for each source type:
    # - database: host, port, database, username, password
    # - api: base_url, auth_type, headers
    # - kafka: bootstrap_servers, topic, group_id
    # - mqtt: broker, port, topic

    # Schema mapping
    schema_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Map source fields to target schema

    # Test configuration
    test_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_test_result: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Credentials encryption
    encrypted_credentials: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Usage statistics
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DataSourceConnector {self.connector_id}:{self.name}>"


class QualityValidationResult(Base):
    """Quality validation result for collected data"""
    __tablename__ = "quality_validation_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )

    # Execution reference
    execution_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Validation summary
    total_records: Mapped[int] = mapped_column(BigInteger, nullable=False)
    valid_records: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invalid_records: Mapped[int] = mapped_column(BigInteger, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_level: Mapped[str] = mapped_column(String(50), nullable=False)

    # Validation details
    validation_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_results: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Example: {
    #   "null_check": {"passed": 950, "failed": 50},
    #   "type_check": {"passed": 1000, "failed": 0},
    #   "range_check": {"passed": 900, "failed": 100}
    # }

    # Issues found
    issues_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Example: {
    #   "missing_values": {"field1": 50, "field2": 20},
    #   "out_of_range": {"field3": 100},
    #   "invalid_types": {"field4": 5}
    # }

    # Sample records (first N invalid records)
    sample_invalid_records: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Recommendations
    recommendations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Example: ["Add default value for field1", "Fix range validation for field3"]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<QualityValidationResult {self.id}>"


class DataStream(Base):
    """Real-time data stream configuration"""
    __tablename__ = "data_streams"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    stream_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Format
    data_format: Mapped[str] = mapped_column(String(50), default="json")  # json, avro, protobuf, csv
    schema_definition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Destination
    destination_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Processing
    realtime_processing: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_pipeline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Buffer
    buffer_size: Mapped[int] = mapped_column(Integer, default=10000)
    buffer_timeout: Mapped[int] = mapped_column(Integer, default=5)  # seconds

    # Status
    status: Mapped[str] = mapped_column(String(50), default="stopped")  # running, stopped, error

    # Statistics
    total_messages: Mapped[int] = mapped_column(BigInteger, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    messages_per_second: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<DataStream {self.stream_id}:{self.name}>"


class WebhookConfig(Base):
    """Webhook configuration for event-driven collection"""
    __tablename__ = "webhook_configs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    webhook_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Webhook path
    webhook_path: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    # Example: /webhooks/data-ingestion/salesforce

    # Authentication
    auth_type: Mapped[str] = mapped_column(String(50), default="none")  # none, api_key, bearer, hmac
    auth_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Expected format
    expected_format: Mapped[str] = mapped_column(String(50), default="json")
    schema_validation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Target task/stream
    target_task_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_stream_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Processing
    preprocessing: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Rate limiting
    rate_limit_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rate_limit_per_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Statistics
    total_calls: Mapped[int] = mapped_column(BigInteger, default=0)
    successful_calls: Mapped[int] = mapped_column(BigInteger, default=0)
    failed_calls: Mapped[int] = mapped_column(BigInteger, default=0)
    last_call_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Ownership
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<WebhookConfig {self.webhook_id}:{self.name}>"
