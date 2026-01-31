"""密码生成工具

用于生成安全的随机密码，用于服务凭据管理。
"""

import secrets
import string
from typing import Optional


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
    special_chars: Optional[str] = None,
) -> str:
    """生成安全的随机密码

    Args:
        length: 密码长度，默认 16
        use_uppercase: 是否包含大写字母
        use_lowercase: 是否包含小写字母
        use_digits: 是否包含数字
        use_special: 是否包含特殊字符
        special_chars: 自定义特殊字符集

    Returns:
        生成的密码字符串

    Raises:
        ValueError: 如果所有字符类型都被禁用
    """
    charset = ""

    if use_uppercase:
        charset += string.ascii_uppercase
    if use_lowercase:
        charset += string.ascii_lowercase
    if use_digits:
        charset += string.digits
    if use_special:
        if special_chars:
            charset += special_chars
        else:
            # 默认使用安全特殊字符（排除容易混淆的字符）
            charset += "!@#$%&*"

    if not charset:
        raise ValueError("至少需要选择一种字符类型")

    # 使用 secrets 生成密码（加密安全）
    return "".join(secrets.choice(charset) for _ in range(length))


def generate_api_token(length: int = 32) -> str:
    """生成 API Token

    生成 Base64 编码的随机字符串，适合用作 API Token。

    Args:
        length: Token 长度，默认 32

    Returns:
        API Token 字符串
    """
    return secrets.token_urlsafe(length)[:length]


def generate_jwt_secret() -> str:
    """生成 JWT 密钥

    生成适合用作 JWT 签名密钥的随机字符串。

    Returns:
        JWT 密钥字符串
    """
    # 使用 64 字节（512 位）的随机数据，Base64 编码后约 86 字符
    return secrets.token_urlsafe(64)


def generate_hex_token(length: int = 32) -> str:
    """生成十六进制 Token

    生成十六进制编码的随机字符串。

    Args:
        length: Token 字节长度（结果会是长度的 2 倍）

    Returns:
        十六进制 Token 字符串
    """
    return secrets.token_hex(length)


def generate_webhook_secret() -> str:
    """生成 Webhook 签名密钥

    生成适合用于 HMAC 签名的密钥。

    Returns:
        Base64 编码的密钥字符串
    """
    return secrets.token_urlsafe(48)


# 预定义的密码策略
PASSWORD_POLICIES = {
    "strong": {
        "length": 20,
        "use_uppercase": True,
        "use_lowercase": True,
        "use_digits": True,
        "use_special": True,
    },
    "medium": {
        "length": 16,
        "use_uppercase": True,
        "use_lowercase": True,
        "use_digits": True,
        "use_special": False,
    },
    "simple": {
        "length": 12,
        "use_uppercase": True,
        "use_lowercase": True,
        "use_digits": True,
        "use_special": False,
    },
}


def generate_password_policy(policy: str = "strong") -> str:
    """根据策略生成密码

    Args:
        policy: 策略名称 (strong/medium/simple)

    Returns:
        生成的密码字符串

    Raises:
        ValueError: 如果策略名称无效
    """
    if policy not in PASSWORD_POLICIES:
        raise ValueError(f"无效的密码策略: {policy}，可选: {list(PASSWORD_POLICIES.keys())}")

    return generate_password(**PASSWORD_POLICIES[policy])
