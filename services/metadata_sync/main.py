"""元数据联动ETL服务 - FastAPI 应用

适配 OpenMetadata Webhook 格式。
"""

import json
import logging
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import TokenPayload, get_current_user
from services.common.database import get_db
from services.common.exceptions import NotFoundError, register_exception_handlers
from services.common.http_client import ServiceClient
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.common.orm_models import ETLMappingORM
from services.common.repositories.mapping_repository import ETLMappingRepository
from services.common.webhook_security import create_webhook_verifier
from services.metadata_sync.config import settings
from services.metadata_sync.models import (
    ChangeType,
    ETLMapping,
    MetadataChangeEvent,
    SyncResult,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="OpenMetadata 元数据变更自动触发 ETL 任务配置更新",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="metadata-sync")
register_exception_handlers(app)
setup_metrics(app)

# OpenMetadata 客户端
openmetadata_url = getattr(settings, 'OPENMETADATA_API_URL', None) or settings.DATAHUB_GMS_URL
openmetadata_token = getattr(settings, 'OPENMETADATA_JWT_TOKEN', None) or settings.DATAHUB_TOKEN
openmetadata_client = ServiceClient(openmetadata_url, token=openmetadata_token)

# ETL 系统客户端
ds_client = ServiceClient(settings.DOLPHINSCHEDULER_API_URL, token=settings.DOLPHINSCHEDULER_TOKEN)
seatunnel_client = ServiceClient(settings.SEATUNNEL_API_URL)
hop_client = ServiceClient(settings.HOP_API_URL)

# Webhook 签名验证器（支持 OpenMetadata 格式）
webhook_secret = getattr(settings, 'OPENMETADATA_WEBHOOK_SECRET', None) or settings.DATAHUB_WEBHOOK_SECRET
webhook_verifier = create_webhook_verifier(
    secret=webhook_secret,
    header_name="X-OM-Signature",  # OpenMetadata 使用的签名头
    is_development=settings.is_development(),
)


def _orm_to_pydantic(orm: ETLMappingORM) -> ETLMapping:
    """ORM 转 Pydantic"""
    return ETLMapping(
        id=orm.id,
        source_urn=orm.source_urn,
        target_task_type=orm.target_task_type,
        target_task_id=orm.target_task_id,
        trigger_on=[ChangeType(t) for t in orm.trigger_on],
        auto_update_config=orm.auto_update_config,
        description=orm.description or "",
        enabled=orm.enabled,
        source_fqn=getattr(orm, 'source_fqn', None),
    )


def _pydantic_to_orm(mapping: ETLMapping, created_by: str | None = None) -> ETLMappingORM:
    """Pydantic 转 ORM"""
    return ETLMappingORM(
        id=mapping.id,
        source_urn=mapping.source_urn,
        target_task_type=mapping.target_task_type,
        target_task_id=mapping.target_task_id,
        trigger_on=[t.value for t in mapping.trigger_on],
        auto_update_config=mapping.auto_update_config,
        description=mapping.description,
        enabled=mapping.enabled,
        created_by=created_by,
    )


@app.post("/api/metadata/webhook", response_model=SyncResult)
async def receive_metadata_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    body: bytes = Depends(webhook_verifier),
):
    """接收 OpenMetadata 元数据变更事件 (Webhook)

    支持两种格式：
    1. OpenMetadata Alerts/Notifications 格式（推荐）
    2. DataHub 格式（向后兼容）

    此端点需要有效的 HMAC 签名验证。
    签名应在 X-OM-Signature 头中提供。

    OpenMetadata 事件示例:
    {
        "eventType": "entityCreated",
        "entityType": "table",
        "entityId": "uuid",
        "entityFullyQualifiedName": "mysql.db.table",
        "changeDescription": {
            "fieldsAdded": [],
            "fieldsUpdated": [],
            "fieldsDeleted": []
        }
    }

    开发环境（ENVIRONMENT != production）允许无签名请求，但会记录警告。
    """
    # 解析 JSON body
    try:
        event_data = json.loads(body)
        event = MetadataChangeEvent(**event_data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"无法解析 Webhook 请求体: {e}")
        return SyncResult(
            success=False,
            message=f"请求体解析失败: {e}",
            affected_tasks=[],
        )

    if event.event_id is None:
        event.event_id = str(uuid.uuid4())

    # 记录事件详情
    entity_identifier = event.entityFullyQualifiedName or event.entity_urn or "unknown"
    logger.info(f"收到元数据变更事件: {entity_identifier} [{event.change_type}] (type: {event.eventType or event.entity_type})")

    # 查找匹配的映射规则
    repo = ETLMappingRepository(db)
    all_mappings = await repo.get_all()

    # 使用 ETLMapping.matches_event 方法匹配
    matching_orm = []
    for orm in all_mappings:
        mapping = _orm_to_pydantic(orm)
        if mapping.matches_event(event):
            matching_orm.append(orm)

    # 如果没有匹配到，回退到旧的匹配逻辑
    if not matching_orm and event.entity_urn:
        matching_orm = await repo.find_matching(event.entity_urn, event.change_type.value)

    affected_tasks = []
    for orm in matching_orm:
        mapping = _orm_to_pydantic(orm)
        try:
            if mapping.target_task_type == "dolphinscheduler":
                await _trigger_dolphinscheduler(mapping.target_task_id)
            elif mapping.target_task_type == "seatunnel":
                await _trigger_seatunnel(mapping.target_task_id)
            elif mapping.target_task_type == "hop":
                await _trigger_hop(mapping.target_task_id)
            affected_tasks.append(f"{mapping.target_task_type}:{mapping.target_task_id}")
            logger.info(f"成功触发任务: {mapping.target_task_type}:{mapping.target_task_id}")
        except Exception as e:
            logger.error(f"触发任务失败: {mapping.target_task_id}, 错误: {e}")

    return SyncResult(
        success=True,
        message=f"处理完成，触发 {len(affected_tasks)} 个任务",
        affected_tasks=affected_tasks,
        details={
            "event_id": event.event_id,
            "event_type": event.eventType or event.entity_type,
            "entity": entity_identifier,
        },
    )


