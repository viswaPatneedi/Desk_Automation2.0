# Device Lock Issue - Root Cause Analysis & Fix (May 12, 2026)

## Summary
Two maintenance executions failed due to device lock expiration issues:
- **Execution 85e750f3**: Lock refresh at iteration 2 showed "-1h 59m" time remaining
- **Execution 0713712a**: Device lock lost/expired between iteration 1 and iteration 2

**Root Cause**: Timezone mismatch in datetime comparison when calculating lock expiration time

## Issue Details

### Problem 1: Timezone Mismatch in `get_time_until_expiration()`

**Location**: `models/device_lock.py` lines 223-243

**What Was Happening**:
```python
# BROKEN CODE:
completion_time = datetime.fromisoformat(lock.estimated_completion.replace('Z', '+00:00'))
now = datetime.utcnow().replace(tzinfo=timezone.utc)
remaining = int((completion_time - now).total_seconds())
```

**The Bug**:
- Device locks are stored with NAIVE datetime: `"2026-05-12T03:05:48.439341"` (NO timezone)
- The `.replace('Z', '+00:00')` does NOTHING because there's no 'Z' in the string
- Comparing naive datetime (`completion_time`) with aware datetime (`now` + timezone.utc) raises exception
- Exception handler returns `-1`
- Calculation: `hours = -1 // 3600 = -1`, `minutes = (-1 % 3600) // 60 = 59`
- Result: Logs show "Time remaining: -1h 59m" ❌

**Visible Impact**:
```
[2026-05-12 01:10:44 UTC] 🔒 [LOCK-REFRESH] Lock refreshed for remaining 14 iterations
[2026-05-12 01:10:45 UTC]    Time remaining: -1h 59m  ← WRONG!
```

### Problem 2: Cascading Lock Verification Failures

Similar timezone issues in these methods:
- `is_device_locked()`: Can't verify if lock is expired
- `get_device_lock()`: Expiration check fails
- `cleanup_expired_locks()`: Can't identify expired locks
- `extend_lock()`: Can't extend expired locks safely
- `get_user_locks()`: Can't validate user's locks

## Solution Implemented

### Fix 1: Timezone-Aware DateTime Handling

Changed all datetime parsing to handle both formats:

```python
@staticmethod
def get_time_until_expiration(device_ip):
    # ... existing code ...
    try:
        completion_string = lock.estimated_completion
        
        # Handle both timezone-aware and naive datetime formats
        if 'Z' in completion_string:
            # Format: "2026-05-12T03:05:48.439341Z"
            completion_string = completion_string.replace('Z', '+00:00')
            completion_time = datetime.fromisoformat(completion_string)
        else:
            # Format: "2026-05-12T03:05:48.439341" (naive)
            completion_time = datetime.fromisoformat(completion_string)
            completion_time = completion_time.replace(tzinfo=timezone.utc)
        
        # Get current time as aware UTC
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        
        # Now both are timezone-aware - comparison works!
        remaining = int((completion_time - now).total_seconds())
        return max(0, remaining)
    except Exception as e:
        logger.warning(f"Error calculating time until expiration: {str(e)}")
        return -1
```

**Key Changes**:
1. Detects whether timezone info is present (looks for 'Z')
2. Makes naive datetimes timezone-aware before comparison
3. Ensures both values being compared have consistent timezone info
4. Catches exceptions with proper logging

### Fix 2: Enhanced Lock Refresh Logging

Added detailed debugging to `refresh_lock()`:

```python
print(f"✓ Lock refreshed for {device_ip}: {new_duration} seconds ({new_duration//3600}h...)")
print(f"❌ Lock verification failed: No lock found for {device_ip}")
# etc.
```

**Benefits**:
- Clear visibility into why lock refresh fails
- Helps diagnose future issues quickly
- Logs actual duration calculated

### Fix 3: Refined Duration Calculation

Updated `calculate_job_duration()` for `maintenance_CURL_deepsleep_wakeup`:

```python
elif method == 'maintenance_CURL_deepsleep_wakeup':
    # ACTUAL OBSERVED: 43-45 minutes per iteration
    # Using conservative estimate of 3000 seconds (50 min)
    # With 1.5x buffer: 3000 * iterations * 1.5
    total_seconds += 3000  # Changed from 3120
```

**Reasoning**:
- Actual iterations take ~43.6 minutes
- Previous estimate of 3120 seconds (52 min) was reasonable but could be tighter
- 3000 seconds (50 min) is better baseline
- With 1.5x buffer: provides 25-50 minute buffer per iteration

## Files Modified

### 1. `models/device_lock.py`
- `is_device_locked()`: Timezone-safe expiration check
- `get_device_lock()`: Timezone-safe parsing
- `get_user_locks()`: Timezone-safe iteration
- `cleanup_expired_locks()`: Timezone-safe cleanup
- `extend_lock()`: Timezone-safe extension
- `get_time_until_expiration()`: **Primary Fix** ✅

### 2. `utils/device_lock_manager.py`
- `refresh_lock()`: Enhanced logging for debugging
- `calculate_job_duration()`: Updated CURL deepsleep estimate

## Testing Recommendations

### 1. Verify Time Calculation
- Run a maintenance execution for 2-3 iterations
- Check logs for "Time remaining:" at each lock refresh
- Should show positive hours/minutes (e.g., "Time remaining: 18h 20m")
- Should NOT show "-1h 59m"

### 2. Verify Lock Persistence
- Monitor device_locks.json for lock state throughout execution
- Lock should remain valid through all iterations
- No "Device lock lost or expired" messages

### 3. Full Execution Test
- Run 15-iteration maintenance sequence
- Should complete without lock-related failures
- Monitor both execution logs and Flask app logs for lock refresh messages

## Example Correct Behavior (After Fix)

```
[2026-05-12 01:10:44 UTC] ITERATION 2/15
[2026-05-12 01:10:44 UTC] 🔒 [LOCK-REFRESH] Lock refreshed for remaining 14 iterations
[2026-05-12 01:10:45 UTC]    Time remaining: 18h 20m  ← CORRECT!
[2026-05-12 01:10:45 UTC] ✓ Lock refreshed for 10.0.0.166: 65520 seconds (18h 12m) for 14 remaining iterations

[2026-05-12 02:33:23 UTC] ITERATION 3/15
[2026-05-12 02:33:23 UTC] 🔒 [LOCK-REFRESH] Lock refreshed for remaining 13 iterations
[2026-05-12 02:33:24 UTC]    Time remaining: 17h 15m  ← CORRECT!
```

## Commits
- **Commit**: 1663706
- **Message**: "fix: Device lock timezone handling and refresh logging"
- **Changes**: 125 insertions, 45 deletions

## Deployment Status
✅ App restarted with fixes (PID: 1037040, Port: 11078)
✅ Ready for testing

## Prevention for Future Issues

1. **Always use timezone-aware datetimes** for comparing times across different sources
2. **Test datetime parsing** with multiple formats in unit tests
3. **Add logging** before all datetime comparisons to catch issues early
4. **Document datetime format** used in JSON storage (naive vs aware)
5. **Add validation** in lock_device() to ensure consistent format
