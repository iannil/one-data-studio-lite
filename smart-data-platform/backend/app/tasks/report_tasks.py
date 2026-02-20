"""Celery tasks for report generation operations.

This module contains Celery tasks for scheduled report generation
and distribution.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.celery_worker import celery_app
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
                    "format": schedule.output_format,
                }

                # Update last run time
                schedule.last_run_at = datetime.now(timezone.utc)
                schedule.next_run_at = schedule.calculate_next_run()
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
        # TODO: Implement email sending logic
        # For now, return mock result
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Report).where(Report.id == uuid.UUID(report_id))
            )
            report = result.scalar_one_or_none()

            if not report:
                return {"status": "error", "message": f"Report not found: {report_id}"}

            return {
                "status": "success",
                "report_id": report_id,
                "report_name": report.name,
                "recipient": recipient_email,
                "format": report_format,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "message": "Email sending not yet implemented",
            }

    return asyncio.run(_send())
