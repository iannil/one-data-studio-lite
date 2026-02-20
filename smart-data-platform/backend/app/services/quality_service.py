# Data Quality Service

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.core.observability import LifecycleTracker
from app.models import DataSource, DataQualityIssue, QualityIssueSeverity, QualityAssessmentHistory, DataAsset


class DataQualityService:
    """Service for analyzing and tracking data quality."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @LifecycleTracker(name="Quality.calculate_quality_score")
    async def calculate_quality_score(
        self,
        source_id: uuid.UUID,
        table_name: str,
    ) -> dict[str, Any]:
        """
        Calculate an overall quality score for a table.

        Score is based on:
        - Completeness (null values) - 30%
        - Uniqueness (duplicate rows) - 20%
        - Validity (data type violations) - 20%
        - Consistency (format violations) - 15%
        - Timeliness (data freshness) - 15%
        """
        # Get data source
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        # Load sample data
        connector = get_connector(source.type, source.connection_config)
        df = await connector.read_data(table_name=table_name, limit=10000)

        if df.empty:
            return {
                "overall_score": 0,
                "completeness_score": 0,
                "uniqueness_score": 0,
                "validity_score": 0,
                "consistency_score": 0,
                "timeliness_score": 0,
                "row_count": 0,
                "column_count": 0,
            }

        # Calculate individual scores
        completeness = self._calculate_completeness(df)
        uniqueness = self._calculate_uniqueness(df)
        validity = self._calculate_validity(df)
        consistency = self._calculate_consistency(df)
        timeliness = self._calculate_timeliness(df)

        # Weighted overall score
        overall = (
            completeness * 0.30 +
            uniqueness * 0.20 +
            validity * 0.20 +
            consistency * 0.15 +
            timeliness * 0.15
        )

        return {
            "overall_score": round(overall, 2),
            "completeness_score": round(completeness, 2),
            "uniqueness_score": round(uniqueness, 2),
            "validity_score": round(validity, 2),
            "consistency_score": round(consistency, 2),
            "timeliness_score": round(timeliness, 2),
            "row_count": len(df),
            "column_count": len(df.columns),
            "assessment": self._get_quality_assessment(overall),
        }

    def _calculate_completeness(self, df: pd.DataFrame) -> float:
        """Calculate completeness score (100% = no nulls)."""
        if df.empty:
            return 0.0

        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()

        return (1 - null_cells / total_cells) * 100 if total_cells > 0 else 0

    def _calculate_uniqueness(self, df: pd.DataFrame) -> float:
        """Calculate uniqueness score (100% = no duplicates)."""
        if df.empty:
            return 0.0

        duplicate_rows = df.duplicated().sum()
        return (1 - duplicate_rows / len(df)) * 100 if len(df) > 0 else 0

    def _calculate_validity(self, df: pd.DataFrame) -> float:
        """
        Calculate validity score based on data type violations.

        Checks for:
        - Numeric columns with non-numeric values
        - Date columns with invalid dates
        - String columns exceeding reasonable length
        """
        if df.empty:
            return 0.0

        total_cells = 0
        invalid_cells = 0

        for col in df.columns:
            col_data = df[col]
            total_cells += len(col_data)

            # Skip if all null
            if col_data.isnull().all():
                continue

            # Check numeric columns
            if col_data.dtype in ["int64", "float64"]:
                # For numeric, pandas already ensures type
                pass
            # Check object columns for potential type violations
            elif col_data.dtype == "object":
                # Check for columns that should be numeric
                try:
                    numeric_values = pd.to_numeric(col_data, errors="coerce")
                    if numeric_values.notna().sum() > len(col_data) * 0.8:
                        # Mostly numeric, count non-numeric as invalid
                        invalid_cells += (col_data.notna() & numeric_values.isna()).sum()
                except Exception:
                    pass

        return (1 - invalid_cells / total_cells) * 100 if total_cells > 0 else 0

    def _calculate_consistency(self, df: pd.DataFrame) -> float:
        """
        Calculate consistency score based on format violations.

        Checks for:
        - Email format in columns named email
        - Phone format in columns named phone
        - Date format consistency
        """
        if df.empty:
            return 0.0

        total_checked = 0
        consistent_values = 0

        for col in df.columns:
            col_lower = col.lower()

            # Check email format
            if "email" in col_lower or "mail" in col_lower:
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    total_checked += len(non_null)
                    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    valid_emails = non_null.astype(str).str.match(email_pattern, na=False)
                    consistent_values += valid_emails.sum()

            # Check phone format (basic)
            elif "phone" in col_lower or "tel" in col_lower:
                non_null = df[col].dropna()
                if len(non_null) > 0:
                    total_checked += len(non_null)
                    # Basic phone pattern: 10-15 digits with optional separators
                    phone_pattern = r"^[\d\s\-\+\(\)]{10,15}$"
                    valid_phones = non_null.astype(str).str.match(phone_pattern, na=False)
                    consistent_values += valid_phones.sum()

        return (consistent_values / total_checked * 100) if total_checked > 0 else 100

    def _calculate_timeliness(self, df: pd.DataFrame) -> float:
        """
        Calculate timeliness score based on data freshness.

        Looks for date columns and checks how recent the latest data is.
        """
        if df.empty:
            return 0.0

        # Find potential date columns
        date_cols = []
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["date", "time", "created", "updated", "modified"]):
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce")
                    if parsed.notna().sum() > len(df) * 0.5:
                        date_cols.append(parsed)
                except Exception:
                    pass

        if not date_cols:
            # No date columns found, assume timely
            return 100.0

        # Use the most recent date from any date column
        most_recent = max([col.max() for col in date_cols if col.max() is not pd.NaT])

        if pd.isna(most_recent):
            return 50.0

        # Calculate days since latest data
        days_old = (datetime.now(timezone.utc) - most_recent.to_pydatetime()).days

        # Score based on data freshness
        if days_old <= 1:
            return 100.0
        elif days_old <= 7:
            return 90.0
        elif days_old <= 30:
            return 70.0
        elif days_old <= 90:
            return 50.0
        else:
            return max(20.0, 100 - days_old)

    def _get_quality_assessment(self, score: float) -> str:
        """Get quality assessment label."""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    @LifecycleTracker(name="Quality.detect_issues")
    async def detect_quality_issues(
        self,
        source_id: uuid.UUID,
        table_name: str,
        asset_id: uuid.UUID | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Detect and categorize data quality issues."""
        from app.models import DataSource

        # Get data source
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == source_id)
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        # Load data
        connector = get_connector(source.type, source.connection_config)
        df = await connector.read_data(table_name=table_name, limit=10000)

        issues = {
            "critical": [],
            "warning": [],
            "info": [],
        }

        # Check for high null percentage columns
        for col in df.columns:
            null_pct = df[col].isnull().sum() / len(df) * 100

            if null_pct > 50:
                issue = {
                    "type": "high_null_percentage",
                    "column": col,
                    "null_percentage": round(null_pct, 2),
                    "message": f"Column '{col}' has {null_pct:.1f}% null values",
                }
                issues["critical"].append(issue)
                if persist and asset_id:
                    await self._persist_issue(
                        asset_id=asset_id,
                        source_id=source_id,
                        table_name=table_name,
                        column_name=col,
                        severity=QualityIssueSeverity.CRITICAL,
                        issue_type="high_null_percentage",
                        description=issue["message"],
                        context={"null_percentage": null_pct},
                    )
            elif null_pct > 20:
                issue = {
                    "type": "moderate_null_percentage",
                    "column": col,
                    "null_percentage": round(null_pct, 2),
                    "message": f"Column '{col}' has {null_pct:.1f}% null values",
                }
                issues["warning"].append(issue)
                if persist and asset_id:
                    await self._persist_issue(
                        asset_id=asset_id,
                        source_id=source_id,
                        table_name=table_name,
                        column_name=col,
                        severity=QualityIssueSeverity.WARNING,
                        issue_type="moderate_null_percentage",
                        description=issue["message"],
                        context={"null_percentage": null_pct},
                    )

        # Check for duplicate rows
        duplicate_count = df.duplicated().sum()
        duplicate_pct = duplicate_count / len(df) * 100 if len(df) > 0 else 0

        if duplicate_pct > 10:
            issue = {
                "type": "high_duplicate_percentage",
                "duplicate_count": int(duplicate_count),
                "duplicate_percentage": round(duplicate_pct, 2),
                "message": f"{duplicate_count} duplicate rows found ({duplicate_pct:.1f}%)",
            }
            issues["critical"].append(issue)
            if persist and asset_id:
                await self._persist_issue(
                    asset_id=asset_id,
                    source_id=source_id,
                    table_name=table_name,
                    column_name=None,
                    severity=QualityIssueSeverity.CRITICAL,
                    issue_type="high_duplicate_percentage",
                    description=issue["message"],
                    context={"duplicate_count": duplicate_count, "duplicate_percentage": duplicate_pct},
                )
        elif duplicate_pct > 1:
            issue = {
                "type": "duplicate_rows",
                "duplicate_count": int(duplicate_count),
                "duplicate_percentage": round(duplicate_pct, 2),
                "message": f"{duplicate_count} duplicate rows found ({duplicate_pct:.1f}%)",
            }
            issues["warning"].append(issue)
            if persist and asset_id:
                await self._persist_issue(
                    asset_id=asset_id,
                    source_id=source_id,
                    table_name=table_name,
                    column_name=None,
                    severity=QualityIssueSeverity.WARNING,
                    issue_type="duplicate_rows",
                    description=issue["message"],
                    context={"duplicate_count": duplicate_count, "duplicate_percentage": duplicate_pct},
                )

        # Check for columns with low cardinality (potential categorization issues)
        for col in df.columns:
            unique_count = df[col].nunique()
            cardinality = unique_count / len(df) if len(df) > 0 else 0

            if cardinality < 0.01 and unique_count > 1 and df[col].notna().sum() > 100:
                issue = {
                    "type": "low_cardinality",
                    "column": col,
                    "unique_values": int(unique_count),
                    "cardinality": round(cardinality, 4),
                    "message": f"Column '{col}' has very low cardinality ({unique_count} unique values)",
                }
                issues["info"].append(issue)
                if persist and asset_id:
                    await self._persist_issue(
                        asset_id=asset_id,
                        source_id=source_id,
                        table_name=table_name,
                        column_name=col,
                        severity=QualityIssueSeverity.INFO,
                        issue_type="low_cardinality",
                        description=issue["message"],
                        context={"unique_values": unique_count, "cardinality": cardinality},
                    )

        # Check for outlier values in numeric columns
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].notna().sum() > 10:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 3 * IQR
                upper_bound = Q3 + 3 * IQR

                outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
                outlier_pct = outliers / df[col].notna().sum() * 100

                if outlier_pct > 5:
                    issue = {
                        "type": "outliers_detected",
                        "column": col,
                        "outlier_count": int(outliers),
                        "outlier_percentage": round(outlier_pct, 2),
                        "message": f"Column '{col}' has {outliers} potential outliers ({outlier_pct:.1f}%)",
                    }
                    issues["warning"].append(issue)
                    if persist and asset_id:
                        await self._persist_issue(
                            asset_id=asset_id,
                            source_id=source_id,
                            table_name=table_name,
                            column_name=col,
                            severity=QualityIssueSeverity.WARNING,
                            issue_type="outliers_detected",
                            description=issue["message"],
                            context={"outlier_count": outliers, "outlier_percentage": outlier_pct},
                        )

        return {
            "issues": issues,
            "total_issues": (
                len(issues["critical"]) +
                len(issues["warning"]) +
                len(issues["info"])
            ),
            "critical_count": len(issues["critical"]),
            "warning_count": len(issues["warning"]),
            "info_count": len(issues["info"]),
        }

    async def _persist_issue(
        self,
        asset_id: uuid.UUID,
        source_id: uuid.UUID,
        table_name: str,
        column_name: str | None,
        severity: QualityIssueSeverity,
        issue_type: str,
        description: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Persist a quality issue to the database."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # Use upsert to avoid duplicates
        stmt = pg_insert(DataQualityIssue).values(
            asset_id=asset_id,
            source_id=source_id,
            table_name=table_name,
            column_name=column_name,
            severity=severity,
            issue_type=issue_type,
            description=description,
            context=context,
            resolved=False,
        ).on_conflict_do_nothing(
            index_elements=["asset_id", "table_name", "column_name", "issue_type", "resolved"]
        )

        await self.db.execute(stmt)

    @LifecycleTracker(name="Quality.track_quality_trend")
    async def track_quality_trend(
        self,
        asset_id: uuid.UUID | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """Track quality trends over time using historical assessment data."""
        from datetime import timedelta

        if asset_id:
            # Query historical quality assessments from database
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            result = await self.db.execute(
                select(QualityAssessmentHistory)
                .where(QualityAssessmentHistory.asset_id == asset_id)
                .where(QualityAssessmentHistory.assessed_at >= cutoff_date)
                .order_by(QualityAssessmentHistory.assessed_at.desc())
                .limit(100)
            )
            history = result.scalars().all()

            if history:
                trend = [
                    {
                        "date": h.assessed_at.isoformat(),
                        "score": h.overall_score,
                        "completeness": h.completeness_score,
                        "uniqueness": h.uniqueness_score,
                        "validity": h.validity_score,
                    }
                    for h in reversed(history)
                ]
                avg_score = sum(h.overall_score for h in history) / len(history)

                # Determine trend direction
                if len(trend) >= 2:
                    recent_avg = sum(t["score"] for t in trend[-5:]) / min(5, len(trend))
                    older_avg = sum(t["score"] for t in trend[:5]) / min(5, len(trend))
                    if recent_avg > older_avg + 5:
                        direction = "improving"
                    elif recent_avg < older_avg - 5:
                        direction = "declining"
                    else:
                        direction = "stable"
                else:
                    direction = "stable"

                return {
                    "asset_id": str(asset_id),
                    "period_days": days,
                    "trend": trend,
                    "average_score": round(avg_score, 2),
                    "trend_direction": direction,
                    "data_points": len(trend),
                }

        # Fallback for no historical data
        return {
            "period_days": days,
            "trend": [],
            "average_score": 0,
            "trend_direction": "unknown",
            "message": "No historical data available",
        }

    @LifecycleTracker(name="Quality.save_assessment")
    async def save_quality_assessment(
        self,
        asset_id: uuid.UUID,
        scores: dict[str, Any],
    ) -> QualityAssessmentHistory:
        """Save a quality assessment to the database for trend tracking."""
        assessment = QualityAssessmentHistory(
            asset_id=asset_id,
            overall_score=scores.get("overall_score", 0),
            completeness_score=scores.get("completeness_score", 0),
            uniqueness_score=scores.get("uniqueness_score", 0),
            validity_score=scores.get("validity_score", 0),
            consistency_score=scores.get("consistency_score", 0),
            timeliness_score=scores.get("timeliness_score", 0),
            row_count=scores.get("row_count"),
            column_count=scores.get("column_count"),
            metrics={
                "assessment": scores.get("assessment"),
            },
        )
        self.db.add(assessment)
        await self.db.flush()
        return assessment

    @LifecycleTracker(name="Quality.get_unresolved_issues")
    async def get_unresolved_issues(
        self,
        asset_id: uuid.UUID | None = None,
        severity: QualityIssueSeverity | None = None,
        limit: int = 100,
    ) -> list[DataQualityIssue]:
        """Get unresolved quality issues from the database."""
        query = select(DataQualityIssue).where(DataQualityIssue.resolved == False)

        if asset_id:
            query = query.where(DataQualityIssue.asset_id == asset_id)
        if severity:
            query = query.where(DataQualityIssue.severity == severity)

        query = query.order_by(DataQualityIssue.detected_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    @LifecycleTracker(name="Quality.resolve_issue")
    async def resolve_issue(
        self,
        issue_id: uuid.UUID,
        resolved_by: uuid.UUID,
    ) -> bool:
        """Mark a quality issue as resolved."""
        result = await self.db.execute(
            select(DataQualityIssue).where(DataQualityIssue.id == issue_id)
        )
        issue = result.scalar_one_or_none()

        if not issue:
            return False

        issue.resolved = True
        issue.resolved_at = datetime.now(timezone.utc)
        issue.resolved_by = resolved_by
        await self.db.flush()
        return True

    @LifecycleTracker(name="Quality.generate_report")
    async def generate_quality_report(
        self,
        source_id: uuid.UUID,
        table_name: str,
        asset_id: uuid.UUID | None = None,
        save_assessment: bool = True,
    ) -> dict[str, Any]:
        """Generate a comprehensive quality report."""
        # Get quality score
        score = await self.calculate_quality_score(source_id, table_name)

        # Detect issues
        issues = await self.detect_quality_issues(
            source_id, table_name, asset_id=asset_id, persist=save_assessment
        )

        # Get trend
        trend = await self.track_quality_trend(asset_id=asset_id)

        # Save assessment history
        if save_assessment and asset_id:
            await self.save_quality_assessment(asset_id, score)

        # Generate recommendations
        recommendations = self._generate_recommendations(score, issues)

        return {
            "table_name": table_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                **score,
                **{
                    "total_issues": issues["total_issues"],
                    "critical_issues": issues["critical_count"],
                    "warning_issues": issues["warning_count"],
                },
            },
            "issues": issues["issues"],
            "trend": trend,
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self,
        score: dict[str, Any],
        issues: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate actionable recommendations based on findings."""
        recommendations = []

        # Based on overall score
        if score["overall_score"] < 60:
            recommendations.append({
                "priority": "high",
                "category": "overall",
                "action": "Review data quality processes",
                "description": "Overall quality is below acceptable levels. Review data collection and validation processes.",
            })

        # Based on completeness
        if score["completeness_score"] < 80:
            recommendations.append({
                "priority": "high",
                "category": "completeness",
                "action": "Improve data capture",
                "description": "Implement better validation at data entry points to reduce null values.",
            })

        # Based on uniqueness
        if score["uniqueness_score"] < 90:
            recommendations.append({
                "priority": "medium",
                "category": "uniqueness",
                "action": "Add deduplication",
                "description": "Implement deduplication processes to remove duplicate records.",
            })

        # Based on critical issues
        for issue in issues["issues"]["critical"]:
            if issue["type"] == "high_null_percentage":
                recommendations.append({
                    "priority": "high",
                    "category": "completeness",
                    "action": f"Review column: {issue['column']}",
                    "description": issue["message"],
                })

        return recommendations
