"""Asset management service with value assessment and auto-cataloging capabilities."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
from openai import AsyncOpenAI
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AssetAccess, AssetType, DataAsset, AccessLevel


class AssetValueLevel:
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AssetService:
    """Service for data asset management and value assessment."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_usage_statistics(
        self,
        asset_id: uuid.UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get usage statistics for an asset.

        Args:
            asset_id: The asset ID
            days: Number of days to look back (default 30)

        Returns:
            Usage statistics including access counts, unique users, etc.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        total_accesses = await self.db.execute(
            select(func.count(AssetAccess.id))
            .where(AssetAccess.asset_id == asset_id)
            .where(AssetAccess.accessed_at >= cutoff_date)
        )
        total_count = total_accesses.scalar() or 0

        unique_users = await self.db.execute(
            select(func.count(func.distinct(AssetAccess.user_id)))
            .where(AssetAccess.asset_id == asset_id)
            .where(AssetAccess.accessed_at >= cutoff_date)
        )
        unique_user_count = unique_users.scalar() or 0

        access_by_type = await self.db.execute(
            select(
                AssetAccess.access_type,
                func.count(AssetAccess.id).label("count"),
            )
            .where(AssetAccess.asset_id == asset_id)
            .where(AssetAccess.accessed_at >= cutoff_date)
            .group_by(AssetAccess.access_type)
        )
        access_type_stats = {row.access_type: row.count for row in access_by_type}

        daily_trend = await self.db.execute(
            select(
                func.date(AssetAccess.accessed_at).label("date"),
                func.count(AssetAccess.id).label("count"),
            )
            .where(AssetAccess.asset_id == asset_id)
            .where(AssetAccess.accessed_at >= cutoff_date)
            .group_by(func.date(AssetAccess.accessed_at))
            .order_by(func.date(AssetAccess.accessed_at))
        )
        daily_stats = [{"date": str(row.date), "count": row.count} for row in daily_trend]

        return {
            "asset_id": str(asset_id),
            "period_days": days,
            "total_accesses": total_count,
            "unique_users": unique_user_count,
            "access_by_type": access_type_stats,
            "daily_trend": daily_stats,
            "avg_daily_accesses": round(total_count / days, 2) if days > 0 else 0,
        }

    async def calculate_lineage_depth(
        self,
        asset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Calculate the lineage depth for an asset.

        Returns:
            Lineage depth metrics including upstream/downstream depths
        """
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        async def get_depth(
            asset_ids: list[uuid.UUID],
            direction: str,
            current_depth: int,
            visited: set[uuid.UUID],
            max_depth: int = 10,
        ) -> int:
            if current_depth >= max_depth or not asset_ids:
                return current_depth - 1

            valid_ids = [aid for aid in asset_ids if aid not in visited]
            if not valid_ids:
                return current_depth - 1

            query_result = await self.db.execute(
                select(DataAsset).where(DataAsset.id.in_(valid_ids))
            )
            assets = list(query_result.scalars())

            max_found_depth = current_depth - 1
            for a in assets:
                visited.add(a.id)
                next_ids = (
                    a.upstream_assets if direction == "upstream" else a.downstream_assets
                )
                if next_ids:
                    depth = await get_depth(
                        next_ids, direction, current_depth + 1, visited, max_depth
                    )
                    max_found_depth = max(max_found_depth, depth)
                else:
                    max_found_depth = max(max_found_depth, current_depth)

            return max_found_depth

        upstream_depth = 0
        downstream_depth = 0

        if asset.upstream_assets:
            upstream_depth = await get_depth(
                asset.upstream_assets, "upstream", 1, {asset.id}
            )

        if asset.downstream_assets:
            downstream_depth = await get_depth(
                asset.downstream_assets, "downstream", 1, {asset.id}
            )

        return {
            "asset_id": str(asset_id),
            "upstream_depth": upstream_depth,
            "downstream_depth": downstream_depth,
            "total_depth": upstream_depth + downstream_depth,
            "has_upstream": len(asset.upstream_assets or []) > 0,
            "has_downstream": len(asset.downstream_assets or []) > 0,
            "direct_upstream_count": len(asset.upstream_assets or []),
            "direct_downstream_count": len(asset.downstream_assets or []),
        }

    async def evaluate_asset_value(
        self,
        asset_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Evaluate the business value of an asset.

        Combines usage statistics and lineage analysis to determine value.

        Returns:
            Value assessment including score and level
        """
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        usage_stats = await self.get_usage_statistics(asset_id)
        lineage = await self.calculate_lineage_depth(asset_id)

        score = 0.0

        access_score = min(usage_stats["total_accesses"] / 100, 30)
        score += access_score

        user_score = min(usage_stats["unique_users"] * 3, 20)
        score += user_score

        downstream_score = min(lineage["downstream_depth"] * 5, 20)
        score += downstream_score

        dependency_score = min(lineage["direct_downstream_count"] * 2, 10)
        score += dependency_score

        if asset.is_certified:
            score += 10

        if asset.tags and len(asset.tags) >= 3:
            score += 5

        if asset.description and len(asset.description) >= 50:
            score += 5

        score = min(score, 100)

        if score >= 70:
            level = AssetValueLevel.HIGH
        elif score >= 40:
            level = AssetValueLevel.MEDIUM
        else:
            level = AssetValueLevel.LOW

        return {
            "asset_id": str(asset_id),
            "value_score": round(score, 2),
            "value_level": level,
            "factors": {
                "usage_frequency": {
                    "score": round(access_score, 2),
                    "max": 30,
                    "metric": usage_stats["total_accesses"],
                },
                "user_reach": {
                    "score": round(user_score, 2),
                    "max": 20,
                    "metric": usage_stats["unique_users"],
                },
                "business_impact": {
                    "score": round(downstream_score, 2),
                    "max": 20,
                    "metric": lineage["downstream_depth"],
                },
                "dependency_count": {
                    "score": round(dependency_score, 2),
                    "max": 10,
                    "metric": lineage["direct_downstream_count"],
                },
                "certification_bonus": 10 if asset.is_certified else 0,
                "metadata_quality": (5 if asset.tags and len(asset.tags) >= 3 else 0)
                    + (5 if asset.description and len(asset.description) >= 50 else 0),
            },
            "usage_summary": usage_stats,
            "lineage_summary": lineage,
        }

    async def update_asset_value_score(
        self,
        asset_id: uuid.UUID,
    ) -> DataAsset:
        """Calculate and persist the value score for an asset.

        Returns:
            Updated asset with new value_score
        """
        evaluation = await self.evaluate_asset_value(asset_id)

        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        asset.value_score = evaluation["value_score"]
        await self.db.commit()
        await self.db.refresh(asset)

        return asset

    async def batch_update_value_scores(
        self,
        asset_ids: list[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        """Batch update value scores for multiple assets.

        Args:
            asset_ids: Optional list of asset IDs. If None, updates all active assets.

        Returns:
            Summary of updates
        """
        if asset_ids:
            query = select(DataAsset).where(
                DataAsset.id.in_(asset_ids),
                DataAsset.is_active.is_(True),
            )
        else:
            query = select(DataAsset).where(DataAsset.is_active.is_(True))

        result = await self.db.execute(query)
        assets = list(result.scalars())

        updated = 0
        failed = 0
        results = []

        for asset in assets:
            try:
                evaluation = await self.evaluate_asset_value(asset.id)
                asset.value_score = evaluation["value_score"]
                results.append({
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "score": evaluation["value_score"],
                    "level": evaluation["value_level"],
                })
                updated += 1
            except Exception as e:
                results.append({
                    "asset_id": str(asset.id),
                    "name": asset.name,
                    "error": str(e),
                })
                failed += 1

        await self.db.commit()

        return {
            "total_processed": len(assets),
            "updated": updated,
            "failed": failed,
            "results": results,
        }

    async def get_value_distribution(self) -> dict[str, Any]:
        """Get distribution of asset values across all active assets.

        Returns:
            Summary statistics of asset values
        """
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.is_active.is_(True))
        )
        assets = list(result.scalars())

        high_value = [a for a in assets if (a.value_score or 0) >= 70]
        medium_value = [a for a in assets if 40 <= (a.value_score or 0) < 70]
        low_value = [a for a in assets if (a.value_score or 0) < 40]
        unscored = [a for a in assets if a.value_score is None]

        scores = [a.value_score for a in assets if a.value_score is not None]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            "total_assets": len(assets),
            "distribution": {
                "high": {
                    "count": len(high_value),
                    "percentage": round(len(high_value) / len(assets) * 100, 2) if assets else 0,
                },
                "medium": {
                    "count": len(medium_value),
                    "percentage": round(len(medium_value) / len(assets) * 100, 2) if assets else 0,
                },
                "low": {
                    "count": len(low_value),
                    "percentage": round(len(low_value) / len(assets) * 100, 2) if assets else 0,
                },
                "unscored": {
                    "count": len(unscored),
                    "percentage": round(len(unscored) / len(assets) * 100, 2) if assets else 0,
                },
            },
            "average_score": round(avg_score, 2),
            "top_assets": [
                {"id": str(a.id), "name": a.name, "score": a.value_score}
                for a in sorted(assets, key=lambda x: x.value_score or 0, reverse=True)[:10]
            ],
        }

    async def auto_catalog_from_etl(
        self,
        pipeline_id: uuid.UUID,
        pipeline_name: str,
        target_table: str,
        target_schema: str | None,
        df: pd.DataFrame,
        source_table: str | None = None,
    ) -> dict[str, Any]:
        """Auto-catalog a data asset after ETL execution.

        Creates or updates a DataAsset with:
        1. Extracted data attributes (row count, columns, data quality)
        2. AI-generated description and tags
        3. Automatic value score

        Args:
            pipeline_id: ETL pipeline ID
            pipeline_name: ETL pipeline name
            target_table: Target table name
            target_schema: Target schema name
            df: DataFrame containing the ETL output
            source_table: Optional source table for lineage

        Returns:
            Catalog result with asset details
        """
        result = await self.db.execute(
            select(DataAsset).where(
                DataAsset.source_table == target_table,
                DataAsset.source_schema == target_schema,
            )
        )
        existing_asset = result.scalar_one_or_none()

        data_profile = self._extract_data_profile(df)

        ai_metadata = await self._generate_ai_metadata(
            table_name=target_table,
            schema_name=target_schema,
            data_profile=data_profile,
            pipeline_name=pipeline_name,
        )

        if existing_asset:
            asset = await self._update_asset_catalog(
                asset=existing_asset,
                data_profile=data_profile,
                ai_metadata=ai_metadata,
                source_table=source_table,
            )
            action = "updated"
        else:
            asset = await self._create_asset_catalog(
                target_table=target_table,
                target_schema=target_schema,
                data_profile=data_profile,
                ai_metadata=ai_metadata,
                source_table=source_table,
            )
            action = "created"

        evaluation = await self.evaluate_asset_value(asset.id)
        asset.value_score = evaluation["value_score"]
        await self.db.commit()
        await self.db.refresh(asset)

        return {
            "action": action,
            "asset_id": str(asset.id),
            "asset_name": asset.name,
            "data_profile": data_profile,
            "ai_summary": asset.ai_summary,
            "tags": asset.tags,
            "value_score": asset.value_score,
            "value_level": evaluation["value_level"],
        }

    def _extract_data_profile(self, df: pd.DataFrame) -> dict[str, Any]:
        """Extract data profile from DataFrame.

        Returns:
            Data profile including row count, columns, and quality metrics
        """
        profile: dict[str, Any] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": [],
            "quality_metrics": {},
        }

        total_cells = len(df) * len(df.columns)
        total_nulls = int(df.isnull().sum().sum())
        profile["quality_metrics"]["completeness"] = round(
            (1 - total_nulls / total_cells) * 100, 2
        ) if total_cells > 0 else 100.0

        duplicate_count = len(df) - len(df.drop_duplicates())
        profile["quality_metrics"]["uniqueness"] = round(
            (1 - duplicate_count / len(df)) * 100, 2
        ) if len(df) > 0 else 100.0

        for col in df.columns:
            col_info: dict[str, Any] = {
                "name": col,
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": round(df[col].isnull().sum() / len(df) * 100, 2) if len(df) > 0 else 0,
                "unique_count": int(df[col].nunique()),
            }

            if df[col].dtype in ["int64", "float64"]:
                col_info["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_info["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                col_info["mean"] = round(float(df[col].mean()), 2) if not df[col].isnull().all() else None
            elif df[col].dtype == "object":
                col_info["avg_length"] = round(df[col].astype(str).str.len().mean(), 1)
                col_info["top_values"] = df[col].value_counts().head(3).to_dict()

            profile["columns"].append(col_info)

        return profile

    async def _generate_ai_metadata(
        self,
        table_name: str,
        schema_name: str | None,
        data_profile: dict[str, Any],
        pipeline_name: str,
    ) -> dict[str, Any]:
        """Generate AI-powered metadata for the asset.

        Returns:
            AI-generated description, tags, category, and domain
        """
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        columns_summary = [
            {
                "name": col["name"],
                "type": col["dtype"],
                "null_pct": col["null_percentage"],
                "unique": col["unique_count"],
            }
            for col in data_profile["columns"][:20]
        ]

        prompt = f"""Analyze this data table and generate metadata for a data asset catalog.

Table: {schema_name + '.' if schema_name else ''}{table_name}
Source ETL Pipeline: {pipeline_name}
Row Count: {data_profile['row_count']}
Columns: {len(data_profile['columns'])}
Data Quality:
- Completeness: {data_profile['quality_metrics']['completeness']}%
- Uniqueness: {data_profile['quality_metrics']['uniqueness']}%

Column Details:
{json.dumps(columns_summary, indent=2)}

Generate metadata in JSON format:
{{
  "name": "Human-readable asset name",
  "description": "Clear description of what this data represents and its business purpose",
  "summary": "Brief AI summary (1-2 sentences)",
  "category": "One of: master_data, transaction, analytics, reference, staging",
  "domain": "Business domain like sales, customer, product, finance, operations, etc.",
  "tags": ["tag1", "tag2", "tag3"],
  "sensitivity_level": "One of: public, internal, restricted, confidential",
  "suggested_use_cases": ["use case 1", "use case 2"]
}}"""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data catalog expert. Generate accurate metadata for data assets based on their structure and content.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return {
                "name": table_name,
                "description": f"Data asset from ETL pipeline: {pipeline_name}",
                "summary": f"Auto-cataloged table with {data_profile['row_count']} rows",
                "category": "staging",
                "domain": "unknown",
                "tags": ["auto-cataloged", "etl-output"],
                "sensitivity_level": "internal",
            }

    async def _create_asset_catalog(
        self,
        target_table: str,
        target_schema: str | None,
        data_profile: dict[str, Any],
        ai_metadata: dict[str, Any],
        source_table: str | None,
    ) -> DataAsset:
        """Create a new asset from catalog data."""
        sensitivity_map = {
            "public": AccessLevel.PUBLIC,
            "internal": AccessLevel.INTERNAL,
            "restricted": AccessLevel.RESTRICTED,
            "confidential": AccessLevel.CONFIDENTIAL,
        }

        asset = DataAsset(
            name=ai_metadata.get("name", target_table),
            description=ai_metadata.get("description"),
            asset_type=AssetType.TABLE,
            source_table=target_table,
            source_schema=target_schema,
            access_level=sensitivity_map.get(
                ai_metadata.get("sensitivity_level", "internal"),
                AccessLevel.INTERNAL,
            ),
            tags=ai_metadata.get("tags", ["auto-cataloged"]),
            category=ai_metadata.get("category"),
            domain=ai_metadata.get("domain"),
            ai_summary=ai_metadata.get("summary"),
            lineage_json={
                "data_profile": data_profile,
                "suggested_use_cases": ai_metadata.get("suggested_use_cases", []),
            },
            is_active=True,
        )

        if source_table:
            source_result = await self.db.execute(
                select(DataAsset).where(DataAsset.source_table == source_table)
            )
            source_asset = source_result.scalar_one_or_none()
            if source_asset:
                asset.upstream_assets = [source_asset.id]

        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)

        return asset

    async def _update_asset_catalog(
        self,
        asset: DataAsset,
        data_profile: dict[str, Any],
        ai_metadata: dict[str, Any],
        source_table: str | None,
    ) -> DataAsset:
        """Update an existing asset with new catalog data."""
        asset.ai_summary = ai_metadata.get("summary", asset.ai_summary)
        asset.description = ai_metadata.get("description", asset.description)

        existing_tags = set(asset.tags or [])
        new_tags = set(ai_metadata.get("tags", []))
        asset.tags = list(existing_tags | new_tags)

        if not asset.category:
            asset.category = ai_metadata.get("category")
        if not asset.domain:
            asset.domain = ai_metadata.get("domain")

        asset.lineage_json = {
            **(asset.lineage_json or {}),
            "data_profile": data_profile,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        if source_table:
            source_result = await self.db.execute(
                select(DataAsset).where(DataAsset.source_table == source_table)
            )
            source_asset = source_result.scalar_one_or_none()
            if source_asset:
                existing_upstream = list(asset.upstream_assets or [])
                if source_asset.id not in existing_upstream:
                    asset.upstream_assets = existing_upstream + [source_asset.id]

        await self.db.commit()
        await self.db.refresh(asset)

        return asset

    async def get_asset_by_table(
        self,
        table_name: str,
        schema_name: str | None = None,
    ) -> DataAsset | None:
        """Get asset by source table name."""
        query = select(DataAsset).where(DataAsset.source_table == table_name)
        if schema_name:
            query = query.where(DataAsset.source_schema == schema_name)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_value_trend(
        self,
        asset_id: uuid.UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get value trend analysis for an asset.

        Analyzes how asset value has changed over time based on usage patterns.

        Args:
            asset_id: The asset ID
            days: Number of days to analyze (default 30)

        Returns:
            Value trend including historical data and trend direction
        """
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        daily_accesses = await self.db.execute(
            select(
                func.date(AssetAccess.accessed_at).label("date"),
                func.count(AssetAccess.id).label("count"),
                func.count(func.distinct(AssetAccess.user_id)).label("unique_users"),
            )
            .where(AssetAccess.asset_id == asset_id)
            .where(AssetAccess.accessed_at >= cutoff_date)
            .group_by(func.date(AssetAccess.accessed_at))
            .order_by(func.date(AssetAccess.accessed_at))
        )

        daily_data = [
            {
                "date": str(row.date),
                "access_count": row.count,
                "unique_users": row.unique_users,
            }
            for row in daily_accesses
        ]

        if len(daily_data) >= 2:
            first_half = daily_data[: len(daily_data) // 2]
            second_half = daily_data[len(daily_data) // 2 :]

            first_avg = (
                sum(d["access_count"] for d in first_half) / len(first_half)
                if first_half
                else 0
            )
            second_avg = (
                sum(d["access_count"] for d in second_half) / len(second_half)
                if second_half
                else 0
            )

            if first_avg > 0:
                change_percentage = round(
                    ((second_avg - first_avg) / first_avg) * 100, 2
                )
            else:
                change_percentage = 100.0 if second_avg > 0 else 0.0

            if change_percentage > 10:
                trend_direction = "up"
            elif change_percentage < -10:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            change_percentage = None
            trend_direction = "insufficient_data"

        current_score = asset.value_score
        if current_score is not None:
            if current_score >= 70:
                current_level = AssetValueLevel.HIGH
            elif current_score >= 40:
                current_level = AssetValueLevel.MEDIUM
            else:
                current_level = AssetValueLevel.LOW
        else:
            current_level = None

        trend_scores = []
        if len(daily_data) >= 7:
            week_chunks = [daily_data[i : i + 7] for i in range(0, len(daily_data), 7)]
            for i, chunk in enumerate(week_chunks):
                total_accesses = sum(d["access_count"] for d in chunk)
                total_users = max(d["unique_users"] for d in chunk) if chunk else 0

                estimated_score = min(
                    (total_accesses / 100 * 30)
                    + (total_users * 3)
                    + (10 if asset.is_certified else 0),
                    100,
                )
                trend_scores.append(
                    {
                        "period": f"Week {i + 1}",
                        "start_date": chunk[0]["date"] if chunk else None,
                        "end_date": chunk[-1]["date"] if chunk else None,
                        "estimated_score": round(estimated_score, 2),
                        "access_count": total_accesses,
                        "unique_users": total_users,
                    }
                )

        return {
            "asset_id": str(asset_id),
            "asset_name": asset.name,
            "current_score": current_score,
            "current_level": current_level,
            "trend": trend_scores,
            "daily_data": daily_data,
            "change_percentage": change_percentage,
            "trend_direction": trend_direction,
            "analysis_period_days": days,
        }

    async def export_asset_data(
        self,
        asset_id: uuid.UUID,
        format_type: str = "csv",
        columns: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100000,
    ) -> dict[str, Any]:
        """
        Export asset data to various formats.

        Args:
            asset_id: The asset ID to export
            format_type: Output format (csv, excel, json, parquet)
            columns: Optional list of columns to include
            filters: Optional filters to apply
            limit: Maximum rows to export

        Returns:
            Export result with file path and metadata
        """
        from app.connectors import get_connector
        from app.models import DataSource
        import os
        from pathlib import Path

        # Get asset details
        result = await self.db.execute(
            select(DataAsset).where(DataAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")

        if not asset.source_table:
            raise ValueError(f"Asset has no associated source table")

        # Get data source for the asset
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == asset.source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            # Try to find the table in any available source
            source_result = await self.db.execute(
                select(DataSource).limit(1)
            )
            source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError("No data source available for export")

        # Load data
        connector = get_connector(source.type, source.connection_config)
        df = await connector.read_data(
            table_name=asset.source_table,
            limit=limit,
        )

        # Apply column selection
        if columns:
            existing_columns = [c for c in columns if c in df.columns]
            df = df[existing_columns]

        # Apply filters
        if filters:
            df = self._apply_dataframe_filters(df, filters)

        # Create export directory
        export_dir = Path("/tmp/exports")
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = asset.name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{timestamp}.{format_type}"
        file_path = export_dir / filename

        # Export based on format
        if format_type == "csv":
            df.to_csv(file_path, index=False)
        elif format_type == "excel":
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Data", index=False)
        elif format_type == "json":
            df.to_json(file_path, orient="records", indent=2)
        elif format_type == "parquet":
            df.to_parquet(file_path, index=False)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        # Get file size
        file_size = file_path.stat().st_size

        # Log export in audit
        await self._log_export_activity(asset_id, format_type, len(df), file_size)

        return {
            "asset_id": str(asset_id),
            "asset_name": asset.name,
            "format": format_type,
            "file_path": str(file_path),
            "filename": filename,
            "row_count": len(df),
            "column_count": len(df.columns),
            "file_size_bytes": file_size,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def _apply_dataframe_filters(
        self,
        df: pd.DataFrame,
        filters: dict[str, Any],
    ) -> pd.DataFrame:
        """Apply filters to a DataFrame."""
        result = df.copy()

        for column, filter_config in filters.items():
            if column not in result.columns:
                continue

            if isinstance(filter_config, dict):
                # Range filter
                if "min" in filter_config:
                    result = result[result[column] >= filter_config["min"]]
                if "max" in filter_config:
                    result = result[result[column] <= filter_config["max"]]
                # Values filter
                if "values" in filter_config:
                    result = result[result[column].isin(filter_config["values"])]
            elif isinstance(filter_config, list):
                result = result[result[column].isin(filter_config)]
            else:
                # Equality filter
                result = result[result[column] == filter_config]

        return result

    async def _log_export_activity(
        self,
        asset_id: uuid.UUID,
        format_type: str,
        row_count: int,
        file_size: int,
    ) -> None:
        """Log export activity to audit log."""
        # This would log to the audit table
        # For now, it's a placeholder for tracking
        pass

    async def get_export_formats(self) -> list[dict[str, Any]]:
        """Get available export formats with descriptions."""
        return [
            {
                "format": "csv",
                "name": "CSV",
                "description": "Comma-separated values",
                "extension": "csv",
                "supports_large_files": True,
                "supports_multiple_sheets": False,
            },
            {
                "format": "excel",
                "name": "Excel",
                "description": "Microsoft Excel format",
                "extension": "xlsx",
                "supports_large_files": False,
                "supports_multiple_sheets": True,
            },
            {
                "format": "json",
                "name": "JSON",
                "description": "JavaScript Object Notation",
                "extension": "json",
                "supports_large_files": True,
                "supports_multiple_sheets": False,
            },
            {
                "format": "parquet",
                "name": "Parquet",
                "description": "Apache Parquet columnar storage",
                "extension": "parquet",
                "supports_large_files": True,
                "supports_multiple_sheets": False,
            },
        ]

    async def export_multiple_assets(
        self,
        asset_ids: list[uuid.UUID],
        format_type: str = "csv",
        combine: bool = False,
    ) -> dict[str, Any]:
        """
        Export multiple assets.

        Args:
            asset_ids: List of asset IDs to export
            format_type: Output format
            combine: Whether to combine into a single file (Excel only)

        Returns:
            Export results for each asset
        """
        results = []

        for asset_id in asset_ids:
            try:
                result = await self.export_asset_data(
                    asset_id=asset_id,
                    format_type=format_type,
                )
                results.append({
                    "asset_id": str(asset_id),
                    "status": "success",
                    **result,
                })
            except Exception as e:
                results.append({
                    "asset_id": str(asset_id),
                    "status": "failed",
                    "error": str(e),
                })

        return {
            "total_assets": len(asset_ids),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "results": results,
        }
