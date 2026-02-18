"""Data standard service with AI-powered suggestions and compliance checking."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.standard import (
    ComplianceResult,
    DataStandard,
    StandardApplication,
    StandardStatus,
    StandardType,
)


class StandardService:
    """Service for data standard management, AI suggestions, and compliance checking."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def suggest_standards(
        self,
        source_id: uuid.UUID,
        table_name: str,
        sample_data: pd.DataFrame,
    ) -> dict[str, Any]:
        """Use AI to suggest data standards for a table's columns.

        Args:
            source_id: Data source ID
            table_name: Name of the table to analyze
            sample_data: Sample data from the table

        Returns:
            Suggested standards for each column
        """
        columns_info = []
        for col in sample_data.columns:
            col_info: dict[str, Any] = {
                "name": col,
                "dtype": str(sample_data[col].dtype),
                "sample_values": sample_data[col].dropna().head(10).tolist(),
                "null_count": int(sample_data[col].isnull().sum()),
                "unique_count": int(sample_data[col].nunique()),
            }

            if sample_data[col].dtype == "object":
                lengths = sample_data[col].astype(str).str.len()
                col_info["min_length"] = int(lengths.min())
                col_info["max_length"] = int(lengths.max())
                col_info["avg_length"] = round(float(lengths.mean()), 1)

            columns_info.append(col_info)

        prompt = f"""Analyze this table and suggest data standards for each column.

Table: {table_name}
Columns:
{json.dumps(columns_info, indent=2, default=str)}

For each column, suggest applicable data standards:

1. FIELD_FORMAT: Pattern/format specification (regex, date format, etc.)
2. ENCODING_RULE: Character encoding and allowed characters
3. NAMING_CONVENTION: Column naming rules
4. VALUE_DOMAIN: Allowed values or ranges
5. DATA_QUALITY: Completeness, uniqueness requirements

Respond in JSON format:
{{
  "columns": [
    {{
      "column_name": "column_name",
      "suggested_standards": [
        {{
          "type": "field_format|encoding_rule|naming_convention|value_domain|data_quality",
          "name": "Standard name",
          "code": "UNIQUE_CODE",
          "description": "What this standard enforces",
          "rules": {{
            "pattern": "regex pattern if applicable",
            "format": "date|email|phone|uuid|etc",
            "allowed_values": ["list", "if", "applicable"],
            "range": {{"min": 0, "max": 100}},
            "completeness": 0.95,
            "not_null": true
          }},
          "confidence": 0.85
        }}
      ],
      "detected_type": "email|phone|date|currency|id|name|etc",
      "notes": "Any special observations"
    }}
  ],
  "table_standards": [
    {{
      "type": "naming_convention",
      "name": "Table naming standard",
      "code": "TBL_NAMING_001",
      "rules": {{}},
      "confidence": 0.9
    }}
  ]
}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a data governance expert. Analyze data and suggest appropriate data standards based on patterns, data types, and best practices.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content or "{}")

        return {
            "source_id": str(source_id),
            "table_name": table_name,
            "columns_analyzed": len(columns_info),
            "suggestions": result,
        }

    async def create_standard_from_suggestion(
        self,
        suggestion: dict[str, Any],
        owner_id: uuid.UUID | None = None,
    ) -> DataStandard:
        """Create a data standard from an AI suggestion.

        Args:
            suggestion: AI-generated standard suggestion
            owner_id: Optional owner ID

        Returns:
            Created DataStandard
        """
        type_mapping = {
            "field_format": StandardType.FIELD_FORMAT,
            "encoding_rule": StandardType.ENCODING_RULE,
            "naming_convention": StandardType.NAMING_CONVENTION,
            "value_domain": StandardType.VALUE_DOMAIN,
            "data_quality": StandardType.DATA_QUALITY,
        }

        standard = DataStandard(
            name=suggestion.get("name", "Untitled Standard"),
            code=suggestion.get("code", f"STD_{uuid.uuid4().hex[:8].upper()}"),
            description=suggestion.get("description"),
            standard_type=type_mapping.get(
                suggestion.get("type", "field_format"),
                StandardType.FIELD_FORMAT,
            ),
            status=StandardStatus.DRAFT,
            rules=suggestion.get("rules", {}),
            ai_suggested=True,
            ai_confidence=suggestion.get("confidence"),
            owner_id=owner_id,
        )

        self.db.add(standard)
        await self.db.commit()
        await self.db.refresh(standard)

        return standard

    async def check_compliance(
        self,
        standard_id: uuid.UUID,
        data: pd.DataFrame,
        column_name: str | None = None,
        source_id: uuid.UUID | None = None,
        table_name: str | None = None,
    ) -> ComplianceResult:
        """Check data compliance against a standard.

        Args:
            standard_id: Standard ID to check against
            data: DataFrame to check
            column_name: Optional column to check
            source_id: Optional source ID for recording
            table_name: Optional table name for recording

        Returns:
            ComplianceResult with check details
        """
        start_time = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(DataStandard).where(DataStandard.id == standard_id)
        )
        standard = result.scalar_one_or_none()

        if not standard:
            raise ValueError(f"Standard not found: {standard_id}")

        if column_name and column_name not in data.columns:
            raise ValueError(f"Column not found: {column_name}")

        check_data = data[column_name] if column_name else data

        violations = []
        compliant_count = 0
        violation_count = 0
        total_records = len(check_data)

        if standard.standard_type == StandardType.FIELD_FORMAT:
            compliant_count, violation_count, violations = self._check_field_format(
                check_data, standard.rules
            )
        elif standard.standard_type == StandardType.VALUE_DOMAIN:
            compliant_count, violation_count, violations = self._check_value_domain(
                check_data, standard.rules
            )
        elif standard.standard_type == StandardType.DATA_QUALITY:
            compliant_count, violation_count, violations = self._check_data_quality(
                check_data, standard.rules
            )
        else:
            compliant_count = total_records
            violation_count = 0

        compliance_score = compliant_count / total_records if total_records > 0 else 1.0
        is_compliant = compliance_score >= 0.95

        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        compliance_result = ComplianceResult(
            standard_id=standard_id,
            source_id=source_id,
            table_name=table_name,
            column_name=column_name,
            is_compliant=is_compliant,
            compliance_score=round(compliance_score, 4),
            total_records=total_records,
            compliant_records=compliant_count,
            violation_records=violation_count,
            violations={
                "sample_violations": violations[:100],
                "violation_types": self._categorize_violations(violations),
            },
            check_duration_ms=duration_ms,
        )

        self.db.add(compliance_result)
        await self.db.commit()
        await self.db.refresh(compliance_result)

        return compliance_result

    def _check_field_format(
        self,
        data: pd.Series | pd.DataFrame,
        rules: dict[str, Any],
    ) -> tuple[int, int, list[dict]]:
        """Check field format compliance."""
        violations = []
        compliant = 0
        violated = 0

        pattern = rules.get("pattern")
        min_length = rules.get("min_length")
        max_length = rules.get("max_length")

        # Handle DataFrame: check first column or flatten all values
        if isinstance(data, pd.DataFrame):
            if len(data.columns) == 0:
                return 0, 0, []
            # Use first column for field format check
            data = data.iloc[:, 0]

        for idx, value in data.items():
            if pd.isna(value):
                if rules.get("allow_null", True):
                    compliant += 1
                else:
                    violations.append({
                        "value": None,
                        "reason": "Null not allowed",
                        "row_index": idx,
                    })
                    violated += 1
                continue

            str_value = str(value)
            is_valid = True
            reasons = []

            if pattern:
                try:
                    if not re.match(pattern, str_value):
                        is_valid = False
                        reasons.append("Pattern mismatch")
                except re.error:
                    pass

            if min_length and len(str_value) < min_length:
                is_valid = False
                reasons.append(f"Length below minimum ({min_length})")

            if max_length and len(str_value) > max_length:
                is_valid = False
                reasons.append(f"Length exceeds maximum ({max_length})")

            if is_valid:
                compliant += 1
            else:
                violations.append({
                    "value": str_value[:50],
                    "reason": "; ".join(reasons),
                    "row_index": idx,
                })
                violated += 1

        return compliant, violated, violations

    def _check_value_domain(
        self,
        data: pd.Series | pd.DataFrame,
        rules: dict[str, Any],
    ) -> tuple[int, int, list[dict]]:
        """Check value domain compliance."""
        violations = []
        compliant = 0
        violated = 0

        allowed_values = rules.get("allowed_values")
        value_range = rules.get("range")

        # Handle DataFrame: check first column
        if isinstance(data, pd.DataFrame):
            if len(data.columns) == 0:
                return 0, 0, []
            data = data.iloc[:, 0]

        for idx, value in data.items():
            if pd.isna(value):
                if rules.get("allow_null", True):
                    compliant += 1
                else:
                    violations.append({
                        "value": None,
                        "reason": "Null not allowed",
                        "row_index": idx,
                    })
                    violated += 1
                continue

            is_valid = True
            reasons = []

            if allowed_values and value not in allowed_values:
                is_valid = False
                reasons.append(f"Value not in allowed list: {allowed_values}")

            if value_range:
                try:
                    num_value = float(value)
                    if "min" in value_range and num_value < value_range["min"]:
                        is_valid = False
                        reasons.append(f"Value below minimum ({value_range['min']})")
                    if "max" in value_range and num_value > value_range["max"]:
                        is_valid = False
                        reasons.append(f"Value exceeds maximum ({value_range['max']})")
                except (ValueError, TypeError):
                    is_valid = False
                    reasons.append("Value not numeric")

            if is_valid:
                compliant += 1
            else:
                violations.append({
                    "value": str(value)[:50],
                    "reason": "; ".join(reasons),
                    "row_index": idx,
                })
                violated += 1

        return compliant, violated, violations

    def _check_data_quality(
        self,
        data: pd.Series | pd.DataFrame,
        rules: dict[str, Any],
    ) -> tuple[int, int, list[dict]]:
        """Check data quality compliance."""
        violations = []

        if isinstance(data, pd.DataFrame):
            series = data.iloc[:, 0] if len(data.columns) > 0 else pd.Series()
        else:
            series = data

        total = len(series)
        null_count = int(series.isnull().sum())
        completeness = (total - null_count) / total if total > 0 else 1.0

        required_completeness = rules.get("completeness", 0.0)
        not_null = rules.get("not_null", False)
        uniqueness = rules.get("uniqueness", False)

        compliant = 0
        violated = 0

        if not_null and null_count > 0:
            violations.append({
                "value": f"{null_count} null values",
                "reason": "Not null constraint violated",
                "row_index": None,
            })
            violated = null_count
            compliant = total - null_count
        elif completeness < required_completeness:
            violations.append({
                "value": f"Completeness: {completeness:.2%}",
                "reason": f"Below required completeness ({required_completeness:.0%})",
                "row_index": None,
            })
            violated = null_count
            compliant = total - null_count
        else:
            compliant = total

        if uniqueness:
            duplicate_count = total - series.nunique()
            if duplicate_count > 0:
                violations.append({
                    "value": f"{duplicate_count} duplicates",
                    "reason": "Uniqueness constraint violated",
                    "row_index": None,
                })
                violated += duplicate_count
                compliant = max(0, compliant - duplicate_count)

        return compliant, violated, violations

    def _categorize_violations(
        self,
        violations: list[dict],
    ) -> dict[str, int]:
        """Categorize violations by type."""
        categories: dict[str, int] = {}

        for v in violations:
            reason = v.get("reason", "unknown")
            key = reason.split(";")[0].strip().lower().replace(" ", "_")
            categories[key] = categories.get(key, 0) + 1

        return categories

    async def apply_standard(
        self,
        standard_id: uuid.UUID,
        target_type: str,
        table_name: str | None = None,
        column_name: str | None = None,
        source_id: uuid.UUID | None = None,
        asset_id: uuid.UUID | None = None,
        is_mandatory: bool = False,
        applied_by: uuid.UUID | None = None,
    ) -> StandardApplication:
        """Apply a standard to a target (table, column, or asset).

        Args:
            standard_id: Standard to apply
            target_type: One of 'table', 'column', 'asset'
            table_name: Table name if applicable
            column_name: Column name if applicable
            source_id: Data source ID if applicable
            asset_id: Asset ID if applicable
            is_mandatory: Whether compliance is mandatory
            applied_by: User who applied the standard

        Returns:
            Created StandardApplication
        """
        result = await self.db.execute(
            select(DataStandard).where(DataStandard.id == standard_id)
        )
        standard = result.scalar_one_or_none()

        if not standard:
            raise ValueError(f"Standard not found: {standard_id}")

        application = StandardApplication(
            standard_id=standard_id,
            target_type=target_type,
            source_id=source_id,
            table_name=table_name,
            column_name=column_name,
            asset_id=asset_id,
            is_mandatory=is_mandatory,
            applied_by=applied_by,
        )

        self.db.add(application)
        await self.db.commit()
        await self.db.refresh(application)

        return application

    async def approve_standard(
        self,
        standard_id: uuid.UUID,
        approved_by: uuid.UUID,
    ) -> DataStandard:
        """Approve a standard and move it from draft/review to approved.

        Args:
            standard_id: Standard to approve
            approved_by: User who approved

        Returns:
            Updated DataStandard
        """
        result = await self.db.execute(
            select(DataStandard).where(DataStandard.id == standard_id)
        )
        standard = result.scalar_one_or_none()

        if not standard:
            raise ValueError(f"Standard not found: {standard_id}")

        if standard.status == StandardStatus.APPROVED:
            raise ValueError("Standard is already approved")

        standard.status = StandardStatus.APPROVED
        standard.approved_at = datetime.now(timezone.utc)
        standard.approved_by = approved_by

        await self.db.commit()
        await self.db.refresh(standard)

        return standard

    async def create_new_version(
        self,
        standard_id: uuid.UUID,
        updated_rules: dict[str, Any],
        owner_id: uuid.UUID | None = None,
    ) -> DataStandard:
        """Create a new version of a standard.

        The existing standard remains unchanged, a new draft version is created.

        Args:
            standard_id: Original standard ID
            updated_rules: New rules for the version
            owner_id: Owner of the new version

        Returns:
            New DataStandard version
        """
        result = await self.db.execute(
            select(DataStandard).where(DataStandard.id == standard_id)
        )
        original = result.scalar_one_or_none()

        if not original:
            raise ValueError(f"Standard not found: {standard_id}")

        new_version = DataStandard(
            name=original.name,
            code=f"{original.code}_v{original.version + 1}",
            description=original.description,
            standard_type=original.standard_type,
            status=StandardStatus.DRAFT,
            rules=updated_rules,
            applicable_domains=original.applicable_domains,
            applicable_data_types=original.applicable_data_types,
            tags=original.tags,
            owner_id=owner_id or original.owner_id,
            department=original.department,
            ai_suggested=False,
            version=original.version + 1,
            previous_version_id=original.id,
        )

        self.db.add(new_version)
        await self.db.commit()
        await self.db.refresh(new_version)

        return new_version

    async def get_standards_by_type(
        self,
        standard_type: StandardType | None = None,
        status: StandardStatus | None = None,
    ) -> list[DataStandard]:
        """Get standards filtered by type and/or status.

        Args:
            standard_type: Optional filter by type
            status: Optional filter by status

        Returns:
            List of matching DataStandard
        """
        query = select(DataStandard)

        if standard_type:
            query = query.where(DataStandard.standard_type == standard_type)

        if status:
            query = query.where(DataStandard.status == status)

        query = query.order_by(DataStandard.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars())

    async def get_compliance_history(
        self,
        standard_id: uuid.UUID | None = None,
        table_name: str | None = None,
        column_name: str | None = None,
        limit: int = 100,
    ) -> list[ComplianceResult]:
        """Get compliance check history.

        Args:
            standard_id: Optional filter by standard
            table_name: Optional filter by table
            column_name: Optional filter by column
            limit: Maximum results to return

        Returns:
            List of ComplianceResult
        """
        query = select(ComplianceResult)

        if standard_id:
            query = query.where(ComplianceResult.standard_id == standard_id)

        if table_name:
            query = query.where(ComplianceResult.table_name == table_name)

        if column_name:
            query = query.where(ComplianceResult.column_name == column_name)

        query = query.order_by(ComplianceResult.checked_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars())
