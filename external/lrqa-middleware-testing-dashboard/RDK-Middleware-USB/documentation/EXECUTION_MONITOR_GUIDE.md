# Execution Monitor Service - Documentation

## Overview

The **Execution Monitor Service** is an automated background monitoring system that continuously tracks running test executions and handles failures, device unreachability, and stuck executions. It ensures reliability and provides automatic recovery and notification capabilities.

## Features

### 1. **Continuous Execution Monitoring**
- Monitors all running and pending jobs every 30 seconds
- Tracks execution progress by monitoring iteration and step numbers
- Detects stuck executions (no progress for 3 minutes)

### 2. **Device Reachability Check**
- Automatically checks if devices are reachable via SSH
- Uses configurable timeout (default: 10 seconds)
- Validates actual connectivity with test command execution

### 3. **Automatic Recovery**
- **If Device is Reachable:**
  - Attempts to resume execution from last checkpoint
  - Retries up to 3 times before marking as failed
  - Logs recovery attempts to job's log file
  
- **If Device is Unreachable:**
  - Checks if all iterations might be completed based on log analysis
  - Generates final report if execution is complete
  - Marks job as failed if device unreachable for extended period (>5 minutes)

### 4. **Smart Completion Detection**
- Analyzes log files for completion indicators:
  - "completed successfully"
  - "All iterations completed"
  - "✓ Test execution completed"
  - Iteration count matching total iterations
- Validates `iteration_results` dictionary

### 5. **Email Notifications**
- **On Successful Completion:**
  - Sends detailed execution report
  - Includes iteration results
  - Attaches log files
  
- **On Failure:**
  - Sends failure notification with reason
  - Includes partial results
  - Attaches available logs

### 6. **Queue Management Integration**
- Automatically triggers next queued job for device when current job completes/fails
- Cleans up execution state for completed jobs
- Prevents queue bottlenecks

## Architecture

### Components

```
ExecutionMonitorService
├── Monitor Thread (daemon)
│   └── Runs monitoring loop every 30 seconds
├── Execution State Tracker
│   └── Tracks progress for each job
├── Device Reachability Checker
│   └── SSH-based connectivity validation
├── Recovery Manager
│   ├── Resume from checkpoint
│   └── Retry logic
└── Notification Manager
    ├── Email reports
    └── Job finalization
```

### Integration Points

1. **app.py** - Service initialization and lifecycle management
2. **QueueService** - Triggers next jobs after completion
3. **EmailService** - Sends notifications to users
4. **TestExecutionService** - Resumes stuck executions
5. **Job Model** - Tracks job state and progress
6. **Device Model** - Retrieves device credentials for SSH

## Configuration

### Service Parameters

```python
MONITOR_INTERVAL = 30          # Check every 30 seconds
STUCK_THRESHOLD = 180          # Consider stuck after 3 minutes
MAX_RETRY_ATTEMPTS = 3         # Max retry attempts
DEVICE_UNREACHABLE_TIMEOUT = 10  # SSH timeout in seconds
```

### Execution State Tracking

For each job, the service tracks:
- `last_update` - Timestamp of last progress
- `last_iteration` - Last completed iteration number
- `last_step` - Last completed step number
- `retry_count` - Number of resume attempts
- `device_check_count` - Number of reachability checks
- `last_check` - Timestamp of last check

## Usage

### Automatic Operation

The service starts automatically when the application launches:

```bash
python app.py
```

Output:
```
============================================================
EXECUTION MONITOR SERVICE INITIALIZATION
============================================================
✅ Execution Monitor Service: INITIALIZED
   → Will monitor running executions for stuck state
   → Auto-recovery for device reachable issues
   → Email notifications for completion/failure
============================================================

[EXECUTION MONITOR] Started - checking every 30 seconds
```

### Manual Control

```python
# In app.py or custom script
from services.execution_monitor_service import ExecutionMonitorService

# Initialize
monitor = ExecutionMonitorService(
    email_service=email_service,
    test_execution_service=test_execution_service,
    queue_service=queue_service
)

# Start monitoring
monitor.start_monitoring()

# Stop monitoring
monitor.stop_monitoring()
```

## Behavior Scenarios

### Scenario 1: Device Unreachable During Execution

```
1. Execution starts on device 10.0.0.50
2. Device becomes unreachable (network issue)
3. Monitor detects no progress for 3 minutes
4. Monitor checks device SSH - FAILED
5. Monitor analyzes log file
   - If iterations complete: Generates report, sends email
   - If incomplete: Marks failed after 5+ minutes
```

