# DeepSleep Method - Flask UI Integration Guide

## Overview

This guide shows how to integrate the new **remote_type** and **sleep_duration_minutes** parameters into the Flask application and Jobs UI.

---

## 1. Flask Endpoint Integration

### Update Jobs Submission Endpoint (app.py)

Add parameter handling to the job submission endpoint. Here's how different device methods should handle job parameters:

```python
# In app.py, update the job submission route

@app.route('/api/jobs/submit', methods=['POST'])
def submit_job():
    """
    Submit a new job/task for device execution.
    
    Expected POST parameters:
    - device_ip: Device IP address
    - method: Method name (e.g., 'deepsleep', 'reboot')
    - [method-specific parameters]: Varies by method
    
    For DeepSleep method:
    - remote_type: 'XUMO', 'SKY', or 'auto' (optional, defaults to auto)
    - sleep_duration_minutes: Integer minutes (optional, defaults to 60)
    """
    try:
        data = request.get_json() or request.form
        
        device_ip = data.get('device_ip')
        method = data.get('method')
        
        if not device_ip or not method:
            return {'error': 'Missing device_ip or method'}, 400
        
        # Get device info
        device = get_device_by_ip(device_ip)
        if not device:
            return {'error': 'Device not found'}, 404
        
        # Build method-specific parameters
        job_params = {
            'iteration': int(data.get('iteration', 1)),
            'skip_pre_validation': data.get('skip_pre_validation', False) == 'true'
        }
        
        # Add method-specific parameters
        if method == 'deepsleep':
            # Extract DeepSleep parameters
            remote_type = data.get('remote_type', '').upper() or None
            
            # Validate remote type
            if remote_type and remote_type not in ['XUMO', 'SKY']:
                if remote_type != 'AUTO':
                    return {'error': f'Invalid remote_type: {remote_type}'}, 400
                remote_type = None  # Convert 'AUTO' to None for auto-detection
            
            job_params['remote_type'] = remote_type
            
            # Extract and validate sleep duration
            try:
                sleep_duration = int(data.get('sleep_duration_minutes', 60))
                if sleep_duration < 1 or sleep_duration > 1440:  # 1 min to 24 hours
                    return {'error': 'sleep_duration_minutes must be 1-1440'}, 400
                job_params['sleep_duration_minutes'] = sleep_duration
            except ValueError:
                return {'error': 'sleep_duration_minutes must be integer'}, 400
        
        # Create job
        job_id = create_job(
            device_ip=device_ip,
            method=method,
            parameters=job_params,
            device_name=device.get('name'),
            user_id=session.get('user_id')
        )
        
        return {
            'success': True,
            'job_id': job_id,
            'message': f'Job {job_id} submitted for {method}'
        }, 202
        
    except Exception as e:
        return {'error': str(e)}, 500
```

---

## 2. Job Execution Handler

### Update Method Execution Logic

When a job is executed, pass parameters to the method controller:

```python
# In controllers/job_controller.py or similar

def execute_job(job_id):
    """Execute a queued job."""
    job = get_job(job_id)
    
    if not job:
        return False
    
    device_ip = job['device_ip']
    method = job['method']
    parameters = job.get('parameters', {})
    
    try:
        # Route to appropriate method executor
        if method == 'deepsleep':
            result = execute_deepsleep_job(
                device_ip=device_ip,
                device_name=job['device_name'],
                **parameters  # Unpacks: iteration, remote_type, sleep_duration_minutes
            )
        elif method == 'reboot':
            result = execute_reboot_job(device_ip, **parameters)
        else:
            return False
        
        update_job_status(job_id, 'completed' if result else 'failed')
        return result
        
    except Exception as e:
        update_job_status(job_id, 'failed', error=str(e))
        return False


def execute_deepsleep_job(device_ip, device_name, **kwargs):
    """
    Execute DeepSleep method with parameters.
    
    Parameters in kwargs:
    - iteration: Iteration number
    - remote_type: 'XUMO' or 'SKY' or None
    - sleep_duration_minutes: Integer (default 60)
    """
    from method_deepsleep import execute_deepsleep_process
    
    device = get_device_by_ip(device_ip)
    if not device:
        return False
    
    return execute_deepsleep_process(
        device_ip=device_ip,
        port=device['port'],
        username=device['username'],
        password=device['password'],
        device_name=device_name,
        iteration=kwargs.get('iteration', 1),
        skip_pre_validation=kwargs.get('skip_pre_validation', False),
        remote_type=kwargs.get('remote_type'),
        sleep_duration_minutes=kwargs.get('sleep_duration_minutes', 60)
    )
```

---

## 3. HTML/JavaScript UI Integration

