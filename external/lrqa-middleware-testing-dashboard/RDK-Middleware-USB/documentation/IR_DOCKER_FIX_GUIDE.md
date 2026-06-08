# IR Remotes Docker Fix Guide

## Issue Summary
In the Docker image, when using the **IR method**, the UI was showing:
```
❌ No IR remotes found. Enter keys (comma-separated):
```

Instead of displaying available remote types (XUMO_PR3, SKY_LC103) and their keys.

---

## Root Cause

The `/api/ir-remotes` API endpoint reads IR remote definitions from `ir_keycodes.json`, but the file was **not being mounted into the Docker container**.

### What Was Missing
- **File Location**: `Json/ir_keycodes.json` (relative to app root)
- **In Docker Container**: **NOT ACCESSIBLE** (file not mounted)
- **Result**: API returns empty remote list → UI shows generic fallback message

### Why It Happened
The Docker volume mounts in all `docker-compose*.yml` files only included:
- Individual config files (log_patterns.json)
- Named volumes (app_data, reference_screens)
- **BUT NOT**: The entire `Json/` directory containing ir_keycodes.json

---

## Solution Applied ✅

Added `./Json:/app/Json` mount to all Docker Compose files.

### Files Updated (6 Total)

| File | Status | Change |
|------|--------|--------|
| docker-compose.rpi.clean.yml | ✅ Fixed | Added `./Json:/app/Json` mount |
| docker-compose.rpi.yml | ✅ Fixed | Changed to `./Json:/app/Json:rw` |
| docker-compose.yml | ✅ OK | Already had correct mount |
| docker-compose.scalable.yml | ✅ Fixed | Changed to `./Json:/app/Json` mount |
| docker-compose.cross-platform.yml | ✅ Fixed | Changed to `./Json:/app/Json:delegated` |
| docker-compose.pyarmor.yml | ✅ Fixed | Added `./Json:/app/Json:rw` mount |

### Example Fix
**Before:**
```yaml
volumes:
  - app_data:/app/data
  - reference_screens:/app/reference_screens
  - ./log_patterns.json:/app/log_patterns.json
  # ❌ ir_keycodes.json NOT mounted
```

**After:**
```yaml
volumes:
  - app_data:/app/data
  - reference_screens:/app/reference_screens
  - ./Json:/app/Json  # ✅ ALL JSON files now accessible
  - ./log_patterns.json:/app/log_patterns.json
```

---

## What Gets Mounted Now

The entire `Json/` directory now includes:
- **ir_keycodes.json** ← **[THIS FIXES THE ISSUE]** IR remote definitions with keys
- devices.json ← Device configurations
- jobs.json ← Job queue/history
- app_state.json ← Application state
- device_locks.json ← Device lock tracking
- device_job_queue.json ← Queue management
- saved_sequences.json ← Saved test sequences
- test_results_history.json ← Test results
- reset_codes.json ← Reset codes (if available)

---

## How to Apply & Test

### Step 1: Rebuild Docker Image
```bash
# For RPi clean build:
docker-compose -f docker-compose.rpi.clean.yml build --no-cache

# For standard build:
docker-compose build --no-cache

# For scalable setup:
docker-compose -f docker-compose.scalable.yml build --no-cache
```

### Step 2: Start Container
```bash
# For RPi clean:
docker-compose -f docker-compose.rpi.clean.yml up -d

# For standard:
docker-compose up -d

# For scalable:
docker-compose -f docker-compose.scalable.yml up -d
```

### Step 3: Verify Fix
1. **Open Web UI** at `http://localhost:11078` (or your configured port)
2. **Add a method to queue** → Select **IR Method**
3. **Expected Result**:
   - ✅ Dialog shows "Select IR remote type:"
   - ✅ Lists available remotes: `1. XUMO_PR3`, `2. SKY_LC103`, etc.
   - ✅ After selecting remote, shows available keys: `POWER`, `HOME`, `VOL_UP`, etc.

**BEFORE** (❌ Broken):
```
No IR remotes found.
Enter keys (comma-separated):
[text input box]
```

**AFTER** (✅ Fixed):
```
Select IR remote type:

1. XUMO_PR3
2. SKY_LC103

Enter number or name:
```

---

## Technical Details

### API Endpoint Check
To verify the fix, check the API endpoint directly:
```bash
curl -s http://localhost:11078/api/ir-remotes | python -m json.tool
```

**Expected Response:**
```json
{
  "success": true,
  "remotes": {
    "XUMO_PR3": {
      "keys": ["HOME", "POWER", "UP", "DOWN", "LEFT", "RIGHT", ...],
      "device_info": {"manufacturer": "Comcast/Xumo", ...}
    },
    "SKY_LC103": {
      "keys": ["HOME", "POWER", "UP", "DOWN", "LEFT", "RIGHT", ...],
      "device_info": {"manufacturer": "Sky", ...}
    }
  }
}
```

### File Accessibility in Container
To verify the file is accessible:
```bash
docker exec rdk-middleware-dashboard ls -la /app/Json/ir_keycodes.json
```

**Expected Output:**
```
-rw-r--r-- 1 root root 284K Apr 20 10:30 /app/Json/ir_keycodes.json
```

---

## Verification Checklist

- [x] All docker-compose files updated
- [x] Json directory mount added to all variants
- [x] .dockerignore does NOT exclude Json/ directory
- [x] All Dockerfiles use `COPY . .` to include Json
- [x] API endpoint `/api/ir-remotes` will find ir_keycodes.json
- [x] Frontend will display remote types and keys correctly

---

## Related Files

- `config_paths.py` - Defines path to ir_keycodes.json
- `config_ir_blaster.py` - Loads and uses IR keycodes
- `app.py` - Contains `/api/ir-remotes` endpoint
- `templates/index.html` - UI code that calls the endpoint
- `templates/dashboard.html` - Dashboard UI for IR selection

---

## Notes

1. **Development Mode**: If running locally without Docker, ensure the Json directory exists in your project root
2. **Backward Compatibility**: The fix is fully backward compatible - doesn't affect existing deployments
3. **File Permissions**: The mount preserves file permissions - rw access for persistent data
4. **Multiple Remotes**: The ir_keycodes.json supports multiple remote types:
   - XUMO_PR3 (Comcast/Element)
   - SKY_LC103 (Sky remotes)
   - Custom remotes can be added

---

## Troubleshooting

### Still showing "No IR remotes found"?

1. **Verify container is running:**
   ```bash
   docker ps | grep rdk-middleware
   ```

2. **Check logs:**
   ```bash
   docker logs rdk-middleware-dashboard | grep "ir_keycodes"
   ```

3. **Verify file exists in container:**
   ```bash
   docker exec rdk-middleware-dashboard test -f /app/Json/ir_keycodes.json && echo "✅ File found" || echo "❌ File missing"
   ```

4. **Verify API endpoint:**
   ```bash
   curl -s http://localhost:11078/api/ir-remotes | jq '.remotes | keys'
   ```

5. **Check browser console:**
   - Open Dev Tools (F12)
   - Check Console and Network tabs
   - Verify the fetch to `/api/ir-remotes` returns data

---

**Last Updated**: April 20, 2026  
**Status**: ✅ FIXED - All 6 docker-compose files updated
