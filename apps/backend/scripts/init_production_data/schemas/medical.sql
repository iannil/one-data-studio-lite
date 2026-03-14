-- Medical Health System Schema (MySQL)
-- Database: medical_db
-- Data Volume: ~4M records total

-- Note: Database creation is handled by the generator
-- This script assumes the database already exists

USE medical_db;

-- Disable foreign key checks for table drops
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- Drop existing tables in reverse dependency order
-- ============================================
DROP TABLE IF EXISTS lab_results;
DROP TABLE IF EXISTS lab_tests;
DROP TABLE IF EXISTS prescription_items;
DROP TABLE IF EXISTS prescriptions;
DROP TABLE IF EXISTS diagnoses;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS departments;
DROP TABLE IF EXISTS hospitals;

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 1. Hospitals Table (200 records)
-- ============================================
CREATE TABLE hospitals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hospital_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    hospital_level VARCHAR(20) NOT NULL,  -- 三级甲等, 三级乙等, 二级甲等, 二级乙等, 一级
    hospital_type VARCHAR(30) NOT NULL,  -- comprehensive, specialized, traditional_chinese, rehabilitation
    ownership VARCHAR(30) NOT NULL,  -- public, private, military
    province VARCHAR(50) NOT NULL,
    city VARCHAR(50) NOT NULL,
    district VARCHAR(50),
    address TEXT NOT NULL,
    postal_code VARCHAR(10),
    phone VARCHAR(50),
    emergency_phone VARCHAR(50),
    website VARCHAR(200),
    email VARCHAR(100),
    license_number VARCHAR(64),
    established_date DATE,
    bed_count INTEGER,
    actual_bed_count INTEGER,
    staff_count INTEGER,
    doctor_count INTEGER,
    annual_outpatient_visits INTEGER,
    annual_inpatient_admissions INTEGER,
    specialties JSON,  -- List of specialty departments
    equipment JSON,  -- Major medical equipment
    certifications JSON,  -- Accreditations and certifications
    insurance_accepted JSON,  -- Accepted insurance types
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_hospitals_level (hospital_level),
    INDEX idx_hospitals_city (city),
    INDEX idx_hospitals_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 2. Departments Table (2,000 records)
-- ============================================
CREATE TABLE departments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    department_code VARCHAR(32) NOT NULL UNIQUE,
    hospital_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 内科, 外科, 妇产科, 儿科, etc.
    parent_id BIGINT NULL,  -- For sub-departments
    floor VARCHAR(20),
    building VARCHAR(50),
    room_numbers VARCHAR(200),
    phone VARCHAR(50),
    description TEXT,
    specialties TEXT,
    services_offered JSON,
    operating_hours JSON,  -- { "monday": "08:00-17:00", ... }
    appointment_required BOOLEAN DEFAULT TRUE,
    max_daily_appointments INTEGER,
    consultation_fee DECIMAL(10, 2),
    is_emergency BOOLEAN NOT NULL DEFAULT FALSE,
    is_outpatient BOOLEAN NOT NULL DEFAULT TRUE,
    is_inpatient BOOLEAN NOT NULL DEFAULT FALSE,
    bed_count INTEGER,
    head_doctor_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE RESTRICT,
    FOREIGN KEY (parent_id) REFERENCES departments(id) ON DELETE SET NULL,
    INDEX idx_departments_hospital_id (hospital_id),
    INDEX idx_departments_category (category),
    INDEX idx_departments_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 3. Doctors Table (20,000 records)
