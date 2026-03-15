"""
IDE Management API Endpoints

Provides endpoints for managing VS Code Server instances and terminal sessions.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.ide import (
    get_vscode_manager,
    get_terminal_manager,
    IDEType,
    VSCodeServerConfig,
    VSCodeStatus,
    TerminalStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ide", tags=["IDE"])


# ============================================================================
# Request/Response Models
# ============================================================================


class VSCodeConfigCreate(BaseModel):
    """Request model for creating VS Code config"""
    version: str = "stable"
    port: Optional[int] = None
    host: str = "0.0.0.0"
    without_connection_token: bool = False
    memory_limit: Optional[str] = None
    cpu_limit: Optional[str] = None
    extensions: List[str] = []
    settings: Dict[str, Any] = {}
    enable_password: bool = False
    password: Optional[str] = None
    data_dir: Optional[str] = None
    work_dir: Optional[str] = None


class VSCodeInstanceResponse(BaseModel):
    """Response model for VS Code instance"""
    id: str
    notebook_id: int
    user_id: int
    status: str
    url: str
    port: int
    workspace_path: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    extensions: List[str] = []


class TerminalSessionCreate(BaseModel):
    """Request model for creating terminal session"""
    notebook_id: int
    shell: str = "/bin/bash"
    rows: int = 24
    cols: int = 80
    cwd: str = "/home/jovyan"
    env_vars: Dict[str, str] = {}


class TerminalInputRequest(BaseModel):
    """Request model for sending terminal input"""
    input: str = Field(..., alias="input")


class TerminalResizeRequest(BaseModel):
    """Request model for resizing terminal"""
    rows: int
    cols: int


class TerminalSessionResponse(BaseModel):
    """Response model for terminal session"""
    id: str
    notebook_id: int
    user_id: int
    status: str
    shell: str
    rows: int
    cols: int
    cwd: str
    created_at: str
    last_activity: str


class TerminalMessage(BaseModel):
    """Terminal output message"""
    id: str
    type: str
    data: str
    timestamp: str


# ============================================================================
# VS Code Server Endpoints
# ============================================================================


@router.post("/vscode", response_model=VSCodeInstanceResponse)
async def create_vscode_instance(
    notebook_id: int,
    config: Optional[VSCodeConfigCreate] = None,
    current_user: User = Depends(get_current_user),
):
    """Create a new VS Code Server instance"""
    manager = get_vscode_manager()

    vscode_config = VSCodeServerConfig(
        version=config.version if config else "stable",
        port=config.port if config else None,
        host=config.host if config else "0.0.0.0",
        without_connection_token=config.without_connection_token if config else False,
        memory_limit=config.memory_limit if config else None,
        cpu_limit=config.cpu_limit if config else None,
        extensions=config.extensions if config else [],
        settings=config.settings if config else {},
        enable_password=config.enable_password if config else False,
        password=config.password if config else None,
        data_dir=config.data_dir if config else None,
        work_dir=config.work_dir if config else None,
    )

    instance = await manager.create_instance(
        notebook_id=notebook_id,
        user_id=current_user.id,
        config=vscode_config,
    )

    return VSCodeInstanceResponse(
        id=instance.id,
        notebook_id=instance.notebook_id,
        user_id=instance.user_id,
        status=instance.status.value,
        url=instance.url,
        port=instance.port,
        workspace_path=instance.workspace_path,
        created_at=instance.created_at.isoformat(),
        started_at=instance.started_at.isoformat() if instance.started_at else None,
        extensions=instance.config.extensions,
    )


@router.post("/vscode/{instance_id}/start")
async def start_vscode_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """Start a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    success, message = await manager.start_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.post("/vscode/{instance_id}/stop")
async def stop_vscode_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """Stop a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    success, message = await manager.stop_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.post("/vscode/{instance_id}/restart")
async def restart_vscode_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """Restart a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    success, message = await manager.restart_instance(instance_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.delete("/vscode/{instance_id}")
async def delete_vscode_instance(
    instance_id: str,
    remove_data: bool = Query(False, description="Remove instance data"),
    current_user: User = Depends(get_current_user),
):
    """Delete a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    success, message = await manager.delete_instance(instance_id, remove_data=remove_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.get("/vscode", response_model=List[VSCodeInstanceResponse])
async def list_vscode_instances(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
):
    """List VS Code Server instances"""
    manager = get_vscode_manager()

    status = None
    if status_filter:
        try:
            status = VSCodeStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    instances = await manager.list_instances(
        user_id=current_user.id,
        status=status,
    )

    return [
        VSCodeInstanceResponse(
            id=i.id,
            notebook_id=i.notebook_id,
            user_id=i.user_id,
            status=i.status.value,
            url=i.url,
            port=i.port,
            workspace_path=i.workspace_path,
            created_at=i.created_at.isoformat(),
            started_at=i.started_at.isoformat() if i.started_at else None,
            extensions=i.config.extensions,
        )
        for i in instances
    ]


@router.get("/vscode/{instance_id}", response_model=Dict[str, Any])
async def get_vscode_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get VS Code Server instance details"""
    manager = get_vscode_manager()

    instance_status = await manager.get_instance_status(instance_id)

    if not instance_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    # Check ownership
    if instance_status["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    return instance_status


@router.get("/vscode/{instance_id}/logs")
async def get_vscode_logs(
    instance_id: str,
    lines: int = Query(100, ge=1, le=1000, description="Number of log lines"),
    current_user: User = Depends(get_current_user),
):
    """Get logs from a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    logs = await manager.get_instance_logs(instance_id, lines=lines)

    return {"logs": logs}


@router.post("/vscode/{instance_id}/extensions/{extension_id}")
async def install_vscode_extension(
    instance_id: str,
    extension_id: str,
    current_user: User = Depends(get_current_user),
):
    """Install an extension in a VS Code Server instance"""
    manager = get_vscode_manager()

    # Get instance to verify ownership
    instance = await manager.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VS Code instance not found"
        )

    if instance.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this instance"
        )

    success, message = await manager.install_extension(instance_id, extension_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


# ============================================================================
# Terminal Endpoints
# ============================================================================


@router.post("/terminal", response_model=TerminalSessionResponse)
async def create_terminal_session(
    session_data: TerminalSessionCreate,
    current_user: User = Depends(get_current_user),
):
    """Create a new terminal session"""
    manager = get_terminal_manager()

    session = await manager.create_session(
        notebook_id=session_data.notebook_id,
        user_id=current_user.id,
        shell=session_data.shell,
        rows=session_data.rows,
        cols=session_data.cols,
        cwd=session_data.cwd,
        env_vars=session_data.env_vars,
    )

    return TerminalSessionResponse(
        id=session.id,
        notebook_id=session.notebook_id,
        user_id=session.user_id,
        status=session.status.value,
        shell=session.shell,
        rows=session.rows,
        cols=session.cols,
        cwd=session.cwd,
        created_at=session.created_at.isoformat(),
        last_activity=session.last_activity.isoformat(),
    )


@router.post("/terminal/{session_id}/input")
async def send_terminal_input(
    session_id: str,
    request: TerminalInputRequest,
    current_user: User = Depends(get_current_user),
):
    """Send input to a terminal session"""
    manager = get_terminal_manager()

    # Get session to verify ownership
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    success, message = await manager.send_input(session_id, request.input)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.post("/terminal/{session_id}/resize")
async def resize_terminal(
    session_id: str,
    request: TerminalResizeRequest,
    current_user: User = Depends(get_current_user),
):
    """Resize a terminal session"""
    manager = get_terminal_manager()

    # Get session to verify ownership
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    success, message = await manager.resize(session_id, request.rows, request.cols)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.get("/terminal/{session_id}/output", response_model=List[TerminalMessage])
async def get_terminal_output(
    session_id: str,
    since: Optional[str] = Query(None, description="Get messages since this ID"),
    current_user: User = Depends(get_current_user),
):
    """Get output from a terminal session"""
    manager = get_terminal_manager()

    # Get session to verify ownership
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    output = await manager.get_output(session_id, since=since)

    return [TerminalMessage(**o) for o in output]


@router.post("/terminal/{session_id}/terminate")
async def terminate_terminal_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Terminate a terminal session"""
    manager = get_terminal_manager()

    # Get session to verify ownership
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    success, message = await manager.terminate_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.delete("/terminal/{session_id}")
async def delete_terminal_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a terminal session"""
    manager = get_terminal_manager()

    # Get session to verify ownership
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    success, message = await manager.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=message
        )

    return {"success": True, "message": message}


@router.get("/terminal", response_model=List[TerminalSessionResponse])
async def list_terminal_sessions(
    notebook_id: Optional[int] = Query(None, description="Filter by notebook ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
):
    """List terminal sessions"""
    manager = get_terminal_manager()

    status = None
    if status_filter:
        try:
            status = TerminalStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )

    sessions = await manager.list_sessions(
        user_id=current_user.id,
        notebook_id=notebook_id,
        status=status,
    )

    return [
        TerminalSessionResponse(
            id=s["id"],
            notebook_id=s["notebook_id"],
            user_id=s["user_id"],
            status=s["status"],
            shell=s["shell"],
            rows=s.get("rows", 24),
            cols=s.get("cols", 80),
            cwd=s.get("cwd", "/home/jovyan"),
            created_at=s["created_at"],
            last_activity=s["last_activity"],
        )
        for s in sessions
    ]


@router.get("/terminal/{session_id}", response_model=Dict[str, Any])
async def get_terminal_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get terminal session details"""
    manager = get_terminal_manager()

    session = await manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal session not found"
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this session"
        )

    return session


# ============================================================================
# System Endpoints
# ============================================================================


@router.get("/health")
async def ide_health_check(
    current_user: User = Depends(get_current_user),
):
    """Get IDE system health status"""
    vscode_manager = get_vscode_manager()
    terminal_manager = get_terminal_manager()

    vscode_health = await vscode_manager.health_check()
    terminal_health = await terminal_manager.health_check()

    return {
        "vscode": vscode_health,
        "terminal": terminal_health,
    }
