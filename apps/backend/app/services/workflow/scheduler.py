"""
Workflow Scheduler for One Data Studio Lite

Manages workflow scheduling and execution.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .dag_engine import DAGEngine, DAGConfig
from .task_runner import TaskRunner

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowScheduler:
    """
    Workflow Scheduler

    Manages DAG execution, scheduling, and run lifecycle.
    """

    def __init__(self, dag_engine: Optional[DAGEngine] = None):
        """
        Initialize scheduler

        Args:
            dag_engine: DAG engine instance (created if not provided)
        """
        self.dag_engine = dag_engine or DAGEngine()
        self.task_runner = TaskRunner()
        self.active_runs: Dict[str, Dict[str, Any]] = {}
        self.scheduled_runs: Dict[str, Dict[str, Any]] = {}

    async def create_dag(self, config: DAGConfig) -> Dict[str, Any]:
        """
        Create a new DAG

        Args:
            config: DAG configuration

        Returns:
            Created DAG info
        """
        return await self.dag_engine.create_dag(config)

    async def update_dag(self, dag_id: str, config: DAGConfig) -> Dict[str, Any]:
        """
        Update an existing DAG

        Args:
            dag_id: DAG ID
            config: New DAG configuration

        Returns:
            Updated DAG info
        """
        return await self.dag_engine.update_dag(dag_id, config)

    async def delete_dag(self, dag_id: str) -> bool:
        """
        Delete a DAG

        Args:
            dag_id: DAG ID

        Returns:
            True if deleted successfully
        """
        return await self.dag_engine.delete_dag(dag_id)

    async def trigger_dag_run(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a manual DAG run

        Args:
            dag_id: DAG ID to trigger
            conf: Run configuration

        Returns:
            DAG run info
        """
        # This would interact with Airflow to trigger the DAG
        # For now, return a mock response
        run_id = f"manual_{dag_id}_{datetime.utcnow().timestamp()}"
        self.scheduled_runs[run_id] = {
            "dag_id": dag_id,
            "state": ExecutionStatus.RUNNING,
            "start_date": datetime.utcnow().isoformat(),
            "conf": conf,
        }
        return await self.dag_engine.trigger_dag_run(dag_id, conf)

    async def get_dag_status(self, dag_id: str) -> Dict[str, Any]:
        """
        Get DAG status

        Args:
            dag_id: DAG ID

        Returns:
            DAG status info
        """
        return await self.dag_engine.get_dag_status(dag_id)

    async def list_dags(self) -> List[Dict[str, Any]]:
        """
        List all DAGs

        Returns:
            List of DAG info
        """
        return await self.dag_engine.list_dags()

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get DAG runs

        Args:
            dag_id: DAG ID
            limit: Max number of runs

        Returns:
            List of DAG runs
        """
        return await self.dag_engine.get_dag_runs(dag_id, limit)

    async def get_run_info(
        self,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get DAG run information

        Args:
            run_id: Run ID

        Returns:
            Run info or None if not found
        """
        return self.scheduled_runs.get(run_id)

    async def pause_dag(self, dag_id: str) -> bool:
        """
        Pause a DAG (prevent scheduled runs)

        Args:
            dag_id: DAG ID

        Returns:
            True if paused successfully
        """
        # This would interact with Airflow API
        logger.info(f"Pausing DAG: {dag_id}")
        return True

    async def unpause_dag(self, dag_id: str) -> bool:
        """
        Unpause a DAG (allow scheduled runs)

        Args:
            dag_id: DAG ID

        Returns:
            True if unpaused successfully
        """
        # This would interact with Airflow API
        logger.info(f"Unpausing DAG: {dag_id}")
        return True

    async def cancel_run(self, run_id: str) -> bool:
        """
        Cancel a running DAG run

        Args:
            run_id: Run ID

        Returns:
            True if cancelled successfully
        """
        run_info = self.scheduled_runs.get(run_id)
        if not run_info:
            return False

        run_info["state"] = ExecutionStatus.CANCELLED
        return True

    async def get_task_instances(
        self,
        dag_id: str,
        run_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get task instances for a DAG run

        Args:
            dag_id: DAG ID
            run_id: Optional run ID (for specific run)

        Returns:
            List of task instances
        """
        # This would query Airflow API for task instances
        return []
