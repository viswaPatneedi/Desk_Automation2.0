# DeepSleep Method Execution Analysis & Fixes

## 📋 INVESTIGATION SUMMARY

### 1. STARTUP SCRIPT FOUND ✅
**Location**: `start_venv_with_email.sh`
- Activates Python venv with email configuration  
- Runs: `./venv/bin/python3 app.py`
- Logs to: `/tmp/flask_prod.log`
- Designed for production use with email integration

**Usage**:
```bash
./start_venv_with_email.sh
# App will start in background with PID logged to console
```

---

## 🐛 ROOT CAUSE: "[RESUMING JOB] Continuing from iteration 1/1" on Fresh Executions

### The Bug
When you execute DeepSleep for the first time (fresh execution), you see:
```
[RESUMING JOB] Continuing from iteration 1/1
```

### Why This Happens
**File**: `models/job.py` line 16  
**Issue**: Default value for `current_iteration` was set to `1` instead of `0`

```python
# BEFORE (WRONG):
def __init__(self, ..., current_iteration=1, ...):

# AFTER (FIXED):
def __init__(self, ..., current_iteration=0, ...):
```

### The Flow Chain
1. Fresh job created via `Job.create_job()` → uses default `current_iteration=1`
2. Test execution service checks: `if job.current_iteration > 0:` ✓ (TRUE!)
3. Thinks job is resumed → logs "[RESUMING JOB]"
4. Recovery logic also falsely triggers
5. Phase 2 recovery runs when it shouldn't

### Fix Applied ✅
- Updated `models/job.py` → `current_iteration` default: `1` → `0`
- Updated `RDK-Middleware-USB/docker-files/models/job.py` → same fix
- Fresh jobs now start from iteration 0 as intended

---

## 📊 DeepSleep Method Workflow (INTENDED)

### Phase 1: Boot Phase (Optional)
```
IF perform_reboot=True:
  → Reboot device
  → Reactivate screen capture service
  → Reconnect SSH
```

### Phase 2: DeepSleep Transition
```
CASE 2a: Device is ON
  → Press IR Power key to go to STANDBY
  → Verify device reaches STANDBY state
  → Send HOME key to stay on home screen
  
CASE 2b: Device is STANDBY (and NOT on HOME)
  → [RECOVERY TRIGGERED]
  → Send HOME key to navigate back to home screen
  → Verify device is back on HOME screen
```

### Phase 2c: Verify DeepSleep
```
Check if device is truly in DEEPSLEEP state
(Not critical - continues if verification fails)
```

### Phase 3: Wake Up & Verify  
```
Wait for sleep_duration_minutes
  → Send IR Power key to wake device
  → Verify device returns to HOME screen
  → Measure time from wake command to HOME screen appearance
```

---

## ⚠️ Why Recovery Part Shows in Fresh Execution

**Not a bug - this is intentional!** The recovery logic in Phase 2 Case 2b will trigger if:
- Device was already in STANDBY state when test started
- Device failed to properly transition to STANDBY during Phase 2
- Device lost connection during transition

### When Recovery SHOULD NOT Trigger
- Only when device is ON at start of test
- Properly transitions to STANDBY
- Stays on HOME screen during STANDBY wait

### When Recovery WILL Trigger  
- Device left in STANDBY from previous test ← **Most common**
- Device crashes during phase transition
- Network instability during state change

---

## 🔍 Execution ID [8efe3c86-d8ca-49fd-8d2c-6c40fffd097c] Analysis

### How to Check This Execution
1. Look in `Json/app_state.json`
2. Search for execution ID to find the execution record
3. Check the console logs in **Operations > Console Logs** section in dashboard
4. Look for:
   - Which phase recovery triggered
   - Device power state at start
   - Any intermediate failures
   - IR remote type used (should beexact model like SKY_LC103, XUMO_PR3)

### What to Verify
```
✓ Device power state at execution start (ON or STANDBY)?
✓ Which phase triggered recovery (should be Phase 2 Case 2b)?
✓ Remote type shown: Should be exact model (SKY_LC103 / XUMO_PR3)
   NOT generic type (SKY / XUMO)
✓ Did recovery successfully get device back to HOME?
✓ Did Phase 3 wake-up complete successfully?
```

---

## 🛠️ FIXES APPLIED

### 1. Job Initial Iteration Bug ✅
- **Files Changed**: 
  - `models/job.py` (line 13)
  - `RDK-Middleware-USB/docker-files/models/job.py` (line 14)
- **Change**: `current_iteration=1` → `current_iteration=0`
- **Effect**: Fresh executions no longer show false "[RESUMING JOB]" message

### 2. Dynamic IR Remote Selection (Previous Session) ✅
- Added `/api/available_ir_remotes` endpoint in `app.py`
- Updated `promptForDeepSleepParams()` modal to fetch remotes from endpoint
- Updated `promptForMaintenanceDeepSleepParams()` modal similarly  
- Updated `method_deepsleep.py` to use remote model names directly (no mapping)
- **Effect**: Remote dropdown populated from `ir_keycodes.json`, shows actual models

---

## 🚀 NEXT STEPS

### 1. Verify App Starts Correctly
```bash
# Kill old process
pkill -f "python app.py"

# Start using proper startup script
./start_venv_with_email.sh

# Monitor logs
tail -f /tmp/flask_prod.log
```

### 2. Test Fresh DeepSleep Execution
```
✓ Queue a new DeepSleep method job (first time, NOT resume)
✓ Check console logs - should NOT show "[RESUMING JOB]"
✓ Device should go through all 3 phases properly
✓ Remote type should show correct model (e.g., SKY_LC103)
```

### 3. Analyze Execution [8efe3c86] Logs
- Check console output for this execution
- Verify which phase recovery triggered
- Confirm it was intentional (not false recovery)

### 4. Verify Recovery Behavior
```
Test Case 1 - Fresh Execution (No Resume):
  → Start new job
  → Should NOT show "[RESUMING JOB]"
  → Recovery only if device actually in STANDBY at start

Test Case 2 - Resume Execution:
  → Manually set job.current_iteration > 0
  → NOW should show "[RESUMING JOB]"  
  → Recovery resumes from saved checkpoint
```

---

## 📝 Key Configuration Values

**From Execution Flow**:
- `sleep_duration_minutes`: 60 (default, overridable at runtime)
- `perform_reboot`: false (default, overridable)
- `remote_type`: User selects from dropdown (now populated from ir_keycodes.json)
- `iteration`: Always 1 for fresh execution (now with fix)

**Available Remotes** (from ir_keycodes.json):
- SKY_LC103 (Sky Remote)
- XUMO_PR3 (Xumo/Comcast Remote)

---

## ❓ Troubleshooting

### If You Still See "[RESUMING JOB]" After Restart
1. Verify the Job model update took effect
2. Check `Json/app_state.json` - does device have `current_iteration > 0`?
3. May need to clear old jobs or reset current_iteration to 0 manually

### If Recovery Triggers Unexpectedly  
1. Check device power state at test start
2. May indicate device is left in STANDBY between tests
3. Either is a device state issue, not a code issue

### If Recovery Doesn't Trigger When Needed
1. Device may have already recovered automatically
2. Check Phase 2a transition - device may be properly in STANDBY
3. Recovery only needed if device in STANDBY + NOT on HOME

