"""Unit tests for token blacklist

Tests for services/common/token_blacklist.py
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

import pytest

import jwt

from services.common.token_blacklist import (
    get_blacklist,
    TokenBlacklist,
    _blacklist,
)


class TestGetBlacklist:
    """测试获取黑名单单例"""

    def test_get_blacklist_returns_singleton(self):
        """测试返回单例"""
        # Reset the global first
        import services.common.token_blacklist
        services.common.token_blacklist._blacklist = None

        bl1 = get_blacklist()
        bl2 = get_blacklist()

        assert id(bl1) == id(bl2)

    def test_get_blacklist_initializes_once(self):
        """测试只初始化一次"""
        # Reset the global first
        import services.common.token_blacklist
        services.common.token_blacklist._blacklist = None

        bl1 = get_blacklist()
        bl2 = get_blacklist()

        assert id(bl1) == id(bl2)


class TestTokenBlacklistInit:
    """测试黑名单初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        bl = TokenBlacklist()

        assert bl._redis is None
        assert bl._redis_url == "redis://localhost:6379/0"

    def test_init_custom_url(self):
        """测试自定义 Redis URL"""
        bl = TokenBlacklist(redis_url="redis://custom:6380/1")

        assert bl._redis_url == "redis://custom:6380/1"


class TestHashToken:
    """测试 Token hash"""

    def test_hash_token(self):
        """测试生成 Token hash"""
        bl = TokenBlacklist()

        token = "test_token_12345"
        result = bl._hash_token(token)

        assert isinstance(result, str)
        assert len(result) == 32  # SHA256 hex truncated to 32 chars
        assert result == bl._hash_token(token)  # Same input = same hash

    def test_hash_token_different_tokens(self):
        """测试不同 Token 产生不同 hash"""
        bl = TokenBlacklist()

        hash1 = bl._hash_token("token1")
        hash2 = bl._hash_token("token2")

        assert hash1 != hash2


class TestGetTokenJti:
    """测试从 Token 提取 JTI"""

    def test_get_token_jti_with_jti(self):
        """测试从带 JTI 的 Token 提取"""
        bl = TokenBlacklist()

        # Create a token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti-123", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                jti = bl.get_token_jti(token)

        assert jti == "test-jti-123"

    def test_get_token_jti_without_jti(self):
        """测试从无 JTI 的 Token 提取（使用 hash）"""
        bl = TokenBlacklist()

        # Create a token without jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                jti = bl.get_token_jti(token)

        # Should return hash of the token
        assert jti is not None
        assert len(jti) == 32

    def test_get_token_jti_invalid_token(self):
        """测试无效 Token 返回 None"""
        bl = TokenBlacklist()

        jti = bl.get_token_jti("invalid_token")

        assert jti is None


class TestGetTokenTtl:
    """测试获取 Token TTL"""

    def test_get_token_ttl_valid(self):
        """测试有效 Token 的 TTL"""
        bl = TokenBlacklist()

        # Create a token expiring in 1 hour
        secret = "test_secret"
        exp_time = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        token = jwt.encode(
            {"sub": "user", "exp": exp_time},
            secret,
            algorithm="HS256"
        )

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                ttl = bl._get_token_ttl(token)

        # Should be approximately 3600 seconds (1 hour)
        assert 3500 < ttl <= 3600

    def test_get_token_ttl_expired(self):
        """测试已过期 Token 的 TTL"""
        bl = TokenBlacklist()

        # Create an expired token
        secret = "test_secret"
        exp_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        token = jwt.encode(
            {"sub": "user", "exp": exp_time},
            secret,
            algorithm="HS256"
        )

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                ttl = bl._get_token_ttl(token)

        assert ttl == 0

    def test_get_token_ttl_invalid(self):
        """测试无效 Token 返回默认 TTL"""
        bl = TokenBlacklist()

        ttl = bl._get_token_ttl("invalid_token")

        assert ttl == 86400  # Default 24 hours


class TestIsAvailable:
    """测试 Redis 可用性检查"""

    def test_is_available_true(self):
        """测试 Redis 可用"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        bl._redis = mock_redis

        result = bl.is_available()

        assert result is True

    def test_is_available_false(self):
        """测试 Redis 不可用"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.is_available()

        assert result is False


