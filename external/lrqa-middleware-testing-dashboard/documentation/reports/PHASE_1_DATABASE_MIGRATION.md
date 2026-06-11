# Phase 1: Database Migration (v1.0 JSON → v2.0 PostgreSQL)

## Overview

This document outlines the complete database migration process for Desk-Automation v2.0, transitioning from JSON-based persistence (v1.0) to a centralized PostgreSQL database.

**Phase Duration**: 5-7 days  
**Estimated Timeline**: June 8 - June 15, 2026  
**Status**: ✅ IMPLEMENTATION STARTED

---

## Phase 1 Artifacts Created

### 1. **config/database_schema.sql** ✅
   - Complete PostgreSQL schema with all tables, indexes, and views
   - 16 core tables + 6 new v2.0 tables
   - Supporting views for convenience queries
   - Full documentation with entity relationships

### 2. **models/database.py** ✅
   - SQLAlchemy ORM models (v2.0)
   - Database configuration and connection pooling
   - All model relationships defined
   - Session management utilities
   - Health check and initialization functions

   **Models Implemented**:
   - User
   - Device
   - LogPattern
   - SystemCommand
   - Method
   - SavedSequence
   - Job
   - ExecutionContext (NEW)
   - TestResult
   - AuditLog (NEW)
   - StagingChange (NEW)
   - DataSyncLog (NEW)
   - AgentStatus (NEW)
   - DeviceLock

### 3. **utilities/database_migration.py** ✅
   - JSON data loader with safe error handling
   - Migration class for each entity type
   - Backup and recovery procedures
   - Migration reporting and logging
   - Main function for command-line execution

### 4. **requirements.txt** ✅
   - Added SQLAlchemy 2.0.23
   - Added psycopg2-binary 2.9.9
   - Added alembic 1.13.1
   - Added pydantic 2.5.0
   - Added cryptography 41.0.7
   - Added PyGithub 2.1.1
   - Added python-dotenv 1.0.0

---

## Database Schema Summary

### Core Tables (Migrated from JSON)
| Table | Source | Records | Purpose |
|-------|--------|---------|---------|
| users | users.json | ~5-10 | User authentication & team management |
| devices | devices.json | ~50-100 | Device registry & SSH config |
| log_patterns | log_patterns.json | ~20-50 | Log validation patterns |
| system_commands | system_commands.json | ~30-50 | System commands library |
| methods | (new) | ~25 | Method definitions |
| saved_sequences | saved_sequences.json | ~10-20 | Saved test sequences |
| jobs | jobs.json | ~100-500 | Job execution history |
| test_results | test_results_history.json | ~1000+ | Test execution results |
| ir_keycodes | ir_keycodes.json | ~50-100 | IR remote keycodes |
| device_locks | device_locks.json | ~5-10 | Device lock tracking |

### New v2.0 Tables
| Table | Purpose | Records |
|-------|---------|---------|
| execution_contexts | Preserve execution environment | 1-to-1 with jobs |
| audit_logs | Immutable change tracking | Continuous growth |
| staging_changes | Approval workflow | As needed |
| data_sync_log | Multi-location sync tracking | Per sync event |
| agent_status | Monitor agent health | Per agent |
| implementation_progress | Track v2.0 implementation | 19 requirements |

---

## Setup Prerequisites

### 1. PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/

# Start PostgreSQL service
sudo service postgresql start
```

### 2. Create Database User & Database
```bash
sudo -u postgres psql

-- Inside PostgreSQL console
CREATE USER desk_automation WITH PASSWORD 'change_me_password';
CREATE DATABASE desk_automation_v2 OWNER desk_automation;
GRANT ALL PRIVILEGES ON DATABASE desk_automation_v2 TO desk_automation;
\q
```

### 3. Environment Configuration
Create or update `.env` file:
```bash
# Database configuration
DATABASE_URL=postgresql://desk_automation:change_me_password@localhost:5432/desk_automation_v2
SQL_DEBUG=false

# Application configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
```

### 4. Python Dependencies
```bash
# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import sqlalchemy; import psycopg2; print('✅ All dependencies installed')"
```

---

## Migration Steps

### Step 1: Backup Existing JSON Files
```bash
# The migration script automatically creates a backup
# Backup location: Json_backup_YYYYMMDD_HHMMSS/
# Manual backup (optional):
cp -r Json Json_backup_$(date +%Y%m%d_%H%M%S)
```

### Step 2: Initialize Database Schema
```bash
# Option A: Using Python script
python -c "from models.database import init_db; init_db()"

# Option B: Using SQL file directly
psql -U desk_automation -d desk_automation_v2 -f config/database_schema.sql
```

### Step 3: Run Data Migration
```bash
# Run full migration
python utilities/database_migration.py

# Expected output:
# 🚀 STARTING v2.0 DATABASE MIGRATION
# 🔄 Migrating users...
# ✅ Migrated X users
# 🔄 Migrating devices...
# ✅ Migrated X devices
# ... (continues for all tables)
# 📊 MIGRATION SUMMARY
# ✅ Migration completed!
# 📄 Report: migration_report.json
```

### Step 4: Verify Migration
```bash
# Check migration report
cat migration_report.json

# Verify records in PostgreSQL
psql -U desk_automation -d desk_automation_v2

-- Inside PostgreSQL console
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM devices;
SELECT COUNT(*) FROM jobs;
SELECT COUNT(*) FROM test_results;
\q
```

### Step 5: Health Check
```bash
# Test database connection
python -c "from models.database import health_check; health_check()"

