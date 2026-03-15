"""
VS Code Server Management Service

Manages VS Code Server instances for online IDE functionality.
"""

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import subprocess
import socket
import os
import tempfile
import shutil

from sqlalchemy.orm import Session

from app.models.notebook import Notebook
from app.core.database import get_db

logger = logging.getLogger(__name__)


class IDEType(str, Enum):
    """IDE type options"""
    JUPYTER = "jupyter"
    VSCODE = "vscode"
    VSCODE_INSIDERS = "vscode-insiders"


class VSCodeStatus(str, Enum):
    """VS Code Server status"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class VSCodeServerConfig:
    """VS Code Server configuration"""
    # Server settings
    version: str = "stable"
    port: Optional[int] = None  # Auto-assign if None
    host: str = "0.0.0.0"
    without_connection_token: bool = False

    # Resource limits
    memory_limit: Optional[str] = None  # e.g., "2G"
    cpu_limit: Optional[str] = None  # e.g., "1"

    # Extension settings
    extensions: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)

    # Security
    enable_password: bool = False
    password: Optional[str] = None

    # Storage
    data_dir: Optional[str] = None
    work_dir: Optional[str] = None


@dataclass
class VSCodeServerInstance:
    """VS Code Server instance"""
    id: str
    notebook_id: int
    user_id: int
    status: VSCodeStatus
    url: str
    port: int
    pid: Optional[int] = None
    config: VSCodeServerConfig = field(default_factory=VSCodeServerConfig)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    error_message: Optional[str] = None

    # Workspace info
    workspace_path: Optional[str] = None
    git_enabled: bool = False


class VSCodeManager:
    """
    VS Code Server Manager

    Manages lifecycle of VS Code Server instances.
    """

    def __init__(self):
        self.instances: Dict[str, VSCodeServerInstance] = {}
        self._port_range = (8000, 9000)
        self._used_ports: set = set()
        self._install_dir = "/tmp/vscode-server-install"
        self._server_binary = "/tmp/vscode-server/bin/code-server"

    async def get_instance(self, instance_id: str) -> Optional[VSCodeServerInstance]:
        """Get VS Code instance by ID"""
        return self.instances.get(instance_id)

    async def list_instances(
        self,
        user_id: Optional[int] = None,
        status: Optional[VSCodeStatus] = None,
    ) -> List[VSCodeServerInstance]:
        """List VS Code instances with optional filters"""
        instances = list(self.instances.values())

        if user_id:
            instances = [i for i in instances if i.user_id == user_id]

        if status:
            instances = [i for i in instances if i.status == status]

        return instances

    def _get_available_port(self) -> int:
        """Get an available port for VS Code Server"""
        for port in range(self._port_range[0], self._port_range[1]):
            if port not in self._used_ports:
                # Check if port is actually available
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.bind(("127.0.0.1", port))
                    sock.close()
                    self._used_ports.add(port)
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports for VS Code Server")

    def _release_port(self, port: int) -> None:
        """Release a port"""
        self._used_ports.discard(port)

    def _create_instance_dir(self, instance_id: str) -> str:
        """Create directory for VS Code instance"""
        base_dir = "/tmp/vscode-instances"
        instance_dir = os.path.join(base_dir, instance_id)
        os.makedirs(instance_dir, exist_ok=True)

        # Create subdirectories
        os.makedirs(os.path.join(instance_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(instance_dir, "workspace"), exist_ok=True)

        return instance_dir

    async def create_instance(
        self,
        notebook_id: int,
        user_id: int,
        config: Optional[VSCodeServerConfig] = None,
    ) -> VSCodeServerInstance:
        """Create a new VS Code Server instance"""
        instance_id = f"vscode-{notebook_id}-{user_id}"

        # Check if instance already exists
        if instance_id in self.instances:
            existing = self.instances[instance_id]
            if existing.status == VSCodeStatus.RUNNING:
                return existing
            else:
                # Clean up existing instance
                await self.stop_instance(instance_id)

        # Create configuration
        if config is None:
            config = VSCodeServerConfig()

        # Get available port
        port = config.port or self._get_available_port()

        # Create instance directory
        instance_dir = self._create_instance_dir(instance_id)

        # Create workspace
        workspace_path = os.path.join(instance_dir, "workspace")

        # Create instance
        instance = VSCodeServerInstance(
            id=instance_id,
            notebook_id=notebook_id,
            user_id=user_id,
            status=VSCodeStatus.STARTING,
            url=f"http://localhost:{port}",
            port=port,
            config=config,
            workspace_path=workspace_path,
        )

        self.instances[instance_id] = instance
        return instance

    async def start_instance(self, instance_id: str) -> Tuple[bool, str]:
        """Start a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False, "Instance not found"

        if instance.status == VSCodeStatus.RUNNING:
            return True, "Already running"

        try:
            instance.status = VSCodeStatus.STARTING

            # Prepare environment
            env = os.environ.copy()
            env["VSCODE_AGENT_FOLDER"] = instance.config.data_dir or "/tmp/vscode-server"

            # Prepare command
            # For production, this would use code-server or a similar solution
            # Here we simulate the process
            cmd = self._build_start_command(instance)

            logger.info(f"Starting VS Code Server for {instance_id}: {' '.join(cmd)}")

            # In a real implementation, we would start the actual code-server process
            # For now, we'll simulate the startup
            await asyncio.sleep(2)  # Simulate startup time

            instance.status = VSCodeStatus.RUNNING
            instance.started_at = datetime.utcnow()
            instance.last_heartbeat = datetime.utcnow()

            return True, "VS Code Server started successfully"

        except Exception as e:
            logger.error(f"Failed to start VS Code Server: {e}")
            instance.status = VSCodeStatus.ERROR
            instance.error_message = str(e)
            return False, str(e)

    def _build_start_command(self, instance: VSCodeServerInstance) -> List[str]:
        """Build the command to start VS Code Server"""
        cmd = []

        # In production, this would be the actual code-server command
        cmd.extend(["code-server"])

        # Bind address
        cmd.extend(["--bind-addr", f"{instance.config.host}:{instance.port}"])

        # Auth
        if instance.config.without_connection_token:
            cmd.append("--without-connection-token")
        elif instance.config.enable_password and instance.config.password:
            cmd.extend(["--password", instance.config.password])

        # User data dir
        if instance.config.data_dir:
            cmd.extend(["--user-data-dir", instance.config.data_dir])

        # Workspace
        if instance.workspace_path:
            cmd.append(instance.workspace_path)

        return cmd

    async def stop_instance(self, instance_id: str) -> Tuple[bool, str]:
        """Stop a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False, "Instance not found"

        try:
            instance.status = VSCodeStatus.STOPPING

            # Kill process if running
            if instance.pid:
                try:
                    os.kill(instance.pid, 15)  # SIGTERM
                    await asyncio.sleep(2)

                    # Force kill if still running
                    try:
                        os.kill(instance.pid, 9)  # SIGKILL
                    except ProcessLookupError:
                        pass
                except ProcessLookupError:
                    pass

            # Release port
            self._release_port(instance.port)

            # Update status
            instance.status = VSCodeStatus.STOPPED
            instance.pid = None

            return True, "VS Code Server stopped successfully"

        except Exception as e:
            logger.error(f"Failed to stop VS Code Server: {e}")
            instance.status = VSCodeStatus.ERROR
            instance.error_message = str(e)
            return False, str(e)

    async def delete_instance(self, instance_id: str, remove_data: bool = False) -> Tuple[bool, str]:
        """Delete a VS Code Server instance"""
        # Stop instance first
        await self.stop_instance(instance_id)

        instance = self.instances.get(instance_id)
        if not instance:
            return False, "Instance not found"

        try:
            # Remove instance directory if requested
            if remove_data:
                instance_dir = os.path.join("/tmp/vscode-instances", instance_id)
                if os.path.exists(instance_dir):
                    shutil.rmtree(instance_dir)

            # Remove from memory
            del self.instances[instance_id]

            return True, "VS Code Server deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete VS Code Server: {e}")
            return False, str(e)

    async def restart_instance(self, instance_id: str) -> Tuple[bool, str]:
        """Restart a VS Code Server instance"""
        # Stop the instance
        await self.stop_instance(instance_id)

        # Wait a moment
        await asyncio.sleep(1)

        # Start again
        return await self.start_instance(instance_id)

    async def get_instance_logs(
        self,
        instance_id: str,
        lines: int = 100,
    ) -> List[str]:
        """Get logs from a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return []

        # In a real implementation, this would read from the actual log file
        # For now, return mock logs
        return [
            f"[INFO] VS Code Server starting on port {instance.port}",
            f"[INFO] Workspace: {instance.workspace_path}",
            f"[INFO] Extensions loaded: {', '.join(instance.config.extensions)}",
            "[INFO] Server ready",
        ]

    async def send_command_to_instance(
        self,
        instance_id: str,
        command: str,
    ) -> Tuple[bool, str]:
        """Send a command to a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False, "Instance not found"

        if instance.status != VSCodeStatus.RUNNING:
            return False, "Instance is not running"

        # Commands could include: open_file, install_extension, etc.
        logger.info(f"Sending command to {instance_id}: {command}")

        # In a real implementation, this would communicate with the VS Code Server API
        return True, "Command sent successfully"

    async def install_extension(
        self,
        instance_id: str,
        extension_id: str,
    ) -> Tuple[bool, str]:
        """Install an extension in a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False, "Instance not found"

        # Add to config
        if extension_id not in instance.config.extensions:
            instance.config.extensions.append(extension_id)

        # In a real implementation, this would run code-server --install-extension
        command = f"install_extension:{extension_id}"
        return await self.send_command_to_instance(instance_id, command)

    async def get_instance_status(
        self,
        instance_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get detailed status of a VS Code Server instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return None

        # Check if process is still running
        is_alive = False
        if instance.pid:
            try:
                os.kill(instance.pid, 0)  # Check if process exists
                is_alive = True
            except ProcessLookupError:
                pass

        return {
            "id": instance.id,
            "notebook_id": instance.notebook_id,
            "user_id": instance.user_id,
            "status": instance.status.value if is_alive else VSCodeStatus.STOPPED.value,
            "url": instance.url,
            "port": instance.port,
            "workspace_path": instance.workspace_path,
            "created_at": instance.created_at.isoformat(),
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "last_heartbeat": instance.last_heartbeat.isoformat() if instance.last_heartbeat else None,
            "extensions": instance.config.extensions,
            "is_alive": is_alive,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all instances"""
        now = datetime.utcnow()
        healthy_count = 0
        unhealthy_count = 0
        stale_instances = []

        for instance_id, instance in self.instances.items():
            if instance.status == VSCodeStatus.RUNNING:
                # Check heartbeat
                if instance.last_heartbeat:
                    heartbeat_age = (now - instance.last_heartbeat).total_seconds()
                    if heartbeat_age > 300:  # 5 minutes
                        stale_instances.append(instance_id)
                        unhealthy_count += 1
                    else:
                        healthy_count += 1
                else:
                    unhealthy_count += 1

        return {
            "total_instances": len(self.instances),
            "healthy_instances": healthy_count,
            "unhealthy_instances": unhealthy_count,
            "stale_instances": stale_instances,
        }

    async def cleanup_stale_instances(self, max_age_minutes: int = 60) -> int:
        """Clean up instances that haven't been used recently"""
        now = datetime.utcnow()
        max_age = timedelta(minutes=max_age_minutes)
        cleaned = 0

        for instance_id, instance in list(self.instances.items()):
            if instance.last_heartbeat:
                age = now - instance.last_heartbeat
                if age > max_age and instance.status != VSCodeStatus.RUNNING:
                    await self.delete_instance(instance_id, remove_data=True)
                    cleaned += 1

        return cleaned


# Global VS Code manager instance
_vscode_manager: Optional[VSCodeManager] = None


def get_vscode_manager() -> VSCodeManager:
    """Get the global VS Code manager instance"""
    global _vscode_manager
    if _vscode_manager is None:
        _vscode_manager = VSCodeManager()
    return _vscode_manager
