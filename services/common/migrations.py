"""数据库迁移脚本

初始化数据库表并插入默认数据。

运行方式:
    python -m services.common.migrations
    或
    python services/common/migrations.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.common.database import Base, get_database_url
from services.common.orm_models import (
    UserORM,
    RoleORM,
    PermissionORM,
    RolePermissionORM,
    ServiceAccountORM,
    SystemConfigORM,
)

logger = logging.getLogger(__name__)


# ============================================================
# 默认权限定义
# ============================================================

DEFAULT_PERMISSIONS = [
    # 数据权限
    ("data:read", "读取数据", "数据读取权限"),
    ("data:write", "写入数据", "数据写入权限"),
    ("data:delete", "删除数据", "数据删除权限"),

    # Pipeline 权限
    ("pipeline:read", "查看Pipeline", "查看数据流权限"),
    ("pipeline:run", "运行Pipeline", "执行数据流权限"),
    ("pipeline:manage", "管理Pipeline", "创建/修改/删除数据流权限"),

    # 系统权限
    ("system:admin", "系统管理", "系统管理权限"),
    ("system:user:manage", "用户管理", "用户管理权限"),
    ("system:config", "配置管理", "系统配置权限"),
    ("system:super_admin", "超级管理员", "超级管理员权限"),

    # 元数据权限
    ("metadata:read", "读取元数据", "查看元数据权限"),
    ("metadata:write", "写入元数据", "修改元数据权限"),

    # 敏感数据权限
    ("sensitive:read", "查看敏感数据", "查看敏感数据权限"),
    ("sensitive:manage", "管理敏感数据", "管理敏感数据权限"),

    # 审计权限
    ("audit:read", "查看审计日志", "查看审计日志权限"),

    # 质量管理权限
    ("quality:read", "查看质量", "查看数据质量权限"),
    ("quality:manage", "管理质量", "管理数据质量权限"),

    # 服务调用权限
    ("service:call", "服务调用", "服务间调用权限"),
]


# ============================================================
# 默认角色及其权限
# ============================================================

DEFAULT_ROLES = [
    {
        "role_code": "super_admin",
        "role_name": "超级管理员",
        "description": "系统最高权限管理员",
        "is_system": True,
        "permissions": [p[0] for p in DEFAULT_PERMISSIONS],  # 所有权限
    },
    {
        "role_code": "admin",
        "role_name": "管理员",
        "description": "系统管理员",
        "is_system": True,
        "permissions": [
            "data:read", "data:write", "data:delete",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "system:admin", "system:user:manage", "system:config",
            "metadata:read", "metadata:write",
            "sensitive:read", "sensitive:manage",
            "audit:read",
            "quality:read", "quality:manage",
        ],
    },
    {
        "role_code": "data_scientist",
        "role_name": "数据科学家",
        "description": "数据分析与挖掘人员",
        "is_system": True,
        "permissions": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run",
            "metadata:read", "metadata:write",
            "sensitive:read",
        ],
    },
    {
        "role_code": "analyst",
        "role_name": "数据分析师",
        "description": "数据分析人员",
        "is_system": True,
        "permissions": [
            "data:read",
            "pipeline:read",
            "metadata:read",
        ],
    },
    {
        "role_code": "engineer",
        "role_name": "数据工程师",
        "description": "数据开发与运维人员",
        "is_system": True,
        "permissions": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "metadata:read", "metadata:write",
        ],
    },
    {
        "role_code": "steward",
        "role_name": "数据治理员",
        "description": "数据质量管理与治理人员",
        "is_system": True,
        "permissions": [
            "data:read",
            "metadata:read", "metadata:write",
            "quality:read", "quality:manage",
        ],
    },
    {
        "role_code": "viewer",
        "role_name": "查看者",
        "description": "只读权限用户",
        "is_system": True,
        "permissions": [
            "data:read",
            "pipeline:read",
        ],
    },
    {
        "role_code": "service_account",
        "role_name": "服务账户",
        "description": "服务间调用的特殊账户",
        "is_system": True,
        "permissions": [
            "service:call",
            "data:read",
        ],
    },
]


# ============================================================
# 从 DEV_USERS 环境变量迁移用户
# ============================================================

def _get_dev_users() -> dict:
    """获取开发环境用户配置"""
    import json

    users_json = os.environ.get("DEV_USERS", "")
    if users_json:
        try:
            return json.loads(users_json)
        except json.JSONDecodeError:
            pass

    # 默认开发用户
    return {
        "admin": {"password": "admin123", "role": "admin", "display_name": "管理员"},
        "super_admin": {"password": "admin123", "role": "super_admin", "display_name": "超级管理员"},
        "analyst": {"password": "ana123", "role": "analyst", "display_name": "数据分析师"},
        "viewer": {"password": "view123", "role": "viewer", "display_name": "查看者"},
        "data_scientist": {"password": "sci123", "role": "data_scientist", "display_name": "数据科学家"},
        "engineer": {"password": "eng123", "role": "engineer", "display_name": "数据工程师"},
        "steward": {"password": "stw123", "role": "steward", "display_name": "数据治理员"},
    }


def _hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    import hashlib
    import secrets
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


# ============================================================
# 迁移函数
# ============================================================

async def create_tables(engine):
    """创建所有数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def insert_permissions(session: AsyncSession):
    """插入默认权限"""
    existing = await session.execute(select(PermissionORM))
    existing_codes = {p.code for p in existing.scalars()}

    for code, name, description in DEFAULT_PERMISSIONS:
        if code not in existing_codes:
            permission = PermissionORM(code=code, name=name, description=description, category="general")
            session.add(permission)

    await session.commit()
    logger.info(f"插入权限完成: {len(DEFAULT_PERMISSIONS)} 条")


