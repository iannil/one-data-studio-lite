"""
HR System Data Generator.

Generates production-level test data for the hr_system_db database (MySQL):
- departments (500)
- positions (1,000)
- employees (100,000)
- salary_records (1,200,000)
- attendance (2,400,000)
- performance_reviews (200,000)
- training_records (150,000)
- leave_requests (100,000)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import text

from .base import BaseDataGenerator, create_mysql_database
from .. import config
from ..config import (
    CHINESE_CITIES,
    HR_DB_CONFIG,
    HR_POSITIONS,
)


class HRDataGenerator(BaseDataGenerator):
    """Generator for HR system test data."""

    SCHEMA_FILE = Path(__file__).parent.parent / "schemas" / "hr.sql"

    def __init__(self):
        super().__init__(HR_DB_CONFIG.connection_string)
        self.department_ids: list[int] = []
        self.position_ids: list[int] = []
        self.employee_ids: list[int] = []

    def create_database(self) -> None:
        """Create the hr_system_db database if it doesn't exist."""
        create_mysql_database(
            HR_DB_CONFIG.host,
            HR_DB_CONFIG.port,
            HR_DB_CONFIG.user,
            HR_DB_CONFIG.password,
            HR_DB_CONFIG.database
        )

    def create_schema(self) -> None:
        """Create the hr_system database schema (tables)."""
        # Check if tables already exist - skip if they do
        with self.get_connection() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_schema = '{HR_DB_CONFIG.database}' AND table_name = 'employees'"
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
        """Generate all HR data."""
        self._generate_departments()
        self._generate_positions()
        self._generate_employees()
        self._generate_salary_records()
        self._generate_attendance()
        self._generate_performance_reviews()
        self._generate_training_records()
        self._generate_leave_requests()

    def _generate_departments(self) -> None:
        """Generate department data."""
        total = config.DATA_VOLUME_CONFIG.hr_departments
        columns = [
            "department_code", "name", "parent_id", "level", "path",
            "budget", "headcount_limit", "current_headcount", "cost_center",
            "location", "description", "status", "created_at", "updated_at"
        ]

        dept_names = [
            "技术研发中心", "产品管理部", "设计中心", "数据科学部", "运维工程部",
            "质量保障部", "项目管理办公室", "人力资源部", "财务部", "法务部",
            "市场营销部", "销售部", "客户服务部", "行政管理部", "战略规划部",
            "供应链管理部", "采购部", "仓储物流部", "安全生产部", "企业文化部",
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            level_1_count = min(20, total)
            now = datetime.now()

            for i in range(total):
                if i < level_1_count:
                    level = 1
                    parent_id = None
                    path = f"/{i + 1}/"
                    name = dept_names[i % len(dept_names)]
                else:
                    level = random.choice([2, 3])
                    parent_idx = random.randint(0, min(i - 1, level_1_count - 1))
                    parent_id = parent_idx + 1
                    path = f"/{parent_id}/{i + 1}/"
                    base_name = dept_names[parent_idx % len(dept_names)]
                    name = f"{base_name}-{random.choice(['一', '二', '三', '四', '五'])}组"

                yield (
                    f"DEPT{i + 1:05d}",
                    name,
                    parent_id,
                    level,
                    path,
                    round(random.uniform(100000, 10000000), 2),
                    random.randint(10, 500),
                    0,
                    f"CC{random.randint(1000, 9999)}",
                    random.choice(CHINESE_CITIES),
                    f"{name}负责公司核心业务",
                    random.choices(["active", "inactive"], weights=[0.95, 0.05])[0],
                    now,
                    now
                )

        self.batch_insert("departments", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM departments"))
            self.department_ids = [row[0] for row in result]

    def _generate_positions(self) -> None:
        """Generate position data."""
        total = config.DATA_VOLUME_CONFIG.hr_positions
        columns = [
            "position_code", "name", "department_id", "job_level", "job_family",
            "min_salary", "max_salary", "currency", "requirements",
            "responsibilities", "qualifications", "skills", "headcount",
            "filled_count", "is_remote_eligible", "status", "created_at", "updated_at"
        ]

        job_families = ["Engineering", "Product", "Design", "Data", "Operations", "HR", "Finance", "Sales", "Marketing"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            base_positions = HR_POSITIONS * (total // len(HR_POSITIONS) + 1)
            now = datetime.now()

            for i in range(total):
                pos = base_positions[i]
                dept_id = random.choice(self.department_ids)
                level = pos["level"]
                min_sal = random.randint(8000, 30000) if level.startswith("P") else random.randint(30000, 100000)
                max_sal = int(min_sal * random.uniform(1.3, 2.0))

                yield (
                    f"POS{i + 1:06d}",
                    f"{pos['name']} {random.choice(['I', 'II', 'III', ''])}".strip(),
                    dept_id,
                    level,
                    random.choice(job_families),
                    min_sal,
                    max_sal,
                    "CNY",
                    "本科及以上学历，相关工作经验",
                    f"负责{pos['department']}相关工作",
                    "良好的沟通能力和团队协作精神",
                    ["Python", "SQL", "Excel"] if "工程师" in pos["name"] else ["Office", "Communication"],
                    random.randint(1, 20),
                    0,
                    random.random() > 0.6,
                    random.choices(["active", "inactive"], weights=[0.9, 0.1])[0],
                    now,
                    now
                )

        self.batch_insert("positions", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM positions"))
            self.position_ids = [row[0] for row in result]

    def _generate_employees(self) -> None:
        """Generate employee data."""
        total = config.DATA_VOLUME_CONFIG.hr_employees
        columns = [
            "employee_id", "name", "english_name", "id_card_encrypted", "gender",
            "birth_date", "phone", "email", "personal_email", "address", "city",
            "province", "emergency_contact_name", "emergency_contact_phone",
            "emergency_contact_relation", "position_id", "department_id",
            "manager_id", "hire_date", "probation_end_date", "contract_start_date",
            "contract_end_date", "contract_type", "work_location", "work_type",
            "education_level", "education_major", "education_school",
            "years_of_experience", "previous_company", "bank_name",
            "bank_account_encrypted", "tax_id_encrypted", "social_insurance_id",
            "housing_fund_id", "annual_leave_days", "used_leave_days",
            "sick_leave_days", "used_sick_days", "photo_url", "status",
            "resignation_date", "resignation_reason", "last_working_date",
            "created_at", "updated_at"
        ]

        contract_types = ["permanent", "fixed_term", "contractor", "intern"]
        education_levels = ["high_school", "bachelor", "master", "phd"]
        majors = ["计算机科学", "软件工程", "电子工程", "工商管理", "会计学", "市场营销", "人力资源", "法学"]
        schools = ["清华大学", "北京大学", "浙江大学", "上海交通大学", "复旦大学", "中山大学", "武汉大学", "南京大学"]
        companies = ["阿里巴巴", "腾讯", "百度", "字节跳动", "美团", "京东", "华为", "小米"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                name = self.generate_chinese_name()
                gender = random.choice(["M", "F"])
                birth_year = random.randint(1970, 2002)
                hire_date = self.generate_random_datetime(
                    datetime(2015, 1, 1),
                    datetime(2025, 12, 31)
                ).date()
                status = random.choices(
                    ["active", "on_leave", "resigned", "terminated"],
                    weights=[0.85, 0.05, 0.08, 0.02]
                )[0]
                resignation_date = hire_date + timedelta(days=random.randint(180, 2000)) if status == "resigned" else None
                manager_id = random.randint(1, max(1, i)) if i > 100 else None

                yield (
                    f"EMP{i + 1:08d}",
                    name,
                    self._name_to_pinyin(name).upper(),
                    self.generate_id_card(),
                    gender,
                    datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date(),
                    self.generate_phone_number(),
                    f"emp{i + 1}@company.com",
                    self.generate_email(name),
                    self.generate_address(),
                    random.choice(CHINESE_CITIES),
                    random.choice(["北京市", "上海市", "广东省", "浙江省", "江苏省"]),
                    self.generate_chinese_name(),
                    self.generate_phone_number(),
                    random.choice(["父母", "配偶", "兄弟姐妹"]),
                    random.choice(self.position_ids),
                    random.choice(self.department_ids),
                    manager_id,
                    hire_date,
                    hire_date + timedelta(days=90),
                    hire_date,
                    hire_date + timedelta(days=random.choice([365, 730, 1095])),
                    random.choice(contract_types),
                    random.choice(CHINESE_CITIES),
                    random.choice(["onsite", "remote", "hybrid"]),
                    random.choice(education_levels),
                    random.choice(majors),
                    random.choice(schools),
                    random.randint(0, 20),
                    random.choice(companies) if random.random() > 0.3 else None,
                    random.choice(["中国工商银行", "中国建设银行", "招商银行", "中国银行"]),
                    self.generate_bank_card(),
                    f"TAX***{random.randint(1000, 9999)}",
                    f"SI{random.randint(10000000, 99999999)}",
                    f"HF{random.randint(10000000, 99999999)}",
                    random.randint(5, 20),
                    round(random.uniform(0, 10), 1),
                    random.randint(5, 15),
                    round(random.uniform(0, 5), 1),
                    None,
                    status,
                    resignation_date,
                    "个人原因" if status == "resigned" else None,
                    resignation_date + timedelta(days=30) if resignation_date else None,
                    now,
                    now
                )

        self.batch_insert("employees", columns, data_generator(), total)

        with self.get_connection() as conn:
            result = conn.execute(text("SELECT id FROM employees"))
            self.employee_ids = [row[0] for row in result]

    def _generate_salary_records(self) -> None:
        """Generate salary record data."""
        total = config.DATA_VOLUME_CONFIG.hr_salary_records
        columns = [
            "record_id", "employee_id", "pay_period_start", "pay_period_end",
            "pay_date", "base_salary", "position_allowance", "housing_allowance",
            "transportation_allowance", "meal_allowance", "communication_allowance",
            "overtime_pay", "overtime_hours", "bonus", "bonus_type", "commission",
            "other_income", "gross_salary", "social_insurance_employee",
            "housing_fund_employee", "income_tax", "other_deductions",
            "deduction_notes", "total_deductions", "net_salary",
            "social_insurance_company", "housing_fund_company", "total_company_cost",
            "currency", "payment_method", "payment_status", "paid_at",
            "approved_by", "approved_at", "notes", "created_at", "updated_at"
        ]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                employee_id = random.choice(self.employee_ids)
                year = random.randint(2023, 2025)
                month = random.randint(1, 12)
                period_start = datetime(year, month, 1).date()
                period_end = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                period_end = period_end.date()
                pay_date = period_end + timedelta(days=random.randint(5, 10))

                base = round(random.uniform(8000, 50000), 2)
                pos_allow = round(base * random.uniform(0.1, 0.3), 2)
                housing = round(random.uniform(1000, 3000), 2)
                transport = round(random.uniform(200, 800), 2)
                meal = round(random.uniform(300, 600), 2)
                comm = round(random.uniform(100, 300), 2)
                overtime_hrs = round(random.uniform(0, 40), 2)
                overtime = round(overtime_hrs * base / 174 * 1.5, 2)
                bonus = round(random.uniform(0, 10000), 2) if random.random() > 0.8 else 0
                commission = round(random.uniform(0, 5000), 2) if random.random() > 0.9 else 0
                other_income = round(random.uniform(0, 1000), 2) if random.random() > 0.95 else 0

                gross = base + pos_allow + housing + transport + meal + comm + overtime + bonus + commission + other_income

                si_emp = round(gross * 0.105, 2)
                hf_emp = round(gross * 0.07, 2)
                taxable = gross - si_emp - hf_emp - 5000
                tax = max(0, round(taxable * 0.1, 2)) if taxable > 0 else 0
                other_ded = round(random.uniform(0, 200), 2) if random.random() > 0.9 else 0

                total_ded = si_emp + hf_emp + tax + other_ded
                net = gross - total_ded

                si_comp = round(gross * 0.28, 2)
                hf_comp = round(gross * 0.07, 2)
                total_comp = gross + si_comp + hf_comp

                yield (
                    f"SAL{uuid.uuid4().hex[:24].upper()}",
                    employee_id,
                    period_start,
                    period_end,
                    pay_date,
                    base,
                    pos_allow,
                    housing,
                    transport,
                    meal,
                    comm,
                    overtime,
                    overtime_hrs,
                    bonus,
                    "performance" if bonus > 0 else None,
                    commission,
                    other_income,
                    gross,
                    si_emp,
                    hf_emp,
                    tax,
                    other_ded,
                    "其他扣款" if other_ded > 0 else None,
                    total_ded,
                    net,
                    si_comp,
                    hf_comp,
                    total_comp,
                    "CNY",
                    "bank_transfer",
                    random.choices(["paid", "pending"], weights=[0.95, 0.05])[0],
                    datetime.combine(pay_date, time(10, 0)) if random.random() > 0.05 else None,
                    random.randint(1, 50),
                    datetime.combine(pay_date - timedelta(days=2), time(16, 0)),
                    None,
                    now,
                    now
                )

        self.batch_insert("salary_records", columns, data_generator(), total)

    def _generate_attendance(self) -> None:
        """Generate attendance data."""
        total = config.DATA_VOLUME_CONFIG.hr_attendance
        columns = [
            "attendance_id", "employee_id", "attendance_date", "check_in_time",
            "check_out_time", "check_in_location", "check_out_location",
            "check_in_device", "check_out_device", "check_in_method",
            "check_out_method", "scheduled_start", "scheduled_end", "work_hours",
            "overtime_hours", "is_late", "late_minutes", "is_early_leave",
            "early_leave_minutes", "is_absent", "absence_type", "leave_request_id",
            "is_business_trip", "business_trip_location", "is_work_from_home",
            "status", "exception_reason", "approved_by", "approved_at", "notes",
            "created_at", "updated_at"
        ]

        check_methods = ["card", "face", "fingerprint", "mobile"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()
            # Calculate records per employee to ensure uniqueness
            records_per_employee = total // len(self.employee_ids) + 1

            record_count = 0
            for employee_id in self.employee_ids:
                if record_count >= total:
                    return

                # Generate unique dates for this employee
                base_date = datetime(2024, 1, 1)
                for day_offset in range(records_per_employee):
                    if record_count >= total:
                        return

                    att_date = (base_date + timedelta(days=day_offset)).date()

                    scheduled_start = time(9, 0)
                    scheduled_end = time(18, 0)

                    is_absent = random.random() < 0.02
                    is_wfh = random.random() < 0.15 if not is_absent else False
                    is_trip = random.random() < 0.05 if not is_absent and not is_wfh else False

                    if is_absent:
                        check_in = None
                        check_out = None
                        work_hours = 0
                        is_late = False
                        late_mins = 0
                        is_early = False
                        early_mins = 0
                    else:
                        late_mins = random.randint(0, 60) if random.random() < 0.1 else 0
                        early_mins = random.randint(0, 30) if random.random() < 0.05 else 0
                        check_in = datetime.combine(att_date, time(9, late_mins // 60, late_mins % 60))
                        check_out = datetime.combine(att_date, time(18 - early_mins // 60, 60 - early_mins % 60 if early_mins else 0))
                        if check_out.minute >= 60:
                            check_out = check_out.replace(minute=0, hour=check_out.hour + 1)
                        work_hours = round((check_out - check_in).seconds / 3600, 2)
                        is_late = late_mins > 0
                        is_early = early_mins > 0

                    overtime = round(random.uniform(0, 4), 2) if random.random() < 0.2 else 0

                    yield (
                        f"ATT{uuid.uuid4().hex[:24].upper()}",
                        employee_id,
                        att_date,
                        check_in,
                        check_out,
                        random.choice(CHINESE_CITIES) + "办公室" if check_in else None,
                        random.choice(CHINESE_CITIES) + "办公室" if check_out else None,
                        f"Device-{random.randint(1, 100)}" if check_in else None,
                        f"Device-{random.randint(1, 100)}" if check_out else None,
                        random.choice(check_methods) if check_in else None,
                        random.choice(check_methods) if check_out else None,
                        scheduled_start,
                        scheduled_end,
                        work_hours,
                        overtime,
                        is_late,
                        late_mins,
                        is_early,
                        early_mins,
                        is_absent,
                        random.choice(["sick", "personal", "annual"]) if is_absent else None,
                        None,
                        is_trip,
                        random.choice(CHINESE_CITIES) if is_trip else None,
                        is_wfh,
                        "normal" if not is_absent and not is_late and not is_early else "abnormal",
                        "迟到" if is_late else ("早退" if is_early else ("缺勤" if is_absent else None)),
                        random.randint(1, 100) if is_absent or is_late else None,
                        now if is_absent or is_late else None,
                        None,
                        now,
                        now
                    )
                    record_count += 1

        self.batch_insert("attendance", columns, data_generator(), total)

    def _generate_performance_reviews(self) -> None:
        """Generate performance review data."""
        total = config.DATA_VOLUME_CONFIG.hr_performance_reviews
        columns = [
            "review_id", "employee_id", "reviewer_id", "review_period_start",
            "review_period_end", "review_type", "overall_rating", "rating_level",
            "goals_achievement", "kpi_scores", "competency_scores", "strengths",
            "areas_for_improvement", "achievements", "development_plan",
            "training_recommendations", "career_aspirations", "manager_comments",
            "employee_comments", "hr_comments", "salary_increase_recommended",
            "salary_increase_percentage", "promotion_recommended",
            "recommended_position", "bonus_recommended", "recommended_bonus",
            "pip_required", "pip_details", "next_review_date",
            "employee_acknowledged", "employee_acknowledged_at", "status",
            "submitted_at", "reviewed_at", "approved_by", "approved_at",
            "created_at", "updated_at"
        ]

        review_types = ["quarterly", "semi_annual", "annual", "probation"]
        rating_levels = {
            (4.5, 5.1): "exceeds",
            (3.5, 4.5): "meets",
            (2.5, 3.5): "needs_improvement",
            (1.0, 2.5): "unsatisfactory"
        }

        def get_rating_level(rating: float) -> str:
            for (low, high), level in rating_levels.items():
                if low <= rating < high:
                    return level
            return "meets"

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                employee_id = random.choice(self.employee_ids)
                reviewer_id = random.choice(self.employee_ids)
                while reviewer_id == employee_id:
                    reviewer_id = random.choice(self.employee_ids)

                review_type = random.choice(review_types)
                year = random.randint(2023, 2025)
                quarter = random.randint(1, 4)
                period_start = datetime(year, (quarter - 1) * 3 + 1, 1).date()
                period_end = (datetime(year, quarter * 3, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                period_end = period_end.date()

                rating = round(random.uniform(2.5, 5.0), 2)
                status = random.choices(
                    ["draft", "submitted", "reviewed", "approved", "completed"],
                    weights=[0.05, 0.1, 0.15, 0.2, 0.5]
                )[0]

                yield (
                    f"REV{uuid.uuid4().hex[:24].upper()}",
                    employee_id,
                    reviewer_id,
                    period_start,
                    period_end,
                    review_type,
                    rating,
                    get_rating_level(rating),
                    round(random.uniform(60, 100), 2),
                    {"delivery": round(random.uniform(3, 5), 1), "quality": round(random.uniform(3, 5), 1)},
                    {"teamwork": round(random.uniform(3, 5), 1), "communication": round(random.uniform(3, 5), 1)},
                    "工作认真负责，团队协作能力强",
                    "需要提升项目管理能力",
                    "完成了多个重要项目",
                    "参加管理培训课程",
                    "推荐参加领导力培训",
                    "希望在技术方向深入发展",
                    "表现优秀，建议给予晋升机会",
                    "认可评价，将努力改进",
                    "建议加强职业规划指导",
                    rating >= 4.0,
                    round(random.uniform(5, 15), 2) if rating >= 4.0 else None,
                    rating >= 4.5,
                    "高级工程师" if rating >= 4.5 else None,
                    rating >= 3.5,
                    round(random.uniform(5000, 50000), 2) if rating >= 3.5 else None,
                    rating < 2.5,
                    "需要制定绩效改进计划" if rating < 2.5 else None,
                    (period_end + timedelta(days=90)),
                    status in ["approved", "completed"],
                    now if status in ["approved", "completed"] else None,
                    status,
                    now if status != "draft" else None,
                    now if status in ["reviewed", "approved", "completed"] else None,
                    random.randint(1, 50) if status in ["approved", "completed"] else None,
                    now if status in ["approved", "completed"] else None,
                    now,
                    now
                )

        self.batch_insert("performance_reviews", columns, data_generator(), total)

    def _generate_training_records(self) -> None:
        """Generate training record data."""
        total = config.DATA_VOLUME_CONFIG.hr_training_records
        columns = [
            "record_id", "employee_id", "training_name", "training_type",
            "training_category", "training_provider", "instructor_name",
            "training_location", "is_online", "training_url", "start_date",
            "end_date", "duration_hours", "scheduled_hours", "actual_hours",
            "attendance_rate", "pre_assessment_score", "post_assessment_score",
            "certification_name", "certification_id", "certification_date",
            "certification_expiry", "cost", "cost_center", "reimbursed",
            "feedback_rating", "feedback_comments", "skills_acquired", "status",
            "completion_date", "notes", "created_at", "updated_at"
        ]

        training_types = ["onboarding", "technical", "soft_skills", "compliance", "leadership"]
        training_names = [
            "新员工入职培训", "Python高级编程", "项目管理实战", "沟通技巧提升",
            "信息安全意识", "领导力发展", "数据分析入门", "敏捷开发实践",
            "产品思维训练", "职业素养提升", "团队协作工作坊", "创新思维培训"
        ]
        providers = ["内部培训", "外部机构", "在线平台", "高校合作"]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                employee_id = random.choice(self.employee_ids)
                training_type = random.choice(training_types)
                is_online = random.random() > 0.6
                start_date = self.generate_random_datetime(
                    datetime(2023, 1, 1),
                    datetime(2025, 12, 31)
                ).date()
                duration = random.randint(4, 40)
                status = random.choices(
                    ["scheduled", "in_progress", "completed", "cancelled"],
                    weights=[0.1, 0.1, 0.75, 0.05]
                )[0]

                yield (
                    f"TRN{uuid.uuid4().hex[:24].upper()}",
                    employee_id,
                    random.choice(training_names),
                    training_type,
                    training_type,
                    random.choice(providers),
                    self.generate_chinese_name(),
                    "线上" if is_online else random.choice(CHINESE_CITIES) + "培训中心",
                    is_online,
                    "https://training.company.com/course/" + uuid.uuid4().hex[:8] if is_online else None,
                    start_date,
                    start_date + timedelta(days=random.randint(1, 5)),
                    duration,
                    duration,
                    round(duration * random.uniform(0.8, 1.0), 2) if status == "completed" else None,
                    round(random.uniform(80, 100), 2) if status == "completed" else None,
                    round(random.uniform(60, 100), 2) if status == "completed" else None,
                    round(random.uniform(70, 100), 2) if status == "completed" else None,
                    "结业证书" if status == "completed" and random.random() > 0.5 else None,
                    f"CERT{random.randint(10000, 99999)}" if status == "completed" and random.random() > 0.5 else None,
                    start_date + timedelta(days=random.randint(5, 30)) if status == "completed" else None,
                    start_date + timedelta(days=365 * 2) if status == "completed" else None,
                    round(random.uniform(500, 10000), 2),
                    f"CC{random.randint(1000, 9999)}",
                    status == "completed",
                    round(random.uniform(3.5, 5.0), 2) if status == "completed" else None,
                    "培训内容丰富，收获很大" if status == "completed" else None,
                    ["Python", "数据分析"] if status == "completed" else None,
                    status,
                    start_date + timedelta(days=random.randint(1, 10)) if status == "completed" else None,
                    None,
                    now,
                    now
                )

        self.batch_insert("training_records", columns, data_generator(), total)

    def _generate_leave_requests(self) -> None:
        """Generate leave request data."""
        total = config.DATA_VOLUME_CONFIG.hr_leave_requests
        columns = [
            "request_id", "employee_id", "leave_type", "start_date", "end_date",
            "start_half_day", "end_half_day", "total_days", "reason",
            "attachment_urls", "medical_certificate", "delegate_to",
            "delegate_tasks", "balance_before", "balance_after", "approver_id",
            "approval_level", "status", "rejection_reason", "submitted_at",
            "approved_at", "actual_return_date", "return_notes", "created_at",
            "updated_at"
        ]

        leave_types = ["annual", "sick", "personal", "maternity", "paternity", "bereavement", "marriage", "unpaid"]
        leave_weights = [0.4, 0.25, 0.15, 0.05, 0.05, 0.03, 0.02, 0.05]

        def data_generator() -> Iterator[tuple[Any, ...]]:
            now = datetime.now()

            for i in range(total):
                employee_id = random.choice(self.employee_ids)
                leave_type = random.choices(leave_types, weights=leave_weights)[0]
                start_date = self.generate_random_datetime(
                    datetime(2024, 1, 1),
                    datetime(2026, 2, 18)
                ).date()
                total_days = round(random.uniform(0.5, 15), 1)
                end_date = start_date + timedelta(days=int(total_days))
                status = random.choices(
                    ["pending", "approved", "rejected", "cancelled"],
                    weights=[0.1, 0.75, 0.1, 0.05]
                )[0]

                yield (
                    f"LV{uuid.uuid4().hex[:24].upper()}",
                    employee_id,
                    leave_type,
                    start_date,
                    end_date,
                    random.choice(["morning", "afternoon"]) if total_days < 1 else None,
                    random.choice(["morning", "afternoon"]) if total_days < 1 else None,
                    total_days,
                    f"因{random.choice(['个人事务', '身体不适', '家庭原因', '旅行计划'])}需要请假",
                    None,
                    leave_type == "sick" and random.random() > 0.5,
                    random.choice(self.employee_ids) if random.random() > 0.7 else None,
                    "工作已交接" if random.random() > 0.7 else None,
                    round(random.uniform(5, 15), 1),
                    round(random.uniform(0, 10), 1),
                    random.choice(self.employee_ids) if status in ["approved", "rejected"] else None,
                    1,
                    status,
                    "人员紧张，请调整时间" if status == "rejected" else None,
                    now,
                    now if status in ["approved", "rejected"] else None,
                    end_date + timedelta(days=1) if status == "approved" and random.random() > 0.9 else None,
                    "准时返岗" if status == "approved" else None,
                    now,
                    now
                )

        self.batch_insert("leave_requests", columns, data_generator(), total)
