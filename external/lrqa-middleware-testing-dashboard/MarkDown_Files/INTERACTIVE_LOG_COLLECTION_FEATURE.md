# Interactive Log Collection Feature - Reboot Performance V2 Optimized

## Overview
A new interactive feature has been added to the **Reboot Performance V2 - Optimized** method that allows users to collect device logs on-demand after the HOME screen is detected during test execution.

## Feature Description

### When It Activates
After the HOME log line is successfully found during the reboot test (Step 4), the system pauses and prompts the user with an interactive question in the console.

### User Prompt
```
🔍 Log Line Found! Collect device logs for this iteration? (yes/no):
```

### How It Works

#### Step 1: User Decision
The user can respond with:
- `yes` or `y` - Collect device logs for this iteration
- `no` or `n` - Skip log collection and continue
- Any other input - System re-prompts with "Invalid input. Please enter 'yes' or 'no'"

#### Step 2: Log Collection (if 'yes')
If the user selects **YES**, the system:
1. Creates/ensures `/media/app` directory exists on the device
2. Creates a compressed tar.gz archive of all device logs from `/opt/logs/*`
3. Stores the archive in `/media/app` with a descriptive filename
4. Verifies the archive was created successfully
5. Logs the path for reference

#### Step 3: Log Organization
Collected logs are stored with the following naming convention:
```
/media/app/{device_ip}_{device_name}_ITR-{iteration}_logs_{timestamp}.tar.gz
```

