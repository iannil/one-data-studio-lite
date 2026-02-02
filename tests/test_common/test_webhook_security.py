"""Unit tests for webhook security utilities

Tests for services/common/webhook_security.py
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from services.common.webhook_security import (
    compute_signature,
    verify_signature,
    WebhookSignatureVerifier,
    create_webhook_verifier,
)


class TestComputeSignature:
    """测试签名计算"""

    def test_compute_signature_basic(self):
        """测试基本签名计算"""
        payload = b"test payload"
        secret = "test_secret"

        signature = compute_signature(payload, secret)

        assert signature.startswith("sha256=")
        assert len(signature) > 10

    def test_compute_signature_consistent(self):
        """测试相同输入产生相同签名"""
        payload = b"test payload"
        secret = "test_secret"

        sig1 = compute_signature(payload, secret)
        sig2 = compute_signature(payload, secret)

        assert sig1 == sig2

    def test_compute_signature_different_payloads(self):
        """测试不同载荷产生不同签名"""
        secret = "test_secret"

        sig1 = compute_signature(b"payload1", secret)
        sig2 = compute_signature(b"payload2", secret)

        assert sig1 != sig2

    def test_compute_signature_different_secrets(self):
        """测试不同密钥产生不同签名"""
        payload = b"test payload"

        sig1 = compute_signature(payload, "secret1")
        sig2 = compute_signature(payload, "secret2")

        assert sig1 != sig2


class TestVerifySignature:
    """测试签名验证"""

    def test_verify_signature_valid(self):
        """测试有效签名验证"""
        payload = b"test payload"
        secret = "test_secret"

        signature = compute_signature(payload, secret)
        is_valid = verify_signature(payload, signature, secret)

        assert is_valid is True

    def test_verify_signature_invalid(self):
        """测试无效签名验证"""
        payload = b"test payload"
        secret = "test_secret"

        is_valid = verify_signature(payload, "sha256=invalid", secret)

        assert is_valid is False

    def test_verify_signature_empty_signature(self):
        """测试空签名"""
        is_valid = verify_signature(b"payload", "", "secret")

        assert is_valid is False

    def test_verify_signature_empty_secret(self):
        """测试空密钥"""
        is_valid = verify_signature(b"payload", "sha256=abc", "")

        assert is_valid is False


class TestWebhookSignatureVerifier:
    """测试 Webhook 签名验证器"""

    def test_init_default(self):
        """测试默认初始化"""
        verifier = WebhookSignatureVerifier(secret="test_secret")

        assert verifier.secret == "test_secret"
        assert verifier.header_name == "x-datahub-signature"
        assert verifier.allow_unsigned is False

    def test_init_custom_header(self):
        """测试自定义签名头"""
        verifier = WebhookSignatureVerifier(
            secret="test_secret",
            header_name="X-Custom-Signature"
        )

        assert verifier.header_name == "x-custom-signature"

    def test_init_allow_unsigned(self):
        """测试允许无签名"""
        verifier = WebhookSignatureVerifier(
            secret="test_secret",
            allow_unsigned=True
        )

        assert verifier.allow_unsigned is True

    @pytest.mark.asyncio
    async def test_call_valid_signature(self):
        """测试有效签名调用"""
        verifier = WebhookSignatureVerifier(secret="test_secret")

        payload = b"test payload"
        signature = compute_signature(payload, "test_secret")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=payload)
        request.headers = {"x-datahub-signature": signature}

        result = await verifier(request)

        assert result == payload

    @pytest.mark.asyncio
    async def test_call_invalid_signature_raises(self):
        """测试无效签名抛出异常"""
        verifier = WebhookSignatureVerifier(secret="test_secret")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"payload")
        request.headers = {"x-datahub-signature": "sha256=invalid"}

        with pytest.raises(HTTPException) as exc_info:
            await verifier(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_call_missing_signature_raises(self):
        """测试缺少签名抛出异常"""
        verifier = WebhookSignatureVerifier(secret="test_secret")

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"payload")
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await verifier(request)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_call_missing_signature_allowed(self):
        """测试允许无签名"""
        verifier = WebhookSignatureVerifier(
            secret="test_secret",
            allow_unsigned=True
        )

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"payload")
        request.headers = {}

        result = await verifier(request)

        assert result == b"payload"

    @pytest.mark.asyncio
    async def test_call_no_secret_no_unsigned_raises(self):
        """测试无密钥且不允许无签名时抛出异常"""
        verifier = WebhookSignatureVerifier(secret="", allow_unsigned=False)

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"payload")
        request.headers = {}

        with pytest.raises(HTTPException) as exc_info:
            await verifier(request)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_call_no_secret_allow_unsigned(self):
        """测试无密钥但允许无签名"""
        verifier = WebhookSignatureVerifier(secret="", allow_unsigned=True)

        request = MagicMock(spec=Request)
        request.body = AsyncMock(return_value=b"payload")
        request.headers = {}

        result = await verifier(request)

        assert result == b"payload"


class TestCreateWebhookVerifier:
    """测试创建 Webhook 验证器工厂函数"""

    def test_create_default(self):
        """测试默认创建"""
        verifier = create_webhook_verifier(secret="test_secret")

        assert isinstance(verifier, WebhookSignatureVerifier)
        assert verifier.secret == "test_secret"

    def test_create_custom_header(self):
        """测试自定义签名头"""
        verifier = create_webhook_verifier(
            secret="test_secret",
            header_name="X-Custom-Signature"
        )

        assert verifier.header_name == "x-custom-signature"

    def test_create_development_mode_no_secret(self):
        """测试开发模式无密钥"""
        verifier = create_webhook_verifier(
            secret="",
            is_development=True
        )

        assert verifier.allow_unsigned is True

    def test_create_production_mode_no_secret(self):
        """测试生产模式无密钥"""
        verifier = create_webhook_verifier(
            secret="",
            is_development=False
        )

        assert verifier.allow_unsigned is False

    def test_create_development_mode_with_secret(self):
        """测试开发模式有密钥"""
        verifier = create_webhook_verifier(
            secret="test_secret",
            is_development=True
        )

        assert verifier.allow_unsigned is False
