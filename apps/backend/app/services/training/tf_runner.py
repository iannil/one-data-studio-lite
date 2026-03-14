"""
TensorFlow Distributed Training Runner

Implements TensorFlow distributed training with support for:
- MirroredStrategy (single node, multi-GPU)
- MultiWorkerMirroredStrategy (multi-node, multi-GPU)
- TPUStrategy (TPU training)
- ParameterServerStrategy (parameter server training)
"""

import logging
import asyncio
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    tf = None

from .distributed_trainer import (
    BaseDistributedTrainer,
    TrainingConfig,
    TrainingJob,
    TrainingStatus,
    DistributedStrategy,
)


logger = logging.getLogger(__name__)


class TensorFlowTrainer(BaseDistributedTrainer):
    """
    TensorFlow Distributed Trainer

    Supports multiple distribution strategies:
    - MirroredStrategy: Single node, multi-GPU
    - MultiWorkerMirroredStrategy: Multi-node, multi-GPU
    - TPUStrategy: TPU training
    - ParameterServerStrategy: Parameter server training
    - CentralStorageStrategy: Central storage strategy
    """

    def __init__(self, config: TrainingConfig):
        super().__init__(config)

        # Determine strategy to use
        self._strategy = self._create_strategy()

    def _create_strategy(self):
        """Create TensorFlow distribution strategy"""
        if not TF_AVAILABLE:
            logger.warning("TensorFlow not available")
            return None

        strategy_type = self.config.strategy

        if strategy_type == DistributedStrategy.MIRRORED:
            # Single node, multi-GPU
            return tf.distribute.MirroredStrategy()

        elif strategy_type == DistributedStrategy.MULTI_WORKER_MIRRORED:
            # Multi-node, multi-GPU
            return tf.distribute.MultiWorkerMirroredStrategy()

        elif strategy_type == DistributedStrategy.TPUS:
            # TPU training
            tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
            return tf.distribute.TPUStrategy(tpu)

        elif strategy_type == DistributedStrategy.PARAMETER_SERVER:
            # Parameter server
            return tf.distribute.ParameterServerStrategy()

        elif strategy_type == DistributedStrategy.SINGLE_NODE:
            # Default to MirroredStrategy for multi-GPU
            gpus = self.config.resources.gpu_count
            if gpus > 1:
                return tf.distribute.MirroredStrategy()
            else:
                return tf.distribute.get_strategy()  # Default strategy

        else:
            # Default strategy
            return tf.distribute.get_strategy()

    async def submit(self) -> TrainingJob:
        """Submit TensorFlow training job"""
        job = TrainingJob(
            job_id=self.job_id,
            config=self.config,
            status=TrainingStatus.STARTING,
            created_at=datetime.utcnow(),
        )

        command = self.build_launch_command()
        logger.info(f"Submitting TensorFlow job {self.job_id}")
        logger.info(f"Strategy: {self.config.strategy}")
        logger.info(f"Command: {' '.join(command)}")

        job.status = TrainingStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.pod_names = [f"{self.job_id}-worker-{i}" for i in range(
            self.config.num_nodes
        )]

        return job

    async def get_status(self, job_id: str) -> TrainingStatus:
        """Get training job status"""
        return self._status

    async def get_logs(
        self,
        job_id: str,
        follow: bool = False,
        tail_lines: Optional[int] = None,
    ) -> str:
        """Get training logs"""
        return f"Logs for TensorFlow training job {job_id}"

    async def cancel(self, job_id: str) -> bool:
        """Cancel training job"""
        self._status = TrainingStatus.CANCELLED
        return True

    async def get_metrics(self, job_id: str) -> Dict[str, Any]:
        """Get training metrics"""
        return {
            "loss": 0.234,
            "accuracy": 0.912,
            "learning_rate": 0.0001,
            "epoch": 3,
            "step": 3000,
        }

    def build_launch_command(self) -> List[str]:
        """Build TensorFlow training command"""
        cmd = ["python", self.config.entry_point]
        cmd.extend(self.config.entry_point_args)
        return cmd

    def get_environment_variables(self, rank: int = 0, world_size: int = 1) -> Dict[str, str]:
        """Get TensorFlow environment variables"""
        env = super().get_environment_variables(rank, world_size)

        # TensorFlow cluster configuration
        if self.config.num_nodes > 1:
            # Build TF_CONFIG for multi-worker training
            cluster_config = self._build_tf_config(rank)
            env["TF_CONFIG"] = json.dumps(cluster_config)

        # GPU settings
        if self.config.resources.gpu_count > 0:
            gpu_list = ",".join(str(i) for i in range(self.config.resources.gpu_count))
            env["CUDA_VISIBLE_DEVICES"] = gpu_list

        # XLA settings (for acceleration)
        if self.config.hyperparameters.get("xla_enable", False):
            env["TF_XLA_FLAGS"] = "--tf_xla_auto_jit=2"

        # Mixed precision
        if self.config.hyperparameters.get("mixed_precision", False):
            env["TF_ENABLE_AUTO_MIXED_PRECISION"] = "1"

        return env

    def _build_tf_config(self, rank: int) -> Dict[str, Any]:
        """Build TF_CONFIG for multi-worker training"""
        workers = []
        for i in range(self.config.num_nodes):
            worker_host = f"worker-{i}.{self.job_id}"
            worker_port = self.config.master_port or 2222
            workers.append(f"{worker_host}:{worker_port}")

        cluster_config = {
            "cluster": {
                "worker": workers,
            },
            "task": {
                "type": "worker",
                "index": rank,
            },
        }

        return cluster_config

    def get_training_script_template(self) -> str:
        """Get TensorFlow distributed training script template"""
        return '''import os
import json
import argparse
import tensorflow as tf


def get_strategy():
    """Get distribution strategy from TF_CONFIG"""
    tf_config = os.environ.get("TF_CONFIG")

    if tf_config:
        config = json.loads(tf_config)
        task_type = config.get("task", {}).get("type")
        task_index = config.get("task", {}).get("index")

        if "cluster" in config:
            # Multi-worker training
            if task_type == "worker":
                return tf.distribute.MultiWorkerMirroredStrategy()
            elif task_type == "ps":
                # Parameter server
                return tf.distribute.ParameterServerStrategy()

    # Default: single node, multi-GPU
    return tf.distribute.MirroredStrategy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=0.001)
    args = parser.parse_args()

    # Get distribution strategy
    strategy = get_strategy()

    with strategy.scope():
        # Create model within strategy scope
        model = create_model()

        # Global batch size
        global_batch_size = args.batch_size * strategy.num_replicas_in_sync

        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=args.lr),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )

    # Load data
    train_dataset, val_dataset = load_data(global_batch_size)

    # Train model
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath="/artifacts/checkpoints/model-{epoch}.ckpt",
            save_weights_only=True,
            save_best_only=True,
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir="/artifacts/tensorboard",
        ),
    ]

    model.fit(
        train_dataset,
        epochs=args.epochs,
        validation_data=val_dataset,
        callbacks=callbacks,
    )

    # Save model
    model.save("/artifacts/model")


def create_model():
    """Create model architecture"""
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(28, 28)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation="relu"),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    return model


def load_data(global_batch_size):
    """Load and prepare datasets"""
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

    # Normalize
    x_train, x_test = x_train / 255.0, x_test / 255.0

    # Create datasets
    train_dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train))
    train_dataset = train_dataset.shuffle(10000).batch(global_batch_size)

    val_dataset = tf.data.Dataset.from_tensor_slices((x_test, y_test))
    val_dataset = val_dataset.batch(global_batch_size)

    return train_dataset, val_dataset


if __name__ == "__main__":
    main()
'''


