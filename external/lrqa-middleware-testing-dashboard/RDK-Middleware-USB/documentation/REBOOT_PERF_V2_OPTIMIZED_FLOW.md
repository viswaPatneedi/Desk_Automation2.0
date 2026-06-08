# Reboot Performance V2 Optimized - Method Flow Documentation

**Last Updated**: February 2, 2026  
**Method File**: `method_reboot_perf_v2_optimized.py`  
**Version**: Ultra-Optimized (10s wait + 40s SSH probe)

---

## 📊 Method Overview

This method tests device reboot performance by measuring time from reboot command to HOME screen detection. It uses intelligent SSH probing and automatic log collection on failures.

**Key Innovation**: Data-driven timing optimization based on real device behavior (84s average boot time)

**Performance**: ~50% faster than legacy V2 (1.5-3 min vs 3-5 min)

---

## 🔄 Complete Sequential Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    METHOD EXECUTION START                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Pre-Reboot Setup                                        │
│ • SSH connect to device (IP:10022)                              │
│ • Fetch build details (firmware version, etc.)                  │
│ • Activate ScreenCapture service                                │
│ • Press HOME button (ensure consistent start state)             │
│ • Wait 10s for UI to settle                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1.5: Capture BEFORE Screenshot                             │
│ • Take reference screenshot before reboot                       │
│ • Non-blocking: continues even if screenshot fails              │
│ • Saved to screenshots_list[0]                                  │
│ • Used later for visual validation comparison                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Send Reboot Command & Timestamp                         │
│ • Capture UTC timestamp (reboot_start_time)                     │
│ • Execute: ssh.exec_command("reboot")                           │
│ • Close SSH connection (device reboots)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Ultra-Optimized Wait + SSH Probing                      │
│ • Wait 10s passive (allow device shutdown to complete)          │
│ • Start SSH probing at 40s mark (optimal for 84s boot avg)      │
│ • Probe every 5s until reconnect (max 100s timeout)             │
│ • Establish SSH connection when device comes online             │
│                                                                  │
│ Why 40s? Real device data shows boots in 84s avg (40-90s range) │
│ Result: Catches SSH reconnection at ideal moment                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Monitor for HOME Screen (Immediate)                     │
│ • Start monitoring immediately after SSH reconnects             │
│ • Check /opt/logs/sky-messages.log every 5 seconds              │
│ • Search for HOME screen patterns:                              │
│   - "QMS.*HOME_TILES.*complete"                                 │
│   - "App.*appId=com.entos.monarch_ui"                           │
│   - Fallback: last 100 lines for HOME indicators                │
│ • Only accept logs AFTER reboot_start_time (timestamp filter)   │
│ • Remaining timeout = home_screen_timeout - elapsed_time        │
│ • Return: (home_found, home_log_line, home_time)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │ HOME Found?     │
                    │ (Decision)      │
                    └─────────────────┘
                      ↓             ↓
                    YES            NO
                      ↓             ↓
        ┌─────────────────┐   ┌─────────────────┐
        │  SUCCESS PATH   │   │  FAILURE PATH   │
        │   (Steps 5-7)   │   │  (Steps 5-6.6)  │
        └─────────────────┘   └─────────────────┘
```

---

## 📋 CRITICAL: Log Collection Strategy (ONE capture per iteration)

### **SUCCESS PATH - Log Collection Logic:**
```
IF HOME screen log detected in /opt/logs/sky-messages.log (after reboot_start_time):
  ├─ Run optional_checks (e.g., CHECK CRASH in /opt/logs/core_log.txt for ".*process crash.*")
  ├─ IF crash pattern found:
  │   └─ Capture entire device logs to /media/app/ for this iteration ✅
  └─ IF NO crash pattern found:
      └─ Continue to next iteration (NO log capture) ✅
```

### **FAILURE PATH - Log Collection Logic:**
```
IF HOME screen log NOT detected:
  ├─ Run optional_checks (e.g., CHECK CRASH in /opt/logs/core_log.txt)
  └─ ALWAYS capture entire device logs to /media/app/ for this iteration ✅
      (Regardless of crash pattern detection)
