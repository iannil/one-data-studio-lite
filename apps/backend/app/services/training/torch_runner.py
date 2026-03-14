"""
PyTorch Distributed Training Runner

Implements PyTorch DDP (DistributedDataParallel) training
with support for multi-node and multi-GPU training.
"""

import logging
import asyncio
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import torch
    import torch.distributed as dist
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

from .distributed_trainer import (
    BaseDistributedTrainer,
    TrainingConfig,
    TrainingJob,
    TrainingStatus,
    ResourceConfig,
)

logger = logging.getLogger(__name__)


class PyTorchDDPTrainer(BaseDistributedTrainer):
    """
    PyTorch DDP (DistributedDataParallel) Trainer

    Supports:
    - Single node, multi-GPU training
    - Multi-node, multi-GPU training
    - Automatic mixed precision (AMP)
    - Gradient checkpointing
    - Model checkpointing
    """

    def __init__(self, config: TrainingConfig):
        super().__init__(config)

        # DDP-specific settings
        self._ddp_config = {
            "find_unused_parameters": config.hyperparameters.get("find_unused_parameters", False),
            "gradient_as_bucket_view": config.hyperparameters.get("gradient_as_bucket_view", True),
            "static_graph": config.hyperparameters.get("static_graph", False),
        }

        # AMP settings
        self._use_amp = config.hyperparameters.get("amp", True)
        self._amp_dtype = config.hyperparameters.get("amp_dtype", "float16")

    async def submit(self) -> TrainingJob:
        """
        Submit PyTorch DDP training job

        For local development, this runs synchronously.
        For Kubernetes, this would create pods/trainers.
        """
        job = TrainingJob(
            job_id=self.job_id,
            config=self.config,
            status=TrainingStatus.STARTING,
            created_at=datetime.utcnow(),
        )

        # Build launch command
        command = self.build_launch_command()

        logger.info(f"Submitting PyTorch DDP job {self.job_id}")
        logger.info(f"Command: {' '.join(command)}")

        # In a real implementation, this would:
        # 1. Create Kubernetes pods/PyTorchJob resource
        # 2. Wait for pods to be ready
        # 3. Start training

        # For now, simulate job submission
        job.status = TrainingStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.pod_names = [f"{self.job_id}-rank-{i}" for i in range(
            self.config.num_nodes * self.config.num_processes_per_node
        )]

        return job

    async def get_status(self, job_id: str) -> TrainingStatus:
        """
        Get training job status

        In production, this would check Kubernetes pod status.
        """
        # Simulated status check
        # In production, check Kubernetes pod status
        return self._status

    async def get_logs(
        self,
        job_id: str,
        follow: bool = False,
        tail_lines: Optional[int] = None,
    ) -> str:
        """
        Get training logs

        In production, this would fetch from Kubernetes logs.
        """
        # Simulated logs
        return f"Logs for training job {job_id}"

    async def cancel(self, job_id: str) -> bool:
        """
        Cancel training job

        In production, this would delete Kubernetes pods.
        """
        self._status = TrainingStatus.CANCELLED
        return True

    async def get_metrics(self, job_id: str) -> Dict[str, Any]:
        """
        Get training metrics

        In production, this would parse training logs or
        query MLflow for metrics.
        """
        return {
            "loss": 0.123,
            "accuracy": 0.956,
            "learning_rate": 0.001,
            "epoch": 5,
            "step": 5000,
        }

    def build_launch_command(self) -> List[str]:
        """
        Build torchrun or torch.distributed.launch command

        Returns:
            Command as list of strings
        """
        # Use torchrun for PyTorch >= 1.9
        # Fallback to torch.distributed.launch for older versions

        # Base command
        cmd = ["torchrun"]

        # Distributed settings
        cmd.extend([
            "--nproc_per_node", str(self.config.num_processes_per_node),
            "--nnodes", str(self.config.num_nodes),
        ])

        if self.config.num_nodes > 1:
            cmd.extend([
                "--master_addr", self.config.master_addr,
                "--master_port", str(self.config.master_port or 29500),
            ])

        # Node rank (set by environment variable in multi-node)
        node_rank = os.environ.get("NODE_RANK", "0")
        cmd.extend(["--node_rank", node_rank])

        # Rendezvous settings for multi-node
        if self.config.num_nodes > 1:
            cmd.extend([
                "--rdzv_backend", "c10d",
                "--rdzv_endpoint", f"{self.config.master_addr}:{self.config.master_port or 29500}",
            ])

        # Training script
        cmd.append(self.config.entry_point)

        # User arguments
        cmd.extend(self.config.entry_point_args)

        return cmd

    def get_environment_variables(self, rank: int = 0, world_size: int = 1) -> Dict[str, str]:
        """Get PyTorch DDP environment variables"""
        env = super().get_environment_variables(rank, world_size)

        # PyTorch DDP specific
        env.update({
            "LOCAL_RANK": str(rank % self.config.num_processes_per_node),
            "NODE_RANK": str(rank // self.config.num_processes_per_node),
            "GROUP_WORLD_SIZE": str(world_size),
        })

        # CUDA settings
        if self.config.resources.gpu_count > 0:
            gpu_list = ",".join(str(i) for i in range(self.config.resources.gpu_count))
            env["CUDA_VISIBLE_DEVICES"] = gpu_list

        # NCCL settings for multi-node
        if self.config.num_nodes > 1:
            env.update({
                "NCCL_SOCKET_IFNAME": os.environ.get("NCCL_SOCKET_IFNAME", "eth0"),
                "NCCL_DEBUG": os.environ.get("NCCL_DEBUG", "INFO"),
                "NCCL_IB_DISABLE": os.environ.get("NCCL_IB_DISABLE", "1"),
                "NCCL_P2P_LEVEL": os.environ.get("NCCL_P2P_LEVEL", "0"),  # For single-node NVLink
            })

        # Mixed precision
        if self._use_amp:
            env["TORCH AMP DTYPE"] = self._amp_dtype

        return env

    def get_dataloader_config(self) -> Dict[str, Any]:
        """
        Get recommended dataloader configuration for DDP

        Returns:
            Dataloader configuration
        """
        world_size = self.config.num_nodes * self.config.num_processes_per_node

        return {
            "batch_size": self.config.hyperparameters.get("batch_size", 32) // world_size,
            "num_workers": self.config.hyperparameters.get("num_workers", 4),
            "pin_memory": self.config.hyperparameters.get("pin_memory", True),
            "shuffle": self.config.hyperparameters.get("shuffle", True),
            "drop_last": self.config.hyperparameters.get("drop_last", True),
        }

    def get_training_script_template(self) -> str:
        """
        Get a template for PyTorch DDP training script

        Returns:
            Python script template
        """
        return '''import os
import argparse
import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler


def setup_ddp():
    """Initialize DDP"""
    dist.init_process_group(
        backend="nccl" if torch.cuda.is_available() else "gloo",
    )
    local_rank = int(os.environ["LOCAL_RANK"])
    torch.cuda.set_device(local_rank)
    return local_rank


def cleanup_ddp():
    """Cleanup DDP"""
    dist.destroy_process_group()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--lr", type=float, default=0.001)
    args = parser.parse_args()

    # Setup DDP
    local_rank = setup_ddp()
    rank = dist.get_rank()
    world_size = dist.get_world_size()

    # Create model and wrap with DDP
    model = YourModel()
    model = model.to(local_rank)
    model = DDP(model, device_ids=[local_rank])

    # Create dataloader with DistributedSampler
    dataset = YourDataset()
    sampler = DistributedSampler(
        dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True,
    )
    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size // world_size,
        sampler=sampler,
        num_workers=4,
        pin_memory=True,
    )

    # Training loop
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        sampler.set_epoch(epoch)

        for batch_idx, (data, target) in enumerate(dataloader):
            data, target = data.to(local_rank), target.to(local_rank)

            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()

            if rank == 0 and batch_idx % 100 == 0:
                print(f"Epoch {epoch}, Batch {batch_idx}, Loss: {loss.item()}")

    cleanup_ddp()


if __name__ == "__main__":
    main()
'''


def get_pytorch_job_manifest(
    job: TrainingJob,
    image: str = "pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime",
) -> Dict[str, Any]:
    """
    Generate Kubernetes PyTorchJob manifest

    Requires Kubeflow Training Operator to be installed.

    Args:
        job: Training job
        image: Docker image to use

    Returns:
        Kubernetes manifest as dictionary
    """
    world_size = job.config.num_nodes * job.config.num_processes_per_node

    manifest = {
        "apiVersion": "kubeflow.org/v1",
        "kind": "PyTorchJob",
        "metadata": {
            "name": job.job_id,
            "namespace": job.config.namespace,
            "labels": {
                "app": "training",
                "training-backend": "pytorch",
            },
        },
        "spec": {
            "pytorchReplicaSpecs": {
                "Master": {
                    "replicas": 1,
                    "restartPolicy": "OnFailure",
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "pytorch",
                                "image": image,
                                "command": job.config.entry_point.split(),
                                "args": job.config.entry_point_args,
                                "env": [
                                    {"name": "MASTER_ADDR", "value": "$(PYTORCH_JOB_MASTER_SERVICE)"},
                                    {"name": "MASTER_PORT", "value": "23456"},
                                    {"name": "WORLD_SIZE", "value": str(world_size)},
                                    {"name": "NCCL_DEBUG", "value": "INFO"},
                                ],
                                "resources": job.config.resources.to_k8s_resources(),
                            }],
                        },
                    },
                },
                "Worker": {
                    "replicas": job.config.num_nodes * job.config.num_processes_per_node - 1,
                    "restartPolicy": "OnFailure",
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "pytorch",
                                "image": image,
                                "command": job.config.entry_point.split(),
                                "args": job.config.entry_point_args,
                                "env": [
                                    {"name": "MASTER_ADDR", "value": "$(PYTORCH_JOB_MASTER_SERVICE)"},
                                    {"name": "MASTER_PORT", "value": "23456"},
                                    {"name": "WORLD_SIZE", "value": str(world_size)},
                                ],
                                "resources": job.config.resources.to_k8s_resources(),
                            }],
                        },
                    },
                },
            },
        },
    }

    return manifest


