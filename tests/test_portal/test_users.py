"""Unit tests for portal users router

Tests for services/portal/routers/users.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi import HTTPException

from services.portal.routers.users import (
    _check_admin_permission,
    _check_super_admin_permission,
    _hash_password,
    _verify_password,
    _get_user_by_username,
    _orm_to_response,
    router,
    create_user,
    list_users,
    get_user,
    update_user,
    delete_user,
    disable_user,
)
from services.common.auth import TokenPayload
from services.portal.models import UserCreate, UserUpdate, DisableUserRequest


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/users"


class TestCheckAdminPermission:
    """测试管理员权限检查"""

    def test_check_admin_permission_admin_success(self):
        """测试管理员通过检查"""
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        _check_admin_permission(mock_payload)

    def test_check_admin_permission_super_admin_success(self):
        """测试超级管理员通过检查"""
        mock_payload = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        _check_admin_permission(mock_payload)

    def test_check_admin_permission_fails(self):
        """测试普通用户被拒绝"""
        mock_payload = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            _check_admin_permission(mock_payload)

        assert exc_info.value.status_code == 403


class TestCheckSuperAdminPermission:
    """测试超级管理员权限检查"""

    def test_check_super_admin_permission_success(self):
        """测试超级管理员通过检查"""
        mock_payload = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        _check_super_admin_permission(mock_payload)

    def test_check_super_admin_permission_fails_for_admin(self):
        """测试管理员被拒绝"""
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            _check_super_admin_permission(mock_payload)

        assert exc_info.value.status_code == 403


class TestHashPassword:
    """测试密码哈希"""

    @pytest.mark.asyncio
    async def test_hash_password(self):
        """测试哈希密码"""
        password = "test_password"
        hash1 = await _hash_password(password)
        hash2 = await _hash_password(password)

        # Same input should produce different hashes due to salt
        assert hash1 != hash2
        # Both should contain colon separator
        assert ":" in hash1
        assert ":" in hash2

    @pytest.mark.asyncio
    async def test_hash_password_format(self):
        """测试哈希格式"""
        password = "test_password"
        hash_result = await _hash_password(password)

        salt, pwd_hash = hash_result.split(":")
        assert len(salt) == 32  # 16 bytes = 32 hex chars
        assert len(pwd_hash) == 64  # SHA256 hex


class TestVerifyPassword:
    """测试密码验证"""

    @pytest.mark.asyncio
    async def test_verify_password_success(self):
        """测试验证成功"""
        password = "test_password"
        hash_result = await _hash_password(password)

        result = await _verify_password(password, hash_result)

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_password_failure(self):
        """测试验证失败"""
        password = "test_password"
        hash_result = await _hash_password(password)

        result = await _verify_password("wrong_password", hash_result)

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_password_invalid_hash(self):
        """测试无效哈希"""
        result = await _verify_password("test", "invalid_hash")

        assert result is False


class TestGetUserByUsername:
    """测试根据用户名获取用户"""

    @pytest.mark.asyncio
    async def test_get_user_by_username_found(self):
        """测试找到用户"""
        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await _get_user_by_username(mock_db, "testuser")

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_user_by_username_not_found(self):
        """测试未找到用户"""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await _get_user_by_username(mock_db, "nonexistent")

        assert result is None


class TestOrmToResponse:
    """测试 ORM 到响应的转换"""

    def test_orm_to_response(self):
        """测试转换逻辑"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.role_code = "viewer"
        mock_user.display_name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.phone = "1234567890"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = datetime(2023, 6, 1, 12, 0, 0)
        mock_user.created_at = datetime(2023, 1, 1, 10, 0, 0)
        mock_user.created_by = "admin"

        result = _orm_to_response(mock_user)

        assert result["id"] == 1
        assert result["username"] == "testuser"
        assert result["role"] == "viewer"
        assert result["display_name"] == "Test User"
        assert result["email"] == "test@example.com"
        assert result["is_active"] is True

    def test_orm_to_response_none_values(self):
        """测试空值处理"""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "test"
        mock_user.role_code = "viewer"
        mock_user.display_name = "Test"
        mock_user.email = None
        mock_user.phone = None
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.created_at = datetime(2023, 1, 1)
        mock_user.created_by = "admin"

        result = _orm_to_response(mock_user)

        assert result["email"] is None
        assert result["phone"] is None
        assert result["last_login_at"] is None


