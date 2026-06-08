# Device Lock Fix Implementation Guide

## Overview
This guide contains all code changes needed to fix the critical device locking issues that caused job 63d6588b-04ec-4d8b-a4d1-9f5dab04ba9e to fail.

---

## Change 1: Update test_execution_service.py - Lock Acquisition

**Location**: services/test_execution_service.py, around line 1700-1720 in the `execute_test_queue` method

**Current Code**:
```python
# Lock the device
lock_acquired = DeviceLock.lock_device(device_ip, job_id)
if not lock_acquired:
    return jsonify({'success': False, 'error': 'Could not acquire device lock'}), 409
```

**New Code**:
```python
# Import at top of file:
from utils.device_lock_manager import DeviceLockManager

# Then in execute_test_queue method:
# Lock the device with ACCURATE duration calculation
from flask_login import current_user

lock = DeviceLockManager.acquire_lock_with_duration(
    device_ip=device.ip,
    device_name=device.name,
    user_id=current_user.ntid,
    job_id=job_id,
    execution_queue=execution_queue,
    iterations=iterations
)

if not lock:
    existing_lock = DeviceLock.get_device_lock(device.ip)
    if existing_lock:
        return jsonify({
            'success': False, 
            'error': f'Device is locked by {existing_lock.user_id} until {existing_lock.estimated_completion}'
        }), 409
    else:
        return jsonify({'success': False, 'error': 'Could not acquire device lock'}), 409

log_service.log(f"🔒 Device locked for {lock_acquired.estimated_completion}")
log_service.log(f"   Lock duration: {(datetime.fromisoformat(lock.estimated_completion) - datetime.utcnow()).total_seconds() / 3600:.1f} hours")
```

---

## Change 2: Update test_execution_service.py - Per-Iteration Lock Refresh

**Location**: services/test_execution_service.py, around line 1550 (start of iteration loop)

**Add BEFORE the iteration starts**:
```python
# Import at top:
from utils.device_lock_manager import DeviceLockManager

# Then in the loop:
for i in range(start_iteration, iterations):
    # CRITICAL: Refresh lock at the START of each iteration
    if job_id and i > start_iteration:
        remaining_iterations = iterations - i
        if not DeviceLockManager.refresh_lock(device.ip, job_id, execution_queue, remaining_iterations):
            log_service.log(f"\n❌ CRITICAL: Device lock lost or expired!")
            log_service.log(f"⚠️  Device {device.ip} is no longer reserved for job {job_id}")
            if job_id:
                Job.update_job_status(job_id, 'failed', 
                    end_time=datetime.now(timezone.utc).isoformat(),
                    log_file_path=log_file_path
                )
                DeviceLock.unlock_device(device.ip)
            raise RuntimeError(f"Device lock lost or expired: {device.ip}")
        
        time_remaining = DeviceLock.get_time_until_expiration(device.ip)
        log_service.log(f"\n🔒 [LOCK-REFRESH] Lock refreshed for remaining {remaining_iterations} iterations")
        log_service.log(f"   Time remaining: {time_remaining // 3600}h {(time_remaining % 3600) // 60}m")
    
    # Continue with rest of iteration code...
    log_service.log(f"\n{'='*60}")
    log_service.log(f"ITERATION {i+1}/{iterations}")
    log_service.log(f"{'='*60}")
```

---

## Change 3: Update method_deepsleep.py - Lock Validation During Wait

**Location**: method_deepsleep.py, find the deepsleep wait loop (around 900 second wait)

**Current Code**:
```python
# Waiting for deepsleep duration
for elapsed_seconds in range(900):
    time.sleep(1)
    #  Print progress...
```

**New Code**:
```python
# Import at top:
from utils.device_lock_manager import DeviceLockManager

# Then replace the wait loop:
from datetime import datetime, timezone

try:
    # Use enhanced wait with lock validation
    DeviceLockManager.wait_with_lock_validation(
        duration_seconds=900,  # or sleep_duration_minutes * 60
        device_ip=device_ip,
        job_id=job_id,
        log_callback=log_service.log
    )
except RuntimeError as lock_error:
    log_service.log(f"\n❌ {str(lock_error)}")
    log_service.log(f"⚠️  Cannot continue deepsleep - device reservation lost")
    raise
```

---

## Change 4: Update test_execution_service.py - Finally Block Cleanup

**Location**: services/test_execution_service.py, around line 2220 in finally block

**Current Code**:
```python
finally:
    # Close the job-specific log handle
    if log_file_handle:
        try:
            log_file_handle.close()
        except:
            pass
    log_service.close_iteration_log()
```

**New Code**:
```python
finally:
    # Close the job-specific log handle
    if log_file_handle:
        try:
            log_file_handle.close()
        except:
            pass
    
    # CRITICAL: Ensure device is unlocked, but verify ownership first
    if job_id and device:
        try:
            if DeviceLock.is_lock_owned_by_job(device.ip, job_id):
                DeviceLock.unlock_device(device.ip)
                log_service.log(f"🔓 Device unlocked: {device.ip}")
            else:
                current_lock = DeviceLock.get_device_lock(device.ip)
                if current_lock:
                    log_service.log(f"⚠️ Device locked by job {current_lock.job_id}, not unlocking")
                else:
                    log_service.log(f"⚠️ Device already unlocked")
        except Exception as unlock_error:
            log_service.log(f"❌ Error checking lock ownership: {unlock_error}")
    
    log_service.close_iteration_log()
    
    # Clear crash marker
    if self.recovery_service and job_id:
        try:
            self.recovery_service.clear_crash_marker()
        except:
            pass
```

