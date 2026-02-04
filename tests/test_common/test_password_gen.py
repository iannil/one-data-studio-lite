"""Unit tests for password generation utilities

Tests for services/common/password_gen.py
"""

import pytest

from services.common.password_gen import (
    PASSWORD_POLICIES,
    generate_api_token,
    generate_hex_token,
    generate_jwt_secret,
    generate_password,
    generate_password_policy,
    generate_webhook_secret,
)


class TestGeneratePassword:
    """测试 generate_password 函数"""

    def test_generate_password_default_length(self):
        """测试默认长度密码生成"""
        password = generate_password()
        assert len(password) == 16

    def test_generate_password_custom_length(self):
        """测试自定义长度密码生成"""
        password = generate_password(length=32)
        assert len(password) == 32

    def test_generate_password_with_uppercase(self):
        """测试包含大写字母的密码"""
        password = generate_password(length=100, use_uppercase=True, use_lowercase=False, use_digits=False, use_special=False)
        assert all(c.isupper() for c in password)
        assert len(password) == 100

    def test_generate_password_with_lowercase(self):
        """测试包含小写字母的密码"""
        password = generate_password(length=100, use_uppercase=False, use_lowercase=True, use_digits=False, use_special=False)
        assert all(c.islower() for c in password)
        assert len(password) == 100

    def test_generate_password_with_digits(self):
        """测试包含数字的密码"""
        password = generate_password(length=50, use_uppercase=False, use_lowercase=False, use_digits=True, use_special=False)
        assert all(c.isdigit() for c in password)
        assert len(password) == 50

    def test_generate_password_with_special(self):
        """测试包含特殊字符的密码"""
        password = generate_password(length=100, use_uppercase=False, use_lowercase=False, use_digits=False, use_special=True)
        assert all(c in "!@#$%&*" for c in password)
        assert len(password) == 100

    def test_generate_password_custom_special_chars(self):
        """测试自定义特殊字符集"""
        password = generate_password(length=50, use_uppercase=False, use_lowercase=False, use_digits=False, use_special=True, special_chars="+-=")
        assert all(c in "+-=" for c in password)

    def test_generate_password_all_types(self):
        """测试包含所有字符类型的密码"""
        # Generate multiple passwords to ensure probabilistic test passes
        passwords = [generate_password(length=100) for _ in range(10)]

        # Check at least one password has all required character types
        has_valid_password = False
        for password in passwords:
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%&*" for c in password)
            if has_upper and has_lower and has_digit and has_special:
                has_valid_password = True
                break

        assert has_valid_password, "No password with all required character types was generated"

    def test_generate_password_no_char_types_raises_error(self):
        """测试所有字符类型禁用时抛出错误"""
        with pytest.raises(ValueError, match="至少需要选择一种字符类型"):
            generate_password(use_uppercase=False, use_lowercase=False, use_digits=False, use_special=False)

    def test_generate_password_is_deterministic_length(self):
        """测试生成的密码长度正确"""
        for length in [8, 12, 16, 24, 32, 64]:
            password = generate_password(length=length)
            assert len(password) == length


class TestGenerateApiToken:
    """测试 generate_api_token 函数"""

    def test_generate_api_token_default_length(self):
        """测试默认长度 API Token 生成"""
        token = generate_api_token()
        assert len(token) == 32

    def test_generate_api_token_custom_length(self):
        """测试自定义长度 API Token 生成"""
        token = generate_api_token(length=48)
        assert len(token) == 48

    def test_generate_api_token_is_url_safe(self):
        """测试 API Token 是 URL 安全的"""
        token = generate_api_token()
        # URL-safe base64 只包含字母、数字、-、_
        assert all(c.isalnum() or c in '-_' for c in token)

    def test_generate_api_token_unique(self):
        """测试生成的 Token 是唯一的"""
        tokens = {generate_api_token() for _ in range(100)}
        assert len(tokens) == 100


