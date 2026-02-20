"""
Create example ETL pipelines for production data sources.

Creates 2 example pipelines for each data system:
- Finance: 交易汇总报表, 风险指标计算
- IoT: 设备状态聚合, 告警统计分析
- HR: 薪资月度报表, 考勤统计分析
- Medical: 就诊统计分析, 处方分析报表

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/create_example_pipelines.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.metadata import DataSource
from app.models.etl import ETLPipeline, ETLStep, ETLStepType, PipelineStatus


# Pipeline definitions - will be populated with actual source IDs
def get_pipeline_definitions(sources: dict[str, UUID]) -> list[dict]:
    """Get pipeline definitions with actual source IDs."""
    return [
        # ===============================
        # Finance Pipelines
        # ===============================
        {
            "name": "金融交易日汇总报表",
            "description": "按日期汇总交易数据，计算每日交易量、交易金额、手续费等指标",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["finance"]),
                "query": """
                    SELECT
                        DATE(transaction_date) as trade_date,
                        transaction_type,
                        COUNT(*) as transaction_count,
                        SUM(amount) as total_amount,
                        AVG(amount) as avg_amount,
                        SUM(fee) as total_fee,
                        COUNT(DISTINCT account_id) as unique_accounts
                    FROM finance.transactions
                    WHERE status = 'completed'
                    GROUP BY DATE(transaction_date), transaction_type
                    ORDER BY trade_date DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["finance"]),
                "table_name": "finance.daily_transaction_summary",
                "if_exists": "replace",
            },
            "tags": ["finance", "report", "daily"],
            "steps": [
                {
                    "name": "按日期排序",
                    "step_type": ETLStepType.SORT,
                    "config": {"columns": ["trade_date"], "ascending": False},
                    "order": 1,
                },
                {
                    "name": "计算交易占比",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "fee_ratio",
                                "expression": "total_fee / total_amount * 100",
                            }
                        ]
                    },
                    "order": 2,
                },
            ],
        },
        {
            "name": "客户风险评分分析",
            "description": "分析客户风险评估数据，按风险等级分组统计",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["finance"]),
                "query": """
                    SELECT
                        c.customer_type,
                        r.risk_level,
                        r.risk_category,
                        COUNT(*) as customer_count,
                        AVG(r.risk_score) as avg_risk_score,
                        MIN(r.assessment_date) as earliest_assessment,
                        MAX(r.assessment_date) as latest_assessment
                    FROM finance.risk_assessments r
                    JOIN finance.customers c ON r.customer_id = c.id
                    WHERE r.is_active = true
                    GROUP BY c.customer_type, r.risk_level, r.risk_category
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["finance"]),
                "table_name": "finance.risk_analysis_report",
                "if_exists": "replace",
            },
            "tags": ["finance", "risk", "analysis"],
            "steps": [
                {
                    "name": "风险等级映射",
                    "step_type": ETLStepType.MAP_VALUES,
                    "config": {
                        "column": "risk_level",
                        "mapping": {
                            "low": "低风险",
                            "medium": "中风险",
                            "high": "高风险",
                            "critical": "极高风险",
                        },
                    },
                    "order": 1,
                },
                {
                    "name": "按风险评分排序",
                    "step_type": ETLStepType.SORT,
                    "config": {"columns": ["avg_risk_score"], "ascending": False},
                    "order": 2,
                },
            ],
        },
        # ===============================
        # IoT Pipelines
        # ===============================
        {
            "name": "设备状态实时聚合",
            "description": "聚合设备最新状态数据，按设备类型和状态分组统计",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["iot"]),
                "query": """
                    SELECT
                        dt.type_name as device_type,
                        d.status,
                        d.location,
                        COUNT(*) as device_count,
                        COUNT(CASE WHEN d.is_online = true THEN 1 END) as online_count,
                        AVG(EXTRACT(EPOCH FROM (NOW() - d.last_heartbeat))/3600) as avg_hours_since_heartbeat
                    FROM iot.devices d
                    JOIN iot.device_types dt ON d.device_type_id = dt.id
                    GROUP BY dt.type_name, d.status, d.location
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["iot"]),
                "table_name": "iot.device_status_summary",
                "if_exists": "replace",
            },
            "tags": ["iot", "device", "status"],
            "steps": [
                {
                    "name": "计算在线率",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "online_rate",
                                "expression": "online_count / device_count * 100",
                            }
                        ]
                    },
                    "order": 1,
                },
                {
                    "name": "按设备数量排序",
                    "step_type": ETLStepType.SORT,
                    "config": {"columns": ["device_count"], "ascending": False},
                    "order": 2,
                },
            ],
        },
        {
            "name": "告警统计分析报表",
            "description": "按告警级别和类型统计告警数据，分析告警趋势",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["iot"]),
                "query": """
                    SELECT
                        DATE(a.triggered_at) as alert_date,
                        a.severity,
                        a.alert_type,
                        COUNT(*) as alert_count,
                        COUNT(CASE WHEN a.is_resolved = true THEN 1 END) as resolved_count,
                        AVG(EXTRACT(EPOCH FROM (a.resolved_at - a.triggered_at))/60) as avg_resolution_minutes
                    FROM iot.alerts a
                    WHERE a.triggered_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(a.triggered_at), a.severity, a.alert_type
                    ORDER BY alert_date DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["iot"]),
                "table_name": "iot.alert_statistics",
                "if_exists": "replace",
            },
            "tags": ["iot", "alert", "statistics"],
            "steps": [
                {
                    "name": "告警级别映射",
                    "step_type": ETLStepType.MAP_VALUES,
                    "config": {
                        "column": "severity",
                        "mapping": {
                            "info": "信息",
                            "warning": "警告",
                            "error": "错误",
                            "critical": "严重",
                        },
                    },
                    "order": 1,
                },
                {
                    "name": "计算解决率",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "resolution_rate",
                                "expression": "resolved_count / alert_count * 100",
                            }
                        ]
                    },
                    "order": 2,
                },
            ],
        },
        # ===============================
        # HR Pipelines
        # ===============================
        {
            "name": "员工薪资月度统计",
            "description": "按部门汇总月度薪资数据，计算平均薪资、总成本等指标",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["hr"]),
                "query": """
                    SELECT
                        d.name as department_name,
                        DATE_FORMAT(s.pay_date, '%Y-%m') as pay_month,
                        COUNT(DISTINCT s.employee_id) as employee_count,
                        SUM(s.gross_salary) as total_gross,
                        AVG(s.gross_salary) as avg_gross,
                        SUM(s.net_salary) as total_net,
                        SUM(s.total_deductions) as total_deductions,
                        SUM(s.bonus) as total_bonus,
                        SUM(s.overtime_pay) as total_overtime
                    FROM hr_system.salary_records s
                    JOIN hr_system.employees e ON s.employee_id = e.id
                    JOIN hr_system.departments d ON e.department_id = d.id
                    WHERE s.payment_status = 'paid'
                    GROUP BY d.name, DATE_FORMAT(s.pay_date, '%Y-%m')
                    ORDER BY pay_month DESC, total_gross DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["hr"]),
                "table_name": "monthly_salary_report",
                "if_exists": "replace",
            },
            "tags": ["hr", "salary", "monthly"],
            "steps": [
                {
                    "name": "计算人均奖金",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "avg_bonus",
                                "expression": "total_bonus / employee_count",
                            }
                        ]
                    },
                    "order": 1,
                },
                {
                    "name": "按总薪资排序",
                    "step_type": ETLStepType.SORT,
                    "config": {"columns": ["pay_month", "total_gross"], "ascending": [False, False]},
                    "order": 2,
                },
            ],
        },
        {
            "name": "员工考勤分析报表",
            "description": "按部门统计考勤数据，分析迟到、早退、缺勤情况",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["hr"]),
                "query": """
                    SELECT
                        d.name as department_name,
                        DATE_FORMAT(a.attendance_date, '%Y-%m') as month,
                        COUNT(*) as total_records,
                        SUM(CASE WHEN a.is_late = 1 THEN 1 ELSE 0 END) as late_count,
                        SUM(CASE WHEN a.is_early_leave = 1 THEN 1 ELSE 0 END) as early_leave_count,
                        SUM(CASE WHEN a.is_absent = 1 THEN 1 ELSE 0 END) as absent_count,
                        AVG(a.work_hours) as avg_work_hours,
                        SUM(a.overtime_hours) as total_overtime_hours
                    FROM hr_system.attendance a
                    JOIN hr_system.employees e ON a.employee_id = e.id
                    JOIN hr_system.departments d ON e.department_id = d.id
                    GROUP BY d.name, DATE_FORMAT(a.attendance_date, '%Y-%m')
                    ORDER BY month DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["hr"]),
                "table_name": "attendance_analysis_report",
                "if_exists": "replace",
            },
            "tags": ["hr", "attendance", "analysis"],
            "steps": [
                {
                    "name": "计算出勤率",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "attendance_rate",
                                "expression": "(total_records - absent_count) / total_records * 100",
                            },
                            {
                                "column": "late_rate",
                                "expression": "late_count / total_records * 100",
                            },
                        ]
                    },
                    "order": 1,
                },
            ],
        },
        # ===============================
        # Medical Pipelines
        # ===============================
        {
            "name": "门诊就诊统计分析",
            "description": "按科室和医生统计门诊就诊数据，分析就诊量和患者满意度",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["medical"]),
                "query": """
                    SELECT
                        h.name as hospital_name,
                        dep.name as department_name,
                        doc.name as doctor_name,
                        DATE_FORMAT(a.appointment_date, '%Y-%m') as month,
                        COUNT(*) as appointment_count,
                        SUM(CASE WHEN a.status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                        SUM(CASE WHEN a.status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count,
                        SUM(CASE WHEN a.status = 'no_show' THEN 1 ELSE 0 END) as no_show_count
                    FROM medical.appointments a
                    JOIN medical.doctors doc ON a.doctor_id = doc.id
                    JOIN medical.departments dep ON doc.department_id = dep.id
                    JOIN medical.hospitals h ON dep.hospital_id = h.id
                    GROUP BY h.name, dep.name, doc.name, DATE_FORMAT(a.appointment_date, '%Y-%m')
                    ORDER BY month DESC, appointment_count DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["medical"]),
                "table_name": "outpatient_statistics",
                "if_exists": "replace",
            },
            "tags": ["medical", "outpatient", "statistics"],
            "steps": [
                {
                    "name": "计算完成率",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "completion_rate",
                                "expression": "completed_count / appointment_count * 100",
                            },
                            {
                                "column": "no_show_rate",
                                "expression": "no_show_count / appointment_count * 100",
                            },
                        ]
                    },
                    "order": 1,
                },
            ],
        },
        {
            "name": "处方用药分析报表",
            "description": "分析处方药品使用情况，按药品类别统计用量和金额",
            "source_type": "query",
            "source_config": {
                "source_id": str(sources["medical"]),
                "query": """
                    SELECT
                        pi.drug_category,
                        pi.drug_name,
                        DATE_FORMAT(p.prescription_date, '%Y-%m') as month,
                        COUNT(DISTINCT p.id) as prescription_count,
                        SUM(pi.quantity) as total_quantity,
                        SUM(pi.unit_price * pi.quantity) as total_amount,
                        AVG(pi.unit_price) as avg_unit_price,
                        COUNT(DISTINCT p.patient_id) as unique_patients
                    FROM medical.prescription_items pi
                    JOIN medical.prescriptions p ON pi.prescription_id = p.id
                    WHERE p.status = 'dispensed'
                    GROUP BY pi.drug_category, pi.drug_name, DATE_FORMAT(p.prescription_date, '%Y-%m')
                    ORDER BY month DESC, total_amount DESC
                """,
            },
            "target_type": "table",
            "target_config": {
                "source_id": str(sources["medical"]),
                "table_name": "prescription_analysis_report",
                "if_exists": "replace",
            },
            "tags": ["medical", "prescription", "analysis"],
            "steps": [
                {
                    "name": "计算平均处方金额",
                    "step_type": ETLStepType.CALCULATE,
                    "config": {
                        "calculations": [
                            {
                                "column": "avg_prescription_amount",
                                "expression": "total_amount / prescription_count",
                            }
                        ]
                    },
                    "order": 1,
                },
                {
                    "name": "按金额排序",
                    "step_type": ETLStepType.SORT,
                    "config": {"columns": ["total_amount"], "ascending": False},
                    "order": 2,
                },
            ],
        },
    ]