async def insert_roles(session: AsyncSession):
    """插入默认角色及权限关联"""
    # 获取所有权限
    permissions_result = await session.execute(select(PermissionORM))
    all_permissions = {p.code: p.id for p in permissions_result.scalars()}

    for role_def in DEFAULT_ROLES:
        # 检查角色是否已存在
        existing = await session.execute(
            select(RoleORM).where(RoleORM.role_code == role_def["role_code"])
        )
        if existing.scalars().first():
            continue

        # 创建角色
        role = RoleORM(
            role_code=role_def["role_code"],
            role_name=role_def["role_name"],
            description=role_def["description"],
            is_system=role_def["is_system"],
        )
        session.add(role)
        await session.flush()

        # 关联权限
        for perm_code in role_def["permissions"]:
            if perm_code in all_permissions:
                role_perm = RolePermissionORM(
                    role_id=role.id,
                    permission_code=perm_code,
                )
                session.add(role_perm)

    await session.commit()
    logger.info(f"插入角色完成: {len(DEFAULT_ROLES)} 个")


async def migrate_dev_users(session: AsyncSession, migrate_passwords: bool = False):
    """从 DEV_USERS 迁移用户到数据库

    Args:
        migrate_passwords: 是否迁移原始密码（生产环境应为 False，强制用户重置密码）
    """
    dev_users = _get_dev_users()
    created_count = 0

    for username, user_info in dev_users.items():
        # 检查用户是否已存在
        existing = await session.execute(
            select(UserORM).where(UserORM.username == username)
        )
        if existing.scalars().first():
            continue

        # 创建用户
        if migrate_passwords:
            password_hash = _hash_password(user_info["password"])
        else:
            # 使用随机密码，用户首次登录后需要重置
            import secrets
            random_password = secrets.token_urlsafe(16)
            password_hash = _hash_password(random_password)
            logger.warning(f"用户 {username} 使用随机密码，请在首次登录后重置: {random_password}")

        user = UserORM(
            username=username,
            password_hash=password_hash,
            role_code=user_info["role"],
            display_name=user_info["display_name"],
            is_active=True,
        )
        session.add(user)
        created_count += 1

    await session.commit()
    logger.info(f"迁移用户完成: {created_count} 个")


async def insert_default_config(session: AsyncSession):
    """插入默认系统配置"""
    default_configs = [
        {
            "key": "session.timeout",
            "value": 86400,
            "description": "会话超时时间（秒）",
            "category": "auth",
        },
        {
            "key": "max.login.attempts",
            "value": 5,
            "description": "最大登录失败次数",
            "category": "security",
        },
        {
            "key": "password.min.length",
            "value": 8,
            "description": "密码最小长度",
            "category": "security",
        },
        {
            "key": "system.initialized",
            "value": False,
            "description": "系统是否已初始化",
            "category": "system",
        },
    ]

    for config in default_configs:
        existing = await session.execute(
            select(SystemConfigORM).where(SystemConfigORM.key == config["key"])
        )
        if not existing.scalars().first():
            system_config = SystemConfigORM(
                key=config["key"],
                value=config["value"],
                description=config["description"],
                category=config["category"],
            )
            session.add(system_config)

    await session.commit()
    logger.info("插入默认系统配置完成")


# ============================================================
# 主迁移函数
# ============================================================

async def run_migrations(migrate_passwords: bool = False):
    """运行所有迁移

    Args:
        migrate_passwords: 是否迁移原始密码
    """
    database_url = get_database_url()

    # 检查数据库 URL
    if "changeme" in database_url.lower():
        logger.warning("数据库 URL 使用默认密码，建议修改")

    # 创建引擎
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        # 1. 创建表
        await create_tables(engine)

        # 2. 插入数据
        async with async_session_maker() as session:
            await insert_permissions(session)
            await insert_roles(session)
            await migrate_dev_users(session, migrate_passwords=migrate_passwords)
            await insert_default_config(session)

        logger.info("数据库迁移完成！")

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        await engine.dispose()


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="数据库迁移脚本")
    parser.add_argument(
        "--migrate-passwords",
        action="store_true",
        help="迁移原始密码（生产环境不建议使用）",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出",
    )

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 运行迁移
    asyncio.run(run_migrations(migrate_passwords=args.migrate_passwords))
