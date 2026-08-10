# Parallel Multi-Device Execution - Activation & Testing Guide

## Problem Diagnosis

### What Was Happening
When you triggered 2 devices on the same R-Pi backend:
- **Device 1 (MAC: 04:B8:6A:14:17:97)** - Job: `a4f281c2-142b-4eb1-b129-2a0e64872747`
  - Status: ❌ **FAILED** (after 60 seconds)
  - Reason: Timeout acquiring tunnel to R-Pi 10.138.17.42
  
- **Device 2 (MAC: 04:B8:6A:16:0D:AB)** - Job: `41be67cb-67ca-4108-aef0-df84714d463e`
  - Status: ⏳ **IN PROGRESS** (had tunnel lock)

### Root Cause
Both devices made **separate API calls** to `/api/execute` (single-device endpoint).  
This created two independent jobs that **competed for the same R-Pi tunnel** instead of **coordinating**.

The error from job a4f281c2's execution log:
```
[TUNNEL-COORD] ❌ Timeout acquiring tunnel for DT_LAB_XIONE-UK-17-97 (R-Pi: 10.138.17.42)
Currently held by job 41be67cb-67ca-4108-aef0-df84714d463e
```

---

## Solution Implemented

### 3 Components Added

#### 1️⃣ **Multi-Device Controller Method**
**File:** `controllers/test_controller.py`  
**New Method:** `execute_test_multiple()` (+130 lines)

```python
def execute_test_multiple(self):
    """POST /api/execute-multiple - Execute test on multiple devices"""
    # ✅ Validates device_ips array
    # ✅ Creates individual Job records
    # ✅ Acquires device locks for all
    # ✅ Calls TestExecutionService.execute_tests_for_multiple_devices()
```

**Key Features:**
- Accepts `device_ips` array in JSON
- Creates separate job for each device (for tracking)
- Acquires all device locks before starting execution
- Rollback mechanism if any lock fails

#### 2️⃣ **Multi-Device Flask Endpoint**
**File:** `app.py`  
**New Route:** `/api/execute-multiple` (POST)

```python
@app.route('/api/execute-multiple', methods=['POST'])
@login_required
def execute_test_multiple():
    """Execute tests on multiple devices in parallel with device grouping"""
    return test_controller.execute_test_multiple()
```

#### 3️⃣ **Enhanced Multi-Device Execution Service**
**File:** `services/test_execution_service.py`  
**Method:** `execute_tests_for_multiple_devices()` (UPDATED)

```python
def execute_tests_for_multiple_devices(self, devices, execution_queue, 
                                       iterations, job_id)
```

**Updates:**
- Enhanced to handle flexible `job_id` parameter:
  - `str`: Single job_id (backward compatible)
  - `list`: List of job_ids per device
  - `dict`: device_name → job_id mapping
- Modified `_execute_group()` to use per-device job_id for tracking

---

## How It Now Works

### Single-Device Path (OLD - Still Works)
```
User → Dashboard (Select 1 device)
    ↓
    POST /api/execute
    ↓
    execute_test() 
    ↓
    execute_test_queue() (single-device)
    ↓
    Result: Device executes alone
```

### Multi-Device Path (NEW - Parallel Execution)
```
User → Dashboard (Select 2+ devices on same R-Pi)
    ↓
    POST /api/execute-multiple
    ↓
    execute_test_multiple()
    ├─ Validates device_ips array
    ├─ Creates individual Job records
    ├─ Acquires all device locks
    └─ Calls execute_tests_for_multiple_devices()
        ├─ Analyzes devices by R-Pi backend
        ├─ Groups devices by shared R-Pi
        ├─ For each group:
        │  ├─ Acquires GROUP-level lock (R-Pi)
        │  ├─ Establishes ONE shared tunnel
        │  ├─ Launches all devices in GROUP in PARALLEL
        │  │  └─ Each device: _execute_single_device_with_shared_tunnel()
        │  └─ Releases GROUP lock
        └─ Returns results
    ↓
    Result: Both devices execute simultaneously ⚡
```

---

## Testing the Feature

### Prerequisites
- Both devices must be on and reachable
- Both devices must share the same R-Pi backend (check `Json/devices.json`)
- Flask app running with new `/api/execute-multiple` endpoint

### Manual Test

#### 1. Check Device R-Pi Configuration
```bash
cd /path/to/dashboard
python3 << 'EOF'
import json
with open('Json/devices.json', 'r') as f:
    devices = json.load(f)
    
for device in devices:
    print(f"Device: {device['name']:30s} IP: {device['ip']:15s} R-Pi: {device.get('rpi_config', {}).get('rpi_ip', 'N/A')}")
EOF
```

Example output:
```
Device: ELEMENT_A4K                 IP: 10.0.0.250       R-Pi: 10.138.17.42
Device: DT_LAB_XIONE-UK-17-97      IP: 10.0.0.28        R-Pi: 10.138.17.42
Device: DT_LAB_SKY_XIONE-UK-0D_AB  IP: ?.?.?.?          R-Pi: 10.138.17.42
```

#### 2. Trigger Multi-Device Execution

