"""敏感数据检测 - 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class SensitivityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ScanRequest(BaseModel):
    """扫描请求"""
    table_name: str
    database: str | None = None
    sample_size: int = 100


class SensitiveField(BaseModel):
    """敏感字段"""
    column_name: str
    sensitivity_level: SensitivityLevel
    detected_types: list[str]       # phone, id_card, email 等
    detection_method: str           # regex / llm / field_name
    sample_count: int = 0           # 匹配的样本数
    confidence: float = 0.0         # 置信度 0-1


class ScanReport(BaseModel):
    """扫描报告"""
    id: str
    table_name: str
    scan_time: datetime
    total_columns: int
    sensitive_columns: int
    fields: list[SensitiveField]
    risk_level: SensitivityLevel


class DetectionRule(BaseModel):
    """自定义检测规则"""
    id: str | None = None
    name: str
    pattern: str                    # 正则表达式
    sensitivity_level: SensitivityLevel
    description: str = ""
    enabled: bool = True


class ClassifyRequest(BaseModel):
    """数据分类请求"""
    data_samples: list[dict[str, Any]]
    context: str | None = None   # 额外上下文信息
