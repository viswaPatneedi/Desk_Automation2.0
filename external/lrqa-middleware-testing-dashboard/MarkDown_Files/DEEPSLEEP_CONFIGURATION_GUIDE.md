# DeepSleep Method - Enhanced Configuration Guide

## Overview

The `execute_deepsleep_process()` method has been enhanced to accept **user-configurable parameters** for:
1. **Remote Type** (XUMO or SKY) - Select which IR remote to use for waking the device
2. **Sleep Duration** (in minutes) - Flexible DeepSleep duration from 10 minutes to multiple hours

This allows users to customize the DeepSleep test in the UI without code modifications.

---

## Updated Method Signature

```python
def execute_deepsleep_process(
    device_ip,                          # Target device IP
    port,                               # SSH port (typically 10022)
    username,                           # SSH username
    password,                           # SSH password
    iteration=1,                        # Iteration number
    skip_pre_validation=False,          # Skip pre-validation checks
    device_name="Device",              # Device name for IR selection
    combined_method_name=None,          # For combined method sequences
    remote_type=None,                   # NEW: IR remote type (XUMO/SKY)
    sleep_duration_minutes=60           # NEW: Sleep duration in minutes
):
    """
    Execute Deep Sleep Process with configurable remote type and sleep duration.
    
    Args:
        remote_type: 'XUMO' or 'SKY' (case-insensitive)
                    If None, auto-detects from device_name
                    
        sleep_duration_minutes: DeepSleep duration in minutes
                               Default: 60 (1 hour)
                               Supported: 10, 30, 60, 120, 300, custom
    
    Returns:
        bool: True if successful, False otherwise
    """
```

---

## Parameter Details

### 1. Remote Type Selection

#### What it does:
- Determines which IR remote control type to use when waking the device from DeepSleep
- Sends the appropriate IR POWER command based on remote type

#### Available Options:
| Option | Use Case | Device Examples |
|--------|----------|-----------------|
| **XUMO** | XUMO-equipped devices | Most modern Comcast devices |
| **SKY** | Sky Broadband remotes | Sky Q, Sky Glass devices |

#### Auto-Detection Logic:
If `remote_type=None`:
```
if 'SKY' in device_name.upper():
    → Use 'SKY_LC103' remote
else:
    → Use 'XUMO_PR3' remote (default)
```

#### Example Usage:
```python
# User selects XUMO from UI dropdown
execute_deepsleep_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="password",
    remote_type="XUMO",           # ← User selected
    sleep_duration_minutes=60
)

# User selects SKY from UI dropdown
execute_deepsleep_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="password",
    remote_type="SKY",            # ← User selected
    sleep_duration_minutes=120
)

# User doesn't set remote_type (auto-detect)
execute_deepsleep_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="password",
    remote_type=None,             # ← Empty, auto-detect from device_name
    sleep_duration_minutes=60
)
```

### 2. Sleep Duration Configuration

#### What it does:
- Configurable DeepSleep wait time in minutes
- Replaces hardcoded 1-hour (60-minute) default
- Progress logging adjusts based on duration

#### Supported Values:
| Duration | Minutes | Seconds | Use Case |
|----------|---------|---------|----------|
| Quick test | 10 | 600 | Rapid validation |
| Standard | 30 | 1,800 | Common test duration |
| **Default** | **60** | **3,600** | Default (1 hour) |
| Extended | 120 | 7,200 | 2-hour stress test |
| Long-running | 300 | 18,000 | 5-hour endurance test |
| Custom | any | any×60 | User-defined |

#### Example Usage:
```python
# Quick 10-minute DeepSleep test
execute_deepsleep_process(
    ...,
    sleep_duration_minutes=10
)

# Standard 1-hour test
execute_deepsleep_process(
    ...,
    sleep_duration_minutes=60  # Default
)

# Extended 2-hour test
execute_deepsleep_process(
    ...,
    sleep_duration_minutes=120
)

# Long-running 5-hour test
execute_deepsleep_process(
    ...,
    sleep_duration_minutes=300
)

# Custom duration (e.g., 45 minutes)
execute_deepsleep_process(
    ...,
    sleep_duration_minutes=45
)
```

