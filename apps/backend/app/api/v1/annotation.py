"""
Annotation API Endpoints

REST API for Label Studio integration, project management,
and auto-annotation features.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.annotation import (
    AnnotationService,
    AutoAnnotationService,
    AnnotationMetricsService,
    LabelStudioProjectConfig,
    get_label_studio_token,
)

router = APIRouter(prefix="/annotation", tags=["annotation"])

# Services
annotation_service = AnnotationService()
auto_annotation_service = AutoAnnotationService()
metrics_service = AnnotationMetricsService()


# Request/Response Models
class ProjectCreateRequest(BaseModel):
    """Request to create annotation project"""

    name: str = Field(..., min_length=1, max_length=256)
    description: str = Field("", max_length=2048)
    task_type: str = Field(
        "image_classification",
        description="Type of annotation task"
    )
    labeling_config: Optional[str] = Field(
        None,
        description="Custom labeling config (XML)"
    )
    use_default_config: bool = Field(
        True,
        description="Use default config for task type"
    )
    auto_annotation: bool = Field(
        False,
        description="Enable model-assisted annotation"
    )
    mlflow_run_id: Optional[str] = Field(
        None,
        description="MLflow run for auto-annotation model"
    )


class ProjectResponse(BaseModel):
    """Annotation project response"""

    id: str
    name: str
    description: str
    task_type: str
    status: str
    auto_annotation: bool
    created_at: str
    stats: dict


class TaskImportRequest(BaseModel):
    """Request to import annotation tasks"""

    project_id: str
    tasks: List[dict] = Field(..., min_items=1)
    preannotate: bool = Field(False, description="Generate pre-annotations")
    model: str = Field("gpt-4-vision-preview", description="Model for pre-annotation")


class PreAnnotationRequest(BaseModel):
    """Request for pre-annotation"""

    task_type: str = Field(..., description="image_classification, text_classification, etc.")
    data: dict = Field(..., description="Task data (image URL, text, etc.)")
    model: str = Field("gpt-4-vision-preview", description="Model to use")
    labels: Optional[List[str]] = Field(None, description="Available labels")


class PreAnnotationResponse(BaseModel):
    """Pre-annotation result"""

    result: List[dict]
    score: float
    model: str


class ExportRequest(BaseModel):
    """Request to export annotations"""

    project_id: str
    format: str = Field("JSON", description="Export format")
    only_finished: bool = Field(True, description="Export only completed")


# Endpoints


@router.post("/auth/token")
async def get_auth_token(
    token_data: dict = Depends(get_label_studio_token),
) -> dict:
    """
    Get Label Studio authentication token.

    Returns a JWT token that can be used to authenticate with Label Studio.
    """
    return {
        "token": token_data["token"],
        "label_studio_url": token_data["label_studio_url"],
        "user": token_data["user"]
    }


@router.post("/projects", response_model=ProjectResponse)
async def create_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a new annotation project.

    Args:
        request: Project creation request
        current_user: Authenticated user

    Returns:
        Created project details
    """
    # Determine labeling config
    labeling_config = request.labeling_config
    if request.use_default_config and not labeling_config:
        config_map = {
            "image_classification": LabelStudioProjectConfig.IMAGE_CLASSIFICATION_CONFIG,
            "object_detection": LabelStudioProjectConfig.OBJECT_DETECTION_CONFIG,
            "segmentation": LabelStudioProjectConfig.SEGMENTATION_CONFIG,
            "text_classification": LabelStudioProjectConfig.TEXT_CLASSIFICATION_CONFIG,
            "ner": LabelStudioProjectConfig.NER_CONFIG,
            "multimodal": LabelStudioProjectConfig.MULTIMODAL_CONFIG,
        }
        labeling_config = config_map.get(
            request.task_type,
            LabelStudioProjectConfig.IMAGE_CLASSIFICATION_CONFIG
        )

    project = await annotation_service.create_project(
        name=request.name,
        description=request.description,
        labeling_config=labeling_config,
        task_type=request.task_type,
        auto_annotation=request.auto_annotation,
        mlflow_run_id=request.mlflow_run_id,
    )

    return project


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """
    List annotation projects.

    Args:
        skip: Number of projects to skip
        limit: Maximum number of projects to return
        current_user: Authenticated user

    Returns:
        List of projects
    """
    projects = await annotation_service.get_projects(current_user.id)
    return projects[skip : skip + limit]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get annotation project details.

    Args:
        project_id: Project ID
        current_user: Authenticated user

    Returns:
        Project details
    """
    project = await annotation_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Delete an annotation project.

    Args:
        project_id: Project ID
        current_user: Authenticated user

    Returns:
        Deletion result
    """
    success = await annotation_service.delete_project(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return {"deleted": True, "project_id": project_id}


@router.post("/projects/tasks/import")
async def import_tasks(
    request: TaskImportRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Import tasks to annotation project.

    Args:
        request: Task import request
        current_user: Authenticated user

    Returns:
        Import result
    """
    result = await annotation_service.import_tasks(
        project_id=request.project_id,
        tasks=request.tasks,
        preannotate=request.preannotate,
        model=request.model,
    )
    return result


@router.post("/projects/tasks/export")
async def export_annotations(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Export annotations from project.

    Args:
        request: Export request
        current_user: Authenticated user

    Returns:
        Export result with annotations
    """
    result = await annotation_service.export_annotations(
        project_id=request.project_id,
        export_format=request.format,
        only_finished=request.only_finished,
    )
    return result


@router.get("/projects/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get annotation project statistics.

    Args:
        project_id: Project ID
        current_user: Authenticated user

    Returns:
        Project statistics
    """
    stats = await annotation_service.get_project_stats(project_id)
    return stats


@router.post("/pre-annotate", response_model=PreAnnotationResponse)
async def pre_annotate(
    request: PreAnnotationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate pre-annotation for a single task.

    Args:
        request: Pre-annotation request
        current_user: Authenticated user

    Returns:
        Pre-annotation result
    """
    # Handle image annotation
    if request.task_type.startswith("image"):
        image_url = request.data.get("image")
        if not image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Image URL required for image annotation"
            )

        sub_type = request.task_type.replace("image_", "")
        result = await auto_annotation_service.pre_annotate_image(
            image_url=image_url,
            task_type=sub_type,
            model=request.model,
        )
        return result

    # Handle text annotation
    elif request.task_type.startswith("text"):
        text = request.data.get("text")
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text content required for text annotation"
            )

        labels = request.labels or ["Positive", "Negative", "Neutral"]
        sub_type = request.task_type.replace("text_", "")
        result = await auto_annotation_service.pre_annotate_text(
            text=text,
            task_type=sub_type,
            labels=labels,
            model=request.model,
        )
        return result

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported task type: {request.task_type}"
        )


