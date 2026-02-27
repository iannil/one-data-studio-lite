"""
Medical Health System Data Generator.

Generates production-level test data for the medical_db database (MySQL):
- hospitals (200)
- departments (2,000)
- doctors (20,000)
- patients (500,000)
- appointments (1,000,000)
- diagnoses (800,000)
- prescriptions (600,000)
- prescription_items (2,000,000)
- lab_tests (400,000)
- lab_results (1,500,000)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import text

from .base import BaseDataGenerator, create_mysql_database
from .. import config
from ..config import (
    CHINESE_CITIES,
    CHINESE_PROVINCES,
    HOSPITAL_LEVELS,
    ICD10_CODES,
    MEDICAL_DB_CONFIG,
    MEDICAL_DEPARTMENTS,
)


class MedicalDataGenerator(BaseDataGenerator):
    """Generator for medical health system test data."""

    SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "medical.sql"

    def __init__(self):
        super().__init__(MEDICAL_DB_CONFIG.connection_string)
        self.hospital_ids: list[int] = []
        self.department_ids: list[int] = []
        self.doctor_ids: list[int] = []
        self.patient_ids: list[int] = []
        self.appointment_ids: list[int] = []
        self.diagnosis_ids: list[int] = []
        self.prescription_ids: list[int] = []
        self.lab_test_ids: list[int] = []

    def create_database(self) -> None:
        """Create the medical_db database if it doesn't exist."""
        create_mysql_database(
            MEDICAL_DB_CONFIG.host,
            MEDICAL_DB_CONFIG.port,
            MEDICAL_DB_CONFIG.user,
            MEDICAL_DB_CONFIG.password,
            MEDICAL_DB_CONFIG.database
        )

    def create_schema(self) -> None:
        """Create the medical database schema (tables)."""
        # Check if tables already exist - skip if they do
        with self.get_connection() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema = '{MEDICAL_DB_CONFIG.database}' AND table_name = 'patients'"
            ))
            if result.scalar() > 0:
                print("  (Tables already exist, skipping schema creation)")
                return

        # Execute schema creation
        with self.get_connection() as conn:
            with open(self.SCHEMA_FILE, encoding="utf-8") as f:
                sql_content = f.read()

            statements = sql_content.split(";")
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(text(statement))
                        conn.commit()
                    except Exception as e:
                        # Only ignore "already exists" type errors
                        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                            continue
                        raise  # Re-raise other errors

    def generate_data(self) -> None:
        """Generate all medical data."""
        self._generate_hospitals()
        self._generate_departments()
        self._generate_doctors()
        self._generate_patients()
        self._generate_appointments()
        self._generate_diagnoses()
        self._generate_prescriptions()
        self._generate_prescription_items()
        self._generate_lab_tests()
        self._generate_lab_results()

    def _generate_hospitals(self) -> None:
        """Generate hospital data."""
        total = config.DATA_VOLUME_CONFIG.medical_hospitals
        columns = [
            "hospital_code", "name", "short_name", "hospital_level", "hospital_type",
            "ownership", "province", "city", "district", "address", "postal_code",
            "phone", "emergency_phone", "website", "email", "license_number",
            "established_date", "bed_count", "actual_bed_count", "staff_count",
            "doctor_count", "annual_outpatient_visits", "annual_inpatient_admissions",
            "specialties", "equipment", "certifications", "insurance_accepted",
            "latitude", "longitude", "status", "created_at", "updated_at"
        ]

        hospital_types = ["comprehensive", "specialized", "traditional_chinese", "rehabilitation"]
        ownership_types = ["public", "private", "military"]
        insurance_types = ["医保", "商业保险", "新农合", "公费医疗"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                city = random.choice(CHINESE_CITIES)
                province = random.choice(CHINESE_PROVINCES)
                level = random.choices(HOSPITAL_LEVELS, weights=[0.15, 0.25, 0.30, 0.20, 0.10])[0]
                lat, lon = self.generate_coordinates()
                bed_count = random.randint(100, 5000)

                yield (
                    f"HOSP{i + 1:05d}",
                    f"{city}市第{random.choice(['一', '二', '三', '四', '五'])}人民医院",
                    f"{city[:2]}一院",
                    level,
                    random.choice(hospital_types),
                    random.choice(ownership_types),
                    province,
                    city,
                    f"{city}市中心区",
                    f"{city}市中心路{random.randint(1, 999)}号",
                    f"{random.randint(100000, 999999)}",
                    f"0{random.randint(10, 99)}-{random.randint(10000000, 99999999)}",
                    f"0{random.randint(10, 99)}-{random.randint(10000000, 99999999)}",
                    f"https://www.hospital{i + 1}.com",
                    f"contact@hospital{i + 1}.com",
                    f"LIC{random.randint(10000000, 99999999)}",
                    datetime(random.randint(1950, 2010), random.randint(1, 12), random.randint(1, 28)).date(),
                    bed_count,
                    int(bed_count * random.uniform(0.7, 0.95)),
                    random.randint(500, 10000),
                    random.randint(100, 2000),
                    random.randint(100000, 5000000),
                    random.randint(10000, 200000),
                    random.sample(MEDICAL_DEPARTMENTS, k=min(10, len(MEDICAL_DEPARTMENTS))),
                    ["CT", "MRI", "超声", "X光", "内镜"],
                    ["ISO9001", "JCI认证"] if random.random() > 0.5 else None,
                    random.sample(insurance_types, k=random.randint(2, 4)),
                    lat,
                    lon,
                    random.choices(["active", "inactive"], weights=[0.95, 0.05])[0],
                    now,
                    now
                )

        self.batch_insert("hospitals", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM hospitals"))
            self.hospital_ids = [row[0] for row in result]

    def _generate_departments(self) -> None:
        """Generate department data."""
        total = config.DATA_VOLUME_CONFIG.medical_departments
        columns = [
            "department_code", "hospital_id", "name", "category", "parent_id",
            "floor", "building", "room_numbers", "phone", "description",
            "specialties", "services_offered", "operating_hours",
            "appointment_required", "max_daily_appointments", "consultation_fee",
            "is_emergency", "is_outpatient", "is_inpatient", "bed_count",
            "status", "created_at", "updated_at"
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()
            dept_idx = 0

            for hospital_id in self.hospital_ids:
                num_depts = total // len(self.hospital_ids)
                for j in range(num_depts):
                    if dept_idx >= total:
                        return

                    dept_name = MEDICAL_DEPARTMENTS[j % len(MEDICAL_DEPARTMENTS)]
                    is_emergency = "急诊" in dept_name
                    dept_idx += 1

                    yield (
                        f"DEPT{dept_idx:06d}",
                        hospital_id,
                        dept_name,
                        dept_name[:2] if len(dept_name) >= 2 else dept_name,
                        None,
                        f"{random.randint(1, 10)}楼",
                        random.choice(["门诊楼", "住院楼", "医技楼", "急诊楼"]),
                        f"{random.randint(100, 999)}-{random.randint(100, 999)}",
                        f"0{random.randint(10, 99)}-{random.randint(10000000, 99999999)}",
                        f"{dept_name}提供专业医疗服务",
                        f"{dept_name}相关疾病诊治",
                        ["门诊", "住院", "手术"],
                        {"weekday": "08:00-17:00", "weekend": "08:00-12:00"},
                        not is_emergency,
                        random.randint(50, 200) if not is_emergency else None,
                        round(random.uniform(10, 100), 2),
                        is_emergency,
                        True,
                        random.random() > 0.3,
                        random.randint(10, 100) if random.random() > 0.5 else None,
                        "active",
                        now,
                        now
                    )

        self.batch_insert("departments", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM departments"))
            self.department_ids = [row[0] for row in result]

    def _generate_doctors(self) -> None:
        """Generate doctor data."""
        total = config.DATA_VOLUME_CONFIG.medical_doctors
        columns = [
            "doctor_code", "hospital_id", "department_id", "name", "gender",
            "birth_date", "id_card_encrypted", "phone", "email", "title",
            "professional_level", "license_number", "license_issue_date",
            "license_expiry_date", "education_level", "medical_school",
            "graduation_year", "specializations", "certifications",
            "research_interests", "publications_count", "years_of_experience",
            "consultation_fee", "expert_fee", "is_expert", "is_available_for_appointment",
            "max_daily_appointments", "appointment_duration_minutes", "schedule",
            "languages", "photo_url", "bio", "rating", "review_count",
            "status", "hire_date", "resignation_date", "created_at", "updated_at"
        ]

        titles = ["主任医师", "副主任医师", "主治医师", "住院医师"]
        title_weights = [0.15, 0.25, 0.35, 0.25]
        levels = ["senior", "associate", "attending", "resident"]
        education_levels = ["bachelor", "master", "phd"]
        medical_schools = ["北京协和医学院", "上海交通大学医学院", "复旦大学医学院", "中山大学医学院", "华中科技大学同济医学院"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                hospital_id = random.choice(self.hospital_ids)
                department_id = random.choice(self.department_ids)
                name = self.generate_chinese_name()
                gender = random.choice(["M", "F"])
                title_idx = random.choices(range(len(titles)), weights=title_weights)[0]
                birth_year = random.randint(1960, 1995)
                exp_years = 2026 - birth_year - 24
                is_expert = title_idx < 2 and random.random() > 0.5

                yield (
                    f"DOC{i + 1:06d}",
                    hospital_id,
                    department_id,
                    name,
                    gender,
                    datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date(),
                    self.generate_id_card(),
                    self.generate_phone_number(),
                    self.generate_email(name),
                    titles[title_idx],
                    levels[title_idx],
                    f"LIC{random.randint(10000000000, 99999999999)}",
                    datetime(random.randint(2000, 2020), random.randint(1, 12), 1).date(),
                    datetime(random.randint(2025, 2030), random.randint(1, 12), 1).date(),
                    random.choice(education_levels),
                    random.choice(medical_schools),
                    birth_year + 24,
                    [random.choice(MEDICAL_DEPARTMENTS)[:4] + "疾病"],
                    ["执业医师资格证"],
                    "临床医学研究",
                    random.randint(0, 100) if title_idx < 2 else random.randint(0, 20),
                    max(0, exp_years),
                    round(random.uniform(20, 100), 2),
                    round(random.uniform(100, 500), 2) if is_expert else None,
                    is_expert,
                    random.random() > 0.1,
                    random.randint(20, 50),
                    random.choice([10, 15, 20, 30]),
                    {"mon": "08:00-12:00", "tue": "08:00-12:00", "wed": "14:00-17:00"},
                    ["中文", "英文"] if random.random() > 0.7 else ["中文"],
                    None,
                    f"{name}医生，从医{exp_years}年，擅长{random.choice(MEDICAL_DEPARTMENTS)[:4]}疾病诊治",
                    round(random.uniform(4.0, 5.0), 2),
                    random.randint(10, 1000),
                    random.choices(["active", "inactive"], weights=[0.95, 0.05])[0],
                    datetime(random.randint(2000, 2020), random.randint(1, 12), random.randint(1, 28)).date(),
                    None,
                    now,
                    now
                )

        self.batch_insert("doctors", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM doctors"))
            self.doctor_ids = [row[0] for row in result]

    def _generate_patients(self) -> None:
        """Generate patient data."""
        total = config.DATA_VOLUME_CONFIG.medical_patients
        columns = [
            "patient_code", "medical_record_number", "id_card_encrypted", "name",
            "gender", "birth_date", "phone", "phone_encrypted", "email",
            "address", "city", "province", "postal_code", "emergency_contact_name",
            "emergency_contact_phone", "emergency_contact_relation", "blood_type",
            "allergies", "chronic_conditions", "current_medications", "medical_history",
            "family_history", "insurance_type", "insurance_number", "insurance_company",
            "primary_hospital_id", "primary_doctor_id", "occupation", "marital_status",
            "nationality", "ethnicity", "height_cm", "weight_kg", "smoking_status",
            "drinking_status", "exercise_frequency", "registration_date",
            "last_visit_date", "visit_count", "status", "created_at", "updated_at"
        ]

        blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        allergies_list = ["青霉素", "磺胺类", "头孢", "花粉", "海鲜", "无"]
        chronic_list = ["高血压", "糖尿病", "心脏病", "哮喘", "关节炎", "无"]
        marital_statuses = ["未婚", "已婚", "离异", "丧偶"]
        occupations = ["工人", "农民", "教师", "医生", "工程师", "公务员", "自由职业", "学生", "退休"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                name = self.generate_chinese_name()
                gender = random.choice(["M", "F", "O"])
                birth_year = random.randint(1940, 2020)
                city = random.choice(CHINESE_CITIES)
                province = random.choice(CHINESE_PROVINCES)
                reg_date = self.generate_random_datetime(
                    datetime(2020, 1, 1),
                    datetime(2025, 12, 31)
                ).date()
                visit_count = random.randint(1, 50)
                last_visit = reg_date + timedelta(days=random.randint(0, 365 * 2)) if visit_count > 1 else reg_date

                yield (
                    f"PAT{i + 1:08d}",
                    f"MRN{i + 1:010d}",
                    self.generate_id_card(),
                    name,
                    gender,
                    datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date(),
                    self.generate_phone_number(),
                    f"***{random.randint(1000, 9999)}****",
                    self.generate_email(name) if random.random() > 0.5 else None,
                    self.generate_address(),
                    city,
                    province,
                    f"{random.randint(100000, 999999)}",
                    self.generate_chinese_name(),
                    self.generate_phone_number(),
                    random.choice(["父母", "配偶", "子女", "兄弟姐妹"]),
                    random.choice(blood_types) if random.random() > 0.3 else None,
                    [random.choice(allergies_list)] if random.random() > 0.7 else None,
                    [random.choice(chronic_list)] if random.random() > 0.6 else None,
                    ["阿司匹林"] if random.random() > 0.8 else None,
                    "既往体健" if random.random() > 0.5 else "有高血压病史",
                    "父亲有高血压" if random.random() > 0.7 else "家族史无特殊",
                    random.choice(["医保", "自费", "商业保险"]),
                    f"INS{random.randint(10000000, 99999999)}" if random.random() > 0.3 else None,
                    random.choice(["中国人寿", "平安保险", "太平洋保险"]) if random.random() > 0.5 else None,
                    random.choice(self.hospital_ids) if random.random() > 0.5 else None,
                    random.choice(self.doctor_ids) if random.random() > 0.7 else None,
                    random.choice(occupations),
                    random.choice(marital_statuses),
                    "中国",
                    random.choice(["汉族", "回族", "藏族", "维吾尔族", "苗族"]),
                    round(random.uniform(150, 190), 1),
                    round(random.uniform(45, 100), 1),
                    random.choice(["never", "former", "current"]),
                    random.choice(["never", "occasional", "regular"]),
                    random.choice(["never", "occasional", "regular", "frequent"]),
                    reg_date,
                    last_visit,
                    visit_count,
                    "active",
                    now,
                    now
                )

        self.batch_insert("patients", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM patients"))
            self.patient_ids = [row[0] for row in result]

    def _generate_appointments(self) -> None:
        """Generate appointment data."""
        total = config.DATA_VOLUME_CONFIG.medical_appointments
        columns = [
            "appointment_code", "patient_id", "doctor_id", "department_id",
            "hospital_id", "appointment_type", "appointment_date", "time_slot_start",
            "time_slot_end", "queue_number", "chief_complaint", "symptoms",
            "symptom_duration", "severity", "is_first_visit", "referral_source",
            "registration_fee", "consultation_fee", "total_fee", "payment_status",
            "payment_method", "paid_at", "insurance_claim_id", "insurance_covered_amount",
            "check_in_time", "consultation_start_time", "consultation_end_time",
            "waiting_time_minutes", "consultation_duration_minutes", "no_show",
            "status", "source", "notes", "created_at", "updated_at"
        ]

        appointment_types = ["outpatient", "follow_up", "emergency", "teleconsultation"]
        type_weights = [0.6, 0.25, 0.1, 0.05]
        time_slots = [
            (time(8, 0), time(8, 30)),
            (time(8, 30), time(9, 0)),
            (time(9, 0), time(9, 30)),
            (time(9, 30), time(10, 0)),
            (time(10, 0), time(10, 30)),
            (time(10, 30), time(11, 0)),
            (time(14, 0), time(14, 30)),
            (time(14, 30), time(15, 0)),
            (time(15, 0), time(15, 30)),
            (time(15, 30), time(16, 0)),
        ]
        symptoms_list = ["发热", "咳嗽", "头痛", "腹痛", "乏力", "胸闷", "呼吸困难", "关节痛"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                patient_id = random.choice(self.patient_ids)
                doctor_id = random.choice(self.doctor_ids)
                department_id = random.choice(self.department_ids)
                hospital_id = random.choice(self.hospital_ids)
                apt_type = random.choices(appointment_types, weights=type_weights)[0]
                apt_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                ).date()
                slot = random.choice(time_slots)
                status = random.choices(
                    ["scheduled", "confirmed", "checked_in", "in_progress", "completed", "cancelled", "no_show"],
                    weights=[0.05, 0.1, 0.05, 0.05, 0.65, 0.05, 0.05]
                )[0]
                reg_fee = round(random.uniform(5, 20), 2)
                cons_fee = round(random.uniform(20, 200), 2)
                total_fee = reg_fee + cons_fee

                yield (
                    f"APT{uuid.uuid4().hex[:24].upper()}",
                    patient_id,
                    doctor_id,
                    department_id,
                    hospital_id,
                    apt_type,
                    apt_date,
                    slot[0],
                    slot[1],
                    random.randint(1, 100),
                    random.choice(symptoms_list) + "，" + random.choice(["3天", "1周", "半月", "1月"]),
                    random.sample(symptoms_list, k=random.randint(1, 3)),
                    random.choice(["1天", "3天", "1周", "2周", "1月"]),
                    random.choice(["mild", "moderate", "severe"]),
                    random.random() > 0.3,
                    random.choice(["self", "referral", "emergency"]),
                    reg_fee,
                    cons_fee,
                    total_fee,
                    "paid" if status in ["checked_in", "in_progress", "completed"] else "pending",
                    random.choice(["现金", "医保", "微信", "支付宝", "银行卡"]),
                    datetime.combine(apt_date, slot[0]) - timedelta(hours=random.randint(1, 24)) if status != "pending" else None,
                    f"CLM{random.randint(10000000, 99999999)}" if random.random() > 0.5 else None,
                    round(total_fee * random.uniform(0.5, 0.8), 2) if random.random() > 0.5 else None,
                    datetime.combine(apt_date, slot[0]) - timedelta(minutes=random.randint(5, 30)) if status in ["checked_in", "in_progress", "completed"] else None,
                    datetime.combine(apt_date, slot[0]) if status in ["in_progress", "completed"] else None,
                    datetime.combine(apt_date, slot[1]) if status == "completed" else None,
                    random.randint(5, 60) if status in ["checked_in", "in_progress", "completed"] else None,
                    random.randint(10, 30) if status == "completed" else None,
                    status == "no_show",
                    status,
                    random.choice(["online", "phone", "walk_in"]),
                    None,
                    now,
                    now
                )

        self.batch_insert("appointments", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM appointments WHERE status = 'completed'"))
            self.appointment_ids = [row[0] for row in result]

    def _generate_diagnoses(self) -> None:
        """Generate diagnosis data."""
        total = config.DATA_VOLUME_CONFIG.medical_diagnoses
        columns = [
            "diagnosis_code", "appointment_id", "patient_id", "doctor_id",
            "icd10_code", "icd10_name", "diagnosis_type", "diagnosis_status",
            "severity", "onset_date", "onset_type", "clinical_description",
            "examination_findings", "vital_signs", "physical_exam_notes",
            "differential_diagnosis", "treatment_plan", "follow_up_required",
            "follow_up_date", "follow_up_instructions", "hospitalization_required",
            "admission_recommended", "referral_required", "referral_department",
            "referral_reason", "prognosis", "notes", "created_at", "updated_at"
        ]

        diagnosis_types = ["primary", "secondary", "differential", "final"]
        type_weights = [0.5, 0.3, 0.1, 0.1]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()
            icd_items = list(ICD10_CODES.items())

            for i in range(total):
                if not self.appointment_ids:
                    appointment_id = random.randint(1, config.DATA_VOLUME_CONFIG.medical_appointments)
                else:
                    appointment_id = random.choice(self.appointment_ids)

                patient_id = random.choice(self.patient_ids)
                doctor_id = random.choice(self.doctor_ids)
                icd_code, icd_name = random.choice(icd_items)
                severity = random.choice(["mild", "moderate", "severe", "critical"])
                onset_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                ).date()

                yield (
                    f"DX{uuid.uuid4().hex[:24].upper()}",
                    appointment_id,
                    patient_id,
                    doctor_id,
                    icd_code,
                    icd_name,
                    random.choices(diagnosis_types, weights=type_weights)[0],
                    random.choices(["suspected", "confirmed", "ruled_out"], weights=[0.2, 0.7, 0.1])[0],
                    severity,
                    onset_date - timedelta(days=random.randint(1, 30)),
                    random.choice(["acute", "chronic", "recurrent"]),
                    f"患者主诉{icd_name}相关症状，经检查诊断为{icd_name}",
                    "体格检查未见明显异常" if severity == "mild" else "体格检查发现异常体征",
                    {"blood_pressure": f"{random.randint(90, 140)}/{random.randint(60, 90)}", "heart_rate": random.randint(60, 100), "temperature": round(random.uniform(36.0, 38.5), 1)},
                    "一般情况尚可，神志清楚",
                    [random.choice(list(ICD10_CODES.values()))] if random.random() > 0.7 else None,
                    f"建议{random.choice(['药物治疗', '手术治疗', '保守治疗', '中西医结合治疗'])}",
                    random.random() > 0.3,
                    onset_date + timedelta(days=random.randint(7, 30)) if random.random() > 0.3 else None,
                    "定期复查，如有不适及时就诊",
                    severity == "critical",
                    severity in ["severe", "critical"],
                    random.random() > 0.8,
                    random.choice(MEDICAL_DEPARTMENTS) if random.random() > 0.8 else None,
                    "病情需要专科诊治" if random.random() > 0.8 else None,
                    random.choice(["良好", "一般", "需密切观察"]),
                    None,
                    now,
                    now
                )

        self.batch_insert("diagnoses", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM diagnoses"))
            self.diagnosis_ids = [row[0] for row in result]

    def _generate_prescriptions(self) -> None:
        """Generate prescription data."""
        total = config.DATA_VOLUME_CONFIG.medical_prescriptions
        columns = [
            "prescription_code", "diagnosis_id", "patient_id", "doctor_id",
            "prescription_type", "prescription_date", "valid_days", "expiry_date",
            "total_items", "total_amount", "insurance_amount", "self_pay_amount",
            "payment_status", "paid_at", "dispensing_status", "dispensed_at",
            "dispensed_by", "pharmacy_location", "special_instructions",
            "allergies_checked", "interactions_checked", "warnings",
            "is_narcotic", "is_psychotropic", "is_antibiotic",
            "requires_skin_test", "electronic_signature", "status",
            "created_at", "updated_at"
        ]

        prescription_types = ["outpatient", "inpatient", "discharge", "chronic"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                diagnosis_id = random.choice(self.diagnosis_ids) if self.diagnosis_ids else random.randint(1, total)
                patient_id = random.choice(self.patient_ids)
                doctor_id = random.choice(self.doctor_ids)
                rx_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                ).date()
                total_items = random.randint(1, 8)
                total_amount = round(random.uniform(50, 500), 2)
                insurance_amt = round(total_amount * random.uniform(0.5, 0.8), 2)
                status = random.choices(
                    ["active", "dispensed", "cancelled"],
                    weights=[0.1, 0.85, 0.05]
                )[0]

                yield (
                    f"RX{uuid.uuid4().hex[:24].upper()}",
                    diagnosis_id,
                    patient_id,
                    doctor_id,
                    random.choice(prescription_types),
                    rx_date,
                    random.choice([3, 7, 14, 30]),
                    rx_date + timedelta(days=random.choice([3, 7, 14, 30])),
                    total_items,
                    total_amount,
                    insurance_amt,
                    total_amount - insurance_amt,
                    "paid" if status == "dispensed" else "pending",
                    datetime.combine(rx_date, time(random.randint(9, 17), random.randint(0, 59))) if status == "dispensed" else None,
                    "dispensed" if status == "dispensed" else "pending",
                    datetime.combine(rx_date, time(random.randint(9, 17), random.randint(0, 59))) if status == "dispensed" else None,
                    self.generate_chinese_name() if status == "dispensed" else None,
                    "门诊药房" if status == "dispensed" else None,
                    "按时服药，注意饮食",
                    True,
                    True,
                    ["注意药物相互作用"] if random.random() > 0.8 else None,
                    random.random() < 0.02,
                    random.random() < 0.03,
                    random.random() < 0.3,
                    random.random() < 0.1,
                    f"SIG{uuid.uuid4().hex[:16].upper()}",
                    status,
                    now,
                    now
                )

        self.batch_insert("prescriptions", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM prescriptions"))
            self.prescription_ids = [row[0] for row in result]

    def _generate_prescription_items(self) -> None:
        """Generate prescription item data."""
        total = config.DATA_VOLUME_CONFIG.medical_prescription_items
        columns = [
            "item_code", "prescription_id", "sequence_number", "drug_code",
            "drug_name", "generic_name", "drug_type", "drug_category",
            "specification", "manufacturer", "unit", "dosage", "dosage_unit",
            "frequency", "frequency_code", "administration_route", "duration_days",
            "quantity", "unit_price", "total_price", "insurance_ratio",
            "insurance_covered", "self_pay", "is_covered_by_insurance",
            "skin_test_required", "skin_test_result", "special_instructions",
            "substitution_allowed", "dispensed_quantity", "dispensed_at",
            "batch_number", "expiry_date", "status", "created_at", "updated_at"
        ]

        drugs = [
            {"name": "阿莫西林胶囊", "generic": "阿莫西林", "type": "western", "cat": "antibiotics", "spec": "0.5g*24粒", "unit": "盒", "price": 15.0},
            {"name": "布洛芬缓释胶囊", "generic": "布洛芬", "type": "western", "cat": "analgesics", "spec": "0.3g*20粒", "unit": "盒", "price": 22.0},
            {"name": "氨氯地平片", "generic": "氨氯地平", "type": "western", "cat": "cardiovascular", "spec": "5mg*28片", "unit": "盒", "price": 35.0},
            {"name": "二甲双胍片", "generic": "二甲双胍", "type": "western", "cat": "antidiabetic", "spec": "0.5g*60片", "unit": "盒", "price": 18.0},
            {"name": "奥美拉唑肠溶胶囊", "generic": "奥美拉唑", "type": "western", "cat": "gastrointestinal", "spec": "20mg*14粒", "unit": "盒", "price": 28.0},
            {"name": "感冒灵颗粒", "generic": "感冒灵", "type": "traditional_chinese", "cat": "cold", "spec": "10g*10袋", "unit": "盒", "price": 12.0},
            {"name": "板蓝根颗粒", "generic": "板蓝根", "type": "traditional_chinese", "cat": "antiviral", "spec": "10g*20袋", "unit": "盒", "price": 15.0},
            {"name": "头孢克肟胶囊", "generic": "头孢克肟", "type": "western", "cat": "antibiotics", "spec": "0.1g*12粒", "unit": "盒", "price": 45.0},
        ]
        frequencies = [
            ("每日3次", "tid"),
            ("每日2次", "bid"),
            ("每日1次", "qd"),
            ("每8小时", "q8h"),
            ("睡前", "qn"),
        ]
        routes = ["oral", "injection", "topical", "inhalation"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                prescription_id = random.choice(self.prescription_ids) if self.prescription_ids else random.randint(1, total)
                drug = random.choice(drugs)
                freq = random.choice(frequencies)
                qty = random.randint(1, 5)
                total_price = drug["price"] * qty
                insurance_ratio = round(random.uniform(0.6, 0.9), 2)

                yield (
                    f"RXI{uuid.uuid4().hex[:24].upper()}",
                    prescription_id,
                    random.randint(1, 8),
                    f"DRG{random.randint(10000, 99999)}",
                    drug["name"],
                    drug["generic"],
                    drug["type"],
                    drug["cat"],
                    drug["spec"],
                    random.choice(["华润制药", "石药集团", "恒瑞医药", "扬子江药业", "以岭药业"]),
                    drug["unit"],
                    random.choice(["1粒", "2粒", "1片", "10ml", "1袋"]),
                    random.choice(["粒", "片", "ml", "袋"]),
                    freq[0],
                    freq[1],
                    random.choice(routes),
                    random.choice([3, 7, 14, 30]),
                    qty,
                    drug["price"],
                    total_price,
                    insurance_ratio,
                    round(total_price * insurance_ratio, 2),
                    round(total_price * (1 - insurance_ratio), 2),
                    True,
                    drug["cat"] == "antibiotics" and random.random() < 0.3,
                    "阴性" if drug["cat"] == "antibiotics" and random.random() < 0.3 else None,
                    "饭后服用",
                    True,
                    qty if random.random() > 0.1 else None,
                    now if random.random() > 0.1 else None,
                    f"BN{random.randint(100000, 999999)}" if random.random() > 0.1 else None,
                    (now + timedelta(days=random.randint(180, 730))).date(),
                    random.choices(["pending", "dispensed"], weights=[0.1, 0.9])[0],
                    now,
                    now
                )

        self.batch_insert("prescription_items", columns, data_generator(), total)

    def _generate_lab_tests(self) -> None:
        """Generate lab test data."""
        total = config.DATA_VOLUME_CONFIG.medical_lab_tests
        columns = [
            "test_code", "appointment_id", "patient_id", "ordering_doctor_id",
            "test_category", "test_type", "test_name", "test_items", "urgency",
            "fasting_required", "specimen_type", "specimen_collected",
            "specimen_collected_at", "specimen_collected_by", "specimen_id",
            "lab_department", "lab_technician", "equipment_used",
            "test_started_at", "test_completed_at", "report_generated_at",
            "reporting_doctor_id", "price", "payment_status", "insurance_covered",
            "clinical_indication", "special_instructions", "is_abnormal",
            "critical_values", "critical_notified", "critical_notified_at",
            "critical_notified_to", "status", "notes", "created_at", "updated_at"
        ]

        test_configs = [
            {"category": "blood", "type": "routine", "name": "血常规", "items": ["白细胞", "红细胞", "血红蛋白", "血小板"], "price": 25},
            {"category": "blood", "type": "biochemistry", "name": "肝功能", "items": ["ALT", "AST", "总胆红素", "白蛋白"], "price": 80},
            {"category": "blood", "type": "biochemistry", "name": "肾功能", "items": ["肌酐", "尿素氮", "尿酸"], "price": 60},
            {"category": "blood", "type": "lipid", "name": "血脂", "items": ["总胆固醇", "甘油三酯", "HDL", "LDL"], "price": 50},
            {"category": "urine", "type": "routine", "name": "尿常规", "items": ["蛋白", "糖", "白细胞", "红细胞"], "price": 20},
            {"category": "imaging", "type": "xray", "name": "胸部X光", "items": ["胸部正位片"], "price": 100},
            {"category": "imaging", "type": "ct", "name": "胸部CT", "items": ["胸部平扫"], "price": 350},
            {"category": "imaging", "type": "ultrasound", "name": "腹部B超", "items": ["肝胆脾胰", "双肾"], "price": 150},
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                if not self.appointment_ids:
                    appointment_id = random.randint(1, config.DATA_VOLUME_CONFIG.medical_appointments)
                else:
                    appointment_id = random.choice(self.appointment_ids)

                patient_id = random.choice(self.patient_ids)
                doctor_id = random.choice(self.doctor_ids)
                config = random.choice(test_configs)
                test_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                )
                status = random.choices(
                    ["ordered", "collected", "processing", "completed", "cancelled"],
                    weights=[0.05, 0.05, 0.05, 0.80, 0.05]
                )[0]
                is_abnormal = random.random() < 0.2
                is_critical = is_abnormal and random.random() < 0.1

                yield (
                    f"LAB{uuid.uuid4().hex[:24].upper()}",
                    appointment_id,
                    patient_id,
                    doctor_id,
                    config["category"],
                    config["type"],
                    config["name"],
                    config["items"],
                    random.choice(["routine", "urgent", "stat"]),
                    config["category"] == "blood",
                    config["category"] if config["category"] != "imaging" else None,
                    status in ["collected", "processing", "completed"],
                    test_date if status in ["collected", "processing", "completed"] else None,
                    self.generate_chinese_name() if status in ["collected", "processing", "completed"] else None,
                    f"SP{random.randint(10000000, 99999999)}" if status in ["collected", "processing", "completed"] else None,
                    "检验科" if config["category"] != "imaging" else "放射科",
                    self.generate_chinese_name() if status == "completed" else None,
                    random.choice(["Sysmex", "Roche", "Beckman", "Siemens"]) if status == "completed" else None,
                    test_date + timedelta(minutes=30) if status in ["processing", "completed"] else None,
                    test_date + timedelta(hours=random.randint(1, 4)) if status == "completed" else None,
                    test_date + timedelta(hours=random.randint(2, 6)) if status == "completed" else None,
                    random.choice(self.doctor_ids) if status == "completed" else None,
                    config["price"],
                    "paid" if status in ["collected", "processing", "completed"] else "pending",
                    round(config["price"] * random.uniform(0.6, 0.8), 2),
                    f"诊断{random.choice(list(ICD10_CODES.values()))}",
                    "空腹8小时" if config["category"] == "blood" else None,
                    is_abnormal if status == "completed" else None,
                    is_critical if status == "completed" else None,
                    is_critical if status == "completed" else None,
                    test_date + timedelta(hours=3) if is_critical and status == "completed" else None,
                    self.generate_chinese_name() if is_critical and status == "completed" else None,
                    status,
                    None,
                    now,
                    now
                )

        self.batch_insert("lab_tests", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM lab_tests WHERE status = 'completed'"))
            self.lab_test_ids = [row[0] for row in result]

    def _generate_lab_results(self) -> None:
        """Generate lab result data."""
        total = config.DATA_VOLUME_CONFIG.medical_lab_results
        columns = [
            "result_code", "lab_test_id", "item_code", "item_name",
            "item_abbreviation", "result_value", "result_numeric", "unit",
            "reference_range", "reference_low", "reference_high", "is_abnormal",
            "abnormal_flag", "is_critical", "delta_check", "previous_value",
            "previous_date", "interpretation", "methodology", "instrument",
            "reagent_lot", "quality_control_status", "verified_by", "verified_at",
            "comments", "created_at", "updated_at"
        ]

        result_items = [
            {"name": "白细胞计数", "abbr": "WBC", "unit": "10^9/L", "low": 4.0, "high": 10.0},
            {"name": "红细胞计数", "abbr": "RBC", "unit": "10^12/L", "low": 4.0, "high": 5.5},
            {"name": "血红蛋白", "abbr": "HGB", "unit": "g/L", "low": 120, "high": 160},
            {"name": "血小板计数", "abbr": "PLT", "unit": "10^9/L", "low": 100, "high": 300},
            {"name": "谷丙转氨酶", "abbr": "ALT", "unit": "U/L", "low": 0, "high": 40},
            {"name": "谷草转氨酶", "abbr": "AST", "unit": "U/L", "low": 0, "high": 40},
            {"name": "肌酐", "abbr": "Cr", "unit": "umol/L", "low": 44, "high": 133},
            {"name": "血糖", "abbr": "GLU", "unit": "mmol/L", "low": 3.9, "high": 6.1},
            {"name": "总胆固醇", "abbr": "TC", "unit": "mmol/L", "low": 0, "high": 5.2},
            {"name": "甘油三酯", "abbr": "TG", "unit": "mmol/L", "low": 0, "high": 1.7},
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                lab_test_id = random.choice(self.lab_test_ids) if self.lab_test_ids else random.randint(1, total)
                item = random.choice(result_items)
                value = round(random.uniform(item["low"] * 0.5, item["high"] * 1.5), 2)
                is_abnormal = value < item["low"] or value > item["high"]
                is_critical = is_abnormal and (value < item["low"] * 0.5 or value > item["high"] * 2)

                if is_abnormal:
                    if value < item["low"]:
                        flag = "LL" if is_critical else "L"
                    else:
                        flag = "HH" if is_critical else "H"
                else:
                    flag = None

                yield (
                    f"RES{uuid.uuid4().hex[:24].upper()}",
                    lab_test_id,
                    f"ITM{random.randint(1000, 9999)}",
                    item["name"],
                    item["abbr"],
                    str(value),
                    value,
                    item["unit"],
                    f"{item['low']}-{item['high']}",
                    item["low"],
                    item["high"],
                    is_abnormal,
                    flag,
                    is_critical,
                    random.random() < 0.1,
                    round(random.uniform(item["low"], item["high"]), 2) if random.random() < 0.3 else None,
                    (now - timedelta(days=random.randint(30, 365))).date() if random.random() < 0.3 else None,
                    "结果异常，建议复查" if is_abnormal else "结果正常",
                    random.choice(["化学发光法", "酶联免疫法", "电化学法"]),
                    random.choice(["Sysmex XN-1000", "Roche Cobas 8000", "Beckman AU5800"]),
                    f"LOT{random.randint(100000, 999999)}",
                    "合格",
                    self.generate_chinese_name(),
                    now,
                    None,
                    now,
                    now
                )

        self.batch_insert("lab_results", columns, data_generator(), total)