#### Progress Logging:
- **For durations < 10 minutes**: Log every 1-2 chunks (10-20 seconds)
- **For durations 10-60 minutes**: Log every 60 seconds
- **For durations > 60 minutes**: Log every 60 seconds with minute breakdown

Example output for 120-minute (2-hour) test:
```
⏱️  DeepSleep duration: 120 minutes (7200 seconds)
Waiting 7200 seconds (120 minutes) before waking up device from DeepSleep...
  ⏱️  Progress: 60/7200 seconds (1m elapsed, 119m remaining)
  ⏱️  Progress: 120/7200 seconds (2m elapsed, 118m remaining)
  ⏱️  Progress: 180/7200 seconds (3m elapsed, 117m remaining)
  ...
  ⏱️  Progress: 7140/7200 seconds (119m elapsed, 1m remaining)
✓ DeepSleep wait complete (7200 seconds = 120 minutes)
```

---

## UI Integration for JOBS

### Job Configuration Form

Add these fields to the DeepSleep method configuration:

```html
<!-- Remote Type Selection -->
<label for="remote_type">IR Remote Type:</label>
<select id="remote_type" name="remote_type">
    <option value="auto">Auto-detect (from device name)</option>
    <option value="XUMO">XUMO Remote (XUMO_PR3)</option>
    <option value="SKY">Sky Remote (SKY_LC103)</option>
</select>

<!-- Sleep Duration Input -->
<label for="deepsleep_duration">DeepSleep Duration (minutes):</label>
<select id="deepsleep_duration" name="sleep_duration_minutes">
    <option value="10">10 minutes (Quick test)</option>
    <option value="30">30 minutes</option>
    <option value="60" selected>60 minutes (1 hour - Default)</option>
    <option value="120">120 minutes (2 hours)</option>
    <option value="300">300 minutes (5 hours)</option>
    <option value="custom">Custom duration</option>
</select>

<!-- Custom Duration Input (shown if "custom" is selected) -->
<div id="custom_duration_div" style="display:none;">
    <label for="custom_duration">Custom duration (minutes):</label>
    <input type="number" id="custom_duration" name="custom_duration" 
           min="1" max="1440" placeholder="Enter minutes (1-1440)">
</div>
```

### Job Queue JSON Structure

```json
{
    "job_id": "deepsleep_001",
    "device_ip": "192.168.1.100",
    "device_name": "Xumo-Device-01",
    "method": "deepsleep",
    "parameters": {
        "iteration": 1,
        "remote_type": "XUMO",          // ← NEW: User-selected
        "sleep_duration_minutes": 60    // ← NEW: User-selected
    },
    "execution_status": "queued",
    "created_at": "2026-03-27T14:30:00Z"
}
```

### Execution Log Output

When the method executes, logs will show (example):
```
================================================================================
DEEPSLEEP PROCESS - START
================================================================================
Device: Xumo-Device-01 (192.168.1.100)
Iteration: 1
DeepSleep Duration: 120 minutes
Remote Type: XUMO
================================================================================

[PRE-DEEPSLEEP VALIDATION] Checking device state...
✓ Device is on HOME screen
✓ Screenshot saved: screenshots/192.168.1.100/Xumo-Device-01/iteration_1/Before/...

Initiating DeepSleep cycle...
✓ DeepSleep timer set: {...}
✓ POWER key sent

Waiting 60 seconds for device to enter DeepSleep...
✓ Device is inaccessible via SSH (confirmed in DeepSleep)

⏱️  DeepSleep duration: 120 minutes (7200 seconds)
Waiting 7200 seconds (120 minutes) before waking up device from DeepSleep...
  ⏱️  Progress: 60/7200 seconds (1m elapsed, 119m remaining)
  ⏱️  Progress: 120/7200 seconds (2m elapsed, 118m remaining)
  ...
✓ DeepSleep wait complete (7200 seconds = 120 minutes)

Sending IR POWER command to wake device from DeepSleep...
📡 Using user-selected remote type: XUMO
🔌 Using IR port 1 with iTach at 192.168.1.50:4999
📡 Remote type: XUMO_PR3
✓ IR POWER command sent successfully

Waiting 15 seconds for device to wake up...
✓ Device is back online (SSH connected)

Checking if device is on HOME screen after DeepSleep...
✓ Device is on HOME screen after DeepSleep
✓ Screenshot saved: screenshots/192.168.1.100/Xumo-Device-01/iteration_1/After/...

✓ DeepSleep process completed successfully for iteration 1
```

