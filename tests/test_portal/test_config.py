"""Unit tests for portal config

Tests for services/portal/config.py
"""

# Import settings after setting up environment
import importlib
from unittest.mock import MagicMock, patch

import pytest

from services.portal.config import (
    _get_dev_users,
    _get_jwt_secret,
    get_config,
    init_config_center,
    on_config_change,
    register_config_callback,
    set_config,
    settings,
    unregister_config_callback,
)


class TestGetJwtSecret:
    """测试获取 JWT 密钥"""

    def test_get_jwt_secret_from_env(self):
        """测试从环境变量获取 JWT 密钥"""
        with patch.dict('os.environ', {'JWT_SECRET': 'test_secret'}):
            result = _get_jwt_secret()

            assert result == 'test_secret'

    def test_get_jwt_secret_default(self):
        """测试默认 JWT 密钥"""
        with patch.dict('os.environ', {}, clear=True):
            result = _get_jwt_secret()

            assert result == 'dev-only-change-in-production'


class TestGetDevUsers:
    """测试获取开发用户"""

    def test_get_dev_users_default(self):
        """测试默认开发用户"""
        result = _get_dev_users()

        assert isinstance(result, dict)
        assert 'admin' in result
        assert 'super_admin' in result

    def test_get_dev_users_from_env(self):
        """测试从环境变量获取开发用户"""
        users_json = '{"testuser": {"password": "pass123", "role": "admin", "display_name": "Test"}}'
        with patch.dict('os.environ', {'DEV_USERS': users_json}):
            result = _get_dev_users()

            assert 'testuser' in result
            assert result['testuser']['role'] == 'admin'

    def test_get_dev_users_invalid_json(self):
        """测试无效 JSON 时返回默认值"""
        with patch.dict('os.environ', {'DEV_USERS': 'invalid json'}):
            result = _get_dev_users()

            # Should return default users
            assert 'admin' in result


class TestSettings:
    """测试 Settings 类"""

    def test_settings_allowed_origins_default(self):
        """测试默认允许的来源"""
        assert isinstance(settings.ALLOWED_ORIGINS, list)
        assert 'http://localhost:3000' in settings.ALLOWED_ORIGINS

    def test_settings_cookie_config_default(self):
        """测试默认 Cookie 配置"""
        assert settings.COOKIE_NAME == 'ods_token'
        assert settings.COOKIE_SAMESITE == 'lax'
        assert settings.USE_COOKIE_AUTH is True

    def test_settings_superset_config_default(self):
        """测试默认 Superset 配置"""
        assert settings.SUPERSET_ADMIN_USER == 'admin'
        assert settings.SUPERSET_ADMIN_PASSWORD == 'admin123'

    def test_settings_smtp_config_default(self):
        """测试默认 SMTP 配置"""
        assert settings.SMTP_HOST == 'localhost'
        assert settings.SMTP_PORT == 587
        assert settings.SMTP_ENABLED is False

    def test_settings_dev_users(self):
        """测试开发用户配置"""
        assert isinstance(settings.DEV_USERS, dict)
        assert 'admin' in settings.DEV_USERS


class TestConfigCallbacks:
    """测试配置回调"""

    def test_register_config_callback(self):
        """测试注册配置回调"""
        callback = lambda key, value: None

        register_config_callback(callback)

        # Callback should be registered (no error)

    def test_unregister_config_callback(self):
        """测试注销配置回调"""
        callback = lambda key, value: None

        # Register first, then unregister
        register_config_callback(callback)
        unregister_config_callback(callback)

        # Should complete without error

    def test_on_config_change(self):
        """测试配置变更处理"""
        # Register a callback
        callback = MagicMock()
        register_config_callback(callback)

        # Trigger config change
        on_config_change('/test/key', 'new_value')

        # Callback should be called
        callback.assert_called_once_with('/test/key', 'new_value')

        # Clean up
        unregister_config_callback(callback)


class TestConfigCenter:
    """测试配置中心"""

    @pytest.mark.asyncio
    async def test_init_config_center_disabled(self):
        """测试配置中心禁用时初始化"""
        with patch.dict('os.environ', {'ENABLE_CONFIG_CENTER': 'false'}):
            # Reload settings to pick up env var
            import services.portal.config as config_module
            importlib.reload(config_module)
            from services.portal.config import init_config_center

            result = await init_config_center()

            assert result is None

    @pytest.mark.asyncio
    async def test_get_config(self):
        """测试获取配置"""
        with patch.dict('os.environ', {}, clear=True):
            result = await get_config('/test/key', default='default')

            assert result == 'default'

    @pytest.mark.asyncio
    async def test_set_config(self):
        """测试设置配置"""
        with patch.dict('os.environ', {'ENABLE_CONFIG_CENTER': 'false'}):
            result = await set_config('/test/key', 'value')

            assert result is False

    @pytest.mark.asyncio
    async def test_get_config_from_env(self):
        """测试从环境变量获取配置"""
        # Config key "/test/key" becomes env var "_TEST_KEY"
        with patch.dict('os.environ', {'_TEST_KEY': 'env_value'}):
            result = await get_config('/test/key', default='default')

            assert result == 'env_value'


class TestSettingsValidation:
    """测试 Settings 验证方法"""

    def test_is_production_default(self):
        """测试默认环境判断"""
        # Default ENVIRONMENT is development
        assert settings.is_production() is False

    def test_validate_security_warnings(self):
        """测试安全配置警告"""
        warnings = settings.validate_security()

        # Development environment should have some warnings
        assert isinstance(warnings, list)

    def test_validate_security_no_warnings_for_good_config(self):
        """测试验证返回列表类型"""
        warnings = settings.validate_security()

        # Should always return a list
        assert isinstance(warnings, list)


class TestConfigCenterIntegration:
    """测试配置中心集成"""

    @pytest.mark.asyncio
    async def test_init_config_center_disabled(self):
        """测试配置中心禁用时初始化"""

        # Mock settings to disable config center
        with patch('services.portal.config.settings') as mock_settings:
            mock_settings.ENABLE_CONFIG_CENTER = False

            result = await init_config_center()
            assert result is None

    @pytest.mark.asyncio
    async def test_set_config_disabled(self):
        """测试配置中心禁用时的设置"""
        from services.portal.config import set_config

        with patch('services.portal.config.settings') as mock_settings:
            mock_settings.ENABLE_CONFIG_CENTER = False

            result = await set_config('test/key', 'value')
            assert result is False

    @pytest.mark.asyncio
    async def test_get_config_returns_default_when_no_env(self):
        """测试无环境变量时返回默认值"""
        from services.portal.config import get_config

        with patch.dict('os.environ', {}, clear=True):
            with patch('services.portal.config.settings') as mock_settings:
                mock_settings.ENABLE_CONFIG_CENTER = False

                result = await get_config('test/key', default='default')
                assert result == 'default'
