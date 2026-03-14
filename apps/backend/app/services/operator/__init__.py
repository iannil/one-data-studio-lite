"""
Kubernetes Operator Service Package

Provides Custom Resource Definitions (CRDs) and operator implementations
for managing platform resources on Kubernetes.
"""

from .operator import (
    ResourceState,
    ConditionType,
    Condition,
    ResourceStatus,
    CRDDefinition,
    OperatorController,
    NotebookOperator,
    TrainingJobOperator,
    InferenceServiceOperator,
    OperatorManager,
    get_operator_manager,
)

__all__ = [
    # Enums
    "ResourceState",
    "ConditionType",
    # Classes
    "Condition",
    "ResourceStatus",
    "CRDDefinition",
    "OperatorController",
    "NotebookOperator",
    "TrainingJobOperator",
    "InferenceServiceOperator",
    "OperatorManager",
    "get_operator_manager",
]
