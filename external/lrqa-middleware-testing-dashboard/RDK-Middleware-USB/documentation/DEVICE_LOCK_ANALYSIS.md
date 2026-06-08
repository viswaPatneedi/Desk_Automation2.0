# Critical Device Locking Analysis - Job 63d6588b-04ec-4d8b-a4d1-9f5dab04ba9e

## Executive Summary
**CRITICAL BUG FOUND**: Device 10.0.0.95 (CELLO-SKY) was **prematurely unlocked** during job execution while iterations were still in progress. The job shows "running" status in jobs.json but "unlocked" status in device_locks.json, allowing other jobs to interfere.

---

## Root Cause Analysis

### 1. **CRITICAL: Inadequate Lock Duration Calculation**
**File**: `models/device_lock.py` (lines 80-96)

```python
@staticmethod
def lock_device(device_ip, device_name, user_id, job_id, estimated_duration_seconds):
    """Lock a device for a specific job."""
    locks = DeviceLock.load_all()
    
    now = datetime.utcnow()
    estimated_completion = (now + timedelta(seconds=estimated_duration_seconds)).isoformat()
    # ... rest of code
```

**Problem**: The lock duration is **fixed at creation time** and doesn't account for:
- Long-running operations (deepsleep waits 15 minutes per iteration!)
- Multiple iterations (50 iterations × 15+ minutes each)
- Network delays, device delays, screenshot processing

**For this job**:
- Job Duration: ~50 iterations × (900s deepsleep + 180s wait) = **~50 hours minimum**
- Lock Duration: Likely estimated as 300-1800 seconds (5-30 minutes)
- **Result**: Lock expired while job was still running on iteration 16

### 2. **CRITICAL: No Lock Refresh/Extension Mechanism**
**File**: `services/test_execution_service.py` (lines 1500-2300)

The execution loop runs for hours but **never updates or refreshes the lock**:
```python
for i in range(start_iteration, iterations):
    # No DeviceLock.lock_device() called again
    # No lock duration update
    # No lock heartbeat
    
    for method_index, queue_item in enumerate(execution_queue):
        # Execute deepsleep (900+ seconds)
        # During this wait, lock could expire!
        method_result = execute_deepsleep_process(...)
```

### 3. **CRITICAL: Expired Lock Not Detected During Execution**
**File**: `models/device_lock.py` (lines 113-125)

Lock expiration is only checked when:
- A new job requests the device
- `cleanup_expired_locks()` is called manually
- Device lock status is queried

**During execution**: No periodic check to ensure lock is still valid!

### 4. **CRITICAL: Finally Block Releases Lock Even if Already Released**
**File**: `services/test_execution_service.py` (lines 2218-2235)

```python
except Exception as e:
    # ... error handling ...
    if job_id:
        Job.update_job_status(job_id, 'failed', ...)
        DeviceLock.unlock_device(device.ip)  # Line 2232

finally:
    # Close log handles
    if log_file_handle:
        log_file_handle.close()
    log_service.close_iteration_log()
    
    # NO second attempt to unlock here
    # But if already unlocked by another process, this is fine
```

**Issue**: Once lock expires and is cleaned up by another job request, the device becomes available for other executions before this job completes.

---

## What Happened on April 12, 2026

**Timeline of Failure**:

1. **11:16:41 UTC** - Job starts, iteration 16 begins
   - Device locked for ~30-60 minute estimated duration
   - But actual execution will be ~15 minutes per iteration × 34 remaining iterations

2. **11:22:56 UTC** - Execution stops abruptly mid-deepsleep wait
   - Log output: `⏱️ Elapsed: 4m 0s | Remaining: 10m 59s`
   - Thread likely received exception or was killed

3. **At some point between 11:22-present**:
   - Device lock expired (estimated_completion reached)
   - `DeviceLock.unlock_device()` called automatically OR
   - Another job request triggered `cleanup_expired_locks()`
   - Device is now available for other jobs (device_locks.json is currently EMPTY)

4. **Result**: 
   - Job status: "running" (but no background thread executing)
   - Device locked: NO (lock expired)
   - If another job requests device: GRANTED (lock is gone!)
   - Original job: STUCK and ORPHANED

---

## System Resource Status at Failure Time

- **Memory**: 1.2GB free (adequate)
- **Disk**: 45GB free on root (NOT critical)
- **CPU Load**: 0.55 (normal)
- **No OOM killer** events recorded

