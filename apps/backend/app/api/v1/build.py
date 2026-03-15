"""
Build API Endpoints

Provides REST API for image building, registry management,
and container debugging.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.build import BuildStatus
from app.services.build.image_builder import (
    get_image_builder,
    BuildConfig,
    BaseImage,
    BaseImageType,
    PackageInstall,
    PackageType,
    CustomCommand,
    FileCopy,
    EnvironmentVariable,
    WorkingDir,
    ExposePort,
    BuildResult,
)
from app.services.build.registry_manager import (
    get_registry_manager,
    RegistryConfig,
    RegistryType,
    PushResult,
    PullResult,
)
from app.services.build.debug_service import (
    get_container_debugger,
    ShellType,
    CommandResult,
    DebugSession,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/build", tags=["Build"])


# ============================================================================
# Request/Response Models
# ============================================================================


class BaseImageRequest(BaseModel):
    """Base image configuration"""
    name: str
    tag: str = "latest"
    type: BaseImageType = BaseImageType.CUSTOM
    registry: Optional[str] = None


class PackageInstallRequest(BaseModel):
    """Package installation configuration"""
    package_type: PackageType
    packages: List[str]
    version_constraints: Optional[Dict[str, str]] = None
    upgrade: bool = True


class CustomCommandRequest(BaseModel):
    """Custom command configuration"""
    command: str
    run_as_root: bool = True
    description: Optional[str] = None


class FileCopyRequest(BaseModel):
    """File copy configuration"""
    source_path: str
    destination_path: str
    chown: Optional[str] = None
    chmod: Optional[str] = None


class EnvironmentVarRequest(BaseModel):
    """Environment variable"""
    name: str
    value: str


class WorkingDirRequest(BaseModel):
    """Working directory"""
    path: str
    create: bool = True


class ExposePortRequest(BaseModel):
    """Port to expose"""
    port: int
    protocol: str = "tcp"


class BuildConfigRequest(BaseModel):
    """Complete build configuration"""
    name: str
    base_image: BaseImageRequest
    packages: List[PackageInstallRequest] = []
    commands: List[CustomCommandRequest] = []
    files: List[FileCopyRequest] = []
    env_vars: List[EnvironmentVarRequest] = []
    working_dir: Optional[WorkingDirRequest] = None
    expose_ports: List[ExposePortRequest] = []
    entrypoint: Optional[str] = None
    cmd: Optional[List[str]] = None
    user: Optional[str] = None
    labels: Dict[str, str] = {}
    tag: Optional[str] = None


class BuildResponse(BaseModel):
    """Build response"""
    build_id: str
    image_name: str
    tag: str
    status: str
    created_at: datetime
    error: Optional[str] = None
    image_id: Optional[str] = None
    build_time_ms: int = 0


class BuildListResponse(BaseModel):
    """Build list item"""
    build_id: str
    name: str
    image_name: str
    status: str
    created_at: datetime
    size_bytes: Optional[int] = None


class RegistryConfigRequest(BaseModel):
    """Registry configuration"""
    name: str
    registry: str
    registry_type: RegistryType = RegistryType.DOCKER_HUB
    endpoint: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_public: bool = False


class RegistryResponse(BaseModel):
    """Registry response"""
    id: str
    name: str
    registry: str
    registry_type: str
    endpoint: Optional[str]
    is_public: bool
    created_at: datetime


class PushImageRequest(BaseModel):
    """Push image request"""
    local_image: str
    target_tag: Optional[str] = None


class PullImageRequest(BaseModel):
    """Pull image request"""
    image_name: str
    tag: str = "latest"


class DebugSessionRequest(BaseModel):
    """Start debug session request"""
    container_id: str
    shell_type: ShellType = ShellType.BASH
    timeout_minutes: int = 30


class DebugSessionResponse(BaseModel):
    """Debug session response"""
    session_id: str
    container_id: str
    container_name: str
    shell_type: str
    status: str
    created_at: datetime


class CommandExecuteRequest(BaseModel):
    """Execute command request"""
    command: str
    timeout_seconds: int = 30
    workdir: Optional[str] = None


class CommandExecuteResponse(BaseModel):
    """Command execution response"""
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool


# ============================================================================
# Build Endpoints
# ============================================================================


@router.post("/build", response_model=BuildResponse)
async def start_build(
    config: BuildConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start an image build"""
    builder = get_image_builder(db)

    # Convert request to BuildConfig
    build_config = BuildConfig(
        name=config.name,
        base_image=BaseImage(**config.base_image.dict()),
        packages=[PackageInstall(**p.dict()) for p in config.packages],
        commands=[CustomCommand(**c.dict()) for c in config.commands],
        files=[FileCopy(**f.dict()) for f in config.files],
        env_vars=[EnvironmentVariable(**e.dict()) for e in config.env_vars],
        working_dir=WorkingDir(**config.working_dir.dict()) if config.working_dir else None,
        expose_ports=[ExposePort(**p.dict()) for p in config.expose_ports],
        entrypoint=config.entrypoint,
        cmd=config.cmd,
        user=config.user,
        labels=config.labels,
    )

    result = await builder.start_build(
        config=build_config,
        user_id=str(current_user.id),
        tag=config.tag,
    )

    return BuildResponse(
        build_id=result.build_id,
        image_name=result.image_name,
        tag=result.tag,
        status=result.status.value,
        created_at=result.created_at,
        error=result.error,
        image_id=result.image_id,
        build_time_ms=result.build_time_ms,
    )


