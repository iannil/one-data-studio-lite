"""初始化数据脚本

为系统提供初始化数据，包括：
1. 基础数据（权限、角色、配置）
2. 用户数据
3. 业务域数据（数据集、元数据、管道、质量规则）
4. 组织架构数据（部门、项目、工作空间）
5. 演示数据（用于功能验证）
6. 敏感数据测试场景

运行方式:
    python -m services.common.seed_data
    或
    python services/common/seed_data.py
"""

import asyncio
import json
import logging
import secrets
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.common.database import get_database_url
from services.common.orm_models import (
    AuditEventORM,
    DetectionRuleORM,
    ETLMappingORM,
    MaskRuleORM,
    PermissionORM,
    RoleORM,
    RolePermissionORM,
    ScanReportORM,
    SensitiveFieldORM,
    ServiceAccountORM,
    SystemConfigORM,
    UserApiKeyORM,
    UserORM,
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
# 第三阶段：业务域数据
# ============================================================

async def seed_detection_rules(session: AsyncSession) -> int:
    """插入敏感数据检测规则"""
    rules = [
        {
            "id": str(secrets.token_hex(16)),
            "name": "中国大陆手机号",
            "pattern": r"1[3-9]\d{9}",
            "sensitivity_level": "high",
            "description": "检测中国大陆手机号码格式",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "身份证号码",
            "pattern": r"[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]",
            "sensitivity_level": "critical",
            "description": "检测18位中国居民身份证号码",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "银行卡号",
            "pattern": r"\b\d{16,19}\b",
            "sensitivity_level": "critical",
            "description": "检测银行卡号（16-19位数字）",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "邮箱地址",
            "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            "sensitivity_level": "medium",
            "description": "检测邮箱地址格式",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "IPv4地址",
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "sensitivity_level": "low",
            "description": "检测IPv4地址",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "员工工号",
            "pattern": r"^EMP\d{6}$",
            "sensitivity_level": "medium",
            "description": "检测员工工号格式 EMP+6位数字",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "统一社会信用代码",
            "pattern": r"[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}",
            "sensitivity_level": "high",
            "description": "检测18位统一社会信用代码",
            "enabled": True,
        },
        {
            "id": str(secrets.token_hex(16)),
            "name": "车牌号",
            "pattern": r"[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5,6}",
            "sensitivity_level": "medium",
            "description": "检测中国车牌号",
            "enabled": True,
        },
    ]

    count = 0
    for rule_info in rules:
        existing = await session.execute(
            select(DetectionRuleORM).where(DetectionRuleORM.name == rule_info["name"])
        )
        if not existing.scalars().first():
            rule = DetectionRuleORM(**rule_info)
            session.add(rule)
            count += 1

    await session.commit()
    logger.info(f"敏感数据检测规则插入完成: {count} 条")
    return count


async def seed_mask_rules(session: AsyncSession) -> int:
    """插入脱敏规则"""
    rules = [
        {
            "table_name": "customers",
            "column_name": "phone",
            "algorithm_type": "MASK_FIRST_LAST",
            "algorithm_props": {"mask_first": 3, "mask_last": 4, "mask_char": "*"},
            "enabled": True,
        },
        {
            "table_name": "customers",
            "column_name": "id_card",
            "algorithm_type": "MASK_FIRST_LAST",
            "algorithm_props": {"mask_first": 6, "mask_last": 4, "mask_char": "*"},
            "enabled": True,
        },
        {
            "table_name": "payment_info",
            "column_name": "bank_card",
            "algorithm_type": "MASK_FIRST_LAST",
            "algorithm_props": {"mask_first": 4, "mask_last": 4, "mask_char": "*"},
            "enabled": True,
        },
        {
            "table_name": "customers",
            "column_name": "email",
            "algorithm_type": "MASK_EMAIL",
            "algorithm_props": {},
            "enabled": True,
        },
    ]

    count = 0
    for rule_info in rules:
        existing = await session.execute(
            select(MaskRuleORM).where(
                MaskRuleORM.table_name == rule_info["table_name"],
                MaskRuleORM.column_name == rule_info["column_name"]
            )
        )
        if not existing.scalars().first():
            mask_rule = MaskRuleORM(**rule_info)
            session.add(mask_rule)
            count += 1

    await session.commit()
    logger.info(f"脱敏规则插入完成: {count} 条")
    return count


async def seed_etl_mappings(session: AsyncSession) -> int:
    """插入ETL映射规则"""
    mappings = [
        {
            "id": str(secrets.token_hex(16)),
            "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,marketing.users,PROD)",
            "target_task_type": "seatunnel",
            "target_task_id": "sync_users_to_warehouse",
            "trigger_on": ["CREATE", "UPDATE"],
            "auto_update_config": True,
            "description": "同步用户表到数据仓库",
            "enabled": True,
            "created_by": "admin",
        },
        {
            "id": str(secrets.token_hex(16)),
            "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,ecommerce.orders,PROD)",
            "target_task_type": "hop",
            "target_task_id": "process_orders_etl",
            "trigger_on": ["CREATE"],
            "auto_update_config": False,
            "description": "订单数据ETL处理",
            "enabled": True,
            "created_by": "engineer",
        },
        {
            "id": str(secrets.token_hex(16)),
            "source_urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,analytics.click_events,PROD)",
            "target_task_type": "dolphinscheduler",
            "target_task_id": "daily_analytics_pipeline",
            "trigger_on": ["UPDATE"],
            "auto_update_config": True,
            "description": "每日分析数据流水线",
            "enabled": True,
            "created_by": "data_scientist",
        },
    ]

    count = 0
    for mapping_info in mappings:
        existing = await session.execute(
            select(ETLMappingORM).where(
                ETLMappingORM.source_urn == mapping_info["source_urn"]
            )
        )
        if not existing.scalars().first():
            etl_mapping = ETLMappingORM(**mapping_info)
            session.add(etl_mapping)
            count += 1

    await session.commit()
    logger.info(f"ETL映射规则插入完成: {count} 条")
    return count


async def seed_business_tables(session: AsyncSession) -> int:
    """创建业务演示表"""
    # 组织架构表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            parent_id INTEGER,
            description TEXT
        )
    """))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            department_id INTEGER,
            owner_id INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    """))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            project_id INTEGER,
            description TEXT,
            created_at TEXT
        )
    """))

    # 数据资产表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS datasets (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            domain TEXT,
            format TEXT,
            size_bytes INTEGER,
            row_count INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT,
            updated_at TEXT
        )
    """))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS quality_rules (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            rule_type TEXT,
            dataset_id INTEGER,
            threshold REAL,
            description TEXT,
            enabled BOOLEAN DEFAULT 1
        )
    """))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            pipeline_type TEXT,
            source_system TEXT,
            target_system TEXT,
            schedule TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT
        )
    """))

    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS dashboards (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            owner_id INTEGER,
            category TEXT,
            is_public BOOLEAN DEFAULT 0,
            created_at TEXT
        )
    """))

    # 插入部门数据
    await session.execute(text("""
        INSERT OR REPLACE INTO departments (id, name, code, parent_id, description) VALUES
        (1, '数据平台部', 'DP', NULL, '负责数据平台建设与运维'),
        (2, '数据分析部', 'DA', NULL, '负责数据分析与挖掘'),
        (3, '数据工程部', 'DE', 1, '负责数据工程开发'),
        (4, '数据治理部', 'DG', 1, '负责数据质量管理'),
        (5, '业务分析部', 'BA', 2, '负责业务数据分析')
    """))

    # 插入项目数据
    await session.execute(text("""
        INSERT OR REPLACE INTO projects (id, name, code, department_id, owner_id, status, created_at) VALUES
        (1, '用户画像平台', 'USER_PROFILE', 1, 3, 'active', '2024-01-01'),
        (2, '实时数据仓库', 'RT_DW', 3, 3, 'active', '2024-01-02'),
        (3, '营销分析平台', 'MKT_ANALYTICS', 5, 4, 'active', '2024-01-03'),
        (4, '数据质量中心', 'DQ_CENTER', 4, 5, 'active', '2024-01-04'),
        (5, '智能推荐系统', 'REC_SYS', 2, 6, 'active', '2024-01-05')
    """))

    # 插入工作空间数据
    await session.execute(text("""
        INSERT OR REPLACE INTO workspaces (id, name, project_id, description, created_at) VALUES
        (1, '开发环境', 1, '用户画像平台开发环境', '2024-01-01'),
        (2, '测试环境', 1, '用户画像平台测试环境', '2024-01-01'),
        (3, '生产环境', 1, '用户画像平台生产环境', '2024-01-01')
    """))

    # 插入数据集数据（扩展到15个）
    await session.execute(text("""
        INSERT OR REPLACE INTO datasets (id, name, description, domain, format, size_bytes, row_count, status, created_at, updated_at) VALUES
        (1, '用户基础信息表', '存储用户基本信息', 'user', 'parquet', 1024000, 100000, 'active', '2024-01-01', '2024-01-10'),
        (2, '订单明细表', '存储订单交易明细', 'ecommerce', 'parquet', 5120000, 500000, 'active', '2024-01-02', '2024-01-10'),
        (3, '用户行为日志', '用户点击浏览日志', 'behavior', 'json', 10240000, 1000000, 'active', '2024-01-03', '2024-01-10'),
        (4, '产品信息表', '商品SKU信息', 'product', 'parquet', 256000, 10000, 'active', '2024-01-04', '2024-01-10'),
        (5, '营销活动表', '营销活动配置数据', 'marketing', 'mysql', 128000, 1000, 'active', '2024-01-05', '2024-01-10'),
        (6, '用户标签表', '用户画像标签数据', 'user', 'parquet', 2048000, 100000, 'active', '2024-01-06', '2024-01-10'),
        (7, '风险评分表', '用户风险评分数据', 'risk', 'parquet', 512000, 100000, 'active', '2024-01-07', '2024-01-10'),
        (8, '渠道来源表', '流量渠道数据', 'marketing', 'mysql', 64000, 500, 'active', '2024-01-08', '2024-01-10'),
        (9, '商品类目表', '商品分类层级结构', 'product', 'mysql', 128000, 2000, 'active', '2024-01-09', '2024-01-10'),
        (10, '用户收货地址', '用户配送地址信息', 'user', 'parquet', 768000, 150000, 'active', '2024-01-10', '2024-01-10'),
        (11, '优惠券记录', '优惠券发放使用记录', 'marketing', 'parquet', 2560000, 300000, 'active', '2024-01-11', '2024-01-10'),
        (12, '退款流水表', '订单退款明细', 'ecommerce', 'parquet', 1280000, 100000, 'active', '2024-01-12', '2024-01-10'),
        (13, '搜索关键词', '用户搜索日志', 'behavior', 'json', 20480000, 2000000, 'active', '2024-01-13', '2024-01-10'),
        (14, '库存流水表', '商品库存变动记录', 'product', 'parquet', 5120000, 800000, 'active', '2024-01-14', '2024-01-10'),
        (15, '用户积分流水', '积分获取消费记录', 'user', 'parquet', 3072000, 600000, 'active', '2024-01-15', '2024-01-10')
    """))

    # 插入质量规则数据（扩展到15+规则）
    await session.execute(text("""
        INSERT OR REPLACE INTO quality_rules (id, name, rule_type, dataset_id, threshold, description, enabled) VALUES
        (1, '空值检测', 'null_check', 1, 0.0, '用户ID不能为空', 1),
        (2, '唯一性检测', 'unique_check', 1, 1.0, '用户ID必须唯一', 1),
        (3, '格式检测', 'format_check', 1, 0.95, '手机号格式正确率', 1),
        (4, '范围检测', 'range_check', 2, 0.0, '订单金额不能为负', 1),
        (5, '及时性检测', 'timeliness_check', 3, 3600, '日志延迟不超过1小时', 1),
        (6, '完整性检测', 'completeness_check', 4, 0.99, 'SKU信息完整率', 1),
        (7, '一致性检测', 'consistency_check', 5, 1.0, '活动时间一致', 1),
        (8, '波动检测', 'volatility_check', 2, 0.5, '订单量波动检测', 1),
        (9, '重复检测', 'duplicate_check', 3, 0.0, '日志不能重复', 1),
        (10, '分布检测', 'distribution_check', 6, 0.1, '标签分布异常', 1),
        (11, '数值精度检测', 'precision_check', 2, 0.01, '金额精度为2位小数', 1),
        (12, '长度检测', 'length_check', 1, 100, '用户名长度不超过100字符', 1),
        (13, '正则检测', 'regex_check', 1, 1.0, '邮箱格式符合正则', 1),
        (14, '引用完整性检测', 'fk_check', 2, 1.0, '订单用户ID必须存在', 1),
        (15, '枚举值检测', 'enum_check', 2, 1.0, '订单状态必须为有效值', 1),
        (16, '时效性检测', 'freshness_check', 3, 86400, '数据更新时间不超过24小时', 1),
        (17, '异常值检测', 'outlier_check', 2, 3.0, '订单金额异常值(3倍标准差)', 1),
        (18, '覆盖率检测', 'coverage_check', 4, 0.95, '商品类目覆盖率', 1)
    """))

    # 插入管道数据（扩展到10个管道）
    await session.execute(text("""
        INSERT OR REPLACE INTO pipelines (id, name, pipeline_type, source_system, target_system, schedule, status, created_at) VALUES
        (1, '用户数据同步', 'sync', 'mysql', 'data_warehouse', '0 2 * * *', 'active', '2024-01-01'),
        (2, '订单数据清洗', 'cleaning', 'mysql', 'parquet', '0 3 * * *', 'active', '2024-01-02'),
        (3, '日志数据采集', 'ingestion', 'kafka', 'hdfs', 'continuous', 'active', '2024-01-03'),
        (4, '用户标签计算', 'compute', 'data_warehouse', 'redis', '0 4 * * *', 'active', '2024-01-04'),
        (5, '风险评分更新', 'ml', 'data_warehouse', 'mysql', '0 5 * * *', 'active', '2024-01-05'),
        (6, '产品数据同步', 'sync', 'mysql', 'data_warehouse', '0 1 * * *', 'active', '2024-01-06'),
        (7, '营销数据聚合', 'aggregation', 'parquet', 'mysql', '0 6 * * *', 'active', '2024-01-07'),
        (8, '实时数据流处理', 'stream', 'kafka', 'clickhouse', 'continuous', 'active', '2024-01-08'),
        (9, '历史数据归档', 'archive', 'mysql', 's3', '0 0 * * 0', 'active', '2024-01-09'),
        (10, '全量数据导出', 'export', 'data_warehouse', 'mysql', '0 3 * * 0', 'active', '2024-01-10')
    """))

    # 插入仪表板数据（扩展到8个）
    await session.execute(text("""
        INSERT OR REPLACE INTO dashboards (id, name, description, owner_id, category, is_public, created_at) VALUES
        (1, '用户增长分析', '用户注册、活跃、留存分析', 3, 'user', 1, '2024-01-01'),
        (2, '销售业绩看板', '销售数据实时监控', 4, 'ecommerce', 1, '2024-01-02'),
        (3, '数据质量监控', '数据质量指标监控', 5, 'governance', 1, '2024-01-03'),
        (4, '营销效果分析', '营销活动ROI分析', 4, 'marketing', 1, '2024-01-04'),
        (5, '实时数据大屏', '实时流量、订单、用户监控', 3, 'realtime', 1, '2024-01-05'),
        (6, '风控预警看板', '风险事件、异常交易监控', 6, 'risk', 0, '2024-01-06'),
        (7, '数据资产地图', '全平台数据资产目录', 5, 'catalog', 1, '2024-01-07'),
        (8, '系统运维监控', 'ETL任务、数据同步状态', 3, 'operations', 1, '2024-01-08')
    """))

    await session.commit()
    logger.info("业务表插入完成")
    return 1  # 返回批次数


async def seed_scan_reports(session: AsyncSession) -> int:
    """插入敏感数据扫描报告示例"""
    reports = [
        {
            "id": str(secrets.token_hex(16)),
            "table_name": "customers",
            "database_name": "marketing",
            "scan_time": datetime.now() - timedelta(days=1),
            "total_columns": 6,
            "sensitive_columns": 4,
            "risk_level": "high",
            "scanned_by": "super_admin",
        },
        {
            "id": str(secrets.token_hex(16)),
            "table_name": "payment_info",
            "database_name": "ecommerce",
            "scan_time": datetime.now() - timedelta(days=2),
            "total_columns": 4,
            "sensitive_columns": 1,
            "risk_level": "critical",
            "scanned_by": "super_admin",
        },
        {
            "id": str(secrets.token_hex(16)),
            "table_name": "users_with_phone",
            "database_name": "test",
            "scan_time": datetime.now() - timedelta(days=3),
            "total_columns": 3,
            "sensitive_columns": 1,
            "risk_level": "high",
            "scanned_by": "admin",
        },
    ]

    count = 0
    for report_info in reports:
        report = ScanReportORM(**report_info)
        session.add(report)
        count += 1

    await session.commit()
    logger.info(f"扫描报告插入完成: {count} 条")
    return count


async def seed_sensitive_fields(session: AsyncSession) -> int:
    """插入敏感字段详情示例"""
    # 获取第一个报告ID
    report_result = await session.execute(select(ScanReportORM).limit(1))
    first_report = report_result.scalars().first()

    if not first_report:
        return 0

    fields = [
        {
            "report_id": first_report.id,
            "column_name": "phone",
            "sensitivity_level": "high",
            "detected_types": ["phone"],
            "detection_method": "regex",
            "sample_count": 100,
            "confidence": 0.98,
        },
        {
            "report_id": first_report.id,
            "column_name": "email",
            "sensitivity_level": "medium",
            "detected_types": ["email"],
            "detection_method": "regex",
            "sample_count": 100,
            "confidence": 0.95,
        },
        {
            "report_id": first_report.id,
            "column_name": "id_card",
            "sensitivity_level": "critical",
            "detected_types": ["id_card"],
            "detection_method": "regex",
            "sample_count": 100,
            "confidence": 0.92,
        },
        {
            "report_id": first_report.id,
            "column_name": "address",
            "sensitivity_level": "medium",
            "detected_types": ["address"],
            "detection_method": "llm",
            "sample_count": 100,
            "confidence": 0.85,
        },
    ]

    count = 0
    for field_info in fields:
        field = SensitiveFieldORM(**field_info)
        session.add(field)
        count += 1

    await session.commit()
    logger.info(f"敏感字段插入完成: {count} 条")
    return count


async def seed_audit_events(session: AsyncSession) -> int:
    """插入审计事件示例"""
    events = [
        {
            "id": str(secrets.token_hex(16)),
            "subsystem": "portal",
            "event_type": "login",
            "user": "admin",
            "action": "User login",
            "resource": "/api/auth/login",
            "status_code": 200,
            "duration_ms": 125.5,
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "created_at": datetime.now() - timedelta(hours=1),
        },
        {
            "id": str(secrets.token_hex(16)),
            "subsystem": "portal",
            "event_type": "api_call",
            "user": "admin",
            "action": "GET /api/users",
            "resource": "/api/users",
            "status_code": 200,
            "duration_ms": 45.2,
            "ip_address": "192.168.1.100",
            "created_at": datetime.now() - timedelta(hours=1, minutes=5),
        },
        {
            "id": str(secrets.token_hex(16)),
            "subsystem": "metadata_sync",
            "event_type": "sync",
            "user": "service_account",
            "action": "Metadata sync executed",
            "resource": "datahub",
            "status_code": 200,
            "duration_ms": 2500.0,
            "created_at": datetime.now() - timedelta(hours=2),
        },
        {
            "id": str(secrets.token_hex(16)),
            "subsystem": "sensitive_detect",
            "event_type": "scan",
            "user": "super_admin",
            "action": "Sensitive data scan",
            "resource": "customers",
            "status_code": 200,
            "duration_ms": 1500.0,
            "created_at": datetime.now() - timedelta(days=1),
        },
        {
            "id": str(secrets.token_hex(16)),
            "subsystem": "portal",
            "event_type": "api_call",
            "user": "analyst",
            "action": "GET /api/datasets",
            "resource": "/api/datasets",
            "status_code": 200,
            "duration_ms": 78.3,
            "ip_address": "192.168.1.105",
            "created_at": datetime.now() - timedelta(hours=3),
        },
    ]

    count = 0
    for event_info in events:
        event = AuditEventORM(**event_info)
        session.add(event)
        count += 1

    await session.commit()
    logger.info(f"审计事件插入完成: {count} 条")
    return count


async def seed_metadata_entities(session: AsyncSession) -> dict:
    """创建元数据实体（DataHub格式）

    为元数据管理提供示例实体，用于测试和演示。
    返回创建的元数据实体信息。
    """
    # 创建元数据存储表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS metadata_entities (
            id INTEGER PRIMARY KEY,
            urn TEXT NOT NULL UNIQUE,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            domain TEXT,
            owner TEXT,
            properties TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """))

    # DataHub 格式的元数据实体
    entities = [
        {
            "id": 1,
            "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,marketing.users,PROD)",
            "entity_type": "dataset",
            "name": "users",
            "description": "用户基础信息表",
            "domain": "user",
            "owner": "data_platform",
            "properties": json.dumps({
                "customProperties": {
                    "schema": "marketing",
                    "table": "users",
                    "platform": "mysql"
                },
                "schemaMetadata": {
                    "schemaName": "marketing",
                    "fields": [
                        {"fieldName": "id", "fieldType": "BIGINT", "description": "用户ID", "nullable": False},
                        {"fieldName": "username", "fieldType": "VARCHAR(50)", "description": "用户名", "nullable": False},
                        {"fieldName": "email", "fieldType": "VARCHAR(100)", "description": "邮箱", "nullable": True},
                        {"fieldName": "phone", "fieldType": "VARCHAR(20)", "description": "手机号", "nullable": True},
                        {"fieldName": "created_at", "fieldType": "TIMESTAMP", "description": "创建时间", "nullable": False}
                    ]
                }
            }),
            "created_at": "2024-01-01",
            "updated_at": "2024-01-10"
        },
        {
            "id": 2,
            "urn": "urn:li:dataset:(urn:li:dataPlatform:mysql,ecommerce.orders,PROD)",
            "entity_type": "dataset",
            "name": "orders",
            "description": "订单明细表",
            "domain": "ecommerce",
            "owner": "data_platform",
            "properties": json.dumps({
                "customProperties": {
                    "schema": "ecommerce",
                    "table": "orders",
                    "platform": "mysql"
                },
                "schemaMetadata": {
                    "schemaName": "ecommerce",
                    "fields": [
                        {"fieldName": "id", "fieldType": "BIGINT", "description": "订单ID", "nullable": False},
                        {"fieldName": "user_id", "fieldType": "BIGINT", "description": "用户ID", "nullable": False},
                        {"fieldName": "total_amount", "fieldType": "DECIMAL(10,2)", "description": "订单金额", "nullable": False},
                        {"fieldName": "status", "fieldType": "VARCHAR(20)", "description": "订单状态", "nullable": False},
                        {"fieldName": "created_at", "fieldType": "TIMESTAMP", "description": "创建时间", "nullable": False}
                    ]
                }
            }),
            "created_at": "2024-01-02",
            "updated_at": "2024-01-10"
        },
        {
            "id": 3,
            "urn": "urn:li:dataJob:(urn:li:dataFlow:(airflow,daily_sync,PROD),daily_user_sync)",
            "entity_type": "dataJob",
            "name": "daily_user_sync",
            "description": "每日用户数据同步任务",
            "domain": "ingestion",
            "owner": "engineer",
            "properties": json.dumps({
                "customProperties": {
                    "type": "batch",
                    "schedule": "0 2 * * *"
                },
                "dataFlow": {
                    "orchestrator": "airflow",
                    "name": "daily_sync",
                    "cluster": "PROD"
                }
            }),
            "created_at": "2024-01-01",
            "updated_at": "2024-01-10"
        },
        {
            "id": 4,
            "urn": "urn:li:dataFlow:(airflow,daily_sync,PROD)",
            "entity_type": "dataFlow",
            "name": "daily_sync",
            "description": "每日数据同步流",
            "domain": "ingestion",
            "owner": "engineer",
            "properties": json.dumps({
                "customProperties": {
                    "project": "data_warehouse"
                },
                "orchestrator": "airflow",
                "cluster": "PROD"
            }),
            "created_at": "2024-01-01",
            "updated_at": "2024-01-10"
        },
        {
            "id": 5,
            "urn": "urn:li:corpGroup:DataPlatform",
            "entity_type": "corpGroup",
            "name": "DataPlatform",
            "description": "数据平台部门",
            "domain": "organization",
            "owner": "super_admin",
            "properties": json.dumps({
                "customProperties": {
                    "type": "department",
                    "parent": None
                },
                "members": ["admin", "engineer", "steward"]
            }),
            "created_at": "2024-01-01",
            "updated_at": "2024-01-10"
        },
        {
            "id": 6,
            "urn": "urn:li:glossaryTerm:User.KPI",
            "entity_type": "glossaryTerm",
            "name": "User.KPI",
            "description": "用户相关关键指标术语",
            "domain": "governance",
            "owner": "steward",
            "properties": json.dumps({
                "definition": "用户维度关键指标，包括DAU、MAU、留存率等",
                "terms": ["DAU", "MAU", "留存率", "流失率"]
            }),
            "created_at": "2024-01-05",
            "updated_at": "2024-01-10"
        },
    ]

    for entity in entities:
        await session.execute(text("""
            INSERT OR REPLACE INTO metadata_entities
            (id, urn, entity_type, name, description, domain, owner, properties, created_at, updated_at)
            VALUES (:id, :urn, :entity_type, :name, :description, :domain, :owner, :properties, :created_at, :updated_at)
        """), entity)

    await session.commit()
    logger.info(f"元数据实体插入完成: {len(entities)} 条")
    return {"entities": len(entities), "urns": [e["urn"] for e in entities]}


