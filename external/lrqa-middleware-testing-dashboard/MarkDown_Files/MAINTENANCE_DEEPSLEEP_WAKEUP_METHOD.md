# Maintenance > DeepSleep > Wakeup Method

## Overview

The **Maintenance > DeepSleep > Wakeup** method is a comprehensive device testing workflow that combines three critical operations:

1. **Maintenance Cycle**: Proper device firmware/software maintenance following RDK MaintenanceManager standards
2. **DeepSleep State**: Verification that the device enters deep sleep correctly
3. **Wakeup & Recovery**: IR-based wake-up with precise timing measurement

This method is essential for validating:
- Device firmware maintenance operations
- Low-power sleep state functionality
- Device recovery from deep sleep
- IR remote control reliability
- Device wake-up time performance

## Architecture

### File Structure

```
method_maintenance_deepsleep_wakeup.py    # Main method implementation
config_commands.py                        # Maintenance Manager JSONRPC commands
config_timing.py                          # Timing configurations
config_ir_blaster.py                      # IR command generation
services/test_execution_service.py        # Method registration & orchestration
```

### Maintenance Manager Commands (RDK)

Four JSONRPC 2.0 commands are used for maintenance operations:

```python
# Check current maintenance activity status
maintenance_get_status_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.getMaintenanceActivityStatus","params":{}}\' http://127.0.0.1:9998/jsonrpc'

# Possible statuses: IDLE, IN_PROGRESS, MAINTENANCE_ERROR, MAINTENANCE_COMPLETE

# Start maintenance cycle
maintenance_start_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.startMaintenance","params":{}}\' http://127.0.0.1:9998/jsonrpc'

# Stop an active maintenance cycle
maintenance_stop_command = 'curl --header "Content-Type: application/json" --request POST --silent -d \'{"jsonrpc":"2.0","id":"3","method":"org.rdk.MaintenanceManager.1.stopMaintenance","params":{}}\' http://127.0.0.1:9998/jsonrpc'

# Reboot with maintenance flag
maintenance_reboot_command = 'curl -d \'{"jsonrpc":"2.0","id":42,"method":"org.rdk.System.reboot","params":{"rebootReason":"MAINTENANCE_REBOOT"}}\' http://127.0.0.1:9998/jsonrpc'
```

## Execution Flow

### 12-Step Process

#### **Step 1-2: Check & Manage Maintenance Status**
```
✓ Connect to device via SSH
✓ Fetch device build details
✓ Query current maintenance activity status
✓ If maintenance in-progress (not ERROR/COMPLETE):
  - Stop the active maintenance
  - Wait 5 minutes before starting new cycle
✓ If no active maintenance, proceed immediately
```

#### **Step 3: Put Device in STANDBY**
```
✓ Send POWER key command via SSH
✓ Wait 30 seconds for device state transition
✓ Query power state using QueryPowerState
✓ Verify device is in STANDBY state
✓ Wait additional 30 seconds (total 1 minute before maintenance)
```

#### **Step 4: Start Maintenance Cycle**
```
✓ Send startMaintenance JSONRPC command
✓ Record timestamp
```

#### **Step 5: Poll Maintenance Status**
```
✓ Poll every 30 seconds for maintenance status
✓ Verify device remains in STANDBY during maintenance
✓ Continue polling until status is MAINTENANCE_ERROR or MAINTENANCE_COMPLETE
✓ Maximum polling timeout: 60 minutes
✓ Validate device lock every 10 seconds (job tracking)
```

#### **Step 6: Device Reboot After Maintenance**
```
✓ Send maintenance reboot command via JSONRPC
✓ Wait 2 minutes for reboot processing
```

#### **Step 7: Verify STANDBY After Reboot**
```
✓ Reconnect to device via SSH
✓ Query power state
✓ Confirm device is in STANDBY
```

