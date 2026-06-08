# Device Logs Organization Update

## Problem
Device logs captured from `/opt/logs/` on devices were being saved to a flat `device_logs/` directory without device identification. This made it impossible to determine which log file belonged to which device when testing multiple devices.

Example of old structure:
```
device_logs/
├── Iteration-5_Reboot-ERROR_sky-messages.log
├── Iteration-5_Reboot-ERROR_core_log.txt
├── Iteration-10_Reboot-FAILED_sky-messages.log
└── Iteration-10_Reboot-FAILED_core_log.txt
```
**Issue**: Cannot tell which device these logs came from!

## Solution Implemented

### New Folder Structure
Device logs are now organized with device-specific folders and iteration subfolders:

```
device_logs/
├── 10.253.182.85/              # Device IP
│   ├── ITR-1/                  # Iteration 1
│   │   ├── 10.253.182.85_DeviceName_Iteration-1_Reboot-ERROR-Logs_20260114_UTC.tar.gz
│   │   ├── sky-messages.log
│   │   └── core_log.txt
│   ├── ITR-2/                  # Iteration 2
│   │   ├── sky-messages.log
│   │   └── core_log.txt
│   └── ITR-5/
│       └── ...
└── 10.253.182.90/              # Another device
    ├── ITR-1/
    └── ITR-2/
```

### Benefits
1. ✅ **Device Identification**: Each device has its own folder (by IP address)
2. ✅ **Iteration Tracking**: Logs organized by iteration number
3. ✅ **Easy Navigation**: Find logs for specific device/iteration quickly
4. ✅ **No Conflicts**: Multiple devices can have same iteration numbers
5. ✅ **Clear Hierarchy**: device_ip → iteration → log files

## Code Changes

### 1. Updated `method_utils.py`

#### `capture_device_logs_sftp()` function:
- Added `device_ip` parameter
- Creates folder structure: `device_logs/<device_ip>/ITR-<iteration>/`
- Updated docstring with folder structure details

#### `capture_minimal_logs_fallback()` function:
- Added `device_ip` parameter
- Uses same folder structure as main capture function
- Ensures fallback logs go to correct device folder

### 2. Updated Method Files

All method files now pass `device_ip` to capture functions:

**method_reboot.py**:
- Line ~166: `capture_device_logs_sftp(ssh, log_filename, log_message, iteration, device_ip)`
- Line ~249: `capture_minimal_logs_fallback(ssh, ..., iteration, device_ip)`

**method_reboot_performance.py**:
- Line ~366: Updated both capture function calls with `device_ip`

**method_reboot_performance_v2.py**:
- Line ~551: Updated both capture function calls with `device_ip`

## Log File Contents

### Full Capture (SFTP):
When successful, downloads a `.tar.gz` archive containing:
- All files from `/opt/logs/` on the device
- sky-messages.log
- core_log.txt
- receiver.log (if present)
- Other system logs

### Fallback Capture:
When SFTP fails, captures last 100 lines of:
- `/opt/logs/sky-messages.log` → `Iteration-X_Method-Status_sky-messages.log`
- `/opt/logs/core_log.txt` → `Iteration-X_Method-Status_core_log.txt`

## Usage Examples

### Finding Logs for a Specific Device and Iteration:
```bash
# Device 10.253.182.85, Iteration 5
cd device_logs/10.253.182.85/ITR-5/

# View sky-messages.log
cat sky-messages.log

# View all logs for this iteration
ls -lh
```

### Finding All Logs for a Device:
```bash
# All iterations for device 10.253.182.85
cd device_logs/10.253.182.85/
ls -lh
# Shows: ITR-1/ ITR-2/ ITR-3/ ...
```

### Finding Logs Across All Devices for Iteration 10:
```bash
find device_logs/ -type d -name "ITR-10"
# Output:
# device_logs/10.253.182.85/ITR-10/
# device_logs/10.253.182.90/ITR-10/
```

## Two Log Directory Types

### 1. `iteration_logs/` - Test Execution Logs
- **Purpose**: Dashboard's view of test execution
- **Content**: SSH commands, timing, step-by-step execution details
- **Format**: `<device_ip>_<method>_<timestamp>_UTC.log`
- **Example**: `10.253.182.85_Reboot_20260114_042623_UTC.log`

### 2. `device_logs/` - Device System Logs
- **Purpose**: Device's internal system logs
- **Content**: Actual log files from device's `/opt/logs/`
- **Format**: `<device_ip>/<ITR-N>/<logfile>`
- **Example**: `10.253.182.85/ITR-5/sky-messages.log`

## Backward Compatibility

Old logs in flat `device_logs/` structure remain accessible. New logs will use the device-specific folder structure. You can clean up old logs after verifying the new structure works correctly.

## Migration (Optional)

To organize existing logs by device, you can manually create device folders and move logs, or simply let new logs use the new structure and archive old ones.

## Testing

After deployment, verify:
1. New device logs appear in `device_logs/<device_ip>/ITR-N/` structure
2. Multiple devices create separate folders
3. Iteration subfolders are created correctly
4. Log files include device identification in filename

---

**Updated**: January 14, 2026  
**Status**: ✅ Implemented and Ready for Testing  
**Files Modified**: 
- `method_utils.py`
- `method_reboot.py`
- `method_reboot_performance.py`
- `method_reboot_performance_v2.py`
