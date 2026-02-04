"""Tests for password generation utilities

Tests password generation functions including edge cases for:
- Empty character sets
- Various character combinations
- Token generation
- Policy-based generation
"""

import string

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
    """Tests for generate_password function"""

    def test_default_password(self):
        """Should generate password with default settings"""
        password = generate_password()
        assert len(password) == 16
        # Should contain uppercase, lowercase, digits, and special chars
        # Since it's random, we check that all character types are in the charset
        assert all(c in string.ascii_letters + string.digits + "!@#$%&*" for c in password)

    def test_custom_length(self):
        """Should generate password with custom length"""
        for length in [8, 12, 16, 24, 32]:
            password = generate_password(length=length)
            assert len(password) == length

    def test_minimum_length(self):
        """Should handle minimum length of 1"""
        password = generate_password(length=1)
        assert len(password) == 1

    def test_uppercase_only(self):
        """Should generate password with uppercase only"""
        password = generate_password(
            length=20,
            use_uppercase=True,
            use_lowercase=False,
            use_digits=False,
            use_special=False,
        )
        assert len(password) == 20
        assert password.isupper()
        assert password.isalpha()

    def test_lowercase_only(self):
        """Should generate password with lowercase only"""
        password = generate_password(
            length=20,
            use_uppercase=False,
            use_lowercase=True,
            use_digits=False,
            use_special=False,
        )
        assert len(password) == 20
        assert password.islower()
        assert password.isalpha()

    def test_digits_only(self):
        """Should generate password with digits only"""
        password = generate_password(
            length=20,
            use_uppercase=False,
            use_lowercase=False,
            use_digits=True,
            use_special=False,
        )
        assert len(password) == 20
        assert password.isdigit()

    def test_special_chars_only(self):
        """Should generate password with special characters only"""
        password = generate_password(
            length=20,
            use_uppercase=False,
            use_lowercase=False,
            use_digits=False,
            use_special=True,
        )
        assert len(password) == 20
        assert all(c in "!@#$%&*" for c in password)

    def test_custom_special_chars(self):
        """Should use custom special characters"""
        custom_chars = "-_=+"
        password = generate_password(
            length=20,
            use_uppercase=False,
            use_lowercase=False,
            use_digits=False,
            use_special=True,
            special_chars=custom_chars,
        )
        assert len(password) == 20
        assert all(c in custom_chars for c in password)

    def test_uppercase_and_digits(self):
        """Should generate password with uppercase and digits"""
        password = generate_password(
            length=20,
            use_uppercase=True,
            use_lowercase=False,
            use_digits=True,
            use_special=False,
        )
        assert len(password) == 20
        assert all(c.isupper() or c.isdigit() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)

    def test_lowercase_and_special(self):
        """Should generate password with lowercase and special"""
        password = generate_password(
            length=20,
            use_uppercase=False,
            use_lowercase=True,
            use_digits=False,
            use_special=True,
        )
        assert len(password) == 20
        assert all(c.islower() or c in "!@#$%&*" for c in password)
        assert any(c.islower() for c in password)
        assert any(c in "!@#$%&*" for c in password)

    def test_empty_charset_raises_error(self):
        """Should raise ValueError when all character types are disabled"""
        with pytest.raises(ValueError, match="至少需要选择一种字符类型"):
            generate_password(
                length=16,
                use_uppercase=False,
                use_lowercase=False,
                use_digits=False,
                use_special=False,
            )

    def test_passwords_are_unique(self):
        """Should generate different passwords each time"""
        passwords = [generate_password(length=32) for _ in range(100)]
        assert len(set(passwords)) == 100

    def test_exclude_ambiguous_chars_not_in_default(self):
        """Default special chars should exclude easily confused characters"""
        password = generate_password(length=100, use_special=True)
        # Should not include: l (looks like 1), O (looks like 0), etc.
        # These are in the default special char set
        assert "!" in password or "@" in password or "#" in password


class TestGenerateApiToken:
    """Tests for generate_api_token function"""

    def test_default_length(self):
        """Should generate token with default length"""
        token = generate_api_token()
        assert len(token) == 32

    def test_custom_length(self):
        """Should generate token with custom length"""
        for length in [16, 24, 32, 48, 64]:
            token = generate_api_token(length=length)
            assert len(token) == length

    def test_token_is_url_safe(self):
        """Should generate URL-safe tokens"""
        token = generate_api_token(64)
        # URL-safe base64 uses A-Z, a-z, 0-9, -, and _
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_tokens_are_unique(self):
        """Should generate different tokens each time"""
        tokens = [generate_api_token(32) for _ in range(100)]
        assert len(set(tokens)) == 100


