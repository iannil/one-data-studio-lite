from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseConnector(ABC):
    """Base class for all data source connectors."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    async def test_connection(self) -> tuple[bool, str]:
        """Test the connection to the data source."""
        pass

    @abstractmethod
    async def get_tables(self) -> list[dict[str, Any]]:
        """Get list of tables/collections in the data source."""
        pass

    @abstractmethod
    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        """Get column metadata for a specific table."""
        pass

    @abstractmethod
    async def get_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        pass

    @abstractmethod
    async def read_data(
        self,
        table_name: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Read data from the source."""
        pass

    @abstractmethod
    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a raw query."""
        pass
