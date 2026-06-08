# Maintenance > DeepSleep > Wakeup - Integration Guide

## Overview

This guide explains how to integrate the new `maintenance_deepsleep_wakeup` method into your existing test workflows and sequences.

---

## Integration Points

### 1. **TestExecutionService Integration** ✅ Already Configured
The method is automatically registered in `services/test_execution_service.py`:

```python
# Line 32 (added): Import the method
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process

# Lines 715-735 (added): Method handler in _execute_queue_sequence()
elif method == "maintenance_deepsleep_wakeup":
    remote_type_mdw = queue_item.get('remote_type', None)
    sleep_duration = queue_item.get('sleep_duration_minutes', 60)
    method_result = execute_maintenance_deepsleep_wakeup_process(...)
```

**No additional integration needed in app.py** - the service handles it automatically.

---

## Usage Patterns

### Pattern 1: Standalone Method (Simple)
```python
# In your test controller or flow
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup"
    }
]

test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1
)
```

### Pattern 2: With Custom Parameters
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "remote_type": "SKY",              # Optional: XUMO or SKY
        "sleep_duration_minutes": 120      # Optional: Default 60
    }
]

test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1,
    job_id="job-123"                      # Optional: For lock management
)
```

### Pattern 3: In Sequence with Other Methods
```python
execution_queue = [
    {"method": "reboot"},                          # Pre-test warmup
    {
        "method": "maintenance_deepsleep_wakeup",  # Main maintenance test
        "sleep_duration_minutes": 60
    },
    {"method": "ir_test", "ir_keys": ["POWER"]}    # Post-test validation
]

test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=1,
    sequence_name="Complete Device Maintenance Suite"
)
```

### Pattern 4: Multiple Iterations
```python
execution_queue = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "sleep_duration_minutes": 60
    }
]

# Run 5 times to test consistency
test_execution_service.execute_test_queue(
    device_ip="10.0.0.126",
    execution_queue=execution_queue,
    iterations=5,
    job_id="job-stress-test"
)
```

### Pattern 5: Direct Function Call (Advanced)
```python
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process
from services.test_execution_service import TestExecutionService

result = execute_maintenance_deepsleep_wakeup_process(
    device_ip="10.0.0.126",
    port=10022,
    username="root",
    password="skypass",
    iteration=1,
    device_name="SKY-Device-1",
    remote_type="SKY",
    sleep_duration_minutes=60,
    job_id="job-123"
)

# Process result
if result['success']:
    wakeup_time = result['wakeup_time_seconds']
    print(f"✓ Device woke up in {wakeup_time:.1f} seconds")
else:
    print(f"✗ Failed: {result['details']}")
```

---

## Frontend Integration (if applicable)

### Adding Method to UI Dropdown
If your UI has a method selector, add to the list:

```python
# In app.py or UI controller
AVAILABLE_METHODS = [
    "reboot",
    "reboot_performance",
    "reboot_performance_v2",
    "deepsleep",
    "maintenance_deepsleep_wakeup",  # ← Add this
    "ir_test",
    "voice_command",
    # ... others
]
```

### UI Parameters
If your UI has parameter input, add these fields:

```html
<!-- Method-specific parameters -->
<div id="mdw-params" style="display:none;">
    <label for="mdw-remote-type">Remote Type:</label>
    <select id="mdw-remote-type">
        <option value="">Auto-detect (from device name)</option>
        <option value="XUMO">XUMO</option>
        <option value="SKY">SKY</option>
    </select>
    
    <label for="mdw-sleep-duration">Sleep Duration (minutes):</label>
    <input type="number" id="mdw-sleep-duration" min="10" max="600" value="60">
