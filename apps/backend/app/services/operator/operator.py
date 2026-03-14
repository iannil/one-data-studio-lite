"""
Kubernetes Operator Service

Provides Custom Resource Definitions (CRDs) and operator implementations
for managing platform resources on Kubernetes.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import asyncio
import yaml

logger = logging.getLogger(__name__)


class ResourceState(str, Enum):
    """Resource state"""

    PENDING = "Pending"
    CREATING = "Creating"
    RUNNING = "Running"
    UPDATING = "Updating"
    DELETING = "Deleting"
    COMPLETED = "Completed"
    FAILED = "Failed"
    UNKNOWN = "Unknown"


class ConditionType(str, Enum):
    """Condition types for resources"""

    READY = "Ready"
    RESOURCES_AVAILABLE = "ResourcesAvailable"
    PROVISIONED = "Provisioned"
    RUNNING = "Running"
    FAILED = "Failed"
    TERMINATING = "Terminating"


@dataclass
class Condition:
    """Resource condition"""

    type: ConditionType
    status: str  # True, False, Unknown
    reason: Optional[str] = None
    message: Optional[str] = None
    last_transition_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Kubernetes condition format"""
        return {
            "type": self.type.value,
            "status": self.status,
            "reason": self.reason,
            "message": self.message,
            "lastTransitionTime": self.last_transition_time.isoformat() if self.last_transition_time else None,
            "lastUpdateTime": self.last_update_time.isoformat() if self.last_update_time else None,
        }


@dataclass
class ResourceStatus:
    """Resource status"""

    phase: ResourceState
    conditions: List[Condition] = field(default_factory=list)
    observed_generation: int = 0
    replicas: int = 0
    ready_replicas: int = 0
    available_replicas: int = 0
    updated_replicas: int = 0

    # URLs
    service_url: Optional[str] = None
    jupyter_url: Optional[str] = None
    tensorboard_url: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Error info
    error_message: Optional[str] = None
    error_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "phase": self.phase.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "observedGeneration": self.observed_generation,
            "replicas": self.replicas,
            "readyReplicas": self.ready_replicas,
            "availableReplicas": self.available_replicas,
            "updatedReplicas": self.updated_replicas,
            "serviceURL": self.service_url,
            "jupyterURL": self.jupyter_url,
            "tensorboardURL": self.tensorboard_url,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "errorMessage": self.error_message,
            "errorReason": self.error_reason,
        }


# ============================================================================
# CRD Definitions
# ============================================================================