---

## Change 5: Add SSH Connectivity Test

**Create new file**: utils/ssh_connectivity_test.py

```python
"""SSH Connectivity Tester - Validates device accessibility"""

import paramiko
import socket
import time

class SSHConnectivityTester:
    """Test SSH connectivity to devices"""
    
    @staticmethod
    def test_connectivity(device_ip, port=10022, username='root', password='',
                          timeout=10, retries=3):
        """
        Test SSH connectivity to a device.
        
        Args:
            device_ip: Device IP address
            port: SSH port (default 10022)
            username: SSH username (default 'root')
            password: SSH password
            timeout: Connection timeout in seconds
            retries: Number of retry attempts
        
        Returns:
            dict: {
                'success': bool,
                'connected': bool,
                'attempts': int,
                'error': str or None,
                'device_info': dict or None
            }
        """
        result = {
            'success': False,
            'connected': False,
            'attempts': 0,
            'error': None,
            'device_info': None
        }
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        for attempt in range(retries):
            result['attempts'] = attempt + 1
            try:
                # Try to connect
                client.connect(
                    hostname=device_ip,
                    port=port,
                    username=username,
                    password=password,
                    timeout=timeout
                )
                
                # Connection successful
                result['connected'] = True
                
                # Get device info
                try:
                    stdin, stdout, stderr = client.exec_command('uptime')
                    uptime = stdout.read().decode().strip()
                    result['device_info'] = {'uptime': uptime}
                except:
                    pass
                
                result['success'] = True
                break
                
            except socket.timeout:
                result['error'] = f"Connection timeout (attempt {attempt + 1}/{retries})"
                if attempt < retries - 1:
                    time.sleep(2)  # Wait before retry
            
            except paramiko.AuthenticationException:
                result['error'] = "Authentication failed - check credentials"
                break
            
            except paramiko.SSHException as e:
                result['error'] = f"SSH error: {str(e)}"
                if attempt < retries - 1:
                    time.sleep(1)  # Wait before retry
            
            except Exception as e:
                result['error'] = f"Connection error: {str(e)}"
                if attempt < retries - 1:
                    time.sleep(1)  # Wait before retry
        
        finally:
            try:
                client.close()
            except:
                pass
        
        return result
    
    @staticmethod
    def diagnose_connectivity(device_ip, port=10022):
        """
        Perform comprehensive connectivity diagnosis.
        
        Args:
            device_ip: Device IP address
            port: SSH port
        
        Returns:
            dict: Diagnostic information
        """
        diagnosis = {
            'device_ip': device_ip,
            'port': port,
            'ping_reachable': False,
            'ssh_connectable': False,
            'error': None
        }
        
        # Test basic connectivity (ping)
        import os
        response = os.system(f"ping -c 1 {device_ip} > /dev/null 2>&1")
        diagnosis['ping_reachable'] = (response == 0)
        
        # Test SSH connectivity
        result = SSHConnectivityTester.test_connectivity(
            device_ip=device_ip,
            port=port,
            timeout=5,
            retries=2
        )
        
        diagnosis['ssh_connectable'] = result['connected']
        if not result['success']:
            diagnosis['error'] = result['error']
        
        return diagnosis
```

**Usage in test execution**:
```python
# Before starting job execution:
from utils.ssh_connectivity_test import SSHConnectivityTester

connectivity = SSHConnectivityTester.test_connectivity(device.ip, device.port, device.username, device.password)
if not connectivity['success']:
    log_service.log(f"❌ Cannot connect to device {device.ip}: {connectivity['error']}")
    Job.update_job_status(job_id, 'failed', end_time=datetime.now(timezone.utc).isoformat())
    return False

log_service.log(f"✓ SSH connectivity confirmed: {device.ip}")
```

---

## Change 6: Enhanced Job Status API

**Location**: app.py, add new endpoint for lock status

```python
@app.route('/api/jobs/<job_id>/lock-status', methods=['GET'])
@login_required
def get_job_lock_status(job_id):
    """Get current lock status for a job"""
    try:
        job = Job.get_job(job_id)
        if not job:
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        device_ip = job.device_ip
        lock = DeviceLock.get_device_lock(device_ip)
        
        if not lock:
            return jsonify({
                'success': True,
                'locked': False,
                'device_ip': device_ip
            })
        
        time_remaining = DeviceLock.get_time_until_expiration(device_ip)
        is_owned_by_job = lock.job_id == job_id
        
        return jsonify({
            'success': True,
            'locked': True,
            'device_ip': device_ip,
            'locked_by_job': is_owned_by_job,
            'locked_by_user': lock.user_id,
            'time_remaining_seconds': max(0, time_remaining),
            'estimated_completion': lock.estimated_completion,
            'warning': time_remaining < 600  # Warning if <10 min remaining
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

---

## Change 7: Add Monitoring Dashboard Widget

**Location**: templates/index.html - Add lock status indicator

```html
<!-- Add to job execution card -->
<div id="lock-status-indicator" style="display: none;">
    <div class="alert alert-warning" role="alert">
        <i class="bi bi-exclamation-triangle"></i>
        <span id="lock-warning-text"></span>
        <button class="btn btn-sm btn-primary" onclick="extendLock()">Extend Lock</button>
    </div>
