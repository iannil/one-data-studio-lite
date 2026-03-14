"""
Jupyter Hub Manager for One Data Studio Lite

Manages communication with Jupyter Hub API.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from httpx import AsyncClient, HTTPError, TimeoutException

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NotebookServer:
    """Notebook server information"""

    name: str
    user: str
    state: str  # running, stopped, error
    image: str
    cpu_limit: float
    mem_limit: str
    gpu_limit: int
    url: Optional[str] = None
    pod_name: Optional[str] = None
    created_at: Optional[str] = None
    last_activity: Optional[str] = None


class JupyterHubManager:
    """
    Jupyter Hub API client

    Manages notebook servers through Jupyter Hub REST API.
    """

    def __init__(
        self,
        hub_url: str = None,
        api_token: str = None,
    ):
        """
        Initialize Jupyter Hub manager

        Args:
            hub_url: Jupyter Hub API URL
            api_token: Jupyter Hub API token
        """
        self.hub_url = hub_url or settings.JUPYTERHUB_API_URL
        self.api_token = api_token or settings.JUPYTERHUB_API_TOKEN
        self.client = AsyncClient(
            base_url=self.hub_url,
            headers={"Authorization": f"token {self.api_token}"},
            timeout=30.0,
        )

    async def get_users(self) -> List[Dict[str, Any]]:
        """
        Get all users from Jupyter Hub

        Returns:
            List of user dictionaries
        """
        try:
            response = await self.client.get("/api/users")
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to get users: {e}")
            raise
        except TimeoutException:
            logger.error("Timeout while getting users")
            raise

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific user from Jupyter Hub

        Args:
            username: Username

        Returns:
            User dictionary or None
        """
        try:
            response = await self.client.get(f"/api/users/{username}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to get user {username}: {e}")
            raise

    async def create_user(
        self,
        username: str,
        password: Optional[str] = None,
        admin: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new user in Jupyter Hub

        Args:
            username: Username
            password: User password (for dummy auth)
            admin: Whether user is admin

        Returns:
            Created user dictionary
        """
        try:
            data = {"name": username, "admin": admin}
            response = await self.client.post("/api/users", json=data)
            response.raise_for_status()
            logger.info(f"Created user: {username}")
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to create user {username}: {e}")
            raise

    async def delete_user(self, username: str) -> bool:
        """
        Delete a user from Jupyter Hub

        Args:
            username: Username

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(f"/api/users/{username}")
            response.raise_for_status()
            logger.info(f"Deleted user: {username}")
            return True
        except HTTPError as e:
            logger.error(f"Failed to delete user {username}: {e}")
            raise

    async def start_server(
        self,
        username: str,
        server_name: str = "",
        spawner_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start a notebook server for a user

        Args:
            username: Username
            server_name: Server name (for named servers)
            spawner_config: Spawner configuration overrides

        Returns:
            Server information
        """
        try:
            # Build spawn request
            data = {}
            if spawner_config:
                data["spawner_config"] = spawner_config

            # Start the server
            response = await self.client.post(
                f"/api/users/{username}/servers/{server_name}",
                json=data if data else None,
            )
            response.raise_for_status()
            logger.info(f"Started server for user {username}")
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to start server for user {username}: {e}")
            raise

    async def stop_server(
        self,
        username: str,
        server_name: str = "",
    ) -> bool:
        """
        Stop a notebook server for a user

        Args:
            username: Username
            server_name: Server name

        Returns:
            True if successful
        """
        try:
            response = await self.client.delete(
                f"/api/users/{username}/servers/{server_name}"
            )
            response.raise_for_status()
            logger.info(f"Stopped server for user {username}")
            return True
        except HTTPError as e:
            logger.error(f"Failed to stop server for user {username}: {e}")
            raise

    async def get_server(
        self,
        username: str,
        server_name: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Get server information for a user

        Args:
            username: Username
            server_name: Server name

        Returns:
            Server information or None
        """
        try:
            response = await self.client.get(
                f"/api/users/{username}/servers/{server_name}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to get server for user {username}: {e}")
            raise

    async def list_servers(self, username: str) -> List[Dict[str, Any]]:
        """
        List all servers for a user

        Args:
            username: Username

        Returns:
            List of server dictionaries
        """
        try:
            response = await self.client.get(f"/api/users/{username}")
            response.raise_for_status()
            user_data = response.json()
            return user_data.get("servers", [])
        except HTTPError as e:
            logger.error(f"Failed to list servers for user {username}: {e}")
            raise

    async def get_server_progress(
        self,
        username: str,
        server_name: str = "",
    ) -> Dict[str, Any]:
        """
        Get server spawn progress

        Args:
            username: Username
            server_name: Server name

        Returns:
            Progress information
        """
        try:
            response = await self.client.get(
                f"/api/users/{username}/servers/{server_name}/progress"
            )
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            logger.error(f"Failed to get progress for user {username}: {e}")
            raise

    async def check_server_ready(
        self,
        username: str,
        server_name: str = "",
        timeout: float = 600.0,
    ) -> bool:
        """
        Check if a server is ready

        Args:
            username: Username
            server_name: Server name
            timeout: Maximum time to wait in seconds

        Returns:
            True if server is ready
        """
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            try:
                server = await self.get_server(username, server_name)
                if server and server.get("ready", False):
                    return True

                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Server ready check timed out for user {username}")
                    return False

                # Wait before retry
                await asyncio.sleep(5)

            except Exception as e:
                logger.warning(f"Error checking server ready: {e}")
                await asyncio.sleep(5)

    async def get_user_quota(self, username: str) -> Dict[str, Any]:
        """
        Get user's resource quota

        This is a platform-specific method that queries the backend
        for user's allocated resources.

        Args:
            username: Username

        Returns:
            Quota dictionary with cpu, memory, gpu keys
        """
        try:
            # This would call the backend API
            # For now, return default quotas
            return {
                "cpu": 4,
                "memory": "8G",
                "gpu": 1,
            }
        except Exception as e:
            logger.warning(f"Failed to get quota for user {username}: {e}")
            return {}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
