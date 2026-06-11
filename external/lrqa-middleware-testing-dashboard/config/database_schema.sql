-- Desk-Automation v2.0 PostgreSQL Schema
-- Migration from JSON-based persistence to centralized database
-- Date: June 8, 2026

-- ============================================================
-- CORE TABLES (Existing data migration)
-- ============================================================

-- Users table (replaces users.json)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    team_name VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Devices table (replaces devices.json)
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    ip VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    password VARCHAR(255),
    port INTEGER DEFAULT 10022,
    device_type VARCHAR(100),
    mac_address VARCHAR(17),
    vnc_url TEXT,
    location VARCHAR(100),
    team_name VARCHAR(255) NOT NULL,
    use_jump_host BOOLEAN DEFAULT FALSE,
    jump_host_config JSONB,
    ir_config JSONB,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Log Patterns table (replaces log_patterns.json)
CREATE TABLE IF NOT EXISTS log_patterns (
    id SERIAL PRIMARY KEY,
    pattern_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    regex VARCHAR(1000) NOT NULL,
    description TEXT,
    team_name VARCHAR(255),
    location VARCHAR(100),
    is_custom BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- System Commands table (replaces system_commands.json)
CREATE TABLE IF NOT EXISTS system_commands (
    id SERIAL PRIMARY KEY,
    cmd_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    command TEXT NOT NULL,
    description TEXT,
    category VARCHAR(100),
    team_name VARCHAR(255),
    location VARCHAR(100),
    is_custom BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Methods table (new - for method definitions)
CREATE TABLE IF NOT EXISTS methods (
    id SERIAL PRIMARY KEY,
    method_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    script_path VARCHAR(512),
    parameters JSONB,
    team_name VARCHAR(255),
    location VARCHAR(100),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Saved Sequences table (replaces saved_sequences.json) - ENHANCED
CREATE TABLE IF NOT EXISTS saved_sequences (
    id SERIAL PRIMARY KEY,
    seq_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    methods JSONB NOT NULL, -- Array of {method_id, ir_keys, voice_text, rationale}
    method_rationale JSONB, -- Method selection intent tracking
    execution_count INTEGER DEFAULT 0,
    total_duration_seconds FLOAT,
    average_duration_seconds FLOAT,
    team_name VARCHAR(255) NOT NULL,
    location VARCHAR(100),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Jobs table (replaces jobs.json) - ENHANCED
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    device_id INTEGER REFERENCES devices(id),
    device_ip VARCHAR(15),
    device_name VARCHAR(255),
    execution_queue JSONB,
    methods TEXT, -- Legacy compatibility
    iterations INTEGER,
    sequence_id INTEGER REFERENCES saved_sequences(id),
    sequence_name VARCHAR(255),
    execution_type VARCHAR(50), -- 'direct_method' or 'saved_sequence'
    status VARCHAR(50), -- pending, running, completed, failed, cancelled
    execution_context_id INTEGER, -- Reference to execution_contexts
    current_step INTEGER DEFAULT 0,
    current_iteration INTEGER DEFAULT 0,
    iteration_results JSONB,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    log_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Test Results table (replaces test_results_history.json) - ENHANCED
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255),
    iteration INTEGER,
    phase VARCHAR(100),
    status VARCHAR(50),
    details TEXT,
    device_id INTEGER REFERENCES devices(id),
    device_name VARCHAR(255),
    device_ip VARCHAR(15),
    method VARCHAR(255),
    username VARCHAR(255),
    sequence_name VARCHAR(255),
    screenshots TEXT,
    logs TEXT,
    performance_seconds FLOAT,
    optional_checks JSONB,
    build_info TEXT,
    tiles_summary JSONB,
    rdk_milestones_log TEXT,
    boot_type VARCHAR(100),
    execution_context_id INTEGER, -- Link to execution context
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IR Keycodes table (replaces ir_keycodes.json)
CREATE TABLE IF NOT EXISTS ir_keycodes (
    id SERIAL PRIMARY KEY,
    keycode VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    button_name VARCHAR(100),
    category VARCHAR(100),
    device_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Device Locks table (replaces device_locks.json)
CREATE TABLE IF NOT EXISTS device_locks (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES devices(id),
    device_ip VARCHAR(15) UNIQUE,
    user_id INTEGER REFERENCES users(id),
    job_id VARCHAR(255),
    lock_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estimated_completion TIMESTAMP,
    eta_seconds INTEGER,
    eta_formatted VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- NEW TABLES (v2.0 enhancements)
-- ============================================================

-- Execution Contexts table (NEW - Requirement 8: Context Preservation)
CREATE TABLE IF NOT EXISTS execution_contexts (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(255) REFERENCES jobs(job_id),
    device_snapshot JSONB NOT NULL, -- Device specs at execution time
    methods_snapshot JSONB NOT NULL, -- Method definitions at execution time
    user_snapshot JSONB NOT NULL, -- User and team info at execution time
    environment_snapshot JSONB, -- Environment variables
    system_config_snapshot JSONB, -- System configuration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs table (NEW - Requirement 9, 14: Audit trail & Change management)
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(100) NOT NULL, -- create, update, delete, approve, reject, deploy
    entity_type VARCHAR(100) NOT NULL, -- device, job, method, sequence, user, etc.
    entity_id VARCHAR(255),
    performed_by INTEGER REFERENCES users(id),
    old_values JSONB,
    new_values JSONB,
    reason TEXT,
    impact_assessment JSONB, -- For change management
    status VARCHAR(50), -- success, failure, pending
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_immutable BOOLEAN DEFAULT TRUE
);

-- Staging Changes table (NEW - Requirement 11: Staging/Approval workflow)
CREATE TABLE IF NOT EXISTS staging_changes (
    id SERIAL PRIMARY KEY,
    change_id VARCHAR(255) UNIQUE NOT NULL,
    entity_type VARCHAR(100) NOT NULL, -- device, sequence, log_pattern, system_command, user
    entity_data JSONB NOT NULL, -- Complete entity data for review
    submitted_by INTEGER REFERENCES users(id),
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending', -- pending, approved, rejected
    reviewed_by INTEGER REFERENCES users(id),
    review_comment TEXT,
    reviewed_at TIMESTAMP,
    approved_at TIMESTAMP
);

-- Data Sync Log table (NEW - Requirement 16: Distributed sync tracking)
CREATE TABLE IF NOT EXISTS data_sync_log (
    id SERIAL PRIMARY KEY,
    sync_id VARCHAR(255) UNIQUE NOT NULL,
    source_location VARCHAR(100),
    source_instance VARCHAR(255),
    entity_type VARCHAR(100), -- device, method, log_pattern, sequence, command
    entity_id VARCHAR(255),
    action_type VARCHAR(50), -- pull, push, conflict_resolved
    data_hash VARCHAR(64), -- SHA256 hash for integrity check
    conflict_detected BOOLEAN DEFAULT FALSE,
    conflict_resolution JSONB, -- How conflict was resolved
    approved_by INTEGER REFERENCES users(id),
    github_sync_status VARCHAR(50), -- pending, synced, failed
    github_commit_sha VARCHAR(40),
    is_encrypted BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Status table (NEW - Requirement 3.1: Agent monitoring)
CREATE TABLE IF NOT EXISTS agent_status (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL, -- orchestrator, eta_device_lock, email_reporting, ai_screen_analyzer, distributed_sync, memory_monitor
    is_running BOOLEAN DEFAULT TRUE,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    task_count_total INTEGER DEFAULT 0,
    task_count_completed INTEGER DEFAULT 0,
    task_count_failed INTEGER DEFAULT 0,
    error_message TEXT,
    health_status VARCHAR(50), -- healthy, degraded, unhealthy
    metrics JSONB, -- CPU, memory, response time, etc.
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Implementation Progress table (NEW - Requirement 3.1: Memory monitoring)
CREATE TABLE IF NOT EXISTS implementation_progress (
    id SERIAL PRIMARY KEY,
    requirement_id INTEGER, -- 1-19
    requirement_name VARCHAR(255),
    status VARCHAR(50), -- not_started, in_progress, completed, blocked
    progress_percentage INTEGER DEFAULT 0,
    subtask_total INTEGER DEFAULT 0,
    subtask_completed INTEGER DEFAULT 0,
    phase_number INTEGER, -- 1-5
    owner_user_id INTEGER REFERENCES users(id),
    target_completion_date DATE,
    actual_completion_date DATE,
    notes TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES (for performance)
-- ============================================================

-- User indexes
CREATE INDEX idx_users_team_name ON users(team_name);
CREATE INDEX idx_users_is_admin ON users(is_admin);

-- Device indexes
CREATE INDEX idx_devices_team_name ON devices(team_name);
CREATE INDEX idx_devices_location ON devices(location);
CREATE INDEX idx_devices_ip ON devices(ip);

-- Job indexes
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_device_id ON jobs(device_id);
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_execution_context_id ON jobs(execution_context_id);

-- Test Results indexes
CREATE INDEX idx_test_results_job_id ON test_results(job_id);
CREATE INDEX idx_test_results_device_id ON test_results(device_id);
CREATE INDEX idx_test_results_timestamp ON test_results(timestamp);

-- Audit Logs indexes
CREATE INDEX idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX idx_audit_logs_entity_id ON audit_logs(entity_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_performed_by ON audit_logs(performed_by);

-- Staging Changes indexes
CREATE INDEX idx_staging_changes_status ON staging_changes(status);
CREATE INDEX idx_staging_changes_entity_type ON staging_changes(entity_type);

-- Data Sync Log indexes
CREATE INDEX idx_data_sync_log_source_location ON data_sync_log(source_location);
CREATE INDEX idx_data_sync_log_entity_type ON data_sync_log(entity_type);
CREATE INDEX idx_data_sync_log_timestamp ON data_sync_log(timestamp);

-- ============================================================
-- VIEWS (for convenience)
-- ============================================================

-- Active devices view
CREATE OR REPLACE VIEW active_devices AS
SELECT d.* FROM devices d
WHERE d.is_active = TRUE
ORDER BY d.team_name, d.location;

-- Pending staging changes view
CREATE OR REPLACE VIEW pending_stagings AS
SELECT * FROM staging_changes
WHERE status = 'pending'
ORDER BY submitted_at ASC;

-- Recent audit trail view
CREATE OR REPLACE VIEW recent_audit_trail AS
SELECT * FROM audit_logs
ORDER BY timestamp DESC
LIMIT 1000;

-- ============================================================
-- INITIAL DATA (Optional - can be populated after migration)
-- ============================================================

-- Create default admin user (password should be changed immediately)
-- INSERT INTO users (username, password_hash, email, is_admin, team_name)
-- VALUES ('admin', 'CHANGE_ME_HASH', 'admin@example.com', TRUE, 'ADMIN');
