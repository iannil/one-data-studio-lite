"""Unit tests for portal system router

Tests for services/portal/routers/system.py
"""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
from fastapi import HTTPException

from services.portal.routers.system import (
    _check_admin_permission,
    _check_super_admin_permission,
    router,
    get_system_config,
    update_system_config,
    initialize_system,
    get_system_metrics,
    emergency_stop,
    revoke_all_tokens,
)
from services.common.auth import TokenPayload
from services.portal.models import SystemConfigUpdate, SystemInitRequest, EmergencyStopRequest, RevokeAllTokensRequest


class TestRouter:
    """测试路由配置"""

    def test_router_prefix(self):
        """测试路由前缀"""
        assert router.prefix == "/api/system"


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


class TestGetSystemConfig:
    """测试获取系统配置端点"""

    @pytest.mark.asyncio
    async def test_get_system_config_success(self):
        """测试成功获取系统配置"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock configs
        mock_cfg1 = MagicMock()
        mock_cfg1.key = "app.name"
        mock_cfg1.value = "TestApp"
        mock_cfg1.is_sensitive = False

        mock_cfg2 = MagicMock()
        mock_cfg2.key = "app.secret"
        mock_cfg2.value = "secret123"
        mock_cfg2.is_sensitive = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_cfg1, mock_cfg2]
        mock_db.execute.return_value = mock_result

        result = await get_system_config(mock_db, mock_user)

        assert result.data is not None
        assert result.data["app.name"] == "TestApp"
        assert result.data["app.secret"] == "********"

    @pytest.mark.asyncio
    async def test_get_system_config_not_admin(self):
        """测试非管理员无法获取系统配置"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_system_config(mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestUpdateSystemConfig:
    """测试更新系统配置端点"""

    @pytest.mark.asyncio
    async def test_update_system_config_success(self):
        """测试成功更新系统配置"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="super_admin"
        )

        # Mock existing config
        mock_cfg = MagicMock()
        mock_cfg.key = "app.name"
        mock_cfg.value = "OldValue"

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_cfg
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()

        req = SystemConfigUpdate(key="app.name", value="NewValue")

        result = await update_system_config(req, mock_db, mock_user)

        assert result.message == "系统配置更新成功"

    @pytest.mark.asyncio
    async def test_update_system_config_not_super_admin(self):
        """测试非超级管理员无法更新"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = SystemConfigUpdate(key="test", value="value")

        with pytest.raises(HTTPException) as exc_info:
            await update_system_config(req, mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestInitializeSystem:
    """测试初始化系统端点"""

    @pytest.mark.asyncio
    async def test_initialize_system_success(self):
        """测试成功初始化系统"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="super_admin"
        )

        # Mock execute to handle the chain: execute().scalars().first()
        call_count = [0]

        async def mock_execute_side(query):
            call_count[0] += 1
            result = MagicMock()
            # Return None for .first() to indicate no existing configs
            result.scalars.return_value.first.return_value = None
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        req = SystemInitRequest()

        result = await initialize_system(req, mock_db, mock_user)

        assert "初始化" in result.message or "成功" in result.message

    @pytest.mark.asyncio
    async def test_initialize_system_not_super_admin(self):
        """测试非超级管理员无法初始化"""
        mock_db = AsyncMock()
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = SystemInitRequest()

        with pytest.raises(HTTPException) as exc_info:
            await initialize_system(req, mock_db, mock_user)

        assert exc_info.value.status_code == 403


class TestGetSystemMetrics:
    """测试获取系统指标端点"""

    @pytest.mark.asyncio
    async def test_get_system_metrics_success(self):
        """测试成功获取系统指标"""
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        # Mock psutil functions
        with patch('services.portal.routers.system.psutil') as mock_psutil:
            # Mock cpu_percent
            mock_psutil.cpu_percent.return_value = 50.0

            # Mock virtual_memory
            mock_mem = MagicMock()
            mock_mem.total = 8000000000
            mock_mem.available = 4000000000
            mock_mem.percent = 50.0
            mock_psutil.virtual_memory.return_value = mock_mem

            # Mock disk_usage
            mock_disk = MagicMock()
            mock_disk.total = 1000000000
            mock_disk.used = 500000000
            mock_disk.free = 500000000
            mock_disk.percent = 50.0
            mock_psutil.disk_usage.return_value = mock_disk

            # Mock boot_time
            mock_psutil.boot_time.return_value = 1672531200.0

            # Mock net_io_counters
            mock_net = MagicMock()
            mock_net.bytes_sent = 1000000
            mock_net.bytes_recv = 2000000
            mock_net.packets_sent = 1000
            mock_net.packets_recv = 2000
            mock_psutil.net_io_counters.return_value = mock_net

            result = await get_system_metrics(mock_user)

            assert result is not None
            assert hasattr(result, "status") or hasattr(result, "portal")

    @pytest.mark.asyncio
    async def test_get_system_metrics_not_admin(self):
        """测试非管理员无法获取系统指标"""
        mock_user = TokenPayload(
            sub="user",
            username="user",
            role="viewer",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_system_metrics(mock_user)

        assert exc_info.value.status_code == 403


class TestEmergencyStop:
    """测试紧急停止端点"""

    @pytest.mark.asyncio
    async def test_emergency_stop_success(self):
        """测试成功执行紧急停止"""
        mock_user = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1),
            user_id="super_admin"
        )

        req = EmergencyStopRequest(
            reason="Test emergency stop",
            confirmed=True
        )

        with patch('services.common.service_control.emergency_stop_all', new_callable=AsyncMock) as mock_stop:
            mock_stop.return_value = {"stopped": ["service1", "service2"]}
            result = await emergency_stop(req, mock_user)

            assert "停止" in result.message or "已执行" in result.message

    @pytest.mark.asyncio
    async def test_emergency_stop_not_confirmed(self):
        """测试未确认的紧急停止"""
        mock_user = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = EmergencyStopRequest(
            reason="Test",
            confirmed=False
        )

        with pytest.raises(HTTPException) as exc_info:
            await emergency_stop(req, mock_user)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_emergency_stop_not_super_admin(self):
        """测试非超级管理员无法执行"""
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = EmergencyStopRequest(
            reason="Test",
            confirmed=True
        )

        with pytest.raises(HTTPException) as exc_info:
            await emergency_stop(req, mock_user)

        assert exc_info.value.status_code == 403


class TestRevokeAllTokens:
    """测试撤销所有 Token 端点"""

    @pytest.mark.asyncio
    async def test_revoke_all_tokens_success(self):
        """测试成功撤销所有 Token"""
        mock_user = TokenPayload(
            sub="super",
            username="super",
            role="super_admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        mock_blacklist = MagicMock()
        mock_blacklist.revoke_all = AsyncMock(return_value=10)

        with patch('services.portal.routers.system.get_blacklist', return_value=mock_blacklist):
            req = RevokeAllTokensRequest(
                reason="Security audit",
                exclude_users=[]
            )

            result = await revoke_all_tokens(req, mock_user)

            assert "撤销" in result.message or "success" in result.message.lower()

    @pytest.mark.asyncio
    async def test_revoke_all_tokens_not_super_admin(self):
        """测试非超级管理员无法撤销"""
        mock_user = TokenPayload(
            sub="admin",
            username="admin",
            role="admin",
            exp=datetime(2099, 12, 31),
            iat=datetime(2023, 1, 1)
        )

        req = RevokeAllTokensRequest(
            reason="Test",
            exclude_users=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await revoke_all_tokens(req, mock_user)

        assert exc_info.value.status_code == 403
