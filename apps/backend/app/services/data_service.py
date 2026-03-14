"""Data service for standardized asset data access."""
from __future__ import annotations

import io
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.models import AssetAccess, AssetApiConfig, DataAsset, DataSource


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class DataService:
    """Service for standardized data asset access with export capabilities."""

    SENSITIVE_PATTERNS = {
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{4}[-.]?\d{4}\b"),
        "id_card": re.compile(r"\b\d{6}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b"),
        "bank_card": re.compile(r"\b\d{16,19}\b"),
        "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    }

    SENSITIVE_COLUMN_KEYWORDS = [
        "email", "phone", "mobile", "tel", "password", "secret", "token",
        "id_card", "idcard", "ssn", "credit_card", "bank_card", "cvv",
        "address", "ip", "ip_address", "salary", "income",
    ]

    DEFAULT_RATE_LIMITS = {
        "query": {"requests": 100, "window_seconds": 60},
        "export": {"requests": 10, "window_seconds": 300},
    }

    _rate_limit_cache: dict[str, list[datetime]] = defaultdict(list)

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_rate_limit(
        self,
        user_id: uuid.UUID,
        operation: str,
        custom_limits: dict[str, Any] | None = None,
    ) -> bool:
        """Check if user has exceeded rate limit for an operation.

        Args:
            user_id: User ID making the request
            operation: Type of operation (query, export)
            custom_limits: Optional custom rate limits

        Returns:
            True if within limits, raises RateLimitExceeded if exceeded
        """
        limits = custom_limits or self.DEFAULT_RATE_LIMITS.get(operation, {})
        if not limits:
            return True

        max_requests = limits.get("requests", 100)
        window_seconds = limits.get("window_seconds", 60)

        cache_key = f"{user_id}:{operation}"
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=window_seconds)

        self._rate_limit_cache[cache_key] = [
            t for t in self._rate_limit_cache[cache_key] if t > cutoff
        ]

        if len(self._rate_limit_cache[cache_key]) >= max_requests:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {operation}: "
                f"{max_requests} requests per {window_seconds} seconds"
            )

        self._rate_limit_cache[cache_key].append(now)
        return True

    def detect_sensitive_columns(
        self,
        df: pd.DataFrame,
        sample_size: int = 100,
    ) -> list[str]:
        """Detect columns that may contain sensitive data.

        Args:
            df: DataFrame to analyze
            sample_size: Number of rows to sample for pattern detection

        Returns:
            List of column names that may contain sensitive data
        """
        sensitive_columns = []

        for col in df.columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in self.SENSITIVE_COLUMN_KEYWORDS):
                sensitive_columns.append(col)
                continue

            if df[col].dtype == "object":
                sample = df[col].dropna().head(sample_size)
                for value in sample:
                    str_value = str(value)
                    for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
                        if pattern.search(str_value):
                            sensitive_columns.append(col)
                            break
                    if col in sensitive_columns:
                        break

        return list(set(sensitive_columns))

    def apply_auto_desensitization(
        self,
        df: pd.DataFrame,
        sensitive_columns: list[str] | None = None,
        desensitization_rules: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        """Apply automatic desensitization to sensitive columns.

        Args:
            df: DataFrame to desensitize
            sensitive_columns: List of columns to mask (auto-detected if None)
            desensitization_rules: Optional custom rules per column

        Returns:
            DataFrame with sensitive data masked
        """
        if sensitive_columns is None:
            sensitive_columns = self.detect_sensitive_columns(df)

        if not sensitive_columns:
            return df

        result = df.copy()
        rules = desensitization_rules or {}

        for col in sensitive_columns:
            if col not in result.columns:
                continue

            rule = rules.get(col, "partial")
            col_lower = col.lower()

            if "email" in col_lower:
                result[col] = result[col].apply(self._mask_email)
            elif any(kw in col_lower for kw in ["phone", "mobile", "tel"]):
                result[col] = result[col].apply(self._mask_phone)
            elif any(kw in col_lower for kw in ["id_card", "idcard", "ssn"]):
                result[col] = result[col].apply(self._mask_id_card)
            elif any(kw in col_lower for kw in ["credit_card", "bank_card"]):
                result[col] = result[col].apply(self._mask_bank_card)
            elif rule == "hash":
                import hashlib
                result[col] = result[col].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16]
                    if pd.notna(x) else x
                )
            elif rule == "replace":
                result[col] = "[MASKED]"
            else:
                result[col] = result[col].apply(self._partial_mask)

        return result

    def _mask_email(self, value: Any) -> str:
        """Mask email address."""
        if pd.isna(value):
            return value
        email = str(value)
        if "@" not in email:
            return self._partial_mask(email)
        parts = email.split("@")
        local = parts[0]
        domain = parts[1] if len(parts) > 1 else ""
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"

    def _mask_phone(self, value: Any) -> str:
        """Mask phone number."""
        if pd.isna(value):
            return value
        phone = str(value)
        digits = re.sub(r"\D", "", phone)
        if len(digits) <= 4:
            return "*" * len(phone)
        return digits[:3] + "*" * (len(digits) - 7) + digits[-4:]

    def _mask_id_card(self, value: Any) -> str:
        """Mask ID card number."""
        if pd.isna(value):
            return value
        id_card = str(value)
        if len(id_card) <= 6:
            return "*" * len(id_card)
        return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]

    def _mask_bank_card(self, value: Any) -> str:
        """Mask bank card number."""
        if pd.isna(value):
            return value
        card = str(value)
        digits = re.sub(r"\D", "", card)
        if len(digits) <= 8:
            return "*" * len(card)
        return digits[:4] + "*" * (len(digits) - 8) + digits[-4:]

    def _partial_mask(self, value: Any) -> str:
        """Apply partial masking to a value."""
        if pd.isna(value):
            return value
        s = str(value)
        if len(s) <= 4:
            return "*" * len(s)
        return s[:2] + "*" * (len(s) - 4) + s[-2:]

    async def _get_api_config(
        self, asset_id: uuid.UUID
    ) -> AssetApiConfig | None:
        """Get API configuration for an asset."""
        result = await self.db.execute(
            select(AssetApiConfig).where(AssetApiConfig.asset_id == asset_id)
        )
        return result.scalar_one_or_none()

    def _apply_api_config_to_columns(
        self,
        df: pd.DataFrame,
        api_config: AssetApiConfig,
    ) -> pd.DataFrame:
        """Apply column exposure/hiding rules from API config."""
        result = df.copy()

        if api_config.exposed_columns:
            valid_columns = [c for c in api_config.exposed_columns if c in result.columns]
            if valid_columns:
                result = result[valid_columns]

        if api_config.hidden_columns:
            columns_to_keep = [c for c in result.columns if c not in api_config.hidden_columns]
            result = result[columns_to_keep]

        return result

    async def query_asset_data(
        self,
        asset_id: uuid.UUID,
        user_id: uuid.UUID,
        query_params: dict[str, Any] | None = None,
        limit: int = 1000,
        offset: int = 0,
        enable_rate_limit: bool = True,
        enable_desensitization: bool = True,
    ) -> dict[str, Any]:
        """Query data from a data asset.

        Args:
            asset_id: Asset ID to query
            user_id: User making the query
            query_params: Optional query parameters (filters, sorting)
            limit: Maximum rows to return (default 1000)
            offset: Number of rows to skip (default 0)
            enable_rate_limit: Whether to enforce rate limiting
            enable_desensitization: Whether to auto-mask sensitive data

        Returns:
            Query result with data and metadata
        """
        api_config = await self._get_api_config(asset_id)

        if api_config:
            if not api_config.is_enabled:
                raise ValueError("API access is disabled for this asset")

            if not api_config.allow_query:
                raise ValueError("Query operation is not allowed for this asset")

            limit = min(limit, api_config.max_limit)
            if limit > api_config.max_limit:
                limit = api_config.max_limit

            if enable_rate_limit:
                custom_limits = {
                    "requests": api_config.rate_limit_requests,
                    "window_seconds": api_config.rate_limit_window_seconds,
                }
                await self.check_rate_limit(user_id, "query", custom_limits)

            enable_desensitization = api_config.enable_desensitization
        elif enable_rate_limit:
            await self.check_rate_limit(user_id, "query")

        asset = await self._get_asset(asset_id)

        if not asset.source_table:
            raise ValueError("Asset does not have a source table")

        source = await self._get_data_source(asset)
        connector = get_connector(source.type, source.connection_config)

        df = await connector.read_data(
            table_name=asset.source_table,
            schema=asset.source_schema,
            limit=limit + offset,
        )

        if offset > 0:
            df = df.iloc[offset:]

        df = df.head(limit)

        if api_config:
            df = self._apply_api_config_to_columns(df, api_config)

        if query_params:
            df = self._apply_query_params(df, query_params)

        sensitive_columns = []
        if enable_desensitization:
            desensitization_rules = None
            if api_config and api_config.desensitization_rules:
                desensitization_rules = api_config.desensitization_rules
            sensitive_columns = self.detect_sensitive_columns(df)
            if sensitive_columns:
                df = self.apply_auto_desensitization(
                    df, sensitive_columns, desensitization_rules
                )

        await self._record_access(
            asset_id=asset_id,
            user_id=user_id,
            access_type="query",
            details={
                "limit": limit,
                "offset": offset,
                "row_count": len(df),
                "masked_columns": sensitive_columns,
            },
        )

        asset.usage_count = (asset.usage_count or 0) + 1
        asset.last_accessed_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "asset_id": str(asset_id),
            "asset_name": asset.name,
            "data": df.to_dict(orient="records"),
            "row_count": len(df),
            "columns": list(df.columns),
            "total_rows": await self._get_total_rows(asset),
            "limit": limit,
            "offset": offset,
            "masked_columns": sensitive_columns,
        }

    async def export_asset_data(
        self,
        asset_id: uuid.UUID,
        user_id: uuid.UUID,
        format: str = "csv",
        query_params: dict[str, Any] | None = None,
        limit: int | None = None,
        enable_rate_limit: bool = True,
        enable_desensitization: bool = True,
    ) -> dict[str, Any]:
        """Export data from a data asset in specified format.

        Args:
            asset_id: Asset ID to export
            user_id: User requesting export
            format: Export format (csv, json, parquet, excel)
            query_params: Optional query parameters
            limit: Maximum rows to export (None for all)
            enable_rate_limit: Whether to enforce rate limiting
            enable_desensitization: Whether to auto-mask sensitive data

        Returns:
            Export result with file content or path
        """
        api_config = await self._get_api_config(asset_id)

        if api_config:
            if not api_config.is_enabled:
                raise ValueError("API access is disabled for this asset")

            if not api_config.allow_export:
                raise ValueError("Export operation is not allowed for this asset")

            allowed_formats = api_config.allowed_export_formats or ["csv", "json"]
            if format not in allowed_formats:
                raise ValueError(
                    f"Format '{format}' is not allowed. Allowed formats: {allowed_formats}"
                )

            if limit is not None:
                limit = min(limit, api_config.max_limit)
            else:
                limit = api_config.max_limit

            if enable_rate_limit:
                custom_limits = {
                    "requests": api_config.rate_limit_requests,
                    "window_seconds": api_config.rate_limit_window_seconds,
                }
                await self.check_rate_limit(user_id, "export", custom_limits)

            enable_desensitization = api_config.enable_desensitization
        elif enable_rate_limit:
            await self.check_rate_limit(user_id, "export")

        asset = await self._get_asset(asset_id)

        if not asset.source_table:
            raise ValueError("Asset does not have a source table")

        source = await self._get_data_source(asset)
        connector = get_connector(source.type, source.connection_config)

        df = await connector.read_data(
            table_name=asset.source_table,
            schema=asset.source_schema,
            limit=limit,
        )

        if api_config:
            df = self._apply_api_config_to_columns(df, api_config)

        if query_params:
            df = self._apply_query_params(df, query_params)

        sensitive_columns = []
        if enable_desensitization:
            desensitization_rules = None
            if api_config and api_config.desensitization_rules:
                desensitization_rules = api_config.desensitization_rules
            sensitive_columns = self.detect_sensitive_columns(df)
            if sensitive_columns:
                df = self.apply_auto_desensitization(
                    df, sensitive_columns, desensitization_rules
                )

        content, content_type, filename = self._export_dataframe(
            df, format, asset.name
        )

        await self._record_access(
            asset_id=asset_id,
            user_id=user_id,
            access_type="export",
            details={
                "format": format,
                "row_count": len(df),
                "file_size": len(content) if isinstance(content, bytes) else len(content.encode()),
                "masked_columns": sensitive_columns,
            },
        )

        asset.usage_count = (asset.usage_count or 0) + 1
        asset.last_accessed_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "asset_id": str(asset_id),
            "asset_name": asset.name,
            "format": format,
            "row_count": len(df),
            "content": content,
            "content_type": content_type,
            "filename": filename,
            "masked_columns": sensitive_columns,
        }

    async def get_access_statistics(
        self,
        asset_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get access statistics for assets or users.

        Args:
            asset_id: Optional filter by asset
            user_id: Optional filter by user
            days: Number of days to look back

        Returns:
            Access statistics summary
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = select(AssetAccess).where(AssetAccess.accessed_at >= cutoff_date)

        if asset_id:
            query = query.where(AssetAccess.asset_id == asset_id)
        if user_id:
            query = query.where(AssetAccess.user_id == user_id)

        result = await self.db.execute(query)
        accesses = list(result.scalars())

        access_by_type: dict[str, int] = {}
        access_by_day: dict[str, int] = {}
        unique_users: set[uuid.UUID] = set()
        unique_assets: set[uuid.UUID] = set()

        for access in accesses:
            access_by_type[access.access_type] = access_by_type.get(access.access_type, 0) + 1

            day_str = access.accessed_at.strftime("%Y-%m-%d")
            access_by_day[day_str] = access_by_day.get(day_str, 0) + 1

            unique_users.add(access.user_id)
            unique_assets.add(access.asset_id)

        return {
            "period_days": days,
            "total_accesses": len(accesses),
            "unique_users": len(unique_users),
            "unique_assets": len(unique_assets),
            "access_by_type": access_by_type,
            "daily_trend": [
                {"date": k, "count": v}
                for k, v in sorted(access_by_day.items())
            ],
            "avg_daily_accesses": round(len(accesses) / days, 2) if days > 0 else 0,
        }

    async def get_top_accessed_assets(
        self,
        limit: int = 10,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get top accessed assets.

        Args:
            limit: Maximum assets to return
            days: Number of days to look back

        Returns:
            List of top accessed assets with counts
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                AssetAccess.asset_id,
                func.count(AssetAccess.id).label("access_count"),
            )
            .where(AssetAccess.accessed_at >= cutoff_date)
            .group_by(AssetAccess.asset_id)
            .order_by(func.count(AssetAccess.id).desc())
            .limit(limit)
        )

        top_assets = []
        for row in result:
            asset_result = await self.db.execute(
                select(DataAsset).where(DataAsset.id == row.asset_id)
            )
            asset = asset_result.scalar_one_or_none()

            if asset:
                top_assets.append({
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "domain": asset.domain,
                    "category": asset.category,
                    "access_count": row.access_count,
                })

        return top_assets

    async def _get_asset(self, asset_id: uuid.UUID) -> DataAsset:
        """Get asset by ID."""
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if not asset.is_active:
            raise ValueError(f"Asset is not active: {asset_id}")

        return asset

    async def _get_data_source(self, asset: DataAsset) -> DataSource:
        """Get the data source for an asset."""
        result = await self.db.execute(select(DataSource).limit(1))
        source = result.scalar_one_or_none()

        if not source:
            raise ValueError("No data source available")

        return source

    async def _get_total_rows(self, asset: DataAsset) -> int | None:
        """Get total row count for an asset table."""
        try:
            source = await self._get_data_source(asset)
            connector = get_connector(source.type, source.connection_config)

            count_query = f"SELECT COUNT(*) as cnt FROM {asset.source_table}"
            result = await connector.execute_query(count_query)

            if result and len(result) > 0:
                return result[0].get("cnt")
        except Exception:
            pass

        return None

    def _apply_query_params(
        self,
        df: pd.DataFrame,
        query_params: dict[str, Any],
    ) -> pd.DataFrame:
        """Apply query parameters to DataFrame.

        Supports:
        - filters: List of filter conditions
        - sort_by: Column to sort by
        - sort_order: 'asc' or 'desc'
        - columns: List of columns to select
        """
        result = df.copy()

        filters = query_params.get("filters", [])
        for f in filters:
            column = f.get("column")
            operator = f.get("operator", "eq")
            value = f.get("value")

            if column not in result.columns:
                continue

            if operator == "eq":
                result = result[result[column] == value]
            elif operator == "ne":
                result = result[result[column] != value]
            elif operator == "gt":
                result = result[result[column] > value]
            elif operator == "gte":
                result = result[result[column] >= value]
            elif operator == "lt":
                result = result[result[column] < value]
            elif operator == "lte":
                result = result[result[column] <= value]
            elif operator == "in":
                result = result[result[column].isin(value)]
            elif operator == "contains":
                result = result[result[column].astype(str).str.contains(str(value), na=False)]

        sort_by = query_params.get("sort_by")
        if sort_by and sort_by in result.columns:
            ascending = query_params.get("sort_order", "asc") == "asc"
            result = result.sort_values(by=sort_by, ascending=ascending)

        columns = query_params.get("columns")
        if columns:
            valid_columns = [c for c in columns if c in result.columns]
            if valid_columns:
                result = result[valid_columns]

        return result

    def _export_dataframe(
        self,
        df: pd.DataFrame,
        format: str,
        asset_name: str,
    ) -> tuple[bytes | str, str, str]:
        """Export DataFrame to specified format.

        Returns:
            Tuple of (content, content_type, filename)
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in asset_name)

        if format == "csv":
            content = df.to_csv(index=False)
            return content, "text/csv", f"{safe_name}_{timestamp}.csv"

        elif format == "json":
            content = df.to_json(orient="records", date_format="iso")
            return content, "application/json", f"{safe_name}_{timestamp}.json"

        elif format == "parquet":
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            content = buffer.getvalue()
            return content, "application/octet-stream", f"{safe_name}_{timestamp}.parquet"

        elif format == "excel":
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False)
            content = buffer.getvalue()
            return content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{safe_name}_{timestamp}.xlsx"

        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def _record_access(
        self,
        asset_id: uuid.UUID,
        user_id: uuid.UUID,
        access_type: str,
        details: dict[str, Any] | None = None,
    ) -> AssetAccess:
        """Record an asset access."""
        access = AssetAccess(
            asset_id=asset_id,
            user_id=user_id,
            access_type=access_type,
            access_details=details,
        )

        self.db.add(access)
        await self.db.commit()
        await self.db.refresh(access)

        return access
