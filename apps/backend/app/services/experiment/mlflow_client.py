"""
MLflow Client Wrapper

Provides a Pythonic interface to MLflow tracking server.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pathlib import Path

try:
    import mlflow
    from mlflow.tracking import MlflowClient
    from mlflow.entities import Experiment, Run
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class MLflowClientWrapper:
    """
    Wrapper around MLflow client with simplified API
    """

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        registry_uri: Optional[str] = None,
    ):
        """
        Initialize MLflow client

        Args:
            tracking_uri: MLflow tracking server URI
            registry_uri: MLflow model registry URI
        """
        if not MLFLOW_AVAILABLE:
            raise ImportError(
                "MLflow is not installed. Install it with: pip install mlflow"
            )

        self.tracking_uri = tracking_uri or settings.MLFLOW_TRACKING_URI
        self.registry_uri = registry_uri or settings.MLFLOW_REGISTRY_URI

        # Set tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        if self.registry_uri:
            mlflow.set_registry_uri(self.registry_uri)

        self._client = MlflowClient(tracking_uri=self.tracking_uri)

    # Experiment Operations

    def create_experiment(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
        artifact_location: Optional[str] = None,
    ) -> str:
        """
        Create a new experiment

        Args:
            name: Experiment name
            tags: Optional tags for the experiment
            artifact_location: Optional artifact location

        Returns:
            Experiment ID
        """
        experiment_id = self._client.create_experiment(
            name=name,
            tags=tags,
            artifact_location=artifact_location,
        )
        logger.info(f"Created experiment: {name} (ID: {experiment_id})")
        return experiment_id

    def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get experiment by ID

        Args:
            experiment_id: Experiment ID

        Returns:
            Experiment metadata
        """
        exp = self._client.get_experiment(experiment_id)
        return self._experiment_to_dict(exp)

    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get experiment by name

        Args:
            name: Experiment name

        Returns:
            Experiment metadata or None if not found
        """
        try:
            exp = self._client.get_experiment_by_name(name)
            return self._experiment_to_dict(exp) if exp else None
        except Exception as e:
            logger.error(f"Error getting experiment by name {name}: {e}")
            return None

    def list_experiments(
        self,
        view_type: str = "ACTIVE_ONLY",
    ) -> List[Dict[str, Any]]:
        """
        List all experiments

        Args:
            view_type: View type (ACTIVE_ONLY, DELETED_ONLY, ALL)

        Returns:
            List of experiment metadata
        """
        from mlflow.entities import ViewType

        view_type_map = {
            "ACTIVE_ONLY": ViewType.ACTIVE_ONLY,
            "DELETED_ONLY": ViewType.DELETED_ONLY,
            "ALL": ViewType.ALL,
        }

        experiments = self._client.list_experiments(view_type=view_type_map.get(view_type, ViewType.ACTIVE_ONLY))
        return [self._experiment_to_dict(exp) for exp in experiments]

    def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete an experiment (soft delete)

        Args:
            experiment_id: Experiment ID

        Returns:
            True if deleted successfully
        """
        try:
            self._client.delete_experiment(experiment_id)
            logger.info(f"Deleted experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting experiment {experiment_id}: {e}")
            return False

    def restore_experiment(self, experiment_id: str) -> bool:
        """
        Restore a deleted experiment

        Args:
            experiment_id: Experiment ID

        Returns:
            True if restored successfully
        """
        try:
            self._client.restore_experiment(experiment_id)
            logger.info(f"Restored experiment: {experiment_id}")
            return True
        except Exception as e:
            logger.error(f"Error restoring experiment {experiment_id}: {e}")
            return False

    def update_experiment(
        self,
        experiment_id: str,
        name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Update experiment metadata

        Args:
            experiment_id: Experiment ID
            name: New name
            tags: Tags to set (replaces all tags)

        Returns:
            True if updated successfully
        """
        try:
            if name:
                self._client.rename_experiment(experiment_id, name)
            if tags:
                self._client.set_experiment_tag(experiment_id, tags)
            return True
        except Exception as e:
            logger.error(f"Error updating experiment {experiment_id}: {e}")
            return False

    # Run Operations

    def create_run(
        self,
        experiment_id: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Create a new run

        Args:
            experiment_id: Experiment ID
            run_name: Optional run name
            tags: Optional tags

        Returns:
            Run ID
        """
        run = self._client.create_run(
            experiment_id=experiment_id,
            tags=tags,
            run_name=run_name,
        )
        logger.info(f"Created run: {run.info.run_id} in experiment {experiment_id}")
        return run.info.run_id

    def get_run(self, run_id: str) -> Dict[str, Any]:
        """
        Get run by ID

        Args:
            run_id: Run ID

        Returns:
            Run metadata with params, metrics, and tags
        """
        run = self._client.get_run(run_id)
        return self._run_to_dict(run)

    def list_runs(
        self,
        experiment_id: Optional[str] = None,
        max_results: int = 1000,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        List runs from an experiment

        Args:
            experiment_id: Experiment ID (None for all experiments)
            max_results: Maximum number of runs to return
            order_by: List of order by clauses

        Returns:
            List of run metadata
        """
        runs = self._client.search_runs(
            experiment_ids=[experiment_id] if experiment_id else None,
            max_results=max_results,
            order_by=order_by,
        )
        return [self._run_to_dict(run) for run in runs]

    def delete_run(self, run_id: str) -> bool:
        """
        Delete a run

        Args:
            run_id: Run ID

        Returns:
            True if deleted successfully
        """
        try:
            self._client.delete_run(run_id)
            logger.info(f"Deleted run: {run_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting run {run_id}: {e}")
            return False

    def restore_run(self, run_id: str) -> bool:
        """
        Restore a deleted run

        Args:
            run_id: Run ID

        Returns:
            True if restored successfully
        """
        try:
            self._client.restore_run(run_id)
            logger.info(f"Restored run: {run_id}")
            return True
        except Exception as e:
            logger.error(f"Error restoring run {run_id}: {e}")
            return False

    # Logging Operations

    def log_param(self, run_id: str, key: str, value: str) -> bool:
        """Log a parameter to a run"""
        try:
            self._client.log_param(run_id, key, value)
            return True
        except Exception as e:
            logger.error(f"Error logging param {key} to run {run_id}: {e}")
            return False

    def log_params(self, run_id: str, params: Dict[str, Any]) -> bool:
        """Log multiple parameters to a run"""
        try:
            # Convert all values to strings
            str_params = {k: str(v) for k, v in params.items()}
            self._client.log_params(run_id, str_params)
            return True
        except Exception as e:
            logger.error(f"Error logging params to run {run_id}: {e}")
            return False

    def log_metric(self, run_id: str, key: str, value: float, step: int = 0) -> bool:
        """Log a metric to a run"""
        try:
            self._client.log_metric(run_id, key, value, step=step)
            return True
        except Exception as e:
            logger.error(f"Error logging metric {key} to run {run_id}: {e}")
            return False

    def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: int = 0,
    ) -> bool:
        """Log multiple metrics to a run"""
        try:
            self._client.log_metrics(run_id, metrics, step=step)
            return True
        except Exception as e:
            logger.error(f"Error logging metrics to run {run_id}: {e}")
            return False

    def log_batch(
        self,
        run_id: str,
        params: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Log a batch of params, metrics, and tags"""
        try:
            self._client.log_batch(
                run_id,
                params=[(k, str(v)) for k, v in (params or {}).items()],
                metrics=metrics or {},
                tags=tags or {},
            )
            return True
        except Exception as e:
            logger.error(f"Error logging batch to run {run_id}: {e}")
            return False

    def log_artifact(
        self,
        run_id: str,
        local_path: str,
        artifact_path: Optional[str] = None,
    ) -> bool:
        """Log an artifact file"""
        try:
            self._client.log_artifact(run_id, local_path, artifact_path)
            return True
        except Exception as e:
            logger.error(f"Error logging artifact {local_path} to run {run_id}: {e}")
            return False

    def log_artifacts(
        self,
        run_id: str,
        local_dir: str,
        artifact_path: Optional[str] = None,
    ) -> bool:
        """Log all artifacts in a directory"""
        try:
            self._client.log_artifacts(run_id, local_dir, artifact_path)
            return True
        except Exception as e:
            logger.error(f"Error logging artifacts from {local_dir} to run {run_id}: {e}")
            return False

    def log_model(
        self,
        run_id: str,
        model_path: str,
        model_type: str = "sklearn",
        **kwargs,
    ) -> bool:
        """Log a model to MLflow"""
        try:
            if model_type == "sklearn":
                mlflow.sklearn.log_model(sklearn_model=kwargs.get("model"), artifact_path=model_path)
            elif model_type == "pytorch":
                mlflow.pytorch.log_model(pytorch_model=kwargs.get("model"), artifact_path=model_path)
            elif model_type == "tensorflow":
                mlflow.tensorflow.log_model(tf_model=kwargs.get("model"), artifact_path=model_path)
            else:
                # Custom model
                mlflow.pyfunc.log_model(artifact_path=model_path, **kwargs)
            return True
        except Exception as e:
            logger.error(f"Error logging model to run {run_id}: {e}")
            return False

    def set_tag(self, run_id: str, key: str, value: str) -> bool:
        """Set a tag on a run"""
        try:
            self._client.set_tag(run_id, key, value)
            return True
        except Exception as e:
            logger.error(f"Error setting tag {key} on run {run_id}: {e}")
            return False

    def set_tags(self, run_id: str, tags: Dict[str, str]) -> bool:
        """Set multiple tags on a run"""
        try:
            self._client.set_tags(run_id, tags)
            return True
        except Exception as e:
            logger.error(f"Error setting tags on run {run_id}: {e}")
            return False

    def delete_tag(self, run_id: str, key: str) -> bool:
        """Delete a tag from a run"""
        try:
            self._client.delete_tag(run_id, key)
            return True
        except Exception as e:
            logger.error(f"Error deleting tag {key} from run {run_id}: {e}")
            return False

    # Run State Operations

    def set_terminated(self, run_id: str, status: str = "FINISHED", end_time: Optional[int] = None) -> bool:
        """
        Terminate a run

        Args:
            run_id: Run ID
            status: Terminal status (FINISHED, FAILED, KILLED)
            end_time: Optional end time in milliseconds since epoch

        Returns:
            True if terminated successfully
        """
        try:
            from mlflow.entities import LifecycleStage

            status_map = {
                "FINISHED": "FINISHED",
                "FAILED": "FAILED",
                "KILLED": "KILLED",
            }

            self._client.set_terminated(run_id, status=status_map.get(status, "FINISHED"), end_time=end_time)
            return True
        except Exception as e:
            logger.error(f"Error terminating run {run_id}: {e}")
            return False

    # Metric History

    def get_metric_history(self, run_id: str, key: str) -> List[Dict[str, Any]]:
        """
        Get metric history for a specific metric

        Args:
            run_id: Run ID
            key: Metric key

        Returns:
            List of metric values with timestamps and steps
        """
        try:
            history = self._client.get_metric_history(run_id, key)
            return [
                {
                    "key": h.key,
                    "value": h.value,
                    "timestamp": h.timestamp,
                    "step": h.step,
                }
                for h in history
            ]
        except Exception as e:
            logger.error(f"Error getting metric history for {key} in run {run_id}: {e}")
            return []

    # Artifacts

    def list_artifacts(self, run_id: str, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List artifacts for a run

        Args:
            run_id: Run ID
            path: Artifact path

        Returns:
            List of artifact metadata
        """
        try:
            artifacts = self._client.list_artifacts(run_id, path)
            return [
                {
                    "path": a.path,
                    "is_dir": a.is_dir,
                    "size": a.file_size if not a.is_dir else None,
                }
                for a in artifacts
            ]
        except Exception as e:
            logger.error(f"Error listing artifacts for run {run_id}: {e}")
            return []

    def download_artifacts(
        self,
        run_id: str,
        path: str,
        local_path: str,
    ) -> bool:
        """
        Download artifacts from a run

        Args:
            run_id: Run ID
            path: Artifact path
            local_path: Local destination path

        Returns:
            True if downloaded successfully
        """
        try:
            self._client.download_artifacts(run_id, path, local_path)
            return True
        except Exception as e:
            logger.error(f"Error downloading artifacts from run {run_id}: {e}")
            return False

    # Search

    def search_runs(
        self,
        experiment_ids: Optional[List[str]] = None,
        filter_string: Optional[str] = None,
        max_results: int = 1000,
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
        runs = self._client.search_runs(
            experiment_ids=experiment_ids,
            filter_string=filter_string,
            max_results=max_results,
            order_by=order_by,
        )
        return [self._run_to_dict(run) for run in runs]

    # Helper Methods

    def _experiment_to_dict(self, exp: Experiment) -> Dict[str, Any]:
        """Convert MLflow Experiment to dict"""
        return {
            "id": exp.experiment_id,
            "name": exp.name,
            "artifact_location": exp.artifact_location,
            "lifecycle_stage": exp.lifecycle_stage,
            "tags": exp.tags or {},
            "creation_time": exp.creation_time,
            "last_update_time": exp.last_update_time,
        }

    def _run_to_dict(self, run: Run) -> Dict[str, Any]:
        """Convert MLflow Run to dict"""
        return {
            "run_id": run.info.run_id,
            "experiment_id": run.info.experiment_id,
            "run_name": run.info.run_name,
            "status": run.info.status,
            "lifecycle_stage": run.info.lifecycle_stage,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "artifact_uri": run.info.artifact_uri,
            "params": run.data.params or {},
            "metrics": run.data.metrics or {},
            "tags": run.data.tags or {},
        }

    # Context Manager for Active Run

    def start_run(
        self,
        experiment_id: Optional[str] = None,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
    ):
        """
        Context manager for starting a run

        Usage:
            with mlflow_client.start_run(experiment_id="123") as run:
                mlflow_client.log_param("lr", 0.001)
        """
        return mlflow.start_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=tags,
            description=description,
        )


# Singleton instance
_mlflow_client: Optional[MLflowClientWrapper] = None


def get_mlflow_client() -> MLflowClientWrapper:
    """Get or create MLflow client singleton"""
    global _mlflow_client
    if _mlflow_client is None:
        _mlflow_client = MLflowClientWrapper()
    return _mlflow_client
