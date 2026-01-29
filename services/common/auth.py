"""JWT 认证工具"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# JWT 配置 - 从环境变量读取，提供开发环境默认值
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))

security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT 令牌载荷"""
    sub: str           # 用户ID
    username: str
    role: str = "user"
    exp: datetime


def create_token(
    user_id: str,
    username: str,
    role: str = "user",
    expires_delta: Optional[timedelta] = None,
) -> str:
    """创建 JWT 令牌"""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRE_HOURS))
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> TokenPayload:
    """验证 JWT 令牌"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> TokenPayload:
    """FastAPI 依赖注入 - 获取当前用户"""
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