class TestGenerateJwtSecret:
    """测试 generate_jwt_secret 函数"""

    def test_generate_jwt_secret_length(self):
        """测试 JWT 密钥长度"""
        secret = generate_jwt_secret()
        # 64 bytes base64 encoded
        assert len(secret) > 50

    def test_generate_jwt_secret_is_url_safe(self):
        """测试 JWT 密钥是 URL 安全的"""
        secret = generate_jwt_secret()
        assert all(c.isalnum() or c in '-_' for c in secret)

    def test_generate_jwt_secret_unique(self):
        """测试生成的密钥是唯一的"""
        secrets = {generate_jwt_secret() for _ in range(100)}
        assert len(secrets) == 100


class TestGenerateHexToken:
    """测试 generate_hex_token 函数"""

    def test_generate_hex_token_default(self):
        """测试默认长度十六进制 Token"""
        token = generate_hex_token()
        # 32 bytes = 64 hex chars
        assert len(token) == 64

    def test_generate_hex_token_custom_length(self):
        """测试自定义长度十六进制 Token"""
        token = generate_hex_token(length=16)
        assert len(token) == 32  # 2 chars per byte

    def test_generate_hex_token_only_hex(self):
        """测试只包含十六进制字符"""
        token = generate_hex_token()
        assert all(c in '0123456789abcdef' for c in token)

    def test_generate_hex_token_unique(self):
        """测试生成的 Token 是唯一的"""
        tokens = {generate_hex_token() for _ in range(100)}
        assert len(tokens) == 100


class TestGenerateWebhookSecret:
    """测试 generate_webhook_secret 函数"""

    def test_generate_webhook_secret_length(self):
        """测试 Webhook 密钥长度"""
        secret = generate_webhook_secret()
        assert len(secret) > 30

    def test_generate_webhook_secret_is_url_safe(self):
        """测试 Webhook 密钥是 URL 安全的"""
        secret = generate_webhook_secret()
        assert all(c.isalnum() or c in '-_' for c in secret)

    def test_generate_webhook_secret_unique(self):
        """测试生成的密钥是唯一的"""
        secrets = {generate_webhook_secret() for _ in range(100)}
        assert len(secrets) == 100


class TestGeneratePasswordPolicy:
    """测试 generate_password_policy 函数"""

    def test_generate_password_policy_strong(self):
        """测试强密码策略"""
        # Generate multiple passwords to ensure probabilistic test passes
        passwords = [generate_password_policy("strong") for _ in range(10)]

        # Check at least one password has all required character types
        has_valid_password = False
        for password in passwords:
            assert len(password) == 20
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            has_special = any(c in "!@#$%&*" for c in password)
            if has_upper and has_lower and has_digit and has_special:
                has_valid_password = True
                break

        assert has_valid_password, "No password with all required character types was generated"

    def test_generate_password_policy_medium(self):
        """测试中等密码策略"""
        # Generate multiple passwords to ensure probabilistic test passes
        passwords = [generate_password_policy("medium") for _ in range(10)]

        # Check all passwords have correct length and no special characters
        for password in passwords:
            assert len(password) == 16
            has_special = any(c in "!@#$%&*" for c in password)
            assert not has_special, "Medium policy should not include special characters"

        # Check at least one password has all required character types
        has_valid_password = False
        for password in passwords:
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            if has_upper and has_lower and has_digit:
                has_valid_password = True
                break

        assert has_valid_password, "No password with all required character types was generated"

    def test_generate_password_policy_simple(self):
        """测试简单密码策略"""
        # Generate multiple passwords to ensure probabilistic test passes
        passwords = [generate_password_policy("simple") for _ in range(10)]

        # Check all passwords have correct length
        for password in passwords:
            assert len(password) == 12

        # Check at least one password has all required character types
        has_valid_password = False
        for password in passwords:
            has_upper = any(c.isupper() for c in password)
            has_lower = any(c.islower() for c in password)
            has_digit = any(c.isdigit() for c in password)
            if has_upper and has_lower and has_digit:
                has_valid_password = True
                break

        assert has_valid_password, "No password with all required character types was generated"

    def test_generate_password_policy_invalid(self):
        """测试无效策略抛出错误"""
        with pytest.raises(ValueError, match="无效的密码策略"):
            generate_password_policy("invalid_policy")

    def test_password_policies_dict(self):
        """测试密码策略字典包含正确的键"""
        assert "strong" in PASSWORD_POLICIES
        assert "medium" in PASSWORD_POLICIES
        assert "simple" in PASSWORD_POLICIES
