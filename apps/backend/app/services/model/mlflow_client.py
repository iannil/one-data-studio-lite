"""
MLflow Client for One Data Studio Lite

Provides a wrapper around MLflow tracking and model registry APIs.
"""

import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# MLflow configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")


class MLflowClient:
    """
    Wrapper around MLflow client

    Provides methods for tracking experiments, runs, and model registry.
    """

    def __init__(self, tracking_uri: Optional[str] = None):
        """
        Initialize MLflow client

        Args:
            tracking_uri: MLflow tracking server URI
        """
        self.tracking_uri = tracking_uri or MLFLOW_TRACKING_URI
        self._client = None

    def _get_client(self):
        """Get or create MLflow client"""
        if self._client is None:
            try:
                from mlflow.tracking import MlflowClient
                self._client = MlflowClient(tracking_uri=self.tracking_uri)
            except ImportError:
                logger.warning("MLflow not installed, using mock client")
                self._client = MockMLflowClient()
        return self._client

    async def log_param(
        self,
        run_id: str,
        key: str,
        value: Any,
    ):
        """Log a parameter for a run"""
        client = self._get_client()
        client.log_param(run_id, key, value)

    async def log_params(
        self,
        run_id: str,
        params: Dict[str, Any],
    ):
        """Log multiple parameters"""
        client = self._get_client()
        for key, value in params.items():
            client.log_param(run_id, key, value)

    async def log_metric(
        self,
        run_id: str,
        key: str,
        value: float,
        step: Optional[int] = None,
    ):
        """Log a metric for a run"""
        client = self._get_client()
        client.log_metric(run_id, key, value, step=step)

    async def log_metrics(
        self,
        run_id: str,
        metrics: Dict[str, float],
        step: Optional[int] = None,
    ):
        """Log multiple metrics"""
        client = self._get_client()
        for key, value in metrics.items():
            client.log_metric(run_id, key, value, step=step)

    async def log_model(
        self,
        run_id: str,
        model_path: str,
        model_type: str = "sklearn",
        **kwargs,
    ):
        """Log a model artifact"""
        client = self._get_client()
        client.log_model(
            run_id,
            artifact_path=model_path,
            model_type=model_type,
            **kwargs,
        )

    async def log_artifact(
        self,
        run_id: str,
        local_path: str,
        artifact_path: Optional[str] = None,
    ):
        """Log an artifact file/directory"""
        client = self._get_client()
        client.log_artifact(run_id, local_path, artifact_path)

    async def create_experiment(
        self,
        name: str,
        artifact_location: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Create a new experiment"""
        client = self._get_client()
        experiment_id = client.create_experiment(
            name=name,
            artifact_location=artifact_location,
            tags=tags,
        )
        return str(experiment_id)

    async def get_experiment_by_name(
        self,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        """Get experiment by name"""
        client = self._get_client()
        try:
            exp = client.get_experiment_by_name(name)
            if exp:
                return {
                    "experiment_id": str(exp.experiment_id),
                    "name": exp.name,
                    "artifact_location": exp.artifact_location,
                    "lifecycle_stage": exp.lifecycle_stage,
                }
        except Exception as e:
            logger.error(f"Error getting experiment: {e}")
        return None

    async def list_experiments(
        self,
        view_type: str = "active_only",
    ) -> List[Dict[str, Any]]:
        """List all experiments"""
        client = self._get_client()
        experiments = client.search_experiments()

        result = []
        for exp in experiments:
            if view_type == "active_only" and exp.lifecycle_stage == "deleted":
                continue

            result.append({
                "experiment_id": str(exp.experiment_id),
                "name": exp.name,
                "artifact_location": exp.artifact_location,
                "lifecycle_stage": exp.lifecycle_stage,
                "creation_time": exp.creation_time,
                "last_update": exp.last_update_time,
            })

        return result

    async def create_run(
        self,
        experiment_id: str,
        run_name: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Create a new run"""
        client = self._get_client()
        run = client.create_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=tags,
        )
        return run.info.run_id

    async def get_run(self, run_id: str) -> Dict[str, Any]:
        """Get run information"""
        client = self._get_client()
        run = client.get_run(run_id)

        return {
            "run_id": run.info.run_id,
            "experiment_id": str(run.info.experiment_id),
            "run_name": run.info.run_name,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "artifact_uri": run.info.artifact_uri,
            "params": run.data.params,
            "metrics": run.data.metrics,
            "tags": run.data.tags,
        }

    async def list_runs(
        self,
        experiment_id: str,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List runs in an experiment"""
        client = self._get_client()
        runs = client.search_runs(
            experiment_ids=[experiment_id],
            max_results=max_results,
            order_by=order_by,
        )

        result = []
        for run in runs:
            result.append({
                "run_id": run.info.run_id,
                "experiment_id": str(run.info.experiment_id),
                "run_name": run.info.run_name,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "artifact_uri": run.info.artifact_uri,
                "params": run.data.params,
                "metrics": run.data.metrics,
            })

        return result

    async def list_artifacts(
        self,
        run_id: str,
        artifact_path: str = "",
    ) -> List[Dict[str, Any]]:
        """List artifacts for a run"""
        client = self._get_client()
        artifacts = client.list_artifacts(run_id, artifact_path)

        return [
            {
                "path": art.path,
                "is_dir": art.is_dir,
                "file_size": art.file_size,
            }
            for art in artifacts
        ]

    async def download_artifacts(
        self,
        run_id: str,
        artifact_path: str,
        dst_path: str,
    ):
        """Download artifacts from a run"""
        client = self._get_client()
        client.download_artifacts(run_id, artifact_path, dst_path)


class MockMLflowClient:
    """
    Mock MLflow client for development/testing when MLflow is not available
    """

    def __init__(self):
        self._params: Dict[str, Dict[str, Any]] = {}
        self._metrics: Dict[str, Dict[str, List[float]]] = {}
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._experiments: Dict[str, Dict[str, Any]] = {}

    def log_param(self, run_id: str, key: str, value: Any):
        if run_id not in self._params:
            self._params[run_id] = {}
        self._params[run_id][key] = str(value)

    def log_params(self, run_id: str, params: Dict[str, Any]):
        if run_id not in self._params:
            self._params[run_id] = {}
        for key, value in params.items():
            self._params[run_id][key] = str(value)

    def log_metric(self, run_id: str, key: str, value: float, step=None):
        if run_id not in self._metrics:
            self._metrics[run_id] = {}
        if key not in self._metrics[run_id]:
            self._metrics[run_id][key] = []
        self._metrics[run_id][key].append(value)

    def log_metrics(self, run_id: str, metrics: Dict[str, float], step=None):
        for key, value in metrics.items():
            self.log_metric(run_id, key, value)

    def log_model(self, run_id: str, artifact_path: str, model_type="sklearn", **kwargs):
        logger.info(f"Mock: Logging model at {artifact_path} for run {run_id}")

    def log_artifact(self, run_id: str, local_path: str, artifact_path=None):
        logger.info(f"Mock: Logging artifact {local_path} for run {run_id}")

    def create_experiment(
        self,
        name: str,
        artifact_location=None,
        tags=None,
    ) -> Any:
        exp_id = f"exp_{len(self._experiments)}"
        self._experiments[exp_id] = {
            "name": name,
            "artifact_location": artifact_location,
            "tags": tags or {},
        }
        return type("obj", (object,), {"experiment_id": exp_id})

    def get_experiment_by_name(self, name: str):
        for exp in self._experiments.values():
            if exp["name"] == name:
                return type("obj", (object,), exp)
        return None

    def search_experiments(self):
        return [
            type("obj", (object,), {**exp, "experiment_id": exp_id, "lifecycle_stage": "active"})
            for exp_id, exp in self._experiments.items()
        ]

    def create_run(self, experiment_id, run_name, tags=None):
        run_id = f"run_{len(self._runs)}"
        self._runs[run_id] = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "run_name": run_name,
            "status": "running",
        }
        return type("obj", (object,), {"info": type("obj", (object,), {"run_id": run_id})})

    def get_run(self, run_id):
        run = self._runs.get(run_id)
        if run:
            return type("obj", (object,), {
                "info": type("obj", (object,), run),
                "data": type("obj", (object,), {
                    "params": self._params.get(run_id, {}),
                    "metrics": self._metrics.get(run_id, {}),
                    "tags": {},
                }),
            })
        raise ValueError(f"Run {run_id} not found")

    def search_runs(self, experiment_ids=None, max_results=100, order_by=None):
        return [
            type("obj", (object,), {"info": r, "data": type("obj", (object,), {"params": {}, "metrics": {}})})
            for r in self._runs.values()
        ]

    def list_artifacts(self, run_id, artifact_path=""):
        return []

    def download_artifacts(self, run_id, artifact_path, dst_path):
        logger.info(f"Mock: Downloading artifacts for {run_id}")

    def register_model(self, model_uri, name):
        return type("obj", (object,), {"version": 1, "name": name})

    def get_registered_model(self, name):
        return type("obj", (object,), {"name": name, "description": "", "tags": {}})

    def get_model_version(self, name, version):
        return type("obj", (object,), {"name": name, "version": version, "current_stage": "None", "run_id": None})

    def get_latest_versions(self, name, stages=None):
        return []

    def get_model_versions(self, name):
        return []

    def update_model_version(self, name, version, description=None):
        pass

    def transition_model_version_stage(self, name, version, stage, archive_existing_versions=False):
        pass

    def delete_registered_model(self, name):
        pass

    def delete_model_version(self, name, version):
        pass

    def search_registered_models(self, filter_string=None, max_results=100, order_by=None):
        return []

    def create_registered_model(self, name, tags=None, description=""):
        return type("obj", (object,), {"name": name, "tags": tags or {}, "description": description})

    def rename_registered_model(self, name, new_name):
        pass

    def set_model_version_tag(self, name, version, key, value):
        pass


# Singleton instance
_mlflow_client: Optional[MLflowClient] = None


def get_mlflow_client(tracking_uri: Optional[str] = None) -> MLflowClient:
    """Get or create MLflow client singleton"""
    global _mlflow_client
    if _mlflow_client is None:
        _mlflow_client = MLflowClient(tracking_uri)
    return _mlflow_client
