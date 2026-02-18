from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Response
from sqlalchemy import select, or_

from app.api.deps import CurrentUser, DBSession
from app.models import DataAsset, AssetAccess, AssetApiConfig, AccessLevel
from app.schemas import (
    DataAssetCreate,
    DataAssetResponse,
    DataAssetUpdate,
    AssetLineageResponse,
    AssetSearchRequest,
    AssetSearchResponse,
    AssetExportRequest,
    AssetExportResponse,
    AssetAutoRegisterRequest,
    AssetAutoRegisterResponse,
    AssetGenerateDescriptionRequest,
    AssetGenerateDescriptionResponse,
    AssetValueTrendResponse,
    AssetApiConfigCreate,
    AssetApiConfigUpdate,
    AssetApiConfigResponse,
    AssetApiDocsResponse,
)

router = APIRouter(prefix="/assets", tags=["Data Assets"])


@router.post("", response_model=DataAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    request: DataAssetCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> DataAsset:
    """Create a new data asset."""
    asset = DataAsset(
        name=request.name,
        description=request.description,
        asset_type=request.asset_type,
        source_table=request.source_table,
        source_schema=request.source_schema,
        source_database=request.source_database,
        owner_id=current_user.id,
        department=request.department,
        access_level=request.access_level,
        tags=request.tags,
        category=request.category,
        domain=request.domain,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return asset


@router.get("", response_model=list[DataAssetResponse])
async def list_assets(
    db: DBSession,
    current_user: CurrentUser,
    category: str | None = None,
    domain: str | None = None,
    access_level: AccessLevel | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DataAsset]:
    """List data assets."""
    query = select(DataAsset).where(DataAsset.is_active.is_(True))

    if category:
        query = query.where(DataAsset.category == category)
    if domain:
        query = query.where(DataAsset.domain == domain)
    if access_level:
        query = query.where(DataAsset.access_level == access_level)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)

    return list(result.scalars())


@router.get("/{asset_id}", response_model=DataAssetResponse)
async def get_asset(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> DataAsset:
    """Get a specific data asset."""
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.usage_count += 1
    from datetime import datetime, timezone
    asset.last_accessed_at = datetime.now(timezone.utc)

    access_log = AssetAccess(
        asset_id=asset.id,
        user_id=current_user.id,
        access_type="read",
    )
    db.add(access_log)
    await db.commit()

    return asset


@router.patch("/{asset_id}", response_model=DataAssetResponse)
async def update_asset(
    asset_id: UUID,
    request: DataAssetUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> DataAsset:
    """Update a data asset."""
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    await db.commit()
    await db.refresh(asset)

    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_asset(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete (soft) a data asset."""
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.is_active = False
    await db.commit()


@router.post("/search", response_model=AssetSearchResponse)
async def search_assets(
    request: AssetSearchRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetSearchResponse:
    """Search data assets using AI-powered search."""
    query = select(DataAsset).where(DataAsset.is_active.is_(True))

    query = query.where(
        or_(
            DataAsset.name.ilike(f"%{request.query}%"),
            DataAsset.description.ilike(f"%{request.query}%"),
            DataAsset.ai_summary.ilike(f"%{request.query}%"),
        )
    )

    if request.asset_types:
        query = query.where(DataAsset.asset_type.in_(request.asset_types))

    if request.access_levels:
        query = query.where(DataAsset.access_level.in_(request.access_levels))

    if request.tags:
        query = query.where(DataAsset.tags.overlap(request.tags))

    query = query.limit(request.limit)
    result = await db.execute(query)
    assets = list(result.scalars())

    return AssetSearchResponse(
        results=assets,
        total=len(assets),
        ai_summary=f"Found {len(assets)} assets matching '{request.query}'"
        if assets
        else f"No assets found for '{request.query}'",
    )


@router.get("/{asset_id}/lineage", response_model=AssetLineageResponse)
async def get_lineage(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    depth: int = 1,
) -> AssetLineageResponse:
    """Get data lineage for an asset.

    Args:
        asset_id: The asset ID to get lineage for
        depth: How many levels of lineage to traverse (1-3, default 1)
    """
    depth = min(max(depth, 1), 3)

    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    async def collect_lineage(
        asset_ids: list[UUID],
        direction: str,
        current_depth: int,
        visited: set[UUID],
    ) -> list[dict]:
        """Recursively collect lineage assets."""
        if current_depth > depth or not asset_ids:
            return []

        valid_ids = [aid for aid in asset_ids if aid not in visited]
        if not valid_ids:
            return []

        query_result = await db.execute(
            select(DataAsset).where(DataAsset.id.in_(valid_ids))
        )
        assets = list(query_result.scalars())

        collected = []
        for a in assets:
            visited.add(a.id)
            collected.append({
                "id": str(a.id),
                "name": a.name,
                "type": a.asset_type.value,
                "description": a.description,
                "domain": a.domain,
                "category": a.category,
                "depth": current_depth,
            })

            next_ids = a.upstream_assets if direction == "upstream" else a.downstream_assets
            if next_ids and current_depth < depth:
                nested = await collect_lineage(
                    next_ids, direction, current_depth + 1, visited
                )
                collected.extend(nested)

        return collected

    visited_up: set[UUID] = {asset.id}
    visited_down: set[UUID] = {asset.id}

    upstream = await collect_lineage(
        asset.upstream_assets or [], "upstream", 1, visited_up
    )
    downstream = await collect_lineage(
        asset.downstream_assets or [], "downstream", 1, visited_down
    )

    nodes = [
        {
            "id": str(asset.id),
            "name": asset.name,
            "type": "current",
            "assetType": asset.asset_type.value,
            "description": asset.description,
            "domain": asset.domain,
            "category": asset.category,
        },
    ]

    for u in upstream:
        nodes.append({
            "id": u["id"],
            "name": u["name"],
            "type": "upstream",
            "assetType": u["type"],
            "description": u.get("description"),
            "domain": u.get("domain"),
            "category": u.get("category"),
            "depth": u.get("depth", 1),
        })

    for d in downstream:
        nodes.append({
            "id": d["id"],
            "name": d["name"],
            "type": "downstream",
            "assetType": d["type"],
            "description": d.get("description"),
            "domain": d.get("domain"),
            "category": d.get("category"),
            "depth": d.get("depth", 1),
        })

    edges = []
    edges.extend([{"source": u["id"], "target": str(asset.id)} for u in upstream if u.get("depth") == 1])
    edges.extend([{"source": str(asset.id), "target": d["id"]} for d in downstream if d.get("depth") == 1])

    for u in upstream:
        if u.get("depth", 1) > 1:
            parent_id = None
            for other in upstream:
                if other.get("depth") == u["depth"] - 1:
                    parent_id = other["id"]
                    break
            if parent_id:
                edges.append({"source": u["id"], "target": parent_id})

    for d in downstream:
        if d.get("depth", 1) > 1:
            parent_id = None
            for other in downstream:
                if other.get("depth") == d["depth"] - 1:
                    parent_id = other["id"]
                    break
            if parent_id:
                edges.append({"source": parent_id, "target": d["id"]})

    lineage_graph = {
        "nodes": nodes,
        "edges": edges,
    }

    return AssetLineageResponse(
        asset_id=asset.id,
        upstream=upstream,
        downstream=downstream,
        lineage_graph=lineage_graph,
    )


@router.get("/{asset_id}/value")
async def get_asset_value(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Get value assessment for an asset."""
    from app.services.asset_service import AssetService

    service = AssetService(db)
    try:
        return await service.evaluate_asset_value(asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{asset_id}/value/refresh")
async def refresh_asset_value(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Recalculate and persist value score for an asset."""
    from app.services.asset_service import AssetService

    service = AssetService(db)
    try:
        asset = await service.update_asset_value_score(asset_id)
        return {
            "asset_id": str(asset.id),
            "value_score": asset.value_score,
            "message": "Value score updated successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{asset_id}/usage-stats")
async def get_usage_stats(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    days: int = 30,
) -> dict:
    """Get usage statistics for an asset."""
    from app.services.asset_service import AssetService

    service = AssetService(db)
    return await service.get_usage_statistics(asset_id, days)


@router.get("/value/distribution")
async def get_value_distribution(
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Get distribution of asset values across all assets."""
    from app.services.asset_service import AssetService

    service = AssetService(db)
    return await service.get_value_distribution()


@router.post("/value/batch-refresh")
async def batch_refresh_values(
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Batch refresh value scores for all active assets."""
    from app.services.asset_service import AssetService

    service = AssetService(db)
    return await service.batch_update_value_scores()


@router.post("/ai-search")
async def ai_search_assets(
    query: str,
    db: DBSession,
    current_user: CurrentUser,
    limit: int = 20,
) -> dict:
    """AI-powered semantic search for data assets."""
    from app.services.ai_service import AIService

    service = AIService(db)
    return await service.search_assets(query, limit)


@router.post("/{asset_id}/export", response_model=AssetExportResponse)
async def export_asset(
    asset_id: UUID,
    request: AssetExportRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetExportResponse:
    """Export asset data."""
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if not asset.source_table:
        raise HTTPException(status_code=400, detail="Asset has no source table")

    access_log = AssetAccess(
        asset_id=asset.id,
        user_id=current_user.id,
        access_type="export",
        access_details={"format": request.format},
    )
    db.add(access_log)
    await db.commit()

    return AssetExportResponse(
        download_url=f"/api/v1/assets/{asset_id}/download?format={request.format}",
        format=request.format,
        row_count=0,
        file_size_bytes=0,
    )


@router.post("/{asset_id}/certify", response_model=DataAssetResponse)
async def certify_asset(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> DataAsset:
    """Certify a data asset."""
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    from datetime import datetime, timezone

    asset.is_certified = True
    asset.certified_by = current_user.id
    asset.certified_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(asset)

    return asset


@router.post("/auto-register", response_model=AssetAutoRegisterResponse)
async def auto_register_asset(
    request: AssetAutoRegisterRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetAutoRegisterResponse:
    """Auto-register a data asset from table metadata.

    Scans the specified table and creates or updates a data asset with:
    - Extracted data profile (row count, columns, quality metrics)
    - AI-generated description and tags
    - Automatic value score calculation
    - Lineage connection if source_table is provided
    """
    import pandas as pd
    from sqlalchemy import create_engine
    from app.core.config import settings
    from app.services.asset_service import AssetService

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    sync_engine = create_engine(sync_url)

    try:
        table_ref = request.table_name
        if request.schema_name:
            table_ref = f"{request.schema_name}.{request.table_name}"

        df = pd.read_sql_table(
            request.table_name,
            sync_engine,
            schema=request.schema_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read table: {str(e)}",
        )

    service = AssetService(db)

    try:
        import uuid
        result = await service.auto_catalog_from_etl(
            pipeline_id=uuid.uuid4(),
            pipeline_name=request.pipeline_name or "Manual Registration",
            target_table=request.table_name,
            target_schema=request.schema_name,
            df=df,
            source_table=request.source_table,
        )

        return AssetAutoRegisterResponse(
            action=result["action"],
            asset_id=result["asset_id"],
            asset_name=result["asset_name"],
            data_profile=result.get("data_profile"),
            ai_summary=result.get("ai_summary"),
            tags=result.get("tags", []),
            value_score=result.get("value_score"),
            value_level=result.get("value_level"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Auto-registration failed: {str(e)}",
        )


@router.post("/{asset_id}/generate-description", response_model=AssetGenerateDescriptionResponse)
async def generate_asset_description(
    asset_id: UUID,
    request: AssetGenerateDescriptionRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetGenerateDescriptionResponse:
    """Generate AI-powered description for a data asset.

    Uses AI to analyze the asset's metadata, columns, and quality metrics
    to generate a comprehensive description and suggested tags.
    """
    import json
    from openai import AsyncOpenAI
    from app.core.config import settings

    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset_info = {
        "name": asset.name,
        "current_description": asset.description,
        "source_table": asset.source_table,
        "source_schema": asset.source_schema,
        "asset_type": asset.asset_type.value,
        "current_tags": asset.tags or [],
        "current_domain": asset.domain,
        "current_category": asset.category,
    }

    if request.include_columns and asset.lineage_json:
        data_profile = asset.lineage_json.get("data_profile", {})
        asset_info["columns"] = [
            {"name": c.get("name"), "type": c.get("dtype")}
            for c in data_profile.get("columns", [])[:20]
        ]

    if request.include_quality_metrics and asset.lineage_json:
        data_profile = asset.lineage_json.get("data_profile", {})
        asset_info["quality_metrics"] = data_profile.get("quality_metrics", {})
        asset_info["row_count"] = data_profile.get("row_count")

    prompt = f"""Analyze this data asset and generate comprehensive metadata.

Asset Information:
{json.dumps(asset_info, indent=2, ensure_ascii=False)}

Generate metadata in JSON format:
{{
  "name": "Human-readable asset name (keep original if appropriate)",
  "description": "Clear description of what this data represents and its business purpose (2-3 sentences)",
  "summary": "Brief AI summary (1 sentence)",
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "suggested_domain": "Business domain like sales, customer, product, finance, operations",
  "suggested_category": "One of: master_data, transaction, analytics, reference, staging"
}}"""

    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data catalog expert. Generate accurate metadata for data assets based on their structure and context.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        ai_result = json.loads(response.choices[0].message.content or "{}")

        if ai_result.get("description"):
            asset.description = ai_result["description"]
        if ai_result.get("summary"):
            asset.ai_summary = ai_result["summary"]

        await db.commit()
        await db.refresh(asset)

        return AssetGenerateDescriptionResponse(
            asset_id=str(asset.id),
            name=ai_result.get("name", asset.name),
            description=ai_result.get("description", asset.description or ""),
            summary=ai_result.get("summary", ""),
            suggested_tags=ai_result.get("suggested_tags", []),
            suggested_domain=ai_result.get("suggested_domain"),
            suggested_category=ai_result.get("suggested_category"),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI description generation failed: {str(e)}",
        )


@router.get("/{asset_id}/value/trend", response_model=AssetValueTrendResponse)
async def get_asset_value_trend(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    days: int = 30,
) -> AssetValueTrendResponse:
    """Get value trend analysis for an asset.

    Returns historical value scores and trend direction.
    """
    from app.services.asset_service import AssetService

    service = AssetService(db)
    try:
        trend_result = await service.get_value_trend(asset_id, days)
        return AssetValueTrendResponse(
            asset_id=str(asset_id),
            current_score=trend_result.get("current_score"),
            current_level=trend_result.get("current_level"),
            trend=trend_result.get("trend", []),
            change_percentage=trend_result.get("change_percentage"),
            trend_direction=trend_result.get("trend_direction"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============= API Config Endpoints =============


@router.get("/{asset_id}/api-config", response_model=AssetApiConfigResponse)
async def get_asset_api_config(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetApiConfigResponse:
    """Get API configuration for a data asset.

    Returns the current API endpoint configuration including rate limits,
    field exposure settings, and authentication requirements.
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    config_result = await db.execute(
        select(AssetApiConfig).where(AssetApiConfig.asset_id == asset_id)
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="API configuration not found")

    api_endpoint = _generate_api_endpoint(asset, config)
    api_documentation = _generate_api_documentation(asset, config)

    response = AssetApiConfigResponse.model_validate(config)
    response.api_endpoint = api_endpoint
    response.api_documentation = api_documentation

    return response


@router.put("/{asset_id}/api-config", response_model=AssetApiConfigResponse)
async def upsert_asset_api_config(
    asset_id: UUID,
    request: AssetApiConfigUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetApiConfigResponse:
    """Create or update API configuration for a data asset.

    If no configuration exists, creates a new one. Otherwise updates existing.
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    config_result = await db.execute(
        select(AssetApiConfig).where(AssetApiConfig.asset_id == asset_id)
    )
    config = config_result.scalar_one_or_none()

    update_data = request.model_dump(exclude_unset=True)

    if config:
        for field, value in update_data.items():
            setattr(config, field, value)
    else:
        config = AssetApiConfig(asset_id=asset_id, **update_data)
        db.add(config)

    await db.commit()
    await db.refresh(config)

    api_endpoint = _generate_api_endpoint(asset, config)
    api_documentation = _generate_api_documentation(asset, config)

    response = AssetApiConfigResponse.model_validate(config)
    response.api_endpoint = api_endpoint
    response.api_documentation = api_documentation

    return response


@router.delete(
    "/{asset_id}/api-config",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_asset_api_config(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """Delete API configuration for a data asset.

    This disables the API endpoint for this asset.
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    config_result = await db.execute(
        select(AssetApiConfig).where(AssetApiConfig.asset_id == asset_id)
    )
    config = config_result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="API configuration not found")

    await db.delete(config)
    await db.commit()


@router.get("/{asset_id}/api-docs", response_model=AssetApiDocsResponse)
async def get_asset_api_docs(
    asset_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> AssetApiDocsResponse:
    """Get API documentation for a data asset.

    Returns endpoint URL, request/response examples, and usage instructions.
    """
    result = await db.execute(select(DataAsset).where(DataAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    config_result = await db.execute(
        select(AssetApiConfig).where(AssetApiConfig.asset_id == asset_id)
    )
    config = config_result.scalar_one_or_none()

    if not config:
        config = AssetApiConfig(asset_id=asset_id)

    api_endpoint = _generate_api_endpoint(asset, config)
    available_operations = []
    if config.allow_query:
        available_operations.append("query")
    if config.allow_export:
        available_operations.append("export")

    request_examples = _generate_request_examples(asset, config, api_endpoint)
    response_example = _generate_response_example(asset, config)

    return AssetApiDocsResponse(
        asset_id=str(asset.id),
        asset_name=asset.name,
        api_endpoint=api_endpoint,
        description=asset.description,
        is_enabled=config.is_enabled,
        require_auth=config.require_auth,
        rate_limit={
            "requests": config.rate_limit_requests,
            "window_seconds": config.rate_limit_window_seconds,
        },
        available_operations=available_operations,
        allowed_formats=config.allowed_export_formats or ["csv", "json"],
        limits={
            "default_limit": config.default_limit,
            "max_limit": config.max_limit,
        },
        request_examples=request_examples,
        response_example=response_example,
    )


def _generate_api_endpoint(asset: DataAsset, config: AssetApiConfig) -> str:
    """Generate the API endpoint URL for an asset."""
    slug = config.endpoint_slug or str(asset.id)
    return f"/api/v1/data-service/query/{slug}"


def _generate_api_documentation(
    asset: DataAsset, config: AssetApiConfig
) -> dict:
    """Generate API documentation for an asset."""
    return {
        "endpoint": _generate_api_endpoint(asset, config),
        "methods": ["GET", "POST"],
        "rate_limit": f"{config.rate_limit_requests} requests per {config.rate_limit_window_seconds} seconds",
        "authentication": "Bearer token required" if config.require_auth else "None",
        "operations": {
            "query": config.allow_query,
            "export": config.allow_export,
        },
        "export_formats": config.allowed_export_formats,
        "limits": {
            "default": config.default_limit,
            "max": config.max_limit,
        },
    }


def _generate_request_examples(
    asset: DataAsset, config: AssetApiConfig, api_endpoint: str
) -> dict:
    """Generate request examples for API documentation."""
    base_url = "https://your-api-domain.com"

    examples = {
        "curl_query": f'curl -X GET "{base_url}{api_endpoint}?limit={config.default_limit}" \\\n  -H "Authorization: Bearer YOUR_TOKEN"',
        "curl_export": f'curl -X GET "{base_url}/api/v1/data-service/export/{asset.id}?format=csv" \\\n  -H "Authorization: Bearer YOUR_TOKEN" \\\n  -o data.csv',
        "javascript_query": f"""fetch("{base_url}{api_endpoint}?limit={config.default_limit}", {{
  headers: {{
    "Authorization": "Bearer YOUR_TOKEN"
  }}
}})
.then(response => response.json())
.then(data => console.log(data));""",
        "python_query": f"""import requests

response = requests.get(
    "{base_url}{api_endpoint}",
    headers={{"Authorization": "Bearer YOUR_TOKEN"}},
    params={{"limit": {config.default_limit}}}
)
data = response.json()""",
    }

    return examples


def _generate_response_example(asset: DataAsset, config: AssetApiConfig) -> dict:
    """Generate response example for API documentation."""
    return {
        "asset_id": str(asset.id),
        "asset_name": asset.name,
        "data": [
            {"column1": "value1", "column2": "value2"},
            {"column1": "value3", "column2": "value4"},
        ],
        "row_count": 2,
        "columns": ["column1", "column2"],
        "total_rows": 100,
        "limit": config.default_limit,
        "offset": 0,
    }
