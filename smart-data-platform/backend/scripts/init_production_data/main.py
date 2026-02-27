#!/usr/bin/env python
"""
Production Data Generation Script

Main entry point for generating production-level test data for:
- Finance System (PostgreSQL - finance_db database) ~5M records
- IoT Platform (PostgreSQL - iot_db database) ~6M records
- HR System (MySQL - hr_system_db database) ~3M records
- Medical System (MySQL - medical_db database) ~4M records

Usage:
    python -m backend.scripts.init_production_data.main [OPTIONS]

Options:
    --all           Generate all systems (default)
    --finance       Generate finance system only
    --iot           Generate IoT platform only
    --hr            Generate HR system only
    --medical       Generate medical system only
    --parallel      Run generators in parallel (experimental)
    --dry-run       Show what would be generated without executing

Examples:
    # Generate all systems
    python -m backend.scripts.init_production_data.main

    # Generate specific systems
    python -m backend.scripts.init_production_data.main --finance --iot

    # Dry run to see configuration
    python -m backend.scripts.init_production_data.main --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

from . import config
from .config import (
    DATA_VOLUME_CONFIG,
    GENERATOR_CONFIG,
    MYSQL_CONFIG,
    POSTGRESQL_CONFIG,
)


def get_generators() -> dict:
    """Lazy import of generators to allow config modification before import."""
    from .generators import (
        FinanceDataGenerator,
        HRDataGenerator,
        IoTDataGenerator,
        MedicalDataGenerator,
    )
    return {
        "finance": FinanceDataGenerator,
        "iot": IoTDataGenerator,
        "hr": HRDataGenerator,
        "medical": MedicalDataGenerator,
    }


def print_banner() -> None:
    """Print script banner."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         Production Data Generation Script v1.0                   ║
║         Smart Data Platform - Test Data Generator                ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def print_config(scale: float = 1.0) -> None:
    """Print configuration summary."""
    vol = config.DATA_VOLUME_CONFIG

    if scale != 1.0:
        print(f"\n📊 Data Volume Configuration (scaled to {scale*100:.0f}%):")
    else:
        print("\n📊 Data Volume Configuration:")
    print("=" * 60)

    print("\n🏦 Finance System (PostgreSQL - finance_db database):")
    print(f"   - Customers:          {vol.finance_customers:>12,}")
    print(f"   - Accounts:           {vol.finance_accounts:>12,}")
    print(f"   - Transactions:       {vol.finance_transactions:>12,}")
    print(f"   - Portfolios:         {vol.finance_portfolios:>12,}")
    print(f"   - Portfolio Holdings: {vol.finance_portfolio_holdings:>12,}")
    print(f"   - Risk Assessments:   {vol.finance_risk_assessments:>12,}")
    print(f"   - Audit Logs:         {vol.finance_audit_logs:>12,}")
    finance_total = sum([
        vol.finance_customers,
        vol.finance_accounts,
        vol.finance_transactions,
        vol.finance_portfolios,
        vol.finance_portfolio_holdings,
        vol.finance_risk_assessments,
        vol.finance_audit_logs,
    ])
    print(f"   {'Total:':20} {finance_total:>12,}")

    print("\n🌐 IoT Platform (PostgreSQL - iot_db database):")
    print(f"   - Device Types:       {vol.iot_device_types:>12,}")
    print(f"   - Devices:            {vol.iot_devices:>12,}")
    print(f"   - Sensors:            {vol.iot_sensors:>12,}")
    print(f"   - Sensor Readings:    {vol.iot_sensor_readings:>12,}")
    print(f"   - Device Events:      {vol.iot_device_events:>12,}")
    print(f"   - Alerts:             {vol.iot_alerts:>12,}")
    print(f"   - Maintenance Logs:   {vol.iot_maintenance_logs:>12,}")
    iot_total = sum([
        vol.iot_device_types,
        vol.iot_devices,
        vol.iot_sensors,
        vol.iot_sensor_readings,
        vol.iot_device_events,
        vol.iot_alerts,
        vol.iot_maintenance_logs,
    ])
    print(f"   {'Total:':20} {iot_total:>12,}")

    print("\n👥 HR System (MySQL - hr_system_db database):")
    print(f"   - Departments:        {vol.hr_departments:>12,}")
    print(f"   - Positions:          {vol.hr_positions:>12,}")
    print(f"   - Employees:          {vol.hr_employees:>12,}")
    print(f"   - Salary Records:     {vol.hr_salary_records:>12,}")
    print(f"   - Attendance:         {vol.hr_attendance:>12,}")
    print(f"   - Performance Reviews:{vol.hr_performance_reviews:>12,}")
    print(f"   - Training Records:   {vol.hr_training_records:>12,}")
    print(f"   - Leave Requests:     {vol.hr_leave_requests:>12,}")
    hr_total = sum([
        vol.hr_departments,
        vol.hr_positions,
        vol.hr_employees,
        vol.hr_salary_records,
        vol.hr_attendance,
        vol.hr_performance_reviews,
        vol.hr_training_records,
        vol.hr_leave_requests,
    ])
    print(f"   {'Total:':20} {hr_total:>12,}")

    print("\n🏥 Medical System (MySQL - medical_db database):")
    print(f"   - Hospitals:          {vol.medical_hospitals:>12,}")
    print(f"   - Departments:        {vol.medical_departments:>12,}")
    print(f"   - Doctors:            {vol.medical_doctors:>12,}")
    print(f"   - Patients:           {vol.medical_patients:>12,}")
    print(f"   - Appointments:       {vol.medical_appointments:>12,}")
    print(f"   - Diagnoses:          {vol.medical_diagnoses:>12,}")
    print(f"   - Prescriptions:      {vol.medical_prescriptions:>12,}")
    print(f"   - Prescription Items: {vol.medical_prescription_items:>12,}")
    print(f"   - Lab Tests:          {vol.medical_lab_tests:>12,}")
    print(f"   - Lab Results:        {vol.medical_lab_results:>12,}")
    medical_total = sum([
        vol.medical_hospitals,
        vol.medical_departments,
        vol.medical_doctors,
        vol.medical_patients,
        vol.medical_appointments,
        vol.medical_diagnoses,
        vol.medical_prescriptions,
        vol.medical_prescription_items,
        vol.medical_lab_tests,
        vol.medical_lab_results,
    ])
    print(f"   {'Total:':20} {medical_total:>12,}")

    grand_total = finance_total + iot_total + hr_total + medical_total
    print("\n" + "=" * 60)
    print(f"   {'GRAND TOTAL:':20} {grand_total:>12,}")
    print("=" * 60)

    print("\n🔧 Generator Configuration:")
    print(f"   - Batch Size:         {GENERATOR_CONFIG.batch_size:>12,}")
    print(f"   - Commit Every:       {GENERATOR_CONFIG.commit_every:>12,}")
    print(f"   - Random Seed:        {GENERATOR_CONFIG.seed:>12}")
    print(f"   - Locale:             {GENERATOR_CONFIG.locale:>12}")

    print("\n🔌 Database Connections:")
    print(f"   - PostgreSQL: {POSTGRESQL_CONFIG.host}:{POSTGRESQL_CONFIG.port}")
    print(f"   - MySQL:      {MYSQL_CONFIG.host}:{MYSQL_CONFIG.port}")


