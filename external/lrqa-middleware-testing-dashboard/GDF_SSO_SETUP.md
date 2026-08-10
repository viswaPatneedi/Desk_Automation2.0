# GDF SSO Authentication Setup Guide

## Overview

The application now supports Comcast GDF ECATS API for sending IR commands to GDF_RACK devices. Since the API requires SSO (Single Sign-On) authentication, you must configure your GDF credentials.

## What Changed

### New Files Created:
1. **`services/gdf_auth_service.py`** - Handles SSO login and maintains authenticated session
2. **`config/config_gdf_api.py`** - Configuration for GDF API endpoints and credentials

### Modified Files:
1. **`methods/method_gdf_ir_test.py`** - Now uses authenticated GDF service instead of unauthenticated requests

## HTTP 401 Error Fix

**Previous Issue:**
```
curl "https://app.catsprd.comcast.net/gdf/gateway/rest/settop/04:B8:6A:16:0D:AB/ir/pressKey?command=HOME&keySet=LC103"
# Returns: HTTP 401 Unauthorized
```

**Root Cause:** API requires SSO authentication (session token or credentials)

**Solution:** Authenticate with username/password and maintain authenticated session

## Setup Instructions

### Step 1: Get Your GDF Credentials

Contact your Comcast administrator to get SSO credentials for:
- **GDF Username** - Your Comcast SSO username
- **GDF Password** - Your Comcast SSO password

### Step 2: Set Environment Variables

Add these to your `.env` file or export them in your shell:

```bash
# Option A: Add to .env file in project root
echo "GDF_USERNAME=your-username" >> .env
echo "GDF_PASSWORD=your-password" >> .env

# Option B: Export in shell
export GDF_USERNAME="your-username"
export GDF_PASSWORD="your-password"
```

**Security Notes:**
- ⚠️ Never commit credentials to Git
- Use `.env` file with `.gitignore` entry
- For production, use secure credential management (AWS Secrets, Vault, etc.)

### Step 3: Restart the Application

```bash
pkill -f "python3 app.py"
sleep 2
source venv/bin/activate
nohup python3 app.py > /tmp/app.log 2>&1 &
```

### Step 4: Verify Configuration

Check logs for successful authentication:

```bash
tail -f /tmp/app.log | grep "GDF AUTH"
```

Expected output:
```
[GDF AUTH] Attempting SSO login for user: your-username
✓ [GDF AUTH] Authentication successful (HTTP 200)
✓ [GDF AUTH] Auth token obtained
```

## How It Works

### Authentication Flow

```
1. First IR command sent
    ↓
2. Check if already authenticated
    ↓
3. If not: Call GDFAuthService.login_with_credentials()
    ↓
4. POST to: https://app.catsprd.comcast.net/gdf/gateway/rest/auth/login
    with: {"username": "...", "password": "..."}
    ↓
5. If HTTP 200: Extract auth token or save session cookies
    ↓
6. Use authenticated session for all subsequent IR commands
    ↓
7. If 401 received: Auto-retry with re-authentication
```

### Session Management

- **Session Persistence**: Cookies and tokens maintained in `requests.Session()`
- **Auto-Retry**: If 401 received, automatically re-authenticate and retry
- **Timeout**: 15 seconds for authentication, 10 seconds for IR commands
- **Retries**: 3 attempts with backoff for network failures

## Usage

### From Python Code

```python
from services.gdf_auth_service import get_gdf_auth_service

# Get authenticated service
gdf_auth = get_gdf_auth_service()

# Login (automatic if not already authenticated)
success, message, token = gdf_auth.login_with_credentials()

# Send IR command
success, status_code, response = gdf_auth.send_ir_command(
    mac_address="04:B8:6A:16:0D:AB",
    ir_key="HOME",
    keyset="LC103"  # SKYSTREAM device
)
```

### From Web API

```bash
# Send IR test (automatically handles authentication)
curl -X POST http://localhost:11079/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "10.0.0.28",
    "method": "ir_test",
    "selected_keys": ["HOME", "POWER"],
    "device_type": "SKYSTREAM",
    "mac_address": "04:B8:6A:16:0D:AB"
  }'
```

