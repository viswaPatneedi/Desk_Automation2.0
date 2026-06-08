# Execution Monitor - Quick Reference

## What It Does

The Execution Monitor automatically:
- ✅ Monitors all running test executions
- ✅ Detects stuck executions (no progress for 3 minutes)
- ✅ Checks if device is reachable via SSH
- ✅ Resumes execution if device is back online
- ✅ Generates reports when execution completes
- ✅ Sends email notifications to users
- ✅ Triggers next queued job automatically

## Key Scenarios

### 1. Device Becomes Unreachable

**What Happens:**
1. Monitor detects no progress for 3 minutes
2. Checks device SSH connection → **FAILED**
3. Checks log file to see if execution completed
4. **If completed:** Generates report & sends email
5. **If not completed:** Waits & rechecks (up to 5 minutes)
6. **After 5 min:** Marks job as failed & notifies user

### 2. Execution Gets Stuck (Device Online)

**What Happens:**
1. Monitor detects no progress for 3 minutes
2. Checks device SSH connection → **SUCCESS**
3. Attempts to resume execution (Retry 1/3)
4. If resume fails, retries 2 more times
5. After 3 failed retries → marks job as failed

### 3. Execution Completes but Device Goes Offline

**What Happens:**
1. All iterations complete successfully
2. Device goes offline before final status update
3. Monitor analyzes log file → finds "completed successfully"
4. Marks job as completed
5. Sends success email with results
6. Triggers next queued job

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Check Interval | 30 sec | How often to check jobs |
| Stuck Threshold | 3 min | No progress = stuck |
| Max Retries | 3 | Resume attempts |
| SSH Timeout | 10 sec | Device reachability check |
| Unreachable Threshold | 5 min | Mark failed if unreachable |

## Email Notifications

### Success Email
- Job ID, device, method, iterations
- Execution duration
- Pass/fail status
- Log file attached

### Failure Email
- Job ID, device, method
- Failure reason (device unreachable, stuck, etc.)
- Partial results
- Log file attached

## Logs Location

**Console:**
```
[EXECUTION MONITOR] Checking 2 running/pending jobs
[EXECUTION MONITOR] Job progressing: iteration 5, step 2
[EXECUTION MONITOR] ⚠️ Job stuck - attempting recovery
```

**Job Log File:**
```
[2026-02-03 14:30:45 UTC] [RECOVERY] Job resumed from iteration 3
[2026-02-03 14:35:20 UTC] [FAILURE] Device unreachable
```

## How to Check Status

### Check if Monitor is Running

```bash
# Look for this in application logs:
[EXECUTION MONITOR] Started - checking every 30 seconds
```

### Check Current Monitoring State

```bash
# Check console for periodic monitoring messages
tail -f logs/app.log | grep "EXECUTION MONITOR"
```

## Troubleshooting

### Monitor Not Running
**Symptom:** No monitoring messages in logs  
**Check:**
1. Application started successfully
2. No errors in EXECUTION MONITOR SERVICE INITIALIZATION
3. Check `execution_monitor_service` is not None

### Jobs Not Recovering
**Symptom:** Stuck jobs remain stuck  
**Check:**
1. Device SSH credentials in devices.json
2. Device actually reachable (manual SSH test)
3. Test Execution Service initialized
4. Job has `execution_queue` defined

### Emails Not Sending
**Symptom:** No emails received  
**Check:**
1. Email Service enabled (check startup logs)
2. SMTP credentials configured (SENDER_EMAIL, SENDER_PASSWORD)
3. User has valid email in User model
4. Check spam/junk folder

## Manual Actions

### Restart Monitor
```bash
# Application handles this automatically
# Just restart the Flask app
python app.py
```

### Force Check Stuck Jobs
```bash
# Use existing utility
python fix_stuck_jobs.py
```

### Clear Execution State
The monitor automatically cleans up state for completed jobs.  
No manual action needed.

## Integration

### Works With:
- ✅ Queue Service (triggers next jobs)
- ✅ Email Service (sends notifications)
- ✅ Test Execution Service (resumes executions)
- ✅ Job Model (updates job status)
- ✅ Device Model (fetches SSH credentials)

### Requires:
- ✅ Jobs must have `user_id` (for email)
- ✅ Devices must be in `devices.json` (for SSH)
- ✅ Jobs track `current_iteration` and `current_step`
- ✅ Log files exist for completion detection

## Benefits

1. **No Manual Intervention:** Automatic recovery and notification
2. **Prevents Queue Bottlenecks:** Failed jobs don't block queue
3. **User Transparency:** Email notifications keep users informed
4. **Reliable Results:** Captures results even if device goes offline
5. **Smart Recovery:** Only retries when likely to succeed

## Example Workflow

```
User triggers test → Job queued → Execution starts
         ↓
Device becomes unreachable mid-execution
         ↓
Monitor detects (after 3 min)
         ↓
Checks device SSH → FAILED
         ↓
Analyzes log file → "7/10 iterations completed"
         ↓
Waits & rechecks device (5 more minutes)
         ↓
Device still unreachable
         ↓
Marks job as FAILED
         ↓
Sends email: "Execution failed - Device unreachable (7/10 completed)"
         ↓
Triggers next queued job for device
```

---

**Quick Start:** Just run `python app.py` - monitoring starts automatically!

**Need Help?** See [EXECUTION_MONITOR_GUIDE.md](EXECUTION_MONITOR_GUIDE.md) for full documentation.