-- ============================================
CREATE TABLE doctors (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    doctor_code VARCHAR(32) NOT NULL UNIQUE,
    hospital_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    gender ENUM('M', 'F') NOT NULL,
    birth_date DATE,
    id_card_encrypted VARCHAR(64),  -- Masked
    phone VARCHAR(20),
    email VARCHAR(100),
    title VARCHAR(50) NOT NULL,  -- 主任医师, 副主任医师, 主治医师, 住院医师
    professional_level VARCHAR(30),  -- senior, associate, attending, resident
    license_number VARCHAR(64) NOT NULL,
    license_issue_date DATE,
    license_expiry_date DATE,
    education_level VARCHAR(30),  -- bachelor, master, phd
    medical_school VARCHAR(200),
    graduation_year INTEGER,
    specializations JSON,  -- List of specializations
    certifications JSON,  -- Board certifications
    research_interests TEXT,
    publications_count INTEGER DEFAULT 0,
    years_of_experience INTEGER,
    consultation_fee DECIMAL(10, 2),
    expert_fee DECIMAL(10, 2),
    is_expert BOOLEAN DEFAULT FALSE,
    is_available_for_appointment BOOLEAN DEFAULT TRUE,
    max_daily_appointments INTEGER DEFAULT 30,
    appointment_duration_minutes INTEGER DEFAULT 15,
    schedule JSON,  -- Weekly schedule
    languages JSON,
    photo_url VARCHAR(500),
    bio TEXT,
    rating DECIMAL(3, 2) CHECK (rating BETWEEN 1 AND 5),
    review_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    hire_date DATE,
    resignation_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    INDEX idx_doctors_hospital_id (hospital_id),
    INDEX idx_doctors_department_id (department_id),
    INDEX idx_doctors_title (title),
    INDEX idx_doctors_is_expert (is_expert),
    INDEX idx_doctors_status (status)
) ENGINE=InnoDB;

-- Add head_doctor_id foreign key to departments after doctors table exists
ALTER TABLE departments
    ADD FOREIGN KEY (head_doctor_id) REFERENCES doctors(id) ON DELETE SET NULL;

