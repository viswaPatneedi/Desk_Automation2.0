"""
Database Configuration and ORM Models setup
Desk-Automation v2.0 - PostgreSQL + SQLAlchemy
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import NullPool, QueuePool
from datetime import datetime, timezone
import logging

# Logger
logger = logging.getLogger(__name__)

# Database URL from environment or config
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/desk_automation_v2'
)

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.environ.get('SQL_DEBUG', 'false').lower() == 'true'
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(SessionLocal)

# Base class for ORM models
Base = declarative_base()


# ============================================================
# ORM MODELS
# ============================================================

class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    team_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    last_login = Column(DateTime)
    active = Column(Boolean, default=True)
    
    # Relationships
    devices = relationship("Device", back_populates="created_by_user")
    jobs = relationship("Job", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="performed_by_user")
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'team_name': self.team_name,
            'is_admin': self.is_admin,
            'is_approved': self.is_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active
        }


class Device(Base):
    """Device model"""
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(15), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    port = Column(Integer, default=10022)
    device_type = Column(String(100))
    mac_address = Column(String(17))
    vnc_url = Column(Text)
    location = Column(String(100))
    team_name = Column(String(255), nullable=False)
    use_jump_host = Column(Boolean, default=False)
    jump_host_config = Column(JSON)
    ir_config = Column(JSON)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_devices_team_name', 'team_name'),
        Index('idx_devices_location', 'location'),
        Index('idx_devices_ip', 'ip'),
    )
    
    # Relationships
    created_by_user = relationship("User", back_populates="devices")
    jobs = relationship("Job", back_populates="device")
    test_results = relationship("TestResult", back_populates="device")
    device_locks = relationship("DeviceLock", back_populates="device", uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'name': self.name,
            'username': self.username,
            'port': self.port,
            'device_type': self.device_type,
            'mac_address': self.mac_address,
            'vnc_url': self.vnc_url,
            'location': self.location,
            'team_name': self.team_name,
            'use_jump_host': self.use_jump_host,
            'jump_host_config': self.jump_host_config,
            'ir_config': self.ir_config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }


class LogPattern(Base):
    """Log Pattern model"""
    __tablename__ = "log_patterns"
    
    id = Column(Integer, primary_key=True)
    pattern_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    regex = Column(String(1000), nullable=False)
    description = Column(Text)
    team_name = Column(String(255))
    location = Column(String(100))
    is_custom = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


class SystemCommand(Base):
    """System Command model"""
    __tablename__ = "system_commands"
    
    id = Column(Integer, primary_key=True)
    cmd_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    command = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String(100))
    team_name = Column(String(255))
    location = Column(String(100))
    is_custom = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


class Method(Base):
    """Method model"""
    __tablename__ = "methods"
    
    id = Column(Integer, primary_key=True)
    method_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    script_path = Column(String(512))
    parameters = Column(JSON)
    team_name = Column(String(255))
    location = Column(String(100))
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)


class SavedSequence(Base):
    """Saved Sequence model"""
    __tablename__ = "saved_sequences"
    
    id = Column(Integer, primary_key=True)
    seq_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    methods = Column(JSON, nullable=False)  # Array of {method_id, ir_keys, voice_text, rationale}
    method_rationale = Column(JSON)  # Method selection intent tracking
    execution_count = Column(Integer, default=0)
    total_duration_seconds = Column(Float)
    average_duration_seconds = Column(Float)
    team_name = Column(String(255), nullable=False)
    location = Column(String(100))
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="sequence")


class Job(Base):
    """Job model - enhanced for v2.0"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    device_id = Column(Integer, ForeignKey('devices.id'))
    device_ip = Column(String(15))
    device_name = Column(String(255))
    execution_queue = Column(JSON)
    methods = Column(Text)  # Legacy compatibility
    iterations = Column(Integer)
    sequence_id = Column(Integer, ForeignKey('saved_sequences.id'))
    sequence_name = Column(String(255))
    execution_type = Column(String(50))  # 'direct_method' or 'saved_sequence'
    status = Column(String(50))  # pending, running, completed, failed, cancelled
    execution_context_id = Column(Integer, ForeignKey('execution_contexts.id'))
    current_step = Column(Integer, default=0)
    current_iteration = Column(Integer, default=0)
    iteration_results = Column(JSON)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    log_file_path = Column(Text)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_jobs_status', 'status'),
        Index('idx_jobs_device_id', 'device_id'),
        Index('idx_jobs_user_id', 'user_id'),
        Index('idx_jobs_created_at', 'created_at'),
        Index('idx_jobs_execution_context_id', 'execution_context_id'),
    )
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    device = relationship("Device", back_populates="jobs")
    sequence = relationship("SavedSequence", back_populates="jobs")
    execution_context = relationship("ExecutionContext", primaryjoin="Job.execution_context_id == ExecutionContext.id", foreign_keys="[Job.execution_context_id]", uselist=False)
    test_results = relationship("TestResult", back_populates="job")


class ExecutionContext(Base):
    """Execution Context model - NEW for v2.0"""
    __tablename__ = "execution_contexts"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), ForeignKey('jobs.job_id'))
    device_snapshot = Column(JSON, nullable=False)  # Device specs at execution time
    methods_snapshot = Column(JSON, nullable=False)  # Method definitions at execution time
    user_snapshot = Column(JSON, nullable=False)  # User and team info at execution time
    environment_snapshot = Column(JSON)  # Environment variables
    system_config_snapshot = Column(JSON)  # System configuration
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    job = relationship("Job", primaryjoin="ExecutionContext.job_id == Job.job_id", foreign_keys="[ExecutionContext.job_id]", uselist=False)
    test_results = relationship("TestResult", back_populates="execution_context")