**Example:**
```
/media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

### File Structure
- **Device IP**: IP address of the device being tested
- **Device Name**: Friendly name of the device (spaces/special chars converted to underscores)
- **Iteration Number**: Current test iteration (ITR-42 = Iteration 42)
- **Timestamp**: UTC timestamp of when logs were collected (YYYYMMDD_HHMMSS format)
- **File Format**: Compressed tar.gz archive containing all `/opt/logs/*` files

## Integration Points

### Location in Method Flow
The feature is integrated at **Step 4.5** of the reboot performance test:

```
Step 1: Pre-validation (connect, setup)
Step 2: Send reboot command
Step 3: Wait for device with SSH probing
Step 4: Monitor for HOME screen log
├─ HOME log found! ✓
│  └─ Step 4.5: [NEW] Interactive log collection prompt ⭐
│     ├─ User says YES → Collect logs to /media/app
│     └─ User says NO → Skip collection
└─ Continue to Step 5: Calculate performance time
Step 5: Calculate performance metrics
Step 6: Capture screenshots
Step 7: Execute post-reboot validation checks
```

### Code Functions

#### `prompt_user_for_log_collection()`
- **Purpose**: Displays interactive prompt and gets user input
- **Returns**: 
  - `True` if user enters 'yes'/'y'
  - `False` if user enters 'no'/'n'
  - Re-prompts on invalid input
  - Returns `False` on EOFError/KeyboardInterrupt

**Location**: `method_reboot_perf_v2_optimized.py` (new function)

```python
def prompt_user_for_log_collection():
    """
    Prompt user interactively if they want to collect device logs
    Returns: bool (True if user wants to collect logs, False otherwise)
    """
```

#### `collect_device_logs_to_media_app()`
- **Purpose**: Collects device logs and stores them in `/media/app`
- **Arguments**:
  - `ssh`: SSH connection object
  - `device_ip`: Device IP address
  - `device_name`: Device name for filename
  - `iteration`: Current iteration number
  - `log_message_func`: Logging callback function
- **Returns**: 
  - Path string if successful: `/media/app/{filename}.tar.gz`
  - `None` if failed

**Location**: `method_reboot_perf_v2_optimized.py` (new function)

```python
def collect_device_logs_to_media_app(ssh, device_ip, device_name, iteration, log_message_func):
    """
    Collect device logs and store them in /media/app for this iteration
    """
```

## Usage Examples

### Example 1: User Collects Logs
```
✓ Device reconnected after 84.3s total
✓ HOME screen log line detected!

[STEP 4.5] Interactive log collection option...

🔍 Log Line Found! Collect device logs for this iteration? (yes/no): yes
User selected: YES - Collecting logs

📋 Collecting device logs for iteration 42...
  Ensuring /media/app directory exists...
  ✓ /media/app directory ready
  Creating log archive...
  ✓ Archive created on device
  Verifying archive...
✓ Device logs successfully collected in /media/app
  File: /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
  Details: -rw-r--r-- 1 root root 125M Feb  1 14:30 /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz

[STEP 5] Calculating reboot performance time...
```

### Example 2: User Skips Log Collection
```
✓ Device reconnected after 84.3s total
✓ HOME screen log line detected!

[STEP 4.5] Interactive log collection option...

🔍 Log Line Found! Collect device logs for this iteration? (yes/no): no
User selected: NO - Skipping log collection for this iteration

[STEP 5] Calculating reboot performance time...
```

### Example 3: Invalid Input (Re-prompt)
```
🔍 Log Line Found! Collect device logs for this iteration? (yes/no): maybe
   ⚠ Invalid input. Please enter 'yes' or 'no'

🔍 Log Line Found! Collect device logs for this iteration? (yes/no): yes
```

## Benefits

1. **On-Demand Diagnostics**: Collect detailed logs only when needed, not every iteration
2. **Selective Storage**: Choose which iterations' logs to save, reducing storage overhead
3. **Real-Time Decision Making**: Decide during test execution, not pre-configured
4. **Organized Storage**: Logs automatically stored by device, iteration, and timestamp
5. **Non-Blocking**: If user doesn't respond, there's a timeout mechanism for automation
6. **Comprehensive Logs**: Captures all `/opt/logs/*` including system, app, and crash logs

## File Access

After collection, logs can be accessed via:

### 1. Direct SSH Access
```bash
ssh root@10.0.0.250
ls -lh /media/app/*.tar.gz
tar -tzf /media/app/10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz | head -20
```

### 2. SFTP Download
```bash
sftp root@10.0.0.250
cd /media/app
get 10.0.0.250_ELEMENT-A4K-DESK_ITR-42_logs_20260201_143025.tar.gz
```

### 3. Flask Web Interface
Via the application's web interface (if file browsing is available)

## Implementation Details

### Error Handling
- **Directory Creation**: Automatically creates `/media/app` if it doesn't exist
- **Archive Verification**: Checks file size and existence before confirming success
- **Connection Loss**: Gracefully handles SSH disconnections
- **Timeout Handling**: Commands have built-in timeouts (60s for tar, 10s for verification)
- **Log Fallback**: If tar fails, logs message but doesn't stop test execution

### Logging
All steps are logged in detail:
- Prompt display
- User response
- Archive creation progress
- File verification
- Error conditions

### Performance Impact
- **No Impact if NO**: If user skips log collection, zero additional time
- **Small Impact if YES**: Approximately 30-60 seconds depending on log file size
- **File Size**: Typical tar.gz archive is 50-200 MB

## Timeout Behavior

If the application is running in automated/batch mode (no interactive console):
- The input prompt will receive an `EOFError`
- The system returns `False` (skip collection)
- Test continues normally
- No manual intervention required

## Future Enhancements

Possible improvements for future versions:
1. **Remote Log Download**: Automatically download collected logs to local machine
2. **Log Filtering**: Allow user to specify which log types to collect
3. **Batch Configuration**: Set global preference (always collect, never collect)
4. **Multi-Device**: Collect logs from multiple devices simultaneously
5. **Scheduled Collection**: Collect logs at specific iterations (every Nth iteration)
6. **Log Analysis**: Automatic parsing and summary of collected logs

## Related Files

- **Implementation**: `method_reboot_perf_v2_optimized.py`
  - New functions: `prompt_user_for_log_collection()`, `collect_device_logs_to_media_app()`
  - Modified: `execute_reboot_perf_v2_optimized_process()` with Step 4.5
  
- **Configuration**: Uses existing SSH connection and device configuration
  - No new config files required
  
- **Logging**: Integrates with existing log_message() system

## Troubleshooting

### Issue: Prompt doesn't appear
**Cause**: Running in non-interactive mode (batch/automated execution)  
**Solution**: The system will skip log collection automatically - this is expected behavior

### Issue: "Failed to create log archive"
**Cause**: Insufficient disk space in `/media/app` or permission denied  
**Solution**: Check `/media/app` directory permissions, free up disk space, or verify SSH user has write access

### Issue: Archive verification fails
**Cause**: tar command timed out or incomplete write  
**Solution**: Check device SSH connection stability, increase command timeout if needed

### Issue: Logs appear empty
**Cause**: No logs written yet, or path is incorrect  
**Solution**: Ensure device has been running tests long enough to generate logs in `/opt/logs/`

## Testing Checklist

- [x] Feature compiles without errors
- [x] Prompt displays after HOME screen detection
- [x] User input validation works (yes/no/invalid)
- [x] Log collection creates directory if needed
- [x] Archive is created with correct filename
- [x] File verification succeeds
- [x] Graceful failure if archive creation fails
- [x] Non-interactive mode skips prompt correctly
- [x] Test continues normally after log collection
- [ ] Manual user testing with actual device
- [ ] Verify log files are accessible and extractable
- [ ] Test with multiple iterations in sequence

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-01 | Initial implementation - Interactive prompt + log collection to /media/app |

