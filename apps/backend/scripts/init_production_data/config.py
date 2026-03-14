"""
Configuration for production data generation.

Defines database connections, data volumes, and generation parameters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PostgreSQLConfig:
    """PostgreSQL connection configuration for platform database."""

    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "3102"))
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")
    database: str = os.getenv("PG_DATABASE", "smart_data")

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def async_connection_string(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def admin_connection_string(self) -> str:
        """Connection string for admin operations (database creation)."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/postgres"


@dataclass(frozen=True)
class FinanceDBConfig:
    """Finance database configuration."""

    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "3102"))
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")
    database: str = "finance_db"

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class IoTDBConfig:
    """IoT database configuration."""

    host: str = os.getenv("PG_HOST", "localhost")
    port: int = int(os.getenv("PG_PORT", "3102"))
    user: str = os.getenv("PG_USER", "postgres")
    password: str = os.getenv("PG_PASSWORD", "postgres")
    database: str = "iot_db"

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class MedicalDBConfig:
    """Medical database configuration (MySQL)."""

    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3108"))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "mysql123")
    database: str = "medical_db"

    @property
    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class HRDBConfig:
    """HR database configuration (MySQL)."""

    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3108"))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "mysql123")
    database: str = "hr_system_db"

    @property
    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class MySQLConfig:
    """MySQL connection configuration."""

    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3108"))
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "mysql123")

    @property
    def connection_string(self) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}"

    def database_connection_string(self, database: str) -> str:
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{database}"


@dataclass(frozen=True)
class DataVolumeConfig:
    """Data volume configuration for each system."""

    # Finance System (PostgreSQL - finance_db database)
    finance_customers: int = 100_000
    finance_accounts: int = 200_000
    finance_transactions: int = 3_000_000
    finance_portfolios: int = 50_000
    finance_portfolio_holdings: int = 300_000
    finance_risk_assessments: int = 100_000
    finance_audit_logs: int = 1_000_000

    # IoT Platform (PostgreSQL - iot_db database)
    iot_device_types: int = 100
    iot_devices: int = 50_000
    iot_sensors: int = 200_000
    iot_sensor_readings: int = 5_000_000
    iot_device_events: int = 500_000
    iot_alerts: int = 100_000
    iot_maintenance_logs: int = 50_000

    # HR System (MySQL - hr_system_db database)
    hr_departments: int = 500
    hr_positions: int = 1_000
    hr_employees: int = 100_000
    hr_salary_records: int = 1_200_000
    hr_attendance: int = 2_400_000
    hr_performance_reviews: int = 200_000
    hr_training_records: int = 150_000
    hr_leave_requests: int = 100_000

    # Medical System (MySQL - medical_db database)
    medical_hospitals: int = 200
    medical_departments: int = 2_000
    medical_doctors: int = 20_000
    medical_patients: int = 500_000
    medical_appointments: int = 1_000_000
    medical_diagnoses: int = 800_000
    medical_prescriptions: int = 600_000
    medical_prescription_items: int = 2_000_000
    medical_lab_tests: int = 400_000
    medical_lab_results: int = 1_500_000

    def scaled(self, factor: float) -> "DataVolumeConfig":
        """Return a new config with all volumes scaled by the given factor."""
        return DataVolumeConfig(
            finance_customers=max(100, int(self.finance_customers * factor)),
            finance_accounts=max(200, int(self.finance_accounts * factor)),
            finance_transactions=max(1000, int(self.finance_transactions * factor)),
            finance_portfolios=max(50, int(self.finance_portfolios * factor)),
            finance_portfolio_holdings=max(100, int(self.finance_portfolio_holdings * factor)),
            finance_risk_assessments=max(100, int(self.finance_risk_assessments * factor)),
            finance_audit_logs=max(1000, int(self.finance_audit_logs * factor)),
            iot_device_types=max(10, int(self.iot_device_types * factor)),
            iot_devices=max(100, int(self.iot_devices * factor)),
            iot_sensors=max(200, int(self.iot_sensors * factor)),
            iot_sensor_readings=max(1000, int(self.iot_sensor_readings * factor)),
            iot_device_events=max(500, int(self.iot_device_events * factor)),
            iot_alerts=max(100, int(self.iot_alerts * factor)),
            iot_maintenance_logs=max(50, int(self.iot_maintenance_logs * factor)),
            hr_departments=max(50, int(self.hr_departments * factor)),
            hr_positions=max(100, int(self.hr_positions * factor)),
            hr_employees=max(1000, int(self.hr_employees * factor)),
            hr_salary_records=max(1000, int(self.hr_salary_records * factor)),
            hr_attendance=max(2000, int(self.hr_attendance * factor)),
            hr_performance_reviews=max(200, int(self.hr_performance_reviews * factor)),
            hr_training_records=max(150, int(self.hr_training_records * factor)),
            hr_leave_requests=max(100, int(self.hr_leave_requests * factor)),
            medical_hospitals=max(20, int(self.medical_hospitals * factor)),
            medical_departments=max(200, int(self.medical_departments * factor)),
            medical_doctors=max(200, int(self.medical_doctors * factor)),
            medical_patients=max(500, int(self.medical_patients * factor)),
            medical_appointments=max(1000, int(self.medical_appointments * factor)),
            medical_diagnoses=max(800, int(self.medical_diagnoses * factor)),
            medical_prescriptions=max(600, int(self.medical_prescriptions * factor)),
            medical_prescription_items=max(2000, int(self.medical_prescription_items * factor)),
            medical_lab_tests=max(400, int(self.medical_lab_tests * factor)),
            medical_lab_results=max(1500, int(self.medical_lab_results * factor)),
        )


