from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserUpdate, LoginRequest
from app.schemas.metadata import DataSourceCreate, MetadataScanRequest
from app.schemas.etl import ETLPipelineCreate, ETLStepCreate
from app.schemas.asset import DataAssetCreate, AssetSearchRequest
from app.schemas.alert import AlertRuleCreate
from app.models.metadata import DataSourceType
from app.models.etl import ETLStepType
from app.models.asset import AssetType, AccessLevel


class TestUserSchemas:
    def test_user_create_valid(self):
        user = UserCreate(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
        )
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"

    def test_user_create_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                password="password123",
                full_name="Test User",
            )

    def test_login_request_valid(self):
        login = LoginRequest(
            email="test@example.com",
            password="password123",
        )
        assert login.email == "test@example.com"


class TestDataSourceSchemas:
    def test_data_source_create_valid(self):
        source = DataSourceCreate(
            name="Test DB",
            type=DataSourceType.POSTGRESQL,
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "testdb",
            },
        )
        assert source.name == "Test DB"
        assert source.type == DataSourceType.POSTGRESQL

    def test_data_source_create_empty_name(self):
        with pytest.raises(ValidationError):
            DataSourceCreate(
                name="",
                type=DataSourceType.POSTGRESQL,
                connection_config={},
            )

    def test_metadata_scan_request_defaults(self):
        request = MetadataScanRequest()
        assert request.include_row_count is False
        assert request.table_filter is None


class TestETLSchemas:
    def test_etl_step_create_valid(self):
        step = ETLStepCreate(
            name="Filter Step",
            step_type=ETLStepType.FILTER,
            config={"conditions": [{"column": "status", "operator": "eq", "value": "active"}]},
            order=1,
        )
        assert step.name == "Filter Step"
        assert step.step_type == ETLStepType.FILTER

    def test_etl_pipeline_create_valid(self):
        pipeline = ETLPipelineCreate(
            name="Test Pipeline",
            source_type="table",
            source_config={"source_id": "123", "table_name": "users"},
            target_type="table",
            target_config={"table_name": "users_clean"},
            steps=[
                ETLStepCreate(
                    name="Dedupe",
                    step_type=ETLStepType.DEDUPLICATE,
                    config={},
                    order=1,
                ),
            ],
        )
        assert pipeline.name == "Test Pipeline"
        assert len(pipeline.steps) == 1


class TestAssetSchemas:
    def test_data_asset_create_valid(self):
        asset = DataAssetCreate(
            name="Sales Data",
            asset_type=AssetType.TABLE,
            access_level=AccessLevel.INTERNAL,
            tags=["sales", "revenue"],
        )
        assert asset.name == "Sales Data"
        assert asset.asset_type == AssetType.TABLE

    def test_asset_search_request_defaults(self):
        request = AssetSearchRequest(query="sales")
        assert request.query == "sales"
        assert request.limit == 20


class TestAlertSchemas:
    def test_alert_rule_create_valid(self):
        rule = AlertRuleCreate(
            name="High Error Rate",
            metric_sql="SELECT COUNT(*) as errors FROM logs WHERE level = 'error'",
            metric_name="errors",
            condition="gt",
            threshold=100,
        )
        assert rule.name == "High Error Rate"
        assert rule.condition == "gt"
        assert rule.threshold == 100
