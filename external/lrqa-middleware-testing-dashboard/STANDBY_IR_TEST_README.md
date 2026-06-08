# Standby & DeepSleep Test with IR Power Control

## Overview

This method automates testing of device standby and deep sleep functionality using **IR POWER commands** instead of WakeOnLAN. It's based on the `standby_test.sh` reference script but with enhancements for real-time logging and dashboard integration.

**Key Difference from Reference Script:**
- ❌ **No WakeOnLAN** - Uses IR POWER key commands instead
- ✅ **IR Control** - Remotely control power states via TV remote commands
- ✅ **Real-Time Logging** - Detailed step-by-step logs for user visibility
- ✅ **User Prompts** - Asks for remote type before execution
- ✅ **Dashboard Integration** - Returns structured JSON logs

## Files

### 1. `standby_deep_sleep_ir_control.py`
**Standalone executable method** with user prompts
- Can be run directly from command line: `python standby_deep_sleep_ir_control.py`
- Asks user for device IP and remote type
- Outputs formatted real-time logs

### 2. `standby_ir_integration.py`
**Dashboard integration method** for RDK-E Middleware QA Tool
- Can be called from test controller with device_ip and remote_type
- Returns structured JSON logs
- Real-time console logging for visibility

## Test Sequence

```
┌─────────────────────────────────────────────────────────────┐
│     STANDBY & DEEPSLEEP TEST WITH IR POWER CONTROL          │
└─────────────────────────────────────────────────────────────┘
     │
     ├─ STEP 1: Wake Device (IR POWER × 3)
     │   └─ Wait 5 seconds, query power state
     │
     ├─ STEP 2: Wait for Boot State to reach "NORMAL"
     │   └─ Poll: 0:9001/as/system/bootstate
     │   └─ Max 10 attempts, 6s interval
     │
     ├─ STEP 3: Wait for EPG UI to Load
     │   └─ Check: grep 'com.bskyb.epgui - RUNNING' /opt/logs/sky-messages.log
     │   └─ Max 10 attempts, 6s interval
     │
     ├─ STEP 4: Verify Device is ON
     │   └─ Send IR POWER to ensure ON state
     │   └─ Query power state
     │   └─ Fail if not "ON"
     │
     ├─ STEP 5: Configure Deep Sleep Parameters
     │   └─ curl: Set lowPowerTimerDuration = 30s
     │   └─ curl: Set nextMaintenanceTimeOverride = 30s
     │   └─ echo: Write 30 to /tmp/deepSleepTimerVal
     │
     ├─ STEP 6: Toggle Device to SLEEP
     │   └─ Send IR POWER to enter sleep
     │
     ├─ STEP 7: Wait for Sleep Cycle (5 minutes)
     │   └─ Device enters sleep automatically
     │   └─ Timer triggers auto-wake after ~30s
     │
     ├─ STEP 8: Verify Device in Sleep State
     │   └─ Poll power state for LIGHTSLEEP/DEEPSLEEP/STANDBY
     │   └─ Max 10 attempts
     │
     ├─ STEP 9: Reboot Device
     │   └─ curl: 0:9001/as/system/action/reset?type=reboot
     │
     └─ STEP 10: Wait for Reboot (2 minutes)
         └─ Poll power state after reboot complete
```

## Real-Time Logging Example

```
[14:15:02 UTC] ℹ️  === STANDBY & DEEP SLEEP TEST WITH IR CONTROL ===
[14:15:02 UTC] ℹ️  Device: 10.0.0.106, Remote: SKY
[14:15:02 UTC] ℹ️  STEP 1: Wake Device from Standby
[14:15:02 UTC] ℹ️  Sending IR Command: Wake attempt 1/3
[14:15:02 UTC] ℹ️  Executing command: IR KEY_POWER - Wake attempt 1/3
[14:15:03 UTC] ✅ Command executed: Success
[14:15:05 UTC] ✅ Power state: ON
[14:15:08 UTC] ℹ️  STEP 2: Wait for Boot State
[14:15:08 UTC] ℹ️  Boot state check 1/10
[14:15:14 UTC] ✅ Boot state reached: {...NORMAL...}
[14:15:14 UTC] ℹ️  STEP 3: Wait for EPG UI
[14:15:20 UTC] ✅ EPG is running: com.bskyb.epgui - RUNNING
...
[14:20:30 UTC] ✅ Device in sleep state: DEEPSLEEP
[14:20:31 UTC] ✅ === TEST COMPLETED SUCCESSFULLY ===
```