async def seed_dashboard_definitions(session: AsyncSession) -> dict:
    """创建仪表板定义（Superset格式）

    为BI分析提供示例仪表板配置，用于测试和演示。
    """
    # 创建仪表板定义表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS dashboard_definitions (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            dashboard_id INTEGER NOT NULL,
            definition TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
    """))

    # Superset 格式的仪表板定义
    definitions = [
        {
            "id": 1,
            "slug": "user_growth_analysis",
            "dashboard_id": 1,
            "definition": json.dumps({
                "position": {"x": 0, "y": 0, "w": 12, "h": 8},
                "meta": {"refreshFrequency": 60, "chartOrientation": "vertical"},
                "charts": [
                    {
                        "id": "chart_1",
                        "name": "每日新增用户",
                        "type": "line",
                        "datasource": "users",
                        "x_axis": "created_at",
                        "metrics": ["count(*)"],
                        "groupby": ["created_at"]
                    },
                    {
                        "id": "chart_2",
                        "name": "用户留存漏斗",
                        "type": "funnel",
                        "datasource": "users",
                        "steps": ["注册", "激活", "下单", "复购"]
                    },
                    {
                        "id": "chart_3",
                        "name": "用户地域分布",
                        "type": "map",
                        "datasource": "users",
                        "region": "province"
                    },
                    {
                        "id": "chart_4",
                        "name": "DAU/MAU趋势",
                        "type": "line",
                        "datasource": "user_events",
                        "metrics": ["dau", "mau"]
                    }
                ],
                "filters": {
                    "time_range": "last_30_days",
                    "date_column": "created_at"
                }
            }),
            "version": 1,
            "created_at": "2024-01-01",
            "updated_at": "2024-01-10"
        },
        {
            "id": 2,
            "slug": "sales_performance",
            "dashboard_id": 2,
            "definition": json.dumps({
                "position": {"x": 0, "y": 0, "w": 16, "h": 10},
                "meta": {"refreshFrequency": 300, "chartOrientation": "horizontal"},
                "charts": [
                    {
                        "id": "chart_5",
                        "name": "GMV趋势",
                        "type": "line",
                        "datasource": "orders",
                        "metrics": ["sum(total_amount)"],
                        "time_column": "created_at"
                    },
                    {
                        "id": "chart_6",
                        "name": "品类销售占比",
                        "type": "pie",
                        "datasource": "orders",
                        "dimension": "category",
                        "metric": "sum(total_amount)"
                    },
                    {
                        "id": "chart_7",
                        "name": "TOP10商品",
                        "type": "bar",
                        "datasource": "order_items",
                        "dimension": "product_name",
                        "metric": "sum(quantity)",
                        "limit": 10
                    },
                    {
                        "id": "chart_8",
                        "name": "订单状态分布",
                        "type": "dist_bar",
                        "datasource": "orders",
                        "dimension": "status"
                    }
                ],
                "filters": {
                    "time_range": "last_7_days",
                    "date_column": "created_at"
                }
            }),
            "version": 1,
            "created_at": "2024-01-02",
            "updated_at": "2024-01-10"
        },
        {
            "id": 3,
            "slug": "data_quality_monitor",
            "dashboard_id": 3,
            "definition": json.dumps({
                "position": {"x": 0, "y": 0, "w": 14, "h": 9},
                "meta": {"refreshFrequency": 600},
                "charts": [
                    {
                        "id": "chart_9",
                        "name": "数据质量评分",
                        "type": "big_number",
                        "datasource": "quality_metrics",
                        "metric": "avg(score)"
                    },
                    {
                        "id": "chart_10",
                        "name": "任务失败率",
                        "type": "line",
                        "datasource": "etl_tasks",
                        "metrics": ["failure_rate"],
                        "groupby": ["execution_date"]
                    },
                    {
                        "id": "chart_11",
                        "name": "数据延迟监控",
                        "type": "gauge",
                        "datasource": "data_freshness",
                        "metric": "avg(delay_seconds)"
                    },
                    {
                        "id": "chart_12",
                        "name": "质量规则执行结果",
                        "type": "table",
                        "datasource": "quality_rules",
                        "columns": ["rule_name", "dataset", "status", "last_run"]
                    }
                ]
            }),
            "version": 1,
            "created_at": "2024-01-03",
            "updated_at": "2024-01-10"
        },
        {
            "id": 4,
            "slug": "marketing_roi",
            "dashboard_id": 4,
            "definition": json.dumps({
                "position": {"x": 0, "y": 0, "w": 12, "h": 8},
                "meta": {"refreshFrequency": 3600},
                "charts": [
                    {
                        "id": "chart_13",
                        "name": "ROI排名",
                        "type": "bar",
                        "datasource": "campaigns",
                        "dimension": "campaign_name",
                        "metric": "roi"
                    },
                    {
                        "id": "chart_14",
                        "name": "渠道转化漏斗",
                        "type": "funnel",
                        "datasource": "channel_events",
                        "steps": ["曝光", "点击", "访问", "注册", "下单"]
                    }
                ]
            }),
            "version": 1,
            "created_at": "2024-01-04",
            "updated_at": "2024-01-10"
        },
    ]

    for definition in definitions:
        await session.execute(text("""
            INSERT OR REPLACE INTO dashboard_definitions
            (id, slug, dashboard_id, definition, version, created_at, updated_at)
            VALUES (:id, :slug, :dashboard_id, :definition, :version, :created_at, :updated_at)
        """), definition)

    await session.commit()
    logger.info(f"仪表板定义插入完成: {len(definitions)} 条")
    return {"definitions": len(definitions), "slugs": [d["slug"] for d in definitions]}


async def seed_dataset_schemas(session: AsyncSession) -> dict:
    """创建数据集Schema定义

    为数据资产管理提供详细的Schema信息。
    """
    # 创建Schema定义表
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS dataset_schemas (
            id INTEGER PRIMARY KEY,
            dataset_id INTEGER NOT NULL,
            schema_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            data_type TEXT NOT NULL,
            is_nullable BOOLEAN DEFAULT 1,
            description TEXT,
            tags TEXT,
            created_at TEXT
        )
    """))

    # Schema字段定义
    schema_fields = [
        # 用户基础信息表Schema
        {"id": 1, "dataset_id": 1, "schema_name": "marketing", "column_name": "id", "data_type": "BIGINT", "is_nullable": 0, "description": "用户唯一标识", "tags": "['PK', 'PII']"},
        {"id": 2, "dataset_id": 1, "schema_name": "marketing", "column_name": "username", "data_type": "VARCHAR(50)", "is_nullable": 0, "description": "用户名", "tags": "['PII']"},
        {"id": 3, "dataset_id": 1, "schema_name": "marketing", "column_name": "email", "data_type": "VARCHAR(100)", "is_nullable": 1, "description": "邮箱地址", "tags": "['PII', 'SENSITIVE']"},
        {"id": 4, "dataset_id": 1, "schema_name": "marketing", "column_name": "phone", "data_type": "VARCHAR(20)", "is_nullable": 1, "description": "手机号码", "tags": "['PII', 'SENSITIVE']"},
        {"id": 5, "dataset_id": 1, "schema_name": "marketing", "column_name": "created_at", "data_type": "TIMESTAMP", "is_nullable": 0, "description": "创建时间", "tags": "['SYSTEM']"},
        # 订单明细表Schema
        {"id": 6, "dataset_id": 2, "schema_name": "ecommerce", "column_name": "id", "data_type": "BIGINT", "is_nullable": 0, "description": "订单ID", "tags": "['PK']"},
        {"id": 7, "dataset_id": 2, "schema_name": "ecommerce", "column_name": "user_id", "data_type": "BIGINT", "is_nullable": 0, "description": "用户ID", "tags": "['FK']"},
        {"id": 8, "dataset_id": 2, "schema_name": "ecommerce", "column_name": "total_amount", "data_type": "DECIMAL(10,2)", "is_nullable": 0, "description": "订单总金额", "tags": "['METRIC']"},
        {"id": 9, "dataset_id": 2, "schema_name": "ecommerce", "column_name": "status", "data_type": "VARCHAR(20)", "is_nullable": 0, "description": "订单状态", "tags": "['DIMENSION']"},
        {"id": 10, "dataset_id": 2, "schema_name": "ecommerce", "column_name": "created_at", "data_type": "TIMESTAMP", "is_nullable": 0, "description": "创建时间", "tags": "['SYSTEM']"},
    ]

    for field in schema_fields:
        await session.execute(text("""
            INSERT OR REPLACE INTO dataset_schemas
            (id, dataset_id, schema_name, column_name, data_type, is_nullable, description, tags, created_at)
            VALUES (:id, :dataset_id, :schema_name, :column_name, :data_type, :is_nullable, :description, :tags, '2024-01-01')
        """), field)

    await session.commit()
    logger.info(f"数据集Schema插入完成: {len(schema_fields)} 条")
    return {"fields": len(schema_fields), "datasets": 2}


