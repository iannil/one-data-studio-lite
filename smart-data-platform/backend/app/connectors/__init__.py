from typing import Any, Union

from app.connectors.base import BaseConnector
from app.connectors.database import DatabaseConnector
from app.connectors.file import FileConnector
from app.connectors.api import APIConnector
from app.models.metadata import DataSourceType


def _normalize_type(source_type: Union[DataSourceType, str]) -> DataSourceType:
    """Normalize source type string to DataSourceType enum."""
    if isinstance(source_type, DataSourceType):
        return source_type

    # Handle uppercase/lowercase/mixed case strings
    type_str = str(source_type).lower().strip()
    type_mapping = {
        "postgresql": DataSourceType.POSTGRESQL,
        "mysql": DataSourceType.MYSQL,
        "oracle": DataSourceType.ORACLE,
        "sqlserver": DataSourceType.SQLSERVER,
        "mssql": DataSourceType.SQLSERVER,
        "sqlite": DataSourceType.SQLITE,
        "csv": DataSourceType.CSV,
        "excel": DataSourceType.EXCEL,
        "xlsx": DataSourceType.EXCEL,
        "json": DataSourceType.JSON,
        "api": DataSourceType.API,
    }
    return type_mapping.get(type_str, DataSourceType.POSTGRESQL)


def get_connector(source_type: Union[DataSourceType, str], config: dict[str, Any]) -> BaseConnector:
    """Factory function to create the appropriate connector."""

    # Normalize type to enum
    normalized_type = _normalize_type(source_type)

    database_types = {
        DataSourceType.POSTGRESQL,
        DataSourceType.MYSQL,
        DataSourceType.ORACLE,
        DataSourceType.SQLSERVER,
        DataSourceType.SQLITE,
    }

    file_types = {
        DataSourceType.CSV,
        DataSourceType.EXCEL,
        DataSourceType.JSON,
    }

    if normalized_type in database_types:
        return DatabaseConnector({**config, "type": normalized_type.value})
    elif normalized_type in file_types:
        return FileConnector({**config, "file_type": normalized_type.value})
    elif normalized_type == DataSourceType.API:
        return APIConnector(config)
    else:
        raise ValueError(f"Unsupported data source type: {source_type}")


__all__ = [
    "BaseConnector",
    "DatabaseConnector",
    "FileConnector",
    "APIConnector",
    "get_connector",
]
