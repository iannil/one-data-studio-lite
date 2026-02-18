"""Tests for data standard service functionality."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.models.standard import (
    ComplianceResult,
    DataStandard,
    StandardApplication,
    StandardStatus,
    StandardType,
)
from app.services.standard_service import StandardService


class TestStandardService:
    """Test suite for StandardService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a StandardService instance with mock database."""
        return StandardService(mock_db)

    @pytest.fixture
    def sample_standard(self):
        """Create a sample DataStandard for testing."""
        standard = MagicMock(spec=DataStandard)
        standard.id = uuid.uuid4()
        standard.name = "Email Format Standard"
        standard.code = "EMAIL_FMT_001"
        standard.description = "Standard for email field format"
        standard.standard_type = StandardType.FIELD_FORMAT
        standard.status = StandardStatus.DRAFT
        standard.rules = {
            "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$",
            "max_length": 255,
        }
        standard.version = 1
        return standard

    @pytest.fixture
    def sample_dataframe(self):
        """Create a sample DataFrame for testing."""
        return pd.DataFrame({
            "email": [
                "test@example.com",
                "invalid-email",
                "valid.user@domain.org",
                None,
                "another@test.co.uk",
            ],
            "age": [25, 30, 35, -5, 150],
            "status": ["active", "inactive", "active", "pending", "invalid"],
        })


class TestFieldFormatCompliance(TestStandardService):
    """Test field format compliance checking."""

    def test_check_field_format_pattern_valid(self, service):
        """Test field format check with valid pattern."""
        data = pd.Series(["2024-01-15", "2024-02-20", "2024-03-25"])
        rules = {"pattern": r"^\d{4}-\d{2}-\d{2}$"}

        compliant, violated, violations = service._check_field_format(data, rules)

        assert compliant == 3
        assert violated == 0
        assert len(violations) == 0

    def test_check_field_format_pattern_invalid(self, service):
        """Test field format check with invalid values."""
        data = pd.Series(["2024-01-15", "invalid", "2024-03-25", "not-a-date"])
        rules = {"pattern": r"^\d{4}-\d{2}-\d{2}$"}

        compliant, violated, violations = service._check_field_format(data, rules)

        assert compliant == 2
        assert violated == 2
        assert len(violations) == 2

    def test_check_field_format_length_constraints(self, service):
        """Test field format check with length constraints."""
        data = pd.Series(["short", "medium_length", "very_long_string_here"])
        rules = {"min_length": 6, "max_length": 15}

        compliant, violated, violations = service._check_field_format(data, rules)

        assert compliant == 1
        assert violated == 2

    def test_check_field_format_null_handling_allowed(self, service):
        """Test field format check with null values allowed."""
        data = pd.Series(["valid", None, "also_valid"])
        rules = {"pattern": r"^\w+$", "allow_null": True}

        compliant, violated, violations = service._check_field_format(data, rules)

        assert compliant == 3
        assert violated == 0

    def test_check_field_format_null_handling_not_allowed(self, service):
        """Test field format check with null values not allowed."""
        data = pd.Series(["valid", None, "also_valid"])
        rules = {"pattern": r"^\w+$", "allow_null": False}

        compliant, violated, violations = service._check_field_format(data, rules)

        assert compliant == 2
        assert violated == 1


class TestValueDomainCompliance(TestStandardService):
    """Test value domain compliance checking."""

    def test_check_value_domain_allowed_values(self, service):
        """Test value domain check with allowed values list."""
        data = pd.Series(["active", "inactive", "pending", "invalid_status"])
        rules = {"allowed_values": ["active", "inactive", "pending"]}

        compliant, violated, violations = service._check_value_domain(data, rules)

        assert compliant == 3
        assert violated == 1

    def test_check_value_domain_numeric_range(self, service):
        """Test value domain check with numeric range."""
        data = pd.Series([25, 30, 150, -5, 65])
        rules = {"range": {"min": 0, "max": 120}}

        compliant, violated, violations = service._check_value_domain(data, rules)

        assert compliant == 3
        assert violated == 2

    def test_check_value_domain_null_handling(self, service):
        """Test value domain check with null values."""
        data = pd.Series(["A", None, "B"])
        rules = {"allowed_values": ["A", "B"], "allow_null": False}

        compliant, violated, violations = service._check_value_domain(data, rules)

        assert compliant == 2
        assert violated == 1


class TestDataQualityCompliance(TestStandardService):
    """Test data quality compliance checking."""

    def test_check_data_quality_completeness(self, service):
        """Test data quality completeness check."""
        data = pd.Series([1, 2, None, 4, 5, None])
        rules = {"completeness": 0.8}

        compliant, violated, violations = service._check_data_quality(data, rules)

        assert violated == 2

    def test_check_data_quality_not_null(self, service):
        """Test data quality not null constraint."""
        data = pd.Series([1, 2, None, 4, 5])
        rules = {"not_null": True}

        compliant, violated, violations = service._check_data_quality(data, rules)

        assert violated == 1
        assert any("Not null constraint" in v["reason"] for v in violations)

    def test_check_data_quality_uniqueness(self, service):
        """Test data quality uniqueness constraint."""
        data = pd.Series([1, 2, 2, 3, 3, 3])
        rules = {"uniqueness": True}

        compliant, violated, violations = service._check_data_quality(data, rules)

        assert violated == 3
        assert any("Uniqueness constraint" in v["reason"] for v in violations)


class TestStandardOperations(TestStandardService):
    """Test standard CRUD operations."""

    @pytest.mark.asyncio
    async def test_check_compliance_creates_result(
        self, service, mock_db, sample_standard, sample_dataframe
    ):
        """Test compliance check creates a result record."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        result = await service.check_compliance(
            standard_id=sample_standard.id,
            data=sample_dataframe,
            column_name="email",
            table_name="users",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert isinstance(result, ComplianceResult)

    @pytest.mark.asyncio
    async def test_check_compliance_standard_not_found(self, service, mock_db, sample_dataframe):
        """Test compliance check raises error when standard not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Standard not found"):
            await service.check_compliance(
                standard_id=uuid.uuid4(),
                data=sample_dataframe,
                column_name="email",
            )

    @pytest.mark.asyncio
    async def test_check_compliance_column_not_found(
        self, service, mock_db, sample_standard, sample_dataframe
    ):
        """Test compliance check raises error when column not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Column not found"):
            await service.check_compliance(
                standard_id=sample_standard.id,
                data=sample_dataframe,
                column_name="nonexistent_column",
            )

    @pytest.mark.asyncio
    async def test_apply_standard(self, service, mock_db, sample_standard):
        """Test applying a standard to a target."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        result = await service.apply_standard(
            standard_id=sample_standard.id,
            target_type="column",
            table_name="users",
            column_name="email",
            is_mandatory=True,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert isinstance(result, StandardApplication)

    @pytest.mark.asyncio
    async def test_approve_standard(self, service, mock_db, sample_standard):
        """Test approving a standard."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        approver_id = uuid.uuid4()
        result = await service.approve_standard(
            standard_id=sample_standard.id,
            approved_by=approver_id,
        )

        assert sample_standard.status == StandardStatus.APPROVED
        assert sample_standard.approved_by == approver_id
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_already_approved_standard(self, service, mock_db, sample_standard):
        """Test approving an already approved standard raises error."""
        sample_standard.status = StandardStatus.APPROVED

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        with pytest.raises(ValueError, match="already approved"):
            await service.approve_standard(
                standard_id=sample_standard.id,
                approved_by=uuid.uuid4(),
            )

    @pytest.mark.asyncio
    async def test_create_new_version(self, service, mock_db, sample_standard):
        """Test creating a new version of a standard."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_standard
        mock_db.execute.return_value = mock_result

        new_rules = {**sample_standard.rules, "max_length": 100}

        result = await service.create_new_version(
            standard_id=sample_standard.id,
            updated_rules=new_rules,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert isinstance(result, DataStandard)

    @pytest.mark.asyncio
    async def test_get_standards_by_type(self, service, mock_db, sample_standard):
        """Test getting standards filtered by type."""
        mock_result = MagicMock()
        mock_result.scalars.return_value = [sample_standard]
        mock_db.execute.return_value = mock_result

        results = await service.get_standards_by_type(
            standard_type=StandardType.FIELD_FORMAT,
            status=StandardStatus.DRAFT,
        )

        assert len(results) == 1
        assert results[0] == sample_standard


class TestViolationCategorization(TestStandardService):
    """Test violation categorization."""

    def test_categorize_violations_empty(self, service):
        """Test categorizing empty violations list."""
        result = service._categorize_violations([])
        assert result == {}

    def test_categorize_violations_single_type(self, service):
        """Test categorizing violations of single type."""
        violations = [
            {"value": "x", "reason": "Pattern mismatch", "row_index": 1},
            {"value": "y", "reason": "Pattern mismatch", "row_index": 2},
        ]

        result = service._categorize_violations(violations)

        assert result["pattern_mismatch"] == 2

    def test_categorize_violations_multiple_types(self, service):
        """Test categorizing violations of multiple types."""
        violations = [
            {"value": "x", "reason": "Pattern mismatch", "row_index": 1},
            {"value": "y", "reason": "Length exceeded", "row_index": 2},
            {"value": "z", "reason": "Pattern mismatch", "row_index": 3},
        ]

        result = service._categorize_violations(violations)

        assert result["pattern_mismatch"] == 2
        assert result["length_exceeded"] == 1


class TestAISuggestions(TestStandardService):
    """Test AI-powered standard suggestions."""

    @pytest.mark.asyncio
    async def test_create_standard_from_suggestion(self, service, mock_db):
        """Test creating a standard from an AI suggestion."""
        suggestion = {
            "name": "Phone Number Format",
            "code": "PHONE_FMT_001",
            "description": "Standard for phone number formatting",
            "type": "field_format",
            "rules": {
                "pattern": r"^\+?[1-9]\d{1,14}$",
            },
            "confidence": 0.92,
        }

        result = await service.create_standard_from_suggestion(
            suggestion=suggestion,
            owner_id=uuid.uuid4(),
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert isinstance(result, DataStandard)
        assert result.name == "Phone Number Format"
        assert result.ai_suggested is True
        assert result.ai_confidence == 0.92