</div>
```

### UI Show/Hide Logic
```javascript
// Show parameters when method is selected
document.getElementById('method-select').addEventListener('change', function(e) {
    if (e.target.value === 'maintenance_deepsleep_wakeup') {
        document.getElementById('mdw-params').style.display = 'block';
    } else {
        document.getElementById('mdw-params').style.display = 'none';
    }
});
```

---

## Configuration Integration

### devices.json
Ensure your device has proper IR configuration:

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

### config_timing.py
Timing is already configured, but can be customized:

```python
# Existing values (no changes needed)
wait_for_deepsleep = 60          # Initial wait for DeepSleep entry
wait_after_wakeup = 20           # Wait after IR wake command
MAINTENANCE_WAIT_AFTER_REBOOT = 900  # 15 minutes
```

---

## Results Integration

### Accessing Result Data
```python
result = execute_maintenance_deepsleep_wakeup_process(...)

# Available fields:
iteration = result['iteration']              # 1
success = result['success']                  # True/False
wakeup_time = result['wakeup_time_seconds']  # 45.3 (or None if failed)
screenshots = result['screenshots']          # List of paths
logs = result['logs']                        # List of paths
details = result['details']                  # Summary string
```

### Storing Results
```python
from models.test_result import TestResult

# Store result in database (if applicable)
test_result = TestResult(
    device_ip="10.0.0.126",
    method="maintenance_deepsleep_wakeup",
    iteration=1,
    success=result['success'],
    duration_seconds=result.get('wakeup_time_seconds'),
    data={
        'wakeup_time': result.get('wakeup_time_seconds'),
        'screenshots': result.get('screenshots'),
        'details': result.get('details')
    }
)
test_result.save()
```

### Displaying Results
```python
# In your results reporting
wakeup_time = result.get('wakeup_time_seconds')

print(f"{'✓' if result['success'] else '✗'} Maintenance > DeepSleep > Wakeup")
print(f"  Iteration: {result['iteration']}")
print(f"  Wakeup Time: {wakeup_time:.1f}s" if wakeup_time else "  Wakeup Time: N/A (Failed)")
print(f"  Status: {'PASSED' if result['success'] else 'FAILED'}")
print(f"  Details: {result['details']}")
```

---

## Logging Integration

### Log Service Integration
Logging is automatically handled by method_utils.py:

```python
from services.log_service import LogService

log_service = LogService()
# Logs are automatically written to:
# - iteration_logs/device_MAINTENANCE_DEEPSLEEP_WAKEUP_UTC.log
# - Console output (real-time)
```

### Custom Log Handling
```python
from method_utils import log_message

# All log_message() calls within the method are captured
log_message("Custom log entry")  # Automatically prefixed and timestamped
```

---

## Error Handling Integration

### With Try-Catch
```python
try:
    result = execute_maintenance_deepsleep_wakeup_process(
        device_ip="10.0.0.126",
        port=10022,
        username="root",
        password="skypass",
        device_name="SKY-Device-1"
    )
    
    if not result['success']:
        print(f"Method failed: {result['details']}")
        # Handle specific failure modes
        if "lock lost" in result['details'].lower():
            print("Device lock was lost - retry with a new job")
        elif "not wake up" in result['details'].lower():
            print("IR wake-up may have failed - check iTach")
        
except Exception as e:
    print(f"Unexpected error: {str(e)}")
```

### Status Propagation
```python
# If using in a sequence, handle failures
execution_queue = [
    {"method": "reboot"},
    {"method": "maintenance_deepsleep_wakeup"},
    {"method": "ir_test"}
]

for iteration in range(1, 4):  # 3 iterations
    results = execute_test_queue(...)
    
    # Check if maintenance method succeeded
    maintenance_result = results.get('maintenance_deepsleep_wakeup')
    if not maintenance_result['success']:
        print("Maintenance failed - stopping sequence")
        break  # Stop on failure
    else:
        wakeup_time = maintenance_result['wakeup_time_seconds']
        print(f"Wakeup time: {wakeup_time:.1f}s")
```

---

## Performance Monitoring Integration

### Wakeup Time Tracking
```python
import json
from datetime import datetime

# Collect wakeup times across iterations
wakeup_times = []

