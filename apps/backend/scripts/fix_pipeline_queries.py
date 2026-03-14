#!/usr/bin/env python3
"""Fix ETL pipeline queries to avoid format string issues."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.etl import ETLPipeline


# Fixed queries without % characters
FIXED_QUERIES = {
    # HR pipeline - use CONCAT instead of DATE_FORMAT
    "b921cca9-67e3-42a8-b0f1-6d543175edf1": """SELECT d.name as department_name,
CONCAT(YEAR(s.pay_date), '-', LPAD(MONTH(s.pay_date), 2, '0')) as pay_month,
COUNT(DISTINCT s.employee_id) as employee_count,
SUM(s.gross_salary) as total_gross,
AVG(s.gross_salary) as avg_gross,
SUM(s.net_salary) as total_net,
SUM(s.total_deductions) as total_deductions,
SUM(s.bonus) as total_bonus,
SUM(s.overtime_pay) as total_overtime
FROM salary_records s
JOIN employees e ON s.employee_id = e.id
JOIN departments d ON e.department_id = d.id
WHERE s.payment_status = 'paid'
GROUP BY d.name, pay_month
ORDER BY pay_month DESC, total_gross DESC""",

    # Medical pipeline - use CONCAT instead of DATE_FORMAT
    "45b471b4-8eb9-44d6-8c5f-d4d392955c0d": """SELECT
DATE(a.appointment_date) as visit_date,
d.name as department_name,
COUNT(*) as patient_count,
COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_count,
AVG(EXTRACT(EPOCH FROM (a.end_time - a.start_time))/60) as avg_duration_minutes
FROM appointments a
JOIN departments d ON a.department_id = d.id
WHERE a.appointment_date >= CURDATE() - INTERVAL 30 DAY
GROUP BY DATE(a.appointment_date), d.name
ORDER BY visit_date DESC, patient_count DESC""",
}


def update_pipeline_query_direct(pipeline_id: str, new_query: str) -> None:
    """Update pipeline query directly using psycopg2."""
    import json

    conn = psycopg2.connect(
        host="localhost",
        port=3102,
        database="smart_data",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    # Get current source_config
    cursor.execute("SELECT source_config FROM etl_pipelines WHERE id = %s", (pipeline_id,))
    row = cursor.fetchone()
    if not row:
        print(f"Pipeline not found: {pipeline_id}")
        conn.close()
        return

    source_config = row[0]
    source_config['query'] = new_query

    # Update entire source_config
    cursor.execute(
        "UPDATE etl_pipelines SET source_config = %s::jsonb WHERE id = %s",
        (json.dumps(source_config), pipeline_id)
    )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Updated: {pipeline_id}")


async def main():
    """Fix all pipeline queries."""
    print("Fixing pipeline queries...")

    for pipeline_id, query in FIXED_QUERIES.items():
        update_pipeline_query_direct(pipeline_id, query)

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