---

## Backward Compatibility

### Default Behavior (No Parameters Provided)
```python
# Old code still works - uses defaults
execute_deepsleep_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="password"
)
# Uses: remote_type=None (auto-detect), sleep_duration_minutes=60 (1 hour)
```

### New Features (With Parameters)
```python
# New flexible approach
execute_deepsleep_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="password",
    remote_type="SKY",              # ← NEW
    sleep_duration_minutes=120      # ← NEW
)
```

---

## Testing Scenarios

### Scenario 1: Quick Validation (10 minutes, XUMO)
```python
execute_deepsleep_process(
    device_ip="192.168.1.100",
    device_name="XUMO-Device",
    remote_type="XUMO",
    sleep_duration_minutes=10
)
# Total execution time: ~15 minutes
```

### Scenario 2: Standard Test (1 hour, Auto-detect)
```python
execute_deepsleep_process(
    device_ip="192.168.1.100",
    device_name="SKY-Broadband-Device",
    remote_type=None,              # Auto-detect → SKY
    sleep_duration_minutes=60
)
# Total execution time: ~65 minutes
```

### Scenario 3: Extended Stress Test (5 hours, SKY)
```python
for iteration in range(3):
    execute_deepsleep_process(
        device_ip="192.168.1.100",
        device_name="SKY-Device-01",
        remote_type="SKY",
        sleep_duration_minutes=300,  # 5 hours
        iteration=iteration+1
    )
# Total execution time: ~15 hours (for 3 iterations)
```

---

## Code Implementation Reference

### How Remote Type is Used

```python
# Old code (hardcoded):
remote_type = ir_config.get('remote_type') or ('SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3')

# NEW code (user-configurable):
if remote_type and remote_type.upper() in ['XUMO', 'SKY']:
    selected_remote_type = remote_type.upper()
else:
    selected_remote_type = 'SKY_LC103' if 'SKY' in device_name.upper() else 'XUMO_PR3'

ir_code_power = generate_ir_code("POWER", ir_config['ir_port'], remote_type=selected_remote_type)
```

### How Sleep Duration is Used

```python
# Old code (hardcoded 1 hour):
sleep_duration = 60 * 60  # 3600 seconds
for i in range(360):
    time.sleep(10)

# NEW code (user-configurable):
sleep_duration = sleep_duration_minutes * 60  # Convert to seconds
total_chunks = sleep_duration // 10

for i in range(int(total_chunks)):
    time.sleep(10)
    elapsed = (i + 1) * 10
    # Progress logging...
```

---

## Future Enhancements

1. **Wake-up Command Selection**: Allow users to choose between IR POWER, voice commands, or other methods
2. **Post-DeepSleep Checks**: Option to skip HOME screen validation
3. **Network Validation**: Option to include network connectivity checks after wakeup
4. **Screenshot Intervals**: Option to capture screenshots at regular intervals during DeepSleep wait
5. **Notification Alerts**: Email/Slack alerts when DeepSleep duration completes

---

## Summary

| Feature | Before | After |
|---------|--------|-------|
| **Remote Type** | Hardcoded XUMO | User selectable (XUMO/SKY) |
| **Sleep Duration** | Hardcoded 1 hour | User configurable (10min-5hrs+) |
| **UI Integration** | Not customizable | Editable in JOBS UI |
| **Flexibility** | Fixed behavior | Highly flexible |
| **Logging** | Basic progress | Adaptive progress messages |
| **Use Cases** | Single scenario | Multiple test scenarios |

---

**Last Updated:** 2026-03-27  
**Status:** Enhanced with user-configurable parameters  
**File:** method_deepsleep.py