for iteration in range(1, 11):  # 10 iterations
    result = execute_maintenance_deepsleep_wakeup_process(
        device_ip="10.0.0.126",
        port=10022,
        username="root",
        password="skypass",
        iteration=iteration
    )
    
    if result['success']:
        wakeup_times.append(result['wakeup_time_seconds'])

# Analyze performance
if wakeup_times:
    import statistics
    avg_time = statistics.mean(wakeup_times)
    min_time = min(wakeup_times)
    max_time = max(wakeup_times)
    std_dev = statistics.stdev(wakeup_times) if len(wakeup_times) > 1 else 0
    
    report = {
        "test_date": datetime.now().isoformat(),
        "device": "10.0.0.126",
        "iterations": len(wakeup_times),
        "average_wakeup_seconds": avg_time,
        "min_wakeup_seconds": min_time,
        "max_wakeup_seconds": max_time,
        "std_dev": std_dev
    }
    
    with open('wakeup_performance_report.json', 'w') as f:
        json.dump(report, f, indent=2)
```

### Dashboarding
```python
# For your dashboard/reporting system
metrics = {
    "method": "maintenance_deepsleep_wakeup",
    "wakeup_time_seconds": 45.3,
    "success": True,
    "maintenance_duration_minutes": 45,
    "deepsleep_confirmed": True,
    "homescreen_verified": True
}

# Send to your metrics system
send_to_dashboard(metrics)
```

---

## Sequence Integration Examples

### Example 1: Daily Maintenance Test
```python
# Scheduled daily at 10 PM
daily_maintenance_sequence = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "sleep_duration_minutes": 60,
        "remote_type": "SKY"
    }
]

# Execute on all production devices
for device in production_devices:
    test_execution_service.execute_test_queue(
        device_ip=device.ip,
        execution_queue=daily_maintenance_sequence,
        iterations=1,
        sequence_name="Daily Maintenance Test"
    )
```

### Example 2: Pre-Release Validation
```python
# Test suite before pushing new firmware
prerelease_validation = [
    {"method": "reboot"},
    {"method": "reboot_performance_v2"},
    {
        "method": "maintenance_deepsleep_wakeup",
        "sleep_duration_minutes": 120  # Longer sleep for new firmware
    },
    {"method": "ir_test", "ir_keys": ["POWER", "OK", "BACK"]},
    {"method": "voice_command", "voice_text": "hello"}
]

for iteration in range(1, 6):  # 5 iterations
    results = test_execution_service.execute_test_queue(
        device_ip="10.0.0.126",
        execution_queue=prerelease_validation,
        iterations=1,
        sequence_name=f"Pre-Release Validation - Iteration {iteration}"
    )
    
    # Validate all methods passed
    all_passed = all(r['success'] for r in results.values())
    if not all_passed:
        print(f"Validation failed at iteration {iteration}")
        break
```

### Example 3: Stress Test (Multiple Iterations)
```python
# Long-running stability test
stress_test_sequence = [
    {
        "method": "maintenance_deepsleep_wakeup",
        "sleep_duration_minutes": 60
    }
]

results_summary = {
    "total": 10,
    "passed": 0,
    "failed": 0,
    "wakeup_times": []
}

for iteration in range(1, 11):
    result = execute_maintenance_deepsleep_wakeup_process(
        device_ip="10.0.0.126",
        port=10022,
        username="root",
        password="skypass",
        iteration=iteration
    )
    
    if result['success']:
        results_summary["passed"] += 1
        results_summary["wakeup_times"].append(result['wakeup_time_seconds'])
    else:
        results_summary["failed"] += 1

# Report results
print(f"Stress Test Summary:")
print(f"  Passed: {results_summary['passed']}/{results_summary['total']}")
print(f"  Failed: {results_summary['failed']}/{results_summary['total']}")
if results_summary['wakeup_times']:
    avg_wakeup = sum(results_summary['wakeup_times']) / len(results_summary['wakeup_times'])
    print(f"  Average wakeup time: {avg_wakeup:.1f} seconds")
