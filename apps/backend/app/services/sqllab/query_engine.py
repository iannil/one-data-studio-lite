"""
SQLLab Query Engine

Provides multi-database query execution with support for:
- MySQL, PostgreSQL, ClickHouse, Hive, Presto/Trino
- Query result pagination and caching
- Query history and saved queries
- Query performance analysis
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
import json

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DatabaseType(str, Enum):
    """Supported database types"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    HIVE = "hive"
    PRESTO = "presto"
    TRINO = "trino"
    SQLITE = "sqlite"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"


class QueryStatus(str, Enum):
    """Query execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ResultFormat(str, Enum):
    """Query result formats"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PARQUET = "parquet"


@dataclass
class DatabaseConnection:
    """Database connection configuration"""
    id: str
    name: str
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    # Additional options
    options: Dict[str, Any] = field(default_factory=dict)
    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None


@dataclass
class QueryResult:
    """Query execution result"""
    query_id: str
    status: QueryStatus
    rows: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0
    rows_affected: int = 0
    limit_reached: bool = False
    message: Optional[str] = None
    error: Optional[str] = None
    # Query metadata
    executed_at: datetime = field(default_factory=datetime.utcnow)
    cached: bool = False


@dataclass
class QueryHistory:
    """Query history entry"""
    id: str
    user_id: str
    connection_id: str
    query: str
    status: QueryStatus
    execution_time_ms: float
    row_count: int
    executed_at: datetime
    # Optional
    name: Optional[str] = None
    description: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class SavedQuery:
    """Saved query for reuse"""
    id: str
    user_id: str
    name: str
    query: str
    connection_id: str
    # Optional metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    is_public: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QueryExecution:
    """Query execution context"""
    query_id: str
    connection: DatabaseConnection
    sql: str
    limit: Optional[int] = None
    offset: Optional[int] = None
    # Execution options
    timeout_seconds: int = 300
    enable_cache: bool = True
    cache_ttl_seconds: int = 3600
    # Metrics
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class QueryEngineFactory:
    """
    Factory for creating database connections

    Supports multiple database types with connection pooling.
    """

    _engines: Dict[str, Any] = {}

    @classmethod
    def create_engine(cls, connection: DatabaseConnection) -> Any:
        """Create a database engine for the connection"""
        from sqlalchemy import create_engine

        # Check if engine already exists
        engine_key = f"{connection.id}_{connection.db_type.value}"
        if engine_key in cls._engines:
            return cls._engines[engine_key]

        # Build connection URL
        url = cls._build_connection_url(connection)

        # Create engine with pool settings
        engine = create_engine(
            url,
            pool_size=connection.pool_size,
            max_overflow=connection.max_overflow,
            pool_timeout=connection.pool_timeout,
            pool_recycle=connection.pool_recycle,
            pool_pre_ping=True,
            echo=False,
        )

        cls._engines[engine_key] = engine
        return engine

    @classmethod
    def _build_connection_url(cls, connection: DatabaseConnection) -> str:
        """Build SQLAlchemy connection URL"""
        if connection.db_type == DatabaseType.MYSQL:
            return f"mysql+pymysql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
        elif connection.db_type == DatabaseType.POSTGRESQL:
            return f"postgresql://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
        elif connection.db_type == DatabaseType.CLICKHOUSE:
            return f"clickhouse+native://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
        elif connection.db_type == DatabaseType.SQLITE:
            return f"sqlite:///{connection.host}"
        elif connection.db_type == DatabaseType.SNOWFLAKE:
            return f"snowflake://{connection.username}:{connection.password}@{connection.host}/{connection.database}"
        elif connection.db_type == DatabaseType.BIGQUERY:
            return f"bigquery://{connection.project_id}/{connection.dataset}"
        elif connection.db_type == DatabaseType.REDSHIFT:
            return f"redshift+psycopg2://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"
        else:
            # Generic URL for other types
            return f"{connection.db_type.value}://{connection.username}:{connection.password}@{connection.host}:{connection.port}/{connection.database}"

    @classmethod
    def dispose_engine(cls, connection_id: str, db_type: str):
        """Dispose a database engine"""
        engine_key = f"{connection_id}_{db_type}"
        if engine_key in cls._engines:
            cls._engines[engine_key].dispose()
            del cls._engines[engine_key]