#### **Step 8: Wait for DeepSleep Entry**
```
✓ Wait 15 minutes in STANDBY
⏳ Log progress every 60 seconds
✓ This allows device to naturally enter DeepSleep
```

#### **Step 9: Verify DeepSleep (SSH Inaccessible)**
```
✓ Attempt SSH connection with 10-second timeout
✓ If SSH fails → Device confirmed in DeepSleep ✓
✓ If SSH succeeds → Warning (device may not be in DeepSleep)
```

#### **Step 10: Wake Up with IR POWER Command**
```
📝 Record POWER key send timestamp
🔌 Configure IR command based on remote type:
   - XUMO_PR3 (auto-detect if device name contains 'XUMO')
   - SKY_LC103 (auto-detect if device name contains 'SKY')
🔊 Send IR command via iTach device
```

#### **Step 11: Measure Wakeup Time**
```
⏱️  Wait 20 seconds for device startup
🔄 Attempt SSH reconnection (max 10 retries, 5-second intervals)
✓ Record SSH accessible timestamp
📊 Calculate: wakeup_time = ssh_accessible_time - power_key_send_time
📋 Log precise wakeup duration
```

#### **Step 12: Post-Wakeup Validation**
```
✓ Activate ScreenCapture service
✓ Fetch build details post-wakeup  
✓ Check for HOME screen
✓ Capture screenshot if on HOME screen
✓ Run error diagnostics if not on HOME screen
```

## Usage

### Method Registration in Execution Queue

```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",              # Optional: XUMO or SKY (auto-detects from device name if not specified)
        "sleep_duration_minutes": 60       # Optional: Default 60 minutes
    }
]

device.execute_queue_method(execution_queue, iterations=1, job_id="job-123")
```

### Direct Python Call

```python
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process

result = execute_maintenance_deepsleep_wakeup_process(
    device_ip="10.0.0.126",
    port=10022,
    username="root",
    password="skypass",
    iteration=1,
    device_name="SKY-Device-1",
    remote_type="SKY",                    # Optional
    sleep_duration_minutes=60,            # Optional
    job_id="job-123"                      # Optional
)

# Result structure:
# {
#     "iteration": 1,
#     "screenshots": ["path/to/screenshot.png"],
#     "logs": ["path/to/logs"],
#     "success": True,
#     "wakeup_time_seconds": 45.3,
#     "details": "Maintenance completed, DeepSleep verified, wakeup time: 45.3s"
# }
```

### Command Line Execution

```bash
python method_maintenance_deepsleep_wakeup.py 10.0.0.126 10022 root skypass "SKY-Device" SKY
```

## Return Values

### Success Response
```json
{
    "iteration": 1,
    "screenshots": [
        "/path/to/screenshots/device_Iteration-1_Before-Maintenance_20260414_120000.png",
        "/path/to/screenshots/device_Iteration-1_After-Wakeup_20260414_140500.png"
    ],
    "logs": [
        "/path/to/logs/device_MAINTENANCE_DEEPSLEEP_WAKEUP_20260414_120000_UTC.log"
    ],
    "success": true,
    "wakeup_time_seconds": 45.3,
    "details": "Maintenance completed, DeepSleep verified, wakeup time: 45.3s"
}
```

### Failure Response
```json
{
    "iteration": 1,
    "screenshots": [],
    "logs": [],
    "success": false,
    "wakeup_time_seconds": null,
    "details": "Device did not wake up from DeepSleep"
}
```

## Key Features

### ✓ Maintenance Cycle Handling
- Properly stops existing maintenance before starting new cycles
- 5-minute wait after stopping existing maintenance
- Respects RDK MaintenanceManager status states
- Handles both MAINTENANCE_ERROR and MAINTENANCE_COMPLETE states

### ✓ Deep Sleep Verification
- SSH accessibility test confirms device is unreachable in DeepSleep
- 15-minute natural DeepSleep entry wait period
- Prevents premature wake-up attempts

