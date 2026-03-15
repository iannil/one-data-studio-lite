"""
Annotation Services Package

Provides integration with Label Studio for data annotation,
quality control, and multimedia annotation capabilities.
"""

from app.services.annotation.auth import (
    LabelStudioAuthConfig,
    LabelStudioTokenGenerator,
    LabelStudioAuthMiddleware,
    LabelStudioUserSync,
    get_label_studio_auth,
    get_label_studio_token,
)
from app.services.annotation.service import (
    AnnotationService,
    AutoAnnotationService,
    AnnotationMetricsService,
    LabelStudioProjectConfig,
)
from app.services.annotation.quality_control import (
    ReviewStatus,
    QualityMetricType,
    ReviewTask,
    QualityReport,
    ConsensusResult,
    InterAnnotatorAgreement,
    ConsensusBuilder,
    AnnotationQualityControl,
    get_quality_control_service,
)
from app.services.annotation.multimedia import (
    AudioAnnotationType,
    VideoAnnotationType,
    AudioSegment,
    VideoFrame,
    VideoObject,
    AudioAnnotationService,
    VideoAnnotationService,
    MultimediaAnnotationService,
    get_multimedia_annotation_service,
)

__all__ = [
    # Auth
    "LabelStudioAuthConfig",
    "LabelStudioTokenGenerator",
    "LabelStudioAuthMiddleware",
    "LabelStudioUserSync",
    "get_label_studio_auth",
    "get_label_studio_token",
    # Service
    "AnnotationService",
    "AutoAnnotationService",
    "AnnotationMetricsService",
    "LabelStudioProjectConfig",
    # Quality Control
    "ReviewStatus",
    "QualityMetricType",
    "ReviewTask",
    "QualityReport",
    "ConsensusResult",
    "InterAnnotatorAgreement",
    "ConsensusBuilder",
    "AnnotationQualityControl",
    "get_quality_control_service",
    # Multimedia
    "AudioAnnotationType",
    "VideoAnnotationType",
    "AudioSegment",
    "VideoFrame",
    "VideoObject",
    "AudioAnnotationService",
    "VideoAnnotationService",
    "MultimediaAnnotationService",
    "get_multimedia_annotation_service",
]
