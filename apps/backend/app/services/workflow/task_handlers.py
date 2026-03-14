"""
Workflow Task Handlers

Implementations of task handlers for various task types.
"""

import logging
import subprocess
import tempfile
from typing import Dict, Any, List
from datetime import datetime

from .task_types import (
    BaseTaskHandler,
    TaskType,
    TaskConfig,
    register_task_handler,
)

from app.services.etl_engine import ETLEngine
from app.connectors import get_connector
from app.core.database import get_async_session

logger = logging.getLogger(__name__)


@register_task_handler(TaskType.SQL)
class SQLTaskHandler(BaseTaskHandler):
    """SQL task handler - executes SQL queries"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQL query"""
        sql = self.config.parameters.get("sql")
        data_source_id = self.config.parameters.get("data_source_id")

        if not sql:
            raise ValueError("SQL query is required")

        # Get database connection
        connector = get_connector(
            "postgresql",  # Default to PostgreSQL, can be parameterized
            {
                "host": self.config.parameters.get("host", "localhost"),
                "port": self.config.parameters.get("port", 5432),
                "database": self.config.parameters.get("database"),
                "user": self.config.parameters.get("user"),
                "password": self.config.parameters.get("password"),
            },
        )

        # Execute query
        results = await connector.execute_query(sql)

        return {
            "rows_affected": len(results) if isinstance(results, list) else 0,
            "results": results[:100],  # Return first 100 rows
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate SQL task configuration"""
        errors = []
        if not self.config.parameters.get("sql"):
            errors.append("SQL query is required")
        if not self.config.parameters.get("data_source_id") and not self.config.parameters.get(
            "database"
        ):
            errors.append("Database connection info is required")
        return errors

    def get_operator_params(self) -> Dict[str, Any]:
        """Get Airflow SQL operator params"""
        return {
            **super().get_operator_params(),
            "sql": self.config.parameters.get("sql"),
            "conn_id": self.config.parameters.get("conn_id", "airflow_db"),
        }


@register_task_handler(TaskType.PYTHON)
class PythonTaskHandler(BaseTaskHandler):
    """Python task handler - executes Python code"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code"""
        code = self.config.parameters.get("code")

        if not code:
            raise ValueError("Python code is required")

        # Create a safe execution environment
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                # Add math and datetime
                **__import__("math").__dict__,
                **__import__("datetime").__dict__,
                **__import__("json").__dict__,
                **__import__("pandas").__dict__,
            }
        }

        # Add context variables
        safe_globals.update(context)

        # Execute code
        try:
            exec(code, safe_globals)
            return {
                "status": "success",
                "executed_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Python execution error: {e}")
            raise

    def validate(self) -> List[str]:
        """Validate Python task configuration"""
        errors = []
        if not self.config.parameters.get("code"):
            errors.append("Python code is required")
        return errors


