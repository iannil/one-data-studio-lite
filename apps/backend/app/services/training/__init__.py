"""
Training Service Package

Provides distributed training support for PyTorch and TensorFlow.
"""

from .distributed_trainer import (
    TrainingBackend,
    TrainingStatus,
    DistributedStrategy,
    TrainingConfig,
    ResourceConfig,
    TrainingJob,
    BaseDistributedTrainer,
    TrainingOrchestrator,
    get_training_orchestrator,
)

from .torch_runner import (
    PyTorchDDPTrainer,
    get_pytorch_job_manifest,
    calculate_effective_batch_size,
    get_recommended_lr,
    validate_ddp_configuration,
    PYTORCH_VERSION,
)

from .tf_runner import (
    TensorFlowTrainer,
    get_tf_job_manifest,
    get_tpu_training_config,
    validate_tf_configuration,
    TF_VERSION,
)

__all__ = [
    # Core classes
    "TrainingBackend",
    "TrainingStatus",
    "DistributedStrategy",
    "TrainingConfig",
    "ResourceConfig",
    "TrainingJob",
    "BaseDistributedTrainer",
    "TrainingOrchestrator",
    "get_training_orchestrator",

    # PyTorch
    "PyTorchDDPTrainer",
    "get_pytorch_job_manifest",
    "calculate_effective_batch_size",
    "get_recommended_lr",
    "validate_ddp_configuration",
    "PYTORCH_VERSION",

    # TensorFlow
    "TensorFlowTrainer",
    "get_tf_job_manifest",
    "get_tpu_training_config",
    "validate_tf_configuration",
    "TF_VERSION",
]
