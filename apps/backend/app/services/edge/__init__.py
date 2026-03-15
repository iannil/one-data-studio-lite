"""
Edge Computing Service Package

Provides edge computing functionality:
- Node registration and management
- Model deployment to edge
- Job scheduling and execution
- Metrics collection and aggregation
"""

from .manager import (
    DeploymentConfig,
    DeploymentResult,
    EdgeNodeManager,
    EdgeDeploymentManager,
    EdgeJobManager,
    EdgeMetricsCollector,
    get_node_manager,
    get_deployment_manager,
    get_job_manager,
    get_metrics_collector,
)

__all__ = [
    # Config
    "DeploymentConfig",
    # Result
    "DeploymentResult",
    # Managers
    "EdgeNodeManager",
    "EdgeDeploymentManager",
    "EdgeJobManager",
    "EdgeMetricsCollector",
    # Getters
    "get_node_manager",
    "get_deployment_manager",
    "get_job_manager",
    "get_metrics_collector",
]
