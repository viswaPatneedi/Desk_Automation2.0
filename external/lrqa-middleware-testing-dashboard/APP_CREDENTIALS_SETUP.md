# App Credentials System - Setup & Deployment Guide

## Quick Start (5 minutes)

### Step 1: Apply Database Migration
```bash
# Connect to your PostgreSQL database
psql -U postgres -h localhost -d desk_automation_v2 < migrations/001_create_app_credentials_table.sql

# Or manually run the SQL from the migrations file in psql
```

### Step 2: Verify Installation
```bash
# Check table was created
psql -U postgres -h localhost -d desk_automation_v2
\dt app_credentials

# Should return the table structure
```

### Step 3: Designate Super Admin
```sql
-- Set a user as super admin
UPDATE users 
SET is_super_admin = TRUE 
WHERE username = 'your_admin_username';

-- Verify
SELECT username, is_super_admin FROM users WHERE is_super_admin = TRUE;
```

### Step 4: Restart Flask App
```bash
# Kill existing app processes
pkill -9 -f "python app.py"

# Restart with fresh imports
cd /path/to/lrqa-middleware-testing-dashboard
source venv/bin/activate
python app.py &
```

### Step 5: Test in UI
1. Login as super admin
2. Click User Menu (top right) → Admin → App Credentials
3. Click "Add New Credential"
4. Fill in Netflix credentials and save
5. Create Netflix execution and verify auto-population

---

## Deployment Checklist

- [ ] Database migration applied (`001_create_app_credentials_table.sql`)
- [ ] Users table has `is_super_admin` and `is_team_admin` columns
- [ ] Indexes created for query performance
- [ ] Super admin role assigned to at least one user
- [ ] Flask app restarted
- [ ] Tested credential creation in UI
- [ ] Tested Netflix auto-population
- [ ] Verified credentials not leaking in logs
- [ ] API endpoints responding (`GET /api/admin/app-credentials`)

---

## Architecture Files Reference

```
models/
├── app_credential.py              ← AppCredential ORM model
├── database.py                    ← User model updated (is_super_admin field)
└── __init__.py                    ← Updated to export AppCredential

controllers/
└── app_credential_controller.py   ← Business logic (CRUD, access control)

methods/
└── method_netflix_playback.py     ← Updated to fetch credentials from DB

templates/
├── index.html                     ← UI enhancements
└── modals/app_credentials/
    └── management.html            ← Super admin credentials panel

migrations/
└── 001_create_app_credentials_table.sql  ← Database schema

app.py                             ← 8 new API endpoints added

APP_CREDENTIALS_IMPLEMENTATION.md   ← Full documentation
```

---

## Configuration Files

No additional config files needed. Everything is managed through:
- PostgreSQL database
- API endpoints (auto-authenticated via Flask-Login)
- UI modals (auto-visible for super admins only)

---

## API Reference

### Authentication
All endpoints require:
- `@login_required` decorator
- `is_super_admin=True` for admin endpoints
- CSRF token in POST/PUT/DELETE requests

### Example API Calls

```bash
# Get all Netflix credentials (requires super admin)
curl -X GET http://localhost:5000/api/admin/app-credentials?app_name=netflix \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create new credential
curl -X POST http://localhost:5000/api/admin/app-credentials \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "netflix",
    "username": "user@netflix.com",
    "password": "secure_password",
    "login_url": "http://netflix.com/tv2",
    "team_name": "QA-Team",
    "is_primary": true
  }'

# Fetch primary Netflix credential for method execution
curl -X GET http://localhost:5000/api/admin/app-credentials/by-app/netflix?team_name=QA-Team
```

---

## Troubleshooting

### Issue: "Module not found: app_credential"
**Solution**: Ensure `models/app_credential.py` exists and is importable
```bash
# Check file exists
ls -la models/app_credential.py

# Check import works
python3 -c "from models.app_credential import AppCredential; print('OK')"
```

### Issue: "AppCredential table doesn't exist"
**Solution**: Run migrations and verify table creation
```bash
# Check table exists
psql -U postgres -h localhost -d desk_automation_v2 -c "\dt app_credentials"

# If missing, re-run migration
psql -U postgres -h localhost -d desk_automation_v2 < migrations/001_create_app_credentials_table.sql
```

### Issue: "Unauthorized" when accessing credentials admin
**Solution**: Verify super admin role
```bash
# In psql, check user roles
SELECT username, is_super_admin, is_admin FROM users WHERE username = 'your_user';

# If not super admin, update:
UPDATE users SET is_super_admin = TRUE WHERE username = 'your_user';
```

### Issue: Netflix credentials not auto-loading
**Solution**: Check browser console and API responses
```javascript
// In browser DevTools console
fetch('/api/admin/app-credentials/by-app/netflix?team_name=QA-Team')
  .then(r => r.json())
  .then(d => console.log(d))
```

---

## Security Hardening

### 1. Password Encryption
For production, encrypt passwords:
```python
# In app_credential_controller.py, add:
from cryptography.fernet import Fernet

# Encrypt before store:
cipher = Fernet(key)
encrypted_pwd = cipher.encrypt(password.encode())
```

### 2. Database Encryption
Enable PostgreSQL encryption at rest:
```bash
# Add to postgresql.conf:
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
```

### 3. Audit Logging
Sensitive operations logged and monitored:
- Who created/modified credentials
- When credentials were last used
- Failed access attempts

### 4. Rate Limiting
Add rate limiting to prevent brute force:
```python
from flask_limiter import Limiter

limiter = Limiter(app)

@app.route('/api/admin/app-credentials', methods=['POST'])
@limiter.limit("10 per minute")
def create_credential():
    ...
```

---

## Monitoring & Maintenance

### Monthly Tasks
- [ ] Review credential usage statistics
- [ ] Rotate old credentials (6+ months)
- [ ] Check for unused credentials (0 usage_count in 3 months)
- [ ] Monitor failed authentication attempts in logs

### Metrics to Track
- Credentials per app (target: 1-3 per app/team)
- Usage distribution (which credentials used most)
- Credential age (oldest should be rotated)
- Failed access log patterns

### Sample Query to Find Unused Credentials
```sql
SELECT 
    credential_id,
    app_name,
    team_name,
    created_at,
    usage_count,
    CASE 
        WHEN usage_count = 0 THEN 'NEVER USED'
        WHEN CURRENT_TIMESTAMP - last_used_at > interval '90 days' THEN 'STALE'
        ELSE 'ACTIVE'
    END as status
FROM 
    app_credentials
WHERE 
    is_active = TRUE
ORDER BY 
    usage_count ASC;
```

---

## Changelog

### Version 1.0 (2026-07-26)
- ✅ Initial release
- ✅ AppCredential ORM model
- ✅ CRUD API endpoints
- ✅ Super admin UI
- ✅ Netflix integration
- ✅ Usage tracking

### Planned for v2.0
- [ ] Credential encryption at rest
- [ ] Support for more apps (Disney+, Hulu, Prime, YouTube)
- [ ] Credential rotation policies
- [ ] Advanced audit logging
- [ ] Credential usage dashboard
- [ ] Import/export credentials
- [ ] Credential templates

---

## Support

For issues or questions:
1. Check APP_CREDENTIALS_IMPLEMENTATION.md for full documentation
2. Review browser console logs (DevTools F12)
3. Check Flask app logs: `tail -f /tmp/flask.log`
4. Query database directly for troubleshooting

---

**Ready to deploy!** 🚀

Follow the Quick Start section above to get credentials management up and running in minutes.