@dataclass(frozen=True)
class GeneratorConfig:
    """Generator runtime configuration."""

    batch_size: int = 10_000
    commit_every: int = 10_000
    show_progress: bool = True
    seed: int = 42
    locale: str = "zh_CN"


# Default configuration instances
POSTGRESQL_CONFIG = PostgreSQLConfig()
MYSQL_CONFIG = MySQLConfig()
FINANCE_DB_CONFIG = FinanceDBConfig()
IOT_DB_CONFIG = IoTDBConfig()
MEDICAL_DB_CONFIG = MedicalDBConfig()
HR_DB_CONFIG = HRDBConfig()
DATA_VOLUME_CONFIG = DataVolumeConfig()
GENERATOR_CONFIG = GeneratorConfig()


# Chinese-specific data constants
CHINESE_SURNAMES: list[str] = [
    "王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴",
    "徐", "孙", "马", "朱", "胡", "郭", "林", "何", "高", "罗",
    "郑", "梁", "谢", "宋", "唐", "许", "邓", "冯", "韩", "曹",
    "曾", "彭", "萧", "蔡", "潘", "田", "董", "袁", "于", "余",
    "叶", "蒋", "杜", "苏", "魏", "程", "吕", "丁", "沈", "任",
]

CHINESE_GIVEN_NAMES: list[str] = [
    "伟", "芳", "娜", "秀英", "敏", "静", "丽", "强", "磊", "洋",
    "艳", "勇", "军", "杰", "娟", "涛", "明", "超", "秀兰", "霞",
    "平", "刚", "桂英", "华", "梅", "鹏", "辉", "玲", "桂兰", "峰",
    "建华", "建国", "建军", "志强", "志明", "志伟", "志华", "海燕", "海涛", "海峰",
    "文华", "文杰", "文军", "文明", "晓明", "晓红", "晓华", "晓伟", "小红", "小明",
]

CHINESE_CITIES: list[str] = [
    "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "武汉",
    "成都", "重庆", "天津", "西安", "青岛", "大连", "宁波", "厦门",
    "长沙", "郑州", "济南", "合肥", "福州", "无锡", "东莞", "佛山",
]

CHINESE_PROVINCES: list[str] = [
    "北京市", "上海市", "天津市", "重庆市",
    "河北省", "山西省", "辽宁省", "吉林省", "黑龙江省",
    "江苏省", "浙江省", "安徽省", "福建省", "江西省", "山东省",
    "河南省", "湖北省", "湖南省", "广东省", "海南省",
    "四川省", "贵州省", "云南省", "陕西省", "甘肃省",
    "青海省", "台湾省", "内蒙古自治区", "广西壮族自治区",
    "西藏自治区", "宁夏回族自治区", "新疆维吾尔自治区",
]

# Bank constants
BANK_NAMES: list[str] = [
    "中国工商银行", "中国建设银行", "中国农业银行", "中国银行",
    "交通银行", "招商银行", "浦发银行", "中信银行",
    "民生银行", "兴业银行", "光大银行", "华夏银行",
    "广发银行", "平安银行", "北京银行", "上海银行",
]

BANK_CODES: list[str] = [
    "ICBC", "CCB", "ABC", "BOC", "BOCOM", "CMB", "SPDB", "CITIC",
    "CMBC", "CIB", "CEB", "HXB", "GDB", "PAB", "BOB", "BOS",
]

# Medical constants
HOSPITAL_LEVELS: list[str] = ["三级甲等", "三级乙等", "二级甲等", "二级乙等", "一级"]

MEDICAL_DEPARTMENTS: list[str] = [
    "内科", "外科", "儿科", "妇产科", "眼科", "耳鼻喉科",
    "口腔科", "皮肤科", "神经内科", "神经外科", "心血管内科",
    "呼吸内科", "消化内科", "肾内科", "内分泌科", "风湿免疫科",
    "骨科", "泌尿外科", "胸外科", "肝胆外科", "肛肠科",
    "整形外科", "烧伤科", "康复科", "中医科", "急诊科",
    "重症医学科", "麻醉科", "放射科", "检验科", "病理科",
]

