"""Tests for AI service functionality."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models import DataSource, MetadataColumn, MetadataTable, DataAsset
from app.models.asset import AssetType
from app.services.ai_service import AIService, SQLSecurityValidator


class TestSQLSecurityValidator:
    """Test suite for SQL security validation."""

    def test_validate_safe_select(self):
        """Test validation of safe SELECT query."""
        sql = "SELECT * FROM users WHERE id = 1"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is True
        assert len(violations) == 0

    def test_validate_safe_with_cte(self):
        """Test validation of safe CTE query."""
        sql = "WITH active_users AS (SELECT * FROM users WHERE active = true) SELECT * FROM active_users"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is True

    def test_validate_drop_table(self):
        """Test validation blocks DROP TABLE."""
        sql = "DROP TABLE users"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "DROP statement" in violations

    def test_validate_truncate(self):
        """Test validation blocks TRUNCATE."""
        sql = "TRUNCATE TABLE users"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "TRUNCATE TABLE" in violations

    def test_validate_delete(self):
        """Test validation blocks DELETE."""
        sql = "DELETE FROM users WHERE id = 1"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "DELETE FROM" in violations

    def test_validate_insert(self):
        """Test validation blocks INSERT."""
        sql = "INSERT INTO users (name) VALUES ('test')"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "INSERT INTO" in violations

    def test_validate_update(self):
        """Test validation blocks UPDATE."""
        sql = "UPDATE users SET name = 'test' WHERE id = 1"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "UPDATE statement" in violations

    def test_validate_sql_injection_comment(self):
        """Test validation blocks SQL comment injection."""
        sql = "SELECT * FROM users; -- DROP TABLE users"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "SQL comment injection" in violations

    def test_validate_union_information_schema(self):
        """Test validation blocks information_schema access via UNION."""
        sql = "SELECT * FROM users UNION SELECT * FROM information_schema.tables"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False

    def test_validate_sleep_function(self):
        """Test validation blocks SLEEP function."""
        sql = "SELECT * FROM users WHERE SLEEP(5)"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "SLEEP function" in violations

    def test_validate_empty_query(self):
        """Test validation of empty query."""
        sql = ""
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert "Empty SQL query" in violations

    def test_validate_non_select_query(self):
        """Test validation blocks non-SELECT queries."""
        sql = "CALL some_procedure()"
        is_safe, violations = SQLSecurityValidator.validate(sql)
        assert is_safe is False
        assert any("allowed statement" in v for v in violations)

    def test_sanitize_removes_comments(self):
        """Test sanitization removes SQL comments."""
        sql = "SELECT * FROM users -- comment\nWHERE id = 1"
        result = SQLSecurityValidator.sanitize(sql)
        assert "--" not in result

    def test_sanitize_removes_block_comments(self):
        """Test sanitization removes block comments."""
        sql = "SELECT /* hidden */ * FROM users"
        result = SQLSecurityValidator.sanitize(sql)
        assert "/*" not in result
        assert "*/" not in result

    def test_sanitize_normalizes_whitespace(self):
        """Test sanitization normalizes whitespace."""
        sql = "SELECT  *   FROM    users"
        result = SQLSecurityValidator.sanitize(sql)
        assert result == "SELECT * FROM users"


class TestAIService:
    """Test suite for AIService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create an AIService instance with mock database."""
        with patch("app.services.ai_service.AsyncOpenAI"):
            return AIService(mock_db)

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", None, "Diana", "Eve"],
            "email": ["alice@test.com", "bob@test.com", None, "diana@test.com", "eve@test.com"],
            "age": [25, 30, 35, 28, 22],
        })


class TestDataQualityAnalysis(TestAIService):
    """Test data quality analysis."""

    def test_analyze_data_quality_basic(self, service, sample_dataframe):
        """Test basic data quality analysis."""
        stats = service._analyze_data_quality(sample_dataframe)

        assert stats["row_count"] == 5
        assert stats["column_count"] == 4
        assert len(stats["columns"]) == 4
        assert "duplicate_rows" in stats

    def test_analyze_data_quality_null_count(self, service, sample_dataframe):
        """Test null count in data quality analysis."""
        stats = service._analyze_data_quality(sample_dataframe)

        name_stats = stats["columns"]["name"]
        assert name_stats["null_count"] == 1
        assert name_stats["null_percentage"] == 20.0

    def test_analyze_data_quality_numeric_stats(self, service, sample_dataframe):
        """Test numeric statistics in data quality analysis."""
        stats = service._analyze_data_quality(sample_dataframe)

        age_stats = stats["columns"]["age"]
        assert age_stats["min"] == 22
        assert age_stats["max"] == 35
        assert "mean" in age_stats
        assert "std" in age_stats

    def test_analyze_data_quality_string_stats(self, service, sample_dataframe):
        """Test string statistics in data quality analysis."""
        stats = service._analyze_data_quality(sample_dataframe)

        email_stats = stats["columns"]["email"]
        assert "top_values" in email_stats
        assert "avg_length" in email_stats

    def test_analyze_data_quality_duplicates(self, service):
        """Test duplicate detection in data quality analysis."""
        df_with_dups = pd.DataFrame({
            "id": [1, 1, 2, 2, 3],
            "name": ["A", "A", "B", "B", "C"],
        })

        stats = service._analyze_data_quality(df_with_dups)

        assert stats["duplicate_rows"] == 2
        assert stats["duplicate_percentage"] == 40.0


class TestFieldAnalysis(TestAIService):
    """Test field meaning analysis."""

    @pytest.mark.asyncio
    async def test_analyze_field_meanings(self, service, mock_db):
        """Test AI-powered field meaning analysis."""
        table = MagicMock(spec=MetadataTable)
        table.id = uuid.uuid4()

        column = MagicMock(spec=MetadataColumn)
        column.column_name = "email"
        column.data_type = "varchar"
        column.nullable = True
        column.is_primary_key = False
        column.tags = []

        source = MagicMock(spec=DataSource)
        source.type = "postgresql"
        source.connection_config = {}

        mock_table_result = MagicMock()
        mock_table_result.scalar_one_or_none.return_value = table

        mock_columns_result = MagicMock()
        mock_columns_result.scalars.return_value = [column]

        mock_source_result = MagicMock()
        mock_source_result.scalar_one_or_none.return_value = source

        mock_db.execute.side_effect = [
            mock_table_result,
            mock_columns_result,
            mock_source_result,
        ]

        with patch("app.services.ai_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=pd.DataFrame({"email": ["test@example.com"]}))
            mock_connector.return_value = mock_conn

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "columns": [{
                                "name": "email",
                                "meaning": "User email address",
                                "category": "PII",
                                "tags": ["contact", "pii"],
                            }],
                            "table_summary": "User contact information",
                        })
                    )
                )
            ]
            service.client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await service.analyze_field_meanings(
                source_id=uuid.uuid4(),
                table_name="users",
            )

            assert result["columns_analyzed"] == 1
            assert len(result["results"]) == 1


class TestNLToSQL(TestAIService):
    """Test natural language to SQL conversion."""

    @pytest.mark.asyncio
    async def test_natural_language_to_sql_success(self, service, mock_db):
        """Test successful NL to SQL conversion."""
        table = MagicMock(spec=MetadataTable)
        table.id = uuid.uuid4()
        table.table_name = "sales"
        table.schema_name = "public"
        table.ai_description = "Sales transactions"

        mock_tables_result = MagicMock()
        mock_tables_result.scalars.return_value = [table]

        mock_columns_result = MagicMock()
        mock_columns_result.scalars.return_value = []

        mock_db.execute.side_effect = [mock_tables_result, mock_columns_result]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "sql": "SELECT SUM(amount) FROM sales WHERE date >= '2024-01-01'",
                        "explanation": "Sums sales amount for the year",
                        "visualization_suggestion": {
                            "chart_type": "bar",
                        },
                    })
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.natural_language_to_sql(
            query="Total sales this year"
        )

        assert "sql" in result
        assert "SELECT" in result["sql"]

    @pytest.mark.asyncio
    async def test_natural_language_to_sql_security_block(self, service, mock_db):
        """Test NL to SQL blocks dangerous queries."""
        table = MagicMock(spec=MetadataTable)
        table.id = uuid.uuid4()
        table.table_name = "users"
        table.schema_name = "public"

        mock_tables_result = MagicMock()
        mock_tables_result.scalars.return_value = [table]

        mock_columns_result = MagicMock()
        mock_columns_result.scalars.return_value = []

        mock_db.execute.side_effect = [mock_tables_result, mock_columns_result]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "sql": "DROP TABLE users",
                        "explanation": "Drops the users table",
                    })
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.natural_language_to_sql(
            query="Delete all users"
        )

        assert result.get("security_error") is True
        assert "error" in result


class TestAssetSearch(TestAIService):
    """Test AI-powered asset search."""

    @pytest.mark.asyncio
    async def test_search_assets_no_results(self, service, mock_db):
        """Test asset search with no results."""
        mock_result = MagicMock()
        mock_result.scalars.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.search_assets("nonexistent query")

        assert result["total"] == 0
        assert len(result["results"]) == 0

    @pytest.mark.asyncio
    async def test_search_assets_with_results(self, service, mock_db):
        """Test asset search with matching results."""
        asset = MagicMock(spec=DataAsset)
        asset.id = uuid.uuid4()
        asset.name = "Customer Data"
        asset.description = "Customer information"
        asset.ai_summary = "Contains customer details"
        asset.domain = "sales"
        asset.category = "master_data"
        asset.tags = ["customer", "pii"]
        asset.asset_type = AssetType.TABLE
        asset.usage_count = 100
        asset.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value = [asset]
        mock_db.execute.return_value = mock_result

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "matches": [{
                            "id": str(asset.id),
                            "relevance_score": 0.95,
                            "match_reason": "Contains customer data",
                        }],
                        "search_summary": "Found customer data asset",
                        "suggested_queries": ["customer details"],
                    })
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.search_assets("customer data")

        assert result["total"] == 1
        assert result["results"][0]["relevance_score"] == 0.95


class TestSensitiveFieldDetection(TestAIService):
    """Test sensitive field detection."""

    @pytest.mark.asyncio
    async def test_detect_sensitive_fields(self, service, mock_db):
        """Test AI-powered sensitive field detection."""
        table = MagicMock(spec=MetadataTable)
        table.id = uuid.uuid4()

        column = MagicMock(spec=MetadataColumn)
        column.column_name = "ssn"
        column.data_type = "varchar"

        source = MagicMock(spec=DataSource)
        source.type = "postgresql"
        source.connection_config = {}

        mock_table_result = MagicMock()
        mock_table_result.scalar_one_or_none.return_value = table

        mock_columns_result = MagicMock()
        mock_columns_result.scalars.return_value = [column]

        mock_source_result = MagicMock()
        mock_source_result.scalar_one_or_none.return_value = source

        mock_db.execute.side_effect = [
            mock_table_result,
            mock_columns_result,
            mock_source_result,
        ]

        with patch("app.services.ai_service.get_connector") as mock_connector:
            mock_conn = MagicMock()
            mock_conn.read_data = AsyncMock(return_value=pd.DataFrame({"ssn": ["123-45-6789"]}))
            mock_connector.return_value = mock_conn

            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(
                    message=MagicMock(
                        content=json.dumps({
                            "columns": [{
                                "name": "ssn",
                                "sensitivity_level": "critical",
                                "data_type": "PII",
                                "masking_strategy": "hash",
                                "reason": "Social Security Number",
                            }],
                            "overall_risk": "high",
                            "compliance_notes": ["GDPR relevant"],
                        })
                    )
                )
            ]
            service.client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await service.detect_sensitive_fields(
                source_id=uuid.uuid4(),
                table_name="users",
            )

            assert len(result["columns"]) == 1
            assert result["columns"][0]["sensitivity_level"] == "critical"


class TestTimeSeries(TestAIService):
    """Test time series prediction."""

    @pytest.mark.asyncio
    async def test_predict_time_series_insufficient_data(self, service):
        """Test time series prediction with insufficient data."""
        data = [{"date": "2024-01-01", "value": 100}]

        result = await service.predict_time_series(
            data=data,
            date_column="date",
            value_column="value",
        )

        assert "error" in result
        assert result["min_required"] == 5

    @pytest.mark.asyncio
    async def test_predict_time_series_success(self, service):
        """Test successful time series prediction."""
        data = [
            {"date": "2024-01-01", "value": 100},
            {"date": "2024-01-02", "value": 110},
            {"date": "2024-01-03", "value": 105},
            {"date": "2024-01-04", "value": 115},
            {"date": "2024-01-05", "value": 120},
        ]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "predictions": [
                            {"date": "2024-01-06", "value": 125, "confidence": 0.85},
                        ],
                        "trend": "increasing",
                        "seasonality": "none",
                        "analysis": "Steady growth pattern",
                        "confidence_overall": 0.8,
                    })
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.predict_time_series(
            data=data,
            date_column="date",
            value_column="value",
            periods=1,
        )

        assert "predictions" in result
        assert result["trend"] == "increasing"


class TestClusterAnalysis(TestAIService):
    """Test cluster analysis."""

    @pytest.mark.asyncio
    async def test_cluster_analysis_insufficient_data(self, service):
        """Test cluster analysis with insufficient data."""
        data = [{"feature1": 1, "feature2": 2}]

        result = await service.cluster_analysis(
            data=data,
            features=["feature1", "feature2"],
            n_clusters=3,
        )

        assert "error" in result
        assert result["min_required"] == 3

    @pytest.mark.asyncio
    async def test_cluster_analysis_invalid_features(self, service):
        """Test cluster analysis with invalid features."""
        data = [
            {"feature1": 1, "feature2": 2},
            {"feature1": 2, "feature2": 3},
            {"feature1": 3, "feature2": 4},
        ]

        result = await service.cluster_analysis(
            data=data,
            features=["nonexistent"],
            n_clusters=2,
        )

        assert "error" in result
        assert "No valid features" in result["error"]

    @pytest.mark.asyncio
    async def test_cluster_analysis_success(self, service):
        """Test successful cluster analysis."""
        data = [
            {"age": 25, "income": 50000},
            {"age": 30, "income": 60000},
            {"age": 35, "income": 75000},
            {"age": 45, "income": 90000},
            {"age": 50, "income": 100000},
        ]

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({
                        "cluster_insights": [
                            {
                                "cluster_id": 0,
                                "name": "Young Professionals",
                                "description": "Young people with lower income",
                                "key_characteristics": ["young", "entry-level"],
                            },
                        ],
                        "summary": "Two distinct customer segments",
                        "recommendations": ["Target marketing"],
                    })
                )
            )
        ]
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.cluster_analysis(
            data=data,
            features=["age", "income"],
            n_clusters=2,
        )

        assert "clusters" in result
        assert result["n_clusters"] == 2
        assert "data_with_clusters" in result


class TestSQLValidation(TestAIService):
    """Test SQL validation functionality."""

    @pytest.mark.asyncio
    async def test_validate_sql_safe(self, service, mock_db):
        """Test validating safe SQL."""
        result = await service.validate_sql_query(
            sql="SELECT * FROM users",
            execute=False,
        )

        assert result["is_safe"] is True
        assert len(result["violations"]) == 0

    @pytest.mark.asyncio
    async def test_validate_sql_dangerous(self, service, mock_db):
        """Test validating dangerous SQL."""
        result = await service.validate_sql_query(
            sql="DROP TABLE users",
            execute=False,
        )

        assert result["is_safe"] is False
        assert len(result["violations"]) > 0
        assert "error" in result
