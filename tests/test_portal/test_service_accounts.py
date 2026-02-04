"""Unit tests for portal service_accounts router

Tests for services/portal/routers/service_accounts.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from services.common.auth import TokenPayload
from services.portal.models import ServiceAccountCreate
from services.portal.routers.service_accounts import (
    _check_admin_permission,
    _generate_secret,
    _hash_secret,
    _orm_to_response,
    create_service_account,
    delete_service_account,
    disable_service_account,
    enable_service_account,
    get_service_account,
    get_service_account_call_history,
    get_service_account_call_stats,
    list_service_accounts,
    regenerate_secret,
    router,
)


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/service-accounts"


class TestCheckAdminPermission:
    """测试管理员权限检查"""

    def test_check_admin_permission_success(self):
        """测试管理员通过检查"""
        mock_payload = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Should not raise
        _check_admin_permission(mock_payload)

    def test_check_admin_permission_super_admin(self):
        """测试超级管理员通过检查"""
        mock_payload = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Should not raise
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
        assert "权限不足" in exc_info.value.detail


class TestGenerateSecret:
    """测试密钥生成"""

    @pytest.mark.asyncio
    async def test_generate_secret(self):
        """测试生成密钥"""
        secret = await _generate_secret()

        assert secret.startswith("svc_")
        assert len(secret) > 40

    @pytest.mark.asyncio
    async def test_generate_secret_unique(self):
        """测试生成的密钥是唯一的"""
        secret1 = await _generate_secret()
        secret2 = await _generate_secret()

        assert secret1 != secret2


class TestHashSecret:
    """测试密钥哈希"""

    @pytest.mark.asyncio
    async def test_hash_secret(self):
        """测试哈希密钥"""
        secret = "test_secret_123"
        hash1 = await _hash_secret(secret)
        hash2 = await _hash_secret(secret)

        # Same input should produce different hashes due to salt
        assert hash1 != hash2
        # But both should start with $2b$ (bcrypt prefix)
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")


class TestOrmToResponse:
    """测试 ORM 到响应的转换"""

    def test_orm_to_response(self):
        """测试转换逻辑"""
        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_sa.name = "test_service"
        mock_sa.display_name = "Test Service"
        mock_sa.description = "A test service account"
        mock_sa.role_code = "service_account"
        mock_sa.is_active = True
        mock_sa.last_used_at = datetime(2023, 1, 1, 12, 0, 0)
        mock_sa.created_at = datetime(2023, 1, 1, 10, 0, 0)
        mock_sa.created_by = "admin"
        mock_sa.expires_at = datetime(2024, 1, 1, 10, 0, 0)

        result = _orm_to_response(mock_sa)

        assert result["id"] == 1
        assert result["name"] == "test_service"
        assert result["display_name"] == "Test Service"
        assert result["description"] == "A test service account"
        assert result["role"] == "service_account"
        assert result["is_active"] is True
        assert result["created_at"] == "2023-01-01T10:00:00"

    def test_orm_to_response_none_values(self):
        """测试空值处理"""
        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_sa.name = "test"
        mock_sa.display_name = "Test"
        mock_sa.description = None
        mock_sa.role_code = "service_account"
        mock_sa.is_active = True
        mock_sa.last_used_at = None
        mock_sa.created_at = None
        mock_sa.created_by = "admin"
        mock_sa.expires_at = None

        result = _orm_to_response(mock_sa)

        assert result["description"] == ""
        assert result["last_used_at"] is None
        assert result["created_at"] is None
        assert result["expires_at"] is None


class TestCreateServiceAccount:
    """测试创建服务账户端点"""

    @pytest.mark.asyncio
    async def test_create_service_account_success(self):
        """测试成功创建服务账户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="admin_id"
        )

        # Track call count for different execute calls
        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # First call checks existing account - none exists
                result.scalars.return_value.first.return_value = None
            elif call_count[0] == 2:
                # Second call checks role - role exists
                result.scalars.return_value.first.return_value = MagicMock()
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock created account - set the id after refresh
        def mock_refresh(sa):
            sa.id = 1

        mock_db.refresh.side_effect = mock_refresh

        req = ServiceAccountCreate(
            name="test_service",
            display_name="Test Service",
            description="A test service",
            role="service_account"
        )

        result = await create_service_account(req, mock_db, mock_user)

        assert result.name == "test_service"
        assert result.secret is not None
        assert result.secret.startswith("svc_")

    @pytest.mark.asyncio
    async def test_create_service_account_not_admin(self):
        """测试非管理员无法创建"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = ServiceAccountCreate(
            name="test",
            display_name="Test",
            role="service_account"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_service_account(req, mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestListServiceAccounts:
    """测试获取服务账户列表端点"""

    @pytest.mark.asyncio
    async def test_list_service_accounts_success(self):
        """测试成功获取服务账户列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock service accounts
        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_sa.name = "test_service"
        mock_sa.display_name = "Test Service"
        mock_sa.description = "Test"
        mock_sa.role_code = "service_account"
        mock_sa.is_active = True
        mock_sa.last_used_at = None
        mock_sa.created_at = datetime(2023, 1, 1)
        mock_sa.created_by = "admin"
        mock_sa.expires_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_sa]
        mock_db.execute.return_value = mock_result

        result = await list_service_accounts(mock_db, mock_user)

        assert result.total >= 0
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_list_service_accounts_viewer_forbidden(self):
        """测试普通用户无法获取服务账户列表"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_service_accounts(mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestGetServiceAccount:
    """测试获取服务账户详情端点"""

    @pytest.mark.asyncio
    async def test_get_service_account_success(self):
        """测试成功获取服务账户详情"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_sa.name = "test_service"
        mock_sa.display_name = "Test Service"
        mock_sa.description = "Test"
        mock_sa.role_code = "service_account"
        mock_sa.is_active = True
        mock_sa.last_used_at = None
        mock_sa.created_at = datetime(2023, 1, 1)
        mock_sa.created_by = "admin"
        mock_sa.expires_at = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result

        result = await get_service_account("test_service", mock_db, mock_user)

        assert result.data is not None
        assert result.data["name"] == "test_service"

    @pytest.mark.asyncio
    async def test_get_service_account_not_found(self):
        """测试获取不存在的服务账户"""
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
            await get_service_account("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestDeleteServiceAccount:
    """测试删除服务账户端点"""

    @pytest.mark.asyncio
    async def test_delete_service_account_success(self):
        """测试成功删除服务账户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_sa = MagicMock()
        mock_sa.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await delete_service_account("test_service", mock_db, mock_user)

        assert "已删除" in result.message

    @pytest.mark.asyncio
    async def test_delete_service_account_not_found(self):
        """测试删除不存在的服务账户"""
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
            await delete_service_account("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestRegenerateSecret:
    """测试重新生成密钥端点"""

    @pytest.mark.asyncio
    async def test_regenerate_secret_success(self):
        """测试成功重新生成密钥"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_sa = MagicMock()
        mock_sa.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await regenerate_secret("test_service", mock_db, mock_user)

        assert result.message == "密钥重新生成成功"
        assert result.data is not None
        assert "secret" in result.data

    @pytest.mark.asyncio
    async def test_regenerate_secret_not_found(self):
        """测试重新生成不存在的服务账户密钥"""
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
            await regenerate_secret("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestDisableServiceAccount:
    """测试禁用服务账户端点"""

    @pytest.mark.asyncio
    async def test_disable_service_account_success(self):
        """测试成功禁用服务账户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_sa = MagicMock()
        mock_sa.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await disable_service_account("test_service", mock_db, mock_user)

        assert "已禁用" in result.message

    @pytest.mark.asyncio
    async def test_disable_service_account_not_found(self):
        """测试禁用不存在的服务账户"""
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
            await disable_service_account("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestEnableServiceAccount:
    """测试启用服务账户端点"""

    @pytest.mark.asyncio
    async def test_enable_service_account_success(self):
        """测试成功启用服务账户"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_sa = MagicMock()
        mock_sa.id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        result = await enable_service_account("test_service", mock_db, mock_user)

        assert "已启用" in result.message

    @pytest.mark.asyncio
    async def test_enable_service_account_not_found(self):
        """测试启用不存在的服务账户"""
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
            await enable_service_account("nonexistent", mock_db, mock_user)

        assert exc_info.value.status_code == 404


class TestGetServiceAccountCallHistory:
    """测试获取服务账户调用历史端点"""

    @pytest.mark.asyncio
    async def test_get_call_history_success(self):
        """测试成功获取调用历史"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock service account
        mock_sa = MagicMock()
        mock_sa.id = 1

        # Mock audit events
        mock_event = MagicMock()
        mock_event.id = "evt_123"
        mock_event.subsystem = "api"
        mock_event.action = "get_data"
        mock_event.resource = "/api/data"
        mock_event.status_code = 200
        mock_event.duration_ms = 100
        mock_event.ip_address = "127.0.0.1"
        mock_event.created_at = datetime(2023, 1, 1)

        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # First call checks service account
                result.scalars.return_value.first.return_value = mock_sa
            elif call_count[0] == 2:
                # Second call gets count
                result.scalar.return_value = 10
            elif call_count[0] == 3:
                # Third call gets stats
                stats_row = MagicMock()
                stats_row.total_calls = 10
                stats_row.success_calls = 9
                stats_row.avg_duration = 150
                result.first.return_value = stats_row
            else:
                # Fourth call gets events
                result.scalars.return_value.all.return_value = [mock_event]
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)

        # Don't pass date filters to avoid Query issues
        result = await get_service_account_call_history(
            name="test_service",
            db=mock_db,
            current_user=mock_user,
            start_date=None,
            end_date=None,
            subsystem=None,
            page=1,
            page_size=50
        )

        assert result.service_account == "test_service"
        assert result.total >= 0
        assert isinstance(result.items, list)

    @pytest.mark.asyncio
    async def test_get_call_history_not_found(self):
        """测试获取不存在账户的调用历史"""
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
            # Use keyword arguments to avoid issues
            await get_service_account_call_history(
                name="nonexistent",
                db=mock_db,
                current_user=mock_user,
                start_date=None,
                end_date=None,
                subsystem=None,
                page=1,
                page_size=50
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_call_history_invalid_date_format(self):
        """测试无效日期格式"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock service account exists
        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_sa
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            # Use keyword arguments to avoid issues
            await get_service_account_call_history(
                name="test_service",
                db=mock_db,
                current_user=mock_user,
                start_date="invalid-date",
                end_date=None,
                subsystem=None,
                page=1,
                page_size=50
            )

        assert exc_info.value.status_code == 400
        assert "日期格式错误" in exc_info.value.detail


class TestGetServiceAccountCallStats:
    """测试获取服务账户调用统计端点"""

    @pytest.mark.asyncio
    async def test_get_call_stats_success(self):
        """测试成功获取调用统计"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock service account
        mock_sa = MagicMock()
        mock_sa.id = 1
        mock_sa.last_used_at = datetime(2023, 6, 1)

        # Mock stats
        mock_stats = MagicMock()
        mock_stats.total_calls = 100
        mock_stats.success_calls = 95
        mock_stats.avg_duration = 120
        mock_stats.last_call_at = datetime(2023, 6, 15)

        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                result.scalars.return_value.first.return_value = mock_sa
            else:
                result.first.return_value = mock_stats
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)

        result = await get_service_account_call_stats(
            "test_service",
            mock_db,
            mock_user
        )

        assert result.data is not None
        assert result.data["service_account"] == "test_service"

    @pytest.mark.asyncio
    async def test_get_call_stats_not_found(self):
        """测试获取不存在账户的调用统计"""
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
            await get_service_account_call_stats(
                "nonexistent",
                mock_db,
                mock_user
            )

        assert exc_info.value.status_code == 404
