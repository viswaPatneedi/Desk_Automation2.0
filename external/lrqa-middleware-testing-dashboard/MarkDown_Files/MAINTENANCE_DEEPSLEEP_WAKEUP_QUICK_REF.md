# Maintenance > DeepSleep > Wakeup - Quick Reference

## TL;DR

The **Maintenance > DeepSleep > Wakeup** method runs a complete device maintenance, sleep, and recovery cycle following the attached specification.

```
MAINTENANCE → STANDBY → MAINTENANCE CYCLE → REBOOT →
STANDBY → DEEP SLEEP (15 min) → IR WAKE-UP → MEASURE TIME → VALIDATE
```

## 30-Second Overview

| Step | Action | Duration | Purpose |
|------|--------|----------|---------|
| 1-2 | Check & manage maintenance status | 5 min (if stopping) | Ensure clean maintenance start |
| 3 | Put device in STANDBY | 1 min | Prepare for maintenance |
| 4-5 | Start maintenance & poll status | 30-60 min | Run firmware maintenance |
| 6-7 | Reboot & verify STANDBY | 5 min | Complete maintenance cycle |
| 8 | Wait for DeepSleep entry | 15 min | Natural deep sleep entry |
| 9 | Verify SSH inaccessible | - | Confirm DeepSleep state |
| 10-11 | IR wake-up & measure time | 30-60 sec | Measure wake-up performance |
| 12 | Validate functionality | 3-5 min | Confirm device operational |

**Total: 60-95 minutes**

## Quick Start

### Option 1: Queue Method (Recommended)
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",     # Optional: auto-detects from device name
        "sleep_duration_minutes": 60
    }
]

device.execute_queue_method(execution_queue, iterations=1)
```

### Option 2: Direct Call
```python
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process

result = execute_maintenance_deepsleep_wakeup_process(
    device_ip="10.0.0.126",
    port=10022,
    username="root",
    password="skypass",
    device_name="SKY-Device-1",
    remote_type="SKY"
)

print(f"Wakeup time: {result['wakeup_time_seconds']} seconds")
print(f"Success: {result['success']}")
```

### Option 3: Command Line
```bash
python method_maintenance_deepsleep_wakeup.py 10.0.0.126 10022 root skypass "SKY-Device" SKY
```

## Key Return Values

```python
{
    "iteration": 1,
    "screenshots": ["screenshot_before.png", "screenshot_after.png"],
    "success": True,
    "wakeup_time_seconds": 45.3,  # ⭐ Key metric: Time from IR POWER to SSH accessible
    "details": "Maintenance completed, DeepSleep verified, wakeup time: 45.3s"
}
```

## Response Statuses

| Status | Polling Interval | Meaning |
|--------|------------------|---------|
| `IDLE` | - | No maintenance running |
| `IN_PROGRESS` | 30 sec | Maintenance cycle active |
| `MAINTENANCE_ERROR` | - | Maintenance failed |
| `MAINTENANCE_COMPLETE` | - | Maintenance succeeded |
| `UNKNOWN` | - | Status parsing failed |

## Configuration Checklist

### ✓ Device Must Have
- [ ] RDK MaintenanceManager support (JSONRPC 9998)
- [ ] IR blaster capability
- [ ] SSH on port 10022 (or configured port)
- [ ] QueryPowerState command
- [ ] IR codes configured in devices.json

### ✓ iTach Configuration
```json
{
    "ir_config": {
        "itach_ip": "10.0.0.12",
        "itach_port": 4998,
        "ir_port": "1"
    }
}
```

### ✓ Remote Types
| Type | Default For | Commands |
|------|-------------|----------|
| `XUMO_PR3` | Device names with "XUMO" | POWER, OK, Back, etc. |
| `SKY_LC103` | Device names with "SKY" | POWER, OK, Back, etc. |

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Maintenance never completes | Device firmware issue | Check device logs, increase polling timeout |
| Device not in DeepSleep | Premature wakeup | Verify USB disconnected, check power supply |
| SSH reconnect timeout | Device not booting | Check network, verify boot logs, try manual wake-up |
| IR command fails | iTach unreachable | Verify iTach IP/port, test IR separately |
| Device lock lost | Job cancelled | Job can be retried |

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Maintenance duration | 30-60 min | Varies by device |
| DeepSleep entry time | <15 min | After reboot |
| Wakeup time (IR to SSH) | 30-60 sec | Key performance indicator |
| HOME screen validation | <5 min | Post-wakeup |

## Debug Logging

Enable detailed logging:
```python
from method_utils import log_message