class TestRevoke:
    """测试撤销 Token"""

    def test_revoke_redis_unavailable(self):
        """测试 Redis 不可用时撤销"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.revoke("test_token")

        assert result is False

    def test_revoke_invalid_token(self):
        """测试撤销无效 Token"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        bl._redis = mock_redis

        result = bl.revoke("invalid_token")

        assert result is False

    def test_revoke_expired_token(self):
        """测试撤销已过期 Token"""
        bl = TokenBlacklist()

        # Create an expired token
        secret = "test_secret"
        exp_time = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
        token = jwt.encode(
            {"sub": "user", "exp": exp_time},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.revoke(token)

        assert result is False

    def test_revoke_success(self):
        """测试成功撤销 Token"""
        bl = TokenBlacklist()

        # Create a valid token
        secret = "test_secret"
        exp_time = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti", "exp": exp_time},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.setex.return_value = True
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.revoke(token)

        assert result is True


class TestIsRevoked:
    """测试检查 Token 是否被撤销"""

    def test_is_revoked_redis_unavailable(self):
        """测试 Redis 不可用时返回 False"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.is_revoked("test_token")

        assert result is False

    def test_is_revoked_invalid_token(self):
        """测试无效 Token 返回 False"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        bl._redis = mock_redis

        result = bl.is_revoked("invalid_token")

        assert result is False

    def test_is_revoked_true(self):
        """测试 Token 已被撤销"""
        bl = TokenBlacklist()

        # Create a token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti-123", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 1
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.is_revoked(token)

        assert result is True

    def test_is_revoked_false(self):
        """测试 Token 未被撤销"""
        bl = TokenBlacklist()

        # Create a token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti-456", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 0
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.is_revoked(token)

        assert result is False


class TestRevokeUserTokens:
    """测试撤销用户所有 Token"""

    def test_revoke_user_tokens_redis_unavailable(self):
        """测试 Redis 不可时返回 0"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.revoke_user_tokens("user123")

        assert result == 0

    def test_revoke_user_tokens_success(self):
        """测试成功撤销用户 Token"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.setex.return_value = True
        bl._redis = mock_redis

        result = bl.revoke_user_tokens("user123")

        assert result == 1

    def test_revoke_user_tokens_with_exception(self):
        """测试异常情况"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.setex.side_effect = Exception("Redis error")
        bl._redis = mock_redis

        result = bl.revoke_user_tokens("user123")

        assert result == 0


class TestIsUserRevoked:
    """测试检查用户 Token 是否被批量撤销"""

    def test_is_user_revoked_redis_unavailable(self):
        """测试 Redis 不可时返回 False"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.is_user_revoked("user123", "token")

        assert result is False

    def test_is_user_revoked_no_key(self):
        """测试无撤销记录"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 0
        bl._redis = mock_redis

        result = bl.is_user_revoked("user123", "token")

        assert result is False

    def test_is_user_revoked_with_except_token(self):
        """测试排除当前 Token"""
        bl = TokenBlacklist()

        # Create token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "current-jti", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 1
        mock_redis.get.return_value = json.dumps({
            "revoked_at": "2024-01-01T00:00:00",
            "except_token_jti": "current-jti"
        })
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.is_user_revoked("user123", token)

        assert result is False  # Current token is excepted

    def test_is_user_revoked_true(self):
        """测试用户已被撤销"""
        bl = TokenBlacklist()

        # Create token with different jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "other-jti", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.exists.return_value = 1
        mock_redis.get.return_value = json.dumps({
            "revoked_at": "2024-01-01T00:00:00",
            "except_token_jti": "current-jti"
        })
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.is_user_revoked("user123", token)

        assert result is True


class TestGetRevokedInfo:
    """测试获取撤销信息"""

    def test_get_revoked_info_redis_unavailable(self):
        """测试 Redis 不可时返回 None"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = bl.get_revoked_info("token")

        assert result is None

    def test_get_revoked_info_invalid_token(self):
        """测试无效 Token 返回 None"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        bl._redis = mock_redis

        result = bl.get_revoked_info("invalid_token")

        assert result is None

    def test_get_revoked_info_no_data(self):
        """测试无撤销信息"""
        bl = TokenBlacklist()

        # Create token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.get_revoked_info(token)

        assert result is None

    def test_get_revoked_info_success(self):
        """测试成功获取撤销信息"""
        bl = TokenBlacklist()

        # Create token with jti
        secret = "test_secret"
        token = jwt.encode(
            {"sub": "user", "jti": "test-jti-789", "exp": 9999999999},
            secret,
            algorithm="HS256"
        )

        revoked_data = {
            "revoked_at": "2024-01-01T00:00:00",
            "jti": "test-jti-789"
        }

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = json.dumps(revoked_data)
        bl._redis = mock_redis

        with patch('services.common.token_blacklist.JWT_SECRET', secret):
            with patch('services.common.token_blacklist.JWT_ALGORITHM', 'HS256'):
                result = bl.get_revoked_info(token)

        assert result is not None
        assert result["jti"] == "test-jti-789"


class TestRemoveExpired:
    """测试清理过期条目"""

    def test_remove_expired(self):
        """测试清理过期条目"""
        bl = TokenBlacklist()

        # Redis automatically handles expiration, this is a stub
        result = bl.remove_expired()

        assert result == 0


class TestRevokeAll:
    """测试批量撤销所有 Token"""

    @pytest.mark.asyncio
    async def test_revoke_all_redis_unavailable(self):
        """测试 Redis 不可时返回 0"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        bl._redis = mock_redis

        result = await bl.revoke_all()

        assert result == 0

    @pytest.mark.asyncio
    async def test_revoke_all_success(self):
        """测试成功批量撤销"""
        bl = TokenBlacklist()

        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        mock_redis.scan_iter.return_value = []
        mock_redis.setex.return_value = True
        bl._redis = mock_redis

        result = await bl.revoke_all()

        assert result == 0  # No keys to revoke

    @pytest.mark.asyncio
    async def test_revoke_all_with_except_users(self):
        """测试带排除用户列表的批量撤销"""
        bl = TokenBlacklist()

        # Mock scan_iter to return different results for different match patterns
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        call_count = [0]

        def scan_iterator(match, *args, **kwargs):
            call_count[0] += 1
            if "user:" in match:
                return iter([b"user:bob", b"user:charlie"])  # alice excluded
            else:
                return iter([])  # No token:blacklist entries

        mock_redis.scan_iter.side_effect = scan_iterator
        mock_redis.get.return_value = json.dumps({"revoked_at": "2024-01-01"})
        mock_redis.setex.return_value = True
        bl._redis = mock_redis

        result = await bl.revoke_all(except_users=["alice"])

        # Should revoke bob and charlie (2 users)
        assert result == 2
