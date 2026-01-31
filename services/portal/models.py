"""统一入口门户 - 数据模型"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    token: Optional[str] = None
    user: Optional["UserInfo"] = None
    message: str = ""


class RefreshTokenResponse(BaseModel):
    """Token刷新响应"""
    success: bool
    token: Optional[str] = None
    message: str = ""


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    role: str
    display_name: Optional[str] = None
    email: Optional[str] = None


class SubsystemStatus(BaseModel):
    """子系统状态"""
    name: str
    display_name: str
    url: str
    status: str  # "online" | "offline" | "unknown"
    version: Optional[str] = None


class PortalInfo(BaseModel):
    """门户信息"""
    name: str
    version: str
    subsystems: list[SubsystemStatus]
