"""
Edge Manager Service

Manages edge computing operations:
- Node registration and management
- Model deployment
- Job scheduling
- Metrics collection
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge import (
    EdgeNode,
    EdgeModel,
    EdgeDeployment,
    EdgeJob,
    EdgeDevice,
    EdgeMetrics,
    EdgeInferenceResult,
    NodeStatus,
    DeploymentStatus,
    JobStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class DeploymentConfig:
    """Configuration for model deployment"""
    batch_size: int = 1
    precision: str = "fp32"  # fp32, fp16, int8
    num_workers: int = 2
    input_format: str = "rgb"
    input_width: int = 640
    input_height: int = 640
    normalize: bool = True
    enable_profiling: bool = False


@dataclass
class DeploymentResult:
    """Result of model deployment"""
    deployment_id: str
    status: str
    message: str = ""
    error: Optional[str] = None


class EdgeNodeManager:
    """Manages edge node registration and lifecycle"""

    async def register_node(
        self,
        db: AsyncSession,
        name: str,
        hardware_model: str,
        cpu_cores: int,
        memory_mb: int,
        owner_id: str,
        ip_address: Optional[str] = None,
        location: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
    ) -> EdgeNode:
        """Register a new edge node"""
        node_id = str(uuid.uuid4())

        node = EdgeNode(
            node_id=node_id,
            name=name,
            hardware_model=hardware_model,
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            ip_address=ip_address,
            location=location,
            capabilities=capabilities,
            owner_id=owner_id,
            status=NodeStatus.ONLINE,
            last_heartbeat=datetime.utcnow(),
        )

        db.add(node)
        await db.commit()
        await db.refresh(node)

        logger.info(f"Registered edge node: {node_id}")
        return node

    async def update_heartbeat(
        self,
        db: AsyncSession,
        node_id: str,
        status: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update node heartbeat"""
        result = await db.execute(
            select(EdgeNode).where(EdgeNode.node_id == node_id)
        )
        node = result.scalar_one_or_none()

        if not node:
            return False

        node.status = status
        node.last_heartbeat = datetime.utcnow()

        if metrics:
            # Store metrics separately
            metrics_record = EdgeMetrics(
                node_id=node_id,
                timestamp=datetime.utcnow(),
                cpu_percent=metrics.get("cpu_percent"),
                memory_percent=metrics.get("memory_percent"),
                memory_used_mb=metrics.get("memory_used_mb"),
                gpu_percent=metrics.get("gpu_percent"),
                gpu_memory_percent=metrics.get("gpu_memory_percent"),
                gpu_temperature=metrics.get("gpu_temperature"),
            )
            db.add(metrics_record)

        await db.commit()
        return True

    async def list_nodes(
        self,
        db: AsyncSession,
        owner_id: str,
        status: Optional[str] = None,
        group: Optional[str] = None,
    ) -> List[EdgeNode]:
        """List edge nodes"""
        query = select(EdgeNode).where(EdgeNode.owner_id == owner_id)

        if status:
            query = query.where(EdgeNode.status == status)
        if group:
            query = query.where(EdgeNode.group == group)

        result = await db.execute(query)
        return result.scalars().all()

    async def get_offline_nodes(
        self,
        db: AsyncSession,
        timeout_seconds: int = 300,
    ) -> List[EdgeNode]:
        """Get nodes that haven't sent heartbeat recently"""
        threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        result = await db.execute(
            select(EdgeNode).where(
                and_(
                    EdgeNode.last_heartbeat < threshold,
                    EdgeNode.status != NodeStatus.OFFLINE,
                )
            )
        )

        return result.scalars().all()


