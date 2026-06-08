# Detailed Overview of Methods and Functionality (UPDATED)

Based on the complete application code with latest modifications applied.

---

## **1. REBOOT METHOD** (`execute_reboot_process`)

**Purpose**: Tests device's ability to reboot and return to operational state

**Complete Flow**:

### **Phase 1: Pre-Reboot Validation**
- Establishes SSH connection to device
- Fetches build details (`cat /version.txt`)
- Activates ScreenCapture service
- **Sends HOME_KEY_COMMAND** to device to load the HOME screen
- Waits 3 seconds for command processing
- **Waits 10 seconds** for HOME screen to load
- Checks logs for HOME screen presence
- Captures "Before Reboot" screenshot
- **Result**: Confirms device is in known-good state before testing

### **Phase 2: Execute Reboot**
- Sends `systemctl reboot` command via SSH
- Connection closes as device reboots

### **Phase 3: Wait for Reboot (100 Second Wait)**
- Initial countdown: 100 seconds
- **Progress updates every 10 seconds on the SAME line** (no new line for each update)
- Display format: `  90 seconds remaining...` → `  80 seconds remaining...` (overwriting same line)
- Ensures device has adequate time to complete boot sequence

### **Phase 4: Reconnect with Retry Logic**
- Calls `wait_for_device()` function
- Retries SSH connection every 10 seconds
- Timeout: Configured via `total_timeout` setting
- Logs connection attempts until successful

### **Phase 5: Post-Reboot Validation**
- Re-fetches build details from rebooted device
- Reactivates ScreenCapture service
- Checks logs for HOME screen pattern: `log_check_command_HOME`
- Always captures screenshot (success or failure state)

### **Phase 6A: Success Path (HOME Screen Reached)**
- Logs: "✓ Device reached HOME screen after reboot"
- Creates folder: `screenshots/{DeviceIP}_{DeviceName}/ITR-{iteration}/After/`
- Screenshot name: `{DeviceIP}_{DeviceName}_AfterReboot_HomeScreen_{timestamp}.png`
- **15-Minute Maintenance Wait**:
  - Countdown timer: **Updates every 60 seconds on the SAME line**
  - Display format: `  15 minutes remaining...` → `  14 minutes remaining...` (overwriting same line)
  - Allows system maintenance tasks to complete
  - Prevents premature testing during OS stabilization

### **Phase 6B: Failure Path (NO HOME Screen)**
- Logs: "✗ Device did NOT reach HOME screen after reboot"
- Checks device power state via Thunder API
- Creates folder: `screenshots/{DeviceIP}_{DeviceName}/ITR-{iteration}/After/`
- Captures diagnostic screenshot
- Screenshot name: `{DeviceIP}_{DeviceName}_AfterReboot_NO-HOMESCREEN_{timestamp}.png`
- **Enhanced Error Diagnostics**:
  - **Process Crash Detection**: Checks `log_check_command_Crash` for application failures
  - **Network Error Analysis**: Searches `log_check_command_Network_Error` for connectivity issues
  - **Realtek Module Check**: Uses `log_check_command_Realtek` for driver problems
  - **WiFi Error Detection**: Identifies wireless connection failures
- **Log Capture**: 
  - Creates tarball: `tar -czf /media/apps/ITR-{iteration}-NO-HOMESCREEN_AFTERREBOOT_{timestamp}.tgz /opt/logs/*`
  - Downloads via SFTP to local storage
  - Deletes remote file after transfer

**Return**: `True` (success) or `False` (failure)

---

## **2. DEEPSLEEP METHOD** (`execute_deepsleep_process`)

**Purpose**: Tests device's deep sleep/standby functionality and wake-up capability

**Complete Flow**:

### **Phase 1: Pre-DeepSleep Validation** (Optional - Skipped in Sequences)
- `skip_pre_validation=False`: Standalone DeepSleep test
- `skip_pre_validation=True`: Part of method sequence (e.g., Reboot + DeepSleep)

**When Enabled**:
- Checks device power state via `device_status_command`
- Sends HOME key based on state:
  - If STANDBY: Sends IR HOME command to wake + waits 10s
  - If ON: Sends HOME via Thunder API
- Validates HOME screen presence in logs
- Captures "Before DeepSleep" screenshot

### **Phase 2: Initiate DeepSleep**
- Sets DeepSleep timer via Thunder API: `deepsleep_command`
- Sends POWER key via Thunder API to trigger standby
- Closes SSH connection
- **Initial Wait**: 60 seconds for device to enter DeepSleep
- **Verification**: Attempts SSH connection
  - Success = ⚠ Device not in DeepSleep
  - Failure = ✓ Confirmed in DeepSleep state