class QueryValidator:
    """
    SQL query validation and analysis

    Provides:
    - SQL syntax validation
    - Query complexity analysis
    - Performance recommendations
    - Security checks (SQL injection)
    """

    # Dangerous keywords that might indicate SQL injection
    DANGEROUS_PATTERNS = [
        "DROP TABLE",
        "DELETE FROM",
        "TRUNCATE",
        "ALTER TABLE",
        "EXEC(",
        "EXECUTE(",
        "xp_cmdshell",
    ]

    @staticmethod
    def validate_query(sql: str, db_type: DatabaseType) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query syntax

        Returns (is_valid, error_message)
        """
        sql = sql.strip()

        if not sql:
            return False, "Query is empty"

        # Check for dangerous patterns
        sql_upper = sql.upper()
        for pattern in QueryValidator.DANGEROUS_PATTERNS:
            if pattern in sql_upper:
                return False, f"Dangerous SQL pattern detected: {pattern}"

        # Check if it's a SELECT query (read-only)
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH") and not sql_upper.startswith("SHOW") and not sql_upper.startswith("DESCRIBE") and not sql_upper.startswith("EXPLAIN"):
            return False, "Only SELECT queries are allowed"

        # Basic syntax check
        try:
            # Try to parse the query
            # For MySQL
            if db_type == DatabaseType.MYSQL:
                import sqlparse
                statements = sqlparse.parse(sql)
                if not statements:
                    return False, "Failed to parse SQL"
            # Other dialects could be added here
        except ImportError:
            # sqlparse not available, skip detailed validation
            pass
        except Exception as e:
            return False, f"SQL validation error: {str(e)}"

        return True, None

    @staticmethod
    def analyze_complexity(sql: str) -> Dict[str, Any]:
        """
        Analyze query complexity

        Returns metrics about query complexity.
        """
        sql_upper = sql.upper()

        complexity = {
            "joins": sql_upper.count(" JOIN "),
            "subqueries": sql_upper.count("SELECT") - 1,
            "unions": sql_upper.count(" UNION "),
            "group_bys": sql_upper.count(" GROUP BY"),
            "order_bys": sql_upper.count(" ORDER BY"),
            "has_aggregation": "GROUP BY" in sql_upper or "HAVING" in sql_upper,
            "has_window_functions": "OVER (" in sql_upper,
            "estimated_cost": 0,
        }

        # Calculate estimated complexity cost
        cost = 1
        cost += complexity["joins"] * 2
        cost += complexity["subqueries"] * 3
        cost += complexity["unions"] * 2
        if complexity["has_aggregation"]:
            cost += 2
        if complexity["has_window_functions"]:
            cost += 3

        complexity["estimated_cost"] = cost
        complexity["complexity_level"] = "low" if cost < 5 else "medium" if cost < 10 else "high"

        return complexity

    @staticmethod
    def get_recommendations(analysis: Dict[str, Any]) -> List[str]:
        """Get performance recommendations based on query analysis"""
        recommendations = []

        if analysis["joins"] > 3:
            recommendations.append("Consider reducing the number of JOINs or breaking into multiple queries")

        if analysis["subqueries"] > 2:
            recommendations.append("Consider using CTEs (WITH clauses) instead of nested subqueries")

        if analysis["has_window_functions"]:
            recommendations.append("Window functions can be expensive, ensure proper indexing")

        if analysis["complexity_level"] == "high":
            recommendations.append("High complexity query - consider adding LIMIT clause for testing")

        return recommendations


class QueryCache:
    """
    Query result caching

    Caches query results to improve performance for repeated queries.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[QueryResult, datetime]] = {}

    def _generate_key(self, connection_id: str, sql: str, limit: Optional[int]) -> str:
        """Generate cache key"""
        content = f"{connection_id}:{sql}:{limit}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, connection_id: str, sql: str, limit: Optional[int]) -> Optional[QueryResult]:
        """Get cached result if available and not expired"""
        key = self._generate_key(connection_id, sql, limit)
        if key in self._cache:
            result, timestamp = self._cache[key]
            # Check if result is still valid (1 hour default)
            if datetime.utcnow() - timestamp < timedelta(hours=1):
                result.cached = True
                return result
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None

    def set(self, connection_id: str, sql: str, limit: Optional[int], result: QueryResult, ttl_seconds: int = 3600):
        """Cache query result"""
        key = self._generate_key(connection_id, sql, limit)
        self._cache[key] = (result, datetime.utcnow())

    def invalidate(self, connection_id: Optional[str] = None):
        """Invalidate cache"""
        if connection_id:
            # Invalidate all cache entries for a connection
            keys_to_remove = [
                k for k in self._cache
                if k.startswith(hashlib.md5(f"{connection_id}:".encode()).hexdigest()[:8])
            ]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            # Clear all cache
            self._cache.clear()

    def cleanup_expired(self):
        """Remove expired cache entries"""
        expired_keys = []
        for key, (_, timestamp) in self._cache.items():
            if datetime.utcnow() - timestamp > timedelta(hours=1):
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]


