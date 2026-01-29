"""AI清洗服务 - 数据模型"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class QualityIssueType(str, Enum):
    """数据质量问题类型"""
    NULL_VALUES = "null_values"           # 空值
    DUPLICATES = "duplicates"             # 重复值
    TYPE_MISMATCH = "type_mismatch"       # 类型不匹配
    OUTLIER = "outlier"                   # 异常值
    FORMAT_ERROR = "format_error"         # 格式错误
    INCONSISTENCY = "inconsistency"       # 不一致


class AnalyzeRequest(BaseModel):
    """数据质量分析请求"""
    table_name: str
    database: Optional[str] = None
    sample_size: int = 1000


class QualityIssue(BaseModel):
    """数据质量问题"""
    column: str
    issue_type: QualityIssueType
    description: str
    affected_rows: int = 0
    severity: str = "medium"    # low / medium / high
    sample_values: list[Any] = []


class DataQualityReport(BaseModel):
    """数据质量报告"""
    table_name: str
    total_rows: int
    analyzed_rows: int
    issues: list[QualityIssue]
    quality_score: float        # 0-100


class CleaningRule(BaseModel):
    """清洗规则"""
    rule_id: str
    name: str
    description: str
    target_column: str
    rule_type: str              # filter / replace / fill / transform / deduplicate
    config: dict[str, Any]


class CleaningRecommendation(BaseModel):
    """清洗规则推荐"""
    rules: list[CleaningRule]
    explanation: str            # AI 给出的解释


class SeaTunnelTransformConfig(BaseModel):
    """SeaTunnel Transform 配置"""
    plugin_name: str
    source_table_name: str
    result_table_name: str
    config: dict[str, Any]


class GenerateConfigRequest(BaseModel):
    """生成 SeaTunnel 配置请求"""
    table_name: str
    rules: list[CleaningRule]
    output_table: Optional[str] = None