-- ============================================
-- 4. Patients Table (500,000 records)
-- ============================================
CREATE TABLE patients (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    patient_code VARCHAR(32) NOT NULL UNIQUE,
    medical_record_number VARCHAR(32) UNIQUE,
    id_card_encrypted VARCHAR(64) NOT NULL,  -- Masked
    name VARCHAR(100) NOT NULL,
    gender ENUM('M', 'F', 'O') NOT NULL,
    birth_date DATE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    phone_encrypted VARCHAR(64),  -- Masked
    email VARCHAR(100),
    address TEXT,
    city VARCHAR(50),
    province VARCHAR(50),
    postal_code VARCHAR(10),
    emergency_contact_name VARCHAR(100),
    emergency_contact_phone VARCHAR(20),
    emergency_contact_relation VARCHAR(50),
    blood_type VARCHAR(5),  -- A+, A-, B+, B-, AB+, AB-, O+, O-
    allergies JSON,  -- List of known allergies
    chronic_conditions JSON,  -- List of chronic conditions
    current_medications JSON,
    medical_history TEXT,
    family_history TEXT,
    insurance_type VARCHAR(50),
    insurance_number VARCHAR(64),
    insurance_company VARCHAR(100),
    primary_hospital_id BIGINT,
    primary_doctor_id BIGINT,
    occupation VARCHAR(100),
    marital_status VARCHAR(20),
    nationality VARCHAR(50) DEFAULT '中国',
    ethnicity VARCHAR(50),
    height_cm DECIMAL(5, 1),
    weight_kg DECIMAL(5, 1),
    bmi DECIMAL(4, 1) AS (weight_kg / POWER(height_cm / 100, 2)) VIRTUAL,
    smoking_status VARCHAR(20),  -- never, former, current
    drinking_status VARCHAR(20),  -- never, occasional, regular
    exercise_frequency VARCHAR(20),  -- never, occasional, regular, frequent
    registration_date DATE NOT NULL,
    last_visit_date DATE,
    visit_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (primary_hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL,
    FOREIGN KEY (primary_doctor_id) REFERENCES doctors(id) ON DELETE SET NULL,
    INDEX idx_patients_phone (phone),
    INDEX idx_patients_registration_date (registration_date),
    INDEX idx_patients_last_visit_date (last_visit_date),
    INDEX idx_patients_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 5. Appointments Table (1,000,000 records)
-- ============================================
CREATE TABLE appointments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    appointment_code VARCHAR(32) NOT NULL UNIQUE,
    patient_id BIGINT NOT NULL,
    doctor_id BIGINT NOT NULL,
    department_id BIGINT NOT NULL,
    hospital_id BIGINT NOT NULL,
    appointment_type VARCHAR(30) NOT NULL,  -- outpatient, follow_up, emergency, teleconsultation
    appointment_date DATE NOT NULL,
    time_slot_start TIME NOT NULL,
    time_slot_end TIME NOT NULL,
    queue_number INTEGER,
    chief_complaint TEXT,
    symptoms JSON,
    symptom_duration VARCHAR(100),
    severity VARCHAR(20),  -- mild, moderate, severe
    is_first_visit BOOLEAN DEFAULT TRUE,
    referral_source VARCHAR(50),  -- self, referral, emergency
    referring_doctor_id BIGINT,
    registration_fee DECIMAL(10, 2),
    consultation_fee DECIMAL(10, 2),
    total_fee DECIMAL(10, 2),
    payment_status VARCHAR(20) DEFAULT 'pending',  -- pending, paid, refunded
    payment_method VARCHAR(30),
    paid_at TIMESTAMP NULL,
    insurance_claim_id VARCHAR(64),
    insurance_covered_amount DECIMAL(10, 2),
    check_in_time TIMESTAMP NULL,
    consultation_start_time TIMESTAMP NULL,
    consultation_end_time TIMESTAMP NULL,
    waiting_time_minutes INTEGER,
    consultation_duration_minutes INTEGER,
    no_show BOOLEAN DEFAULT FALSE,
    cancellation_reason TEXT,
    cancelled_at TIMESTAMP NULL,
    rescheduled_from BIGINT,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- scheduled, confirmed, checked_in, in_progress, completed, cancelled, no_show
    source VARCHAR(30) DEFAULT 'online',  -- online, phone, walk_in, referral
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE RESTRICT,
    INDEX idx_appointments_patient_id (patient_id),
    INDEX idx_appointments_doctor_id (doctor_id),
    INDEX idx_appointments_date (appointment_date),
    INDEX idx_appointments_status (status),
    INDEX idx_appointments_type (appointment_type)
) ENGINE=InnoDB;

-- ============================================
-- 6. Diagnoses Table (800,000 records)
-- ============================================
CREATE TABLE diagnoses (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    diagnosis_code VARCHAR(32) NOT NULL UNIQUE,
    appointment_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    doctor_id BIGINT NOT NULL,
    icd10_code VARCHAR(10) NOT NULL,  -- ICD-10 code
    icd10_name VARCHAR(200) NOT NULL,
    diagnosis_type VARCHAR(30) NOT NULL,  -- primary, secondary, differential, final
    diagnosis_status VARCHAR(20) NOT NULL DEFAULT 'confirmed',  -- suspected, confirmed, ruled_out
    severity VARCHAR(20),  -- mild, moderate, severe, critical
    onset_date DATE,
    onset_type VARCHAR(20),  -- acute, chronic, recurrent
    clinical_description TEXT,
    examination_findings TEXT,
    vital_signs JSON,  -- { "blood_pressure": "120/80", "heart_rate": 72, ... }
    physical_exam_notes TEXT,
    differential_diagnosis JSON,
    treatment_plan TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    follow_up_instructions TEXT,
    hospitalization_required BOOLEAN DEFAULT FALSE,
    admission_recommended BOOLEAN DEFAULT FALSE,
    referral_required BOOLEAN DEFAULT FALSE,
    referral_department VARCHAR(100),
    referral_reason TEXT,
    prognosis VARCHAR(200),
    notes TEXT,
    reviewed_by BIGINT,
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE RESTRICT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE RESTRICT,
    INDEX idx_diagnoses_appointment_id (appointment_id),
    INDEX idx_diagnoses_patient_id (patient_id),
    INDEX idx_diagnoses_icd10_code (icd10_code),
    INDEX idx_diagnoses_diagnosis_type (diagnosis_type)
) ENGINE=InnoDB;

-- ============================================
-- 7. Prescriptions Table (600,000 records)
-- ============================================
CREATE TABLE prescriptions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    prescription_code VARCHAR(32) NOT NULL UNIQUE,
    diagnosis_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    doctor_id BIGINT NOT NULL,
    prescription_type VARCHAR(30) NOT NULL,  -- outpatient, inpatient, discharge, chronic
    prescription_date DATE NOT NULL,
    valid_days INTEGER DEFAULT 3,
    expiry_date DATE,
    total_items INTEGER NOT NULL DEFAULT 0,
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
    insurance_amount DECIMAL(12, 2) DEFAULT 0,
    self_pay_amount DECIMAL(12, 2) DEFAULT 0,
    payment_status VARCHAR(20) DEFAULT 'pending',
    paid_at TIMESTAMP NULL,
    dispensing_status VARCHAR(20) DEFAULT 'pending',  -- pending, partial, dispensed, returned
    dispensed_at TIMESTAMP NULL,
    dispensed_by VARCHAR(100),
    pharmacy_location VARCHAR(200),
    special_instructions TEXT,
    allergies_checked BOOLEAN DEFAULT TRUE,
    interactions_checked BOOLEAN DEFAULT TRUE,
    warnings JSON,
    is_narcotic BOOLEAN DEFAULT FALSE,
    is_psychotropic BOOLEAN DEFAULT FALSE,
    is_antibiotic BOOLEAN DEFAULT FALSE,
    requires_skin_test BOOLEAN DEFAULT FALSE,
    electronic_signature VARCHAR(200),
    reviewed_by BIGINT,
    reviewed_at TIMESTAMP NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    cancelled_reason TEXT,
    cancelled_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id) ON DELETE RESTRICT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE RESTRICT,
    INDEX idx_prescriptions_diagnosis_id (diagnosis_id),
    INDEX idx_prescriptions_patient_id (patient_id),
    INDEX idx_prescriptions_doctor_id (doctor_id),
    INDEX idx_prescriptions_date (prescription_date),
    INDEX idx_prescriptions_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 8. Prescription Items Table (2,000,000 records)
