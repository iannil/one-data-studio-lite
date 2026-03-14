"""
DAG to Argo Workflow Converter

Converts internal DAG definitions to Argo Workflow specifications.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .argo_client import (
    Workflow,
    WorkflowNode,
    Artifact,
    ResourceRequirements,
    ArtifactLocation,
)

logger = logging.getLogger(__name__)


@dataclass
class DAGEdge:
    """Edge in a DAG"""

    from_node: str
    to_node: str
    condition: Optional[str] = None  # Optional condition for execution


@dataclass
class DAGNode:
    """Node in a DAG"""

    node_id: str
    name: str
    task_type: str
    description: Optional[str] = None

    # Task configuration
    image: Optional[str] = None
    command: Optional[List[str]] = None
    args: Optional[List[str]] = None
    script: Optional[str] = None
    source_code: Optional[str] = None

    # Dependencies
    depends_on: List[str] = None

    # Resources
    cpu_request: Optional[str] = None
    cpu_limit: Optional[str] = None
    memory_request: Optional[str] = None
    memory_limit: Optional[str] = None
    gpu_count: Optional[int] = None

    # Environment
    env_vars: Dict[str, str] = None

    # Retry policy
    retry_count: int = 0
    retry_backoff: Optional[int] = None
    retry_duration: Optional[str] = None

    # Timeout
    timeout_seconds: Optional[int] = None

    # Position (for UI)
    position_x: float = 0
    position_y: float = 0


@dataclass
class DAGDefinition:
    """DAG definition for conversion"""

    dag_id: str
    name: str
    description: Optional[str] = None
    schedule: Optional[str] = None
    tags: List[str] = None
    nodes: List[DAGNode] = None
    edges: List[DAGEdge] = None

    # Global settings
    namespace: str = "default"
    service_account: Optional[str] = None
    ttl_seconds_after_finished: Optional[int] = None
    parallelism: Optional[int] = None

    # Artifact repository
    s3_bucket: Optional[str] = None
    s3_endpoint: Optional[str] = None
    s3_access_key: Optional[str] = None
    s3_secret_key: Optional[str] = None

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = []
        if self.tags is None:
            self.tags = []


class DAGToArgoConverter:
    """
    Converts internal DAG definitions to Argo Workflow specifications
    """

    # Task type to image mappings
    TASK_IMAGES = {
        "sql": "postgres:15",
        "python": "python:3.11-slim",
        "shell": "bash:5",
        "notebook": "jupyter/scipy-notebook:latest",
        "etl": "python:3.11-slim",
        "training": "pytorch/pytorch:2.0-cuda11.7-cudnn8-runtime",
        "inference": "pytorch/pytorch:2.0-cuda11.7-cudnn8-runtime",
        "evaluation": "python:3.11-slim",
        "model_register": "python:3.11-slim",
        "email": "curlimages/curl:latest",
        "sensor": "argoproj/argoexec:latest",
        "http": "curlimages/curl:latest",
        "notification": "curlimages/curl:latest",
    }

    def __init__(
        self,
        default_namespace: str = "default",
        default_service_account: Optional[str] = None,
    ):
        """
        Initialize converter

        Args:
            default_namespace: Default Kubernetes namespace
            default_service_account: Default service account
        """
        self.default_namespace = default_namespace
        self.default_service_account = default_service_account

    async def convert(
        self,
        dag: DAGDefinition,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Workflow:
        """
        Convert DAG to Argo Workflow

        Args:
            dag: DAG definition
            variables: Variable values for substitution

        Returns:
            Argo Workflow
        """
        # Substitute variables in DAG
        dag = self._substitute_variables(dag, variables or {})

        # Build workflow
        workflow = Workflow(
            name=dag.dag_id,
            namespace=dag.namespace,
            entrypoint="main",
            service_account_name=dag.service_account or self.default_service_account,
            ttl_seconds_after_finished=dag.ttl_seconds_after_finished,
            parallelism=dag.parallelism,
            labels={"dag_id": dag.dag_id},
            annotations={"description": dag.description or ""},
        )

        # Add artifact repository if configured
        if dag.s3_bucket:
            workflow.artifact_repository = {
                "s3": {
                    "bucket": dag.s3_bucket,
                    "endpoint": dag.s3_endpoint or "s3.amazonaws.com",
                    "accessKeySecret": {"name": "s3-credentials", "key": "accessKey"},
                    "secretKeySecret": {"name": "s3-credentials", "key": "secretKey"},
                }
            }

        # Build node map for dependency resolution
        node_map = {node.node_id: node for node in dag.nodes}

        # Convert nodes to Argo templates and DAG tasks
        for node in dag.nodes:
            template = self._convert_node_to_template(node, variables or {})
            workflow.templates.append(template)

        # Build DAG structure
        tasks = []
        processed = set()

        # Process nodes in topological order
        for node in self._topological_sort(dag.nodes):
            task = self._convert_node_to_task(node, node_map, processed, variables or {})
            tasks.append(task)
            processed.add(node.node_id)

        workflow.tasks = tasks

        logger.info(f"Converted DAG {dag.dag_id} to Argo Workflow with {len(dag.nodes)} nodes")
        return workflow

    def _substitute_variables(
        self,
        dag: DAGDefinition,
        variables: Dict[str, Any],
    ) -> DAGDefinition:
        """Substitute variables in DAG definition"""
        # Create a shallow copy to avoid modifying original
        substituted = dag

        # Substitute in node configurations
        for node in substituted.nodes:
            if node.args:
                node.args = self._substitute_in_list(node.args, variables)
            if node.env_vars:
                for key, value in node.env_vars.items():
                    if isinstance(value, str):
                        node.env_vars[key] = self._substitute_string(value, variables)

        return substituted

    def _substitute_string(self, text: str, variables: Dict[str, Any]) -> str:
        """Substitute {{ variable }} placeholders"""
        for key, value in variables.items():
            placeholder = f"{{{{ {key} }}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        return text

    def _substitute_in_list(self, items: List[str], variables: Dict[str, Any]) -> List[str]:
        """Substitute variables in list"""
        return [self._substitute_string(item, variables) for item in items]

    def _topological_sort(self, nodes: List[DAGNode]) -> List[DAGNode]:
        """Sort nodes topologically by dependencies"""
        sorted_nodes = []
        visited = set()

        def visit(node: DAGNode):
            if node.node_id in visited:
                return
            visited.add(node.node_id)

            # Visit dependencies first
            if node.depends_on:
                for dep_id in node.depends_on:
                    dep_node = next((n for n in nodes if n.node_id == dep_id), None)
                    if dep_node:
                        visit(dep_node)

            sorted_nodes.append(node)

        for node in nodes:
            visit(node)

        return sorted_nodes

    def _convert_node_to_template(
        self,
        node: DAGNode,
        variables: Dict[str, Any],
    ) -> WorkflowNode:
        """Convert DAG node to Argo template"""
        # Determine image
        image = node.image or self.TASK_IMAGES.get(node.task_type, "alpine:latest")

        # Build resource requirements
        resources = None
        if any([node.cpu_request, node.cpu_limit, node.memory_request, node.memory_limit, node.gpu_count]):
            resources = ResourceRequirements(
                requests_cpu=node.cpu_request,
                limits_cpu=node.cpu_limit,
                requests_memory=node.memory_request,
                limits_memory=node.memory_limit,
                gpu_count=node.gpu_count,
                gpu_type="nvidia.com/gpu" if node.gpu_count else None,
            )

        # Build retry strategy
        retry_strategy = None
        if node.retry_count > 0:
            retry_strategy = {"limit": node.retry_count}
            if node.retry_backoff:
                retry_strategy["backoff"] = {"duration": f"{node.retry_backoff}s"}
            if node.retry_duration:
                retry_strategy["retryPolicy"] = "OnFailure"

        # Create template based on task type
        if node.script or node.source_code:
            # Script template
            template = WorkflowNode(
                name=node.node_id,
                template_type="script",
                image=image,
                command=node.command or ["python"],
                source=node.script or node.source_code or "",
                resources=resources,
                active_deadline_seconds=node.timeout_seconds,
                retry_strategy=retry_strategy,
                env=node.env_vars or {},
                labels={"task_type": node.task_type},
                annotations={"description": node.description or ""},
            )
        else:
            # Container template
            template = WorkflowNode(
                name=node.node_id,
                template_type="container",
                image=image,
                command=node.command,
                args=node.args,
                resources=resources,
                active_deadline_seconds=node.timeout_seconds,
                retry_strategy=retry_strategy,
                env=node.env_vars or {},
                labels={"task_type": node.task_type},
                annotations={"description": node.description or ""},
            )

        return template

    def _convert_node_to_task(
        self,
        node: DAGNode,
        node_map: Dict[str, DAGNode],
        processed: set,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Convert DAG node to Argo DAG task"""
        task: Dict[str, Any] = {
            "name": node.node_id,
            "template": node.node_id,
        }

        # Add arguments if present
        if node.args:
            task["arguments"] = {
                "parameters": [{"name": f"param-{i}", "value": arg} for i, arg in enumerate(node.args)]
            }

        # Add dependencies
        dependencies = []
        if node.depends_on:
            dependencies.extend(node.depends_on)

        task["dependencies"] = dependencies

        return task


