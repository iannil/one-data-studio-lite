"""初始化数据脚本

为系统提供初始化数据，包括：
1. 基础数据（权限、角色、配置）
2. 用户数据
3. 演示数据（用于功能验证）

运行方式:
    python -m services.common.seed_data
    或
    python services/common/seed_data.py
"""

import asyncio
import logging
import os
import secrets
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.common.database import get_database_url
from services.common.orm_models import (
    UserORM,
    RoleORM,
    PermissionORM,
    RolePermissionORM,
    ServiceAccountORM,
    SystemConfigORM,
    UserApiKeyORM,
)

logger = logging.getLogger(__name__)


# ============================================================
# 密码处理
# ============================================================

def _hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    import hashlib
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


# ============================================================
# 第一阶段：系统基础数据
# ============================================================

async def seed_permissions(session: AsyncSession) -> int:
    """插入默认权限"""
    permissions = [
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

    existing = await session.execute(select(PermissionORM))
    existing_codes = {p.code for p in existing.scalars()}

    count = 0
    for code, name, description in permissions:
        if code not in existing_codes:
            permission = PermissionORM(
                code=code,
                name=name,
                description=description,
                category="general"
            )
            session.add(permission)
            count += 1

    await session.commit()
    logger.info(f"权限插入完成: {count} 条")
    return count


async def seed_roles(session: AsyncSession) -> int:
    """插入默认角色及权限关联"""
    roles = [
        {
            "role_code": "super_admin",
            "role_name": "超级管理员",
            "description": "系统最高权限管理员",
            "is_system": True,
            "permissions": [
                "data:read", "data:write", "data:delete",
                "pipeline:read", "pipeline:run", "pipeline:manage",
                "system:admin", "system:user:manage", "system:config", "system:super_admin",
                "metadata:read", "metadata:write",
                "sensitive:read", "sensitive:manage",
                "audit:read",
                "quality:read", "quality:manage",
                "service:call",
            ],
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

    # 获取所有权限
    permissions_result = await session.execute(select(PermissionORM))
    all_permissions = {p.code: p.id for p in permissions_result.scalars()}

    count = 0
    for role_def in roles:
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

        count += 1

    await session.commit()
    logger.info(f"角色插入完成: {count} 个")
    return count


async def seed_system_config(session: AsyncSession) -> int:
    """插入默认系统配置"""
    configs = [
        {
            "key": "session.timeout",
            "value": 86400,
            "description": "会话超时时间（秒）",
            "category": "auth",
            "is_sensitive": False,
        },
        {
            "key": "max.login.attempts",
            "value": 5,
            "description": "最大登录失败次数",
            "category": "security",
            "is_sensitive": False,
        },
        {
            "key": "password.min.length",
            "value": 8,
            "description": "密码最小长度",
            "category": "security",
            "is_sensitive": False,
        },
        {
            "key": "system.initialized",
            "value": False,
            "description": "系统是否已初始化",
            "category": "system",
            "is_sensitive": False,
        },
        {
            "key": "password.reset.timeout",
            "value": 900,
            "description": "密码重置验证码有效期（秒）",
            "category": "auth",
            "is_sensitive": False,
        },
    ]

    count = 0
    for config in configs:
        existing = await session.execute(
            select(SystemConfigORM).where(SystemConfigORM.key == config["key"])
        )
        if not existing.scalars().first():
            system_config = SystemConfigORM(**config)
            session.add(system_config)
            count += 1

    await session.commit()
    logger.info(f"系统配置插入完成: {count} 条")
    return count


# ============================================================
# 第二阶段：用户数据
# ============================================================

async def seed_users(session: AsyncSession, environment: str = "development") -> int:
    """插入初始用户数据

    Args:
        session: 数据库会话
        environment: 环境类型 (development/production)
    """
    # 生产环境使用随机密码
    if environment.lower() == "production":
        admin_password = secrets.token_urlsafe(16)
        logger.warning(f"生产环境管理员密码: {admin_password} (请在首次登录后修改)")
    else:
        admin_password = "admin123"

    users = [
        {
            "username": "admin",
            "password": admin_password,
            "role_code": "admin",
            "display_name": "系统管理员",
            "email": "admin@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "super_admin",
            "password": admin_password,
            "role_code": "super_admin",
            "display_name": "超级管理员",
            "email": "super_admin@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "analyst",
            "password": "ana123",
            "role_code": "analyst",
            "display_name": "数据分析师",
            "email": "analyst@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "viewer",
            "password": "view123",
            "role_code": "viewer",
            "display_name": "查看者",
            "email": "viewer@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "data_scientist",
            "password": "sci123",
            "role_code": "data_scientist",
            "display_name": "数据科学家",
            "email": "scientist@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "engineer",
            "password": "eng123",
            "role_code": "engineer",
            "display_name": "数据工程师",
            "email": "engineer@one-data-studio.local",
            "is_active": True,
        },
        {
            "username": "steward",
            "password": "stw123",
            "role_code": "steward",
            "display_name": "数据治理员",
            "email": "steward@one-data-studio.local",
            "is_active": True,
        },
    ]

    count = 0
    for user_info in users:
        # 检查用户是否已存在
        existing = await session.execute(
            select(UserORM).where(UserORM.username == user_info["username"])
        )
        if existing.scalars().first():
            continue

        password_hash = _hash_password(user_info["password"])
        user = UserORM(
            username=user_info["username"],
            password_hash=password_hash,
            role_code=user_info["role_code"],
            display_name=user_info["display_name"],
            email=user_info.get("email"),
            is_active=user_info["is_active"],
            created_by="system",
        )
        session.add(user)
        count += 1

    await session.commit()
    logger.info(f"用户插入完成: {count} 个")
    return count


async def seed_service_accounts(session: AsyncSession) -> int:
    """插入服务账户"""
    service_accounts = [
        {
            "name": "internal-sync",
            "display_name": "内部同步服务",
            "description": "用于元数据同步的内部服务账户",
            "role_code": "service_account",
            "is_active": True,
        },
        {
            "name": "data-api-gateway",
            "display_name": "数据 API 网关",
            "description": "数据 API 网关服务账户",
            "role_code": "service_account",
            "is_active": True,
        },
    ]

    count = 0
    for sa_info in service_accounts:
        # 检查服务账户是否已存在
        existing = await session.execute(
            select(ServiceAccountORM).where(ServiceAccountORM.name == sa_info["name"])
        )
        if existing.scalars().first():
            continue

        # 生成 API Token
        api_token = f"ods_sa_{secrets.token_urlsafe(32)}"

        service_account = ServiceAccountORM(
            name=sa_info["name"],
            display_name=sa_info["display_name"],
            description=sa_info["description"],
            role_code=sa_info["role_code"],
            api_token=api_token,
            is_active=sa_info["is_active"],
            created_by="system",
        )
        session.add(service_account)
        count += 1

    await session.commit()
    logger.info(f"服务账户插入完成: {count} 个")
    return count


async def seed_user_api_keys(session: AsyncSession) -> int:
    """为演示用户生成API访问密钥

    为具有服务调用权限的用户生成API密钥，
    便于进行API调用测试。
    """
    # 定义需要生成API密钥的用户
    users_with_api_keys = [
        {
            "username": "admin",
            "key_name": "管理员API密钥",
            "scopes": ["*"],
            "is_active": True,
        },
        {
            "username": "super_admin",
            "key_name": "超级管理员API密钥",
            "scopes": ["*"],
            "is_active": True,
        },
        {
            "username": "data_scientist",
            "key_name": "数据科学家API密钥",
            "scopes": ["data:read", "data:write", "pipeline:read", "pipeline:run", "metadata:read"],
            "is_active": True,
        },
        {
            "username": "engineer",
            "key_name": "数据工程师API密钥",
            "scopes": ["data:read", "data:write", "pipeline:*", "metadata:*"],
            "is_active": True,
        },
        {
            "username": "analyst",
            "key_name": "数据分析师API密钥",
            "scopes": ["data:read", "pipeline:read", "metadata:read"],
            "is_active": True,
        },
    ]

    count = 0
    for api_key_info in users_with_api_keys:
        # 检查用户是否存在
        user_result = await session.execute(
            select(UserORM).where(UserORM.username == api_key_info["username"])
        )
        user = user_result.scalars().first()
        if not user:
            logger.warning(f"用户 {api_key_info['username']} 不存在，跳过API密钥生成")
            continue

        # 检查用户是否已有同名API密钥
        existing = await session.execute(
            select(UserApiKeyORM).where(
                UserApiKeyORM.user_id == user.id,
                UserApiKeyORM.key_name == api_key_info["key_name"]
            )
        )
        if existing.scalars().first():
            logger.info(f"用户 {api_key_info['username']} 已有API密钥，跳过")
            continue

        # 生成API密钥
        api_key = f"ods_ak_{secrets.token_urlsafe(32)}"
        api_secret = f"ods_sk_{secrets.token_urlsafe(48)}"

        user_api_key = UserApiKeyORM(
            user_id=user.id,
            key_name=api_key_info["key_name"],
            api_key=api_key,
            api_secret=api_secret,
            scopes=api_key_info["scopes"],
            is_active=api_key_info["is_active"],
            expires_at=None,  # 演示密钥永不过期
            last_used_at=None,
            created_by="system",
        )
        session.add(user_api_key)
        count += 1

        # 记录密钥信息（仅用于开发环境展示）
        logger.info(f"为用户 {api_key_info['username']} 生成API密钥:")
        logger.info(f"  API Key: {api_key}")
        logger.info(f"  API Secret: {api_secret}")

    await session.commit()
    logger.info(f"用户API密钥插入完成: {count} 个")
    return count


# ============================================================
# 主函数
# ============================================================

async def seed_all_data(
    environment: str = "development",
    skip_users: bool = False,
) -> dict:
    """执行所有数据初始化

    Args:
        environment: 环境类型
        skip_users: 是否跳过用户初始化

    Returns:
        初始化结果统计
    """
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    results = {
        "permissions": 0,
        "roles": 0,
        "system_config": 0,
        "users": 0,
        "service_accounts": 0,
        "user_api_keys": 0,
    }

    try:
        async with async_session_maker() as session:
            # 第一阶段：基础数据
            logger.info("开始初始化基础数据...")
            results["permissions"] = await seed_permissions(session)
            results["roles"] = await seed_roles(session)
            results["system_config"] = await seed_system_config(session)

            # 第二阶段：用户数据
            if not skip_users:
                logger.info("开始初始化用户数据...")
                results["users"] = await seed_users(session, environment)
                results["service_accounts"] = await seed_service_accounts(session)
                results["user_api_keys"] = await seed_user_api_keys(session)

        logger.info(f"数据初始化完成！结果: {results}")
        return results

    except Exception as e:
        logger.error(f"数据初始化失败: {e}")
        raise
    finally:
        await engine.dispose()


async def verify_data() -> dict:
    """验证初始化数据是否完整"""
    database_url = get_database_url()
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    verification = {
        "permissions": {"expected": 19, "actual": 0, "status": "missing"},
        "roles": {"expected": 8, "actual": 0, "status": "missing"},
        "system_config": {"expected": 5, "actual": 0, "status": "missing"},
        "users": {"expected": 7, "actual": 0, "status": "optional"},
        "service_accounts": {"expected": 2, "actual": 0, "status": "optional"},
        "user_api_keys": {"expected": 5, "actual": 0, "status": "optional"},
    }

    try:
        async with async_session_maker() as session:
            # 检查权限
            perm_result = await session.execute(select(PermissionORM))
            verification["permissions"]["actual"] = len(perm_result.scalars().all())
            verification["permissions"]["status"] = (
                "ok" if verification["permissions"]["actual"] >= verification["permissions"]["expected"] else "incomplete"
            )

            # 检查角色
            role_result = await session.execute(select(RoleORM))
            verification["roles"]["actual"] = len(role_result.scalars().all())
            verification["roles"]["status"] = (
                "ok" if verification["roles"]["actual"] >= verification["roles"]["expected"] else "incomplete"
            )

            # 检查系统配置
            config_result = await session.execute(select(SystemConfigORM))
            verification["system_config"]["actual"] = len(config_result.scalars().all())
            verification["system_config"]["status"] = (
                "ok" if verification["system_config"]["actual"] >= verification["system_config"]["expected"] else "incomplete"
            )

            # 检查用户
            user_result = await session.execute(select(UserORM))
            verification["users"]["actual"] = len(user_result.scalars().all())

            # 检查服务账户
            sa_result = await session.execute(select(ServiceAccountORM))
            verification["service_accounts"]["actual"] = len(sa_result.scalars().all())

            # 检查用户API密钥
            api_key_result = await session.execute(select(UserApiKeyORM))
            verification["user_api_keys"]["actual"] = len(api_key_result.scalars().all())

        return verification

    finally:
        await engine.dispose()


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="初始化数据脚本")
    parser.add_argument(
        "--environment", "-e",
        default="development",
        choices=["development", "production"],
        help="环境类型",
    )
    parser.add_argument(
        "--skip-users",
        action="store_true",
        help="跳过用户初始化",
    )
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        help="验证数据完整性",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出",
    )

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.verify:
        # 验证模式
        result = asyncio.run(verify_data())
        print("\n=== 数据验证结果 ===")
        for key, value in result.items():
            status_icon = "✅" if value["status"] == "ok" else "⚠️" if value["status"] == "incomplete" else "ℹ️"
            print(f"{status_icon} {key}: {value['actual']}/{value['expected']} ({value['status']})")

        all_ok = all(v["status"] in ("ok", "optional") for v in result.values())
        sys.exit(0 if all_ok else 1)
    else:
        # 初始化模式
        result = asyncio.run(seed_all_data(
            environment=args.environment,
            skip_users=args.skip_users,
        ))
        print("\n=== 初始化完成 ===")
        for key, value in result.items():
            print(f"✓ {key}: {value} 条")