### DeepSleep Method Form (in templates/index.html or similar)

```html
<!-- DeepSleep Method Configuration Form -->
<div id="deepsleep_method_form" style="display:none;">
    <div class="form-section">
        <h3>DeepSleep Configuration</h3>
        
        <!-- Remote Type Selection -->
        <div class="form-group">
            <label for="deepsleep_remote_type">IR Remote Type:</label>
            <select id="deepsleep_remote_type" name="remote_type" class="form-control">
                <option value="">Auto-detect (from device name)</option>
                <option value="XUMO">XUMO Remote (XUMO_PR3)</option>
                <option value="SKY">Sky Remote (SKY_LC103)</option>
            </select>
            <small class="form-text text-muted">
                Determines which IR remote control to use for waking the device.
                Auto-detect uses 'SKY' for Sky devices, 'XUMO' for others.
            </small>
        </div>
        
        <!-- Sleep Duration Selection -->
        <div class="form-group">
            <label for="deepsleep_duration">DeepSleep Duration:</label>
            <div style="display: flex; gap: 10px;">
                <select id="deepsleep_duration" name="sleep_duration_preset" 
                        class="form-control" style="flex: 1;">
                    <option value="10">Quick test (10 min)</option>
                    <option value="30">30 minutes</option>
                    <option value="60" selected>Standard (60 min / 1 hour)</option>
                    <option value="120">Extended (120 min / 2 hours)</option>
                    <option value="300">Long-running (300 min / 5 hours)</option>
                    <option value="custom">Custom duration</option>
                </select>
            </div>
            <small class="form-text text-muted">
                Time the device will remain in DeepSleep before being woken.
            </small>
        </div>
        
        <!-- Custom Duration Input (hidden by default) -->
        <div id="custom_duration_group" class="form-group" style="display:none;">
            <label for="deepsleep_custom_duration">Custom Duration (minutes):</label>
            <input type="number" id="deepsleep_custom_duration" 
                   min="1" max="1440" value="60" class="form-control"
                   placeholder="Enter minutes (1-1440, max 24 hours)">
            <small class="form-text text-muted">
                Enter any duration from 1 to 1440 minutes (24 hours).
            </small>
        </div>
        
        <!-- Iteration Count (optional) -->
        <div class="form-group">
            <label for="deepsleep_iterations">Number of Iterations:</label>
            <input type="number" id="deepsleep_iterations" 
                   min="1" max="10" value="1" class="form-control">
            <small class="form-text text-muted">
                Run DeepSleep test multiple times sequentially.
            </small>
        </div>
        
        <!-- Summary Info -->
        <div class="alert alert-info" id="deepsleep_summary">
            <strong>Estimated Execution Time:</strong>
            <span id="deepsleep_estimated_time">~65 minutes</span>
            (DeepSleep duration + validation overhead)
        </div>
    </div>
</div>

<!-- JavaScript for form handling -->
<script>
// Show/hide custom duration input
document.getElementById('deepsleep_duration').addEventListener('change', function() {
    const isCustom = this.value === 'custom';
    document.getElementById('custom_duration_group').style.display = isCustom ? 'block' : 'none';
    updateDeepsleepSummary();
});

// Update estimated execution time
function updateDeepsleepSummary() {
    const durationSelect = document.getElementById('deepsleep_duration');
    const customDuration = document.getElementById('deepsleep_custom_duration');
    const iterations = parseInt(document.getElementById('deepsleep_iterations').value) || 1;
    
    let duration = durationSelect.value === 'custom' 
        ? parseInt(customDuration.value) || 60
        : parseInt(durationSelect.value);
    
    // Add overhead: ~5-10 minutes per iteration (pre-check, post-check, logging)
    const overhead = 5;
    const totalTimePerIteration = duration + overhead;
    const totalTime = totalTimePerIteration * iterations;
    
    const hours = Math.floor(totalTime / 60);
    const minutes = totalTime % 60;
    const timeStr = hours > 0 
        ? `${hours}h ${minutes}m (~${totalTime} minutes)`
        : `${minutes} minutes`;
    
    document.getElementById('deepsleep_estimated_time').textContent = timeStr;
}

// Listen for iteration changes
document.getElementById('deepsleep_iterations').addEventListener('change', updateDeepsleepSummary);
document.getElementById('deepsleep_custom_duration').addEventListener('change', updateDeepsleepSummary);

// Initial calculation
updateDeepsleepSummary();

// Form submission
function submitDeepsleepJob() {
    const device = document.getElementById('device_select').value;
    const remoteType = document.getElementById('deepsleep_remote_type').value || null;
    const durationPreset = document.getElementById('deepsleep_duration').value;
    const customDuration = document.getElementById('deepsleep_custom_duration').value;
    const iterations = document.getElementById('deepsleep_iterations').value;
    
    const sleepDuration = durationPreset === 'custom' 
        ? parseInt(customDuration)
        : parseInt(durationPreset);
    
    // Validate
    if (!device) {
        alert('Please select a device');
        return;
    }
    
    if (sleepDuration < 1 || sleepDuration > 1440) {
        alert('Sleep duration must be 1-1440 minutes');
        return;
    }
    
    // Submit job
    const jobPayload = {
        device_ip: device,
        method: 'deepsleep',
        iteration: 1,
        remote_type: remoteType,
        sleep_duration_minutes: sleepDuration
    };
    
    // For multiple iterations, queue multiple jobs
    const jobsToSubmit = [];
    for (let i = 0; i < iterations; i++) {
        jobsToSubmit.push({
            ...jobPayload,
            iteration: i + 1
        });
    }
    
    // Submit all jobs
    Promise.all(jobsToSubmit.map(job => 
        fetch('/api/jobs/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(job)
        })
    ))
    .then(() => {
        alert(`Successfully submitted ${jobsToSubmit.length} DeepSleep job(s)`);
        loadAndDisplayJobs();  // Refresh job list
    })
    .catch(error => {
        alert(`Error submitting job: ${error}`);
    });
}
</script>
```

