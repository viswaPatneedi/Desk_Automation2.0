# Dashboard.html - Missing Parameter Handlers Analysis

## Executive Summary
**23 total methods found** in Available Test Methods section. **11 have parameter handlers**, **12 do not**.

**Critical Issues: 4 methods that NEED handlers but DON'T HAVE them**

---

## Methods WITH Parameter Handlers ✅

### Synchronous Handlers (in `getMethodParameters()` switch statement)
1. **reboot_perf_v2_optimized** - Collects: remote_type
2. **deepsleep** - Collects: remote_type, sleep_duration_minutes
3. **send_remote_keys** - Collects: remote_keys
4. **wait** - Collects: wait_seconds
5. **execute_command** - Collects: command_text, expected_output, validation_type
6. **screen_validation** - Collects: expected_text
7. **memcapture_tool** - Collects: system_command_name, command, label, duration_seconds, interval_seconds
8. **check_logs** - Collects: selected_patterns (via modal)

### Async Handlers (in `getMethodParametersAsync()` if/else statements)
9. **ir_test** - Collects: ir_keys, remote_type
10. **navigate_to_tiles** - Collects: section, tile_to_navigate
11. **maintenance_deepsleep_wakeup** - Collects: remoteType, sleepDuration, executeDeepSleep
12. **reboot_perf_v2_optimized** - Collects: optional_checks, home_screen_timeout, log_search_patterns, auto_collect_logs

---

## Methods WITHOUT Handlers & Analysis

### ✅ NO HANDLER NEEDED - Straightforward Operations
| Method | Reason | Description |
|--------|--------|-------------|
| **reboot** | No user input required | Performs automatic reboot with built-in validation |
| **power_key** | No user input required | Sends fixed power key command |
| **status** | No user input required | Queries device state - read-only |
| **xumo_activation** | Fully automated | Fetches code & activates automatically |
| **navigate_inputs_xumo** | Predetermined navigation | Fixed menu navigation to Inputs, validates tiles |
| **activate_flux** | Automated script execution | Downloads & executes Flux_widget.sh, extracts IP |
| **collect_device_logs** | Standard operation | Collects all device logs to tar.gz archive |

### 🚨 CRITICAL - NEEDS HANDLER BUT MISSING ✗

#### 1. **soft_hard_boot**
- **data-method:** `soft_hard_boot`
- **Current Status:** ❌ NO HANDLER
- **Tooltip Says:** "**Selectable boot type (HARD or SOFT)**"
- **Expected Parameters:** 
  - `boot_type` - User must choose between:
    - **HARD BOOT**: Uses `systemctl reboot` command
    - **SOFT BOOT**: Navigates Settings GUI > System Management > Reset & Updates > Restart device
- **Implementation Needed:** Modal or prompt to select boot type before execution
- **Why It's Critical:** Without user input, the method cannot determine which boot path to execute

---

#### 2. **voice_command**
- **data-method:** `voice_command`
- **Current Status:** ❌ NO HANDLER
- **Tooltip Says:** "Executes voice commands by converting text to voice action"
  - Examples: `'Search for Netflix'`, `'Open YouTube'`, `'Volume up'`
- **Expected Parameters:**
  - `voice_text` - The voice command text to execute
- **Implementation Needed:** Prompt to enter voice command text
- **Why It's Critical:** Method requires specific voice text to execute - cannot proceed without user input

---

#### 3. **capture_current_screen**
- **data-method:** `capture_current_screen`
- **Current Status:** ❌ NO HANDLER
- **Tooltip Says:** "**Prompts for image name**"
  - Process: 1. Prompts for image name 2. Captures screenshot 3. Saves image in USB session folder
- **Expected Parameters:**
  - `image_name` - User-provided name for the screenshot file
- **Implementation Needed:** Prompt to enter image name before capture
- **Why It's Critical:** Tooltip explicitly states it should prompt for image name - functionality is incomplete

---

#### 4. **trail_method**
- **data-method:** `trail_method`
- **Current Status:** ❌ NO HANDLER
- **Tooltip Says:** "Cloned from Reboot Performance V2 - OPTIMIZED"
  - Features same as reboot_perf_v2_optimized including "**Post-Checks: Optional (enter -NA- to skip)**"
- **Expected Parameters:** 
  - `optional_checks` - Same as reboot_perf_v2_optimized
  - `home_screen_timeout` - Timeout for HOME screen detection
  - `log_search_patterns` - Log patterns to monitor
  - `auto_collect_logs` - Whether to auto-collect logs
- **Implementation Needed:** Add async handler identical or similar to reboot_perf_v2_optimized handler
- **Why It's Critical:** Tooltip indicates it has same features as reboot_perf_v2_optimized (which DOES have a handler), creating inconsistency

---

