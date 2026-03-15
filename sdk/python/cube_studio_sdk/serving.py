"""
Serving module for SDK

Provides ModelService class for model serving and deployment.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .client import CubeStudioClient

logger = logging.getLogger(__name__)


class ServingStatus(str, Enum):
    """Model serving status"""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServingConfig:
    """Model serving configuration"""
    # Model
    model_id: str
    model_version: str
    
    # Deployment
    replicas: int = 1
    instance_type: str = "cpu"  # cpu, gpu, gpu-multi
    
    # Resources
    cpu_request: str = "500m"
    cpu_limit: str = "2"
    memory_request: str = "2Gi"
    memory_limit: str = "8Gi"
    gpu_count: int = 0
    gpu_type: str = "T4"
    
    # Inference
    batch_size: int = 1
    max_batch_size: int = 32
    batch_timeout_ms: int = 10
    
    # Networking
    port: int = 8080
    enable_auth: bool = False
    
    # Scaling
    min_replicas: int = 1
    max_replicas: int = 5
    target_cpu_utilization: int = 70


class ModelService:
    """
    Model service for managing model serving

    Example:
        ```python
        async with CubeStudioClient() as client:
            service = ModelService(
                client=client,
                name="my-model-service",
                config=ServingConfig(
                    model_id="model-123",
                    model_version="1.0.0",
                    replicas=2,
                    instance_type="gpu",
                )
            )
            
            # Deploy service
            await service.deploy()
            
            # Get endpoint URL
            url = service.endpoint_url
            
            # Make prediction
            result = await service.predict({"data": [1, 2, 3]})
        ```
    """

    def __init__(
        self,
        client: CubeStudioClient,
        name: str,
        config: ServingConfig,
        service_id: Optional[str] = None,
        status: ServingStatus = ServingStatus.PENDING,
        endpoint_url: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.client = client
        self.name = name
        self.config = config
        self.service_id = service_id
        self.status = status
        self.endpoint_url = endpoint_url
        self.created_at = created_at
        self.updated_at = updated_at

    async def deploy(self) -> "ModelService":
        """Deploy the model service"""
        response = await self.client._client.post(
            "/api/v1/serving/services",
            json={
                "name": self.name,
                "model_id": self.config.model_id,
                "model_version": self.config.model_version,
                "replicas": self.config.replicas,
                "instance_type": self.config.instance_type,
                "resources": {
                    "cpu_request": self.config.cpu_request,
                    "cpu_limit": self.config.cpu_limit,
                    "memory_request": self.config.memory_request,
                    "memory_limit": self.config.memory_limit,
                    "gpu_count": self.config.gpu_count,
                    "gpu_type": self.config.gpu_type,
                },
                "inference": {
                    "batch_size": self.config.batch_size,
                    "max_batch_size": self.config.max_batch_size,
                    "batch_timeout_ms": self.config.batch_timeout_ms,
                },
                "networking": {
                    "port": self.config.port,
                    "enable_auth": self.config.enable_auth,
                },
                "scaling": {
                    "min_replicas": self.config.min_replicas,
                    "max_replicas": self.config.max_replicas,
                    "target_cpu_utilization": self.config.target_cpu_utilization,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        
        self.service_id = data["service_id"]
        self.status = ServingStatus(data.get("status", "pending"))
        self.created_at = datetime.now()
        
        # Wait for deployment
        await self._wait_for_running()
        
        return self

    async def _wait_for_running(
        self,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ):
        """Wait for service to be running"""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            await self.refresh()
            
            if self.status == ServingStatus.RUNNING:
                break
            elif self.status == ServingStatus.FAILED:
                raise RuntimeError(f"Service deployment failed: {self.service_id}")
            
            if (asyncio.get_event_loop().time() - start_time) > timeout:
                raise TimeoutError(f"Service deployment timed out: {self.service_id}")
            
            await asyncio.sleep(poll_interval)

    async def refresh(self) -> "ModelService":
        """Refresh service status"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.get(f"/api/v1/serving/services/{self.service_id}")
        response.raise_for_status()
        data = response.json()
        
        self.status = ServingStatus(data.get("status", self.status))
        self.endpoint_url = data.get("endpoint_url")
        self.updated_at = datetime.now()
        
        return self

    async def predict(
        self,
        data: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Make a prediction

        Args:
            data: Input data
            timeout: Request timeout

        Returns:
            Prediction result
        """
        if not self.endpoint_url:
            await self.refresh()
            if not self.endpoint_url:
                raise RuntimeError("Service endpoint not available")
        
        response = await self.client._client.post(
            self.endpoint_url,
            json=data,
            timeout=timeout,
        )
        response.raise_for_status()
        
        return response.json()

    async def predict_batch(
        self,
        batch: List[Dict[str, Any]],
        timeout: float = 60.0,
    ) -> List[Dict[str, Any]]:
        """
        Make batch predictions

        Args:
            batch: List of input data
            timeout: Request timeout

        Returns:
            List of prediction results
        """
        if not self.endpoint_url:
            await self.refresh()
            if not self.endpoint_url:
                raise RuntimeError("Service endpoint not available")
        
        response = await self.client._client.post(
            f"{self.endpoint_url}/batch",
            json={"instances": batch},
            timeout=timeout,
        )
        response.raise_for_status()
        
        return response.json()["predictions"]

    async def scale(self, replicas: int) -> "ModelService":
        """Scale service replicas"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.post(
            f"/api/v1/serving/services/{self.service_id}/scale",
            json={"replicas": replicas},
        )
        response.raise_for_status()
        
        self.config.replicas = replicas
        return self

    async def stop(self) -> bool:
        """Stop the service"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.post(f"/api/v1/serving/services/{self.service_id}/stop")
        response.raise_for_status()
        
        self.status = ServingStatus.STOPPED
        self.endpoint_url = None
        return True

    async def start(self) -> "ModelService":
        """Start a stopped service"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.post(f"/api/v1/serving/services/{self.service_id}/start")
        response.raise_for_status()
        
        await self._wait_for_running()
        return self

    async def delete(self) -> bool:
        """Delete the service"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.delete(f"/api/v1/serving/services/{self.service_id}")
        response.raise_for_status()
        
        self.service_id = None
        self.status = ServingStatus.STOPPED
        self.endpoint_url = None
        return True

    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.get(f"/api/v1/serving/services/{self.service_id}/metrics")
        response.raise_for_status()
        
        return response.json()

    async def get_logs(
        self,
        tail_lines: int = 100,
        follow: bool = False,
    ) -> str:
        """Get service logs"""
        if not self.service_id:
            raise ValueError("Service not deployed yet")
            
        response = await self.client._client.get(
            f"/api/v1/serving/services/{self.service_id}/logs",
            params={"tail": tail_lines, "follow": follow},
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("logs", "")

    def __repr__(self) -> str:
        return f"ModelService(service_id={self.service_id}, name={self.name}, status={self.status})"
