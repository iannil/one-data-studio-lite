"""统一入口门户 - 数据模型"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

# When email-validator is not installed, EmailStr cannot be used
# because pydantic requires the library for validation
# We use plain str instead and validate manually if needed
try:
    from pydantic import EmailStr as _EmailStr
    EMAIL_STR_AVAILABLE = True
except ImportError:
    _EmailStr = str  # type: ignore
    EMAIL_STR_AVAILABLE = False

# Use str directly to avoid pydantic validation issues
EmailStr = str  # type: ignore


# ============================================================
# 认证相关模型
# ============================================================

class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应"""
    success: bool
    token: str | None = None
    user: Optional["UserInfo"] = None
    message: str = ""


class RefreshTokenResponse(BaseModel):
    """Token刷新响应"""
    success: bool
    token: str | None = None
    message: str = ""


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证新密码强度"""
        from services.common.security import PasswordStrength, check_password_strength

        # 跳过默认开发密码的检查（仅在修改时）
        if v in ["admin123", "password", "12345678"]:
            raise ValueError("密码过于常见，请使用更强的密码")

        # 检查密码强度（至少中等）
        strength, issues = check_password_strength(v)

        if strength < PasswordStrength.MODERATE:
            if issues:
                raise ValueError(f"密码强度不足：{'; '.join(issues)}")
            else:
                raise ValueError("密码强度不足，请使用包含大小写字母、数字和特殊字符的组合")

        return v


class RegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = "user"
    display_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        from services.common.security import PasswordStrength, check_password_strength

        strength, issues = check_password_strength(v)

        if strength < PasswordStrength.MODERATE:
            if issues:
                raise ValueError(f"密码强度不足：{'; '.join(issues)}")
            else:
                raise ValueError("密码强度不足，请使用包含大小写字母、数字和特殊字符的组合")

        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed_roles = {"super_admin", "admin", "data_scientist", "analyst", "viewer", "service_account"}
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v


class UserInfo(BaseModel):
    """用户信息"""
    user_id: str
    username: str
    role: str
    display_name: str | None = None
    email: str | None = None
    permissions: list[str] = []


# ============================================================
# 用户管理模型
# ============================================================

class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str
    display_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        from services.common.security import PasswordStrength, check_password_strength

        strength, issues = check_password_strength(v)

        if strength < PasswordStrength.MODERATE:
            if issues:
                raise ValueError(f"密码强度不足：{'; '.join(issues)}")
            else:
                raise ValueError("密码强度不足，请使用包含大小写字母、数字和特殊字符的组合")

        return v


class UserUpdate(BaseModel):
    """更新用户请求"""
    display_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    role: str | None = None


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    role: str  # API 使用 role 而非 role_code
    display_name: str
    email: str | None = None
    phone: str | None = None
    is_active: bool
    is_locked: bool
    last_login_at: str | None = None  # ISO format string
    created_at: str  # ISO format string
    created_by: str | None = None


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    items: list[dict]  # UserResponse as dict


class DisableUserRequest(BaseModel):
    """禁用用户请求"""
    reason: str
    disabled_by: str


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        from services.common.security import PasswordStrength, check_password_strength

        strength, issues = check_password_strength(v)

        if strength < PasswordStrength.MODERATE:
            if issues:
                raise ValueError(f"密码强度不足：{'; '.join(issues)}")
            else:
                raise ValueError("密码强度不足，请使用包含大小写字母、数字和特殊字符的组合")

        return v


# ============================================================
# 密码重置模型
# ============================================================

class PasswordResetCodeRequest(BaseModel):
    """发送密码重置验证码请求"""
    email: str
    username: str = Field(default="")  # 可选，用于辅助验证


class PasswordResetVerifyRequest(BaseModel):
    """验证密码重置验证码请求"""
    email: str
    code: str = Field(..., min_length=6, max_length=8)


class PasswordResetConfirmRequest(BaseModel):
    """确认密码重置请求"""
    email: str
    code: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度"""
        from services.common.security import PasswordStrength, check_password_strength

        strength, issues = check_password_strength(v)

        if strength < PasswordStrength.MODERATE:
            if issues:
                raise ValueError(f"密码强度不足：{'; '.join(issues)}")
            else:
                raise ValueError("密码强度不足，请使用包含大小写字母、数字和特殊字符的组合")

        return v