# ICD-10 codes (simplified)
ICD10_CODES: dict[str, str] = {
    "J00": "急性鼻咽炎",
    "J06.9": "急性上呼吸道感染",
    "J18.9": "肺炎",
    "I10": "高血压",
    "E11.9": "2型糖尿病",
    "K29.7": "胃炎",
    "K80.2": "胆囊结石",
    "M54.5": "腰痛",
    "N39.0": "尿路感染",
    "R50.9": "发热",
    "R51": "头痛",
    "R10.4": "腹痛",
    "A09": "胃肠炎",
    "B34.9": "病毒感染",
    "J45": "哮喘",
}

# IoT device types
IOT_DEVICE_TYPES: list[dict[str, Any]] = [
    {"name": "温度传感器", "category": "环境监测", "unit": "°C"},
    {"name": "湿度传感器", "category": "环境监测", "unit": "%"},
    {"name": "压力传感器", "category": "工业监测", "unit": "Pa"},
    {"name": "流量计", "category": "工业监测", "unit": "m³/h"},
    {"name": "电能表", "category": "能源监测", "unit": "kWh"},
    {"name": "水表", "category": "能源监测", "unit": "m³"},
    {"name": "气体传感器", "category": "安全监测", "unit": "ppm"},
    {"name": "烟雾报警器", "category": "安全监测", "unit": "level"},
    {"name": "门禁控制器", "category": "安防系统", "unit": "status"},
    {"name": "摄像头", "category": "安防系统", "unit": "fps"},
    {"name": "GPS定位器", "category": "定位追踪", "unit": "coordinates"},
    {"name": "振动传感器", "category": "设备监测", "unit": "mm/s"},
    {"name": "光照传感器", "category": "环境监测", "unit": "lux"},
    {"name": "噪音传感器", "category": "环境监测", "unit": "dB"},
    {"name": "pH传感器", "category": "水质监测", "unit": "pH"},
]

# HR job titles
HR_POSITIONS: list[dict[str, str]] = [
    {"name": "软件工程师", "level": "P5", "department": "技术部"},
    {"name": "高级软件工程师", "level": "P6", "department": "技术部"},
    {"name": "技术专家", "level": "P7", "department": "技术部"},
    {"name": "产品经理", "level": "P5", "department": "产品部"},
    {"name": "高级产品经理", "level": "P6", "department": "产品部"},
    {"name": "UI设计师", "level": "P5", "department": "设计部"},
    {"name": "UX设计师", "level": "P6", "department": "设计部"},
    {"name": "数据分析师", "level": "P5", "department": "数据部"},
    {"name": "数据科学家", "level": "P6", "department": "数据部"},
    {"name": "运维工程师", "level": "P5", "department": "运维部"},
    {"name": "测试工程师", "level": "P5", "department": "质量部"},
    {"name": "项目经理", "level": "P6", "department": "PMO"},
    {"name": "人事专员", "level": "P4", "department": "人力资源部"},
    {"name": "财务专员", "level": "P4", "department": "财务部"},
    {"name": "法务专员", "level": "P5", "department": "法务部"},
    {"name": "市场专员", "level": "P4", "department": "市场部"},
    {"name": "销售代表", "level": "P4", "department": "销售部"},
    {"name": "客服专员", "level": "P3", "department": "客服部"},
    {"name": "行政专员", "level": "P3", "department": "行政部"},
    {"name": "总监", "level": "M3", "department": "管理层"},
]

# Finance product types
FINANCE_PRODUCTS: list[dict[str, Any]] = [
    {"name": "活期存款", "type": "deposit", "risk_level": 1, "min_amount": 0},
    {"name": "定期存款", "type": "deposit", "risk_level": 1, "min_amount": 1000},
    {"name": "货币基金", "type": "fund", "risk_level": 2, "min_amount": 100},
    {"name": "债券基金", "type": "fund", "risk_level": 3, "min_amount": 1000},
    {"name": "混合基金", "type": "fund", "risk_level": 4, "min_amount": 1000},
    {"name": "股票基金", "type": "fund", "risk_level": 5, "min_amount": 1000},
    {"name": "指数基金", "type": "fund", "risk_level": 4, "min_amount": 100},
    {"name": "黄金ETF", "type": "etf", "risk_level": 4, "min_amount": 100},
    {"name": "理财产品", "type": "wealth", "risk_level": 3, "min_amount": 10000},
    {"name": "大额存单", "type": "deposit", "risk_level": 1, "min_amount": 200000},
]

TRANSACTION_TYPES: list[str] = [
    "存款", "取款", "转账", "消费", "退款", "利息", "手续费", "红利", "申购", "赎回",
]