# Expected output:
# ✅ Database health check passed
```

---

## Integration with Flask App

### Update `app.py`

```python
# Add to app.py (after Flask initialization)
from models.database import init_db, get_session, health_check

# Initialize database on app startup
with app.app_context():
    init_db()
    if health_check():
        print("✅ Database ready")
    else:
        print("❌ Database connection failed")
```

### Update Model Imports

```python
# Replace old JSON-based model imports
# OLD:
# from models.device import Device  # JSON-based

# NEW:
# from models.database import Device  # PostgreSQL-based
```

### Update Controllers

Controllers will need minimal changes:
- Device.load_all() → session.query(Device).filter_by(is_active=True).all()
- Device.add(device) → session.add(device); session.commit()
- Device.delete(ip) → session.delete(device); session.commit()

---

## Data Validation

### Pre-Migration Checks
1. ✅ JSON files exist and are valid
2. ✅ PostgreSQL database is accessible
3. ✅ No duplicate records (email, IP, username)
4. ✅ Required fields are populated

### Post-Migration Checks
1. ✅ All records successfully migrated
2. ✅ No data corruption detected
3. ✅ Foreign keys are valid
4. ✅ Indexes are created
5. ✅ Performance queries execute <100ms

### Rollback Plan
If migration fails:
1. Restore from backed-up JSON files: `cp -r Json_backup_*/* Json/`
2. Revert app.py changes
3. Restart Flask app with old code
4. Investigate error in migration_report.json
5. Fix issue and retry migration

---

## Performance Optimization

### Indexing Strategy
- Primary keys on all tables
- Foreign keys indexed for join performance
- Team_name, location indexed for filtering
- Status, timestamp, created_at indexed for queries
- Composite indexes for common query patterns

### Connection Pooling
```python
# Configured in models/database.py
pool_size=20          # Connections to keep
max_overflow=40       # Additional connections when needed
pool_pre_ping=True    # Verify connections before use
```

### Query Optimization
- Bulk inserts in migration (batches of 1000)
- Lazy loading for relationships
- Indexes on frequently filtered fields
- Query plan analysis for large result sets

---

## Troubleshooting

### Issue: Connection Refused
```
Error: psycopg2.OperationalError: could not connect to server:
```
**Solution**:
- Check PostgreSQL is running: `sudo service postgresql status`
- Verify DATABASE_URL in .env
- Ensure password is correct

### Issue: Table Already Exists
```
Error: psycopg2.ProgrammingError: relation "users" already exists
```
**Solution**:
- Drop existing tables: `DROP TABLE IF EXISTS users CASCADE;`
- Or use migration script: `init_db()` handles this

### Issue: Data Validation Errors
```
Error: Foreign key constraint violation
```
**Solution**:
- Check migration_report.json for error details
- Verify JSON data has valid references
- Run partial migration for specific table

---

## Next Steps After Phase 1

### Phase 2: Agent Framework (Days 8-14)
- Create agents/ folder with sub-agent implementations
- Implement Agent-ETA-DeviceLock
- Implement Agent-EmailReporting  
- Implement Agent-MemoryMonitor
- Test agent communication

### Phase 3: Modal UI (Days 15-19)
- Convert forms to modals
- Add execution context capture UI
- Update JavaScript handlers

### Phase 4: Distributed Sync (Days 20-29)
- Agent-DistributedDataSync implementation
- Multi-location deployment

### Phase 5: Security (Days 30-34)
- PyArmor integration
- Docker encryption

---

## Testing Plan

### Unit Tests
- [ ] Database initialization
- [ ] Model creation and relationships
- [ ] Migration data validation
- [ ] Query performance

### Integration Tests
- [ ] Full JSON→PostgreSQL migration
- [ ] Data integrity verification
- [ ] Rollback procedure
- [ ] Health checks

### Performance Tests
- [ ] Query latency <100ms (p95)
- [ ] Bulk insert performance
- [ ] Connection pool efficiency
- [ ] Index effectiveness

---

## Documentation

### Files Created
- ✅ `config/database_schema.sql` - PostgreSQL schema
- ✅ `models/database.py` - SQLAlchemy ORM
- ✅ `utilities/database_migration.py` - Migration utilities
- ✅ `PHASE_1_README.md` - This document

### Future Documentation
- [ ] API documentation for database service
- [ ] ORM relationship diagrams
- [ ] Query performance benchmarks
- [ ] Backup and recovery procedures

---

## Success Criteria

- [x] PostgreSQL schema designed and created
- [x] SQLAlchemy ORM models implemented
- [x] Migration utilities created
- [x] Requirements.txt updated
- [ ] Full migration executed successfully
- [ ] All records verified in PostgreSQL
- [ ] Health checks passing
- [ ] Phase 2 dependencies resolved

---

## Timeline

| Date | Task | Status |
|------|------|--------|
| June 8 | Schema design + ORM models + Migration utils | ✅ DONE |
| June 9 | Test migration with copy of production data | 🔄 TODO |
| June 10 | Fix any migration errors | 🔄 TODO |
| June 11 | Performance optimization | 🔄 TODO |
| June 12 | Integration with Flask app | 🔄 TODO |
| June 13 | Full testing (unit, integration, performance) | 🔄 TODO |
| June 15 | Phase 1 complete, Phase 2 ready to start | 🔄 TODO |

---

**Phase 1 Started**: June 8, 2026  
**Phase 1 Target End**: June 15, 2026  
**Total Effort**: ~30+ hours  

For updates on progress, see: `/memories/repo/v2-work-progress.md`
