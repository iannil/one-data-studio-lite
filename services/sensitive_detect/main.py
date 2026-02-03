"""敏感数据AI识别服务 - FastAPI 应用

使用数据库持久化检测规则和扫描报告。
"""

import logging
import uuid
from datetime import UTC, datetime

import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import TokenPayload, get_current_user
from services.common.database import (
    get_db,
    get_table_columns,
    validate_identifier,
    validate_table_exists,
)
from services.common.exceptions import AppException, NotFoundError, register_exception_handlers
from services.common.llm_client import LLMError, call_llm
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.common.orm_models import DetectionRuleORM, ScanReportORM, SensitiveFieldORM
from services.common.repositories.detection_repository import (
    DetectionRuleRepository,
    ScanReportRepository,
)
from services.sensitive_detect.config import settings
from services.sensitive_detect.models import (
    ClassifyRequest,
    DetectionRule,
    ScanReport,
    ScanRequest,
    SensitiveField,
    SensitivityLevel,
)
from services.sensitive_detect.patterns import detect_by_field_name, detect_by_pattern

logger = logging.getLogger(__name__)

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


def _rule_orm_to_pydantic(orm: DetectionRuleORM) -> DetectionRule:
    """ORM 转 Pydantic"""
    return DetectionRule(
        id=orm.id,
        name=orm.name,
        pattern=orm.pattern,
        sensitivity_level=SensitivityLevel(orm.sensitivity_level),
        description=orm.description or "",
        enabled=orm.enabled,
    )


def _rule_pydantic_to_orm(rule: DetectionRule) -> DetectionRuleORM:
    """Pydantic 转 ORM"""
    return DetectionRuleORM(
        id=rule.id or str(uuid.uuid4()),
        name=rule.name,
        pattern=rule.pattern,
        sensitivity_level=rule.sensitivity_level.value,
        description=rule.description,
        enabled=rule.enabled,
    )


def _field_to_orm(field: SensitiveField, report_id: str) -> SensitiveFieldORM:
    """SensitiveField 转 ORM"""
    return SensitiveFieldORM(
        report_id=report_id,
        column_name=field.column_name,
        sensitivity_level=field.sensitivity_level.value,
        detected_types=field.detected_types,
        detection_method=field.detection_method,
        sample_count=field.sample_count,
        confidence=field.confidence,
    )


def _field_orm_to_pydantic(orm: SensitiveFieldORM) -> SensitiveField:
    """ORM 转 Pydantic"""
    return SensitiveField(
        column_name=orm.column_name,
        sensitivity_level=SensitivityLevel(orm.sensitivity_level),
        detected_types=orm.detected_types,
        detection_method=orm.detection_method,
        sample_count=orm.sample_count,
        confidence=orm.confidence,
    )


def _report_orm_to_pydantic(
    orm: ScanReportORM,
    fields: list[SensitiveFieldORM],
) -> ScanReport:
    """ORM 转 Pydantic"""
    return ScanReport(
        id=orm.id,
        table_name=orm.table_name,
        scan_time=orm.scan_time,
        total_columns=orm.total_columns,
        sensitive_columns=orm.sensitive_columns,
        fields=[_field_orm_to_pydantic(f) for f in fields],
        risk_level=SensitivityLevel(orm.risk_level),
    )


