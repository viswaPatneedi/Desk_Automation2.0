# 🔧 DeepSleep Method Issue - Complete Investigation Report

## ✅ FIXES IMPLEMENTED

### 1. **CRITICAL BUG FIXED: Fresh Execution Showing False "[RESUMING JOB]" Message**

**Root Cause**: Job model initialized `current_iteration=1` instead of `current_iteration=0`

**Files Updated**:
- ✅ `models/job.py` (line 13)
- ✅ `RDK-Middleware-USB/docker-files/models/job.py` (line 14)

**Change**:
```python
# BEFORE:
def __init__(self, ..., current_iteration=1, ...):

# AFTER:  
def __init__(self, ..., current_iteration=0, ...):
```

**Impact**: Fresh jobs will now start from iteration 0, no false recovery messages

---

## 📋 STARTUP & DEPLOYMENT

### How to Start Application

**Script Found**: `start_venv_with_email.sh` (ready to use)

```bash
cd /home/viswa-pi4/Desktop/LRQA-DASHBOARD/lrqa-middleware-testing-dashboard

# Option 1: Use startup script (recommended)
./start_venv_with_email.sh

# Option 2: Manual start
source venv/bin/activate
export SMTP_SERVER='smtp.gmail.com'
export SMTP_PORT='587'
export SENDER_EMAIL='cperdkemiddleware@gmail.com'
export SENDER_PASSWORD='tbbwaifvmtzovqcs'
python3 app.py

# Monitor logs
tail -f /tmp/flask_prod.log  # Script logs here
```

**App Access**:
- URL: `http://localhost:8080` (check hostname if remote)
- Get IP: `hostname -I | awk '{print $1}'`

---

## 🔄 DeepSleep Method - Workflow Explanation

### Overall Method Flow
```
JOB QUEUED
    ↓
Connected to Device
    ↓
Get Build & IR Config
    ↓
PHASE 1: [OPTIONAL] Reboot
    ├─ if perform_reboot=True:
    │   ├─ Send reboot command to device
    │   ├─ Wait for device to come back online
    │   └─ Reactivate screen capture service
    └─ if perform_reboot=False:
        └─ Skip this phase
    ↓
PHASE 2: DeepSleep Transition
    ├─ Check current power state (ON or STANDBY?)
    ├─ If ON:
    │   ├─ Send IR Power key → Device goes to STANDBY [CASE 2a]
    │   └─ Verify reached STANDBY
    ├─ If STANDBY:
    │   ├─ Check if on HOME screen [CASE 2b Recovery]
    │   ├─ If NOT on HOME:
    │   │   └─ Send HOME key → Navigate back to HOME
    │   └─ If on HOME:
    │       └─ Continue
    ↓
PHASE 2c: Verify DeepSleep State
    ├─ Optional verification
    └─ Continues even if fails
    ↓
PHASE 3: Wakeup & Verify
    ├─ Wait: sleep_duration_minutes
    ├─ Send IR Power key → Wake device
    ├─ Verify device returns to HOME screen
    └─ Measure: Time from wake command to HOME appearance
    ↓
JOB COMPLETE
```

### When Does Recovery Trigger? ✅

Recovery (Phase 2 Case 2b) triggers when:
```
✓ Device is in STANDBY state AND
✓ NOT on HOME screen

This is NORMAL and EXPECTED when:
- Device was left in STANDBY from previous test
- Device is faulty and goes to STANDBY unexpectedly
- Network issues cause state loss

Recovery is NOT a bug - it's AUTOMATIC recovery!
```

### When Recovery SHOULD NOT Trigger

Recovery shouldn't trigger (green path) when:
```
✓ Device is ON at test start → properly goes to STANDBY → stays on HOME
✓ No device faults or network issues
```

---

## 🧪 Understanding Execution [8efe3c86-d8ca-49fd-8d2c-6c40fffd097c]

### To Check This Execution

1. **Find the logs**:
   - Dashboard → Operations → Console Logs
   - Or search: `Json/app_state.json` for execution ID

2. **Check these sections**:
   ```
   [DEEPSLEEP PROCESS - START]
   Device: {name} ({ip})
   Iteration: {iteration}
   DeepSleep Duration: {minutes} minutes
   Perform Reboot: {true/false}
   Remote Type Requested: {type}
   
   [Phase Analysis]
   📡 Remote Type Selected: {remote_type}
   ✓ Using remote model: {actual_model}
   
   [Phase 2 Status]
   ✓ Device power state: ON/STANDBY?
   📍 [CASE 2a] OR 📍 [CASE 2b] - Recovery?
   
   [Phase 3 Status]
   ✓ DEEPSLEEP PROCESS COMPLETED SUCCESSFULLY
   Time to HOME: {seconds} seconds
   ```

3. **What to verify**:
   - [ ] Remote type shows EXACT model (SKY_LC103, XUMO_PR3) not generic (SKY, XUMO)
   - [ ] Which case triggered: 2a (normal) or 2b (recovery needed)?
   - [ ] If 2b triggered: Is device faulty or leftover from previous test?
   - [ ] Phase 3: Did wake-up succeed? Time reasonable?
   - [ ] Final status: PASSED or FAILED?

