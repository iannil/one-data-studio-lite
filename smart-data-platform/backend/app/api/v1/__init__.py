from fastapi import APIRouter

from app.api.v1.auth import router as auth_router, admin_router as users_router
from app.api.v1.metadata import router as sources_router, metadata_router
from app.api.v1.collect import router as collect_router
from app.api.v1.etl import router as etl_router, ai_router as etl_ai_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.asset import router as asset_router, subscriptions_router
from app.api.v1.security import router as security_router, alerts_router, audit_router
from app.api.v1.bi import router as bi_router
from app.api.v1.standard import router as standard_router
from app.api.v1.data_service import router as data_service_router
from app.api.v1.permission import router as permission_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.lineage import router as lineage_router
from app.api.v1.report import router as report_router
from app.api.v1.quality import router as quality_router
from app.api.v1.celery import router as celery_router

api_router = APIRouter()

# Authentication & Users
api_router.include_router(auth_router)
api_router.include_router(users_router)

# Data Sources & Metadata
api_router.include_router(sources_router)
api_router.include_router(metadata_router)

# Data Collection
api_router.include_router(collect_router)

# ETL
api_router.include_router(etl_router)
api_router.include_router(etl_ai_router)

# Analysis
api_router.include_router(analysis_router)

# Data Quality
api_router.include_router(quality_router)

# Assets
api_router.include_router(asset_router)
api_router.include_router(subscriptions_router)

# Data Standards
api_router.include_router(standard_router)

# Data Service API
api_router.include_router(data_service_router)

# Permissions
api_router.include_router(permission_router)

# Security
api_router.include_router(security_router)
api_router.include_router(alerts_router)
api_router.include_router(audit_router)

# BI Integration
api_router.include_router(bi_router)

# OCR Document Processing
api_router.include_router(ocr_router)

# Data Lineage
api_router.include_router(lineage_router)

# Report Builder
api_router.include_router(report_router)

# Celery Task Management
api_router.include_router(celery_router, prefix="/celery", tags=["Celery"])
