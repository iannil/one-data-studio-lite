"""
Pytest configuration and shared fixtures for E2E testing with real database.

This module provides:
- Async test client fixtures
- Real database session fixtures
- User authentication fixtures for all 5 roles
- Database initialization and cleanup
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import create_access_token, get_password_hash
from app.models import User, Role, UserRole
from tests.fixtures.test_users import ROLE_PERMISSIONS


TEST_USERS = [
    {
        "email": "admin@test.com",
        "password": "admin_password_123",
        "full_name": "Super Admin",
        "is_superuser": True,
        "role_name": "superuser",
    },
    {
        "email": "engineer@test.com",
        "password": "engineer_password_123",
        "full_name": "Data Engineer",
        "is_superuser": False,
        "role_name": "data_engineer",
    },
    {
        "email": "analyst@test.com",
        "password": "analyst_password_123",
        "full_name": "Data Analyst",
        "is_superuser": False,
        "role_name": "data_analyst",
    },
    {
        "email": "asset_admin@test.com",
        "password": "asset_admin_password_123",
        "full_name": "Asset Admin",
        "is_superuser": False,
        "role_name": "asset_admin",
    },
    {
        "email": "security@test.com",
        "password": "security_password_123",
        "full_name": "Security Admin",
        "is_superuser": False,
        "role_name": "security_admin",
    },
]


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


async def _create_roles(session: AsyncSession) -> dict[str, Role]:
    """Create all roles if they don't exist."""
    roles = {}
    for role_name, permissions in ROLE_PERMISSIONS.items():
        result = await session.execute(
            select(Role).where(Role.name == role_name)
        )
        role = result.scalar_one_or_none()
        if not role:
            role = Role(
                name=role_name,
                description=f"{role_name.replace('_', ' ').title()} role",
                permissions=permissions,
            )
            session.add(role)
            await session.flush()
        roles[role_name] = role
    return roles


async def _create_test_users(session: AsyncSession) -> dict[str, dict]:
    """Create all test users if they don't exist."""
    roles = await _create_roles(session)
    users = {}

    for user_data in TEST_USERS:
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                is_active=True,
                is_superuser=user_data["is_superuser"],
            )
            session.add(user)
            await session.flush()

            role = roles[user_data["role_name"]]
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
            )
            session.add(user_role)

        users[user_data["role_name"]] = {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        }

    await session.commit()
    return users


_test_users_cache: dict[str, dict] = {}


@pytest_asyncio.fixture(scope="session")
async def init_database():
    """Initialize database with tables and test data (session-scoped)."""
    global _test_users_cache

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        _test_users_cache = await _create_test_users(session)

    yield _test_users_cache

    # Keep tables for inspection after tests


