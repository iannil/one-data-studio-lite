-- HR System Schema (MySQL)
-- Database: hr_system_db
-- Data Volume: ~3M records total

-- Note: Database creation is handled by the generator
-- This script assumes the database already exists

USE hr_system_db;

-- Disable foreign key checks for table drops
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. Departments Table (500 records)
-- Self-referencing for hierarchical structure
-- ============================================
DROP TABLE IF EXISTS leave_requests;
DROP TABLE IF EXISTS training_records;
DROP TABLE IF EXISTS performance_reviews;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS salary_records;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS positions;
DROP TABLE IF EXISTS departments;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE departments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    department_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    parent_id BIGINT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    path VARCHAR(500),  -- e.g., '/1/5/23/' for hierarchical queries
    manager_id BIGINT NULL,
    budget DECIMAL(18, 2),
    headcount_limit INTEGER,
    current_headcount INTEGER NOT NULL DEFAULT 0,
    cost_center VARCHAR(32),
    location VARCHAR(100),
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE SET NULL,
    INDEX idx_departments_parent_id (parent_id),
    INDEX idx_departments_path (path),
    INDEX idx_departments_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 2. Positions Table (1,000 records)
-- ============================================
CREATE TABLE positions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    position_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    department_id BIGINT NOT NULL,
    job_level VARCHAR(10) NOT NULL,  -- P1-P10 (Individual Contributor), M1-M5 (Manager)
    job_family VARCHAR(50),  -- Engineering, Product, Design, Operations, etc.
    min_salary DECIMAL(12, 2),
    max_salary DECIMAL(12, 2),
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    requirements TEXT,
    responsibilities TEXT,
    qualifications TEXT,
    skills JSON,
    headcount INTEGER NOT NULL DEFAULT 1,
    filled_count INTEGER NOT NULL DEFAULT 0,
    is_remote_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    INDEX idx_positions_department_id (department_id),
    INDEX idx_positions_job_level (job_level),
    INDEX idx_positions_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 3. Employees Table (100,000 records)
-- ============================================
CREATE TABLE employees (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    english_name VARCHAR(100),
    id_card_encrypted VARCHAR(64) NOT NULL,  -- Masked for privacy
    gender ENUM('M', 'F', 'O') NOT NULL,
    birth_date DATE,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    personal_email VARCHAR(100),
    address TEXT,
    city VARCHAR(50),
    province VARCHAR(50),
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(50),
    position_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    manager_id BIGINT NULL,
    hire_date DATE NOT NULL,
    probation_end_date DATE,
    contract_start_date DATE,
    contract_end_date DATE,
    contract_type VARCHAR(30),  -- permanent, fixed_term, contractor, intern
    work_location VARCHAR(100),
    work_type ENUM('onsite', 'remote', 'hybrid') NOT NULL DEFAULT 'onsite',
    education_level VARCHAR(30),  -- high_school, bachelor, master, phd
    education_major VARCHAR(100),
    education_school VARCHAR(100),
    years_of_experience INTEGER,
    previous_company VARCHAR(100),
    bank_name VARCHAR(100),
    bank_account_encrypted VARCHAR(64),  -- Masked for privacy
    tax_id_encrypted VARCHAR(64),  -- Masked for privacy
    social_insurance_id VARCHAR(64),
    housing_fund_id VARCHAR(64),
    annual_leave_days INTEGER NOT NULL DEFAULT 10,
    used_leave_days DECIMAL(4, 1) NOT NULL DEFAULT 0,
    sick_leave_days INTEGER NOT NULL DEFAULT 10,
    used_sick_days DECIMAL(4, 1) NOT NULL DEFAULT 0,
    photo_url VARCHAR(500),
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, on_leave, resigned, terminated
    resignation_date DATE,
    resignation_reason TEXT,
    last_working_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL,
    INDEX idx_employees_department_id (department_id),
    INDEX idx_employees_position_id (position_id),
    INDEX idx_employees_manager_id (manager_id),
    INDEX idx_employees_hire_date (hire_date),
    INDEX idx_employees_status (status)
) ENGINE=InnoDB;

-- Add manager_id foreign key to departments after employees table exists
ALTER TABLE departments
    ADD FOREIGN KEY (manager_id) REFERENCES employees(id) ON DELETE SET NULL;

