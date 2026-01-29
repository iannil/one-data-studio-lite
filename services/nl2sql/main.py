"""NL2SQL 服务 - FastAPI 应用"""

import time
import uuid
from typing import Optional

import httpx
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.exceptions import register_exception_handlers, AppException
from services.common.metrics import setup_metrics
from services.common.middleware import RequestLoggingMiddleware
from services.nl2sql.config import settings
from services.nl2sql.models import (
    NL2SQLRequest,
    NL2SQLResponse,
    SQLExplanationRequest,
    SQLExplanation,
    TableInfo,
    ColumnInfo,
)
from services.nl2sql.prompts import (
    SYSTEM_PROMPT,
    SCHEMA_TEMPLATE,
    QUERY_TEMPLATE,
    EXPLAIN_TEMPLATE,
    FEW_SHOT_EXAMPLES,
)

app = FastAPI(
    title=settings.APP_NAME,
    description="自然语言转 SQL 查询服务",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware, service_name="nl2sql")
register_exception_handlers(app)
setup_metrics(app)


async def _call_llm(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """调用 LLM 生成文本"""
    url = f"{settings.LLM_BASE_URL}/api/generate"
    payload = {
        "model": settings.LLM_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": settings.LLM_TEMPERATURE,
            "num_predict": settings.LLM_MAX_TOKENS,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except Exception as e:
        raise AppException(f"LLM 调用失败: {e}", code=503)


async def _get_schema_info(db: AsyncSession, database: Optional[str] = None) -> str:
    """获取数据库表结构信息"""
    schema_parts = []
    # 查询所有表
    result = await db.execute(text(
        "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
    ))
    tables = result.fetchall()

    for table_name, table_comment in tables:
        # 查询表的列信息
        cols_result = await db.execute(text(
            "SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ), {"table": table_name})
        columns = cols_result.fetchall()

        col_desc = ", ".join(
            f"`{c[0]}` {c[1]}" + (f" -- {c[2]}" if c[2] else "")
            for c in columns
        )
        comment = f" -- {table_comment}" if table_comment else ""
        schema_parts.append(f"表 `{table_name}`{comment}: ({col_desc})")

    return "\n".join(schema_parts) if schema_parts else "暂无可用表结构信息"


@app.post("/api/nl2sql/query", response_model=NL2SQLResponse)
async def nl2sql_query(
    req: NL2SQLRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """自然语言查询 - 转换为 SQL 并执行"""
    start = time.time()

    # 获取表结构
    schema_info = await _get_schema_info(db, req.database)

    # 构建提示词
    prompt = SCHEMA_TEMPLATE.format(schema_info=schema_info)
    # 添加 few-shot 示例
    for ex in FEW_SHOT_EXAMPLES:
        prompt += f"\n用户问题: {ex['question']}\nSQL: {ex['sql']}\n"
    prompt += "\n" + QUERY_TEMPLATE.format(question=req.question)

    # 调用 LLM 生成 SQL
    generated_sql = await _call_llm(prompt)
    # 清理 SQL（移除可能的 markdown 标记）
    generated_sql = generated_sql.strip().strip("`").strip()
    if generated_sql.startswith("sql"):
        generated_sql = generated_sql[3:].strip()

    # 安全检查：只允许 SELECT
    sql_upper = generated_sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        raise AppException("安全限制：仅允许 SELECT 查询", code=400)

    # 执行 SQL
    try:
        result = await db.execute(text(generated_sql))
        columns = list(result.keys()) if result.returns_rows else []
        rows = [list(row) for row in result.fetchmany(req.max_rows)] if result.returns_rows else []
    except Exception as e:
        return NL2SQLResponse(
            success=False,
            question=req.question,
            generated_sql=generated_sql,
            explanation=f"SQL 执行失败: {e}",
            execution_time_ms=(time.time() - start) * 1000,
        )

    # 生成解释
    explain_prompt = EXPLAIN_TEMPLATE.format(sql=generated_sql, schema_info=schema_info)
    explanation = await _call_llm(explain_prompt)

    return NL2SQLResponse(
        success=True,
        question=req.question,
        generated_sql=generated_sql,
        explanation=explanation,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=(time.time() - start) * 1000,
    )


@app.post("/api/nl2sql/explain", response_model=SQLExplanation)
async def explain_sql(
    req: SQLExplanationRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """解释 SQL 查询"""
    schema_info = await _get_schema_info(db, req.database)
    prompt = EXPLAIN_TEMPLATE.format(sql=req.sql, schema_info=schema_info)
    explanation = await _call_llm(prompt)
    return SQLExplanation(sql=req.sql, explanation=explanation)


@app.get("/api/nl2sql/tables", response_model=list[TableInfo])
async def list_tables(
    db: AsyncSession = Depends(get_db),
    user: TokenPayload = Depends(get_current_user),
):
    """列出可用表和字段"""
    result = await db.execute(text(
        "SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
    ))
    tables = []
    for table_name, table_comment in result.fetchall():
        cols_result = await db.execute(text(
            "SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT, COLUMN_KEY, IS_NULLABLE "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table"
        ), {"table": table_name})
        columns = [
            ColumnInfo(
                name=c[0], data_type=c[1], comment=c[2] or None,
                is_primary_key=(c[3] == "PRI"), is_nullable=(c[4] == "YES"),
            )
            for c in cols_result.fetchall()
        ]
        tables.append(TableInfo(
            database="default",
            table_name=table_name,
            comment=table_comment or None,
            columns=columns,
        ))
    return tables


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nl2sql"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
