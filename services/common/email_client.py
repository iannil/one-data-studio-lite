"""邮件发送客户端

支持 SMTP 邮件发送，用于密码重置验证码、通知等。
"""

import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

logger = logging.getLogger(__name__)


class EmailClient:
    """邮件发送客户端"""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        use_tls: bool | None = None,
        timeout: int | None = None,
    ):
        """初始化邮件客户端

        Args:
            host: SMTP 服务器地址
            port: SMTP 端口
            username: SMTP 用户名
            password: SMTP 密码
            from_email: 发件人邮箱
            from_name: 发件人名称
            use_tls: 是否使用 TLS
            timeout: 连接超时时间（秒）
        """
        self.host = host or os.environ.get("SMTP_HOST", "localhost")
        self.port = port or int(os.environ.get("SMTP_PORT", "587"))
        self.username = username or os.environ.get("SMTP_USERNAME", "")
        self.password = password or os.environ.get("SMTP_PASSWORD", "")
        self.from_email = from_email or os.environ.get("SMTP_FROM_EMAIL", "noreply@one-data-studio.local")
        self.from_name = from_name or os.environ.get("SMTP_FROM_NAME", "ONE-DATA-STUDIO-LITE")
        self.use_tls = use_tls if use_tls is not None else os.environ.get("SMTP_USE_TLS", "true").lower() == "true"
        self.timeout = timeout or int(os.environ.get("SMTP_TIMEOUT", "30"))
        self._enabled = os.environ.get("SMTP_ENABLED", "false").lower() == "true"

    def is_enabled(self) -> bool:
        """检查邮件服务是否启用"""
        return self._enabled

    def is_configured(self) -> bool:
        """检查邮件服务是否已配置"""
        return bool(self.host and self.from_email)

    async def send_email(
        self,
        to_email: str | list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
    ) -> bool:
        """发送邮件

        Args:
            to_email: 收件人邮箱（单个或列表）
            subject: 邮件主题
            html_content: HTML 邮件内容
            text_content: 纯文本邮件内容（可选）

        Returns:
            是否发送成功
        """
        if not self._enabled:
            logger.warning("邮件服务未启用，跳过发送")
            return False

        if not self.is_configured():
            logger.warning("邮件服务未配置，无法发送邮件")
            return False

        # 构建邮件
        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
        message["Subject"] = subject

        # 添加纯文本部分
        if text_content:
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)

        # 添加 HTML 部分
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        try:
            # 发送邮件
            async with aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
                use_tls=self.use_tls,
            ) as smtp:
                if self.username and self.password:
                    await smtp.login(self.username, self.password)

                await smtp.send_message(message)

            logger.info(f"邮件发送成功: {to_email}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    async def send_password_reset_code(
        self,
        to_email: str,
        code: str,
        username: str | None = None,
        expires_minutes: int = 15,
    ) -> bool:
        """发送密码重置验证码邮件

        Args:
            to_email: 收件人邮箱
            code: 验证码
            username: 用户名（可选）
            expires_minutes: 验证码有效期（分钟）

        Returns:
            是否发送成功
        """
        subject = "密码重置验证码"

        # HTML 内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .code {{ font-size: 32px; font-weight: bold; color: #4CAF50; text-align: center; padding: 20px; background-color: #fff; margin: 20px 0; letter-spacing: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #777; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>密码重置验证码</h2>
                </div>
                <div class="content">
                    <p>您好{f' {username}' if username else ''}，</p>
                    <p>您 requested 重置密码。请使用以下验证码完成密码重置：</p>
                    <div class="code">{code}</div>
                    <p><strong>有效期：</strong>{expires_minutes} 分钟</p>
                    <p>如果您没有请求重置密码，请忽略此邮件。</p>
                </div>
                <div class="footer">
                    <p>此邮件由系统自动发送，请勿回复。</p>
                    <p>© 2026 ONE-DATA-STUDIO-LITE</p>
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本内容
        text_content = f"""
您好{f' {username}' if username else ''}，

您请求重置密码。请使用以下验证码完成密码重置：

验证码: {code}
有效期: {expires_minutes} 分钟

如果您没有请求重置密码，请忽略此邮件。

---
此邮件由系统自动发送，请勿回复。
© 2026 ONE-DATA-STUDIO-LITE
        """.strip()

        return await self.send_email(to_email, subject, html_content, text_content)


# 全局单例
_email_client: EmailClient | None = None


def get_email_client() -> EmailClient:
    """获取邮件客户端单例"""
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client


async def send_password_reset_email(
    email: str,
    code: str,
    username: str | None = None,
) -> bool:
    """发送密码重置邮件（便捷函数）

    Args:
        email: 收件人邮箱
        code: 验证码
        username: 用户名（可选）

    Returns:
        是否发送成功
    """
    client = get_email_client()
    return await client.send_password_reset_code(email, code, username)
