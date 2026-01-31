"""Repository 层

提供数据访问层的统一接口，封装 ORM 操作。
"""

from services.common.repositories.base import BaseRepository
from services.common.repositories.audit_repository import AuditRepository
from services.common.repositories.detection_repository import (
    DetectionRuleRepository,
    ScanReportRepository,
)
from services.common.repositories.mapping_repository import ETLMappingRepository
from services.common.repositories.mask_repository import MaskRuleRepository

__all__ = [
    "BaseRepository",
    "AuditRepository",
    "DetectionRuleRepository",
    "ScanReportRepository",
    "ETLMappingRepository",
    "MaskRuleRepository",
]