### **Phase 3: DeepSleep Duration**
- **Wait**: 10 minutes (600 seconds)
- **Progress updates every 60 seconds on the SAME line**
- Display format: `  10 minutes 0 seconds remaining...` → `  9 minutes 0 seconds remaining...` (overwriting same line)
- Simulates extended standby period

### **Phase 4: Wake Device with IR**
- Retrieves device-specific IR configuration from `devices.json`:
  - `itach_ip`: Global Caché iTach IP (e.g., 10.0.0.33)
  - `itach_port`: iTach port (default 4998)
  - `ir_port`: IR connector number (1-3)
- Generates IR POWER code: `sendir,1:{ir_port},30610,38000,1,37,8,29...`
- Sends command to iTach via TCP socket
- Waits 15 seconds for device to boot

### **Phase 5: Reconnect After Wake**
- Calls `reconnect_to_device_with_retry()`:
  - Max retries: 10
  - Retry interval: 5 seconds
- Reactivates ScreenCapture service
- Re-fetches build details

### **Phase 6: Post-Wake Validation**
- Checks logs for HOME screen pattern
- **Success**: Captures HOME screen screenshot
  - Screenshot name: `{DeviceIP}_{DeviceName}_AfterDeepSleep_HomeScreen_{timestamp}.png`
- **Failure with IR Retry Logic**:
  - Checks power state
  - If STANDBY/OFF: Resends IR POWER command (2nd attempt)
  - Waits 10 seconds and rechecks

### **Phase 7: Error Diagnostics** (If HOME Not Reached)
- Captures diagnostic screenshot
- Screenshot name: `{DeviceIP}_{DeviceName}_AfterDeepSleep_NO-HOMESCREEN_{timestamp}.png`
- **OCR Text Extraction**: Identifies current screen via Tesseract
- **Enhanced Error Diagnostics**:
  - **Process Crash Detection**: Checks `log_check_command_Crash` for application failures
  - **Network Error Analysis**: Searches `log_check_command_Network_Error` for connectivity issues
  - **Realtek Module Check**: Uses `log_check_command_Realtek` for driver problems
  - **WiFi Error Detection**: Identifies wireless connection failures
- **Log Capture**: 
  - Creates tarball: `tar -czf /media/apps/ITR-{iteration}-NO-HOMESCREEN_AfterDeepSleep_{timestamp}.tgz /opt/logs/*`
  - Downloads via SFTP to local storage
  - Deletes remote file after transfer

**Return**: `True` (success) or `False` (failure)

---

## **3. IR COMMAND TEST METHOD** (`execute_ir_test_process`)

**Purpose**: Blind IR command transmission without SSH requirement - ideal for wake-up testing

**Complete Flow**:

### **Phase 1: IR Configuration Retrieval**
- Loads device config from `devices.json` (single source of truth)
- No SSH required at this stage
- Logs:
  - Device name
  - iTach IP address
  - iTach port
  - IR port (connector)
  - Selected keys (HOME, POWER, or both)

### **Phase 2: Dynamic IR Code Generation**
- For each selected key:
  - Calls `generate_ir_code(command_type, ir_port)`
  - Loads template from `ir_keycodes.json`
  - Format: `"command_template": "sendir,1:{ir_port},<freq>,<waveform>..."`
  - Substitutes `{ir_port}` with actual port number (1-3)
  - Example output: `sendir,1:3,24624,38000,1,37,8,29,8,65...`

### **Phase 3: Blind IR Transmission**
- **HOME Key** (if selected):
  - Sends IR command to iTach via TCP socket
  - No device interaction required
  - Logs preview of IR code (first 80 characters)
- **POWER Key** (if selected):
  - Same blind transmission process
  - Useful for wake-up scenarios
- Waits 8 seconds for device to process commands

### **Phase 4: Optional SSH Verification**
- Attempts SSH connection (timeout: 10 seconds)
- **If SSH Unavailable**:
  - Logs: "Device may be in DeepSleep or powering up"
  - Returns `True` (commands sent successfully)
  - Skips verification

### **Phase 5: Log Verification** (If SSH Available)
- **For HOME Key**:
  - Searches `/opt/logs/sky-messages.log` for: `keycode: Ethan::Key_Home`
  - Displays most recent matching log entry
  - Shows total count of HOME events