@register_task_handler(TaskType.SHELL)
class ShellTaskHandler(BaseTaskHandler):
    """Shell task handler - executes shell commands"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shell command"""
        command = self.config.parameters.get("command")

        if not command:
            raise ValueError("Shell command is required")

        # Execute command
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout, stderr = process.communicate()

        return {
            "return_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate Shell task configuration"""
        errors = []
        if not self.config.parameters.get("command"):
            errors.append("Shell command is required")
        return errors


@register_task_handler(TaskType.ETL)
class ETLTaskHandler(BaseTaskHandler):
    """ETL task handler - executes ETL pipeline

    Integration with existing ETL engine - allows ETL pipelines
    to be used as tasks in workflow DAGs.
    """

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ETL pipeline"""
        import uuid

        pipeline_id = self.config.parameters.get("pipeline_id")

        if not pipeline_id:
            raise ValueError("ETL pipeline_id is required")

        # Get ETL engine and run pipeline
        async with get_async_session() as db:
            from app.models import ETLPipeline
            from sqlalchemy import select

            # Load the pipeline
            try:
                pipeline_uuid = uuid.UUID(pipeline_id)
            except ValueError:
                raise ValueError(f"Invalid pipeline_id format: {pipeline_id}")

            result = await db.execute(
                select(ETLPipeline).where(ETLPipeline.id == pipeline_uuid)
            )
            pipeline = result.scalar_one_or_none()

            if not pipeline:
                raise ValueError(f"ETL pipeline not found: {pipeline_id}")

            # Execute using ETL engine
            etl_engine = ETLEngine(db)
            execution_result = await etl_engine.execute_pipeline(
                pipeline=pipeline,
                preview_mode=self.config.parameters.get("preview_mode", False),
                preview_rows=self.config.parameters.get("preview_rows", 100),
            )

        return {
            "pipeline_id": pipeline_id,
            "status": execution_result.get("status"),
            "rows_input": execution_result.get("rows_input", 0),
            "rows_output": execution_result.get("rows_output", 0),
            "duration_ms": execution_result.get("duration_ms", 0),
            "trace_id": execution_result.get("trace_id"),
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate ETL task configuration"""
        errors = []
        if not self.config.parameters.get("pipeline_id"):
            errors.append("ETL pipeline_id is required")
        return errors

    def get_operator_params(self) -> Dict[str, Any]:
        """Get Airflow operator params for ETL task"""
        return {
            **super().get_operator_params(),
            "pipeline_id": self.config.parameters.get("pipeline_id"),
            "preview_mode": self.config.parameters.get("preview_mode", False),
        }


@register_task_handler(TaskType.TRAINING)
class TrainingTaskHandler(BaseTaskHandler):
    """Training task handler - executes ML training"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute training job"""
        from app.services.ml.training import TrainingService

        training_service = TrainingService()

        experiment_id = self.config.parameters.get("experiment_id")
        model_config = self.config.parameters.get("model_config", {})

        # Run training
        run = await training_service.train(
            experiment_id=experiment_id,
            model_config=model_config,
            dataset_id=self.config.parameters.get("dataset_id"),
            hyperparameters=self.config.parameters.get("hyperparameters", {}),
        )

        return {
            "run_id": run.id,
            "status": run.status,
            "metrics": run.metrics,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate Training task configuration"""
        errors = []
        if not self.config.parameters.get("experiment_id"):
            errors.append("experiment_id is required")
        return errors


@register_task_handler(TaskType.INFERENCE)
class InferenceTaskHandler(BaseTaskHandler):
    """Inference task handler - runs model inference"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute inference"""
        from app.services.serving import InferenceService

        inference_service = InferenceService()

        model_version_id = self.config.parameters.get("model_version_id")
        input_data = self.config.parameters.get("input_data", {})

        # Run inference
        result = await inference_service.predict(
            model_version_id=model_version_id,
            data=input_data,
        )

        return {
            "predictions": result,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate Inference task configuration"""
        errors = []
        if not self.config.parameters.get("model_version_id"):
            errors.append("model_version_id is required")
        return errors


@register_task_handler(TaskType.WAIT)
class WaitTaskHandler(BaseTaskHandler):
    """Wait task handler - waits for specified time"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait"""
        import asyncio

        wait_seconds = self.config.parameters.get("wait_seconds", 60)
        await asyncio.sleep(wait_seconds)

        return {
            "waited_seconds": wait_seconds,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate Wait task configuration"""
        errors = []
        wait_seconds = self.config.parameters.get("wait_seconds", 60)
        if wait_seconds < 0:
            errors.append("wait_seconds must be non-negative")
        return errors


@register_task_handler(TaskType.SENSOR)
class SensorTaskHandler(BaseTaskHandler):
    """Sensor task handler - waits for a condition"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sensor check"""
        import asyncio

        sensor_type = self.config.parameters.get("sensor_type", "file")

        # Poll until condition is met or timeout
        timeout = self.config.parameters.get("timeout_seconds", 300)
        poke_interval = self.config.parameters.get("poke_interval_seconds", 60)

        start_time = datetime.utcnow()

        while True:
            # Check condition
            condition_met = await self.poke(context)

            if condition_met:
                return {
                    "sensor_type": sensor_type,
                    "condition_met": True,
                    "executed_at": datetime.utcnow().isoformat(),
                }

            # Check timeout
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                raise TimeoutError(f"Sensor timed out after {timeout} seconds")

            # Wait before next poke
            await asyncio.sleep(poke_interval)

    async def poke(self, context: Dict[str, Any]) -> bool:
        """Check if sensor condition is met"""
        sensor_type = self.config.parameters.get("sensor_type")

        if sensor_type == "file":
            # Check if file exists
            import os
            file_path = self.config.parameters.get("file_path")
            return os.path.exists(file_path)

        elif sensor_type == "sql":
            # Check if SQL query returns results
            connector = get_connector(
                "postgresql",
                self.config.parameters.get("connection", {}),
            )
            result = await connector.execute_query(
                self.config.parameters.get("sql", "SELECT 1")
            )
            return len(result) > 0

        elif sensor_type == "api":
            # Check API endpoint
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.parameters.get("url"),  # type: ignore
                    headers=self.config.parameters.get("headers", {}),
                ) as response:
                    return response.status == 200

        return False

    def validate(self) -> List[str]:
        """Validate Sensor task configuration"""
        errors = []
        sensor_type = self.config.parameters.get("sensor_type")
        if not sensor_type:
            errors.append("sensor_type is required")
        return errors


@register_task_handler(TaskType.NOTEBOOK)
class NotebookTaskHandler(BaseTaskHandler):
    """Notebook task handler - executes Jupyter notebook"""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute notebook"""
        import papermill as pm

        notebook_path = self.config.parameters.get("notebook_path")
        output_path = self.config.parameters.get("output_path")
        parameters = self.config.parameters.get("parameters", {})

        # Execute notebook
        result = pm.execute_notebook(
            input_path=notebook_path,
            output_path=output_path,
            parameters=parameters,
        )

        return {
            "notebook_path": notebook_path,
            "output_path": output_path,
            "executed_at": datetime.utcnow().isoformat(),
        }

    def validate(self) -> List[str]:
        """Validate Notebook task configuration"""
        errors = []
        if not self.config.parameters.get("notebook_path"):
            errors.append("notebook_path is required")
        return errors