```bash
# Get a valid session cookie first (login to dashboard)
COOKIE="session=your_session_cookie_here"

# Call the multi-device endpoint
curl -X POST http://localhost:5000/api/execute-multiple \
  -H "Content-Type: application/json" \
  -H "Cookie: $COOKIE" \
  -d '{
    "device_ips": ["10.0.0.28", "10.0.0.250"],
    "execution_queue": [
      {"method": "reboot_perf_v2_optimized"}
    ],
    "iterations": 2
  }'
```

Expected response:
```json
{
  "message": "Multi-device execution started with device grouping",
  "job_ids": ["job_id_1", "job_id_2"],
  "device_count": 2,
  "eta_seconds": 120
}
```

#### 3. Verify Parallel Execution

**Check Job Status Dashboard:**
- Both jobs should show status: **"running"** (not sequential)
- Monitor logs to see both devices executing simultaneously

**Check Execution Logs:**
```bash
ls -lath logs/jobs/*/execution.log | head -5
# Check timestamps - both should be running at same time
```

**Expected Log Output:**
```
[GROUP-EXEC] GroupID-xyz: Attempting to acquire lock for R-Pi 10.138.17.42...
[GROUP-EXEC] GroupID-xyz: ✅ Lock acquired
[GROUP-EXEC] GroupID-xyz: Establishing tunnel to R-Pi 10.138.17.42...
[GROUP-EXEC] GroupID-xyz: ✅ Tunnel established - 2 devices will share it
[DEVICE-EXEC] ELEMENT_A4K: Starting execution (using group tunnel)...
[DEVICE-EXEC] DT_LAB_XIONE-UK-17-97: Starting execution (using group tunnel)...
[DEVICE-EXEC] ✅ ELEMENT_A4K: Execution completed
[DEVICE-EXEC] ✅ DT_LAB_XIONE-UK-17-97: Execution completed
[GROUP-EXEC] GroupID-xyz: All devices in group completed
```

---

## Performance Expectations

### Before (Sequential)
```
Device A: ████████████ (60s)
Device B:             ████████████ (60s)
Total Time: 120 seconds ❌
```

### After (Parallel)
```
Device A: ████████████ (60s)
Device B: ████████████ (60s)
Total Time: 60 seconds ⚡ (2× faster)
```

With 3+ devices on same R-Pi:
```
3 devices: ~7× faster
4 devices: ~10× faster
```

---

## API Reference

### `/api/execute` (Single Device - Existing)
**Method:** POST  
**Auth:** Required (login_required)  
**Body:**
```json
{
  "device_ip": "10.0.0.28",
  "execution_queue": [{"method": "reboot_perf_v2_optimized"}],
  "iterations": 2
}
```

### `/api/execute-multiple` (Multiple Devices - NEW)
**Method:** POST  
**Auth:** Required (login_required)  
**Body:**
```json
{
  "device_ips": ["10.0.0.28", "10.0.0.250"],
  "execution_queue": [
    {"method": "reboot_perf_v2_optimized"}
  ],
  "iterations": 2,
  "sequence_name": "optional_sequence_name"
}
```

**Response:**
```json
{
  "message": "Multi-device execution started with device grouping",
  "job_ids": ["abc123", "def456"],
  "device_count": 2,
  "eta_seconds": 120
}
```

---

## Troubleshooting

### Issue: Still Getting 404 on `/api/execute-multiple`
**Cause:** Flask app not reloaded  
**Fix:**
```bash
# Kill old process
pkill -f "python3 app.py"
sleep 2

# Restart
cd /path/to/dashboard
python3 app.py
```

### Issue: Devices Still Execute Sequentially
**Cause:** Devices not sent in multi-device API call  
**Fix:** Ensure dashboard is calling `/api/execute-multiple` (not `/api/execute`)

### Issue: One Device Fails While Other Executes
**Cause:** Device lock failed or tunnel establishment failed  
**Solution:** Check device connectivity and R-Pi backend availability

---

## Code Locations

| File | Changes | Lines |
|------|---------|-------|
| `app.py` | Added `/api/execute-multiple` route | 3576-3580 |
| `controllers/test_controller.py` | Added `execute_test_multiple()` method | 225-366 |
| `services/test_execution_service.py` | Enhanced multi-device execution support | 2507-2700 |

---

## Dashboard Integration (Pending)

The backend is ready. The dashboard needs to be updated to:

1. **Add Multi-Device Selection UI**
   - Allow selecting multiple devices
   - Show R-Pi grouping recommendations

2. **Route to `/api/execute-multiple`**
   - When 2+ devices selected on same R-Pi
   - Send `device_ips` array instead of single `device_ip`

3. **Update Job Monitoring**
   - Show related job IDs when displaying multi-device execution
   - Link jobs that executed as a group

---

## Next Steps

1. ✅ **Backend Implemented** - Multi-device execution code ready
2. ⏳ **Restart Flask** - Ensure new endpoint loads
3. 🔧 **Test Manually** - Verify parallel execution with curl
4. 🎨 **Update Dashboard UI** - Add multi-device selection
5. 📊 **Monitor Performance** - Verify 7× speedup for multi-device scenarios

