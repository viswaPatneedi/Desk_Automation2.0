# Standby & DeepSleep IR Control Test - Implementation Summary

## ✅ Files Created

### 1. **methods/standby_deep_sleep_ir_control.py**
   - **Type**: Standalone executable Python script
   - **Lines**: ~400
   - **Purpose**: Interactive standalone version with user prompts
   - **Usage**: `python standby_deep_sleep_ir_control.py`
   - **Features**:
     - Prompts for device IP (defaults to 10.0.0.106)
     - Prompts for remote type (SKY, SAMSUNG, LG, XIAOMI, CUSTOM)
     - Real-time formatted logging with timestamps
     - Step-by-step visual progress indicators
     - Can be run independently

### 2. **methods/standby_ir_integration.py**
   - **Type**: Dashboard integration module
   - **Lines**: ~350
   - **Purpose**: Integrates with RDK-E Middleware QA Dashboard
   - **Usage**: Can be imported and used by test controller
   - **Features**:
     - `StandbyDeepSleepIRTest` class for OOP approach
     - `run_test_method(device_ip, remote_type)` function
     - Returns structured JSON logs
     - Real-time console logging for visibility
     - Can be called from Flask routes
     - Returns success status + detailed logs

### 3. **STANDBY_IR_TEST_README.md**
   - **Type**: Comprehensive documentation
   - **Sections**:
     - Overview and key differences from reference script
     - Complete test sequence flow diagram
     - Real-time logging example output
     - Usage examples (standalone, dashboard, test controller)
     - Curl commands reference
     - IR key commands table
     - Remote types supported
     - Environment requirements
     - Error handling matrix
     - Timing information
     - Future enhancements

## 🔑 Key Features

### ✨ IR Power Control (Instead of WakeOnLAN)
- Uses `KEY_POWER` IR commands to toggle device states
- Multiple attempts (3×) to ensure state change
- Works with configurable remote types

### 📊 Real-Time Logging
Each step logs with:
- **Timestamp**: UTC ISO format (e.g., `2026-05-13T14:15:02Z`)
- **Level**: INFO, SUCCESS, WARNING, ERROR
- **Message**: Action description
- **Details**: Output or error details

Format:
```
[14:15:02 UTC] ✅ Power state: ON
[14:15:03 UTC] ℹ️  Executing command: Boot state check
[14:15:08 UTC] ✅ Boot state reached: NORMAL
```

### 🎯 Test Steps (11 total)

| # | Step | Duration | IR Commands |
|---|------|----------|-------------|
| 1 | Wake Device | ~5s | 3× KEY_POWER |
| 2 | Wait Boot | ~60s | None |
| 3 | Wait EPG | ~60s | None |
| 4 | Verify ON | ~10s | 1× KEY_POWER |
| 5 | Set Timers | ~3s | None (curl) |
| 6 | Toggle Sleep | ~1s | 1× KEY_POWER |
| 7 | Sleep Cycle | 5 min | None |
| 8 | Verify Sleep | ~10s | None |
| 9 | Reboot | ~1s | None (curl) |
| 10 | Wait Reboot | 2 min | None |
| 11 | Final Check | ~5s | None |

**Total Duration**: ~8 minutes

### 📝 Curl Commands (Same as standby_test.sh)

Three curl commands used for timer configuration:

```bash
# 1. Set low power timer to 30 seconds
curl -s 0:9001/as/test/preferences -d '{"lowPowerTimerDuration":"30"}'

# 2. Set maintenance timer to 30 seconds  
curl -s 0:9001/as/test/preferences -d '{"nextMaintenanceTimeOverride":"30"}'

# 3. Reboot device
curl -s '0:9001/as/system/action/reset?type=reboot' -d ''
```

### 🔄 Query Commands

```bash
# Query power state
QueryPowerState

# Check boot state
curl -s '0:9001/as/system/bootstate'

# Check EPG running
grep 'com.bskyb.epgui - RUNNING' /opt/logs/sky-messages.log
```

## 📋 User Prompts

When running standalone, user is prompted for:

1. **Device IP Address**
   - Default: 10.0.0.106
   - Input Format: 10.0.0.XXX

