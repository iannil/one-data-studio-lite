"""
Cube Studio Client

Main client for interacting with Cube Studio API.
"""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

from .pipeline import Pipeline

logger = logging.getLogger(__name__)


class CubeStudioClient:
    """
    Main client for Cube Studio API
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3101",
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the client

        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
            token: JWT token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._build_headers(api_key, token),
            timeout=timeout,
        )

    def _build_headers(self, api_key: Optional[str], token: Optional[str]) -> Dict[str, str]:
        """Build request headers"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif api_key:
            headers["X-API-Key"] = api_key
            
        return headers

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    # ========================================================================
    # Authentication
    # ========================================================================

    async def login(
        self,
        username: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Login and get authentication token

        Args:
            username: Username
            password: Password

        Returns:
            Login response with token
        """
        response = await self._client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        
        # Update client headers with token
        if "access_token" in data:
            self._client.headers["Authorization"] = f"Bearer {data['access_token']}"
            
        return data

    async def logout(self) -> Dict[str, Any]:
        """Logout and invalidate token"""
        response = await self._client.post("/api/v1/auth/logout")
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Pipelines
    # ========================================================================

    async def create_pipeline(
        self,
        name: str,
        description: Optional[str] = None,
        tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Pipeline:
        """
        Create a new pipeline

        Args:
            name: Pipeline name
            description: Pipeline description
            tasks: List of task configurations

        Returns:
            Created Pipeline
        """
        response = await self._client.post(
            "/api/v1/pipelines",
            json={
                "name": name,
                "description": description,
                "tasks": tasks or [],
            },
        )
        response.raise_for_status()
        data = response.json()
        
        return Pipeline(client=self, **data)

    async def get_pipeline(self, pipeline_id: str) -> Pipeline:
        """
        Get a pipeline by ID

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline object
        """
        response = await self._client.get(f"/api/v1/pipelines/{pipeline_id}")
        response.raise_for_status()
        data = response.json()
        
        return Pipeline(client=self, **data)

    async def list_pipelines(
        self,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all pipelines"""
        params = {"limit": limit}
        if status:
            params["status"] = status
            
        response = await self._client.get("/api/v1/pipelines", params=params)
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Training Jobs
    # ========================================================================

    async def create_training_job(
        self,
        name: str,
        model_type: str,
        dataset_id: str,
        config: Dict[str, Any],
        gpu_count: int = 1,
        gpu_type: str = "T4",
    ) -> Dict[str, Any]:
        """
        Create a training job

        Args:
            name: Job name
            model_type: Type of model to train
            dataset_id: Dataset ID
            config: Training configuration
            gpu_count: Number of GPUs
            gpu_type: GPU type

        Returns:
            Created job info
        """
        response = await self._client.post(
            "/api/v1/training/jobs",
            json={
                "name": name,
                "model_type": model_type,
                "dataset_id": dataset_id,
                "config": config,
                "gpu_count": gpu_count,
                "gpu_type": gpu_type,
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_training_job(self, job_id: str) -> Dict[str, Any]:
        """Get training job status"""
        response = await self._client.get(f"/api/v1/training/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def list_training_jobs(
        self,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List training jobs"""
        params = {"limit": limit}
        if status:
            params["status"] = status
            
        response = await self._client.get("/api/v1/training/jobs", params=params)
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Models
    # ========================================================================

    async def list_models(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List models"""
        response = await self._client.get("/api/v1/models", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get model details"""
        response = await self._client.get(f"/api/v1/models/{model_id}")
        response.raise_for_status()
        return response.json()

    async def register_model(
        self,
        name: str,
        version: str,
        model_type: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Register a model"""
        # Upload model file first, then register
        with open(file_path, "rb") as f:
            files = {"file": f}
            data = {
                "name": name,
                "version": version,
                "model_type": model_type,
                "metadata": json.dumps(metadata or {}),
            }
            response = await self._client.post(
                "/api/v1/models/upload",
                data=data,
                files=files,
            )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # GPU Resources
    # ========================================================================

    async def allocate_gpu(
        self,
        gpu_type: str = "T4",
        count: int = 1,
        task_id: Optional[str] = None,
        ttl_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Allocate GPU resources"""
        response = await self._client.post(
            "/api/v1/gpu/allocate",
            json={
                "spec": {
                    "gpu_type": gpu_type,
                    "vendor": "nvidia",
                    "count": count,
                },
                "task_id": task_id,
                "ttl_minutes": ttl_minutes,
            },
        )
        response.raise_for_status()
        return response.json()

    async def release_gpu(self, allocation_id: str) -> Dict[str, Any]:
        """Release GPU allocation"""
        response = await self._client.delete(f"/api/v1/gpu/allocations/{allocation_id}")
        response.raise_for_status()
        return response.json()

    async def get_gpu_summary(self) -> Dict[str, Any]:
        """Get cluster GPU summary"""
        response = await self._client.get("/api/v1/gpu/summary")
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Algorithm Marketplace
    # ========================================================================

    async def list_algorithms(
        self,
        category: Optional[str] = None,
        framework: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List algorithms from marketplace"""
        params = {"limit": limit}
        if category:
            params["category"] = category
        if framework:
            params["framework"] = framework
        if search:
            params["search"] = search
            
        response = await self._client.get("/api/v1/aihub/algorithms", params=params)
        response.raise_for_status()
        return response.json()

    async def get_algorithm(self, algorithm_id: str) -> Dict[str, Any]:
        """Get algorithm details"""
        response = await self._client.get(f"/api/v1/aihub/algorithms/{algorithm_id}")
        response.raise_for_status()
        return response.json()

    async def deploy_algorithm(
        self,
        algorithm_id: str,
        version: str = "latest",
        instance_type: str = "cpu",
        replicas: int = 1,
    ) -> Dict[str, Any]:
        """Deploy an algorithm"""
        response = await self._client.post(
            "/api/v1/aihub/algorithms/deploy",
            json={
                "algorithm_id": algorithm_id,
                "version": version,
                "instance_type": instance_type,
                "replicas": replicas,
            },
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Data Sources
    # ========================================================================

    async def list_data_sources(
        self,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List data sources"""
        response = await self._client.get("/api/v1/datasources", params={"limit": limit})
        response.raise_for_status()
        return response.json()

    async def test_data_source(self, source_id: str) -> Dict[str, Any]:
        """Test data source connection"""
        response = await self._client.post(f"/api/v1/datasources/{source_id}/test")
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Metrics
    # ========================================================================

    async def calculate_metric(
        self,
        metric_id: str,
        dimensions: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Calculate a metric"""
        response = await self._client.post(
            "/api/v1/metrics/calculate",
            json={
                "metric_id": metric_id,
                "dimensions": dimensions,
                "start_date": start_date,
                "end_date": end_date,
            },
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Health
    # ========================================================================

    async def health(self) -> Dict[str, Any]:
        """Check API health"""
        response = await self._client.get("/api/v1/health")
        return response.json()
