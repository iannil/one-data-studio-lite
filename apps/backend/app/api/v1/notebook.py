"""
Notebook API endpoints for One Data Studio Lite

Provides REST API for managing Jupyter notebook servers.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, require_permission
from app.models.user import User
from app.services.notebook import NotebookService
from app.services.notebook.spawner import ResourceProfile, NotebookImage

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


# Request/Response Schemas
class NotebookCreateRequest(BaseModel):
    """Request to create a notebook"""

    image_id: Optional[str] = Field(None, description="Notebook image ID")
    profile_id: Optional[str] = Field(None, description="Resource profile ID")
    server_name: Optional[str] = Field("", description="Server name (for named servers)")


class NotebookResponse(BaseModel):
    """Notebook server response"""

    id: str = Field(..., description="Notebook ID (user/server_name)")
    name: str = Field(..., description="Server name")
    user: str = Field(..., description="Username")
    state: str = Field(..., description="Server state")
    image: str = Field(..., description="Notebook image")
    cpu_limit: float = Field(..., description="CPU limit")
    mem_limit: str = Field(..., description="Memory limit")
    gpu_limit: int = Field(..., description="GPU limit")
    url: Optional[str] = Field(None, description="Notebook URL")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")


class ImageResponse(BaseModel):
    """Notebook image response"""

    id: str
    name: str
    description: str
    image: str
    icon: str
    packages: List[str]
    default: bool
    gpu_required: bool
    gpu_recommended: bool


class ProfileResponse(BaseModel):
    """Resource profile response"""

    id: str
    name: str
    description: str
    cpu_limit: float
    cpu_guarantee: float
    mem_limit: str
    mem_guarantee: str
    gpu_limit: int
    default: bool


class ProgressResponse(BaseModel):
    """Spawn progress response"""

    progress: int = Field(..., description="Progress percentage (0-100)")
    message: str = Field(..., description="Progress message")
    ready: bool = Field(..., description="Whether server is ready")


# Helper function to get notebook service
async def get_notebook_service() -> NotebookService:
    """Get notebook service instance"""
    from app.core.config import settings

    return NotebookService(
        hub_url=settings.JUPYTERHUB_API_URL,
        api_token=settings.JUPYTERHUB_API_TOKEN,
    )


@router.get("", response_model=List[NotebookResponse])
async def list_notebooks(
    current_user: User = Depends(get_current_user),
):
    """
    List notebook servers

    Returns a list of notebook servers. Admin users see all servers,
    regular users only see their own.
    """
    service = await get_notebook_service()

    try:
        # Non-admin users can only see their own notebooks
        username = current_user.username if not current_user.is_admin else None

        notebooks = await service.list_notebooks(username)

        return [
            NotebookResponse(
                id=f"{nb.user}/{nb.name}",
                name=nb.name,
                user=nb.user,
                state=nb.state,
                image=nb.image,
                cpu_limit=nb.cpu_limit,
                mem_limit=nb.mem_limit,
                gpu_limit=nb.gpu_limit,
                url=nb.url,
                created_at=nb.created_at,
                last_activity=nb.last_activity,
            )
            for nb in notebooks
        ]
    finally:
        await service.close()


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    request: NotebookCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new notebook server

    Creates and starts a new notebook server for the current user.
    """
    service = await get_notebook_service()

    try:
        notebook = await service.create_notebook(
            username=current_user.username,
            image_id=request.image_id,
            profile_id=request.profile_id,
            server_name=request.server_name,
        )

        return NotebookResponse(
            id=f"{notebook.user}/{notebook.name}",
            name=notebook.name,
            user=notebook.user,
            state=notebook.state,
            image=notebook.image,
            cpu_limit=notebook.cpu_limit,
            mem_limit=notebook.mem_limit,
            gpu_limit=notebook.gpu_limit,
            url=notebook.url,
            created_at=notebook.created_at,
            last_activity=notebook.last_activity,
        )
    finally:
        await service.close()


@router.get("/{user_id}", response_model=NotebookResponse)
async def get_notebook(
    user_id: str,
    server_name: str = "",
    current_user: User = Depends(get_current_user),
):
    """
    Get a notebook server

    Returns information about a specific notebook server.
    """
    # Check permission
    if user_id != current_user.username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notebook",
        )

    service = await get_notebook_service()

    try:
        notebook = await service.get_notebook(user_id, server_name)

        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found",
            )

        return NotebookResponse(
            id=f"{notebook.user}/{notebook.name}",
            name=notebook.name,
            user=notebook.user,
            state=notebook.state,
            image=notebook.image,
            cpu_limit=notebook.cpu_limit,
            mem_limit=notebook.mem_limit,
            gpu_limit=notebook.gpu_limit,
            url=notebook.url,
            created_at=notebook.created_at,
            last_activity=notebook.last_activity,
        )
    finally:
        await service.close()