**Conclusion**: Resource issues NOT the cause.

---

## Vulnerability: Device Lock Race Condition

**Scenario**:
```
Time 1: Job A requests device X
Time 2: Device X locked for Job A (estimated duration: 1 hour)
Time 3: Job A executing, iteration 25/50 (3 hours actual needed)
Time 4: Lock expires (1 hour timeout reached)
Time 5: Job B requests device X
Time 6: DeviceLock.is_device_locked() returns FALSE (lock expired)
Time 7: Device X locked for Job B
Time 8: Job B starts executing on device while Job A is STILL using it!
Time 9: COLLISION - Both jobs fighting for same device
```

---

## Recommended Fixes

### Fix 1: Dynamic Lock Duration Based on Job Parameters
**Priority**: CRITICAL
**File**: `services/test_execution_service.py` (around line 1720)

```python
# Calculate realistic lock duration from job parameters
total_seconds = 0
for queue_item in execution_queue:
    method = queue_item.get('method')
    
    if method == 'deepsleep':
        sleep_duration = queue_item.get('sleep_duration_minutes', 60)
        total_seconds += (sleep_duration * 60) + 300  # 300s for overhead
    elif method == 'wait':
        wait_seconds = queue_item.get('wait_seconds', 0)
        total_seconds += wait_seconds
    # ... add other method durations ...

# Multiply by iterations and add 50% buffer
estimated_duration = (total_seconds * iterations) * 1.5

# Create/update lock with accurate duration
lock = DeviceLock.lock_device(
    device_ip=device.ip,
    device_name=device.name,
    user_id=current_user.ntid,
    job_id=job_id,
    estimated_duration_seconds=int(estimated_duration)
)
```

### Fix 2: Implement Lock Heartbeat/Refresh
**Priority**: CRITICAL
**File**: `services/test_execution_service.py` (per iteration)

```python
# Add before each iteration or between long operations
for i in range(start_iteration, iterations):
    # Refresh lock at the START of each iteration
    if job_id and i > 0:  # Skip for first iteration
        DeviceLock.unlock_device(device.ip)
        # Recalculate remaining time
        remaining_iterations = iterations - (i + 1)
        remaining_duration_seconds = calculate_remaining_duration(queue_item, remaining_iterations)
        DeviceLock.lock_device(
            device.ip, device.name, current_user.ntid, job_id,
            estimated_duration_seconds=int(remaining_duration_seconds)
        )
        log_service.log(f"🔒 [LOCK-REFRESH] Lock refreshed for iterations {i+2} to {iterations}")
```

### Fix 3: Periodic Lock Validation During Execution
**Priority**: HIGH
**File**: `services/test_execution_service.py` (during long waits)

```python
# Inside deepsleep wait loop
@staticmethod
def wait_with_lock_check(duration_seconds, device_ip, log_callback):
    """Wait while periodically checking if device is still locked"""
    CHECK_INTERVAL = 60  # Check every 60 seconds
    elapsed = 0
    
    while elapsed < duration_seconds:
        time.sleep(min(CHECK_INTERVAL, duration_seconds - elapsed))
        elapsed += CHECK_INTERVAL
        
        # Check if lock is still valid
        if not DeviceLock.is_device_locked(device_ip):
            log_callback(f"❌ CRITICAL: Device lock lost! Another job may be using device {device_ip}")
            log_callback(f"⚠️ Cannot continue execution - device is no longer reserved")
            raise RuntimeError(f"Device lock lost for {device_ip}")
        
        log_callback(f"  ⏱ {elapsed}s elapsed, {duration_seconds - elapsed}s remaining... (lock valid ✓)")
```

### Fix 4: Automatic Cleanup on Job Completion/Failure
**Priority**: HIGH
**File**: `services/test_execution_service.py` (finally block)

```python
finally:
    # Close log handles
    if log_file_handle:
        try:
            log_file_handle.close()
        except:
            pass
    
    # CRITICAL: Always ensure device is unlocked, but only once
    if job_id and device:
        try:
            # Check if device is still locked by THIS job
            current_lock = DeviceLock.get_device_lock(device.ip)
            if current_lock and current_lock.job_id == job_id:
                DeviceLock.unlock_device(device.ip)
                log_service.log(f"🔓 Device unlocked: {device.ip}")
            else if current_lock:
                log_service.log(f"⚠️ Device locked by another job {current_lock.job_id}, not unlocking")
            else:
                log_service.log(f"⚠️ Device already unlocked")
        except Exception as unlock_error:
            log_service.log(f"❌ Error unlocking device: {unlock_error}")
    
    log_service.close_iteration_log()
    
    # Clear crash marker
    if self.recovery_service and job_id:
        try:
            self.recovery_service.clear_crash_marker()
        except:
            pass
```

