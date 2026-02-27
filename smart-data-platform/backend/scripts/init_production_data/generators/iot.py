"""
IoT Platform Data Generator.

Generates production-level test data for the iot database:
- device_types (100)
- devices (50,000)
- sensors (200,000)
- sensor_readings (5,000,000)
- device_events (500,000)
- alerts (100,000)
- maintenance_logs (50,000)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import text

from .base import BaseDataGenerator, create_postgresql_database
from .. import config
from ..config import (
    CHINESE_CITIES,
    IOT_DB_CONFIG,
    IOT_DEVICE_TYPES,
    POSTGRESQL_CONFIG,
)


class IoTDataGenerator(BaseDataGenerator):
    """Generator for IoT platform test data."""

    SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "iot.sql"

    def __init__(self):
        super().__init__(IOT_DB_CONFIG.connection_string)
        self.device_type_ids: list[int] = []
        self.device_ids: list[int] = []
        self.sensor_ids: list[int] = []

    def create_database(self) -> None:
        """Create the iot_db database if it doesn't exist."""
        create_postgresql_database(
            POSTGRESQL_CONFIG.admin_connection_string,
            IOT_DB_CONFIG.database
        )

    def create_schema(self) -> None:
        """Create the iot schema (tables in public)."""
        self.execute_sql_file(str(self.SCHEMA_FILE))

    def generate_data(self) -> None:
        """Generate all IoT data."""
        self._generate_device_types()
        self._generate_devices()
        self._generate_sensors()
        self._generate_sensor_readings()
        self._generate_device_events()
        self._generate_alerts()
        self._generate_maintenance_logs()

    def _generate_device_types(self) -> None:
        """Generate device type data."""
        total = config.DATA_VOLUME_CONFIG.iot_device_types
        columns = [
            "type_code", "name", "category", "manufacturer", "model",
            "protocol", "data_format", "firmware_version", "power_type",
            "expected_lifetime_days", "default_sampling_interval", "specifications",
            "created_at", "updated_at"
        ]

        manufacturers = ["华为", "中兴", "海康威视", "大华", "博世", "西门子", "ABB", "施耐德"]
        protocols = ["mqtt", "http", "modbus", "coap", "lorawan", "nbiot"]
        power_types = ["battery", "solar", "wired", "hybrid"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            base_types = IOT_DEVICE_TYPES * (total // len(IOT_DEVICE_TYPES) + 1)
            for i in range(total):
                base = base_types[i]
                now = datetime.now()

                yield (
                    f"DT{i + 1:04d}",
                    f"{base['name']} {random.choice(['Pro', 'Plus', 'Lite', 'Max', ''])}".strip(),
                    base["category"],
                    random.choice(manufacturers),
                    f"Model-{random.choice(['A', 'B', 'C', 'X', 'Z'])}{random.randint(100, 999)}",
                    random.choice(protocols),
                    "json",
                    f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
                    random.choice(power_types),
                    random.randint(365, 3650),
                    random.choice([10, 30, 60, 300, 600, 3600]),
                    json.dumps({
                        "unit": base["unit"],
                        "accuracy": f"±{round(random.uniform(0.1, 2.0), 1)}%",
                        "operating_temp": "-20°C ~ 60°C",
                        "protection_level": random.choice(["IP65", "IP66", "IP67", "IP68"])
                    }),
                    now,
                    now
                )

        self.batch_insert("device_types", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM device_types"))
            self.device_type_ids = [row[0] for row in result]

    def _generate_devices(self) -> None:
        """Generate device data."""
        total = config.DATA_VOLUME_CONFIG.iot_devices
        columns = [
            "device_id", "device_type_id", "name", "description", "serial_number",
            "mac_address", "ip_address", "firmware_version", "hardware_version",
            "latitude", "longitude", "altitude", "location_name", "installation_date",
            "warranty_until", "owner_id", "group_id", "tags", "config",
            "last_heartbeat_at", "last_data_at", "battery_level", "signal_strength",
            "status", "error_code", "error_message", "created_at", "updated_at"
        ]

        statuses = ["online", "offline", "maintenance", "error"]
        status_weights = [0.75, 0.15, 0.05, 0.05]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                device_type_id = random.choice(self.device_type_ids)
                lat, lon = self.generate_coordinates()
                city = random.choice(CHINESE_CITIES)
                status = random.choices(statuses, weights=status_weights)[0]
                now = datetime.now()
                install_date = self.generate_random_datetime(
                    datetime(2020, 1, 1),
                    datetime(2025, 12, 31)
                ).date()

                yield (
                    f"DEV{uuid.uuid4().hex[:16].upper()}",
                    device_type_id,
                    f"设备-{city[:2]}-{i + 1:05d}",
                    f"位于{city}的监测设备",
                    f"SN{uuid.uuid4().hex[:12].upper()}",
                    self.generate_mac_address(),
                    self.generate_ip_address() if random.random() > 0.3 else None,
                    f"{random.randint(1, 3)}.{random.randint(0, 9)}.{random.randint(0, 99)}",
                    f"v{random.randint(1, 2)}.0",
                    lat,
                    lon,
                    round(random.uniform(0, 500), 2),
                    f"{city}工业园区{random.randint(1, 20)}号厂房",
                    install_date,
                    install_date + timedelta(days=random.randint(365, 1095)),
                    f"owner{random.randint(1, 100)}",
                    f"group{random.randint(1, 50)}",
                    [random.choice(["生产", "测试", "监控", "预警", "远程"])] if random.random() > 0.5 else None,
                    json.dumps({"reporting_interval": random.choice([60, 300, 600]), "threshold_enabled": True}),
                    now - timedelta(minutes=random.randint(0, 1440)) if status == "online" else None,
                    now - timedelta(minutes=random.randint(0, 1440)) if status == "online" else None,
                    random.randint(0, 100) if random.random() > 0.3 else None,
                    random.randint(-100, -30) if random.random() > 0.3 else None,
                    status,
                    f"E{random.randint(100, 999)}" if status == "error" else None,
                    "Connection timeout" if status == "error" else None,
                    now,
                    now
                )

        self.batch_insert("devices", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM devices"))
            self.device_ids = [row[0] for row in result]

    def _generate_sensors(self) -> None:
        """Generate sensor data."""
        total = config.DATA_VOLUME_CONFIG.iot_sensors
        columns = [
            "sensor_id", "device_id", "name", "sensor_type", "unit", "data_type",
            "min_value", "max_value", "precision_value", "accuracy",
            "sampling_interval", "aggregation_method", "threshold_low",
            "threshold_high", "alert_enabled", "calibration_date", "calibration_due",
            "calibration_offset", "calibration_factor", "last_value",
            "last_reading_at", "status", "created_at", "updated_at"
        ]

        sensor_configs = [
            {"type": "temperature", "unit": "°C", "min": -40, "max": 100, "precision": 0.1},
            {"type": "humidity", "unit": "%", "min": 0, "max": 100, "precision": 0.5},
            {"type": "pressure", "unit": "Pa", "min": 0, "max": 500000, "precision": 10},
            {"type": "flow_rate", "unit": "m³/h", "min": 0, "max": 1000, "precision": 0.01},
            {"type": "power", "unit": "kW", "min": 0, "max": 10000, "precision": 0.1},
            {"type": "voltage", "unit": "V", "min": 0, "max": 500, "precision": 0.01},
            {"type": "current", "unit": "A", "min": 0, "max": 1000, "precision": 0.01},
            {"type": "vibration", "unit": "mm/s", "min": 0, "max": 100, "precision": 0.001},
            {"type": "noise", "unit": "dB", "min": 20, "max": 140, "precision": 0.1},
            {"type": "co2", "unit": "ppm", "min": 0, "max": 5000, "precision": 1},
        ]
        aggregation_methods = ["avg", "sum", "min", "max", "last"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                device_id = random.choice(self.device_ids)
                config = random.choice(sensor_configs)
                now = datetime.now()
                cal_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2025, 12, 31)
                ).date()
                last_value = round(random.uniform(config["min"], config["max"]), 2)

                yield (
                    f"SNS{uuid.uuid4().hex[:16].upper()}",
                    device_id,
                    f"{config['type'].replace('_', ' ').title()} Sensor {i + 1}",
                    config["type"],
                    config["unit"],
                    "float",
                    config["min"],
                    config["max"],
                    config["precision"],
                    round(random.uniform(0.1, 2.0), 4),
                    random.choice([10, 30, 60, 300, 600]),
                    random.choice(aggregation_methods),
                    config["min"] + (config["max"] - config["min"]) * 0.1,
                    config["max"] - (config["max"] - config["min"]) * 0.1,
                    random.random() > 0.2,
                    cal_date,
                    cal_date + timedelta(days=365),
                    round(random.uniform(-1, 1), 6),
                    round(random.uniform(0.98, 1.02), 6),
                    last_value,
                    now - timedelta(seconds=random.randint(0, 3600)),
                    random.choices(["active", "inactive", "error"], weights=[0.9, 0.07, 0.03])[0],
                    now,
                    now
                )

        self.batch_insert("sensors", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM sensors"))
            self.sensor_ids = [row[0] for row in result]

    def _generate_sensor_readings(self) -> None:
        """Generate sensor readings data (time-series)."""
        total = config.DATA_VOLUME_CONFIG.iot_sensor_readings
        columns = [
            "sensor_id", "value", "quality", "raw_value", "unit", "metadata",
            "is_anomaly", "anomaly_score", "recorded_at", "received_at"
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                sensor_id = random.choice(self.sensor_ids)
                value = round(random.uniform(-100, 1000), 6)
                raw_value = value * random.uniform(0.99, 1.01)
                quality = random.choices([100, 95, 90, 80, 50], weights=[0.7, 0.15, 0.1, 0.04, 0.01])[0]
                is_anomaly = random.random() < 0.02
                recorded_at = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                )

                yield (
                    sensor_id,
                    value,
                    quality,
                    raw_value,
                    random.choice(["°C", "%", "Pa", "m³/h", "kW", "V", "A"]),
                    json.dumps({"source": "auto"}) if random.random() > 0.9 else None,
                    is_anomaly,
                    round(random.uniform(0.8, 1.0), 4) if is_anomaly else None,
                    recorded_at,
                    recorded_at + timedelta(milliseconds=random.randint(10, 500))
                )

        self.batch_insert("sensor_readings", columns, data_generator(), total)

    def _generate_device_events(self) -> None:
        """Generate device event data."""
        total = config.DATA_VOLUME_CONFIG.iot_device_events
        columns = [
            "event_id", "device_id", "event_type", "severity", "source",
            "message", "details", "acknowledged", "acknowledged_by",
            "acknowledged_at", "resolution", "resolved_at", "occurred_at", "created_at"
        ]

        event_types = ["startup", "shutdown", "config_change", "firmware_update", "error", "warning", "heartbeat"]
        severities = ["debug", "info", "warning", "error", "critical"]
        severity_weights = [0.05, 0.5, 0.25, 0.15, 0.05]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                device_id = random.choice(self.device_ids)
                event_type = random.choice(event_types)
                severity = random.choices(severities, weights=severity_weights)[0]
                occurred_at = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                )
                acknowledged = random.random() > 0.3 if severity in ["warning", "error", "critical"] else False

                yield (
                    f"EVT{uuid.uuid4().hex[:24].upper()}",
                    device_id,
                    event_type,
                    severity,
                    random.choice(["system", "user", "api", "scheduler"]),
                    f"{event_type.replace('_', ' ').title()} event occurred",
                    json.dumps({"event_code": random.randint(100, 999), "context": "auto-generated"}),
                    acknowledged,
                    f"operator{random.randint(1, 50)}" if acknowledged else None,
                    occurred_at + timedelta(minutes=random.randint(5, 120)) if acknowledged else None,
                    "Issue resolved" if acknowledged and random.random() > 0.5 else None,
                    occurred_at + timedelta(hours=random.randint(1, 24)) if acknowledged and random.random() > 0.5 else None,
                    occurred_at,
                    occurred_at
                )

        self.batch_insert("device_events", columns, data_generator(), total)

    def _generate_alerts(self) -> None:
        """Generate alert data."""
        total = config.DATA_VOLUME_CONFIG.iot_alerts
        columns = [
            "alert_id", "device_id", "sensor_id", "alert_type", "severity",
            "rule_name", "condition", "actual_value", "threshold_value",
            "message", "status", "priority", "escalation_level",
            "notification_sent", "notification_channels", "assigned_to",
            "acknowledged_by", "acknowledged_at", "resolved_by", "resolved_at",
            "resolution_notes", "triggered_at", "created_at", "updated_at"
        ]

        alert_types = ["threshold", "anomaly", "connectivity", "battery", "maintenance"]
        severities = ["info", "warning", "critical", "emergency"]
        severity_weights = [0.2, 0.4, 0.3, 0.1]
        statuses = ["active", "acknowledged", "resolved", "suppressed"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                device_id = random.choice(self.device_ids)
                sensor_id = random.choice(self.sensor_ids) if random.random() > 0.3 else None
                severity = random.choices(severities, weights=severity_weights)[0]
                status = random.choices(statuses, weights=[0.2, 0.3, 0.45, 0.05])[0]
                triggered_at = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                )
                actual = round(random.uniform(0, 100), 2)
                threshold = round(actual * random.uniform(0.7, 0.95), 2)
                now = datetime.now()

                yield (
                    f"ALT{uuid.uuid4().hex[:24].upper()}",
                    device_id,
                    sensor_id,
                    random.choice(alert_types),
                    severity,
                    f"Rule-{random.randint(1, 100)}",
                    f"value > {threshold}",
                    actual,
                    threshold,
                    f"Alert: Value {actual} exceeded threshold {threshold}",
                    status,
                    random.randint(1, 5),
                    random.randint(0, 3),
                    status != "active",
                    ["email", "sms"] if status != "active" else None,
                    f"tech{random.randint(1, 20)}" if status in ["acknowledged", "resolved"] else None,
                    f"operator{random.randint(1, 50)}" if status in ["acknowledged", "resolved"] else None,
                    triggered_at + timedelta(minutes=random.randint(5, 60)) if status in ["acknowledged", "resolved"] else None,
                    f"tech{random.randint(1, 20)}" if status == "resolved" else None,
                    triggered_at + timedelta(hours=random.randint(1, 48)) if status == "resolved" else None,
                    "Issue investigated and resolved" if status == "resolved" else None,
                    triggered_at,
                    triggered_at,
                    now
                )

        self.batch_insert("alerts", columns, data_generator(), total)

    def _generate_maintenance_logs(self) -> None:
        """Generate maintenance log data."""
        total = config.DATA_VOLUME_CONFIG.iot_maintenance_logs
        columns = [
            "maintenance_id", "device_id", "maintenance_type", "category",
            "description", "scheduled_at", "started_at", "completed_at",
            "estimated_duration", "actual_duration", "technician_id",
            "technician_name", "work_order_id", "parts_used", "labor_cost",
            "parts_cost", "total_cost", "findings", "actions_taken",
            "recommendations", "next_maintenance_date", "attachments",
            "status", "created_at", "updated_at"
        ]

        maintenance_types = ["preventive", "corrective", "predictive", "emergency"]
        categories = ["calibration", "repair", "replacement", "inspection", "cleaning"]
        statuses = ["scheduled", "in_progress", "completed", "cancelled"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            for i in range(total):
                device_id = random.choice(self.device_ids)
                mtype = random.choice(maintenance_types)
                status = random.choices(statuses, weights=[0.15, 0.1, 0.7, 0.05])[0]
                scheduled_at = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 6, 30)
                )
                started_at = scheduled_at + timedelta(minutes=random.randint(-30, 60)) if status in ["in_progress", "completed"] else None
                est_duration = random.randint(30, 480)
                actual_duration = random.randint(int(est_duration * 0.8), int(est_duration * 1.5)) if status == "completed" else None
                completed_at = started_at + timedelta(minutes=actual_duration) if status == "completed" and started_at else None
                labor_cost = round(random.uniform(100, 2000), 2)
                parts_cost = round(random.uniform(0, 5000), 2)
                now = datetime.now()

                yield (
                    f"MNT{uuid.uuid4().hex[:24].upper()}",
                    device_id,
                    mtype,
                    random.choice(categories),
                    f"{mtype.capitalize()} maintenance for device",
                    scheduled_at,
                    started_at,
                    completed_at,
                    est_duration,
                    actual_duration,
                    f"tech{random.randint(1, 50)}",
                    self.generate_chinese_name(),
                    f"WO{random.randint(10000, 99999)}",
                    json.dumps([{"part": "Sensor Module", "qty": 1}]) if random.random() > 0.5 else None,
                    labor_cost,
                    parts_cost,
                    labor_cost + parts_cost,
                    "Device inspected, all components functional" if status == "completed" else None,
                    "Cleaned sensors, updated firmware" if status == "completed" else None,
                    "Schedule next inspection in 6 months" if status == "completed" else None,
                    (completed_at + timedelta(days=180)).date() if completed_at else None,
                    None,
                    status,
                    now,
                    now
                )

        self.batch_insert("maintenance_logs", columns, data_generator(), total)
