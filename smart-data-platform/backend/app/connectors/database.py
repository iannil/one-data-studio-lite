from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.connectors.base import BaseConnector


class DatabaseConnector(BaseConnector):
    """Connector for SQL databases (PostgreSQL, MySQL, etc.)."""

    DRIVER_MAP = {
        "postgresql": "postgresql+psycopg2",
        "mysql": "mysql+pymysql",
        "oracle": "oracle+cx_oracle",
        "sqlserver": "mssql+pyodbc",
        "sqlite": "sqlite",
    }

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.engine = None
        self._build_engine()

    def _build_engine(self) -> None:
        db_type = self.config.get("type", "postgresql")
        driver = self.DRIVER_MAP.get(db_type, "postgresql+psycopg2")

        if db_type == "sqlite":
            url = f"sqlite:///{self.config.get('database', ':memory:')}"
        else:
            url = (
                f"{driver}://"
                f"{self.config.get('username', '')}:"
                f"{self.config.get('password', '')}@"
                f"{self.config.get('host', 'localhost')}:"
                f"{self.config.get('port', 5432)}/"
                f"{self.config.get('database', '')}"
            )

        self.engine = create_engine(url, pool_pre_ping=True)

    async def test_connection(self) -> tuple[bool, str]:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Connection successful"
        except SQLAlchemyError as e:
            return False, str(e)

    async def get_tables(self) -> list[dict[str, Any]]:
        try:
            inspector = inspect(self.engine)
            tables = []

            for schema in inspector.get_schema_names():
                if schema in ("information_schema", "pg_catalog"):
                    continue

                for table_name in inspector.get_table_names(schema=schema):
                    tables.append({
                        "schema_name": schema if schema != "public" else None,
                        "table_name": table_name,
                        "table_type": "table",
                    })

                for view_name in inspector.get_view_names(schema=schema):
                    tables.append({
                        "schema_name": schema if schema != "public" else None,
                        "table_name": view_name,
                        "table_type": "view",
                    })

            return tables
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to get tables: {e}") from e

    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        try:
            inspector = inspect(self.engine)

            schema = None
            if "." in table_name:
                schema, table_name = table_name.split(".", 1)

            columns = inspector.get_columns(table_name, schema=schema)
            pk_columns = set(
                inspector.get_pk_constraint(table_name, schema=schema).get("constrained_columns", [])
            )

            return [
                {
                    "column_name": col["name"],
                    "data_type": str(col["type"]),
                    "nullable": col.get("nullable", True),
                    "is_primary_key": col["name"] in pk_columns,
                    "default_value": str(col.get("default")) if col.get("default") else None,
                    "ordinal_position": idx,
                }
                for idx, col in enumerate(columns)
            ]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to get columns: {e}") from e

    async def get_row_count(self, table_name: str) -> int:
        try:
            with self.engine.connect() as conn:
                # Handle schema.table format
                if '.' in table_name:
                    schema, table = table_name.split('.', 1)
                    sql = f'SELECT COUNT(*) FROM "{schema}"."{table}"'
                else:
                    sql = f"SELECT COUNT(*) FROM {table_name}"
                result = conn.execute(text(sql))
                return result.scalar() or 0
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to get row count: {e}") from e

    async def read_data(
        self,
        table_name: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        try:
            if query:
                sql = query
            elif table_name:
                # Handle schema.table format - quote properly for PostgreSQL
                if '.' in table_name:
                    schema, table = table_name.split('.', 1)
                    sql = f'SELECT * FROM "{schema}"."{table}"'
                else:
                    sql = f"SELECT * FROM {table_name}"
                if limit:
                    sql += f" LIMIT {limit}"
            else:
                raise ValueError("Either table_name or query must be provided")

            return pd.read_sql(sql, self.engine)
        except Exception as e:
            raise RuntimeError(f"Failed to read data: {e}") from e

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return []
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to execute query: {e}") from e

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
