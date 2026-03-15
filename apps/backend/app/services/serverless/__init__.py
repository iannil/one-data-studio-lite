"""
Serverless Service Package

Provides serverless function computation:
- Python executor
- Container executor
- Auto-scaling capabilities
- HTTP, Timer, Event, Queue triggers
"""

from .executor import (
    ExecutionConfig,
    ExecutionResult,
    PythonExecutor,
    ContainerExecutor,
    ServerlessExecutor,
    get_serverless_executor,
)

__all__ = [
    # Config
    "ExecutionConfig",
    # Result
    "ExecutionResult",
    # Executors
    "PythonExecutor",
    "ContainerExecutor",
    # Main
    "ServerlessExecutor",
    "get_serverless_executor",
]
