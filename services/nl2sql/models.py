"""NL2SQL 服务 - 数据模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class NL2SQLRequest(BaseModel):
    """自然语言查询请求"""
    question: str           # 自然语言问题
    database: Optional[str] = None  # 指定数据库
    max_rows: int = 100     # 最大返回行数


class NL2SQLResponse(BaseModel):
    """自然语言查询响应"""
    success: bool
    question: str
    generated_sql: str
    explanation: str        # SQL 的自然语言解释
    columns: list[str] = []
    rows: list[list[Any]] = []
    row_count: int = 0
    execution_time_ms: float = 0


class SQLExplanationRequest(BaseModel):
    """SQL 解释请求"""
    sql: str
    database: Optional[str] = None


class SQLExplanation(BaseModel):
    """SQL 解释响应"""
    sql: str
    explanation: str        # 中文自然语言解释


class TableInfo(BaseModel):
    """表信息"""
    database: str
    table_name: str
    comment: Optional[str] = None
    columns: list["ColumnInfo"] = []


class ColumnInfo(BaseModel):
    """字段信息"""
    name: str
    data_type: str
    comment: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True


class QueryHistory(BaseModel):
    """查询历史"""
    id: str
    question: str
    generated_sql: str
    success: bool
    created_at: datetime
