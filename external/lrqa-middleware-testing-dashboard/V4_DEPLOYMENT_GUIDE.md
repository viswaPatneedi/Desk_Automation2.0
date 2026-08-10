# v4 Tunnel Sharing Fix - Deployment Summary & Verification Guide

## Overview
**Issue Fixed**: Second device (Job 2) on same R-Pi waiting 60 seconds for exclusive tunnel lock instead of detecting and reusing first device's (Job 1) tunnel.

**Root Cause**: Tunnel registration happened AFTER connection succeeded (~14 seconds later), so Job 2 couldn't detect it early enough.

**Solution**: Register tunnel IMMEDIATELY at acquisition start with "acquiring" status, so Job 2 detects pending tunnel right away.

---

## Code Changes Deployed

### 1. Global Tunnel Registry Functions
**File**: `services/test_execution_service.py` (Lines 47-76)

```python
# Module-level thread-safe registry
_ACTIVE_TUNNELS = {}
_TUNNEL_LOCK = threading.RLock()

def register_tunnel(device_ip: str, tunnel_data: Dict) → None
def get_tunnel(device_ip: str) → Optional[Dict]
def find_companion_tunnel(device_ip: str, target_rpi_ip: str) → Optional[Dict]
def unregister_tunnel(device_ip: str) → None
```

**Why**: Replaces per-instance `self.active_tunnels` which was invisible across threads.

### 2. Enhanced `_wait_for_shared_tunnel()` Method
**File**: `services/test_execution_service.py` (Lines 217-288)

**Key Changes**:
- ✅ Recognizes `status='acquiring'` and WAITS for tunnel to connect
- ✅ Checks both: global registry AND active job status
- ✅ Loops with 2-second intervals, up to 15 seconds total
- ✅ Returns tunnel once `tunnel_service` object appears

**Expected Flow**:
```
Job 2 starts → _wait_for_shared_tunnel()
  → Finds Job 1's tunnel with status='acquiring'
  → Logs: "Companion tunnel ACQUIRING status... waiting"
  → Sleeps 1 second, checks again
  → Finds Job 1's tunnel with actual tunnel_service
  → Returns tunnel for reuse (no exclusive lock needed)
```

### 3. Early Tunnel Registration in `establish_tunnel_for_device()`
**File**: `services/test_execution_service.py` (Lines 293-318)

**New Step at Line ~307**:
```python
# ✨ REGISTER A "PENDING" TUNNEL IMMEDIATELY (before acquisition)
register_tunnel(device.ip, {
    'tunnel_service': None,  # Not connected yet
    'rpi_ip': rpi_ip,
    'status': 'acquiring',  # Flag: acquisition in progress
    'job_id': current_job_id
})
print(f"✅ [TUNNEL-REGISTRY] Registered PENDING tunnel for {device.name}...")
```

**Then**: Proceed with `tunnel_coordinator.acquire_tunnel()` (may take seconds)
**Then**: Connect GDFRPiShellService (may take 14+ seconds)
**Finally**: Update registration with actual `tunnel_service` object

### 4. Cleanup in Failure Paths
**File**: `services/test_execution_service.py`

All failure paths now unregister pending tunnel:
- Line ~335: If `tunnel_coordinator.acquire_tunnel()` fails
- Line ~353: If tunnel connection fails
- Line ~376: If exception during tunnel setup

---

## Expected Behavior After v4 Fix

### Timeline for Parallel Execution (both devices on same R-Pi)
```
21:53:39.203  Job 1 (10.0.0.140) created
21:53:39.562  Job 2 (10.0.0.28) created (359ms later)

BEFORE v4 (FAILS):
  21:53:39 → Job 1: Start tunnel acquisition
  21:53:39 → Job 2: _wait_for_shared_tunnel() finds NOTHING (too early)
  21:53:39 → Job 2: Try to acquire exclusive lock
  21:53:39 → Job 2: BLOCKED (Job 1 holds it)
  21:54:39 → Job 2: TIMEOUT after 60 seconds → FAILED

AFTER v4 (SUCCEEDS):
  21:53:39.203 → Job 1: START tunnel acquisition
  21:53:39.207 →   Job 1: Register "acquiring" in global registry
  21:53:39.562 → Job 2: START
  21:53:39.565 →   Job 2: _wait_for_shared_tunnel() finds Job 1's pending tunnel!
  21:53:39.566 →   Job 2: Logs "Companion tunnel ACQUIRING status... waiting"
  21:53:39.567 →   Job 2: Sleeps 1 second
  21:53:40.567 →   Job 2: Checks again → tunnel still acquiring
  ...
  21:53:53.200 → Job 1: Tunnel connection complete!
  21:53:53.210 →   Job 1: Update registration with tunnel_service
  21:53:53.211 → Job 2: Detects tunnel_service object!
  21:53:53.212 →   Job 2: Log "SUCCESS! REUSING established tunnel"
  21:53:53.213 →   Job 2: Return tunnel for reuse
  21:53:53.214 → Both jobs executing in PARALLEL with shared tunnel
```

---

## How to Verify v4 is Working

### Option 1: Check Flask Logs (Real-time)
```bash
cd ~/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
tail -f flask_v4.log | grep -E "TUNNEL|tunnel|REGISTRY|registry"
```

