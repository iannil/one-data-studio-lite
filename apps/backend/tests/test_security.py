from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    def test_get_password_hash(self):
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 50

    def test_verify_password_correct(self):
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "test_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    def test_create_access_token(self):
        subject = "user_123"
        token = create_access_token(subject)

        assert token is not None
        assert len(token) > 50

    def test_decode_access_token_valid(self):
        subject = "user_123"
        token = create_access_token(subject)

        payload = decode_access_token(token)

        assert payload is not None
        assert payload["sub"] == subject
        assert "exp" in payload

    def test_decode_access_token_invalid(self):
        payload = decode_access_token("invalid_token")
        assert payload is None

    def test_create_token_with_extra_data(self):
        subject = "user_123"
        extra = {"role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(subject, extra_data=extra)

        payload = decode_access_token(token)

        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_token_expiration(self):
        from datetime import timedelta

        subject = "user_123"
        token = create_access_token(subject, expires_delta=timedelta(hours=2))

        payload = decode_access_token(token)
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        assert exp_time > now
        assert (exp_time - now).total_seconds() <= 2 * 3600 + 60
