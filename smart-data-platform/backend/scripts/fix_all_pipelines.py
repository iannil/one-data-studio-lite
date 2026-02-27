#!/usr/bin/env python3
"""Fix all ETL pipeline queries to match actual database schema."""

import json
import psycopg2
from typing import Dict


# Pipeline fixes based on actual schema inspection
PIPELINE_FIXES: Dict[str, str] = {
    # IoT Device Status - fix column names
    "7cbc0f36-cb4b-42ce-8c2f-2d1868b9489a": """
        SELECT dt.name as device_type,
               d.status,
               COALESCE(d.location_name, 'Unknown') as location,
               COUNT(*) as device_count
        FROM devices d
        JOIN device_types dt ON d.device_type_id = dt.id
        GROUP BY dt.name, d.status, d.location_name
    """,

    # IoT Alerts - fix column names (status not is_resolved)
    "7df913ae-f3c2-4a34-983a-102fd8270c8c": """
        SELECT DATE_TRUNC('day', a.triggered_at)::date as alert_date,
               a.severity,
               a.alert_type,
               COUNT(*) as alert_count,
               COUNT(CASE WHEN a.status = 'resolved' THEN 1 END) as resolved_count
        FROM alerts a
        WHERE a.triggered_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE_TRUNC('day', a.triggered_at)::date, a.severity, a.alert_type
        ORDER BY alert_date DESC
    """,

    # HR Attendance - fix based on actual columns (name not first_name/last_name)
    "4707ac42-fcb4-443d-904e-50819e087b0a": """
        SELECT e.employee_id,
               e.name as employee_name,
               d.name as department,
               COUNT(*) as total_days,
               SUM(CASE WHEN a.status = 'normal' THEN 1 ELSE 0 END) as normal_days,
               SUM(CASE WHEN a.is_absent = 1 THEN 1 ELSE 0 END) as absent_days,
               SUM(CASE WHEN a.is_late = 1 THEN 1 ELSE 0 END) as late_days
        FROM attendance a
        JOIN employees e ON a.employee_id = e.employee_id
        JOIN departments d ON e.department_id = d.id
        WHERE a.attendance_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY e.employee_id, e.name, d.name
        ORDER BY total_days DESC
    """,

    # Medical Outpatient - fix column names
    "45b471b4-8eb9-44d6-8c5f-d4d392955c0d": """
        SELECT a.appointment_date as visit_date,
               d.name as department_name,
               COUNT(*) as patient_count,
               COUNT(CASE WHEN a.status = 'completed' THEN 1 END) as completed_count,
               AVG(a.consultation_duration_minutes) as avg_duration_minutes
        FROM appointments a
        JOIN departments d ON a.department_id = d.id
        WHERE a.appointment_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY a.appointment_date, d.name
        ORDER BY visit_date DESC, patient_count DESC
    """,

    # Medical Prescriptions - fix column names
    "067d3a66-f611-4232-ac3e-61b60cf7641c": """
        SELECT p.prescription_date,
               d.name as department_name,
               COUNT(*) as prescription_count,
               SUM(pi.quantity) as total_items,
               AVG(pi.quantity) as avg_items_per_prescription
        FROM prescriptions p
        JOIN prescription_items pi ON p.id = pi.prescription_id
        JOIN doctors doc ON p.doctor_id = doc.id
        JOIN departments d ON doc.department_id = d.id
        WHERE p.prescription_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY p.prescription_date, d.name
        ORDER BY prescription_date DESC, total_items DESC
    """,

    # Customer Risk Analysis - fix table references (customer_code not customer_id)
    "d40dc61f-64e0-4f7c-8fd2-dfc86dc2e1da": """
        SELECT c.customer_code,
               c.name as customer_name,
               r.risk_level,
               r.risk_score,
               r.assessment_date
        FROM customers c
        JOIN risk_assessments r ON c.customer_code = r.customer_code
        WHERE r.is_active = true
        ORDER BY r.risk_score DESC
    """,
}


def update_pipeline_query(pipeline_id: str, new_query: str) -> bool:
    """Update pipeline query in database."""
    conn = psycopg2.connect(
        host="localhost", port=3102, database="smart_data",
        user="postgres", password="postgres"
    )
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT source_config FROM etl_pipelines WHERE id = %s", (pipeline_id,))
        row = cursor.fetchone()
        if not row:
            print(f"  ⚠️  Pipeline not found: {pipeline_id}")
            return False

        source_config = row[0]
        source_config['query'] = new_query.strip()

        cursor.execute(
            "UPDATE etl_pipelines SET source_config = %s::jsonb WHERE id = %s",
            (json.dumps(source_config), pipeline_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"  ❌ Error updating {pipeline_id}: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def main():
    print("=" * 60)
    print("Fixing ETL Pipeline Queries")
    print("=" * 60)

    fixed = 0
    failed = 0

    for pipeline_id, query in PIPELINE_FIXES.items():
        if update_pipeline_query(pipeline_id, query):
            print(f"  ✅ Fixed: {pipeline_id}")
            fixed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"Fixed: {fixed}, Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
