from __future__ import annotations

import json
import uuid
from typing import Any

import pandas as pd
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.core.config import settings
from app.core.observability import LifecycleTracker
from app.core.security import SQLSecurityValidator
from app.models import DataSource, MetadataColumn, MetadataTable, DataAsset


class AIService:
    """Service for AI-powered features using OpenAI."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    @LifecycleTracker(name="AI.analyze_field_meanings", log_result=False)
    async def analyze_field_meanings(
        self,
        source_id: uuid.UUID,
        table_name: str,
    ) -> dict[str, Any]:
        """Analyze column meanings using AI."""
        result = await self.db.execute(
            select(MetadataTable).where(
                MetadataTable.source_id == source_id,
                MetadataTable.table_name == table_name,
            )
        )
        table = result.scalar_one_or_none()

        if not table:
            raise ValueError(f"Table not found: {table_name}")

        columns_result = await self.db.execute(
            select(MetadataColumn).where(MetadataColumn.table_id == table.id)
        )
        columns = list(columns_result.scalars())

        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)
        sample_data = await connector.read_data(table_name=table_name, limit=5)

        columns_info = [
            {
                "name": col.column_name,
                "type": col.data_type,
                "nullable": col.nullable,
                "is_pk": col.is_primary_key,
                "sample_values": sample_data[col.column_name].head(3).tolist()
                if col.column_name in sample_data.columns
                else [],
            }
            for col in columns
        ]

        prompt = f"""Analyze the following database table columns and provide:
1. A description of what each column likely represents
2. A data category (e.g., PII, Financial, Temporal, Geographic, Identifier, Measurement, etc.)
3. Suggested tags for categorization

Table: {table_name}
Columns:
{json.dumps(columns_info, indent=2, default=str)}