class EdgeDeploymentManager:
    """Manages model deployment to edge nodes"""

    async def deploy_model(
        self,
        db: AsyncSession,
        model_id: str,
        node_id: str,
        name: str,
        config: DeploymentConfig,
        update_strategy: str = "manual",
    ) -> DeploymentResult:
        """
        Deploy a model to an edge node.

        Args:
            db: Database session
            model_id: Model to deploy
            node_id: Target node
            name: Deployment name
            config: Deployment configuration
            update_strategy: Update strategy (manual, rolling, blue_green)

        Returns:
            Deployment result
        """
        # Verify model exists
        model_result = await db.execute(
            select(EdgeModel).where(EdgeModel.model_id == model_id)
        )
        model = model_result.scalar_one_or_none()

        if not model:
            return DeploymentResult(
                deployment_id="",
                status=DeploymentStatus.FAILED,
                error=f"Model {model_id} not found",
            )

        # Verify node exists
        node_result = await db.execute(
            select(EdgeNode).where(EdgeNode.node_id == node_id)
        )
        node = node_result.scalar_one_or_none()

        if not node:
            return DeploymentResult(
                deployment_id="",
                status=DeploymentStatus.FAILED,
                error=f"Node {node_id} not found",
            )

        if node.status != NodeStatus.ONLINE:
            return DeploymentResult(
                deployment_id="",
                status=DeploymentStatus.FAILED,
                error=f"Node {node_id} is not online (status: {node.status})",
            )

        deployment_id = str(uuid.uuid4())

        deployment = EdgeDeployment(
            deployment_id=deployment_id,
            model_id=model_id,
            node_id=node_id,
            name=name,
            status=DeploymentStatus.DEPLOYING,
            config={
                "batch_size": config.batch_size,
                "precision": config.precision,
                "num_workers": config.num_workers,
                "input_format": config.input_format,
                "input_width": config.input_width,
                "input_height": config.input_height,
            },
            update_strategy=update_strategy,
        )

        db.add(deployment)
        await db.commit()

        # Simulate deployment (in production, this would communicate with edge agent)
        await self._execute_deployment(db, deployment, model, node)

        return DeploymentResult(
            deployment_id=deployment_id,
            status=deployment.status,
            message=f"Deployment {deployment_id} {deployment.status}",
        )

    async def _execute_deployment(
        self,
        db: AsyncSession,
        deployment: EdgeDeployment,
        model: EdgeModel,
        node: EdgeNode,
    ) -> None:
        """Execute the actual deployment"""
        try:
            # Simulate deployment process
            await asyncio.sleep(1)

            deployment.status = DeploymentStatus.DEPLOYED
            deployment.deployed_at = datetime.utcnow()
            deployment.health_status = "healthy"
            deployment.last_health_check = datetime.utcnow()

            # Update statistics
            model.deployment_count += 1
            node.deployment_count += 1

            await db.commit()

            logger.info(f"Deployment {deployment.deployment_id} completed successfully")

        except Exception as e:
            logger.error(f"Deployment {deployment.deployment_id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.message = str(e)
            await db.commit()

    async def list_deployments(
        self,
        db: AsyncSession,
        node_id: Optional[str] = None,
        model_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[EdgeDeployment]:
        """List deployments"""
        query = select(EdgeDeployment)

        if node_id:
            query = query.where(EdgeDeployment.node_id == node_id)
        if model_id:
            query = query.where(EdgeDeployment.model_id == model_id)
        if status:
            query = query.where(EdgeDeployment.status == status)

        result = await db.execute(query)
        return result.scalars().all()

    async def delete_deployment(
        self,
        db: AsyncSession,
        deployment_id: str,
    ) -> bool:
        """Delete a deployment"""
        result = await db.execute(
            select(EdgeDeployment).where(EdgeDeployment.deployment_id == deployment_id)
        )
        deployment = result.scalar_one_or_none()

        if not deployment:
            return False

        # Update status to stopped
        deployment.status = DeploymentStatus.STOPPED

        await db.commit()
        return True


class EdgeJobManager:
    """Manages jobs running on edge nodes"""

    async def create_job(
        self,
        db: AsyncSession,
        name: str,
        job_type: str,
        node_id: str,
        config: Dict[str, Any],
        owner_id: str,
        deployment_id: Optional[str] = None,
        schedule_cron: Optional[str] = None,
    ) -> EdgeJob:
        """Create a new edge job"""
        job_id = str(uuid.uuid4())

        job = EdgeJob(
            job_id=job_id,
            name=name,
            job_type=job_type,
            node_id=node_id,
            deployment_id=deployment_id,
            config=config,
            schedule_cron=schedule_cron,
            owner_id=owner_id,
            status=JobStatus.PENDING,
        )

        db.add(job)
        await db.commit()
        await db.refresh(job)

        return job

    async def start_job(
        self,
        db: AsyncSession,
        job_id: str,
    ) -> bool:
        """Start a job"""
        result = await db.execute(
            select(EdgeJob).where(EdgeJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job or job.status != JobStatus.PENDING:
            return False

        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()

        await db.commit()

        # Trigger job execution on edge node
        # In production, this would send command to edge agent
        return True

    async def update_job_progress(
        self,
        db: AsyncSession,
        job_id: str,
        progress: float,
        current_step: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update job progress"""
        result_obj = await db.execute(
            select(EdgeJob).where(EdgeJob.job_id == job_id)
        )
        job = result_obj.scalar_one_or_none()

        if not job:
            return False

        job.progress = progress
        if current_step:
            job.current_step = current_step
        if result:
            job.result = result

        if progress >= 100:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(
                (datetime.utcnow() - job.started_at).total_seconds()
            ) if job.started_at else None

        await db.commit()
        return True

    async def list_jobs(
        self,
        db: AsyncSession,
        node_id: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> List[EdgeJob]:
        """List edge jobs"""
        query = select(EdgeJob)

        if node_id:
            query = query.where(EdgeJob.node_id == node_id)
        if status:
            query = query.where(EdgeJob.status == status)
        if owner_id:
            query = query.where(EdgeJob.owner_id == owner_id)

        query = query.order_by(EdgeJob.created_at.desc())

        result = await db.execute(query)
        return result.scalars().all()


class EdgeMetricsCollector:
    """Collects and aggregates edge metrics"""

    async def record_inference(
        self,
        db: AsyncSession,
        deployment_id: str,
        node_id: str,
        output: Dict[str, Any],
        latency_ms: int,
        pre_processing_ms: Optional[int] = None,
        inference_ms: Optional[int] = None,
        post_processing_ms: Optional[int] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record inference result"""
        result_id = str(uuid.uuid4())

        result = EdgeInferenceResult(
            id=result_id,
            deployment_id=deployment_id,
            node_id=node_id,
            timestamp=datetime.utcnow(),
            output=output,
            latency_ms=latency_ms,
            pre_processing_ms=pre_processing_ms,
            inference_ms=inference_ms,
            post_processing_ms=post_processing_ms,
            input_data=input_data,
        )

        db.add(result)

        # Update deployment statistics
        deployment_result = await db.execute(
            select(EdgeDeployment).where(
                EdgeDeployment.deployment_id == deployment_id
            )
        )
        deployment = deployment_result.scalar_one_or_none()

        if deployment:
            deployment.inference_count += 1
            deployment.total_latency_ms += latency_ms

        await db.commit()

        return result_id

    async def get_node_metrics(
        self,
        db: AsyncSession,
        node_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[EdgeMetrics]:
        """Get metrics for a node"""
        query = select(EdgeMetrics).where(EdgeMetrics.node_id == node_id)

        if start_time:
            query = query.where(EdgeMetrics.timestamp >= start_time)
        if end_time:
            query = query.where(EdgeMetrics.timestamp <= end_time)

        query = query.order_by(EdgeMetrics.timestamp.desc()).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    async def aggregate_metrics(
        self,
        db: AsyncSession,
        node_id: str,
        deployment_id: Optional[str] = None,
        hours: int = 24,
    ) -> Dict[str, Any]:
        """Aggregate metrics for a time period"""
        start_time = datetime.utcnow() - timedelta(hours=hours)

        query = select(EdgeMetrics).where(
            and_(
                EdgeMetrics.node_id == node_id,
                EdgeMetrics.timestamp >= start_time,
            )
        )

        if deployment_id:
            query = query.where(EdgeMetrics.deployment_id == deployment_id)

        result = await db.execute(query)
        metrics = result.scalars().all()

        if not metrics:
            return {}

        # Calculate aggregates
        cpu_values = [m.cpu_percent for m in metrics if m.cpu_percent is not None]
        memory_values = [m.memory_percent for m in metrics if m.memory_percent is not None]
        gpu_values = [m.gpu_percent for m in metrics if m.gpu_percent is not None]

        return {
            "node_id": node_id,
            "period_hours": hours,
            "samples": len(metrics),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else None,
                "max": max(cpu_values) if cpu_values else None,
                "min": min(cpu_values) if cpu_values else None,
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values) if memory_values else None,
                "max": max(memory_values) if memory_values else None,
                "min": min(memory_values) if memory_values else None,
            },
            "gpu": {
                "avg": sum(gpu_values) / len(gpu_values) if gpu_values else None,
                "max": max(gpu_values) if gpu_values else None,
                "min": min(gpu_values) if gpu_values else None,
            },
        }


# Global managers
_node_manager: Optional[EdgeNodeManager] = None
_deployment_manager: Optional[EdgeDeploymentManager] = None
_job_manager: Optional[EdgeJobManager] = None
_metrics_collector: Optional[EdgeMetricsCollector] = None


def get_node_manager() -> EdgeNodeManager:
    global _node_manager
    if _node_manager is None:
        _node_manager = EdgeNodeManager()
    return _node_manager


def get_deployment_manager() -> EdgeDeploymentManager:
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = EdgeDeploymentManager()
    return _deployment_manager


def get_job_manager() -> EdgeJobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = EdgeJobManager()
    return _job_manager


def get_metrics_collector() -> EdgeMetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = EdgeMetricsCollector()
    return _metrics_collector
