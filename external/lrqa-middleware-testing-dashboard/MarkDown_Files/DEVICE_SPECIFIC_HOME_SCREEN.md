# Device-Specific HOME Screen Detection

## Overview

Different RDK devices use different log patterns to indicate when the HOME screen has loaded. This application now supports device-specific HOME screen detection to accurately validate device state after reboot or other operations.

---

## Supported Devices

### **Standard Sky Devices** (Default)
- **Pattern**: `QMS Bookmark.*HOME_TILES.*load.*complete`
- **Log File**: `/opt/logs/sky-messages.log`
- **Example Log Line**:
  ```
  2026-01-14T20:30:15.234Z QMS Bookmark: HOME_TILES load complete
  ```

### **Rogers-Xfinity-IUI Devices**
- **Device Names**: Any device with "ROGERS" and "XFINITY" in the name
- **Pattern**: `.*App focus: Focus set to app.*appId=com.entos.monarch_ui`
- **Log File**: `/opt/logs/sky-messages.log`
- **Example Log Line**:
  ```
  2026-01-14T20:45:37.588Z com.sky.as.apps_com.bskyb.epgui[3303]:  AppsModel.log: "App focus: Focus set to app. appId=com.entos.monarch_ui"
  ```

---

## Configuration

### Location
All HOME screen patterns are defined in **`config_log_patterns.py`**:

```python
# Standard Sky HOME screen pattern
log_line_HOME = "QMS Bookmark.*HOME_TILES.*load.*complete"

# Rogers-Xfinity-IUI HOME screen pattern
log_line_HOME_ROGERS_XFINITY = ".*App focus: Focus set to app.*appId=com.entos.monarch_ui"
```

### Helper Functions

#### **`get_home_screen_pattern(device_name)`**
Returns the appropriate log pattern based on device name.

```python
from config_log_patterns import get_home_screen_pattern

# For standard device
pattern = get_home_screen_pattern("Element-A4K")
# Returns: "QMS Bookmark.*HOME_TILES.*load.*complete"

# For Rogers-Xfinity device
pattern = get_home_screen_pattern("ROGERS-XFINITY-IUIv1")
# Returns: ".*App focus: Focus set to app.*appId=com.entos.monarch_ui"
```

#### **`get_home_screen_command(device_name)`**
Returns the appropriate grep command to check for HOME screen.

```python
from config_log_patterns import get_home_screen_command

# For standard device
command = get_home_screen_command("Element-A4K")
# Returns: 'grep -E "QMS Bookmark.*HOME_TILES.*load.*complete" /opt/logs/sky-messages.log'

# For Rogers-Xfinity device
command = get_home_screen_command("ROGERS-XFINITY-IUIv1")
# Returns: 'grep -E ".*App focus: Focus set to app.*appId=com.entos.monarch_ui" /opt/logs/sky-messages.log'
```

---

## Usage in Method Files

### Current Implementation (Manual)
Currently, method files use the default pattern directly:

```python
from config_log_patterns import log_line_HOME, log_check_command_HOME

# Check HOME screen
stdin, stdout, stderr = ssh.exec_command(log_check_command_HOME)
log_output = stdout.read().decode('utf-8', errors='ignore')

if log_line_HOME.split(".*")[0] in log_output:
    log_message("✓ Device is on HOME screen")
```

### Recommended Update (Device-Aware)
To support device-specific patterns, update method files to use helper functions:

```python
from config_log_patterns import get_home_screen_pattern, get_home_screen_command

# Get device-specific pattern
home_pattern = get_home_screen_pattern(device_name)
home_command = get_home_screen_command(device_name)

# Check HOME screen using device-specific command
stdin, stdout, stderr = ssh.exec_command(home_command)
log_output = stdout.read().decode('utf-8', errors='ignore')

if home_pattern.split(".*")[0] in log_output:
    log_message("✓ Device is on HOME screen")
```

---

## Adding New Device Patterns

### Step 1: Identify the Log Pattern
SSH into the device and monitor the logs:

