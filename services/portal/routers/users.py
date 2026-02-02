"""用户管理 API 路由

提供用户 CRUD 操作、禁用/启用、密码重置等功能。
"""

import secrets
import hashlib
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.orm_models import UserORM, RoleORM, PermissionORM, RolePermissionORM
from services.portal.models import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    DisableUserRequest,
    ResetPasswordRequest,
    ApiResponse,
)

router = APIRouter(prefix="/api/users", tags=["users"])


# ============================================================
# 权限检查辅助函数
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


async def _hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


async def _verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, pwd_hash = password_hash.split(":")
        computed_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return computed_hash == pwd_hash
    except ValueError:
        return False


async def _get_user_by_username(db: AsyncSession, username: str) -> UserORM | None:
    """根据用户名获取用户"""
    result = await db.execute(select(UserORM).where(UserORM.username == username))
    return result.scalars().first()


def _orm_to_response(user: UserORM) -> dict:
    """将 ORM 模型转换为响应字典"""
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role_code,
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "is_active": user.is_active,
        "is_locked": user.is_locked,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "created_by": user.created_by,
    }


# ============================================================
# 用户管理端点
# ============================================================

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """创建新用户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    # 检查用户名是否已存在
    existing = await _get_user_by_username(db, req.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户名 '{req.username}' 已存在"
        )

    # 检查角色是否存在
    role_result = await db.execute(select(RoleORM).where(RoleORM.role_code == req.role))
    role = role_result.scalars().first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色 '{req.role}' 不存在"
        )

    # 检查是否尝试创建管理员角色（只有超级管理员可以）
    if req.role in ("admin", "super_admin") and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员可以创建管理员用户"
        )

    # 创建用户
    password_hash = await _hash_password(req.password)
    user = UserORM(
        username=req.username,
        password_hash=password_hash,
        role_code=req.role,
        display_name=req.display_name,
        email=req.email,
        phone=req.phone,
        created_by=current_user.user_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return ApiResponse(
        message="用户创建成功",
        data={"id": user.id, "username": user.username}
    )


@router.get("", response_model=UserListResponse)
async def list_users(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    role: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[TokenPayload, Depends(get_current_user)] = None,
):
    """获取用户列表

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    # 构建查询
    query = select(UserORM)
    count_query = select(UserORM)

    # 应用筛选条件
    if role:
        query = query.where(UserORM.role_code == role)
        count_query = count_query.where(UserORM.role_code == role)
    if is_active is not None:
        query = query.where(UserORM.is_active == is_active)
        count_query = count_query.where(UserORM.is_active == is_active)

    # 获取总数
    total_result = await db.execute(select(func.count()).select_from(UserORM))
    total = total_result.scalar() or 0

    # 分页
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(UserORM.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    # 非超级管理员不能看到超级管理员
    if current_user.role != "super_admin":
        users = [u for u in users if u.role_code != "super_admin"]

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_orm_to_response(u) for u in users]
    )


@router.get("/{username}", response_model=ApiResponse)
async def get_user(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取用户详情

    管理员可以查看所有用户，普通用户只能查看自己。
    """
    # 非管理员只能查看自己
    if current_user.role not in ("admin", "super_admin") and current_user.user_id != username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 非超级管理员不能查看超级管理员
    if current_user.role != "super_admin" and user.role_code == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    return ApiResponse(
        data=_orm_to_response(user)
    )


@router.put("/{username}", response_model=ApiResponse)
async def update_user(
    username: str,
    req: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """更新用户信息

    管理员可以更新所有用户，普通用户只能更新自己的基本信息。
    """
    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 权限检查
    is_self = current_user.user_id == username
    if not is_self and current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    # 非管理员不能修改角色
    if req.role and is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改自己的角色"
        )

    if req.role and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员可以修改用户角色"
        )

    # 构建更新数据
    update_data = {}
    if req.display_name is not None:
        update_data["display_name"] = req.display_name
    if req.email is not None:
        update_data["email"] = req.email
    if req.phone is not None:
        update_data["phone"] = req.phone
    if req.role is not None and current_user.role == "super_admin":
        update_data["role_code"] = req.role

    if update_data:
        await db.execute(
            update(UserORM)
            .where(UserORM.username == username)
            .values(**update_data)
        )
        await db.commit()

    return ApiResponse(message="用户信息更新成功")


@router.delete("/{username}", response_model=ApiResponse)
async def delete_user(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """删除用户

    只有超级管理员可以删除用户。不能删除自己。
    """
    _check_super_admin_permission(current_user)

    if username == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    await db.execute(delete(UserORM).where(UserORM.username == username))
    await db.commit()

    return ApiResponse(message="用户删除成功")


@router.post("/{username}/disable", response_model=ApiResponse)
async def disable_user(
    username: str,
    req: DisableUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """禁用用户

    需要管理员或超级管理员权限。不能禁用自己。
    """
    _check_admin_permission(current_user)

    if username == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用自己的账户"
        )

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 管理员不能禁用超级管理员
    if user.role_code == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    # 管理员不能禁用其他管理员
    if user.role_code == "admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有超级管理员可以禁用管理员"
        )

    await db.execute(
        update(UserORM)
        .where(UserORM.username == username)
        .values(
            is_active=False,
            disabled_at=datetime.utcnow(),
            disabled_by=req.disabled_by,
            disable_reason=req.reason,
        )
    )
    await db.commit()

    return ApiResponse(message=f"用户 '{username}' 已禁用")


@router.post("/{username}/enable", response_model=ApiResponse)
async def enable_user(
    username: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """启用用户

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 管理员不能启用超级管理员
    if user.role_code == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    await db.execute(
        update(UserORM)
        .where(UserORM.username == username)
        .values(
            is_active=True,
            disabled_at=None,
            disabled_by=None,
            disable_reason=None,
        )
    )
    await db.commit()

    return ApiResponse(message=f"用户 '{username}' 已启用")


@router.post("/{username}/reset-password", response_model=ApiResponse)
async def reset_user_password(
    username: str,
    req: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """重置用户密码

    需要管理员或超级管理员权限。
    """
    _check_admin_permission(current_user)

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 管理员不能重置超级管理员密码
    if user.role_code == "super_admin" and current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    password_hash = await _hash_password(req.new_password)
    await db.execute(
        update(UserORM)
        .where(UserORM.username == username)
        .values(
            password_hash=password_hash,
            password_changed_at=datetime.utcnow(),
        )
    )
    await db.commit()

    return ApiResponse(message="密码重置成功")


@router.put("/{username}/role", response_model=ApiResponse)
async def change_user_role(
    username: str,
    new_role: Annotated[str, Query()],
    reason: Annotated[str, Query()] = "",
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[TokenPayload, Depends(get_current_user)] = None,
):
    """修改用户角色

    只有超级管理员可以修改用户角色。
    """
    _check_super_admin_permission(current_user)

    if username == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的角色"
        )

    user = await _get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 '{username}' 不存在"
        )

    # 检查角色是否存在
    role_result = await db.execute(select(RoleORM).where(RoleORM.role_code == new_role))
    if not role_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色 '{new_role}' 不存在"
        )

    await db.execute(
        update(UserORM)
        .where(UserORM.username == username)
        .values(role_code=new_role)
    )
    await db.commit()

    return ApiResponse(message=f"用户 '{username}' 角色已修改为 '{new_role}'")