def run_generator(generator_class: type, name: str) -> dict[str, Any]:
    """Run a single generator and return statistics."""
    start_time = time.time()
    try:
        generator = generator_class()
        generator.run()
        elapsed = time.time() - start_time
        return {
            "name": name,
            "status": "success",
            "elapsed": elapsed,
            "error": None,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "name": name,
            "status": "failed",
            "elapsed": elapsed,
            "error": str(e),
        }


def run_sequential(generators: list[tuple[type, str]]) -> list[dict[str, Any]]:
    """Run generators sequentially."""
    results = []
    for generator_class, name in generators:
        print(f"\n🚀 Starting {name}...")
        result = run_generator(generator_class, name)
        results.append(result)
        if result["status"] == "success":
            print(f"✅ {name} completed in {result['elapsed']:.2f} seconds")
        else:
            print(f"❌ {name} failed: {result['error']}")
    return results


def run_parallel(generators: list[tuple[type, str]]) -> list[dict[str, Any]]:
    """Run generators in parallel using ThreadPoolExecutor."""
    results = []
    print("\n🚀 Starting parallel execution...")

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(run_generator, gen_class, name): name
            for gen_class, name in generators
        }

        for future in as_completed(futures):
            name = futures[future]
            result = future.result()
            results.append(result)
            if result["status"] == "success":
                print(f"✅ {name} completed in {result['elapsed']:.2f} seconds")
            else:
                print(f"❌ {name} failed: {result['error']}")

    return results


def print_summary(results: list[dict[str, Any]], total_time: float) -> None:
    """Print execution summary."""
    print("\n" + "=" * 60)
    print("📋 Execution Summary")
    print("=" * 60)

    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")

    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"   {status_icon} {result['name']:20} {result['elapsed']:>8.2f}s")

    print("-" * 60)
    print(f"   Total Time: {total_time:.2f} seconds")
    print(f"   Success: {success_count}, Failed: {failed_count}")
    print("=" * 60)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate production-level test data for Smart Data Platform"
    )
    parser.add_argument("--all", action="store_true", help="Generate all systems (default)")
    parser.add_argument("--finance", action="store_true", help="Generate finance system")
    parser.add_argument("--iot", action="store_true", help="Generate IoT platform")
    parser.add_argument("--hr", action="store_true", help="Generate HR system")
    parser.add_argument("--medical", action="store_true", help="Generate medical system")
    parser.add_argument("--parallel", action="store_true", help="Run in parallel (experimental)")
    parser.add_argument("--dry-run", action="store_true", help="Show config without executing")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Scale factor for data volume (0.1 = 10%%, 0.5 = 50%%, 1.0 = 100%%)"
    )

    args = parser.parse_args()

    # Apply scaling if specified
    if args.scale != 1.0:
        config.DATA_VOLUME_CONFIG = DATA_VOLUME_CONFIG.scaled(args.scale)

    print_banner()
    print_config(args.scale)

    if args.dry_run:
        print("\n[Dry Run] No data will be generated.")
        return 0

    # Lazy import generators AFTER scaling is applied
    gen_classes = get_generators()

    generators: list[tuple[type, str]] = []

    if args.finance or (not any([args.finance, args.iot, args.hr, args.medical])):
        generators.append((gen_classes["finance"], "Finance System"))

    if args.iot or (not any([args.finance, args.iot, args.hr, args.medical])):
        generators.append((gen_classes["iot"], "IoT Platform"))

    if args.hr or (not any([args.finance, args.iot, args.hr, args.medical])):
        generators.append((gen_classes["hr"], "HR System"))

    if args.medical or (not any([args.finance, args.iot, args.hr, args.medical])):
        generators.append((gen_classes["medical"], "Medical System"))

    print(f"\n⏰ Starting generation at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Systems to generate: {', '.join(name for _, name in generators)}")

    start_time = time.time()

    if args.parallel:
        results = run_parallel(generators)
    else:
        results = run_sequential(generators)

    total_time = time.time() - start_time
    print_summary(results, total_time)

    failed = any(r["status"] == "failed" for r in results)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