@app.post("/api/metadata/sync", response_model=SyncResult)
async def manual_sync(
    user: TokenPayload = Depends(get_current_user),
):
    """手动触发全量元数据同步

    从 OpenMetadata 获取所有表信息。
    """
    try:
        # OpenMetadata API: GET /api/v1/tables
        tables = await openmetadata_client.get("/tables", params={
            "limit": 100,
            "fields": "columns,tags",
        })
        synced_count = len(tables.get("data", [])) if isinstance(tables, dict) else 0
        return SyncResult(
            success=True,
            message="元数据同步完成",
            details={"synced_entities": synced_count},
        )
    except Exception as e:
        logger.error(f"元数据同步失败: {e}")
        return SyncResult(success=False, message=f"同步失败: {e}")


@app.get("/api/metadata/mappings", response_model=list[ETLMapping])
async def list_mappings(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """列出所有映射规则"""
    repo = ETLMappingRepository(db)
    results = await repo.get_all()
    return [_orm_to_pydantic(r) for r in results]


@app.post("/api/metadata/mappings", response_model=ETLMapping)
async def create_mapping(
    mapping: ETLMapping,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """创建映射规则"""
    mapping.id = str(uuid.uuid4())[:8]
    repo = ETLMappingRepository(db)
    orm = _pydantic_to_orm(mapping, created_by=user.sub)
    await repo.create(orm)
    return mapping


@app.get("/api/metadata/mappings/{mapping_id}", response_model=ETLMapping)
async def get_mapping(
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """获取映射规则"""
    repo = ETLMappingRepository(db)
    orm = await repo.get_by_id(mapping_id)
    if not orm:
        raise NotFoundError("映射规则", mapping_id)
    return _orm_to_pydantic(orm)


@app.put("/api/metadata/mappings/{mapping_id}", response_model=ETLMapping)
async def update_mapping(
    mapping_id: str,
    mapping: ETLMapping,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """更新映射规则"""
    repo = ETLMappingRepository(db)
    existing = await repo.get_by_id(mapping_id)

    if existing:
        existing.source_urn = mapping.source_urn
        existing.target_task_type = mapping.target_task_type
        existing.target_task_id = mapping.target_task_id
        existing.trigger_on = [t.value for t in mapping.trigger_on]
        existing.auto_update_config = mapping.auto_update_config
        existing.description = mapping.description
        existing.enabled = mapping.enabled
        await db.flush()
        return _orm_to_pydantic(existing)
    else:
        mapping.id = mapping_id
        orm = _pydantic_to_orm(mapping, created_by=user.sub)
        await repo.create(orm)
        return mapping


@app.delete("/api/metadata/mappings/{mapping_id}")
async def delete_mapping(
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """删除映射规则"""
    repo = ETLMappingRepository(db)
    success = await repo.delete(mapping_id)
    if not success:
        raise NotFoundError("映射规则", mapping_id)
    return {"message": "映射规则已删除"}


async def _trigger_dolphinscheduler(task_id: str):
    """触发 DolphinScheduler 任务"""
    await ds_client.post("/projects/1/executors/start-process-instance", data={
        "processDefinitionId": int(task_id),
        "failureStrategy": "CONTINUE",
        "warningType": "NONE",
    })


async def _trigger_seatunnel(task_id: str):
    """触发 SeaTunnel 任务"""
    await seatunnel_client.post("/hazelcast/rest/maps/submit-job", data={
        "job_id": task_id,
    })


async def _trigger_hop(task_id: str):
    """触发 Apache Hop 任务

    通过 Hop Server REST API 执行工作流或管道。
    """
    await hop_client.post(f"/hop/api/run/{task_id}", data={
        "runConfigurationName": "local",
    })


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "metadata-sync"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
