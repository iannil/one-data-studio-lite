"""
Annotation Services Package

Provides integration with Label Studio for data annotation.
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
]
