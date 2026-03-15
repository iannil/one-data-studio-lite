"""
Pipeline module for SDK

Provides Pipeline and PipelineTask classes for managing workflows.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Coroutine, Optional

from .client import CubeStudioClient

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class PipelineStatus(str, Enum):
    """Pipeline execution status"""
    DRAFT = "draft"
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class TaskResult:
    """Task execution result"""
    task_id: str
    status: TaskStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineTask:
    """Pipeline task definition"""
    task_id: str
    name: str
    type: str
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 3
    timeout_seconds: Optional[int] = None
    
    # Runtime state
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[TaskResult] = None


@dataclass
class PipelineRun:
    """Pipeline execution run"""
    run_id: str
    pipeline_id: str
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    tasks: list[PipelineTask] = field(default_factory=list)
    error: Optional[str] = None


class Pipeline:
    """
    Pipeline class for managing workflows
    
    Example:
        ```python
        async with CubeStudioClient() as client:
            pipeline = await client.create_pipeline(
                name="my-pipeline",
                tasks=[
                    {"name": "extract", "type": "extract"},
                    {"name": "transform", "type": "transform", "dependencies": ["extract"]},
                    {"name": "load", "type": "load", "dependencies": ["transform"]},
                ]
            )
            
            # Run the pipeline
            run = await pipeline.run()
            
            # Wait for completion
            result = await run.wait_for_completion()
        ```
    """

    def __init__(
        self,
        client: CubeStudioClient,
        id: str,
        name: str,
        description: Optional[str] = None,
        tasks: Optional[list[Dict[str, Any]]] = None,
        status: PipelineStatus = PipelineStatus.DRAFT,
        created_at: Optional[datetime] = None,
        **kwargs
    ):
        self.client = client
        self.id = id
        self.name = name
        self.description = description
        self._task_definitions = tasks or []
        self.status = status
        self.created_at = created_at or datetime.now()

    @classmethod
    def from_dict(cls, client: CubeStudioClient, data: Dict[str, Any]) -> "Pipeline":
        """Create Pipeline from API response"""
        return cls(client=client, **data)

    async def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "Pipeline":
        """Update pipeline"""
        response = await self.client._client.put(
            f"/api/v1/pipelines/{self.id}",
            json={
                k: v for k, v in
                {"name": name, "description": description}.items()
                if v is not None
            },
        )
        response.raise_for_status()
        data = response.json()
        
        if name:
            self.name = name
        if description:
            self.description = description
            
        return self

    async def delete(self) -> bool:
        """Delete the pipeline"""
        response = await self.client._client.delete(f"/api/v1/pipelines/{self.id}")
        response.raise_for_status()
        return True

    def add_task(
        self,
        name: str,
        task_type: str,
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[list[str]] = None,
    ) -> "Pipeline":
        """
        Add a task to the pipeline

        Args:
            name: Task name
            task_type: Type of task
            config: Task configuration
            dependencies: List of task names this task depends on

        Returns:
            Self for chaining
        """
        self._task_definitions.append({
            "name": name,
            "type": task_type,
            "config": config or {},
            "dependencies": dependencies or [],
        })
        return self

    def extract(
        self,
        name: str = "extract",
        source_id: Optional[str] = None,
        table_name: Optional[str] = None,
        **config
    ) -> "Pipeline":
        """Add an extract task"""
        task_config = {"source_id": source_id, "table_name": table_name, **config}
        return self.add_task(name, "extract", task_config)

    def transform(
        self,
        name: str = "transform",
        steps: Optional[list[Dict[str, Any]]] = None,
        **config
    ) -> "Pipeline":
        """Add a transform task"""
        task_config = {"steps": steps or [], **config}
        return self.add_task(name, "transform", task_config)

    def load(
        self,
        name: str = "load",
        destination_id: Optional[str] = None,
        table_name: Optional[str] = None,
        **config
    ) -> "Pipeline":
        """Add a load task"""
        task_config = {"destination_id": destination_id, "table_name": table_name, **config}
        return self.add_task(name, "load", task_config)

    def train_model(
        self,
        name: str = "train",
        model_type: str = "sklearn",
        dataset_id: Optional[str] = None,
        target_column: Optional[str] = None,
        **config
    ) -> "Pipeline":
        """Add a model training task"""
        task_config = {
            "model_type": model_type,
            "dataset_id": dataset_id,
            "target_column": target_column,
            **config
        }
        return self.add_task(name, "train_model", task_config)

    def python_script(
        self,
        name: str,
        script_path: str,
        arguments: Optional[list[str]] = None,
        **config
    ) -> "Pipeline":
        """Add a Python script task"""
        task_config = {"script_path": script_path, "arguments": arguments or [], **config}
        return self.add_task(name, "python", task_config)

    def sql_query(
        self,
        name: str,
        query: str,
        connection_id: Optional[str] = None,
        **config
    ) -> "Pipeline":
        """Add a SQL query task"""
        task_config = {"query": query, "connection_id": connection_id, **config}
        return self.add_task(name, "sql", task_config)

    async def save(self) -> "Pipeline":
        """Save the pipeline"""
        response = await self.client._client.post(
            "/api/v1/pipelines",
            json={
                "name": self.name,
                "description": self.description,
                "tasks": self._task_definitions,
            },
        )
        response.raise_for_status()
        data = response.json()
        
        # Update self with new data
        self.id = data.get("id", self.id)
        self.status = data.get("status", self.status)
        
        return self

    async def run(self, **kwargs) -> PipelineRun:
        """
        Execute the pipeline

        Args:
            **kwargs: Additional execution parameters

        Returns:
            PipelineRun for tracking execution
        """
        response = await self.client._client.post(
            f"/api/v1/pipelines/{self.id}/run",
            json=kwargs,
        )
        response.raise_for_status()
        data = response.json()
        
        run = PipelineRun(
            run_id=data["run_id"],
            pipeline_id=self.id,
            status=PipelineStatus(data.get("status", "running")),
            started_at=datetime.now(),
        )
        
        return run

    async def get_runs(self, limit: int = 10) -> list[PipelineRun]:
        """Get pipeline execution runs"""
        response = await self.client._client.get(
            f"/api/v1/pipelines/{self.id}/runs",
            params={"limit": limit},
        )
        response.raise_for_status()
        
        runs_data = response.json()
        return [
            PipelineRun(
                run_id=r["run_id"],
                pipeline_id=self.id,
                status=PipelineStatus(r["status"]),
                started_at=datetime.fromisoformat(r["started_at"]),
                completed_at=datetime.fromisoformat(r["completed_at"]) if r.get("completed_at") else None,
            )
            for r in runs_data
        ]

    def __repr__(self) -> str:
        return f"Pipeline(id={self.id}, name={self.name}, status={self.status})"


# Extend PipelineRun with wait methods

async def wait_for_completion(
    self: PipelineRun,
    poll_interval: float = 5.0,
    timeout: Optional[float] = None,
) -> TaskResult:
    """
    Wait for pipeline run to complete

    Args:
        poll_interval: Seconds between status checks
        timeout: Maximum time to wait (None = infinite)

    Returns:
        Final task result
    """
    import asyncio
    
    start_time = asyncio.get_event_loop().time()
    
    while True:
        # Check timeout
        if timeout and (asyncio.get_event_loop().time() - start_time) > timeout:
            raise TimeoutError(f"Pipeline run {self.run_id} timed out")
        
        # Check status
        if self.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            break
            
        await asyncio.sleep(poll_interval)
    
    return TaskResult(
        task_id=self.run_id,
        status=TaskStatus.SUCCESS if self.status == PipelineStatus.SUCCESS else TaskStatus.FAILED,
        end_time=self.completed_at,
        error=self.error,
    )


async def stream_logs(
    self: PipelineRun,
    poll_interval: float = 2.0,
) -> AsyncGenerator[str, None]:
    """
    Stream logs from pipeline run

    Args:
        poll_interval: Seconds between log fetches

    Yields:
        Log lines
    """
    import asyncio
    
    last_log_time = None
    
    while True:
        # Fetch logs since last check
        # In production, would use SSE or WebSocket
        await asyncio.sleep(poll_interval)
        
        if self.status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            break


PipelineRun.wait_for_completion = wait_for_completion
PipelineRun.stream_logs = stream_logs
