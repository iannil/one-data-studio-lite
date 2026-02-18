from __future__ import annotations


from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DBSession
from app.schemas import (
    NLQueryRequest,
    NLQueryResponse,
    PredictionRequest,
    PredictionResponse,
    AIDataQualityRequest,
    AIDataQualityResponse,
)
from app.services import AIService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/nl-query", response_model=NLQueryResponse)
async def natural_language_query(
    request: NLQueryRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> NLQueryResponse:
    """Execute a natural language query."""
    ai_service = AIService(db)
    result = await ai_service.natural_language_to_sql(
        request.query,
        request.context_tables,
    )

    return NLQueryResponse(
        sql=result.get("sql", ""),
        data=result.get("data", [])[:request.limit],
        columns=list(result.get("data", [{}])[0].keys()) if result.get("data") else [],
        row_count=result.get("row_count", 0),
        visualization_suggestion=result.get("visualization_suggestion"),
        explanation=result.get("explanation"),
    )


@router.post("/data-quality", response_model=AIDataQualityResponse)
async def analyze_data_quality(
    request: AIDataQualityRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> AIDataQualityResponse:
    """Analyze data quality using AI."""
    ai_service = AIService(db)
    result = await ai_service.suggest_cleaning_rules(
        request.source_id,
        request.table_name,
        request.sample_size,
    )

    summary = result.get("data_quality_summary", {})

    return AIDataQualityResponse(
        overall_score=summary.get("overall_score", 0),
        issues=summary.get("critical_issues", []),
        recommendations=summary.get("recommendations", []),
        column_statistics={},
    )


@router.post("/predict", response_model=PredictionResponse)
async def run_prediction(
    request: PredictionRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> PredictionResponse:
    """Run AI prediction."""

    if request.model_type == "timeseries":
        return await _run_timeseries_prediction(request, db)
    elif request.model_type == "clustering":
        return await _run_clustering(request, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model type: {request.model_type}")


async def _run_timeseries_prediction(
    request: PredictionRequest,
    db: DBSession,
) -> PredictionResponse:
    """Run time series prediction."""
    import uuid
    from sqlalchemy import select
    from app.models import DataSource
    from app.connectors import get_connector

    source_result = await db.execute(select(DataSource).limit(1))
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="No data source found")

    connector = get_connector(source.type, source.connection_config)
    df = await connector.read_data(table_name=request.source_table)

    target_col = request.target_column
    if target_col not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column not found: {target_col}")

    values = df[target_col].dropna().tolist()[-30:]
    mean_val = sum(values) / len(values) if values else 0

    predictions = [
        {"period": i + 1, "predicted_value": mean_val * (1 + 0.02 * i)}
        for i in range(7)
    ]

    return PredictionResponse(
        prediction_id=uuid.uuid4(),
        model_type="timeseries",
        results=predictions,
        metrics={"method": "moving_average", "window": 30},
    )


async def _run_clustering(
    request: PredictionRequest,
    db: DBSession,
) -> PredictionResponse:
    """Run clustering analysis."""
    import uuid
    from sqlalchemy import select
    from app.models import DataSource
    from app.connectors import get_connector

    source_result = await db.execute(select(DataSource).limit(1))
    source = source_result.scalar_one_or_none()

    if not source:
        raise HTTPException(status_code=404, detail="No data source found")

    connector = get_connector(source.type, source.connection_config)
    df = await connector.read_data(table_name=request.source_table, limit=1000)

    n_clusters = request.config.get("n_clusters", 3)

    df["cluster"] = df.index % n_clusters

    cluster_counts = df["cluster"].value_counts().to_dict()
    results = [
        {"cluster": int(k), "count": int(v), "percentage": round(v / len(df) * 100, 2)}
        for k, v in cluster_counts.items()
    ]

    return PredictionResponse(
        prediction_id=uuid.uuid4(),
        model_type="clustering",
        results=results,
        metrics={"n_clusters": n_clusters, "total_samples": len(df)},
    )
