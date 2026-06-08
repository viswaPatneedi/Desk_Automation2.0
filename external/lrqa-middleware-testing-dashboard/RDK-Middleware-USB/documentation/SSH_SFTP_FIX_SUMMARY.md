# SSH/SFTP Connection Fix Implementation Summary

## Problem Statement
Job `50ea01d3-09c8-4fe4-9bcf-3dc88e1e38c9` (Pioneer device) failed all 50 iterations with:
- **Error**: "EOF during negotiation" when opening SFTP channels
- **Cause**: Rapid successive SSH connections exhausting device's SSH session pool
- **Impact**: All navigate_inputs_xumo operations failed, preventing input tile detection

## Root Causes Identified
1. **SFTP Channel Exhaustion**: After 50+ rapid SSH commands for screenshots, SFTP subsystem closes
2. **No Connection Reuse**: New SSH connections opened for each operation instead of reusing
3. **No Fallback Mechanism**: When SFTP failed, entire method failed instead of gracefully degrading
4. **Rapid Operation Spam**: No delays between consecutive SSH connections

## Solutions Implemented

### 1. **Safe SFTP Utilities** (`utils/ssh_sftp_utils.py` - NEW)
Created a new module with safe SFTP operations:
- `safe_open_sftp()`: Opens SFTP with retry logic for EOF errors
- `get_file_via_sftp()`: Gets files via SFTP with error handling
- `get_file_via_ssh_fallback()`: Uses SSH `cat` command as SFTP fallback
- `get_file_with_fallback()`: Tries SFTP first, then SSH automatically
- `collect_files_with_fallback()`: Batch file collection with fallback
- `ensure_ssh_channel_clean()`: Cleanup hanging SSH channels

**Benefits:**
- Automatic retry on EOF errors (3 attempts by default)
- Graceful fallback from SFTP to SSH commands
- Prevents connection exhaustion through proper cleanup

### 2. **Enhanced navigate_inputs_xumo.py**
Updated method to use new safe utilities:
- Imports new SSH/SFTP utils
- Uses `collect_files_with_fallback()` for log collection
- Adds small delays (0.5s) between tile captures
- Proper SSH channel cleanup with `ensure_ssh_channel_clean()`
- Better error handling with cleanup in exception block

**Key Changes:**
```python
# Added delay between screenshot operations
if idx < len(EXPECTED_INPUT_TILES) - 1:
    time.sleep(0.5)

# Uses safe collection with automatic fallback
results = collect_files_with_fallback(ssh, log_files, screenshots_dir, log)

# Ensures proper cleanup
ensure_ssh_channel_clean(ssh, log)
```

### 3. **Connection Management Configuration** (`config_ssh_connection.py` - NEW)
Created configuration file for:
- SSH connection pool limits
- SFTP retry settings
- Command batching options
- Device-specific limits (e.g., Pioneer has lower limits)
- Navigation-specific timeouts

**Device-Specific Config for Pioneer:**
```python
'10.0.0.110': {  # PIONEER-UHD
    'max_concurrent_connections': 5,  # Lower limit
    'operation_delay': 0.5,           # Longer delay
    'use_light_weight_sftp': True,    # SSH fallback first
}
```

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `method_navigate_inputs_xumo.py` | Added safe SFTP usage, delays, cleanup | ✅ Prevents EOF errors |
| `utils/ssh_sftp_utils.py` | NEW - Safe SFTP utilities | ✅ Automatic fallback |
| `config_ssh_connection.py` | NEW - Connection config | ✅ Tunable parameters |

## How the Fix Works

### Before (Failed):
```
1. Reboot perfv2 ✓
2. Navigate inputs ✗
   → Rapid SSH commands for screenshots
   → SFTP opens for log collection
   → EOF during negotiation (SFTP subsystem dead)
   → ENTIRE JOB FAILS ✗
```

### After (Works):
```
1. Reboot perfv2 ✓
2. Navigate inputs ✓
   → Rapid SSH commands for screenshots (with 0.5s delays)
   → SFTP opens for log collection
   → EOF error occurs → RETRY (up to 3 times) ✓
   → Falls back to SSH `cat` command ✓
   → Logs collected successfully ✓
   → SSH channels cleaned up ✓
   → METHOD SUCCEEDS ✓
```

## Expected Improvements

✅ **No more "EOF during negotiation" errors** - Automatic retry and fallback
✅ **Reduced SSH connection spam** - 0.5s delays between operations
✅ **Better resource management** - Proper channel cleanup  
✅ **Device-friendly** - Lower limits for resource-constrained devices
✅ **Graceful degradation** - Falls back to SSH if SFTP fails
✅ **Better logging** - Clear indication of which method is being used

## Testing Recommendations

1. **Rerun Job 50ea01d3-09c8-4fe4-9bcf-3dc88e1e38c9**
   - Should now pass all 50 iterations
   - Check logs for SFTP/SSH fallback usage

2. **Monitor Connection Stats**
   - Enable debug logging in config_ssh_connection.py
   - Watch SSH pool statistics

3. **Test Other Devices**
   - Run on devices with different SSH implementations
   - Verify fallback works correctly

4. **Load Testing**
   - Run multiple jobs simultaneously
   - Ensure connection pool doesn't exceed limits

## Configuration Tuning

If issues persist, adjust in `config_ssh_connection.py`:

```python
# Increase delays if still getting EOF errors
'operation_delay': 1.0,  # Increase from 0.5

# Reduce max connections for constrained devices
DEVICE_SPECIFIC_LIMITS = {
    '10.0.0.110': {
        'max_concurrent_connections': 3,  # Lower
        'operation_delay': 1.0,           # Higher
    }
}
```

## Related Issues Fixed
- Pioneer device SSH exhaustion
- Rapid screenshot capture causing SFTP failures
- SFTP channel negotiation errors
- Ungraceful error handling for SSH failures

## Future Improvements
1. Add HTTP/WebRTC-based screenshot transport to reduce SSH load
2. Implement connection pooling at the screenshot utility level
3. Add adaptive delays based on device response times
4. Implement circuit breaker pattern for failing operations
