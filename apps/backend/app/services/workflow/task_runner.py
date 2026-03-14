"""
Task Runner for One Data Studio Lite

Executes individual workflow tasks.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .task_types import TaskConfig, TaskRegistry

logger = logging.getLogger(__name__)


class TaskRunner:
    """
    Task Runner

    Executes individual workflow tasks with proper error handling,
    retry logic, and timeout management.
    """

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def execute_task(
        self,
        config: TaskConfig,
        context: Dict[str, Any],
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Execute a single task

        Args:
            config: Task configuration
            context: Execution context from previous tasks
            execution_id: Execution run ID

        Returns:
            Task execution result
        """
        start_time = datetime.utcnow()
        status = "success"
        error_message = None
        result = None

        try:
            # Create handler and validate
            handler = TaskRegistry.create_handler(config)
            validation_errors = handler.validate()

            if validation_errors:
                raise ValueError(f"Task validation failed: {validation_errors}")

            # Execute with timeout
            timeout = config.timeout_seconds
            if timeout:
                result = await asyncio.wait_for(
                    self._run_with_retry(handler, context),
                    timeout=timeout,
                )
            else:
                result = await self._run_with_retry(handler, context)

        except asyncio.TimeoutError:
            status = "failed"
            error_message = f"Task timed out after {timeout} seconds"
            logger.error(f"Task {config.task_id} timed out")

        except Exception as e:
            status = "failed"
            error_message = str(e)
            logger.error(f"Task {config.task_id} failed: {e}")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return {
            "task_id": config.task_id,
            "execution_id": execution_id,
            "status": status,
            "result": result,
            "error": error_message,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
        }

    async def _run_with_retry(
        self,
        handler,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run task with retry logic

        Args:
            handler: Task handler instance
            context: Execution context

        Returns:
            Task result
        """
        max_retries = handler.config.retry_count
        retry_delay = handler.config.retry_delay_seconds

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                return await handler.execute(context)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning(
                        f"Task failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s: {e}"
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    raise last_error

    async def execute_tasks_parallel(
        self,
        configs: list[TaskConfig],
        context: Dict[str, Any],
        execution_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Execute multiple tasks in parallel

        Args:
            configs: List of task configurations
            context: Execution context
            execution_id: Execution run ID

        Returns:
            Dictionary mapping task_id to execution result
        """
        tasks = [
            self.execute_task(config, context, execution_id)
            for config in configs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            config.task_id: result if not isinstance(result, Exception) else {
                "status": "failed",
                "error": str(result),
            }
            for config, result in zip(configs, results)
        }

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled successfully
        """
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            del self.running_tasks[task_id]
            return True
        return False

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a running task

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            if task.done():
                return {"task_id": task_id, "status": "completed"}
            else:
                return {"task_id": task_id, "status": "running"}
        return None
