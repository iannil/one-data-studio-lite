"""Unit tests for portal main

Tests for services/portal/main.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest

from services.portal.main import (
    _hash_password,
    _verify_password,
    _get_user_from_db,
    _get_permissions_for_role,
    app,
    SUBSYSTEMS,
    INTERNAL_SERVICES,
)
from services.common.orm_models import UserORM
from services.common.auth import TokenPayload


class TestHashPassword:
    """测试密码哈希"""

    def test_hash_password_returns_string(self):
        """测试返回字符串"""
        result = _hash_password("test_password")

        assert isinstance(result, str)
        assert ":" in result

    def test_hash_password_contains_salt_and_hash(self):
        """测试包含盐值和哈希值"""
        result = _hash_password("test_password")

        parts = result.split(":")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # 16 bytes salt = 32 hex chars
        assert len(parts[1]) == 64  # SHA256 = 64 hex chars

    def test_hash_password_different_passwords(self):
        """测试不同密码产生不同哈希"""
        result1 = _hash_password("password1")
        result2 = _hash_password("password2")

        assert result1 != result2

    def test_hash_password_same_password_different_salt(self):
        """测试相同密码不同盐值"""
        result1 = _hash_password("same_password")
        result2 = _hash_password("same_password")

        # 盐值不同，哈希值应该不同
        salt1, hash1 = result1.split(":")
        salt2, hash2 = result2.split(":")
        assert salt1 != salt2
        assert hash1 != hash2


class TestVerifyPassword:
    """测试密码验证"""

    def test_verify_password_correct(self):
        """测试正确密码"""
        password = "test_password"
        password_hash = _hash_password(password)

        result = _verify_password(password, password_hash)

        assert result is True

    def test_verify_password_incorrect(self):
        """测试错误密码"""
        password_hash = _hash_password("correct_password")

        result = _verify_password("wrong_password", password_hash)

        assert result is False

    def test_verify_password_invalid_format(self):
        """测试无效格式"""
        result = _verify_password("password", "invalid_format")

        assert result is False

    def test_verify_password_empty_parts(self):
        """测试空部分"""
        result = _verify_password("password", ":")

        assert result is False


class TestGetUserFromDb:
    """测试从数据库获取用户"""

    @pytest.mark.asyncio
    async def test_get_user_from_db_found(self):
        """测试找到用户"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_user = MagicMock(spec=UserORM)
        mock_user.username = "testuser"
        mock_result.scalars.return_value.first.return_value = mock_user
        mock_session.execute.return_value = mock_result

        result = await _get_user_from_db(mock_session, "testuser")

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_from_db_not_found(self):
        """测试用户不存在"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await _get_user_from_db(mock_session, "nonexistent")

        assert result is None


class TestGetPermissionsForRole:
    """测试根据角色获取权限"""

    def test_get_permissions_super_admin(self):
        """测试超级管理员权限"""
        result = _get_permissions_for_role("super_admin")

        assert isinstance(result, list)
        assert "system:super_admin" in result
        assert "system:admin" in result
        assert "data:read" in result
        assert "data:write" in result

    def test_get_permissions_admin(self):
        """测试管理员权限"""
        result = _get_permissions_for_role("admin")

        assert isinstance(result, list)
        assert "system:admin" in result
        assert "system:super_admin" not in result
        assert "data:read" in result
        assert "data:write" in result

    def test_get_permissions_data_scientist(self):
        """测试数据科学家权限"""
        result = _get_permissions_for_role("data_scientist")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "data:write" in result
        assert "pipeline:run" in result
        assert "system:admin" not in result

    def test_get_permissions_analyst(self):
        """测试分析师权限"""
        result = _get_permissions_for_role("analyst")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "data:write" not in result
        assert "pipeline:read" in result

    def test_get_permissions_viewer(self):
        """测试查看者权限"""
        result = _get_permissions_for_role("viewer")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "data:write" not in result
        assert "pipeline:read" in result

    def test_get_permissions_service_account(self):
        """测试服务账号权限"""
        result = _get_permissions_for_role("service_account")

        assert isinstance(result, list)
        assert "service:call" in result
        assert "data:read" in result

    def test_get_permissions_engineer(self):
        """测试工程师权限"""
        result = _get_permissions_for_role("engineer")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "data:write" in result
        assert "pipeline:manage" in result

    def test_get_permissions_steward(self):
        """测试数据管理员权限"""
        result = _get_permissions_for_role("steward")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "metadata:write" in result
        assert "quality:manage" in result

    def test_get_permissions_user(self):
        """测试普通用户权限"""
        result = _get_permissions_for_role("user")

        assert isinstance(result, list)
        assert "data:read" in result
        assert "data:write" not in result

    def test_get_permissions_unknown_role(self):
        """测试未知角色返回空列表"""
        result = _get_permissions_for_role("unknown_role")

        assert result == []


class TestSubsystemsConstant:
    """测试子系统配置常量"""

    def test_subsystems_not_empty(self):
        """测试子系统列表不为空"""
        assert len(SUBSYSTEMS) > 0

    def test_subsystems_structure(self):
        """测试子系统结构"""
        for sys in SUBSYSTEMS:
            assert "name" in sys
            assert "display_name" in sys
            assert "url" in sys
            assert "health_path" in sys

    def test_subsystems_contains_cube_studio(self):
        """测试包含 Cube-Studio"""
        cube_studio = [s for s in SUBSYSTEMS if s["name"] == "cube-studio"]
        assert len(cube_studio) == 1


class TestInternalServicesConstant:
    """测试内部服务配置常量"""

    def test_internal_services_not_empty(self):
        """测试内部服务列表不为空"""
        assert len(INTERNAL_SERVICES) > 0

    def test_internal_services_structure(self):
        """测试内部服务结构"""
        for svc in INTERNAL_SERVICES:
            assert "name" in svc
            assert "display_name" in svc
            assert "url" in svc

    def test_internal_services_contains_nl2sql(self):
        """测试包含 NL2SQL 服务"""
        nl2sql = [s for s in INTERNAL_SERVICES if s["name"] == "nl2sql"]
        assert len(nl2sql) == 1


class TestLifespan:
    """测试应用生命周期"""

    @pytest.mark.asyncio
    async def test_lifespan_startup_checks_security(self):
        """测试启动时检查安全配置"""
        from services.portal.main import lifespan

        mock_app = MagicMock()

        with patch('services.portal.main.check_security_configuration') as mock_check:
            with patch('services.portal.main.init_config_center', return_value=AsyncMock()):
                async with lifespan(mock_app):
                    mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_inits_config_center(self):
        """测试启动时初始化配置中心"""
        from services.portal.main import lifespan

        mock_app = MagicMock()

        with patch('services.portal.main.check_security_configuration'):
            with patch('services.portal.main.init_config_center', return_value=AsyncMock()) as mock_init:
                async with lifespan(mock_app):
                    mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_config_center_error_logged(self):
        """测试配置中心错误被记录"""
        from services.portal.main import lifespan

        mock_app = MagicMock()

        with patch('services.portal.main.check_security_configuration'):
            with patch('services.portal.main.init_config_center', side_effect=Exception("Connection error")):
                with patch('services.portal.main.logger') as mock_logger:
                    async with lifespan(mock_app):
                        mock_logger.warning.assert_called()


class TestLoginEndpoint:
    """测试登录端点"""

    @pytest.mark.asyncio
    async def test_login_success_db_user(self):
        """测试数据库用户登录成功"""
        from services.portal.main import login, LoginRequest, Response
        from services.common.auth import create_token

        mock_user = MagicMock(spec=UserORM)
        mock_user.username = "testuser"
        mock_user.role_code = "admin"
        mock_user.display_name = "Test User"
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.password_hash = _hash_password("password123")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            with patch('services.portal.main.create_token', return_value="test_token"):
                with patch('services.portal.main.settings.USE_COOKIE_AUTH', False):
                    req = LoginRequest(username="testuser", password="password123")
                    response = Response()
                    result = await login(req, response, mock_db)

                    assert result.success is True
                    assert result.token == "test_token"
                    assert result.user.username == "testuser"

    @pytest.mark.asyncio
    async def test_login_user_disabled(self):
        """测试已禁用用户登录失败"""
        from services.portal.main import login, LoginRequest, Response
        from fastapi import HTTPException

        mock_user = MagicMock(spec=UserORM)
        mock_user.is_active = False

        mock_db = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = LoginRequest(username="testuser", password="password123")
            response = Response()

            with pytest.raises(HTTPException) as exc_info:
                await login(req, response, mock_db)

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_login_user_locked(self):
        """测试已锁定用户登录失败"""
        from services.portal.main import login, LoginRequest, Response
        from fastapi import HTTPException

        mock_user = MagicMock(spec=UserORM)
        mock_user.is_active = True
        mock_user.is_locked = True

        mock_db = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = LoginRequest(username="testuser", password="password123")
            response = Response()

            with pytest.raises(HTTPException) as exc_info:
                await login(req, response, mock_db)

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """测试错误密码"""
        from services.portal.main import login, LoginRequest, Response
        from fastapi import HTTPException

        mock_user = MagicMock(spec=UserORM)
        mock_user.is_active = True
        mock_user.is_locked = False
        mock_user.password_hash = _hash_password("correct_password")
        mock_user.failed_login_attempts = 0

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = LoginRequest(username="testuser", password="wrong_password")
            response = Response()

            with pytest.raises(HTTPException) as exc_info:
                await login(req, response, mock_db)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_dev_user_success(self):
        """测试开发环境用户登录成功"""
        from services.portal.main import login, LoginRequest, Response

        mock_db = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=None):
            with patch('services.portal.main.create_token', return_value="test_token"):
                with patch('services.portal.main.settings.DEV_USERS', {
                    'admin': {'password': 'admin123', 'role': 'admin', 'display_name': 'Admin'}
                }):
                    with patch('services.portal.main.settings.USE_COOKIE_AUTH', False):
                        req = LoginRequest(username="admin", password="admin123")
                        response = Response()
                        result = await login(req, response, mock_db)

                        assert result.success is True
                        assert result.user.role == "admin"


class TestLogoutEndpoint:
    """测试登出端点"""

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(self):
        """测试登出清除 Cookie"""
        from services.portal.main import logout

        mock_response = MagicMock()

        with patch('services.portal.main.settings.USE_COOKIE_AUTH', True):
            with patch('services.portal.main.settings.COOKIE_DOMAIN', None):
                result = await logout(mock_response)

                assert result["success"] is True
                mock_response.delete_cookie.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_no_cookie_auth(self):
        """测试无 Cookie 认证时登出"""
        from services.portal.main import logout

        mock_response = MagicMock()

        with patch('services.portal.main.settings.USE_COOKIE_AUTH', False):
            result = await logout(mock_response)

            assert result["success"] is True
            mock_response.delete_cookie.assert_not_called()


class TestRefreshTokenEndpoint:
    """测试刷新令牌端点"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """测试刷新令牌成功"""
        from services.portal.main import refresh_user_token
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer old_token"}

        with patch('services.portal.main.refresh_token', return_value="new_token"):
            result = await refresh_user_token(mock_request)

            assert result.success is True
            assert result.token == "new_token"

    @pytest.mark.asyncio
    async def test_refresh_token_no_auth_header(self):
        """测试无认证头"""
        from services.portal.main import refresh_user_token
        from fastapi import Request, HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await refresh_user_token(mock_request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """测试无效令牌"""
        from services.portal.main import refresh_user_token
        from fastapi import Request, HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid_token"}

        with patch('services.portal.main.refresh_token', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_user_token(mock_request)

            assert exc_info.value.status_code == 401


class TestValidateTokenEndpoint:
    """测试令牌验证端点"""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """测试令牌验证成功"""
        from services.portal.main import validate_token
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer valid_token"}

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_db = AsyncMock()

        with patch('services.common.auth.verify_token', return_value=mock_payload):
            with patch('services.portal.main._get_user_from_db', return_value=None):
                with patch('services.portal.main.settings.DEV_USERS', {
                    'testuser': {'role': 'admin', 'display_name': 'Test User'}
                }):
                    result = await validate_token(mock_request, mock_db)

                    assert result["valid"] is True
                    assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_validate_token_no_auth_header(self):
        """测试无认证头"""
        from services.portal.main import validate_token
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        result = await validate_token(mock_request, None)

        assert result["valid"] is False
        assert result["code"] == 40100

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self):
        """测试无效令牌"""
        from services.portal.main import validate_token
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid_token"}

        with patch('services.common.auth.verify_token', side_effect=ValueError("Invalid token")):
            result = await validate_token(mock_request, None)

            assert result["valid"] is False
            assert result["code"] == 40102


class TestGetUserInfoEndpoint:
    """测试获取用户信息端点"""

    @pytest.mark.asyncio
    async def test_get_user_info_db_user(self):
        """测试获取数据库用户信息"""
        from services.portal.main import get_user_info

        mock_user = MagicMock(spec=UserORM)
        mock_user.display_name = "Test User"
        mock_user.email = "test@example.com"
        mock_user.phone = "1234567890"

        mock_db = AsyncMock()
        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            result = await get_user_info(mock_payload, mock_db)

            assert result["username"] == "testuser"
            assert result["display_name"] == "Test User"
            assert result["email"] == "test@example.com"
            assert result["phone"] == "1234567890"

    @pytest.mark.asyncio
    async def test_get_user_info_dev_user(self):
        """测试获取开发环境用户信息"""
        from services.portal.main import get_user_info

        mock_db = AsyncMock()
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.main._get_user_from_db', return_value=None):
            with patch('services.portal.main.settings.DEV_USERS', {
                'admin': {
                    'role': 'admin',
                    'display_name': 'Admin User',
                    'email': 'admin@example.com',
                    'phone': '9876543210'
                }
            }):
                result = await get_user_info(mock_payload, mock_db)

                assert result["username"] == "admin"
                assert result["display_name"] == "Admin User"
                assert result["email"] == "admin@example.com"


class TestRevokeTokenEndpoint:
    """测试撤销令牌端点"""

    @pytest.mark.asyncio
    async def test_revoke_token_success(self):
        """测试撤销令牌成功"""
        from services.portal.main import revoke_token
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer test_token"}
        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_blacklist = MagicMock()
        mock_blacklist.is_available.return_value = True
        mock_blacklist.revoke.return_value = True

        with patch('services.common.token_blacklist.get_blacklist', return_value=mock_blacklist):
            result = await revoke_token(mock_request, mock_payload)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_revoke_token_no_auth_header(self):
        """测试无认证头"""
        from services.portal.main import revoke_token
        from fastapi import Request
        from fastapi import HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await revoke_token(mock_request, mock_payload)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_token_blacklist_unavailable(self):
        """测试黑名单服务不可用"""
        from services.portal.main import revoke_token
        from fastapi import Request
        from fastapi import HTTPException

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer test_token"}
        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_blacklist = MagicMock()
        mock_blacklist.is_available.return_value = False

        with patch('services.common.token_blacklist.get_blacklist', return_value=mock_blacklist):
            with pytest.raises(HTTPException) as exc_info:
                await revoke_token(mock_request, mock_payload)

            assert exc_info.value.status_code == 503


class TestRevokeUserTokensEndpoint:
    """测试撤销用户令牌端点"""

    @pytest.mark.asyncio
    async def test_revoke_user_tokens_admin(self):
        """测试管理员撤销用户令牌"""
        from services.portal.main import revoke_user_tokens
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer admin_token"}
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_blacklist = MagicMock()
        mock_blacklist.is_available.return_value = True
        mock_blacklist.revoke_user_tokens.return_value = 5

        with patch('services.common.token_blacklist.get_blacklist', return_value=mock_blacklist):
            result = await revoke_user_tokens("target_user", mock_request, mock_payload)

            assert result["success"] is True
            assert result["count"] == 5

    @pytest.mark.asyncio
    async def test_revoke_user_tokens_forbidden(self):
        """测试非管理员无权限"""
        from services.portal.main import revoke_user_tokens
        from fastapi import Request
        from fastapi import HTTPException

        mock_request = MagicMock(spec=Request)
        mock_payload = TokenPayload(
            sub="user",
            username="user",
            role="user",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await revoke_user_tokens("target_user", mock_request, mock_payload)

        assert exc_info.value.status_code == 403


class TestRegisterEndpoint:
    """测试注册端点"""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """测试注册成功"""
        from services.portal.main import register, RegisterRequest

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        with patch('services.portal.main._get_user_from_db', return_value=None):
            with patch('services.portal.main.create_token', return_value="test_token"):
                req = RegisterRequest(
                    username="newuser",
                    password="StrongP@ss123",
                    role="viewer",
                    display_name="New User",
                    email="new@example.com"
                )
                result = await register(req, mock_db)

                assert result.success is True
                assert result.token == "test_token"
                assert result.user.username == "newuser"

    @pytest.mark.asyncio
    async def test_register_user_exists(self):
        """测试用户已存在"""
        from services.portal.main import register, RegisterRequest
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_user = MagicMock(spec=UserORM)

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = RegisterRequest(
                username="existing",
                password="StrongP@ss123",
                role="viewer",
                display_name="Existing User",
            )
            with pytest.raises(HTTPException) as exc_info:
                await register(req, mock_db)

            assert exc_info.value.status_code == 409


class TestChangePasswordEndpoint:
    """测试修改密码端点"""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """测试修改密码成功"""
        from services.portal.main import change_password, ChangePasswordRequest

        mock_user = MagicMock(spec=UserORM)
        mock_user.password_hash = _hash_password("old_password")

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="user",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = ChangePasswordRequest(
                old_password="old_password",
                new_password="new_password"
            )
            result = await change_password(req, mock_payload, mock_db)

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_change_password_wrong_old_password(self):
        """测试旧密码错误"""
        from services.portal.main import change_password, ChangePasswordRequest
        from fastapi import HTTPException

        mock_user = MagicMock(spec=UserORM)
        mock_user.password_hash = _hash_password("correct_old_password")

        mock_db = AsyncMock()
        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="user",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with patch('services.portal.main._get_user_from_db', return_value=mock_user):
            req = ChangePasswordRequest(
                old_password="wrong_old_password",
                new_password="new_password"
            )
            with pytest.raises(HTTPException) as exc_info:
                await change_password(req, mock_payload, mock_db)

            assert exc_info.value.status_code == 401


class TestGetPermissionsEndpoint:
    """测试获取权限端点"""

    @pytest.mark.asyncio
    async def test_get_permissions(self):
        """测试获取权限"""
        from services.portal.main import get_permissions

        mock_payload = TokenPayload(
            sub="testuser",
            username="testuser",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        result = await get_permissions(mock_payload)

        assert result["username"] == "testuser"
        assert result["role"] == "admin"
        assert isinstance(result["permissions"], list)
        assert len(result["permissions"]) > 0


class TestHealthCheckEndpoint:
    """测试健康检查端点"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from services.portal.main import health_check

        result = await health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "portal"


