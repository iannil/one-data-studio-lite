"""认证模块单元测试"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

from services.common.auth import (
    TokenPayload,
    can_refresh_token,
    create_token,
    refresh_token,
    verify_token,
)


class TestCreateToken:
    """测试 Token 创建"""

    def test_create_token_default(self):
        """测试使用默认过期时间创建 Token"""
        token = create_token("user123", "testuser")
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT 格式

        payload = verify_token(token)
        assert payload.sub == "user123"
        assert payload.username == "testuser"
        assert payload.role == "user"

    def test_create_token_with_role(self):
        """测试创建带角色的 Token"""
        token = create_token("user123", "testuser", role="admin")
        payload = verify_token(token)
        assert payload.role == "admin"

    def test_create_token_custom_expiry(self):
        """测试自定义过期时间"""
        token = create_token(
            "user123",
            "testuser",
            expires_delta=timedelta(hours=1)
        )
        payload = verify_token(token)
        # 验证过期时间约为 1 小时后
        now = datetime.now(UTC)
        assert payload.exp > now + timedelta(minutes=59)
        assert payload.exp < now + timedelta(minutes=61)


class TestVerifyToken:
    """测试 Token 验证"""

    def test_verify_valid_token(self):
        """测试验证有效 Token"""
        token = create_token("user123", "testuser")
        payload = verify_token(token)
        assert payload.sub == "user123"

    def test_verify_invalid_token(self):
        """测试验证无效 Token"""
        with pytest.raises(HTTPException) as exc:
            verify_token("invalid_token")
        assert exc.value.status_code == 401

    def test_verify_expired_token(self):
        """测试验证过期 Token"""
        # 创建已过期的 Token
        token = create_token(
            "user123",
            "testuser",
            expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert "过期" in exc.value.detail


class TestRefreshToken:
    """测试 Token 刷新"""

    def test_can_refresh_in_window(self):
        """测试在刷新窗口内可以刷新"""
        # 创建即将过期的 Token
        token = create_token(
            "user123",
            "testuser",
            expires_delta=timedelta(minutes=25)  # 在 30 分钟窗口内
        )
        assert can_refresh_token(token) is True

    def test_cannot_refresh_fresh_token(self):
        """测试新创建的 Token 不能刷新"""
        token = create_token("user123", "testuser")
        assert can_refresh_token(token) is False

    def test_refresh_token(self):
        """测试刷新 Token"""
        old_token = create_token(
            "user123",
            "testuser",
            expires_delta=timedelta(minutes=25)
        )
        new_token = refresh_token(old_token)

        assert new_token is not None
        assert new_token != old_token

        # 新 Token 有效期应该更长
        old_payload = verify_token(old_token)
        new_payload = verify_token(new_token)
        assert new_payload.exp > old_payload.exp

    def test_refresh_expired_token_too_old(self):
        """测试过期太久的 Token 不能刷新"""
        import jwt

        from services.common.auth import JWT_ALGORITHM, JWT_SECRET

        # 创建超过 30 分钟前过期的 Token
        exp_time = datetime.now(UTC) - timedelta(minutes=31)
        payload = {
            "sub": "user123",
            "username": "testuser",
            "role": "user",
            "exp": exp_time,
        }
        old_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        new_token = refresh_token(old_token)
        assert new_token is None


class TestTokenPayload:
    """测试 TokenPayload 模型"""

    def test_token_payload_creation(self):
        """测试创建 TokenPayload"""
        exp = datetime.now(UTC) + timedelta(hours=1)
        payload = TokenPayload(
            sub="user123",
            username="testuser",
            role="admin",
            exp=exp,
        )
        assert payload.sub == "user123"
        assert payload.username == "testuser"
        assert payload.role == "admin"
        assert payload.exp == exp


@pytest.mark.redis
class TestTokenBlacklist:
    """测试 Token 黑名单

    这些测试需要 Redis 运行在 localhost:6379
    """

    @pytest.fixture
    def blacklist(self, monkeypatch):
        """Token 黑名单测试 fixture"""
        from services.common.token_blacklist import TokenBlacklist

        # 使用测试 Redis (DB 15)
        blacklist = TokenBlacklist(redis_url="redis://localhost:6379/15")

        # 清理测试数据
        try:
            blacklist.redis.flushdb()
        except Exception:
            pytest.skip("Redis 不可用")

        yield blacklist

        # 清理
        try:
            blacklist.redis.flushdb()
        except Exception:
            pass

    def test_blacklist_available(self, blacklist):
        """测试黑名单可用性"""
        assert blacklist.is_available() is True

    def test_revoke_token(self, blacklist):
        """测试撤销 Token"""
        token = create_token("user123", "testuser")
        result = blacklist.revoke(token)
        assert result is True
        assert blacklist.is_revoked(token) is True

    def test_revoke_token_with_ttl(self, blacklist):
        """测试撤销 Token 并设置 TTL"""
        token = create_token("user123", "testuser")
        result = blacklist.revoke(token, ttl=60)
        assert result is True
        assert blacklist.is_revoked(token) is True

    def test_get_token_jti(self, blacklist):
        """测试提取 Token JTI"""
        token = create_token("user123", "testuser")
        jti = blacklist.get_token_jti(token)
        assert jti is not None
        assert isinstance(jti, str)

    def test_revoke_user_tokens(self, blacklist):
        """测试撤销用户所有 Token"""
        token1 = create_token("user123", "testuser")
        token2 = create_token("user123", "testuser")

        # 撤销用户 Token，排除 token1
        count = blacklist.revoke_user_tokens("user123", except_token=token1)

        assert count >= 0
        # token1 应该仍然有效
        assert blacklist.is_user_revoked("user123", token1) is False
        # token2 应该被撤销
        assert blacklist.is_user_revoked("user123", token2) is True
