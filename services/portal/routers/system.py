"""系统管理 API 路由

提供系统配置、指标查询、紧急操作等功能。
"""

import os
import psutil
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.orm_models import SystemConfigORM, RoleORM, PermissionORM, RolePermissionORM
from services.common.token_blacklist import get_blacklist
from services.portal.models import (
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemConfigSet,
    SystemInitRequest,
    SystemMetricsResponse,
    EmergencyStopRequest,
    RevokeAllTokensRequest,
    ApiResponse,
)
from services.portal.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


# ============================================================
# 权限检查
# ============================================================

def _check_admin_permission(user: TokenPayload) -> None:
    """检查用户是否有管理员权限"""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )


def _check_super_admin_permission(user: TokenPayload) -> None:
    """检查用户是否有超级管理员权限"""
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )


# ============================================================
# 系统配置端点
# ============================================================

@router.get("/config", response_model=ApiResponse)
async def get_system_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取系统配置

    需要管理员或超级管理员权限。敏感配置会被隐藏。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(SystemConfigORM))
    configs = result.scalars().all()

    config_data = {}
    for cfg in configs:
        # 隐藏敏感配置
        if cfg.is_sensitive:
            config_data[cfg.key] = "********"
        else:
            config_data[cfg.key] = cfg.value

    return ApiResponse(data=config_data)