class CRDDefinition:
    """Custom Resource Definition builder"""

    @staticmethod
    def notebook_crd() -> Dict[str, Any]:
        """Notebook CRD definition"""
        return {
            "apiVersion": "apiextensions.k8s.io/v1",
            "kind": "CustomResourceDefinition",
            "metadata": {
                "name": "notebooks.studio.one-data.io",
            },
            "spec": {
                "group": "studio.one-data.io",
                "names": {
                    "kind": "Notebook",
                    "plural": "notebooks",
                    "singular": "notebook",
                    "shortNames": ["nb"],
                },
                "scope": "Namespaced",
                "versions": [
                    {
                        "name": "v1alpha1",
                        "served": True,
                        "storage": True,
                        "schema": {
                            "openAPIV3Schema": {
                                "type": "object",
                                "properties": {
                                    "spec": {
                                        "type": "object",
                                        "properties": {
                                            "image": {"type": "string"},
                                            "cpu": {"type": "string"},
                                            "memory": {"type": "string"},
                                            "gpu": {"type": "integer"},
                                            "storage": {"type": "string"},
                                            "ports": {"type": "array", "items": {"type": "integer"}},
                                            "env": {"type": "object"},
                                            "workspace": {"type": "string"},
                                            "timeout": {"type": "integer"},
                                            "auto_stop": {"type": "boolean"},
                                        },
                                        "required": ["image"],
                                    },
                                },
                            },
                        },
                        "subresources": {
                            "status": {},
                            "scale": {"specReplicasPath": ".spec.replicas"},
                        },
                    }
                ],
            },
        }

    @staticmethod
    def training_job_crd() -> Dict[str, Any]:
        """TrainingJob CRD definition"""
        return {
            "apiVersion": "apiextensions.k8s.io/v1",
            "kind": "CustomResourceDefinition",
            "metadata": {
                "name": "trainingjobs.studio.one-data.io",
            },
            "spec": {
                "group": "studio.one-data.io",
                "names": {
                    "kind": "TrainingJob",
                    "plural": "trainingjobs",
                    "singular": "trainingjob",
                    "shortNames": ["tj", "train"],
                },
                "scope": "Namespaced",
                "versions": [
                    {
                        "name": "v1alpha1",
                        "served": True,
                        "storage": True,
                        "schema": {
                            "openAPIV3Schema": {
                                "type": "object",
                                "properties": {
                                    "spec": {
                                        "type": "object",
                                        "properties": {
                                            "backend": {"type": "string"},
                                            "strategy": {"type": "string"},
                                            "entry_point": {"type": "string"},
                                            "entry_point_args": {"type": "array", "items": {"type": "string"}},
                                            "num_nodes": {"type": "integer"},
                                            "num_processes_per_node": {"type": "integer"},
                                            "model_uri": {"type": "string"},
                                            "output_uri": {"type": "string"},
                                            "tensorboard": {"type": "boolean"},
                                            "docker_image": {"type": "string"},
                                            "resources": {
                                                "type": "object",
                                                "properties": {
                                                    "cpu": {"type": "string"},
                                                    "memory": {"type": "string"},
                                                    "gpu": {"type": "integer"},
                                                    "gpu_type": {"type": "string"},
                                                },
                                            },
                                        },
                                        "required": ["backend", "strategy", "entry_point"],
                                    },
                                },
                            },
                        },
                        "subresources": {
                            "status": {},
                        },
                    }
                ],
            },
        }

    @staticmethod
    def inference_service_crd() -> Dict[str, Any]:
        """InferenceService CRD definition"""
        return {
            "apiVersion": "apiextensions.k8s.io/v1",
            "kind": "CustomResourceDefinition",
            "metadata": {
                "name": "inferenceservices.studio.one-data.io",
            },
            "spec": {
                "group": "studio.one-data.io",
                "names": {
                    "kind": "InferenceService",
                    "plural": "inferenceservices",
                    "singular": "inferenceservice",
                    "shortNames": ["isvc", "inference"],
                },
                "scope": "Namespaced",
                "versions": [
                    {
                        "name": "v1alpha1",
                        "served": True,
                        "storage": True,
                        "schema": {
                            "openAPIV3Schema": {
                                "type": "object",
                                "properties": {
                                    "spec": {
                                        "type": "object",
                                        "properties": {
                                            "model_uri": {"type": "string"},
                                            "predictor_type": {"type": "string"},
                                            "framework": {"type": "string"},
                                            "replicas": {"type": "integer"},
                                            "autoscaling_enabled": {"type": "boolean"},
                                            "min_replicas": {"type": "integer"},
                                            "max_replicas": {"type": "integer"},
                                            "resources": {
                                                "type": "object",
                                                "properties": {
                                                    "cpu": {"type": "string"},
                                                    "memory": {"type": "string"},
                                                    "gpu": {"type": "integer"},
                                                },
                                            },
                                            "deployment_mode": {"type": "string"},
                                        },
                                        "required": ["model_uri"],
                                    },
                                },
                            },
                        },
                        "subresources": {
                            "status": {},
                            "scale": {"specReplicasPath": ".spec.replicas"},
                        },
                    }
                ],
            },
        }


# ============================================================================
# Operator Base Classes
# ============================================================================

