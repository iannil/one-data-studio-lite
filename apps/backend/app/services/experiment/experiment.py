"""
Experiment Service

Business logic for experiment management.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .mlflow_client import get_mlflow_client

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    Service for managing MLflow experiments
    """

    def __init__(self):
        self._mlflow = get_mlflow_client()

    async def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new experiment

        Args:
            name: Experiment name
            description: Optional description
            tags: Optional tags
            project_id: Optional project ID for multi-tenancy

        Returns:
            Created experiment metadata
        """
        # Add project tag if provided
        experiment_tags = tags or {}
        if description:
            experiment_tags["description"] = description
        if project_id:
            experiment_tags["project_id"] = str(project_id)

        experiment_id = self._mlflow.create_experiment(
            name=name,
            tags=experiment_tags if experiment_tags else None,
        )

        return await self.get_experiment(experiment_id)

    async def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get experiment by ID

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment metadata
        """
        exp = self._mlflow.get_experiment(experiment_id)

        # Get run count
        runs = self._mlflow.list_runs(experiment_id, max_results=1)
        run_count = len(self._mlflow.list_runs(experiment_id, max_results=10000))

        # Get best run (by first metric)
        best_run = self._get_best_run(experiment_id)

        return {
            **exp,
            "run_count": run_count,
            "best_run": best_run,
            "description": exp.get("tags", {}).get("description", ""),
        }

    async def list_experiments(
        self,
        project_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all experiments

        Args:
            project_id: Optional project ID filter
            search: Optional search term for name

        Returns:
            List of experiment metadata with stats
        """
        experiments = self._mlflow.list_experiments()

        # Filter by project if specified
        if project_id is not None:
            experiments = [
                e for e in experiments
                if e.get("tags", {}).get("project_id") == str(project_id)
            ]

        # Filter by search term
        if search:
            search_lower = search.lower()
            experiments = [
                e for e in experiments
                if search_lower in e.get("name", "").lower()
            ]

        # Add run counts and best runs
        result = []
        for exp in experiments:
            runs = self._mlflow.list_runs(exp["id"], max_results=10000)
            run_count = len(runs)

            best_run = None
            if runs:
                # Try to find a run with metrics to determine "best"
                best_run = self._get_best_run(exp["id"])

            result.append({
                **exp,
                "run_count": run_count,
                "best_run": best_run,
                "description": exp.get("tags", {}).get("description", ""),
            })

        return result

    async def update_experiment(
        self,
        experiment_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Update experiment

        Args:
            experiment_id: Experiment ID
            name: New name
            description: New description (stored as tag)
            tags: New tags (replaces all tags)

        Returns:
            True if updated successfully
        """
        update_tags = tags or {}

        if description:
            update_tags["description"] = description

        return self._mlflow.update_experiment(
            experiment_id=experiment_id,
            name=name,
            tags=update_tags if update_tags else None,
        )

    async def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete experiment (soft delete)

        Args:
            experiment_id: Experiment ID

        Returns:
            True if deleted successfully
        """
        return self._mlflow.delete_experiment(experiment_id)

    async def restore_experiment(self, experiment_id: str) -> bool:
        """
        Restore deleted experiment

        Args:
            experiment_id: Experiment ID

        Returns:
            True if restored successfully
        """
        return self._mlflow.restore_experiment(experiment_id)

    async def get_experiment_runs(
        self,
        experiment_id: str,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all runs for an experiment

        Args:
            experiment_id: Experiment ID
            max_results: Maximum number of runs
            order_by: Order by clauses

        Returns:
            List of run metadata
        """
        return self._mlflow.list_runs(
            experiment_id=experiment_id,
            max_results=max_results,
            order_by=order_by or ["start_time DESC"],
        )

    async def get_experiment_metrics(
        self,
        experiment_id: str,
        metric_keys: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get metric history for all metrics in an experiment

        Args:
            experiment_id: Experiment ID
            metric_keys: Optional list of specific metric keys

        Returns:
            Dict mapping metric key to history
        """
        runs = await self.get_experiment_runs(experiment_id, max_results=1000)

        all_metrics: Dict[str, List[Dict[str, Any]]] = {}

        for run in runs:
            run_id = run["run_id"]
            metrics = run.get("metrics", {})

            for key, value in metrics.items():
                if metric_keys and key not in metric_keys:
                    continue

                if key not in all_metrics:
                    all_metrics[key] = []

                all_metrics[key].append({
                    "run_id": run_id,
                    "run_name": run.get("run_name", run_id[:8]),
                    "value": value,
                    "timestamp": run.get("start_time"),
                    "step": 0,  # Static metrics from run summary
                })

        return all_metrics

    async def compare_runs(
        self,
        run_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Compare multiple runs

        Args:
            run_ids: List of run IDs to compare

        Returns:
            Comparison data with params and metrics
        """
        runs = []
        all_params = set()
        all_metrics = set()

        for run_id in run_ids:
            run = self._mlflow.get_run(run_id)
            runs.append(run)
            all_params.update(run.get("params", {}).keys())
            all_metrics.update(run.get("metrics", {}).keys())

        return {
            "runs": runs,
            "param_keys": sorted(all_params),
            "metric_keys": sorted(all_metrics),
        }

    async def delete_runs_batch(
        self,
        experiment_id: str,
        run_ids: List[str],
    ) -> Dict[str, bool]:
        """
        Delete multiple runs

        Args:
            experiment_id: Experiment ID
            run_ids: List of run IDs to delete

        Returns:
            Dict mapping run_id to success status
        """
        results = {}
        for run_id in run_ids:
            results[run_id] = self._mlflow.delete_run(run_id)
        return results

    def _get_best_run(
        self,
        experiment_id: str,
        metric_key: str = None,
        mode: str = "max",
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best run for an experiment

        Args:
            experiment_id: Experiment ID
            metric_key: Metric key to optimize (uses first available if None)
            mode: "min" or "max"

        Returns:
            Best run metadata or None
        """
        runs = self._mlflow.list_runs(experiment_id, max_results=1000)

        if not runs:
            return None

        # Filter runs with metrics
        runs_with_metrics = [r for r in runs if r.get("metrics")]
        if not runs_with_metrics:
            return None

        # Determine metric to use
        if metric_key is None:
            # Use first available metric
            first_run = runs_with_metrics[0]
            metric_key = list(first_run.get("metrics", {}).keys())[0]

        # Find best run
        best_run = None
        best_value = None

        for run in runs_with_metrics:
            value = run.get("metrics", {}).get(metric_key)
            if value is None:
                continue

            if best_value is None:
                best_value = value
                best_run = run
            elif mode == "max" and value > best_value:
                best_value = value
                best_run = run
            elif mode == "min" and value < best_value:
                best_value = value
                best_run = run

        if best_run:
            return {
                **best_run,
                "optimized_metric": metric_key,
                "optimized_value": best_value,
            }

        return None


# Singleton instance
_experiment_service: Optional[ExperimentService] = None


def get_experiment_service() -> ExperimentService:
    """Get or create experiment service singleton"""
    global _experiment_service
    if _experiment_service is None:
        _experiment_service = ExperimentService()
    return _experiment_service
