from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import get_connector
from app.core.config import settings
from app.models import Alert, AlertRule, AlertStatus, DataSource

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing and checking alerts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_rule(self, rule: AlertRule) -> Alert | None:
        """Check an alert rule and create alert if triggered."""
        try:
            source_result = await self.db.execute(select(DataSource).limit(1))
            source = source_result.scalar_one_or_none()

            if not source:
                return None

            connector = get_connector(source.type, source.connection_config)
            result = await connector.execute_query(rule.metric_sql)

            if not result:
                return None

            current_value = float(result[0].get(rule.metric_name, 0))

            is_triggered = self._evaluate_condition(
                current_value,
                rule.condition,
                rule.threshold,
            )

            if is_triggered:
                recent_alert = await self._get_recent_alert(rule.id, rule.cooldown_minutes)
                if recent_alert:
                    return None

                alert = Alert(
                    rule_id=rule.id,
                    severity=rule.severity,
                    status=AlertStatus.ACTIVE,
                    message=self._build_alert_message(rule, current_value),
                    current_value=current_value,
                    threshold_value=rule.threshold,
                )
                self.db.add(alert)
                await self.db.commit()

                await self._send_notifications(rule, alert)

                return alert

            return None

        except Exception as e:
            raise RuntimeError(f"Failed to check alert rule: {e}") from e

    def _evaluate_condition(
        self,
        current: float,
        condition: str,
        threshold: float,
    ) -> bool:
        """Evaluate if the condition is met."""
        conditions = {
            "gt": current > threshold,
            "gte": current >= threshold,
            "lt": current < threshold,
            "lte": current <= threshold,
            "eq": current == threshold,
            "ne": current != threshold,
        }
        return conditions.get(condition, False)

    def _build_alert_message(self, rule: AlertRule, current_value: float) -> str:
        """Build alert message."""
        condition_symbols = {
            "gt": ">",
            "gte": ">=",
            "lt": "<",
            "lte": "<=",
            "eq": "==",
            "ne": "!=",
        }
        symbol = condition_symbols.get(rule.condition, rule.condition)

        return (
            f"Alert: {rule.name}\n"
            f"Metric '{rule.metric_name}' = {current_value} "
            f"(threshold: {symbol} {rule.threshold})"
        )

    async def _get_recent_alert(
        self,
        rule_id: uuid.UUID,
        cooldown_minutes: int,
    ) -> Alert | None:
        """Check if there's a recent alert within cooldown period."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)

        result = await self.db.execute(
            select(Alert)
            .where(Alert.rule_id == rule_id)
            .where(Alert.triggered_at > cutoff)
            .where(Alert.status == AlertStatus.ACTIVE)
        )
        return result.scalar_one_or_none()

    async def _send_notifications(self, rule: AlertRule, alert: Alert) -> None:
        """Send alert notifications."""
        for channel in rule.notification_channels:
            if channel == "email":
                await self._send_email_notification(rule, alert)
            elif channel == "webhook":
                await self._send_webhook_notification(rule, alert)
            elif channel == "dingtalk":
                await self._send_dingtalk_notification(rule, alert)
            elif channel == "wecom":
                await self._send_wecom_notification(rule, alert)
            elif channel == "feishu":
                await self._send_feishu_notification(rule, alert)

    async def _send_email_notification(self, rule: AlertRule, alert: Alert) -> None:
        """Send email notification via SMTP."""
        config = rule.notification_config or {}
        recipients = config.get("email_recipients", [])

        if not recipients:
            return

        # Get SMTP settings from config or use environment
        smtp_host = config.get("smtp_host", getattr(settings, "SMTP_HOST", "localhost"))
        smtp_port = config.get("smtp_port", getattr(settings, "SMTP_PORT", 587))
        smtp_user = config.get("smtp_user", getattr(settings, "SMTP_USER", ""))
        smtp_password = config.get("smtp_password", getattr(settings, "SMTP_PASSWORD", ""))
        smtp_from = config.get("smtp_from", getattr(settings, "SMTP_FROM", "alerts@smartdata.local"))
        use_tls = config.get("smtp_tls", getattr(settings, "SMTP_TLS", True))

        # Build email
        subject = f"[{alert.severity.value.upper()}] Alert: {rule.name}"
        body = self._build_email_body(rule, alert)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = ", ".join(recipients)

        # Plain text version
        text_content = MIMEText(body, "plain", "utf-8")
        msg.attach(text_content)

        # HTML version
        html_body = self._build_html_email_body(rule, alert)
        html_content = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_content)

        try:
            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)

            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)

            server.sendmail(smtp_from, recipients, msg.as_string())
            server.quit()

            logger.info(f"Email notification sent for alert {alert.id} to {recipients}")

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    def _build_email_body(self, rule: AlertRule, alert: Alert) -> str:
        """Build plain text email body."""
        return f"""
