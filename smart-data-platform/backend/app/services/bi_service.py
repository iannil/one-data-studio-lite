from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


class SupersetAPIError(Exception):
    """Exception raised for Superset API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SupersetClient:
    """Client for interacting with Superset REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.base_url = (base_url or settings.SUPERSET_URL).rstrip("/")
        self.username = username or settings.SUPERSET_USERNAME
        self.password = password or settings.SUPERSET_PASSWORD
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if self._access_token and self._token_expires_at:
            if datetime.now(timezone.utc) < self._token_expires_at:
                return

        await self.login()

    async def login(self) -> str:
        """Authenticate with Superset and obtain access token.

        Returns:
            Access token string.

        Raises:
            SupersetAPIError: If authentication fails.
        """
        url = f"{self.base_url}/api/v1/security/login"
        payload = {
            "username": self.username,
            "password": self.password,
            "provider": "db",
            "refresh": True,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()

                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")

                # Token typically expires in 1 hour
                from datetime import timedelta
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=55)

                if not self._access_token:
                    raise SupersetAPIError("No access token in response")

                logger.info("Successfully authenticated with Superset")
                return self._access_token

            except httpx.HTTPStatusError as e:
                raise SupersetAPIError(
                    f"Authentication failed: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise SupersetAPIError(f"Connection failed: {e}") from e

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to Superset API."""
        await self._ensure_authenticated()

        url = f"{self.base_url}/api/v1{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                    timeout=60,
                )
                response.raise_for_status()
                return response.json() if response.text else {}

            except httpx.HTTPStatusError as e:
                raise SupersetAPIError(
                    f"API request failed: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise SupersetAPIError(f"Connection failed: {e}") from e

    async def get_csrf_token(self) -> str:
        """Get CSRF token for write operations."""
        await self._ensure_authenticated()

        url = f"{self.base_url}/api/v1/security/csrf_token/"
        headers = {"Authorization": f"Bearer {self._access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get("result", "")

    async def create_database(
        self,
        name: str,
        sqlalchemy_uri: str,
        extra: dict | None = None,
    ) -> int:
        """Create a database connection in Superset.

        Args:
            name: Display name for the database.
            sqlalchemy_uri: SQLAlchemy connection URI.
            extra: Optional extra configuration.

        Returns:
            Database ID.
        """
        payload = {
            "database_name": name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_ctas": True,
            "allow_cvas": True,
            "allow_dml": False,
            "extra": extra or {},
        }

        result = await self._request("POST", "/database/", json=payload)
        database_id = result.get("id")

        logger.info(f"Created database '{name}' with ID {database_id}")
        return database_id

    async def get_database(self, database_id: int) -> dict[str, Any]:
        """Get database connection details."""
        return await self._request("GET", f"/database/{database_id}")

    async def list_databases(self) -> list[dict[str, Any]]:
        """List all database connections."""
        result = await self._request("GET", "/database/")
        return result.get("result", [])

    async def create_dataset(
        self,
        database_id: int,
        table_name: str,
        schema: str | None = None,
    ) -> int:
        """Create a dataset in Superset.

        Args:
            database_id: ID of the database connection.
            table_name: Name of the table.
            schema: Database schema (default: public).

        Returns:
            Dataset ID.
        """
        payload = {
            "database": database_id,
            "table_name": table_name,
            "schema": schema or "public",
        }

        result = await self._request("POST", "/dataset/", json=payload)
        dataset_id = result.get("id")

        logger.info(f"Created dataset '{table_name}' with ID {dataset_id}")
        return dataset_id

    async def refresh_dataset(self, dataset_id: int) -> bool:
        """Refresh a dataset's columns from the database.

        Args:
            dataset_id: ID of the dataset.

        Returns:
            True if refresh succeeded.
        """
        try:
            await self._request("PUT", f"/dataset/{dataset_id}/refresh")
            logger.info(f"Refreshed dataset {dataset_id}")
            return True
        except SupersetAPIError as e:
            logger.error(f"Failed to refresh dataset {dataset_id}: {e}")
            return False

    async def get_dataset(self, dataset_id: int) -> dict[str, Any]:
        """Get dataset details."""
        return await self._request("GET", f"/dataset/{dataset_id}")

    async def list_datasets(
        self,
        database_id: int | None = None,
        page: int = 0,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """List datasets.

        Args:
            database_id: Optional filter by database.
            page: Page number (0-indexed).
            page_size: Number of results per page.

        Returns:
            List of datasets.
        """
        params = {"page": page, "page_size": page_size}

        if database_id:
            params["filters"] = f"[{{\"col\":\"database\",\"opr\":\"rel_o_m\",\"value\":{database_id}}}]"

        result = await self._request("GET", "/dataset/", params=params)
        return result.get("result", [])

    async def delete_dataset(self, dataset_id: int) -> bool:
        """Delete a dataset."""
        try:
            await self._request("DELETE", f"/dataset/{dataset_id}")
            logger.info(f"Deleted dataset {dataset_id}")
            return True
        except SupersetAPIError:
            return False

    async def check_health(self) -> dict[str, Any]:
        """Check Superset health status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=10,
                )
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response": response.text,
                }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}


