"""
Test data initialization script for E2E testing with real database.

Creates 5 test users with proper roles and permissions:
1. Super Admin - admin@test.com (is_superuser=True)
2. Data Engineer - engineer@test.com (data_engineer role)
3. Data Analyst - analyst@test.com (data_analyst role)
4. Asset Admin - asset_admin@test.com (asset_admin role)
5. Security Admin - security@test.com (security_admin role)
"""
from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import User, Role, UserRole


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


async def create_roles(session: AsyncSession) -> dict[str, Role]:
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


async def create_test_users(session: AsyncSession) -> dict[str, User]:
    """Create all test users if they don't exist."""
    roles = await create_roles(session)
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

        users[user_data["role_name"]] = user

    await session.commit()
    return users


async def get_test_user(session: AsyncSession, email: str) -> User | None:
    """Get a test user by email."""
    result = await session.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_test_user_by_role(session: AsyncSession, role_name: str) -> User | None:
    """Get a test user by role name."""
    email_map = {
        "superuser": "admin@test.com",
        "data_engineer": "engineer@test.com",
        "data_analyst": "analyst@test.com",
        "asset_admin": "asset_admin@test.com",
        "security_admin": "security@test.com",
    }
    email = email_map.get(role_name)
    if email:
        return await get_test_user(session, email)
    return None


async def setup_test_database():
    """Initialize database with tables and test data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        users = await create_test_users(session)
        return users


async def cleanup_test_database():
    """Drop all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


if __name__ == "__main__":
    async def main():
        print("Setting up test database...")
        users = await setup_test_database()
        print(f"Created {len(users)} test users:")
        for role, user in users.items():
            print(f"  - {role}: {user.email} (id: {user.id})")

    asyncio.run(main())