---

## 4. Job Display/History

### Show Job Parameters in UI

```html
<!-- Job History/Status Display -->
<table id="jobs_table" class="table table-striped">
    <thead>
        <tr>
            <th>Job ID</th>
            <th>Device</th>
            <th>Method</th>
            <th>Parameters</th>
            <th>Status</th>
            <th>Duration</th>
        </tr>
    </thead>
    <tbody id="jobs_tbody">
        <!-- Populated by JavaScript -->
    </tbody>
</table>

<script>
function formatJobParameters(params, method) {
    if (method === 'deepsleep') {
        const parts = [];
        if (params.remote_type) {
            parts.push(`Remote: ${params.remote_type}`);
        } else {
            parts.push('Remote: Auto-detect');
        }
        parts.push(`Duration: ${params.sleep_duration_minutes}m`);
        return parts.join(' | ');
    }
    return JSON.stringify(params);
}

// When displaying jobs
fetch('/api/jobs')
    .then(r => r.json())
    .then(jobs => {
        const tbody = document.getElementById('jobs_tbody');
        jobs.forEach(job => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${job.job_id}</td>
                <td>${job.device_name}</td>
                <td>${job.method}</td>
                <td>${formatJobParameters(job.parameters, job.method)}</td>
                <td><span class="badge badge-${job.status}">${job.status}</span></td>
                <td>${job.duration_minutes || '-'}</td>
            `;
        });
    });
</script>
```

---

## 5. Database/JSON Storage

### Job Queue Storage Format

```json
{
    "jobs": [
        {
            "job_id": "deepsleep_20260327_001",
            "device_ip": "192.168.1.100",
            "device_name": "XUMO-Device-01",
            "method": "deepsleep",
            "parameters": {
                "iteration": 1,
                "remote_type": "XUMO",
                "sleep_duration_minutes": 120,
                "skip_pre_validation": false
            },
            "status": "completed",
            "created_at": "2026-03-27T14:30:00Z",
            "started_at": "2026-03-27T14:35:00Z",
            "completed_at": "2026-03-27T16:42:00Z",
            "duration_minutes": 127,
            "log_file": "iteration_logs/192.168.1.100_deepsleep_20260327_143000_UTC.log"
        },
        {
            "job_id": "deepsleep_20260327_002",
            "device_ip": "192.168.1.50",
            "device_name": "SKY-Broadband-Device",
            "method": "deepsleep",
            "parameters": {
                "iteration": 1,
                "remote_type": null,
                "sleep_duration_minutes": 60,
                "skip_pre_validation": false
            },
            "status": "in_progress",
            "created_at": "2026-03-27T14:45:00Z",
            "started_at": "2026-03-27T14:50:00Z"
        }
    ]
}
```

---

## 6. Parameter Validation

### Validation Rules

```python
# validation_helpers.py

DEEPSLEEP_VALIDATION_RULES = {
    'remote_type': {
        'allowed_values': ['XUMO', 'SKY', None],
        'default': None,
        'validation': lambda x: x is None or x.upper() in ['XUMO', 'SKY'],
        'error_message': 'remote_type must be XUMO, SKY, or empty for auto-detect'
    },
    'sleep_duration_minutes': {
        'type': int,
        'min': 1,
        'max': 1440,  # 24 hours
        'default': 60,
        'validation': lambda x: isinstance(x, int) and 1 <= x <= 1440,
        'error_message': 'sleep_duration_minutes must be integer 1-1440'
    }
}