class TestListSubsystemsEndpoint:
    """测试列子系统端点"""

    @pytest.mark.asyncio
    async def test_list_subsystems(self):
        """测试列子系统"""
        from services.portal.main import list_subsystems

        with patch('services.portal.main._check_subsystems', return_value=[]):
            result = await list_subsystems()

            assert isinstance(result, list)


class TestPortalHomeEndpoint:
    """测试门户首页端点"""

    @pytest.mark.asyncio
    async def test_portal_home(self):
        """测试门户首页"""
        from services.portal.main import portal_home

        with patch('services.portal.main._check_subsystems', return_value=[]):
            result = await portal_home()

            assert result.name == "ONE-DATA-STUDIO-LITE"
            assert result.version == "0.1.0"


class TestCheckSubsystems:
    """测试检查子系统函数"""

    @pytest.mark.asyncio
    async def test_check_subsystems_all_healthy(self):
        """测试所有子系统健康"""
        from services.portal.main import _check_subsystems

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client_instance

            result = await _check_subsystems()

            assert len(result) > 0
            # Should have status "online" for successful requests

    @pytest.mark.asyncio
    async def test_check_subsystems_all_offline(self):
        """测试所有子系统离线"""
        from services.portal.main import _check_subsystems

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client_instance

            result = await _check_subsystems()

            assert len(result) > 0
            for status in result:
                assert status.status == "offline"