class TestResult(Base):
    """Test Result model - enhanced for v2.0"""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(255), ForeignKey('jobs.job_id'))
    iteration = Column(Integer)
    phase = Column(String(100))
    status = Column(String(50))
    details = Column(Text)
    device_id = Column(Integer, ForeignKey('devices.id'))
    device_name = Column(String(255))
    device_ip = Column(String(15))
    method = Column(String(255))
    username = Column(String(255))
    sequence_name = Column(String(255))
    screenshots = Column(Text)
    logs = Column(Text)
    performance_seconds = Column(Float)
    optional_checks = Column(JSON)
    build_info = Column(Text)
    tiles_summary = Column(JSON)
    rdk_milestones_log = Column(Text)
    boot_type = Column(String(100))
    execution_context_id = Column(Integer, ForeignKey('execution_contexts.id'))
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_test_results_job_id', 'job_id'),
        Index('idx_test_results_device_id', 'device_id'),
        Index('idx_test_results_timestamp', 'timestamp'),
    )
    
    # Relationships
    job = relationship("Job", back_populates="test_results")
    device = relationship("Device", back_populates="test_results")
    execution_context = relationship("ExecutionContext", back_populates="test_results")


class AuditLog(Base):
    """Audit Log model - NEW for v2.0"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    action_type = Column(String(100), nullable=False)  # create, update, delete, approve, reject, deploy
    entity_type = Column(String(100), nullable=False)  # device, job, method, sequence, user, etc.
    entity_id = Column(String(255))
    performed_by = Column(Integer, ForeignKey('users.id'))
    old_values = Column(JSON)
    new_values = Column(JSON)
    reason = Column(Text)
    impact_assessment = Column(JSON)  # For change management
    status = Column(String(50))  # success, failure, pending
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    is_immutable = Column(Boolean, default=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_entity_type', 'entity_type'),
        Index('idx_audit_logs_entity_id', 'entity_id'),
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_performed_by', 'performed_by'),
    )
    
    # Relationships
    performed_by_user = relationship("User", back_populates="audit_logs")


class StagingChange(Base):
    """Staging Change model - NEW for v2.0"""
    __tablename__ = "staging_changes"
    
    id = Column(Integer, primary_key=True)
    change_id = Column(String(255), unique=True, nullable=False)
    entity_type = Column(String(100), nullable=False)  # device, sequence, log_pattern, system_command, user
    entity_data = Column(JSON, nullable=False)  # Complete entity data for review
    submitted_by = Column(Integer, ForeignKey('users.id'))
    submitted_at = Column(DateTime, default=datetime.now(timezone.utc))
    status = Column(String(50), default='pending')  # pending, approved, rejected
    reviewed_by = Column(Integer, ForeignKey('users.id'))
    review_comment = Column(Text)
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index('idx_staging_changes_status', 'status'),
        Index('idx_staging_changes_entity_type', 'entity_type'),
    )


class DataSyncLog(Base):
    """Data Sync Log model - NEW for v2.0"""
    __tablename__ = "data_sync_log"
    
    id = Column(Integer, primary_key=True)
    sync_id = Column(String(255), unique=True, nullable=False)
    source_location = Column(String(100))
    source_instance = Column(String(255))
    entity_type = Column(String(100))  # device, method, log_pattern, sequence, command
    entity_id = Column(String(255))
    action_type = Column(String(50))  # pull, push, conflict_resolved
    data_hash = Column(String(64))  # SHA256 hash for integrity check
    conflict_detected = Column(Boolean, default=False)
    conflict_resolution = Column(JSON)  # How conflict was resolved
    approved_by = Column(Integer, ForeignKey('users.id'))
    github_sync_status = Column(String(50))  # pending, synced, failed
    github_commit_sha = Column(String(40))
    is_encrypted = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index('idx_data_sync_log_source_location', 'source_location'),
        Index('idx_data_sync_log_entity_type', 'entity_type'),
        Index('idx_data_sync_log_timestamp', 'timestamp'),
    )


class AgentStatus(Base):
    """Agent Status model - NEW for v2.0"""
    __tablename__ = "agent_status"
    
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(255), nullable=False)  # orchestrator, eta_device_lock, email_reporting, etc.
    is_running = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, default=datetime.now(timezone.utc))
    task_count_total = Column(Integer, default=0)
    task_count_completed = Column(Integer, default=0)
    task_count_failed = Column(Integer, default=0)
    error_message = Column(Text)
    health_status = Column(String(50))  # healthy, degraded, unhealthy
    metrics = Column(JSON)  # CPU, memory, response time, etc.
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


class DeviceLock(Base):
    """Device Lock model"""
    __tablename__ = "device_locks"
    
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey('devices.id'))
    device_ip = Column(String(15), unique=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    job_id = Column(String(255))
    lock_time = Column(DateTime, default=datetime.now(timezone.utc))
    estimated_completion = Column(DateTime)
    eta_seconds = Column(Integer)
    eta_formatted = Column(String(50))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    device = relationship("Device", back_populates="device_locks")


# ============================================================
# DATABASE UTILITIES
# ============================================================

def init_db():
    """Initialize database - create all tables"""
    logger.info("Initializing database...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized successfully")


def get_session():
    """Get a new database session"""
    return Session()


def close_session():
    """Close the scoped session"""
    Session.remove()


def health_check():
    """Check database connection health"""
    try:
        session = get_session()
        session.execute('SELECT 1')
        session.close()
        logger.info("✅ Database health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False