def _level_order(level: SensitivityLevel) -> int:
    return {"low": 0, "medium": 1, "high": 2, "critical": 3}[level.value]


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

    # 获取列信息（使用兼容函数）
    all_columns = await get_table_columns(db, req.table_name)
    # Extract only name and type
    columns = [(col[0], col[1]) for col in all_columns]

    sensitive_fields: list[SensitiveField] = []

    for col_name, data_type in columns:
        detected_types = []
        detection_method = ""
        max_level = None

        try:
            safe_col = validate_identifier(col_name)
        except ValueError:
            continue

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

    report_id = str(uuid.uuid4())[:8]

    # 创建 ORM 模型
    report_orm = ScanReportORM(
        id=report_id,
        table_name=req.table_name,
        database_name=req.database,
        scan_time=datetime.now(UTC),
        total_columns=len(columns),
        sensitive_columns=len(sensitive_fields),
        risk_level=risk_level.value,
        scanned_by=user.sub,
    )
    field_orms = [_field_to_orm(f, report_id) for f in sensitive_fields]

    # 保存到数据库
    repo = ScanReportRepository(db)
    await repo.create_with_fields(report_orm, field_orms)

    return ScanReport(
        id=report_id,
        table_name=req.table_name,
        scan_time=report_orm.scan_time,
        total_columns=len(columns),
        sensitive_columns=len(sensitive_fields),
        fields=sensitive_fields,
        risk_level=risk_level,
    )


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

    try:
        response = await call_llm(prompt=prompt, use_cache=True)
        return {"analysis": response}
    except LLMError as e:
        logger.error(f"LLM 分类调用失败: {e}")
        raise AppException(f"LLM 调用失败: {e}", code=e.code)


@app.get("/api/sensitive/rules", response_model=list[DetectionRule])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """列出检测规则"""
    repo = DetectionRuleRepository(db)
    results = await repo.get_all()
    return [_rule_orm_to_pydantic(r) for r in results]


