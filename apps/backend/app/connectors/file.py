from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.connectors.base import BaseConnector


class FileConnector(BaseConnector):
    """Connector for file-based data sources (CSV, Excel, JSON)."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.file_path = Path(config.get("file_path", ""))
        self.file_type = config.get("file_type", "").lower()

        if not self.file_type and self.file_path.suffix:
            self.file_type = self.file_path.suffix[1:].lower()

    async def test_connection(self) -> tuple[bool, str]:
        if not self.file_path.exists():
            return False, f"File not found: {self.file_path}"

        if not self.file_path.is_file():
            return False, f"Path is not a file: {self.file_path}"

        return True, "File accessible"

    async def get_tables(self) -> list[dict[str, Any]]:
        if self.file_type in ("xlsx", "xls"):
            df = pd.ExcelFile(self.file_path)
            return [
                {"table_name": sheet, "table_type": "sheet"}
                for sheet in df.sheet_names
            ]

        return [{"table_name": self.file_path.stem, "table_type": "file"}]

    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        df = await self._read_sample(table_name, 1)

        return [
            {
                "column_name": col,
                "data_type": str(df[col].dtype),
                "nullable": df[col].isnull().any(),
                "is_primary_key": False,
                "ordinal_position": idx,
            }
            for idx, col in enumerate(df.columns)
        ]

    async def get_row_count(self, table_name: str) -> int:
        df = await self.read_data(table_name)
        return len(df)

    async def _read_sample(self, table_name: str | None, nrows: int) -> pd.DataFrame:
        if self.file_type == "csv":
            return pd.read_csv(
                self.file_path,
                nrows=nrows,
                encoding=self.config.get("encoding", "utf-8"),
                delimiter=self.config.get("delimiter", ","),
            )
        elif self.file_type in ("xlsx", "xls"):
            return pd.read_excel(
                self.file_path,
                sheet_name=table_name,
                nrows=nrows,
            )
        elif self.file_type == "json":
            df = pd.read_json(
                self.file_path,
                orient=self.config.get("orient", "records"),
            )
            return df.head(nrows)
        elif self.file_type == "parquet":
            return pd.read_parquet(self.file_path).head(nrows)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")

    async def read_data(
        self,
        table_name: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        if self.file_type == "csv":
            df = pd.read_csv(
                self.file_path,
                encoding=self.config.get("encoding", "utf-8"),
                delimiter=self.config.get("delimiter", ","),
                nrows=limit,
            )
        elif self.file_type in ("xlsx", "xls"):
            df = pd.read_excel(
                self.file_path,
                sheet_name=table_name,
                nrows=limit,
            )
        elif self.file_type == "json":
            df = pd.read_json(
                self.file_path,
                orient=self.config.get("orient", "records"),
            )
            if limit:
                df = df.head(limit)
        elif self.file_type == "parquet":
            df = pd.read_parquet(self.file_path)
            if limit:
                df = df.head(limit)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")

        return df

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError("File connectors don't support raw queries")
