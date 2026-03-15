"""
Cube Studio Python SDK

Provides Python SDK for Pipeline operations including:
- Pipeline task submission
- Execution monitoring
- Resource management
- Artifact handling
"""

from .client import CubeStudioClient
from .pipeline import Pipeline, PipelineTask, TaskStatus
from .training import TrainingJob
from .serving import ModelService

__version__ = "0.1.0"

__all__ = [
    "CubeStudioClient",
    "Pipeline",
    "PipelineTask",
    "TaskStatus",
    "TrainingJob",
    "ModelService",
]
