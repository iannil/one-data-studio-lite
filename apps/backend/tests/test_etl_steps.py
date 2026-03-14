from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pandas as pd
import numpy as np

from app.services.etl_engine import (
    FilterStep,
    DeduplicateStep,
    MapValuesStep,
    JoinStep,
    CalculateStep,
    FillMissingStep,
    AIFillMissingStep,
    MaskStep,
    AutoMaskStep,
    RenameStep,
    TypeCastStep,
    AggregateStep,
    SortStep,
    DropColumnsStep,
    SelectColumnsStep,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "age": [25, 30, 35, 30, 28],
        "salary": [50000.0, 60000.0, None, 55000.0, 52000.0],
        "department": ["HR", "IT", "IT", "HR", "Sales"],
    })


class TestFilterStep:
    @pytest.mark.asyncio
    async def test_filter_eq(self, sample_df):
        step = FilterStep({
            "conditions": [{"column": "department", "operator": "eq", "value": "IT"}]
        })
        result = await step.process(sample_df)
        assert len(result) == 2
        assert all(result["department"] == "IT")

    @pytest.mark.asyncio
    async def test_filter_gt(self, sample_df):
        step = FilterStep({
            "conditions": [{"column": "age", "operator": "gt", "value": 28}]
        })
        result = await step.process(sample_df)
        assert len(result) == 3
        assert all(result["age"] > 28)

    @pytest.mark.asyncio
    async def test_filter_in(self, sample_df):
        step = FilterStep({
            "conditions": [{"column": "name", "operator": "in", "value": ["Alice", "Bob"]}]
        })
        result = await step.process(sample_df)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_filter_contains(self, sample_df):
        step = FilterStep({
            "conditions": [{"column": "name", "operator": "contains", "value": "li"}]
        })
        result = await step.process(sample_df)
        assert len(result) == 2  # Alice and Charlie

    @pytest.mark.asyncio
    async def test_filter_is_null(self, sample_df):
        step = FilterStep({
            "conditions": [{"column": "salary", "operator": "is_null"}]
        })
        result = await step.process(sample_df)
        assert len(result) == 1
        assert result.iloc[0]["name"] == "Charlie"


class TestDeduplicateStep:
    @pytest.mark.asyncio
    async def test_deduplicate_all(self):
        df = pd.DataFrame({
            "id": [1, 1, 2, 3],
            "name": ["Alice", "Alice", "Bob", "Charlie"],
        })
        step = DeduplicateStep({})
        result = await step.process(df)
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_deduplicate_by_column(self, sample_df):
        step = DeduplicateStep({"columns": ["age"]})
        result = await step.process(sample_df)
        assert len(result) == 4  # age 30 appears twice


class TestMapValuesStep:
    @pytest.mark.asyncio
    async def test_map_values(self, sample_df):
        step = MapValuesStep({
            "column": "department",
            "mapping": {"HR": "Human Resources", "IT": "Information Technology"},
        })
        result = await step.process(sample_df)
        assert "Human Resources" in result["department"].values
        assert "Information Technology" in result["department"].values
        assert "Sales" in result["department"].values  # Unmapped value preserved


class TestCalculateStep:
    @pytest.mark.asyncio
    async def test_calculate_formula(self, sample_df):
        step = CalculateStep({
            "calculations": [{
                "target_column": "bonus",
                "expression": "salary * 0.1",
                "type": "formula",
            }]
        })
        result = await step.process(sample_df)
        assert "bonus" in result.columns
        assert result.loc[0, "bonus"] == 5000.0

    @pytest.mark.asyncio
    async def test_calculate_concat(self, sample_df):
        step = CalculateStep({
            "calculations": [{
                "target_column": "info",
                "columns": ["name", "department"],
                "separator": " - ",
                "type": "concat",
            }]
        })
        result = await step.process(sample_df)
        assert "info" in result.columns
        assert result.loc[0, "info"] == "Alice - HR"


