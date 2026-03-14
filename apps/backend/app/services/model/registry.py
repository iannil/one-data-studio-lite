"""
Model Registry Service

Business logic for model registration, versioning, and stage management.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .mlflow_client import get_mlflow_client

logger = logging.getLogger(__name__)


class ModelRegistryService:
    """
    Service for managing MLflow model registry
    """

    def __init__(self):
        self._mlflow = get_mlflow_client()

    async def register_model(
        self,
        name: str,
        run_id: str,
        artifact_path: str,
        model_type: str = "sklearn",
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Register a model from a run

        Args:
            name: Model name
            run_id: Run ID that produced the model
            artifact_path: Path to model artifact in run
            model_type: Model framework type
            description: Optional description
            tags: Optional tags

        Returns:
            Created model version info
        """
        try:
            import mlflow

            # Create model version in MLflow Model Registry
            model_uri = f"runs:/{run_id}/{artifact_path}"

            # Register the model
            model_version = mlflow.register_model(
                model_uri=model_uri,
                name=name,
            )

            # Add description and tags
            if description:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                client.update_model_version(
                    name=name,
                    version=model_version.version,
                    description=description,
                )

            if tags:
                client.set_model_version_tag(
                    name=name,
                    version=model_version.version,
                    key=next(iter(tags)),  # MLflow only supports one tag at a time
                    value=next(iter(tags.values())),
                )

            logger.info(f"Registered model {name} version {model_version.version}")

            return {
                "name": name,
                "version": model_version.version,
                "run_id": run_id,
                "artifact_path": artifact_path,
                "model_type": model_type,
                "description": description,
                "current_stage": "None",
                "created_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error registering model: {e}")
            raise

    async def list_models(
        self,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all registered models

        Args:
            search: Optional search term for name

        Returns:
            List of model metadata with latest version info
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            models = client.search_registered_models()

            result = []
            for model in models:
                model_name = model.name

                if search and search.lower() not in model_name.lower():
                    continue

                # Get latest version info
                versions = client.get_latest_versions(
                    name=model_name,
                    stages=["Staging", "Production", "Archived", "None"],
                )

                latest_version = None
                production_version = None
                staging_version = None

                for v in versions:
                    if v.current_stage == "Production":
                        production_version = v.version
                    if v.current_stage == "Staging":
                        staging_version = v.version
                    if v.current_stage == "None" and not latest_version:
                        latest_version = v.version

                result.append({
                    "name": model_name,
                    "description": model.description or "",
                    "latest_version": latest_version,
                    "production_version": production_version,
                    "staging_version": staging_version,
                    "tags": model.tags or {},
                    "creation_time": model.creation_timestamp,
                })

            return result
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def get_model(self, name: str) -> Dict[str, Any]:
        """
        Get model by name

        Args:
            name: Model name

        Returns:
            Model metadata with all versions
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            model = client.get_registered_model(name)

            # Get all versions
            versions = client.get_model_versions(name=name)

            version_list = []
            for v in versions:
                run = client.get_run(v.run_id) if v.run_id else None

                version_list.append({
                    "version": v.version,
                    "run_id": v.run_id,
                    "run_name": run.info.run_name if run else None,
                    "current_stage": v.current_stage,
                    "status": v.status,
                    "description": v.description or "",
                    "creation_time": v.creation_timestamp,
                    "last_updated": v.last_updated_timestamp,
                    "source": v.source,
                })

            return {
                "name": model.name,
                "description": model.description or "",
                "tags": model.tags or {},
                "creation_time": model.creation_timestamp,
                "last_updated": model.last_updated_timestamp,
                "versions": sorted(version_list, key=lambda x: int(x["version"]), reverse=True),
            }
        except Exception as e:
            logger.error(f"Error getting model {name}: {e}")
            raise

    async def get_model_version(
        self,
        name: str,
        version: str,
    ) -> Dict[str, Any]:
        """
        Get specific model version

        Args:
            name: Model name
            version: Version number

        Returns:
            Model version metadata with run info
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            model_version = client.get_model_version(name, version)
            run = client.get_run(model_version.run_id) if model_version.run_id else None

            # Get model artifacts
            artifacts = self._mlflow.list_artifacts(model_version.run_id) if model_version.run_id else []

            return {
                "name": name,
                "version": model_version.version,
                "run_id": model_version.run_id,
                "run_name": run.info.run_name if run else None,
                "current_stage": model_version.current_stage,
                "status": model_version.status,
                "description": model_version.description or "",
                "source": model_version.source,
                "creation_time": model_version.creation_timestamp,
                "last_updated": model_version.last_updated_timestamp,
                "tags": model_version.tags or {},
                "artifacts": artifacts,
                "run_params": run.data.params if run else {},
                "run_metrics": run.data.metrics if run else {},
            }
        except Exception as e:
            logger.error(f"Error getting model version {name}:{version}: {e}")
            raise

    async def update_model_version(
        self,
        name: str,
        version: str,
        description: Optional[str] = None,
    ) -> bool:
        """
        Update model version description

        Args:
            name: Model name
            version: Version number
            description: New description

        Returns:
            True if updated successfully
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            if description:
                client.update_model_version(
                    name=name,
                    version=version,
                    description=description,
                )

            return True
        except Exception as e:
            logger.error(f"Error updating model version {name}:{version}: {e}")
            return False

    async def transition_model_stage(
        self,
        name: str,
        version: str,
        stage: str,
        archive_existing_versions: bool = False,
    ) -> bool:
        """
        Transition model version to a new stage

        Args:
            name: Model name
            version: Version number
            stage: Target stage (Staging, Production, Archived, None)
            archive_existing_versions: Whether to archive existing versions in stage

        Returns:
            True if transitioned successfully
        """
        try:
            from mlflow.tracking import MlflowClient
            from mlflow.entities import LifecycleStage

            client = MlflowClient()

            stage_map = {
                "Staging": "Staging",
                "Production": "Production",
                "Archived": "Archived",
                "None": "None",
            }

            client.transition_model_version_stage(
                name=name,
                version=version,
                stage=stage_map.get(stage, "None"),
                archive_existing_versions=archive_existing_versions,
            )

            logger.info(f"Transitioned {name}:{version} to {stage}")
            return True
        except Exception as e:
            logger.error(f"Error transitioning model stage: {e}")
            return False

    async def delete_model(self, name: str) -> bool:
        """
        Delete a model (all versions)

        Args:
            name: Model name

        Returns:
            True if deleted successfully
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            client.delete_registered_model(name)
            logger.info(f"Deleted model: {name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting model {name}: {e}")
            return False

    async def delete_model_version(
        self,
        name: str,
        version: str,
    ) -> bool:
        """
        Delete a specific model version

        Args:
            name: Model name
            version: Version number

        Returns:
            True if deleted successfully
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            client.delete_model_version(name, version)
            logger.info(f"Deleted model version: {name}:{version}")
            return True
        except Exception as e:
            logger.error(f"Error deleting model version {name}:{version}: {e}")
            return False

    async def get_model_stage_history(
        self,
        name: str,
        version: str,
    ) -> List[Dict[str, Any]]:
        """
        Get stage transition history for a model version

        Args:
            name: Model name
            version: Version number

        Returns:
            List of stage transitions
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            model_version = client.get_model_version(name, version)

            history = []
            # MLflow doesn't provide full history in the API
            # Return current state as a single entry
            history.append({
                "name": name,
                "version": version,
                "stage": model_version.current_stage,
                "timestamp": model_version.last_updated_timestamp,
            })

            return history
        except Exception as e:
            logger.error(f"Error getting model history {name}:{version}: {e}")
            return []

    async def create_registered_model(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new registered model (without version)

        Args:
            name: Model name
            description: Optional description
            tags: Optional tags

        Returns:
            Created model metadata
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            model = client.create_registered_model(
                name=name,
                tags=list(tags.items()) if tags else None,
                description=description,
            )

            return {
                "name": model.name,
                "description": model.description or "",
                "tags": model.tags or {},
                "creation_time": model.creation_timestamp,
            }
        except Exception as e:
            logger.error(f"Error creating registered model {name}: {e}")
            raise

    async def rename_model(
        self,
        name: str,
        new_name: str,
    ) -> bool:
        """
        Rename a registered model

        Args:
            name: Current model name
            new_name: New model name

        Returns:
            True if renamed successfully
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            client.rename_registered_model(name, new_name)
            logger.info(f"Renamed model {name} to {new_name}")
            return True
        except Exception as e:
            logger.error(f"Error renaming model {name}: {e}")
            return False

    async def get_model_uri(
        self,
        name: str,
        version: str,
    ) -> str:
        """
        Get model URI for loading

        Args:
            name: Model name
            version: Version number

        Returns:
            Model URI for mlflow.<framework>.load_model()
        """
        return f"models:/{name}/{version}"

    async def search_models(
        self,
        filter_string: Optional[str] = None,
        max_results: int = 100,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search registered models

        Args:
            filter_string: Filter string (e.g., "name like 'my%'")
            max_results: Maximum number of results
            order_by: Order by clauses

        Returns:
            List of matching models
        """
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()

            models = client.search_registered_models(
                filter_string=filter_string,
                max_results=max_results,
                order_by=order_by,
            )

            return [
                {
                    "name": m.name,
                    "description": m.description or "",
                    "tags": m.tags or {},
                    "creation_time": m.creation_timestamp,
                }
                for m in models
            ]
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []


# Singleton instance
_model_registry_service: Optional[ModelRegistryService] = None


def get_model_registry_service() -> ModelRegistryService:
    """Get or create model registry service singleton"""
    global _model_registry_service
    if _model_registry_service is None:
        _model_registry_service = ModelRegistryService()
    return _model_registry_service
