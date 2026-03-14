"""
Workflow Scheduler for One Data Studio Lite

Manages workflow scheduling and execution.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid

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
        return await self.dag_engine.pause_dag(dag_id)

    async def unpause_dag(self, dag_id: str) -> bool:
        """
        Unpause a DAG (allow scheduled runs)

        Args:
            dag_id: DAG ID

        Returns:
            True if unpaused successfully
        """
        return await self.dag_engine.unpause_dag(dag_id)

    async def set_dag_active(self, dag_id: str, is_active: bool) -> bool:
        """
        Set DAG active status

        Args:
            dag_id: DAG ID
            is_active: Active status

        Returns:
            True if updated successfully
        """
        return await self.dag_engine.set_dag_active(dag_id, is_active)

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
        if run_id:
            return await self.dag_engine.get_task_instances(dag_id, run_id)
        return []

    # ==========================================================================
    # Backfill Functionality
    # ==========================================================================

    async def backfill_dag(
        self,
        dag_id: str,
        start_date: str,
        end_date: str,
        dry_run: bool = False,
        clear_first: bool = False,
        task_regex: Optional[str] = None,
        max_backfill_runs: int = 365,
    ) -> Dict[str, Any]:
        """
        Backfill a DAG for historical dates

        This triggers DAG runs for past dates that were missed or need to be re-run.

        Args:
            dag_id: DAG ID to backfill
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dry_run: Run in dry-run mode without executing
            clear_first: Clear existing runs first
            task_regex: Regex pattern to filter tasks
            max_backfill_runs: Maximum number of backfill runs

        Returns:
            Backfill result with status and details
        """
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)

            # Calculate number of days
            delta = end_dt - start_dt
            days = delta.days + 1

            if days > max_backfill_runs:
                raise ValueError(
                    f"Backfill range exceeds maximum of {max_backfill_runs} days"
                )

            # Clear existing runs if requested
            cleared_runs = 0
            if clear_first and not dry_run:
                cleared_runs = await self._clear_dag_runs(
                    dag_id, start_date, end_date
                )

            # Create backfill DAG runs
            backfill_id = f"backfill_{dag_id}_{datetime.utcnow().timestamp()}"

            results = []
            current_date = start_dt
            run_count = 0

            while current_date <= end_dt:
                execution_date = current_date.strftime("%Y-%m-%dT%H:%M:%S")

                if not dry_run:
                    try:
                        result = await self.trigger_dag_run(
                            dag_id=dag_id,
                            conf={
                                "backfill": True,
                                "backfill_id": backfill_id,
                                "execution_date": execution_date,
                                "task_regex": task_regex,
                            },
                        )
                        results.append({
                            "execution_date": execution_date,
                            "dag_run_id": result.get("dag_run_id"),
                            "status": result.get("state"),
                        })
                        run_count += 1
                    except Exception as e:
                        logger.error(
                            f"Failed to trigger backfill run for {execution_date}: {e}"
                        )
                        results.append({
                            "execution_date": execution_date,
                            "status": "failed",
                            "error": str(e),
                        })
                else:
                    results.append({
                        "execution_date": execution_date,
                        "status": "dry_run",
                    })

                current_date = current_date + timedelta(days=1)

            logger.info(
                f"Backfill completed: {dag_id} from {start_date} to {end_date} "
                f"({run_count} runs triggered)"
            )

            return {
                "backfill_id": backfill_id,
                "dag_id": dag_id,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
                "dry_run": dry_run,
                "clear_first": clear_first,
                "cleared_runs": cleared_runs,
                "runs_triggered": run_count if not dry_run else 0,
                "runs": results,
                "status": "completed" if not dry_run else "dry_run",
            }

        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Backfill failed for {dag_id}: {e}")
            return {
                "dag_id": dag_id,
                "status": "failed",
                "error": str(e),
            }

    async def _clear_dag_runs(
        self,
        dag_id: str,
        start_date: str,
        end_date: str,
    ) -> int:
        """
        Clear DAG runs within a date range

        Args:
            dag_id: DAG ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Number of runs cleared
        """
        # This would interact with Airflow API to clear runs
        # For now, just log
        logger.info(
            f"Clearing DAG runs for {dag_id} from {start_date} to {end_date}"
        )
        return 0

    async def get_backfill_status(
        self,
        backfill_id: str,
    ) -> Dict[str, Any]:
        """
        Get the status of a backfill operation

        Args:
            backfill_id: Backfill operation ID

        Returns:
            Backfill status information
        """
        # This would query the database for backfill status
        return {
            "backfill_id": backfill_id,
            "status": "unknown",
            "message": "Backfill status tracking not yet implemented",
        }

    async def list_backfills(
        self,
        dag_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List backfill operations

        Args:
            dag_id: Optional DAG ID filter
            limit: Max number of results

        Returns:
            List of backfill operations
        """
        # This would query the database for backfill operations
        return []

    # ==========================================================================
    # DAG Code Management
    # ==========================================================================

    async def get_dag_code(self, dag_id: str) -> Optional[str]:
        """
        Get the generated Python code for a DAG

        Args:
            dag_id: DAG ID

        Returns:
            DAG code or None if file doesn't exist
        """
        return await self.dag_engine.get_dag_code(dag_id)

    async def validate_dag(self, dag_id: str) -> Dict[str, Any]:
        """
        Validate a DAG's syntax

        Args:
            dag_id: DAG ID

        Returns:
            Validation result
        """
        try:
            code = await self.get_dag_code(dag_id)
            if not code:
                return {"valid": False, "error": "DAG file not found"}

            # Try to compile the code
            compile(code, f"<string:{dag_id}>", "exec")

            return {"valid": True, "dag_id": dag_id}

        except SyntaxError as e:
            return {"valid": False, "error": f"Syntax error: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