```

### **Decision Matrix:**

| HOME Found? | Crash Detected? | Action | Continue? |
|-------------|-----------------|--------|-----------|
| ✅ YES | ✅ YES | **Collect logs** to /media/app/ | ✅ Continue to next iteration |
| ✅ YES | ❌ NO | **No log capture** | ✅ Continue to next iteration |
| ❌ NO | ✅ YES | **Collect logs** to /media/app/ | ✅ Continue to next iteration |
| ❌ NO | ❌ NO | **Collect logs** to /media/app/ | ✅ Continue to next iteration |

**KEY PRINCIPLE**: Only ONE log file capture per iteration (no duplicates)

---

## ✅ SUCCESS PATH (HOME Screen Found)

### **STEP 5: Calculate Performance**
1. **Parse Log Timestamp** from HOME log line
2. **Calculate Duration**: `reboot_duration = log_timestamp - reboot_start_time`
3. **Log Results**: Display performance (e.g., `84.33s`)

---

### **STEP 6: Calculate Reboot Performance**

1. **Parse Log Timestamp** from HOME log line:
   - Format: ISO 8601 (`2026-01-06T18:58:44.641Z`)
   - Fallback: Custom format (`YYMMDD-HH:MM:SS.microseconds`)

2. **Calculate Duration**:
   ```python
   reboot_duration = log_timestamp - reboot_start_time
   ```

3. **Display Results**:
   ```
   ✓ Reboot Start Time (UTC): 2026-02-02 10:15:30.123
   ✓ HOME Log Timestamp (UTC): 2026-02-02 10:16:54.456
   ✓ Calculated Reboot Duration: 84.33 seconds
   ```

---l_checks` (user-configured):

```python
optional_checks = {
  'custom_commands': [
    {'grep_cmd': 'grep -i "crash" /opt/logs/*', 'label': 'Crash Check'},
    {'grep_cmd': 'grep -E "ERROR|FATAL" /opt/logs/*', 'label': 'Error Check'}
  ],
  'auto_collect_on_match': True
}
```

**Actions**:
- Run custom grep commands on device logs
- Search for crash/error patterns
- Auto-collect logs if patterns detected
- Return pass/fail status
- Check `stop_iterations` flag (halt test if critical error)
 ⭐ CRITICAL

Execute `optional_checks` to determine if log collection is needed:

```python
optional_checks = {
  'custom_commands': [
    {'grep_cmd': 'grep ".*process crash.*" /opt/logs/core_log.txt', 'label': 'CHECK CRASH'},
    {'grep_cmd': 'grep -E "ERROR|FATAL" /opt/logs/*', 'label': 'Error Check'}
  ],
  'auto_collect_on_match': True  # Collect logs if pattern found
}
```

**Execution Flow**:
1. Run each grep command on device
2. Check for pattern matches (e.g., ".*process crash.*" in `/opt/logs/core_log.txt`)
3. **IF pattern found**:
   - Collect entire device logs to `/media/app/`
   - Archive: `{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz`
   - Add to logs_list[]
4. **IF NO pattern found**:
   - No log collection
   - Contin8: Return Success**

```python
{
  "success": True,
  "iteration": 1,
  "performance_seconds": 84.33,
  "screenshots": [
    "/path/to/BEFORE_screenshot.png",
    "/path/to/SUCCESS_screenshot.png"
  ],
  "logs": [
    "/media/app/{device}_ITR-1_logs_20260202_101654.tar.gz"  # Only if crash detected
  ],
  "optional_checks": {
    "overall_passed": True,  # False if crash detected
    "stop_iterations": False,
    "custom_checks": [...],
    "collected_logs": [...]  # Empty if no crash
  },
  "screen_validation": {
    "screen_validation_passed": True,
    "message": "Screen comparison successful"
  }
}
```
 & Collect Logs** ⭐ CRITICAL

**When HOME screen NOT found: ALWAYS collect logs**

**Execution Flow**:
```
1. Run optional_checks (if configured):
   ├─ Execute grep commands (e.g., crash detection in /opt/logs/core_log.txt)
   ├─ Check for pattern matches
   └─ Log results (informational only)

2. ALWAYS collect device logs (regardless of optional_checks result):
   ├─ Create tar.gz of all /opt/logs/* files
   ├─ Store in /media/app/ directory
   ├─ Archive: {device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz
   └─ Add to logs_list[]

3. Continue to next iteration
```

**Why always collect on failure?**
- Device didn't reach HOME screen = something wrong
- Need comprehensive logs for root cause analysis
- Optional checks provide additional context but logs collected regardless

