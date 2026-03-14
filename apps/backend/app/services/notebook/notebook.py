"""
Notebook Service for One Data Studio Lite

High-level service for managing Jupyter notebooks.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .hub_manager import JupyterHubManager, NotebookServer
from .spawner import SpawnerConfig, ResourceProfile, NotebookImage

logger = logging.getLogger(__name__)


class NotebookService:
    """
    Notebook service

    Provides high-level operations for managing notebook servers,
    including CRUD operations, lifecycle management, and integration
    with the platform's user and quota systems.
    """

    def __init__(
        self,
        hub_url: str = None,
        api_token: str = None,
    ):
        """
        Initialize notebook service

        Args:
            hub_url: Jupyter Hub API URL
            api_token: Jupyter Hub API token
        """
        self.hub = JupyterHubManager(hub_url, api_token)

    async def list_notebooks(
        self,
        username: Optional[str] = None,
    ) -> List[NotebookServer]:
        """
        List notebook servers

        Args:
            username: Filter by username (if None, list all for admin)

        Returns:
            List of notebook servers
        """
        try:
            if username:
                # Get servers for specific user
                servers = await self.hub.list_servers(username)
                result = []
                for name, server in servers.items():
                    result.append(self._to_notebook_server(username, name, server))
                return result
            else:
                # Get all users and their servers
                users = await self.hub.get_users()
                result = []
                for user in users:
                    user_name = user["name"]
                    servers = user.get("servers", {})
                    for name, server in servers.items():
                        result.append(
                            self._to_notebook_server(user_name, name, server)
                        )
                return result
        except Exception as e:
            logger.error(f"Failed to list notebooks: {e}")
            raise

    async def get_notebook(
        self,
        username: str,
        server_name: str = "",
    ) -> Optional[NotebookServer]:
        """
        Get a notebook server

        Args:
            username: Username
            server_name: Server name

        Returns:
            Notebook server or None
        """
        try:
            server = await self.hub.get_server(username, server_name)
            if server:
                return self._to_notebook_server(username, server_name, server)
            return None
        except Exception as e:
            logger.error(f"Failed to get notebook for user {username}: {e}")
            raise

    async def create_notebook(
        self,
        username: str,
        image_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        server_name: str = "",
    ) -> NotebookServer:
        """
        Create a new notebook server

        Args:
            username: Username
            image_id: Notebook image ID
            profile_id: Resource profile ID
            server_name: Server name (for named servers)

        Returns:
            Created notebook server
        """
        try:
            # Get user quota
            quota = await self.hub.get_user_quota(username)

            # Calculate spawner configuration
            spawner_config = SpawnerConfig.calculate_spawner_config(
                image_id=image_id,
                profile_id=profile_id,
                user_quota=quota,
            )

            # Start the server
            await self.hub.start_server(username, server_name, spawner_config)

            # Wait for server to be ready
            await self.hub.check_server_ready(username, server_name)

            # Get server info
            server = await self.hub.get_server(username, server_name)

            return self._to_notebook_server(
                username,
                server_name,
                server or {},
                spawner_config,
            )
        except Exception as e:
            logger.error(f"Failed to create notebook for user {username}: {e}")
            raise

    async def start_notebook(
        self,
        username: str,
        server_name: str = "",
    ) -> bool:
        """
        Start a stopped notebook server

        Args:
            username: Username
            server_name: Server name

        Returns:
            True if successful
        """
        try:
            await self.hub.start_server(username, server_name)
            return True
        except Exception as e:
            logger.error(f"Failed to start notebook for user {username}: {e}")
            raise

    async def stop_notebook(
        self,
        username: str,
        server_name: str = "",
    ) -> bool:
        """
        Stop a running notebook server

        Args:
            username: Username
            server_name: Server name

        Returns:
            True if successful
        """
        try:
            await self.hub.stop_server(username, server_name)
            return True
        except Exception as e:
            logger.error(f"Failed to stop notebook for user {username}: {e}")
            raise

    async def delete_notebook(
        self,
        username: str,
        server_name: str = "",
    ) -> bool:
        """
        Delete a notebook server

        Args:
            username: Username
            server_name: Server name

        Returns:
            True if successful
        """
        try:
            # Stop the server first
            await self.stop_notebook(username, server_name)
            return True
        except Exception as e:
            logger.error(f"Failed to delete notebook for user {username}: {e}")
            raise

    async def get_notebook_progress(
        self,
        username: str,
        server_name: str = "",
    ) -> Dict[str, Any]:
        """
        Get notebook spawn progress

        Args:
            username: Username
            server_name: Server name

        Returns:
            Progress information
        """
        try:
            return await self.hub.get_server_progress(username, server_name)
        except Exception as e:
            logger.error(f"Failed to get progress for user {username}: {e}")
            raise

    async def list_available_images(
        self,
        gpu_available: bool = False,
    ) -> List[NotebookImage]:
        """
        List available notebook images

        Args:
            gpu_available: Whether GPU is available

        Returns:
            List of notebook images
        """
        return SpawnerConfig.get_available_images(gpu_available)

    async def list_available_profiles(
        self,
        gpu_available: bool = False,
    ) -> List[ResourceProfile]:
        """
        List available resource profiles

        Args:
            gpu_available: Whether GPU is available

        Returns:
            List of resource profiles
        """
        return SpawnerConfig.get_available_profiles(gpu_available)

    def _to_notebook_server(
        self,
        username: str,
        server_name: str,
        server_data: Dict[str, Any],
        spawner_config: Optional[Dict[str, Any]] = None,
    ) -> NotebookServer:
        """
        Convert hub server data to NotebookServer

        Args:
            username: Username
            server_name: Server name
            server_data: Server data from hub
            spawner_config: Spawner configuration used

        Returns:
            NotebookServer instance
        """
        # Get image from spawner config or server data
        image = (
            spawner_config.get("image_spec", "")
            if spawner_config
            else server_data.get("image", "one-data-studio/notebook-pytorch:latest")
        )

        # Get resource limits
        cpu_limit = (
            spawner_config.get("cpu_limit", 2)
            if spawner_config
            else server_data.get("cpu_limit", 2)
        )
        mem_limit = (
            spawner_config.get("mem_limit", "4G")
            if spawner_config
            else server_data.get("mem_limit", "4G")
        )
        gpu_limit = (
            spawner_config.get("extra_resource_limits", {}).get("nvidia.com/gpu", "0")
            if spawner_config
            else server_data.get("gpu_limit", 0)
        )

        # Convert GPU limit to int
        if isinstance(gpu_limit, str):
            gpu_limit = int(gpu_limit)

        # Determine state
        state = "running"
        if not server_data.get("ready", True):
            state = "pending"
        elif server_data.get("pending", False):
            state = "starting"

        # Build URL
        url = None
        if server_data.get("ready", False):
            base_url = server_data.get("url", "")
            url = f"{base_url}{server_name}" if server_name else base_url

        return NotebookServer(
            name=server_name or "default",
            user=username,
            state=state,
            image=image,
            cpu_limit=cpu_limit,
            mem_limit=mem_limit,
            gpu_limit=gpu_limit,
            url=url,
            pod_name=server_data.get("pod_name"),
            created_at=server_data.get("started"),
            last_activity=server_data.get("last_activity"),
        )

    async def close(self):
        """Close the service and underlying connections"""
        await self.hub.close()