2. **Remote Type** (Multiple choice)
   ```
   1. SKY (default)
   2. SAMSUNG
   3. LG
   4. XIAOMI
   5. CUSTOM
   ```

## 🔌 Integration Points

### For Dashboard Test Controller

```python
# In controllers/test_controller.py
from methods.standby_ir_integration import run_test_method

# Call the method
success, logs = run_test_method(
    device_ip="10.0.0.106",
    remote_type="SKY"
)

# Return to user
return jsonify({
    'success': success,
    'method': 'standby_deep_sleep_ir_control',
    'device': device_ip,
    'remote_type': remote_type,
    'duration_seconds': calculate_duration(logs),
    'logs': logs['logs'],
    'status': 'completed'
})
```

### Return Structure

```json
{
  "status": "success",
  "device_ip": "10.0.0.106",
  "remote_type": "SKY",
  "start_time": "2026-05-13T14:15:00Z",
  "end_time": "2026-05-13T14:23:15Z",
  "logs": [
    {
      "timestamp": "2026-05-13T14:15:02Z",
      "level": "INFO",
      "message": "STEP 1: Wake Device from Standby",
      "details": "Using IR POWER commands"
    },
    ...
  ]
}
```

## 🚀 How to Use

### Standalone
```bash
cd Enhancement
python methods/standby_deep_sleep_ir_control.py
```

### Import in Code
```python
from methods.standby_ir_integration import run_test_method

success, logs = run_test_method("10.0.0.106", "SKY")
print(f"Test passed: {success}")
```

### Add to Dashboard
1. Implement endpoint in test_controller.py
2. Add route handler to app.py
3. Add UI button in dashboard.html
4. Call endpoint with device_ip and remote_type

## 🔍 Differences from standby_test.sh

| Feature | standby_test.sh | New Method |
|---------|-----------------|-----------|
| Wake method | wakeonlan | IR POWER key |
| Remote type | Fixed | User selectable |
| Logging | Script output | Real-time structured |
| Integration | Bash script | Python module |
| Dashboard | None | Full integration |
| Error recovery | Basic | Enhanced |
| User prompts | None | Device IP + remote type |
| Exit codes | 0/1 | success boolean + logs |

## ✔️ Validation

- ✅ Python syntax validated (both files compile)
- ✅ Follows project conventions
- ✅ Comprehensive error handling
- ✅ Real-time logging at each step  
- ✅ Same curl commands as reference script
- ✅ Ready for dashboard integration
- ✅ Documented with examples

## 📦 Files Summary

```
Enhancement/
├── STANDBY_IR_TEST_README.md           # Full documentation
├── methods/
│   ├── standby_deep_sleep_ir_control.py   # Standalone version (400 lines)
│   └── standby_ir_integration.py          # Dashboard integration (350 lines)
```

## 🎯 Next Steps

1. **Test the method**
   - Run standalone: `python methods/standby_deep_sleep_ir_control.py`
   - Verify with a real device

2. **Integrate with dashboard**
   - Add to test_controller.py
   - Add route to app.py
   - Add UI button to dashboard.html

3. **Add to config**
   - Add method name to `config_commands.py` AVAILABLE_METHODS
   - Add parameter definitions

4. **Test via dashboard**
   - Execute from UI
   - Verify real-time logging works
   - Confirm JSON output format

## 📞 Method Metadata

```python
method_config = {
    "name": "standby_deep_sleep_ir_control",
    "title": "Standby & DeepSleep Test (IR Control)",
    "description": "Test standby/deep sleep with IR POWER key control",
    "parameters": [
        {"name": "device_ip", "type": "string", "required": True},
        {"name": "remote_type", "type": "select", "options": ["SKY", "SAMSUNG", "LG", "XIAOMI", "CUSTOM"]}
    ],
    "duration_minutes": 8,
    "requires_ir_blaster": False,
    "requires_wakeonlan": False,
    "requires_ssh": True
}
```

---

**Created**: 2026-05-13
**Status**: ✅ Ready for integration
**Files**: 3 (1 README + 2 Python methods)
**Total Lines of Code**: ~750 lines
