from __future__ import annotations

from typing import Any

import httpx
import pandas as pd

from app.connectors.base import BaseConnector


class APIConnector(BaseConnector):
    """Connector for REST API data sources."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "")
        self.headers = config.get("headers", {})
        self.auth = config.get("auth")  # {"type": "bearer", "token": "..."}
        self.timeout = config.get("timeout", 30)

    def _get_headers(self) -> dict[str, str]:
        headers = dict(self.headers)

        if self.auth:
            auth_type = self.auth.get("type", "bearer")
            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.auth.get('token', '')}"
            elif auth_type == "api_key":
                key_name = self.auth.get("key_name", "X-API-Key")
                headers[key_name] = self.auth.get("api_key", "")

        return headers

    async def test_connection(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.base_url,
                    headers=self._get_headers(),
                )
                if response.status_code < 400:
                    return True, f"Connection successful (status: {response.status_code})"
                return False, f"Connection failed with status: {response.status_code}"
        except httpx.RequestError as e:
            return False, str(e)

    async def get_tables(self) -> list[dict[str, Any]]:
        endpoints = self.config.get("endpoints", [])
        return [
            {"table_name": ep.get("name", ep.get("path")), "table_type": "endpoint"}
            for ep in endpoints
        ]

    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        df = await self.read_data(table_name, limit=1)
        return [
            {
                "column_name": col,
                "data_type": str(df[col].dtype),
                "nullable": True,
                "is_primary_key": False,
                "ordinal_position": idx,
            }
            for idx, col in enumerate(df.columns)
        ]

    async def get_row_count(self, table_name: str) -> int:
        return -1

    async def read_data(
        self,
        table_name: str | None = None,
        query: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        endpoints = self.config.get("endpoints", [])
        endpoint = next(
            (ep for ep in endpoints if ep.get("name") == table_name or ep.get("path") == table_name),
            None,
        )

        if not endpoint and table_name:
            url = f"{self.base_url.rstrip('/')}/{table_name.lstrip('/')}"
        elif endpoint:
            url = f"{self.base_url.rstrip('/')}/{endpoint.get('path', '').lstrip('/')}"
        else:
            url = self.base_url

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            method = endpoint.get("method", "GET") if endpoint else "GET"
            params = endpoint.get("params", {}) if endpoint else {}

            if limit:
                params["limit"] = limit

            if method.upper() == "GET":
                response = await client.get(url, headers=self._get_headers(), params=params)
            else:
                response = await client.post(url, headers=self._get_headers(), json=params)

            response.raise_for_status()
            data = response.json()

        data_path = endpoint.get("data_path") if endpoint else None
        if data_path:
            for key in data_path.split("."):
                data = data.get(key, data)

        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            df = pd.DataFrame([data])
        else:
            raise ValueError(f"Unexpected data type: {type(data)}")

        if limit:
            df = df.head(limit)

        return df

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        raise NotImplementedError("API connectors don't support raw queries")
