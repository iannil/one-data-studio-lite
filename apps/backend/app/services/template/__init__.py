"""
Template Service Package

Provides workflow template management functionality.
"""

from .template_service import (
    TemplateService,
    TemplateVariable,
    TemplateTask,
    WorkflowTemplate,
    get_template_service,
)

from .template_market import (
    TemplateMarketService,
    TemplateCategory,
    TemplateComplexity,
    TemplateReview,
    TemplateVersion,
    TemplateStats,
    MarketTemplate,
    get_market_service,
)

__all__ = [
    # Base template service
    "TemplateService",
    "TemplateVariable",
    "TemplateTask",
    "WorkflowTemplate",
    "get_template_service",
    # Template market
    "TemplateMarketService",
    "TemplateCategory",
    "TemplateComplexity",
    "TemplateReview",
    "TemplateVersion",
    "TemplateStats",
    "MarketTemplate",
    "get_market_service",
]
