"""角色管理 API 路由

提供角色 CRUD 操作、权限管理等功能。
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from services.common.auth import get_current_user, TokenPayload
from services.common.database import get_db
from services.common.orm_models import RoleORM, PermissionORM, RolePermissionORM
from services.portal.models import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    ApiResponse,
)

router = APIRouter(prefix="/api/roles", tags=["roles"])


# ============================================================
# 权限检查
# ============================================================

def _check_super_admin_permission(user: TokenPayload) -> None:
    """检查用户是否有超级管理员权限"""
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )


# 预定义的权限列表
PREDEFINED_PERMISSIONS = {
    # 数据权限
    "data:read": "读取数据",
    "data:write": "写入数据",
    "data:delete": "删除数据",
    # Pipeline 权限
    "pipeline:read": "查看 Pipeline",
    "pipeline:run": "运行 Pipeline",
    "pipeline:manage": "管理 Pipeline",
    # 系统权限
    "system:admin": "系统管理",
    "system:user:manage": "用户管理",
    "system:config": "系统配置",
    "system:super_admin": "超级管理员",
    # 元数据权限
    "metadata:read": "读取元数据",
    "metadata:write": "写入元数据",
    # 敏感数据权限
    "sensitive:read": "查看敏感数据",
    "sensitive:manage": "管理敏感数据",
    # 审计权限
    "audit:read": "查看审计日志",
    # 服务调用权限
    "service:call": "服务间调用",
    # 数据质量权限
    "quality:read": "查看数据质量",
    "quality:manage": "管理数据质量",
}


# 预定义的角色列表
PREDEFINED_ROLES = {
    "super_admin": {
        "name": "超级管理员",
        "description": "拥有所有权限的超级管理员",
        "permissions": list(PREDEFINED_PERMISSIONS.keys()),
    },
    "admin": {
        "name": "管理员",
        "description": "系统管理员，拥有大部分权限",
        "permissions": [
            "data:read", "data:write", "data:delete",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "system:admin", "system:user:manage", "system:config",
            "metadata:read", "metadata:write",
            "sensitive:read", "sensitive:manage",
            "audit:read",
        ],
    },
    "data_scientist": {
        "name": "数据科学家",
        "description": "数据科学家，可以进行数据处理和分析",
        "permissions": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run",
            "metadata:read", "metadata:write",
            "sensitive:read",
        ],
    },
    "analyst": {
        "name": "数据分析师",
        "description": "数据分析师，可以查看和查询数据",
        "permissions": [
            "data:read",
            "pipeline:read",
            "metadata:read",
        ],
    },
    "viewer": {
        "name": "查看者",
        "description": "只读用户，只能查看数据",
        "permissions": [
            "data:read",
            "pipeline:read",
        ],
    },
    "service_account": {
        "name": "服务账户",
        "description": "服务间调用的账户",
        "permissions": [
            "service:call",
            "data:read",
        ],
    },
    "engineer": {
        "name": "数据工程师",
        "description": "数据工程师，负责ETL和数据处理",
        "permissions": [
            "data:read", "data:write",
            "pipeline:read", "pipeline:run", "pipeline:manage",
            "metadata:read", "metadata:write",
        ],
    },
    "steward": {
        "name": "数据治理员",
        "description": "数据治理员，负责数据质量管理",
        "permissions": [
            "data:read",
            "metadata:read", "metadata:write",
            "quality:read", "quality:manage",
        ],
    },
    "user": {
        "name": "普通用户",
        "description": "普通用户，基本数据访问权限",
        "permissions": ["data:read"],
    },
}


async def _ensure_permissions_exist(db: AsyncSession) -> None:
    """确保预定义的权限存在于数据库中"""
    for code, name in PREDEFINED_PERMISSIONS.items():
        result = await db.execute(select(PermissionORM).where(PermissionORM.code == code))
        if not result.scalars().first():
            # 确定权限分类
            category = code.split(":")[0]
            permission = PermissionORM(
                code=code,
                name=name,
                description=f"{name}权限",
                category=category,
            )
            db.add(permission)
    await db.commit()


def _orm_to_response(role: RoleORM, permissions: list[str]) -> dict:
    """将 ORM 模型转换为响应字典"""
    return {
        "id": role.id,
        "role_code": role.role_code,
        "role_name": role.role_name,
        "description": role.description or "",
        "is_system": role.is_system,
        "permissions": permissions,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "created_by": role.created_by,
    }


# ============================================================
# 角色管理端点
# ============================================================

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    req: RoleCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """创建新角色

    只有超级管理员可以创建角色。
    """
    _check_super_admin_permission(current_user)

    # 确保权限存在
    await _ensure_permissions_exist(db)

    # 检查角色代码是否已存在
    existing_result = await db.execute(select(RoleORM).where(RoleORM.role_code == req.role_code))
    if existing_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"角色 '{req.role_code}' 已存在"
        )

    # 验证权限是否存在
    valid_permissions = set(PREDEFINED_PERMISSIONS.keys())
    for perm in req.permissions:
        if perm not in valid_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的权限: {perm}"
            )

    # 创建角色
    role = RoleORM(
        role_code=req.role_code,
        role_name=req.role_name,
        description=req.description,
        created_by=current_user.user_id,
    )
    db.add(role)
    await db.flush()
    await db.refresh(role)

    # 添加权限关联
    for perm_code in req.permissions:
        role_perm = RolePermissionORM(
            role_id=role.id,
            permission_code=perm_code,
        )
        db.add(role_perm)

    await db.commit()

    return ApiResponse(
        message="角色创建成功",
        data={"role_code": role.role_code, "role_name": role.role_name}
    )


@router.get("", response_model=RoleListResponse)
async def list_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取角色列表

    需要管理员或超级管理员权限。
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    result = await db.execute(select(RoleORM).order_by(RoleORM.role_code))
    roles = result.scalars().all()

    # 获取每个角色的权限
    role_responses = []
    for role in roles:
        perm_result = await db.execute(
            select(RolePermissionORM)
            .where(RolePermissionORM.role_id == role.id)
        )
        role_perms = perm_result.scalars().all()
        permissions = [rp.permission_code for rp in role_perms]
        role_responses.append(_orm_to_response(role, permissions))

    return RoleListResponse(total=len(role_responses), items=role_responses)


@router.get("/{role_code}", response_model=ApiResponse)
async def get_role(
    role_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """获取角色详情

    需要管理员或超级管理员权限。
    """
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )

    result = await db.execute(select(RoleORM).where(RoleORM.role_code == role_code))
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"角色 '{role_code}' 不存在"
        )

    # 获取角色权限
    perm_result = await db.execute(
        select(RolePermissionORM)
        .where(RolePermissionORM.role_id == role.id)
    )
    role_perms = perm_result.scalars().all()
    permissions = [rp.permission_code for rp in role_perms]

    return ApiResponse(data=_orm_to_response(role, permissions))


@router.put("/{role_code}", response_model=ApiResponse)
async def update_role(
    role_code: str,
    req: RoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """更新角色

    只有超级管理员可以更新角色。
    """
    _check_super_admin_permission(current_user)

    result = await db.execute(select(RoleORM).where(RoleORM.role_code == role_code))
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"角色 '{role_code}' 不存在"
        )

    # 系统角色不能修改部分字段
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统内置角色不能修改"
        )

    # 更新基本信息
    update_data = {}
    if req.role_name is not None:
        update_data["role_name"] = req.role_name
    if req.description is not None:
        update_data["description"] = req.description

    if update_data:
        await db.execute(
            update(RoleORM)
            .where(RoleORM.role_code == role_code)
            .values(**update_data)
        )

    # 处理权限变更
    if req.add_permissions or req.remove_permissions:
        # 验证权限
        valid_permissions = set(PREDEFINED_PERMISSIONS.keys())
        for perm in req.add_permissions + req.remove_permissions:
            if perm not in valid_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的权限: {perm}"
                )

        # 添加权限
        for perm_code in req.add_permissions:
            existing = await db.execute(
                select(RolePermissionORM)
                .where(RolePermissionORM.role_id == role.id, RolePermissionORM.permission_code == perm_code)
            )
            if not existing.scalars().first():
                role_perm = RolePermissionORM(
                    role_id=role.id,
                    permission_code=perm_code,
                )
                db.add(role_perm)

        # 移除权限
        for perm_code in req.remove_permissions:
            await db.execute(
                delete(RolePermissionORM)
                .where(RolePermissionORM.role_id == role.id, RolePermissionORM.permission_code == perm_code)
            )

    await db.commit()

    return ApiResponse(message="角色更新成功")


@router.delete("/{role_code}", response_model=ApiResponse)
async def delete_role(
    role_code: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[TokenPayload, Depends(get_current_user)],
):
    """删除角色

    只有超级管理员可以删除非系统内置角色。
    """
    _check_super_admin_permission(current_user)

    result = await db.execute(select(RoleORM).where(RoleORM.role_code == role_code))
    role = result.scalars().first()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"角色 '{role_code}' 不存在"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统内置角色不能删除"
        )

    await db.execute(delete(RolePermissionORM).where(RolePermissionORM.role_id == role.id))
    await db.execute(delete(RoleORM).where(RoleORM.role_code == role_code))
    await db.commit()

    return ApiResponse(message=f"角色 '{role_code}' 已删除")
