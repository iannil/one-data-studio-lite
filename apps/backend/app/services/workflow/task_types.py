"""
Workflow Task Types Registry

Defines available task types for workflow DAGs.
"""

from enum import Enum
from typing import Dict, Type, Callable, Any, List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


class TaskType(str, Enum):
    """Workflow task types"""

    # Data tasks
    SQL = "sql"
    PYTHON = "python"
    SHELL = "shell"
    ETL = "etl"

    # ML tasks
    TRAINING = "training"
    INFERENCE = "inference"
    EVALUATION = "evaluation"
    MODEL_REGISTER = "model_register"

    # Dependency tasks
    WAIT = "wait"
    SENSOR = "sensor"

    # Notification tasks
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"

    # Data transfer tasks
    EXPORT = "export"
    IMPORT = "import"

    # Notebook tasks
    NOTEBOOK = "notebook"


@dataclass
class TaskConfig:
    """Base task configuration"""

    task_id: str
    task_type: TaskType
    name: str
    description: Optional[str] = None
    depends_on: Optional[List[str]] = None
    retry_count: int = 0
    retry_delay_seconds: int = 300
    timeout_seconds: Optional[int] = None
    # Task-specific parameters
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.depends_on is None:
            self.depends_on = []


class BaseTaskHandler(ABC):
    """
    Base class for task handlers

    Task handlers implement the execution logic for each task type.
    """

    def __init__(self, config: TaskConfig):
        self.config = config

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task

        Args:
            context: Execution context with variables from previous tasks

        Returns:
            Task output data
        """
        pass

    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate task configuration

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    def get_airflow_operator(self) -> Dict[str, Any]:
        """
        Get Airflow operator configuration for this task

        Returns:
            Airflow operator configuration
        """
        return {
            "task_id": self.config.task_id,
            **self.get_operator_params(),
        }

    def get_operator_params(self) -> Dict[str, Any]:
        """Get operator-specific parameters"""
        return {
            "retries": self.config.retry_count,
            "retry_delay": self.config.retry_delay_seconds,
        }


# Task handler registry
TASK_HANDLERS: Dict[TaskType, Type[BaseTaskHandler]] = {}


def register_task_handler(task_type: TaskType):
    """
    Decorator to register a task handler

    Usage:
        @register_task_handler(TaskType.SQL)
    class SQLTaskHandler(BaseTaskHandler):
            ...
    """

    def decorator(cls: Type[BaseTaskHandler]):
        TASK_HANDLERS[task_type] = cls
        return cls

    return decorator


class TaskRegistry:
    """
    Task registry for managing available task types and handlers
    """

    @staticmethod
    def get_handler(task_type: TaskType) -> Optional[Type[BaseTaskHandler]]:
        """Get handler class for a task type"""
        return TASK_HANDLERS.get(task_type)

    @staticmethod
    def create_handler(config: TaskConfig) -> BaseTaskHandler:
        """Create handler instance from config"""
        handler_class = TaskRegistry.get_handler(config.task_type)
        if not handler_class:
            raise ValueError(f"No handler registered for task type: {config.task_type}")
        return handler_class(config)

    @staticmethod
    def list_task_types() -> List[Dict[str, Any]]:
        """List all available task types"""
        return [
            {
                "type": task_type.value,
                "name": task_type.value.replace("_", " ").title(),
                "category": TaskRegistry._get_category(task_type),
            }
            for task_type in TaskType
        ]

    @staticmethod
    def _get_category(task_type: TaskType) -> str:
        """Get category for a task type"""
        categories = {
            # Data tasks
            TaskType.SQL: "Data",
            TaskType.PYTHON: "Code",
            TaskType.SHELL: "Code",
            TaskType.ETL: "Data",
            # ML tasks
            TaskType.TRAINING: "Machine Learning",
            TaskType.INFERENCE: "Machine Learning",
            TaskType.EVALUATION: "Machine Learning",
            TaskType.MODEL_REGISTER: "Machine Learning",
            # Dependency tasks
            TaskType.WAIT: "Control Flow",
            TaskType.SENSOR: "Control Flow",
            # Notification tasks
            TaskType.EMAIL: "Notification",
            TaskType.WEBHOOK: "Notification",
            TaskType.SLACK: "Notification",
            # Data transfer
            TaskType.EXPORT: "Data Transfer",
            TaskType.IMPORT: "Data Transfer",
            # Notebook
            TaskType.NOTEBOOK: "Notebook",
        }
        return categories.get(task_type, "Other")


# Import task handler implementations
from .task_handlers import (
    SQLTaskHandler,
    PythonTaskHandler,
    ShellTaskHandler,
    ETLTaskHandler,
    TrainingTaskHandler,
    InferenceTaskHandler,
    WaitTaskHandler,
    SensorTaskHandler,
    NotebookTaskHandler,
)

__all__ = [
    "TaskType",
    "TaskConfig",
    "BaseTaskHandler",
    "TaskRegistry",
    "register_task_handler",
]