Respond in JSON format:
{{
  "columns": [
    {{
      "name": "column_name",
      "meaning": "Description of the column",
      "category": "Data category",
      "tags": ["tag1", "tag2"]
    }}
  ],
  "table_summary": "Brief description of what this table represents"
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data analyst expert. Analyze database schemas and provide meaningful descriptions.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        analysis = json.loads(response.choices[0].message.content or "{}")

        for col_analysis in analysis.get("columns", []):
            col_name = col_analysis.get("name")
            matching_col = next((c for c in columns if c.column_name == col_name), None)

            if matching_col:
                matching_col.ai_inferred_meaning = col_analysis.get("meaning")
                matching_col.ai_data_category = col_analysis.get("category")
                matching_col.tags = list(set(matching_col.tags or []) | set(col_analysis.get("tags", [])))

        table.ai_description = analysis.get("table_summary")
        await self.db.commit()

        return {
            "table_id": table.id,
            "columns_analyzed": len(columns),
            "results": analysis.get("columns", []),
        }

    @LifecycleTracker(name="AI.suggest_cleaning_rules")
    async def suggest_cleaning_rules(
        self,
        source_id: uuid.UUID,
        table_name: str,
        sample_size: int = 1000,
    ) -> dict[str, Any]:
        """Suggest data cleaning rules based on data quality analysis."""
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)
        df = await connector.read_data(table_name=table_name, limit=sample_size)

        quality_stats = self._analyze_data_quality(df)

        prompt = f"""Analyze this data quality report and suggest ETL cleaning rules.

Data Quality Report for table '{table_name}':
{json.dumps(quality_stats, indent=2, default=str)}

Available ETL step types:
- filter: Filter rows based on conditions
- deduplicate: Remove duplicate rows
- map_values: Map/replace values
- fill_missing: Fill missing values
- mask: Mask sensitive data
- type_cast: Convert data types
- rename: Rename columns

Suggest cleaning rules in JSON format:
{{
  "suggestions": [
    {{
      "step_type": "step_type_name",
      "config": {{ config object }},
      "reason": "Why this rule is suggested",
      "confidence": 0.95
    }}
  ],
  "data_quality_summary": {{
    "overall_score": 0-100,
    "critical_issues": ["issue1", "issue2"],
    "recommendations": ["recommendation1"]
  }}
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data quality expert. Analyze data and suggest cleaning rules.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content or "{}")

    def _analyze_data_quality(self, df: pd.DataFrame) -> dict[str, Any]:
        """Analyze data quality metrics."""
        stats: dict[str, Any] = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": {},
        }

        for col in df.columns:
            col_stats: dict[str, Any] = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isnull().sum()),
                "null_percentage": round(df[col].isnull().sum() / len(df) * 100, 2),
                "unique_count": int(df[col].nunique()),
                "unique_percentage": round(df[col].nunique() / len(df) * 100, 2),
            }

            if df[col].dtype in ["int64", "float64"]:
                col_stats["min"] = float(df[col].min()) if not df[col].isnull().all() else None
                col_stats["max"] = float(df[col].max()) if not df[col].isnull().all() else None
                col_stats["mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
                col_stats["std"] = float(df[col].std()) if not df[col].isnull().all() else None

            if df[col].dtype == "object":
                value_counts = df[col].value_counts().head(5)
                col_stats["top_values"] = value_counts.to_dict()
                col_stats["avg_length"] = df[col].astype(str).str.len().mean()

            stats["columns"][col] = col_stats

        duplicate_count = len(df) - len(df.drop_duplicates())
        stats["duplicate_rows"] = duplicate_count
        stats["duplicate_percentage"] = round(duplicate_count / len(df) * 100, 2)

        return stats

    @LifecycleTracker(name="AI.natural_language_to_sql", log_result=False)
    async def natural_language_to_sql(
        self,
        query: str,
        context_tables: list[str] | None = None,
    ) -> dict[str, Any]:
        """Convert natural language query to SQL."""
        tables_result = await self.db.execute(select(MetadataTable))
        all_tables = list(tables_result.scalars())

        if context_tables:
            tables = [t for t in all_tables if t.table_name in context_tables]
        else:
            tables = all_tables[:10]

        schema_info = []
        for table in tables:
            columns_result = await self.db.execute(
                select(MetadataColumn).where(MetadataColumn.table_id == table.id)
            )
            columns = list(columns_result.scalars())

            schema_info.append({
                "table": table.table_name,
                "schema": table.schema_name,
                "description": table.ai_description or table.description,
                "columns": [
                    {
                        "name": col.column_name,
                        "type": col.data_type,
                        "meaning": col.ai_inferred_meaning or col.description,
                    }
                    for col in columns
                ],
            })

        prompt = f"""Convert the following natural language query to SQL.

Available tables and their schemas:
{json.dumps(schema_info, indent=2)}

User query: "{query}"

Respond in JSON format:
{{
  "sql": "SELECT ...",
  "explanation": "Brief explanation of what this query does",
  "visualization_suggestion": {{
    "chart_type": "bar|line|pie|table|scatter",
    "x_axis": "column_name",
    "y_axis": "column_name",
    "group_by": "optional_column"
  }}
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a SQL expert. Convert natural language to accurate SQL queries.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content or "{}")

        sql = result.get("sql", "")
        if sql:
            # Validate SQL for security before execution
            is_safe, violations = SQLSecurityValidator.validate(sql)

            if not is_safe:
                result["security_error"] = True
                result["security_violations"] = violations
                result["error"] = f"SQL query blocked for security: {', '.join(violations)}"
                return result

            # Sanitize the SQL
            sql = SQLSecurityValidator.sanitize(sql)
            result["sql"] = sql

            source_result = await self.db.execute(select(DataSource).limit(1))
            source = source_result.scalar_one_or_none()

            if source:
                connector = get_connector(source.type, source.connection_config)
                try:
                    data = await connector.execute_query(sql)
                    result["data"] = data[:100]
                    result["row_count"] = len(data)
                except Exception as e:
                    result["error"] = str(e)

        return result

    async def predict_missing_values(
        self,
        source_id: uuid.UUID,
        table_name: str,
        target_column: str,
        feature_columns: list[str],
    ) -> dict[str, Any]:
        """Use AI to predict missing values."""
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)
        df = await connector.read_data(table_name=table_name)

        missing_mask = df[target_column].isnull()
        if not missing_mask.any():
            return {
                "model_type": "none",
                "accuracy": None,
                "filled_count": 0,
                "message": "No missing values found",
            }

        complete_data = df[~missing_mask]
        missing_data = df[missing_mask]

        sample_complete = complete_data[feature_columns + [target_column]].head(50).to_dict(orient="records")
        sample_missing = missing_data[feature_columns].head(10).to_dict(orient="records")

        prompt = f"""Given the following complete data samples, predict the missing values.

Complete data with target column '{target_column}':
{json.dumps(sample_complete, indent=2, default=str)}

Data with missing '{target_column}' to predict:
{json.dumps(sample_missing, indent=2, default=str)}

Respond in JSON format:
{{
  "predictions": [
    {{"index": 0, "predicted_value": "value"}},
    ...
  ],
  "model_type": "pattern_matching|regression|classification",
  "confidence": 0.85
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data scientist. Predict missing values based on patterns in the data.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content or "{}")

        return {
            "model_type": result.get("model_type", "ai_prediction"),
            "accuracy": result.get("confidence"),
            "filled_count": len(result.get("predictions", [])),
            "preview": result.get("predictions", [])[:10],
        }

    @LifecycleTracker(name="AI.search_assets")
    async def search_assets(
        self,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search data assets using AI-powered semantic matching.

        Supports natural language queries like:
        - "近30天活跃用户数据"
        - "customer purchase history"
        - "sales metrics by region"
        """
        assets_result = await self.db.execute(
            select(DataAsset).where(DataAsset.is_active.is_(True))
        )
        all_assets = list(assets_result.scalars())

        if not all_assets:
            return {
                "results": [],
                "total": 0,
                "ai_summary": "暂无可搜索的数据资产",
            }

        assets_info = [
            {
                "id": str(asset.id),
                "name": asset.name,
                "description": asset.description,
                "ai_summary": asset.ai_summary,
                "domain": asset.domain,
                "category": asset.category,
                "tags": asset.tags,
                "asset_type": asset.asset_type.value,
                "usage_count": asset.usage_count,
            }
            for asset in all_assets
        ]

        prompt = f"""You are a data asset search engine. Find assets that match the user's query.

User Query: "{query}"

Available Data Assets:
{json.dumps(assets_info, indent=2, ensure_ascii=False)}

Analyze the query and return matching assets ranked by relevance.
Consider:
1. Semantic meaning (not just keyword matching)
2. Domain/category relevance
3. Description and AI summary content
4. Tags and usage patterns

Respond in JSON format:
{{
  "matches": [
    {{
      "id": "asset_id",
      "relevance_score": 0.95,
      "match_reason": "Brief explanation of why this matches"
    }}
  ],
  "search_summary": "Brief summary of what was found",
  "suggested_queries": ["related query 1", "related query 2"]
}}

Return at most {limit} matches, ordered by relevance_score descending."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a semantic search engine for data assets. Match user queries to relevant data assets based on meaning, not just keywords.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content or "{}")
        matches = result.get("matches", [])

        # Extract matched IDs for reference
        _ = [m["id"] for m in matches]
        matched_assets = [
            {
                **next((a for a in assets_info if a["id"] == m["id"]), {}),
                "relevance_score": m.get("relevance_score", 0),
                "match_reason": m.get("match_reason", ""),
            }
            for m in matches
            if any(a["id"] == m["id"] for a in assets_info)
        ]

        return {
            "results": matched_assets,
            "total": len(matched_assets),
            "ai_summary": result.get("search_summary", f"Found {len(matched_assets)} matching assets"),
            "suggested_queries": result.get("suggested_queries", []),
        }

    async def detect_sensitive_fields(
        self,
        source_id: uuid.UUID,
        table_name: str,
    ) -> dict[str, Any]:
        """Detect potentially sensitive fields using AI.

        Returns field sensitivity classification and recommended masking strategies.
        """
        result = await self.db.execute(
            select(MetadataTable).where(
                MetadataTable.source_id == source_id,
                MetadataTable.table_name == table_name,
            )
        )
        table = result.scalar_one_or_none()

        if not table:
            raise ValueError(f"Table not found: {table_name}")

        columns_result = await self.db.execute(
            select(MetadataColumn).where(MetadataColumn.table_id == table.id)
        )
        columns = list(columns_result.scalars())

        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)
        sample_data = await connector.read_data(table_name=table_name, limit=10)

        columns_info = [
            {
                "name": col.column_name,
                "type": col.data_type,
                "sample_values": sample_data[col.column_name].head(5).tolist()
                if col.column_name in sample_data.columns
                else [],
            }
            for col in columns
        ]

        prompt = f"""Analyze the following database columns and identify sensitive data.

Table: {table_name}
Columns:
{json.dumps(columns_info, indent=2, default=str)}

For each column, determine:
1. Sensitivity level: none, low, medium, high, critical
2. Data type: PII (personally identifiable), PHI (health), PCI (payment), credentials, business_sensitive, none
3. Recommended masking strategy: none, partial_mask, hash, encrypt, tokenize, redact

Respond in JSON format:
{{
  "columns": [
    {{
      "name": "column_name",
      "sensitivity_level": "high",
      "data_type": "PII",
      "masking_strategy": "partial_mask",
      "masking_config": {{"start": 3, "end": 4}},
      "reason": "Contains email addresses"
    }}
  ],
  "overall_risk": "medium",
  "compliance_notes": ["GDPR relevant", "Consider encryption at rest"]
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data security expert. Identify sensitive data and recommend protection strategies.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content or "{}")

    async def predict_time_series(
        self,
        data: list[dict],
        date_column: str,
        value_column: str,
        periods: int = 7,
    ) -> dict[str, Any]:
        """Predict future values using AI time series analysis.

        Args:
            data: Historical data points
            date_column: Name of date/time column
            value_column: Name of value column to predict
            periods: Number of future periods to predict
        """
        if len(data) < 5:
            return {
                "error": "Insufficient data for prediction",
                "min_required": 5,
                "provided": len(data),
            }

        prompt = f"""Analyze this time series data and predict the next {periods} values.

Historical Data (date, value):
{json.dumps(data[-30:], indent=2, default=str)}

Date column: {date_column}
Value column: {value_column}

Analyze trends, seasonality, and patterns. Then predict the next {periods} periods.

Respond in JSON format:
{{
  "predictions": [
    {{"date": "YYYY-MM-DD", "value": 123.45, "confidence": 0.85}}
  ],
  "trend": "increasing|decreasing|stable",
  "seasonality": "daily|weekly|monthly|none",
  "analysis": "Brief explanation of patterns observed",
  "confidence_overall": 0.75
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a time series analyst. Predict future values based on historical patterns.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        return json.loads(response.choices[0].message.content or "{}")

    async def cluster_analysis(
        self,
        data: list[dict],
        features: list[str],
        n_clusters: int = 3,
    ) -> dict[str, Any]:
        """Perform clustering analysis using scikit-learn K-Means.

        Args:
            data: Data points to cluster
            features: Feature columns to use for clustering
            n_clusters: Number of clusters (default 3)
        """
        if len(data) < n_clusters:
            return {
                "error": "Insufficient data for clustering",
                "min_required": n_clusters,
                "provided": len(data),
            }

        df = pd.DataFrame(data)

        available_features = [f for f in features if f in df.columns]
        if not available_features:
            return {
                "error": "No valid features found",
                "requested": features,
                "available": list(df.columns),
            }

        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler

        feature_data = df[available_features].copy()

        for col in available_features:
            if feature_data[col].dtype == 'object':
                feature_data[col] = pd.factorize(feature_data[col])[0]

        feature_data = feature_data.fillna(feature_data.mean())

        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(feature_data)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(scaled_data)

        df['cluster'] = clusters

        cluster_stats = []
        for i in range(n_clusters):
            cluster_data = df[df['cluster'] == i]
            stats = {
                "cluster_id": i,
                "size": len(cluster_data),
                "percentage": round(len(cluster_data) / len(df) * 100, 2),
                "feature_means": {},
            }

            for feat in available_features:
                if cluster_data[feat].dtype in ['int64', 'float64']:
                    stats["feature_means"][feat] = round(float(cluster_data[feat].mean()), 2)

            cluster_stats.append(stats)

        prompt = f"""Analyze these clustering results and provide insights.

Cluster Statistics:
{json.dumps(cluster_stats, indent=2)}

Features used: {available_features}
Total data points: {len(df)}

Provide meaningful names and descriptions for each cluster.

Respond in JSON format:
{{
  "cluster_insights": [
    {{
      "cluster_id": 0,
      "name": "Descriptive name",
      "description": "What this cluster represents",
      "key_characteristics": ["trait1", "trait2"]
    }}
  ],
  "summary": "Overall clustering summary",
  "recommendations": ["Action item 1", "Action item 2"]
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data scientist. Analyze clustering results and provide business insights.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        ai_analysis = json.loads(response.choices[0].message.content or "{}")

        for i, insight in enumerate(ai_analysis.get("cluster_insights", [])):
            if i < len(cluster_stats):
                cluster_stats[i].update(insight)

        return {
            "clusters": cluster_stats,
            "n_clusters": n_clusters,
            "features_used": available_features,
            "total_samples": len(df),
            "summary": ai_analysis.get("summary", ""),
            "recommendations": ai_analysis.get("recommendations", []),
            "data_with_clusters": df.to_dict(orient="records"),
        }

    async def summarize_anomalies(
        self,
        anomaly_results: dict[str, Any],
    ) -> str:
        """Generate AI summary for anomaly detection results.

        Args:
            anomaly_results: Results from detect_anomalies_with_ai.

        Returns:
            AI-generated summary of anomalies found.
        """
        findings = anomaly_results.get("findings", [])

        if not findings:
            return "No anomalies detected in the analyzed columns."

        prompt = f"""Summarize the following anomaly detection results for a business user.

Anomaly Detection Results:
{json.dumps(findings, indent=2)}

Provide a concise summary that:
1. Highlights columns with significant anomalies
2. Explains what the anomalies might indicate
3. Suggests potential actions

Keep the summary to 2-3 sentences."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data analyst. Summarize anomaly findings clearly for business stakeholders.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        return response.choices[0].message.content or "Unable to generate summary."

    async def validate_sql_query(
        self,
        sql: str,
        execute: bool = False,
    ) -> dict[str, Any]:
        """Validate and optionally execute a SQL query.

        Args:
            sql: SQL query to validate.
            execute: Whether to execute the query if valid.

        Returns:
            Validation results and optional query results.
        """
        is_safe, violations = SQLSecurityValidator.validate(sql)

        result = {
            "sql": sql,
            "is_safe": is_safe,
            "violations": violations,
        }

        if not is_safe:
            result["error"] = f"SQL blocked: {', '.join(violations)}"
            return result

        if execute:
            sanitized_sql = SQLSecurityValidator.sanitize(sql)
            result["sanitized_sql"] = sanitized_sql

            source_result = await self.db.execute(select(DataSource).limit(1))
            source = source_result.scalar_one_or_none()

            if source:
                connector = get_connector(source.type, source.connection_config)
                try:
                    data = await connector.execute_query(sanitized_sql)
                    result["data"] = data[:100]
                    result["row_count"] = len(data)
                    result["executed"] = True
                except Exception as e:
                    result["error"] = str(e)
                    result["executed"] = False
            else:
                result["error"] = "No data source available"
                result["executed"] = False

        return result

    async def discover_cross_source_relations(
        self,
        source_ids: list[uuid.UUID] | None = None,
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """Discover potential cross-data source relationships.

        Analyzes column names, types, and sample data across multiple data sources
        to identify potential join relationships and foreign key references.

        Args:
            source_ids: Optional list of source IDs to analyze. If None, analyzes all.
            confidence_threshold: Minimum confidence score to include (0.0 to 1.0).

        Returns:
            Dictionary containing discovered relations and suggestions.
        """
        from difflib import SequenceMatcher

        if source_ids:
            sources_result = await self.db.execute(
                select(DataSource).where(DataSource.id.in_(source_ids))
            )
        else:
            sources_result = await self.db.execute(select(DataSource))

        sources = list(sources_result.scalars())

        if len(sources) < 1:
            return {
                "relations": [],
                "summary": "No data sources available for analysis",
                "sources_analyzed": 0,
            }

        all_columns: list[dict[str, Any]] = []

        for source in sources:
            tables_result = await self.db.execute(
                select(MetadataTable).where(MetadataTable.source_id == source.id)
            )
            tables = list(tables_result.scalars())

            for table in tables:
                columns_result = await self.db.execute(
                    select(MetadataColumn).where(MetadataColumn.table_id == table.id)
                )
                columns = list(columns_result.scalars())

                for col in columns:
                    all_columns.append({
                        "source_id": str(source.id),
                        "source_name": source.name,
                        "table_id": str(table.id),
                        "table_name": table.table_name,
                        "schema_name": table.schema_name,
                        "column_id": str(col.id),
                        "column_name": col.column_name,
                        "data_type": col.data_type,
                        "is_primary_key": col.is_primary_key,
                        "is_foreign_key": col.is_foreign_key,
                        "ai_category": col.ai_data_category,
                        "ai_meaning": col.ai_inferred_meaning,
                    })

        if len(all_columns) < 2:
            return {
                "relations": [],
                "summary": "Not enough columns to analyze",
                "sources_analyzed": len(sources),
            }

        potential_relations = []

        for i, col_a in enumerate(all_columns):
            for col_b in all_columns[i + 1:]:
                if col_a["source_id"] == col_b["source_id"] and col_a["table_id"] == col_b["table_id"]:
                    continue

                name_a = col_a["column_name"].lower()
                name_b = col_b["column_name"].lower()

                name_similarity = SequenceMatcher(None, name_a, name_b).ratio()

                normalized_a = self._normalize_column_name(name_a)
                normalized_b = self._normalize_column_name(name_b)
                normalized_similarity = SequenceMatcher(None, normalized_a, normalized_b).ratio()

                type_match = self._types_compatible(col_a["data_type"], col_b["data_type"])

                pk_fk_match = (
                    (col_a["is_primary_key"] and "id" in name_b) or
                    (col_b["is_primary_key"] and "id" in name_a) or
                    (col_a["is_foreign_key"] or col_b["is_foreign_key"])
                )

                category_match = (
                    col_a["ai_category"] and col_b["ai_category"] and
                    col_a["ai_category"] == col_b["ai_category"]
                )

                confidence = self._calculate_relation_confidence(
                    name_similarity=name_similarity,
                    normalized_similarity=normalized_similarity,
                    type_match=type_match,
                    pk_fk_match=pk_fk_match,
                    category_match=category_match,
                )

                if confidence >= confidence_threshold:
                    potential_relations.append({
                        "column_a": col_a,
                        "column_b": col_b,
                        "confidence": round(confidence, 3),
                        "name_similarity": round(max(name_similarity, normalized_similarity), 3),
                        "type_compatible": type_match,
                        "pk_fk_indicator": pk_fk_match,
                        "category_match": category_match,
                    })

        potential_relations.sort(key=lambda x: x["confidence"], reverse=True)
        top_relations = potential_relations[:20]

        if top_relations:
            ai_analysis = await self._analyze_relations_with_ai(top_relations)
        else:
            ai_analysis = {
                "enhanced_relations": [],
                "summary": "No potential cross-source relations found",
                "recommendations": [],
            }

        final_relations = []
        for rel in ai_analysis.get("enhanced_relations", []):
            if rel.get("final_confidence", rel.get("confidence", 0)) >= confidence_threshold:
                final_relations.append({
                    "source_column": {
                        "source_id": rel["column_a"]["source_id"],
                        "source_name": rel["column_a"]["source_name"],
                        "table_name": rel["column_a"]["table_name"],
                        "column_name": rel["column_a"]["column_name"],
                    },
                    "target_column": {
                        "source_id": rel["column_b"]["source_id"],
                        "source_name": rel["column_b"]["source_name"],
                        "table_name": rel["column_b"]["table_name"],
                        "column_name": rel["column_b"]["column_name"],
                    },
                    "confidence": rel.get("final_confidence", rel.get("confidence")),
                    "relation_type": rel.get("relation_type", "potential_join"),
                    "reason": rel.get("reason", "Column name and type similarity"),
                })

        return {
            "relations": final_relations,
            "summary": ai_analysis.get("summary", f"Found {len(final_relations)} potential relations"),
            "recommendations": ai_analysis.get("recommendations", []),
            "sources_analyzed": len(sources),
            "columns_analyzed": len(all_columns),
        }

    def _normalize_column_name(self, name: str) -> str:
        """Normalize column name for comparison."""
        import re
        name = re.sub(r"[_\-\s]", "", name.lower())
        name = re.sub(r"(id|key|fk|pk)$", "", name)
        name = re.sub(r"^(fk_|pk_|id_)", "", name)
        return name

    def _types_compatible(self, type_a: str, type_b: str) -> bool:
        """Check if two data types are compatible for join."""
        type_a = type_a.lower() if type_a else ""
        type_b = type_b.lower() if type_b else ""

        int_types = {"int", "integer", "bigint", "smallint", "serial", "bigserial"}
        str_types = {"varchar", "text", "char", "string", "character varying"}
        uuid_types = {"uuid", "guid"}

        def get_type_group(t: str) -> str:
            t_lower = t.split("(")[0].strip()
            if t_lower in int_types or "int" in t_lower:
                return "integer"
            if t_lower in str_types or "char" in t_lower or "text" in t_lower:
                return "string"
            if t_lower in uuid_types:
                return "uuid"
            return t_lower

        return get_type_group(type_a) == get_type_group(type_b)

    def _calculate_relation_confidence(
        self,
        name_similarity: float,
        normalized_similarity: float,
        type_match: bool,
        pk_fk_match: bool,
        category_match: bool,
    ) -> float:
        """Calculate overall confidence score for a potential relation."""
        score = 0.0

        best_name_similarity = max(name_similarity, normalized_similarity)
        score += best_name_similarity * 0.4

        if type_match:
            score += 0.25

        if pk_fk_match:
            score += 0.2

        if category_match:
            score += 0.15

        return min(score, 1.0)

    async def _analyze_relations_with_ai(
        self,
        relations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Use AI to analyze and enhance relation suggestions."""
        relations_for_ai = [
            {
                "column_a": {
                    "table": f"{r['column_a']['source_name']}.{r['column_a']['table_name']}",
                    "column": r["column_a"]["column_name"],
                    "type": r["column_a"]["data_type"],
                    "is_pk": r["column_a"]["is_primary_key"],
                },
                "column_b": {
                    "table": f"{r['column_b']['source_name']}.{r['column_b']['table_name']}",
                    "column": r["column_b"]["column_name"],
                    "type": r["column_b"]["data_type"],
                    "is_pk": r["column_b"]["is_primary_key"],
                },
                "initial_confidence": r["confidence"],
            }
            for r in relations
        ]

        prompt = f"""Analyze these potential cross-data source relationships.

Potential Relations:
{json.dumps(relations_for_ai, indent=2)}

For each relation, determine:
1. Whether it's likely a valid join relationship
2. The type of relationship (foreign_key, join_key, semantic_link, coincidental)
3. A confidence adjustment based on semantic analysis
4. A brief reason for your assessment

Respond in JSON format:
{{
  "enhanced_relations": [
    {{
      "index": 0,
      "is_valid": true,
      "relation_type": "foreign_key",
      "confidence_adjustment": 0.1,
      "reason": "user_id typically references users table primary key"
    }}
  ],
  "summary": "Brief summary of findings",
  "recommendations": ["recommendation 1", "recommendation 2"]
}}"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a database architect expert. Analyze potential cross-database relationships and assess their validity.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            ai_result = json.loads(response.choices[0].message.content or "{}")

            enhanced_relations = []
            for enhancement in ai_result.get("enhanced_relations", []):
                idx = enhancement.get("index", 0)
                if idx < len(relations):
                    rel = relations[idx].copy()
                    adjustment = enhancement.get("confidence_adjustment", 0)
                    rel["final_confidence"] = min(1.0, max(0, rel["confidence"] + adjustment))
                    rel["relation_type"] = enhancement.get("relation_type", "potential_join")
                    rel["reason"] = enhancement.get("reason", "")
                    rel["is_valid"] = enhancement.get("is_valid", True)

                    if rel["is_valid"]:
                        enhanced_relations.append(rel)

            return {
                "enhanced_relations": enhanced_relations,
                "summary": ai_result.get("summary", ""),
                "recommendations": ai_result.get("recommendations", []),
            }

        except Exception as e:
            return {
                "enhanced_relations": relations,
                "summary": f"AI analysis unavailable: {e}",
                "recommendations": [],
            }

    async def predict_time_series_enhanced(
        self,
        data: list[dict],
        date_column: str,
        value_column: str,
        periods: int = 7,
        method: str = "auto",
    ) -> dict[str, Any]:
        """Predict future values using statistical time series forecasting.

        Uses real ML/statistical methods instead of AI generation for more accuracy.

        Args:
            data: Historical data points
            date_column: Name of date/time column
            value_column: Name of value column to predict
            periods: Number of future periods to predict
            method: Forecasting method (auto, moving_average, exponential_smooth, trend)
        """
        from app.services.ml_utils import TimeSeriesForecaster

        forecaster = TimeSeriesForecaster()
        result = forecaster.forecast(
            data=data,
            date_column=date_column,
            value_column=value_column,
            periods=periods,
            method=method,
        )

        return result

    async def detect_anomalies(
        self,
        data: list[dict],
        features: list[str],
        method: str = "isolation_forest",
        contamination: float = 0.1,
    ) -> dict[str, Any]:
        """Detect anomalies in data using ML algorithms.

        Args:
            data: Data points to analyze
            features: Feature columns to use for detection
            method: Detection method (isolation_forest, statistical)
            contamination: Expected proportion of outliers

        Returns:
            Anomaly detection results with flagged anomalies
        """
        from app.services.ml_utils import AnomalyDetector

        detector = AnomalyDetector(contamination=contamination)
        result = detector.detect(
            data=data,
            features=features,
            method=method,
        )

        return result

    async def cluster_analysis_enhanced(
        self,
        data: list[dict],
        features: list[str],
        algorithm: str = "kmeans",
        n_clusters: int = 3,
        **kwargs,
    ) -> dict[str, Any]:
        """Perform clustering analysis using ML algorithms.

        Args:
            data: Data points to cluster
            features: Feature columns to use
            algorithm: Clustering algorithm (kmeans, dbscan)
            n_clusters: Number of clusters (for KMeans)
            **kwargs: Additional algorithm parameters

        Returns:
            Clustering results with assignments and statistics
        """
        from app.services.ml_utils import EnhancedClustering

        clusterer = EnhancedClustering()
        result = clusterer.cluster(
            data=data,
            features=features,
            algorithm=algorithm,
            n_clusters=n_clusters,
            **kwargs,
        )

        return result
