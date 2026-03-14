"""Initialize admin user for the platform."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import User


async def create_admin_user():
    """Create admin user if not exists."""

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing = result.scalar_one_or_none()

        if existing:
            print("Admin user already exists:")
            print(f"  Email: admin@example.com")
            print(f"  ID: {existing.id}")
            return

        # Create admin user
        admin = User(
            email="admin@example.com",
            hashed_password=get_password_hash("admin123456"),
            full_name="系统管理员",
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print("=" * 50)
        print("Admin user created successfully!")
        print("=" * 50)
        print(f"  Email:    admin@example.com")
        print(f"  Password: admin123456")
        print(f"  ID:       {admin.id}")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(create_admin_user())