-- ============================================
-- 4. Salary Records Table (1,200,000 records)
-- Monthly salary records
-- ============================================
CREATE TABLE salary_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    record_id VARCHAR(64) NOT NULL UNIQUE,
    employee_id BIGINT NOT NULL,
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    pay_date DATE NOT NULL,
    base_salary DECIMAL(12, 2) NOT NULL,
    position_allowance DECIMAL(12, 2) DEFAULT 0,
    housing_allowance DECIMAL(12, 2) DEFAULT 0,
    transportation_allowance DECIMAL(12, 2) DEFAULT 0,
    meal_allowance DECIMAL(12, 2) DEFAULT 0,
    communication_allowance DECIMAL(12, 2) DEFAULT 0,
    overtime_pay DECIMAL(12, 2) DEFAULT 0,
    overtime_hours DECIMAL(6, 2) DEFAULT 0,
    bonus DECIMAL(12, 2) DEFAULT 0,
    bonus_type VARCHAR(50),  -- performance, annual, project, referral
    commission DECIMAL(12, 2) DEFAULT 0,
    other_income DECIMAL(12, 2) DEFAULT 0,
    gross_salary DECIMAL(12, 2) NOT NULL,
    social_insurance_employee DECIMAL(12, 2) DEFAULT 0,
    housing_fund_employee DECIMAL(12, 2) DEFAULT 0,
    income_tax DECIMAL(12, 2) DEFAULT 0,
    other_deductions DECIMAL(12, 2) DEFAULT 0,
    deduction_notes TEXT,
    total_deductions DECIMAL(12, 2) NOT NULL,
    net_salary DECIMAL(12, 2) NOT NULL,
    social_insurance_company DECIMAL(12, 2) DEFAULT 0,
    housing_fund_company DECIMAL(12, 2) DEFAULT 0,
    total_company_cost DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'CNY',
    payment_method VARCHAR(30) DEFAULT 'bank_transfer',
    payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    paid_at TIMESTAMP NULL,
    approved_by BIGINT,
    approved_at TIMESTAMP NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    INDEX idx_salary_employee_id (employee_id),
    INDEX idx_salary_pay_period (pay_period_start, pay_period_end),
    INDEX idx_salary_pay_date (pay_date),
    INDEX idx_salary_payment_status (payment_status)
) ENGINE=InnoDB;

-- ============================================
-- 5. Attendance Records Table (2,400,000 records)
-- Daily attendance with check-in/out times
-- ============================================
CREATE TABLE attendance (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    attendance_id VARCHAR(64) NOT NULL UNIQUE,
    employee_id BIGINT NOT NULL,
    attendance_date DATE NOT NULL,
    check_in_time TIMESTAMP NULL,
    check_out_time TIMESTAMP NULL,
    check_in_location VARCHAR(200),
    check_out_location VARCHAR(200),
    check_in_device VARCHAR(50),
    check_out_device VARCHAR(50),
    check_in_method VARCHAR(30),  -- card, face, fingerprint, mobile, manual
    check_out_method VARCHAR(30),
    scheduled_start TIME,
    scheduled_end TIME,
    work_hours DECIMAL(5, 2),
    overtime_hours DECIMAL(5, 2) DEFAULT 0,
    is_late BOOLEAN NOT NULL DEFAULT FALSE,
    late_minutes INTEGER DEFAULT 0,
    is_early_leave BOOLEAN NOT NULL DEFAULT FALSE,
    early_leave_minutes INTEGER DEFAULT 0,
    is_absent BOOLEAN NOT NULL DEFAULT FALSE,
    absence_type VARCHAR(30),  -- sick, personal, annual, maternity, bereavement
    leave_request_id BIGINT,
    is_business_trip BOOLEAN NOT NULL DEFAULT FALSE,
    business_trip_location VARCHAR(200),
    is_work_from_home BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'normal',  -- normal, abnormal, pending, approved
    exception_reason TEXT,
    approved_by BIGINT,
    approved_at TIMESTAMP NULL,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    UNIQUE KEY uk_employee_date (employee_id, attendance_date),
    INDEX idx_attendance_date (attendance_date),
    INDEX idx_attendance_status (status),
    INDEX idx_attendance_is_late (is_late),
    INDEX idx_attendance_is_absent (is_absent)
) ENGINE=InnoDB;

