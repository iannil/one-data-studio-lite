"""Unit tests for portal roles router

Tests for services/portal/routers/roles.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.common.auth import TokenPayload
from services.portal.models import RoleCreate, RoleUpdate
from services.portal.routers.roles import (
    PREDEFINED_PERMISSIONS,
    PREDEFINED_ROLES,
    _check_super_admin_permission,
    _ensure_permissions_exist,
    _orm_to_response,
    create_role,
    delete_role,
    get_role,
    list_roles,
    router,
    update_role,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/roles"


class TestPredefinedData:
    """测试预定义数据"""

    def test_predefined_permissions(self):
        """测试预定义权限列表"""
        assert "data:read" in PREDEFINED_PERMISSIONS
        assert "system:super_admin" in PREDEFINED_PERMISSIONS
        assert "pipeline:run" in PREDEFINED_PERMISSIONS
        assert len(PREDEFINED_PERMISSIONS) >= 15

    def test_predefined_roles(self):
        """测试预定义角色列表"""
        assert "super_admin" in PREDEFINED_ROLES
        assert "admin" in PREDEFINED_ROLES
        assert "viewer" in PREDEFINED_ROLES
        assert "service_account" in PREDEFINED_ROLES
        assert len(PREDEFINED_ROLES) >= 8


class TestCheckSuperAdminPermission:
    """测试超级管理员权限检查"""

    def test_check_super_admin_permission_success(self):
        """测试超级管理员通过检查"""
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Should not raise
        _check_super_admin_permission(mock_payload)

    def test_check_super_admin_permission_fails(self):
        """测试非超级管理员被拒绝"""
        mock_payload = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            _check_super_admin_permission(mock_payload)

        assert exc_info.value.status_code == 403
        assert "权限不足" in exc_info.value.detail


class TestOrmToResponse:
    """测试 ORM 到响应的转换"""

    def test_orm_to_response(self):
        """测试转换逻辑"""
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.role_code = "test_role"
        mock_role.role_name = "Test Role"
        mock_role.description = "A test role"
        mock_role.is_system = False
        mock_role.created_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_role.created_by = "admin"

        permissions = ["data:read", "data:write"]

        result = _orm_to_response(mock_role, permissions)

        assert result["id"] == 1
        assert result["role_code"] == "test_role"
        assert result["role_name"] == "Test Role"
        assert result["description"] == "A test role"
        assert result["is_system"] is False
        assert result["permissions"] == ["data:read", "data:write"]
        assert result["created_at"] == "2023-01-01T12:00:00"

    def test_orm_to_response_none_values(self):
        """测试空值处理"""
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.role_code = "test"
        mock_role.role_name = "Test"
        mock_role.description = None
        mock_role.is_system = False
        mock_role.created_at = None
        mock_role.created_by = None

        result = _orm_to_response(mock_role, [])

        assert result["description"] == ""
        assert result["created_at"] is None


class TestEnsurePermissionsExist:
    """测试确保权限存在"""

    @pytest.mark.asyncio
    async def test_ensure_permissions_exist_creates_missing(self):
        """测试创建缺失的权限"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()

        await _ensure_permissions_exist(mock_db)

        # Should have attempted to create permissions
        assert mock_db.execute.call_count >= len(PREDEFINED_PERMISSIONS)
        assert mock_db.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_ensure_permissions_exist_skips_existing(self):
        """测试跳过已存在的权限"""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        # Permission exists
        mock_result.scalars.return_value.first.return_value = MagicMock()
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        await _ensure_permissions_exist(mock_db)

        # Should not add anything since all exist
        assert mock_db.add.call_count == 0


