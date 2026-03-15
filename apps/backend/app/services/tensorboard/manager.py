"""
TensorBoard Instance Manager

Manages the lifecycle of TensorBoard instances including creation,
deployment to Kubernetes, and cleanup.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import select, and_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tensorboard import (
    TensorBoardInstance,
    TensorBoardAccessLog,
    TensorBoardConfig,
)
from app.schemas.tensorboard import (
    TensorBoardCreate,
    TensorBoardUpdate,
)

logger = logging.getLogger(__name__)


class TensorBoardManager:
    """
    TensorBoard instance lifecycle manager

    Handles creation, deployment, starting, stopping, and cleanup of
    TensorBoard instances in Kubernetes.
    """

    def __init__(self, db: AsyncSession, k8s_client=None):
        """
        Initialize TensorBoard manager

        Args:
            db: Database session
            k8s_client: Kubernetes client (optional, for testing)
        """
        self.db = db
        self._k8s_client = k8s_client

    @property
    def k8s_client(self):
        """Lazy load Kubernetes client"""
        if self._k8s_client is None:
            from app.services.k8s import get_kubernetes_client
            self._k8s_client = get_kubernetes_client()
        return self._k8s_client

    async def create_instance(
        self,
        data: TensorBoardCreate,
        owner_id: str,
    ) -> TensorBoardInstance:
        """
        Create a new TensorBoard instance

        Args:
            data: Instance creation data
            owner_id: User ID of the owner

        Returns:
            Created TensorBoardInstance
        """
        instance_id = f"tensorboard-{uuid4().hex[:8]}"

        instance = TensorBoardInstance(
            instance_id=instance_id,
            owner_id=owner_id,
            tenant_id=data.tenant_id,
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            log_dir=data.log_dir,
            log_source=data.log_source,
            experiment_id=data.experiment_id,
            run_id=data.run_id,
            training_job_id=data.training_job_id,
            image=data.image,
            port=data.port,
            cpu_limit=data.cpu_limit,
            cpu_request=data.cpu_request,
            memory_limit=data.memory_limit,
            memory_request=data.memory_request,
            service_type=data.service_type,
            namespace=data.namespace,
            auto_stop=data.auto_stop,
            idle_timeout_seconds=data.idle_timeout_seconds,
            labels=data.labels,
            annotations=data.annotations,
            status="pending",
        )

        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info(f"Created TensorBoard instance {instance_id} for user {owner_id}")

        # Start deployment asynchronously
        asyncio.create_task(self._deploy_instance(instance))

        return instance

    async def _deploy_instance(self, instance: TensorBoardInstance) -> None:
        """
        Deploy TensorBoard instance to Kubernetes

        Args:
            instance: TensorBoard instance to deploy
        """
        try:
            # Update status to starting
            instance.status = "starting"
            await self.db.commit()

            # Prepare Kubernetes resources
            namespace = instance.namespace
            pod_name = f"tensorboard-{instance.instance_id}"
            service_name = f"tensorboard-{instance.instance_id}"

            # Create deployment/pod
            await self._create_tensorboard_pod(instance, pod_name, namespace)

            # Create service
            await self._create_tensorboard_service(instance, service_name, pod_name, namespace)

            # Create ingress if needed
            if instance.service_type in ["NodePort", "LoadBalancer"]:
                ingress_name = await self._create_tensorboard_ingress(
                    instance, service_name, namespace
                )
            else:
                ingress_name = None

            # Update instance with Kubernetes resource names
            instance.pod_name = pod_name
            instance.service_name = service_name
            instance.ingress_name = ingress_name
            instance.status = "running"
            instance.started_at = datetime.utcnow()
            instance.internal_url = f"http://{service_name}.{namespace}.svc.cluster.local:{instance.port}"

            await self.db.commit()

            logger.info(f"Deployed TensorBoard instance {instance.instance_id}")

        except Exception as e:
            logger.error(f"Failed to deploy TensorBoard instance {instance.instance_id}: {e}")
            instance.status = "failed"
            instance.status_message = str(e)
            await self.db.commit()

    async def _create_tensorboard_pod(
        self,
        instance: TensorBoardInstance,
        pod_name: str,
        namespace: str,
    ) -> None:
        """Create TensorBoard pod/deployment in Kubernetes"""
        # Prepare logdir based on source
        logdir = self._prepare_logdir(instance)

        # Build pod spec
        pod_spec = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": namespace,
                "labels": {
                    "app": "tensorboard",
                    "tensorboard-id": instance.instance_id,
                    **(instance.labels or {}),
                },
                "annotations": instance.annotations or {},
            },
            "spec": {
                "containers": [{
                    "name": "tensorboard",
                    "image": instance.image,
                    "command": ["tensorboard"],
                    "args": [
                        "--logdir", logdir,
                        "--host", "0.0.0.0",
                        "--port", str(instance.port),
                    ],
                    "ports": [{
                        "containerPort": instance.port,
                        "protocol": "TCP",
                    }],
                    "resources": self._build_resources(instance),
                }],
                "restartPolicy": "Always",
            },
        }

        # Apply to Kubernetes
        await self.k8s_client.create_pod(namespace, pod_spec)

    async def _create_tensorboard_service(
        self,
        instance: TensorBoardInstance,
        service_name: str,
        pod_name: str,
        namespace: str,
    ) -> None:
        """Create Kubernetes service for TensorBoard"""
        service_spec = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": namespace,
                "labels": {
                    "app": "tensorboard",
                    "tensorboard-id": instance.instance_id,
                },
            },
            "spec": {
                "selector": {
                    "app": "tensorboard",
                    "tensorboard-id": instance.instance_id,
                },
                "ports": [{
                    "port": instance.port,
                    "targetPort": instance.port,
                    "protocol": "TCP",
                }],
                "type": instance.service_type,
            },
        }

        await self.k8s_client.create_service(namespace, service_spec)

    async def _create_tensorboard_ingress(
        self,
        instance: TensorBoardInstance,
        service_name: str,
        namespace: str,
    ) -> Optional[str]:
        """Create ingress for external TensorBoard access"""
        ingress_name = f"tensorboard-{instance.instance_id}"

        ingress_spec = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "Ingress",
            "metadata": {
                "name": ingress_name,
                "namespace": namespace,
                "annotations": {
                    "nginx.ingress.kubernetes.io/rewrite-target": "/",
                },
            },
            "spec": {
                "rules": [{
                    "host": f"{instance.instance_id}.tensorboard.example.com",
                    "http": {
                        "paths": [{
                            "path": "/",
                            "pathType": "Prefix",
                            "backend": {
                                "service": {
                                    "name": service_name,
                                    "port": {"number": instance.port},
                                },
                            },
                        }],
                    },
                }],
            },
        }

        await self.k8s_client.create_ingress(namespace, ingress_spec)

        # Set external URL
        instance.external_url = f"http://{instance.instance_id}.tensorboard.example.com"

        return ingress_name

    def _prepare_logdir(self, instance: TensorBoardInstance) -> str:
        """Prepare logdir based on storage source"""
        if instance.log_source == "minio":
            # MinIO/S3 compatible URL
            from app.core.config import settings
            return f"s3://{settings.MINIO_BUCKET}{instance.log_dir}"
        elif instance.log_source == "nfs":
            # NFS mounted path
            return f"/mnt/nfs{instance.log_dir}"
        elif instance.log_source == "s3":
            # AWS S3
            return instance.log_dir
        else:
            return instance.log_dir

    def _build_resources(self, instance: TensorBoardInstance) -> Dict[str, Any]:
        """Build Kubernetes resource requirements"""
        resources = {}

        if instance.cpu_request or instance.cpu_limit:
            requests = {}
            if instance.cpu_request:
                requests["cpu"] = instance.cpu_request
            if instance.memory_request:
                requests["memory"] = instance.memory_request
            resources["requests"] = requests

        if instance.cpu_limit or instance.memory_limit:
            limits = {}
            if instance.cpu_limit:
                limits["cpu"] = instance.cpu_limit
            if instance.memory_limit:
                limits["memory"] = instance.memory_limit
            resources["limits"] = limits

        return resources

    async def get_instance(self, instance_id: str) -> Optional[TensorBoardInstance]:
        """
        Get TensorBoard instance by ID

        Args:
            instance_id: Instance ID

        Returns:
            TensorBoardInstance or None
        """
        result = await self.db.execute(
            select(TensorBoardInstance).where(
                TensorBoardInstance.instance_id == instance_id
            )
        )
        return result.scalar_one_or_none()

    async def list_instances(
        self,
        owner_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        training_job_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[TensorBoardInstance], int]:
        """
        List TensorBoard instances with filtering

        Args:
            owner_id: Filter by owner
            experiment_id: Filter by experiment
            training_job_id: Filter by training job
            status: Filter by status
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            Tuple of (list of instances, total count)
        """
        conditions = []

        if owner_id:
            conditions.append(TensorBoardInstance.owner_id == owner_id)
        if experiment_id:
            conditions.append(TensorBoardInstance.experiment_id == experiment_id)
        if training_job_id:
            conditions.append(TensorBoardInstance.training_job_id == training_job_id)
        if status:
            conditions.append(TensorBoardInstance.status == status)

        query = select(TensorBoardInstance)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(TensorBoardInstance.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Get paginated results
        query = query.order_by(TensorBoardInstance.created_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        instances = result.scalars().all()

        return list(instances), total

    async def stop_instance(self, instance: TensorBoardInstance) -> bool:
        """
        Stop a running TensorBoard instance

        Args:
            instance: Instance to stop

        Returns:
            True if successful
        """
        try:
            # Delete Kubernetes resources
            if instance.pod_name:
                await self.k8s_client.delete_pod(instance.namespace, instance.pod_name)
            if instance.service_name:
                await self.k8s_client.delete_service(instance.namespace, instance.service_name)
            if instance.ingress_name:
                await self.k8s_client.delete_ingress(instance.namespace, instance.ingress_name)

            # Update instance
            instance.status = "stopped"
            instance.stopped_at = datetime.utcnow()

            await self.db.commit()

            logger.info(f"Stopped TensorBoard instance {instance.instance_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop TensorBoard instance {instance.instance_id}: {e}")
            instance.status = "error"
            instance.status_message = str(e)
            await self.db.commit()
            return False

    async def start_instance(self, instance: TensorBoardInstance) -> bool:
        """
        Start a stopped TensorBoard instance

        Args:
            instance: Instance to start

        Returns:
            True if successful
        """
        if instance.status == "running":
            return True

        try:
            instance.status = "pending"
            await self.db.commit()

            # Redeploy
            asyncio.create_task(self._deploy_instance(instance))

            return True

        except Exception as e:
            logger.error(f"Failed to start TensorBoard instance {instance.instance_id}: {e}")
            instance.status = "error"
            instance.status_message = str(e)
            await self.db.commit()
            return False

    async def delete_instance(self, instance: TensorBoardInstance) -> bool:
        """
        Delete a TensorBoard instance

        Args:
            instance: Instance to delete

        Returns:
            True if successful
        """
        try:
            # Stop if running
            if instance.status == "running":
                await self.stop_instance(instance)

            # Delete from database
            await self.db.delete(instance)
            await self.db.commit()

            logger.info(f"Deleted TensorBoard instance {instance.instance_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete TensorBoard instance {instance.instance_id}: {e}")
            await self.db.rollback()
            return False

    async def update_instance(
        self,
        instance: TensorBoardInstance,
        data: TensorBoardUpdate,
    ) -> TensorBoardInstance:
        """
        Update TensorBoard instance

        Args:
            instance: Instance to update
            data: Update data

        Returns:
            Updated instance
        """
        # Update allowed fields
        if data.name is not None:
            instance.name = data.name
        if data.description is not None:
            instance.description = data.description
        if data.auto_stop is not None:
            instance.auto_stop = data.auto_stop
        if data.idle_timeout_seconds is not None:
            instance.idle_timeout_seconds = data.idle_timeout_seconds
        if data.labels is not None:
            instance.labels = data.labels
        if data.annotations is not None:
            instance.annotations = data.annotations

        await self.db.commit()
        await self.db.refresh(instance)

        return instance

    async def log_access(
        self,
        instance_id: str,
        user_id: Optional[str],
        access_type: str = "web",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Log TensorBoard access

        Args:
            instance_id: Instance ID
            user_id: User ID
            access_type: Access type (web, api)
            ip_address: Client IP address
            user_agent: User agent string
        """
        log = TensorBoardAccessLog(
            instance_id=instance_id,
            user_id=user_id,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(log)

        # Update last access time
        await self.db.execute(
            update(TensorBoardInstance)
            .where(TensorBoardInstance.instance_id == instance_id)
            .values(last_access_at=datetime.utcnow())
        )

        await self.db.commit()

    async def get_instance_url(self, instance: TensorBoardInstance) -> str:
        """
        Get access URL for TensorBoard instance

        Args:
            instance: TensorBoard instance

        Returns:
            Access URL
        """
        if instance.external_url:
            return instance.external_url
        elif instance.internal_url:
            return instance.internal_url
        else:
            # Generate proxy URL
            return f"/api/v1/tensorboard/{instance.instance_id}/proxy"

    async def cleanup_idle_instances(self, idle_timeout_minutes: int = 60) -> int:
        """
        Stop idle TensorBoard instances

        Args:
            idle_timeout_minutes: Idle timeout in minutes

        Returns:
            Number of instances stopped
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=idle_timeout_minutes)

        result = await self.db.execute(
            select(TensorBoardInstance).where(
                and_(
                    TensorBoardInstance.status == "running",
                    TensorBoardInstance.auto_stop == True,
                    TensorBoardInstance.last_access_at < cutoff_time,
                )
            )
        )
        instances = result.scalars().all()

        stopped_count = 0
        for instance in instances:
            if await self.stop_instance(instance):
                stopped_count += 1

        logger.info(f"Cleaned up {stopped_count} idle TensorBoard instances")
        return stopped_count

    async def get_statistics(
        self,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get TensorBoard usage statistics

        Args:
            owner_id: Filter by owner (optional)

        Returns:
            Statistics dictionary
        """
        conditions = []

        if owner_id:
            conditions.append(TensorBoardInstance.owner_id == owner_id)

        # Total instances
        total_query = select(func.count(TensorBoardInstance.id))
        if conditions:
            total_query = total_query.where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_instances = total_result.scalar()

        # Running instances
        running_conditions = conditions + [TensorBoardInstance.status == "running"]
        running_query = select(func.count(TensorBoardInstance.id)).where(and_(*running_conditions))
        running_result = await self.db.execute(running_query)
        running_instances = running_result.scalar()

        # Stopped instances
        stopped_conditions = conditions + [TensorBoardInstance.status == "stopped"]
        stopped_query = select(func.count(TensorBoardInstance.id)).where(and_(*stopped_conditions))
        stopped_result = await self.db.execute(stopped_query)
        stopped_instances = stopped_result.scalar()

        # Failed instances
        failed_conditions = conditions + [TensorBoardInstance.status == "failed"]
        failed_query = select(func.count(TensorBoardInstance.id)).where(and_(*failed_conditions))
        failed_result = await self.db.execute(failed_query)
        failed_instances = failed_result.scalar()

        return {
            "total_instances": total_instances,
            "running_instances": running_instances,
            "stopped_instances": stopped_instances,
            "failed_instances": failed_instances,
            "total_usage_hours": 0.0,  # TODO: Calculate from access logs
            "avg_session_duration_minutes": 0.0,  # TODO: Calculate from access logs
        }