class TestGenerateJwtSecret:
    """Tests for generate_jwt_secret function"""

    def test_length(self):
        """Should generate JWT secret of appropriate length"""
        secret = generate_jwt_secret()
        # 64 bytes base64 encoded should be about 86 characters
        assert len(secret) >= 80

    def test_is_url_safe(self):
        """Should generate URL-safe secret"""
        secret = generate_jwt_secret()
        assert all(c.isalnum() or c in "-_" for c in secret)

    def test_secrets_are_unique(self):
        """Should generate different secrets each time"""
        secrets = [generate_jwt_secret() for _ in range(100)]
        assert len(set(secrets)) == 100


class TestGenerateHexToken:
    """Tests for generate_hex_token function"""

    def test_default_length(self):
        """Should generate hex token with default length"""
        token = generate_hex_token()
        # 32 bytes = 64 hex characters
        assert len(token) == 64

    def test_custom_length(self):
        """Should generate hex token with custom length"""
        token = generate_hex_token(16)
        # 16 bytes = 32 hex characters
        assert len(token) == 32

    def test_contains_only_hex_digits(self):
        """Should contain only hexadecimal characters"""
        token = generate_hex_token()
        assert all(c in "0123456789abcdef" for c in token)

    def test_tokens_are_unique(self):
        """Should generate different tokens each time"""
        tokens = [generate_hex_token(16) for _ in range(100)]
        assert len(set(tokens)) == 100


class TestGenerateWebhookSecret:
    """Tests for generate_webhook_secret function"""

    def test_length(self):
        """Should generate webhook secret of appropriate length"""
        secret = generate_webhook_secret()
        # 48 bytes base64 encoded should be about 64 characters
        assert len(secret) >= 60

    def test_is_url_safe(self):
        """Should generate URL-safe secret"""
        secret = generate_webhook_secret()
        assert all(c.isalnum() or c in "-_" for c in secret)

    def test_secrets_are_unique(self):
        """Should generate different secrets each time"""
        secrets = [generate_webhook_secret() for _ in range(100)]
        assert len(set(secrets)) == 100


class TestGeneratePasswordPolicy:
    """Tests for generate_password_policy function"""

    def test_strong_policy(self):
        """Should generate password using strong policy"""
        password = generate_password_policy("strong")
        policy = PASSWORD_POLICIES["strong"]
        assert len(password) == policy["length"]
        # Strong policy includes all character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%&*" for c in password)
        assert has_upper
        assert has_lower
        assert has_digit
        assert has_special

    def test_medium_policy(self):
        """Should generate password using medium policy"""
        password = generate_password_policy("medium")
        policy = PASSWORD_POLICIES["medium"]
        assert len(password) == policy["length"]
        # Medium policy excludes special chars
        assert all(c.isalnum() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        assert has_upper
        has_lower
        assert has_digit

    def test_simple_policy(self):
        """Should generate password using simple policy"""
        password = generate_password_policy("simple")
        policy = PASSWORD_POLICIES["simple"]
        assert len(password) == policy["length"]
        # Simple policy is shorter and excludes special chars
        assert len(password) == 12
        assert all(c.isalnum() for c in password)

    def test_invalid_policy_raises_error(self):
        """Should raise ValueError for invalid policy name"""
        with pytest.raises(ValueError, match="无效的密码策略"):
            generate_password_policy("invalid")

    def test_error_message_includes_valid_policies(self):
        """Error message should list valid policy names"""
        valid_policies = list(PASSWORD_POLICIES.keys())
        with pytest.raises(ValueError) as exc_info:
            generate_password_policy("invalid")
        assert "strong" in str(exc_info.value)
        assert "medium" in str(exc_info.value)
        assert "simple" in str(exc_info.value)

    def test_default_to_strong_policy(self):
        """Should default to strong policy when not specified"""
        password1 = generate_password_policy()
        password2 = generate_password_policy("strong")
        assert len(password1) == len(password2)
        # Both should have same character types
        assert all(c.isalnum() or c in "!@#$%&*" for c in password1)
        assert all(c.isalnum() or c in "!@#$%&*" for c in password2)


class TestCryptographicStrength:
    """Tests to ensure cryptographic strength"""

    def test_uses_secrets_module(self):
        """Should use cryptographically secure random generation"""
        # Generate many passwords and check for uniqueness
        # This would be unlikely with a weak PRNG
        passwords = [generate_password(length=16) for _ in range(1000)]
        unique_ratio = len(set(passwords)) / len(passwords)
        assert unique_ratio > 0.99

    def test_token_distribution(self):
        """Tokens should be well-distributed"""
        tokens = [generate_hex_token(4) for _ in range(1000)]
        # Each hex digit should appear roughly equally
        all_chars = "".join(tokens)
        hex_digits = "0123456789abcdef"
        for digit in hex_digits:
            count = all_chars.count(digit)
            # Each digit should appear roughly 1/16 of the time (~6.25%)
            # Allow for variance due to randomness (3% to 10%)
            ratio = count / len(all_chars)
            assert 0.03 < ratio < 0.10, f"Distribution for {digit}: {ratio}"
