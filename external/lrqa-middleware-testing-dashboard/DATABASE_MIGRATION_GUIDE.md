# Database Migration Guide for IR Blaster & Power Control Configuration

## Overview
This guide explains how to add the new `ir_blaster_config` and `power_control_config` columns to the existing devices table if you're using a database (PostgreSQL/MySQL).

## Problem
Two new JSON columns were added to the Device model:
- `ir_blaster_config` - Stores IR Blaster (iTach) configuration
- `power_control_config` - Stores Power Control device configuration

## Solution

### Option 1: Automatic Migration (Flask-Migrate)
If you're using Flask-Migrate, run:

```bash
# Generate a new migration
flask db migrate -m "Add IR Blaster and Power Control configs to devices"

# Review the migration file (alembic/versions/)

# Apply the migration
flask db upgrade
```

### Option 2: Manual SQL Migration

#### For PostgreSQL:
```sql
ALTER TABLE devices ADD COLUMN ir_blaster_config JSONB DEFAULT NULL;
ALTER TABLE devices ADD COLUMN power_control_config JSONB DEFAULT NULL;

-- Add indexes for performance (optional)
CREATE INDEX idx_devices_ir_blaster ON devices USING GIN (ir_blaster_config);
CREATE INDEX idx_devices_power_control ON devices USING GIN (power_control_config);
```

#### For MySQL/MariaDB:
```sql
ALTER TABLE devices ADD COLUMN ir_blaster_config JSON DEFAULT NULL;
ALTER TABLE devices ADD COLUMN power_control_config JSON DEFAULT NULL;

-- Add indexes for performance (optional)
CREATE INDEX idx_devices_ir_blaster ON devices(ir_blaster_config(100));
CREATE INDEX idx_devices_power_control ON devices(power_control_config(100));
```

#### For SQLite (Development):
```sql
ALTER TABLE devices ADD COLUMN ir_blaster_config TEXT DEFAULT NULL;
ALTER TABLE devices ADD COLUMN power_control_config TEXT DEFAULT NULL;
```

### Option 3: Fresh Database Setup
If starting fresh or in development environment:

1. Delete existing database file (for SQLite):
   ```bash
   rm instance/app.db
   ```

2. Delete migrations directory:
   ```bash
   rm -rf migrations/
   ```

3. Reinitialize database:
   ```bash
   python
   >>> from app import app, db
   >>> with app.app_context():
   ...     db.create_all()
   >>> exit()
   ```

## Testing the Migration

### After migration, verify the columns exist:

**PostgreSQL:**
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'devices' 
ORDER BY ordinal_position;
```

**MySQL:**
```sql
DESCRIBE devices;
```

**SQLite:**
```sql
PRAGMA table_info(devices);
```

## Rollback (if needed)

### If using Flask-Migrate:
```bash
# List migrations
flask db history

# Downgrade to previous version
flask db downgrade
```

### Manual rollback (if using manual SQL):

**PostgreSQL:**
```sql
ALTER TABLE devices DROP COLUMN ir_blaster_config;
ALTER TABLE devices DROP COLUMN power_control_config;
```

**MySQL:**
```sql
ALTER TABLE devices DROP COLUMN ir_blaster_config;
ALTER TABLE devices DROP COLUMN power_control_config;
```

## Verification Steps

1. **Check database columns exist:**
   ```bash
   python -c "from models.database import Device; print([c.name for c in Device.__table__.columns])"
   ```

2. **Test adding a device with new configurations:**
   ```bash
   curl -X POST http://localhost:5000/api/devices \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Test-Device",
       "device_type": "XUMO",
       "lab_ip": "10.0.0.28",
       "lab_port": 10022,
       "lab_username": "root",
       "mac_address": "1C:2F:A2:30:35:B6",
       "location": "IND",
       "team_name": "QA",
       "is_rack_device": true,
       "rpi_config": {"rpi_ip": "10.138.17.42", "rpi_port": 60201, "rpi_username": "pi", "rpi_password": "password"},
       "ir_blaster_config": {"ir_blaster_ip": "10.0.0.50", "ir_blaster_port": 4998, "ir_connector": "1"},
       "power_control_config": {"power_type": "PDU", "power_ip": "10.0.0.51", "power_outlet": "5"}
     }'
   ```

3. **Verify devices API returns new fields:**
   ```bash
   curl http://localhost:5000/api/devices | jq '.devices[0] | {ir_blaster_config, power_control_config}'
   ```

## No Migration Required For:
- **JSON file storage** - devices.json automatically supports new fields
- **SQLite development** - new Python code manages schema
- **First-time deployments** - tables created fresh with new columns

## Impact Analysis

| Environment | Impact | Action Required |
|------------|--------|-----------------|
| Development (SQLite) | ✅ None | Just update code |
| Test Database (empty) | ✅ None | Just recreate |
| Production (PostgreSQL) | ⚠️ Requires migration | Run migration |
| Production (MySQL) | ⚠️ Requires migration | Run migration |
| FallbackJSON storage | ✅ None | None required |

## Safety Notes

✅ **Safe Operations:**
- Columns default to NULL, won't break existing queries
- JSON columns are backward compatible
- No data loss for existing devices
- All new configurations are optional

⚠️ **Considerations:**
- Test migrations in staging first
- Backup database before production migration
- No downtime required for migration
- Existing devices will have NULL values for new fields

## Support

If migration fails or tables already exist:

1. Check table schema exists:
   ```bash
   python models/database.py --check-tables
   ```

2. Reset database (development only):
   ```bash
   python -c "from models.database import init_db; init_db()"
   ```

3. Enable debug logging:
   ```python
   import logging
   logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
   ```

---

**Status:** ✅ Migration guide complete
**Backward Compatible:** Yes
**Data Loss Risk:** No
**Rollback Possible:** Yes
