"""Unit tests for email client

Tests for services/common/email_client.py

Note: aiosmtplib is an optional dependency. Tests will be skipped if not installed.
"""

import sys

import pytest

# Skip all tests if aiosmtplib is not installed
pytest.importorskip("aiosmtplib", reason="aiosmtplib not installed")

from unittest.mock import AsyncMock, MagicMock, patch

from services.common.email_client import (
    EmailClient,
    get_email_client,
    send_password_reset_email,
)


class TestEmailClient:
    """测试邮件客户端"""

    def test_init_default(self):
        """测试默认初始化"""
        with patch.dict('os.environ', {}, clear=True):
            client = EmailClient()

            assert client.host == "localhost"
            assert client.port == 587
            assert client.from_email == "noreply@one-data-studio.local"
            assert client.from_name == "ONE-DATA-STUDIO-LITE"

    def test_init_from_env(self):
        """测试从环境变量初始化"""
        with patch.dict('os.environ', {
            'SMTP_HOST': 'smtp.example.com',
            'SMTP_PORT': '465',
            'SMTP_USERNAME': 'user@example.com',
            'SMTP_PASSWORD': 'password',
            'SMTP_FROM_EMAIL': 'noreply@example.com',
            'SMTP_FROM_NAME': 'Example App',
            'SMTP_USE_TLS': 'false',
            'SMTP_TIMEOUT': '60',
            'SMTP_ENABLED': 'true',
        }):
            client = EmailClient()

            assert client.host == "smtp.example.com"
            assert client.port == 465
            assert client.username == "user@example.com"
            assert client.password == "password"
            assert client.from_email == "noreply@example.com"
            assert client.from_name == "Example App"
            assert client.use_tls is False
            assert client.timeout == 60

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        client = EmailClient(
            host="custom.host.com",
            port=2525,
            username="custom_user",
            password="custom_pass",
            from_email="custom@example.com",
            from_name="Custom App",
            use_tls=False,
            timeout=120,
        )

        assert client.host == "custom.host.com"
        assert client.port == 2525
        assert client.username == "custom_user"
        assert client.password == "custom_pass"
        assert client.from_email == "custom@example.com"
        assert client.from_name == "Custom App"
        assert client.use_tls is False
        assert client.timeout == 120

    def test_is_enabled_true(self):
        """测试邮件服务已启用"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient()

            assert client.is_enabled() is True

    def test_is_enabled_false(self):
        """测试邮件服务未启用"""
        with patch.dict('os.environ', {}, clear=True):
            client = EmailClient()

            assert client.is_enabled() is False

    def test_is_configured_true(self):
        """测试邮件服务已配置"""
        client = EmailClient(host="smtp.example.com", from_email="test@example.com")

        assert client.is_configured() is True

    def test_is_configured_false_no_host(self):
        """测试邮件服务未配置（无主机）"""
        with patch.dict('os.environ', {}, clear=True):
            client = EmailClient()

            # localhost is set, from_email is set
            # So this would be configured
            client2 = EmailClient(host="", from_email="test@example.com")
            assert client2.is_configured() is False

    def test_is_configured_false_no_from_email(self):
        """测试邮件服务未配置（无发件人）"""
        client = EmailClient(host="smtp.example.com", from_email="")

        assert client.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_email_not_enabled(self):
        """测试邮件服务未启用时发送"""
        with patch.dict('os.environ', {}, clear=True):
            client = EmailClient()

            result = await client.send_email("test@example.com", "Test", "<p>Test</p>")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_not_configured(self):
        """测试邮件服务未配置时发送"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient(host="", from_email="")

            result = await client.send_email("test@example.com", "Test", "<p>Test</p>")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """测试成功发送邮件"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient(
                host="smtp.example.com",
                from_email="noreply@example.com",
                username="user",
                password="pass",
            )

            # Mock SMTP
            with patch('services.common.email_client.aiosmtplib.SMTP') as mock_smtp:
                mock_smtp_instance = AsyncMock()
                mock_smtp_instance.__aenter__ = AsyncMock(return_value=mock_smtp_instance)
                mock_smtp_instance.__aexit__ = AsyncMock()
                mock_smtp_instance.login = AsyncMock()
                mock_smtp_instance.send_message = AsyncMock()
                mock_smtp.return_value = mock_smtp_instance

                result = await client.send_email("test@example.com", "Test", "<p>Test</p>")

                assert result is True

    @pytest.mark.asyncio
    async def test_send_email_smtp_error(self):
        """测试 SMTP 错误处理"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient(
                host="smtp.example.com",
                from_email="noreply@example.com",
            )

            # Mock SMTP to raise error
            with patch('services.common.email_client.aiosmtplib.SMTP') as mock_smtp:
                mock_smtp_instance = AsyncMock()
                mock_smtp_instance.__aenter__ = AsyncMock(side_effect=Exception("SMTP Error"))
                mock_smtp.return_value = mock_smtp_instance

                result = await client.send_email("test@example.com", "Test", "<p>Test</p>")

                assert result is False

    @pytest.mark.asyncio
    async def test_send_email_multiple_recipients(self):
        """测试发送给多个收件人"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient(
                host="smtp.example.com",
                from_email="noreply@example.com",
            )

            with patch('services.common.email_client.aiosmtplib.SMTP') as mock_smtp:
                mock_smtp_instance = AsyncMock()
                mock_smtp_instance.__aenter__ = AsyncMock(return_value=mock_smtp_instance)
                mock_smtp_instance.__aexit__ = AsyncMock()
                mock_smtp_instance.send_message = AsyncMock()
                mock_smtp.return_value = mock_smtp_instance

                result = await client.send_email(
                    ["test1@example.com", "test2@example.com"],
                    "Test",
                    "<p>Test</p>"
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_send_password_reset_code_not_enabled(self):
        """测试邮件未启用时发送密码重置码"""
        with patch.dict('os.environ', {}, clear=True):
            client = EmailClient()

            result = await client.send_password_reset_code("test@example.com", "123456")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_password_reset_code_success(self):
        """测试成功发送密码重置码"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            client = EmailClient(
                host="smtp.example.com",
                from_email="noreply@example.com",
            )

            with patch('services.common.email_client.aiosmtplib.SMTP') as mock_smtp:
                mock_smtp_instance = AsyncMock()
                mock_smtp_instance.__aenter__ = AsyncMock(return_value=mock_smtp_instance)
                mock_smtp_instance.__aexit__ = AsyncMock()
                mock_smtp_instance.send_message = AsyncMock()
                mock_smtp.return_value = mock_smtp_instance

                result = await client.send_password_reset_code(
                    "test@example.com",
                    "123456",
                    username="testuser",
                    expires_minutes=30,
                )

                assert result is True


