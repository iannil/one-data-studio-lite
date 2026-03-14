"""
Argo Workflow Service

Provides integration with Argo Workflows for orchestrating
complex workflows on Kubernetes.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)


class WorkflowPhase(str, Enum):
    """Argo workflow phases"""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    ERROR = "Error"
    Skipped = "Skipped"


class NodePhase(str, Enum):
    """Argo workflow node phases"""

    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    FAILED = "Failed"
    ERROR = "Error"
    Skipped = "Skipped"
    Omitted = "Omitted"


class ArtifactLocation(str, Enum):
    """Artifact storage locations"""

    S3 = "s3"
    GCS = "gcs"
    GIT = "git"
    HTTP = "http"
    RAW = "raw"
    MEMORY = "memory"


@dataclass
class Artifact:
    """Workflow artifact definition"""

    name: str
    path: str
    location_type: ArtifactLocation
    location: Optional[str] = None
    from_: Optional[str] = None  # Expression to generate artifact
    archive: Optional[Dict[str, Any]] = None
    mode: int = 0o644

    def to_argo_spec(self) -> Dict[str, Any]:
        """Convert to Argo artifact spec"""
        spec: Dict[str, Any] = {"name": self.name, "path": self.path}

        if self.location:
            location_key = self.location_type.value
            spec[location_key] = {"key": self.location} if self.location_type != ArtifactLocation.RAW else self.location

        if self.from_:
            spec["from"] = self.from_

        if self.archive:
            spec["archive"] = self.archive

        return spec


@dataclass
class ResourceRequirements:
    """Compute resource requirements"""

    requests_cpu: Optional[str] = None
    requests_memory: Optional[str] = None
    limits_cpu: Optional[str] = None
    limits_memory: Optional[str] = None
    gpu_count: Optional[int] = None
    gpu_type: Optional[str] = None
    ephemeral_storage: Optional[str] = None

    def to_resource_spec(self) -> Dict[str, Any]:
        """Convert to Kubernetes resource spec"""
        resources: Dict[str, Any] = {}

        requests = {}
        if self.requests_cpu:
            requests["cpu"] = self.requests_cpu
        if self.requests_memory:
            requests["memory"] = self.requests_memory
        if self.gpu_count and self.gpu_type:
            requests[self.gpu_type] = str(self.gpu_count)

        limits = {}
        if self.limits_cpu:
            limits["cpu"] = self.limits_cpu
        if self.limits_memory:
            limits["memory"] = self.limits_memory
        if self.gpu_count and self.gpu_type:
            limits[self.gpu_type] = str(self.gpu_count)
        if self.ephemeral_storage:
            limits["ephemeral-storage"] = self.ephemeral_storage

        if requests:
            resources["requests"] = requests
        if limits:
            resources["limits"] = limits

        return resources if resources else None


@dataclass
class WorkflowNode:
    """Workflow node (template) definition"""

    name: str
    template_type: str = "container"  # container, script, resource, etc.
    image: Optional[str] = None
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    script: Optional[str] = None
    source: Optional[str] = None  # For script templates
    dependencies: List[str] = field(default_factory=list)

    # Resources
    resources: Optional[ResourceRequirements] = None
    active_deadline_seconds: Optional[int] = None
    retry_strategy: Optional[Dict[str, Any]] = None

    # Artifacts
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    input_artifacts: List[Artifact] = field(default_factory=list)
    output_artifacts: List[Artifact] = field(default_factory=list)

    # Container settings
    working_dir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    volume_mounts: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_argo_template(self) -> Dict[str, Any]:
        """Convert to Argo template spec"""
        template: Dict[str, Any] = {
            "name": self.name,
        }

        if self.template_type == "container":
            template["container"] = {}
            if self.image:
                template["container"]["image"] = self.image
            if self.command:
                template["container"]["command"] = self.command
            if self.args:
                template["container"]["args"] = self.args
            if self.working_dir:
                template["container"]["workingDir"] = self.working_dir
            if self.env:
                template["container"]["env"] = [
                    {"name": k, "value": v} for k, v in self.env.items()
                ]
            if self.volume_mounts:
                template["container"]["volumeMounts"] = self.volume_mounts
            if self.resources:
                template["container"]["resources"] = self.resources.to_resource_spec()

        elif self.template_type == "script":
            template["script"] = {}
            if self.image:
                template["script"]["image"] = self.image
            if self.source:
                template["script"]["source"] = self.source
            if self.command:
                template["script"]["command"] = self.command
            if self.resources:
                template["script"]["resources"] = self.resources.to_resource_spec()

        # Inputs/Outputs
        if self.inputs:
            template["inputs"] = self.inputs
        elif self.input_artifacts:
            template["inputs"] = {"artifacts": [a.to_argo_spec() for a in self.input_artifacts]}

        if self.outputs:
            template["outputs"] = self.outputs
        elif self.output_artifacts:
            template["outputs"] = {"artifacts": [a.to_argo_spec() for a in self.output_artifacts]}

        # Other settings
        if self.active_deadline_seconds:
            template["activeDeadlineSeconds"] = self.active_deadline_seconds
        if self.retry_strategy:
            template["retryStrategy"] = self.retry_strategy

        if self.labels or self.annotations:
            template["metadata"] = {}
            if self.labels:
                template["metadata"]["labels"] = self.labels
            if self.annotations:
                template["metadata"]["annotations"] = self.annotations

        return template


@dataclass
class Workflow:
    """Argo workflow definition"""

    name: str
    namespace: str = "default"
    generate_name: bool = True
    entrypoint: str = "main"

    # Workflow spec
    templates: List[WorkflowNode] = field(default_factory=list)
    arguments: Optional[Dict[str, Any]] = None

    # DAG definition
    tasks: List[Dict[str, Any]] = field(default_factory=list)

    # Execution settings
    service_account_name: Optional[str] = None
    automount_service_account_token: Optional[bool] = None
    executors: Optional[Dict[str, Any]] = None

    # Pod settings
    pod_spec_patch: Optional[str] = None
    pod_metadata: Optional[Dict[str, Any]] = None

    # Scheduling
    node_selector: Dict[str, str] = field(default_factory=dict)
    tolerations: List[Dict[str, Any]] = field(default_factory=list)
    affinity: Optional[Dict[str, Any]] = None

    # Parallelism
    parallelism: Optional[int] = None
    ttl_seconds_after_finished: Optional[int] = None

    # Artifacts
    artifact_repository: Optional[Dict[str, Any]] = None

    # Metadata
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    priority: Optional[int] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    phase: WorkflowPhase = WorkflowPhase.PENDING

    def to_argo_workflow_spec(self) -> Dict[str, Any]:
        """Convert to Argo Workflow spec"""
        # Build templates
        templates = [t.to_argo_template() for t in self.templates]

        # Build DAG tasks if using DAG
        dag_tasks = None
        if self.tasks:
            dag_tasks = self.tasks

        spec: Dict[str, Any] = {
            "entrypoint": self.entrypoint,
            "templates": templates,
        }

        if self.arguments:
            spec["arguments"] = self.arguments
        if self.service_account_name:
            spec["serviceAccountName"] = self.service_account_name
        if self.automount_service_account_token is not None:
            spec["automountServiceAccountToken"] = self.automount_service_account_token
        if self.executors:
            spec["executors"] = self.executors
        if self.pod_spec_patch:
            spec["podSpecPatch"] = self.pod_spec_patch
        if self.pod_metadata:
            spec["podMetadata"] = self.pod_metadata
        if self.node_selector:
            spec["nodeSelector"] = self.node_selector
        if self.tolerations:
            spec["tolerations"] = self.tolerations
        if self.affinity:
            spec["affinity"] = self.affinity
        if self.parallelism:
            spec["parallelism"] = self.parallelism
        if self.ttl_seconds_after_finished:
            spec["ttlSecondsAfterFinished"] = self.ttl_seconds_after_finished
        if self.artifact_repository:
            spec["artifactRepository"] = self.artifact_repository

        # If we have tasks, add a DAG template
        if dag_tasks:
            dag_template = {
                "name": "main",
                "dag": {
                    "tasks": dag_tasks,
                },
            }
            templates.append(dag_template)

        metadata: Dict[str, Any] = {
            "generateName": self.name if self.generate_name else self.name,
            "namespace": self.namespace,
        }

        if self.labels:
            metadata["labels"] = self.labels
        if self.annotations:
            metadata["annotations"] = self.annotations

        return {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": metadata,
            "spec": spec,
        }


@dataclass
class WorkflowStatus:
    """Argo workflow status"""

    name: str
    namespace: str
    phase: WorkflowPhase
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    message: Optional[str] = None

    # Node status
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    started_at_iso: Optional[str] = None
    finished_at_iso: Optional[str] = None

    # Conditions
    conditions: List[Dict[str, Any]] = field(default_factory=list)

    # Resources
    resources_duration: Optional[str] = None
    progress: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "namespace": self.namespace,
            "phase": self.phase.value,
            "startedAt": self.started_at_iso or (self.started_at.isoformat() if self.started_at else None),
            "finishedAt": self.finished_at_iso or (self.finished_at.isoformat() if self.finished_at else None),
            "message": self.message,
            "nodes": self.nodes,
            "conditions": self.conditions,
            "resourcesDuration": self.resources_duration,
            "progress": self.progress,
        }


class ArgoClient:
    """
    Client for interacting with Argo Workflows API

    Provides methods to submit, monitor, and manage workflows.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:2746",
        namespace: str = "default",
        auth_token: Optional[str] = None,
    ):
        """
        Initialize Argo client

        Args:
            base_url: Argo server URL
            namespace: Kubernetes namespace
            auth_token: Optional auth token
        """
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.auth_token = auth_token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def submit_workflow(
        self,
        workflow: Workflow,
        create_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Submit a workflow to Argo

        Args:
            workflow: Workflow definition
            create_options: Options for workflow creation

        Returns:
            Created workflow response
        """
        import httpx

        workflow_spec = workflow.to_argo_workflow_spec()
        url = f"{self.base_url}/api/v1/workflows/{self.namespace}"

        # Add create options
        params = {}
        if create_options:
            if "dry_run" in create_options:
                params["dryRun"] = create_options["dry_run"]
            if "server_dry_run" in create_options:
                params["serverDryRun"] = create_options["server_dry_run"]

        logger.info(f"Submitting workflow: {workflow.name}")

        # In production, make actual HTTP request
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         url,
        #         json=workflow_spec,
        #         headers=self._get_headers(),
        #         params=params,
        #     )
        #     response.raise_for_status()
        #     return response.json()

        # Mock response for now
        await asyncio.sleep(0.1)
        return {
            "metadata": {
                "name": f"{workflow.name}-abc123",
                "namespace": self.namespace,
                "uid": str(uuid.uuid4()),
                "creationTimestamp": datetime.utcnow().isoformat() + "Z",
            },
            "spec": workflow_spec["spec"],
            "status": {
                "phase": "Pending",
                "startedAt": datetime.utcnow().isoformat() + "Z",
            },
        }

    async def get_workflow(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get workflow status

        Args:
            name: Workflow name
            namespace: Kubernetes namespace

        Returns:
            Workflow status or None
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}"

        logger.info(f"Getting workflow: {name}")

        # Mock response
        await asyncio.sleep(0.1)
        return {
            "metadata": {
                "name": name,
                "namespace": ns,
                "creationTimestamp": datetime.utcnow().isoformat() + "Z",
            },
            "spec": {},
            "status": {
                "phase": "Running",
                "startedAt": datetime.utcnow().isoformat() + "Z",
                "nodes": {},
            },
        }

    async def list_workflows(
        self,
        namespace: Optional[str] = None,
        phases: Optional[List[WorkflowPhase]] = None,
        labels: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List workflows with filters

        Args:
            namespace: Kubernetes namespace
            phases: Filter by phases
            labels: Filter by labels
            limit: Max results
            offset: Pagination offset

        Returns:
            List of workflows
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}"

        params = {"limit": limit, "offset": offset}
        if phases:
            params[" phases"] = ",".join([p.value for p in phases])
        if labels:
            params["labelSelector"] = ",".join(labels)

        logger.info(f"Listing workflows in namespace: {ns}")

        # Mock response
        await asyncio.sleep(0.1)
        return []

    async def delete_workflow(
        self,
        name: str,
        namespace: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        Delete a workflow

        Args:
            name: Workflow name
            namespace: Kubernetes namespace
            force: Force deletion

        Returns:
            True if deleted
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}"

        logger.info(f"Deleting workflow: {name}")

        # Mock delete
        await asyncio.sleep(0.1)
        return True

    async def retry_workflow(
        self,
        name: str,
        namespace: Optional[str] = None,
        restart_successful: bool = False,
    ) -> Dict[str, Any]:
        """
        Retry a failed workflow

        Args:
            name: Workflow name
            namespace: Kubernetes namespace
            restart_successful: Also retry successful nodes

        Returns:
            New workflow info
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}/retry"

        logger.info(f"Retrying workflow: {name}")

        await asyncio.sleep(0.1)
        return {"name": f"{name}-retry", "namespace": ns}

    async def stop_workflow(
        self,
        name: str,
        namespace: Optional[str] = None,
    ) -> bool:
        """
        Stop a running workflow

        Args:
            name: Workflow name
            namespace: Kubernetes namespace

        Returns:
            True if stopped
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}/stop"

        logger.info(f"Stopping workflow: {name}")

        await asyncio.sleep(0.1)
        return True

    async def get_workflow_logs(
        self,
        name: str,
        namespace: Optional[str] = None,
        node_id: Optional[str] = None,
        log_options: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get workflow logs

        Args:
            name: Workflow name
            namespace: Kubernetes namespace
            node_id: Specific node ID
            log_options: Log options (tail, grep, etc.)

        Returns:
            List of log entries
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}/log"

        params = {}
        if node_id:
            params["nodeID"] = node_id
        if log_options:
            if "tail" in log_options:
                params["tail"] = log_options["tail"]
            if "grep" in log_options:
                params["grep"] = log_options["grep"]
            if "container" in log_options:
                params["container"] = log_options["container"]

        logger.info(f"Getting logs for workflow: {name}")

        # Mock response
        await asyncio.sleep(0.1)
        return [
            {"content": "Mock log line 1", "time": datetime.utcnow().isoformat()},
            {"content": "Mock log line 2", "time": datetime.utcnow().isoformat()},
        ]

    async def get_workflow_artifacts(
        self,
        name: str,
        namespace: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get workflow artifacts

        Args:
            name: Workflow name
            namespace: Kubernetes namespace
            node_id: Specific node ID

        Returns:
            List of artifacts
        """
        ns = namespace or self.namespace
        url = f"{self.base_url}/api/v1/workflows/{ns}/{name}/artifacts"

        logger.info(f"Getting artifacts for workflow: {name}")

        await asyncio.sleep(0.1)
        return []


# Singleton instance
_argo_client: Optional[ArgoClient] = None


def get_argo_client(
    base_url: str = "http://localhost:2746",
    namespace: str = "default",
    auth_token: Optional[str] = None,
) -> ArgoClient:
    """Get or create Argo client singleton"""
    global _argo_client
    if _argo_client is None:
        _argo_client = ArgoClient(base_url, namespace, auth_token)
    return _argo_client