@router.get("/builds", response_model=List[BuildListResponse])
async def list_builds(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all builds"""
    builder = get_image_builder(db)

    build_status = BuildStatus(status_filter) if status_filter else None
    results = await builder.list_builds(
        user_id=str(current_user.id),
        status=build_status,
        limit=limit,
    )

    return [
        BuildListResponse(
            build_id=r.build_id,
            name=r.image_name,
            image_name=r.tag,
            status=r.status.value,
            created_at=r.created_at,
            size_bytes=r.size_bytes,
        )
        for r in results
    ]


@router.get("/builds/{build_id}", response_model=BuildResponse)
async def get_build(
    build_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get build details"""
    builder = get_image_builder(db)

    result = await builder.get_build_status(build_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build not found"
        )

    return BuildResponse(
        build_id=result.build_id,
        image_name=result.image_name,
        tag=result.tag,
        status=result.status.value,
        created_at=result.created_at,
        error=result.error,
        image_id=result.image_id,
        build_time_ms=result.build_time_ms,
    )


@router.delete("/builds/{build_id}")
async def delete_build(
    build_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a build"""
    builder = get_image_builder(db)

    success = await builder.delete_build(build_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build not found"
        )

    return {"success": True, "message": "Build deleted"}


@router.post("/builds/{build_id}/cancel")
async def cancel_build(
    build_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel an active build"""
    builder = get_image_builder(db)

    success = await builder.cancel_build(build_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Build cannot be cancelled"
        )

    return {"success": True, "message": "Build cancelled"}


@router.get("/builds/{build_id}/logs")
async def get_build_logs(
    build_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get build logs"""
    builder = get_image_builder(db)

    result = await builder.get_build_status(build_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build not found"
        )

    # Get layers with their content
    from app.models.build import BuildLayer as DBBuildLayer
    layers = db.query(DBBuildLayer).filter(
        DBBuildLayer.build_id == build_id
    ).order_by(DBBuildLayer.layer_order).all()

    return {
        "build_id": build_id,
        "status": result.status.value,
        "layers": [
            {
                "order": l.layer_order,
                "type": l.layer_type,
                "content": l.content,
                "status": l.status,
                "error": l.error_message,
            }
            for l in layers
        ],
        "error": result.error,
    }


# ============================================================================
# Registry Endpoints
# ============================================================================


@router.post("/registries", response_model=RegistryResponse)
async def add_registry(
    config: RegistryConfigRequest,
    test_connection: bool = Query(True, description="Test connection before adding"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new registry"""
    manager = get_registry_manager(db)

    registry_config = RegistryConfig(
        name=config.name,
        registry=config.registry,
        registry_type=config.registry_type,
        endpoint=config.endpoint,
        username=config.username,
        password=config.password,
        is_public=config.is_public,
    )

    try:
        record = await manager.add_registry(
            config=registry_config,
            user_id=str(current_user.id),
            test_connection=test_connection,
        )

        return RegistryResponse(
            id=record.id,
            name=record.name,
            registry=record.registry,
            registry_type=record.registry_type,
            endpoint=record.endpoint,
            is_public=record.is_public,
            created_at=record.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/registries", response_model=List[RegistryResponse])
async def list_registries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all registries"""
    manager = get_registry_manager(db)

    registries = await manager.list_registries(user_id=str(current_user.id))

    return [
        RegistryResponse(
            id=r.id,
            name=r.name,
            registry=r.registry,
            registry_type=r.registry_type,
            endpoint=r.endpoint,
            is_public=r.is_public,
            created_at=r.created_at,
        )
        for r in registries
    ]


@router.delete("/registries/{registry_id}")
async def delete_registry(
    registry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a registry"""
    manager = get_registry_manager(db)

    success = await manager.delete_registry(registry_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registry not found"
        )

    return {"success": True, "message": "Registry deleted"}


@router.post("/registries/{registry_id}/login")
async def login_registry(
    registry_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Login to a registry"""
    manager = get_registry_manager(db)

    success, error = await manager.login_to_registry(registry_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {error}"
        )

    return {"success": True, "message": "Logged in successfully"}


@router.post("/registries/{registry_id}/push")
async def push_image(
    registry_id: str,
    request: PushImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Push an image to a registry"""
    manager = get_registry_manager(db)

    result = await manager.push_image(
        local_image=request.local_image,
        registry_id=registry_id,
        target_tag=request.target_tag,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )

    return {
        "success": True,
        "image_name": result.image_name,
        "tag": result.tag,
        "digest": result.digest,
        "duration_ms": result.duration_ms,
    }


@router.post("/registries/{registry_id}/pull")
async def pull_image(
    registry_id: str,
    request: PullImageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pull an image from a registry"""
    manager = get_registry_manager(db)

    result = await manager.pull_image(
        registry_id=registry_id,
        image_name=request.image_name,
        tag=request.tag,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )

    return {
        "success": True,
        "image_name": result.image_name,
        "tag": result.tag,
        "image_id": result.image_id,
        "duration_ms": result.duration_ms,
    }


@router.get("/registries/{registry_id}/repositories/{repository}/tags")
async def list_repository_tags(
    registry_id: str,
    repository: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List tags for a repository"""
    manager = get_registry_manager(db)

    tags = await manager.list_repository_tags(
        registry_id=registry_id,
        repository=repository,
    )

    return {
        "registry_id": registry_id,
        "repository": repository,
        "tags": tags,
    }


# ============================================================================
# Debugging Endpoints
# ============================================================================


@router.get("/debug/containers")
async def list_debuggable_containers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List containers available for debugging"""
    debugger = get_container_debugger(db)

    containers = await debugger.list_debuggable_containers()

    return {
        "containers": containers,
        "count": len(containers),
    }


@router.post("/debug/sessions", response_model=DebugSessionResponse)
async def start_debug_session(
    request: DebugSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a debug session with a container"""
    debugger = get_container_debugger(db)

    session = await debugger.start_session(
        container_id=request.container_id,
        shell_type=request.shell_type,
        user_id=str(current_user.id),
        timeout_minutes=request.timeout_minutes,
    )

    return DebugSessionResponse(
        session_id=session.session_id,
        container_id=session.container_id,
        container_name=session.container_name,
        shell_type=session.shell_type.value,
        status=session.status.value,
        created_at=session.created_at,
    )


@router.get("/debug/sessions", response_model=List[DebugSessionResponse])
async def list_debug_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List active debug sessions"""
    debugger = get_container_debugger(db)

    sessions = await debugger.list_sessions(user_id=str(current_user.id))

    return [
        DebugSessionResponse(
            session_id=s.session_id,
            container_id=s.container_id,
            container_name=s.container_name,
            shell_type=s.shell_type.value,
            status=s.status.value,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.delete("/debug/sessions/{session_id}")
async def terminate_debug_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Terminate a debug session"""
    debugger = get_container_debugger(db)

    success = await debugger.terminate_session(session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"success": True, "message": "Session terminated"}


@router.post("/debug/sessions/{session_id}/execute", response_model=CommandExecuteResponse)
async def execute_command(
    session_id: str,
    request: CommandExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Execute a command in a debug session"""
    debugger = get_container_debugger(db)

    result = await debugger.execute_command(
        session_id=session_id,
        command=request.command,
        timeout_seconds=request.timeout_seconds,
        workdir=request.workdir,
    )

    return CommandExecuteResponse(
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        duration_ms=result.duration_ms,
        timed_out=result.timed_out,
    )


@router.get("/debug/containers/{container_id}/processes")
async def get_container_processes(
    container_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get processes running in a container"""
    debugger = get_container_debugger(db)

    processes = await debugger.get_container_processes(container_id)

    return {
        "container_id": container_id,
        "processes": processes,
        "count": len(processes),
    }


@router.get("/debug/containers/{container_id}/logs")
async def get_container_logs(
    container_id: str,
    tail: int = Query(100, ge=1, le=10000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get container logs"""
    debugger = get_container_debugger(db)

    logs = await debugger.get_container_logs(container_id, tail=tail)

    return {
        "container_id": container_id,
        "logs": logs,
    }


@router.get("/debug/containers/{container_id}/stats")
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get container resource statistics"""
    debugger = get_container_debugger(db)

    stats = await debugger.get_container_stats(container_id)

    return stats
