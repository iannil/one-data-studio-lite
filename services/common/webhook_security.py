"""Webhook 签名验证模块

提供 HMAC-SHA256 签名验证功能，用于验证来自外部系统（如 DataHub）的 Webhook 请求。
"""

import hashlib
import hmac
import logging

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def compute_signature(payload: bytes, secret: str) -> str:
    """计算 HMAC-SHA256 签名

    Args:
        payload: 请求体原始字节
        secret: 签名密钥

    Returns:
        签名字符串，格式为 sha256=<hex>
    """
    signature = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """验证 Webhook 签名

    Args:
        payload: 请求体原始字节
        signature: 请求头中的签名（格式: sha256=<hex>）
        secret: 签名密钥

    Returns:
        签名是否有效
    """
    if not signature or not secret:
        return False

    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


class WebhookSignatureVerifier:
    """Webhook 签名验证器

    用作 FastAPI 依赖注入，验证请求签名。

    Usage:
        verifier = WebhookSignatureVerifier(secret="your-secret")

        @app.post("/webhook")
        async def webhook(payload = Depends(verifier)):
            ...
    """

    def __init__(
        self,
        secret: str,
        header_name: str = "X-DataHub-Signature",
        allow_unsigned: bool = False,
    ):
        """初始化签名验证器

        Args:
            secret: 签名密钥，如果为空则跳过验证（仅限开发环境）
            header_name: 签名头名称
            allow_unsigned: 是否允许无签名请求（仅限开发环境）
        """
        self.secret = secret
        self.header_name = header_name.lower()
        self.allow_unsigned = allow_unsigned

    async def __call__(self, request: Request) -> bytes:
        """验证签名并返回请求体

        Args:
            request: FastAPI Request 对象

        Returns:
            请求体原始字节

        Raises:
            HTTPException: 签名验证失败时返回 401
        """
        body = await request.body()

        # 无密钥配置时
        if not self.secret:
            if self.allow_unsigned:
                logger.warning(
                    "Webhook 签名验证已禁用（未配置密钥），请在生产环境配置 Webhook Secret"
                )
                return body
            else:
                logger.error("Webhook Secret 未配置，拒绝请求")
                raise HTTPException(
                    status_code=500,
                    detail="服务端配置错误：Webhook Secret 未配置"
                )

        # 获取签名
        signature = request.headers.get(self.header_name)

        if not signature:
            if self.allow_unsigned:
                logger.warning("收到无签名的 Webhook 请求（开发模式允许）")
                return body
            else:
                logger.warning(f"Webhook 请求缺少签名头 {self.header_name}")
                raise HTTPException(
                    status_code=401,
                    detail=f"缺少签名头 {self.header_name}"
                )

        # 验证签名
        if not verify_signature(body, signature, self.secret):
            logger.warning(f"Webhook 签名验证失败: {signature[:20]}...")
            raise HTTPException(
                status_code=401,
                detail="签名验证失败"
            )

        logger.debug("Webhook 签名验证通过")
        return body


def create_webhook_verifier(
    secret: str,
    header_name: str = "X-DataHub-Signature",
    is_development: bool = False,
) -> WebhookSignatureVerifier:
    """创建 Webhook 签名验证器的工厂函数

    Args:
        secret: 签名密钥
        header_name: 签名头名称
        is_development: 是否为开发环境（开发环境允许无签名请求）

    Returns:
        WebhookSignatureVerifier 实例
    """
    return WebhookSignatureVerifier(
        secret=secret,
        header_name=header_name,
        allow_unsigned=is_development and not secret,
    )
