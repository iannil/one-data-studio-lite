"""
Run Service

Business logic for run management.
"""

import logging
import tempfile
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .mlflow_client import get_mlflow_client

logger = logging.getLogger(__name__)


class RunService:
    """
    Service for managing MLflow runs
    """

    def __init__(self):
        self._mlflow = get_mlflow_client()

    async def create_run(
        self,
        experiment_id: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new run

        Args:
            experiment_id: Experiment ID
            run_name: Optional run name
            tags: Optional tags

        Returns:
            Created run metadata
        """
        run_id = self._mlflow.create_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=tags,
        )

        return await self.get_run(run_id)

    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get run by ID

        Args:
            run_id: Run ID

        Returns:
            Run metadata with enhanced data
        """
        run = self._mlflow.get_run(run_id)

        # Get artifacts
        artifacts = self._mlflow.list_artifacts(run_id)

        # Get metric histories for key metrics
        metric_histories = {}
        for key in list(run.get("metrics", {}).keys())[:10]:  # Limit to 10 metrics
            history = self._mlflow.get_metric_history(run_id, key)
            if history:
                metric_histories[key] = history

        return {
            **run,
            "artifacts": artifacts,
            "metric_histories": metric_histories,
        }

    async def list_runs(
        self,
        experiment_id: Optional[str] = None,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List runs

        Args:
            experiment_id: Optional experiment ID
            max_results: Maximum number of runs
            order_by: Order by clauses
            status: Optional status filter

        Returns:
            List of run metadata
        """
        runs = self._mlflow.list_runs(
            experiment_id=experiment_id,
            max_results=max_results,
            order_by=order_by or ["start_time DESC"],
        )

        # Filter by status if specified
        if status:
            runs = [r for r in runs if r.get("status") == status]

        return runs

    async def update_run(
        self,
        run_id: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Update run metadata

        Args:
            run_id: Run ID
            run_name: New run name
            tags: Tags to set

        Returns:
            True if updated successfully
        """
        try:
            if tags:
                self._mlflow.set_tags(run_id, tags)
            # MLflow doesn't support renaming runs directly
            # Can be done via tags
            if run_name:
                self._mlflow.set_tag(run_id, "mlflow.runName", run_name)
            return True
        except Exception as e:
            logger.error(f"Error updating run {run_id}: {e}")
            return False

    async def log_params(
        self,
        run_id: str,
        params: Dict[str, Any],
    ) -> bool:
        """
        Log parameters to a run

        Args:
            run_id: Run ID
            params: Parameters to log

        Returns:
            True if logged successfully
        """
        return self._mlflow.log_params(run_id, params)

    async def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: int = 0,
    ) -> bool:
        """
        Log metrics to a run

        Args:
            run_id: Run ID
            metrics: Metrics to log
            step: Training step

        Returns:
            True if logged successfully
        """
        return self._mlflow.log_metrics(run_id, metrics, step=step)

    async def log_metric_batch(
        self,
        run_id: str,
        metrics: List[Dict[str, Any]],
    ) -> bool:
        """
        Log multiple metric values at different steps

        Args:
            run_id: Run ID
            metrics: List of {"key": str, "value": float, "step": int, "timestamp": int}

        Returns:
            True if logged successfully
        """
        try:
            for metric in metrics:
                self._mlflow.log_metric(
                    run_id,
                    metric["key"],
                    metric["value"],
                    step=metric.get("step", 0),
                )
            return True
        except Exception as e:
            logger.error(f"Error logging metric batch to run {run_id}: {e}")
            return False

    async def log_artifact_from_file(
        self,
        run_id: str,
        file_path: str,
        artifact_path: Optional[str] = None,
    ) -> bool:
        """
        Log an artifact file

        Args:
            run_id: Run ID
            file_path: Path to local file
            artifact_path: Destination artifact path

        Returns:
            True if logged successfully
        """
        return self._mlflow.log_artifact(run_id, file_path, artifact_path)

    async def log_artifact_from_bytes(
        self,
        run_id: str,
        content: bytes,
        artifact_path: str,
    ) -> bool:
        """
        Log an artifact from bytes

        Args:
            run_id: Run ID
            content: File content
            artifact_path: Destination artifact path

        Returns:
            True if logged successfully
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False) as f:
                f.write(content)
                temp_path = f.name

            # Log artifact
            result = self._mlflow.log_artifact(run_id, temp_path, artifact_path)

            # Clean up
            os.unlink(temp_path)

            return result
        except Exception as e:
            logger.error(f"Error logging artifact from bytes to run {run_id}: {e}")
            return False

    async def log_model(
        self,
        run_id: str,
        model_path: str,
        model_type: str = "sklearn",
        model: Any = None,
        **kwargs,
    ) -> bool:
        """
        Log a model

        Args:
            run_id: Run ID
            model_path: Artifact path for the model
            model_type: Model type (sklearn, pytorch, tensorflow, pyfunc)
            model: Model object
            **kwargs: Additional arguments for model logging

        Returns:
            True if logged successfully
        """
        return self._mlflow.log_model(
            run_id=run_id,
            model_path=model_path,
            model_type=model_type,
            model=model,
            **kwargs,
        )

    async def set_run_status(
        self,
        run_id: str,
        status: str,
    ) -> bool:
        """
        Set run status (terminate run)

        Args:
            run_id: Run ID
            status: Status (FINISHED, FAILED, KILLED)

        Returns:
            True if status set successfully
        """
        return self._mlflow.set_terminated(run_id, status=status)

    async def delete_run(self, run_id: str) -> bool:
        """
        Delete a run

        Args:
            run_id: Run ID

        Returns:
            True if deleted successfully
        """
        return self._mlflow.delete_run(run_id)

    async def restore_run(self, run_id: str) -> bool:
        """
        Restore a deleted run

        Args:
            run_id: Run ID

        Returns:
            True if restored successfully
        """
        return self._mlflow.restore_run(run_id)

    async def get_metric_history(
        self,
        run_id: str,
        metric_key: str,
    ) -> List[Dict[str, Any]]:
        """
        Get metric history

        Args:
            run_id: Run ID
            metric_key: Metric key

        Returns:
            List of metric values with timestamps and steps
        """
        return self._mlflow.get_metric_history(run_id, metric_key)

    async def get_run_artifacts(
        self,
        run_id: str,
        path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List run artifacts

        Args:
            run_id: Run ID
            path: Artifact path

        Returns:
            List of artifact metadata
        """
        return self._mlflow.list_artifacts(run_id, path)

    async def download_artifact(
        self,
        run_id: str,
        path: str,
        local_path: str,
    ) -> bool:
        """
        Download artifact

        Args:
            run_id: Run ID
            path: Artifact path
            local_path: Local destination path

        Returns:
            True if downloaded successfully
        """
        return self._mlflow.download_artifacts(run_id, path, local_path)

    async def search_runs(
        self,
        experiment_ids: Optional[List[str]] = None,
        filter_string: Optional[str] = None,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for runs

        Args:
            experiment_ids: List of experiment IDs
            filter_string: Filter string (e.g., "params.lr > 0.01")
            max_results: Maximum number of results
            order_by: Order by clauses

        Returns:
            List of run metadata
        """
        return self._mlflow.search_runs(
            experiment_ids=experiment_ids,
            filter_string=filter_string,
            max_results=max_results,
            order_by=order_by,
        )

    async def get_run_comparison(
        self,
        run_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple runs

        Args:
            run_ids: List of run IDs

        Returns:
            Comparison data
        """
        runs = []
        all_params = set()
        all_metrics = set()

        for run_id in run_ids:
            run = await self.get_run(run_id)
            runs.append(run)
            all_params.update(run.get("params", {}).keys())
            all_metrics.update(run.get("metrics", {}).keys())

        return {
            "runs": runs,
            "param_keys": sorted(all_params),
            "metric_keys": sorted(all_metrics),
        }

    async def batch_create_runs(
        self,
        experiment_id: str,
        configs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Create multiple runs with initial params

        Args:
            experiment_id: Experiment ID
            configs: List of run configs with name, tags, params

        Returns:
            List of created run IDs
        """
        results = []
        for config in configs:
            run_id = self._mlflow.create_run(
                experiment_id=experiment_id,
                run_name=config.get("name"),
                tags=config.get("tags"),
            )

            # Log initial params if provided
            if config.get("params"):
                self._mlflow.log_params(run_id, config["params"])

            results.append({"run_id": run_id, "config": config})

        return results


# Singleton instance
_run_service: Optional[RunService] = None


def get_run_service() -> RunService:
    """Get or create run service singleton"""
    global _run_service
    if _run_service is None:
        _run_service = RunService()
    return _run_service
