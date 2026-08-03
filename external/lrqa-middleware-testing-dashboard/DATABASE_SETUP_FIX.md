# Database Setup & Credentials Management Fix

## Problem Summary

When accessing "App Credentials Management", users see a **500 INTERNAL SERVER ERROR** with PostgreSQL authentication failure:

```
Error: (psycopg2.OperationalError) connection to server at "localhost" (127.0.0.1), port 5432
failed: FATAL: password authentication failed for user "postgres"
```

### Root Causes Identified

1. **Conflicting Database Defaults**: 
   - `config/flask_database.py` expects user `lrqa` with password `lrqa_password`
   - `models/database.py` was using hardcoded defaults `postgres:postgres` (❌ WRONG)
   - These mismatches caused connection failures

2. **Missing/Incorrect .env Configuration**:
   - PostgreSQL credentials must be set in `.env` file
   - If not configured, application uses incorrect default credentials

3. **No Error Messages**:
   - Previous error handling just returned generic 500 errors
   - Users had no guidance on how to fix the problem

---

## Fixes Applied

### ✅ Fix 1: Unified Database Defaults

**File**: `models/database.py` (Lines 20-25)

Changed database defaults to match Flask configuration:

```python
# BEFORE (❌ Wrong)
DB_NAME = os.environ.get('DB_NAME', 'desk_automation_v2')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

# AFTER (✅ Fixed)
DB_NAME = os.environ.get('DB_NAME', 'lrqa_v2')
DB_USER = os.environ.get('DB_USER', 'lrqa')
DB_PASSWORD = os.environ.get('DB_PASSWORD', 'lrqa_password')
```

### ✅ Fix 2: Better Error Messages

**File**: `controllers/app_credential_controller.py`

Added detailed error messages to help users identify and fix the issue:

- **Authentication failures**: Shows that .env configuration is needed
- **Connection failures**: Suggests checking PostgreSQL service status
- **Table not found**: Instructs on database initialization
- **Generic errors**: Provides debugging hints

### ✅ Fix 3: Database Table Initialization

**File**: `app.py` (Lines 103-115)

Added automatic database table creation on app startup:

```python
# Initialize database tables on startup
try:
    initialize_database_on_startup(app)
    print("✓ Database tables created/verified")
except Exception as e:
    print(f"⚠ Warning: Database table initialization: {str(e)}")
```

---

## How to Configure

### Option 1: Use Environment Variables (Recommended)

Edit your **`.env`** file in the project root:

```bash
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=lrqa_v2
DB_USER=lrqa
DB_PASSWORD=your-secure-password-here
```

### Option 2: Create PostgreSQL User & Database

If the PostgreSQL user doesn't exist, create it:

```bash
# Connect as PostgreSQL admin (requires sudo)
sudo -u postgres psql

# Inside psql console:
CREATE USER lrqa WITH PASSWORD 'your-secure-password-here';
ALTER ROLE lrqa CREATEDB;
CREATE DATABASE lrqa_v2 OWNER lrqa;
GRANT ALL PRIVILEGES ON DATABASE lrqa_v2 TO lrqa;

# Exit psql
\q
```

### Option 3: Test Connection

Verify your database connection:

```bash
psql -h localhost -U lrqa -d lrqa_v2 -c "SELECT 1"
```

Should output:
```
 ?column? 
----------
        1
(1 row)
```

---

## Testing the Fix

1. **Restart the Flask Application**:
   ```bash
   pkill -f "python app.py"  # Stop current app
   python app.py  # Start app - should see:
   # ✓ Database initialized for Flask
   # ✓ Database tables created/verified
   ```

2. **Open App Credentials Management**:
   - Go to dashboard → Click "⚙️ Settings" → "App Credentials Management"
   - Should now load successfully without 500 errors

3. **Add a Test Credential**:
   - App Name: Netflix
   - Team Name: Your-Team
   - Username: test@example.com
   - Password: test123
   - Should show success message

4. **View Existing Credentials**:
   - List should display:
     - App name (Netflix, Disney+, etc.)
     - Team name
     - Username
     - Edit/Primary/Delete buttons
     - Usage statistics

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `password authentication failed for user "lrqa"` | Check your .env file has correct DB_PASSWORD, or create the user with `CREATE USER lrqa...` |
| `could not connect to server on "localhost" (127.0.0.1), port 5432` | Ensure PostgreSQL is running: `pg_isready` should return "accepting connections" |
| `table "app_credentials" does not exist` | Restart the Flask app - it should auto-create tables on startup |
| `FATAL: database "lrqa_v2" does not exist` | Create the database: `createdb -U postgres lrqa_v2` |
| Still getting 500 errors | Check Flask console output for detailed error messages |

---

## Environment Variable Reference

| Variable | Default | Example |
|----------|---------|---------|
| `DB_HOST` | `localhost` | `127.0.0.1` |
| `DB_PORT` | `5432` | `5432` |
| `DB_NAME` | `lrqa_v2` | `lrqa_v2` |
| `DB_USER` | `lrqa` | `lrqa` |
| `DB_PASSWORD` | `lrqa_password` | `mySecurePass123!` |
| `DB_POOL_SIZE` | `20` | `20` |
| `DB_MAX_OVERFLOW` | `40` | `40` |
| `DB_POOL_PRE_PING` | `true` | `true` |
| `DB_ECHO` | `false` | `false` |

---

## Related Files

- **Database Config**: `config/flask_database.py` (Flask setup)
- **Database Models**: `models/database.py` (SQLAlchemy ORM)
- **Credentials Controller**: `controllers/app_credential_controller.py` (CRUD logic)
- **Credentials Model**: `models/app_credential.py` (AppCredential ORM model)
- **Environment Template**: `.env.example` (Reference for all settings)

---

## Notes for Deployment

- **Never commit the .env file** - It contains sensitive credentials
- **Always use environment variables** in production
- **Use AWS Secrets Manager** for hosting on AWS (recommended)
- **Set secure passwords** with special characters and proper strength
- **Enable connection pooling** for production (DB_POOL_SIZE, DB_MAX_OVERFLOW)

---

**Last Updated**: 2026-08-03  
**Status**: ✅ Fixed and tested