@router.post("/{user_id}/start", response_model=NotebookResponse)
async def start_notebook(
    user_id: str,
    server_name: str = "",
    current_user: User = Depends(get_current_user),
):
    """
    Start a stopped notebook server

    Starts a notebook server that was previously stopped.
    """
    # Check permission
    if user_id != current_user.username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to start this notebook",
        )

    service = await get_notebook_service()

    try:
        await service.start_notebook(user_id, server_name)
        notebook = await service.get_notebook(user_id, server_name)

        if not notebook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notebook not found",
            )

        return NotebookResponse(
            id=f"{notebook.user}/{notebook.name}",
            name=notebook.name,
            user=notebook.user,
            state=notebook.state,
            image=notebook.image,
            cpu_limit=notebook.cpu_limit,
            mem_limit=notebook.mem_limit,
            gpu_limit=notebook.gpu_limit,
            url=notebook.url,
            created_at=notebook.created_at,
            last_activity=notebook.last_activity,
        )
    finally:
        await service.close()


@router.post("/{user_id}/stop")
async def stop_notebook(
    user_id: str,
    server_name: str = "",
    current_user: User = Depends(get_current_user),
):
    """
    Stop a running notebook server

    Stops a notebook server to free up resources.
    """
    # Check permission
    if user_id != current_user.username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to stop this notebook",
        )

    service = await get_notebook_service()

    try:
        await service.stop_notebook(user_id, server_name)
        return {"message": "Notebook stopped successfully"}
    finally:
        await service.close()


@router.delete("/{user_id}")
async def delete_notebook(
    user_id: str,
    server_name: str = "",
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notebook server

    Stops and deletes a notebook server.
    """
    # Check permission
    if user_id != current_user.username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this notebook",
        )

    service = await get_notebook_service()

    try:
        await service.delete_notebook(user_id, server_name)
        return {"message": "Notebook deleted successfully"}
    finally:
        await service.close()


@router.get("/{user_id}/progress", response_model=ProgressResponse)
async def get_notebook_progress(
    user_id: str,
    server_name: str = "",
    current_user: User = Depends(get_current_user),
):
    """
    Get notebook spawn progress

    Returns the progress of notebook server spawning.
    """
    # Check permission
    if user_id != current_user.username and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this notebook",
        )

    service = await get_notebook_service()

    try:
        progress = await service.get_notebook_progress(user_id, server_name)

        return ProgressResponse(
            progress=progress.get("progress", 0),
            message=progress.get("message", ""),
            ready=progress.get("ready", False),
        )
    finally:
        await service.close()


@router.get("/images", response_model=List[ImageResponse])
async def list_notebook_images(
    gpu_available: bool = False,
    current_user: User = Depends(get_current_user),
):
    """
    List available notebook images

    Returns a list of available notebook images/templates.
    """
    service = await get_notebook_service()

    try:
        images = await service.list_available_images(gpu_available)

        return [
            ImageResponse(
                id=img.id,
                name=img.name,
                description=img.description,
                image=img.image,
                icon=img.icon,
                packages=img.packages,
                default=img.default,
                gpu_required=img.gpu_required,
                gpu_recommended=img.gpu_recommended,
            )
            for img in images
        ]
    finally:
        await service.close()


@router.get("/profiles", response_model=List[ProfileResponse])
async def list_resource_profiles(
    gpu_available: bool = False,
    current_user: User = Depends(get_current_user),
):
    """
    List available resource profiles

    Returns a list of available resource profiles.
    """
    service = await get_notebook_service()

    try:
        profiles = await service.list_available_profiles(gpu_available)

        return [
            ProfileResponse(
                id=profile.id,
                name=profile.name,
                description=profile.description,
                cpu_limit=profile.cpu_limit,
                cpu_guarantee=profile.cpu_guarantee,
                mem_limit=profile.mem_limit,
                mem_guarantee=profile.mem_guarantee,
                gpu_limit=profile.gpu_limit,
                default=profile.default,
            )
            for profile in profiles
        ]
    finally:
        await service.close()