</div>

<script>
// Check lock status every 60 seconds
setInterval(function() {
    const jobId = document.querySelector('[data-job-id]')?.dataset.jobId;
    if (!jobId) return;
    
    fetch(`/api/jobs/${jobId}/lock-status`)
        .then(r => r.json())
        .then(data => {
            const indicator = document.getElementById('lock-status-indicator');
            if (data.locked) {
                if (data.time_remaining_seconds < 600) {  // Less than 10 minutes
                    indicator.style.display = 'block';
                    const hours = Math.floor(data.time_remaining_seconds / 3600);
                    const mins = Math.floor((data.time_remaining_seconds % 3600) / 60);
                    document.getElementById('lock-warning-text').textContent = 
                        `Device lock expires in ${hours}h ${mins}m`;
                }
            } else if (data.job_id !== null) {  // Job still running but no lock
                indicator.innerHTML = '<div class="alert alert-danger">⚠️ CRITICAL: Device lock lost! Job may fail.</div>';
                indicator.style.display = 'block';
            }
        });
}, 60000);
</script>
```

---

## Testing Checklist

- [ ] Test 1: Create job with single 15-minute deepsleep
  - Monitor device_locks.json for lock validity
  - Verify lock extends/refreshes per iteration

- [ ] Test 2: Create job with 5 iterations of 15-minute deepsleep
  - Expected: Lock remains valid for ~2+ hours
  - Verify lock string shows increasing estimated_completion time

- [ ] Test 3: Concurrent job requests
  - Start Job A (2 hour deepsleep)
  - While Job A running, request same device with Job B
  - Expected: Job B queued, not executed

- [ ] Test 4: Monitor lock during deepsleep wait
  - Check logs show "lock valid ✓" every 60 seconds
  - Verify no "lock lost" errors

- [ ] Test 5: Job completion
  - Verify device lock removed after completion
  - Verify device available for next job

- [ ] Test 6: SSH connectivity validation
  - Verify device connection tested before job start
  - Verify job fails gracefully if device unreachable

---

## Deployment Steps

1. **Backup current code**:
   ```bash
   git checkout -b device-lock-fixes
   ```

2. **Create utility files**:
   - `utils/device_lock_manager.py` ✓ DONE
   - `utils/ssh_connectivity_test.py` (see Change 5)

3. **Update model**:
   - `models/device_lock.py` ✓ DONE (added new methods)

4. **Update service**:
   - `services/test_execution_service.py` (implement Changes 1-4)

5. **Update method modules**:
   - `method_deepsleep.py` (implement Change 3)

6. **Update API**:
   - `app.py` (implement Change 6)

7. **Update UI**:
   - `templates/index.html` (implement Change 7)

8. **Test thoroughly**:
   - Run test checklist above
   - Monitor logs during execution

9. **Deploy to production**:
   ```bash
   git merge device-lock-fixes
   python app.py
   ```

---

## Verification

After deployment, verify fixes with:

```bash
# Check lock is accurate
curl http://localhost:5000/api/locks

# Check job lock status
curl http://localhost:5000/api/jobs/63d6588b-04ec-4d8b-a4d1-9f5dab04ba9e/lock-status

# Monitor execution logs
tail -f logs/jobs/63d6588b-04ec-4d8b-a4d1-9f5dab04ba9e/execution.log | grep "LOCK"
```

---

## Expected Log Output (After Fixes)

```
[2026-04-12 11:16:41 UTC] 🔒 Device locked for 2026-04-12T13:16:41
   Lock duration: 2.0 hours
...
[2026-04-12 11:17:10 UTC] ITERATION 1/50
[2026-04-12 11:17:10 UTC] 🔒 [LOCK-REFRESH] Lock refreshed for remaining 49 iterations
   Time remaining: 1h 59m
...
[2026-04-12 11:22:56 UTC]   ⏱ Elapsed: 300s / 900s | Remaining: 600s (lock valid ✓)
[2026-04-12 11:23:56 UTC]   ⏱ Elapsed: 360s / 900s | Remaining: 540s (lock valid ✓)
...
[2026-04-12 13:16:41 UTC] ✅ Iteration 50/50 PASSED
[2026-04-12 13:16:41 UTC] 🔓 Device unlocked: 10.0.0.95
```

---

## Questions?

If you encounter issues:
1. Check device_locks.json for lock validity
2. Review logs for "lock lost" or "lock expired" messages
3. Test SSH connectivity to device: `ssh -p 10022 root@<device_ip>`
4. Verify job_id matches lock's job_id in device_locks.json