@router.put("/config", response_model=ApiResponse)
async def update_system_config(
    req: SystemConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """更新系统配置

    需要超级管理员权限。
    """
    _check_super_admin_permission(current_user)

    result = await db.execute(
        select(SystemConfigORM).where(SystemConfigORM.key == req.key)
    )
    cfg = result.scalars().first()

    if cfg:
        await db.execute(
            sqlite_insert(SystemConfigORM)
            .values(
                key=req.key,
                value=req.value,
                updated_at=datetime.utcnow(),
                updated_by=current_user.user_id,
            )
            .on_conflict_do_update(
                index_elements=["key"],
                set_={
                    "value": req.value,
                    "updated_at": datetime.utcnow(),
                    "updated_by": current_user.user_id,
                }
            )
        )
    else:
        new_cfg = SystemConfigORM(
            key=req.key,
            value=req.value,
            updated_at=datetime.utcnow(),
            updated_by=current_user.user_id,
        )
        db.add(new_cfg)

    await db.commit()

    return ApiResponse(message="系统配置更新成功")


@router.post("/init", response_model=ApiResponse)
async def initialize_system(
    req: SystemInitRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """初始化系统配置

    需要超级管理员权限。首次部署时调用。
    """
    _check_super_admin_permission(current_user)

    # 创建默认配置
    configs = [
        {
            "key": "auth.default_role",
            "value": req.default_role,
            "description": "新用户默认角色",
            "category": "auth",
            "is_sensitive": False,
        },
        {
            "key": "auth.session_timeout",
            "value": req.session_timeout,
            "description": "会话超时时间（秒）",
            "category": "auth",
            "is_sensitive": False,
        },
        {
            "key": "auth.max_login_attempts",
            "value": req.max_login_attempts,
            "description": "最大登录尝试次数",
            "category": "auth",
            "is_sensitive": False,
        },
    ]

    for cfg in configs:
        existing = await db.execute(
            select(SystemConfigORM).where(SystemConfigORM.key == cfg["key"])
        )
        if not existing.scalars().first():
            new_cfg = SystemConfigORM(
                key=cfg["key"],
                value=cfg["value"],
                description=cfg["description"],
                category=cfg["category"],
                is_sensitive=cfg["is_sensitive"],
                updated_by=current_user.user_id,
            )
            db.add(new_cfg)

    # 初始化预定义角色和权限
    await _initialize_roles_and_permissions(db, current_user)

    await db.commit()

    return ApiResponse(message="系统初始化完成")


async def _initialize_roles_and_permissions(
    db: AsyncSession,
    current_user: TokenPayload,
) -> None:
    """初始化预定义的角色和权限"""

    # 预定义的权限
    permissions = [
        # 数据权限
        ("data:read", "读取数据", "data"),
        ("data:write", "写入数据", "data"),
        ("data:delete", "删除数据", "data"),
        # Pipeline 权限
        ("pipeline:read", "查看 Pipeline", "pipeline"),
        ("pipeline:run", "运行 Pipeline", "pipeline"),
        ("pipeline:manage", "管理 Pipeline", "pipeline"),
        # 系统权限
        ("system:admin", "系统管理", "system"),
        ("system:user:manage", "用户管理", "system"),
        ("system:config", "系统配置", "system"),
        # 元数据权限
        ("metadata:read", "读取元数据", "metadata"),
        ("metadata:write", "写入元数据", "metadata"),
        # 敏感数据权限
        ("sensitive:read", "查看敏感数据", "sensitive"),
        ("sensitive:manage", "管理敏感数据", "sensitive"),
        # 审计权限
        ("audit:read", "查看审计日志", "audit"),
        # 服务调用权限
        ("service:call", "服务间调用", "service"),
    ]

    # 创建权限
    for code, name, category in permissions:
        existing = await db.execute(
            select(PermissionORM).where(PermissionORM.code == code)
        )
        if not existing.scalars().first():
            perm = PermissionORM(
                code=code,
                name=name,
                description=f"{name}权限",
                category=category,
            )
            db.add(perm)

    await db.flush()

    # 预定义的角色权限映射
    role_permissions = {
        "super_admin": [
            "data:read", "data:write", "data:delete",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "system:admin", "system:user:manage", "system:config",
            "metadata:read", "metadata:write",
            "sensitive:read", "sensitive:manage",
            "audit:read", "service:call",
        ],
        "admin": [
            "data:read", "data:write",
            "system:user:manage",
            "audit:read",
            "metadata:read", "metadata:write",
        ],
        "data_scientist": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run",
            "metadata:read", "metadata:write",
        ],
        "analyst": [
            "data:read",
            "pipeline:read",
            "metadata:read",
        ],
        "viewer": [
            "data:read",
            "pipeline:read",
        ],
        "service_account": [
            "data:read",
            "service:call",
        ],
    }

    role_names = {
        "super_admin": "超级管理员",
        "admin": "管理员",
        "data_scientist": "数据科学家",
        "analyst": "数据分析师",
        "viewer": "查看者",
        "service_account": "服务账户",
    }

    # 创建角色及其权限
    for role_code, perm_codes in role_permissions.items():
        role_result = await db.execute(
            select(RoleORM).where(RoleORM.role_code == role_code)
        )
        role = role_result.scalars().first()

        if not role:
            role = RoleORM(
                role_code=role_code,
                role_name=role_names[role_code],
                description=f"{role_names[role_code]}角色",
                is_system=True,
                created_by=current_user.user_id,
            )
            db.add(role)
            await db.flush()

        # 添加权限
        for perm_code in perm_codes:
            perm_result = await db.execute(
                select(PermissionORM).where(PermissionORM.code == perm_code)
            )
            perm = perm_result.scalars().first()

            if perm:
                existing_rp = await db.execute(
                    select(RolePermissionORM).where(
                        RolePermissionORM.role_id == role.id,
                        RolePermissionORM.permission_code == perm_code
                    )
                )
                if not existing_rp.scalars().first():
                    rp = RolePermissionORM(
                        role_id=role.id,
                        permission_code=perm_code,
                    )
                    db.add(rp)


@router.get("/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取系统性能指标

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    # 获取系统指标
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    portal_metrics = {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "percent": disk.percent,
        },
    }

    return SystemMetricsResponse(
        status="healthy",
        portal=portal_metrics,
        internal_services=[],
        subsystems=[],
    )


@router.post("/emergency-stop", response_model=ApiResponse)
async def emergency_stop(
    req: EmergencyStopRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """紧急停止所有服务

    需要超级管理员权限，并需要二次确认。
    """
    _check_super_admin_permission(current_user)

    if not req.confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要设置 confirmed=true 确认操作"
        )

    # TODO: 实现实际的停止逻辑
    # 这里只是记录日志，实际需要调用各个服务的停止接口

    return ApiResponse(
        message=f"紧急停止已触发，原因: {req.reason}",
        data={"stopped_at": datetime.utcnow().isoformat()}
    )


@router.post("/emergency-stop", response_model=ApiResponse)
async def emergency_stop_v2(
    req: EmergencyStopRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """紧急停止所有服务（路径版本2）"""
    return await emergency_stop(req, current_user)


# ============================================================
# 认证相关系统操作
# ============================================================

@router.post("/auth/revoke-all", response_model=ApiResponse)
async def revoke_all_tokens(
    req: RevokeAllTokensRequest,
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """撤销所有用户 Token

    需要超级管理员权限。用于安全事件响应。
    """
    _check_super_admin_permission(current_user)

    blacklist = get_blacklist()
    if not blacklist.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="黑名单服务不可用"
        )

    # 撤销所有用户的 Token（除了排除的用户）
    exclude_set = set(req.exclude_users)
    if current_user.user_id not in exclude_set:
        exclude_set.add(current_user.user_id)

    count = await blacklist.revoke_all(except_users=list(exclude_set))

    return ApiResponse(
        message=f"已撤销 {count} 个 Token",
        data={
            "revoked_count": count,
            "reason": req.reason,
            "excluded_users": list(exclude_set),
        }
    )


@router.post("/auth/transfer-admin", response_model=ApiResponse)
async def transfer_admin(
    target_user: Annotated[str, Query()],
    current_password: Annotated[str, Query()],
    confirm: Annotated[bool, Query()] = False,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[TokenPayload, Depends(get_current_user)] = None,
):
    """转移超级管理员权限

    需要当前超级管理员确认。
    """
    _check_super_admin_permission(current_user)

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要设置 confirm=true 确认操作"
        )

    if target_user == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能转移给自己"
        )

    # 验证当前密码
    from services.portal.routers.users import _verify_password
    user_result = await db.execute(
        select(RoleORM).where(RoleORM.role_code == current_user.role)
    )
    # TODO: 实现密码验证逻辑

    # 修改目标用户角色为超级管理员
    from sqlalchemy import update
    from services.common.orm_models import UserORM

    await db.execute(
        update(UserORM)
        .where(UserORM.username == target_user)
        .values(role_code="super_admin")
    )

    # 修改当前用户角色为管理员
    await db.execute(
        update(UserORM)
        .where(UserORM.username == current_user.user_id)
        .values(role_code="admin")
    )

    await db.commit()

    return ApiResponse(
        message=f"超级管理员权限已转移给 {target_user}",
        data={"previous_admin": current_user.user_id, "new_admin": target_user}
    )