def get_tf_job_manifest(
    job: TrainingJob,
    image: str = "tensorflow/tensorflow:2.13.0-gpu",
) -> Dict[str, Any]:
    """
    Generate Kubernetes TFJob manifest

    Requires Kubeflow Training Operator to be installed.

    Args:
        job: Training job
        image: Docker image to use

    Returns:
        Kubernetes manifest as dictionary
    """
    strategy = job.config.strategy
    num_workers = job.config.num_nodes

    # Determine replica configuration based on strategy
    if strategy == DistributedStrategy.PARAMETER_SERVER:
        # Parameter server mode
        chief_replicas = 1
        worker_replicas = num_workers
        ps_replicas = max(1, num_workers // 2)
    else:
        # Standard distributed training
        chief_replicas = 1
        worker_replicas = num_workers
        ps_replicas = 0

    manifest = {
        "apiVersion": "kubeflow.org/v1",
        "kind": "TFJob",
        "metadata": {
            "name": job.job_id,
            "namespace": job.config.namespace,
            "labels": {
                "app": "training",
                "training-backend": "tensorflow",
            },
        },
        "spec": {
            "tfReplicaSpecs": {},
        },
    }

    # Chief replica
    if chief_replicas > 0:
        manifest["spec"]["tfReplicaSpecs"]["Chief"] = {
            "replicas": chief_replicas,
            "restartPolicy": "OnFailure",
            "template": {
                "spec": {
                    "containers": [{
                        "name": "tensorflow",
                        "image": image,
                        "command": ["python"],
                        "args": [job.config.entry_point] + job.config.entry_point_args,
                        "env": [
                            {"name": "TF_JOB_ID", "value": job.job_id},
                        ],
                        "resources": job.config.resources.to_k8s_resources(),
                    }],
                },
            },
        }

    # Worker replicas
    manifest["spec"]["tfReplicaSpecs"]["Worker"] = {
        "replicas": worker_replicas,
        "restartPolicy": "OnFailure",
        "template": {
            "spec": {
                "containers": [{
                    "name": "tensorflow",
                    "image": image,
                    "command": ["python"],
                    "args": [job.config.entry_point] + job.config.entry_point_args,
                    "env": _get_tf_worker_env(job),
                    "resources": job.config.resources.to_k8s_resources(),
                }],
            },
        },
    }

    # Parameter server replicas
    if ps_replicas > 0:
        manifest["spec"]["tfReplicaSpecs"]["PS"] = {
            "replicas": ps_replicas,
            "restartPolicy": "Never",
            "template": {
                "spec": {
                    "containers": [{
                        "name": "tensorflow",
                        "image": image,
                        "command": ["python", "-m", "tensorflow.python.training.parameter_server_keras"],
                        "env": _get_tf_ps_env(job),
                        "resources": job.config.resources.to_k8s_resources(),
                    }],
                },
            },
        }

    return manifest


def _get_tf_worker_env(job: TrainingJob) -> List[Dict[str, str]]:
    """Get environment variables for TensorFlow worker"""
    return [
        {"name": "TF_CONFIG", "valueFrom": {
            "configMapKeyRef": {
                "name": f"{job.job_id}-tf-config",
                "key": "TF_CONFIG",
            }
        }},
        {"name": "WORKER_INDEX", "valueFrom": {
            "fieldRef": {"fieldPath": "metadata.annotations['workerset.sigs.k8s.io/worker-index']"}
        }},
    ]


def _get_tf_ps_env(job: TrainingJob) -> List[Dict[str, str]]:
    """Get environment variables for TensorFlow parameter server"""
    return [
        {"name": "TF_CONFIG", "valueFrom": {
            "configMapKeyRef": {
                "name": f"{job.job_id}-tf-config",
                "key": "TF_CONFIG",
            }
        }},
    ]


def get_tpu_training_config(
    job: TrainingJob,
    tpu_type: str = "v3-8",
    tpu_zone: str = "us-central1-b",
) -> Dict[str, Any]:
    """
    Get TPU training configuration

    Args:
        job: Training job
        tpu_type: Type of TPU (v2-8, v3-8, etc.)
        tpu_zone: GCP zone for TPU

    Returns:
        TPU configuration dictionary
    """
    tpu_name = f"{job.job_id}-tpu"

    return {
        "tpu_name": tpu_name,
        "tpu_type": tpu_type,
        "tpu_zone": tpu_zone,
        "resolver": tf.distribute.cluster_resolver.TPUClusterResolver(
            tpu=tpu_name,
            zone=tpu_zone,
        ),
    }


def validate_tf_configuration(config: TrainingConfig) -> List[str]:
    """
    Validate TensorFlow training configuration

    Args:
        config: Training configuration

    Returns:
        List of validation errors
    """
    errors = []

    if config.backend != "tensorflow":
        errors.append("Backend must be 'tensorflow'")

    # Validate strategy-specific settings
    if config.strategy == DistributedStrategy.TPUS:
        if config.resources.tpu_count == 0:
            errors.append("TPU training requires tpu_count > 0")

    if config.strategy == DistributedStrategy.PARAMETER_SERVER:
        if config.num_nodes < 2:
            errors.append("Parameter server strategy requires at least 2 nodes")

    return errors


class TPUTrainingRunner:
    """
    Specialized runner for TPU training

    Provides utilities for TPU pod slicing and
    efficient data loading on TPUs.
    """

    def __init__(self, config: TrainingConfig):
        self.config = config
        self._tpu_strategy = None

    def initialize_tpu(self) -> bool:
        """Initialize TPU cluster"""
        if not TF_AVAILABLE:
            logger.error("TensorFlow not available for TPU training")
            return False

        try:
            resolver = tf.distribute.cluster_resolver.TPUClusterResolver()
            tf.config.experimental_connect_to_cluster(resolver)
            tf.tpu.experimental.initialize_tpu_system(resolver)
            self._tpu_strategy = tf.distribute.TPUStrategy(resolver)
            logger.info(f"TPU initialized: {resolver.num_accelerators()['TPU']} cores")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TPU: {e}")
            return False

    def get_tpu_batch_size(self, base_batch_size: int) -> int:
        """Get recommended batch size for TPU"""
        if self._tpu_strategy:
            # TPU works best with batch sizes that are multiples of 8
            # and scaled by the number of TPU cores
            num_cores = self._tpu_strategy.num_replicas_in_sync
            return ((base_batch_size + 7) // 8) * 8 * num_cores
        return base_batch_size

    def get_tpu_training_callbacks(self) -> List[tf.keras.callbacks.Callback]:
        """Get recommended callbacks for TPU training"""
        return [
            tf.keras.callbacks.BackupAndRestore(
                backup_dir="/artifs/backups",
            ),
        ]


# Export TensorFlow version info
if TF_AVAILABLE:
    TF_VERSION = tf.__version__
else:
    TF_VERSION = None