class TestFillMissingStep:
    @pytest.mark.asyncio
    async def test_fill_value(self, sample_df):
        step = FillMissingStep({
            "fills": [{"column": "salary", "strategy": "value", "value": 0}]
        })
        result = await step.process(sample_df)
        assert result["salary"].isna().sum() == 0
        assert result.loc[2, "salary"] == 0

    @pytest.mark.asyncio
    async def test_fill_mean(self, sample_df):
        step = FillMissingStep({
            "fills": [{"column": "salary", "strategy": "mean"}]
        })
        result = await step.process(sample_df)
        assert result["salary"].isna().sum() == 0
        expected_mean = (50000 + 60000 + 55000 + 52000) / 4
        assert result.loc[2, "salary"] == expected_mean


class TestMaskStep:
    @pytest.mark.asyncio
    async def test_partial_mask(self):
        df = pd.DataFrame({"phone": ["13812345678", "13987654321"]})
        step = MaskStep({
            "masks": [{"column": "phone", "strategy": "partial", "start": 3, "end": 4}]
        })
        result = await step.process(df)
        assert result.loc[0, "phone"] == "138****5678"

    @pytest.mark.asyncio
    async def test_hash_mask(self):
        df = pd.DataFrame({"email": ["test@example.com"]})
        step = MaskStep({
            "masks": [{"column": "email", "strategy": "hash"}]
        })
        result = await step.process(df)
        assert result.loc[0, "email"] != "test@example.com"
        assert len(result.loc[0, "email"]) == 16


class TestRenameStep:
    @pytest.mark.asyncio
    async def test_rename(self, sample_df):
        step = RenameStep({
            "mapping": {"name": "full_name", "age": "years_old"}
        })
        result = await step.process(sample_df)
        assert "full_name" in result.columns
        assert "years_old" in result.columns
        assert "name" not in result.columns


class TestTypeCastStep:
    @pytest.mark.asyncio
    async def test_cast_to_str(self, sample_df):
        step = TypeCastStep({
            "casts": [{"column": "id", "target_type": "str"}]
        })
        result = await step.process(sample_df)
        assert result["id"].dtype == object

    @pytest.mark.asyncio
    async def test_cast_to_float(self, sample_df):
        step = TypeCastStep({
            "casts": [{"column": "age", "target_type": "float"}]
        })
        result = await step.process(sample_df)
        assert result["age"].dtype == float


class TestAggregateStep:
    @pytest.mark.asyncio
    async def test_aggregate(self, sample_df):
        step = AggregateStep({
            "group_by": ["department"],
            "aggregations": {"salary": "mean", "age": "max"}
        })
        result = await step.process(sample_df)
        assert len(result) == 3  # HR, IT, Sales
        assert "department" in result.columns


class TestSortStep:
    @pytest.mark.asyncio
    async def test_sort_ascending(self, sample_df):
        step = SortStep({"columns": ["age"], "ascending": True})
        result = await step.process(sample_df)
        assert result.iloc[0]["age"] == 25
        assert result.iloc[-1]["age"] == 35

    @pytest.mark.asyncio
    async def test_sort_descending(self, sample_df):
        step = SortStep({"columns": ["salary"], "ascending": False})
        result = await step.process(sample_df)
        assert result.iloc[0]["salary"] == 60000.0


class TestDropColumnsStep:
    @pytest.mark.asyncio
    async def test_drop_columns(self, sample_df):
        step = DropColumnsStep({"columns": ["salary", "department"]})
        result = await step.process(sample_df)
        assert "salary" not in result.columns
        assert "department" not in result.columns
        assert "name" in result.columns


class TestSelectColumnsStep:
    @pytest.mark.asyncio
    async def test_select_columns(self, sample_df):
        step = SelectColumnsStep({"columns": ["id", "name"]})
        result = await step.process(sample_df)
        assert list(result.columns) == ["id", "name"]


