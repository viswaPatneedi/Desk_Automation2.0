# Device Lock Timezone Bug - May 20, 2026

## Incident Summary
Execution `f505e891-4be8-4909-bc95-5e81b07aac81` on device 10.0.0.141 failed with:
```
❌ CRITICAL: Device lock lost or expired!
⚠️  Device 10.0.0.141 is no longer reserved for job f505e891-4be8-4909-bc95-5e81b07aac81
```

**Timeline:**
- Iteration 1: ✅ PASSED (111 seconds)
- Iteration 2: ❌ FAILED - Lock reported as lost/expired immediately at start
- Expected lock duration: 6090 seconds (~101 minutes) for 4 remaining iterations
- Actual lock availability: LOST after 111 seconds (not expired - lost!)

## Root Cause Analysis

### Issue 1: Timezone Mismatch in Lock Expiration Check

**File**: `models/device_lock.py`

**Location**: `lock_device()` method (lines 83-100) and `get_device_lock()` method (lines 144-167)

**The Bug**:

```python
# Line 87-88 in lock_device():
now = datetime.utcnow()  # ❌ NAIVE datetime (no timezone)
estimated_completion = (now + timedelta(seconds=estimated_duration_seconds)).isoformat()
# Result: "2026-05-20T10:57:02.238925" (NO timezone info)

# BUT later, the estimated_completion might be loaded/modified with timezone info

# Line 156-167 in get_device_lock():
completion_string = lock.estimated_completion
if 'Z' in completion_string:
    completion_string = completion_string.replace('Z', '+00:00')  # ❌ Now it's timezone-aware!
else:
    estimated_time = datetime.fromisoformat(completion_string)  # ✅ Naive

# Line 164:
if datetime.utcnow() > estimated_time:  # ❌ COMPARISON BUG!
    # Comparing naive datetime with potentially timezone-aware datetime
    # This raises TypeError in Python!
```

**The Problem Chain**:
1. Lock is created with `datetime.utcnow()` (naive)
2. `estimated_completion` is saved as naive string: "2026-05-20T10:57:02.238925"
3. During `get_device_lock()` retrieval, if timezone info is added (through any data modification), it becomes "2026-05-20T10:57:02.238925+00:00"
4. Comparison `datetime.utcnow() > estimated_time` mixes naive and aware datetimes
5. Python raises `TypeError: can't compare offset-naive and offset-aware datetimes`
6. The exception is caught in the generic `except` block
7. The method SILENTLY returns `None` (lock appears lost)
8. Execution fails with "Device lock lost or expired"

### Supporting Evidence

From the execution log line 125:
```
❌ CRITICAL: Device lock lost or expired!
⚠️  Device 10.0.0.141 is no longer reserved for job f505e891-4be8-4909-bc95-5e81b07aac81
```

The lock wasn't actually expired (111 seconds << 6090 seconds expected)
- It was LOST due to the timezone comparison exception

From `device_locks.json` snapshot:
```json
{
  "10.0.0.252": { ... },
  // 10.0.0.141 is completely absent!
}
```

This confirms the lock lookup returned None and the device was unlocked/removed

## Solution

### Fix 1: Use Consistent Timezone-Aware Datetimes

**File**: `models/device_lock.py`

**Change**: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`

```python
# Line 87 in lock_device():
# BEFORE:
now = datetime.utcnow()  # ❌ Naive

# AFTER:
from datetime import timezone
now = datetime.now(timezone.utc)  # ✅ Timezone-aware (UTC)
```

**Benefits**:
- All timestamps are consistent (timezone-aware)
- Comparisons always safe (tz-aware vs tz-aware)
- No TypeError exceptions
- Clear that all times are UTC

### Fix 2: Safe Timezone Conversion in get_device_lock()

**File**: `models/device_lock.py`

**Chapter**: Update `get_device_lock()` method (lines 144-167):

```python
@staticmethod
def get_device_lock(device_ip):
    """Get lock information for a device."""
    locks = DeviceLock.load_all()
    if device_ip in locks:
        lock = locks[device_ip]
        # Check if expired (SAFE timezone handling)
        try:
            completion_string = lock.estimated_completion
            
            # Normalize timezone string
            if 'Z' in completion_string:
                completion_string = completion_string.replace('Z', '+00:00')
            
            # Parse and ensure awareness
            estimated_time = datetime.fromisoformat(completion_string)
            
            # If naive, make it aware (UTC)
            if estimated_time.tzinfo is None:
                estimated_time = estimated_time.replace(tzinfo=timezone.utc)
            
            # Get current time as aware (UTC)
            current_time = datetime.now(timezone.utc)
            
            # Safe comparison (both are timezone-aware)
            if current_time > estimated_time:
                DeviceLock.unlock_device(device_ip)
                return None
                
        except Exception as e:
            logger.warning(f"Error checking lock expiration for {device_ip}: {str(e)}")
            # On any error, fail SAFE - remove bad lock
            DeviceLock.unlock_device(device_ip)
            return None
            
        return lock
    return None
