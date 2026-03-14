from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BISyncRequest(BaseModel):
    """Request for syncing a table to Superset."""
    schema_name: str = Field(default="public", description="Database schema")


class BISyncResponse(BaseModel):
    """Response from table sync operation."""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    action: str | None = Field(default=None, description="created or refreshed")
    dataset_id: int | None = None
    table_name: str
    schema_name: str | None = Field(default=None, alias="schema")
    superset_url: str | None = None
    error: str | None = None


class BIDatasetResponse(BaseModel):
    """Response for a single dataset."""
    model_config = ConfigDict(populate_by_name=True)

    dataset_id: int
    table_name: str | None
    schema_name: str | None = Field(default=None, alias="schema")
    superset_url: str | None = None
    changed_on: str | None = None


class BIStatusResponse(BaseModel):
    """Response for Superset connection status."""
    superset_url: str
    health: str
    authenticated: bool | None = None
    auth_error: str | None = None
    database_count: int | None = None


class BISyncStatusResponse(BaseModel):
    """Response for table sync status."""
    model_config = ConfigDict(populate_by_name=True)

    synced: bool
    table_name: str
    schema_name: str | None = Field(default=None, alias="schema")
    dataset_id: int | None = None
    superset_url: str | None = None
    changed_on: str | None = None
    error: str | None = None


class BatchSyncRequest(BaseModel):
    """Request for batch syncing multiple tables to Superset."""
    tables: list[str] = Field(..., description="List of table names to sync")
    schema_name: str = Field(default="public", description="Database schema")


class BatchSyncItemResult(BaseModel):
    """Result for a single table in batch sync."""
    model_config = ConfigDict(populate_by_name=True)

    table_name: str
    success: bool
    action: str | None = None
    dataset_id: int | None = None
    superset_url: str | None = None
    error: str | None = None


class BatchSyncResponse(BaseModel):
    """Response from batch sync operation."""
    total: int
    succeeded: int
    failed: int
    results: list[BatchSyncItemResult]


class AssetSyncResponse(BaseModel):
    """Response from asset sync operation."""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    asset_id: str
    asset_name: str
    table_name: str | None = None
    schema_name: str | None = Field(default=None, alias="schema")
    dataset_id: int | None = None
    superset_url: str | None = None
    error: str | None = None
