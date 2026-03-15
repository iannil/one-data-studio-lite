"""
Annotation API Endpoints

REST API for Label Studio integration, project management,
and auto-annotation features.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
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


# ============================================================================
# Quality Control Endpoints
# ============================================================================


class ReviewSubmitRequest(BaseModel):
    """Request to submit a review"""
    task_id: str
    status: str  # approved, rejected, revised
    comments: Optional[str] = None
    revised_annotation: Optional[dict] = None


class ConsensusRequest(BaseModel):
    """Request to build consensus"""
    task_id: str
    annotations: List[dict]
    annotator_ids: List[str]
    method: str = "majority_vote"  # majority_vote, weighted_vote, best_confidence


@router.post("/quality/review-tasks/{task_id}/assign")
async def assign_review_task(
    task_id: str,
    reviewer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Assign a reviewer to a task"""
    from app.services.annotation import get_quality_control_service

    qc_service = get_quality_control_service(db)
    success = qc_service.assign_reviewer(task_id, reviewer_id)

    return {
        "success": success,
        "task_id": task_id,
        "reviewer_id": reviewer_id,
    }


@router.post("/quality/review-tasks/{task_id}/submit")
async def submit_review(
    task_id: str,
    request: ReviewSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Submit review for a task"""
    from app.services.annotation import (
        get_quality_control_service,
        ReviewStatus,
    )

    qc_service = get_quality_control_service(db)

    success = qc_service.submit_review(
        task_id=task_id,
        reviewer_id=str(current_user.id),
        status=ReviewStatus(request.status),
        comments=request.comments,
        revised_annotation=request.revised_annotation,
    )

    return {
        "success": success,
        "task_id": task_id,
    }


@router.get("/quality/review-tasks/pending")
async def get_pending_reviews(
    project_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    """Get pending review tasks for a project"""
    from app.services.annotation import get_quality_control_service

    qc_service = get_quality_control_service(db)
    tasks = qc_service.get_pending_reviews(
        project_id=project_id,
        reviewer_id=str(current_user.id),
        limit=limit,
    )

    return [
        {
            "task_id": t.task_id,
            "project_id": t.project_id,
            "annotator_id": t.annotator_id,
            "submitted_at": t.submitted_at.isoformat(),
            "status": t.review_status.value,
        }
        for t in tasks
    ]


@router.post("/quality/consensus")
async def build_consensus(
    request: ConsensusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Build consensus from multiple annotations"""
    from app.services.annotation import get_quality_control_service

    qc_service = get_quality_control_service(db)

    result = qc_service.build_consensus(
        task_id=request.task_id,
        annotations=request.annotations,
        annotator_ids=request.annotator_ids,
        method=request.method,
    )

    return {
        "task_id": result.task_id,
        "consensus": result.consensus_annotation,
        "agreement_score": result.agreement_score,
        "annotator_count": result.annotator_count,
    }


@router.get("/quality/projects/{project_id}/report")
async def get_quality_report(
    project_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get quality report for a project"""
    from app.services.annotation import get_quality_control_service
    from datetime import datetime

    qc_service = get_quality_control_service(db)

    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    report = qc_service.generate_quality_report(
        project_id=project_id,
        start_date=start,
        end_date=end,
    )

    return report


@router.get("/quality/projects/{project_id}/agreement")
async def get_agreement_metrics(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Calculate inter-annotator agreement for a project"""
    from app.services.annotation import get_quality_control_service

    qc_service = get_quality_control_service(db)
    report = qc_service.calculate_agreement(project_id)

    return {
        "project_id": report.project_id,
        "metric_type": report.metric_type.value,
        "value": report.value,
        "details": report.details,
    }


# ============================================================================
# Audio Annotation Endpoints
# ============================================================================


class AudioAnnotationRequest(BaseModel):
    """Request for audio annotation"""
    audio_url: str
    annotation_type: str  # classification, transcription, diarization, sound_event, emotion
    labels: Optional[List[str]] = None
    language: Optional[str] = None
    num_speakers: Optional[int] = None
    timestamps: bool = True
    model: str = "whisper-1"


@router.post("/audio/pre-annotate")
async def pre_annotate_audio(
    request: AudioAnnotationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate pre-annotation for audio"""
    from app.services.annotation import (
        get_multimedia_annotation_service,
        AudioAnnotationType,
    )

    service = get_multimedia_annotation_service()

    try:
        annotation_type = AudioAnnotationType(request.annotation_type)
        result = await service.pre_annotate_audio(
            audio_url=request.audio_url,
            annotation_type=annotation_type,
            labels=request.labels,
            language=request.language,
            num_speakers=request.num_speakers,
            timestamps=request.timestamps,
            model=request.model,
        )
        return result
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid annotation type: {request.annotation_type}"
        )


# ============================================================================
# Video Annotation Endpoints
# ============================================================================


class VideoAnnotationRequest(BaseModel):
    """Request for video annotation"""
    video_url: str
    annotation_type: str  # classification, object_detection, action_recognition, tracking, captioning
    labels: Optional[List[str]] = None
    frame_sampling: int = 10
    action_labels: Optional[List[str]] = None
    initial_detections: Optional[List[dict]] = None
    model: str = "gpt-4-vision-preview"


@router.post("/video/pre-annotate")
async def pre_annotate_video(
    request: VideoAnnotationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Generate pre-annotation for video"""
    from app.services.annotation import (
        get_multimedia_annotation_service,
        VideoAnnotationType,
    )

    service = get_multimedia_annotation_service()

    try:
        annotation_type = VideoAnnotationType(request.annotation_type)
        result = await service.pre_annotate_video(
            video_url=request.video_url,
            annotation_type=annotation_type,
            labels=request.labels,
            frame_sampling=request.frame_sampling,
            action_labels=request.action_labels,
            initial_detections=request.initial_detections,
            model=request.model,
        )
        return result
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid annotation type: {request.annotation_type}"
        )
