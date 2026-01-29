"""元数据联动ETL服务 - FastAPI 应用"""

import logging
import uuid
from typing import Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from services.common.auth import get_current_user, TokenPayload
from services.common.exceptions import register_exception_handlers, NotFoundError
from services.common.http_client import ServiceClient
from services.common.middleware import RequestLoggingMiddleware
from services.metadata_sync.config import settings
from services.metadata_sync.models import (
    MetadataChangeEvent,
    ETLMapping,
    SyncResult,
    ChangeType,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="DataHub 元数据变更自动触发 ETL 任务配置更新",
    version="0.1.0",
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

# 内存存储映射规则（生产环境应使用数据库）
_mappings: dict[str, ETLMapping] = {}

datahub_client = ServiceClient(settings.DATAHUB_GMS_URL, token=settings.DATAHUB_TOKEN)
ds_client = ServiceClient(settings.DOLPHINSCHEDULER_API_URL, token=settings.DOLPHINSCHEDULER_TOKEN)
seatunnel_client = ServiceClient(settings.SEATUNNEL_API_URL)


@app.post("/api/metadata/webhook", response_model=SyncResult)
async def receive_metadata_event(event: MetadataChangeEvent):
    """接收 DataHub 元数据变更事件 (Webhook)"""
    if event.event_id is None:
        event.event_id = str(uuid.uuid4())

    logger.info(f"收到元数据变更事件: {event.entity_urn} [{event.change_type}]")

    # 查找匹配的映射规则
    affected_tasks = []
    for mapping in _mappings.values():
        if not mapping.enabled:
            continue
        if mapping.source_urn != event.entity_urn:
            continue
        if event.change_type not in mapping.trigger_on:
            continue

        # 触发 ETL 任务更新
        try:
            if mapping.target_task_type == "dolphinscheduler":
                await _trigger_dolphinscheduler(mapping.target_task_id)
            elif mapping.target_task_type == "seatunnel":
                await _trigger_seatunnel(mapping.target_task_id)
            affected_tasks.append(f"{mapping.target_task_type}:{mapping.target_task_id}")
        except Exception as e:
            logger.error(f"触发任务失败: {mapping.target_task_id}, 错误: {e}")

    return SyncResult(
        success=True,
        message=f"处理完成，触发 {len(affected_tasks)} 个任务",
        affected_tasks=affected_tasks,
    )


@app.post("/api/metadata/sync", response_model=SyncResult)
async def manual_sync(
    user: TokenPayload = Depends(get_current_user),
):
    """手动触发全量元数据同步"""
    try:
        # 调用 DataHub 获取最新元数据
        datasets = await datahub_client.get("/entities?action=search", params={
            "entity": "dataset",
            "start": 0,
            "count": 100,
        })
        return SyncResult(
            success=True,
            message="元数据同步完成",
            details={"synced_entities": len(datasets) if isinstance(datasets, list) else 0},
        )
    except Exception as e:
        return SyncResult(success=False, message=f"同步失败: {e}")


@app.get("/api/metadata/mappings", response_model=list[ETLMapping])
async def list_mappings(user: TokenPayload = Depends(get_current_user)):
    """列出所有映射规则"""
    return list(_mappings.values())


@app.put("/api/metadata/mappings/{mapping_id}", response_model=ETLMapping)
async def update_mapping(
    mapping_id: str,
    mapping: ETLMapping,
    user: TokenPayload = Depends(get_current_user),
):
    """更新映射规则"""
    if mapping_id not in _mappings:
        # 新建
        mapping.id = mapping_id
    _mappings[mapping_id] = mapping
    return mapping


async def _trigger_dolphinscheduler(task_id: str):
    """触发 DolphinScheduler 任务"""
    await ds_client.post(f"/projects/1/executors/start-process-instance", data={
        "processDefinitionId": int(task_id),
        "failureStrategy": "CONTINUE",
        "warningType": "NONE",
    })


async def _trigger_seatunnel(task_id: str):
    """触发 SeaTunnel 任务"""
    await seatunnel_client.post(f"/hazelcast/rest/maps/submit-job", data={
        "job_id": task_id,
    })


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "metadata-sync"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
