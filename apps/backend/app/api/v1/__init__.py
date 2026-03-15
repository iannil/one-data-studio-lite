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
from app.api.v1.annotation import router as annotation_router
from app.api.v1.aihub import router as aihub_router
from app.api.v1.llm import router as llm_router
from app.api.v1.training import router as training_router
from app.api.v1.workflow import router as workflow_router, template_router
from app.api.v1.serving import router as serving_router
from app.api.v1.argo import router as argo_router
from app.api.v1.operator import router as operator_router
from app.api.v1.gpu import router as gpu_router
from app.api.v1.tenant import router as tenant_router
from app.api.v1.sso import router as sso_router
from app.api.v1.monitoring import router as monitoring_router
from app.api.v1.ide import router as ide_router
from app.api.v1.feature_store import router as feature_store_router
from app.api.v1.automl import router as automl_router
from app.api.v1.tensorboard import router as tensorboard_router
from app.api.v1.dataset import router as dataset_router
from app.api.v1.finetune import router as finetune_router
from app.api.v1.storage import router as storage_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.serverless import router as serverless_router
from app.api.v1.edge import router as edge_router
from app.api.v1.data_collection import router as data_collection_router

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

# Annotation / Label Studio
api_router.include_router(annotation_router)

# AIHub Model Marketplace
api_router.include_router(aihub_router)

# LLM / Knowledge Base
api_router.include_router(llm_router)

# Distributed Training
api_router.include_router(training_router)

# Workflow / DAG
api_router.include_router(workflow_router)
api_router.include_router(template_router)

# Model Serving
api_router.include_router(serving_router)

# Argo Workflows
api_router.include_router(argo_router)

# Kubernetes Operators
api_router.include_router(operator_router)

# GPU Resource Management
api_router.include_router(gpu_router)

# Multi-Tenant Management
api_router.include_router(tenant_router)

# Single Sign-On
api_router.include_router(sso_router)

# Enterprise Monitoring
api_router.include_router(monitoring_router)

# IDE Management
api_router.include_router(ide_router)

# Feature Store
api_router.include_router(feature_store_router)

# AutoML
api_router.include_router(automl_router)

# TensorBoard
api_router.include_router(tensorboard_router, prefix="/tensorboard", tags=["TensorBoard"])

# Dataset
api_router.include_router(dataset_router, prefix="/datasets", tags=["Datasets"])

# Fine-tuning
api_router.include_router(finetune_router, prefix="/finetune", tags=["Fine-tuning"])

# Storage
api_router.include_router(storage_router, prefix="/storage", tags=["Storage"])

# Phase 3: Advanced Features
# Knowledge Base & RAG
api_router.include_router(knowledge_router, prefix="/knowledge", tags=["Knowledge Base"])

# Serverless Functions
api_router.include_router(serverless_router, prefix="/serverless", tags=["Serverless"])

# Edge Computing
api_router.include_router(edge_router, prefix="/edge", tags=["Edge Computing"])

# Data Collection
api_router.include_router(data_collection_router, prefix="/data-collection", tags=["Data Collection"])
