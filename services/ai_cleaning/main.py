"""AI清洗规则推荐服务 - FastAPI 应用"""

import json
import logging
import uuid

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db, validate_table_exists, validate_identifier
from services.common.exceptions import register_exception_handlers, AppException
from services.common.llm_client import call_llm, LLMError
from services.common.middleware import RequestLoggingMiddleware
from services.common.metrics import setup_metrics
from services.ai_cleaning.config import settings
from services.ai_cleaning.models import (
    AnalyzeRequest,
    DataQualityReport,
    QualityIssue,
    QualityIssueType,
    CleaningRule,
    CleaningRecommendation,
    GenerateConfigRequest,
    SeaTunnelTransformConfig,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI 辅助数据清洗规则推荐服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="ai-cleaning")
register_exception_handlers(app)
setup_metrics(app)


async def _call_llm_service(prompt: str) -> str:
    """调用 LLM（使用统一 LLM 客户端）"""
    try:
        return await call_llm(prompt=prompt, use_cache=False)
    except LLMError as e:
        raise AppException(f"LLM 调用失败: {e}", code=e.code)


def _parse_llm_json_response(llm_response: str, context: str = "") -> list:
    """解析 LLM 返回的 JSON

    Args:
        llm_response: LLM 返回的原始文本
        context: 上下文信息（用于日志）

    Returns:
        解析后的列表，解析失败时返回空列表并记录警告

    Note:
        不会静默失败，会记录警告日志
    """
    try:
        json_str = llm_response
        # 尝试提取 markdown 代码块中的 JSON
        if "```" in json_str:
            parts = json_str.split("```")
            if len(parts) >= 2:
                json_str = parts[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
        return json.loads(json_str.strip())
    except json.JSONDecodeError as e:
        logger.warning(
            f"LLM JSON 解析失败{f' ({context})' if context else ''}: {e}. "
            f"原始响应: {llm_response[:200]}..."
        )
        return []
    except (IndexError, AttributeError) as e:
        logger.warning(
            f"LLM 响应格式异常{f' ({context})' if context else ''}: {e}"
        )
        return []


@app.post("/api/cleaning/analyze", response_model=DataQualityReport)
async def analyze_table(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """分析表的数据质量"""
    # 验证表名安全性
    try:
        safe_table = await validate_table_exists(db, req.table_name)
    except ValueError as e:
        raise AppException(str(e), code=400)

    # 获取表总行数
    count_result = await db.execute(text(f"SELECT COUNT(*) FROM {safe_table}"))
    total_rows = count_result.scalar() or 0

    # 获取列信息
    cols_result = await db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
    ), {"table": req.table_name})
    columns = cols_result.fetchall()

    issues: list[QualityIssue] = []

    for col_name, data_type, is_nullable in columns:
        # 验证列名格式
        try:
            safe_col = validate_identifier(col_name)
        except ValueError:
            continue

        # 检查空值
        null_result = await db.execute(text(
            f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_col} IS NULL"
        ))
        null_count = null_result.scalar() or 0
        if null_count > 0:
            issues.append(QualityIssue(
                column=col_name,
                issue_type=QualityIssueType.NULL_VALUES,
                description=f"字段 {col_name} 存在 {null_count} 个空值",
                affected_rows=null_count,
                severity="high" if null_count > total_rows * 0.1 else "medium",
            ))

        # 检查重复值（字符串/数字类型）
        if data_type in ("varchar", "char", "text", "int", "bigint"):
            dup_result = await db.execute(text(
                f"SELECT {safe_col}, COUNT(*) as cnt FROM {safe_table} "
                f"WHERE {safe_col} IS NOT NULL "
                f"GROUP BY {safe_col} HAVING cnt > 1 LIMIT 5"
            ))
            dups = dup_result.fetchall()
            if dups:
                dup_count = sum(row[1] - 1 for row in dups)
                issues.append(QualityIssue(
                    column=col_name,
                    issue_type=QualityIssueType.DUPLICATES,
                    description=f"字段 {col_name} 存在重复值",
                    affected_rows=dup_count,
                    severity="low",
                    sample_values=[row[0] for row in dups[:3]],
                ))

    # 计算质量得分
    issue_weight = sum(1 for i in issues if i.severity == "high") * 3 + \
                   sum(1 for i in issues if i.severity == "medium") * 2 + \
                   sum(1 for i in issues if i.severity == "low")
    quality_score = max(0, 100 - issue_weight * 5)

    return DataQualityReport(
        table_name=req.table_name,
        total_rows=total_rows,
        analyzed_rows=min(total_rows, req.sample_size),
        issues=issues,
        quality_score=quality_score,
    )


