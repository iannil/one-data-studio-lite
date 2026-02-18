from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.core.database import engine
from app.models import DataSource, ETLPipeline, ETLStepType


class BaseETLStep(ABC):
    """Base class for ETL transformation steps."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process the dataframe and return the transformed result."""
        pass


class FilterStep(BaseETLStep):
    """Filter rows based on conditions."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        conditions = self.config.get("conditions", [])

        for condition in conditions:
            column = condition.get("column")
            operator = condition.get("operator")
            value = condition.get("value")

            if column not in df.columns:
                continue

            if operator == "eq":
                df = df[df[column] == value]
            elif operator == "ne":
                df = df[df[column] != value]
            elif operator == "gt":
                df = df[df[column] > value]
            elif operator == "gte":
                df = df[df[column] >= value]
            elif operator == "lt":
                df = df[df[column] < value]
            elif operator == "lte":
                df = df[df[column] <= value]
            elif operator == "in":
                df = df[df[column].isin(value)]
            elif operator == "not_in":
                df = df[~df[column].isin(value)]
            elif operator == "contains":
                df = df[df[column].astype(str).str.contains(value, na=False)]
            elif operator == "is_null":
                df = df[df[column].isnull()]
            elif operator == "is_not_null":
                df = df[df[column].notnull()]

        return df


class DeduplicateStep(BaseETLStep):
    """Remove duplicate rows."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = self.config.get("columns")
        keep = self.config.get("keep", "first")

        if columns:
            return df.drop_duplicates(subset=columns, keep=keep)
        return df.drop_duplicates(keep=keep)


class MapValuesStep(BaseETLStep):
    """Map values in a column."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        column = self.config.get("column")
        mapping = self.config.get("mapping", {})
        default = self.config.get("default")

        if column not in df.columns:
            return df

        result = df.copy()
        if default is not None:
            result[column] = result[column].map(mapping).fillna(default)
        else:
            result[column] = result[column].map(mapping).fillna(result[column])

        return result


class JoinStep(BaseETLStep):
    """Join with another table.

    Config format:
    {
        "source_id": "uuid-of-data-source",  # Data source containing the join table
        "join_table": "table_name",           # Table to join with
        "join_type": "left",                  # left/right/inner/outer
        "on": ["col1", "col2"],               # Columns to join on (same names in both tables)
        "left_on": ["col1"],                  # Optional: Left table join columns
        "right_on": ["col1"],                 # Optional: Right table join columns
        "suffixes": ["_x", "_y"]              # Optional: Suffixes for overlapping columns
    }
    """

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        join_type = self.config.get("join_type", "left")
        on_columns = self.config.get("on")
        left_on = self.config.get("left_on")
        right_on = self.config.get("right_on")
        suffixes = self.config.get("suffixes", ("_x", "_y"))

        # Load the join table data
        right_df = await self._load_join_table()

        if not isinstance(right_df, pd.DataFrame) or right_df.empty:
            return df

        # Perform the join
        if on_columns:
            result = df.merge(
                right_df,
                how=join_type,
                on=on_columns,
                suffixes=suffixes,
            )
        elif left_on and right_on:
            result = df.merge(
                right_df,
                how=join_type,
                left_on=left_on,
                right_on=right_on,
                suffixes=suffixes,
            )
        else:
            raise ValueError("Join step requires 'on' or 'left_on'/'right_on' columns")

        return result

    async def _load_join_table(self) -> pd.DataFrame:
        """Load data from the join table using the specified data source."""
        source_id = self.config.get("source_id")
        join_table = self.config.get("join_table")
        join_query = self.config.get("join_query")  # Optional: custom query

        if not source_id:
            raise ValueError("Join step requires 'source_id' in config")

        if not join_table and not join_query:
            raise ValueError("Join step requires 'join_table' or 'join_query' in config")

        # Use sync engine to load data (required for pandas)
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        from app.core.config import settings
        from app.models import DataSource

        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        sync_engine = create_engine(sync_url)

        with Session(sync_engine) as session:
            source = session.execute(
                select(DataSource).where(DataSource.id == uuid.UUID(source_id))
            ).scalar_one_or_none()

            if not source:
                raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)

        if join_query:
            return await connector.read_data(query=join_query)
        return await connector.read_data(table_name=join_table)


class CalculateStep(BaseETLStep):
    """Create calculated columns."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        calculations = self.config.get("calculations", [])

        result = df.copy()
        for calc in calculations:
            target_column = calc.get("target_column")
            expression = calc.get("expression")
            calc_type = calc.get("type", "formula")

            if calc_type == "formula":
                result[target_column] = result.eval(expression)
            elif calc_type == "concat":
                columns = calc.get("columns", [])
                separator = calc.get("separator", "")
                result[target_column] = result[columns].astype(str).agg(separator.join, axis=1)
            elif calc_type == "date_diff":
                col1 = calc.get("column1")
                col2 = calc.get("column2")
                unit = calc.get("unit", "days")
                diff = pd.to_datetime(result[col1]) - pd.to_datetime(result[col2])
                if unit == "days":
                    result[target_column] = diff.dt.days
                elif unit == "hours":
                    result[target_column] = diff.dt.total_seconds() / 3600
                elif unit == "minutes":
                    result[target_column] = diff.dt.total_seconds() / 60
                elif unit == "seconds":
                    result[target_column] = diff.dt.total_seconds()
                else:
                    result[target_column] = diff.dt.days

        return result