- **For POWER Key**:
  - Searches for: `keycode: Ethan::Key_RCUPower`
  - Displays most recent matching log entry
  - Shows total count of POWER events

### **Phase 6: Debug Information**
- Shows file info: `ls -lh /opt/logs/sky-messages.log`
- Line count: `wc -l /opt/logs/sky-messages.log`
- Last 50 lines preview
- Grep output analysis

**Use Cases**:
- Wake device from DeepSleep without SSH
- Test IR blaster connectivity
- Verify IR code correctness
- Debug remote control issues

**Return**: `True` (verification successful) or `False` (inconclusive)

---

## **4. METHOD SEQUENCES** (Combinations)

The application supports executing multiple methods in sequence. Common combinations:

### **Reboot + DeepSleep**
1. Execute full Reboot process (with pre/post validation)
2. Execute DeepSleep with `skip_pre_validation=True`
   - Skips redundant HOME screen check
   - Uses device state from reboot completion

### **Reboot + DeepSleep + IR Test**
1. Reboot process
2. DeepSleep process (pre-validation skipped)
3. IR Command Test (selected keys)

---

## **SUPPORTING INFRASTRUCTURE**

### **Screenshot Management** (`create_screenshot_folder`)
- Structure: `screenshots/{DeviceIP}_{DeviceName}/ITR-{iteration}/{Phase}/`
- Phase: "Before" or "After"
- Platform-aware: Uses USB stick on Linux (`/media/pi/Lexar`), local directory on Windows

### **IR Code Management** (`generate_ir_code`)
- Single source: `ir_keycodes.json`
- Template format: `"sendir,1:{ir_port},<frequency>,<waveform>..."`
- Dynamic port substitution
- No fallbacks (returns `None` if not found)

### **Device Configuration** (`get_ir_config_for_device`)
- Single source: `devices.json`
- Returns: `{itach_ip, itach_port, ir_port}`
- No fallbacks (returns `None` if device not found)

### **Log Capture** (`capture_device_logs_sftp`)
- Creates tarball on device: `/media/apps/*.tgz`
- Downloads via SFTP
- Deletes remote file after transfer
- Saves to: `{LOGS_DIR}/ITR-{iteration}-*.tgz`

### **Network Diagnostics** (`check_network_and_realtek_errors`)
- Network errors: `grep` via `log_check_command_Network_Error`
- WiFi errors: Pattern matching in logs
- Realtek modules: `grep` via `log_check_command_Realtek`

### **HTML Report Generation** (`generate_html_report`)
- Creates timestamped HTML file
- Table with: Iteration, Phase, Status, Details, Screenshots, Logs
- Color-coded status: Green (PASSED), Red (FAILED), Orange (WARNING)
- Saved to: `{LOGS_DIR}/{DeviceIP}_{method}_{timestamp}.html`

---

## **KEY DESIGN PRINCIPLES**

1. **Single Source of Truth**: All configuration in `devices.json` and `ir_keycodes.json`
2. **No Fallbacks**: Missing configuration returns `None` to force explicit setup
3. **Comprehensive Logging**: UTC timestamps, detailed progress, error diagnostics
4. **Screenshot Evidence**: Always captured for success and failure scenarios
5. **Efficient Progress Display**: Countdown timers update same line instead of creating new lines
6. **Wait Time Preservation**: All original timeouts maintained (100s reboot, 15min maintenance, 10min DeepSleep)
7. **Error Recovery**: IR retry logic, SSH reconnection attempts, multiple validation checks

---

## **CHANGES SUMMARY (Latest Updates)**

### **Reboot Method**:
✅ Added `HOME_KEY_COMMAND` execution before waiting for HOME screen  
✅ Changed HOME screen wait time from 15 seconds to 10 seconds  
✅ Updated 100-second reboot countdown to display on **same line** (updates every 10 seconds)  
✅ Updated 15-minute maintenance countdown to display on **same line** (updates every 60 seconds)  
✅ Standardized screenshot naming: `NO-HOMESCREEN` (all caps)

### **DeepSleep Method**:
✅ Updated 10-minute DeepSleep countdown to display on **same line** with minute:second format  
✅ Progress updates every 60 seconds instead of 30 seconds  
✅ Standardized screenshot naming: `NO-HOMESCREEN` (all caps)  
✅ Enhanced error diagnostics matching reboot method (crashes, network, Realtek, WiFi)  
✅ Log capture for failure scenarios

### **User Experience Improvements**:
- Cleaner console output with same-line countdown updates
- More consistent screenshot naming convention
- Better wait time progression visibility
- Reduced log clutter during long wait periods