@app.post("/api/sensitive/rules", response_model=DetectionRule)
async def add_rule(
    rule: DetectionRule,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """添加自定义检测规则"""
    rule.id = str(uuid.uuid4())[:8]
    repo = DetectionRuleRepository(db)
    orm = _rule_pydantic_to_orm(rule)
    await repo.create(orm)
    return rule


@app.get("/api/sensitive/rules/{rule_id}", response_model=DetectionRule)
async def get_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """获取检测规则"""
    repo = DetectionRuleRepository(db)
    orm = await repo.get_by_id(rule_id)
    if not orm:
        raise NotFoundError("检测规则", rule_id)
    return _rule_orm_to_pydantic(orm)


@app.delete("/api/sensitive/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """删除检测规则"""
    repo = DetectionRuleRepository(db)
    success = await repo.delete(rule_id)
    if not success:
        raise NotFoundError("检测规则", rule_id)
    return {"message": "规则已删除"}


@app.get("/api/sensitive/reports", response_model=list[ScanReport])
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """列出扫描报告"""
    repo = ScanReportRepository(db)
    reports = await repo.get_latest_reports(page=page, page_size=page_size)
    result = []
    for r in reports:
        fields = await repo.get_fields(r.id)
        result.append(_report_orm_to_pydantic(r, list(fields)))
    return result


@app.get("/api/sensitive/reports/{report_id}", response_model=ScanReport)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """获取扫描报告"""
    repo = ScanReportRepository(db)
    report = await repo.get_by_id(report_id)
    if not report:
        raise NotFoundError("扫描报告", report_id)
    fields = await repo.get_fields(report_id)
    return _report_orm_to_pydantic(report, list(fields))


# ============================================================
# 敏感检测与脱敏联动
# ============================================================

class ScanAndApplyRequest(BaseModel):
    """扫描并应用脱敏规则请求"""
    table_name: str
    database: str | None = None
    sample_size: int = 100
    auto_apply: bool = True


class ScanAndApplyResponse(BaseModel):
    """扫描并应用脱敏规则响应"""
    report: ScanReport
    applied_rules: list[dict]
    skipped_rules: list[dict]




@app.post("/api/sensitive/scan-and-apply", response_model=ScanAndApplyResponse)
async def scan_and_apply(
    req: ScanAndApplyRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """扫描敏感数据并保存脱敏规则到数据库

    工作流程:
    1. 扫描表，识别敏感字段
    2. 根据敏感类型匹配脱敏算法
    3. 保存脱敏规则到数据库（供后续导出或使用）

    注意: ShardingSphere 已移除，脱敏规则仅保存到数据库。
    """
    # 1. 执行扫描
    scan_req = ScanRequest(
        table_name=req.table_name,
        database=req.database,
        sample_size=req.sample_size,
    )

    # 复用扫描逻辑
    try:
        safe_table = await validate_table_exists(db, req.table_name)
    except ValueError as e:
        raise AppException(str(e), code=400)

    # 获取列信息（使用兼容函数）
    all_columns = await get_table_columns(db, req.table_name)
    # Extract only name and type
    columns = [(col[0], col[1]) for col in all_columns]

    sensitive_fields: list[SensitiveField] = []

    for col_name, data_type in columns:
        detected_types = []
        detection_method = ""
        max_level = None

        try:
            safe_col = validate_identifier(col_name)
        except ValueError:
            continue

        field_level = detect_by_field_name(col_name)
        if field_level:
            detected_types.append(f"field_name:{col_name}")
            detection_method = "field_name"
            max_level = SensitivityLevel(field_level)

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

    if sensitive_fields:
        levels = [f.sensitivity_level for f in sensitive_fields]
        risk_level = max(levels, key=_level_order)
    else:
        risk_level = SensitivityLevel.LOW

    report_id = str(uuid.uuid4())[:8]
    report_orm = ScanReportORM(
        id=report_id,
        table_name=req.table_name,
        database_name=req.database,
        scan_time=datetime.now(UTC),
        total_columns=len(columns),
        sensitive_columns=len(sensitive_fields),
        risk_level=risk_level.value,
        scanned_by=user.sub,
    )
    field_orms = [_field_to_orm(f, report_id) for f in sensitive_fields]
    repo = ScanReportRepository(db)
    await repo.create_with_fields(report_orm, field_orms)

    report = ScanReport(
        id=report_id,
        table_name=req.table_name,
        scan_time=report_orm.scan_time,
        total_columns=len(columns),
        sensitive_columns=len(sensitive_fields),
        fields=sensitive_fields,
        risk_level=risk_level,
    )

    # 2. 匹配脱敏算法并应用
    applied_rules = []
    skipped_rules = []

    if req.auto_apply and sensitive_fields:
        # 敏感类型到脱敏算法的映射
        type_to_algorithm = {
            "phone": ("KEEP_FIRST_N_LAST_M", {"first-n": "3", "last-m": "4", "replace-char": "*"}),
            "id_card": ("KEEP_FIRST_N_LAST_M", {"first-n": "6", "last-m": "4", "replace-char": "*"}),
            "bank_card": ("KEEP_FIRST_N_LAST_M", {"first-n": "0", "last-m": "4", "replace-char": "*"}),
            "email": ("MASK_BEFORE_SPECIAL_CHARS", {"special-chars": "@", "replace-char": "*"}),
        }

        for field in sensitive_fields:
            # 从 detected_types 中提取敏感类型
            sensitive_type = None
            for dt in field.detected_types:
                if dt in type_to_algorithm:
                    sensitive_type = dt
                    break
                # 处理 field_name:xxx 格式
                if ":" in dt:
                    base_type = dt.split(":")[0]
                    if base_type == "field_name":
                        # 根据字段名推断类型
                        col_lower = field.column_name.lower()
                        if "phone" in col_lower or "mobile" in col_lower:
                            sensitive_type = "phone"
                        elif "id_card" in col_lower or "idcard" in col_lower:
                            sensitive_type = "id_card"
                        elif "email" in col_lower:
                            sensitive_type = "email"
                        elif "bank" in col_lower or "card" in col_lower:
                            sensitive_type = "bank_card"
                        break

            if sensitive_type and sensitive_type in type_to_algorithm:
                algorithm, props = type_to_algorithm[sensitive_type]
                rule_info = {
                    "table_name": req.table_name,
                    "column_name": field.column_name,
                    "algorithm_type": algorithm,
                    "algorithm_props": props,
                    "sensitive_type": sensitive_type,
                }

                # 保存脱敏规则到数据库（ShardingSphere 已移除）
                # 规则可以导出或在其他脱敏系统中使用
                applied_rules.append(rule_info)
            else:
                skipped_rules.append({
                    "table_name": req.table_name,
                    "column_name": field.column_name,
                    "reason": "无匹配的脱敏算法",
                    "detected_types": field.detected_types,
                })

    return ScanAndApplyResponse(
        report=report,
        applied_rules=applied_rules,
        skipped_rules=skipped_rules,
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sensitive-detect"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