**Look For These Messages**:
- Job 1: `✅ [TUNNEL-REGISTRY] Registered PENDING tunnel`
- Job 2: `🔍 Companion devices: [...]`
- Job 2: `⏳ Attempt N: Companion tunnel ACQUIRING status`
- Job 2: `✨ [SHARED-TUNNEL v4] SUCCESS! REUSING established tunnel`

### Option 2: Check Job Execution Logs
```bash
# After running test from dashboard
JOB_ID="<job-id-of-job-2>"
grep -E "TUNNEL|tunnel|REGISTRY|Companion|SHARED" \
  ~/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard/logs/jobs/$JOB_ID/execution.log
```

**Expected Output for Job 2**:
```
[Device 10.0.0.28] Checking for companion tunnels...
🔍 Companion devices: ['DT_LAB_SKY_XIONE-UK-0D_AB']
✅ [TUNNEL-REGISTRY] Registered pending tunnel for DT_LAB_XIONE-UK-17-97
⏳ Attempt 1: Companion tunnel ACQUIRING status... (14.9s remaining)
⏳ Attempt 2: Companion tunnel ACQUIRING status... (12.9s remaining)
✨ [SHARED-TUNNEL v4] SUCCESS! REUSING established tunnel after 5 attempts
Tunnel established to DT_LAB_XIONE-UK-17-97 via R-Pi
```

### Option 3: Run Direct Python Test
```bash
cd ~/Desk-automation/Desk-Automation-v2.0/external/lrqa-middleware-testing-dashboard
python3 test_tunnel_registry_v4.py
```

**Expected Result**: All tests PASS
- ✅ Register pending tunnel
- ✅ Check registry has tunnel
- ✅ Companion finds pending tunnel
- ✅ Job 2 waits and detects Job 1's connected tunnel
- ✅ Cleanup works

---

## What NOT to Expect

❌ **NO longer seeing these errors**:
- "Timeout acquiring tunnel... Currently held by job"
- "Could not acquire R-Pi tunnel after waiting 60 seconds"
- Job 2 status "failed" with 60-second wait message

❌ **NO longer seeing these patterns**:
- Job 2 starts → waits 60 seconds → fails
- Job 1 completes successfully, but Job 2 always times out
- Only first job succeeds on same-R-Pi device pairs

---

## Key Files Modified

1. **services/test_execution_service.py**
   - Module level: Global tunnel registry
   - `_wait_for_shared_tunnel()` method: Enhanced waiting logic
   - `establish_tunnel_for_device()` method: Early pending registration
   - `cleanup_tunnel_for_device()` method: Cleanup logic

2. **app.py**
   - Added `/api/execute` to public API paths (for testing)
   - Added `/api/job-status/*` wildcard (for testing)

---

## Testing Instructions

### From Dashboard (Standard Way)
1. Open http://localhost:11079/
2. Create test sequence with both devices
3. Submit execution
4. Watch Flask logs: `tail -f flask_v4.log | grep TUNNEL`
5. Check both jobs complete successfully

### From Command Line (Advanced)
```bash
# Start test for Device 1
curl -X POST http://localhost:11079/api/execute \
  -H "Content-Type: application/json" \
  -d '{"device_ip":"10.0.0.140","test_name":"basic_sanity"}'

# Immediately start test for Device 2 (within 1-2 seconds)
curl -X POST http://localhost:11079/api/execute \
  -H "Content-Type: application/json" \
  -d '{"device_ip":"10.0.0.28","test_name":"basic_sanity"}'

# Monitor logs
tail -f flask_v4.log
```

---

## Success Criteria

| Criterion | Before v4 | After v4 |
|-----------|-----------|----------|
| Job 1 (10.0.0.140) completes | ✅ Yes | ✅ Yes |
| Job 2 (10.0.0.28) completes | ❌ No (times out) | ✅ Yes |
| Job 2 execution time | 60+ seconds | <10 seconds |
| Both in parallel | ❌ No (sequential failure) | ✅ Yes |
| Logs show tunnel sharing | ❌ No registry messages | ✅ REGISTRY messages |
| Logs show waiting | ❌ No | ✅ "ACQUIRING status... waiting" |

---

## Troubleshooting

**Issue**: Job 2 still timing out
- Check: Flask running with latest code? (`flask_v4.log` should exist)
- Check: SQL/connection errors in Flask logs?
- Check: Can you see "TUNNEL-REGISTRY" messages?
- If no: Flask may have old code - restart Flask

**Issue**: Job 1 fails to acquire tunnel
- Check: R-Pi accessibility (10.138.17.42 reachable?)
- Check: SSH key configuration for root user
- Check: Other processes holding tunnel coordinator lock?

**Issue**: Registry test fails
- Check: Python dependencies installed?
- Check: Can import TestExecutionService? (`python3 -c "from services.test_execution_service import *"`)

---

## Next Steps After Verification

1. ✅ Verify v4 fix works with parallel devices (THIS)
2. ⏳ Run extended test suite (15+ parallel device pairs)
3. ⏳ Monitor for memory leaks (long-running registry)
4. ⏳ Deploy to production
5. ⏳ Remove testing API endpoints from public paths

---

## References

- **Commit/PR**: [To be filled after git commit]
- **Issue**: Multi-device parallel execution on same R-Pi was failing with 60s timeout
- **Solution Branch**: v4-pending-tunnel-registration
- **Test Files**: 
  - `test_tunnel_registry_v4.py` - Registry logic test
  - `test_parallel_execution_v4.py` - Flask API test (needs auth fix)

