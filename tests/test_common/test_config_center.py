"""Unit tests for config center

Tests for services/common/config_center.py

Note: cryptography is an optional dependency. Tests will be skipped if not installed.
"""


import pytest

# Skip all tests if cryptography is not installed
pytest.importorskip("cryptography", reason="cryptography not installed")

from unittest.mock import AsyncMock, MagicMock, patch

from services.common.config_center import (
    decrypt_value,
    encrypt_value,
    get_config,
    get_config_center,
    reset_config_center,
    set_config,
    watch_callback,
)


class TestEncryptValue:
    """测试值加密"""

    def test_encrypt_value(self):
        """测试加密值"""
        with patch('services.common.config_center._get_encryption_key') as mock_key:
            mock_key.return_value = b'test_key_32_bytes_long_for_test!'

            result = encrypt_value("test_value")

            assert isinstance(result, str)
            assert result != "test_value"


class TestDecryptValue:
    """测试值解密"""

    def test_decrypt_value(self):
        """测试解密值"""
        with patch('services.common.config_center._get_encryption_key') as mock_key:
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            mock_key.return_value = key

            # Encrypt first
            encrypted = encrypt_value("test_value")
            # Then decrypt
            decrypted = decrypt_value(encrypted)

            assert decrypted == "test_value"

    def test_decrypt_value_invalid(self):
        """测试解密无效值"""
        with patch('services.common.config_center._get_encryption_key') as mock_key:
            mock_key.return_value = b'test_key_32_bytes_long_for_test!'

            result = decrypt_value("invalid_encrypted_value")

            # Should return the original value on error
            assert result == "invalid_encrypted_value"


class TestGetConfigCenter:
    """测试获取配置中心单例"""

    def test_get_config_center_returns_singleton(self):
        """测试返回单例"""
        reset_config_center()

        cc1 = get_config_center()
        cc2 = get_config_center()

        assert id(cc1) == id(cc2)

    def test_reset_config_center(self):
        """测试重置配置中心"""
        cc1 = get_config_center()
        reset_config_center()
        cc2 = get_config_center()

        assert isinstance(cc2, type(cc1))


class TestWatchCallback:
    """测试监听回调装饰器"""

    def test_watch_callback_decorator(self):
        """测试监听回调装饰器"""
        with patch('services.common.config_center.get_config_center') as mock_cc:
            mock_cc_instance = MagicMock()
            mock_cc.return_value = mock_cc_instance

            @watch_callback('/test/prefix/')
            def callback(key, value):
                return f"{key}={value}"

            assert callable(callback)


class TestGetConfig:
    """测试获取配置便捷函数"""

    @pytest.mark.asyncio
    async def test_get_config(self):
        """测试获取配置"""
        with patch.dict('os.environ', {}, clear=True):
            result = await get_config('/test/key', default='default')

            assert result == 'default'


class TestSetConfig:
    """测试设置配置便捷函数"""

    @pytest.mark.asyncio
    async def test_set_config(self):
        """测试设置配置"""
        with patch('services.common.config_center.get_config_center') as mock_cc:
            mock_cc_instance = AsyncMock()
            mock_cc_instance.put = AsyncMock(return_value=True)
            mock_cc.return_value = mock_cc_instance

            result = await set_config('/test/key', 'value')

            assert result is True