# ============================================================
# 主函数
# ============================================================

async def seed_all_data(
    environment: str = "development",
    skip_users: bool = False,
    include_business: bool = True,
) -> dict:
    """执行所有数据初始化

    Args:
        environment: 环境类型
        skip_users: 是否跳过用户初始化
        include_business: 是否包含业务数据

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
        "detection_rules": 0,
        "mask_rules": 0,
        "etl_mappings": 0,
        "business_tables": 0,
        "scan_reports": 0,
        "sensitive_fields": 0,
        "audit_events": 0,
        "metadata_entities": 0,
        "dashboard_definitions": 0,
        "dataset_schemas": 0,
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

            # 第三阶段：业务域数据
            if include_business:
                logger.info("开始初始化业务域数据...")
                results["detection_rules"] = await seed_detection_rules(session)
                results["mask_rules"] = await seed_mask_rules(session)
                results["etl_mappings"] = await seed_etl_mappings(session)
                results["business_tables"] = await seed_business_tables(session)
                results["scan_reports"] = await seed_scan_reports(session)
                results["sensitive_fields"] = await seed_sensitive_fields(session)
                results["audit_events"] = await seed_audit_events(session)
                # 第四阶段：扩展业务数据
                logger.info("开始初始化扩展业务数据...")
                metadata_result = await seed_metadata_entities(session)
                results["metadata_entities"] = metadata_result.get("entities", 0)
                dashboard_result = await seed_dashboard_definitions(session)
                results["dashboard_definitions"] = dashboard_result.get("definitions", 0)
                schema_result = await seed_dataset_schemas(session)
                results["dataset_schemas"] = schema_result.get("fields", 0)

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
        "detection_rules": {"expected": 8, "actual": 0, "status": "optional"},
        "mask_rules": {"expected": 4, "actual": 0, "status": "optional"},
        "etl_mappings": {"expected": 3, "actual": 0, "status": "optional"},
        "scan_reports": {"expected": 3, "actual": 0, "status": "optional"},
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
            verification["users"]["status"] = (
                "ok" if verification["users"]["actual"] >= verification["users"]["expected"] else "incomplete"
            )

            # 检查服务账户
            sa_result = await session.execute(select(ServiceAccountORM))
            verification["service_accounts"]["actual"] = len(sa_result.scalars().all())
            verification["service_accounts"]["status"] = (
                "ok" if verification["service_accounts"]["actual"] >= verification["service_accounts"]["expected"] else "incomplete"
            )

            # 检查用户API密钥
            api_key_result = await session.execute(select(UserApiKeyORM))
            verification["user_api_keys"]["actual"] = len(api_key_result.scalars().all())
            verification["user_api_keys"]["status"] = (
                "ok" if verification["user_api_keys"]["actual"] >= verification["user_api_keys"]["expected"] else "incomplete"
            )

            # 检查检测规则
            rule_result = await session.execute(select(DetectionRuleORM))
            verification["detection_rules"]["actual"] = len(rule_result.scalars().all())
            verification["detection_rules"]["status"] = (
                "ok" if verification["detection_rules"]["actual"] >= verification["detection_rules"]["expected"] else "incomplete"
            )

            # 检查脱敏规则
            mask_result = await session.execute(select(MaskRuleORM))
            verification["mask_rules"]["actual"] = len(mask_result.scalars().all())
            verification["mask_rules"]["status"] = (
                "ok" if verification["mask_rules"]["actual"] >= verification["mask_rules"]["expected"] else "incomplete"
            )

            # 检查ETL映射
            etl_result = await session.execute(select(ETLMappingORM))
            verification["etl_mappings"]["actual"] = len(etl_result.scalars().all())
            verification["etl_mappings"]["status"] = (
                "ok" if verification["etl_mappings"]["actual"] >= verification["etl_mappings"]["expected"] else "incomplete"
            )

            # 检查扫描报告
            report_result = await session.execute(select(ScanReportORM))
            verification["scan_reports"]["actual"] = len(report_result.scalars().all())
            verification["scan_reports"]["status"] = (
                "ok" if verification["scan_reports"]["actual"] >= verification["scan_reports"]["expected"] else "incomplete"
            )

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
        "--skip-business",
        action="store_true",
        help="跳过业务数据初始化",
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
            include_business=not args.skip_business,
        ))
        print("\n=== 初始化完成 ===")
        for key, value in result.items():
            print(f"✓ {key}: {value} 条")
