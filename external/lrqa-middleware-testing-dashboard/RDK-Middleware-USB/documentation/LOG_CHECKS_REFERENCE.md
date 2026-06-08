# Complete List of Post-Reboot Log Checks for Reboot PerformanceV2

## Overview
This document lists all available log checks that appear in the "POST-REBOOT LOG CHECKS (MANDATORY)" dialog when you select the Reboot PerformanceV2 method.

---

## LOG CHECK COMMANDS (Grep-based Pattern Matching)

### 1. **Check Home**
- **Display Name in Prompt:** `Check Home`
- **Check Key:** `home`
- **File(s) Searched:** `/opt/logs/sky-messages.log`
- **Log Pattern (Regex):**
  ```
  QMS Bookmark.*HOME_TILES.*load.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui
  ```
- **Command Executed:**
  ```bash
  grep -E "QMS Bookmark.*HOME_TILES.*load.*complete|App focus: Focus set to app.*appId=com.entos.monarch_ui" /opt/logs/sky-messages.log
  ```
- **Purpose:** Detects when HOME screen loads successfully on Sky and Rogers-Xfinity devices
- **Devices Supported:** Sky, Rogers-Xfinity
- **Variable Name in Config:** `log_check_command_HOME`

---

### 2. **Check Network Error**
- **Display Name in Prompt:** `Check Network Error`
- **Check Key:** `network_error`
- **File(s) Searched:** `/opt/logs/sky-messages.log`
- **Log Patterns (Regex - Any of these):**
  ```
  .*MS:EPG Set new panel gadget.*tiles-disconnected.*
  .*Argument missing: Let's try that again
  .*to refresh your connection.*
  ```
- **Command Executed:**
  ```bash
  grep -E ".*MS:EPG Set new panel gadget.*tiles-disconnected.*|.*Argument missing: Let's try that again|.*to refresh your connection.*" /opt/logs/sky-messages.log
  ```
- **Purpose:** Detects network connectivity errors and EPG panel failures
- **Variable Name in Config:** `log_check_command_Network_Error`

---

### 3. **Check Crash**
- **Display Name in Prompt:** `Check Crash`
- **Check Key:** `crash`
- **File(s) Searched:** `/opt/logs/core_log.txt`
- **Log Pattern (Regex):**
  ```
  .*process crash.*
  ```
- **Command Executed:**
  ```bash
  grep -E ".*process crash.*" /opt/logs/core_log.txt
  ```
- **Purpose:** Detects when any system process crashes
- **Variable Name in Config:** `log_check_command_Crash`

---

### 4. **Check Crash WPFFramework**
- **Display Name in Prompt:** `Check Crash WPFFramework`
- **Check Key:** `crash_wpeframework`
- **File(s) Searched:** `/opt/logs/core_log.txt`
- **Log Pattern (Regex):**
  ```
  .*Process crashed = WPEFramework.*
  ```
- **Command Executed:**
  ```bash
  grep -E ".*Process crashed = WPEFramework.*" /opt/logs/core_log.txt
  ```
- **Purpose:** Specifically detects WPEFramework process crashes
- **Variable Name in Config:** `log_check_command_Crash_WPEFramework`

---

### 5. **Check Realtek**
- **Display Name in Prompt:** `Check Realtek`
- **Check Key:** `realtek`
- **File(s) Searched:** `/opt/logs/*` (all files in logs directory)
- **Log Pattern (Regex):**
  ```
  .*Realtek module.*
  ```
- **Command Executed:**
  ```bash
  grep -E ".*Realtek module.*" /opt/logs/*
  ```
- **Purpose:** Detects Realtek module events
- **Variable Name in Config:** `log_check_command_Realtek`

---

## SYSTEM COMMANDS (Direct Linux Commands)

### 6. **Check Teetz**
- **Display Name in Prompt:** `Check Teetz`
- **Check Key:** `teetz`
- **Command Type:** System Directory Listing
- **Command Executed:**
  ```bash
  ls -ltr /lib/teetz/
  ```
- **Purpose:** Lists files in the teetz library directory (ordered by modification time)
- **Variable Name in Config:** `system_command_teetz`

---

### 7. **Check Disk Space**
- **Display Name in Prompt:** `Check Disk Space`
- **Check Key:** `disk_space`
- **Command Type:** System Disk Usage
- **Command Executed:**
  ```bash
  df -h
  ```
- **Purpose:** Shows disk space usage in human-readable format
- **Output Format:** Filesystem, Size, Used, Available, Use%, Mounted on
- **Variable Name in Config:** `system_command_disk_space`

---