-- ============================================
CREATE TABLE prescription_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    item_code VARCHAR(32) NOT NULL UNIQUE,
    prescription_id BIGINT NOT NULL,
    sequence_number INTEGER NOT NULL,
    drug_code VARCHAR(32) NOT NULL,
    drug_name VARCHAR(200) NOT NULL,
    generic_name VARCHAR(200),
    drug_type VARCHAR(50) NOT NULL,  -- western, traditional_chinese, combination
    drug_category VARCHAR(50),  -- antibiotics, analgesics, cardiovascular, etc.
    specification VARCHAR(100),  -- 规格
    manufacturer VARCHAR(200),
    unit VARCHAR(20) NOT NULL,  -- 片, 粒, 支, ml, etc.
    dosage VARCHAR(50) NOT NULL,
    dosage_unit VARCHAR(20) NOT NULL,
    frequency VARCHAR(50) NOT NULL,  -- 每日3次, 每8小时, etc.
    frequency_code VARCHAR(20),  -- tid, bid, qd, etc.
    administration_route VARCHAR(30) NOT NULL,  -- oral, injection, topical, etc.
    duration_days INTEGER,
    quantity DECIMAL(10, 2) NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    insurance_ratio DECIMAL(5, 2),
    insurance_covered DECIMAL(10, 2),
    self_pay DECIMAL(10, 2),
    is_covered_by_insurance BOOLEAN DEFAULT TRUE,
    skin_test_required BOOLEAN DEFAULT FALSE,
    skin_test_result VARCHAR(20),
    special_instructions TEXT,
    substitution_allowed BOOLEAN DEFAULT TRUE,
    substituted_for VARCHAR(200),
    dispensed_quantity DECIMAL(10, 2),
    dispensed_at TIMESTAMP NULL,
    batch_number VARCHAR(64),
    expiry_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, dispensed, returned, cancelled
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (prescription_id) REFERENCES prescriptions(id) ON DELETE CASCADE,
    INDEX idx_prescription_items_prescription_id (prescription_id),
    INDEX idx_prescription_items_drug_code (drug_code),
    INDEX idx_prescription_items_drug_category (drug_category),
    INDEX idx_prescription_items_status (status)
) ENGINE=InnoDB;