class FillMissingStep(BaseETLStep):
    """Fill missing values."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        fills = self.config.get("fills", [])

        result = df.copy()
        for fill in fills:
            column = fill.get("column")
            strategy = fill.get("strategy", "value")
            value = fill.get("value")

            if column not in result.columns:
                continue

            if strategy == "value":
                result[column] = result[column].fillna(value)
            elif strategy == "mean":
                result[column] = result[column].fillna(result[column].mean())
            elif strategy == "median":
                result[column] = result[column].fillna(result[column].median())
            elif strategy == "mode":
                result[column] = result[column].fillna(result[column].mode().iloc[0])
            elif strategy == "forward_fill":
                result[column] = result[column].ffill()
            elif strategy == "backward_fill":
                result[column] = result[column].bfill()

        return result


class MaskStep(BaseETLStep):
    """Mask sensitive data."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        masks = self.config.get("masks", [])

        result = df.copy()
        for mask_config in masks:
            column = mask_config.get("column")
            strategy = mask_config.get("strategy", "partial")

            if column not in result.columns:
                continue

            if strategy == "partial":
                start = mask_config.get("start", 3)
                end = mask_config.get("end", 4)
                mask_char = mask_config.get("mask_char", "*")
                result[column] = result[column].apply(
                    lambda x: self._partial_mask(str(x), start, end, mask_char) if pd.notna(x) else x
                )
            elif strategy == "hash":
                import hashlib
                result[column] = result[column].apply(
                    lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16] if pd.notna(x) else x
                )
            elif strategy == "replace":
                replacement = mask_config.get("replacement", "[MASKED]")
                result[column] = replacement

        return result

    def _partial_mask(self, value: str, start: int, end: int, mask_char: str) -> str:
        if len(value) <= start + end:
            return mask_char * len(value)
        return value[:start] + mask_char * (len(value) - start - end) + value[-end:]


class RenameStep(BaseETLStep):
    """Rename columns."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        mapping = self.config.get("mapping", {})
        return df.rename(columns=mapping)


class TypeCastStep(BaseETLStep):
    """Cast column types."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        casts = self.config.get("casts", [])

        result = df.copy()
        for cast in casts:
            column = cast.get("column")
            target_type = cast.get("target_type")
            errors = cast.get("errors", "coerce")

            if column not in result.columns:
                continue

            if target_type == "int":
                result[column] = pd.to_numeric(result[column], errors=errors).astype("Int64")
            elif target_type == "float":
                result[column] = pd.to_numeric(result[column], errors=errors).astype(float)
            elif target_type == "str":
                result[column] = result[column].astype(str)
            elif target_type == "datetime":
                date_format = cast.get("format")
                result[column] = pd.to_datetime(result[column], format=date_format, errors=errors)
            elif target_type == "bool":
                result[column] = result[column].astype(bool)

        return result


class AggregateStep(BaseETLStep):
    """Aggregate data."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        group_by = self.config.get("group_by", [])
        aggregations = self.config.get("aggregations", {})

        if not group_by or not aggregations:
            return df

        return df.groupby(group_by).agg(aggregations).reset_index()


class SortStep(BaseETLStep):
    """Sort data."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = self.config.get("columns", [])
        ascending = self.config.get("ascending", True)

        if not columns:
            return df

        return df.sort_values(by=columns, ascending=ascending)


class DropColumnsStep(BaseETLStep):
    """Drop columns."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = self.config.get("columns", [])
        existing = [c for c in columns if c in df.columns]
        return df.drop(columns=existing)


class SelectColumnsStep(BaseETLStep):
    """Select specific columns."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        columns = self.config.get("columns", [])
        existing = [c for c in columns if c in df.columns]
        return df[existing]


class CustomPythonStep(BaseETLStep):
    """Execute custom Python code."""

    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        code = self.config.get("code", "")

        local_vars = {"df": df, "pd": pd, "np": np}
        exec(code, {"__builtins__": {}}, local_vars)

        return local_vars.get("result", df)


