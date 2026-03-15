"""
Metric and Dimension Management Service

Provides:
- Metric definition and calculation
- Dimension table management
- Metric lineage tracking
- Time-series aggregation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics"""
    COUNT = "count"                    # Count of records
    SUM = "sum"                        # Sum of values
    AVG = "avg"                        # Average/Mean
    MIN = "min"                        # Minimum value
    MAX = "max"                        # Maximum value
    MEDIAN = "median"                  # Median value
    PERCENTILE = "percentile"          # Percentile value
    STDDEV = "stddev"                  # Standard deviation
    VARIANCE = "variance"              # Variance
    DISTINCT_COUNT = "distinct_count"  # Count of distinct values
    RATIO = "ratio"                    # Ratio of two values
    CUSTOM = "custom"                  # Custom SQL expression


class AggregationType(str, Enum):
    """Time aggregation types"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class MetricStatus(str, Enum):
    """Metric status"""
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class Dimension:
    """A dimension for grouping/filtering metrics"""
    id: str
    name: str
    table_name: str
    column_name: str
    data_type: str
    description: Optional[str] = None
    # Dimension attributes
    is_hierarchy: bool = False
    parent_dimension_id: Optional[str] = None
    level: int = 0
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Metric:
    """A business metric definition"""
    id: str
    name: str
    display_name: str
    metric_type: MetricType
    description: Optional[str] = None
    # Data source
    table_name: str
    column_name: Optional[str] = None
    filter_condition: Optional[str] = None
    # For custom/complex metrics
    expression: Optional[str] = None
    # Dimension grouping
    dimensions: List[str] = field(default_factory=list)
    # Time configuration
    is_time_series: bool = False
    time_column: Optional[str] = None
    # Metadata
    status: MetricStatus = MetricStatus.DRAFT
    owner_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MetricValue:
    """A calculated metric value"""
    metric_id: str
    value: Union[int, float, Decimal]
    dimensions: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MetricCalculationResult:
    """Result of a metric calculation"""
    metric_id: str
    metric_name: str
    values: List[MetricValue]
    total: Optional[Union[int, float]] = None
    # Execution metadata
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_ms: float = 0
    row_count: int = 0
    error: Optional[str] = None


@dataclass
class MetricLineage:
    """Lineage information for a metric"""
    metric_id: str
    upstream_tables: List[str] = field(default_factory=list)
    upstream_metrics: List[str] = field(default_factory=list)
    downstream_metrics: List[str] = field(default_factory=list)
    downstream_tables: List[str] = field(default_factory=list)


class MetricCalculator:
    """
    Metric calculation engine

    Generates SQL for metric calculations with support for:
    - Standard aggregations (SUM, AVG, COUNT, etc.)
    - Time-series aggregations
    - Dimension grouping
    - Custom expressions
    """

    @staticmethod
    def build_metric_query(
        metric: Metric,
        dimensions: Optional[List[Dimension]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[AggregationType] = None,
    ) -> Tuple[str, List[str]]:
        """
        Build SQL query for metric calculation

        Returns (sql_query, select_columns)
        """
        select_parts = []
        group_by_parts = []
        where_parts = []

        # Main metric expression
        if metric.metric_type == MetricType.COUNT:
            expr = f"COUNT(*)"
        elif metric.metric_type == MetricType.SUM:
            expr = f"COALESCE(SUM({metric.column_name}), 0)"
        elif metric.metric_type == MetricType.AVG:
            expr = f"COALESCE(AVG({metric.column_name}), 0)"
        elif metric.metric_type == MetricType.MIN:
            expr = f"COALESCE(MIN({metric.column_name}), 0)"
        elif metric.metric_type == MetricType.MAX:
            expr = f"COALESCE(MAX({metric.column_name}), 0)"
        elif metric.metric_type == MetricType.DISTINCT_COUNT:
            expr = f"COUNT(DISTINCT {metric.column_name})"
        elif metric.metric_type == MetricType.CUSTOM and metric.expression:
            expr = metric.expression
        else:
            expr = "COUNT(*)"

        # Add time series aggregation if needed
        if metric.is_time_series and aggregation and metric.time_column:
            time_trunc = MetricCalculator._get_time_trunc(aggregation)
            select_parts.append(f"{time_trunc}({metric.time_column}) AS time_period")
            group_by_parts.append(f"{time_trunc}({metric.time_column})")

        # Add dimension groupings
        dimension_columns = []
        if dimensions:
            for dim in dimensions:
                select_parts.append(f"{dim.table_name}.{dim.column_name} AS {dim.name}")
                group_by_parts.append(f"{dim.table_name}.{dim.column_name}")
                dimension_columns.append(dim.name)

        # Add metric value
        select_parts.append(f"{expr} AS value")

        # Build SELECT clause
        select_clause = ", ".join(select_parts)

        # Build FROM clause
        from_clause = f"FROM {metric.table_name}"

        # Build WHERE clause
        if metric.filter_condition:
            where_parts.append(metric.filter_condition)

        if start_date and end_date and metric.time_column:
            where_parts.append(f"{metric.time_column} BETWEEN '{start_date}' AND '{end_date}'")

        where_clause = ""
        if where_parts:
            where_clause = "WHERE " + " AND ".join(where_parts)

        # Build GROUP BY clause
        group_by_clause = ""
        if group_by_parts:
            group_by_clause = "GROUP BY " + ", ".join(group_by_parts)

        # Build complete query
        sql = f"SELECT {select_clause} {from_clause} {where_clause} {group_by_clause}"

        return sql, dimension_columns

    @staticmethod
    def _get_time_trunc(aggregation: AggregationType) -> str:
        """Get time truncation function for aggregation type"""
        trunc_map = {
            AggregationType.MINUTE: "date_trunc('minute'",
            AggregationType.HOUR: "date_trunc('hour'",
            AggregationType.DAY: "date_trunc('day'",
            AggregationType.WEEK: "date_trunc('week'",
            AggregationType.MONTH: "date_trunc('month'",
            AggregationType.QUARTER: "date_trunc('quarter'",
            AggregationType.YEAR: "date_trunc('year'",
        }
        return trunc_map.get(aggregation, "date_trunc('day'")


class DimensionManager:
    """
    Dimension table management

    Manages dimension tables, hierarchies, and relationships.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_dimension(
        self,
        name: str,
        table_name: str,
        column_name: str,
        data_type: str,
        description: Optional[str] = None,
        is_hierarchy: bool = False,
        parent_dimension_id: Optional[str] = None,
        level: int = 0,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dimension:
        """Create a new dimension"""
        dimension = Dimension(
            id=str(uuid.uuid4()),
            name=name,
            table_name=table_name,
            column_name=column_name,
            data_type=data_type,
            description=description,
            is_hierarchy=is_hierarchy,
            parent_dimension_id=parent_dimension_id,
            level=level,
            created_by=user_id,
            tags=tags or [],
        )

        # In production, save to database
        logger.info(f"Created dimension: {dimension.id}")
        return dimension

    def get_dimension(self, dimension_id: str) -> Optional[Dimension]:
        """Get a dimension by ID"""
        # In production, query from database
        return None

    def list_dimensions(
        self,
        table_name: Optional[str] = None,
        is_hierarchy: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Dimension]:
        """List dimensions with optional filters"""
        # In production, query from database
        return []

    def get_dimension_values(
        self,
        dimension_id: str,
        limit: int = 1000,
    ) -> List[Any]:
        """Get distinct values for a dimension"""
        dimension = self.get_dimension(dimension_id)
        if not dimension:
            return []

        # In production, query distinct values from dimension table
        return []

    def get_dimension_hierarchy(
        self,
        dimension_id: str,
    ) -> List[Dict[str, Any]]:
        """Get hierarchy for a dimension"""
        dimension = self.get_dimension(dimension_id)
        if not dimension or not dimension.is_hierarchy:
            return []

        # In production, query hierarchy
        return []


class MetricManager:
    """
    Metric management service

    Manages metric definitions, calculations, and lineage.
    """

    def __init__(self, db: Session):
        self.db = db
        self.calculator = MetricCalculator()
        self.dimension_manager = DimensionManager(db)

    # ========================================================================
    # Metric CRUD
    # ========================================================================

    def create_metric(
        self,
        name: str,
        display_name: str,
        metric_type: MetricType,
        table_name: str,
        column_name: Optional[str] = None,
        description: Optional[str] = None,
        filter_condition: Optional[str] = None,
        expression: Optional[str] = None,
        dimensions: Optional[List[str]] = None,
        is_time_series: bool = False,
        time_column: Optional[str] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Metric:
        """Create a new metric"""
        metric = Metric(
            id=str(uuid.uuid4()),
            name=name,
            display_name=display_name,
            metric_type=metric_type,
            table_name=table_name,
            column_name=column_name,
            description=description,
            filter_condition=filter_condition,
            expression=expression,
            dimensions=dimensions or [],
            is_time_series=is_time_series,
            time_column=time_column,
            owner_id=owner_id,
            tags=tags or [],
        )

        # In production, save to database
        logger.info(f"Created metric: {metric.id}")
        return metric

    def get_metric(self, metric_id: str) -> Optional[Metric]:
        """Get a metric by ID"""
        # In production, query from database
        return None

    def get_metric_by_name(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        # In production, query from database
        return None

    def list_metrics(
        self,
        status: Optional[MetricStatus] = None,
        owner_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Metric]:
        """List metrics with optional filters"""
        # In production, query from database
        return []

    def update_metric(
        self,
        metric_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        expression: Optional[str] = None,
        status: Optional[MetricStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Metric]:
        """Update a metric"""
        # In production, update in database
        return None

    def delete_metric(self, metric_id: str) -> bool:
        """Delete a metric"""
        # In production, delete from database
        return True

    # ========================================================================
    # Metric Calculation
    # ========================================================================

    def calculate_metric(
        self,
        metric_id: str,
        dimensions: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[AggregationType] = None,
    ) -> MetricCalculationResult:
        """
        Calculate a metric

        Args:
            metric_id: Metric ID to calculate
            dimensions: Dimension names to group by
            start_date: Start date for time-series queries
            end_date: End date for time-series queries
            aggregation: Time aggregation type

        Returns:
            MetricCalculationResult with values
        """
        start_time = datetime.utcnow()

        metric = self.get_metric(metric_id)
        if not metric:
            return MetricCalculationResult(
                metric_id=metric_id,
                metric_name="",
                values=[],
                error="Metric not found",
            )

        # Get dimension objects
        dimension_objects = []
        if dimensions:
            for dim_name in dimensions:
                # Find dimension by name
                # In production, query from database
                pass

        # Build query
        sql, dimension_columns = self.calculator.build_metric_query(
            metric=metric,
            dimensions=dimension_objects,
            start_date=start_date,
            end_date=end_date,
            aggregation=aggregation,
        )

        # Execute query
        try:
            # In production, execute using appropriate database connection
            # For now, return mock result
            values = [
                MetricValue(
                    metric_id=metric_id,
                    value=100,
                    dimensions={},
                )
            ]

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return MetricCalculationResult(
                metric_id=metric_id,
                metric_name=metric.display_name,
                values=values,
                total=100,
                calculated_at=datetime.utcnow(),
                execution_time_ms=execution_time,
                row_count=1,
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return MetricCalculationResult(
                metric_id=metric_id,
                metric_name=metric.display_name,
                values=[],
                error=str(e),
                calculated_at=datetime.utcnow(),
                execution_time_ms=execution_time,
            )

    def calculate_multiple_metrics(
        self,
        metric_ids: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        aggregation: Optional[AggregationType] = None,
    ) -> List[MetricCalculationResult]:
        """Calculate multiple metrics"""
        results = []
        for metric_id in metric_ids:
            result = self.calculate_metric(
                metric_id=metric_id,
                start_date=start_date,
                end_date=end_date,
                aggregation=aggregation,
            )
            results.append(result)
        return results

    # ========================================================================
    # Metric Lineage
    # ========================================================================

    def get_metric_lineage(self, metric_id: str) -> MetricLineage:
        """Get lineage information for a metric"""
        metric = self.get_metric(metric_id)
        if not metric:
            return MetricLineage(metric_id=metric_id)

        lineage = MetricLineage(
            metric_id=metric_id,
            upstream_tables=[metric.table_name],
        )

        # Find downstream metrics that use this metric
        # In production, query from database

        return lineage

    def analyze_impact(
        self,
        table_name: str,
        column_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze impact of a table/column change on metrics

        Returns affected metrics and dimensions.
        """
        # In production, query metric definitions
        return {
            "affected_metrics": [],
            "affected_dimensions": [],
            "total_metrics": 0,
            "total_dimensions": 0,
        }


class MetricExplainer:
    """
    Metric explanation and documentation

    Generates human-readable explanations of metrics.
    """

    @staticmethod
    def explain_metric(metric: Metric) -> Dict[str, Any]:
        """Generate an explanation of a metric"""
        explanation = {
            "name": metric.display_name,
            "type": metric.metric_type.value,
            "description": metric.description or "",
            "formula": MetricExplainer._get_formula(metric),
            "source_table": metric.table_name,
            "source_column": metric.column_name,
            "dimensions": metric.dimensions,
            "is_time_series": metric.is_time_series,
            "time_column": metric.time_column,
            "example_sql": MetricExplainer._get_example_sql(metric),
        }

        return explanation

    @staticmethod
    def _get_formula(metric: Metric) -> str:
        """Get human-readable formula for metric"""
        if metric.metric_type == MetricType.COUNT:
            return f"Count of records in {metric.table_name}"
        elif metric.metric_type == MetricType.SUM:
            return f"Sum of {metric.column_name} from {metric.table_name}"
        elif metric.metric_type == MetricType.AVG:
            return f"Average of {metric.column_name} from {metric.table_name}"
        elif metric.metric_type == MetricType.CUSTOM:
            return f"Custom expression: {metric.expression}"
        else:
            return f"{metric.metric_type.value.upper()} of {metric.column_name or 'records'}"

    @staticmethod
    def _get_example_sql(metric: Metric) -> str:
        """Get example SQL for the metric"""
        if metric.metric_type == MetricType.COUNT:
            sql = f"SELECT COUNT(*) FROM {metric.table_name}"
        elif metric.metric_type == MetricType.SUM:
            sql = f"SELECT SUM({metric.column_name}) FROM {metric.table_name}"
        elif metric.metric_type == MetricType.AVG:
            sql = f"SELECT AVG({metric.column_name}) FROM {metric.table_name}"
        else:
            sql = f"SELECT * FROM {metric.table_name} LIMIT 10"

        if metric.filter_condition:
            sql += f" WHERE {metric.filter_condition}"

        return sql


# Singleton instances
_metric_manager: Optional[MetricManager] = None
_dimension_manager: Optional[DimensionManager] = None


def get_metric_manager(db: Session) -> MetricManager:
    """Get or create the metric manager instance"""
    return MetricManager(db)


def get_dimension_manager(db: Session) -> DimensionManager:
    """Get or create the dimension manager instance"""
    return DimensionManager(db)