### Scenario 2: Execution Stuck (Device Reachable)

```
1. Execution stuck on iteration 5 of 10
2. Monitor detects no progress for 3 minutes
3. Monitor checks device SSH - SUCCESS
4. Monitor attempts resume (Retry 1/3)
5. If resume fails, retry 2 more times
6. After 3 failed retries: Mark job as failed
```

### Scenario 3: Execution Completes but Device Unreachable

```
1. Execution completes all 10 iterations
2. Device becomes unreachable before final status update
3. Monitor detects stuck state
4. Monitor checks device - FAILED
5. Monitor analyzes log file - finds "completed successfully"
6. Monitor marks job as completed
7. Generates report and sends success email
8. Triggers next queued job for device
```

## Logs and Monitoring

### Console Logs

```
[EXECUTION MONITOR] Checking 2 running/pending jobs
[EXECUTION MONITOR] Job 10.0.0.50_reboot_1738598400 progressing: iteration 3, step 0
[EXECUTION MONITOR] ⚠️  Job 10.0.0.60_deepsleep_1738598450 appears stuck - no progress for 185 seconds
[EXECUTION MONITOR] ✓ Device 10.0.0.60 is reachable
[EXECUTION MONITOR] Attempting to resume execution (attempt 1/3)
[EXECUTION MONITOR] ✓ Successfully resumed job 10.0.0.60_deepsleep_1738598450
```

### Job Log File Entries

```
[2026-02-03 14:30:45 UTC] [RECOVERY] Job resumed from iteration 3, step 0
[2026-02-03 14:35:20 UTC] [FAILURE] Max retry attempts reached - execution stuck
```

## Email Notifications

### Completion Email

**Subject:** Test Execution Complete - Device_Name

**Content:**
- Job ID and device details
- Method(s) executed
- Iterations completed
- Execution duration
- Pass/fail status
- Log file attachments

### Failure Email

**Subject:** Test Execution Complete - Device_Name (Failed)

**Content:**
- Job ID and device details
- Failure reason (e.g., "Device unreachable - execution could not continue")
- Iterations completed before failure
- Partial results
- Log file attachments

## Error Handling

### Graceful Degradation

1. **Email Service Unavailable:**
   - Logs warning message
   - Continues monitoring
   - Does not send notifications

2. **Queue Service Unavailable:**
   - Logs warning message
   - Completes job finalization
   - Does not trigger next job

3. **Test Execution Service Unavailable:**
   - Logs warning message
   - Cannot resume executions
   - Marks jobs as failed

### Exception Handling

All operations wrapped in try-except blocks:
- Monitor loop continues even if individual check fails
- Errors logged with full stack trace
- Execution state preserved across errors

## Performance

### Resource Usage

- **CPU:** Minimal (sleeps between checks)
- **Memory:** ~1-2 MB for state tracking
- **Network:** SSH connection per stuck job per check
- **I/O:** Log file reads for completion detection

### Scalability

- Handles unlimited number of jobs
- Scales linearly with number of stuck jobs
- Cleanup removes completed job state

## Troubleshooting

### Monitor Not Starting

```
⚠️  Execution Monitor Service: ERROR - <error_message>
```

**Solution:** Check imports and service dependencies

### Jobs Not Resuming

**Check:**
1. Test Execution Service initialized
2. Device credentials in devices.json
3. SSH connectivity to device
4. Job has execution_queue defined

### Emails Not Sending

**Check:**
1. Email Service enabled
2. SMTP credentials configured
3. User email in User model
4. Email service initialization logs

## Future Enhancements

1. **Configurable Thresholds:** Per-job or per-device stuck thresholds
2. **Advanced Recovery Strategies:** Method-specific recovery logic
3. **Metrics Dashboard:** Real-time monitoring statistics
4. **Alert Escalation:** Multi-level notification system
5. **Historical Analysis:** Stuck job patterns and trends

## Related Documentation

- [Email Service Setup](EMAIL_SETUP_GUIDE.md)
- [Job Management](APPLICATION_OVERVIEW.md)
- [Queue Service](FEATURES_IMPLEMENTED_NOV20.md)
- [Recovery Service](JOB_RECOVERY_REPORT.md)

---

**Version:** 1.0  
**Last Updated:** February 3, 2026  
**Maintainer:** LRQA Middleware Testing Team
