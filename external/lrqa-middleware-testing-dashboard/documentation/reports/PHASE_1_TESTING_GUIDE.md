# Phase 1 Database Migration - Complete Testing Guide

**Last Updated**: June 9, 2026  
**Status**: Ready for Testing  
**Target**: Complete Phase 1 validation before Phase 3 (Modal UI)

---

## Quick Start Testing (5 minutes)

```bash
# 1. Check PostgreSQL availability
psql --version

# 2. Verify connection
psql -U postgres -c "SELECT version();"

# 3. Run automated setup
python setup_database.py --full-setup

# 4. Verify schema
psql -U lrqa -d lrqa_v2_test -c "\dt"

# 5. Test app integration
python -c "from app import app; print('✓ App loads successfully')"
```

---

## Detailed Testing Procedure

### Phase 1A: PostgreSQL Environment Setup

#### Step 1: Verify PostgreSQL Installation
```bash
# Check if PostgreSQL is installed
which psql

# Expected output: /usr/bin/psql

# Check version (must be 12+)
psql --version

# Expected: psql (PostgreSQL) 14.x or higher
```

**If NOT Installed**:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (using Homebrew)
brew install postgresql

# After installation, start service:
# Ubuntu/Debian: sudo systemctl start postgresql
# macOS: brew services start postgresql
```

#### Step 2: Verify PostgreSQL Service Running
```bash
# Check service status
sudo systemctl status postgresql

# Or (macOS):
brew services list | grep postgresql

# Expected: ✓ running
```

### Phase 1B: Environment Configuration

#### Step 1: Create/Update .env File
```bash
# Copy template
cp .env.example .env

# Edit .env with these values (for testing)
cat > .env << 'EOF'
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lrqa_v2_test
DB_USER=lrqa
DB_PASSWORD=lrqa_password

# Connection Pool
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_PRE_PING=true
DB_ECHO=false

# Feature Flags
ENABLE_DATABASE_MIGRATION=true
ENABLE_JSON_FALLBACK=false

# Other existing config...
EOF
```

#### Step 2: Verify .env Loading
```python
import os
from dotenv import load_dotenv

load_dotenv()
print("DB_HOST:", os.environ.get('DB_HOST'))
print("DB_NAME:", os.environ.get('DB_NAME'))
```

### Phase 1C: Database Creation & Schema Setup

#### Step 1: Create PostgreSQL User (if not exists)
```bash
# Connect to PostgreSQL as superuser
psql -U postgres

# Inside psql:
CREATE USER lrqa WITH PASSWORD 'lrqa_password';
ALTER USER lrqa CREATEDB;
\q
```

#### Step 2: Create Test Database
```bash
# Create database owned by lrqa user
createdb -U postgres -O lrqa lrqa_v2_test

# Verify database created
psql -U postgres -l | grep lrqa_v2_test
```

#### Step 3: Import Database Schema
```bash
# Import schema from SQL file
psql -U lrqa -d lrqa_v2_test -f config/database_schema.sql

# Expected output: CREATE TABLE ... (22 times)
```

#### Step 4: Verify Schema Import
```bash
# Count tables
psql -U lrqa -d lrqa_v2_test -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';"

# Expected: 22 tables

# List all tables
psql -U lrqa -d lrqa_v2_test -c "\dt"

# Expected tables:
# - devices, users, jobs, test_results, device_locks
# - saved_sequences, audit_logs, execution_context
# - ... and more
```

### Phase 1D: ORM Model Validation

#### Step 1: Test SQLAlchemy Models
```bash
# Run this test script
python << 'EOF'
import sys
sys.path.insert(0, '.')

from models.database import (
    Database, Device, User, Job, TestResult, DeviceLock, 
    SavedSequence, AuditLog, ExecutionContext
)

# Initialize database
db = Database()
session = db.get_session()

print("✓ Database class imported successfully")
print("✓ All ORM models imported successfully")

# Test connection
try:
    result = session.execute("SELECT 1")
    print("✓ Database connection successful")
except Exception as e:
    print(f"✗ Connection failed: {e}")

session.close()
EOF
```

### Phase 1E: JSON→PostgreSQL Migration Test

#### Step 1: Backup Current JSON Data
```bash
# Create backup before migration
mkdir -p backups/pre_migration_$(date +%Y%m%d)

# Copy all JSON files
cp devices.json backups/pre_migration_$(date +%Y%m%d)/
cp jobs.json backups/pre_migration_$(date +%Y%m%d)/
cp users.json backups/pre_migration_$(date +%Y%m%d)/
# ... copy all other JSON files

echo "✓ JSON backup created"
```

#### Step 2: Run Migration
```bash
# Execute migration script
python run_phase1_migration.py

# Expected output:
# Migration Starting...
# ✓ Loading JSON data...
# ✓ Migrating devices...
# ✓ Migrating users...
# ... etc
# Migration Complete!
```

#### Step 3: Validate Migration Results
```bash
# Check data was migrated
python << 'EOF'
from models.database import Database, Device, User, Job

db = Database()
session = db.get_session()

# Count records
device_count = session.query(Device).count()
user_count = session.query(User).count()
job_count = session.query(Job).count()

print(f"Devices migrated: {device_count}")
print(f"Users migrated: {user_count}")
print(f"Jobs migrated: {job_count}")

# Verify no duplicates
devices = session.query(Device).all()
device_ids = [d.id for d in devices]
print(f"Unique devices: {len(set(device_ids))}")
if len(set(device_ids)) != len(device_ids):
    print("✗ ERROR: Duplicate devices found!")
else:
    print("✓ No duplicates")

