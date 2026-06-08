# Reboot Performance V2 Method - Complete Guide

## Overview

**Reboot Performance V2** is an advanced reboot monitoring method that measures the time it takes for a device to reboot and reach the HOME screen. It includes mandatory post-reboot validation checks and comprehensive logging.

**Method Key:** `reboot_performance_v2`

**Display Name:** Reboot Performance V2

**File Location:** [method_reboot_performance_v2.py](method_reboot_performance_v2.py)

---

## Key Features

### ✓ Enhanced Features (vs Legacy Reboot Performance)
- **BEFORE Screenshot** - Captures device state before reboot
- **AFTER Screenshot** - Captures device state after reboot reaches HOME
- **Screenshot Comparison** - Validates screen transitions
- **Fixed 85-second Wait** - Standard wait after reboot command
- **Configurable Timeout** - Adjustable HOME screen detection timeout (default: 180s)
- **Post-Reboot Log Checks** - MANDATORY validation checks (can skip with -NA-)
- **Log Filtering** - Only analyzes logs AFTER reboot timestamp
- **Performance Timing** - Calculates exact reboot duration from logs

### ✗ Limitations
- Screen validation is informational only (doesn't affect pass/fail)
- Test passes if HOME screen log line is detected
- Requires valid SSH credentials

---

## Execution Flow (8 Steps)

### **STEP 1: Device Connection & Pre-Reboot Setup**
```
Purpose: Establish SSH connection and prepare device
Actions:
  • Connect via SSH to device (IP, port 10022, user/pass)
  • Fetch device build details (model, version)
  • Activate ScreenCapture service
  • Navigate to HOME screen by sending HOME key
  • Wait 10 seconds for UI to settle
  
Expected Result: Device ready on HOME screen
```

### **STEP 2: Capture BEFORE Screenshot**
```
Purpose: Document device state before reboot
Actions:
  • Take screenshot of current device state
  • Store in execution folder: screenshots/BEFORE_screen.png
  
Expected Result: Reference screenshot captured for comparison
```

### **STEP 3: Send Reboot Command**
```
Purpose: Initiate device reboot
Actions:
  • Execute: systemctl reboot
  • Record exact reboot timestamp (UTC)
  • Close SSH connection gracefully
  • Capture start time: reboot_start_time
  
Expected Result: Device rebooting, SSH disconnected
```

### **STEP 4: Wait for Device to Come Back Online**
```
Purpose: Establish new SSH connection after reboot
Actions:
  • Wait fixed 85 seconds (let device fully boot)
  • Attempt SSH connection every 5 seconds
  • Maximum wait: ~90 seconds for SSH to respond
  • Reactivate ScreenCapture service on new connection
  
Expected Result: New SSH session established, device booting
```

### **STEP 5: Monitor Logs for HOME Screen Detection**
```
Purpose: Detect when device reaches HOME screen
Actions:
  • Monitor /opt/logs/sky-messages.log in real-time
  • Search for HOME indicators:
    - Sky:          "QMS Bookmark.*HOME_TILES.*load.*complete"
    - Rogers-Xfinity: "App focus: Focus set to app.*appId=com.entos.monarch_ui"
  • Only check log lines AFTER reboot timestamp
  • Timeout: {home_screen_timeout} seconds (default: 180s)
  • Poll interval: 1 second
  
Expected Result: HOME screen log line found or timeout reached
```

### **STEP 6: Calculate Reboot Performance Time**
```
Purpose: Compute exact reboot duration
Actions:
  • If HOME found: parse log timestamp from detected line
  • Calculate: log_timestamp - reboot_start_time
  • Result: Exact seconds from reboot command to HOME appearance
  • Fallback: Use detection time if timestamp parsing fails
  
Expected Result: Reboot duration in seconds (e.g., "42.35s")
```

### **STEP 7: Capture AFTER Screenshot & Screen Validation**
```
Purpose: Document final device state and validate screen transition
Actions:
  • Take screenshot of device (should show HOME screen)
  • Compare BEFORE vs AFTER using image analysis
  • Validate screen has changed appropriately
  • Results: Pass/Warn/Fail (informational only)
  • Store: screenshots/AFTER_screen.png
  
Expected Result: Screenshots captured, comparison performed
```

### **STEP 8: Execute Post-Reboot Log Checks (MANDATORY)**
```
Purpose: Validate device system state after reboot
Actions:
  • Run user-selected post-reboot checks
  • Examples:
    - Check Home           (grep in sky-messages.log)
    - Check Crash          (grep in core_log.txt)
    - Check Disk Space     (df -h command)
    - Check Memory Usage   (free -h command)
    - ... 10+ other checks available
  
  User Options:
    • "-NA-"  = Skip all checks
    • "1,3,5" = Run specific check numbers
    • "ALL"   = Run all available checks
    • "2"     = Run single check
  
Expected Result: Validation checks completed or skipped
```

---

## Input Parameters

### Method Configuration

```javascript
{
  method: "reboot_performance_v2",
  ir_keys: [],                      // Not used for this method
  voice_text: "",                   // Not used
  remote_keys: "",                  // Not used
  expected_screen: "",              // Not used
  screen_name: "",                  // Not used
  wait_seconds: 0,                  // Not used
  command: "",                      // Not used
  expected_output: "",              // Not used
  validation_type: "contains",      // Not used
  
  // REBOOT V2 SPECIFIC PARAMETERS
  optional_checks: {
    skip_all: true,                 // OR custom_commands list
    custom_commands: [
      {
        check_key: "crash",
        description: "Check Crash"
      },
      {
        check_key: "disk_space",
        description: "Check Disk Space"
      }
    ]
  },
  wait_after_reboot: 85,            // DEPRECATED (fixed at 85s)
  home_screen_timeout: 180          // Total timeout in seconds (default: 180)
}
```

### Python Function Signature

```python
def execute_reboot_performance_v2_process(
    device_ip,                    # Device IP address
    port,                         # SSH port (default: 10022)
    username,                     # SSH username (default: root)
    password,                     # SSH password
    iteration=1,                  # Current iteration number
    device_name="Device",         # Device display name
    combined_method_name=None,    # Sequence name if part of sequence
    optional_checks=None,         # Post-reboot validation checks
    wait_after_reboot=80,         # DEPRECATED
    home_screen_timeout=180       # Seconds to wait for HOME (default: 180)
):
```

---

## Pass/Fail Criteria

### ✓ TEST PASSES IF:
1. Device reboots successfully (SSH disconnects)
2. Device comes back online (new SSH connection established)
3. **HOME screen log line is detected** (primary criterion)
4. Optional checks run/skip without errors

### ✗ TEST FAILS IF:
1. Initial SSH connection fails
2. Reboot command execution fails
3. Device doesn't come back online (SSH reconnect timeout)
4. **HOME screen log line NOT detected within timeout** (primary failure)
5. Device experiences critical errors (process crashes, network errors)

### ⚠️ INFORMATIONAL RESULTS:
- Screen validation passes/fails (doesn't affect test result)
- Performance timing shown regardless of pass/fail
- Post-reboot checks executed (failures don't cause test failure)

---

## Output Structure

### Return Dictionary

```python
{
    "iteration": 1,
    "screenshots": [
        "/path/to/BEFORE_screen.png",
        "/path/to/AFTER_screen.png"
    ],
    "logs": [
        "/path/to/device_logs.tar.gz"
    ],
    "success": True,              # PRIMARY: HOME screen detected
    "performance": "42.35s",      # Reboot time in seconds
    "home_found": True,           # HOME screen detected
    "screen_validation": {
        "screen_validation_passed": True,
        "message": "Screen comparison successful"
    },
    "post_reboot_checks": {
        "custom_checks": [
            {
                "check_key": "crash",
                "description": "Check Crash",
                "success": True,
                "output": "",     # No crash found
                "error": ""
            }
        ],
        "overall_passed": True,
        "stop_iterations": False  # Continue with next iteration
    }
}
```

### Log File Location

```
/media/pi/Lexar/Enhancement_output/EXECUTION_LOGS/
  └─ {DATE}/
     └─ {DEVICE_IP}_{DEVICE_NAME}/
        └─ ITR-{N}/
           └─ REBOOT_PERFORMANCE_V2_ITR_{N}.log
```

**Example:** 
```
/media/pi/Lexar/Enhancement_output/EXECUTION_LOGS/2026-01-28/
  10-0-0-126_WESTINGHOUSE-4K-DESK/ITR-1/REBOOT_PERFORMANCE_V2_ITR_1.log
```

---

## Example Execution Log

```
═══════════════════════════════════════════════════════════════════════════════
REBOOT PERFORMANCE MONITORING V2 - START
═══════════════════════════════════════════════════════════════════════════════

[STEP 1] Connecting to device and initial setup...
✓ Connected to device successfully
✓ Build Details Fetched: STM32MP135-V1.0 (Build #1234)
✓ ScreenCapture service activated
✓ HOME button pressed to navigate to HOME screen

[STEP 2] Capturing BEFORE screenshot...
✓ Screenshot captured: BEFORE_screen.png

[STEP 3] Sending reboot command...
📡 Executing: systemctl reboot
✓ Reboot command sent at 2026-01-28 15:30:45.123456 UTC
✓ SSH connection closed
⏱ Waiting 85 seconds for device to reboot...

[STEP 4] Waiting for device to come back online...
⏱ Waiting for SSH connectivity (max 90 seconds)...
  Attempt 1: Connection refused... (0/90s elapsed)
  Attempt 5: Connection refused... (20/90s elapsed)
  Attempt 13: Connection refused... (60/90s elapsed)
  Attempt 17: SSH connected! (80/90s elapsed)
✓ Device back online
✓ ScreenCapture service reactivated

[STEP 5] Monitoring logs for HOME screen detection...
⏱ Monitoring for HOME screen (timeout: 180 seconds)
   Looking for patterns after: 2026-01-28 15:30:45.123456 UTC
  0s: Checking logs...
  5s: Checking logs...
 10s: Checking logs...
 ...
 42s: ✓ HOME screen detected!
   Log line: "2026-01-28T15:31:27.456Z QMS Bookmark id=HOME_TILES_PANEL load complete"

[STEP 6] Calculating reboot performance time...
✓ Reboot Start Time (UTC): 2026-01-28 15:30:45.123
✓ HOME Log Timestamp (UTC): 2026-01-28 15:31:27.456
✓ Calculated Reboot Duration: 42.33 seconds

[STEP 7] Capturing success screenshot...
✓ Screenshot captured: AFTER_screen.png
✓ Screen Comparison:
  ✓ BEFORE -> AFTER: Successfully transitioned to HOME screen

[STEP 8] Post-reboot validation checks...
[POST-REBOOT VALIDATION] Running 2 selected check(s)...
  1/2: Check Crash
    ✓ Pattern NOT found (expected - no crashes)
  2/2: Check Disk Space
    ✓ Disk usage is normal (85GB available)

═══════════════════════════════════════════════════════════════════════════════
✓ REBOOT PERFORMANCE TEST V2 PASSED
✓ Performance: 42.33s
═══════════════════════════════════════════════════════════════════════════════
```

---

## Post-Reboot Checks Dialog

When you select the Reboot Performance V2 method, you'll see a mandatory dialog:

```
10.0.0.32:8080 says

═══ POST-REBOOT LOG CHECKS (MANDATORY) ═══

Available checks:

1. Check Home
2. Check Network Error
3. Check Crash
4. Check Crash WPFFramework
5. Check Realtek
6. Check Teetz
7. Check Disk Space
8. Check Memory Usage
9. Check Top
10. Check Dsmgr Status
[... additional approved patterns]

Options:
• Enter "-NA-" (without quotes) = Skip all checks
• Enter numbers (e.g., 1,3,5) = Run specific checks
• Enter "ALL" = Run all available checks

Note: Field is MANDATORY (enter -NA- to bypass)

[Input field]        [OK] [Cancel]
```

### Examples:

| User Input | Result |
|---|---|
| `-NA-` | Skip all checks, test continues |
| `1,3,5` | Run checks 1, 3, and 5 only |
| `ALL` | Run all 10+ available checks |
| `2` | Run only check 2 (Network Error) |
| (empty) | Error - must enter value |
| `Cancel` | Error - must complete dialog |

---

## Common Issues & Troubleshooting

### Issue 1: "HOME screen log line NOT detected"
**Cause:** Device didn't reach HOME within timeout period
**Solutions:**
- Increase `home_screen_timeout` parameter
- Check device logs: `/opt/logs/sky-messages.log`
- Verify HOME button press worked in STEP 1
- Check for crashes or network issues in post-reboot checks

### Issue 2: "SSH connection timeout after reboot"
**Cause:** Device didn't come back online within 90 seconds
**Solutions:**
- Device may need more than 85 seconds to boot
- Check device hardware/power state
- Verify SSH service is enabled on device
- Check network connectivity

### Issue 3: "Screenshot capture failed"
**Cause:** ScreenCapture service not responding
**Solutions:**
- Verify ScreenCapture service is installed on device
- Check if port 22 (ScreenCapture) is accessible
- Try manual restart: `systemctl restart screencapture`

### Issue 4: "Post-reboot check 'X' failed"
**Cause:** Check detected an issue (crash, disk full, etc.)
**Note:** This doesn't cause test failure unless marked as termination trigger
**Action:** Investigate the specific issue reported

---

## Configuration Files

### Log Patterns ([config_log_patterns.py](config_log_patterns.py))
Defines all available post-reboot checks:
```python
log_check_command_HOME = f"grep -E \"{log_line_HOME}\" /opt/logs/sky-messages.log"
log_check_command_Crash = f"grep -E \"{log_line_Crash}\" /opt/logs/core_log.txt"
# ... 8+ more checks
```

### Timing Configuration ([config_timing.py](config_timing.py))
```python
REBOOT_WAIT = 85          # Fixed wait after reboot command
HOME_TIMEOUT = 180        # Default timeout for HOME detection
```

### Device Log Patterns ([config_log_patterns.py](config_log_patterns.py))
```python
log_line_HOME = "QMS Bookmark.*HOME_TILES.*load.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui"
```

---

## Related Methods

- **Reboot Performance** (v1) - Legacy version without screenshots
- **Deep Sleep** - Measures device sleep/wake transitions
- **Power Key** - Tests device power button
- **Screen Validation** - Validates device display state

---

## Performance Benchmarks

| Device Type | Typical Reboot Time | Timeout | Status |
|---|---|---|---|
| Sky Box | 30-45s | 180s | ✓ Fast |
| Rogers-Xfinity | 40-55s | 180s | ✓ Normal |
| Broadcom | 35-50s | 180s | ✓ Normal |
| High-Load Device | 60-90s | 180s | ⚠ Slow |

---

## Reference Files

- **Main Implementation:** [method_reboot_performance_v2.py](method_reboot_performance_v2.py)
- **Post-Reboot Checks:** [config_log_patterns.py](config_log_patterns.py)
- **Frontend Dialog:** [templates/index.html](templates/index.html#L1520-1590)
- **Backend API:** [app.py](app.py#L760-L772)
- **Execution Service:** [services/test_execution_service.py](services/test_execution_service.py)

---

## Version History

**Version 2.0 (Current)**
- BEFORE/AFTER screenshot comparison
- Fixed 85s wait period
- Configurable timeout
- Mandatory post-reboot checks
- Log-based performance calculation
- Screen validation (informational)

**Version 1.0 (Legacy)**
- Basic reboot timing
- No screenshots
- No post-reboot checks
