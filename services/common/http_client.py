"""HTTP 客户端工具 - 服务间通信"""

from typing import Any

import httpx


class ServiceClient:
    """异步 HTTP 客户端封装，用于服务间调用"""

    def __init__(self, base_url: str, timeout: float = 30.0, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token = token

    def _headers(self, extra: dict | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    async def get(self, path: str, params: dict | None = None, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, data: dict | None = None, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}{path}",
                json=data,
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    async def put(self, path: str, data: dict | None = None, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.put(
                f"{self.base_url}{path}",
                json=data,
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete(self, path: str, **kwargs) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                f"{self.base_url}{path}",
                headers=self._headers(),
                **kwargs,
            )
            resp.raise_for_status()
            return resp.json()

    async def health_check(self) -> bool:
        """检查目标服务健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


# 预定义的服务客户端工厂
def create_cube_studio_client(base_url: str = "http://localhost:30080") -> ServiceClient:
    return ServiceClient(base_url)


def create_superset_client(base_url: str = "http://localhost:8088") -> ServiceClient:
    return ServiceClient(base_url)


def create_datahub_client(base_url: str = "http://localhost:8081") -> ServiceClient:
    return ServiceClient(base_url)


def create_dolphinscheduler_client(base_url: str = "http://localhost:12345") -> ServiceClient:
    return ServiceClient(base_url)


def create_seatunnel_client(base_url: str = "http://localhost:5801") -> ServiceClient:
    return ServiceClient(base_url)