STEP_REGISTRY: dict[ETLStepType, type[BaseETLStep]] = {
    ETLStepType.FILTER: FilterStep,
    ETLStepType.DEDUPLICATE: DeduplicateStep,
    ETLStepType.MAP_VALUES: MapValuesStep,
    ETLStepType.JOIN: JoinStep,
    ETLStepType.CALCULATE: CalculateStep,
    ETLStepType.FILL_MISSING: FillMissingStep,
    ETLStepType.MASK: MaskStep,
    ETLStepType.RENAME: RenameStep,
    ETLStepType.TYPE_CAST: TypeCastStep,
    ETLStepType.AGGREGATE: AggregateStep,
    ETLStepType.SORT: SortStep,
    ETLStepType.DROP_COLUMNS: DropColumnsStep,
    ETLStepType.SELECT_COLUMNS: SelectColumnsStep,
    ETLStepType.CUSTOM_PYTHON: CustomPythonStep,
}


class ETLEngine:
    """Main ETL engine for executing pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_pipeline(
        self,
        pipeline: ETLPipeline,
        preview_mode: bool = False,
        preview_rows: int = 100,
    ) -> dict[str, Any]:
        """Execute an ETL pipeline."""
        start_time = datetime.now(timezone.utc)
        step_metrics: dict[str, Any] = {}

        try:
            df = await self._load_source_data(pipeline, preview_rows if preview_mode else None)
            rows_input = len(df)

            enabled_steps = sorted(
                [s for s in pipeline.steps if s.is_enabled],
                key=lambda s: s.order
            )

            for step in enabled_steps:
                step_start = datetime.now(timezone.utc)

                step_class = STEP_REGISTRY.get(step.step_type)
                if not step_class:
                    raise ValueError(f"Unknown step type: {step.step_type}")

                processor = step_class(step.config)
                df = await processor.process(df)

                step_metrics[str(step.id)] = {
                    "name": step.name,
                    "type": step.step_type.value,
                    "rows_out": len(df),
                    "duration_ms": int((datetime.now(timezone.utc) - step_start).total_seconds() * 1000),
                }

            if not preview_mode:
                await self._write_target_data(pipeline, df)
                # 自动更新数据资产血缘关系
                await self._update_lineage(pipeline)
                # 自动编目：创建或更新数据资产
                catalog_result = await self._auto_catalog_asset(pipeline, df)
                # 可选：同步到 Superset BI
                bi_result = await self._sync_to_bi(pipeline)

            return {
                "status": "success",
                "rows_input": rows_input,
                "rows_output": len(df),
                "step_metrics": step_metrics,
                "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
                "preview_data": df.head(preview_rows).to_dict(orient="records") if preview_mode else None,
                "bi_sync": bi_result if not preview_mode else None,
                "asset_catalog": catalog_result if not preview_mode else None,
            }

        except Exception as e:
            return {
                "status": "failed",
                "error_message": str(e),
                "step_metrics": step_metrics,
                "duration_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000),
            }

    async def _load_source_data(
        self,
        pipeline: ETLPipeline,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Load data from the source."""
        source_type = pipeline.source_type
        source_config = pipeline.source_config

        if source_type == "table":
            source_id = source_config.get("source_id")
            table_name = source_config.get("table_name")

            from sqlalchemy import select
            result = await self.db.execute(
                select(DataSource).where(DataSource.id == uuid.UUID(source_id))
            )
            source = result.scalar_one_or_none()

            if not source:
                raise ValueError(f"Data source not found: {source_id}")

            connector = get_connector(source.type, source.connection_config)
            return await connector.read_data(table_name=table_name, limit=limit)

        elif source_type == "query":
            source_id = source_config.get("source_id")
            query = source_config.get("query")

            from sqlalchemy import select
            result = await self.db.execute(
                select(DataSource).where(DataSource.id == uuid.UUID(source_id))
            )
            source = result.scalar_one_or_none()

            if not source:
                raise ValueError(f"Data source not found: {source_id}")

            connector = get_connector(source.type, source.connection_config)
            return await connector.read_data(query=query, limit=limit)

        elif source_type == "file":
            from app.connectors.file import FileConnector
            connector = FileConnector(source_config)
            return await connector.read_data(limit=limit)

        else:
            raise ValueError(f"Unknown source type: {source_type}")

    async def _write_target_data(
        self,
        pipeline: ETLPipeline,
        df: pd.DataFrame,
    ) -> None:
        """Write data to the target."""
        target_type = pipeline.target_type
        target_config = pipeline.target_config

        if target_type == "table":
            table_name = target_config.get("table_name")
            if_exists = target_config.get("if_exists", "append")
            schema = target_config.get("schema")

            from sqlalchemy import create_engine
            from app.core.config import settings
            sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
            sync_engine = create_engine(sync_url)

            df.to_sql(
                table_name,
                sync_engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
            )

        elif target_type == "file":
            file_path = target_config.get("file_path")
            file_format = target_config.get("format", "csv")

            if file_format == "csv":
                df.to_csv(file_path, index=False)
            elif file_format == "json":
                df.to_json(file_path, orient="records")
            elif file_format == "parquet":
                df.to_parquet(file_path, index=False)
            elif file_format == "excel":
                df.to_excel(file_path, index=False)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")

        else:
            raise ValueError(f"Unknown target type: {target_type}")

    async def _update_lineage(
        self,
        pipeline: ETLPipeline,
    ) -> None:
        """Auto-update data asset lineage after ETL execution."""
        from sqlalchemy import select, update
        from app.models import DataAsset

        source_table = None
        target_table = None

        # 获取源表名
        if pipeline.source_type == "table":
            source_table = pipeline.source_config.get("table_name")

        # 获取目标表名
        if pipeline.target_type == "table":
            target_table = pipeline.target_config.get("table_name")

        if not source_table or not target_table:
            return  # 无法建立血缘关系

        # 查找源数据资产
        source_result = await self.db.execute(
            select(DataAsset).where(DataAsset.source_table == source_table)
        )
        source_asset = source_result.scalar_one_or_none()

        # 查找目标数据资产
        target_result = await self.db.execute(
            select(DataAsset).where(DataAsset.source_table == target_table)
        )
        target_asset = target_result.scalar_one_or_none()

        if not source_asset or not target_asset:
            return  # 数据资产不存在，跳过

        # 更新目标资产的上游关系
        if source_asset.id not in (target_asset.upstream_assets or []):
            new_upstream = list(target_asset.upstream_assets or []) + [source_asset.id]
            await self.db.execute(
                update(DataAsset)
                .where(DataAsset.id == target_asset.id)
                .values(upstream_assets=new_upstream)
            )

        # 更新源资产的下游关系
        if target_asset.id not in (source_asset.downstream_assets or []):
            new_downstream = list(source_asset.downstream_assets or []) + [target_asset.id]
            await self.db.execute(
                update(DataAsset)
                .where(DataAsset.id == source_asset.id)
                .values(downstream_assets=new_downstream)
            )

        await self.db.commit()

    async def _sync_to_bi(
        self,
        pipeline: ETLPipeline,
    ) -> dict[str, Any] | None:
        """Optionally sync ETL output to Superset BI.

        Triggered when target_config contains sync_to_bi: true.
        """
        target_config = pipeline.target_config or {}

        # Only sync if explicitly enabled
        if not target_config.get("sync_to_bi", False):
            return None

        # Only sync table targets
        if pipeline.target_type != "table":
            return None

        table_name = target_config.get("table_name")
        schema = target_config.get("schema", "public")

        if not table_name:
            return None

        try:
            from app.services.bi_service import BIService

            bi_service = BIService(self.db)
            result = await bi_service.sync_table_to_superset(
                table_name=table_name,
                schema=schema,
            )

            return {
                "synced": result.get("success", False),
                "dataset_id": result.get("dataset_id"),
                "superset_url": result.get("superset_url"),
                "error": result.get("error"),
            }

        except Exception as e:
            return {
                "synced": False,
                "error": str(e),
            }

    async def _auto_catalog_asset(
        self,
        pipeline: ETLPipeline,
        df: pd.DataFrame,
    ) -> dict[str, Any] | None:
        """Auto-catalog data asset after ETL execution.

        Creates or updates a DataAsset with:
        - Extracted data attributes (row count, columns, quality)
        - AI-generated description and tags
        - Automatic value score evaluation

        Args:
            pipeline: The ETL pipeline that was executed
            df: The output DataFrame

        Returns:
            Catalog result or None if target is not a table
        """
        if pipeline.target_type != "table":
            return None

        target_config = pipeline.target_config or {}
        target_table = target_config.get("table_name")
        target_schema = target_config.get("schema", "public")

        if not target_table:
            return None

        source_table = None
        if pipeline.source_type == "table":
            source_table = pipeline.source_config.get("table_name")

        try:
            from app.services.asset_service import AssetService

            asset_service = AssetService(self.db)
            result = await asset_service.auto_catalog_from_etl(
                pipeline_id=pipeline.id,
                pipeline_name=pipeline.name,
                target_table=target_table,
                target_schema=target_schema,
                df=df,
                source_table=source_table,
            )

            return result

        except Exception as e:
            return {
                "cataloged": False,
                "error": str(e),
            }
