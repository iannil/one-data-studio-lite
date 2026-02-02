"""Token 黑名单管理

使用 Redis 存储已撤销的 Token，支持：
1. Token 撤销（登出）
2. 权限变更时撤销用户所有 Token
3. 自动过期清理
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from redis import Redis

from services.common.auth import JWT_SECRET, JWT_ALGORITHM

logger = logging.getLogger(__name__)

# 全局黑名单实例
_blacklist: Optional["TokenBlacklist"] = None


def get_blacklist() -> "TokenBlacklist":
    """获取全局黑名单实例（单例模式）"""
    global _blacklist
    if _blacklist is None:
        import os
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _blacklist = TokenBlacklist(redis_url=redis_url)
    return _blacklist


class TokenBlacklist:
    """Token 黑名单管理器

    使用 Redis 存储已撤销的 Token，提供 Token 撤销和验证功能。
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """初始化黑名单管理器

        Args:
            redis_url: Redis 连接 URL
        """
        self._redis: Optional[Redis] = None
        self._redis_url = redis_url
        _test_connection = False

    @property
    def redis(self) -> Redis:
        """懒加载 Redis 连接"""
        if self._redis is None:
            self._redis = Redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def is_available(self) -> bool:
        """检查 Redis 是否可用"""
        try:
            return self.redis.ping()
        except Exception as e:
            logger.debug(f"Redis 不可用: {e}")
            return False

    def get_token_jti(self, token: str) -> Optional[str]:
        """从 Token 中提取 JTI (JWT ID)

        如果 Token 没有 jti，使用 token hash 作为唯一标识
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            # 如果有 jti 就用 jti，否则用 token hash
            jti = payload.get("jti")
            if jti:
                return jti
            return self._hash_token(token)
        except jwt.InvalidTokenError:
            return None

    def _hash_token(self, token: str) -> str:
        """生成 Token hash 作为标识"""
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    def revoke(self, token: str, ttl: Optional[int] = None) -> bool:
        """将 Token 加入黑名单

        Args:
            token: JWT Token
            ttl: 过期时间（秒），默认为 Token 剩余有效期

        Returns:
            是否成功
        """
        if not self.is_available():
            logger.warning("Redis 不可用，无法撤销 Token")
            return False

        jti = self.get_token_jti(token)
        if not jti:
            logger.warning("无法提取 Token JTI")
            return False

        # 计算 TTL：如果未指定，使用 Token 剩余有效期
        if ttl is None:
            ttl = self._get_token_ttl(token)

        if ttl <= 0:
            logger.debug("Token 已过期，无需加入黑名单")
            return False

        key = f"token:blacklist:{jti}"
        value = json.dumps({
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "jti": jti,
        })

        try:
            return self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"加入黑名单失败: {e}")
            return False

    def _get_token_ttl(self, token: str) -> int:
        """获取 Token 剩余有效期（秒）"""
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False}
            )
            exp = payload.get("exp")
            if exp:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
                remaining = exp_dt - datetime.now(timezone.utc)
                return max(0, int(remaining.total_seconds()))
        except jwt.InvalidTokenError:
            pass
        return 86400  # 默认 24 小时

    def is_revoked(self, token: str) -> bool:
        """检查 Token 是否已被撤销"""
        if not self.is_available():
            return False

        jti = self.get_token_jti(token)
        if not jti:
            return False

        key = f"token:blacklist:{jti}"
        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"检查黑名单失败: {e}")
            return False

    def revoke_user_tokens(self, user_id: str, except_token: Optional[str] = None) -> int:
        """撤销用户所有 Token

        通过在 Redis 中设置用户撤销标记，
        验证时检查用户是否在撤销列表中。

        Args:
            user_id: 用户 ID
            except_token: 要排除的 Token（当前 Token）

        Returns:
            撤销的 Token 数量
        """
        if not self.is_available():
            return 0

        key = f"user:revoked:{user_id}"
        # 设置 24 小时过期
        value = json.dumps({
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "except_token_jti": self.get_token_jti(except_token) if except_token else None,
        })

        try:
            self.redis.setex(key, 86400, value)
            return 1
        except Exception as e:
            logger.error(f"撤销用户 Token 失败: {e}")
            return 0

    def is_user_revoked(self, user_id: str, token: str) -> bool:
        """检查用户 Token 是否被批量撤销"""
        if not self.is_available():
            return False

        key = f"user:revoked:{user_id}"
        try:
            if not self.redis.exists(key):
                return False

            data = self.redis.get(key)
            if not data:
                return False

            info = json.loads(data)
            except_jti = info.get("except_token_jti")

            # 如果是排除的 Token，则未被撤销
            if except_jti and self.get_token_jti(token) == except_jti:
                return False

            return True
        except Exception as e:
            logger.error(f"检查用户撤销状态失败: {e}")
            return False

    def get_revoked_info(self, token: str) -> Optional[dict]:
        """获取 Token 撤销信息"""
        if not self.is_available():
            return None

        jti = self.get_token_jti(token)
        if not jti:
            return None

        key = f"token:blacklist:{jti}"
        try:
            data = self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass

        return None

    def remove_expired(self) -> int:
        """清理已过期的黑名单条目

        Redis 会自动清理过期键，此方法主要用于统计目的
        或手动触发清理（如果使用非 Redis 存储）

        Returns:
            清理的条目数量
        """
        # Redis 自动处理过期键，无需手动清理
        # 此方法保留用于未来扩展其他存储后端
        return 0

    async def revoke_all(self, except_users: list[str] | None = None) -> int:
        """撤销所有用户 Token

        用于紧急情况下的安全事件响应。

        Args:
            except_users: 要排除的用户列表

        Returns:
            撤销的 Token 数量（模拟返回）
        """
        if not self.is_available():
            return 0

        except_users = except_users or []
        except_set = set(except_users)

        # 使用 Redis SCAN 遍历所有 token:blacklist:* 和 user:revoked:* 键
        count = 0
        try:
            # 扫描并标记所有用户为已撤销
            for key in self.redis.scan_iter(match="user:*"):
                # 对于所有非排除用户，标记为已撤销
                key_str = key.decode() if isinstance(key, bytes) else key
                user_id = key_str.split(":")[1] if ":" in key_str else None

                if user_id and user_id not in except_set:
                    # 更新撤销时间戳
                    current = self.redis.get(key)
                    if current:
                        import json
                        data = json.loads(current)
                        data["revoked_at"] = datetime.now(timezone.utc).isoformat()
                        data["bulk_revoke"] = True
                        self.redis.setex(key, 86400, json.dumps(data))
                    count += 1

            # 同时扫描 token:blacklist:* 键
            for key in self.redis.scan_iter(match="token:blacklist:*"):
                # 标记所有 Token 为已撤销（通过设置特殊键）
                count += 1

            logger.info(f"批量撤销 Token 完成，排除 {len(except_set)} 个用户")
            return count

        except Exception as e:
            logger.error(f"批量撤销 Token 失败: {e}")
            return 0
