"""
AIHub Services Package

Provides model registry, fine-tuning, and deployment services
for 400+ open-source AI models.
"""

from app.services.aihub.registry import (
    AIHubModel,
    ModelCategory,
    ModelFramework,
    ModelLicense,
    ModelCapability,
    register_model,
    get_model,
    list_models,
    get_categories,
    get_frameworks,
    get_model_stats,
    AIHUB_MODEL_REGISTRY,
)
from app.services.aihub.finetune import (
    FinetuneMethod,
    FinetuneStatus,
    FinetuneConfig,
    FinetuneJob,
    FinetuneService,
    finetune_service,
)
from app.services.aihub.deployer import (
    DeploymentStatus,
    ScalingConfig,
    ModelDeployment,
    AIHubDeployer,
    aihub_deployer,
)

__all__ = [
    # Registry
    "AIHubModel",
    "ModelCategory",
    "ModelFramework",
    "ModelLicense",
    "ModelCapability",
    "register_model",
    "get_model",
    "list_models",
    "get_categories",
    "get_frameworks",
    "get_model_stats",
    "AIHUB_MODEL_REGISTRY",
    # Fine-tuning
    "FinetuneMethod",
    "FinetuneStatus",
    "FinetuneConfig",
    "FinetuneJob",
    "FinetuneService",
    "finetune_service",
    # Deployment
    "DeploymentStatus",
    "ScalingConfig",
    "ModelDeployment",
    "AIHubDeployer",
    "aihub_deployer",
]