class TestJoinStep:
    """Tests for JoinStep with external table join."""

    @pytest.fixture
    def left_df(self):
        """Left DataFrame for join tests."""
        return pd.DataFrame({
            "id": [1, 2, 3, 4],
            "name": ["Alice", "Bob", "Charlie", "David"],
            "dept_id": [101, 102, 101, 103],
        })

    @pytest.fixture
    def right_df(self):
        """Right DataFrame for join tests."""
        return pd.DataFrame({
            "dept_id": [101, 102, 104],
            "dept_name": ["Engineering", "Sales", "Marketing"],
        })

    @pytest.mark.asyncio
    async def test_join_inner(self, left_df, right_df):
        """Test inner join."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "inner",
            "on": ["dept_id"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert len(result) == 3  # Only matching dept_ids (101, 102)
        assert "dept_name" in result.columns

    @pytest.mark.asyncio
    async def test_join_left(self, left_df, right_df):
        """Test left join."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "left",
            "on": ["dept_id"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert len(result) == 4  # All left rows preserved
        assert result.loc[result["name"] == "David", "dept_name"].isna().all()

    @pytest.mark.asyncio
    async def test_join_right(self, left_df, right_df):
        """Test right join."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "right",
            "on": ["dept_id"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert len(result) == 4  # All right rows preserved (includes 104)
        assert "Marketing" in result["dept_name"].values

    @pytest.mark.asyncio
    async def test_join_outer(self, left_df, right_df):
        """Test outer join."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "outer",
            "on": ["dept_id"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert len(result) == 5  # All rows from both tables

    @pytest.mark.asyncio
    async def test_join_with_left_right_on(self, left_df):
        """Test join with different column names."""
        right_df = pd.DataFrame({
            "department_id": [101, 102],
            "department_name": ["Engineering", "Sales"],
        })

        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "left",
            "left_on": ["dept_id"],
            "right_on": ["department_id"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert len(result) == 4
        assert "department_name" in result.columns

    @pytest.mark.asyncio
    async def test_join_with_suffixes(self, left_df):
        """Test join with custom suffixes for overlapping columns."""
        right_df = pd.DataFrame({
            "dept_id": [101, 102],
            "name": ["Eng Dept", "Sales Dept"],  # Overlapping column name
        })

        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "inner",
            "on": ["dept_id"],
            "suffixes": ["_person", "_dept"],
        })

        with patch.object(step, "_load_join_table", return_value=right_df):
            result = await step.process(left_df)

        assert "name_person" in result.columns
        assert "name_dept" in result.columns

    @pytest.mark.asyncio
    async def test_join_empty_right_returns_original(self, left_df):
        """Test join with empty right DataFrame returns original."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "inner",
            "on": ["dept_id"],
        })

        with patch.object(step, "_load_join_table", return_value=pd.DataFrame()):
            result = await step.process(left_df)

        pd.testing.assert_frame_equal(result, left_df)

    @pytest.mark.asyncio
    async def test_join_missing_config_raises_error(self, left_df):
        """Test join without on/left_on/right_on raises error."""
        step = JoinStep({
            "source_id": "test-uuid",
            "join_table": "departments",
            "join_type": "inner",
        })

        with patch.object(step, "_load_join_table", return_value=pd.DataFrame({"a": [1]})):
            with pytest.raises(ValueError, match="requires 'on' or 'left_on'/'right_on'"):
                await step.process(left_df)


class TestAIFillMissingStep:
    """Tests for AI-based missing value prediction step."""

    @pytest.fixture
    def df_with_missing(self):
        """DataFrame with missing values for ML prediction."""
        np.random.seed(42)
        return pd.DataFrame({
            "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "feature2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
            "target": [11.0, 22.0, None, 44.0, 55.0, None, 77.0, 88.0, 99.0, 110.0],
        })

    @pytest.mark.asyncio
    async def test_ai_fill_knn(self, df_with_missing):
        """Test KNN-based missing value filling."""
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "knn",
                "params": {"n_neighbors": 3},
            }],
            "fallback_strategy": "mean",
        })
        result = await step.process(df_with_missing)

        assert result["target"].isna().sum() == 0
        assert len(result) == 10
        filled_value_idx2 = result.loc[2, "target"]
        assert filled_value_idx2 > 0

    @pytest.mark.asyncio
    async def test_ai_fill_random_forest(self, df_with_missing):
        """Test Random Forest-based missing value filling."""
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "random_forest",
                "params": {"n_estimators": 10, "max_depth": 3},
            }],
        })
        result = await step.process(df_with_missing)

        assert result["target"].isna().sum() == 0

    @pytest.mark.asyncio
    async def test_ai_fill_linear_regression(self, df_with_missing):
        """Test Linear Regression-based missing value filling."""
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "linear_regression",
            }],
        })
        result = await step.process(df_with_missing)

        assert result["target"].isna().sum() == 0
        predicted_idx2 = result.loc[2, "target"]
        # Linear regression should predict a reasonable value based on pattern
        assert predicted_idx2 > 0

    @pytest.mark.asyncio
    async def test_ai_fill_gradient_boosting(self, df_with_missing):
        """Test Gradient Boosting-based missing value filling."""
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "gradient_boosting",
                "params": {"n_estimators": 10, "max_depth": 2},
            }],
        })
        result = await step.process(df_with_missing)

        assert result["target"].isna().sum() == 0

    @pytest.mark.asyncio
    async def test_ai_fill_no_missing_values(self):
        """Test that no changes are made when there are no missing values."""
        df = pd.DataFrame({
            "feature1": [1.0, 2.0, 3.0],
            "feature2": [10.0, 20.0, 30.0],
            "target": [11.0, 22.0, 33.0],
        })
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "knn",
            }],
        })
        result = await step.process(df)

        pd.testing.assert_frame_equal(result, df)

    @pytest.mark.asyncio
    async def test_ai_fill_fallback_on_insufficient_data(self):
        """Test fallback strategy when training data is insufficient."""
        df = pd.DataFrame({
            "feature1": [1.0, 2.0, 3.0],
            "target": [None, None, 33.0],
        })
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "target",
                "feature_columns": ["feature1"],
                "algorithm": "knn",
            }],
            "fallback_strategy": "mean",
        })
        result = await step.process(df)

        assert result["target"].isna().sum() == 0
        assert result.loc[0, "target"] == 33.0

    @pytest.mark.asyncio
    async def test_ai_fill_classification(self):
        """Test AI fill for classification (low cardinality numeric) target."""
        # Use numeric categories (0, 1) which sklearn handles better
        df = pd.DataFrame({
            "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "feature2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
            "category": [0, 0, None, 1, 1, None, 0, 1, 0, 1],
        })
        step = AIFillMissingStep({
            "fills": [{
                "target_column": "category",
                "feature_columns": ["feature1", "feature2"],
                "algorithm": "random_forest",  # Use RF for better classification
                "params": {"n_estimators": 10, "max_depth": 3},
            }],
        })
        result = await step.process(df)

        assert result["category"].isna().sum() == 0
        # Values should be numeric (filled)

    @pytest.mark.asyncio
    async def test_ai_fill_multiple_columns(self):
        """Test filling multiple columns with different configurations."""
        df = pd.DataFrame({
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
            "t1": [11.0, None, 33.0, 44.0, 55.0, 66.0, 77.0, 88.0],
            "t2": [100.0, 200.0, None, 400.0, 500.0, 600.0, 700.0, 800.0],
        })
        step = AIFillMissingStep({
            "fills": [
                {
                    "target_column": "t1",
                    "feature_columns": ["f1", "f2"],
                    "algorithm": "knn",
                },
                {
                    "target_column": "t2",
                    "feature_columns": ["f1", "f2"],
                    "algorithm": "linear_regression",
                },
            ],
        })
        result = await step.process(df)

        assert result["t1"].isna().sum() == 0
        assert result["t2"].isna().sum() == 0


class TestAutoMaskStep:
    """Tests for automatic sensitive data masking step."""

    @pytest.mark.asyncio
    async def test_auto_mask_email(self):
        """Test automatic email detection and masking."""
        df = pd.DataFrame({
            "email": ["alice@example.com", "bob@test.org", "charlie@domain.net"],
            "user_id": [1, 2, 3],  # Use non-sensitive column name
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
            "default_strategy": "partial",
        })
        result = await step.process(df)

        assert result.loc[0, "email"] != "alice@example.com"
        assert "@" not in result.loc[0, "email"] or "*" in result.loc[0, "email"]
        assert result.loc[0, "user_id"] == 1  # Non-sensitive column preserved

    @pytest.mark.asyncio
    async def test_auto_mask_phone(self):
        """Test automatic phone number detection and masking."""
        df = pd.DataFrame({
            "phone": ["13812345678", "13987654321"],
            "id": [1, 2],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
        })
        result = await step.process(df)

        assert "*" in result.loc[0, "phone"]
        assert result.loc[0, "phone"].startswith("138")
        assert result.loc[0, "phone"].endswith("5678")

    @pytest.mark.asyncio
    async def test_auto_mask_by_column_name(self):
        """Test masking based on column name patterns."""
        df = pd.DataFrame({
            "user_email": ["test@test.com"],
            "phone_number": ["1234567890"],
            "ssn": ["123-45-6789"],
            "password": ["secret123"],
            "normal_column": ["value"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
        })
        result = await step.process(df)

        assert "*" in result.loc[0, "user_email"] or result.loc[0, "user_email"] != "test@test.com"
        assert "*" in result.loc[0, "phone_number"] or len(result.loc[0, "phone_number"]) == 16
        assert result.loc[0, "ssn"] != "123-45-6789"
        assert result.loc[0, "password"] != "secret123"
        assert result.loc[0, "normal_column"] == "value"

    @pytest.mark.asyncio
    async def test_auto_mask_hash_strategy(self):
        """Test hash masking strategy."""
        df = pd.DataFrame({
            "password": ["secret123", "password456"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "low",
            "default_strategy": "hash",
        })
        result = await step.process(df)

        assert result.loc[0, "password"] != "secret123"
        assert len(result.loc[0, "password"]) == 16

    @pytest.mark.asyncio
    async def test_auto_mask_skip_columns(self):
        """Test skipping specified columns from masking."""
        df = pd.DataFrame({
            "email": ["alice@example.com"],
            "phone": ["13812345678"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "low",
            "skip_columns": ["email"],
        })
        result = await step.process(df)

        assert result.loc[0, "email"] == "alice@example.com"
        assert "*" in result.loc[0, "phone"]

    @pytest.mark.asyncio
    async def test_auto_mask_column_overrides(self):
        """Test custom masking configuration for specific columns."""
        df = pd.DataFrame({
            "email": ["alice@example.com"],
            "phone_number": ["13812345678"],  # Sensitive column
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
            "column_overrides": {
                "phone_number": {
                    "strategy": "replace",
                    "replacement": "[REDACTED]",
                },
            },
        })
        result = await step.process(df)

        assert result.loc[0, "phone_number"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_auto_mask_high_threshold(self):
        """Test that lower sensitivity items are not masked with high threshold."""
        df = pd.DataFrame({
            "name": ["Alice Smith"],
            "email": ["alice@example.com"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "critical",
        })
        result = await step.process(df)

        assert result.loc[0, "name"] == "Alice Smith"

    @pytest.mark.asyncio
    async def test_auto_mask_ip_address(self):
        """Test automatic IP address detection and masking."""
        df = pd.DataFrame({
            "ip_address": ["192.168.1.100", "10.0.0.1"],
            "user_agent": ["Mozilla/5.0", "Chrome/91.0"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
        })
        result = await step.process(df)

        assert "*" in result.loc[0, "ip_address"]

    @pytest.mark.asyncio
    async def test_auto_mask_custom_mask_char(self):
        """Test custom masking character."""
        df = pd.DataFrame({
            "phone": ["13812345678"],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
            "mask_char": "#",
        })
        result = await step.process(df)

        assert "#" in result.loc[0, "phone"]
        assert "*" not in result.loc[0, "phone"]

    @pytest.mark.asyncio
    async def test_auto_mask_handles_null_values(self):
        """Test that null values are handled correctly."""
        df = pd.DataFrame({
            "email": ["alice@example.com", None, "bob@test.com"],
            "phone": [None, "13812345678", None],
        })
        step = AutoMaskStep({
            "sensitivity_threshold": "medium",
        })
        result = await step.process(df)

        assert pd.isna(result.loc[1, "email"])
        assert pd.isna(result.loc[0, "phone"])
        assert pd.isna(result.loc[2, "phone"])