## Usage

### Standalone Execution

```bash
# Run with user prompts
python standby_deep_sleep_ir_control.py

# Enter when prompted:
# Device IP: 10.0.0.106
# Remote Type: 1 (SKY) or custom
```

### Dashboard Integration

```python
from methods.standby_ir_integration import run_test_method

# Run test
success, logs = run_test_method(device_ip="10.0.0.106", remote_type="SKY")

# Get results
print(f"Test passed: {success}")
print(f"Logs: {logs['logs']}")
print(f"Total time: {(logs['end_time'] - logs['start_time']).total_seconds()}s")
```

### From Test Controller

```python
# In controllers/test_controller.py
from methods.standby_ir_integration import run_test_method

@app.route('/api/test/standby-ir', methods=['POST'])
def standby_ir_test():
    data = request.json
    device_ip = data.get('device_ip')
    remote_type = data.get('remote_type', 'SKY')
    
    success, logs = run_test_method(device_ip, remote_type)
    
    return jsonify({
        'success': success,
        'logs': logs,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })
```

## Curl Commands Used (Same as standby_test.sh)

### Set Low Power Timer
```bash
curl -s 0:9001/as/test/preferences -d '{"lowPowerTimerDuration":"30"}'
```

### Set Maintenance Timer
```bash
curl -s 0:9001/as/test/preferences -d '{"nextMaintenanceTimeOverride":"30"}'
```

### Reboot Device
```bash
curl -s '0:9001/as/system/action/reset?type=reboot' -d ''
```

### Check Boot State
```bash
curl -s '0:9001/as/system/bootstate'
```

## IR Key Commands

| Command | Purpose |
|---------|---------|
| `KEY_POWER` | Toggle device power state (ON ↔ SLEEP) |
| `KEY_SLEEP` | Force sleep mode (alternative) |
| `KEY_WAKEUP` | Force wake from sleep (alternative) |

## Remote Types Supported

- **SKY** - Sky box remotes
- **SAMSUNG** - Samsung TV remotes
- **LG** - LG TV remotes
- **XIAOMI** - Xiaomi device remotes
- **CUSTOM** - Custom remote type (user-defined)

## Environment Requirements

- SSH access to device on port 10022
- `/media/apps/evemu-tools/send_key.sh` script available on device
- `/opt/logs/sky-messages.log` for EPG verification
- RDK Thunder API accessible at `0:9001/as/*`
- `curl` installed on device
- `QueryPowerState` command available

## Log Output Format

Each log entry contains:
```json
{
  "timestamp": "2026-05-13T14:15:02Z",
  "level": "INFO|SUCCESS|WARNING|ERROR",
  "message": "Description of action",
  "details": "Additional details or output"
}
```

## Error Handling

| Error | Action | Continue? |
|-------|--------|-----------|
| Boot state not reached | Log warning | ⚠️ Yes |
| EPG not loaded | Log warning | ⚠️ Yes |
| Device not ON before sleep | Log error | ❌ No |
| Device didn't enter sleep | Log error | ❌ No |
| SSH timeout | Log error, retry | ⚠️ Depends |
| User interrupt (Ctrl+C) | Log interruption | ❌ No |

## Timing

| Phase | Duration | Notes |
|-------|----------|-------|
| Wake device | ~5s | 3 IR commands with 2s gaps |
| Boot + EPG | ~60s | Polling with 6s intervals |
| Device verification | ~10s | Power state checks |
| Timer setup | ~3s | 3 curl commands |
| Sleep cycle | 5 min | Device sleep + auto-wake |
| Verify sleep | ~10s | Power state polling |
| Reboot | 2 min | Wait for device to reboot |
| **Total** | **~8 minutes** | Approximate total duration |

## References

- Based on: `standby_test.sh`
- RDK Documentation: [Thunder API](https://rdkservices.github.io/)
- Device SSH: Port 10022, user: root

## Future Enhancements

- [ ] Support for multiple remote types (IR command mapping)
- [ ] Configurable timer durations
- [ ] Support for different device boot states (RECOVERY, MAINTENANCE, etc.)
- [ ] Enhanced error recovery with manual intervention options
- [ ] Device health checks between test phases
- [ ] Performance metrics (boot time, wake time, etc.)