# Utility functions for distributed training

def calculate_effective_batch_size(
    base_batch_size: int,
    num_nodes: int,
    gpus_per_node: int,
    gradient_accumulation_steps: int = 1,
) -> int:
    """
    Calculate the effective batch size for distributed training

    Args:
        base_batch_size: Batch size per GPU
        num_nodes: Number of nodes
        gpus_per_node: GPUs per node
        gradient_accumulation_steps: Gradient accumulation steps

    Returns:
        Effective batch size
    """
    return base_batch_size * num_nodes * gpus_per_node * gradient_accumulation_steps


def get_recommended_lr(
    base_lr: float,
    num_nodes: int,
    gpus_per_node: int,
    scaling_rule: str = "linear",
) -> float:
    """
    Get recommended learning rate for distributed training

    Args:
        base_lr: Learning rate for single GPU
        num_nodes: Number of nodes
        gpus_per_node: GPUs per node
        scaling_rule: "linear" or "sqrt"

    Returns:
        Scaled learning rate
    """
    world_size = num_nodes * gpus_per_node

    if scaling_rule == "linear":
        return base_lr * world_size
    elif scaling_rule == "sqrt":
        return base_lr * (world_size ** 0.5)
    else:
        return base_lr


def validate_ddp_configuration(config: TrainingConfig) -> List[str]:
    """
    Validate PyTorch DDP configuration

    Args:
        config: Training configuration

    Returns:
        List of validation errors
    """
    errors = []

    if config.backend != "pytorch":
        errors.append("Backend must be 'pytorch' for DDP training")

    if config.strategy != "ddp":
        errors.append("Strategy must be 'ddp' for PyTorch DDP")

    if config.num_processes_per_node != config.resources.gpu_count:
        errors.append(
            f"num_processes_per_node ({config.num_processes_per_node}) "
            f"must equal gpu_count ({config.resources.gpu_count})"
        )

    # Check for required hyperparameters
    required_params = ["batch_size", "epochs"]
    for param in required_params:
        if param not in config.hyperparameters:
            errors.append(f"Missing required hyperparameter: {param}")

    return errors


# Training hooks for monitoring

class TrainingMonitor:
    """
    Monitor PyTorch DDP training progress

    Can be integrated into training scripts for real-time monitoring.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self._metrics = []

    def log_metric(self, key: str, value: float, step: int):
        """Log a training metric"""
        self._metrics.append({
            "job_id": self.job_id,
            "key": key,
            "value": value,
            "step": step,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def log_metrics(self, metrics: Dict[str, float], step: int):
        """Log multiple training metrics"""
        for key, value in metrics.items():
            self.log_metric(key, value, step)

    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get all logged metrics"""
        return self._metrics

    def save_checkpoint(self, model, optimizer, epoch, path: str):
        """Save training checkpoint"""
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
        }
        torch.save(checkpoint, path)


# Export PyTorch version info
if TORCH_AVAILABLE:
    PYTORCH_VERSION = torch.__version__
    CUDA_AVAILABLE = torch.cuda.is_available()
    CUDA_VERSION = torch.version.cuda if CUDA_AVAILABLE else None
else:
    PYTORCH_VERSION = None
    CUDA_AVAILABLE = False
    CUDA_VERSION = None