-- ============================================
-- 6. Performance Reviews Table (200,000 records)
-- Quarterly/Annual performance evaluations
-- ============================================
CREATE TABLE performance_reviews (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    review_id VARCHAR(64) NOT NULL UNIQUE,
    employee_id BIGINT NOT NULL,
    reviewer_id BIGINT NOT NULL,
    review_period_start DATE NOT NULL,
    review_period_end DATE NOT NULL,
    review_type VARCHAR(30) NOT NULL,  -- quarterly, semi_annual, annual, probation, project
    overall_rating DECIMAL(3, 2) NOT NULL CHECK (overall_rating BETWEEN 1 AND 5),
    rating_level VARCHAR(20) NOT NULL,  -- exceeds, meets, needs_improvement, unsatisfactory
    goals_achievement DECIMAL(5, 2),  -- percentage
    kpi_scores JSON,  -- { "kpi_name": score, ... }
    competency_scores JSON,  -- { "competency": score, ... }
    strengths TEXT,
    areas_for_improvement TEXT,
    achievements TEXT,
    development_plan TEXT,
    training_recommendations TEXT,
    career_aspirations TEXT,
    manager_comments TEXT,
    employee_comments TEXT,
    hr_comments TEXT,
    salary_increase_recommended BOOLEAN DEFAULT FALSE,
    salary_increase_percentage DECIMAL(5, 2),
    promotion_recommended BOOLEAN DEFAULT FALSE,
    recommended_position VARCHAR(100),
    bonus_recommended BOOLEAN DEFAULT FALSE,
    recommended_bonus DECIMAL(12, 2),
    pip_required BOOLEAN DEFAULT FALSE,  -- Performance Improvement Plan
    pip_details TEXT,
    next_review_date DATE,
    employee_acknowledged BOOLEAN DEFAULT FALSE,
    employee_acknowledged_at TIMESTAMP NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft, submitted, reviewed, approved, completed
    submitted_at TIMESTAMP NULL,
    reviewed_at TIMESTAMP NULL,
    approved_by BIGINT,
    approved_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY (reviewer_id) REFERENCES employees(id) ON DELETE RESTRICT,
    INDEX idx_performance_employee_id (employee_id),
    INDEX idx_performance_reviewer_id (reviewer_id),
    INDEX idx_performance_review_period (review_period_start, review_period_end),
    INDEX idx_performance_status (status),
    INDEX idx_performance_rating (overall_rating)
) ENGINE=InnoDB;

-- ============================================
-- 7. Training Records Table (150,000 records)
-- ============================================
CREATE TABLE training_records (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    record_id VARCHAR(64) NOT NULL UNIQUE,
    employee_id BIGINT NOT NULL,
    training_name VARCHAR(200) NOT NULL,
    training_type VARCHAR(50) NOT NULL,  -- onboarding, technical, soft_skills, compliance, leadership
    training_category VARCHAR(50),
    training_provider VARCHAR(100),
    instructor_name VARCHAR(100),
    training_location VARCHAR(200),
    is_online BOOLEAN NOT NULL DEFAULT FALSE,
    training_url VARCHAR(500),
    start_date DATE NOT NULL,
    end_date DATE,
    duration_hours DECIMAL(6, 2),
    scheduled_hours DECIMAL(6, 2),
    actual_hours DECIMAL(6, 2),
    attendance_rate DECIMAL(5, 2),
    pre_assessment_score DECIMAL(5, 2),
    post_assessment_score DECIMAL(5, 2),
    certification_name VARCHAR(200),
    certification_id VARCHAR(100),
    certification_date DATE,
    certification_expiry DATE,
    cost DECIMAL(12, 2),
    cost_center VARCHAR(32),
    reimbursed BOOLEAN DEFAULT FALSE,
    feedback_rating DECIMAL(3, 2) CHECK (feedback_rating BETWEEN 1 AND 5),
    feedback_comments TEXT,
    skills_acquired JSON,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- scheduled, in_progress, completed, cancelled
    completion_date DATE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    INDEX idx_training_employee_id (employee_id),
    INDEX idx_training_type (training_type),
    INDEX idx_training_start_date (start_date),
    INDEX idx_training_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 8. Leave Requests Table (100,000 records)
-- ============================================
CREATE TABLE leave_requests (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    request_id VARCHAR(64) NOT NULL UNIQUE,
    employee_id BIGINT NOT NULL,
    leave_type VARCHAR(30) NOT NULL,  -- annual, sick, personal, maternity, paternity, bereavement, marriage, unpaid
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    start_half_day ENUM('morning', 'afternoon') NULL,
    end_half_day ENUM('morning', 'afternoon') NULL,
    total_days DECIMAL(4, 1) NOT NULL,
    reason TEXT NOT NULL,
    attachment_urls JSON,
    medical_certificate BOOLEAN DEFAULT FALSE,
    delegate_to BIGINT,
    delegate_tasks TEXT,
    balance_before DECIMAL(4, 1),
    balance_after DECIMAL(4, 1),
    approver_id BIGINT,
    approval_level INTEGER DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, cancelled, recalled
    rejection_reason TEXT,
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    actual_return_date DATE,
    return_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE RESTRICT,
    FOREIGN KEY (delegate_to) REFERENCES employees(id) ON DELETE SET NULL,
    FOREIGN KEY (approver_id) REFERENCES employees(id) ON DELETE SET NULL,
    INDEX idx_leave_employee_id (employee_id),
    INDEX idx_leave_type (leave_type),
    INDEX idx_leave_dates (start_date, end_date),
    INDEX idx_leave_status (status),
    INDEX idx_leave_submitted_at (submitted_at)
) ENGINE=InnoDB;

-- ============================================
-- Additional indexes for reporting
-- ============================================
CREATE INDEX idx_employees_resignation ON employees(resignation_date);
CREATE INDEX idx_salary_gross ON salary_records(gross_salary);
CREATE INDEX idx_attendance_overtime ON attendance(overtime_hours);