class ArgoToDAGConverter:
    """
    Converts Argo Workflow specifications back to internal DAG definitions
    """

    def __init__(self):
        """Initialize converter"""

    async def convert_to_dag(
        self,
        argo_workflow: Dict[str, Any],
    ) -> DAGDefinition:
        """
        Convert Argo Workflow to DAG definition

        Args:
            argo_workflow: Argo workflow spec

        Returns:
            DAG definition
        """
        metadata = argo_workflow.get("metadata", {})
        spec = argo_workflow.get("spec", {})

        dag_id = metadata.get("name", "workflow")
        name = metadata.get("name", "workflow")
        namespace = metadata.get("namespace", "default")

        # Get annotations
        annotations = metadata.get("annotations", {})
        description = annotations.get("description")
        tags = (annotations.get("tags") or "").split(",") if annotations.get("tags") else []

        # Extract templates
        templates_spec = spec.get("templates", [])
        templates = {t.get("name"): t for t in templates_spec}

        # Extract DAG tasks
        main_template = next((t for t in templates_spec if t.get("name") == "main"), None)
        dag_tasks = main_template.get("dag", {}).get("tasks", []) if main_template else []

        # Convert to DAG nodes
        nodes = []
        for task in dag_tasks:
            template_name = task.get("template")
            template = templates.get(template_name, {})

            node = self._convert_template_to_node(template_name, template, task)
            nodes.append(node)

        return DAGDefinition(
            dag_id=dag_id,
            name=name,
            description=description,
            tags=tags,
            nodes=nodes,
            namespace=namespace,
        )

    def _convert_template_to_node(
        self,
        name: str,
        template: Dict[str, Any],
        task: Dict[str, Any],
    ) -> DAGNode:
        """Convert Argo template to DAG node"""
        container = template.get("container", {})
        script = template.get("script", {})

        # Determine task type
        labels = template.get("metadata", {}).get("labels", {})
        task_type = labels.get("task_type", "custom")

        # Extract resources
        resources = container.get("resources", {})
        requests = resources.get("requests", {})
        limits = resources.get("limits", {})

        # Extract dependencies
        dependencies = task.get("dependencies", [])

        return DAGNode(
            node_id=name,
            name=name,
            task_type=task_type,
            description=template.get("metadata", {}).get("annotations", {}).get("description"),
            image=container.get("image"),
            command=container.get("command"),
            args=container.get("args"),
            source_code=script.get("source"),
            depends_on=dependencies,
            cpu_request=requests.get("cpu"),
            cpu_limit=limits.get("cpu"),
            memory_request=requests.get("memory"),
            memory_limit=limits.get("memory"),
            gpu_count=self._extract_gpu_count(limits),
            env_vars=self._extract_env_vars(container),
            timeout_seconds=template.get("activeDeadlineSeconds"),
            retry_count=template.get("retryStrategy", {}).get("limit", 0),
        )

    def _extract_gpu_count(self, limits: Dict[str, str]) -> Optional[int]:
        """Extract GPU count from resource limits"""
        for key in limits.keys():
            if "gpu" in key.lower() or "nvidia" in key.lower():
                try:
                    return int(limits[key])
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_env_vars(self, container: Dict[str, Any]) -> Dict[str, str]:
        """Extract environment variables from container spec"""
        env_list = container.get("env", [])
        return {e["name"]: e.get("value", "") for e in env_list if isinstance(e, dict) and "name" in e}


# Singleton instances
_dag_converter: Optional[DAGToArgoConverter] = None
_argo_converter: Optional[ArgoToDAGConverter] = None


def get_dag_converter(
    default_namespace: str = "default",
    default_service_account: Optional[str] = None,
) -> DAGToArgoConverter:
    """Get or create DAG to Argo converter"""
    global _dag_converter
    if _dag_converter is None:
        _dag_converter = DAGToArgoConverter(default_namespace, default_service_account)
    return _dag_converter


def get_argo_converter() -> ArgoToDAGConverter:
    """Get or create Argo to DAG converter"""
    global _argo_converter
    if _argo_converter is None:
        _argo_converter = ArgoToDAGConverter()
    return _argo_converter
