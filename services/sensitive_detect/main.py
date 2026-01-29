"""敏感数据AI识别服务 - FastAPI 应用"""

import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db, validate_table_exists, validate_identifier
from services.common.exceptions import register_exception_handlers, AppException
from services.common.middleware import RequestLoggingMiddleware
from services.common.metrics import setup_metrics
from services.sensitive_detect.config import settings
from services.sensitive_detect.models import (
    ScanRequest,
    ScanReport,
    SensitiveField,
    SensitivityLevel,
    DetectionRule,
    ClassifyRequest,
)
from services.sensitive_detect.patterns import detect_by_pattern, detect_by_field_name

app = FastAPI(
    title=settings.APP_NAME,
    description="敏感数据 AI 识别服务（正则 + LLM）",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="sensitive-detect")
register_exception_handlers(app)
setup_metrics(app)

# 自定义规则存储
_custom_rules: dict[str, DetectionRule] = {}
# 扫描报告存储
_reports: dict[str, ScanReport] = {}


@app.post("/api/sensitive/scan", response_model=ScanReport)
async def scan_table(
    req: ScanRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """扫描表中的敏感数据"""
    # 验证表名安全性
    try:
        safe_table = await validate_table_exists(db, req.table_name)
    except ValueError as e:
        raise AppException(str(e), code=400)

    # 获取列信息
    cols_result = await db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
    ), {"table": req.table_name})
    columns = cols_result.fetchall()

    sensitive_fields: list[SensitiveField] = []

    for col_name, data_type in columns:
        detected_types = []
        detection_method = ""
        max_level = None

        # 列名来自 information_schema，是安全的，但仍需验证格式
        try:
            safe_col = validate_identifier(col_name)
        except ValueError:
            continue  # 跳过格式异常的列名

        # 1. 字段名检测
        field_level = detect_by_field_name(col_name)
        if field_level:
            detected_types.append(f"field_name:{col_name}")
            detection_method = "field_name"
            max_level = SensitivityLevel(field_level)

        # 2. 正则表达式检测（仅字符串类型）
        if data_type in ("varchar", "char", "text", "longtext", "mediumtext"):
            sample_result = await db.execute(text(
                f"SELECT {safe_col} FROM {safe_table} "
                f"WHERE {safe_col} IS NOT NULL LIMIT :limit"
            ), {"limit": req.sample_size})
            samples = [row[0] for row in sample_result.fetchall() if row[0]]

            match_count = 0
            for sample in samples:
                matches = detect_by_pattern(str(sample))
                if matches:
                    match_count += 1
                    for m in matches:
                        if m["type"] not in detected_types:
                            detected_types.append(m["type"])
                        level = SensitivityLevel(m["level"])
                        if max_level is None or _level_order(level) > _level_order(max_level):
                            max_level = level

            if match_count > 0:
                detection_method = detection_method + "+regex" if detection_method else "regex"
                confidence = match_count / len(samples) if samples else 0
            else:
                confidence = 0.5 if detection_method else 0
        else:
            confidence = 0.5 if detection_method else 0
            match_count = 0

        if detected_types and max_level:
            sensitive_fields.append(SensitiveField(
                column_name=col_name,
                sensitivity_level=max_level,
                detected_types=detected_types,
                detection_method=detection_method,
                sample_count=match_count,
                confidence=confidence,
            ))

    # 确定整体风险级别
    if sensitive_fields:
        levels = [f.sensitivity_level for f in sensitive_fields]
        risk_level = max(levels, key=_level_order)
    else:
        risk_level = SensitivityLevel.LOW

    report = ScanReport(
        id=str(uuid.uuid4())[:8],
        table_name=req.table_name,
        scan_time=datetime.now(timezone.utc),
        total_columns=len(columns),
        sensitive_columns=len(sensitive_fields),
        fields=sensitive_fields,
        risk_level=risk_level,
    )

    _reports[report.id] = report
    return report


@app.post("/api/sensitive/classify")
async def classify_data(
    req: ClassifyRequest,
    user: TokenPayload = Depends(get_current_user),
):
    """使用 LLM 分类数据敏感性"""
    samples_str = "\n".join(str(s) for s in req.data_samples[:10])
    prompt = f"""分析以下数据样本，识别其中包含的敏感信息类型。

数据样本:
{samples_str}

{f'额外上下文: {req.context}' if req.context else ''}

请以 JSON 格式输出分析结果，包含:
- field: 字段名
- type: 敏感类型 (phone/id_card/email/bank_card/address/name/其他)
- level: 敏感级别 (low/medium/high/critical)
- reason: 判断理由

只输出 JSON 数组。"""

    url = f"{settings.LLM_BASE_URL}/api/generate"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json={
            "model": settings.LLM_MODEL,
            "prompt": prompt,
            "stream": False,
        })
        resp.raise_for_status()
        return {"analysis": resp.json().get("response", "")}


@app.get("/api/sensitive/rules", response_model=list[DetectionRule])
async def list_rules(user: TokenPayload = Depends(get_current_user)):
    """列出检测规则"""
    return list(_custom_rules.values())


@app.post("/api/sensitive/rules", response_model=DetectionRule)
async def add_rule(
    rule: DetectionRule,
    user: TokenPayload = Depends(get_current_user),
):
    """添加自定义检测规则"""
    rule.id = str(uuid.uuid4())[:8]
    _custom_rules[rule.id] = rule
    return rule


@app.get("/api/sensitive/reports", response_model=list[ScanReport])
async def list_reports(user: TokenPayload = Depends(get_current_user)):
    """列出扫描报告"""
    return list(_reports.values())


def _level_order(level: SensitivityLevel) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}[level.value]


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sensitive-detect"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
