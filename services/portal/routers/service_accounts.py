"""服务账户管理 API 路由

提供服务账户 CRUD 操作、密钥管理等功能。
"""

import secrets
import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.orm_models import ServiceAccountORM, RoleORM
from services.portal.models import (
    ServiceAccountCreate,
    ServiceAccountResponse,
    ServiceAccountCreateResponse,
    ServiceAccountListResponse,
    ApiResponse,
)

router = APIRouter(prefix="/api/service-accounts", tags=["service-accounts"])


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


async def _generate_secret() -> str:
    """生成安全的随机密钥"""
    return f"svc_{secrets.token_urlsafe(32)}"


async def _hash_secret(secret: str) -> str:
    """对密钥进行哈希处理"""
    return hashlib.sha256(secret.encode()).hexdigest()


def _orm_to_response(sa: ServiceAccountORM) -> dict:
    """将 ORM 模型转换为响应字典"""
    return {
        "id": sa.id,
        "name": sa.name,
        "display_name": sa.display_name,
        "description": sa.description or "",
        "role": sa.role_code,
        "is_active": sa.is_active,
        "last_used_at": sa.last_used_at.isoformat() if sa.last_used_at else None,
        "created_at": sa.created_at.isoformat() if sa.created_at else None,
        "created_by": sa.created_by,
        "expires_at": sa.expires_at.isoformat() if sa.expires_at else None,
    }


# ============================================================
# 服务账户管理端点
# ============================================================

@router.post("", response_model=ServiceAccountCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_service_account(
    req: ServiceAccountCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """创建服务账户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    # 检查名称是否已存在
    existing_result = await db.execute(
        select(ServiceAccountORM).where(ServiceAccountORM.name == req.name)
    )
    if existing_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"服务账户 '{req.name}' 已存在"
        )

    # 检查角色是否存在
    role_result = await db.execute(select(RoleORM).where(RoleORM.role_code == req.role))
    if not role_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色 '{req.role}' 不存在"
        )

    # 生成密钥
    secret = await _generate_secret()
    secret_hash = await _hash_secret(secret)

    # 创建服务账户
    sa = ServiceAccountORM(
        name=req.name,
        display_name=req.display_name,
        description=req.description,
        secret_hash=secret_hash,
        role_code=req.role,
        created_by=current_user.user_id,
    )
    db.add(sa)
    await db.commit()
    await db.refresh(sa)

    return ServiceAccountCreateResponse(
        id=sa.id,
        name=sa.name,
        display_name=sa.display_name,
        secret=secret,  # 只在创建时返回
        role=sa.role_code,
    )


@router.get("", response_model=ServiceAccountListResponse)
async def list_service_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取服务账户列表

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    result = await db.execute(
        select(ServiceAccountORM).order_by(ServiceAccountORM.created_at.desc())
    )
    accounts = result.scalars().all()

    return ServiceAccountListResponse(
        total=len(accounts),
        items=[_orm_to_response(sa) for sa in accounts]
    )


@router.get("/{name}", response_model=ApiResponse)
async def get_service_account(
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取服务账户详情

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(ServiceAccountORM).where(ServiceAccountORM.name == name))
    sa = result.scalars().first()

    if not sa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"服务账户 '{name}' 不存在"
        )

    return ApiResponse(data=_orm_to_response(sa))


@router.delete("/{name}", response_model=ApiResponse)
async def delete_service_account(
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """删除服务账户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(ServiceAccountORM).where(ServiceAccountORM.name == name))
    sa = result.scalars().first()

    if not sa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"服务账户 '{name}' 不存在"
        )

    await db.execute(delete(ServiceAccountORM).where(ServiceAccountORM.name == name))
    await db.commit()

    return ApiResponse(message=f"服务账户 '{name}' 已删除")


@router.post("/{name}/regenerate-secret", response_model=ApiResponse)
async def regenerate_secret(
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """重新生成服务账户密钥

    需要管理员或超级管理员权限。
    旧密钥将立即失效。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(ServiceAccountORM).where(ServiceAccountORM.name == name))
    sa = result.scalars().first()

    if not sa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"服务账户 '{name}' 不存在"
        )

    # 生成新密钥
    new_secret = await _generate_secret()
    secret_hash = await _hash_secret(new_secret)

    await db.execute(
        update(ServiceAccountORM)
        .where(ServiceAccountORM.name == name)
        .values(secret_hash=secret_hash)
    )
    await db.commit()

    # 返回新密钥（只显示一次）
    return ApiResponse(
        message="密钥重新生成成功",
        data={"secret": new_secret, "warning": "请妥善保管，此密钥只显示一次"}
    )


@router.post("/{name}/disable", response_model=ApiResponse)
async def disable_service_account(
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """禁用服务账户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(ServiceAccountORM).where(ServiceAccountORM.name == name))
    sa = result.scalars().first()

    if not sa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"服务账户 '{name}' 不存在"
        )

    await db.execute(
        update(ServiceAccountORM)
        .where(ServiceAccountORM.name == name)
        .values(is_active=False)
    )
    await db.commit()

    return ApiResponse(message=f"服务账户 '{name}' 已禁用")


@router.post("/{name}/enable", response_model=ApiResponse)
async def enable_service_account(
    name: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """启用服务账户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    result = await db.execute(select(ServiceAccountORM).where(ServiceAccountORM.name == name))
    sa = result.scalars().first()

    if not sa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"服务账户 '{name}' 不存在"
        )

    await db.execute(
        update(ServiceAccountORM)
        .where(ServiceAccountORM.name == name)
        .values(is_active=True)
    )
    await db.commit()

    return ApiResponse(message=f"服务账户 '{name}' 已启用")
