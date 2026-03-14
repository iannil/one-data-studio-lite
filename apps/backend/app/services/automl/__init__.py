"""
AutoML Service Package

Provides automated machine learning capabilities.
"""

from .automl_service import (
    ProblemType,
    SearchAlgorithm,
    ModelType,
    HyperparameterSpace,
    TrialResult,
    AutoMLResult,
    HyperparameterTuner,
    AutoFeatureEngineering,
    AutoMLEngine,
    get_automl_service,
)

__all__ = [
    "ProblemType",
    "SearchAlgorithm",
    "ModelType",
    "HyperparameterSpace",
    "TrialResult",
    "AutoMLResult",
    "HyperparameterTuner",
    "AutoFeatureEngineering",
    "AutoMLEngine",
    "get_automl_service",
]
