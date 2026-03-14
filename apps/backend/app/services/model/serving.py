"""
Model Serving Service

Business logic for deploying models as inference services using KServe.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from .registry import get_model_registry_service

logger = logging.getLogger(__name__)


class ModelServingService:
    """
    Service for managing model deployments with KServe
    """

    def __init__(self):
        self._registry = get_model_registry_service()
        # In production, this would interact with Kubernetes API
        self._deployments: Dict[str, Dict[str, Any]] = {}

    async def create_deployment(
        self,
        name: str,
        model_name: str,
        model_version: str,
        # Resource configuration
        replicas: int = 1,
        gpu_enabled: bool = False,
        gpu_type: Optional[str] = None,
        gpu_count: int = 1,
        cpu: str = "1",
        memory: str = "2Gi",
        # Traffic configuration
        endpoint: Optional[str] = None,
        traffic_percentage: int = 100,
        # Model configuration
        framework: str = "sklearn",
        # Advanced settings
        autoscaling_enabled: bool = False,
        autoscaling_min: int = 1,
        autoscaling_max: int = 3,
        # Metadata
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        owner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a new model deployment

        Args:
            name: Deployment name
            model_name: Registered model name
            model_version: Model version to deploy
            replicas: Number of replicas
            gpu_enabled: Whether GPU is enabled
            gpu_type: Type of GPU (e.g., nvidia.com/gpu, nvidia.com/a100)
            gpu_count: Number of GPUs per replica
            cpu: CPU request per replica
            memory: Memory request per replica
            endpoint: Custom endpoint name
            traffic_percentage: Traffic percentage for A/B testing
            framework: Model framework (sklearn, pytorch, tensorflow, xgboost, etc.)
            autoscaling_enabled: Enable HPA
            autoscaling_min: Min replicas for HPA
            autoscaling_max: Max replicas for HPA
            description: Deployment description
            tags: Deployment tags
            owner_id: Owner user ID

        Returns:
            Created deployment metadata
        """
        # Verify model exists
        try:
            await self._registry.get_model_version(model_name, model_version)
        except Exception as e:
            raise ValueError(f"Model version not found: {model_name}:{model_version}")

        deployment_id = str(uuid.uuid4())

        # Determine inference service name
        endpoint_name = endpoint or f"{model_name}-{model_version}"

        deployment = {
            "id": deployment_id,
            "name": name,
            "model_name": model_name,
            "model_version": model_version,
            "model_uri": f"models:/{model_name}/{model_version}",
            "framework": framework,
            "status": "deploying",
            # Resource configuration
            "replicas": replicas,
            "gpu_enabled": gpu_enabled,
            "gpu_type": gpu_type,
            "gpu_count": gpu_count,
            "resources": {
                "cpu": cpu,
                "memory": memory,
                "gpu": gpu_count if gpu_enabled else 0,
            },
            # Traffic configuration
            "endpoint": endpoint_name,
            "url": f"http://{endpoint_name}.one-data-studio.svc.cluster.local:8080",
            "traffic_percentage": traffic_percentage,
            # Autoscaling
            "autoscaling": {
                "enabled": autoscaling_enabled,
                "min_replicas": autoscaling_min,
                "max_replicas": autoscaling_max,
            },
            # Metadata
            "description": description,
            "tags": tags or {},
            "owner_id": owner_id,
            # Timestamps
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        self._deployments[deployment_id] = deployment

        # In production, create KServe InferenceService
        # await self._create_inference_service(deployment)

        logger.info(f"Created deployment: {name} (ID: {deployment_id})")

        return deployment

    async def list_deployments(
        self,
        model_name: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all deployments

        Args:
            model_name: Filter by model name
            status: Filter by status
            owner_id: Filter by owner

        Returns:
            List of deployments
        """
        deployments = list(self._deployments.values())

        if model_name:
            deployments = [d for d in deployments if d["model_name"] == model_name]

        if status:
            deployments = [d for d in deployments if d["status"] == status]

        if owner_id:
            deployments = [d for d in deployments if d["owner_id"] == owner_id]

        return sorted(deployments, key=lambda x: x["created_at"], reverse=True)

    async def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get deployment by ID

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment metadata
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Get model details
        try:
            model = await self._registry.get_model_version(
                deployment["model_name"],
                deployment["model_version"],
            )
            deployment["model_details"] = model
        except Exception:
            pass

        return deployment

    async def update_deployment(
        self,
        deployment_id: str,
        replicas: Optional[int] = None,
        traffic_percentage: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update deployment configuration

        Args:
            deployment_id: Deployment ID
            replicas: New replica count
            traffic_percentage: New traffic percentage
            description: New description

        Returns:
            Updated deployment
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        if replicas is not None:
            deployment["replicas"] = replicas
            # In production, update deployment replicas
            # await self._update_deployment_replicas(deployment_id, replicas)

        if traffic_percentage is not None:
            deployment["traffic_percentage"] = traffic_percentage

        if description is not None:
            deployment["description"] = description

        deployment["updated_at"] = datetime.utcnow().isoformat()

        return deployment

    async def delete_deployment(self, deployment_id: str) -> bool:
        """
        Delete a deployment

        Args:
            deployment_id: Deployment ID

        Returns:
            True if deleted successfully
        """
        if deployment_id not in self._deployments:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # In production, delete KServe InferenceService
        # await self._delete_inference_service(deployment_id)

        del self._deployments[deployment_id]
        logger.info(f"Deleted deployment: {deployment_id}")

        return True

    async def scale_deployment(
        self,
        deployment_id: str,
        replicas: int,
    ) -> bool:
        """
        Scale a deployment

        Args:
            deployment_id: Deployment ID
            replicas: Target replica count

        Returns:
            True if scaled successfully
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        deployment["replicas"] = replicas
        deployment["updated_at"] = datetime.utcnow().isoformat()

        # In production, scale Kubernetes Deployment
        logger.info(f"Scaled deployment {deployment_id} to {replicas} replicas")

        return True

    async def rollback_deployment(
        self,
        deployment_id: str,
        target_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Rollback a deployment to a previous version

        Args:
            deployment_id: Deployment ID
            target_version: Target version (None for previous)

        Returns:
            Updated deployment
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # Get model versions to find previous
        model = await self._registry.get_model(deployment["model_name"])

        current_version = int(deployment["model_version"])
        target_version_int = current_version - 1

        if target_version:
            target_version_int = int(target_version)

        # Find the target version
        target_version_str = None
        for v in model["versions"]:
            if int(v["version"]) == target_version_int:
                target_version_str = v["version"]
                break

        if not target_version_str:
            raise ValueError(f"Target version not found: {target_version_int}")

        # Update deployment
        deployment["model_version"] = target_version_str
        deployment["model_uri"] = f"models:/{deployment['model_name']}/{target_version_str}"
        deployment["updated_at"] = datetime.utcnow().isoformat()

        logger.info(f"Rolled back deployment {deployment_id} to version {target_version_str}")

        return deployment

    async def get_deployment_metrics(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """
        Get deployment metrics

        Args:
            deployment_id: Deployment ID

        Returns:
            Deployment metrics (requests, latency, error rate, etc.)
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        # In production, query Prometheus metrics from KServe
        # For now, return mock data
        return {
            "deployment_id": deployment_id,
            "status": deployment["status"],
            "replicas": deployment["replicas"],
            "requests_total": 0,
            "requests_per_second": 0,
            "avg_latency_ms": 0,
            "p95_latency_ms": 0,
            "p99_latency_ms": 0,
            "error_rate": 0.0,
            "cpu_usage_percent": 0,
            "memory_usage_mb": 0,
            "gpu_usage_percent": 0 if deployment["gpu_enabled"] else None,
        }

    async def set_deployment_status(
        self,
        deployment_id: str,
        status: str,
    ) -> bool:
        """
        Set deployment status

        Args:
            deployment_id: Deployment ID
            status: Target status (deploying, running, failed, stopped)

        Returns:
            True if status updated
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return False

        deployment["status"] = status
        deployment["updated_at"] = datetime.utcnow().isoformat()

        return True

    async def create_canary_deployment(
        self,
        name: str,
        model_name: str,
        current_version: str,
        new_version: str,
        canary_traffic_percentage: int = 10,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a canary deployment with traffic splitting

        Args:
            name: Deployment name
            model_name: Model name
            current_version: Current stable version
            new_version: New canary version
            canary_traffic_percentage: Traffic for canary (0-100)
            **kwargs: Additional deployment config

        Returns:
            Canary deployment metadata
        """
        # Create primary deployment (if not exists)
        primary_deployment = await self.create_deployment(
            name=f"{name}-primary",
            model_name=model_name,
            model_version=current_version,
            traffic_percentage=100 - canary_traffic_percentage,
            **kwargs,
        )

        # Create canary deployment
        canary_deployment = await self.create_deployment(
            name=f"{name}-canary",
            model_name=model_name,
            model_version=new_version,
            traffic_percentage=canary_traffic_percentage,
            **kwargs,
        )

        return {
            "name": name,
            "type": "canary",
            "primary_deployment": primary_deployment,
            "canary_deployment": canary_deployment,
            "canary_traffic_percentage": canary_traffic_percentage,
            "endpoint": primary_deployment["endpoint"],
        }

    async def promote_canary(
        self,
        deployment_id: str,
    ) -> Dict[str, Any]:
        """
        Promote canary deployment to primary

        Args:
            deployment_id: Canary deployment ID

        Returns:
            Updated deployment
        """
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        if deployment.get("type") != "canary":
            raise ValueError("Deployment is not a canary deployment")

        # Get versions
        canary_deployment_id = deployment.get("canary_deployment", {}).get("id")
        canary = self._deployments.get(canary_deployment_id)

        # Update primary to canary version
        primary_deployment_id = deployment.get("primary_deployment", {}).get("id")
        primary = self._deployments.get(primary_deployment_id)

        if primary and canary:
            await self.update_deployment(
                primary_deployment_id,
                replicas=primary["replicas"],
                traffic_percentage=100,
            )

            # Delete canary
            await self.delete_deployment(canary_deployment_id)

        return await self.get_deployment(primary_deployment_id)


# Singleton instance
_model_serving_service: Optional[ModelServingService] = None


def get_model_serving_service() -> ModelServingService:
    """Get or create model serving service singleton"""
    global _model_serving_service
    if _model_serving_service is None:
        _model_serving_service = ModelServingService()
    return _model_serving_service
