"""数据资产API - 数据模型"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DatasetQuery(BaseModel):
    """数据集查询请求"""
    sql: str | None = None
    filters: dict[str, Any] = {}
    page: int = 1
    page_size: int = 50
    order_by: str | None = None


class DatasetSchema(BaseModel):
    """数据集 Schema"""
    dataset_id: str
    name: str
    columns: list["ColumnSchema"]
    row_count: int | None = None
    last_updated: datetime | None = None


class ColumnSchema(BaseModel):
    """字段 Schema"""
    name: str
    data_type: str
    description: str | None = None
    is_nullable: bool = True
    is_primary_key: bool = False


class AssetInfo(BaseModel):
    """数据资产信息"""
    asset_id: str
    name: str
    description: str | None = None
    asset_type: str         # table / view / api / file
    owner: str | None = None
    tags: list[str] = []
    quality_score: float | None = None
    lineage_upstream: list[str] = []
    lineage_downstream: list[str] = []


class SearchRequest(BaseModel):
    """资产搜索请求"""
    query: str
    asset_type: str | None = None
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
    notify_url: str | None = None
    events: list[str] = ["schema_change", "data_update"]