# ============================================================
# 角色管理模型
# ============================================================

class RoleCreate(BaseModel):
    """创建角色请求"""
    role_code: str = Field(..., min_length=2, max_length=50)
    role_name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    """更新角色请求"""
    role_name: str | None = None
    description: str | None = None
    add_permissions: list[str] = []
    remove_permissions: list[str] = []


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    role_code: str
    role_name: str
    description: str
    is_system: bool
    permissions: list[str]
    created_at: datetime
    created_by: str | None = None


class RoleListResponse(BaseModel):
    """角色列表响应"""
    total: int
    items: list[RoleResponse]


# ============================================================
# 服务账户模型
# ============================================================

class ServiceAccountCreate(BaseModel):
    """创建服务账户请求"""
    name: str = Field(..., min_length=3, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    role: str = "service_account"


class ServiceAccountResponse(BaseModel):
    """服务账户响应"""
    id: int
    name: str
    display_name: str
    description: str
    role: str
    is_active: bool
    last_used_at: datetime | None = None
    created_at: datetime
    created_by: str | None = None
    expires_at: datetime | None = None
    # 注意: secret 只在创建时返回一次


class ServiceAccountCreateResponse(BaseModel):
    """服务账户创建响应（包含密钥）"""
    id: int
    name: str
    display_name: str
    secret: str  # 只在创建时返回
    role: str


class ServiceAccountListResponse(BaseModel):
    """服务账户列表响应"""
    total: int
    items: list[ServiceAccountResponse]


# ============================================================
# 系统配置模型
# ============================================================

class SystemConfigResponse(BaseModel):
    """系统配置响应"""
    key: str
    value: Any
    description: str
    category: str
    updated_at: datetime
    updated_by: str | None = None


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求"""
    key: str
    value: Any


class SystemConfigSet(BaseModel):
    """设置系统配置请求"""
    key: str
    value: Any
    description: str = ""
    category: str = "general"


class SystemInitRequest(BaseModel):
    """系统初始化请求"""
    default_role: str = "viewer"
    session_timeout: int = Field(default=86400, ge=300)
    max_login_attempts: int = Field(default=5, ge=1, le=20)


class SystemMetricsResponse(BaseModel):
    """系统指标响应"""
    status: str
    portal: dict
    internal_services: list[dict]
    subsystems: list[dict]


class EmergencyStopRequest(BaseModel):
    """紧急停止请求"""
    reason: str
    confirmed: bool = False


class RevokeAllTokensRequest(BaseModel):
    """撤销所有Token请求"""
    reason: str
    exclude_users: list[str] = []


# ============================================================
# 子系统状态模型
# ============================================================

class SubsystemStatus(BaseModel):
    """子系统状态"""
    name: str
    display_name: str
    url: str
    status: str  # "online" | "offline" | "unknown"
    version: str | None = None


class PortalInfo(BaseModel):
    """门户信息"""
    name: str
    version: str
    subsystems: list[SubsystemStatus]


# ============================================================
# 服务账户调用历史模型
# ============================================================

class ServiceAccountCallHistory(BaseModel):
    """服务账户调用历史记录"""
    id: str
    subsystem: str
    action: str
    resource: str | None = None
    status_code: int | None = None
    duration_ms: float | None = None
    ip_address: str | None = None
    created_at: str  # ISO format string


class ServiceAccountCallHistoryQuery(BaseModel):
    """服务账户调用历史查询参数"""
    start_date: str | None = None  # ISO format date string
    end_date: str | None = None
    subsystem: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)


class ServiceAccountCallHistoryResponse(BaseModel):
    """服务账户调用历史响应"""
    service_account: str
    total: int
    page: int
    page_size: int
    items: list[ServiceAccountCallHistory]
    stats: dict  # {total_calls, success_rate, avg_duration_ms}


# ============================================================
# API 响应包装器
# ============================================================

class ApiResponse(BaseModel):
    """通用API响应"""
    code: int = 20000
    message: str = "success"
    data: Any | None = None
    timestamp: int = 0


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    detail: str | None = None
    timestamp: int = 0