class TestCreateRole:
    """测试创建角色端点"""

    @pytest.mark.asyncio
    async def test_create_role_success(self):
        """测试成功创建角色"""
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = AsyncMock(spec=AsyncSession)
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        # Mock existing role check - no existing role
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_execute_result
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.commit = AsyncMock()

        req = RoleCreate(
            role_code="custom_role",
            role_name="Custom Role",
            description="A custom role",
            permissions=["data:read"]
        )

        result = await create_role(req, mock_db, mock_user)

        assert result.data["role_code"] == "custom_role"
        assert result.data["role_name"] == "Custom Role"

    @pytest.mark.asyncio
    async def test_create_role_not_super_admin(self):
        """测试非超级管理员无法创建"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = RoleCreate(
            role_code="test",
            role_name="Test",
            permissions=["data:read"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_role(req, mock_db, mock_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_role_duplicate(self):
        """测试创建重复角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        # Mock existing role
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = MagicMock()
        mock_db.execute.return_value = mock_execute_result

        req = RoleCreate(
            role_code="admin",
            role_name="Admin",
            permissions=["data:read"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_role(req, mock_db, mock_user)

        assert exc_info.value.status_code == 409
        assert "已存在" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_role_invalid_permission(self):
        """测试创建角色时使用无效权限"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        # No existing role
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_execute_result

        req = RoleCreate(
            role_code="test",
            role_name="Test",
            permissions=["invalid:permission"]
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_role(req, mock_db, mock_user)

        assert exc_info.value.status_code == 400
        assert "无效的权限" in exc_info.value.detail


class TestListRoles:
    """测试获取角色列表端点"""

    @pytest.mark.asyncio
    async def test_list_roles_admin(self):
        """测试管理员获取角色列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock roles
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.role_code = "viewer"
        mock_role.role_name = "Viewer"
        mock_role.description = "Read only"
        mock_role.is_system = True
        mock_role.created_at = datetime(2023, 1, 1)
        mock_role.created_by = "system"

        # Mock role permission
        mock_role_perm = MagicMock()
        mock_role_perm.permission_code = "data:read"

        async def mock_execute_side(*args, **kwargs):
            if hasattr(mock_execute_side, 'call_count'):
                mock_execute_side.call_count += 1
            else:
                mock_execute_side.call_count = 1

            result = MagicMock()
            if mock_execute_side.call_count == 1:
                # First call gets roles
                result.scalars.return_value.all.return_value = [mock_role]
            else:
                # Subsequent calls get permissions
                result.scalars.return_value.all.return_value = [mock_role_perm]
            return result

        mock_db.execute = MagicMock(side_effect=mock_execute_side)

        result = await list_roles(mock_db, mock_user)

        assert result.total >= 0
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_list_roles_viewer_forbidden(self):
        """测试普通用户无法获取角色列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_roles(mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestGetRole:
    """测试获取角色详情端点"""

    @pytest.mark.asyncio
    async def test_get_role_success(self):
        """测试成功获取角色详情"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock role
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.role_code = "viewer"
        mock_role.role_name = "Viewer"
        mock_role.description = "Read only"
        mock_role.is_system = True
        mock_role.created_at = datetime(2023, 1, 1)
        mock_role.created_by = "system"

        # Mock role permission
        mock_role_perm = MagicMock()
        mock_role_perm.permission_code = "data:read"

        async def mock_execute_side(*args, **kwargs):
            # First call gets the role
            if hasattr(mock_execute_side, 'call_count'):
                mock_execute_side.call_count += 1
            else:
                mock_execute_side.call_count = 1

            result = MagicMock()
            if mock_execute_side.call_count == 1:
                result.scalars.return_value.first.return_value = mock_role
            else:
                result.scalars.return_value.all.return_value = [mock_role_perm]
            return result

        mock_db.execute = MagicMock(side_effect=mock_execute_side)

        result = await get_role("viewer", mock_db, mock_user)

        assert result.data is not None
        assert result.data["role_code"] == "viewer"

    @pytest.mark.asyncio
    async def test_get_role_not_found(self):
        """测试获取不存在的角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_role("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestUpdateRole:
    """测试更新角色端点"""

    @pytest.mark.asyncio
    async def test_update_role_success(self):
        """测试成功更新角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock role
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.role_code = "custom"
        mock_role.role_name = "Custom"
        mock_role.is_system = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        req = RoleUpdate(
            role_name="Updated Custom",
            description="Updated description"
        )

        result = await update_role("custom", req, mock_db, mock_user)

        assert result.message == "角色更新成功"

    @pytest.mark.asyncio
    async def test_update_role_system_role_forbidden(self):
        """测试无法更新系统角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock system role
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.is_system = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db.execute.return_value = mock_result

        req = RoleUpdate(role_name="New Name")

        with pytest.raises(HTTPException) as exc_info:
            await update_role("admin", req, mock_db, mock_user)

        assert exc_info.value.status_code == 400
        assert "系统内置角色" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_role_not_found(self):
        """测试更新不存在的角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        req = RoleUpdate(role_name="New Name")

        with pytest.raises(HTTPException) as exc_info:
            await update_role("nonexistent", req, mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestDeleteRole:
    """测试删除角色端点"""

    @pytest.mark.asyncio
    async def test_delete_role_success(self):
        """测试成功删除角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock non-system role
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.is_system = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await delete_role("custom", mock_db, mock_user)

        assert "已删除" in result.message

    @pytest.mark.asyncio
    async def test_delete_role_system_forbidden(self):
        """测试无法删除系统角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock system role
        mock_role = MagicMock()
        mock_role.id = 1
        mock_role.is_system = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_role
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_role("admin", mock_db, mock_user)

        assert exc_info.value.status_code == 400
        assert "系统内置角色" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_role_not_found(self):
        """测试删除不存在的角色"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_role("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404
