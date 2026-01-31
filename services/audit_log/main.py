"""统一审计日志服务 - FastAPI 应用

使用数据库持久化审计事件，支持查询、统计和导出。
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.exceptions import register_exception_handlers, NotFoundError
from services.common.metrics import setup_metrics
from services.common.orm_models import AuditEventORM
from services.common.repositories.audit_repository import AuditRepository
from services.audit_log.config import settings
from services.audit_log.models import (
    AuditEvent,
    AuditQuery,
    AuditStats,
    ExportRequest,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="统一审计日志系统 - 汇总各组件操作日志",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
setup_metrics(app)


def _orm_to_pydantic(orm: AuditEventORM) -> AuditEvent:
    """ORM 模型转 Pydantic 模型"""
    return AuditEvent(
        id=orm.id,
        subsystem=orm.subsystem,
        event_type=orm.event_type,
        user=orm.user,
        action=orm.action,
        resource=orm.resource,
        status_code=orm.status_code,
        duration_ms=orm.duration_ms,
        ip_address=orm.ip_address,
        user_agent=orm.user_agent,
        details=orm.details,
        created_at=orm.created_at,
    )


def _pydantic_to_orm(event: AuditEvent) -> AuditEventORM:
    """Pydantic 模型转 ORM 模型"""
    return AuditEventORM(
        id=event.id or str(uuid.uuid4()),
        subsystem=event.subsystem,
        event_type=event.event_type,
        user=event.user,
        action=event.action,
        resource=event.resource,
        status_code=event.status_code,
        duration_ms=event.duration_ms,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        details=event.details,
        created_at=event.created_at or datetime.now(timezone.utc),
    )


@app.post("/api/audit/log", response_model=AuditEvent)
async def record_event(
    event: AuditEvent,
    db: AsyncSession = Depends(get_db),
):
    """记录审计事件（不需要认证，供内部服务调用）"""
    event.id = str(uuid.uuid4())
    event.created_at = datetime.now(timezone.utc)

    repo = AuditRepository(db)
    orm_event = _pydantic_to_orm(event)
    await repo.create(orm_event)

    return event


@app.get("/api/audit/logs", response_model=list[AuditEvent])
async def query_logs(
    subsystem: Optional[str] = None,
    event_type: Optional[str] = None,
    user: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """查询审计日志"""
    repo = AuditRepository(db)
    results = await repo.query(
        subsystem=subsystem,
        event_type=event_type,
        user=user,
        page=page,
        page_size=page_size,
    )
    return [_orm_to_pydantic(r) for r in results]


@app.get("/api/audit/logs/{log_id}", response_model=AuditEvent)
async def get_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """获取指定日志"""
    repo = AuditRepository(db)
    event = await repo.get_by_id(log_id)
    if not event:
        raise NotFoundError("审计日志", log_id)
    return _orm_to_pydantic(event)


@app.get("/api/audit/stats", response_model=AuditStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """审计统计"""
    repo = AuditRepository(db)
    stats = await repo.get_stats()
    return AuditStats(**stats)


@app.post("/api/audit/export")
async def export_logs(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_user),
):
    """导出审计日志"""
    repo = AuditRepository(db)
    results = await repo.export(
        subsystem=req.query.subsystem,
        user=req.query.user,
        start_time=req.query.start_time,
        end_time=req.query.end_time,
    )
    events = [_orm_to_pydantic(r) for r in results]

    if req.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "subsystem", "event_type", "user", "action", "status_code", "created_at"])
        for e in events:
            writer.writerow([e.id, e.subsystem, e.event_type, e.user, e.action, e.status_code, e.created_at])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )
    else:
        data = [e.model_dump(mode="json") for e in events]
        return StreamingResponse(
            io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=audit_logs.json"},
        )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "audit-log"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