@pytest_asyncio.fixture
async def async_client(init_database) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def superuser_headers(init_database) -> dict[str, str]:
    """Create auth headers for superuser."""
    user_data = init_database["superuser"]
    token = create_access_token(user_data["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superuser_mock(init_database):
    """Return superuser data (for backward compatibility)."""
    user_data = init_database["superuser"]
    mock = MagicMock()
    mock.id = UUID(user_data["id"])
    mock.email = user_data["email"]
    mock.full_name = user_data["full_name"]
    mock.is_active = user_data["is_active"]
    mock.is_superuser = user_data["is_superuser"]
    return mock


@pytest.fixture
def data_engineer_headers(init_database) -> dict[str, str]:
    """Create auth headers for data engineer."""
    user_data = init_database["data_engineer"]
    token = create_access_token(user_data["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def data_engineer_mock(init_database):
    """Return data engineer data (for backward compatibility)."""
    user_data = init_database["data_engineer"]
    mock = MagicMock()
    mock.id = UUID(user_data["id"])
    mock.email = user_data["email"]
    mock.full_name = user_data["full_name"]
    mock.is_active = user_data["is_active"]
    mock.is_superuser = user_data["is_superuser"]
    return mock


@pytest.fixture
def data_analyst_headers(init_database) -> dict[str, str]:
    """Create auth headers for data analyst."""
    user_data = init_database["data_analyst"]
    token = create_access_token(user_data["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def data_analyst_mock(init_database):
    """Return data analyst data (for backward compatibility)."""
    user_data = init_database["data_analyst"]
    mock = MagicMock()
    mock.id = UUID(user_data["id"])
    mock.email = user_data["email"]
    mock.full_name = user_data["full_name"]
    mock.is_active = user_data["is_active"]
    mock.is_superuser = user_data["is_superuser"]
    return mock


@pytest.fixture
def asset_admin_headers(init_database) -> dict[str, str]:
    """Create auth headers for asset admin."""
    user_data = init_database["asset_admin"]
    token = create_access_token(user_data["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def asset_admin_mock(init_database):
    """Return asset admin data (for backward compatibility)."""
    user_data = init_database["asset_admin"]
    mock = MagicMock()
    mock.id = UUID(user_data["id"])
    mock.email = user_data["email"]
    mock.full_name = user_data["full_name"]
    mock.is_active = user_data["is_active"]
    mock.is_superuser = user_data["is_superuser"]
    return mock


@pytest.fixture
def security_admin_headers(init_database) -> dict[str, str]:
    """Create auth headers for security admin."""
    user_data = init_database["security_admin"]
    token = create_access_token(user_data["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def security_admin_mock(init_database):
    """Return security admin data (for backward compatibility)."""
    user_data = init_database["security_admin"]
    mock = MagicMock()
    mock.id = UUID(user_data["id"])
    mock.email = user_data["email"]
    mock.full_name = user_data["full_name"]
    mock.is_active = user_data["is_active"]
    mock.is_superuser = user_data["is_superuser"]
    return mock


@pytest.fixture
def sample_data_source_config() -> dict:
    """Sample data source configuration."""
    return {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "test_user",
        "password": "test_password",
    }


@pytest.fixture
def sample_etl_pipeline_config() -> dict:
    """Sample ETL pipeline configuration."""
    return {
        "name": "Test Pipeline",
        "description": "Test ETL pipeline",
        "source_type": "postgresql",
        "source_config": {
            "table": "source_table",
        },
        "target_type": "postgresql",
        "target_config": {
            "table": "target_table",
        },
        "steps": [
            {
                "name": "Filter Step",
                "step_type": "filter",
                "config": {"column": "status", "operator": "eq", "value": "active"},
                "order": 0,
                "is_enabled": True,
            }
        ],
    }


@pytest.fixture
def sample_alert_rule_config() -> dict:
    """Sample alert rule configuration."""
    return {
        "name": "Test Alert Rule",
        "description": "Test alert rule for E2E testing",
        "metric_sql": "SELECT COUNT(*) FROM users WHERE status = 'inactive'",
        "metric_name": "inactive_users_count",
        "condition": "gt",
        "threshold": 100.0,
        "severity": "warning",
        "check_interval_minutes": 15,
        "cooldown_minutes": 60,
        "notification_channels": ["email"],
        "notification_config": {"email": "admin@test.com"},
    }


@pytest.fixture
def sample_asset_config() -> dict:
    """Sample data asset configuration."""
    return {
        "name": "Test Asset",
        "description": "Test data asset for E2E testing",
        "asset_type": "table",
        "source_table": "users",
        "source_schema": "public",
        "source_database": "test_db",
        "department": "Engineering",
        "access_level": "internal",
        "tags": ["test", "e2e"],
        "category": "master_data",
        "domain": "user",
    }


@pytest.fixture(autouse=True)
def mock_ai_service():
    """Mock AIService to avoid real OpenAI API calls."""
    mock_instance = MagicMock()
    mock_instance.natural_language_to_sql = AsyncMock(return_value={
        "sql": "SELECT * FROM users LIMIT 10",
        "data": [{"id": 1, "name": "test"}],
        "row_count": 1,
        "explanation": "Query to fetch users"
    })
    mock_instance.text_to_sql = AsyncMock(return_value={
        "sql": "SELECT * FROM users LIMIT 10",
        "explanation": "Query to fetch users"
    })
    mock_instance.analyze_field = AsyncMock(return_value={
        "field_type": "string",
        "suggestions": []
    })
    mock_instance.suggest_cleaning_rules = AsyncMock(return_value={
        "data_quality_summary": {
            "overall_score": 0.85,
            "critical_issues": [],
            "recommendations": []
        }
    })
    mock_instance.predict_fill = AsyncMock(return_value={"predictions": []})

    mock_class = MagicMock(return_value=mock_instance)

    with patch("app.api.v1.analysis.AIService", mock_class), \
         patch("app.services.AIService", mock_class), \
         patch("app.services.ai_service.AIService", mock_class):
        yield mock_instance


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Clear any dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()