@app.post("/api/cleaning/recommend", response_model=CleaningRecommendation)
async def recommend_rules(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """AI 推荐清洗规则"""
    # 先分析数据质量
    report = await analyze_table(req, db, user)

    if not report.issues:
        return CleaningRecommendation(rules=[], explanation="数据质量良好，无需清洗")

    # 构建提示词
    issues_desc = "\n".join(
        f"- 字段 `{i.column}`: {i.description} (严重度: {i.severity})"
        for i in report.issues
    )
    prompt = f"""你是数据质量专家。根据以下数据质量问题，推荐清洗规则。

表名: {req.table_name}
总行数: {report.total_rows}
质量得分: {report.quality_score}/100

发现的问题:
{issues_desc}

请以 JSON 格式输出清洗规则列表，每条规则包含:
- name: 规则名称
- description: 规则描述
- target_column: 目标字段
- rule_type: 规则类型 (filter/replace/fill/transform/deduplicate)
- config: 配置参数

只输出 JSON 数组，不要其他内容。"""

    llm_response = await _call_llm_service(prompt)

    # 解析 LLM 返回的规则（改进的错误处理）
    rules_data = _parse_llm_json_response(
        llm_response,
        context=f"清洗规则推荐 - 表 {req.table_name}"
    )

    # 如果解析失败，提供默认规则建议
    if not rules_data and report.issues:
        logger.info(f"LLM 返回解析失败，使用默认规则建议")
        # 根据检测到的问题生成默认规则
        for issue in report.issues:
            if issue.issue_type == QualityIssueType.NULL_VALUES:
                rules_data.append({
                    "name": f"填充空值 - {issue.column}",
                    "description": f"填充字段 {issue.column} 的空值",
                    "target_column": issue.column,
                    "rule_type": "fill",
                    "config": {"fill_value": "", "fill_strategy": "empty_string"},
                })
            elif issue.issue_type == QualityIssueType.DUPLICATES:
                rules_data.append({
                    "name": f"去重 - {issue.column}",
                    "description": f"去除字段 {issue.column} 的重复值",
                    "target_column": issue.column,
                    "rule_type": "deduplicate",
                    "config": {},
                })

    rules = []
    for r in rules_data:
        rules.append(CleaningRule(
            rule_id=str(uuid.uuid4())[:8],
            name=r.get("name", "未命名规则"),
            description=r.get("description", ""),
            target_column=r.get("target_column", ""),
            rule_type=r.get("rule_type", "transform"),
            config=r.get("config", {}),
        ))

    return CleaningRecommendation(
        rules=rules,
        explanation=f"基于数据质量分析，发现 {len(report.issues)} 个问题，推荐 {len(rules)} 条清洗规则",
    )


@app.post("/api/cleaning/generate-config", response_model=list[SeaTunnelTransformConfig])
async def generate_seatunnel_config(
    req: GenerateConfigRequest,
    user: TokenPayload = Depends(get_current_user),
):
    """根据清洗规则生成 SeaTunnel Transform 配置"""
    configs = []
    output_table = req.output_table or f"{req.table_name}_cleaned"

    for rule in req.rules:
        if rule.rule_type == "filter":
            configs.append(SeaTunnelTransformConfig(
                plugin_name="Filter",
                source_table_name=req.table_name,
                result_table_name=output_table,
                config={"fields": [rule.target_column], "filter_rule": rule.config},
            ))
        elif rule.rule_type == "replace":
            configs.append(SeaTunnelTransformConfig(
                plugin_name="Replace",
                source_table_name=req.table_name,
                result_table_name=output_table,
                config={"replace_field": rule.target_column, **rule.config},
            ))
        elif rule.rule_type == "fill":
            configs.append(SeaTunnelTransformConfig(
                plugin_name="FieldMapper",
                source_table_name=req.table_name,
                result_table_name=output_table,
                config={"field_mapper": {rule.target_column: rule.config.get("fill_value", "")}},
            ))
        elif rule.rule_type == "deduplicate":
            configs.append(SeaTunnelTransformConfig(
                plugin_name="SQL",
                source_table_name=req.table_name,
                result_table_name=output_table,
                config={"query": f"SELECT DISTINCT * FROM {req.table_name}"},
            ))

    return configs


@app.get("/api/cleaning/rules")
async def list_rule_templates():
    """列出可用的清洗规则模板"""
    return [
        {"type": "filter", "name": "过滤空值", "description": "过滤指定字段的空值行"},
        {"type": "replace", "name": "替换异常值", "description": "将异常值替换为指定值"},
        {"type": "fill", "name": "填充缺失值", "description": "使用均值/中位数/众数填充缺失值"},
        {"type": "transform", "name": "格式转换", "description": "统一字段格式（日期、电话等）"},
        {"type": "deduplicate", "name": "去除重复", "description": "去除重复记录"},
    ]


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-cleaning"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