### ✓ Precise Timing Measurement
- Records exact timestamp when IR POWER command is sent
- Measures SSH reconnection time
- Calculates accurate wake-up duration in seconds
- Supports performance analysis and benchmarking

### ✓ Device Lock Management
- Validates device is reserved for this job every 10 seconds
- Automatically stops execution if lock is lost
- Thread-safe device allocation

### ✓ Job Cancellation Support
- Job cancellation checked every 10 seconds during wait periods
- Graceful cleanup on cancellation
- Prevention of orphaned processes

### ✓ Error Diagnostics
- Network and Realtek wireless error detection
- Detailed log collection on failures
- Screenshot comparison pre/post-wakeup

### ✓ Remote Type Detection
- Auto-detection based on device name (SKY/XUMO)
- User override option via parameters
- Configurable IR port selection

## Configuration

### Timing Configuration (`config_timing.py`)

```python
wait_for_deepsleep = 60          # Wait for initial DeepSleep entry (seconds)
wait_after_wakeup = 20           # Wait after IR wake command before SSH reconnect
wait_for_logs = 15               # Wait for logs to populate after wakeup
MAINTENANCE_WAIT_AFTER_REBOOT = 900  # 15 minutes for DeepSleep entry (from config_eta.py)
```

### Device Configuration (`devices.json`)

```json
{
    "device_ip": "10.0.0.126",
    "name": "SKY-Device-1",
    "port": 10022,
    "username": "root",
    "password": "skypass",
    "ir_config": {
        "itach_ip": "10.0.0.12",
        "itach_port": 4998,
        "ir_port": "1"
    }
}
```

## Monitoring & Logging

### Log Output Includes
```
[STEP 1-2] Maintenance activity status check
[STEP 3] STANDBY transition verification  
[STEP 4] Maintenance cycle initiation
[STEP 5] Periodic status polling with device lock validation
[STEP 6] Post-maintenance reboot
[STEP 8] DeepSleep wait with progress tracking
[STEP 9] DeepSleep confirmation (SSH inaccessibility)
[STEP 10] IR POWER command send with timestamp
[STEP 11] Wakeup time measurement
[STEP 12] Post-wakeup validation
```

### Real-Time Progress Updates
```
⏱️  DeepSleep duration: 60 minutes
🔍 Status: MAINTENANCE_IN_PROGRESS (Poll #5)
✓ Device still in STANDBY
⏳ Elapsed: 8m 30s | Remaining: 51m 30s
✓ Device is inaccessible via SSH (DeepSleep confirmed)
📝 IR POWER command send timestamp: 2026-04-14T16:45:00.123456
✓ Device accessible after 45.3 seconds from IR POWER key
```

## Troubleshooting

### Issue: Maintenance Never Completes
- **Cause**: Device firmware maintenance issue
- **Solution**: Check device logs for maintenance errors
- **Timeout**: Polling continues for 60 minutes maximum

### Issue: Device Not in DeepSleep
- **Cause**: Device waking up prematurely or other activity
- **Solution**: Verify no USB activity, check power supply
- **Log**: "Warning: Device is still accessible via SSH"

### Issue: IR Wake-Up Failed
- **Cause**: iTach device unreachable, IR port misconfigured
- **Solution**: Verify iTach connectivity and IR port assignment
- **Fallback**: Manual wake-up may be required

### Issue: SSH Reconnection Timeout After Wake-Up
- **Cause**: Device not fully booting or network issues
- **Solution**: Check device boot logs, verify network connectivity
- **Retry**: Automatic 10 retries with 5-second intervals

### Issue: Device Lock Lost During Wait
- **Cause**: Job cancelled or device lock expired
- **Status**: Execution stops gracefully
- **Action**: Job can be retried with same device

## Performance Metrics

### Typical Execution Timeline
```
Pre-validation:           2-3 minutes
Maintenance cycle:        30-60 minutes (varies by device)
Reboot + STANDBY verify:  5 minutes
DeepSleep wait:           15 minutes
IR Wake-up:               5-10 seconds
SSH Reconnect:            30-60 seconds
Post-wakeup validation:   3-5 minutes

Total estimate: 60-95 minutes (varies by maintenance completion time)
```