class TestCheckInternalServices:
    """测试检查内部服务函数"""

    @pytest.mark.asyncio
    async def test_check_internal_services(self):
        """测试检查内部服务"""
        from services.portal.main import _check_internal_services

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client_instance

            result = await _check_internal_services()

            assert len(result) > 0
            for service in result:
                assert "name" in service
                assert "status" in service


class TestHealthCheckAllEndpoint:
    """测试聚合健康检查端点"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """测试所有服务健康"""
        from services.portal.main import health_check_all

        with patch('services.portal.main._check_subsystems', return_value=[]):
            with patch('services.portal.main._check_internal_services', return_value=[]):
                result = await health_check_all()

                assert result["status"] == "healthy"
                assert result["portal"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_all_degraded(self):
        """测试服务降级"""
        from services.portal.main import health_check_all, SubsystemStatus

        offline_subsystem = SubsystemStatus(
            name="test",
            display_name="Test",
            url="http://test",
            status="offline"
        )

        unhealthy_service = {"name": "test", "status": "unhealthy"}

        with patch('services.portal.main._check_subsystems', return_value=[offline_subsystem]):
            with patch('services.portal.main._check_internal_services', return_value=[unhealthy_service]):
                result = await health_check_all()

                assert result["status"] == "degraded"
                assert result["unhealthy_count"] == 2


class TestSecurityCheckEndpoint:
    """测试安全检查端点"""

    @pytest.mark.asyncio
    async def test_security_check(self):
        """测试安全检查"""
        from services.portal.main import security_check

        with patch('services.portal.config.Settings.validate_security', return_value=[]):
            with patch('services.common.security.validate_env_config', return_value=[]):
                with patch('services.portal.config.Settings.is_production', return_value=False):
                    with patch.dict('os.environ', {}, clear=True):
                        result = await security_check()

                        assert "security_level" in result
                        assert "score" in result
                        assert "token_status" in result
                        assert "warnings" in result


class TestShutdownEndpoint:
    """测试关闭服务端点"""

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """测试优雅关闭"""
        from services.portal.main import shutdown_service
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "127.0.0.1"

        with patch('threading.Thread') as mock_thread_class:
            mock_thread = MagicMock()
            mock_thread_class.return_value = mock_thread

            result = await shutdown_service(mock_request)

            assert result["status"] == "shutting_down"
            assert result["initiated_by"] == "127.0.0.1"
            mock_thread.start.assert_called_once()