## Testing the Integration

### Test 1: Manual Authentication

```python
python3
>>> from services.gdf_auth_service import get_gdf_auth_service
>>> auth = get_gdf_auth_service()
>>> success, msg, token = auth.login_with_credentials()
>>> print(f"Authenticated: {success}")
>>> print(f"Message: {msg}")
```

### Test 2: Direct curl (After Obtaining Token)

```bash
# If token-based auth:
curl -H "Authorization: Bearer $TOKEN" \
  "https://app.catsprd.comcast.net/gdf/gateway/rest/settop/04:B8:6A:16:0D:AB/ir/pressKey?command=HOME&keySet=LC103"

# If cookie-based auth:
# Cookies are automatically handled by requests.Session()
```

### Test 3: Application Logs

Check application logs for IR test execution:

```bash
# Watch for GDF IR activity
tail -f /tmp/app.log | grep -E "GDF|IR TEST"
```

Expected output:
```
[GDF AUTH] Attempting SSO login for user: techuser
✓ [GDF AUTH] Authentication successful (HTTP 200)
[GDF API] Sending key 'HOME' via GDF ECATS (SSO authenticated)...
✓ [GDF IR] Key 'HOME' sent successfully
```

## Troubleshooting

### 401 Unauthorized After Setup

**Problem:** Still getting HTTP 401 errors

**Solutions:**
1. Verify credentials are correct
   ```bash
   echo $GDF_USERNAME $GDF_PASSWORD
   ```

2. Check if passwords contain special characters (may need escaping)
   ```bash
   # Test credentials directly
   python3 -c "from services.gdf_auth_service import get_gdf_auth_service; \
   auth = get_gdf_auth_service(); print(auth.gdf_username)"
   ```

3. Verify environment variables are loaded
   ```bash
   # Check .env file exists and has GDF_USERNAME, GDF_PASSWORD
   cat .env | grep GDF
   ```

### Connection Timeout

**Problem:** "Timeout: ECATS endpoint" or "Connection error"

**Solutions:**
1. Check network connectivity to app.catsprd.comcast.net
   ```bash
   curl -v https://app.catsprd.comcast.net/gdf/gateway/rest/auth/login
   ```

2. Verify SSL certificates
   ```bash
   # This should show valid certificate
   openssl s_client -connect app.catsprd.comcast.net:443
   ```

3. Check if running behind corporate proxy
   - Add proxy configuration to requests.Session() if needed

### Authentication Token Expires

**Problem:** Works initially, but fails after some time

**Current**: Auto-retry with re-authentication handles this
- System detects 401 and automatically re-authenticates
- Transparent to user

**Future Enhancement**: Could add session refresh logic

## API Response Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | IR command sent |
| 401 | Unauthorized | Auto-retry with re-auth |
| 403 | Forbidden | User not authorized for device |
| 404 | Not Found | Invalid MAC address |
| 500 | Server Error | GDF service issue |
| 503 | Unavailable | GDF service down |

## Security Best Practices

✅ **Do:**
- Store credentials in `.env` file (add to `.gitignore`)
- Use environment variables for secrets
- Enable SSL verification (already enabled)
- Rotate credentials periodically
- Monitor authentication logs

❌ **Don't:**
- Commit `.env` file to Git
- Hardcode credentials in source code
- Use test credentials in production
- Share credentials between users/services
- Store passwords in application config

## Related Configuration

### GDF API Endpoints Used

```python
GDF_API_BASE = "https://app.catsprd.comcast.net/gdf/gateway/rest"
GDF_AUTH_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/auth/login"
GDF_SETTOP_ENDPOINT = "https://app.catsprd.comcast.net/gdf/gateway/rest/settop"
```

### KeySet Mappings

```python
PR1_T2  -> XUMO/ELEMENT devices
LC103   -> SKYSTREAM devices
```

## Support

For issues or questions about GDF SSO integration, contact:
- Comcast GDF Support: [contact info]
- Application Support: Project maintainers

---

**Last Updated:** August 5, 2026  
**Version:** 1.0 - Initial GDF SSO Authentication