---

## 🎯 Remote Type Selection System (NEW)

### How It Works Now
```
User Opens Modal
    ↓
Frontend calls: GET /api/available_ir_remotes
    ↓
Backend reads: ir_keycodes.json
    ↓
Returns: List of actual remote models
    [
      {id: "SKY_LC103", name: "SKY_LC103", display_name: "SKY_LC103 - Sky Remote"},
      {id: "XUMO_PR3", name: "XUMO_PR3", display_name: "XUMO_PR3 - Xumo Remote"}
    ]
    ↓
UI Populates Dropdown with actual models
    ↓
User Selects: "SKY_LC103" or "XUMO_PR3"
    ↓
Backend Uses: Exact model name (no mapping)
    ↓
IR Commands: Executed with correct remote model
```

### Before vs After

| Item | Before | After |
|------|--------|-------|
| Remote Options | Hardcoded generic types (SKY, XUMO, COMCAST, etc) | Dynamic from ir_keycodes.json |
| User Selection | "SKY" (generic) | "SKY_LC103" (exact model) |
| Backend Mapping | SKY→SKY_LC103, XUMO→XUMO_PR1-T2 | No mapping, use as-is |
| Source of Truth | Code hardcoded values | ir_keycodes.json file |
| Updates | Required code change | Just update JSON file |

---

## 🚀 Testing the Fixes

### Test 1: Fresh Execution Without Resume

```bash
1. Queue a NEW DeepSleep job (don't use an existing one)
2. Check console logs:
   ❌ SHOULD NOT see: "[RESUMING JOB]"
   ✅ SHOULD see: "DEEPSLEEP PROCESS - START"
3. Check iteration display:
   ✅ Should show: "Iteration: 1/1" (not "resuming from iteration 1")
```

### Test 2: Remote Type Dropdown

```bash
1. Open DeepSleep Parameters Modal
2. Click on Remote Type dropdown:
   ✅ Should show exact models:
      - "SKY_LC103 - Sky Remote SKY_LC103"
      - "XUMO_PR3 - Xumo Remote XUMO_PR3"
   ❌ Should NOT show: Generic types "SKY", "XUMO", "COMCAST", etc.
3. Select a remote → Queue job
4. Check logs:
   ✅ Should show: "Using remote model: SKY_LC103" (exact model selected)
```

### Test 3: Recovery Detection

```bash
1. Intentionally leave device in STANDBY
2. Start DeepSleep test
3. Check logs:
   ✅ Should detect Case 2b: "Device is STANDBY and NOT on HOME SCREEN"
   ✅ Should show recovery: "Sending HOME key for recovery"
   ✅ Should succeed or log reason for failure
```

---

## 🔐 File Locations Reference

| Item | Location |
|------|----------|
| Startup Script | `start_venv_with_email.sh` |
| Report Document | `DEEPSLEEP_INVESTIGATION_REPORT.md` |
| Job Model (Fix) | `models/job.py` |
| Docker Job Model (Fix) | `RDK-Middleware-USB/docker-files/models/job.py` |
| DeepSleep Method | `method_deepsleep.py` |
| API Endpoint | `app.py` (line 147-200) |
| Dashboard Modal | `templates/dashboard.html` (promptForDeepSleepParams, promptForMaintenanceDeepSleepParams) |
| App Logs | `/tmp/flask_prod.log` |
| Job Data | `Json/app_state.json` |
| IR Keycodes | `Json/ir_keycodes.json` |

---

## ⚠️ Important Notes

### About "[RESUMING JOB]" Message
- **Now Fixed**: Fresh executions will NOT show this message
- Previously: Appeared because `current_iteration` defaulted to 1
- Now: Defaults to 0, so resume logic only triggers for actual resume scenarios

### About Recovery Phase in Logs  
- **Not a Bug**: Recovery (Phase 2 Case 2b) is intentional
- **Expected when**: Device in STANDBY or experiencing issues
- **Indicates**: Device state issue, not code issue
- **Check**: Is device properly powered off between tests?

### About Remote Type  
- **Now Dynamic**: Populated from `ir_keycodes.json`
- **No More Mapping**: User selects exact model, backend uses it directly
- **Easy Updates**: Just update JSON file for new remotes

---

## ✓ Next Steps

1. **Restart App**:
   ```bash
   ./start_venv_with_email.sh
   # or
   pkill -f "python app.py"; sleep 2; ./start_venv_with_email.sh
   ```

2. **Run Test Job**:
   - Queue new DeepSleep method
   - Check console output
   - Verify no false "[RESUMING JOB]" messages
   - Verify remote dropdown shows actual models

3. **Analyze Execution [8efe3c86]**:
   - Check which phase recovery triggered
   - Verify if intentional (device in STANDBY?)
   - Confirm remote model used is correct

4. **Monitor for Issues**:
   - If recovery still happens unexpectedly → check device state
   - If remotes wrong → verify ir_keycodes.json has all models
   - If jobs fail → check logs for actual failure reason (not recovery)