class SQLLabService:
    """
    Main SQLLab service

    Manages database connections, query execution, and result management.
    """

    def __init__(self, db: Session):
        self.db = db
        self.validator = QueryValidator()
        self.cache = QueryCache()

    # ========================================================================
    # Connection Management
    # ========================================================================

    def create_connection(
        self,
        name: str,
        db_type: DatabaseType,
        host: str,
        port: int,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        **options
    ) -> DatabaseConnection:
        """Create a new database connection"""
        connection = DatabaseConnection(
            id=str(uuid.uuid4()),
            name=name,
            db_type=db_type,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            description=description,
            created_by=user_id,
            options=options,
        )

        # Test connection
        try:
            engine = QueryEngineFactory.create_engine(connection)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"Created database connection: {connection.id}")
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise ValueError(f"Connection failed: {str(e)}")

        # In production, save to database
        return connection

    def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """Get a database connection by ID"""
        # In production, query from database
        return None

    def list_connections(
        self,
        user_id: Optional[str] = None,
        db_type: Optional[DatabaseType] = None,
    ) -> List[DatabaseConnection]:
        """List available database connections"""
        # In production, query from database
        return []

    def test_connection(self, connection: DatabaseConnection) -> Tuple[bool, Optional[str]]:
        """Test a database connection"""
        try:
            engine = QueryEngineFactory.create_engine(connection)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                row = result.fetchone()
                if row and row[0] == 1:
                    return True, None
            return False, "Unexpected result"
        except Exception as e:
            return False, str(e)

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a database connection"""
        # Dispose engine
        QueryEngineFactory.dispose_engine(connection_id, "any")  # Would need actual db_type
        # In production, delete from database
        return True

    # ========================================================================
    # Query Execution
    # ========================================================================

    def execute_query(
        self,
        connection_id: str,
        sql: str,
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        enable_cache: bool = True,
    ) -> QueryResult:
        """
        Execute a SQL query

        Args:
            connection_id: Database connection ID
            sql: SQL query to execute
            user_id: User ID executing the query
            limit: Maximum rows to return
            offset: Number of rows to skip
            enable_cache: Enable query result caching

        Returns:
            QueryResult with execution results
        """
        query_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Get connection
        connection = self.get_connection(connection_id)
        if not connection:
            return QueryResult(
                query_id=query_id,
                status=QueryStatus.FAILED,
                error=f"Connection not found: {connection_id}",
            )

        # Validate query
        is_valid, error_msg = self.validator.validate_query(sql, connection.db_type)
        if not is_valid:
            return QueryResult(
                query_id=query_id,
                status=QueryStatus.FAILED,
                error=error_msg,
            )

        # Check cache
        if enable_cache:
            cached_result = self.cache.get(connection_id, sql, limit)
            if cached_result:
                return cached_result

        # Execute query
        try:
            engine = QueryEngineFactory.create_engine(connection)

            # Build query with limit
            final_sql = sql
            if limit:
                # Add LIMIT clause based on database type
                if connection.db_type in [DatabaseType.MYSQL, DatabaseType.POSTGRESQL, DatabaseType.SQLITE]:
                    if "LIMIT" not in sql.upper():
                        final_sql = f"{sql.rstrip(';')} LIMIT {limit}"
                elif connection.db_type == DatabaseType.CLICKHOUSE:
                    if "LIMIT" not in sql.upper():
                        final_sql = f"{sql.rstrip(';')} LIMIT {limit}"

            # Execute
            with engine.connect() as conn:
                result = conn.execute(text(final_sql))

                # Get columns
                columns = list(result.keys())

                # Fetch rows
                rows = []
                for row in result:
                    row_dict = dict(zip(columns, row))
                    rows.append(row_dict)
                    if limit and len(rows) >= limit:
                        break

                execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                query_result = QueryResult(
                    query_id=query_id,
                    status=QueryStatus.SUCCESS,
                    rows=rows,
                    columns=columns,
                    row_count=len(rows),
                    execution_time_ms=execution_time,
                    limit_reached=limit and len(rows) >= limit,
                )

                # Cache result
                if enable_cache:
                    self.cache.set(connection_id, sql, limit, query_result)

                # Save to history
                self._save_to_history(
                    user_id=user_id,
                    connection_id=connection_id,
                    query=sql,
                    status=QueryStatus.SUCCESS,
                    execution_time_ms=execution_time,
                    row_count=len(rows),
                )

                return query_result

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Query execution failed: {e}")

            # Save to history
            self._save_to_history(
                user_id=user_id,
                connection_id=connection_id,
                query=sql,
                status=QueryStatus.FAILED,
                execution_time_ms=execution_time,
                row_count=0,
            )

            return QueryResult(
                query_id=query_id,
                status=QueryStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )

    # ========================================================================
    # Query History
    # ========================================================================

    def _save_to_history(
        self,
        user_id: str,
        connection_id: str,
        query: str,
        status: QueryStatus,
        execution_time_ms: float,
        row_count: int,
    ):
        """Save query to history"""
        # In production, save to database
        logger.debug(f"Saved to history: user={user_id}, query={query[:50]}...")

    def get_query_history(
        self,
        user_id: str,
        limit: int = 100,
        connection_id: Optional[str] = None,
    ) -> List[QueryHistory]:
        """Get query history for a user"""
        # In production, query from database
        return []

    def get_saved_queries(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[SavedQuery]:
        """Get saved queries for a user"""
        # In production, query from database
        return []

    def save_query(
        self,
        user_id: str,
        name: str,
        query: str,
        connection_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False,
    ) -> SavedQuery:
        """Save a query for reuse"""
        saved_query = SavedQuery(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            query=query,
            connection_id=connection_id,
            description=description,
            tags=tags or [],
            is_public=is_public,
        )
        # In production, save to database
        return saved_query

    def delete_saved_query(self, query_id: str, user_id: str) -> bool:
        """Delete a saved query"""
        # In production, delete from database
        return True

    # ========================================================================
    # Schema Exploration
    # ========================================================================

    def get_tables(
        self,
        connection_id: str,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get list of tables in the database"""
        connection = self.get_connection(connection_id)
        if not connection:
            return []

        try:
            engine = QueryEngineFactory.create_engine(connection)

            if connection.db_type == DatabaseType.MYSQL:
                sql = "SHOW TABLES"
            elif connection.db_type == DatabaseType.POSTGRESQL:
                sql = "SELECT tablename as name FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
            elif connection.db_type == DatabaseType.SQLITE:
                sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            elif connection.db_type == DatabaseType.CLICKHOUSE:
                sql = "SELECT name FROM system.tables WHERE database != 'system'"
            else:
                sql = "SHOW TABLES"

            with engine.connect() as conn:
                result = conn.execute(text(sql))
                tables = []
                for row in result:
                    tables.append({"name": row[0]})
                return tables

        except Exception as e:
            logger.error(f"Failed to get tables: {e}")
            return []

    def get_table_schema(
        self,
        connection_id: str,
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """Get table schema (columns, types, etc.)"""
        connection = self.get_connection(connection_id)
        if not connection:
            return []

        try:
            engine = QueryEngineFactory.create_engine(connection)

            if connection.db_type == DatabaseType.MYSQL:
                sql = f"DESCRIBE {table_name}"
            elif connection.db_type == DatabaseType.POSTGRESQL:
                sql = f"SELECT column_name as name, data_type as type, is_nullable as nullable FROM information_schema.columns WHERE table_name = '{table_name}'"
            elif connection.db_type == DatabaseType.SQLITE:
                sql = f"PRAGMA table_info({table_name})"
            elif connection.db_type == DatabaseType.CLICKHOUSE:
                sql = f"DESCRIBE TABLE {table_name}"
            else:
                sql = f"DESCRIBE {table_name}"

            with engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = []
                for row in result:
                    columns.append({
                        "name": row[0],
                        "type": row[1] if len(row) > 1 else "unknown",
                    })
                return columns

        except Exception as e:
            logger.error(f"Failed to get table schema: {e}")
            return []

    def get_table_preview(
        self,
        connection_id: str,
        table_name: str,
        limit: int = 100,
    ) -> QueryResult:
        """Get preview of table data"""
        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        return self.execute_query(
            connection_id=connection_id,
            sql=sql,
            user_id="system",
            enable_cache=False,
        )

    # ========================================================================
    # Query Analysis
    # ========================================================================

    def analyze_query(self, sql: str, db_type: DatabaseType) -> Dict[str, Any]:
        """Analyze query complexity and provide recommendations"""
        # Validate
        is_valid, error = self.validator.validate_query(sql, db_type)
        if not is_valid:
            return {
                "is_valid": False,
                "error": error,
            }

        # Analyze complexity
        complexity = self.validator.analyze_complexity(sql)

        # Get recommendations
        recommendations = self.validator.get_recommendations(complexity)

        return {
            "is_valid": True,
            "complexity": complexity,
            "recommendations": recommendations,
        }


# Singleton instance
_sqllab_service: Optional[SQLLabService] = None


def get_sqllab_service(db: Session) -> SQLLabService:
    """Get or create the SQLLab service instance"""
    return SQLLabService(db)
