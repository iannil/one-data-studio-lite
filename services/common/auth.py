"""JWT 认证工具"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# JWT 配置 - 从环境变量读取，提供开发环境默认值
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))
# Token可在过期前多少分钟内刷新
JWT_REFRESH_THRESHOLD_MINUTES = int(os.environ.get("JWT_REFRESH_THRESHOLD_MINUTES", "30"))
# 服务间通信密钥
SERVICE_SECRET = os.environ.get("SERVICE_SECRET", "internal-service-secret-dev-do-not-use-in-prod")

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT 令牌载荷"""
    sub: str           # 用户ID
    username: str
    role: str = "user"
    exp: datetime
    iat: Optional[datetime] = None  # 签发时间（可选）

    @property
    def user_id(self) -> str:
        """获取用户ID（sub的别名，提供向后兼容）"""
        return self.sub


def create_token(
    user_id: str,
    username: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT 令牌"""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": now.timestamp(),  # Unix 时间戳
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _check_token_blacklist(token: str) -> bool:
    """检查 Token 是否在黑名单中"""
    try:
        from services.common.token_blacklist import get_blacklist
        blacklist = get_blacklist()
        return blacklist.is_revoked(token)
    except Exception:
        return False


def _check_user_revoked(user_id: str, token: str) -> bool:
    """检查用户 Token 是否被批量撤销"""
    try:
        from services.common.token_blacklist import get_blacklist
        blacklist = get_blacklist()
        return blacklist.is_user_revoked(user_id, token)
    except Exception:
        return False


def verify_token(token: str) -> TokenPayload:
    """验证 JWT 令牌"""
    # 检查黑名单
    if _check_token_blacklist(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已撤销",
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # 检查用户是否被批量撤销
        user_id = payload.get("sub")
        if user_id and _check_user_revoked(user_id, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已撤销（权限变更）",
            )

        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效令牌",
        )


async def get_current_user(
    request: Request = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPayload:
    """FastAPI 依赖注入 - 获取当前用户

    支持两种认证方式:
    1. JWT Bearer Token (用户认证)
    2. X-Service-Secret 头 (服务间认证)
    """
    # 优先检查服务间认证密钥
    if request:
        service_secret = request.headers.get("X-Service-Secret")
        if service_secret == SERVICE_SECRET:
            # 服务间调用，返回内部服务用户
            return TokenPayload(
                sub="internal-service",
                username="service",
                role="service",
                exp=datetime.now(timezone.utc) + timedelta(hours=24),
            )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
        )
    return verify_token(credentials.credentials)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[TokenPayload]:
    """FastAPI 依赖注入 - 可选获取当前用户"""
    if credentials is None:
        return None
    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


def can_refresh_token(token: str) -> bool:
    """检查Token是否可以刷新（在过期前阈值时间内）"""
    try:
        # 不验证过期，只解码获取exp
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        threshold = timedelta(minutes=JWT_REFRESH_THRESHOLD_MINUTES)
        # Token已过期或在阈值时间内即将过期，都可以刷新
        return (exp - now) <= threshold
    except jwt.InvalidTokenError:
        return False


def refresh_token(token: str) -> Optional[str]:
    """刷新Token，返回新Token或None（如果无法刷新）"""
    try:
        # 允许已过期的Token刷新，但必须在合理时间内（比如过期后30分钟内）
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False}
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)

        # 如果Token过期超过30分钟，不允许刷新
        if (now - exp) > timedelta(minutes=30):
            return None

        # 生成新Token
        return create_token(
            user_id=payload["sub"],
            username=payload["username"],
            role=payload.get("role", "user"),
        )
    except jwt.InvalidTokenError:
        return None