class TestGetEmailClient:
    """测试获取邮件客户端单例"""

    def test_get_email_client_returns_singleton(self):
        """测试返回单例"""
        client1 = get_email_client()
        client2 = get_email_client()

        assert client1 is client2

    def test_get_email_client_initializes_once(self):
        """测试只初始化一次"""
        # Clear the global first
        import services.common.email_client
        services.common.email_client._email_client = None

        client1 = get_email_client()
        client2 = get_email_client()

        assert id(client1) == id(client2)


class TestSendPasswordResetEmail:
    """测试发送密码重置邮件便捷函数"""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_not_enabled(self):
        """测试邮件未启用时发送"""
        with patch.dict('os.environ', {}, clear=True):
            result = await send_password_reset_email("test@example.com", "123456")

            assert result is False

    @pytest.mark.asyncio
    async def test_send_password_reset_email_with_username(self):
        """测试带用户名发送"""
        with patch.dict('os.environ', {'SMTP_ENABLED': 'true'}):
            # Mock the client
            with patch('services.common.email_client.EmailClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.send_password_reset_code = AsyncMock(return_value=True)
                mock_client_class.return_value = mock_client

                result = await send_password_reset_email(
                    "test@example.com",
                    "123456",
                    username="testuser"
                )

                assert result is True
                mock_client.send_password_reset_code.assert_called_once()
