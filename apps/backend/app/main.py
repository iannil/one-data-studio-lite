from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core import settings
from app.middleware import (
    AuditMiddleware,
    setup_default_rate_limits,
    ValidationMiddleware,
    SecurityHeadersMiddleware,
)
from app.middleware.rate_limit import RateLimitMiddleware

# Conditionally import APScheduler (only when USE_CELERY=false)
USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"
if not USE_CELERY:
    from app.core.scheduler import scheduler


# API metadata for OpenAPI documentation
API_DESCRIPTION = """
# Smart Data Platform API

## Overview
The Smart Data Platform API provides comprehensive data management capabilities including:

- **Data Sources**: Connect to PostgreSQL, MySQL, Oracle, SQL Server, CSV, Excel, JSON, and REST APIs
- **Metadata Management**: Scan, catalog, and manage table/column metadata with AI-powered insights
- **Data Collection**: Schedule and execute data collection tasks with cron-based scheduling
- **ETL Processing**: Build and execute data pipelines with 15+ transformation steps
- **Data Quality**: Analyze and track data quality metrics with comprehensive scoring
- **Data Lineage**: Visualize and analyze upstream/downstream dependencies
- **Asset Management**: Catalog data assets with value scoring and access tracking
- **AI Analysis**: Natural language to SQL, predictive analytics, clustering
- **BI Integration**: Seamless integration with Apache Superset
- **Security**: RBAC permissions, audit logging, rate limiting, data masking

## Authentication

Most endpoints require authentication using a JWT bearer token.

```bash
curl -X POST "{host}/api/v1/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{"email": "admin@example.com", "password": "admin"}'
```

Include the token in subsequent requests:

```bash
curl -X GET "{host}/api/v1/assets" \\
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Rate Limiting

API requests are rate limited:
- Default: 100 requests per 60 seconds
- Auth endpoints: 5 requests per 60 seconds
- AI/NL Query: 20 requests per 60 seconds

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Error Responses

Errors follow this format:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Rate Limit Exceeded
- `500` - Internal Server Error
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Setup default rate limits
    setup_default_rate_limits()

    # Start APScheduler only if not using Celery
    if not USE_CELERY:
        scheduler.start()

    yield

    # Shutdown APScheduler only if not using Celery
    if not USE_CELERY:
        scheduler.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    description=API_DESCRIPTION,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "API Support",
        "email": "support@smartdataplatform.com",
    },
)

# OpenAPI schema configuration for better documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = app.openapi()

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from /api/v1/auth/login",
        }
    }

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and token management",
        },
        {
            "name": "Data Sources",
            "description": "Manage external data source connections",
        },
        {
            "name": "Metadata",
            "description": "Table and column metadata management",
        },
        {
            "name": "Data Collection",
            "description": "Scheduled data collection from sources",
        },
        {
            "name": "ETL Pipelines",
            "description": "Create and manage ETL data pipelines",
        },
        {
            "name": "Analysis",
            "description": "AI-powered data analysis and predictions",
        },
        {
            "name": "Data Quality",
            "description": "Data quality scoring and issue detection",
        },
        {
            "name": "Data Assets",
            "description": "Data asset catalog and management",
        },
        {
            "name": "Data Lineage",
            "description": "Data lineage and impact analysis",
        },
        {
            "name": "BI Integration",
            "description": "Integration with Apache Superset",
        },
        {
            "name": "Security",
            "description": "Security policies and audit logs",
        },
        {
            "name": "Permissions",
            "description": "User roles and permissions",
        },
        {
            "name": "Standards",
            "description": "Data standards and compliance",
        },
        {
            "name": "Reports",
            "description": "Report builder and generation",
        },
        {
            "name": "OCR",
            "description": "Document OCR and data extraction",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Get allowed origins from environment or use defaults
import os

allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not allowed_origins or allowed_origins == [""]:
    # Development defaults
    allowed_origins = [
        "http://localhost:3100",
        "http://localhost:3101",
        "http://127.0.0.1:3100",
        "http://127.0.0.1:3101",
    ]

# IMPORTANT: In FastAPI, middleware executes in LIFO (last-in-first-out) order.
# The LAST middleware added executes FIRST. Therefore, CORS must be added LAST
# to be the OUTERMOST middleware, handling preflight OPTIONS requests before
# any authentication, rate limiting, or validation.

# Add audit logging middleware (innermost - runs after all other middleware)
app.add_middleware(AuditMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, trust_headers=True)

# Add input validation middleware
app.add_middleware(ValidationMiddleware, max_body_size=10 * 1024 * 1024)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware LAST (outermost - runs first, handles preflight requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
