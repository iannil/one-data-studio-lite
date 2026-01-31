"""安全工具模块 - 密码生成、验证和加密

提供生产环境所需的安全工具函数：
- 强密码生成
- 密码强度验证
- Token 生成
- 敏感信息掩码
"""

import os
import random
import string
import secrets
import re
from typing import Optional


# ============================================================
// 密码生成
// ============================================================

def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
    exclude_ambiguous: bool = True,
) -> str:
    """生成强随机密码

    Args:
        length: 密码长度，默认 16
        use_uppercase: 是否包含大写字母
        use_lowercase: 是否包含小写字母
        use_digits: 是否包含数字
        use_special: 是否包含特殊字符
        exclude_ambiguous: 是否排除易混淆字符 (0OIl1)

    Returns:
        生成的密码字符串

    Raises:
        ValueError: 当所有字符类型都被禁用时
    """
    # 定义字符集
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*-_+="

    # 排除易混淆字符
    if exclude_ambiguous:
        uppercase = uppercase.replace("I", "").replace("O", "")
        lowercase = lowercase.replace("l", "")
        digits = digits.replace("0", "").replace("1", "")

    # 构建可用字符集
    charset = ""
    required_chars = []

    if use_uppercase:
        charset += uppercase
        required_chars.append(secrets.choice(uppercase))
    if use_lowercase:
        charset += lowercase
        required_chars.append(secrets.choice(lowercase))
    if use_digits:
        charset += digits
        required_chars.append(secrets.choice(digits))
    if use_special:
        charset += special
        required_chars.append(secrets.choice(special))

    if not charset:
        raise ValueError("至少需要启用一种字符类型")

    # 确保密码包含所有必需的字符类型
    password = list(required_chars)

    # 填充剩余长度
    remaining = length - len(password)
    for _ in range(remaining):
        password.append(secrets.choice(charset))

    # 打乱顺序
    random.shuffle(password)
    return "".join(password)


def generate_jwt_secret() -> str:
    """生成 JWT 密钥

    使用 cryptographically secure 随机数生成器。

    Returns:
        32 字节十六进制密钥
    """
    return secrets.token_hex(32)


def generate_webhook_secret() -> str:
    """生成 Webhook 签名密钥

    用于验证来自外部系统的 Webhook 请求。

    Returns:
        32 字节十六进制密钥
    """
    return secrets.token_hex(32)


def generate_api_key(prefix: str = "od", length: int = 32) -> str:
    """生成 API Key

    Args:
        prefix: 密钥前缀
        length: 随机部分长度（不含前缀）

    Returns:
        格式为 {prefix}_{random} 的 API Key
    """
    random_part = secrets.token_urlsafe(length)[:length]
    return f"{prefix}_{random_part}"


def generate_internal_token() -> str:
    """生成内部服务通信 Token

    Returns:
        内部服务认证 Token
    """
    return secrets.token_urlsafe(48)


# ============================================================
// 密码强度验证
// ============================================================

class PasswordStrength:
    """密码强度等级"""
    WEAK = 0
    MODERATE = 1
    STRONG = 2
    VERY_STRONG = 3

    @classmethod
    def labels(cls) -> dict[int, str]:
        return {
            cls.WEAK: "弱",
            cls.MODERATE: "中等",
            cls.STRONG: "强",
            cls.VERY_STRONG: "非常强",
        }


def check_password_strength(password: str) -> tuple[int, list[str]]:
    """检查密码强度

    Args:
        password: 待检查的密码

    Returns:
        (强度等级, 问题列表)

    强度评分标准：
    - 0 分：弱（长度 < 8 或 包含常见密码）
    - 1 分：中等（长度 >= 8 且包含 2 种字符类型）
    - 2 分：强（长度 >= 12 且包含 3 种字符类型）
    - 3 分：非常强（长度 >= 16 且包含 4 种字符类型）
    """
    issues = []
    score = 0

    # 检查长度
    if len(password) < 8:
        issues.append("密码长度少于8个字符")
        return PasswordStrength.WEAK, issues
    elif len(password) >= 16:
        score += 1
    elif len(password) >= 12:
        score += 0.5

    # 检查字符类型
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))

    char_types = sum([has_upper, has_lower, has_digit, has_special])

    if char_types < 2:
        issues.append("密码应包含至少两种字符类型（大写、小写、数字、特殊字符）")
        return PasswordStrength.WEAK, issues
    elif char_types >= 3:
        score += 1
    elif char_types >= 2:
        score += 0.5

    # 检查常见弱密码
    weak_passwords = [
        "password", "12345678", "abcdefgh", "qwerty12",
        "admin123", "letmein", "welcome1", "password1"
    ]
    if password.lower() in weak_passwords:
        issues.append("密码过于常见，容易被猜测")
        return PasswordStrength.WEAK, issues

    # 检查重复字符
    if len(set(password)) < len(password) / 2:
        issues.append("密码包含过多重复字符")

    # 检查键盘模式
    keyboard_patterns = [
        "qwerty", "asdfgh", "zxcvbn",
        "123456", "654321", "abcdef"
    ]
    lower_password = password.lower()
    for pattern in keyboard_patterns:
        if pattern in lower_password or pattern[::-1] in lower_password:
            issues.append("密码包含键盘序列模式")
            break

    # 确定最终等级
    if score >= 2.5:
        return PasswordStrength.VERY_STRONG, issues
    elif score >= 1.5:
        return PasswordStrength.STRONG, issues
    elif score >= 1:
        return PasswordStrength.MODERATE, issues
    else:
        return PasswordStrength.WEAK, issues


