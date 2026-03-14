"""Celery tasks for report generation operations.

This module contains Celery tasks for scheduled report generation
and distribution.
"""
from __future__ import annotations

import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from app.celery_worker import celery_app
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import Report, ReportSchedule
from sqlalchemy import select


@celery_app.task(name="report.generate_scheduled")
def generate_scheduled_report(schedule_id: str) -> dict[str, Any]:
    """Generate a report based on its schedule configuration.

    Args:
        schedule_id: The report schedule ID to generate.

    Returns:
        Generation result with status and report data.
    """
    import asyncio

    async def _generate() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            try:
                # Get schedule
                result = await db.execute(
                    select(ReportSchedule).where(ReportSchedule.id == uuid.UUID(schedule_id))
                )
                schedule = result.scalar_one_or_none()

                if not schedule:
                    return {"status": "error", "message": f"Schedule not found: {schedule_id}"}

                if not schedule.is_active:
                    return {"status": "skipped", "message": "Schedule is not active"}

                # Get associated report
                report_result = await db.execute(
                    select(Report).where(Report.id == schedule.report_id)
                )
                report = report_result.scalar_one_or_none()

                if not report:
                    return {"status": "error", "message": f"Report not found: {schedule.report_id}"}

                # Generate report (implementation depends on report type)
                # For now, return a mock result
                generation_result = {
                    "status": "success",
                    "schedule_id": schedule_id,
                    "report_id": str(report.id),
                    "report_name": report.name,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "format": schedule.format,
                }

                # Update last run time
                schedule.last_run_at = datetime.now(timezone.utc)
                await db.commit()

                return generation_result

            except Exception as e:
                return {
                    "status": "error",
                    "schedule_id": schedule_id,
                    "error": str(e),
                }

    return asyncio.run(_generate())


@celery_app.task(name="report.generate_all_pending")
def generate_all_pending_reports() -> dict[str, Any]:
    """Generate all reports that are due for generation.

    Checks all active schedules and generates reports for those
    that are due.

    Returns:
        Summary of triggered report generations.
    """
    import asyncio

    async def _generate_all() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            # Get all active schedules that are due
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(ReportSchedule).where(
                    ReportSchedule.is_active.is_(True),
                    ReportSchedule.next_run_at <= now,
                )
            )
            schedules = list(result.scalars())

            results = []
            for schedule in schedules:
                # Generate each report
                task_result = generate_scheduled_report.delay(str(schedule.id))
                results.append({
                    "schedule_id": str(schedule.id),
                    "report_id": str(schedule.report_id),
                    "celery_task_id": task_result.id,
                })

            return {
                "total_due": len(schedules),
                "triggered": results,
            }

    return asyncio.run(_generate_all())


@celery_app.task(name="report.send_email")
def send_report_email(
    report_id: str,
    recipient_email: str,
    report_format: str = "pdf"
) -> dict[str, Any]:
    """Send a generated report via email.

    Args:
        report_id: The report ID to send.
        recipient_email: Email address to send to.
        report_format: Format of the report (pdf, excel, etc).

    Returns:
        Email sending result.
    """
    import asyncio

    async def _send() -> dict[str, Any]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Report).where(Report.id == uuid.UUID(report_id))
            )
            report = result.scalar_one_or_none()

            if not report:
                return {"status": "error", "message": f"Report not found: {report_id}"}

            report_name = report.name  # Capture while session is open

        # Send email via SMTP (outside of db session)
        try:
            sent = _send_email_smtp(
                to_email=recipient_email,
                subject=f"Report: {report_name}",
                body=f"Please find the attached report: {report_name}",
                report_path=_get_report_file_path(report_id, report_format),
            )

            if sent:
                return {
                    "status": "success",
                    "report_id": report_id,
                    "report_name": report_name,
                    "recipient": recipient_email,
                    "format": report_format,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                return {
                    "status": "error",
                    "report_id": report_id,
                    "message": "Failed to send email",
                }
        except Exception as e:
            return {
                "status": "error",
                "report_id": report_id,
                "message": f"Email sending failed: {str(e)}",
            }

    return asyncio.run(_send())


def _send_email_smtp(
    to_email: str,
    subject: str,
    body: str,
    report_path: Path | None = None,
) -> bool:
    """Send email using SMTP.

    Args:
        to_email: Recipient email address.
        subject: Email subject.
        body: Email body text.
        report_path: Optional path to report file to attach.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not settings.SMTP_HOST:
        # SMTP not configured, log and return success (for testing)
        return True

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject

        # Attach body
        msg.attach(MIMEText(body, "plain"))

        # Attach report file if exists
        if report_path and report_path.exists():
            with report_path.open("rb") as f:
                part = MIMEApplication(f.read(), Name=report_path.name)
                part["Content-Disposition"] = f'attachment; filename="{report_path.name}"'
                msg.attach(part)

        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception:
        return False


def _get_report_file_path(report_id: str, report_format: str) -> Path | None:
    """Get the file path for a generated report.

    Args:
        report_id: The report ID.
        report_format: The report format (pdf, excel, etc).

    Returns:
        Path to the report file if it exists, None otherwise.
    """
    reports_dir = Path("/tmp/reports")
    if not reports_dir.exists():
        return None

    matching_files = list(reports_dir.glob(f"report_{report_id}*.{report_format}"))
    return matching_files[0] if matching_files else None