# Logs are automatically written to:
# - Console (real-time)
# - USB execution log: iteration_logs/device_MAINTENANCE_DEEPSLEEP_WAKEUP_UTC.log
# - Screenshots folder: screenshots/device_Iteration-N_Before-Maintenance/
# - Screenshots folder: screenshots/device_Iteration-N_After-Wakeup/
```

## Parameter Reference

| Parameter | Type | Default | Options |
|-----------|------|---------|---------|
| `remote_type` | str | auto-detect | XUMO, SKY, None |
| `sleep_duration_minutes` | int | 60 | 10, 30, 60, 120, 300, custom |
| `iteration` | int | 1 | 1-N |
| `port` | int | 10022 | any |
| `username` | str | root | any |

## Expected Log Output

```
================================================================================
MAINTENANCE > DEEPSLEEP > WAKEUP PROCESS - START
================================================================================
Device: SKY-Device-1 (10.0.0.126)
Iteration: 1
DeepSleep Duration: 60 minutes
================================================================================

[STEP 1-2] Checking maintenance activity status...
✓ Device is online and responsive
✓ No active maintenance (status: IDLE)

[STEP 3] Putting device in STANDBY...
✓ POWER key sent
✓ Device confirmed in STANDBY

[STEP 4] Starting maintenance cycle...
✓ Start maintenance response: {"jsonrpc":"2.0","id":"3","result":{"success":true}}

[STEP 5] Polling maintenance activity status...
  ⏳ Poll interval: waiting 30 seconds (Poll #1)...
  🔍 Status: IN_PROGRESS
  ✓ Device still in STANDBY
  
[... polling continues ...]

  🔍 Status: MAINTENANCE_COMPLETE
✓ Maintenance cycle complete

[STEP 6] Rebooting device after maintenance...
✓ Reboot response: {"jsonrpc":"2.0",...}

[STEP 8] Waiting 15 minutes for device to enter DeepSleep...
  ⏳ 14m remaining until DeepSleep wakeup...
✓ 15-minute wait complete

[STEP 9] Verifying device is inaccessible...
✓ Device is inaccessible via SSH (DeepSleep confirmed)

[STEP 10] Waking up device with IR POWER command...
📡 Auto-detected remote type from device name: SKY_LC103
✓ IR POWER command sent successfully

[STEP 11] Measuring device wakeup time...
✓ Device accessible after 45.3 seconds from IR POWER key

================================================================================
MAINTENANCE > DEEPSLEEP > WAKEUP PROCESS - COMPLETED SUCCESSFULLY
================================================================================
```

## Integration Examples

### With Sequence
```python
sequence = {
    "name": "Complete Device Maintenance",
    "methods": [
        {"method": "maintenance_deepsleep_wakeup"}
    ]
}
execute_sequence(device_ip, sequence)
```

### With Multiple Iterations
```python
execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=[
        {"method": "maintenance_deepsleep_wakeup", "sleep_duration_minutes": 60}
    ],
    iterations=3  # Run 3 times
)
```

### With Custom Sleep Duration
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "sleep_duration_minutes": 120  # 2 hours
    }
]
```

## Files Modified/Created

| File | Change |
|------|--------|
| `method_maintenance_deepsleep_wakeup.py` | ✅ Created |
| `config_commands.py` | ✅ Added maintenance commands |
| `services/test_execution_service.py` | ✅ Added method handler |
| `MAINTENANCE_DEEPSLEEP_WAKEUP_METHOD.md` | ✅ Full documentation |

## Key Timestamps (in logs)

```
2026-04-14T12:00:00.123456 - Maintenance activity check
2026-04-14T12:01:00.234567 - Device in STANDBY
2026-04-14T12:02:00.345678 - Maintenance started
2026-04-14T12:05:00.456789 - Maintenance polling begins
2026-04-14T12:35:00.567890 - Maintenance complete, reboot initiated
2026-04-14T13:35:00.678901 - DeepSleep wait begins
2026-04-14T13:50:00.789012 - DeepSleep wait complete
2026-04-14T13:50:00.890123 - IR POWER command sent ← Reference point
2026-04-14T13:50:45.901234 - SSH reconnect successful ← wakeup_time = 45.3 sec
```

## Metrics Collection

```python
# Extract from result
wakeup_time = result.get('wakeup_time_seconds')
success = result.get('success')
details = result.get('details')

# For performance analysis
if success:
    print(f"✓ Wakeup performance: {wakeup_time:.1f} seconds")
else:
    print(f"✗ Failed: {details}")
```

## Support

For detailed information, see:
- Full documentation: [MAINTENANCE_DEEPSLEEP_WAKEUP_METHOD.md](MAINTENANCE_DEEPSLEEP_WAKEUP_METHOD.md)
- Method source: [method_maintenance_deepsleep_wakeup.py](method_maintenance_deepsleep_wakeup.py)
- Original spec: [Attached document in requirements](Untitled-1)
