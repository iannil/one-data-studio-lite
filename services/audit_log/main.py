"""统一审计日志服务 - FastAPI 应用"""

import csv
import io
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from services.common.auth import get_current_user, TokenPayload
from services.common.exceptions import register_exception_handlers, NotFoundError
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

# 内存存储（生产环境应使用数据库 + Elasticsearch）
_audit_logs: list[AuditEvent] = []


@app.post("/api/audit/log", response_model=AuditEvent)
async def record_event(event: AuditEvent):
    """记录审计事件（不需要认证，供内部服务调用）"""
    event.id = str(uuid.uuid4())[:12]
    event.created_at = datetime.now(timezone.utc)
    _audit_logs.append(event)

    # 保持内存大小合理（开发环境）
    if len(_audit_logs) > 10000:
        _audit_logs[:] = _audit_logs[-5000:]

    return event


@app.get("/api/audit/logs", response_model=list[AuditEvent])
async def query_logs(
    subsystem: Optional[str] = None,
    event_type: Optional[str] = None,
    user: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_user: TokenPayload = Depends(get_current_user),
):
    """查询审计日志"""
    filtered = _audit_logs

    if subsystem:
        filtered = [e for e in filtered if e.subsystem == subsystem]
    if event_type:
        filtered = [e for e in filtered if e.event_type == event_type]
    if user:
        filtered = [e for e in filtered if e.user == user]

    # 按时间倒序
    filtered.sort(key=lambda e: e.created_at or datetime.min, reverse=True)

    # 分页
    start = (page - 1) * page_size
    return filtered[start : start + page_size]


@app.get("/api/audit/logs/{log_id}", response_model=AuditEvent)
async def get_log(
    log_id: str,
    current_user: TokenPayload = Depends(get_current_user),
):
    """获取指定日志"""
    for event in _audit_logs:
        if event.id == log_id:
            return event
    raise NotFoundError("审计日志", log_id)


@app.get("/api/audit/stats", response_model=AuditStats)
async def get_stats(current_user: TokenPayload = Depends(get_current_user)):
    """审计统计"""
    by_subsystem: dict[str, int] = defaultdict(int)
    by_type: dict[str, int] = defaultdict(int)
    by_user: dict[str, int] = defaultdict(int)

    for event in _audit_logs:
        by_subsystem[event.subsystem] += 1
        by_type[event.event_type] += 1
        by_user[event.user] += 1

    times = [e.created_at for e in _audit_logs if e.created_at]

    return AuditStats(
        total_events=len(_audit_logs),
        events_by_subsystem=dict(by_subsystem),
        events_by_type=dict(by_type),
        events_by_user=dict(by_user),
        time_range_start=min(times) if times else None,
        time_range_end=max(times) if times else None,
    )


@app.post("/api/audit/export")
async def export_logs(
    req: ExportRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """导出审计日志"""
    filtered = _audit_logs

    if req.query.subsystem:
        filtered = [e for e in filtered if e.subsystem == req.query.subsystem]
    if req.query.user:
        filtered = [e for e in filtered if e.user == req.query.user]

    if req.format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "subsystem", "event_type", "user", "action", "status_code", "created_at"])
        for e in filtered:
            writer.writerow([e.id, e.subsystem, e.event_type, e.user, e.action, e.status_code, e.created_at])
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
        )
    else:
        data = [e.model_dump(mode="json") for e in filtered]
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