class TestCreateUser:
    """测试创建用户端点"""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """测试成功创建用户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # First call checks existing user - none exists
                result.scalars.return_value.first.return_value = None
            elif call_count[0] == 2:
                # Second call checks role - role exists
                mock_role = MagicMock()
                result.scalars.return_value.first.return_value = mock_role
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        req = UserCreate(
            username="newuser",
            password="StrongP@ss123",
            role="viewer",
            display_name="New User",
            email="new@example.com"
        )

        result = await create_user(req, mock_db, mock_user)

        assert result.message == "用户创建成功"
        assert result.data["username"] == "newuser"

    @pytest.mark.asyncio
    async def test_create_user_not_admin(self):
        """测试非管理员无法创建"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = UserCreate(
            username="test",
            password="StrongP@ss123",
            role="viewer",
            display_name="Test User"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_user(req, mock_db, mock_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user_duplicate(self):
        """测试创建重复用户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        # Mock existing user
        mock_existing = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_existing
        mock_db.execute.return_value = mock_result

        req = UserCreate(
            username="existing",
            password="StrongP@ss123",
            role="viewer",
            display_name="Existing User"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_user(req, mock_db, mock_user)

        assert exc_info.value.status_code == 409


class TestListUsers:
    """测试获取用户列表端点"""

    @pytest.mark.asyncio
    async def test_list_users_success(self):
        """测试成功获取用户列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock users
        mock_user1 = MagicMock()
        mock_user1.id = 1
        mock_user1.username = "user1"
        mock_user1.role_code = "viewer"
        mock_user1.is_active = True
        mock_user1.is_locked = False
        mock_user1.last_login_at = None
        mock_user1.created_at = datetime(2023, 1, 1)
        mock_user1.created_by = "admin"
        mock_user1.display_name = "User 1"
        mock_user1.email = None
        mock_user1.phone = None

        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # First call gets count
                result.scalar.return_value = 1
            else:
                # Second call gets users
                result.scalars.return_value.all.return_value = [mock_user1]
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)

        result = await list_users(
            page=1,
            page_size=20,
            role=None,
            is_active=None,
            db=mock_db,
            current_user=mock_user
        )

        assert result.total >= 0
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_list_users_viewer_forbidden(self):
        """测试普通用户无法获取用户列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_users(
                page=1,
                page_size=20,
                role=None,
                is_active=None,
                db=mock_db,
                current_user=mock_user
            )

        assert exc_info.value.status_code == 403


class TestGetUser:
    """测试获取用户详情端点"""

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """测试成功获取用户详情"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.role_code = "viewer"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.last_login_at = None
        mock_user.created_at = datetime(2023, 1, 1)
        mock_user.created_by = "admin"
        mock_user.display_name = "Test"
        mock_user.email = None
        mock_user.phone = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await get_user("testuser", mock_db, mock_admin)

        assert result.data is not None
        assert result.data["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """测试获取不存在的用户"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
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
            await get_user("nonexistent", mock_db, mock_admin)

        assert exc_info.value.status_code == 404


class TestUpdateUser:
    """测试更新用户端点"""

    @pytest.mark.asyncio
    async def test_update_user_success(self):
        """测试成功更新用户"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_user = MagicMock()
        mock_user.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        req = UserUpdate(
            display_name="Updated Name",
            email="updated@example.com"
        )

        result = await update_user("testuser", req, mock_db, mock_admin)

        assert result.message == "用户信息更新成功"

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """测试更新不存在的用户"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        req = UserUpdate(display_name="Updated")

        with pytest.raises(HTTPException) as exc_info:
            await update_user("nonexistent", req, mock_db, mock_admin)

        assert exc_info.value.status_code == 404


class TestDeleteUser:
    """测试删除用户端点"""

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """测试成功删除用户"""
        mock_db = AsyncMock()
        mock_super = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="super_admin"
        )

        # Mock user to delete (different from current user)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "other_user"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await delete_user("other_user", mock_db, mock_super)

        assert result.message == "用户删除成功"

    @pytest.mark.asyncio
    async def test_delete_user_not_super_admin(self):
        """测试非超级管理员无法删除"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        with pytest.raises(HTTPException) as exc_info:
            await delete_user("testuser", mock_db, mock_admin)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """测试删除不存在的用户"""
        mock_db = AsyncMock()
        mock_super = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="super_admin"
        )

        # Mock _get_user_by_username to return None
        async def mock_execute(query):
            result = MagicMock()
            result.scalars.return_value.first.return_value = None
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        with pytest.raises(HTTPException) as exc_info:
            await delete_user("nonexistent", mock_db, mock_super)

        assert exc_info.value.status_code == 404


class TestDisableUser:
    """测试禁用用户端点"""

    @pytest.mark.asyncio
    async def test_disable_user_success(self):
        """测试成功禁用用户"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        req = DisableUserRequest(
            reason="Violation of policy",
            disabled_by="admin"
        )

        result = await disable_user("testuser", req, mock_db, mock_admin)

        assert "已禁用" in result.message

    @pytest.mark.asyncio
    async def test_disable_user_not_found(self):
        """测试禁用不存在的用户"""
        mock_db = AsyncMock()
        mock_admin = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin"
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        req = DisableUserRequest(
            reason="Test",
            disabled_by="admin"
        )

        with pytest.raises(HTTPException) as exc_info:
            await disable_user("nonexistent", req, mock_db, mock_admin)

        assert exc_info.value.status_code == 404