class OperatorController:
    """Base operator controller"""

    def __init__(self, namespace: str = "default"):
        """
        Initialize operator controller

        Args:
            namespace: Kubernetes namespace
        """
        self.namespace = namespace
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._watchers: Dict[str, asyncio.Task] = {}

    async def start(self):
        """Start the operator controller"""
        logger.info(f"Starting operator controller in namespace: {self.namespace}")
        # Start reconciliation loop
        await self._reconcile_loop()

    async def stop(self):
        """Stop the operator controller"""
        logger.info("Stopping operator controller")
        # Cancel all watchers
        for task in self._watchers.values():
            task.cancel()
        self._watchers.clear()

    async def _reconcile_loop(self):
        """Main reconciliation loop"""
        while True:
            try:
                await self._reconcile()
                await asyncio.sleep(5)  # Reconcile every 5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")
                await asyncio.sleep(10)

    async def _reconcile(self):
        """Reconcile resources"""
        # Override in subclasses
        pass

    def _set_condition(
        self,
        resource: Dict[str, Any],
        condition_type: ConditionType,
        status: str,
        reason: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Set a condition on a resource"""
        conditions = resource.get("status", {}).get("conditions", [])

        # Find existing condition
        existing = None
        for i, cond in enumerate(conditions):
            if cond.get("type") == condition_type.value:
                existing = i
                break

        new_condition = {
            "type": condition_type.value,
            "status": status,
            "reason": reason,
            "message": message,
            "lastTransitionTime": datetime.utcnow().isoformat() + "Z",
            "lastUpdateTime": datetime.utcnow().isoformat() + "Z",
        }

        if existing is not None:
            # Only update if something changed
            old_cond = conditions[existing]
            if (old_cond.get("status") != status or
                old_cond.get("message") != message):
                new_condition["lastTransitionTime"] = old_cond.get("lastTransitionTime", new_condition["lastTransitionTime"])
                conditions[existing] = new_condition
        else:
            conditions.append(new_condition)

    def _update_status(self, resource: Dict[str, Any], status: Dict[str, Any]):
        """Update resource status"""
        if "status" not in resource:
            resource["status"] = {}
        resource["status"].update(status)


class NotebookOperator(OperatorController):
    """
    Operator for managing Notebook resources

    Creates and manages Jupyter notebook servers.
    """

    async def create_notebook(
        self,
        name: str,
        spec: Dict[str, Any],
        owner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a notebook server

        Args:
            name: Notebook name
            spec: Notebook specification
            owner_id: Owner user ID

        Returns:
            Created notebook resource
        """
        resource = {
            "apiVersion": "studio.one-data.io/v1alpha1",
            "kind": "Notebook",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "app": "notebook",
                    "notebook": name,
                },
                "annotations": {
                    "ownerId": str(owner_id) if owner_id else None,
                },
            },
            "spec": spec,
            "status": {
                "phase": ResourceState.PENDING.value,
                "conditions": [],
                "replicas": 0,
                "readyReplicas": 0,
            },
        }

        self._resources[f"{self.namespace}/{name}"] = resource

        # Simulate creation
        await self._reconcile_notebook(name, resource)

        return resource

    async def _reconcile(self):
        """Reconcile all notebooks"""
        for key, resource in list(self._resources.items()):
            if resource.get("kind") == "Notebook":
                name = resource["metadata"]["name"]
                await self._reconcile_notebook(name, resource)

    async def _reconcile_notebook(
        self,
        name: str,
        resource: Dict[str, Any],
    ):
        """Reconcile a notebook resource"""
        status = resource.get("status", {})
        phase = status.get("phase", ResourceState.PENDING.value)

        if phase == ResourceState.PENDING.value:
            # Create notebook
            await self._create_notebook_deployment(resource)
            self._update_status(resource, {
                "phase": ResourceState.CREATING.value,
                "observedGeneration": status.get("observedGeneration", 0) + 1,
            })

        elif phase == ResourceState.CREATING.value:
            # Check if notebook is ready
            if await self._check_notebook_ready(name):
                self._update_status(resource, {
                    "phase": ResourceState.RUNNING.value,
                    "readyReplicas": 1,
                    "replicas": 1,
                    "serviceURL": f"http://{name}.{self.namespace}.svc.cluster.local:8888",
                    "jupyterURL": f"http://{name}.{self.namespace}.svc.cluster.local:8888",
                    "startedAt": datetime.utcnow().isoformat() + "Z",
                })

                self._set_condition(
                    resource,
                    ConditionType.READY,
                    "True",
                    "NotebookReady",
                    "Notebook server is ready",
                )

    async def _create_notebook_deployment(self, resource: Dict[str, Any]):
        """Create Kubernetes deployment for notebook"""
        spec = resource.get("spec", {})
        name = resource["metadata"]["name"]

        # In production, create actual K8s resources
        logger.info(f"Creating notebook deployment: {name}")

    async def _check_notebook_ready(self, name: str) -> bool:
        """Check if notebook is ready"""
        # In production, check actual pod status
        await asyncio.sleep(0.1)
        return True

    async def delete_notebook(self, name: str) -> bool:
        """Delete a notebook"""
        key = f"{self.namespace}/{name}"
        if key in self._resources:
            del self._resources[key]
            logger.info(f"Deleted notebook: {name}")
            return True
        return False


