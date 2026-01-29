"""数据资产服务API网关 - FastAPI 应用"""

from typing import Any, Optional

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db, validate_table_exists, validate_identifier
from services.common.exceptions import register_exception_handlers, NotFoundError, AppException
from services.common.http_client import ServiceClient
from services.common.middleware import RequestLoggingMiddleware
from services.data_api.config import settings
from services.data_api.models import (
    DatasetQuery,
    DatasetSchema,
    ColumnSchema,
    AssetInfo,
    SearchRequest,
    SearchResult,
    Subscription,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="统一数据资产服务API网关",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="data-api")
register_exception_handlers(app)

datahub_client = ServiceClient(settings.DATAHUB_GMS_URL, token=settings.DATAHUB_TOKEN)

# 内存订阅存储
_subscriptions: dict[str, list[Subscription]] = {}


@app.get("/api/data/{dataset_id}")
async def query_dataset(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """查询数据集数据"""
    # dataset_id 映射为表名
    table_name = dataset_id.replace("-", "_")
    offset = (page - 1) * page_size

    try:
        # 验证表名安全性
        safe_table = await validate_table_exists(db, table_name)

        result = await db.execute(text(
            f"SELECT * FROM {safe_table} LIMIT :limit OFFSET :offset"
        ), {"limit": page_size, "offset": offset})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

        count_result = await db.execute(text(f"SELECT COUNT(*) FROM {safe_table}"))
        total = count_result.scalar() or 0
    except ValueError:
        raise NotFoundError("数据集", dataset_id)
    except Exception as e:
        raise NotFoundError("数据集", dataset_id)

    return {"dataset_id": dataset_id, "total": total, "page": page, "data": rows}


@app.get("/api/data/{dataset_id}/schema", response_model=DatasetSchema)
async def get_dataset_schema(
    dataset_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """获取数据集 Schema"""
    table_name = dataset_id.replace("-", "_")

    # 验证表名安全性
    try:
        safe_table = await validate_table_exists(db, table_name)
    except ValueError:
        raise NotFoundError("数据集", dataset_id)

    result = await db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT, COLUMN_KEY, IS_NULLABLE "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table "
        "ORDER BY ORDINAL_POSITION"
    ), {"table": table_name})
    cols = result.fetchall()
    if not cols:
        raise NotFoundError("数据集", dataset_id)

    columns = [
        ColumnSchema(
            name=c[0], data_type=c[1], description=c[2] or None,
            is_primary_key=(c[3] == "PRI"), is_nullable=(c[4] == "YES"),
        )
        for c in cols
    ]

    count_result = await db.execute(text(f"SELECT COUNT(*) FROM {safe_table}"))
    row_count = count_result.scalar()

    return DatasetSchema(
        dataset_id=dataset_id,
        name=table_name,
        columns=columns,
        row_count=row_count,
    )


@app.post("/api/data/{dataset_id}/query")
async def custom_query(
    dataset_id: str,
    req: DatasetQuery,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """在数据集上执行自定义查询"""
    table_name = dataset_id.replace("-", "_")

    # 验证表名安全性
    try:
        safe_table = await validate_table_exists(db, table_name)
    except ValueError:
        raise NotFoundError("数据集", dataset_id)

    if req.sql:
        # 安全检查 - 只允许 SELECT
        sql_upper = req.sql.upper().strip()
        if not sql_upper.startswith("SELECT"):
            raise AppException("仅允许 SELECT 查询", code=400)

        # 禁止危险操作
        dangerous_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER", "CREATE", "GRANT", "EXECUTE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise AppException(f"不允许使用 {keyword} 操作", code=400)

        result = await db.execute(text(req.sql))
    else:
        offset = (req.page - 1) * req.page_size
        result = await db.execute(text(
            f"SELECT * FROM {safe_table} LIMIT :limit OFFSET :offset"
        ), {"limit": req.page_size, "offset": offset})

    columns = list(result.keys())
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return {"columns": columns, "data": rows, "row_count": len(rows)}


@app.get("/api/assets/search", response_model=SearchResult)
async def search_assets(
    query: str = Query(..., min_length=1),
    asset_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
):
    """搜索数据资产 (通过 DataHub)"""
    try:
        search_result = await datahub_client.post("/entities?action=search", data={
            "input": query,
            "entity": "dataset",
            "start": (page - 1) * page_size,
            "count": page_size,
        })
        # 转换 DataHub 结果
        assets = []
        entities = search_result.get("value", {}).get("entities", [])
        for entity in entities:
            assets.append(AssetInfo(
                asset_id=entity.get("entity", ""),
                name=entity.get("entity", "").split(",")[-1] if "," in entity.get("entity", "") else entity.get("entity", ""),
                asset_type="table",
                tags=[],
            ))
        total = search_result.get("value", {}).get("numEntities", 0)
    except Exception:
        assets = []
        total = 0

    return SearchResult(total=total, assets=assets)


@app.get("/api/assets/{asset_id}", response_model=AssetInfo)
async def get_asset(
    asset_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    """获取资产详情"""
    try:
        entity = await datahub_client.get(f"/entities/{asset_id}")
        return AssetInfo(
            asset_id=asset_id,
            name=entity.get("name", asset_id),
            description=entity.get("description"),
            asset_type="table",
        )
    except Exception:
        raise NotFoundError("数据资产", asset_id)


@app.post("/api/assets/{asset_id}/subscribe", response_model=Subscription)
async def subscribe_asset(
    asset_id: str,
    sub: Subscription,
    user: TokenPayload = Depends(get_current_user),
):
    """订阅资产变更"""
    sub.asset_id = asset_id
    sub.subscriber = user.username
    _subscriptions.setdefault(asset_id, []).append(sub)
    return sub


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "data-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