session.close()
EOF
```

### Phase 1F: Flask Integration Test

#### Step 1: Add Database Initialization to app.py
```python
# Add to top of app.py after imports:
from config.flask_database import DatabaseConfig, init_database_for_flask

# Add after Flask app creation:
db_config = DatabaseConfig()
init_database_for_flask(app, db_config)

print("✓ Database configured for Flask")
```

#### Step 2: Test Health Check Endpoint
```bash
# Start app and test endpoint
python app.py &

# In another terminal:
curl http://localhost:5000/health/db

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "pool_size": 20,
#   "active_connections": 1
# }
```

### Phase 1G: Connection Pool Performance Test

#### Step 1: Verify Connection Pooling
```bash
python << 'EOF'
from models.database import Database
import time

db = Database()

# Create multiple sessions to test pool
sessions = []
start_time = time.time()

for i in range(15):
    session = db.get_session()
    sessions.append(session)
    elapsed = time.time() - start_time
    print(f"Session {i+1}: {elapsed:.3f}s (from pool)")

# Close sessions
for session in sessions:
    session.close()

elapsed = time.time() - start_time
print(f"\n✓ Created 15 sessions in {elapsed:.2f}s")
print(f"✓ Connection pooling functional")
EOF
```

### Phase 1H: Data Integrity Verification

#### Step 1: Check All Tables
```bash
# Run comprehensive check
psql -U lrqa -d lrqa_v2_test << 'EOF'
-- Count all tables
SELECT COUNT(*) as total_rows FROM (
  SELECT COUNT(*) FROM devices UNION
  SELECT COUNT(*) FROM users UNION
  SELECT COUNT(*) FROM jobs UNION
  SELECT COUNT(*) FROM test_results UNION
  SELECT COUNT(*) FROM device_locks UNION
  SELECT COUNT(*) FROM saved_sequences UNION
  SELECT COUNT(*) FROM audit_logs UNION
  SELECT COUNT(*) FROM execution_context
) AS counts;

-- Verify foreign keys
\d+ devices
\d+ jobs
\d+ test_results

-- Check indexes
SELECT indexname FROM pg_indexes WHERE schemaname = 'public';
EOF
```

### Phase 1I: Error Handling & Recovery Test

#### Step 1: Test Rollback Procedures
```bash
# Create backup of schema
pg_dump -U lrqa -d lrqa_v2_test -s > config/database_schema_backup.sql

# Test rollback capability
psql -U lrqa -d lrqa_v2_test -c "DROP TABLE test_results;"

# Restore
psql -U lrqa -d lrqa_v2_test -f config/database_schema_backup.sql

echo "✓ Rollback tested successfully"
```

---

## Validation Checklist

- [ ] PostgreSQL 12+ installed and running
- [ ] Test database (lrqa_v2_test) created
- [ ] Schema imported (22 tables)
- [ ] SQLAlchemy models load without errors
- [ ] Database connection successful
- [ ] JSON data backed up
- [ ] Data migration completed
- [ ] Migration validation passed
- [ ] No duplicate records
- [ ] app.py imports database config
- [ ] Flask health check endpoint responds
- [ ] Connection pool working (15+ concurrent connections)
- [ ] All tables accessible via ORM
- [ ] Foreign keys intact
- [ ] Indexes created correctly
- [ ] Rollback procedures tested

---

## Common Issues & Troubleshooting

### Issue 1: PostgreSQL Connection Refused
```
Error: could not translate host name "localhost" to address
```

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl start postgresql

# Or check with:
sudo systemctl status postgresql

# If still failing, restart:
sudo systemctl restart postgresql
```

### Issue 2: Authentication Failed
```
Error: role "lrqa" does not exist
```

**Solution**:
```bash
# Create user as postgres:
sudo -u postgres psql -c "CREATE USER lrqa WITH PASSWORD 'lrqa_password';"

# Grant permissions:
sudo -u postgres psql -c "ALTER USER lrqa CREATEDB;"
```

### Issue 3: Database Already Exists
```
Error: database "lrqa_v2_test" already exists
```

**Solution**:
```bash
# Drop and recreate:
dropdb -U postgres lrqa_v2_test
createdb -U postgres -O lrqa lrqa_v2_test

# Or backup first:
pg_dump -U postgres lrqa_v2_test > backup_$(date +%Y%m%d_%H%M%S).sql
dropdb -U postgres lrqa_v2_test
```

### Issue 4: Schema Import Failed
```
Error: command not found - `psql`
```

**Solution**:
```bash
# Add PostgreSQL to PATH:
# Ubuntu/Debian:
sudo apt-get install postgresql-client

# macOS:
brew install postgresql
```

---

## Performance Baseline Targets

| Metric | Target | Method |
|--------|--------|--------|
| Connection time | <50ms | Time 10 connections |
| Query latency (p95) | <100ms | Test on 1000 records |
| Pool size exhaustion | >50 concurrent | Stress test |
| Connection reuse ratio | >95% | Check pool stats |
| Data migration time | <5s | Time full migration |

---

## Next Steps After Validation

1. **Phase 1 Complete**: Update memory with results
2. **Integration**: Add Flask database initialization to app.py
3. **Phase 3 Start**: Begin Modal UI conversion
4. **Phase 4 Plan**: Distributed sync architecture

---

## Contact & Support

For issues or questions:
1. Check troubleshooting section above
2. Review PHASE_1_DATABASE_MIGRATION.md for detailed docs
3. Check memory files: `/memories/repo/v2-blockers-and-issues.md`

---

**Testing Status**: ⏳ READY TO START  
**Created**: June 9, 2026  
**Last Updated**: June 9, 2026