async def create_pipelines() -> None:
    """Create example ETL pipelines."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("\n" + "=" * 60)
    print("创建示例 ETL 管道")
    print("=" * 60)

    async with async_session() as session:
        # Get data source IDs
        result = await session.execute(select(DataSource))
        all_sources = list(result.scalars())

        # Map source names to IDs
        source_map = {}
        for source in all_sources:
            if "Finance" in source.name or "金融" in source.name:
                source_map["finance"] = source.id
            elif "IoT" in source.name or "物联网" in source.name:
                source_map["iot"] = source.id
            elif "HR" in source.name or "人力资源" in source.name:
                source_map["hr"] = source.id
            elif "Medical" in source.name or "医疗" in source.name:
                source_map["medical"] = source.id

        if len(source_map) < 4:
            print(f"\n❌ 错误: 未找到所有数据源。当前找到: {list(source_map.keys())}")
            print("请先运行 register_production_sources.py")
            return

        print(f"\n找到数据源:")
        for name, source_id in source_map.items():
            print(f"  - {name}: {source_id}")

        # Get pipeline definitions
        pipelines_def = get_pipeline_definitions(source_map)

        created_count = 0
        skipped_count = 0

        for pipe_def in pipelines_def:
            # Check if pipeline already exists
            result = await session.execute(
                select(ETLPipeline).where(ETLPipeline.name == pipe_def["name"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"\n⏭️  跳过: {pipe_def['name']} (已存在)")
                skipped_count += 1
                continue

            # Create pipeline
            pipeline = ETLPipeline(
                name=pipe_def["name"],
                description=pipe_def["description"],
                source_type=pipe_def["source_type"],
                source_config=pipe_def["source_config"],
                target_type=pipe_def["target_type"],
                target_config=pipe_def["target_config"],
                tags=pipe_def["tags"],
                status=PipelineStatus.ACTIVE,
            )
            session.add(pipeline)
            await session.flush()

            # Create steps
            for step_def in pipe_def.get("steps", []):
                step = ETLStep(
                    pipeline_id=pipeline.id,
                    name=step_def["name"],
                    step_type=step_def["step_type"],
                    config=step_def["config"],
                    order=step_def["order"],
                    is_enabled=True,
                )
                session.add(step)

            print(f"\n✅ 已创建: {pipe_def['name']}")
            print(f"   标签: {', '.join(pipe_def['tags'])}")
            print(f"   步骤数: {len(pipe_def.get('steps', []))}")

            created_count += 1

        await session.commit()

        print("\n" + "-" * 60)
        print(f"完成: 创建 {created_count} 个管道, 跳过 {skipped_count} 个")
        print("=" * 60)

        # List all pipelines
        result = await session.execute(select(ETLPipeline))
        all_pipelines = list(result.scalars())

        print("\n📋 当前所有 ETL 管道:")
        print("-" * 60)
        for pipeline in all_pipelines:
            status_icon = "🟢" if pipeline.status == PipelineStatus.ACTIVE else "🔴"
            print(f"  {status_icon} {pipeline.name}")
            print(f"      标签: {', '.join(pipeline.tags)}")
        print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_pipelines())