### Key Performance Indicators
- **Wakeup Time**: Time from IR POWER to SSH accessibility (target: 30-60 seconds)
- **Maintenance Duration**: Time taken for maintenance cycle completion
- **DeepSleep Confirmation**: Time to confirm device inaccessible via SSH

## Integration Examples

### With Other Methods
```python
execution_queue = [
    {"method": "reboot"},                              # Pre-warmup
    {"method": "maintenance_deepsleep_wakeup"},        # Main test
    {"method": "ir_test", "ir_keys": ["POWER", "OK"]} # Post-validation
]
```

### With Custom Remote Types
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "XUMO",
        "sleep_duration_minutes": 120
    }
]
```

## Error Handling

### Cancellation
- Job cancellation is checked every 10 seconds
- Gracefully stops current operation
- Releases device lock
- Returns failure status

### Lock Management
- Device lock validated every 10 seconds during waits
- Prevents execution if lock is lost
- Stops immediately if lock conflict detected
- Returns error with lock status

### Network Failures
- SSH reconnection with exponential backoff
- Automatic retry up to 10 times
- 5-second interval between retries
- Timeout protection (50 seconds total)

## Best Practices

### ✓ Device Selection
- Ensure device has IR blaster capability
- Verify iTach configuration before execution
- Device should support RDK MaintenanceManager

### ✓ Timing
- Schedule during maintenance windows
- Avoid concurrent device operations
- Account for 60-95 minute execution time

### ✓ Monitoring
- Monitor wakeup_time_seconds metric
- Track maintenance completion success rate
- Verify HOME screen validation post-wakeup

### ✓ Error Recovery
- Keep detailed logs for debugging
- Capture pre/post screenshots for analysis
- Test with shorter sleep_duration_minutes for initial validation

## API Reference

### Function Signature
```python
def execute_maintenance_deepsleep_wakeup_process(
    device_ip: str,
    port: int,
    username: str,
    password: str,
    iteration: int = 1,
    device_name: str = "Device",
    combined_method_name: str = None,
    remote_type: str = None,
    sleep_duration_minutes: int = 60,
    job_id: str = None
) -> dict
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_ip` | str | Required | Target device IP address |
| `port` | int | 10022 | SSH port |
| `username` | str | root | SSH username |
| `password` | str | Required | SSH password |
| `iteration` | int | 1 | Iteration number for logging |
| `device_name` | str | "Device" | Device name for IR config & screenshots |
| `combined_method_name` | str | None | Combined method name for folder naming |
| `remote_type` | str | None | Remote type (XUMO/SKY) or auto-detect |
| `sleep_duration_minutes` | int | 60 | DeepSleep duration before wakeup |
| `job_id` | str | None | Job ID for lock management |

### Return Values

| Key | Type | Description |
|-----|------|-------------|
| `iteration` | int | Iteration number |
| `screenshots` | list | Paths to captured screenshots |
| `logs` | list | Paths to execution logs |
| `success` | bool | Overall success status |
| `wakeup_time_seconds` | float | Time from IR POWER to SSH accessible (null if failed) |
| `details` | str | Summary message |

## Version History

### v1.0 (2026-04-14)
- Initial implementation
- 12-step maintenance > deepsleep > wakeup workflow
- Precise wakeup time measurement
- Device lock validation
- Job cancellation support

## Related Documentation

- [DeepSleep Method](METHOD_DEEPSLEEP.md)
- [Reboot Method](METHOD_REBOOT.md)
- [IR Test Method](METHOD_IR_TEST.md)
- [Device Configuration](DEVICES_JSON_GUIDE.md)
- [Maintenance Manager RDK Documentation](DEEPSLEEP_CONFIGURATION_GUIDE.md)
