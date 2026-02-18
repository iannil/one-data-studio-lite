from typing import Any

from app.connectors.base import BaseConnector
from app.connectors.database import DatabaseConnector
from app.connectors.file import FileConnector
from app.connectors.api import APIConnector
from app.models.metadata import DataSourceType


def get_connector(source_type: DataSourceType, config: dict[str, Any]) -> BaseConnector:
    """Factory function to create the appropriate connector."""

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

    if source_type in database_types:
        return DatabaseConnector({**config, "type": source_type.value})
    elif source_type in file_types:
        return FileConnector({**config, "file_type": source_type.value})
    elif source_type == DataSourceType.API:
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
