"""
Model Serving Services

Provides model serving capabilities including:
- Inference service management (KServe/Seldon)
- A/B testing
- Canary deployments
"""

from .serving import (
    ServingPlatform,
    ServingStatus,
    PredictorType,
    DeploymentMode,
    PredictorConfig,
    ABTestConfig,
    CanaryConfig,
    InferenceService,
    ModelServingService,
    get_serving_service,
)

from .ab_testing import (
    TrafficSplitMethod,
    SuccessMetricType,
    ModelVariant,
    ABTestExperiment,
    StatisticalTestResult,
    ABTestingService,
    get_ab_testing_service,
)

from .canary import (
    CanaryPhase,
    CanaryStrategy,
    CanaryStep,
    CanaryDeployment,
    CanaryMetrics,
    CanaryService,
    get_canary_service,
)

__all__ = [
    # Serving
    "ServingPlatform",
    "ServingStatus",
    "PredictorType",
    "DeploymentMode",
    "PredictorConfig",
    "ABTestConfig",
    "CanaryConfig",
    "InferenceService",
    "ModelServingService",
    "get_serving_service",
    # A/B Testing
    "TrafficSplitMethod",
    "SuccessMetricType",
    "ModelVariant",
    "ABTestExperiment",
    "StatisticalTestResult",
    "ABTestingService",
    "get_ab_testing_service",
    # Canary
    "CanaryPhase",
    "CanaryStrategy",
    "CanaryStep",
    "CanaryDeployment",
    "CanaryMetrics",
    "CanaryService",
    "get_canary_service",
]
