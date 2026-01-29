"""数据资产API - 数据模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DatasetQuery(BaseModel):
    """数据集查询请求"""
    sql: Optional[str] = None
    filters: dict[str, Any] = {}
    page: int = 1
    page_size: int = 50
    order_by: Optional[str] = None


class DatasetSchema(BaseModel):
    """数据集 Schema"""
    dataset_id: str
    name: str
    columns: list["ColumnSchema"]
    row_count: Optional[int] = None
    last_updated: Optional[datetime] = None


class ColumnSchema(BaseModel):
    """字段 Schema"""
    name: str
    data_type: str
    description: Optional[str] = None
    is_nullable: bool = True
    is_primary_key: bool = False


class AssetInfo(BaseModel):
    """数据资产信息"""
    asset_id: str
    name: str
    description: Optional[str] = None
    asset_type: str         # table / view / api / file
    owner: Optional[str] = None
    tags: list[str] = []
    quality_score: Optional[float] = None
    lineage_upstream: list[str] = []
    lineage_downstream: list[str] = []


class SearchRequest(BaseModel):
    """资产搜索请求"""
    query: str
    asset_type: Optional[str] = None
    tags: list[str] = []
    page: int = 1
    page_size: int = 20


class SearchResult(BaseModel):
    """搜索结果"""
    total: int
    assets: list[AssetInfo]


class Subscription(BaseModel):
    """资产变更订阅"""
    asset_id: str
    subscriber: str
    notify_url: Optional[str] = None
    events: list[str] = ["schema_change", "data_update"]