### 8. **Check Memory Usage**
- **Display Name in Prompt:** `Check Memory Usage`
- **Check Key:** `memory_usage`
- **Command Type:** System Memory Usage
- **Command Executed:**
  ```bash
  free -h
  ```
- **Purpose:** Shows memory usage in human-readable format
- **Output Format:** total, used, free, shared, buffer/cache
- **Variable Name in Config:** `system_command_memory_usage`

---

### 9. **Check Top**
- **Display Name in Prompt:** `Check Top`
- **Check Key:** `top`
- **Command Type:** System Process Monitoring
- **Command Executed:**
  ```bash
  top -b -n 1 | head -n 20
  ```
- **Purpose:** Shows top 20 lines of process information (batch mode, single iteration)
- **Output Format:** System summary + top processes by CPU/memory
- **Variable Name in Config:** `system_command_top`

---

### 10. **Check Dsmgr Status**
- **Display Name in Prompt:** `Check Dsmgr Status`
- **Check Key:** `dsmgr_status`
- **Command Type:** System Service Status
- **Command Executed:**
  ```bash
  systemctl status dsmgr.service | grep -E "Active"
  ```
- **Purpose:** Checks if DSMGR service is active
- **Output Format:** Active status line (active/inactive)
- **Variable Name in Config:** `system_command_dsmgr_status`

---

## APPROVED PATTERNS (From log_pattern_submissions.json)

Additional patterns can be submitted by users and approved by admins. These are stored in `log_pattern_submissions.json`.

**Format for each approved pattern:**
```json
{
  "pattern_name": {
    "log_pattern": "regex_pattern_here",
    "file_path": "/path/to/log/file",
    "description": "Human readable description",
    "submitted_by": "username"
  }
}
```

When approved patterns are loaded, they follow the same display format as the commands above.

---

## HOW THEY APPEAR IN THE PROMPT DIALOG

When you select "Reboot PerformanceV2" method, the prompt displays:

```
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
[... plus any approved patterns]

Options:
• Enter "-NA-" (without quotes) = Skip all checks
• Enter numbers (e.g., 1,3,5) = Run specific checks
• Enter "ALL" = Run all available checks

Note: Field is MANDATORY (enter -NA- to bypass)
```

---

## INTERACTION EXAMPLES

### Example 1: Check specific items (1, 3, 5)
```
User enters: 1,3,5
Result: Check Home, Check Crash, Check Teetz are executed in sequence
```

### Example 2: Run all checks
```
User enters: ALL
Result: All 10 checks are executed in sequence
```

### Example 3: Skip all checks
```
User enters: -NA-
Result: Checks are skipped, test continues with HOME screen detection only
```

### Example 4: Single check
```
User enters: 2
Result: Only "Check Network Error" is executed
```

---

## FILE LOCATIONS

All log files are located on the device at:
- `/opt/logs/sky-messages.log` - Main application logs
- `/opt/logs/core_log.txt` - Process crash logs
- `/opt/logs/*` - Any log file (for Realtek check)
- `/lib/teetz/` - Teetz library directory (on device filesystem)

---

## CONFIGURATION FILE LOCATION

All check commands are defined in: [config_log_patterns.py](config_log_patterns.py)

To add a new check, add a new variable to this file:
```python
# For log pattern checks
log_check_command_MyCheck = f"grep -E \"pattern_here\" /opt/logs/file.log"

# For system commands
system_command_my_status = "your-linux-command-here"
```

The new check will automatically appear in the prompt dialog on next page reload!

---

## BACKEND PROCESSING FLOW

1. **Frontend:** Fetches `/api/optional_checks` endpoint
2. **Backend:** `get_all_optional_checks()` in `config_log_patterns.py`
   - Calls `get_log_check_commands()` (filters log checks)
   - Calls `get_system_commands()` (gets system commands)
   - Calls `get_all_patterns_with_commands()` (loads approved patterns)
   - Merges all three dictionaries
3. **Display:** JavaScript builds prompt with transformed descriptions
4. **User Input:** Parses numbers and executes selected checks
5. **Execution:** [method_reboot_performance_v2.py](method_reboot_performance_v2.py#L261-L350) runs selected commands via SSH

---

## SOURCE CODE REFERENCES

- **Check Definitions:** [config_log_patterns.py](config_log_patterns.py#L1-L45)
- **Backend Functions:** [config_log_patterns.py](config_log_patterns.py#L75-L125)
- **API Endpoint:** [app.py](app.py#L760-L772)
- **Frontend Dialog:** [templates/index.html](templates/index.html#L1520-1590)
- **Execution:** [method_reboot_performance_v2.py](method_reboot_performance_v2.py#L232-L350)