class BIService:
    """Service for managing BI integrations and data synchronization."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.superset = SupersetClient()
        self._database_id: int | None = None

    async def get_or_create_database_connection(self) -> int:
        """Get or create the Superset database connection for this platform."""
        if self._database_id:
            return self._database_id

        # Check existing databases
        databases = await self.superset.list_databases()
        for db_info in databases:
            if db_info.get("database_name") == "SmartDataPlatform":
                self._database_id = db_info.get("id")
                return self._database_id

        # Create new database connection
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        self._database_id = await self.superset.create_database(
            name="SmartDataPlatform",
            sqlalchemy_uri=sync_url,
            extra={"allows_virtual_table_explore": True},
        )

        return self._database_id

    async def sync_table_to_superset(
        self,
        table_name: str,
        schema: str = "public",
    ) -> dict[str, Any]:
        """Sync a table to Superset as a dataset.

        Args:
            table_name: Name of the table to sync.
            schema: Database schema.

        Returns:
            Sync result with dataset details.
        """
        try:
            database_id = await self.get_or_create_database_connection()

            # Check if dataset already exists
            datasets = await self.superset.list_datasets(database_id=database_id)
            existing_dataset = None

            for ds in datasets:
                if ds.get("table_name") == table_name and ds.get("schema") == schema:
                    existing_dataset = ds
                    break

            if existing_dataset:
                # Refresh existing dataset
                dataset_id = existing_dataset["id"]
                await self.superset.refresh_dataset(dataset_id)
                action = "refreshed"
            else:
                # Create new dataset
                dataset_id = await self.superset.create_dataset(
                    database_id=database_id,
                    table_name=table_name,
                    schema=schema,
                )
                action = "created"

            # Get full dataset details
            dataset = await self.superset.get_dataset(dataset_id)

            return {
                "success": True,
                "action": action,
                "dataset_id": dataset_id,
                "table_name": table_name,
                "schema": schema,
                "superset_url": f"{self.superset.base_url}/superset/explore/table/{dataset_id}/",
                "columns": dataset.get("result", {}).get("columns", []),
            }

        except SupersetAPIError as e:
            logger.error(f"Failed to sync table {table_name}: {e}")
            return {
                "success": False,
                "error": e.message,
                "table_name": table_name,
            }

    async def get_sync_status(self, table_name: str, schema: str = "public") -> dict[str, Any]:
        """Get synchronization status for a table.

        Args:
            table_name: Name of the table.
            schema: Database schema.

        Returns:
            Sync status information.
        """
        try:
            database_id = await self.get_or_create_database_connection()
            datasets = await self.superset.list_datasets(database_id=database_id)

            for ds in datasets:
                if ds.get("table_name") == table_name and ds.get("schema") == schema:
                    return {
                        "synced": True,
                        "dataset_id": ds["id"],
                        "table_name": table_name,
                        "schema": schema,
                        "superset_url": f"{self.superset.base_url}/superset/explore/table/{ds['id']}/",
                        "changed_on": ds.get("changed_on"),
                    }

            return {
                "synced": False,
                "table_name": table_name,
                "schema": schema,
            }

        except SupersetAPIError as e:
            return {
                "synced": False,
                "error": e.message,
                "table_name": table_name,
            }

    async def list_synced_datasets(self) -> list[dict[str, Any]]:
        """List all datasets synced from this platform.

        Returns:
            List of synced datasets.
        """
        try:
            database_id = await self.get_or_create_database_connection()
            datasets = await self.superset.list_datasets(database_id=database_id)

            return [
                {
                    "dataset_id": ds["id"],
                    "table_name": ds.get("table_name"),
                    "schema": ds.get("schema"),
                    "superset_url": f"{self.superset.base_url}/superset/explore/table/{ds['id']}/",
                    "changed_on": ds.get("changed_on"),
                }
                for ds in datasets
            ]

        except SupersetAPIError as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    async def get_superset_status(self) -> dict[str, Any]:
        """Get Superset connection status.

        Returns:
            Status information including health and authentication state.
        """
        health = await self.superset.check_health()

        result = {
            "superset_url": self.superset.base_url,
            "health": health.get("status"),
        }

        if health.get("status") == "healthy":
            try:
                await self.superset.login()
                result["authenticated"] = True
                databases = await self.superset.list_databases()
                result["database_count"] = len(databases)
            except SupersetAPIError as e:
                result["authenticated"] = False
                result["auth_error"] = e.message

        return result

    async def delete_dataset(self, table_name: str, schema: str = "public") -> bool:
        """Delete a dataset from Superset.

        Args:
            table_name: Name of the table.
            schema: Database schema.

        Returns:
            True if deletion succeeded.
        """
        try:
            database_id = await self.get_or_create_database_connection()
            datasets = await self.superset.list_datasets(database_id=database_id)

            for ds in datasets:
                if ds.get("table_name") == table_name and ds.get("schema") == schema:
                    return await self.superset.delete_dataset(ds["id"])

            return False

        except SupersetAPIError:
            return False

    async def batch_sync_tables(
        self,
        tables: list[str],
        schema: str = "public",
    ) -> dict[str, Any]:
        """Batch sync multiple tables to Superset.

        Args:
            tables: List of table names to sync.
            schema: Database schema.

        Returns:
            Batch sync results with individual table results.
        """
        results = []
        succeeded = 0
        failed = 0

        for table_name in tables:
            try:
                result = await self.sync_table_to_superset(
                    table_name=table_name,
                    schema=schema,
                )
                results.append({
                    "table_name": table_name,
                    "success": result.get("success", False),
                    "action": result.get("action"),
                    "dataset_id": result.get("dataset_id"),
                    "superset_url": result.get("superset_url"),
                    "error": result.get("error"),
                })
                if result.get("success"):
                    succeeded += 1
                else:
                    failed += 1
            except Exception as e:
                results.append({
                    "table_name": table_name,
                    "success": False,
                    "error": str(e),
                })
                failed += 1

        return {
            "total": len(tables),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    async def sync_asset_to_superset(
        self,
        asset_id: str,
    ) -> dict[str, Any]:
        """Sync a DataAsset to Superset.

        Args:
            asset_id: The UUID of the DataAsset.

        Returns:
            Sync result with asset and dataset details.
        """
        import uuid as uuid_module
        from sqlalchemy import select
        from app.models import DataAsset

        asset_result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == uuid_module.UUID(asset_id))
        )
        asset = asset_result.scalar_one_or_none()

        if not asset:
            return {
                "success": False,
                "asset_id": asset_id,
                "asset_name": "",
                "error": f"Asset not found: {asset_id}",
            }

        if not asset.source_table:
            return {
                "success": False,
                "asset_id": asset_id,
                "asset_name": asset.name,
                "error": "Asset has no associated source table",
            }

        schema = asset.source_schema or "public"

        try:
            result = await self.sync_table_to_superset(
                table_name=asset.source_table,
                schema=schema,
            )

            return {
                "success": result.get("success", False),
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "table_name": asset.source_table,
                "schema": schema,
                "dataset_id": result.get("dataset_id"),
                "superset_url": result.get("superset_url"),
                "error": result.get("error"),
            }

        except SupersetAPIError as e:
            return {
                "success": False,
                "asset_id": str(asset.id),
                "asset_name": asset.name,
                "table_name": asset.source_table,
                "error": e.message,
            }