**Example Output**:
```
[STEP 6.5] Device not on HOME screen - Executing post-reboot validation checks...
✓ Running check: CHECK CRASH
ℹ Pattern ".*process crash.*" found in /opt/logs/core_log.txt

[STEP 6.5] Collecting device logs to /media/app for this iteration...
✓ Device logs collected: /media/app/192.168.1.100_Device_ITR-1_logs_20260202.tar.gz
```
```

**Actions**:
1. Create tar.gz archive of all `/opt/logs/*` files
2. Store archive in `/media/app/` directory on device
3. Archive naming: `{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz`
4. Add to `logs_list[]` for result tracking

**Critical**: Ensures you have comprehensive logs when test fails

---

### **LEGACY: SFTP Log Backup**

**Fallback for backward compatibility**:
- Download logs to local system via SFTP
- Store in local `device_logs/` directory
- Minimal log capture if SFTP fails
- Kept for systems that don't support `/media/app/`

---

### **STEP 6.6: Return Failure**

```python
{
  "success": False,
  "iteration": 1,
  "screenshots": [
    "/path/to/BEFORE_screenshot.png",  # ONE log capture (STEP 6.5)
  ],
  "optional_checks": {
    "overall_passed": False,  # May be True/False based on checks
    "custom_checks": [...],
    "stop_iterations": False
  }
}
```

**Note**: Only ONE log archive per iteration. Legacy SFTP backup removed to avoid duplicates. "/media/app/{device}_ITR-1_crash_logs.tar.gz",            # STEP 6.5 (if pattern found)
    "/local/device_logs/{device}_FAILED_Logs.tar.gz"          # Legacy SFTP
  ]
}
```

---

## ⏱️ Timing Breakdown

| Step | Duration | Cumulative | Notes |
|------|----------|------------|-------|
| **1** Pre-reboot setup | ~15s | 15s | Connect + HOME button + settle |
| **1.5** BEFORE screenshot | ~10s | 25s | Non-blocking, continues on fail |
| **2** Send reboot | ~1s | 26s | Command execution |
| **3** Wait + SSH probe | 40-90s | 66-116s | 10s wait + probe from 40s |
| **4** HOME monitoring | 0-30s | 66-146s | Immediate on SSH reconnect |
| **5.5-7** Screenshot + checks | ~15s | 81-161s | Success path |
| **TOTAL (success)** | **~1.5-3 min** | | **vs old 3-5 min** ⚡ |

---

## 🎯 Key Features

### **Performance Optimization**
- ✅ **50% Faster**: 10s wait + 40s SSH probe vs old 85s hard wait
- ✅ **Data-Driven**: Based on real device boot analysis (84s average)
- ✅ **Better Log Coverage**: Monitors logs immediately after SSH reconnect

### **Smart Log Collection**
- ✅ **Pattern-Based**: Search for crash/error patterns, collect if found
- ✅ **Auto-Collect**: Optional automatic collection on HOME screen
- ✅ **Failure Guarantee**: Always collects logs when test fails (STEP 6.6)

### **Robust Failure Handling**
- ✅ **Dual Diagnostics**: STEP 6.5 (pattern checks) + 6.6 (always collect)
- ✅ **Multiple Backups**: /media/app/ + legacy SFTP
- ✅ **Screenshot Analysis**: OCR + network error detection

### **Non-Blocking Design**
- ✅ Screenshots don't halt execution if they fail
- ✅ Informational validations continue on error
- ✅ Multiple fallback mechanisms

### **Timezone Aware**
- ✅ All timestamps in UTC for consistency
- ✅ Accurate performance calculation
- ✅ Cross-timezone reliability

---

## 🆕 Recent Enhancement (Feb 2, 2026) - IMPLEMENTED ✅

**What Changed**: Implemented intelligent log collection strategy to prevent duplicates

**Code Changes in `method_reboot_perf_v2_optimized.py`:**

### **FAILURE PATH (STEP 6.5) - Smart Collection Logic:**
```python
# Strategy: Check for crashes first, then ALWAYS collect logs (only once)
logs_already_collected = False

# 1. Run optional_checks (may collect if crash pattern found)
if optional_checks configured:
    check_results = execute_optional_post_reboot_checks(...)
    if check_results.get('collected_logs'):
        logs_already_collected = True
        logs_list.extend(check_results['collected_logs'])
        # Crash detected → logs collected

# 2. ALWAYS collect on FAILURE (if not already collected)
if not logs_already_collected:
    collect_device_logs_to_media_app(...)
    # No crash detected → still collect logs
else:
    # Skip duplicate - logs already captured
```

### **SUCCESS PATH (STEP 7) - Unchanged:**
- Runs optional_checks
- Collects logs ONLY if crash pattern detected
- No collection if no patterns found

### **Removed from Code:**
- ❌ Legacy SFTP backup (redundant, caused duplicates)
- ❌ Separate STEP 6.6 (merged logic into STEP 6.5)
- ❌ `capture_device_logs_sftp()` call in FAILURE path
- ❌ `capture_minimal_logs_fallback()` call

---

**Implementation Summary**:
- **SUCCESS PATH (STEP 7)**: Only collect logs if crash pattern detected in optional_checks
- **FAILURE PATH (STEP 6.5)**: Always collect logs (ONE capture - guaranteed)
- **Duplicate Prevention**: Check `logs_already_collected` flag before second collection

**Log Collection Decision Tree**:
```
                    ┌─────────────────┐
                    │ HOME Found?     │
                    └─────────────────┘
                      ↓             ↓
                    YES            NO
                      ↓             ↓
            ┌─────────────────┐   ┌─────────────────┐
            │ Run optional_   │   │ Run optional_   │
            │ checks          │   │ checks          │
            └─────────────────┘   └─────────────────┘
                      ↓                     ↓
            ┌─────────────────┐   ┌─────────────────┐
            │ Crash detected? │   │ Crash detected? │
            └─────────────────┘   └─────────────────┘
              ↓             ↓       ↓             ↓
            YES            NO     YES            NO
              ↓             ↓       ↓             ↓
        ┌─────────┐   ┌─────────┐ │      ┌──────────┐
        │ Collect │   │ No log  │ │      │ Collect  │
        │ logs    │   │ capture │ │      │ logs     │
        │ (1 file)│   └─────────┘ │      │ (1 file) │
        └─────────┘         Logs collected?
                            (check flag)
                                  │
                            Skip duplicate
```

**Benefits**:
- ✅ **Zero Duplicates**: Only ONE log file per iteration (guaranteed)
- ✅ **Pattern-Based on SUCCESS**: Collect only when crash detected
- ✅ **Always on FAILURE**: Comprehensive diagnostics
- ✅ **Cleaner Storage**: No redundant SFTP backups
- ✅ **Better Performance**: Fewer network transfers

---

## 📝 Configuration Parameters

```python
execute_reboot_perf_v2_optimized_process(
    device_ip="192.168.1.100",
    port=10022,
    username="root",
    password="device_password",
    iteration=1,
    device_name="Sky_Device_01",
    combined_method_name="REBOOT_PERF_V2_OPTIMIZED",
    
    # Optional configuration
    optional_checks={
        'custom_commands': [
            {'grep_cmd': 'grep -i "crash" /opt/logs/*', 'label': 'Crash Check'}
        ],
        'auto_collect_on_match': True,
        'skip_all': False
    },
    
    # Timing parameters
    wait_after_reboot=80,          # Deprecated (now uses optimized probing)
    home_screen_timeout=180,       # Total timeout for HOME screen detection
    
    # Log collection
    auto_collect_logs=False,       # Auto-collect on HOME found
    log_search_patterns=[          # Patterns to search for
        "process crashed",
        "ERROR",
        "FATAL"
    ]
)
```

---

## 🔧 Troubleshooting

### **Issue**: Device doesn't reconnect after reboot
**Check**:
- SSH port 10022 accessible
- Device network configuration
- Firewall rules
- Device power cycle (hard reboot vs soft reboot)

### **Issue**: HOME screen not detected but device is on HOME
**Check**:
- Log patterns in `config_log_patterns.py`
- `/opt/logs/sky-messages.log` contains HOME indicators
- Timestamp filtering (logs after reboot_start_time)
- Log format changes in firmware version

### **Issue**: Screenshots fail consistently
**Check**:
- ScreenCapture service status on device
- `/tmp/screenshot.png` permissions
- SFTP connectivity
- Disk space on device

### **Issue**: Logs not collected to /media/app
**Check**:
- `/media/app/` directory exists on device
- Write permissions on `/media/app/`
- `/opt/logs/` contains log files
- Disk space on device

---

## 📚 Related Files

- **Implementation**: `method_reboot_perf_v2_optimized.py`
- **Utilities**: `method_utils.py`
- **Screenshot Logic**: `screenshot_utils.py`
- **Log Patterns**: `config_log_patterns.py`
- **Timing Config**: `config_timing.py`
- **Commands**: `config_commands.py`

---

**End of Documentation**
