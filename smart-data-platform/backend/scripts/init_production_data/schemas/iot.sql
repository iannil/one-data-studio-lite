-- IoT Platform Schema (PostgreSQL)
-- Schema: iot
-- Data Volume: ~6M records total

-- Create schema
CREATE SCHEMA IF NOT EXISTS iot;

-- Set search path
SET search_path TO iot, public;

-- Drop existing tables (for re-creation)
DROP TABLE IF EXISTS iot.maintenance_logs CASCADE;
DROP TABLE IF EXISTS iot.alerts CASCADE;
DROP TABLE IF EXISTS iot.device_events CASCADE;
DROP TABLE IF EXISTS iot.sensor_readings CASCADE;
DROP TABLE IF EXISTS iot.sensors CASCADE;
DROP TABLE IF EXISTS iot.devices CASCADE;
DROP TABLE IF EXISTS iot.device_types CASCADE;

-- ============================================
-- 1. Device Types Table (100 records)
-- ============================================
CREATE TABLE iot.device_types (
    id SERIAL PRIMARY KEY,
    type_code VARCHAR(32) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 环境监测, 工业监测, 能源监测, 安全监测, 安防系统, 定位追踪
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    protocol VARCHAR(30),  -- mqtt, http, modbus, coap
    data_format VARCHAR(20) DEFAULT 'json',
    firmware_version VARCHAR(20),
    power_type VARCHAR(20),  -- battery, solar, wired, hybrid
    expected_lifetime_days INTEGER,
    default_sampling_interval INTEGER,  -- seconds
    specifications JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for device_types
CREATE INDEX idx_device_types_category ON iot.device_types(category);

-- ============================================
-- 2. Devices Table (50,000 records)
-- ============================================
CREATE TABLE iot.devices (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL UNIQUE,
    device_type_id INTEGER NOT NULL REFERENCES iot.device_types(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    serial_number VARCHAR(64),
    mac_address VARCHAR(17),
    ip_address VARCHAR(45),
    firmware_version VARCHAR(20),
    hardware_version VARCHAR(20),
    latitude DECIMAL(10, 6),
    longitude DECIMAL(10, 6),
    altitude DECIMAL(10, 2),
    location_name VARCHAR(200),
    installation_date DATE,
    warranty_until DATE,
    owner_id VARCHAR(50),
    group_id VARCHAR(50),
    tags TEXT[],
    config JSONB,
    last_heartbeat_at TIMESTAMP WITH TIME ZONE,
    last_data_at TIMESTAMP WITH TIME ZONE,
    battery_level INTEGER CHECK (battery_level BETWEEN 0 AND 100),
    signal_strength INTEGER CHECK (signal_strength BETWEEN -120 AND 0),
    status VARCHAR(20) NOT NULL DEFAULT 'online',  -- online, offline, maintenance, error
    error_code VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for devices
CREATE INDEX idx_devices_device_type_id ON iot.devices(device_type_id);
CREATE INDEX idx_devices_status ON iot.devices(status);
CREATE INDEX idx_devices_location ON iot.devices(latitude, longitude);
CREATE INDEX idx_devices_last_heartbeat ON iot.devices(last_heartbeat_at);
CREATE INDEX idx_devices_owner_id ON iot.devices(owner_id);
CREATE INDEX idx_devices_tags ON iot.devices USING GIN(tags);

-- ============================================
-- 3. Sensors Table (200,000 records)
-- ============================================
CREATE TABLE iot.sensors (
    id BIGSERIAL PRIMARY KEY,
    sensor_id VARCHAR(64) NOT NULL UNIQUE,
    device_id BIGINT NOT NULL REFERENCES iot.devices(id),
    name VARCHAR(100) NOT NULL,
    sensor_type VARCHAR(50) NOT NULL,  -- temperature, humidity, pressure, etc.
    unit VARCHAR(20) NOT NULL,
    data_type VARCHAR(20) NOT NULL DEFAULT 'float',  -- float, integer, boolean, string
    min_value DECIMAL(18, 6),
    max_value DECIMAL(18, 6),
    precision_value DECIMAL(10, 6),
    accuracy DECIMAL(8, 4),
    sampling_interval INTEGER NOT NULL DEFAULT 60,  -- seconds
    aggregation_method VARCHAR(20) DEFAULT 'avg',  -- avg, sum, min, max, last
    threshold_low DECIMAL(18, 6),
    threshold_high DECIMAL(18, 6),
    alert_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    calibration_date DATE,
    calibration_due DATE,
    calibration_offset DECIMAL(10, 6) DEFAULT 0,
    calibration_factor DECIMAL(10, 6) DEFAULT 1,
    last_value DECIMAL(18, 6),
    last_reading_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for sensors
CREATE INDEX idx_sensors_device_id ON iot.sensors(device_id);
CREATE INDEX idx_sensors_sensor_type ON iot.sensors(sensor_type);
CREATE INDEX idx_sensors_status ON iot.sensors(status);

-- ============================================
-- 4. Sensor Readings Table (5,000,000 records)
-- Time-series data with partitioning
-- ============================================
CREATE TABLE iot.sensor_readings (
    id BIGSERIAL,
    sensor_id BIGINT NOT NULL,
    value DECIMAL(18, 6) NOT NULL,
    quality INTEGER NOT NULL DEFAULT 100 CHECK (quality BETWEEN 0 AND 100),
    raw_value DECIMAL(18, 6),
    unit VARCHAR(20),
    metadata JSONB,
    is_anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_score DECIMAL(8, 4),
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, recorded_at)
) PARTITION BY RANGE (recorded_at);

-- Create monthly partitions for 2024-2026
CREATE TABLE iot.sensor_readings_2024_01 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE iot.sensor_readings_2024_02 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE iot.sensor_readings_2024_03 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE iot.sensor_readings_2024_04 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE iot.sensor_readings_2024_05 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE iot.sensor_readings_2024_06 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE iot.sensor_readings_2024_07 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE iot.sensor_readings_2024_08 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE iot.sensor_readings_2024_09 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE iot.sensor_readings_2024_10 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE iot.sensor_readings_2024_11 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE iot.sensor_readings_2024_12 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');

CREATE TABLE iot.sensor_readings_2025_01 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE iot.sensor_readings_2025_02 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE iot.sensor_readings_2025_03 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE iot.sensor_readings_2025_04 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE iot.sensor_readings_2025_05 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE iot.sensor_readings_2025_06 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE iot.sensor_readings_2025_07 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE iot.sensor_readings_2025_08 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE iot.sensor_readings_2025_09 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE iot.sensor_readings_2025_10 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE iot.sensor_readings_2025_11 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE iot.sensor_readings_2025_12 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE iot.sensor_readings_2026_01 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE iot.sensor_readings_2026_02 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE iot.sensor_readings_2026_03 PARTITION OF iot.sensor_readings
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Indexes for sensor_readings
CREATE INDEX idx_sensor_readings_sensor_id ON iot.sensor_readings(sensor_id);
CREATE INDEX idx_sensor_readings_recorded_at ON iot.sensor_readings(recorded_at);
CREATE INDEX idx_sensor_readings_is_anomaly ON iot.sensor_readings(is_anomaly) WHERE is_anomaly = TRUE;

-- ============================================
-- 5. Device Events Table (500,000 records)
-- ============================================
CREATE TABLE iot.device_events (
    id BIGSERIAL PRIMARY KEY,
    event_id VARCHAR(64) NOT NULL UNIQUE,
    device_id BIGINT NOT NULL REFERENCES iot.devices(id),
    event_type VARCHAR(50) NOT NULL,  -- startup, shutdown, config_change, firmware_update, error, warning
    severity VARCHAR(20) NOT NULL DEFAULT 'info',  -- debug, info, warning, error, critical
    source VARCHAR(50),
    message TEXT NOT NULL,
    details JSONB,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolution TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for device_events
CREATE INDEX idx_device_events_device_id ON iot.device_events(device_id);
CREATE INDEX idx_device_events_event_type ON iot.device_events(event_type);
CREATE INDEX idx_device_events_severity ON iot.device_events(severity);
CREATE INDEX idx_device_events_occurred_at ON iot.device_events(occurred_at);
CREATE INDEX idx_device_events_acknowledged ON iot.device_events(acknowledged) WHERE acknowledged = FALSE;

-- ============================================
-- 6. Alerts Table (100,000 records)
-- ============================================
CREATE TABLE iot.alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(64) NOT NULL UNIQUE,
    device_id BIGINT NOT NULL REFERENCES iot.devices(id),
    sensor_id BIGINT REFERENCES iot.sensors(id),
    alert_type VARCHAR(50) NOT NULL,  -- threshold, anomaly, connectivity, battery, maintenance
    severity VARCHAR(20) NOT NULL,  -- info, warning, critical, emergency
    rule_name VARCHAR(100),
    condition TEXT,
    actual_value DECIMAL(18, 6),
    threshold_value DECIMAL(18, 6),
    message TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, acknowledged, resolved, suppressed
    priority INTEGER NOT NULL DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    escalation_level INTEGER NOT NULL DEFAULT 0,
    notification_sent BOOLEAN NOT NULL DEFAULT FALSE,
    notification_channels TEXT[],
    assigned_to VARCHAR(50),
    acknowledged_by VARCHAR(50),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    triggered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for alerts
CREATE INDEX idx_alerts_device_id ON iot.alerts(device_id);
CREATE INDEX idx_alerts_sensor_id ON iot.alerts(sensor_id);
CREATE INDEX idx_alerts_alert_type ON iot.alerts(alert_type);
CREATE INDEX idx_alerts_severity ON iot.alerts(severity);
CREATE INDEX idx_alerts_status ON iot.alerts(status);
CREATE INDEX idx_alerts_triggered_at ON iot.alerts(triggered_at);
CREATE INDEX idx_alerts_priority ON iot.alerts(priority);

-- ============================================
-- 7. Maintenance Logs Table (50,000 records)
-- ============================================
CREATE TABLE iot.maintenance_logs (
    id BIGSERIAL PRIMARY KEY,
    maintenance_id VARCHAR(64) NOT NULL UNIQUE,
    device_id BIGINT NOT NULL REFERENCES iot.devices(id),
    maintenance_type VARCHAR(50) NOT NULL,  -- preventive, corrective, predictive, emergency
    category VARCHAR(50) NOT NULL,  -- calibration, repair, replacement, inspection, cleaning
    description TEXT NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    estimated_duration INTEGER,  -- minutes
    actual_duration INTEGER,  -- minutes
    technician_id VARCHAR(50),
    technician_name VARCHAR(100),
    work_order_id VARCHAR(64),
    parts_used JSONB,
    labor_cost DECIMAL(12, 2),
    parts_cost DECIMAL(12, 2),
    total_cost DECIMAL(12, 2),
    findings TEXT,
    actions_taken TEXT,
    recommendations TEXT,
    next_maintenance_date DATE,
    attachments TEXT[],
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',  -- scheduled, in_progress, completed, cancelled
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for maintenance_logs
CREATE INDEX idx_maintenance_logs_device_id ON iot.maintenance_logs(device_id);
CREATE INDEX idx_maintenance_logs_maintenance_type ON iot.maintenance_logs(maintenance_type);
CREATE INDEX idx_maintenance_logs_status ON iot.maintenance_logs(status);
CREATE INDEX idx_maintenance_logs_scheduled_at ON iot.maintenance_logs(scheduled_at);
CREATE INDEX idx_maintenance_logs_technician_id ON iot.maintenance_logs(technician_id);

-- ============================================
-- Comments for documentation
-- ============================================
COMMENT ON SCHEMA iot IS 'IoT platform schema for device management, sensor data, and monitoring';
COMMENT ON TABLE iot.device_types IS 'Device type catalog with specifications';
COMMENT ON TABLE iot.devices IS 'Device inventory with status and location';
COMMENT ON TABLE iot.sensors IS 'Sensor definitions and configurations';
COMMENT ON TABLE iot.sensor_readings IS 'Time-series sensor data with partitioning';
COMMENT ON TABLE iot.device_events IS 'Device lifecycle and operational events';
COMMENT ON TABLE iot.alerts IS 'Alert and notification records';
COMMENT ON TABLE iot.maintenance_logs IS 'Device maintenance and service records';