```

### Fix 3: Update All DateTime Operations

**Affected methods**:
- `lock_device()` - line 87
- `get_device_lock()` - lines 156-167
- `get_user_locks()` - similar logic
- Any other method using `datetime.utcnow()`

**Pattern to replace everywhere**:
```python
# BEFORE:
datetime.utcnow()

# AFTER:
from datetime import timezone
datetime.now(timezone.utc)
```

## Impact

### Before Fix
- Timezone mismatch causes TypeError in comparison
- Exception caught silently, returns None
- Lock appears "lost" even though it's valid
- Multi-iteration executions fail at iteration 2+
- Users see cryptic "Device lock lost or expired" error

### After Fix
- All timestamps consistently timezone-aware
- Expiration checks work reliably
- Locks properly maintained across iterations
- Executions complete successfully

## Test Cases

### Test 1: Verify Lock Persistence
```python
# Create a lock
DeviceLock.lock_device('10.0.0.141', 'Device', 'user1', 'job1', 6090)

# Try to retrieve immediately
lock = DeviceLock.get_device_lock('10.0.0.141')

# Should return lock (not None)
assert lock is not None
assert lock.job_id == 'job1'
```

### Test 2: Verify Lock Found Across Iterations
```python
# Simulate a 5-iteration job
for i in range(1, 6):
    # At iteration start, verify lock still exists
    lock = DeviceLock.get_device_lock('10.0.0.141')
    assert lock is not None, f"Lock lost at iteration {i}"
    
    # Refresh lock for remaining iterations
    remaining = 5 - i
    duration = 870 * remaining * 1.75  # Same calc as deepsleep
    DeviceLock.unlock_device('10.0.0.141')
    lock = DeviceLock.lock_device('10.0.0.141', 'Device', 'user1', 'job1', int(duration))
    
    print(f"Iteration {i}: Lock valid ✓")
```

### Test 3: Verify Lock Expiration Works
```python
# Create lock with 1 second duration
lock_start = datetime.now(timezone.utc)
DeviceLock.lock_device('10.0.0.141', 'Device', 'user1', 'job1', 1)

# Should exist immediately
lock = DeviceLock.get_device_lock('10.0.0.141')
assert lock is not None

# Wait 2 seconds
time.sleep(2)

# Should be expired now
lock = DeviceLock.get_device_lock('10.0.0.141')
assert lock is None  # Auto-unlocked due to expiry
```

## Files to Modify

1. **`models/device_lock.py`**
   - Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` everywhere
   - Update get_device_lock() expiration check logic
   - Import `timezone` from datetime
   - Update get_user_locks() with same pattern

2. **`utils/device_lock_manager.py`** (if it uses datetime.utcnow)
   - Check all datetime operations
   - Ensure consistency

3. **Other files** using `datetime.utcnow()` for lock operations
   - Search codebase for `utcnow()`
   - Replace with `now(timezone.utc)` in lock-related code

## Prevention Strategies

1. **Always use timezone-aware datetimes** for locks and time-based operations
2. **Never mix naive and aware datetimes** in comparisons
3. **Test lock persistence** across iteration boundaries
4. **Add logging** to show when locks are retrieved/refreshed
5. **Monitor lock validation errors** - they signal timezone issues

## Next Steps

1. Apply fixes to `device_lock.py`
2. Test deepsleep method with 5 iterations (should pass all iterations)
3. Test long-running sequences (50 iterations) to ensure locks don't expire
4. Add unit tests for lock timezone handling
5. Deploy and monitor for "Device lock lost" errors

---

**Status**: Root cause identified, fix ready to implement
**Severity**: HIGH - Affects all multi-iteration executions
**Recommendation**: Apply fix immediately before running more tests
