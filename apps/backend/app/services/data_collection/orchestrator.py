"""
Data Collection Orchestrator

Orchestrates data collection from various sources and回流s to data lake:
- Batch collection
- Scheduled collection
- Streaming collection
- Event-driven collection (webhooks)
- Quality validation
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_collection import (
    CollectionTask,
    CollectionExecution,
    DataSourceConnector,
    QualityValidationResult,
    CollectionType,
    SourceType,
    CollectionStatus,
    QualityLevel,
)
from app.services.storage.backends import StorageBackend, get_storage_backend

logger = logging.getLogger(__name__)


@dataclass
class CollectionResult:
    """Result of a collection execution"""
    execution_id: str
    status: str
    records_collected: int
    records_failed: int
    bytes_collected: int
    duration_seconds: int
    output_files: List[str]
    quality_score: Optional[float] = None
    error_message: Optional[str] = None


class DataConnector(ABC):
    """Abstract base class for data connectors"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to data source"""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""

    @abstractmethod
    async def collect(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Collect a batch of data"""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if connection is working"""

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class DatabaseConnector(DataConnector):
    """Connector for database sources"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._connection = None
        self._iterator = None

    async def connect(self) -> None:
        """Connect to database"""
        try:
            import asyncpg
        except ImportError:
            raise RuntimeError("asyncpg not installed")

        self._connection = await asyncpg.connect(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 5432),
            database=self.config.get("database"),
            user=self.config.get("username"),
            password=self.config.get("password"),
        )

        # Execute query and get result
        query = self.config.get("query")
        if query:
            self._iterator = await self._connection.cursor(query)

    async def disconnect(self) -> None:
        """Close database connection"""
        if self._connection:
            await self._connection.close()

    async def collect(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch a batch of rows"""
        if not self._iterator:
            return []

        rows = await self._iterator.fetch(batch_size)
        return [dict(row) for row in rows]

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            await self.connect()
            result = await self._connection.fetchval("SELECT 1")
            await self.disconnect()
            return result == 1
        except Exception:
            return False


class APIConnector(DataConnector):
    """Connector for REST API sources"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None
        self._has_more = True

    async def connect(self) -> None:
        """Initialize HTTP client"""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx not installed")

        self._client = httpx.AsyncClient(
            timeout=self.config.get("timeout", 30.0),
            headers=self.config.get("headers", {}),
        )

    async def disconnect(self) -> None:
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()

    async def collect(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch data from API"""
        if not self._has_more or not self._client:
            return []

        url = self.config.get("url")
        method = self.config.get("method", "GET").upper()
        params = self.config.get("params", {})

        # Handle pagination
        if self.config.get("pagination"):
            pagination = self.config["pagination"]
            if pagination.get("type") == "offset":
                params[pagination.get("offset_param", "offset")] = self.config.get("_offset", 0)
                params[pagination.get("limit_param", "limit")] = batch_size
            elif pagination.get("type") == "page":
                params[pagination.get("page_param", "page")] = self.config.get("_page", 1)
                params[pagination.get("limit_param", "limit")] = batch_size

        response = await self._client.request(method, url, params=params, json=self.config.get("body"))
        response.raise_for_status()

        data = response.json()

        # Extract data array based on config
        data_path = self.config.get("data_path", "")
        if data_path:
            for key in data_path.split("."):
                data = data.get(key, [])

        if not isinstance(data, list):
            data = [data]

        # Update pagination state
        if len(data) < batch_size:
            self._has_more = False
        elif self.config.get("pagination"):
            pagination_type = self.config["pagination"].get("type")
            if pagination_type == "offset":
                self.config["_offset"] = self.config.get("_offset", 0) + batch_size
            elif pagination_type == "page":
                self.config["_page"] = self.config.get("_page", 1) + 1

        return data

    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            await self.connect()
            url = self.config.get("url")
            test_url = self.config.get("test_url", url)
            response = await self._client.get(test_url)
            await self.disconnect()
            return response.status_code < 400
        except Exception:
            return False


class KafkaConnector(DataConnector):
    """Connector for Kafka streaming"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._consumer = None

    async def connect(self) -> None:
        """Connect to Kafka"""
        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError:
            raise RuntimeError("aiokafka not installed")

        self._consumer = AIOKafkaConsumer(
            self.config.get("topic"),
            bootstrap_servers=self.config.get("bootstrap_servers", "localhost:9092"),
            group_id=self.config.get("group_id", "data-collector"),
            auto_offset_reset=self.config.get("auto_offset_reset", "earliest"),
        )
        await self._consumer.start()

    async def disconnect(self) -> None:
        """Stop consumer"""
        if self._consumer:
            await self._consumer.stop()

    async def collect(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Consume messages from Kafka"""
        if not self._consumer:
            return []

        records = []
        async for msg in self._consumer:
            try:
                value = json.loads(msg.value.decode())
                records.append(value)
                if len(records) >= batch_size:
                    break
            except json.JSONDecodeError:
                records.append({"raw": msg.value.decode()})

        return records

    async def test_connection(self) -> bool:
        """Test Kafka connection"""
        try:
            await self.connect()
            # Check if consumer is started
            result = self._consumer._client is not None
            await self.disconnect()
            return result
        except Exception:
            return False


class FileConnector(DataConnector):
    """Connector for file sources (CSV, JSON, Parquet)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._iterator = None

    async def connect(self) -> None:
        """Initialize file reader"""
        pass  # Files don't need connection

    async def disconnect(self) -> None:
        """Close file reader"""
        self._iterator = None

    async def collect(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Read records from file"""
        file_path = self.config.get("path")
        file_format = self.config.get("format", "csv")

        if not self._iterator:
            if file_format == "csv":
                import aiofiles

                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    import csv
                    from io import StringIO

                    reader = csv.DictReader(StringIO(content))
                    self._iterator = iter(list(reader))

            elif file_format == "json":
                import aiofiles

                async with aiofiles.open(file_path, "r") as f:
                    data = json.loads(await f.read())
                    if isinstance(data, list):
                        self._iterator = iter(data)
                    else:
                        self._iterator = iter([data])

            elif file_format == "jsonl":
                import aiofiles

                async def read_jsonl():
                    async with aiofiles.open(file_path, "r") as f:
                        async for line in f:
                            if line.strip():
                                yield json.loads(line)

                self._iterator = read_jsonl()

        if not self._iterator:
            return []

        records = []
        for _ in range(batch_size):
            try:
                if hasattr(self._iterator, "__anext__"):
                    record = await self._iterator.__anext__()
                else:
                    record = next(self._iterator)
                records.append(record)
            except (StopAsyncIteration, StopIteration):
                break

        return records

    async def test_connection(self) -> bool:
        """Test if file exists and is readable"""
        from pathlib import Path

        file_path = self.config.get("path")
        return Path(file_path).exists()


class QualityValidator:
    """Data quality validation"""

    def __init__(self, rules: Dict[str, Any]):
        self.rules = rules or {}

    def validate(
        self,
        records: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
    ) -> tuple[int, int, Dict[str, Any], List[str]]:
        """
        Validate records.

        Returns:
            (valid_count, invalid_count, validation_details, invalid_samples)
        """
        valid_count = 0
        invalid_count = 0
        details = {}
        invalid_samples = []

        for record in records:
            is_valid, issues = self._validate_record(record, schema)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                if len(invalid_samples) < 10:
                    invalid_samples.append({
                        "record": record,
                        "issues": issues,
                    })

        # Aggregate details
        if schema:
            for field, field_schema in schema.get("properties", {}).items():
                field_type = field_schema.get("type")
                null_check = self.rules.get(f"{field}_nullable", True)
                # Add field-specific validation results

        return valid_count, invalid_count, details, invalid_samples

    def _validate_record(
        self,
        record: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, List[str]]:
        """Validate a single record"""
        issues = []

        # Schema-based validation
        if schema:
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            # Check required fields
            for field in required:
                if field not in record or record[field] is None:
                    issues.append(f"Required field '{field}' is missing")

            # Check field types
            for field, value in record.items():
                if value is None:
                    continue

                field_schema = properties.get(field, {})
                if field_schema:
                    expected_type = field_schema.get("type")
                    if expected_type == "string" and not isinstance(value, str):
                        issues.append(f"Field '{field}' should be string")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        issues.append(f"Field '{field}' should be number")
                    elif expected_type == "integer" and not isinstance(value, int):
                        issues.append(f"Field '{field}' should be integer")

        # Rule-based validation
        for field, rule in self.rules.items():
            if "_" in field and field.endswith("_nullable"):
                continue  # Skip nullable rule

            field_name = field
            rule_parts = rule.split(":")

            if len(rule_parts) == 2:
                condition, value = rule_parts
                if condition == "range":
                    min_val, max_val = map(float, value.split(","))
                    if field_name in record:
                        val = record[field_name]
                        if isinstance(val, (int, float)):
                            if not (min_val <= val <= max_val):
                                issues.append(f"Field '{field_name}' out of range [{min_val}, {max_val}]")

        return len(issues) == 0, issues


class DataCollectionOrchestrator:
    """
    Orchestrates data collection from various sources to data lake
    """

    def __init__(self):
        self._connectors: Dict[str, DataConnector] = {}
        self._storage_backends: Dict[str, StorageBackend] = {}

    def _get_connector(self, source_type: str, config: Dict[str, Any]) -> DataConnector:
        """Get connector for source type"""
        connector_map = {
            SourceType.DATABASE: DatabaseConnector,
            SourceType.API: APIConnector,
            SourceType.KAFKA: KafkaConnector,
            SourceType.FILE: FileConnector,
        }

        connector_class = connector_map.get(source_type.lower())
        if not connector_class:
            raise ValueError(f"Unsupported source type: {source_type}")

        return connector_class(config)

    def _get_storage_backend(
        self,
        destination_type: str,
        config: Dict[str, Any],
    ) -> StorageBackend:
        """Get storage backend for destination"""
        key = f"{destination_type}:{config.get('bucket', config.get('path'))}"

        if key not in self._storage_backends:
            self._storage_backends[key] = get_storage_backend(
                backend=destination_type,
                **config,
            )

        return self._storage_backends[key]

    async def collect_batch(
        self,
        db: AsyncSession,
        task: CollectionTask,
        trigger_type: str = "manual",
        trigger_source: Optional[str] = None,
    ) -> CollectionResult:
        """
        Execute a batch collection task.

        Args:
            db: Database session
            task: Collection task to execute
            trigger_type: How the task was triggered
            trigger_source: Source that triggered the task

        Returns:
            Collection result
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Create execution record
        execution = CollectionExecution(
            execution_id=execution_id,
            task_id=task.task_id,
            status=CollectionStatus.RUNNING,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            started_at=start_time,
        )

        db.add(execution)
        await db.commit()

        try:
            # Get connector
            connector = self._get_connector(task.source_type, task.source_config)

            # Get storage backend
            storage = self._get_storage_backend(
                task.destination_type,
                task.destination_config,
            )

            # Collect data
            total_records = 0
            total_bytes = 0
            batch_count = 0
            output_files = []
            all_records = []

            async with connector:
                while True:
                    records = await connector.collect(batch_size=task.batch_size)
                    if not records:
                        break

                    all_records.extend(records)
                    total_records += len(records)

                    # Write batch to storage
                    batch_id = f"{task.task_id}_{execution_id}_{batch_count}"
                    file_path = f"{task.destination_config.get('prefix', '')}{batch_id}.jsonl"

                    data = "\n".join(json.dumps(r) for r in records).encode()
                    await storage.upload(file_path, data, "application/jsonl")

                    total_bytes += len(data)
                    output_files.append(file_path)
                    batch_count += 1

                    # Check if we should stop (for non-streaming tasks)
                    if task.collection_type != CollectionType.STREAMING and len(records) < task.batch_size:
                        break

            # Validate quality
            quality_score = None
            quality_level = None

            if task.quality_rules:
                validator = QualityValidator(task.quality_rules)
                valid_count, invalid_count, details, samples = validator.validate(all_records)

                quality_score = valid_count / total_records if total_records > 0 else 0

                if quality_score >= 0.95:
                    quality_level = QualityLevel.EXCELLENT
                elif quality_score >= 0.8:
                    quality_level = QualityLevel.GOOD
                elif quality_score >= 0.6:
                    quality_level = QualityLevel.FAIR
                else:
                    quality_level = QualityLevel.POOR

                # Check if quality threshold is met
                if quality_score < task.quality_threshold:
                    if task.stop_on_error:
                        raise ValueError(f"Quality score {quality_score:.2f} below threshold {task.quality_threshold}")

                # Save quality validation result
                quality_result = QualityValidationResult(
                    execution_id=execution_id,
                    total_records=total_records,
                    valid_records=valid_count,
                    invalid_records=invalid_count,
                    quality_score=quality_score,
                    quality_level=quality_level,
                    validation_rules=task.quality_rules,
                    validation_results=details,
                    sample_invalid_records=samples,
                )
                db.add(quality_result)

            # Update execution
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())

            execution.status = CollectionStatus.COMPLETED
            execution.completed_at = end_time
            execution.duration_seconds = duration
            execution.records_collected = total_records
            execution.bytes_collected = total_bytes
            execution.batches_total = batch_count
            execution.batches_completed = batch_count
            execution.output_files = output_files
            execution.output_location = task.destination_config.get("prefix", "")
            execution.quality_score = quality_score
            execution.quality_level = quality_level

            # Update task statistics
            task.total_runs += 1
            task.successful_runs += 1
            task.total_records_collected += total_records
            task.total_bytes_collected += total_bytes
            task.last_run_at = start_time
            task.last_success_at = end_time

            await db.commit()

            logger.info(
                f"Collection {execution_id} completed: "
                f"{total_records} records, {total_bytes} bytes, {duration}s"
            )

            return CollectionResult(
                execution_id=execution_id,
                status=CollectionStatus.COMPLETED,
                records_collected=total_records,
                records_failed=0,
                bytes_collected=total_bytes,
                duration_seconds=duration,
                output_files=output_files,
                quality_score=quality_score,
            )

        except Exception as e:
            logger.error(f"Collection {execution_id} failed: {e}")

            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())

            execution.status = CollectionStatus.FAILED
            execution.completed_at = end_time
            execution.duration_seconds = duration
            execution.error_message = str(e)
            execution.error_stack = None  # Could capture traceback

            # Update task statistics
            task.total_runs += 1
            task.failed_runs += 1
            task.last_run_at = start_time

            await db.commit()

            return CollectionResult(
                execution_id=execution_id,
                status=CollectionStatus.FAILED,
                records_collected=execution.records_collected,
                records_failed=0,
                bytes_collected=execution.bytes_collected,
                duration_seconds=duration,
                output_files=execution.output_files or [],
                error_message=str(e),
            )

    async def test_connector(
        self,
        source_type: str,
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Test a data connector"""
        try:
            connector = self._get_connector(source_type, config)
            success = await connector.test_connection()

            return {
                "success": success,
                "message": "Connection successful" if success else "Connection failed",
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e),
            }


# Global orchestrator instance
_orchestrator: Optional[DataCollectionOrchestrator] = None


def get_collection_orchestrator() -> DataCollectionOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DataCollectionOrchestrator()
    return _orchestrator