def is_strong_password(password: str, min_length: int = 12) -> bool:
    """快速检查密码是否为强密码

    Args:
        password: 待检查的密码
        min_length: 最小长度要求

    Returns:
        是否为强密码
    """
    if len(password) < min_length:
        return False

    # 必须包含至少 3 种字符类型
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))

    return sum([has_upper, has_lower, has_digit, has_special]) >= 3


# ============================================================
// 敏感信息掩码
// ============================================================

def mask_token(token: str, visible_chars: int = 4, mask_char: str = "*") -> str:
    """掩码 Token，只显示部分字符

    Args:
        token: 原始 Token
        visible_chars: 首尾各显示的字符数
        mask_char: 掩码字符

    Returns:
        掩码后的 Token，如 "abcd****************wxyz"
    """
    if len(token) <= visible_chars * 2:
        return mask_char * len(token)

    return (
        token[:visible_chars] +
        mask_char * (len(token) - visible_chars * 2) +
        token[-visible_chars:]
    )


def mask_email(email: str) -> str:
    """掩码邮箱地址

    Args:
        email: 原始邮箱

    Returns:
        掩码后的邮箱，如 "a***@example.com"
    """
    if "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"

    return f"{local[0]}***@{domain}"


def mask_string(s: str, visible_start: int = 2, visible_end: int = 2, mask_char: str = "*") -> str:
    """通用字符串掩码

    Args:
        s: 原始字符串
        visible_start: 开头可见字符数
        visible_end: 结尾可见字符数
        mask_char: 掩码字符

    Returns:
        掩码后的字符串
    """
    if len(s) <= visible_start + visible_end:
        return mask_char * len(s)

    return (
        s[:visible_start] +
        mask_char * (len(s) - visible_start - visible_end) +
        s[-visible_end:] if visible_end > 0 else ""
    )


# ============================================================
// 环境变量安全获取
// ============================================================

def get_env_secret(
    key: str,
    default: Optional[str] = None,
    required: bool = False,
    min_length: int = 8,
) -> Optional[str]:
    """安全地获取环境变量中的密钥/密码

    Args:
        key: 环境变量名
        default: 默认值
        required: 是否必需
        min_length: 最小长度要求

    Returns:
        环境变量值

    Raises:
        ValueError: 必需变量未设置或长度不足时
    """
    value = os.environ.get(key, default)

    if value is None:
        if required:
            raise ValueError(f"必需的环境变量 {key} 未设置")
        return None

    if len(value) < min_length:
        if required:
            raise ValueError(f"环境变量 {key} 的值长度不足 {min_length} 字符")
        import warnings
        warnings.warn(f"环境变量 {key} 的值长度不足 {min_length} 字符")

    return value


def validate_env_config() -> list[str]:
    """验证环境变量配置的安全性

    Returns:
        警告信息列表
    """
    warnings = []

    # 检查常见弱密钥
    weak_indicators = ["password", "secret", "123456", "admin", "change"]
    env_keys = [
        "JWT_SECRET",
        "DATABASE_URL",
        "SUPERSET_ADMIN_PASSWORD",
        "INTERNAL_TOKEN",
        "META_SYNC_DATAHUB_WEBHOOK_SECRET",
    ]

    for key in env_keys:
        value = os.environ.get(key, "")
        if value:
            if any(indicator in value.lower() for indicator in weak_indicators):
                warnings.append(f"{key} 可能包含弱密钥，请检查")
            elif len(value) < 16 and "SECRET" in key or "TOKEN" in key:
                warnings.append(f"{key} 长度较短，建议使用至少 32 字符的随机字符串")

    # 检查生产环境标识
    env = os.environ.get("ENVIRONMENT", "")
    if env.lower() in ("production", "prod"):
        if not os.environ.get("JWT_SECRET") or os.environ.get("JWT_SECRET") == "dev-only-change-in-production":
            warnings.append("生产环境检测到弱 JWT 密钥配置")

    return warnings