```bash
ssh root@<device_ip> -p 10022
tail -f /opt/logs/sky-messages.log | grep -i "home\|focus\|load"
```

Perform an action that loads the HOME screen (reboot, press HOME key) and note the unique log line.

### Step 2: Add Pattern to `config_log_patterns.py`

```python
# Add new pattern variable
log_line_HOME_YOUR_DEVICE = ".*unique pattern for your device.*"

# Add corresponding check command
log_check_command_HOME_YOUR_DEVICE = f'grep -E "{log_line_HOME_YOUR_DEVICE}" /opt/logs/sky-messages.log'
```

### Step 3: Update Helper Functions

Update `get_home_screen_pattern()` and `get_home_screen_command()` to detect your device:

```python
def get_home_screen_pattern(device_name):
    if device_name and 'YOUR_DEVICE' in device_name.upper():
        return log_line_HOME_YOUR_DEVICE
    elif device_name and 'ROGERS' in device_name.upper() and 'XFINITY' in device_name.upper():
        return log_line_HOME_ROGERS_XFINITY
    else:
        return log_line_HOME
```

### Step 4: Test
Run a reboot test on the new device and verify HOME screen detection works correctly.

---

## Method Files to Update

The following method files currently use hardcoded `log_line_HOME` and should be updated to use device-specific patterns:

- [x] ~~`config_log_patterns.py`~~ - **Updated with helper functions**
- [ ] `method_reboot.py` - Uses `log_line_HOME` in 2 locations
- [ ] `method_reboot_performance.py` - Uses `log_line_HOME` in 1 location
- [ ] `method_reboot_performance_v2.py` - Uses `log_line_HOME` in 3 locations
- [ ] `method_deepsleep.py` - Uses `log_line_HOME` in 3 locations
- [ ] `method_ir_test.py` - Uses `log_line_HOME` in 1 location

**Note**: Helper functions are available now. Method files can be updated incrementally as needed for device-specific validation.

---

## Testing

### Manual Test on Rogers-Xfinity Device
1. Select `ROGERS-XFINITY-IUIv1` device in dashboard
2. Run **Reboot** method with 1 iteration
3. Check logs for proper HOME screen detection:
   ```
   ✓ Device is on HOME screen after reboot
   ```

### Verify Pattern Match
SSH into device and manually check:

```bash
ssh root@10.0.0.3 -p 10022
grep -E ".*App focus: Focus set to app.*appId=com.entos.monarch_ui" /opt/logs/sky-messages.log | tail -5
```

Expected output:
```
2026-01-14T20:45:37.588Z com.sky.as.apps_com.bskyb.epgui[3303]:  AppsModel.log: "App focus: Focus set to app. appId=com.entos.monarch_ui"
```

---

## Benefits

✅ **Device-Specific Validation**: Accurate HOME screen detection for different device types  
✅ **Centralized Configuration**: All patterns in one config file  
✅ **Easy Extensibility**: Add new device patterns without changing method logic  
✅ **Auto-Detection**: Helper functions automatically select correct pattern based on device name  
✅ **Backward Compatible**: Standard devices continue to work without changes  

---

## Current Status

**✅ Configuration Added** (Commit: 0ff6768)
- Rogers-Xfinity-IUI pattern added
- Helper functions implemented
- log_check_command_HOME_ROGERS available for optional checks

**⏳ Method Files Integration** (Pending)
- Method files still use default pattern
- Can be updated incrementally as needed
- Helper functions ready for integration

---

## Example: Complete Device Registry Entry

```json
{
    "ip": "10.0.0.3",
    "name": "ROGERS-XFINITY-IUIv1",
    "username": "root",
    "password": "",
    "port": 10022,
    "ir_config": {},
    "mac_address": "F0:46:3B:DD:D3:5C",
    "vnc_url": "http://10.0.0.3:5800/"
}
```

**Detection Logic**: If device name contains both "ROGERS" and "XFINITY" (case-insensitive), use Rogers-Xfinity pattern.

---

**Last Updated**: January 14, 2026  
**Commit**: 0ff6768