Alert Notification
==================

Rule: {rule.name}
Severity: {alert.severity.value.upper()}
Triggered At: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{alert.message}

Current Value: {alert.current_value}
Threshold: {alert.threshold_value}

Please review and take appropriate action.

--
Smart Data Platform Alert System
"""

    def _build_html_email_body(self, rule: AlertRule, alert: Alert) -> str:
        """Build HTML email body."""
        severity_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#17a2b8",
        }
        color = severity_colors.get(alert.severity.value, "#6c757d")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .alert-box {{ border-left: 4px solid {color}; padding: 15px; background: #f8f9fa; margin: 20px 0; }}
        .severity {{ color: {color}; font-weight: bold; text-transform: uppercase; }}
        .metric {{ background: #e9ecef; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .footer {{ color: #6c757d; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <h2>🔔 Alert Notification</h2>

    <div class="alert-box">
        <p><strong>Rule:</strong> {rule.name}</p>
        <p><strong>Severity:</strong> <span class="severity">{alert.severity.value}</span></p>
        <p><strong>Triggered:</strong> {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>

    <h3>Details</h3>
    <div class="metric">
        <p><strong>Current Value:</strong> {alert.current_value}</p>
        <p><strong>Threshold:</strong> {alert.threshold_value}</p>
    </div>

    <p><strong>Message:</strong><br>{alert.message}</p>

    <p>Please review and take appropriate action.</p>

    <div class="footer">
        <p>Smart Data Platform Alert System</p>
    </div>
</body>
</html>
"""

    async def _send_webhook_notification(self, rule: AlertRule, alert: Alert) -> None:
        """Send webhook notification."""
        import httpx

        config = rule.notification_config or {}
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            return

        payload = {
            "alert_id": str(alert.id),
            "rule_name": rule.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "current_value": alert.current_value,
            "threshold": alert.threshold_value,
            "triggered_at": alert.triggered_at.isoformat(),
        }

        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=10)

    async def _send_dingtalk_notification(self, rule: AlertRule, alert: Alert) -> None:
        """Send DingTalk (钉钉) robot notification.

        Config format:
        {
            "dingtalk_webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "dingtalk_secret": "SEC...",  # Optional: for signed requests
            "dingtalk_at_mobiles": ["138xxxx"],  # Optional: @ specific users
            "dingtalk_at_all": false  # Optional: @ all members
        }
        """
        import hashlib
        import hmac
        import base64
        import time
        import urllib.parse
        import httpx

        config = rule.notification_config or {}
        webhook_url = config.get("dingtalk_webhook")

        if not webhook_url:
            return

        secret = config.get("dingtalk_secret")
        if secret:
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode("utf-8"),
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
        }
        emoji = severity_emoji.get(alert.severity.value, "⚪")

        markdown_content = f"""### {emoji} 告警通知

**规则名称**: {rule.name}

**告警级别**: {alert.severity.value.upper()}

**触发时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}

**当前值**: {alert.current_value}

**阈值**: {alert.threshold_value}

**详情**: {alert.message}

---
*Smart Data Platform 告警系统*"""

        payload: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"[{alert.severity.value.upper()}] {rule.name}",
                "text": markdown_content,
            },
        }

        at_mobiles = config.get("dingtalk_at_mobiles", [])
        at_all = config.get("dingtalk_at_all", False)
        if at_mobiles or at_all:
            payload["at"] = {
                "atMobiles": at_mobiles,
                "isAtAll": at_all,
            }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"DingTalk notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send DingTalk notification: {e}")

    async def _send_wecom_notification(self, rule: AlertRule, alert: Alert) -> None:
        """Send WeCom (企业微信) robot notification.

        Config format:
        {
            "wecom_webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
            "wecom_mentioned_list": ["userid1"],  # Optional: @ specific users
            "wecom_mentioned_mobile_list": ["138xxxx"]  # Optional: @ by mobile
        }
        """
        import httpx

        config = rule.notification_config or {}
        webhook_url = config.get("wecom_webhook")

        if not webhook_url:
            return

        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
        }
        emoji = severity_emoji.get(alert.severity.value, "⚪")

        markdown_content = f"""{emoji} **告警通知**
> **规则**: {rule.name}
> **级别**: <font color="warning">{alert.severity.value.upper()}</font>
> **时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}
> **当前值**: {alert.current_value}
> **阈值**: {alert.threshold_value}
> **详情**: {alert.message}"""

        payload: dict[str, Any] = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_content,
            },
        }

        mentioned_list = config.get("wecom_mentioned_list", [])
        mentioned_mobile_list = config.get("wecom_mentioned_mobile_list", [])
        if mentioned_list or mentioned_mobile_list:
            payload["markdown"]["mentioned_list"] = mentioned_list
            payload["markdown"]["mentioned_mobile_list"] = mentioned_mobile_list

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"WeCom notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send WeCom notification: {e}")

    async def _send_feishu_notification(self, rule: AlertRule, alert: Alert) -> None:
        """Send Feishu (飞书) robot notification.

        Config format:
        {
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
            "feishu_secret": "xxx"  # Optional: for signed requests
        }
        """
        import hashlib
        import hmac
        import base64
        import time
        import httpx

        config = rule.notification_config or {}
        webhook_url = config.get("feishu_webhook")

        if not webhook_url:
            return

        timestamp = str(int(time.time()))
        secret = config.get("feishu_secret")
        sign = ""

        if secret:
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                string_to_sign.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")

        severity_color = {
            "critical": "red",
            "high": "orange",
            "medium": "yellow",
            "low": "blue",
        }
        color = severity_color.get(alert.severity.value, "grey")

        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🔔 告警: {rule.name}",
                },
                "template": color,
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**级别**: {alert.severity.value.upper()}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}",
                            },
                        },
                    ],
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**当前值**: {alert.current_value}",
                            },
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**阈值**: {alert.threshold_value}",
                            },
                        },
                    ],
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**详情**: {alert.message}",
                    },
                },
                {
                    "tag": "hr",
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "Smart Data Platform 告警系统",
                        },
                    ],
                },
            ],
        }

        payload: dict[str, Any] = {
            "msg_type": "interactive",
            "card": card,
        }

        if sign:
            payload["timestamp"] = timestamp
            payload["sign"] = sign

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Feishu notification sent for alert {alert.id}")
        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")

    async def acknowledge_alert(
        self,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Alert | None:
        """Acknowledge an alert."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = user_id

        await self.db.commit()
        return alert

    async def resolve_alert(
        self,
        alert_id: uuid.UUID,
        user_id: uuid.UUID,
        resolution_note: str | None = None,
    ) -> Alert | None:
        """Resolve an alert."""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = user_id
        alert.resolution_note = resolution_note

        await self.db.commit()
        return alert

    async def check_all_active_rules(self) -> list[Alert]:
        """Check all active alert rules."""
        result = await self.db.execute(
            select(AlertRule).where(AlertRule.is_enabled.is_(True))
        )
        rules = list(result.scalars())

        triggered_alerts = []
        for rule in rules:
            alert = await self.check_rule(rule)
            if alert:
                triggered_alerts.append(alert)

        return triggered_alerts

    async def detect_anomalies(
        self,
        source_id: str,
        table_name: str,
        column_name: str,
        method: str = "zscore",
        threshold: float = 3.0,
    ) -> dict[str, Any]:
        """Detect anomalies in numeric data using statistical methods.

        Args:
            source_id: UUID of the data source.
            table_name: Name of the table to analyze.
            column_name: Name of the numeric column to check.
            method: Detection method - 'zscore' or 'iqr'.
            threshold: Threshold for anomaly detection:
                - For zscore: number of standard deviations (default 3.0)
                - For iqr: multiplier for IQR (default 1.5)

        Returns:
            Dictionary with anomaly detection results.
        """
        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == uuid.UUID(source_id))
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)

        # Load data
        query = f"SELECT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL"
        df = await connector.read_data(query=query)

        if df.empty:
            return {
                "method": method,
                "column": column_name,
                "total_rows": 0,
                "anomaly_count": 0,
                "anomalies": [],
            }

        values = df[column_name].astype(float).values

        if method == "zscore":
            anomalies, stats = self._detect_zscore_anomalies(values, threshold)
        elif method == "iqr":
            anomalies, stats = self._detect_iqr_anomalies(values, threshold)
        else:
            raise ValueError(f"Unsupported anomaly detection method: {method}")

        return {
            "method": method,
            "column": column_name,
            "total_rows": len(values),
            "anomaly_count": len(anomalies),
            "anomaly_percentage": round(len(anomalies) / len(values) * 100, 2),
            "statistics": stats,
            "anomalies": anomalies[:100],  # Limit to first 100
        }

    def _detect_zscore_anomalies(
        self,
        values: np.ndarray,
        threshold: float = 3.0,
    ) -> tuple[list[dict], dict]:
        """Detect anomalies using Z-score method.

        Points with |z-score| > threshold are considered anomalies.
        """
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return [], {"mean": float(mean), "std": 0.0, "threshold": threshold}

        z_scores = (values - mean) / std
        anomaly_mask = np.abs(z_scores) > threshold
        anomaly_indices = np.where(anomaly_mask)[0]

        anomalies = [
            {
                "index": int(idx),
                "value": float(values[idx]),
                "z_score": float(z_scores[idx]),
            }
            for idx in anomaly_indices
        ]

        stats = {
            "mean": float(mean),
            "std": float(std),
            "threshold": threshold,
            "min": float(np.min(values)),
            "max": float(np.max(values)),
        }

        return anomalies, stats

    def _detect_iqr_anomalies(
        self,
        values: np.ndarray,
        threshold: float = 1.5,
    ) -> tuple[list[dict], dict]:
        """Detect anomalies using IQR (Interquartile Range) method.

        Points outside [Q1 - threshold*IQR, Q3 + threshold*IQR] are anomalies.
        """
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1

        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        anomaly_mask = (values < lower_bound) | (values > upper_bound)
        anomaly_indices = np.where(anomaly_mask)[0]

        anomalies = [
            {
                "index": int(idx),
                "value": float(values[idx]),
                "bound_violated": "lower" if values[idx] < lower_bound else "upper",
            }
            for idx in anomaly_indices
        ]

        stats = {
            "q1": float(q1),
            "q3": float(q3),
            "iqr": float(iqr),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
            "threshold_multiplier": threshold,
            "median": float(np.median(values)),
        }

        return anomalies, stats

    async def detect_anomalies_with_ai(
        self,
        source_id: str,
        table_name: str,
        columns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Detect anomalies using AI-enhanced analysis.

        Combines statistical methods with AI interpretation.

        Args:
            source_id: UUID of the data source.
            table_name: Name of the table to analyze.
            columns: Optional list of columns to analyze (auto-detects numeric if None).

        Returns:
            Dictionary with AI-enhanced anomaly analysis.
        """
        from app.services.ai_service import AIService

        source_result = await self.db.execute(
            select(DataSource).where(DataSource.id == uuid.UUID(source_id))
        )
        source = source_result.scalar_one_or_none()

        if not source:
            raise ValueError(f"Data source not found: {source_id}")

        connector = get_connector(source.type, source.connection_config)

        # Get sample data
        df = await connector.read_data(table_name=table_name, limit=1000)

        if df.empty:
            return {"error": "No data available", "anomalies": []}

        # Auto-detect numeric columns
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        results = {"columns_analyzed": columns, "findings": []}

        for col in columns:
            if col not in df.columns:
                continue

            values = df[col].dropna().values
            if len(values) < 10:
                continue

            # Run both methods
            zscore_anomalies, zscore_stats = self._detect_zscore_anomalies(values)
            iqr_anomalies, iqr_stats = self._detect_iqr_anomalies(values)

            results["findings"].append({
                "column": col,
                "total_values": len(values),
                "zscore_method": {
                    "anomaly_count": len(zscore_anomalies),
                    "statistics": zscore_stats,
                },
                "iqr_method": {
                    "anomaly_count": len(iqr_anomalies),
                    "statistics": iqr_stats,
                },
            })

        # Generate AI summary if available
        try:
            ai_service = AIService(self.db)
            results["ai_summary"] = await ai_service.summarize_anomalies(results)
        except Exception:
            results["ai_summary"] = None

        return results