```

---

## Database Integration (if applicable)

### Result Storage
```python
from models.test_execution import TestExecution

# Store execution record
execution = TestExecution(
    device_ip="10.0.0.126",
    method_name="maintenance_deepsleep_wakeup",
    iteration=1,
    start_time=datetime.now(),
    end_time=datetime.now(),
    success=result['success'],
    wakeup_time_seconds=result.get('wakeup_time_seconds'),
    details=result['details'],
    screenshots=','.join(result['screenshots']),
    logs=','.join(result['logs'])
)
execution.save()
```

### Query & Analytics
```python
# Get all successful wakeup times from past 30 days
from datetime import datetime, timedelta

thirty_days_ago = datetime.now() - timedelta(days=30)
executions = TestExecution.query.filter(
    TestExecution.method_name == 'maintenance_deepsleep_wakeup',
    TestExecution.success == True,
    TestExecution.start_time >= thirty_days_ago
).all()

wakeup_times = [e.wakeup_time_seconds for e in executions if e.wakeup_time_seconds]
print(f"Average wakeup time (30 days): {sum(wakeup_times) / len(wakeup_times):.1f}s")
```

---

## Testing Integration

### Unit Test Example
```python
import unittest
from method_maintenance_deepsleep_wakeup import execute_maintenance_deepsleep_wakeup_process

class TestMaintenanceDeepSleepWakeup(unittest.TestCase):
    
    def test_method_returns_required_fields(self):
        """Verify method returns all required fields"""
        result = execute_maintenance_deepsleep_wakeup_process(
            device_ip="10.0.0.126",
            port=10022,
            username="root",
            password="skypass"
        )
        
        self.assertIn('iteration', result)
        self.assertIn('success', result)
        self.assertIn('wakeup_time_seconds', result)
        self.assertIn('screenshots', result)
        self.assertIn('details', result)
    
    def test_wakeup_time_positive(self):
        """Verify wakeup time is positive when successful"""
        result = execute_maintenance_deepsleep_wakeup_process(...)
        
        if result['success']:
            self.assertGreater(result['wakeup_time_seconds'], 0)
            self.assertLess(result['wakeup_time_seconds'], 300)  # Less than 5 min
```

---

## Checklist

- [x] Method is imported in TestExecutionService
- [x] Method handler is implemented for queue execution
- [x] Configuration (devices.json) is verified
- [x] IR configuration is set up
- [x] Timing parameters are configured
- [x] Error handling is in place
- [x] Logging is configured
- [x] Result storage is set up (if needed)
- [x] UI integration is complete (if needed)
- [x] Documentation is accessible
- [x] Testing is configured (if needed)

---

## Support & Questions

### Common Questions

**Q: Do I need to modify app.py?**  
A: No, the method is automatically registered through TestExecutionService.

**Q: How do I use custom sleep duration?**  
A: Add `"sleep_duration_minutes": 120` to the queue item.

**Q: Can I use this in a sequence with other methods?**  
A: Yes, add it to the execution_queue array with other methods.

**Q: How long does it take?**  
A: Typically 60-95 minutes depending on device and maintenance time.

**Q: What is the key metric I should track?**  
A: `wakeup_time_seconds` - the time from IR POWER to SSH accessibility.

### Troubleshooting Integration

See [MAINTENANCE_DEEPSLEEP_WAKEUP_QUICK_REF.md](MAINTENANCE_DEEPSLEEP_WAKEUP_QUICK_REF.md) "Common Issues & Solutions" section.

---

## Summary

The `maintenance_deepsleep_wakeup` method is designed for easy integration into existing workflows:

✅ No app.py modifications needed  
✅ Works with existing TestExecutionService  
✅ Compatible with sequences and multiple iterations  
✅ Supports performance tracking via wakeup_time_seconds  
✅ Full error handling and recovery  
✅ Ready for production use  

---

**Last Updated**: 2026-04-14  
**Status**: Ready for Integration