#### 5. **capture_base_image**
- **data-method:** `capture_base_image`
- **Current Status:** ❌ NO HANDLER
- **Tooltip Says:** "Captures reference screenshots for screen validation"
  - Tip: "**Capture each screen state you want to validate against**"
- **Expected Parameters:**
  - `screen_name` or `reference_name` - Label for the reference screen
- **Implementation Needed:** Prompt to enter screen name/label
- **Note:** Less critical than #1-4 as it might work without input, but best-practice would be to tag reference images with names

---

## Summary Table

| # | Method | data-method | Handler Status | Priority | Parameters Needed |
|---|--------|-------------|---|---|---|
| 1 | Reboot | `reboot` | ✅ N/A | - | None |
| 2 | Reboot Performance V2 | `reboot_perf_v2_optimized` | ✅ YES | - | optional_checks, home_screen_timeout, log_search_patterns, auto_collect_logs |
| 3 | Trail Method | `trail_method` | ❌ MISSING | **HIGH** | optional_checks, home_screen_timeout, log_search_patterns, auto_collect_logs |
| 4 | Soft Boot/Hard Boot | `soft_hard_boot` | ❌ MISSING | **HIGH** | boot_type (HARD or SOFT) |
| 5 | Deep Sleep | `deepsleep` | ✅ YES | - | remote_type, sleep_duration_minutes |
| 6 | Maintenance > DeepSleep > Wakeup | `maintenance_deepsleep_wakeup` | ✅ YES | - | remoteType, sleepDuration, executeDeepSleep |
| 7 | Power Key | `power_key` | ✅ N/A | - | None |
| 8 | Query Power State | `status` | ✅ N/A | - | None |
| 9 | IR Command Test | `ir_test` | ✅ YES | - | ir_keys, remote_type |
| 10 | Send Voice Command | `voice_command` | ❌ MISSING | **HIGH** | voice_text |
| 11 | Send Remote Keys | `send_remote_keys` | ✅ YES | - | remote_keys |
| 12 | Screen Validation | `screen_validation` | ✅ YES | - | expected_text |
| 13 | XUMO Activation | `xumo_activation` | ✅ N/A | - | None |
| 14 | Base Image Capture | `capture_base_image` | ❌ MISSING | **MEDIUM** | screen_name (recommended) |
| 15 | Capture Current Screen | `capture_current_screen` | ❌ MISSING | **HIGH** | image_name |
| 16 | Navigate to Inputs XUMO-TV | `navigate_inputs_xumo` | ✅ N/A | - | None |
| 17 | Activate Flux | `activate_flux` | ✅ N/A | - | None |
| 18 | Navigate to Tiles | `navigate_to_tiles` | ✅ YES | - | section, tile_to_navigate |
| 19 | Wait | `wait` | ✅ YES | - | wait_seconds |
| 20 | Memcapture Tool | `memcapture_tool` | ✅ YES | - | system_command_name/command, label, duration_seconds, interval_seconds |
| 21 | Execute System Command | `execute_command` | ✅ YES | - | command_text, expected_output, validation_type |
| 22 | Collect Device Logs | `collect_device_logs` | ✅ N/A | - | None |
| 23 | Check Available Logs | `check_logs` | ✅ YES | - | selected_patterns |

---

## Recommendations

### High Priority (Block User)
1. **soft_hard_boot** - Must add handler to collect boot type selection
2. **voice_command** - Must add handler to collect voice command text
3. **capture_current_screen** - Must add handler to collect image name (as per tooltip promise)
4. **trail_method** - Must add handler for optional_checks and configuration (consistent with base variant)

### Medium Priority (Improve UX)
5. **capture_base_image** - Add optional handler to collect screen name/label for better reference image management

---

## Code Locations

**Current Handlers In:**
- `templates/dashboard.html` line **2354-2479** - `getMethodParametersAsync()` async function
- `templates/dashboard.html` line **3110-3300+** - `getMethodParameters()` sync switch statement
- `methodsRequiringInput` arrays at lines **2361** and **3119**

**Methods Not Listed in `methodsRequiringInput`:**
```javascript
// Line 2361 - Async array
const methodsRequiringInput = ['ir_test', 'deepsleep', 'maintenance_deepsleep_wakeup', 'send_remote_keys', 'wait', 'execute_command', 'screen_validation', 'reboot_perf_v2_optimized', 'check_logs', 'navigate_to_tiles', 'memcapture_tool'];

// Line 3119 - Sync array  
const methodsRequiringInput = ['deepsleep', 'send_remote_keys', 'wait', 'execute_command', 'screen_validation', 'reboot_perf_v2_optimized', 'check_logs', 'memcapture_tool'];
```

**Missing from both arrays:**
- `soft_hard_boot`
- `voice_command`
- `capture_current_screen`
- `trail_method`
- ~~`capture_base_image`~~ (optional)