-- ============================================
-- 9. Lab Tests Table (400,000 records)
-- ============================================
CREATE TABLE lab_tests (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    test_code VARCHAR(32) NOT NULL UNIQUE,
    appointment_id BIGINT NOT NULL,
    patient_id BIGINT NOT NULL,
    ordering_doctor_id BIGINT NOT NULL,
    test_category VARCHAR(50) NOT NULL,  -- blood, urine, biochemistry, imaging, pathology
    test_type VARCHAR(100) NOT NULL,
    test_name VARCHAR(200) NOT NULL,
    test_items JSON,  -- List of individual test items
    urgency VARCHAR(20) DEFAULT 'routine',  -- routine, urgent, stat
    fasting_required BOOLEAN DEFAULT FALSE,
    specimen_type VARCHAR(50),  -- blood, urine, stool, tissue, etc.
    specimen_collected BOOLEAN DEFAULT FALSE,
    specimen_collected_at TIMESTAMP NULL,
    specimen_collected_by VARCHAR(100),
    specimen_id VARCHAR(64),
    lab_department VARCHAR(100),
    lab_technician VARCHAR(100),
    equipment_used VARCHAR(100),
    test_started_at TIMESTAMP NULL,
    test_completed_at TIMESTAMP NULL,
    report_generated_at TIMESTAMP NULL,
    reporting_doctor_id BIGINT,
    price DECIMAL(10, 2),
    payment_status VARCHAR(20) DEFAULT 'pending',
    insurance_covered DECIMAL(10, 2),
    clinical_indication TEXT,
    special_instructions TEXT,
    is_abnormal BOOLEAN DEFAULT FALSE,
    critical_values BOOLEAN DEFAULT FALSE,
    critical_notified BOOLEAN DEFAULT FALSE,
    critical_notified_at TIMESTAMP NULL,
    critical_notified_to VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'ordered',  -- ordered, collected, processing, completed, cancelled
    cancellation_reason TEXT,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE RESTRICT,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE RESTRICT,
    FOREIGN KEY (ordering_doctor_id) REFERENCES doctors(id) ON DELETE RESTRICT,
    INDEX idx_lab_tests_appointment_id (appointment_id),
    INDEX idx_lab_tests_patient_id (patient_id),
    INDEX idx_lab_tests_test_category (test_category),
    INDEX idx_lab_tests_status (status),
    INDEX idx_lab_tests_is_abnormal (is_abnormal)
) ENGINE=InnoDB;

-- ============================================
-- 10. Lab Results Table (1,500,000 records)
-- ============================================
CREATE TABLE lab_results (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    result_code VARCHAR(32) NOT NULL UNIQUE,
    lab_test_id BIGINT NOT NULL,
    item_code VARCHAR(32) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    item_abbreviation VARCHAR(20),
    result_value VARCHAR(200),
    result_numeric DECIMAL(18, 6),
    unit VARCHAR(50),
    reference_range VARCHAR(100),
    reference_low DECIMAL(18, 6),
    reference_high DECIMAL(18, 6),
    is_abnormal BOOLEAN DEFAULT FALSE,
    abnormal_flag VARCHAR(10),  -- H (high), L (low), HH (critical high), LL (critical low)
    is_critical BOOLEAN DEFAULT FALSE,
    delta_check BOOLEAN DEFAULT FALSE,
    previous_value DECIMAL(18, 6),
    previous_date DATE,
    interpretation TEXT,
    methodology VARCHAR(100),
    instrument VARCHAR(100),
    reagent_lot VARCHAR(64),
    quality_control_status VARCHAR(20),
    verified_by VARCHAR(100),
    verified_at TIMESTAMP NULL,
    comments TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (lab_test_id) REFERENCES lab_tests(id) ON DELETE CASCADE,
    INDEX idx_lab_results_lab_test_id (lab_test_id),
    INDEX idx_lab_results_item_code (item_code),
    INDEX idx_lab_results_is_abnormal (is_abnormal),
    INDEX idx_lab_results_is_critical (is_critical)
) ENGINE=InnoDB;

-- ============================================
-- Full-text indexes for search functionality
-- ============================================
ALTER TABLE diagnoses ADD FULLTEXT INDEX ft_diagnoses_description (clinical_description, treatment_plan);
ALTER TABLE patients ADD FULLTEXT INDEX ft_patients_history (medical_history, family_history);
