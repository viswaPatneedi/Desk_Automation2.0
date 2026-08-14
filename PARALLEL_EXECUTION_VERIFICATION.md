# Parallel Execution Fix - Quick Verification Guide

## What Was Fixed

**The Issue**: When triggering reboot on 2+ devices simultaneously, only the first device would execute successfully and others would fail.

**The Root Cause**: Tunnel was being unregistered immediately after first device completed, breaking subsequent devices' access during parallel execution.

**The Solution**: 
- Pre-register tunnels for ALL devices BEFORE starting threads
- Keep tunnels active until ALL devices complete
- Cleanup only after entire group finishes

## Quick Test (5 minutes)

### Prerequisites
- Application running
- At least 2 devices on same R-Pi configured
- Devices should be AVAILABLE (not locked)

### Test Steps

**Step 1: Select Multiple Devices**
1. Navigate to Devices panel
2. Select 2-4 devices from same R-Pi (e.g., DESK-R-Pi devices)
   - CELLO-SKY (10.0.0.95)
   - SKY-Glass (10.0.0.166)

**Step 2: Trigger Parallel Reboot**
1. Click "Edit Execution Queue"
2. Select "Reboot" method
3. Set iterations = 1
4. Click "Execute on Selected Devices" button
5. Confirm modal - click "Execute"

**Step 3: Monitor Progress**
1. Check Job Status panel - should show 2 jobs RUNNING
2. Check Application Logs - should see:
   ```
   [GROUP-EXEC] Pre-registering shared tunnel for CELLO-SKY...
   [GROUP-EXEC] Pre-registering shared tunnel for SKY-Glass...
   [DEVICE-EXEC] [group_...-CELLO-SKY]: Starting execution...
   [DEVICE-EXEC] [group_...-SKY-Glass]: Starting execution...
   ```
3. Monitor for "Execution completed successfully" for BOTH devices

**Step 4: Verify Completion**
1. Wait ~3-5 minutes for reboot to complete
2. Check Job Status:
   - ✅ CELLO-SKY: COMPLETED
   - ✅ SKY-Glass: COMPLETED
   - Both should show "Reboot successful"
3. Check Device Status:
   - Both devices should be AVAILABLE (unlocked)

### Expected Results (AFTER FIX)

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Device 1 | ✅ Executes | ✅ Executes |
| Device 2 | ❌ Fails ("Connection lost") | ✅ Executes |
| Device 3 | ❌ Fails ("Connection lost") | ✅ Executes |
| Device 4 | ❌ Fails ("Connection lost") | ✅ Executes |
| Time | N/A (broken) | ~3 min (parallel, not sequential) |

## Logging to Check

### Success Indicators

**In application logs (terminal running app):**

```
✅ All devices PRE-REGISTERED before execution:
[GROUP-EXEC] Pre-registering shared tunnel for CELLO-SKY...
[GROUP-EXEC] Pre-registering shared tunnel for SKY-Glass...
[GROUP-EXEC] ✅ Registered tunnel for CELLO-SKY
[GROUP-EXEC] ✅ Registered tunnel for SKY-Glass

✅ Both devices executing simultaneously:
[DEVICE-EXEC] [group_10_26_52_60-CELLO-SKY]: Starting execution...
[DEVICE-EXEC] [group_10_26_52_60-SKY-Glass]: Starting execution...

✅ Both devices completing successfully:
[DEVICE-EXEC] [group_10_26_52_60-CELLO-SKY]: Execution completed successfully
[DEVICE-EXEC] [group_10_26_52_60-SKY-Glass]: Execution completed successfully

✅ Cleanup AFTER all done:
[GROUP-EXEC] Cleaning up shared tunnel registrations...
[GROUP-EXEC] ✅ Unregistered tunnel for 10.0.0.95
[GROUP-EXEC] ✅ Unregistered tunnel for 10.0.0.166
```

### Failure Indicators (if fix didn't work)

```
❌ WRONG: Device 2 losing tunnel mid-execution
[DEVICE-EXEC] [group_10_26_52_60-SKY-Glass]: Connection lost during execution
[DEVICE-EXEC] [group_10_26_52_60-SKY-Glass]: No tunnel available

❌ WRONG: Tunnel unregistered too early
[GROUP-EXEC] ✅ Unregistered tunnel for 10.0.0.95  (← TOO EARLY!)
[DEVICE-EXEC] [group_10_26_52_60-SKY-Glass]: Tunnel unavailable
```

## Troubleshooting

### If Test Fails

**Symptom**: "Device 2 shows Connection lost"
- Check logs for premature unregistration
- Verify fix was properly applied (line 3232-3240 in test_execution_service.py)

**Symptom**: "Timeout waiting for shared tunnel"
- Increase pre-registration window
- Check R-Pi connectivity

**Symptom**: "Only first device executes"
- Ensure sync changes were saved
- Restart application: `kill <PID>` then restart

### Verify Fix Applied

```bash
# Check for the deferred cleanup code (should exist):
grep -n "Cleaning up shared tunnel registrations" \
  services/test_execution_service.py
# Output: Line 3232 should show

# Check that finally block NO LONGER has unregister:
sed -n '3300,3310p' services/test_execution_service.py
# Should NOT contain: unregister_tunnel(device.ip)
```

## Recovery If Needed

If devices get stuck in LOCKED state after failed fix:

```bash
# Option 1: Restart app (releases all locks)
pkill -f "python.*app.py"
# Wait 5 seconds
python3 app.py

# Option 2: Force unlock via database (if have ssh access):
# sqlite3 app.db
# SELECT * FROM device_locks;
# DELETE FROM device_locks WHERE device_ip='10.0.0.95';
```

## Next Steps

1. ✅ Test with 2 devices (same R-Pi) - Basic test
2. ✅ Test with 4 devices (same R-Pi) - Full capacity
3. ✅ Test with 2 R-Pis (4 devices total, 2 per R-Pi) - Multi-R-Pi parallel
4. ✅ Monitor logs for performance improvements
5. ✅ Update documentation if confirmed working

## Questions/Issues

If execution still fails on multiple devices:
1. Check `/tmp/execution_logs/` for detailed error messages
2. Check device R-Pi configuration is correct
3. Verify R-Pi connectivity with: `ssh lrqa@10.26.52.60 hostname`
4. Check device lock status in application UI

---

**Fix Applied**: services/test_execution_service.py (Lines 3200-3310)
**Date**: 11 August 2026
**Impact**: High - Fixes critical multi-device parallel execution issue