class TrainingJobOperator(OperatorController):
    """
    Operator for managing TrainingJob resources

    Creates and manages distributed training jobs.
    """

    async def create_training_job(
        self,
        name: str,
        spec: Dict[str, Any],
        owner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a training job"""
        resource = {
            "apiVersion": "studio.one-data.io/v1alpha1",
            "kind": "TrainingJob",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "app": "training",
                    "training": name,
                },
            },
            "spec": spec,
            "status": {
                "phase": ResourceState.PENDING.value,
                "conditions": [],
            },
        }

        self._resources[f"{self.namespace}/{name}"] = resource
        await self._reconcile_training_job(name, resource)

        return resource

    async def _reconcile(self):
        """Reconcile all training jobs"""
        for key, resource in list(self._resources.items()):
            if resource.get("kind") == "TrainingJob":
                name = resource["metadata"]["name"]
                await self._reconcile_training_job(name, resource)

    async def _reconcile_training_job(
        self,
        name: str,
        resource: Dict[str, Any],
    ):
        """Reconcile a training job"""
        status = resource.get("status", {})
        phase = status.get("phase", ResourceState.PENDING.value)

        if phase == ResourceState.PENDING.value:
            # Submit training job
            await self._submit_training_job(resource)
            self._update_status(resource, {
                "phase": ResourceState.CREATING.value,
                "startedAt": datetime.utcnow().isoformat() + "Z",
            })

        elif phase == ResourceState.CREATING.value:
            if await self._check_training_job_started(name):
                self._update_status(resource, {
                    "phase": ResourceState.RUNNING.value,
                })

    async def _submit_training_job(self, resource: Dict[str, Any]):
        """Submit training job to Kubernetes"""
        spec = resource.get("spec", {})
        backend = spec.get("backend")
        strategy = spec.get("strategy")

        logger.info(f"Submitting {backend} training job with {strategy} strategy")

    async def _check_training_job_started(self, name: str) -> bool:
        """Check if training job has started"""
        await asyncio.sleep(0.1)
        return True


class InferenceServiceOperator(OperatorController):
    """
    Operator for managing InferenceService resources

    Creates and manages model inference services.
    """

    async def create_inference_service(
        self,
        name: str,
        spec: Dict[str, Any],
        owner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create an inference service"""
        resource = {
            "apiVersion": "studio.one-data.io/v1alpha1",
            "kind": "InferenceService",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "app": "inference",
                    "inference": name,
                },
            },
            "spec": spec,
            "status": {
                "phase": ResourceState.PENDING.value,
                "conditions": [],
                "replicas": 0,
                "readyReplicas": 0,
            },
        }

        self._resources[f"{self.namespace}/{name}"] = resource
        await self._reconcile_inference_service(name, resource)

        return resource

    async def _reconcile(self):
        """Reconcile all inference services"""
        for key, resource in list(self._resources.items()):
            if resource.get("kind") == "InferenceService":
                name = resource["metadata"]["name"]
                await self._reconcile_inference_service(name, resource)

    async def _reconcile_inference_service(
        self,
        name: str,
        resource: Dict[str, Any],
    ):
        """Reconcile an inference service"""
        status = resource.get("status", {})
        phase = status.get("phase", ResourceState.PENDING.value)

        if phase == ResourceState.PENDING.value:
            await self._deploy_inference_service(resource)
            self._update_status(resource, {
                "phase": ResourceState.CREATING.value,
            })

        elif phase == ResourceState.CREATING.value:
            if await self._check_inference_service_ready(name):
                spec = resource.get("spec", {})
                replicas = spec.get("replicas", 1)
                self._update_status(resource, {
                    "phase": ResourceState.RUNNING.value,
                    "replicas": replicas,
                    "readyReplicas": replicas,
                    "serviceURL": f"http://{name}.{self.namespace}.svc.cluster.local:8080",
                })

    async def _deploy_inference_service(self, resource: Dict[str, Any]):
        """Deploy inference service"""
        spec = resource.get("spec", {})
        predictor_type = spec.get("predictor_type")

        logger.info(f"Deploying inference service with {predictor_type} predictor")

    async def _check_inference_service_ready(self, name: str) -> bool:
        """Check if inference service is ready"""
        await asyncio.sleep(0.1)
        return True