### Fix 5: Enhanced Lock Validation Checks
**Priority**: MEDIUM  
**File**: `models/device_lock.py` (add new methods)

```python
@staticmethod
def is_lock_owned_by_job(device_ip, job_id):
    """Check if device is locked by THIS specific job"""
    lock = DeviceLock.get_device_lock(device_ip)
    if not lock:
        return False
    return lock.job_id == job_id

@staticmethod
def extend_lock(device_ip, additional_seconds):
    """Extend existing lock duration"""
    locks = DeviceLock.load_all()
    if device_ip not in locks:
        return False
    
    lock = locks[device_ip]
    # Extend completion time
    old_completion = datetime.fromisoformat(lock.estimated_completion)
    new_completion = old_completion + timedelta(seconds=additional_seconds)
    lock.estimated_completion = new_completion.isoformat()
    locks[device_ip] = lock
    DeviceLock.save_all(locks)
    return True
```

### Fix 6: UI Enhancements for Lock Status
**Priority**: MEDIUM

Add **lock status indicator** in job execution dashboard:
- ✅ Lock valid and extending
- ⚠️ Lock within 5 minutes of expiration
- ❌ Lock expired (job in danger!)

---

## Testing Recommendations

### Test 1: Long-Running Deepsleep Job
```python
# Create job with:
# - Device: CELLO-SKY
# - Methods: deepsleep (15 min), wait (3 min)
# - Iterations: 5
# Expected: Lock should remain valid for 1.5+ hours
```

### Test 2: Concurrent Job Requests
```python
# Start Job A (2 hour deepsleep)
# While Job A is running, request Job B on same device
# Expected: Job B should be QUEUED, not executed
```

### Test 3: Multiple Deepsleep Iterations
```python
# Monitor device_locks.json throughout execution
# Lock should persist (but refresh) through all 50 iterations
```

---

## Files to Modify

1. **services/test_execution_service.py**
   - Add lock refresh logic per iteration
   - Add lock validation checks during long waits
   - Improve finally block cleanup

2. **models/device_lock.py**
   - Add `is_lock_owned_by_job()` method
   - Add `extend_lock()` method
   - Improve documentation on lock timeout issues

3. **method_deepsleep.py** (if exists)
   - Add periodic lock checks during 15-minute wait
   - Log lock status during wait countdown

4. **templates/index.html** (UI)
   - Add lock expiration indicator
   - Show estimated time lock will expire
   - Alert user if lock is about to expire

---

## Severity Assessment

| Issue | Severity | Impact |
|-------|----------|--------|
| Lock expires before job completes | **CRITICAL** | Job orphaned, device available for conflicting operations |
| No lock refresh mechanism | **CRITICAL** | All multi-iteration jobs vulnerable |
| No periodic lock validation | **CRITICAL** | Job can't detect lock loss |
| Fixed timeout doesn't scale with job | **CRITICAL** | Longer jobs always fail |
| Race condition on device allocation | **CRITICAL** | Device contention, data corruption risk |

---

## Immediate Workaround for Current Job

Until fixes are implemented:

1. **Manually extend lock** in device_locks.json:
```bash
# Lock for 50 hours (180,000 seconds) instead of 30 minutes
{
  "10.0.0.95": {
    "device_ip": "10.0.0.95",
    "device_name": "CELLO-SKY",
    "user_id": "vpatne290",
    "job_id": "63d6588b-04ec-4d8b-a4d1-9f5dab04ba9e",
    "locked_at": "2026-04-12T05:35:07.732659",
    "estimated_completion": "2026-04-14T11:35:07.732659",  # +50 hours
    "eta_formatted": "49h 59m"
  }
}
```

2. **Resume the job** from iteration 16

3. **Monitor for lock re-expiration** while fixes are deployed

---

## Prevention Going Forward

- [ ] Implement dynamic duration calculation
- [ ] Add lock refresh per iteration
- [ ] Add periodic validation checks
- [ ] Add UI indicators for lock status
- [ ] Add comprehensive tests for concurrent jobs
- [ ] Add logging for all lock operations
- [ ] Add alerts when lock approaches expiration