@router.get("/projects/{project_id}/metrics/performance")
async def get_annotator_performance(
    project_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """
    Get annotator performance metrics.

    Args:
        project_id: Project ID
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        current_user: Authenticated user

    Returns:
        List of annotator metrics
    """
    metrics = await metrics_service.get_annotator_performance(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
    )
    return metrics


@router.get("/projects/{project_id}/metrics/quality")
async def get_annotation_quality(
    project_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get annotation quality metrics.

    Args:
        project_id: Project ID
        current_user: Authenticated user

    Returns:
        Quality metrics
    """
    quality = await metrics_service.get_annotation_quality(project_id)
    return quality


@router.get("/projects/{project_id}/metrics/labels")
async def get_label_distribution(
    project_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get label distribution for project.

    Args:
        project_id: Project ID
        current_user: Authenticated user

    Returns:
        Label distribution
    """
    distribution = await metrics_service.get_label_distribution(project_id)
    return distribution


@router.get("/configs/templates")
async def get_labeling_config_templates() -> dict:
    """
    Get available labeling configuration templates.

    Returns:
        Dictionary of task types to their configs
    """
    return {
        "image_classification": LabelStudioProjectConfig.IMAGE_CLASSIFICATION_CONFIG,
        "object_detection": LabelStudioProjectConfig.OBJECT_DETECTION_CONFIG,
        "segmentation": LabelStudioProjectConfig.SEGMENTATION_CONFIG,
        "text_classification": LabelStudioProjectConfig.TEXT_CLASSIFICATION_CONFIG,
        "ner": LabelStudioProjectConfig.NER_CONFIG,
        "multimodal": LabelStudioProjectConfig.MULTIMODAL_CONFIG,
    }