# ============================================================================
# Operator Manager
# ============================================================================

class OperatorManager:
    """
    Manager for all platform operators

    Manages Notebook, TrainingJob, and InferenceService operators.
    """

    def __init__(self, namespace: str = "default"):
        """
        Initialize operator manager

        Args:
            namespace: Kubernetes namespace
        """
        self.namespace = namespace
        self.notebook_operator = NotebookOperator(namespace)
        self.training_operator = TrainingJobOperator(namespace)
        self.inference_operator = InferenceServiceOperator(namespace)

    async def start_all(self):
        """Start all operators"""
        logger.info("Starting all operators")

        # Start each operator in its own task
        tasks = [
            asyncio.create_task(self.notebook_operator.start()),
            asyncio.create_task(self.training_operator.start()),
            asyncio.create_task(self.inference_operator.start()),
        ]

        self._operator_tasks = tasks

    async def stop_all(self):
        """Stop all operators"""
        logger.info("Stopping all operators")
        await self.notebook_operator.stop()
        await self.training_operator.stop()
        await self.inference_operator.stop()

    async def install_crds(self) -> Dict[str, Any]:
        """
        Install all CRDs

        Returns:
            Installation results
        """
        results = {}

        crds = [
            ("notebooks", CRDDefinition.notebook_crd()),
            ("trainingjobs", CRDDefinition.training_job_crd()),
            ("inferenceservices", CRDDefinition.inference_service_crd()),
        ]

        for name, crd in crds:
            # In production, apply CRD to Kubernetes
            logger.info(f"Installing CRD: {name}")
            results[name] = {"status": "installed", "crd": crd}

        return results

    # Notebook operations
    async def create_notebook(self, name: str, spec: Dict[str, Any], owner_id: Optional[int] = None):
        return await self.notebook_operator.create_notebook(name, spec, owner_id)

    async def delete_notebook(self, name: str):
        return await self.notebook_operator.delete_notebook(name)

    # Training job operations
    async def create_training_job(self, name: str, spec: Dict[str, Any], owner_id: Optional[int] = None):
        return await self.training_operator.create_training_job(name, spec, owner_id)

    async def delete_training_job(self, name: str):
        if f"{self.namespace}/{name}" in self.training_operator._resources:
            del self.training_operator._resources[f"{self.namespace}/{name}"]
            return True
        return False

    # Inference service operations
    async def create_inference_service(self, name: str, spec: Dict[str, Any], owner_id: Optional[int] = None):
        return await self.inference_operator.create_inference_service(name, spec, owner_id)

    async def delete_inference_service(self, name: str):
        if f"{self.namespace}/{name}" in self.inference_operator._resources:
            del self.inference_operator._resources[f"{self.namespace}/{name}"]
            return True
        return False

    # Get all resources
    def list_notebooks(self) -> List[Dict[str, Any]]:
        return [r for r in self.notebook_operator._resources.values() if r.get("kind") == "Notebook"]

    def list_training_jobs(self) -> List[Dict[str, Any]]:
        return [r for r in self.training_operator._resources.values() if r.get("kind") == "TrainingJob"]

    def list_inference_services(self) -> List[Dict[str, Any]]:
        return [r for r in self.inference_operator._resources.values() if r.get("kind") == "InferenceService"]


# Singleton instance
_operator_manager: Optional[OperatorManager] = None


def get_operator_manager(namespace: str = "default") -> OperatorManager:
    """Get or create operator manager singleton"""
    global _operator_manager
    if _operator_manager is None or _operator_manager.namespace != namespace:
        _operator_manager = OperatorManager(namespace)
    return _operator_manager