def validate_deepsleep_params(params):
    """Validate DeepSleep method parameters."""
    errors = []
    
    # Validate remote_type
    remote_type = params.get('remote_type')
    if remote_type is not None:
        if not isinstance(remote_type, str) or remote_type.upper() not in ['XUMO', 'SKY']:
            errors.append('remote_type must be XUMO, SKY, or empty')
    
    # Validate sleep_duration_minutes
    duration = params.get('sleep_duration_minutes', 60)
    try:
        duration = int(duration)
        if duration < 1 or duration > 1440:
            errors.append('sleep_duration_minutes must be 1-1440')
    except (ValueError, TypeError):
        errors.append('sleep_duration_minutes must be integer')
    
    return errors
```

---

## 7. Logging & Execution Tracking

### Job Execution Log Example

```
================================================================================
DEEPSLEEP PROCESS - START
================================================================================
Device: XUMO-Device-01 (192.168.1.100)
Iteration: 1
DeepSleep Duration: 120 minutes
Remote Type: XUMO
Method Started At: 2026-03-27T14:35:00.123456Z
================================================================================

[PRE-DEEPSLEEP VALIDATION] Checking device state...
✓ Device is on HOME screen
✓ Device SSH connection: OK
✓ Device screenshot captured

Initiating DeepSleep cycle...
✓ DeepSleep timer set: sys.settimeout(timeout_val=3600, timeout_type=0)
✓ POWER key sent (IR Code: XUMO_POWER)

Waiting 60 seconds for device to enter DeepSleep confirmed...
✓ Device SSH connectivity lost (expected - device in DeepSleep)

⏱️  DeepSleep duration: 120 minutes (7200 seconds)
Waiting 7200 seconds before waking device from DeepSleep...
  ⏱️  Progress: 60/7200 seconds (1m elapsed, 119m remaining)
  ⏱️  Progress: 120/7200 seconds (2m elapsed, 118m remaining)
  ⏱️  Progress: 600/7200 seconds (10m elapsed, 110m remaining)
  ⏱️  Progress: 3600/7200 seconds (60m elapsed, 60m remaining)
  ⏱️  Progress: 7140/7200 seconds (119m elapsed, 1m remaining)
✓ DeepSleep wait complete (7200 seconds = 120 minutes)

Sending IR POWER command to wake device from DeepSleep...
📡 Using user-selected remote type: XUMO
🔌 Using IR port 1 with iTach at 192.168.1.50:4999
📡 Remote type: XUMO_PR3
✓ IR POWER command sent successfully

Waiting 15 seconds for device to wake up and connect via SSH...
✓ Device is back online (SSH connected successfully after 8 attempts)

Checking if device is on HOME screen after DeepSleep...
✓ Device is on HOME screen
✓ Device screenshot captured

================================================================================
DEEPSLEEP PROCESS - COMPLETED
================================================================================
Total Duration: 127 minutes
Status: SUCCESS
Method Completed At: 2026-03-27T16:42:30.456789Z
================================================================================
```

---

## 8. Quick Reference: Integration Checklist

- [ ] Update `/api/jobs/submit` endpoint to accept `remote_type` and `sleep_duration_minutes`
- [ ] Add parameter validation in the endpoint
- [ ] Update job execution handler to pass parameters to `execute_deepsleep_process()`
- [ ] Add DeepSleep form section to UI with dropdown/input fields
- [ ] Add JavaScript to show/hide custom duration input
- [ ] Add estimated execution time calculator
- [ ] Update job history display to show parameters
- [ ] Update database/JSON schema for storing parameters
- [ ] Test with various parameter combinations
- [ ] Update API documentation
- [ ] Update user-facing help/guide

---

## Summary

This integration allows:

1. **User selects remote type** → Passed to Flask endpoint → Passed to method → IR command uses selected remote
2. **User selects sleep duration** → Passed to Flask endpoint → Passed to method → Sleep loop runs configured duration
3. **UI shows estimated time** → Dynamically calculated based on parameters
4. **Job history persists** → Parameters stored with job → Can re-run with same config
5. **Backward compatible** → Old code still works with defaults

**File Dependencies:**
- `app.py` - Flask endpoints
- `method_deepsleep.py` - Execution logic (already updated)
- `templates/index.html` - UI form
- `device_job_queue.json` or similar - Job storage

---

**Last Updated:** 2026-03-27  
**Status:** Complete Integration Guide  
**Related Files:** DEEPSLEEP_CONFIGURATION_GUIDE.md, method_deepsleep.py
