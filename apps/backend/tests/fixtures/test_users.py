"""
User fixtures for different role-based testing scenarios.

This module provides fixtures for 5 user types:
1. Superuser (Admin) - Full system access
2. Data Engineer - Data source, ETL, collection management
3. Data Analyst - Query, analysis, asset search
4. Asset Admin - Asset catalog management
5. Security Admin - Alert rules, sensitive data detection
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TestUserData:
    """Immutable test user data."""

    id: UUID
    email: str
    password: str
    full_name: str
    is_active: bool
    is_superuser: bool
    role_name: str
    permissions: list[str]


# Define role permissions based on the system design
ROLE_PERMISSIONS = {
    "superuser": [
        "users:read",
        "users:write",
        "roles:read",
        "roles:write",
        "audit:read",
    ],
    "data_engineer": [
        "sources:read",
        "sources:write",
        "metadata:read",
        "metadata:write",
        "collect:read",
        "collect:write",
        "etl:read",
        "etl:write",
    ],
    "data_analyst": [
        "analysis:read",
        "analysis:write",
        "assets:read",
        "assets:search",
        "lineage:read",
    ],
    "asset_admin": [
        "assets:read",
        "assets:write",
        "assets:certify",
        "lineage:read",
        "lineage:write",
    ],
    "security_admin": [
        "security:read",
        "security:write",
        "alerts:read",
        "alerts:write",
        "alerts:manage",
    ],
}


def create_superuser() -> TestUserData:
    """Create a superuser test fixture."""
    return TestUserData(
        id=uuid4(),
        email="admin@test.com",
        password="admin_password_123",
        full_name="Super Admin",
        is_active=True,
        is_superuser=True,
        role_name="superuser",
        permissions=ROLE_PERMISSIONS["superuser"],
    )


def create_data_engineer() -> TestUserData:
    """Create a data engineer test fixture."""
    return TestUserData(
        id=uuid4(),
        email="engineer@test.com",
        password="engineer_password_123",
        full_name="Data Engineer",
        is_active=True,
        is_superuser=False,
        role_name="data_engineer",
        permissions=ROLE_PERMISSIONS["data_engineer"],
    )


def create_data_analyst() -> TestUserData:
    """Create a data analyst test fixture."""
    return TestUserData(
        id=uuid4(),
        email="analyst@test.com",
        password="analyst_password_123",
        full_name="Data Analyst",
        is_active=True,
        is_superuser=False,
        role_name="data_analyst",
        permissions=ROLE_PERMISSIONS["data_analyst"],
    )


def create_asset_admin() -> TestUserData:
    """Create an asset admin test fixture."""
    return TestUserData(
        id=uuid4(),
        email="asset_admin@test.com",
        password="asset_admin_password_123",
        full_name="Asset Admin",
        is_active=True,
        is_superuser=False,
        role_name="asset_admin",
        permissions=ROLE_PERMISSIONS["asset_admin"],
    )


def create_security_admin() -> TestUserData:
    """Create a security admin test fixture."""
    return TestUserData(
        id=uuid4(),
        email="security@test.com",
        password="security_password_123",
        full_name="Security Admin",
        is_active=True,
        is_superuser=False,
        role_name="security_admin",
        permissions=ROLE_PERMISSIONS["security_admin"],
    )


def get_all_test_users() -> dict[str, TestUserData]:
    """Return all test users as a dictionary."""
    return {
        "superuser": create_superuser(),
        "data_engineer": create_data_engineer(),
        "data_analyst": create_data_analyst(),
        "asset_admin": create_asset_admin(),
        "security_admin": create_security_admin(),
    }


def create_mock_user(user_data: TestUserData) -> Any:
    """Create a mock user object from TestUserData."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.id = user_data.id
    mock.email = user_data.email
    mock.full_name = user_data.full_name
    mock.is_active = user_data.is_active
    mock.is_superuser = user_data.is_superuser
    return mock
